import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from settings_manager_mongo import get_chat_settings
from moderation_manager_mongo import get_user_warns, add_warn, reset_warns
from user_manager_mongo import is_user_admin
from moderation import ban_user, mute_user, kick_user
from telegram.error import BadRequest

async def edited_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle edited messages."""
    if not update.edited_message or not update.edited_message.from_user:
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    settings = get_chat_settings(chat_id)

    # Check if feature is enabled
    if not settings.get("edit_checks_enabled", False):
        return

    # Check target (members or everyone)
    target = settings.get("edit_checks_target", "members")
    is_admin = await is_user_admin(chat_id, user_id, context)
    
    if target == "members" and is_admin:
        return

    # Delete the edited message
    try:
        await update.edited_message.delete()
    except BadRequest as e:
        if "Message to delete not found" not in str(e):
            logging.error(f"Failed to delete edited message: {e}")
            return
    except Exception as e:
        logging.error(f"Error deleting edited message: {e}")
        return

    # Apply penalty
    penalty = settings.get("edit_checks_penalty", "off").lower()
    if penalty == "off":
        return

    user_name = update.effective_user.mention_html()
    
    if penalty == "warn":
        limit = settings.get("edit_checks_warn_limit", 3)
        # Note: add_warn and reset_warns are sync in moderation_manager_mongo
        current_warns = add_warn(chat_id, user_id)
        
        if current_warns >= limit:
            reset_warns(chat_id, user_id)
            await mute_user(update, context, user_id, reason="Reached warn limit for editing messages")
            await context.bot.send_message(
                chat_id, 
                f"🚫 {user_name} has been muted for reaching the warn limit (editing messages).",
                parse_mode='HTML'
            )
        else:
            await context.bot.send_message(
                chat_id,
                f"⚠️ {user_name}, edited messages are not allowed here! ({current_warns}/{limit})",
                parse_mode='HTML'
            )
            
    elif penalty == "mute":
        await mute_user(update, context, user_id, reason="Edited a message")
        await context.bot.send_message(chat_id, f"🔇 {user_name} has been muted for editing a message.", parse_mode='HTML')
        
    elif penalty == "kick":
        await kick_user(update, context, user_id, reason="Edited a message")
        await context.bot.send_message(chat_id, f"👢 {user_name} has been kicked for editing a message.", parse_mode='HTML')
        
    elif penalty == "ban":
        await ban_user(update, context, user_id, reason="Edited a message")
        await context.bot.send_message(chat_id, f"🔨 {user_name} has been banned for editing a message.", parse_mode='HTML')

def get_edit_handlers():
    """Return edit handlers."""
    return [
        MessageHandler(filters.UpdateType.EDITED_MESSAGE & filters.ChatType.GROUPS, edited_message_handler)
    ]
