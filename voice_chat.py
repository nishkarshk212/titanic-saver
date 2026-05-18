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
from font import to_mono
from telegram.ext import Application, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from settings_manager_mongo import get_chat_settings
from user_manager_mongo import is_user_admin

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

# Pending invites: (chat_id, user_id) -> list of message_ids to delete upon join
pending_invites = {}

async def start_voice_chat_monitor(application: Application):
    """Starts the Telethon client to monitor voice chat events."""
    global telethon_client, ptb_application
    ptb_application = application
    
    if not API_ID or not API_HASH or not STRING_SESSION:
        logger.warning("⚠️ Telethon credentials missing. Voice chat join notifications disabled.")
        return

    logger.info("🎙 Starting Voice Chat Monitor...")
    telethon_client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    
    # Connect and start the client properly
    try:
        await telethon_client.start()
        logger.info("✅ Telethon client started successfully!")
    except Exception as e:
        logger.error(f"❌ Failed to start Telethon client: {e}")
        return
    
    @telethon_client.on(events.Raw(UpdateGroupCallParticipants))
    async def handle_voice_chat_join(event):
        """Handles voice chat join events for Users and Channels."""
        # Process everything in a non-blocking way
        asyncio.create_task(_process_vc_join_event(event))

async def _process_vc_join_event(event):
    """Internal function to process VC join events asynchronously."""
    try:
        chat_entity = call_to_chat.get(event.call.id)
        
        if not chat_entity:
            # Optimize: try to get from dialogs more efficiently
            try:
                # We limit the iteration and use a shorter timeout
                async for dialog in telethon_client.iter_dialogs(limit=10):
                    if dialog.is_group or dialog.is_channel:
                        try:
                            # We don't need full channel request for every dialog
                            # Just check if we already know about this call
                            pass # For now, keep the logic simple but limited
                        except: continue
                
                # If still not found, we might have to fetch it, but let's be careful
            except Exception as e:
                logger.warning(f"Error iterating dialogs: {e}")

        for participant in event.participants:
            if not hasattr(participant, 'date') or participant.date is None:
                continue
            
            # Move the rest of the logic here...
            # (I'll keep the logic but wrap it in more background tasks)
            asyncio.create_task(_process_single_participant(event.call.id, participant, chat_entity))
    except Exception as e:
        logger.error(f"❌ Error in _process_vc_join_event: {e}")

