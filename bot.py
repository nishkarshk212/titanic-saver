import logging
import os
import html
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from admin import get_admin_handlers
from welcome import get_welcome_handlers
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
    
    # Get user status and role in group
    user_status = "Unknown"
    user_role = "Member"
    is_muted = False
    
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        status = member.status
        
        # Determine Status & Role
        if status == 'creator':
            user_status = "Present"
            user_role = "Owner/Creator"
        elif status == 'administrator':
            user_status = "Present"
            user_role = "Administrator"
            if member.custom_title:
                user_role += f" ({member.custom_title})"
        elif status == 'member':
            user_status = "Present"
            user_role = "Member"
        elif status == 'restricted':
            user_status = "Present (Restricted)"
            user_role = "Restricted Member"
            if not member.can_send_messages:
                is_muted = True
        elif status == 'left':
            user_status = "Left"
            user_role = "None"
        elif status == 'kicked':
            user_status = "Banned"
            user_role = "None"
            
    except Exception as e:
        logging.error(f"Error getting member status for info: {e}")

    info_text = (
        f"👤 <b>User Information</b>\n\n"
        f"• <b>Name:</b> {html.escape(first_name)}\n"
        f"• <b>Username:</b> @{username if username else 'None'}\n"
        f"• <b>User ID:</b> <code>{user_id}</code>\n"
        f"• <b>Status:</b> {user_status}\n"
        f"• <b>Role:</b> {user_role}\n"
        f"• <b>Muted:</b> {'Yes 🔇' if is_muted else 'No 🔊'}\n"
        f"• <b>Joined Date:</b> {joined_date}\n"
        f"• <b>Total Messages:</b> {msg_count}"
    )
    
    # Create keyboard for admins
    reply_markup = None
    if await is_user_admin(chat_id, update.effective_user.id, context):
        keyboard = [
            [
                InlineKeyboardButton("⚠️ Warns", callback_data=f"info_warns_{user_id}"),
                InlineKeyboardButton("🎭 Roles", callback_data=f"info_roles_{user_id}")
            ],
            [
                InlineKeyboardButton("🔇 Mute" if not is_muted else "🔊 Unmute", callback_data=f"info_mute_{user_id}"),
                InlineKeyboardButton("🔨 Ban", callback_data=f"info_ban_{user_id}")
            ],
            [InlineKeyboardButton("🛡️ Permissions", callback_data=f"info_perms_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

    await send_bot_response(update, context, info_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

async def info_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle management buttons from the /info command."""
    query = update.callback_query
    chat_id = update.effective_chat.id
    admin_id = update.effective_user.id
    
    # Permission check: only admins can use these buttons
    if not await is_user_admin(chat_id, admin_id, context):
        await query.answer("Admin only feature.", show_alert=True)
        return

    data = query.data.split("_")
    action = data[1]
    user_id = int(data[2])
    
    # Import handlers locally to avoid circular imports if needed
    from moderation import mute_command, unmute_command, ban_command, warn_command
    from admin import promote_command
    
    # Create a mock update to reuse existing command logic
    class MockMessage:
        def __init__(self, chat, from_user, reply_to_message=None):
            self.chat = chat
            self.from_user = from_user
            self.reply_to_message = reply_to_message
            self.text = ""
        async def reply_text(self, text, *args, **kwargs):
            await query.message.reply_text(text, *args, **kwargs)

    mock_update = Update(update.update_id, message=MockMessage(update.effective_chat, update.effective_user))
    # For user_id extraction, we'll manually set context.args if needed or rely on a trick
    # Most command handlers use get_user_id which checks reply, mentions, or args.
    # We'll mock context.args to contain the user_id
    context.args = [str(user_id)]

    if action == "warns":
        await warn_command(mock_update, context)
        await query.answer("Warning applied.")
    elif action == "mute":
        # Check current mute status
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status == 'restricted' and not member.can_send_messages:
            await unmute_command(mock_update, context)
            await query.answer("User unmuted.")
        else:
            await mute_command(mock_update, context)
            await query.answer("User muted.")
    elif action == "ban":
        await ban_command(mock_update, context)
        await query.answer("User banned.")
    elif action == "roles":
        await promote_command(mock_update, context)
        await query.answer("Promotion menu opened.")
    elif action == "perms":
        # Reuse promotion for perms as well
        await promote_command(mock_update, context)
        await query.answer("Permissions menu opened.")
    
    # Refresh info if possible (optional)
    # await info_command(mock_update, context)

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
    application.add_handler(CallbackQueryHandler(info_callback_handler, pattern="^info_"))
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
