import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ChatMemberHandler, MessageHandler, filters
from settings_manager import get_chat_settings
from config import send_bot_response

async def kick_if_bot(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    """Kicks the user if they are a bot and Bot Protection is enabled."""
    if not user.is_bot or user.id == context.bot.id:
        return

    chat_id = update.effective_chat.id
    settings = get_chat_settings(chat_id)
    
    if not settings.get("bot_protection_enabled", False):
        return

    try:
        # Check bot permissions
        bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        if not (bot_member.status == 'creator' or (bot_member.status == 'administrator' and bot_member.can_restrict_members)):
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ <b>Bot Protection Alert:</b> A bot was added, but I don't have the 'Ban Users' permission to kick it. Please promote me to administrator with all rights."
            )
            return

        # Kick the added bot
        await context.bot.ban_chat_member(chat_id, user.id)
        await context.bot.unban_chat_member(chat_id, user.id)
        
        # Notify the group
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🚫 <b>Bot Protection:</b> Kicked added bot {user.first_name} (@{user.username}). Adding bots is restricted in this group.",
            parse_mode=ParseMode.HTML
        )
        logging.info(f"Bot Protection: Kicked bot {user.id} in chat {chat_id}")
    except Exception as e:
        logging.error(f"Bot Protection: Failed to kick bot {user.id} in chat {chat_id}: {e}")

async def on_chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detects bot additions via ChatMemberHandler."""
    if not update.chat_member or not update.chat_member.new_chat_member:
        return
        
    # Only act if someone is newly joined/added
    status = update.chat_member.new_chat_member.status
    if status in ['member', 'administrator']:
        await kick_if_bot(update, context, update.chat_member.new_chat_member.user)

async def on_new_members_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detects bot additions via MessageHandler (legacy/service messages)."""
    if not update.message or not update.message.new_chat_members:
        return
        
    for user in update.message.new_chat_members:
        await kick_if_bot(update, context, user)

def get_bot_protection_handlers():
    """Returns the handlers for bot protection."""
    return [
        ChatMemberHandler(on_chat_member_update, ChatMemberHandler.CHAT_MEMBER),
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_members_message)
    ]
