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
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from config import BOT_TOKEN, to_small_caps
from telegram.ext import Application, CallbackQueryHandler, ContextTypes
from settings_manager_mongo import get_chat_settings

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
    
    # Add callback handler for Join VC button
    application.add_handler(CallbackQueryHandler(vc_join_callback, pattern="^join_vc_"))
    
    if not API_ID or not API_HASH or not STRING_SESSION:
        logger.warning("⚠️ Telethon credentials missing. Voice chat join notifications disabled.")
        return

    logger.info("🎙 Starting Voice Chat Monitor...")
    telethon_client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    
    @telethon_client.on(events.Raw(UpdateGroupCallParticipants))
    async def handle_voice_chat_join(event):
        """Handles voice chat join events for Users and Channels."""
        try:
            chat_entity = call_to_chat.get(event.call.id)
            
            if not chat_entity:
                async for dialog in telethon_client.iter_dialogs(limit=20):
                    if dialog.is_group or dialog.is_channel:
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
                if not hasattr(participant, 'date') or participant.date is None:
                    continue
                
                peer = participant.peer
                user_id = None
                peer_type = "user"
                
                if isinstance(peer, PeerUser):
                    user_id = peer.user_id
                    peer_type = "user"
                elif isinstance(peer, PeerChannel):
                    user_id = peer.channel_id
                    peer_type = "channel"
                
                if not user_id: continue
                
                # Deduplicate
                cache_key = f"{user_id}_{event.call.id}"
                now = datetime.datetime.now()
                if cache_key in notification_cache:
                    if (now - notification_cache[cache_key]).total_seconds() < 60:
                        continue
                notification_cache[cache_key] = now

                try:
                    entity = await telethon_client.get_entity(peer)
                    name = getattr(entity, 'first_name', getattr(entity, 'title', "Unknown"))
                    
                    if peer_type == "channel":
                        mention = f'<a href="https://t.me/{entity.username}">{name}</a>' if getattr(entity, 'username', None) else f"<b>{name}</b>"
                    else:
                        mention = f'<a href="tg://user?id={user_id}">{name}</a>'
                    
                    group_name = chat_entity.title if chat_entity and hasattr(chat_entity, 'title') else "the group"
                    chat_id = chat_entity.id if chat_entity else None
                    
                    if not chat_id: continue

                    # Normalize chat_id for settings check (Telethon IDs for channels/supergroups need -100 prefix)
                    settings_chat_id = chat_id
                    if isinstance(chat_entity, PeerChannel) or (str(chat_id).startswith('-100') == False and chat_id > 0):
                        if not str(chat_id).startswith('-100'):
                            settings_chat_id = int(f"-100{chat_id}")

                    # Check if VC join notification is enabled for this chat
                    settings = get_chat_settings(settings_chat_id)
                    if not settings.get("vc_user_join_enabled", True):
                        logger.info(f"VC join notification disabled for {settings_chat_id}")
                        continue

                    # Update the local chat_id variable to the normalized one for sending messages
                    chat_id = settings_chat_id

                    welcome_text = (
                        f"<blockquote>\n"
                        f"ωєℓ¢σмє тσ {group_name}'s νσι¢є ¢нαт\n"
                        f"</blockquote>\n"
                        f"<blockquote>\n"
                        f"ι∂ : <code>{user_id}</code>\n"
                        f"</blockquote>"
                    )
                    
                    bot_info = await ptb_application.bot.get_me()
                    add_url = f"https://t.me/{bot_info.username}?startgroup=true"
                    
                    # Construct join link directly for the button
                    try:
                        # Get full chat info from bot to be sure about the username
                        chat_info = await ptb_application.bot.get_chat(chat_id)
                        if chat_info.username:
                            join_link = f"https://t.me/{chat_info.username}?videochat"
                        else:
                            clean_id = str(chat_id).replace("-100", "")
                            join_link = f"https://t.me/c/{clean_id}?videochat"
                    except Exception as e:
                        logger.warning(f"Failed to get chat info for join link: {e}")
                        # Fallback to chat_entity if bot call fails
                        if hasattr(chat_entity, 'username') and chat_entity.username:
                            join_link = f"https://t.me/{chat_entity.username}?videochat"
                        else:
                            clean_id = str(chat_id).replace("-100", "")
                            join_link = f"https://t.me/c/{clean_id}?videochat"
                    
                    logger.info(f"Generated VC join link for {chat_id}: {join_link}")
                    
                    # Button uses direct URL for faster joining
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("ᴊᴏɪɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ", url=join_link)],
                        [InlineKeyboardButton(to_small_caps("+ ᴀᴅᴅ ᴍᴇ ɪɴ ɢʀᴏᴜᴘ +"), url=add_url)]
                    ])
                    
                    sent_message = await ptb_application.bot.send_message(
                        chat_id=chat_id,
                        text=welcome_text,
                        reply_markup=keyboard,
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True
                    )
                    
                    # Auto delete after 1 minute
                    async def auto_delete_notification(chat_id, message_id):
                        await asyncio.sleep(60)
                        try:
                            await ptb_application.bot.delete_message(chat_id=chat_id, message_id=message_id)
                        except: pass
                    
                    asyncio.create_task(auto_delete_notification(chat_id, sent_message.message_id))
                    
                except Exception as e:
                    logger.error(f"❌ Error sending VC notification: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error in handle_voice_chat_join: {e}")

    await telethon_client.start()
    logger.info("✅ Telethon client started successfully!")

