import logging
import os
import asyncio
import datetime
from telethon import TelegramClient, events
from telethon.tl.functions.phone import GetGroupCallRequest, EditGroupCallParticipantRequest
from telethon.tl.types import UpdateGroupCallParticipants, PeerChat, PeerChannel, PeerUser, UpdateGroupCall, InputGroupCall
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest
from telethon.sessions import StringSession
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ChatMemberBanned
from telegram.constants import ParseMode
from config import BOT_TOKEN, to_small_caps
from font import to_mono
from telegram.ext import Application, CallbackQueryHandler, ContextTypes, MessageHandler, filters, CommandHandler
from settings_manager_mongo import get_chat_settings
from user_manager_mongo import is_user_admin
from database import get_collection, COLLECTIONS

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

# Glitch/Dedox Protection
vc_glitch_cache = {} # (chat_id, user_id) -> timestamp
vc_flood_counter = {} # chat_id -> (count, timestamp)

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
        
        # Manually trigger handler registration in case it was missed
        handlers = get_voice_chat_handlers()
        for handler in handlers:
            ptb_application.add_handler(handler)
        logger.info(f"✅ Voice Chat handlers registered: {[type(h) for h in handlers]}")
        
        # Start automatic ghost cleaner
        asyncio.create_task(auto_ghost_cleaner_task())
    except Exception as e:
        logger.error(f"❌ Failed to start Telethon client: {e}")
        return
    
    @telethon_client.on(events.Raw(UpdateGroupCall))
    async def handle_group_call_update(event):
        """Handles updates to group calls to map call IDs to chat entities."""
        try:
            call = event.call
            if hasattr(event, 'chat_id') and event.chat_id:
                # For PeerChat/PeerChannel, telethon often provides chat_id
                try:
                    entity = await telethon_client.get_entity(event.chat_id)
                    call_to_chat[call.id] = entity
                    logger.info(f"📞 Mapped call {call.id} to chat {entity.id}")
                except: pass
        except Exception as e:
            logger.error(f"Error in handle_group_call_update: {e}")

    @telethon_client.on(events.Raw(UpdateGroupCallParticipants))
    async def handle_voice_chat_join(event):
        """Handles voice chat join events for Users and Channels."""
        # Process everything in a non-blocking way
        asyncio.create_task(_process_vc_join_event(event))

async def cleanup_vc_caches():
    """Clean up expired entries from glitch/flood/notification caches."""
    now = datetime.datetime.now()
    
    # Clean vc_glitch_cache entries older than 30 seconds
    expired_glitch = [k for k, ts in vc_glitch_cache.items() if (now - ts).total_seconds() > 30]
    for k in expired_glitch:
        del vc_glitch_cache[k]
    if expired_glitch:
        logger.debug(f"Cleaned {len(expired_glitch)} expired glitch cache entries")
    
    # Clean notification_cache entries older than 6 minutes (buffer above 5min cooldown)
    expired_notif = [k for k, ts in notification_cache.items() if (now - ts).total_seconds() > 360]
    for k in expired_notif:
        del notification_cache[k]
    
    # Clean flood counter entries older than 90 seconds
    expired_flood = [k for k, (c, ts) in vc_flood_counter.items() if (now - ts).total_seconds() > 90]
    for k in expired_flood:
        del vc_flood_counter[k]

async def auto_ghost_cleaner_task():
    """Periodically cleans up ghost participants and VC caches."""
    await asyncio.sleep(60) # Initial delay
    
    while True:
        try:
            # Clean up expired cache entries first
            await cleanup_vc_caches()
            
            # Find all chats with vc_safety_enabled = True
            collection = get_collection(COLLECTIONS['SETTINGS'])
            if collection is None:
                await asyncio.sleep(1800)
                continue
                
            chats_with_safety = await collection.find({"vc_safety_enabled": True}).to_list(length=None)
            
            for chat_doc in chats_with_safety:
                chat_id = chat_doc.get("chat_id")
                if chat_id:
                    logger.info(f"🧹 Auto-cleaning ghosts for chat {chat_id}")
                    await clean_ghost_participants(chat_id)
                    await asyncio.sleep(5) # Delay between groups to avoid flood
                    
        except Exception as e:
            logger.error(f"Error in auto_ghost_cleaner_task: {e}")
            
        await asyncio.sleep(3600) # Run every hour

