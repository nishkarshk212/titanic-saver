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

# Timestamp when the monitor started — ignore UpdateGroupCallParticipants for first 15s
_vc_monitor_start_ts = None

# Calls we've already resolved but the bot isn't a member — skip resolution next time
_failed_resolutions = {} # call_id -> timestamp

# Tracks call_ids whose first post-gate state dump has already been suppressed
_post_gate_sync_done = set()

async def start_voice_chat_monitor(application: Application):
    """Starts the Telethon client to monitor voice chat events."""
    global telethon_client, ptb_application
    ptb_application = application
    
    if not API_ID or not API_HASH or not STRING_SESSION:
        logger.warning("⚠️ Telethon credentials missing. Voice chat join notifications disabled.")
        return

    logger.info("🎙 Starting Voice Chat Monitor...")
    telethon_client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

    # Register Telethon event handlers BEFORE connecting to avoid missing events
    @telethon_client.on(events.Raw(UpdateGroupCall))
    async def handle_group_call_update(event):
        """Handles updates to group calls to map call IDs to chat entities."""
        try:
            call = event.call
            peer = getattr(event, 'peer', None)
            if peer is None:
                logger.info(f"📞 UpdateGroupCall: call={call.id}, no peer (flags missing)")
                return
            peer_id = getattr(peer, 'channel_id', None) or getattr(peer, 'chat_id', None) or getattr(peer, 'user_id', None)
            if peer_id is None:
                logger.info(f"📞 UpdateGroupCall: call={call.id}, peer={type(peer).__name__} with no id")
                return
            logger.info(f"📞 UpdateGroupCall: call_id={call.id}, peer_id={peer_id}")
            try:
                # Try to get Telethon entity first to determine the chat type
                try:
                    entity = await telethon_client.get_entity(peer_id)
                    from telethon.tl.types import Channel
                    if isinstance(entity, Channel):
                        peer_full = int(f"-100{peer_id}")
                    else:
                        peer_full = -peer_id
                except:
                    # Fallback if get_entity fails
                    peer_full = int(f"-100{peer_id}") if peer_id > 0 else peer_id
                
                try:
                    await ptb_application.bot.get_chat(peer_full)
                except Exception as e:
                    logger.info(f"📞 Skipping call {call.id}: bot not in chat {peer_full} ({e})")
                    return
                
                # If we reached here, the bot is in the chat
                if 'entity' in locals():
                    call_to_chat[call.id] = entity
                    logger.info(f"📞 Mapped call {call.id} to chat {entity.id} (entity)")
                else:
                    call_to_chat[call.id] = peer_full
                    logger.info(f"📞 Mapped call {call.id} to chat {peer_full} (ID only)")
            except Exception as e:
                logger.warning(f"Could not get entity for call {call.id} peer {peer_id}: {e}")
        except Exception as e:
            logger.error(f"Error in handle_group_call_update: {e}")

    @telethon_client.on(events.Raw(UpdateGroupCallParticipants))
    async def handle_voice_chat_join(event):
        """Handles voice chat join events for Users and Channels."""
        logger.info(f"📥 Received UpdateGroupCallParticipants for call {event.call.id} with {len(event.participants)} participants")
        asyncio.create_task(_process_vc_join_event(event))
    
    # Connect and start the client properly
    try:
        await telethon_client.start()
        global _vc_monitor_start_ts
        _vc_monitor_start_ts = datetime.datetime.now()
        logger.info("✅ Telethon client started successfully!")
        
        # Load dialogs to populate cache
        logger.info("📂 Loading dialogs for Telethon client...")
        dialogs = await telethon_client.get_dialogs(limit=50)
        logger.info(f"✅ Loaded {len(dialogs)} dialogs.")
        
        # Register PTB handlers for invite notifications and VC commands
        handlers = get_voice_chat_handlers()
        for handler in handlers:
            ptb_application.add_handler(handler)
        logger.info(f"✅ Voice Chat handlers registered: {[type(h) for h in handlers]}")
        
        # Start automatic ghost cleaner
        asyncio.create_task(auto_ghost_cleaner_task())
        
        # Pre-scan active VCs to populate call_to_chat mapping
        asyncio.create_task(scan_active_vcs())
    except Exception as e:
        logger.error(f"❌ Failed to start Telethon client: {e}")
        return

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
            collection = get_collection(COLLECTIONS['settings'])
            if collection is None:
                await asyncio.sleep(1800)
                continue
                
            chats_with_safety = list(collection.find({"vc_safety_enabled": True}))
            
            for chat_doc in chats_with_safety:
                chat_id = chat_doc.get("chat_id")
                if chat_id:
                    logger.info(f"🧹 Auto-cleaning ghosts for chat {chat_id}")
                    await clean_ghost_participants(chat_id)
                    await asyncio.sleep(5) # Delay between groups to avoid flood
                    
        except Exception as e:
            logger.error(f"Error in auto_ghost_cleaner_task: {e}")
            
        await asyncio.sleep(3600) # Run every hour

