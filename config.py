import os
from dotenv import load_dotenv
import logging

from font import to_small_caps
from settings_manager import get_chat_settings
from user_manager import is_user_admin

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")
OWNER_ID = int(os.getenv("OWNER_ID", 0))

START_VIDEOS = [
    "https://files.catbox.moe/4ij8ag.mp4",
    "https://files.catbox.moe/z68nj0.mp4",
    "https://files.catbox.moe/nl65r9.mp4",
    "https://files.catbox.moe/3v4bft.mp4"
]

async def log_to_channel(context, message):
    """Logs a message to the specified log channel."""
    if LOG_CHANNEL_ID:
        try:
            # We don't apply small caps for logs for better readability
            await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"🔔 #LOG\n\n{message}")
        except Exception as e:
            logging.error(f"Failed to log to channel: {e}")

async def delete_admin_command(update, context):
    """Helper function to delete an admin's command message if enabled."""
    if update.message and update.message.text and update.message.text.startswith('/'):
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        settings = get_chat_settings(chat_id)
        
        if settings.get("command_deletion", False):
            # Check if user is admin/owner
            if await is_user_admin(chat_id, user_id, context):
                try:
                    await update.message.delete()
                except Exception:
                    pass

async def send_bot_response(update, context, text, **kwargs):
    """Sends a bot response formatted with small caps and schedules deletion in 2 mins."""
    # Convert text to small caps
    formatted_text = to_small_caps(text)
    
    # Handle command deletion if enabled for admins
    await delete_admin_command(update, context)

    # Send message
    msg = await update.message.reply_text(formatted_text, **kwargs)
    
    # Schedule deletion in 2 minutes (120 seconds)
    if context.job_queue:
        context.job_queue.run_once(
            delete_message_job,
            120,
            data={"chat_id": msg.chat_id, "message_id": msg.message_id}
        )
    return msg

async def send_bot_media(update, context, video=None, photo=None, caption="", **kwargs):
    """Sends a bot media response with formatted caption and auto-deletion."""
    formatted_caption = to_small_caps(caption)
    
    # Handle command deletion if enabled for admins
    await delete_admin_command(update, context)
    
    if video:
        msg = await update.message.reply_video(video, caption=formatted_caption, **kwargs)
    elif photo:
        msg = await update.message.reply_photo(photo, caption=formatted_caption, **kwargs)
    else:
        return None

    if context.job_queue:
        context.job_queue.run_once(
            delete_message_job,
            120,
            data={"chat_id": msg.chat_id, "message_id": msg.message_id}
        )
    return msg

async def edit_bot_response(query, context, text, **kwargs):
    """Edits a bot message with small caps formatting."""
    formatted_text = to_small_caps(text)
    try:
        await query.edit_message_text(formatted_text, **kwargs)
    except Exception:
        pass

async def delete_message_job(context):
    """Job function to delete a message."""
    data = context.job.data
    try:
        await context.bot.delete_message(chat_id=data["chat_id"], message_id=data["message_id"])
    except Exception:
        pass
