import logging
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
import os
from config import OWNER_ID, log_to_channel
from settings_manager import get_chat_settings, update_chat_setting
from user_manager import cache_user

def format_welcome_message(text, user, chat):
    """Formats the welcome message with dynamic placeholders."""
    now = datetime.datetime.now()
    
    # Placeholders dictionary
    placeholders = {
        "{ID}": str(user.id),
        "{NAME}": user.first_name or "",
        "{SURNAME}": user.last_name or "",
        "{NAMESURNAME}": f"{user.first_name or ''} {user.last_name or ''}".strip(),
        "{LANG}": user.language_code or "Unknown",
        "{DATE}": now.strftime("%Y-%m-%d"),
        "{TIME}": now.strftime("%H:%M:%S"),
        "{WEEKDAY}": now.strftime("%A"),
        "{MENTION}": f'<a href="tg://user?id={user.id}">{user.first_name}</a>',
        "{USERNAME}": f"@{user.username}" if user.username else "No Username",
        "{GROUPNAME}": chat.title or "this group",
        "{RULES}": "/rules" # Placeholder for rules, can be customized
    }
    
    formatted_text = text
    for key, value in placeholders.items():
        formatted_text = formatted_text.replace(key, value)
    
    return formatted_text

async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set the welcome message text."""
    if not update.message: return
    
    # Check admin or owner
    sender_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if sender_id != OWNER_ID:
        member = await context.bot.get_chat_member(chat_id, sender_id)
        if member.status not in ['administrator', 'creator']:
            await update.message.reply_text("Admin only command.")
            return

    text = update.message.text.split(" ", 1)
    if len(text) < 2:
        await update.message.reply_text("Usage: /setwelcome <welcome message text>")
        return

    welcome_text = text[1]
    update_chat_setting(chat_id, "welcome_text", welcome_text)
    await update.message.reply_text("Welcome message text updated!")

async def set_welcome_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set the welcome message photo."""
    if not update.message or not update.message.reply_to_message or not update.message.reply_to_message.photo:
        await update.message.reply_text("Please reply to a photo message with /setphoto to set the welcome photo.")
        return

    # Check admin or owner
    sender_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if sender_id != OWNER_ID:
        member = await context.bot.get_chat_member(chat_id, sender_id)
        if member.status not in ['administrator', 'creator']:
            await update.message.reply_text("Admin only command.")
            return

    photo_file_id = update.message.reply_to_message.photo[-1].file_id
    update_chat_setting(chat_id, "welcome_media", photo_file_id)
    await update.message.reply_text("Welcome photo updated!")

async def set_welcome_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set the welcome message button."""
    if not update.message: return
    
    # Check admin or owner
    sender_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if sender_id != OWNER_ID:
        member = await context.bot.get_chat_member(chat_id, sender_id)
        if member.status not in ['administrator', 'creator']:
            await update.message.reply_text("Admin only command.")
            return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /setbutton <button_text> <button_url>")
        return

    button_text = args[0]
    button_url = args[1]
    
    update_chat_setting(chat_id, "welcome_button_text", button_text)
    update_chat_setting(chat_id, "welcome_button_url", button_url)
    
    await update.message.reply_text(f"Welcome button updated: {button_text} -> {button_url}")

async def on_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when a new member joins."""
    chat_id = update.effective_chat.id
    settings = get_chat_settings(chat_id)
    
    if not settings.get("welcome_enabled", True):
        return

    welcome_text_raw = settings.get('welcome_text', "Welcome {NAME} to the group!")
    welcome_media = settings.get('welcome_media')
    media_enabled = settings.get('welcome_media_enabled', True)
    button_enabled = settings.get('welcome_button_enabled', True)
    button_text = settings.get('welcome_button_text')
    button_url = settings.get('welcome_button_url')

    reply_markup = None
    if button_enabled and button_text and button_url:
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(button_text, url=button_url)]])

    for member in update.message.new_chat_members:
        if member.is_bot: continue
        
        # Cache the user as soon as they join
        cache_user(member.id, member.username, member.first_name)
        
        # Format the welcome message with advanced placeholders
        personal_welcome = format_welcome_message(welcome_text_raw, member, update.effective_chat)
        
        if media_enabled and welcome_media:
            try:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=welcome_media,
                    caption=personal_welcome,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                logging.error(f"Error sending welcome photo: {e}")
                # Fallback to text if photo fails
                await context.bot.send_message(
                    chat_id=chat_id, 
                    text=personal_welcome, 
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
        else:
            await context.bot.send_message(
                chat_id=chat_id, 
                text=personal_welcome, 
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )

def get_welcome_handlers():
    """Return handlers for welcome message."""
    return [
        CommandHandler("setwelcome", set_welcome),
        CommandHandler("setphoto", set_welcome_photo),
        CommandHandler("setbutton", set_welcome_button),
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member)
    ]