async def _process_vc_join_event(event):
    """Internal function to process VC join events asynchronously."""
    try:
        call_id = event.call.id
        chat_entity = call_to_chat.get(call_id)
        
        # Glitch/Dedox Safety: Massive join events
        if len(event.participants) > 10:
            logger.warning(f"⚠️ Massive VC join event ({len(event.participants)} users). Potential glitch/dedox.")
            if chat_entity:
                chat_id = chat_entity.id
                settings = get_chat_settings(chat_id)
                if settings.get("vc_safety_enabled", False):
                    asyncio.create_task(clean_ghost_participants(chat_id))

        if not chat_entity:
            # Try to resolve call from cache or recently active calls
            # If still not found, we might need to skip or try get_entity on the call
            pass

        for participant in event.participants:
            # Check if participant is joining (has 'date') or just state update
            if not hasattr(participant, 'date') or participant.date is None:
                continue
            
            asyncio.create_task(_process_single_participant(call_id, participant, chat_entity))
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
        
        # Deduplicate and Rate Limit
        cache_key = f"{user_id}_{call_id}"
        now = datetime.datetime.now()
        
        # Glitch/Dedox Protection: If user joins too frequently, ignore
        if cache_key in vc_glitch_cache:
            last_join = vc_glitch_cache[cache_key]
            if (now - last_join).total_seconds() < 10: # Joined in last 10 seconds
                logger.warning(f"🚫 Glitch detected: User {user_id} joining too fast. Ignoring.")
                return
        vc_glitch_cache[cache_key] = now

        if cache_key in notification_cache:
            if (now - notification_cache[cache_key]).total_seconds() < 300: # 5 mins cooldown
                return
        notification_cache[cache_key] = now

        # Use timeout and handle "Entity not found" gracefully
        try:
            try:
                entity = await asyncio.wait_for(telethon_client.get_entity(peer), timeout=2.0)
                name = getattr(entity, 'first_name', getattr(entity, 'title', "Unknown"))
            except (ValueError, asyncio.TimeoutError):
                return

            if peer_type == "channel":
                mention = f'<a href="https://t.me/{entity.username}">{name}</a>' if getattr(entity, 'username', None) else f"<b>{name}</b>"
            else:
                mention = f'<a href="tg://user?id={user_id}">{name}</a>'
            
            if not chat_entity:
                # If we don't have chat_entity, we can't send notification to correct chat
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

            # VC Glitch Safety: Check for flood in this specific chat
            chat_flood_key = settings_chat_id
            count, last_ts = vc_flood_counter.get(chat_flood_key, (0, now))
            if (now - last_ts).total_seconds() < 60:
                count += 1
            else:
                count = 1
            vc_flood_counter[chat_flood_key] = (count, now)
            
            if count > 15: # More than 15 joins in 60 seconds
                if settings.get("vc_safety_enabled", False):
                    logger.warning(f"🚨 VC Flood in {settings_chat_id}. Enabling auto-clean.")
                    asyncio.create_task(clean_ghost_participants(settings_chat_id))
                return

            # Delete pending invite notifications if they exist
            invite_key = (settings_chat_id, user_id)
            if invite_key in pending_invites:
                msg_ids = pending_invites.pop(invite_key, [])
                for mid in msg_ids:
                    try:
                        await ptb_application.bot.delete_message(chat_id=settings_chat_id, message_id=mid)
                    except: pass
            
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

