import logging
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from settings_manager_mongo import get_chat_settings

async def delete_msg_job(context: ContextTypes.DEFAULT_TYPE):
    """Job that deletes a message after a delay."""
    job = context.job
    try:
        await context.bot.delete_message(chat_id=job.chat_id, message_id=job.data)
    except Exception as e:
        # Ignore if message is already deleted or bot has no permission
        pass

async def auto_delete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Automatically schedules deletion for every message in the group."""
    if not update.message:
        return
        
    chat_id = update.effective_chat.id
    settings = get_chat_settings(chat_id)
    
    if not settings.get("auto_delete_enabled", False):
        return

    delay = settings.get("auto_delete_time", 60) # seconds
    
    # Schedule deletion job
    logging.info(f"Scheduling deletion for message {update.message.message_id} in {chat_id} in {delay}s")
    context.job_queue.run_once(
        delete_msg_job, 
        when=delay, 
        chat_id=chat_id, 
        data=update.message.message_id,
        name=f"delete_{chat_id}_{update.message.message_id}"
    )

def get_auto_delete_handlers():
    """Return handlers for auto-deletion."""
    # SUPERGROUP is important as most modern groups are supergroups
    return [
        MessageHandler((filters.ChatType.GROUPS | filters.ChatType.SUPERGROUP) & filters.ALL, auto_delete_handler)
    ]