async def vc_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the 'Join Voice Chat' button click for old messages."""
    query = update.callback_query
    
    try:
        # Answer immediately to stop the spinning icon on the button
        await query.answer("Checking voice chat status...")
        
        data_parts = query.data.split("_")
        if len(data_parts) < 3:
            return
            
        chat_id = int(data_parts[2])
        
        # Construct the join link
        chat = await context.bot.get_chat(chat_id)
        if chat.username:
            join_link = f"https://t.me/{chat.username}?videochat"
        else:
            clean_id = str(chat_id).replace("-100", "")
            join_link = f"https://t.me/c/{clean_id}/1?videochat"

        # Check if call is active using Telethon (if available)
        is_active = True # Default to True to allow users to try joining
        if telethon_client and telethon_client.is_connected():
            try:
                tele_chat_id = int(str(chat_id).replace('-100', ''))
                full = await telethon_client(GetFullChannelRequest(channel=tele_chat_id))
                if hasattr(full, 'full_chat') and hasattr(full.full_chat, 'call'):
                    if not full.full_chat.call:
                        is_active = False
            except Exception as te:
                logger.warning(f"Telethon check failed in callback: {te}")

        if is_active:
            # Edit the message to provide the direct join button since answer(url=) is unreliable
            await query.edit_message_reply_markup(
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ ᴄʟɪᴄᴋ ᴛᴏ ᴊᴏɪɴ", url=join_link)],
                    [InlineKeyboardButton(to_small_caps("+ ᴀᴅᴅ ᴍᴇ ɪɴ ɢʀᴏᴜᴘ +"), url=f"https://t.me/{(await context.bot.get_me()).username}?startgroup=true")]
                ])
            )
        else:
            await query.edit_message_text(
                text=f"{query.message.text}\n\n❌ **ɴᴏ ᴀᴄᴛɪᴠᴇ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ ғᴏᴜɴᴅ.**",
                parse_mode=ParseMode.HTML
            )
            
    except Exception as e:
        logger.error(f"Error in vc_join_callback: {e}")
        try:
            await query.answer("Error checking voice chat status.", show_alert=True)
        except: pass

async def stop_voice_chat_monitor():
    """Stops the Telethon client."""
    if telethon_client:
        await telethon_client.disconnect()
        logger.info("🎙 Voice Chat Monitor stopped.")