async def clean_ghost_participants(chat_id):
    """
    Cleans up ghost participants from a voice chat.
    A 'ghost' is someone in the VC list who is not actually in the group
    or is causing a glitch.
    """
    if not telethon_client or not telethon_client.is_connected():
        return False, "Voice monitor (Telethon) not connected."

    try:
        # Normalize chat_id for Telethon
        tele_chat_id = int(str(chat_id).replace('-100', ''))
        
        # Get full chat/channel info to find the call
        try:
            if str(chat_id).startswith('-100'):
                full = await telethon_client(GetFullChannelRequest(channel=tele_chat_id))
            else:
                full = await telethon_client(GetFullChatRequest(chat_id=tele_chat_id))
        except Exception as e:
            logger.error(f"Failed to get full chat info: {e}")
            return False, "Could not fetch group info. Is the bot in the group?"
            
        if not hasattr(full, 'full_chat') or not hasattr(full.full_chat, 'call') or not full.full_chat.call:
            return False, "No active voice chat found."
            
        call = full.full_chat.call
        
        # Get participant list
        call_info = await telethon_client(GetGroupCallRequest(call=call, limit=100))
        participants = call_info.participants
        
        if not participants:
            return True, "Voice chat is empty."
            
        cleaned_count = 0
        for p in participants:
            user_peer = p.peer
            user_id = getattr(user_peer, 'user_id', getattr(user_peer, 'channel_id', None))
            
            if not user_id: continue
            
            # Skip if it's the bot itself or the Telethon account
            me = await telethon_client.get_me()
            if user_id == me.id: continue

            try:
                # Check if user is still in the group using PTB
                member = await ptb_application.bot.get_chat_member(chat_id, user_id)
                if member.status in ['left', 'kicked']:
                    # Remove from VC
                    await telethon_client(EditGroupCallParticipantRequest(
                        call=call,
                        participant=user_peer,
                        removed=True
                    ))
                    cleaned_count += 1
                    await asyncio.sleep(0.5) # Avoid flood
            except Exception as e:
                # If member not found, it's likely a ghost
                if "Chat not found" in str(e) or "User not found" in str(e) or "Member not found" in str(e):
                    await telethon_client(EditGroupCallParticipantRequest(
                        call=call,
                        participant=user_peer,
                        removed=True
                    ))
                    cleaned_count += 1
                    await asyncio.sleep(0.5)
                else:
                    logger.warning(f"Error checking member {user_id}: {e}")
                
        return True, f"✅ Cleaned {cleaned_count} ghost participants."
        
    except Exception as e:
        logger.error(f"Error in clean_ghost_participants: {e}")
        return False, f"Error: {str(e)}"

async def remove_user_from_vc(chat_id, user_id):
    """Forcefully removes a specific user from the voice chat."""
    if not telethon_client or not telethon_client.is_connected():
        return False
        
    try:
        # Normalize chat_id for Telethon
        tele_chat_id = int(str(chat_id).replace('-100', ''))
        
        # Get full chat/channel info to find the call
        if str(chat_id).startswith('-100'):
            full = await telethon_client(GetFullChannelRequest(channel=tele_chat_id))
        else:
            full = await telethon_client(GetFullChatRequest(chat_id=tele_chat_id))
            
        if not hasattr(full, 'full_chat') or not hasattr(full.full_chat, 'call') or not full.full_chat.call:
            return False
            
        call = full.full_chat.call
        
        # Try to remove the user
        await telethon_client(EditGroupCallParticipantRequest(
            call=call,
            participant=PeerUser(user_id=int(user_id)),
            removed=True
        ))
        logger.info(f"✅ User {user_id} removed from VC in chat {chat_id}")
        return True
    except Exception as e:
        logger.warning(f"Failed to remove user {user_id} from VC: {e}")
        return False

async def vcclean_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to clean ghost participants."""
    logger.info(f"vcclean_command triggered by {update.effective_user.id} in chat {update.effective_chat.id}")
    if not update.effective_chat or update.effective_chat.type == 'private':
        return
        
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        return await update.message.reply_text("❌ Only admins can use this command.")
        
    status_msg = await update.message.reply_text("🔍 Scanning voice chat for ghost participants...")
    
    try:
        success, result = await clean_ghost_participants(update.effective_chat.id)
        await status_msg.edit_text(result)
    except Exception as e:
        logger.error(f"Error executing vcclean: {e}")
        await status_msg.edit_text(f"❌ Error: {str(e)}")

def get_voice_chat_handlers():
    """Returns handlers for voice chat events."""
    return [
        CallbackQueryHandler(vc_join_callback, pattern="^join_vc_"),
        MessageHandler(filters.StatusUpdate.VIDEO_CHAT_PARTICIPANTS_INVITED, voice_chat_invite_handler),
        CommandHandler("vcclean", vcclean_command)
    ]

async def stop_voice_chat_monitor():
    """Stops the Telethon client."""
    if telethon_client:
        await telethon_client.disconnect()
        logger.info("🎙 Voice Chat Monitor stopped.")
