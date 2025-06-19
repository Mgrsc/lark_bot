import os
import json
import logging
import re
import time
from flask import Flask, request, jsonify
from api import config
from api.services import lark_service, openai_service, redis_service
from api.commands import handler as command_handler

app = Flask(__name__)

log_level = logging.DEBUG if config.DEBUG_MODE else logging.INFO
logging.basicConfig(level=log_level,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

if config.DEBUG_MODE:
    logger.info("Debug mode is enabled. Verbose logging will be shown.")

def load_prompts():
    if not os.path.exists(config.PROMPTS_DIR):
        logger.error("Prompts directory not found at %s. Please create it.", config.PROMPTS_DIR)
        return
    for filename in os.listdir(config.PROMPTS_DIR):
        if filename.endswith('.txt'):
            name = filename[:-4]
            filepath = os.path.join(config.PROMPTS_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    config.PROMPTS[name] = f.read().strip()
            except IOError as e:
                logger.error("Failed to load prompt from %s: %s", filepath, e)
    if 'default' not in config.PROMPTS:
        logger.error("A 'default.txt' prompt file is required but was not found in %s.", config.PROMPTS_DIR)
    logger.info("Loaded %d prompts: %s", len(config.PROMPTS), list(config.PROMPTS.keys()))

load_prompts()
redis_service.init_redis()

@app.route('/api/lark_callback', methods=['POST'])
def lark_callback():
    data = request.json
    header = data.get("header", {})
    event_id = header.get("event_id")
    log_context = {"event_id": event_id}

    if config.DEBUG_MODE:
        logger.debug("Received Lark callback request: %s", json.dumps(data, indent=2, ensure_ascii=False), extra=log_context)

    if "challenge" in data:
        return jsonify({"challenge": data["challenge"]})

    if header.get("token") != config.LARK_VERIFICATION_TOKEN:
        logger.warning("Invalid verification token received.", extra=log_context)
        return jsonify({"msg": "Invalid token"}), 401

    event = data.get("event", {})
    message = event.get("message", {})
    sender = event.get("sender", {})
    
    if sender.get("sender_type") == "app" or not message:
        return jsonify({"msg": "Ignoring message from bot or empty message"})

    msg_id = message.get("message_id")
    chat_id = message.get("chat_id")
    
    log_context.update({"chat_id": chat_id, "msg_id": msg_id})

    if not msg_id or redis_service.is_message_processed(msg_id):
        logger.info("Duplicate message ignored.", extra=log_context)
        return jsonify({"msg": "Duplicate message ignored"})
    redis_service.mark_message_as_processed(msg_id)

    # Ignore messages that are too old (e.g., older than 5 minutes)
    create_time_ms = message.get("create_time")
    if create_time_ms:
        create_time_s = int(create_time_ms) / 1000
        current_time_s = time.time()
        age_seconds = current_time_s - create_time_s
        if age_seconds > config.MAX_MESSAGE_AGE_SECONDS:
            logger.warning(f"Ignoring stale message (age: {age_seconds:.0f}s).", extra=log_context)
            return jsonify({"msg": "Stale message ignored"})

    text_content = json.loads(message.get("content", "{}")).get("text", "").strip()
    if text_content.startswith('/'):
        parts = text_content.split()
        logger.info("Handling command '%s' for chat.", parts[0], extra=log_context)
        command_handler.handle_command(parts[0], parts[1:], chat_id)
        return jsonify({"msg": "Command handled"})
    
    if not text_content:
        logger.info("Empty message content received.", extra=log_context)
        return jsonify({"msg": "Empty message content"})

    # --- Start of Synchronous Processing for Vercel ---
    start_time = time.time()
    logger.info("Starting synchronous processing for Vercel.", extra=log_context)

    # For group chats, respond only when mentioned. For P2P chats, respond to any message.
    chat_type = message.get("chat_type")
    if chat_type == "group":
        mentions = message.get("mentions", [])
        is_mentioned = any(mention.get("id") == config.LARK_APP_ID for mention in mentions)
        if not is_mentioned:
            logger.info("Bot not mentioned in group chat, ignoring message.", extra=log_context)
            return jsonify({"msg": "Bot not mentioned"})

    # Placeholder message logic is disabled for sync mode as it adds complexity.
    # The response will be sent once fully generated.

    try:
        settings = redis_service.get_chat_settings(chat_id)
        model = settings.get('model') or config.OPENAI_MODEL
        role = settings.get('role') or config.DEFAULT_ROLE
        system_prompt = config.PROMPTS.get(role, config.PROMPTS['default'])
        
        history = redis_service.get_chat_context(chat_id)
        messages = [{"role": "system", "content": system_prompt}, *history, {"role": "user", "content": text_content}]
        
        logger.info("Requesting AI response for chat.", extra=log_context)
        ai_response = openai_service.get_ai_response(messages, model)

        # Remove <think> blocks used for chain-of-thought reasoning.
        ai_response = re.sub(r'<think>.*?</think>', '', ai_response, flags=re.DOTALL)

        # Extract the final answer from the AI's full response, which may include a "chain of thought".
        # The final answer is assumed to start from the last H1 markdown header.
        last_header_pos = ai_response.rfind('\n# ')
        if last_header_pos != -1:
            ai_response = ai_response[last_header_pos:]

        ai_response = ai_response.strip()
        
        lark_service.send_message(chat_id, ai_response)

        history.append({"role": "user", "content": text_content})
        history.append({"role": "assistant", "content": ai_response})
        redis_service.save_chat_context(chat_id, history)
        logger.info("Successfully processed message and sent response.", extra=log_context)

        return jsonify({"msg": "Successfully processed"})

    except Exception as e:
        error_msg = f"🤯 Oops, an error occurred: `{type(e).__name__}`"
        logger.exception("An error occurred while processing the message:", extra=log_context)
        lark_service.send_message(chat_id, error_msg)
        return jsonify({"msg": "Error occurred"}), 500
    finally:
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"Finished synchronous processing in {duration:.2f} seconds.", extra=log_context)

@app.route('/', methods=['GET'])
def health_check():
    """A simple health check endpoint."""
    return jsonify({"status": "ok", "message": "Lark bot is running."}), 200
