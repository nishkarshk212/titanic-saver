import logging
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, MessageHandler, filters, ChatMemberHandler
from config import OWNER_ID
from settings_manager import get_chat_settings
from welcome import format_welcome_message # Reuse the same formatter

async def on_member_leave_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle chat member status changes to detect leaves."""
    result = update.chat_member
    if not result:
        return
        
    old_status = result.old_chat_member.status
    new_status = result.new_chat_member.status
    
    # Strictly ignore joins
    if new_status in ['member', 'restricted', 'administrator', 'creator']:
        return

    # Trigger on leave (detects when a member leaves or is kicked)
    is_leaving = new_status in ['left', 'kicked'] and old_status in ['member', 'administrator', 'restricted']
    
    if is_leaving:
        chat_id = update.effective_chat.id
        settings = get_chat_settings(chat_id)
        
        if not settings.get("goodbye_enabled", False):
            logging.info(f"Skipping goodbye for user {result.old_chat_member.user.id} as goodbye_enabled is False")
            return

        member = result.old_chat_member.user
        if member.is_bot:
            return
            
        await send_goodbye(update.effective_chat, member, context)

async def send_goodbye(chat, user, context: ContextTypes.DEFAULT_TYPE):
    """Sends the goodbye message to a specific user in a chat."""
    chat_id = chat.id
    settings = get_chat_settings(chat_id)
    
    if not settings.get("goodbye_enabled", False):
        return

    goodbye_text_raw = settings.get('goodbye_text', "Goodbye {NAME}, we will miss you!")
    goodbye_media = settings.get('goodbye_media')
    goodbye_media_type = settings.get('goodbye_media_type', 'photo')
    goodbye_delete_time = settings.get('goodbye_delete_time', 60)
    media_enabled = settings.get('goodbye_media_enabled', True)
    button_enabled = settings.get('goodbye_button_enabled', True)
    goodbye_buttons = settings.get('goodbye_buttons', [])
    button_text = settings.get('goodbye_button_text')
    button_url = settings.get('goodbye_button_url')

    reply_markup = None
    if button_enabled:
        keyboard = []
        for btn in goodbye_buttons:
            if btn.get("text") and btn.get("url"):
                keyboard.append([InlineKeyboardButton(btn["text"], url=btn["url"])])
        
        if not keyboard and button_text and button_url:
            keyboard.append([InlineKeyboardButton(button_text, url=button_url)])
            
        if keyboard:
            reply_markup = InlineKeyboardMarkup(keyboard)

    # Format the goodbye message
    personal_goodbye = format_welcome_message(goodbye_text_raw, user, chat)
    
    msg = None
    if media_enabled and goodbye_media:
        try:
            if goodbye_media_type == "photo":
                msg = await context.bot.send_photo(chat_id=chat_id, photo=goodbye_media, caption=personal_goodbye, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
            elif goodbye_media_type == "video":
                msg = await context.bot.send_video(chat_id=chat_id, video=goodbye_media, caption=personal_goodbye, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
            elif goodbye_media_type == "animation":
                msg = await context.bot.send_animation(chat_id=chat_id, animation=goodbye_media, caption=personal_goodbye, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
            else:
                msg = await context.bot.send_document(chat_id=chat_id, document=goodbye_media, caption=personal_goodbye, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        except Exception as e:
            logging.error(f"Error sending goodbye media: {e}")
            msg = await context.bot.send_message(chat_id=chat_id, text=personal_goodbye, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        msg = await context.bot.send_message(chat_id=chat_id, text=personal_goodbye, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    
    if msg and goodbye_delete_time > 0 and context.job_queue:
        from config import delete_message_job
        try:
            context.job_queue.run_once(delete_message_job, goodbye_delete_time, data={"chat_id": chat_id, "message_id": msg.message_id})
        except Exception as e:
            logging.error(f"Error scheduling goodbye deletion: {e}")

def get_goodbye_handlers():
    """Return handlers for goodbye message."""
    return [
        ChatMemberHandler(on_member_leave_update, ChatMemberHandler.CHAT_MEMBER)
    ]
