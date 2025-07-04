import requests
import json
import logging
from typing import Optional
from api.config import LARK_APP_ID, LARK_APP_SECRET
from api.services.redis_service import get_lark_token_from_cache, set_lark_token_to_cache

def get_lark_access_token() -> Optional[str]:
    token = get_lark_token_from_cache()
    if token: return token
    
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": LARK_APP_ID, "app_secret": LARK_APP_SECRET}
    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == 0:
            token, expire = data["tenant_access_token"], data["expire"]
            set_lark_token_to_cache(token, expire)
            return token
    except Exception as e:
        logging.error(f"Error getting Lark token: {e}")
    return None

def send_message(chat_id: str, content: str) -> Optional[str]:
    access_token = get_lark_access_token()
    if not access_token: return None
    
    url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    # Correctly format the content for an interactive message card
    # The 'content' field must be a JSON string for interactive messages.
    # We construct the dictionary first, then dump it to a string.
    card_content = {
        "config": {"wide_screen_mode": True},
        "elements": [{"tag": "markdown", "content": content}]
    }
    payload = {
        "receive_id": chat_id,
        "msg_type": "interactive",
        "content": json.dumps(card_content)
    }
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        data = response.json()
        if data.get("code") == 0:
            return data.get("data", {}).get("message_id")
        logging.error(f"Failed to send Lark message: {data}")
    except Exception as e:
        logging.error(f"Exception sending Lark message: {e}")
    return None

def patch_message(message_id: str, content: str) -> bool:
    access_token = get_lark_access_token()
    if not access_token: return False
    
    url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}"
    card_content = {
        "config": {"wide_screen_mode": True},
        "elements": [{"tag": "markdown", "content": content}]
    }
    payload = {
        "content": json.dumps(card_content)
    }
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.patch(url, headers=headers, json=payload, timeout=5)
        data = response.json()
        if data.get("code") == 0:
            logging.info(f"Successfully patched message {message_id}.")
            return True
        logging.error(f"Failed to patch Lark message {message_id}: {response.text}")
    except Exception as e:
        logging.error(f"Exception patching Lark message {message_id}: {e}")
    return False

def get_bot_open_id() -> Optional[str]:
    """Fetches the bot's own open_id from the Lark API."""
    access_token = get_lark_access_token()
    if not access_token:
        logging.error("Cannot get bot open_id without an access token.")
        return None
    
    url = "https://open.feishu.cn/open-apis/bot/v3/info"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == 0:
            open_id = data.get("bot", {}).get("open_id")
            if open_id:
                logging.info(f"Successfully parsed bot open_id: {open_id}")
                return open_id
            logging.error(f"Could not find open_id in bot info response: {data}")
        else:
            logging.error(f"Failed to get bot info from Lark: {data}")
    except Exception as e:
        logging.error(f"Exception while getting bot info: {e}")
    return None

def resolve_mentions(text_content: str, mentions: list) -> str:
    """Replaces mention placeholders in text with actual user names."""
    if not mentions:
        return text_content
    
    for mention in mentions:
        try:
            user_name = mention.get("name", "")
            mention_key = mention.get("key", "")
            if user_name and mention_key:
                # The key in the 'mentions' array corresponds to the placeholder in the text.
                # e.g., key: "@_user_1" -> text: "... @_user_1 ..."
                text_content = text_content.replace(mention_key, f"@{user_name}")
        except Exception as e:
            logging.error(f"Error processing a mention: {mention}. Error: {e}")
            
    return text_content
