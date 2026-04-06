import logging
from telegram import Update, ChatPermissions
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from config import OWNER_ID, send_bot_response, log_to_channel
from settings_manager import get_chat_settings
from moderation_manager import add_warn, reset_warns
from user_manager import is_user_admin, get_user_id
from block_content_manager import add_blocked_content, remove_blocked_content, is_content_blocked, get_blocked_content

async def block_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to block a specific content (text, media, etc.)."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if user_id != OWNER_ID and not await is_user_admin(chat_id, user_id, context):
        await send_bot_response(update, context, "Only admins can use the /block command.")
        return

    # 1. Handle reply to a message (media or text)
    if update.message.reply_to_message:
        reply = update.message.reply_to_message
        
        # Check for media first
        media_file_id = None
        media_type = None
        
        if reply.photo: 
            media_file_id = reply.photo[-1].file_id
            media_type = "photo"
        elif reply.video: 
            media_file_id = reply.video.file_id
            media_type = "video"
        elif reply.animation: 
            media_file_id = reply.animation.file_id
            media_type = "gif"
        elif reply.document: 
            media_file_id = reply.document.file_id
            media_type = "document"
        elif reply.sticker: 
            media_file_id = reply.sticker.file_id
            media_type = "sticker"
        
        if media_file_id:
            if add_blocked_content(chat_id, "media", media_file_id):
                await send_bot_response(update, context, f"✅ Blocked this {media_type} successfully.")
            else:
                await send_bot_response(update, context, f"ℹ️ This {media_type} is already blocked.")
            return
            
        # If no media, check for text
        if reply.text:
            if add_blocked_content(chat_id, "text", reply.text):
                await send_bot_response(update, context, f"✅ Blocked the text: '{reply.text[:50]}...'")
            else:
                await send_bot_response(update, context, "ℹ️ This text is already blocked.")
            return

    # 2. Handle arguments (words or sentences)
    if context.args:
        text_to_block = " ".join(context.args)
        if add_blocked_content(chat_id, "text", text_to_block):
            await send_bot_response(update, context, f"✅ Blocked the content: '{text_to_block}'")
        else:
            await send_bot_response(update, context, "ℹ️ This content is already blocked.")
        return

    await send_bot_response(update, context, "Usage: Reply to a message with /block or use `/block <text>` to block content.")

async def unblock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to unblock content."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if user_id != OWNER_ID and not await is_user_admin(chat_id, user_id, context):
        return

    # Handle reply
    if update.message.reply_to_message:
        reply = update.message.reply_to_message
        media_file_id = None
        if reply.photo: media_file_id = reply.photo[-1].file_id
        elif reply.video: media_file_id = reply.video.file_id
        elif reply.animation: media_file_id = reply.animation.file_id
        elif reply.document: media_file_id = reply.document.file_id
        elif reply.sticker: media_file_id = reply.sticker.file_id
        
        if media_file_id:
            if remove_blocked_content(chat_id, "media", media_file_id):
                await send_bot_response(update, context, "✅ Unblocked this media.")
            else:
                await send_bot_response(update, context, "❌ This media is not in the block list.")
            return
            
        if reply.text:
            if remove_blocked_content(chat_id, "text", reply.text):
                await send_bot_response(update, context, f"✅ Unblocked: '{reply.text[:50]}...'")
            else:
                await send_bot_response(update, context, "❌ This text is not in the block list.")
            return

    # Handle arguments
    if context.args:
        text_to_unblock = " ".join(context.args)
        if remove_blocked_content(chat_id, "text", text_to_unblock):
            await send_bot_response(update, context, f"✅ Unblocked: '{text_to_unblock}'")
        else:
            await send_bot_response(update, context, "❌ This content is not in the block list.")
        return

    await send_bot_response(update, context, "Usage: Reply to a message with /unblock or use `/unblock <text>`.")

async def list_blocked_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists all blocked text content in the chat."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if user_id != OWNER_ID and not await is_user_admin(chat_id, user_id, context):
        return

    blocked = get_blocked_content(chat_id)
    text_list = blocked.get("text", [])
    
    if not text_list:
        await send_bot_response(update, context, "No text content is blocked in this group.")
        return
        
    response = "🚫 **Blocked Content List:**\n\n"
    for i, item in enumerate(text_list, 1):
        response += f"{i}. `{item}`\n"
    
    await send_bot_response(update, context, response, parse_mode=ParseMode.MARKDOWN)

async def check_blocked_content_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """MessageHandler to check every message for blocked content."""
    if not update.message or not update.effective_chat:
        return
        
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Skip admins and owner
    if user_id == OWNER_ID or await is_user_admin(chat_id, user_id, context):
        return

    is_blocked, reason = is_content_blocked(chat_id, update.message)
    
    if is_blocked:
        settings = get_chat_settings(chat_id)
        
        # Action settings
        limit = settings.get("block_warn_limit", 3)
        penalty = settings.get("block_warn_penalty", "warn") # warn, mute, ban, kick
        
        # Delete the message first
        try:
            await update.message.delete()
        except Exception as e:
            logging.error(f"Failed to delete blocked content: {e}")

        # Apply penalty
        if penalty == "warn":
            current_warns = add_warn(chat_id, user_id)
            if current_warns >= limit:
                reset_warns(chat_id, user_id)
                # Apply secondary penalty if limit reached (default to ban)
                await context.bot.ban_chat_member(chat_id, user_id)
                await context.bot.send_message(
                    chat_id, 
                    f"🚫 {update.effective_user.first_name} has been banned for repeatedly using blocked content ({limit}/{limit})."
                )
            else:
                await context.bot.send_message(
                    chat_id, 
                    f"⚠️ {update.effective_user.first_name}, that content is blocked here. Warning {current_warns}/{limit}."
                )
        elif penalty == "mute":
            await context.bot.restrict_chat_member(chat_id, user_id, permissions=ChatPermissions(can_send_messages=False))
            await context.bot.send_message(chat_id, f"🔇 {update.effective_user.first_name} has been muted for using blocked content.")
        elif penalty == "ban":
            await context.bot.ban_chat_member(chat_id, user_id)
            await context.bot.send_message(chat_id, f"🚫 {update.effective_user.first_name} has been banned for using blocked content.")
        elif penalty == "kick":
            await context.bot.ban_chat_member(chat_id, user_id)
            await context.bot.unban_chat_member(chat_id, user_id)
            await context.bot.send_message(chat_id, f"👞 {update.effective_user.first_name} has been kicked for using blocked content.")
        return

    # Check message length
    settings = get_chat_settings(chat_id)
    length_limit = settings.get("msg_length_limit", 0)
    if length_limit > 0 and update.message.text:
        if len(update.message.text) > length_limit:
            try:
                await update.message.delete()
                await context.bot.send_message(
                    chat_id,
                    f"📏 {update.effective_user.first_name}, your message is too long (>{length_limit} chars) and was deleted."
                )
            except Exception as e:
                logging.error(f"Failed to delete long message: {e}")

def get_block_content_handlers():
    return [
        CommandHandler("block", block_command),
        CommandHandler("unblock", unblock_command),
        CommandHandler("listblock", list_blocked_command),
        # MessageHandler to catch all messages (text and media)
        MessageHandler(filters.ALL & ~filters.COMMAND & filters.ChatType.GROUPS, check_blocked_content_handler)
    ]
