import logging
import asyncio
import re
from config import colored_button
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import ContextTypes, MessageHandler, filters
from settings_manager_mongo import get_chat_settings
from moderation_manager_mongo import get_user_warns, add_warn, reset_warns
from user_manager_mongo import is_user_admin
from moderation import mute_user, kick_user, ban_user
from telegram.error import BadRequest
from config import delete_message_job

# URL Regex to detect links and usernames in bio
URL_PATTERN = re.compile(r'(https?://\S+|www\.\S+|t\.me\S*|@\w+|[\w-]+\.(com|net|org|me|info|biz|io|co|xyz|top|link|tk|ga|ml|cf|gq))', re.IGNORECASE)

# Cache to avoid repeated API calls (user_id -> timestamp)
# Bio doesn't change per chat, so we can cache per user globally
bio_check_cache = {}

async def get_telethon_client():
    """Import and return telethon_client from voice_chat."""
    try:
        from voice_chat import telethon_client
        return telethon_client
    except ImportError:
        return None

async def check_user_bio(user_id):
    """Checks user bio for links using Telethon."""
    client = await get_telethon_client()
    if not client:
        return False, None
        
    # Don't try to connect here, it should be handled in voice_chat.py
    if not client.is_connected():
        # logging.debug("Telethon client not connected")
        return False, None
    
    try:
        from telethon.tl.functions.users import GetFullUserRequest
        # Use a timeout for Telethon calls to prevent "stuck" behavior
        async def fetch_bio():
            # Ensure we have the entity from cache if possible
            try:
                # Telethon can usually handle user_id directly if it has seen the user
                full_user = await client(GetFullUserRequest(user_id))
                return full_user.full_user.about
            except Exception as e:
                # If it hasn't seen the user, try to get entity first
                try:
                    entity = await client.get_entity(user_id)
                    full_user = await client(GetFullUserRequest(entity))
                    return full_user.full_user.about
                except:
                    raise e

        bio = await asyncio.wait_for(fetch_bio(), timeout=5.0)
        # logging.info(f"Bio found for {user_id}: {bio}")
        
        if bio:
            match = URL_PATTERN.search(bio)
            if match:
                logging.info(f"🚨 Bio Link detected for {user_id}: {match.group(0)}")
                return True, bio
    except asyncio.TimeoutError:
        logging.warning(f"Timeout checking bio for {user_id}")
    except Exception as e:
        if "Could not find the input entity" not in str(e) and "User not found" not in str(e):
            logging.error(f"Error checking bio for {user_id}: {e}")
    
    return False, None

async def apply_bio_penalty(update: Update, context, user_id: int, bio: str):
    """Applies the configured penalty for having a link in bio."""
    chat_id = update.effective_chat.id
    settings = get_chat_settings(chat_id)
    
    penalty = settings.get("bio_link_penalty", "warn").lower()
    if penalty == "off":
        return

    # Show only user ID as requested
    user_id_str = f"<code>{user_id}</code>"

    limit = settings.get("bio_link_warn_limit", 3)
    current_warns = add_warn(chat_id, user_id)
    
    keyboard = [
        [
            InlineKeyboardButton(colored_button("➕ Add Warn", "red"), callback_data=f"edit_warn_add_{user_id}"),
            InlineKeyboardButton(colored_button("🔄 Reset Warns", "green"), callback_data=f"edit_warn_reset_{user_id}")
        ]
    ]
    
    bot = context.bot if hasattr(context, 'bot') else context
    
    msg_text = ""
    if current_warns >= limit:
        reset_warns(chat_id, user_id)
        
        if penalty == "mute" or penalty == "warn":
            try:
                await bot.restrict_chat_member(chat_id, user_id, permissions=ChatPermissions(can_send_messages=False))
                keyboard.insert(0, [InlineKeyboardButton(colored_button("🔊 Unmute", "green"), callback_data=f"edit_unmute_{user_id}")])
                msg_text = f"🚫 User {user_id_str} has been muted for reaching the warn limit (Link in bio)."
            except Exception as e:
                logging.error(f"Failed to mute user in bio check: {e}")
                msg_text = f"⚠️ User {user_id_str}, links are not allowed in your bio! ({current_warns}/{limit})"
        elif penalty == "kick":
            try:
                await bot.ban_chat_member(chat_id, user_id)
                await bot.unban_chat_member(chat_id, user_id)
                msg_text = f"👢 User {user_id_str} has been kicked for reaching the warn limit (Link in bio)."
            except Exception as e:
                logging.error(f"Failed to kick user in bio check: {e}")
                msg_text = f"⚠️ User {user_id_str}, links are not allowed in your bio! ({current_warns}/{limit})"
        elif penalty == "ban":
            try:
                await bot.ban_chat_member(chat_id, user_id)
                msg_text = f"🔨 User {user_id_str} has been banned for reaching the warn limit (Link in bio)."
            except Exception as e:
                logging.error(f"Failed to ban user in bio check: {e}")
                msg_text = f"⚠️ User {user_id_str}, links are not allowed in your bio! ({current_warns}/{limit})"
    else:
        msg_text = f"⚠️ User {user_id_str}, links are not allowed in your bio! ({current_warns}/{limit})\nPlease remove it to avoid further penalties."

    try:
        sent_msg = await bot.send_message(
            chat_id=chat_id,
            text=msg_text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Auto delete warning message after custom time (default 5 minutes)
        warn_delete_time = settings.get("warning_delete_time", 300)
        
        # If we have a job_queue, use it
        job_queue = getattr(context, 'job_queue', None)
        if job_queue:
            job_queue.run_once(
                delete_message_job,
                warn_delete_time,
                data={"chat_id": chat_id, "message_id": sent_msg.message_id}
            )
        else:
            # Fallback for when we don't have job_queue (e.g. called from voice_chat.py with ptb_application)
            async def fallback_delete():
                await asyncio.sleep(warn_delete_time)
                try: await bot.delete_message(chat_id, sent_msg.message_id)
                except: pass
            asyncio.create_task(fallback_delete())
            
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

    # Check target (members, admin, everyone)
    target = settings.get("bio_link_target", "members").lower()
    is_admin = await is_user_admin(chat_id, user_id, context)
    
    if target == "members" and is_admin:
        return
    elif target == "admin" and not is_admin:
        return
    # if target is "everyone", we don't return early

    # Run the check in the background to not block the main message loop
    async def run_background_check():
        try:
            # Small delay to ensure Telethon has a chance to "see" the user
            await asyncio.sleep(0.5)
            has_link, bio = await check_user_bio(user_id)
            if has_link:
                # If bio link detected, delete the triggering message immediately if it exists
                if update.message:
                    try:
                        await update.message.delete()
                    except Exception as e:
                        logging.error(f"Failed to delete message after bio link detection: {e}")
                
                await apply_bio_penalty(update, context, user_id, bio)
        except Exception as e:
            logging.error(f"Error in background bio check for {user_id}: {e}")
            
    asyncio.create_task(run_background_check())

def get_bio_handlers():
    """Returns the bio link message handler."""
    return [
        MessageHandler(filters.ChatType.GROUPS & (~filters.COMMAND), bio_link_message_handler)
    ]
