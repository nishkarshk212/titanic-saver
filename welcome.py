import logging
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, ChatMemberHandler
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

async def send_welcome(chat, user, context: ContextTypes.DEFAULT_TYPE):
    """Sends the welcome message to a specific user in a chat."""
    chat_id = chat.id
    settings = get_chat_settings(chat_id)
    
    if not settings.get("welcome_enabled", True):
        return

    welcome_text_raw = settings.get('welcome_text', "Welcome {NAME} to the group!")
    welcome_media = settings.get('welcome_media')
    welcome_media_type = settings.get('welcome_media_type', 'photo')
    welcome_delete_time = settings.get('welcome_delete_time', 60)
    media_enabled = settings.get('welcome_media_enabled', True)
    button_enabled = settings.get('welcome_button_enabled', True)
    welcome_buttons = settings.get('welcome_buttons', [])
    button_text = settings.get('welcome_button_text')
    button_url = settings.get('welcome_button_url')

    reply_markup = None
    if button_enabled:
        keyboard = []
        # Add multiple buttons if they exist
        for btn in welcome_buttons:
            if btn.get("text") and btn.get("url"):
                keyboard.append([InlineKeyboardButton(btn["text"], url=btn["url"])])
        
        # Fallback to single button if no multiple buttons but single button exists
        if not keyboard and button_text and button_url:
            keyboard.append([InlineKeyboardButton(button_text, url=button_url)])
            
        if keyboard:
            reply_markup = InlineKeyboardMarkup(keyboard)
            logging.info(f"Generated welcome keyboard with {len(keyboard)} buttons")
        else:
            logging.info("No welcome buttons generated (keyboard empty)")
    else:
        logging.info("Welcome buttons disabled in settings")

    # Cache the user
    cache_user(user.id, user.username, user.first_name)
    
    # Format the welcome message
    personal_welcome = format_welcome_message(welcome_text_raw, user, chat)
    
    msg = None
    if media_enabled and welcome_media:
        try:
            if welcome_media_type == "photo":
                msg = await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=welcome_media,
                    caption=personal_welcome,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
            elif welcome_media_type == "video":
                msg = await context.bot.send_video(
                    chat_id=chat_id,
                    video=welcome_media,
                    caption=personal_welcome,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
            elif welcome_media_type == "animation":
                msg = await context.bot.send_animation(
                    chat_id=chat_id,
                    animation=welcome_media,
                    caption=personal_welcome,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
            else: # document or fallback
                msg = await context.bot.send_document(
                    chat_id=chat_id,
                    document=welcome_media,
                    caption=personal_welcome,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
        except Exception as e:
            logging.error(f"Error sending welcome media: {e}")
            msg = await context.bot.send_message(
                chat_id=chat_id, 
                text=personal_welcome, 
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
    else:
        msg = await context.bot.send_message(
            chat_id=chat_id, 
            text=personal_welcome, 
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    # Schedule deletion if msg sent and time > 0
    if msg and welcome_delete_time > 0 and context.job_queue:
        from config import delete_message_job
        try:
            context.job_queue.run_once(
                delete_message_job,
                welcome_delete_time,
                data={"chat_id": chat_id, "message_id": msg.message_id}
            )
        except Exception as e:
            logging.error(f"Error scheduling welcome deletion: {e}")

async def on_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when a new member joins via service message (fallback)."""
    if not update.message or not update.message.new_chat_members:
        return
        
    for member in update.message.new_chat_members:
        if member.is_bot: continue
        await send_welcome(update.effective_chat, member, context)

async def on_chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle chat member status changes to detect joins/re-joins."""
    result = update.chat_member
    if not result:
        return
        
    old_status = result.old_chat_member.status
    new_status = result.new_chat_member.status
    settings = get_chat_settings(update.effective_chat.id)
    
    # Debug log
    logging.info(f"Chat Member Update: {old_status} -> {new_status} for user {result.new_chat_member.user.id}")
    
    # Trigger on join (detects both new joins and re-joins)
    # 1. new_status is 'member' or 'administrator' or 'creator'
    # old_status was 'left' or 'kicked' or 'none' (none is for some first-time joins)
    is_joining = new_status in ['member', 'administrator'] and old_status in ['left', 'kicked', 'none', 'restricted']
    
    # Check if it's an invite link join (sometimes status stays same but update triggers)
    # If welcome_rejoin_enabled is True, we should be more permissive.
    
    if is_joining or (settings.get("welcome_rejoin_enabled", True) and new_status == old_status and new_status in ['member', 'restricted']):
        member = result.new_chat_member.user
        if member.is_bot:
            return
            
        # Check rejoin setting if it's clearly a rejoin
        if old_status in ['left', 'kicked', 'restricted'] or (new_status == old_status):
            if not settings.get("welcome_rejoin_enabled", True):
                logging.info(f"Skipping welcome for re-joining user {member.id} as welcome_rejoin_enabled is False")
                return
        
        await send_welcome(update.effective_chat, member, context)

def get_welcome_handlers():
    """Return handlers for welcome message."""
    return [
        CommandHandler("setwelcome", set_welcome),
        CommandHandler("setphoto", set_welcome_photo),
        CommandHandler("setbutton", set_welcome_button),
        # Handle service messages (legacy fallback)
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member),
        # Handle status changes (detects joins and re-joins reliably)
        ChatMemberHandler(on_chat_member_update, ChatMemberHandler.CHAT_MEMBER)
    ]
