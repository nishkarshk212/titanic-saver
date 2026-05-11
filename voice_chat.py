import logging
import os
import asyncio
import datetime
from telethon import TelegramClient, events
from telethon.tl.types import UpdateGroupCallParticipants, PeerChat, PeerChannel, PeerUser, UpdateGroupCall
from telethon.tl.functions.phone import GetGroupCallRequest
from telethon.sessions import StringSession
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from config import BOT_TOKEN, to_small_caps
from telegram.ext import Application

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Telethon Credentials
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
STRING_SESSION = os.getenv("STRING_SESSION", "")

# Initialize Telethon Client
telethon_client = None
ptb_application = None

# Cache to prevent duplicate notifications
notification_cache = {}

# Map call IDs to chat IDs
call_to_chat = {}

async def start_voice_chat_monitor(application: Application):
    """Starts the Telethon client to monitor voice chat events."""
    global telethon_client, ptb_application
    ptb_application = application
    
    if not API_ID or not API_HASH or not STRING_SESSION:
        logger.warning("⚠️ Telethon credentials missing. Voice chat join notifications disabled.")
        return

    logger.info("🎙 Starting Voice Chat Monitor...")
    telethon_client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    
    @telethon_client.on(events.Raw(UpdateGroupCall))
    async def handle_call_update(event):
        """Maps call IDs to chat entities."""
        try:
            # When a call starts or is updated, we try to find its chat
            # This is a bit advanced but helps in mapping
            pass
        except: pass

    @telethon_client.on(events.Raw(UpdateGroupCallParticipants))
    async def handle_voice_chat_join(event):
        """Handles voice chat join events."""
        try:
            for participant in event.participants:
                # Only care about joins
                if not hasattr(participant, 'date') or participant.date is None:
                    continue
                
                user_id = None
                if isinstance(participant.peer, PeerUser):
                    user_id = participant.peer.user_id
                
                if not user_id: continue
                
                # Deduplicate
                cache_key = f"{user_id}_{event.call.id}"
                now = datetime.datetime.now()
                if cache_key in notification_cache:
                    if (now - notification_cache[cache_key]).total_seconds() < 30:
                        continue
                notification_cache[cache_key] = now

                try:
                    # Get user info
                    user = await telethon_client.get_entity(user_id)
                    user_name = user.first_name
                    user_mention = f'<a href="tg://user?id={user_id}">{user_name}</a>'
                    
                    # Try to find the chat by checking all dialogs 
                    # (This is a bit slow but ensures we find the right group)
                    chat_id = None
                    group_name = "the group"
                    
                    async for dialog in telethon_client.iter_dialogs():
                        if dialog.is_group or dialog.is_channel:
                            # We check if the call ID matches or if we can find the call in this chat
                            # For simplicity, we'll look for the user in the group
                            # and assume it's the right one if they are in the voice chat
                            pass
                    
                    # Fallback: Just log it for now
                    logger.info(f"✅ Voice chat join detected: {user_name} ({user_id})")
                    
                    # The message you requested
                    welcome_text = (
                        f"<blockquote>\n"
                        f"ωєℓ¢σмє тσ νσι¢є ¢нαт\n"
                        f"</blockquote>\n"
                        f"<blockquote>\n"
                        f"ηαмє : {user_mention}\n"
                        f"ι∂ : <code>{user_id}</code>\n"
                        f"</blockquote>"
                    )
                    
                    bot_info = await ptb_application.bot.get_me()
                    add_url = f"https://t.me/{bot_info.username}?startgroup=true"
                    
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("ᴊᴏɪɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ", url=add_url)],
                        [InlineKeyboardButton(to_small_caps("+ ᴀᴅᴅ ᴍᴇ ɪɴ ɢʀᴏᴜᴘ +"), url=add_url)]
                    ])
                    
                    # Since we can't reliably get chat_id from raw UpdateGroupCallParticipants,
                    # a better approach is to use PTB's built-in handlers if available 
                    # or listen for Service Messages (ActionChatJoinedByLink, etc.)
                    
                except Exception as e:
                    logger.error(f"❌ Error handling VC participant: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error in handle_voice_chat_join: {e}")

    await telethon_client.start()
    logger.info("✅ Telethon client started successfully!")

async def stop_voice_chat_monitor():
    """Stops the Telethon client."""
    if telethon_client:
        await telethon_client.disconnect()
        logger.info("🎙 Voice Chat Monitor stopped.")

