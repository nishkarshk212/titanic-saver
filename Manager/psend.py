"""
Manager Psend Command - Send private message to a specific user
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler
from settings_manager_mongo import check_command_access
from user_manager_mongo import get_user_id
from config import send_bot_response

async def psend_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a private message to a specific user."""
    if not update.message:
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Check command access
    if not await check_command_access(chat_id, user_id, 'psend', context):
        await send_bot_response(update, context, "❌ You don't have permission to use the /psend command.")
        return

    target_user_id, _ = await get_user_id(update, context)
    
    if not target_user_id:
        await send_bot_response(
            update, context,
            "❌ <b>Usage:</b>\n"
            "• Reply to a user: <code>/psend [message]</code>\n"
            "• Use username/ID: <code>/psend [@username/ID] [message]</code>",
            parse_mode='HTML'
        )
        return

    # Extract message text
    if update.message.reply_to_message:
        message_text = " ".join(context.args) if context.args else ""
    else:
        # If it was an ID/Username in args[0], message is from args[1:]
        message_text = " ".join(context.args[1:]) if len(context.args) > 1 else ""

    if not message_text:
        await send_bot_response(update, context, "❌ Please provide a message to send.")
        return

    try:
        # Send the message
        sender_mention = update.effective_user.mention_html()
        chat_title = update.effective_chat.title
        
        pm_text = (
            f"📩 <b>New Private Message</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"➣ <b>From:</b> {sender_mention}\n"
            f"➣ <b>Group:</b> {chat_title}\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"{message_text}"
        )
        
        await context.bot.send_message(
            chat_id=target_user_id,
            text=pm_text,
            parse_mode='HTML'
        )
        
        await send_bot_response(update, context, f"✅ Message sent to <code>{target_user_id}</code>.")
        
    except Exception as e:
        error_msg = str(e)
        if "bot was blocked" in error_msg.lower():
            await send_bot_response(update, context, "❌ Could not send message: The user has blocked the bot.")
        elif "chat not found" in error_msg.lower():
            await send_bot_response(update, context, "❌ Could not send message: The user has not started the bot.")
        else:
            await send_bot_response(update, context, f"❌ Failed to send message: {error_msg}")

def get_psend_handlers():
    """Return psend command handlers."""
    return [CommandHandler("psend", psend_handler)]
