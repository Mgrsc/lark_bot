import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


LARK_APP_ID = os.getenv("LARK_APP_ID")
LARK_APP_SECRET = os.getenv("LARK_APP_SECRET")
LARK_VERIFICATION_TOKEN = os.getenv("LARK_VERIFICATION_TOKEN")
LARK_BOT_OPEN_ID: Optional[str] = None

LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4-turbo")
LLM_API_TIMEOUT = int(os.getenv("LLM_API_TIMEOUT", "180"))

# Optional parameters - only set if explicitly configured
_temp = os.getenv("LLM_TEMPERATURE")
LLM_TEMPERATURE = float(_temp) if _temp is not None else None

_top_p = os.getenv("LLM_TOP_P")
LLM_TOP_P = float(_top_p) if _top_p is not None else None

_max_tokens = os.getenv("LLM_MAX_TOKENS")
LLM_MAX_TOKENS = int(_max_tokens) if _max_tokens is not None else None

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

ENABLE_SEND_AND_REPLACE = os.getenv("ENABLE_SEND_AND_REPLACE", "true").lower() == 'true'
CLEAR_REDIS_ON_STARTUP = os.getenv("CLEAR_REDIS_ON_STARTUP", "false").strip().lower() == "true"

DEFAULT_ROLE = os.getenv("DEFAULT_ROLE", "default")

PLACEHOLDER_MESSAGE = os.getenv("PLACEHOLDER_MESSAGE", "Thinking, please wait...")

CHAT_CONTEXT_MAX_MESSAGES = int(os.getenv("CHAT_CONTEXT_MAX_MESSAGES", 20))
MAX_MESSAGE_AGE_SECONDS = int(os.getenv("MAX_MESSAGE_AGE_SECONDS", 300))

PROMPTS_DIR = os.path.join(PROJECT_ROOT, 'prompts')
PROMPTS: dict = {}

DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == 'true'

MCP_CONNECT_TIMEOUT = int(os.getenv("MCP_CONNECT_TIMEOUT", "10"))
MCP_TOOLS_REFRESH_INTERVAL = int(os.getenv("MCP_TOOLS_REFRESH_INTERVAL", "300"))  # 5 minutes

def _parse_mcp_servers():
    servers = []
    i = 1
    while True:
        url = os.getenv(f"MCP_SERVER_{i}_URL")
        if not url:
            break
        token = os.getenv(f"MCP_SERVER_{i}_TOKEN")
        servers.append({"url": url, "token": token})
        i += 1
    return servers

MCP_SERVERS = _parse_mcp_servers()