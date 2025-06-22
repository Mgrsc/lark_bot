import asyncio
import json
import traceback
from typing import Optional, List, Dict, Any
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import Tool

from api.config import MCP_STREAM_HTTP_URLS, MCP_CONNECT_TIMEOUT, DEBUG_MODE
import logging

logger = logging.getLogger(__name__)

class MCPHttpClient:
    def __init__(self, base_url: str, exit_stack: AsyncExitStack):
        self.base_url = base_url
        self.session: Optional[ClientSession] = None
        self.exit_stack = exit_stack
        self.tools: List[Tool] = []

    async def connect(self):
        try:
            async def _connect_and_init():
                transport = await self.exit_stack.enter_async_context(
                    streamablehttp_client(self.base_url)
                )
                http_read, http_write, _ = transport
                self.session = await self.exit_stack.enter_async_context(
                    ClientSession(http_read, http_write)
                )
                await self.session.initialize()
                response = await self.session.list_tools()
                self.tools = response.tools
                logger.info(f"Successfully connected to MCP server at {self.base_url}, found tools: {[tool.name for tool in self.tools]}")

            await asyncio.wait_for(_connect_and_init(), timeout=MCP_CONNECT_TIMEOUT)
        except asyncio.TimeoutError:
            logger.error(f"Connection to MCP server at {self.base_url} timed out after {MCP_CONNECT_TIMEOUT} seconds.")
        except Exception as e:
            logger.error(f"Failed to connect to MCP server at {self.base_url}: {e}", exc_info=True)

    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        if not self.session:
            raise ConnectionError("Session not initialized. Please connect first.")
        
        tool_exists = any(tool.name == tool_name for tool in self.tools)
        if not tool_exists:
            raise ValueError(f"Tool '{tool_name}' not found on server {self.base_url}")

        if DEBUG_MODE:
            print(f"Calling tool '{tool_name}' on {self.base_url} with args: {args}")
        
        result = await self.session.call_tool(tool_name, args)
        
        if DEBUG_MODE:
            print(f"Tool '{tool_name}' result: {result}")
            
        return result.content

class MCPManager:
    def __init__(self):
        self.clients: List[MCPHttpClient] = []
        self.exit_stack = AsyncExitStack()
        self.tool_map: Dict[str, MCPHttpClient] = {}

    async def startup(self):
        urls = MCP_STREAM_HTTP_URLS
        if not urls:
            if DEBUG_MODE:
                print("No MCP_STREAM_HTTP_URLS configured, MCP Manager will not connect to any servers.")
            return

        self.clients = [MCPHttpClient(url, self.exit_stack) for url in urls]
        
        connection_tasks = [client.connect() for client in self.clients]
        await asyncio.gather(*connection_tasks)

        for client in self.clients:
            for tool in client.tools:
                if tool.name in self.tool_map:
                    print(f"Warning: Duplicate tool name '{tool.name}' found. The one from {client.base_url} will be used.")
                self.tool_map[tool.name] = client

    async def shutdown(self):
        await self.exit_stack.aclose()

    def get_all_tools(self) -> List[Dict[str, Any]]:
        all_tools = []
        for client in self.clients:
            for tool in client.tools:
                all_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema,
                    },
                })
        return all_tools

    async def call_tool(self, tool_name: str, tool_args: str) -> str:
        if tool_name not in self.tool_map:
            return f"Error: Tool '{tool_name}' not found."
        
        client = self.tool_map[tool_name]
        try:
            args = json.loads(tool_args)
            result = await client.call_tool(tool_name, args)
            
            if isinstance(result, list):
                # Handle cases where the result is a list of content blocks
                result_text = "\n".join([str(item.text) for item in result if hasattr(item, 'text')])
                return result_text
            elif not isinstance(result, str):
                return json.dumps(result, indent=2)
            return result
        except json.JSONDecodeError:
            err_msg = f"Error: Invalid JSON arguments for tool '{tool_name}'."
            logger.warning(err_msg)
            return err_msg
        except Exception as e:
            logger.error(f"An unexpected error occurred while calling tool '{tool_name}': {e}", exc_info=True)
            return f"Error: An unexpected error occurred while calling tool '{tool_name}'."

mcp_manager = MCPManager()