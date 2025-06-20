import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


LARK_APP_ID = os.getenv("LARK_APP_ID")
LARK_APP_SECRET = os.getenv("LARK_APP_SECRET")
LARK_VERIFICATION_TOKEN = os.getenv("LARK_VERIFICATION_TOKEN")
LARK_BOT_OPEN_ID: Optional[str] = None

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
OPENAI_API_TIMEOUT = int(os.getenv("OPENAI_API_TIMEOUT", 60))
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", 0.7))
OPENAI_TOP_P = float(os.getenv("OPENAI_TOP_P", 1.0))
OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", 4096))

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