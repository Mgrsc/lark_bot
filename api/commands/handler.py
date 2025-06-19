from api import config
from api.config import PROMPTS
from api.services import lark_service, redis_service

def handle_command(command: str, args: list, chat_id: str):
    settings = redis_service.get_chat_settings(chat_id)

    if command == "/help":
        roles = ", ".join([f"`{r}`" for r in PROMPTS.keys()])
        current_role = settings.get('role', config.DEFAULT_ROLE)
        text = (f"**🤖 Available Commands**\n\n"
                f"- `/help`: Show this help message.\n"
                f"- `/clear`: Clear conversation history.\n"
                f"- `/model [model_name]`: Show or switch AI model. Current default: `{config.OPENAI_MODEL}`\n"
                f"- `/role [role_name]`: Show or switch bot's role. Current role: `{current_role}`\n"
                f"  Available roles: {roles}")
        lark_service.send_message(chat_id, text)
    elif command == "/clear":
        redis_service.clear_user_data(chat_id)
        lark_service.send_message(chat_id, "✨ Conversation history and settings have been cleared.")
    elif command == "/model":
        if not args:
            current_model = settings.get('model', config.OPENAI_MODEL)
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
    else:
        lark_service.send_message(chat_id, f"🤷‍♀️ Unknown command: **{command}**.")
