import openai
import logging
import json
import asyncio
from typing import List, Dict, Any
from api import config
from api.services.mcp_service import mcp_manager

client = openai.AsyncOpenAI(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL)
logger = logging.getLogger(__name__)

async def get_ai_response(messages: List[Dict[str, Any]], model: str) -> str:
    tools = mcp_manager.get_all_tools()
    
    current_messages = list(messages)

    while True:
        params = {
            "model": model,
            "messages": current_messages,
            "temperature": config.OPENAI_TEMPERATURE,
            "top_p": config.OPENAI_TOP_P,
            "timeout": config.OPENAI_API_TIMEOUT,
        }
        if config.OPENAI_MAX_TOKENS:
            params["max_tokens"] = config.OPENAI_MAX_TOKENS
        
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        if config.DEBUG_MODE:
            logger.debug("Sending request to OpenAI: %s", json.dumps(params, indent=2, ensure_ascii=False))

        completion = await client.chat.completions.create(**params)

        if config.DEBUG_MODE:
            logger.debug("Received response from OpenAI: %s", completion.model_dump_json(indent=2))

        response_message = completion.choices[0].message
        tool_calls = response_message.tool_calls

        if not tool_calls:
            return response_message.content or "No content returned."

        current_messages.append(response_message.model_dump())

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = tool_call.function.arguments
            
            if config.DEBUG_MODE:
                logger.debug(f"AI requested to call tool '{function_name}' with args: {function_args}")

            tool_result = await mcp_manager.call_tool(
                tool_name=function_name,
                tool_args=function_args
            )
            
            current_messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": tool_result,
            })
