import logging
import re
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from settings_manager_mongo import get_chat_settings
from user_manager_mongo import is_user_admin
from config import OWNER_ID

# Regular expression to detect URLs
URL_PATTERN = re.compile(
    r'(https?://[^\s]+|'  # http:// or https://
    r'www\.[^\s]+|'  # www.
    r't\.me/[^\s]+|'  # t.me links
    r'telegram\.me/[^\s]+)',  # telegram.me links
    re.IGNORECASE
)

def contains_link(text):
    """Check if text contains a URL."""
    if not text:
        return False
    return bool(URL_PATTERN.search(text))

async def check_link_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """MessageHandler to check for links in messages and delete them if link spam protection is enabled."""
    if not update.message or not update.effective_chat:
        return
        
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Skip private chats
    if update.effective_chat.type == "private":
        return
    
    # Skip admins and owner - protection only works on members
    if user_id == OWNER_ID or await is_user_admin(chat_id, user_id, context):
        return
    
    # Get settings
    settings = get_chat_settings(chat_id)
    
    # Check if link spam protection is enabled
    if not settings.get("link_spam_protection_enabled", False):
        return
    
    # Check if message contains a link
    message_text = update.message.text or update.message.caption or ""
    
    if contains_link(message_text):
        try:
            # Delete the message with link
            await update.message.delete()
            logging.info(f"Link Spam Protection: Deleted message from user {user_id} in chat {chat_id}")
            
            # Notify the user
            from config import send_bot_response
            await send_bot_response(
                update, context,
                f"⚠️ User <code>{update.effective_user.id}</code>, links are not allowed in this group.",
                parse_mode='HTML'
            )
        except Exception as e:
            logging.error(f"Link Spam Protection: Failed to delete message from user {user_id} in chat {chat_id}: {e}")

def get_link_spam_handlers():
    """Returns the handlers for link spam protection."""
    return [
        MessageHandler(
            filters.ALL & ~filters.COMMAND & filters.ChatType.GROUPS,
            check_link_spam
        )
    ]