async def scan_active_vcs():
    """Pre-scan all groups for active VCs to populate call_to_chat mapping."""
    try:
        logger.info("🔍 Scanning groups for active VCs...")
        collection = get_collection(COLLECTIONS['settings'])
        if collection is None:
            return
        all_chats = list(collection.find({}))
        count = 0
        for chat_doc in all_chats:
            cid = chat_doc.get("chat_id")
            if not cid:
                continue
            try:
                clean_id = int(str(cid).replace('-100', ''))
                try:
                    full = await telethon_client(GetFullChannelRequest(channel=clean_id))
                except Exception as e:
                    # logger.debug(f"Could not get full channel {clean_id}: {e}")
                    try:
                        full = await telethon_client(GetFullChatRequest(chat_id=clean_id))
                    except:
                        continue
                    
                if hasattr(full, 'full_chat') and hasattr(full.full_chat, 'call') and full.full_chat.call:
                    call_id = full.full_chat.call.id
                    if call_id not in call_to_chat:
                        try:
                            # Verify if the bot is actually in the group before mapping
                            await ptb_application.bot.get_chat(cid)
                            entity = await telethon_client.get_entity(clean_id)
                            
                            # Populate Telethon's entity cache for this group
                            logger.info(f"👥 Populating entity cache for group {cid}...")
                            await telethon_client.get_participants(entity, limit=200)
                            
                            call_to_chat[call_id] = entity
                            count += 1
                            logger.info(f"🔍 Pre-scanned active VC: call {call_id} in group {cid}")
                        except Exception as e:
                            # logger.debug(f"Skipping call {call_id} in group {cid}: bot not a member or {e}")
                            continue
                await asyncio.sleep(0.5) # Faster scan on startup
            except:
                continue
        logger.info(f"🔍 Pre-scan complete: mapped {count} active VCs")
    except Exception as e:
        logger.error(f"Error in scan_active_vcs: {e}")

