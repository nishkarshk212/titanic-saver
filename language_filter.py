"""
Language Detection & Filtering Module
Detects message language and filters based on group settings
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

# Supported languages
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'hi': 'Hindi',
    'hinglish': 'Hinglish'  # Hindi + English mix
}

# Language detection based on Unicode ranges
def detect_language(text: str) -> str:
    """
    Detect the language of the text.
    Returns: 'en', 'hi', 'hinglish', or 'other'
    """
    if not text:
        return 'unknown'
    
    # Count characters in different scripts
    hindi_chars = 0
    latin_chars = 0
    other_chars = 0
    total_chars = 0
    
    for char in text:
        if '\u0900' <= char <= '\u097F':  # Devanagari (Hindi)
            hindi_chars += 1
            total_chars += 1
        elif char.isascii() and char.isalpha():  # Latin alphabet (English)
            latin_chars += 1
            total_chars += 1
        elif char.isalpha():  # Other alphabets (Russian, Arabic, Chinese, etc.)
            other_chars += 1
            total_chars += 1
        # Skip spaces, punctuation, numbers, emojis
    
    if total_chars == 0:
        return 'unknown'
    
    # Calculate percentages
    hindi_pct = (hindi_chars / total_chars) * 100
    latin_pct = (latin_chars / total_chars) * 100
    other_pct = (other_chars / total_chars) * 100
    
    # Detection logic
    if other_pct > 50:
        return 'other'  # Mostly non-Hindi, non-English characters
    elif hindi_pct > 70:
        return 'hi'  # Pure Hindi
    elif latin_pct > 70:
        return 'en'  # Pure English
    elif hindi_pct > 20 and latin_pct > 20:
        return 'hinglish'  # Mix of Hindi and English
    elif hindi_pct > 50:
        return 'hi'  # Mostly Hindi
    elif latin_pct > 50:
        return 'en'  # Mostly English
    else:
        return 'other'  # Mixed or other languages

async def check_language_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Check if message language is allowed in the group.
    Returns True if message should be deleted, False if allowed.
    """
    from settings_manager_mongo import get_chat_settings
    from database import is_connected
    
    if not is_connected():
        return False
    
    chat_id = update.effective_chat.id
    message = update.message
    
    # Get group settings
    settings = get_chat_settings(chat_id)
    
    # Check if language filter is enabled
    if not settings.get('language_filter_enabled', False):
        return False
    
    # Get allowed languages (default: en, hi, hinglish)
    allowed_languages = settings.get('allowed_languages', ['en', 'hi', 'hinglish'])
    
    # Get message text
    text = message.text or message.caption
    if not text:
        return False  # Don't filter non-text messages
    
    # Detect language
    detected_lang = detect_language(text)
    
    # If detected language is not allowed, delete message
    if detected_lang not in allowed_languages:
        try:
            # Delete the message
            await message.delete()
            
            # Send warning message
            warning_msg = (
                f"⚠️ <b>Language Filter Active</b>\n\n"
                f"Your message was deleted because it was not in an allowed language.\n\n"
                f"<b>Detected:</b> {detected_lang.upper()}\n"
                f"<b>Allowed:</b> {', '.join([SUPPORTED_LANGUAGES.get(lang, lang) for lang in allowed_languages])}\n\n"
                f"Please use one of the allowed languages."
            )
            
            # Send warning and auto-delete after 10 seconds
            warning = await message.reply_text(warning_msg, parse_mode='HTML')
            
            # Schedule deletion of warning message
            import asyncio
            asyncio.create_task(delete_after_delay(context, warning.chat_id, warning.message_id, 10))
            
            return True  # Message was deleted
            
        except Exception as e:
            logging.error(f"Error deleting message: {e}")
            return False
    
    return False  # Message is allowed

async def delete_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int):
    """Delete a message after specified delay in seconds."""
    import asyncio
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logging.error(f"Error deleting warning message: {e}")

async def language_filter_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle message language filtering."""
    # Only check in groups
    if update.effective_chat.type not in ['group', 'supergroup']:
        return
    
    # Check language filter
    deleted = await check_language_filter(update, context)
    
    if deleted:
        logging.info(f"Message deleted due to language filter in chat {update.effective_chat.id}")

def get_language_name(code: str) -> str:
    """Get language name from code."""
    return SUPPORTED_LANGUAGES.get(code, code)

def get_language_handlers():
    """Return language filter handlers."""
    from telegram.ext import MessageHandler, filters
    return [
        MessageHandler(filters.TEXT | filters.CAPTION, language_filter_handler)
    ]
