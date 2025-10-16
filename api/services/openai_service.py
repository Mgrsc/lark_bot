import logging
import json
from typing import List, Dict, Any
from api import config
from api.services.llm_client import LLMClient
from api.services.mcp_service import mcp_manager

logger = logging.getLogger(__name__)

# Lazy-initialize the LLM client
_llm_client = None

def get_llm_client() -> LLMClient:
    """Get or create the LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient(
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL,
            timeout=config.LLM_API_TIMEOUT,
            temperature=config.LLM_TEMPERATURE,
            top_p=config.LLM_TOP_P,
            max_tokens=config.LLM_MAX_TOKENS,
        )
    return _llm_client

async def get_ai_response(messages: List[Dict[str, Any]], model: str) -> str:
    llm_client = get_llm_client()
    
    # Ensure MCP tool list is fresh (smart refresh every 5 minutes)
    await mcp_manager.ensure_tools_fresh()
    
    tools = mcp_manager.get_all_tools()
    
    current_messages = list(messages)

    while True:
        tool_choice = "auto" if tools else None
        
        if config.DEBUG_MODE:
            logger.debug("Sending request to LLM: model=%s, tools=%d", model, len(tools) if tools else 0)

        response = await llm_client.create_chat_completion(
            messages=current_messages,
            model=model,
            tools=tools if tools else None,
            tool_choice=tool_choice,
        )

        if config.DEBUG_MODE:
            logger.debug("Received response from LLM: %s", json.dumps(response, indent=2, ensure_ascii=False))

        message = response["choices"][0]["message"]
        tool_calls = message.get("tool_calls")

        if not tool_calls:
            return message.get("content") or "No content returned."

        current_messages.append(message)

        for tool_call in tool_calls:
            function_name = tool_call["function"]["name"]
            function_args = tool_call["function"]["arguments"]
            
            if config.DEBUG_MODE:
                logger.debug(f"AI requested to call tool '{function_name}' with args: {function_args}")

            tool_result = await mcp_manager.call_tool(
                tool_name=function_name,
                tool_args=function_args
            )
            
            current_messages.append({
                "tool_call_id": tool_call["id"],
                "role": "tool",
                "name": function_name,
                "content": tool_result,
            })
