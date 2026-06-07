from telegram import InlineKeyboardButton
from settings_manager_mongo import get_chat_settings

# Theme definitions with prefixes and suffixes
THEMES = {
    "default": {"prefix": "", "suffix": "", "name": "Default"},
    "blue": {"prefix": "🔹 ", "suffix": " 🔹", "name": "Blue"},
    "green": {"prefix": "❇️ ", "suffix": " ❇️", "name": "Green"},
    "red": {"prefix": "🔻 ", "suffix": " 🔻", "name": "Red"},
    "gold": {"prefix": "⭐ ", "suffix": " ⭐", "name": "Gold"},
    "pink": {"prefix": "🌸 ", "suffix": " 🌸", "name": "Pink"},
    "purple": {"prefix": "🔮 ", "suffix": " 🔮", "name": "Purple"},
    "aqua": {"prefix": "🌊 ", "suffix": " 🌊", "name": "Aqua"},
    "fire": {"prefix": "🔥 ", "suffix": " 🔥", "name": "Fire"},
}

def get_styled_text(text, chat_id=None, theme_name=None):
    """Decorate text with emojis based on theme."""
    if not theme_name and chat_id:
        settings = get_chat_settings(chat_id)
        theme_name = settings.get("ui_button_style", "default")
    
    theme = THEMES.get(theme_name, THEMES["default"])
    return f"{theme['prefix']}{text}{theme['suffix']}"

def styled_button(text, callback_data=None, url=None, chat_id=None, theme_name=None):
    """Create an InlineKeyboardButton with styled text."""
    styled_text = get_styled_text(text, chat_id=chat_id, theme_name=theme_name)
    if url:
        return InlineKeyboardButton(styled_text, url=url)
    return InlineKeyboardButton(styled_text, callback_data=callback_data)
