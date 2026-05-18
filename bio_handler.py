import logging
import asyncio
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import ContextTypes, MessageHandler, filters
from settings_manager_mongo import get_chat_settings
from moderation_manager_mongo import get_user_warns, add_warn, reset_warns
from user_manager_mongo import is_user_admin
from moderation import mute_user, kick_user, ban_user
from telegram.error import BadRequest
from config import delete_message_job

# URL Regex to detect links in bio
URL_PATTERN = re.compile(r'https?://\S+|www\.\S+|t\.me/\S+|@\S+')

# Cache to avoid repeated API calls to check bios (chat_id -> user_id -> timestamp)
bio_check_cache = {}

async def get_telethon_client():
    """Import and return telethon_client from voice_chat."""
    from voice_chat import telethon_client
    return telethon_client

async def check_user_bio(user_id):
    """Checks user bio for links using Telethon."""
    client = await get_telethon_client()
    if not client or not client.is_connected():
        logging.warning("Telethon client not available for bio check")
        return False, None
    
    try:
        from telethon.tl.functions.users import GetFullUserRequest
        full_user = await client(GetFullUserRequest(user_id))
        bio = full_user.full_user.about
        if bio and URL_PATTERN.search(bio):
            return True, bio
    except Exception as e:
        if "Could not find the input entity" not in str(e):
            logging.error(f"Error checking bio for {user_id}: {e}")
    
    return False, None

async def apply_bio_penalty(update: Update, context, user_id: int, bio: str):
    """Applies the configured penalty for having a link in bio."""
    chat_id = update.effective_chat.id
    settings = get_chat_settings(chat_id)
    
    penalty = settings.get("bio_link_penalty", "warn").lower()
    if penalty == "off":
        return

    # Use mention_html() if update.effective_user matches user_id, else try to get from context
    if update.effective_user and update.effective_user.id == user_id:
        user_mention = update.effective_user.mention_html()
    else:
        try:
            # Check if context has bot attribute (PTB Application or Context)
            bot = context.bot if hasattr(context, 'bot') else context
            member = await bot.get_chat_member(chat_id, user_id)
            user_mention = member.user.mention_html()
        except:
            user_mention = f"User {user_id}"

    limit = settings.get("bio_link_warn_limit", 3)
    current_warns = add_warn(chat_id, user_id)
    
    keyboard = [
        [
            InlineKeyboardButton("➕ Add Warn", callback_data=f"edit_warn_add_{user_id}"),
            InlineKeyboardButton("🔄 Reset Warns", callback_data=f"edit_warn_reset_{user_id}")
        ]
    ]
    
    bot = context.bot if hasattr(context, 'bot') else context
    
    msg_text = ""
    if current_warns >= limit:
        reset_warns(chat_id, user_id)
        
        if penalty == "mute" or penalty == "warn":
            # We need update and context for mute_user, but we can call context.bot.restrict_chat_member directly
            try:
                await bot.restrict_chat_member(chat_id, user_id, permissions=ChatPermissions(can_send_messages=False))
                keyboard.insert(0, [InlineKeyboardButton("🔊 Unmute", callback_data=f"edit_unmute_{user_id}")])
                msg_text = f"🚫 {user_mention} has been muted for reaching the warn limit (Link in bio)."
            except Exception as e:
                logging.error(f"Failed to mute user in bio check: {e}")
                msg_text = f"⚠️ {user_mention}, links are not allowed in your bio! ({current_warns}/{limit})"
        elif penalty == "kick":
            try:
                await bot.ban_chat_member(chat_id, user_id)
                await bot.unban_chat_member(chat_id, user_id)
                msg_text = f"👢 {user_mention} has been kicked for reaching the warn limit (Link in bio)."
            except Exception as e:
                logging.error(f"Failed to kick user in bio check: {e}")
                msg_text = f"⚠️ {user_mention}, links are not allowed in your bio! ({current_warns}/{limit})"
        elif penalty == "ban":
            try:
                await bot.ban_chat_member(chat_id, user_id)
                msg_text = f"🔨 {user_mention} has been banned for reaching the warn limit (Link in bio)."
            except Exception as e:
                logging.error(f"Failed to ban user in bio check: {e}")
                msg_text = f"⚠️ {user_mention}, links are not allowed in your bio! ({current_warns}/{limit})"
    else:
        msg_text = f"⚠️ {user_mention}, links are not allowed in your bio! ({current_warns}/{limit})\nPlease remove it to avoid further penalties."

    try:
        sent_msg = await bot.send_message(
            chat_id=chat_id,
            text=msg_text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Auto delete warning message after 10 seconds
        # If we have a job_queue, use it
        job_queue = getattr(context, 'job_queue', None)
        if job_queue:
            job_queue.run_once(
                delete_message_job,
                10,
                data={"chat_id": chat_id, "message_id": sent_msg.message_id}
            )
        else:
            # Fallback for when we don't have job_queue (e.g. called from voice_chat.py with ptb_application)
            async def fallback_delete():
                await asyncio.sleep(10)
                try: await bot.delete_message(chat_id, sent_msg.message_id)
                except: pass
            asyncio.create_task(fallback_delete())
            
        # If it was a message that triggered this, try to delete it too
        if hasattr(update, 'message') and update.message:
            try:
                await update.message.delete()
            except: pass
            
    except Exception as e:
        logging.error(f"Error in apply_bio_penalty: {e}")

async def bio_link_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Checks bio link when a user sends a message."""
    if not update.effective_chat or not update.effective_user or update.effective_user.is_bot:
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    settings = get_chat_settings(chat_id)
    if not settings.get("bio_link_check_enabled", False):
        return

    # Skip admins
    if await is_user_admin(chat_id, user_id, context):
        return

    # Check cache (once every 1 hour per user per chat)
    now = asyncio.get_event_loop().time()
    user_cache = bio_check_cache.get(chat_id, {})
    last_check = user_cache.get(user_id, 0)
    if now - last_check < 3600:
        return
    
    user_cache[user_id] = now
    bio_check_cache[chat_id] = user_cache

    has_link, bio = await check_user_bio(user_id)
    if has_link:
        await apply_bio_penalty(update, context, user_id, bio)

def get_bio_handlers():
    """Returns the bio link message handler."""
    return [
        MessageHandler(filters.ChatType.GROUPS & (~filters.COMMAND), bio_link_message_handler)
    ]
