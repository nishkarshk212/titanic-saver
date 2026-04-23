"""
Manager Info Command - User information
Ported from AnnieXMusic to python-telegram-bot
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler
from datetime import datetime
from settings_manager_mongo import get_chat_settings

def get_last_seen(status):
    """Get last seen status text."""
    status_map = {
        'online': '☑️ Online',
        'offline': '❄️ Offline',
        'recently': '⏱ Recently',
        'last_week': '🗓 Last Week',
        'last_month': '📆 Last Month',
    }
    return status_map.get(status, '❓ Unknown')

async def whois_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get user information."""
    # Check if command is enabled
    chat = update.effective_chat
    settings = get_chat_settings(chat.id)
    if not settings.get("manager_info_enabled", True):
        return await update.message.reply_text("❌ The /info command is currently disabled.")
    
    try:
        if update.message.reply_to_message:
            user = update.message.reply_to_message.from_user
        elif context.args:
            user = await context.bot.get_chat(" ".join(context.args))
        else:
            user = update.effective_user
        
        loading = await update.message.reply_text("🔍 <b>Gathering user info...</b>", parse_mode='HTML')
        
        name = f"{user.first_name} {user.last_name}" if user.last_name else user.first_name
        username = f"@{user.username}" if user.username else "N/A"
        bio = user.description or "No bio" if hasattr(user, 'description') else "No bio"
        
        text = (
            f"👤 <b>User Info</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"➣ <b>User ID:</b> <code>{user.id}</code>\n"
            f"➣ <b>Name:</b> {name}\n"
            f"➣ <b>Username:</b> {username}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"➣ <b>Verified:</b> {'Yes ✅' if user.is_verified else 'No 🥀'}\n"
            f"➣ <b>Premium:</b> {'Yes ☑️' if user.is_premium else 'No 🥀'}\n"
            f"➣ <b>Bot:</b> {'Yes 🤖' if user.is_bot else 'No 👤'}\n"
            f"➣ <b>Profile Picture:</b> {'Yes 🌠' if user.photo else 'No 🥀'}\n"
        )
        
        profile_url = f"https://t.me/{user.username}" if user.username else f"tg://user?id={user.id}"
        buttons = InlineKeyboardMarkup([[
            InlineKeyboardButton("👤 View Profile", url=profile_url),
        ]])
        
        await loading.edit_text(
            text=text,
            parse_mode='HTML',
            reply_markup=buttons
        )
        
    except Exception as e:
        await update.message.reply_text(f"🥀 Error:\n<code>{str(e)}</code>", parse_mode='HTML')

def get_info_handlers():
    """Return info command handlers."""
    return [CommandHandler(["info", "whois"], whois_handler)]