async def _process_vc_join_event(event):
    """Internal function to process VC join events asynchronously."""
    try:
        call_id = event.call.id
        
        # Skip initial state dump events during the first 5 seconds after startup
        if _vc_monitor_start_ts and (datetime.datetime.now() - _vc_monitor_start_ts).total_seconds() < 5:
            logger.info(f"Ignoring initial state sync for call {call_id} ({len(event.participants)} participants)")
            return
        
        chat_entity = call_to_chat.get(call_id)
        
        # If call_to_chat missing, try resolving the chat from the call itself
        now = datetime.datetime.now()
        last_failed = _failed_resolutions.get(call_id)
        
        # Try resolution if missing, and haven't failed recently (cooldown 5 mins)
        if not chat_entity and (not last_failed or (now - last_failed).total_seconds() > 300):
            try:
                logger.info(f"🔍 Attempting to resolve call {call_id} via GetGroupCallRequest...")
                result = await telethon_client(GetGroupCallRequest(call=event.call, limit=1))
                if result and result.chats:
                    raw_entity = result.chats[0]
                    raw_id = raw_entity.id
                    logger.info(f"📡 Found raw_entity {raw_id} for call {call_id}")
                    
                    # Determine PTB compatible ID
                    from telethon.tl.types import Channel
                    if isinstance(raw_entity, Channel):
                        bot_check_id = int(f"-100{raw_id}")
                    else:
                        bot_check_id = -raw_id
                        
                    try:
                        await ptb_application.bot.get_chat(bot_check_id)
                        chat_entity = raw_entity
                        call_to_chat[call_id] = chat_entity
                        _failed_resolutions.pop(call_id, None)
                        logger.info(f"✅ Successfully resolved call {call_id} -> chat {bot_check_id} ({type(raw_entity).__name__})")
                    except Exception as e:
                        _failed_resolutions[call_id] = now
                        logger.info(f"❌ Skipping call {call_id}: bot not in chat {bot_check_id} or error: {e}")
                else:
                    # Fallback: Deep scan all groups if GetGroupCallRequest returns nothing
                    logger.info(f"❓ GetGroupCallRequest empty for {call_id}. Starting deep scan fallback...")
                    
                    # 1. First try scanning dialogs the account is already in
                    logger.info(f"🔎 Scanning active dialogs for call {call_id}...")
                    dialogs = await telethon_client.get_dialogs(limit=100)
                    found = False
                    for dialog in dialogs:
                        if dialog.is_group or dialog.is_channel:
                            try:
                                full = await telethon_client(GetFullChannelRequest(channel=dialog.entity)) if dialog.is_channel else await telethon_client(GetFullChatRequest(chat_id=dialog.id))
                                if hasattr(full, 'full_chat') and hasattr(full.full_chat, 'call') and full.full_chat.call and full.full_chat.call.id == call_id:
                                    call_to_chat[call_id] = dialog.entity
                                    _failed_resolutions.pop(call_id, None)
                                    logger.info(f"🎯 Dialog scan found call {call_id} in chat {dialog.id}")
                                    
                                    # Populate cache
                                    try: await telethon_client.get_participants(dialog.entity, limit=100)
                                    except: pass
                                    
                                    found = True
                                    chat_entity = dialog.entity
                                    break
                            except: continue
                    
                    # 2. If still not found, scan all groups in DB (backup)
                    if not found:
                        collection = get_collection(COLLECTIONS['settings'])
                        if collection is not None:
                            all_chats = list(collection.find({}))
                            logger.info(f"🔎 Scanning {len(all_chats)} database groups for call {call_id}...")
                            for chat_doc in all_chats:
                                cid = chat_doc.get("chat_id")
                                if not cid: continue
                                try:
                                    clean_id = int(str(cid).replace('-100', ''))
                                    try:
                                        full = await telethon_client(GetFullChannelRequest(channel=clean_id))
                                    except Exception as e:
                                        full = await telethon_client(GetFullChatRequest(chat_id=clean_id))
                                        
                                    if hasattr(full, 'full_chat') and hasattr(full.full_chat, 'call') and full.full_chat.call:
                                        if full.full_chat.call.id == call_id:
                                            entity = await telethon_client.get_entity(clean_id)
                                            chat_entity = entity
                                            call_to_chat[call_id] = chat_entity
                                            _failed_resolutions.pop(call_id, None)
                                            logger.info(f"🎯 DB scan found call {call_id} in chat {cid}")
                                            found = True
                                            break
                                except Exception as e:
                                    continue
                        
                    if not found:
                        _failed_resolutions[call_id] = now
                        logger.info(f"❌ Resolution fallback failed for call {call_id}")
            except Exception as resolve_err:
                _failed_resolutions[call_id] = now
                logger.warning(f"⚠️ Could not resolve chat for call {call_id}: {resolve_err}")
        
        # Glitch/Dedox Safety: Massive join events
        if len(event.participants) > 20: 
            logger.warning(f"⚠️ Massive VC join event ({len(event.participants)} users).")
            if chat_entity:
                cid = chat_entity.id if not isinstance(chat_entity, int) else chat_entity
                asyncio.create_task(clean_ghost_participants(cid))

        # First event after gate: suppress notifications for all current participants
        # (state dump of existing VC members — not real joins)
        if call_id not in _post_gate_sync_done:
            _post_gate_sync_done.add(call_id)
            now = datetime.datetime.now()
            silent_count = 0
            for participant in event.participants:
                if not hasattr(participant, 'date') or participant.date is None:
                    continue
                peer = participant.peer
                uid = None
                if isinstance(peer, PeerUser):
                    uid = peer.user_id
                elif isinstance(peer, PeerChannel):
                    uid = peer.channel_id
                elif isinstance(peer, PeerChat):
                    uid = peer.chat_id
                if uid:
                    notification_cache[f"{uid}_{call_id}"] = now
                    silent_count += 1
            logger.info(f"Pre-populated notification cache for {silent_count} existing participants in call {call_id}")
            return

        # Analyze batch for switches
        leaves = []
        joins = []
        for p in event.participants:
            is_join = hasattr(p, 'date') and p.date is not None and not getattr(p, 'left', False)
            is_leave = getattr(p, 'left', False)
            if is_leave: leaves.append(p)
            elif is_join: joins.append(p)

        # A switch is typically a single user changing their peer (e.g. User -> Channel)
        # This usually results in 1 leave and 1 join in the same update batch.
        is_switch_event = len(leaves) == 1 and len(joins) == 1
        
        # Process participants in parallel tasks to avoid blocking the loop
        for participant in leaves:
            asyncio.create_task(_process_single_participant(call_id, participant, chat_entity, is_join=False, is_switch=is_switch_event))
            
        for participant in joins:
            asyncio.create_task(_process_single_participant(call_id, participant, chat_entity, is_join=True, is_switch=is_switch_event))
    except Exception as e:
        logger.error(f"❌ Error in _process_vc_join_event: {e}")

