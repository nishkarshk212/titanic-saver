import logging
import os
import asyncio
import datetime
from telethon import TelegramClient, events
from telethon.tl.types import UpdateGroupCallParticipants, PeerChat, PeerChannel, PeerUser
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

async def start_voice_chat_monitor(application: Application):
    """Starts the Telethon client to monitor voice chat events."""
    global telethon_client, ptb_application
    ptb_application = application
    
    if not API_ID or not API_HASH or not STRING_SESSION:
        logger.warning("⚠️ Telethon credentials missing. Voice chat join notifications disabled.")
        return

    logger.info("🎙 Starting Voice Chat Monitor...")
    telethon_client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    
    @telethon_client.on(events.Raw(UpdateGroupCallParticipants))
    async def handle_voice_chat_join(event):
        """Handles voice chat join events."""
        try:
            # We need to find the chat_id. Telethon's UpdateGroupCallParticipants 
            # doesn't directly give chat_id. We try to get it from the call.
            try:
                full_call = await telethon_client(GetGroupCallRequest(call=event.call))
                # In many cases, the chat_id can be derived from the call's peer
                # or we can look up which chat this call belongs to.
                # This is complex in raw Telethon, so we'll try a different approach.
                pass
            except: pass

            for participant in event.participants:
                # We only care about users who just joined (have a date)
                if not hasattr(participant, 'date') or participant.date is None:
                    continue
                
                # Prevent duplicate notifications (cache for 10 seconds)
                user_id = None
                if isinstance(participant.peer, PeerUser):
                    user_id = participant.peer.user_id
                
                if not user_id: continue
                
                cache_key = f"{user_id}_{event.call.id}"
                now = datetime.datetime.now()
                if cache_key in notification_cache:
                    if (now - notification_cache[cache_key]).total_seconds() < 10:
                        continue
                notification_cache[cache_key] = now

                try:
                    user = await telethon_client.get_entity(user_id)
                    user_name = user.first_name
                    user_mention = f'<a href="tg://user?id={user_id}">{user_name}</a>'
                    
                    # We need to find the chat where this happened.
                    # Since we can't easily get it from the event, we'll try to find 
                    # the chat by searching through recent dialogs or using a placeholder.
                    # A better way is to use a specific event that includes the chat.
                    
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
                    
                    # Log the join. Sending the message requires a chat_id.
                    # For now, we'll log it and you should see it in your logs.
                    logger.info(f"✅ Voice chat join: {user_name} ({user_id})")
                    
                    # If you want the bot to send the message, we MUST have the chat_id.
                    # One way to get it is to have the bot be an admin and receive 
                    # service messages, or use a more advanced Telethon listener.
                    
                except Exception as e:
                    logger.error(f"❌ Error handling participant: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error in handle_voice_chat_join: {e}")

    await telethon_client.start()
    logger.info("✅ Telethon client started successfully!")

async def stop_voice_chat_monitor():
    """Stops the Telethon client."""
    if telethon_client:
        await telethon_client.disconnect()
        logger.info("🎙 Voice Chat Monitor stopped.")
