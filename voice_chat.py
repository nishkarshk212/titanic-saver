import logging
import os
import asyncio
from telethon import TelegramClient, events
from telethon.tl.types import UpdateGroupCallParticipants
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
            # Check for new participants
            for participant in event.participants:
                # We only care about joining (active)
                if not hasattr(participant, 'date'): continue
                
                user_id = participant.peer.user_id
                
                # Get chat and user details
                try:
                    chat_peer = await telethon_client.get_input_entity(event.call.access_hash)
                    chat = await telethon_client.get_entity(chat_peer)
                    user = await telethon_client.get_entity(user_id)
                    
                    group_name = chat.title
                    user_name = user.first_name
                    user_mention = f'<a href="tg://user?id={user_id}">{user_name}</a>'
                    
                    # Prepare the message
                    welcome_text = (
                        f"<blockquote>"
                        f"ωєℓ¢σмє тσ {group_name}'s νσι¢є ¢нαт"
                        f"</blockquote>\n"
                        f"<blockquote>"
                        f"ηαмє : {user_mention}\n"
                        f"ι∂ : <code>{user_id}</code>"
                        f"</blockquote>"
                    )
                    
                    # Add to group button
                    bot_info = await ptb_application.bot.get_me()
                    add_url = f"https://t.me/{bot_info.username}?startgroup=true"
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton(to_small_caps("+ ᴀᴅᴅ ᴍᴇ ɪɴ ɢʀᴏᴜᴘ +"), url=add_url)]
                    ])
                    
                    # Send via PTB application
                    await ptb_application.bot.send_message(
                        chat_id=chat.id,
                        text=welcome_text,
                        reply_markup=keyboard,
                        parse_mode=ParseMode.HTML
                    )
                    logger.info(f"✅ Voice chat join notification sent for {user_name} in {group_name}")
                    
                except Exception as e:
                    logger.error(f"❌ Error fetching details for voice join: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error in handle_voice_chat_join: {e}")

    await telethon_client.start()
    logger.info("✅ Telethon client started successfully!")

async def stop_voice_chat_monitor():
    """Stops the Telethon client."""
    if telethon_client:
        await telethon_client.disconnect()
        logger.info("🎙 Voice Chat Monitor stopped.")
