from telegram import InlineKeyboardButton
from settings_manager_mongo import get_chat_settings

# Theme definitions with prefixes and suffixes
THEMES = {
    "default": {"prefix": "", "suffix": "", "name": "Default"},
    "blue": {"prefix": "� ", "suffix": "", "name": "Blue"},
    "green": {"prefix": "🟢 ", "suffix": "", "name": "Green"},
    "red": {"prefix": "� ", "suffix": "", "name": "Red"},
    "gold": {"prefix": "🟡 ", "suffix": "", "name": "Gold"},
    "pink": {"prefix": "🌸 ", "suffix": "", "name": "Pink"},
    "purple": {"prefix": "� ", "suffix": "", "name": "Purple"},
    "aqua": {"prefix": "🌊 ", "suffix": "", "name": "Aqua"},
    "fire": {"prefix": "🔥 ", "suffix": "", "name": "Fire"},
    "rainbow": {"prefix": "🌈 ", "suffix": "", "name": "Multi-Color"},
}

# Color sequence for rainbow/multi-color theme
RAINBOW_SEQUENCE = ["blue", "green", "red", "gold", "purple", "aqua", "pink"]

def get_styled_text(text, chat_id=None, theme_name=None, row_index=None):
    """Decorate text with emojis based on theme."""
    if not theme_name and chat_id:
        from settings_manager_mongo import get_chat_settings
        settings = get_chat_settings(chat_id)
        theme_name = settings.get("ui_button_style", "default")
    
    if theme_name == "rainbow" and row_index is not None:
        # Pick a color from the sequence based on row index
        color_key = RAINBOW_SEQUENCE[row_index % len(RAINBOW_SEQUENCE)]
        theme = THEMES.get(color_key, THEMES["default"])
    else:
        theme = THEMES.get(theme_name, THEMES["default"])
        
    return f"{theme['prefix']}{text}{theme['suffix']}"

def styled_button(text, callback_data=None, url=None, chat_id=None, theme_name=None, row_index=None):
    """Create an InlineKeyboardButton with styled text."""
    styled_text = get_styled_text(text, chat_id=chat_id, theme_name=theme_name, row_index=row_index)
    from telegram import InlineKeyboardButton
    if url:
        return InlineKeyboardButton(styled_text, url=url)
    return InlineKeyboardButton(styled_text, callback_data=callback_data)
