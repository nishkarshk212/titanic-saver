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
                    
                    if chat_id and (isinstance(chat_entity, PeerChannel) or (str(chat_id).startswith('-100') == False and chat_id > 0)):
                        if not str(chat_id).startswith('-100'):
                            chat_id = int(f"-100{chat_id}")

                    if not chat_id: continue

                    welcome_text = (
                        f"<blockquote>\n"
                        f"ωєℓ¢σмє тσ {group_name}'s νσι¢є ¢нαт\n"
                        f"</blockquote>\n"
                        f"<blockquote>\n"
                        f"ηαмє : {mention}\n"
                        f"ι∂ : <code>{user_id}</code>\n"
                        f"</blockquote>"
                    )
                    
                    bot_info = await ptb_application.bot.get_me()
                    add_url = f"https://t.me/{bot_info.username}?startgroup=true"
                    
                    # Button uses callback to check active status
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("ᴊᴏɪɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ", callback_data=f"join_vc_{chat_id}")],
                        [InlineKeyboardButton(to_small_caps("+ ᴀᴅᴅ ᴍᴇ ɪɴ ɢʀᴏᴜᴘ +"), url=add_url)]
                    ])
                    
                    await ptb_application.bot.send_message(
                        chat_id=chat_id,
                        text=welcome_text,
                        reply_markup=keyboard,
                        parse_mode=ParseMode.HTML
                    )
                    
                except Exception as e:
                    logger.error(f"❌ Error sending VC notification: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error in handle_voice_chat_join: {e}")

    await telethon_client.start()
    logger.info("✅ Telethon client started successfully!")

async def vc_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the 'Join Voice Chat' button click."""
    query = update.callback_query
    chat_id = int(query.data.split("_")[2])
    
    try:
        # Check if call is active using Telethon
        is_active = False
        try:
            # Resolve entity (handle -100 prefix for Telethon)
            tele_chat_id = int(str(chat_id).replace('-100', ''))
            full = await telethon_client(GetFullChannelRequest(channel=tele_chat_id))
            if hasattr(full, 'full_chat') and hasattr(full.full_chat, 'call'):
                if full.full_chat.call:
                    is_active = True
        except: pass

        if is_active:
            # Get group username for direct link if possible
            chat = await context.bot.get_chat(chat_id)
            if chat.username:
                join_link = f"https://t.me/{chat.username}?videochat"
            else:
                # Fallback to a deep link that works in most clients
                join_link = f"tg://video_chat?peer={chat_id}"
            
            # Answer with URL
            await query.answer()
            await query.edit_message_reply_markup(
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ ᴄʟɪᴄᴋ ᴛᴏ ᴊᴏɪɴ", url=join_link)],
                    [InlineKeyboardButton(to_small_caps("+ ᴀᴅᴅ ᴍᴇ ɪɴ ɢʀᴏᴜᴘ +"), url=f"https://t.me/{(await context.bot.get_me()).username}?startgroup=true")]
                ])
            )
        else:
            await query.answer("ησ α¢тινє νσι¢є ¢нαт", show_alert=True)
            
    except Exception as e:
        logger.error(f"Error in vc_join_callback: {e}")
        await query.answer("Error checking voice chat status.", show_alert=True)

async def stop_voice_chat_monitor():
    """Stops the Telethon client."""
    if telethon_client:
        await telethon_client.disconnect()
        logger.info("🎙 Voice Chat Monitor stopped.")
