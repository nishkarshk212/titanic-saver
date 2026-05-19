import logging
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, ChatMemberHandler
import os
from config import OWNER_ID, log_to_channel
from settings_manager_mongo import get_chat_settings, update_chat_setting
from user_manager_mongo import cache_user

def format_welcome_message(text, user, chat):
    """Formats the welcome message with dynamic placeholders."""
    now = datetime.datetime.now()
    
    # Placeholders dictionary
    # Use HTML for mentions to preserve formatting if the text is HTML
    mention_html = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
    
    placeholders = {
        "{ID}": str(user.id),
        "{NAME}": (user.first_name or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"),
        "{SURNAME}": (user.last_name or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"),
        "{NAMESURNAME}": f"{(user.first_name or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')} {(user.last_name or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')}".strip(),
        "{LANG}": user.language_code or "Unknown",
        "{DATE}": now.strftime("%Y-%m-%d"),
        "{TIME}": now.strftime("%H:%M:%S"),
        "{WEEKDAY}": now.strftime("%A"),
        "{MENTION}": mention_html,
        "{USERNAME}": f"@{user.username}" if user.username else "No Username",
        "{GROUPNAME}": (chat.title or "this group").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"),
        "{RULES}": "/rules" 
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

    # Check if this is a reply to a message
    if update.message.reply_to_message:
        reply = update.message.reply_to_message
        
        # We MUST use text_html to capture premium emojis as <tg-emoji> tags
        if reply.text_html:
            welcome_text = reply.text_html
        elif reply.caption_html:
            welcome_text = reply.caption_html
        else:
            await update.message.reply_text("❌ The replied message doesn't have any text to set as welcome.")
            return
            
        # Also check for media in the replied message
        if reply.photo:
            update_chat_setting(chat_id, "welcome_media", reply.photo[-1].file_id)
            update_chat_setting(chat_id, "welcome_media_type", "photo")
            update_chat_setting(chat_id, "welcome_media_enabled", True)
        elif reply.video:
            update_chat_setting(chat_id, "welcome_media", reply.video.file_id)
            update_chat_setting(chat_id, "welcome_media_type", "video")
            update_chat_setting(chat_id, "welcome_media_enabled", True)
        elif reply.animation:
            update_chat_setting(chat_id, "welcome_media", reply.animation.file_id)
            update_chat_setting(chat_id, "welcome_media_type", "animation")
            update_chat_setting(chat_id, "welcome_media_enabled", True)
            
    else:
        # Fallback to the text after the command
        text = update.message.text_html.split(" ", 1)
        if len(text) < 2:
            await update.message.reply_text("Usage: /setwelcome <text> OR reply to a message with /setwelcome")
            return
        welcome_text = text[1]

    # Save to database
    update_chat_setting(chat_id, "welcome_text", welcome_text)
    await update.message.reply_text("✅ Welcome message updated! Premium Emojis and Quote blocks are now fully supported via HTML tags.")

async def set_welcome_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set the welcome message photo."""
    if not update.message or not update.message.reply_to_message:
        await update.message.reply_text("Please reply to a photo, video, or animation message with /setphoto to set the welcome media.")
        return

    # Check admin or owner
    sender_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if sender_id != OWNER_ID:
        member = await context.bot.get_chat_member(chat_id, sender_id)
        if member.status not in ['administrator', 'creator']:
            await update.message.reply_text("Admin only command.")
            return

    reply = update.message.reply_to_message
    if reply.photo:
        media_id = reply.photo[-1].file_id
        media_type = "photo"
    elif reply.video:
        media_id = reply.video.file_id
        media_type = "video"
    elif reply.animation:
        media_id = reply.animation.file_id
        media_type = "animation"
    else:
        await update.message.reply_text("❌ Please reply to a photo, video, or animation.")
        return

    update_chat_setting(chat_id, "welcome_media", media_id)
    update_chat_setting(chat_id, "welcome_media_type", media_type)
    update_chat_setting(chat_id, "welcome_media_enabled", True)
    await update.message.reply_text(f"✅ Welcome {media_type} updated and enabled!")

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
    welcome_text_html = settings.get('welcome_text', "Welcome {NAME} to the group!")
    personal_welcome = format_welcome_message(welcome_text_html, user, chat)
    
    # Try to delete the previous welcome message
    if settings.get("welcome_clean_enabled", True):
        last_welcome_id = settings.get('last_welcome_id')
        if last_welcome_id:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=last_welcome_id)
            except Exception:
                pass # Message might be already deleted or too old

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

    # Save the new welcome message ID to delete it later
    if msg:
        update_chat_setting(chat_id, "last_welcome_id", msg.message_id)
    
    # Schedule deletion if msg sent, enabled, and time > 0
    if msg and settings.get("welcome_delete_enabled", True) and welcome_delete_time > 0 and context.job_queue:
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
    chat_id = update.effective_chat.id
    settings = get_chat_settings(chat_id)
    
    # Debug log
    logging.info(f"Chat Member Update in {chat_id}: {old_status} -> {new_status} for user {result.new_chat_member.user.id}")
    
    # Check if the bot itself was added or its status changed
    if result.new_chat_member.user.id == context.bot.id:
        if new_status in ['member', 'administrator']:
            from admin_manager_mongo import sync_admins
            await sync_admins(chat_id, context)
            logging.info(f"Bot joined or refreshed in chat {chat_id}, synced admins.")
            
            # Apply group settings like reaction blocking
            if settings.get("block_reactions", False):
                try:
                    await context.bot.set_chat_available_reactions(chat_id, reactions=[])
                    logging.info(f"Reactions for chat {chat_id} blocked on bot join.")
                except: pass
    
    # Active statuses that should receive a welcome message
    active_statuses = ['member', 'administrator', 'restricted']
    
    # Non-active statuses from which a user can "join"
    inactive_statuses = ['left', 'kicked', 'none']

    # Trigger welcome if moving from inactive to active
    is_joining = new_status in active_statuses and old_status in inactive_statuses
    
    if is_joining:
        member = result.new_chat_member.user
        if member.is_bot:
            return
            
        # If it's a rejoin (was previously left or kicked), check the rejoin setting
        if old_status in ['left', 'kicked']:
            if not settings.get("welcome_rejoin_enabled", True):
                logging.info(f"Skipping welcome for re-joining user {member.id} in {chat_id} as welcome_rejoin_enabled is False")
                return
        
        await send_welcome(update.effective_chat, member, context)

def get_welcome_handlers():
    """Return handlers for welcome message."""
    return [
        CommandHandler("setwelcome", set_welcome),
        CommandHandler("setphoto", set_welcome_photo),
        CommandHandler("setbutton", set_welcome_button),
        # Handle status changes (detects joins and re-joins reliably)
        ChatMemberHandler(on_chat_member_update, ChatMemberHandler.CHAT_MEMBER)
    ]
