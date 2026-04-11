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
    Returns: 'en', 'hi', 'hinglish', 'other', or 'safe' (emojis/numbers only)
    """
    if not text:
        return 'unknown'
    
    # Count characters in different categories
    hindi_chars = 0
    latin_chars = 0
    other_chars = 0
    numbers = 0
    emojis = 0
    punctuation = 0
    spaces = 0
    total_alphabetic = 0
    
    for char in text:
        if '\u0900' <= char <= '\u097F':  # Devanagari (Hindi)
            hindi_chars += 1
            total_alphabetic += 1
        elif char.isascii() and char.isalpha():  # Latin alphabet (English)
            latin_chars += 1
            total_alphabetic += 1
        elif char.isalpha():  # Other alphabets (Russian, Arabic, Chinese, etc.)
            other_chars += 1
            total_alphabetic += 1
        elif char.isdigit():  # Numbers
            numbers += 1
        elif char.isspace():  # Spaces
            spaces += 1
        elif is_emoji(char):  # Emojis
            emojis += 1
        else:  # Punctuation, special characters
            punctuation += 1
    
    # If no alphabetic characters, it's safe (emojis, numbers, punctuation only)
    if total_alphabetic == 0:
        return 'safe'
    
    # Calculate percentages based on alphabetic characters only
    hindi_pct = (hindi_chars / total_alphabetic) * 100
    latin_pct = (latin_chars / total_alphabetic) * 100
    other_pct = (other_chars / total_alphabetic) * 100
    
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

def is_emoji(char: str) -> bool:
    """Check if character is an emoji."""
    code_point = ord(char)
    # Common emoji ranges
    return (
        0x1F600 <= code_point <= 0x1F64F or  # Emoticons
        0x1F300 <= code_point <= 0x1F5FF or  # Misc Symbols and Pictographs
        0x1F680 <= code_point <= 0x1F6FF or  # Transport and Map
        0x1F1E0 <= code_point <= 0x1F1FF or  # Regional Indicators (flags)
        0x2600 <= code_point <= 0x26FF or    # Misc symbols
        0x2700 <= code_point <= 0x27BF or    # Dingbats
        0xFE00 <= code_point <= 0xFE0F or    # Variation Selectors
        0x1F900 <= code_point <= 0x1F9FF or  # Supplemental Symbols
        0x1FA00 <= code_point <= 0x1FA6F or  # Chess Symbols
        0x1FA70 <= code_point <= 0x1FAFF     # Symbols and Pictographs Extended
    )

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
    
    # Safe messages (emojis, numbers, punctuation only) are always allowed
    if detected_lang == 'safe':
        return False  # Don't delete
    
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
