import logging
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, MessageHandler, filters
from config import OWNER_ID
from settings_manager import get_chat_settings
from welcome import format_welcome_message # Reuse the same formatter

async def on_member_leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send goodbye message when a member leaves the group."""
    if not update.message or not update.message.left_chat_member:
        return
        
    chat_id = update.effective_chat.id
    settings = get_chat_settings(chat_id)
    
    if not settings.get("goodbye_enabled", True):
        return

    goodbye_text_raw = settings.get('goodbye_text', "Goodbye {NAME}, we will miss you!")
    goodbye_media = settings.get('goodbye_media')
    media_enabled = settings.get('goodbye_media_enabled', True)
    button_enabled = settings.get('goodbye_button_enabled', True)
    button_text = settings.get('goodbye_button_text')
    button_url = settings.get('goodbye_button_url')

    reply_markup = None
    if button_enabled and button_text and button_url:
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(button_text, url=button_url)]])

    member = update.message.left_chat_member
    if member.is_bot: return
    
    # Format the goodbye message with advanced placeholders (reuse same logic)
    personal_goodbye = format_welcome_message(goodbye_text_raw, member, update.effective_chat)
    
    if media_enabled and goodbye_media:
        try:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=goodbye_media,
                caption=personal_goodbye,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logging.error(f"Error sending goodbye photo: {e}")
            await context.bot.send_message(
                chat_id=chat_id, 
                text=personal_goodbye, 
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
    else:
        await context.bot.send_message(
            chat_id=chat_id, 
            text=personal_goodbye, 
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

def get_goodbye_handlers():
    """Return handlers for goodbye message."""
    return [
        MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, on_member_leave)
    ]
