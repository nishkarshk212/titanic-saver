import os
from dotenv import load_dotenv
import logging

from font import to_small_caps
from settings_manager_mongo import get_chat_settings

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")
OWNER_ID = int(os.getenv("OWNER_ID", 0))

START_IMG = os.getenv("START_IMG", "https://i.ibb.co/dwSr1BCH/071045e1b930a364060e7f853a6394b8.jpg https://i.ibb.co/QjxJJq4z/a543640d2cae1726345278d761180958.jpg https://i.ibb.co/VcFwYZj0/c94b8f6d7917e218e2494ef8dda9873c.jpg").split()

async def log_to_channel(context, message):
    """Logs a message to the specified log channel."""
    if LOG_CHANNEL_ID:
        try:
            # We don't apply small caps for logs for better readability
            await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"🔔 #LOG\n\n{message}")
        except Exception as e:
            logging.error(f"Failed to log to channel: {e}")

async def delete_admin_command(update, context):
    """Helper function to delete an admin's command message."""
    if update.message and update.message.text and update.message.text.startswith('/'):
        from user_manager_mongo import is_user_admin
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        # Don't delete if it's a private chat
        if update.effective_chat.type == "private":
            return
            
        # Check if user is admin/owner
        if await is_user_admin(chat_id, user_id, context):
            try:
                # We use a job to delete it slightly later to ensure the command 
                # handler has received the message and started processing
                if context.job_queue:
                    context.job_queue.run_once(
                        delete_message_job,
                        1, # 1 second delay
                        data={"chat_id": chat_id, "message_id": update.message.message_id}
                    )
            except Exception:
                pass

async def send_bot_response(update, context, text, **kwargs):
    """Sends a bot response formatted with small caps and schedules deletion in 30s."""
    logging.info(f"[RESPONSE] Sending response to chat {update.effective_chat.id if update.effective_chat else 'Unknown'}")
    # Convert text to small caps
    formatted_text = to_small_caps(text)
    logging.info(f"[RESPONSE] Formatted text: {formatted_text[:50]}...")
    
    # Send message - Try replying first, fallback to normal message if original is gone
    try:
        msg = await update.message.reply_text(formatted_text, **kwargs)
        logging.info(f"[RESPONSE] Sent via reply_text")
    except Exception as e:
        # If reply fails (e.g. original message deleted), send to chat normally
        logging.info(f"[RESPONSE] reply_text failed: {e}, falling back to send_message")
        msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=formatted_text,
            **kwargs
        )
        logging.info(f"[RESPONSE] Sent via send_message")
    
    # Handle command deletion if enabled for admins (after sending response)
    await delete_admin_command(update, context)
    
    # Schedule deletion in 30 seconds
    if context.job_queue:
        context.job_queue.run_once(
            delete_message_job,
            30,
            data={"chat_id": msg.chat_id, "message_id": msg.message_id}
        )
    return msg

async def send_bot_media(update, context, video=None, photo=None, caption="", **kwargs):
    """Sends a bot media response with formatted caption and auto-deletion in 30s."""
    formatted_caption = to_small_caps(caption)
    
    # Send media - Try replying first, fallback to normal media if original is gone
    try:
        if video:
            msg = await update.message.reply_video(video, caption=formatted_caption, **kwargs)
        elif photo:
            msg = await update.message.reply_photo(photo, caption=formatted_caption, **kwargs)
        else:
            return None
    except Exception:
        # Fallback to direct send
        if video:
            msg = await context.bot.send_video(chat_id=update.effective_chat.id, video=video, caption=formatted_caption, **kwargs)
        elif photo:
            msg = await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo, caption=formatted_caption, **kwargs)
        else:
            return None

    # Handle command deletion if enabled for admins (after sending response)
    await delete_admin_command(update, context)

    if context.job_queue:
        context.job_queue.run_once(
            delete_message_job,
            30,
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

def colored_button(text, color="default"):
    """Add emoji color indicator to button text for visual distinction.
    
    Args:
        text: Button text
        color: 'green', 'red', 'blue', or 'default'
    
    Returns:
        Text with color emoji prefix
    """
    color_map = {
        "green": "🟢",
        "red": "🔴", 
        "blue": "🔵",
        "default": "⚪"
    }
    emoji = color_map.get(color, "⚪")
    return f"{emoji} {text}"
