import logging
import os
import html
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from admin import get_admin_handlers
from welcome import get_welcome_handlers
from goodbye import get_goodbye_handlers
from block_content import get_block_content_handlers
from clean_service import get_clean_service_handlers
from auto_delete import get_auto_delete_handlers
from moderation import get_moderation_handlers
from filter import get_filter_handlers
from settings import get_settings_handlers
from help import get_help_handlers
from config import BOT_TOKEN, LOG_CHANNEL_ID, OWNER_ID, log_to_channel, send_bot_response, send_bot_media, START_VIDEOS
from user_manager import cache_user, increment_message_count, get_user_id, get_user_stats, is_user_admin
from settings_manager import get_chat_settings

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update, context):
    """Start command handler."""
    bot_info = await context.bot.get_me()
    bot_name = bot_info.first_name
    bot_username = bot_info.username
    add_to_group_url = f"https://t.me/{bot_username}?startgroup=true"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add to Group", url=add_to_group_url)]
    ])
    
    video_url = random.choice(START_VIDEOS)
    
    start_message = (
        f"๏ ᴛʜɪs ɪs {bot_name}\n\n"
        "➻ ᴀ ᴘᴏᴡᴇʀғᴜʟ sᴇᴄᴜʀɪᴛʏ ʙᴏᴛ ᴅᴇsɪɢɴᴇᴅ ᴛᴏ ᴘʀᴏᴛᴇᴄᴛ ʏᴏᴜʀ ᴛᴇʟᴇɢʀᴀᴍ ɢʀᴏᴜᴘ\n"
        "ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ & ɢɪᴠᴇ ᴍᴇ ᴀᴅᴍɪɴ & ᴅᴇʟᴇᴛᴇ ᴍᴇssᴀɢᴇ ʀɪɢʜᴛ ɪ sᴛᴀʀᴛ ᴘʀᴏᴛᴇᴄᴛɪɴɢ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ\n"
        "➻ ɢɪᴠᴇ ᴍᴇ ᴀ ᴄʜᴀɴᴄᴇ ʜᴀɴᴅʟᴇ ʏᴏᴜʀ ɢʀᴏᴜᴘ."
    )
    
    await send_bot_media(
        update, context,
        video=video_url,
        caption=start_message,
        reply_markup=keyboard
    )

async def cache_user_handler(update, context):
    """Caches user information and tracks message counts."""
    if not update.effective_chat: return
    
    # 1. Cache the sender and increment message count
    if update.effective_user:
        user = update.effective_user
        cache_user(user.id, user.username, user.first_name)
        if update.message and not update.message.text.startswith('/'):
            increment_message_count(user.id)
    
    # 2. Cache any users mentioned in the message
    if update.message and update.message.entities:
        for entity in update.message.entities:
            if entity.type == 'text_mention':
                cache_user(entity.user.id, entity.user.username, entity.user.first_name)

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to show detailed user info."""
    chat_id = update.effective_chat.id
    settings = get_chat_settings(chat_id)
    
    # Check access (Admin only if setting enabled)
    if settings.get("command_access") == "admins":
        if not await is_user_admin(chat_id, update.effective_user.id, context):
            return # Silently ignore or send error

    user_id, first_name = await get_user_id(update, context)
    if not user_id:
        user = update.effective_user
        user_id, first_name = user.id, user.first_name
    
    stats = get_user_stats(user_id)
    username = stats.get("username") if stats else None
    joined_date = stats.get("joined_date", "Unknown") if stats else "Unknown"
    msg_count = stats.get("msg_count", 0) if stats else 0
    
    info_text = (
        f"👤 <b>User Information</b>\n\n"
        f"• <b>Name:</b> {html.escape(first_name)}\n"
        f"• <b>Username:</b> @{username if username else 'None'}\n"
        f"• <b>User ID:</b> <code>{user_id}</code>\n"
        f"• <b>Joined Date:</b> {joined_date}\n"
        f"• <b>Total Messages:</b> {msg_count}"
    )
    
    await send_bot_response(update, context, info_text, parse_mode=ParseMode.HTML)

async def get_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simple command to show user ID and ensure they are cached."""
    chat_id = update.effective_chat.id
    settings = get_chat_settings(chat_id)
    
    # Check access
    if settings.get("command_access") == "admins":
        if not await is_user_admin(chat_id, update.effective_user.id, context):
            return

    user = update.effective_user
    chat = update.effective_chat
    
    # Use HTML and escape inputs to prevent parsing errors
    user_name = html.escape(user.first_name)
    chat_title = html.escape(chat.title) if chat.title else "Private Chat"
    
    await send_bot_response(
        update, context,
        f"👤 <b>User Info:</b>\n"
        f"• Name: {user_name}\n"
        f"• ID: <code>{user.id}</code>\n"
        f"• Username: @{user.username if user.username else 'None'}\n\n"
        f"📍 <b>Chat Info:</b>\n"
        f"• Title: {chat_title}\n"
        f"• ID: <code>{chat.id}</code>",
        parse_mode=ParseMode.HTML
    )

def main():
    """Main function to run the bot."""
    if not BOT_TOKEN:
        print("BOT_TOKEN not found in .env file. Please add it.")
        return

    # Initialize the bot application
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add general handlers (Group 0)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("id", get_id_command))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(MessageHandler(filters.ALL & (filters.ChatType.GROUPS | filters.ChatType.SUPERGROUP), cache_user_handler), group=-1)

    # Add admin handlers (Group 0)
    for handler in get_admin_handlers():
        application.add_handler(handler)

    # Add help handlers (Group 0)
    for handler in get_help_handlers():
        application.add_handler(handler)

    # Add settings handlers (Group 0)
    for handler in get_settings_handlers():
        application.add_handler(handler)

    # Add moderation handlers (Group 0)
    for handler in get_moderation_handlers():
        application.add_handler(handler)

    # Add welcome handlers (Group 0)
    for handler in get_welcome_handlers():
        application.add_handler(handler)

    # Add goodbye handlers (Group 0)
    for handler in get_goodbye_handlers():
        application.add_handler(handler)

    # Add block content handlers (Group 0)
    for handler in get_block_content_handlers():
        # The MessageHandler for block content check should be in its own group to run concurrently
        if isinstance(handler, MessageHandler) and not isinstance(handler, CommandHandler):
            application.add_handler(handler, group=4)
        else:
            application.add_handler(handler)

    # Add clean service handlers in a separate group (Group 1)
    # This ensures they run even if other handlers match
    for handler in get_clean_service_handlers():
        application.add_handler(handler, group=1)

    # Add auto delete handlers in another separate group (Group 2)
    for handler in get_auto_delete_handlers():
        application.add_handler(handler, group=2)

    # Add filter handlers in another group (Group 3)
    for handler in get_filter_handlers():
        # The filter command handlers go to group 0 (default), 
        # but the MessageHandler for triggers should be in its own group to run concurrently
        if isinstance(handler, MessageHandler):
            application.add_handler(handler, group=3)
        else:
            application.add_handler(handler)

    # Start the bot
    print("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
