import os
import json
import logging
import requests
import redis
import openai
import traceback
from flask import Flask, request, jsonify
from typing import Dict, Any, List, Optional

# --- Environment and Constants ---
LARK_APP_ID = os.getenv("LARK_APP_ID")
LARK_APP_SECRET = os.getenv("LARK_APP_SECRET")
LARK_VERIFICATION_TOKEN = os.getenv("LARK_VERIFICATION_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
CLEAR_REDIS_ON_STARTUP = os.getenv("CLEAR_REDIS_ON_STARTUP", "false").lower() == "true"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

DEFAULT_OPENAI_MODEL = "gpt-4.1"
OPENAI_API_TIMEOUT = int(os.getenv("OPENAI_API_TIMEOUT", 60))

OPENAI_TEMPERATURE = 0.7
OPENAI_TOP_P = 1.0
OPENAI_MAX_TOKENS = 2000
CHAT_CONTEXT_MAX_MESSAGES = 20
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'prompts')

# --- Initialization ---
app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

openai_client = openai.OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
PROMPTS: Dict[str, str] = {}
r: Optional[redis.Redis] = None

def load_prompts():
    global PROMPTS
    PROMPTS.clear()
    if not os.path.exists(PROMPTS_DIR):
        logger.warning("Prompts directory not found at %s. Using a default fallback prompt.", PROMPTS_DIR)
        PROMPTS['default'] = "You are a helpful AI assistant."
        return
    for filename in os.listdir(PROMPTS_DIR):
        if filename.endswith('.txt'):
            role_name = filename[:-4]
            filepath = os.path.join(PROMPTS_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    PROMPTS[role_name] = f.read().strip()
            except IOError as e:
                logger.error("Error loading prompt file %s: %s", filepath, e)
    if 'default' not in PROMPTS:
        logger.warning("'default.txt' not found. Using an internal fallback prompt.")
        PROMPTS['default'] = "You are a helpful AI assistant."
    logger.info("Loaded %d prompts: %s", len(PROMPTS), list(PROMPTS.keys()))

try:
    r = redis.from_url(REDIS_URL, decode_responses=True)
    r.ping()
    redis_info = r.connection_pool.connection_kwargs
    logger.info("Successfully connected to Redis at %s:%s.", redis_info.get('host'), redis_info.get('port'))
    if CLEAR_REDIS_ON_STARTUP:
        r.flushdb()
        logger.warning("Redis database has been flushed on startup as requested.")
except redis.exceptions.ConnectionError as e:
    logger.error("Could not connect to Redis using URL '%s'. Error: %s", REDIS_URL, e)
    r = None

def get_lark_access_token() -> Optional[str]:
    token_key = "lark_access_token"
    if r and r.exists(token_key):
        return r.get(token_key)
    
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": LARK_APP_ID, "app_secret": LARK_APP_SECRET}
    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == 0:
            token, expire_in = data["tenant_access_token"], data["expire"]
            if r:
                r.setex(token_key, expire_in - 120, token)
            return token
        else:
            logger.error("Failed to get Lark token, response: %s", response.text)
    except requests.RequestException as e:
        logger.error("Exception getting Lark token: %s", e)
    return None

def send_lark_message(chat_id: str, content: str, log_context: Dict = None) -> Optional[str]:
    access_token = get_lark_access_token()
    if not access_token:
        logger.error("Failed to send message: could not retrieve access token.", extra=log_context)
        return None
    
    card_content = {"config": {"wide_screen_mode": True}, "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": content}}]}
    url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    payload = {"receive_id": chat_id, "msg_type": "interactive", "content": json.dumps(card_content)}
    headers = {"Content-Type": "application/json; charset=utf-8", "Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        data = response.json()
        if data.get("code") == 0:
            message_id = data.get("data", {}).get("message_id")
            logger.info("Successfully sent initial message.", extra={"message_id": message_id, **(log_context or {})})
            return message_id
        else:
            logger.error("Failed to send Lark message: %s", response.text, extra=log_context)
    except requests.RequestException as e:
        logger.error("Exception sending Lark message: %s", e, extra=log_context)
    return None

def patch_lark_message(message_id: str, content: str, log_context: Dict = None):
    access_token = get_lark_access_token()
    if not access_token:
        logger.error("Failed to patch message: could not retrieve access token.", extra=log_context)
        return
        
    card_content = {"config": {"wide_screen_mode": True}, "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": content}}]}
    url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}"
    payload = {"content": json.dumps(card_content)}
    headers = {"Content-Type": "application/json; charset=utf-8", "Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.patch(url, headers=headers, json=payload, timeout=5)
        if response.json().get("code") != 0:
            logger.error("Failed to patch Lark message %s: %s", message_id, response.text, extra=log_context)
    except requests.RequestException as e:
        logger.error("Exception patching Lark message %s: %s", message_id, e, extra=log_context)

def get_chat_context(chat_id: str) -> List[Dict[str, Any]]:
    if not r: return []
    context = r.get(f"chat_context:{chat_id}")
    return json.loads(context) if context else []

def save_chat_context(chat_id: str, context: List[Dict[str, Any]]):
    if not r: return
    r.set(f"chat_context:{chat_id}", json.dumps(context), ex=7200)

def trim_chat_context(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if len(messages) > (CHAT_CONTEXT_MAX_MESSAGES * 2 + 1):
        return messages[-(CHAT_CONTEXT_MAX_MESSAGES * 2 + 1):]
    return messages

def is_message_processed_redis(message_id: str) -> bool:
    if not r: return False
    return r.exists(f"msg_id:{message_id}")

def mark_message_as_processed_redis(message_id: str):
    if not r: return
    r.setex(f"msg_id:{message_id}", 86400, "processed")

def get_chat_settings(chat_id: str) -> Dict[str, str]:
    if not r: return {}
    return r.hgetall(f"settings:{chat_id}")

def set_chat_setting(chat_id: str, key: str, value: str):
    if not r: return
    r.hset(f"settings:{chat_id}", key, value)
    r.expire(f"settings:{chat_id}", 7 * 86400)

def handle_command(command: str, args: List[str], chat_id: str, log_context: Dict):
    if command == "/help":
        available_roles = ", ".join([f"**{role}**" for role in PROMPTS.keys()])
        help_text = (
            "**🤖 Available Commands**\n\n"
            "- **/help**: Show this help message.\n\n"
            "- **/clear**: Clear the current conversation context and settings.\n\n"
            f"- **/model <model_name>**: Switch the AI model. e.g., **/model {DEFAULT_OPENAI_MODEL}**\n"
            f"  Current default model: **{DEFAULT_OPENAI_MODEL}**\n\n"
            "- **/role <role_name>**: Switch the bot's role (system prompt).\n"
            f"  Available roles: {available_roles}\n"
            "  Default role: **default**\n\n"
            "😊 Enjoy!"
        )
        send_lark_message(chat_id, help_text, log_context)
    elif command == "/clear":
        if r:
            r.delete(f"chat_context:{chat_id}")
            r.delete(f"settings:{chat_id}")
        logger.info("Conversation history and settings cleared.", extra=log_context)
        send_lark_message(chat_id, "✨ Conversation history and settings have been cleared. Let's start over!", log_context)
    elif command == "/model":
        if not args:
            send_lark_message(chat_id, f"🤔 Please provide a model name. e.g., **/model {DEFAULT_OPENAI_MODEL}**", log_context)
            return
        model_name = args[0].strip()
        set_chat_setting(chat_id, 'model', model_name)
        logger.info("Model switched to: %s", model_name, extra=log_context)
        send_lark_message(chat_id, f"✅ Model switched to: **{model_name}**", log_context)
    elif command == "/role":
        if not args:
            send_lark_message(chat_id, f"🤔 Please provide a role name. Available roles: {', '.join([f'**{r}**' for r in PROMPTS.keys()])}", log_context)
            return
        role_name = args[0].strip()
        if role_name not in PROMPTS:
            logger.warning("Role not found: %s", role_name, extra=log_context)
            send_lark_message(chat_id, f"❌ Role not found: **{role_name}**.\nPlease choose from available roles: {', '.join([f'**{r}**' for r in PROMPTS.keys()])}", log_context)
            return
        set_chat_setting(chat_id, 'role', role_name)
        logger.info("Role switched to: %s", role_name, extra=log_context)
        send_lark_message(chat_id, f"🎭 Role switched to: **{role_name}**", log_context)
    else:
        logger.warning("Unknown command received: %s", command, extra=log_context)
        send_lark_message(chat_id, f"🤷‍♀️ Unknown command: **{command}**. Send **/help** to see available commands.", log_context)

@app.route('/api/lark_callback', methods=['POST'])
def lark_callback():
    data = request.json
    if data and "challenge" in data:
        return jsonify({"challenge": data["challenge"]})
    
    header = data.get("header", {})
    if header.get("token") != LARK_VERIFICATION_TOKEN:
        logger.warning("Invalid verification token received.")
        return jsonify({"msg": "Invalid token"}), 401
    
    event = data.get("event", {})
    message = event.get("message", {})
    sender = event.get("sender", {})
    
    if sender.get("sender_type") == "app" or not message:
        return jsonify({"msg": "Ignoring bot message or empty message"})

    message_id = message.get("message_id")
    chat_id = message.get("chat_id")
    log_context = {"chat_id": chat_id, "message_id": message_id}

    if not message_id or is_message_processed_redis(message_id):
        logger.info("Duplicate message ignored.", extra=log_context)
        return jsonify({"msg": "ok, duplicate message ignored"})
    mark_message_as_processed_redis(message_id)

    message_type = message.get("message_type")
    user_message_content = []
    if message_type == "text":
        text_content = json.loads(message.get("content", "{}")).get("text", "").strip()
        if text_content.startswith('/'):
            parts = text_content.split()
            logger.info("Handling command '%s'.", parts[0], extra=log_context)
            handle_command(parts[0], parts[1:], chat_id, log_context)
            return jsonify({"msg": "Command handled"})
        elif text_content:
            user_message_content = [{"type": "text", "text": text_content}]

    if user_message_content:
        placeholder_content = "Thinking... 🧐"
        message_id_to_patch = send_lark_message(chat_id, placeholder_content, log_context)

        if not message_id_to_patch:
            logger.error("Failed to get message_id for patching, aborting.", extra=log_context)
            send_lark_message(chat_id, "Oops, failed to send the initial message.", log_context)
            return jsonify({"msg": "error: could not send initial message"})
        
        log_context["placeholder_id"] = message_id_to_patch

        try:
            settings = get_chat_settings(chat_id)
            model = settings.get('model', DEFAULT_OPENAI_MODEL)
            role_name = settings.get('role', 'default')
            system_prompt = PROMPTS.get(role_name, PROMPTS['default'])

            history = get_chat_context(chat_id)
            messages_to_send = [{"role": "system", "content": system_prompt}, *history, {"role": "user", "content": user_message_content}]
            
            params = {
                "model": model,
                "messages": trim_chat_context(messages_to_send),
                "temperature": OPENAI_TEMPERATURE,
                "top_p": OPENAI_TOP_P,
                "timeout": OPENAI_API_TIMEOUT
            }
            if OPENAI_MAX_TOKENS:
                params["max_tokens"] = OPENAI_MAX_TOKENS
            
            logger.info("Requesting AI completion.", extra=log_context)
            completion = openai_client.chat.completions.create(**params)
            response_text = completion.choices[0].message.content.strip()
            
            patch_lark_message(message_id_to_patch, response_text, log_context)
            
            history.append({"role": "user", "content": user_message_content})
            history.append({"role": "assistant", "content": response_text})
            save_chat_context(chat_id, history)
            logger.info("Successfully processed message and patched response.", extra=log_context)

        except Exception as e:
            error_message = f"🤯 Oops, an error occurred during processing...\n\n**Error details**:\n`{type(e).__name__}`"
            logger.exception("An error occurred during AI processing:", extra=log_context)
            patch_lark_message(message_id_to_patch, error_message, log_context)

    return jsonify({"msg": "ok"})

if __name__ == '__main__':
    load_prompts()
    app.run(host='0.0.0.0', port=5001, debug=True)
