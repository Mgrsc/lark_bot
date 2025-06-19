import openai
import logging
import json
from typing import List, Dict, Any
from api import config

client = openai.OpenAI(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL)
logger = logging.getLogger(__name__)

def get_ai_response(messages: List[Dict[str, Any]], model: str) -> str:
    params = {
        "model": model,
        "messages": messages,
        "temperature": config.OPENAI_TEMPERATURE,
        "top_p": config.OPENAI_TOP_P,
        "timeout": config.OPENAI_API_TIMEOUT
    }
    if config.OPENAI_MAX_TOKENS:
        params["max_tokens"] = config.OPENAI_MAX_TOKENS
    
    if config.DEBUG_MODE:
        logger.debug("Sending request to OpenAI: %s", json.dumps(params, indent=2, ensure_ascii=False))

    completion = client.chat.completions.create(**params)

    if config.DEBUG_MODE:
        logger.debug("Received response from OpenAI: %s", completion.model_dump_json(indent=2))

    return completion.choices[0].message.content
