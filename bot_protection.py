import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ChatMemberHandler, MessageHandler, filters
from settings_manager_mongo import get_chat_settings
from config import send_bot_response
from user_manager_mongo import is_user_admin

async def kick_if_bot(update: Update, context: ContextTypes.DEFAULT_TYPE, user, added_by_user=None):
    """Kicks the bot if added by a member (not admin) and Bot Protection is enabled."""
    if not user.is_bot or user.id == context.bot.id:
        return

    chat_id = update.effective_chat.id
    settings = get_chat_settings(chat_id)
    
    if not settings.get("bot_protection_enabled", False):
        return

    # Check if the user who added the bot is an admin
    # If added by admin, allow it. If added by member, kick the bot.
    if added_by_user:
        try:
            is_admin = await is_user_admin(chat_id, added_by_user.id, context)
            if is_admin:
                # Admin added the bot, allow it
                logging.info(f"Bot Protection: Bot {user.id} added by admin {added_by_user.id} in chat {chat_id}, allowing")
                return
        except Exception as e:
            logging.error(f"Bot Protection: Failed to check admin status in chat {chat_id}: {e}")

    try:
        # Check bot permissions
        bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        if not (bot_member.status == 'creator' or (bot_member.status == 'administrator' and bot_member.can_restrict_members)):
            await send_bot_response(
                update, context,
                "⚠️ <b>Bot Protection Alert:</b> A bot was added, but I don't have the 'Ban Users' permission to kick it. Please promote me to administrator with all rights.",
                parse_mode=ParseMode.HTML
            )
            return

        # Kick the added bot
        await context.bot.ban_chat_member(chat_id, user.id)
        await context.bot.unban_chat_member(chat_id, user.id)
        
        # Notify the group
        await send_bot_response(
            update, context,
            f"🚫 <b>Bot Protection:</b> Kicked added bot {user.first_name} (@{user.username}). Adding bots is restricted in this group.",
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
        # The user who performed the action (added the bot)
        added_by_user = update.chat_member.from_user
        await kick_if_bot(update, context, update.chat_member.new_chat_member.user, added_by_user)

async def on_new_members_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detects bot additions via MessageHandler (legacy/service messages)."""
    if not update.message or not update.message.new_chat_members:
        return
        
    for user in update.message.new_chat_members:
        # The message sender is the one who added the bot
        added_by_user = update.message.from_user
        await kick_if_bot(update, context, user, added_by_user)

def get_bot_protection_handlers():
    """Returns the handlers for bot protection."""
    return [
        ChatMemberHandler(on_chat_member_update, ChatMemberHandler.CHAT_MEMBER),
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_members_message)
    ]
