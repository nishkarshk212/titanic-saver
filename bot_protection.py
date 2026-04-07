import logging
from telegram import Update
from telegram.ext import ContextTypes, ChatMemberHandler
from settings_manager import get_chat_settings
from config import send_bot_response

async def on_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.chat_member or not update.chat_member.new_chat_member:
        return

    chat_id = update.effective_chat.id
    new_member = update.chat_member.new_chat_member.user
    
    if new_member.is_bot and new_member.id != context.bot.id:
        settings = get_chat_settings(chat_id)
        
        if settings.get("bot_protection_enabled", False):
            try:
                bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
                if not (bot_member.status == 'creator' or (bot_member.status == 'administrator' and bot_member.can_restrict_members)):
                    await send_bot_response(update, context, "❌ Bot Protection is enabled but I don't have permission to remove added bots.")
                    return
            except Exception:
                pass
            try:
                await context.bot.ban_chat_member(chat_id, new_member.id)
                await context.bot.unban_chat_member(chat_id, new_member.id)
                
                await send_bot_response(update, context, f"🚫 <b>Bot Protection:</b> Kicked added bot {new_member.first_name} (@{new_member.username}). Adding bots is restricted in this group.")
                logging.info(f"Bot Protection: Kicked bot {new_member.id} in chat {chat_id}")
            except Exception as e:
                logging.error(f"Bot Protection: Failed to kick bot {new_member.id} in chat {chat_id}: {e}")

def get_bot_protection_handlers():
    """Returns the handler for bot protection."""
    return [
        ChatMemberHandler(on_new_member, ChatMemberHandler.CHAT_MEMBER)
    ]