async def _process_single_participant(call_id, participant, chat_entity, is_join=True, is_switch=False):
    """Process a single VC participant join or leave."""
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
        elif isinstance(peer, PeerChat):
            user_id = peer.chat_id
            peer_type = "chat"
        
        if not user_id: 
            logger.info(f"⚠️ Skipping participant in call {call_id}: no user_id found in peer {type(peer).__name__}")
            return
        
        logger.info(f"👤 [START] Processing {user_id} in call {call_id} (Join: {is_join}, Switch: {is_switch})")
        
        # Use timeout and handle "Entity not found" gracefully
        try:
            # 1. Check Chat Entity
            if not chat_entity:
                logger.warning(f"❌ [STOP] No chat_entity for {user_id} in call {call_id}")
                return

            if isinstance(chat_entity, int):
                chat_id = chat_entity
            else:
                chat_id = chat_entity.id
            
            settings_chat_id = chat_id
            if not str(chat_id).startswith('-100'):
                settings_chat_id = int(f"-100{chat_id}")

            # 2. Check Cooldowns/Glitches
            now = datetime.datetime.now()
            if is_join:
                # Glitch check
                glitch_key = f"{user_id}_{call_id}_{participant.date}"
                if glitch_key in vc_glitch_cache:
                    if (now - vc_glitch_cache[glitch_key]).total_seconds() < 10:
                        logger.warning(f"🚫 [STOP] Glitch detected for {user_id}")
                        return
                vc_glitch_cache[glitch_key] = now

                # Cooldown check
                notif_key = f"{user_id}_{call_id}"
                if notif_key in notification_cache:
                    if (now - notification_cache[notif_key]).total_seconds() < 300:
                        logger.info(f"⏸ [STOP] Cooldown active for {user_id}")
                        return
            else:
                leave_cache_key = f"leave_{user_id}_{call_id}"
                if leave_cache_key in notification_cache:
                    if (now - notification_cache[leave_cache_key]).total_seconds() < 30: # Increased to 30s
                        logger.info(f"⏸ [STOP] Leave cooldown active for {user_id}")
                        return
                notification_cache[leave_cache_key] = now
                
                # DO NOT clear join cache immediately to prevent Join-Leave-Join spam glitch
                # join_notif_key = f"{user_id}_{call_id}"
                # notification_cache.pop(join_notif_key, None)
                
                if is_switch:
                    logger.info(f"🔄 [STOP] Identity switch for {user_id} - suppressing 'Left' notification")
                    return

            # 3. Get Entity
            try:
                logger.info(f"🔍 [GET_ENTITY] Fetching {peer_type} {user_id}...")
                entity = await asyncio.wait_for(telethon_client.get_entity(peer), timeout=10.0)
                name = getattr(entity, 'first_name', getattr(entity, 'title', "Unknown"))
                logger.info(f"✅ [ENTITY_FOUND] Name: {name}")
            except Exception as e:
                # Fallback: try to find the user in the group participants
                try:
                    logger.info(f"🔍 [GET_ENTITY_FALLBACK] Searching for {user_id} in group participants...")
                    participants = await telethon_client.get_participants(chat_entity, search=str(user_id))
                    if participants:
                        entity = participants[0]
                        name = getattr(entity, 'first_name', getattr(entity, 'title', "Unknown"))
                        logger.info(f"✅ [ENTITY_FOUND_FALLBACK] Name: {name}")
                    else:
                        # Final attempt: use PTB bot to get basic info
                        logger.info(f"🔍 [GET_ENTITY_FINAL] Using PTB fallback for {user_id}...")
                        chat_member = await ptb_application.bot.get_chat_member(chat_id=settings_chat_id, user_id=user_id)
                        user = chat_member.user
                        name = user.first_name
                        # Create a dummy entity object for the rest of the logic
                        class DummyEntity:
                            def __init__(self, u):
                                self.username = u.username
                                self.first_name = u.first_name
                        entity = DummyEntity(user)
                        logger.info(f"✅ [ENTITY_FOUND_FINAL] Name: {name}")
                except Exception as fallback_err:
                    logger.warning(f"❌ [ENTITY_FAILED] {user_id}: {e} (Fallback also failed: {fallback_err})")
                    return

            # 4. Check Settings
            settings = get_chat_settings(settings_chat_id)
            if is_join and not settings.get("vc_user_join_enabled", True):
                logger.info(f"🔇 [STOP] Join notifs disabled in {settings_chat_id}")
                return
            if not is_join and not settings.get("vc_user_leave_enabled", True):
                logger.info(f"🔇 [STOP] Leave notifs disabled in {settings_chat_id}")
                return

            # 5. Flood Protection (Join only)
            if is_join:
                chat_flood_key = settings_chat_id
                count, last_ts = vc_flood_counter.get(chat_flood_key, (0, now))
                if (now - last_ts).total_seconds() < 60: count += 1
                else: count = 1
                vc_flood_counter[chat_flood_key] = (count, now)
                
                if count > 15: # Standard threshold
                    logger.warning(f"🚨 [FLOOD] chat {settings_chat_id} count {count}")
                    asyncio.create_task(clean_ghost_participants(settings_chat_id))
                    return

        # 6. Send Message
            username_str = f"@{entity.username}" if getattr(entity, 'username', None) else "—"
            display_id = user_id
            
            # For Channels/Chats, ensure we show the -100 prefix if missing
            if peer_type in ["channel", "chat"] and not str(user_id).startswith("-100"):
                display_id = f"-100{user_id}"
            
            # Formatting mention based on peer type
            if peer_type == "channel":
                mention = f'<a href="https://t.me/{entity.username}">{name}</a>' if getattr(entity, 'username', None) else f"<b>{name}</b>"
            elif peer_type == "chat":
                mention = f"<b>{name}</b>"
            else:
                mention = f'<a href="tg://user?id={user_id}">{name}</a>'

            # Status logic
            if is_join:
                if is_switch:
                    status_text = "Switched Identity 🔄"
                else:
                    status_text = "Joined ✅"
            else:
                status_text = "Left ❌"
            
            notification_text = (
                f"<blockquote>\n"
                f"𝚴𝛂ϻ𝛆 ➛ {mention}\n"
                f"𝚰𝛛 ➛ <code>{display_id}</code>\n"
                f"𝐔𝛅𝛆𝛑𝛈𝛂ϻ𝛆 ➛ {username_str}\n"
                f"Status ➛ {status_text}\n"
                f"</blockquote>"
            )
            
            bot_info = await ptb_application.bot.get_me()
            join_link = "https://t.me/Titanic_world_chatting_zonee?videochat"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("ᴊᴏɪɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ", url=join_link)],
                [InlineKeyboardButton(to_small_caps("+ ᴀᴅᴅ ᴍᴇ ɪɴ ɢʀᴏᴜᴘ +"), url=f"https://t.me/{bot_info.username}?startgroup=true")]
            ])
            
            sent_message = await ptb_application.bot.send_message(
                chat_id=settings_chat_id,
                text=notification_text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
            logger.info(f"📤 [SENT] {user_id} to {settings_chat_id}")
            
            if is_join:
                notification_cache[f"{user_id}_{call_id}"] = datetime.datetime.now()
            
            # Auto delete
            async def auto_delete_notification(c_id, m_id):
                await asyncio.sleep(5)
                try: await ptb_application.bot.delete_message(chat_id=c_id, message_id=m_id)
                except: pass
            
            asyncio.create_task(auto_delete_notification(settings_chat_id, sent_message.message_id))
            
        except Exception as e:
            logger.error(f"❌ [CRASH] _process_single_participant: {e}")
    except Exception as e:
        logger.error(f"❌ [CRASH] _process_single_participant outer: {e}")

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
        
        # Use the specific join link provided by the user
        join_link = "https://t.me/Titanic_world_chatting_zonee?videochat"

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
    
    # Pre-populate call_to_chat mapping for this chat
    if telethon_client and telethon_client.is_connected():
        try:
            tele_chat_id = int(str(chat_id).replace('-100', ''))
            full = await telethon_client(GetFullChannelRequest(channel=tele_chat_id))
            if hasattr(full, 'full_chat') and hasattr(full.full_chat, 'call') and full.full_chat.call:
                call_id = full.full_chat.call.id
                if call_id not in call_to_chat:
                    chat_entity = await telethon_client.get_entity(tele_chat_id)
                    call_to_chat[call_id] = chat_entity
                    logger.info(f"📞 Pre-mapped call {call_id} to chat {chat_id} via invite handler")
        except Exception as e:
            logger.warning(f"Could not pre-map call for chat {chat_id}: {e}")
    
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
                        left=True
                    ))
                    cleaned_count += 1
                    await asyncio.sleep(0.5) # Avoid flood
            except Exception as e:
                # If member not found, it's likely a ghost
                if "Chat not found" in str(e) or "User not found" in str(e) or "Member not found" in str(e):
                    await telethon_client(EditGroupCallParticipantRequest(
                        call=call,
                        participant=user_peer,
                        left=True
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
            left=True
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

async def vcstatus_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to show VC monitor status and active calls with live participants."""
    if not update.effective_chat or update.effective_chat.type == 'private':
        return
        
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        return await update.message.reply_text("❌ Only admins can use this command.")
        
    status_msg = (
        f"🎙 <b>Voice Chat Monitor Status</b>\n\n"
        f"<b>Connected:</b> {'✅ Yes' if telethon_client and telethon_client.is_connected() else '❌ No'}\n"
        f"<b>Active Mappings:</b> {len(call_to_chat)}\n"
        f"<b>Notification Cache:</b> {len(notification_cache)}\n"
        f"<b>Failed Resolutions:</b> {len(_failed_resolutions)}\n\n"
    )

    if call_to_chat and telethon_client and telethon_client.is_connected():
        status_msg += "<b>Live Active Voice Chats:</b>\n"
        for call_id, chat_entity in list(call_to_chat.items()):
            try:
                # Determine chat ID for display
                if hasattr(chat_entity, 'id'):
                    cid = chat_entity.id
                    clean_id = int(str(cid).replace('-100', ''))
                    display_name = getattr(chat_entity, 'title', f"Chat {cid}")
                    
                    # Fetch participants for this call
                    try:
                        # Get full chat to ensure we have the correct call reference
                        if isinstance(chat_entity, PeerChannel) or "Channel" in type(chat_entity).__name__:
                            full = await telethon_client(GetFullChannelRequest(channel=clean_id))
                        else:
                            full = await telethon_client(GetFullChatRequest(chat_id=clean_id))
                        
                        if hasattr(full, 'full_chat') and hasattr(full.full_chat, 'call') and full.full_chat.call:
                            call_info = await telethon_client(GetGroupCallRequest(call=full.full_chat.call, limit=100))
                            participants = call_info.participants
                            
                            p_ids = []
                            for p in participants:
                                if not getattr(p, 'left', False):
                                    p_id = getattr(p.peer, 'user_id', getattr(p.peer, 'channel_id', getattr(p.peer, 'chat_id', 'Unknown')))
                                    p_ids.append(f"<code>{p_id}</code>")
                            
                            if p_ids:
                                status_msg += f"• <b>{display_name}</b>: {len(p_ids)} users\n"
                                status_msg += f"  └ {', '.join(p_ids)}\n"
                            else:
                                status_msg += f"• <b>{display_name}</b>: No active participants\n"
                        else:
                            # Call might have ended
                            status_msg += f"• <b>{display_name}</b>: Voice chat ended\n"
                    except Exception as e:
                        status_msg += f"• <b>{display_name}</b>: (Error fetching users)\n"
                else:
                    status_msg += f"• <b>Unknown Chat ({call_id})</b>\n"
            except: continue
    else:
        status_msg += "<i>No active voice chats currently tracked.</i>\n"

    status_msg += f"\n<i>Use /vcrefresh to force a global scan of all groups.</i>"
    
    # Split message if it's too long
    if len(status_msg) > 4000:
        parts = [status_msg[i:i+4000] for i in range(0, len(status_msg), 4000)]
        for part in parts:
            await update.message.reply_text(part, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(status_msg, parse_mode=ParseMode.HTML)

async def vcrefresh_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to force a global scan of all groups for active VCs."""
    if not update.effective_chat or update.effective_chat.type == 'private':
        return
        
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        return await update.message.reply_text("❌ Only admins can use this command.")
        
    msg = await update.message.reply_text("🔄 Starting global VC scan... this may take a minute.")
    
    # Reset failed resolutions to allow retrying everything
    _failed_resolutions.clear()
    
    # Run scan
    asyncio.create_task(scan_active_vcs())
    
    await msg.edit_text("✅ Global VC scan started in background. Check /vcstatus in a moment.")

def get_voice_chat_handlers():
    """Returns handlers for voice chat events."""
    return [
        CallbackQueryHandler(vc_join_callback, pattern="^join_vc_"),
        MessageHandler(filters.StatusUpdate.VIDEO_CHAT_PARTICIPANTS_INVITED, voice_chat_invite_handler),
        CommandHandler("vcclean", vcclean_command),
        CommandHandler("vcstatus", vcstatus_command),
        CommandHandler("vcrefresh", vcrefresh_command)
    ]

async def stop_voice_chat_monitor():
    """Stops the Telethon client."""
    if telethon_client:
        await telethon_client.disconnect()
        logger.info("🎙 Voice Chat Monitor stopped.")
