import logging
import os
import asyncio
import datetime
from telethon import TelegramClient, events
from telethon.tl.types import UpdateGroupCallParticipants, PeerChat, PeerChannel, PeerUser, UpdateGroupCall
from telethon.tl.functions.phone import GetGroupCallRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest
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

# Map call IDs to chat entities
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
    
    @telethon_client.on(events.Raw(UpdateGroupCallParticipants))
    async def handle_voice_chat_join(event):
        """Handles voice chat join events."""
        try:
            # We need to find the chat_id. 
            # We'll try to find it by checking if we have mapped this call ID before.
            chat_entity = call_to_chat.get(event.call.id)
            
            # If not mapped, try to find it by searching active dialogs
            if not chat_entity:
                async for dialog in telethon_client.iter_dialogs(limit=20):
                    if dialog.is_group or dialog.is_channel:
                        # For groups/channels, we can check if they have an active call
                        try:
                            full = await telethon_client(
                                GetFullChannelRequest(channel=dialog.entity) if dialog.is_channel 
                                else GetFullChatRequest(chat_id=dialog.id)
                            )
                            if hasattr(full, 'full_chat') and hasattr(full.full_chat, 'call'):
                                if full.full_chat.call and full.full_chat.call.id == event.call.id:
                                    chat_entity = dialog.entity
                                    call_to_chat[event.call.id] = chat_entity
                                    break
                        except: continue

            for participant in event.participants:
                # Only care about joins (those with a date)
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
                    if (now - notification_cache[cache_key]).total_seconds() < 60:
                        continue
                notification_cache[cache_key] = now

                try:
                    # Get user info
                    user = await telethon_client.get_entity(user_id)
                    user_name = user.first_name
                    user_mention = f'<a href="tg://user?id={user_id}">{user_name}</a>'
                    
                    group_name = chat_entity.title if chat_entity and hasattr(chat_entity, 'title') else "the group"
                    chat_id = chat_entity.id if chat_entity else None
                    
                    # Convert Telethon ID to PTB ID if it's a channel
                    if chat_id and isinstance(chat_entity, PeerChannel) or (str(chat_id).startswith('-100') == False and chat_id > 0 and getattr(chat_entity, 'broadcast', False) or getattr(chat_entity, 'megagroup', False)):
                        if not str(chat_id).startswith('-100'):
                            chat_id = int(f"-100{chat_id}")

                    # If we don't have a chat_id, we can't send the message
                    if not chat_id:
                        logger.warning(f"⚠️ VC join detected for {user_name} but could not resolve chat_id.")
                        continue

                    welcome_text = (
                        f"<blockquote>\n"
                        f"ωєℓ¢σмє тσ {group_name}'s νσι¢є ¢нαт\n"
                        f"</blockquote>\n"
                        f"<blockquote>\n"
                        f"ηαмє : {user_mention}\n"
                        f"ι∂ : <code>{user_id}</code>\n"
                        f"</blockquote>"
                    )
                    
                    bot_info = await ptb_application.bot.get_me()
                    add_url = f"https://t.me/{bot_info.username}?startgroup=true"
                    
                    # Try to get group link
                    vc_link = add_url
                    if hasattr(chat_entity, 'username') and chat_entity.username:
                        vc_link = f"https://t.me/{chat_entity.username}"
                    
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("ᴊᴏɪɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ", url=vc_link)],
                        [InlineKeyboardButton(to_small_caps("+ ᴀᴅᴅ ᴍᴇ ɪɴ ɢʀᴏᴜᴘ +"), url=add_url)]
                    ])
                    
                    # Send via PTB application
                    await ptb_application.bot.send_message(
                        chat_id=chat_id,
                        text=welcome_text,
                        reply_markup=keyboard,
                        parse_mode=ParseMode.HTML
                    )
                    logger.info(f"✅ Voice chat join notification sent for {user_name} in {group_name} ({chat_id})")
                    
                except Exception as e:
                    logger.error(f"❌ Error sending VC notification: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error in handle_voice_chat_join: {e}")

    await telethon_client.start()
    logger.info("✅ Telethon client started successfully!")

async def stop_voice_chat_monitor():
    """Stops the Telethon client."""
    if telethon_client:
        await telethon_client.disconnect()
        logger.info("🎙 Voice Chat Monitor stopped.")