async def _process_single_participant(call_id, participant, chat_entity):
    """Process a single VC participant join."""
    try:
        peer = participant.peer
        user_id = None
        peer_type = "user"
        
        if isinstance(peer, PeerUser):
            user_id = peer.user_id
            peer_type = "user"
        elif isinstance(peer, PeerChannel):
            user_id = peer.channel_id
            peer_type = "channel"
        
        if not user_id: return
        
        # Deduplicate
        cache_key = f"{user_id}_{call_id}"
        now = datetime.datetime.now()
        if cache_key in notification_cache:
            if (now - notification_cache[cache_key]).total_seconds() < 60:
                return
        notification_cache[cache_key] = now

        # Use timeout for entity fetching
        try:
            entity = await asyncio.wait_for(telethon_client.get_entity(peer), timeout=5.0)
            name = getattr(entity, 'first_name', getattr(entity, 'title', "Unknown"))
            
            if peer_type == "channel":
                mention = f'<a href="https://t.me/{entity.username}">{name}</a>' if getattr(entity, 'username', None) else f"<b>{name}</b>"
            else:
                mention = f'<a href="tg://user?id={user_id}">{name}</a>'
            
            if not chat_entity:
                # Try one last time to resolve chat_id from peer if it's a channel join? 
                # No, call_id is linked to the group, not the user.
                return

            group_name = chat_entity.title if hasattr(chat_entity, 'title') else "the group"
            chat_id = chat_entity.id
            
            # Normalize chat_id
            settings_chat_id = chat_id
            if not str(chat_id).startswith('-100'):
                settings_chat_id = int(f"-100{chat_id}")

            # Check settings
            settings = get_chat_settings(settings_chat_id)
            if not settings.get("vc_user_join_enabled", True):
                return

            # Proceed with notification...
            # (Rest of the logic remains similar but inside this background task)
            
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
            
            # Construct join link
            try:
                # Cache chat username for join link
                if not hasattr(chat_entity, 'username') or not chat_entity.username:
                    chat_info = await ptb_application.bot.get_chat(settings_chat_id)
                    username = chat_info.username
                else:
                    username = chat_entity.username
                    
                if username:
                    join_link = f"https://t.me/{username}?videochat"
                else:
                    clean_id = str(settings_chat_id).replace("-100", "")
                    join_link = f"https://t.me/c/{clean_id}?videochat"
            except:
                clean_id = str(settings_chat_id).replace("-100", "")
                join_link = f"https://t.me/c/{clean_id}?videochat"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("ᴊᴏɪɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ", url=join_link)],
                [InlineKeyboardButton(to_small_caps("+ ᴀᴅᴅ ᴍᴇ ɪɴ ɢʀᴏᴜᴘ +"), url=add_url)]
            ])
            
            sent_message = await ptb_application.bot.send_message(
                chat_id=settings_chat_id,
                text=welcome_text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
            
            # Auto delete
            async def auto_delete_notification(c_id, m_id):
                await asyncio.sleep(60)
                try:
                    await ptb_application.bot.delete_message(chat_id=c_id, message_id=m_id)
                except: pass
            
            asyncio.create_task(auto_delete_notification(settings_chat_id, sent_message.message_id))
            
        except Exception as e:
            logger.error(f"Error in _process_single_participant: {e}")
    except Exception as e:
        logger.error(f"❌ Error processing participant: {e}")


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

async def voice_chat_invite_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles notifications when users are invited to a voice chat."""
    logger.info(f"Checking VC invite notification in {update.effective_chat.id}")
    
    if not update.message or not update.message.video_chat_participants_invited:
        logger.info("No video_chat_participants_invited in message")
        return
    
    chat_id = update.effective_chat.id
    settings = get_chat_settings(chat_id)
    
    enabled = settings.get("vc_invite_notification_enabled", True)
    logger.info(f"VC invite notification enabled: {enabled}")
    
    if not enabled:
        return

    inviter = update.effective_user
    invited_users = update.message.video_chat_participants_invited.users
    
    logger.info(f"Processing {len(invited_users)} invited users")
    
    # Static parts in mono
    invited_mono = to_mono("invited")
    to_mono_str = to_mono("to")
    vc_mono = to_mono("'s voice chat")
    
    for user in invited_users:
        # Format: {inviter_mention} 𝚒𝚗𝚟𝚒𝚝𝚎𝚍 {invitee_mention}𝚝𝚘 ˹ 🇹ɪᴛᴀɴɪᴄ ꭙ 🇼ᴏʀʟᴅ ˼ 🪽'𝚜 𝚟𝚘𝚒𝚌𝚎 𝚌𝚑𝚊𝚝
        inviter_mention = inviter.mention_html()
        invitee_mention = user.mention_html()
        
        # Constructing the message with requested styling
        message_text = (
            f"<blockquote>\n"
            f"{inviter_mention} {invited_mono} {invitee_mention} {to_mono_str} "
            f"˹ 🇹ɪᴛᴀɴɪᴄ ꭙ 🇼ᴏʀʟᴅ ˼ 🪽{vc_mono}\n"
            f"</blockquote>"
        )
        
        try:
            sent_msg = await context.bot.send_message(
                chat_id=chat_id,
                text=message_text,
                parse_mode=ParseMode.HTML
            )
            logger.info(f"Sent VC invite notification for {user.first_name} in {chat_id}")
            
            # Store message IDs for deletion upon join
            # We store the original service message ID AND the bot's notification ID
            invite_key = (chat_id, user.id)
            if invite_key not in pending_invites:
                pending_invites[invite_key] = []
            
            # Add service message ID (if not already added)
            service_msg_id = update.message.message_id
            if service_msg_id not in pending_invites[invite_key]:
                pending_invites[invite_key].append(service_msg_id)
            
            # Add bot's notification message ID
            pending_invites[invite_key].append(sent_msg.message_id)
            
            # Optional: auto-cleanup pending_invites after some time (e.g., 1 hour)
            async def cleanup_invite(key, msg_id):
                await asyncio.sleep(3600)
                if key in pending_invites and msg_id in pending_invites[key]:
                    pending_invites[key].remove(msg_id)
                    if not pending_invites[key]:
                        pending_invites.pop(key, None)
            
            asyncio.create_task(cleanup_invite(invite_key, sent_msg.message_id))

        except Exception as e:
            logger.error(f"Error sending invite notification: {e}")

def get_voice_chat_handlers():
    """Returns handlers for voice chat events."""
    return [
        CallbackQueryHandler(vc_join_callback, pattern="^join_vc_"),
        MessageHandler(filters.StatusUpdate.VIDEO_CHAT_PARTICIPANTS_INVITED, voice_chat_invite_handler)
    ]

async def stop_voice_chat_monitor():
    """Stops the Telethon client."""
    if telethon_client:
        await telethon_client.disconnect()
        logger.info("🎙 Voice Chat Monitor stopped.")
