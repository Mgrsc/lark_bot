import httpx
import logging
import json
from typing import List, Dict, Any, Optional, AsyncIterator

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        timeout: int = 180,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        if not api_key:
            raise ValueError("LLM_API_KEY is required")
        if not base_url:
            raise ValueError("LLM_BASE_URL is required")
        
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
    
    async def close(self):
        await self.client.aclose()
    
    async def create_chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a chat completion using the LLM API.
        Compatible with OpenAI Chat Completions API format.
        """
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        
        # Only add optional parameters if they are explicitly set
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        if self.top_p is not None:
            payload["top_p"] = self.top_p
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens
        
        if tools:
            payload["tools"] = tools
            if tool_choice:
                payload["tool_choice"] = tool_choice
        
        url = f"{self.base_url}/chat/completions"
        
        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during LLM request: {e}")
            raise
