import asyncio
from api import config
from api.config import PROMPTS
from api.services import lark_service, redis_service
from api.services.mcp_service import mcp_manager

def handle_command(command: str, args: list, chat_id: str):
    settings = redis_service.get_chat_settings(chat_id)

    if command == "/help":
        roles = ", ".join([f"`{r}`" for r in PROMPTS.keys()])
        current_role = settings.get('role', config.DEFAULT_ROLE)
        text = (f"**🤖 Available Commands**\n\n"
                f"- `/help`: Show this help message.\n"
                f"- `/clear`: Clear conversation history.\n"
                f"- `/model [model_name]`: Show or switch AI model. Current default: `{config.LLM_MODEL}`\n"
                f"- `/role [role_name]`: Show or switch bot's role. Current role: `{current_role}`\n"
                f"  Available roles: {roles}\n"
                f"- `/refresh`: Refresh MCP tool list from all servers.")
        lark_service.send_message(chat_id, text)
    elif command == "/clear":
        redis_service.clear_user_data(chat_id)
        lark_service.send_message(chat_id, "✨ Conversation history and settings have been cleared.")
    elif command == "/model":
        if not args:
            current_model = settings.get('model', config.LLM_MODEL)
            lark_service.send_message(chat_id, f"ℹ️ Current model: **{current_model}**")
            return
        model = args[0].strip()
        redis_service.set_chat_setting(chat_id, 'model', model)
        lark_service.send_message(chat_id, f"✅ Model switched to: **{model}**")
    elif command == "/role":
        if not args:
            current_role = settings.get('role', config.DEFAULT_ROLE)
            lark_service.send_message(chat_id, f"ℹ️ Current role: **{current_role}**")
            return
        role = args[0].strip()
        if role not in PROMPTS:
            lark_service.send_message(chat_id, f"❌ Role not found: **{role}**.")
            return
        redis_service.set_chat_setting(chat_id, 'role', role)
        redis_service.clear_chat_context(chat_id)
        lark_service.send_message(chat_id, f"🎭 Role switched to: **{role}**. Conversation history has been cleared.")
    elif command == "/refresh":
        lark_service.send_message(chat_id, "🔄 Refreshing MCP tool list...")
        try:
            # Run async refresh in sync context
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in Flask request context, need to run in the event loop thread
                from api.app import run_async_from_sync
                run_async_from_sync(mcp_manager.refresh_all_tools())
            else:
                asyncio.run(mcp_manager.refresh_all_tools())
            
            tool_count = len(mcp_manager.tool_map)
            tools_list = ", ".join([f"`{name}`" for name in list(mcp_manager.tool_map.keys())[:10]])
            if tool_count > 10:
                tools_list += f", ... and {tool_count - 10} more"
            
            lark_service.send_message(
                chat_id, 
                f"✅ MCP tool list refreshed successfully!\n\n"
                f"**Total tools**: {tool_count}\n"
                f"**Tools**: {tools_list if tool_count > 0 else 'None'}"
            )
        except Exception as e:
            lark_service.send_message(chat_id, f"❌ Failed to refresh tools: {str(e)}")
    else:
        lark_service.send_message(chat_id, f"🤷‍♀️ Unknown command: **{command}**.")
