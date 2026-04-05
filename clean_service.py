import logging
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from settings_manager import get_chat_settings

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

    if should_delete:
        logging.info(f"Deleting service message in {chat_id}")
        try:
            await update.message.delete()
        except Exception as e:
            logging.error(f"Failed to delete service message in {chat_id}: {e}")

def get_clean_service_handlers():
    """Return handlers for cleaning service messages."""
    return [
        MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS | 
            filters.StatusUpdate.LEFT_CHAT_MEMBER | 
            filters.StatusUpdate.VIDEO_CHAT_STARTED | 
            filters.StatusUpdate.VIDEO_CHAT_ENDED | 
            filters.StatusUpdate.VIDEO_CHAT_PARTICIPANTS_INVITED | 
            filters.StatusUpdate.VIDEO_CHAT_SCHEDULED,
            clean_service_messages
        )
    ]
