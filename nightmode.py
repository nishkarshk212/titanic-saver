"""
Night Mode Module - Restrict group activities during specified hours
"""

import logging
from datetime import datetime
import pytz
from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes, MessageHandler, filters
from settings_manager_mongo import get_chat_settings
from user_manager_mongo import is_user_admin
from config import OWNER_ID

def is_night_time(chat_id):
    """Checks if it's currently night time for the chat."""
    settings = get_chat_settings(chat_id)
    if not settings.get("nightmode_enabled", False):
        return False

    start_hour = settings.get("nightmode_start", 23)
    end_hour = settings.get("nightmode_end", 9)
    timezone_str = settings.get("nightmode_timezone", "UTC")

    try:
        tz = pytz.timezone(timezone_str)
    except Exception:
        tz = pytz.UTC

    now = datetime.now(tz)
    current_hour = now.hour

    if start_hour > end_hour:
        # Overnights (e.g., 23 to 9)
        return current_hour >= start_hour or current_hour < end_hour
    else:
        # Same day (e.g., 22 to 23)
        return start_hour <= current_hour < end_hour

async def handle_nightmode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles night mode restrictions."""
    if not update.effective_chat or not update.effective_user or update.effective_chat.type == "private":
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Skip admins and owner
    if user_id == OWNER_ID or await is_user_admin(chat_id, user_id, context):
        return

    if not is_night_time(chat_id):
        return

    settings = get_chat_settings(chat_id)
    message = update.effective_message

    should_delete = False
    
    # Check restrictions
    if settings.get("nightmode_restrict_text", False) and message.text and not message.text.startswith('/'):
        should_delete = True
    elif settings.get("nightmode_restrict_media", False) and (message.photo or message.video or message.audio or message.document or message.animation):
        should_delete = True
    elif settings.get("nightmode_restrict_stickers", False) and message.sticker:
        should_delete = True
    elif settings.get("nightmode_global_silence", False): # If everything is silenced
        should_delete = True

    if should_delete:
        try:
            await message.delete()
            # Optional: Send a temporary warning if advised
            if settings.get("nightmode_advise_enabled", True):
                # We can use a job to avoid spamming warnings
                job_key = f"night_warn_{chat_id}_{user_id}"
                if job_key not in context.user_data or (datetime.now().timestamp() - context.user_data[job_key]) > 60:
                    warn = await context.bot.send_message(
                        chat_id,
                        f"🌙 <b>Night Mode is Active</b>\n\n"
                        f"Restrictions are currently in place. Please wait until morning!",
                        parse_mode='HTML'
                    )
                    context.user_data[job_key] = datetime.now().timestamp()
                    # Auto delete warning
                    context.job_queue.run_once(
                        lambda c: c.bot.delete_message(chat_id, warn.message_id),
                        10
                    )
        except Exception as e:
            logging.error(f"Error in nightmode deletion: {e}")

async def handle_nightmode_config_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles configuration input for night mode settings."""
    state_data = context.user_data.get('config_state')
    if not state_data or not isinstance(state_data, tuple) or state_data[0] not in ['nightmode_time', 'nightmode_timezone']:
        return False
    
    state, chat_id = state_data
    
    if update.message and update.message.text == "/cancel":
        context.user_data['config_state'] = None
        await update.message.reply_text("❌ Configuration cancelled.")
        return True

    text = update.message.text
    if not text:
        return False

    if state == 'nightmode_time':
        try:
            parts = text.split()
            if len(parts) != 2: raise ValueError
            start_hour = int(parts[0])
            end_hour = int(parts[1])
            if not (0 <= start_hour <= 23 and 0 <= end_hour <= 23): raise ValueError
            
            from settings_manager_mongo import update_chat_setting
            update_chat_setting(chat_id, "nightmode_start", start_hour)
            update_chat_setting(chat_id, "nightmode_end", end_hour)
            
            await update.message.reply_text(f"✅ Night Mode time slot set to: <b>{start_hour} to {end_hour}</b>", parse_mode='HTML')
        except:
            await update.message.reply_text("❌ Invalid format. Please enter two numbers between 0 and 23 (e.g., <code>23 9</code>).", parse_mode='HTML')
            return True
            
    elif state == 'nightmode_timezone':
        try:
            pytz.timezone(text)
            from settings_manager_mongo import update_chat_setting
            update_chat_setting(chat_id, "nightmode_timezone", text)
            await update.message.reply_text(f"✅ Night Mode time zone set to: <b>{text}</b>", parse_mode='HTML')
        except:
            await update.message.reply_text("❌ Invalid timezone. Examples: <code>Asia/Kolkata</code>, <code>UTC</code>, <code>Europe/London</code>.", parse_mode='HTML')
            return True

    # Reset state and return to nightmode menu
    context.user_data['config_state'] = None
    from settings import settings_callback
    # We can't easily trigger the callback without a query, so we just prompt to reopen
    await update.message.reply_text("Settings updated! Please reopen /settings to see the changes.")
    return True

def get_nightmode_handlers():
    """Returns nightmode message handlers."""
    from telegram.ext import MessageHandler, filters
    return [
        MessageHandler(filters.REPLY & filters.ChatType.PRIVATE, handle_nightmode_config_input),
        MessageHandler(filters.ALL & ~filters.COMMAND & filters.ChatType.GROUPS, handle_nightmode)
    ]
