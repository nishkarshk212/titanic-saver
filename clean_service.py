import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from settings_manager_mongo import get_chat_settings
from config import delete_message_job

async def clean_service_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Automatically deletes service messages based on group settings."""
    if not update.message:
        return
        
    chat_id = update.effective_chat.id
    settings = get_chat_settings(chat_id)
    
    if not settings.get("clean_service_enabled", True):
        return

    should_delete = False
    
    # 1. New Member Joins
    if update.message.new_chat_members and settings.get("clean_join", True):
        should_delete = True
        
    # 2. Member Leaves
    elif update.message.left_chat_member and settings.get("clean_left", True):
        should_delete = True
        
    # 3. Individual Video/Voice Chat Messages
    elif update.message.video_chat_started and settings.get("clean_video_chat_started", True):
        should_delete = True
    elif update.message.video_chat_ended and settings.get("clean_video_chat_ended", True):
        should_delete = True
    elif update.message.video_chat_participants_invited and settings.get("clean_video_chat_invited", True):
        should_delete = True
    elif update.message.video_chat_scheduled and settings.get("clean_video_chat_scheduled", True):
        should_delete = True
    elif update.message.pinned_message and settings.get("clean_pinned_message", True):
        should_delete = True
        logging.info(f"Pinned message detected. clean_pinned_message setting: {settings.get('clean_pinned_message', True)}. Update message: {update.message}")
    elif update.message.new_chat_title and settings.get("clean_title", True):
        # Name change notification should delete in 15 seconds
        logging.info(f"New chat title detected. Scheduling deletion in 15s in {chat_id}")
        context.job_queue.run_once(
            delete_message_job,
            15,
            data={"chat_id": chat_id, "message_id": update.message.message_id}
        )
        return
    elif update.message.new_chat_photo and settings.get("clean_photo", True):
        should_delete = True
    elif update.message.delete_chat_photo and settings.get("clean_photo", True):
        should_delete = True
    elif update.message.group_chat_created or update.message.supergroup_chat_created or update.message.channel_chat_created:
        should_delete = True
    elif update.message.migrate_to_chat_id or update.message.migrate_from_chat_id:
        should_delete = True
    elif update.message.message_auto_delete_timer_changed:
        should_delete = True

    if should_delete:
        logging.info(f"Attempting to delete service message in {chat_id}. Message ID: {update.message.message_id}")
        try:
            await update.message.delete()
            logging.info(f"Successfully deleted service message in {chat_id}. Message ID: {update.message.message_id}")
        except Exception as e:
            logging.error(f"Failed to delete service message in {chat_id}, Message ID: {update.message.message_id}: {e}")

def get_clean_service_handlers():
    """Return handlers for cleaning service messages."""
    return [
        MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS | 
            filters.StatusUpdate.LEFT_CHAT_MEMBER | 
            filters.StatusUpdate.VIDEO_CHAT_STARTED | 
            filters.StatusUpdate.VIDEO_CHAT_ENDED | 
            filters.StatusUpdate.VIDEO_CHAT_PARTICIPANTS_INVITED | 
            filters.StatusUpdate.VIDEO_CHAT_SCHEDULED |
            filters.StatusUpdate.PINNED_MESSAGE |
            filters.StatusUpdate.NEW_CHAT_TITLE |
            filters.StatusUpdate.NEW_CHAT_PHOTO |
            filters.StatusUpdate.DELETE_CHAT_PHOTO |
            filters.StatusUpdate.CHAT_CREATED |
            filters.StatusUpdate.MIGRATED |
            filters.StatusUpdate.MESSAGE_AUTO_DELETE_TIMER_CHANGED,
            clean_service_messages
        )
    ]
