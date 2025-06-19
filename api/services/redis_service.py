import redis
import json
import logging
from typing import Dict, Any, List, Optional
from api.config import REDIS_URL, CLEAR_REDIS_ON_STARTUP

r: Optional[redis.Redis] = None

def init_redis():
    global r
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        r.ping()
        info = r.connection_pool.connection_kwargs
        logging.info(f"Successfully connected to Redis at {info.get('host')}:{info.get('port')}.")
        if CLEAR_REDIS_ON_STARTUP:
            r.flushdb()
            logging.warning("Redis database has been flushed on startup.")
    except Exception as e:
        logging.error(f"Could not connect to Redis: {e}.")
        r = None

def get_chat_context(chat_id: str) -> List[Dict[str, Any]]:
    if not r: return []
    context = r.get(f"chat_context:{chat_id}")
    return json.loads(context) if context else []

def save_chat_context(chat_id: str, context: List[Dict[str, Any]]):
    if not r: return
    r.set(f"chat_context:{chat_id}", json.dumps(context), ex=7200)

def get_chat_settings(chat_id: str) -> Dict[str, str]:
    if not r: return {}
    return r.hgetall(f"settings:{chat_id}")

def set_chat_setting(chat_id: str, key: str, value: str):
    if not r: return
    r.hset(f"settings:{chat_id}", key, value)
    r.expire(f"settings:{chat_id}", 7 * 86400)

def is_message_processed(message_id: str) -> bool:
    if not r: return False
    return r.exists(f"msg_id:{message_id}")

def mark_message_as_processed(message_id: str):
    if not r: return
    r.setex(f"msg_id:{message_id}", 86400, "processed")

def get_lark_token_from_cache() -> Optional[str]:
    if not r: return None
    return r.get("lark_access_token")

def set_lark_token_to_cache(token: str, expire_in: int):
    if not r: return
    r.setex("lark_access_token", expire_in - 120, token)

def clear_user_data(chat_id: str):
    if not r: return
    r.delete(f"chat_context:{chat_id}")
    r.delete(f"settings:{chat_id}")

def clear_chat_context(chat_id: str):
    if not r: return
    r.delete(f"chat_context:{chat_id}")
