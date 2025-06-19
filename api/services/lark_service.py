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
    
    card = {"config": {"wide_screen_mode": True}, "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": content}}]}
    url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    payload = {"receive_id": chat_id, "msg_type": "interactive", "content": json.dumps(card)}
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

def patch_message(message_id: str, content: str):
    access_token = get_lark_access_token()
    if not access_token: return
    
    card = {"config": {"wide_screen_mode": True}, "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": content}}]}
    url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}"
    payload = {"content": json.dumps(card)}
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.patch(url, headers=headers, json=payload, timeout=5)
        if response.json().get("code") != 0:
            logging.error(f"Failed to patch Lark message {message_id}: {response.text}")
    except Exception as e:
        logging.error(f"Exception patching Lark message {message_id}: {e}")
