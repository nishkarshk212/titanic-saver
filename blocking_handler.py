from telegram import Update, MessageEntity, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.constants import ParseMode
from datetime import datetime, timedelta
import logging
import copy

from config import OWNER_ID, send_bot_response
from settings_manager_mongo import get_chat_settings, update_chat_setting
from user_manager_mongo import is_user_admin, cache_user

# DEFAULT_SETTINGS for blocking (will be merged with MongoDB settings)
DEFAULT_BLOCKING_SETTINGS = {
    "blocking_enabled": True,
    "block_stickers": False,
    "block_premium_sticker": False,
    "block_link": False,
    "block_embed_link": False,
    "block_media": False,
    "block_documents": False,
    "block_forward": False,
    "block_channel_post": False,
    "block_command": False,
    "block_contact": False,
    "block_location": False,
    "block_voice": False,
    "block_audio": False,
    "block_video_note": False,
    "block_poll": False,
    "block_dice": False,
    "block_game": False,
    "msg_length_min": 0,
    "msg_length_max": 2000,
    "msg_length_delete": False,
    "msg_length_penalty": "off",  # off, warn, kick, mute, ban
    "custom_block_list": [],
    "custom_block_media": [],
    "custom_block_stickers": [],
    "user_permissions": {},  # {user_id: {"block_stickers": True, ...}}
    # Clean service settings
    "clean_service_enabled": True,
    "clean_join": False,
    "clean_left": False,
    "clean_title": False,
    "clean_photo": False,
    "clean_voice_start": False,
    "clean_voice_end": False,
    "clean_voice_schedule": False,
    "clean_voice_invite": False,
    "clean_pinned": False,
}

async def is_admin_or_creator(context, chat_id, user_id, message=None):
    """Check if user is admin/creator, including anonymous admin support."""
    # Anonymous admin proxy ID (1087968824)
    if user_id == 1087968824:
        logging.info(f"[BLOCKING] Detected anonymous admin message (user_id=1087968824)")
        return True
    
    # Also check if message has sender_chat (indicates anonymous admin or channel)
    if message and getattr(message, 'sender_chat', None):
        if message.sender_chat.id == chat_id:
            logging.info(f"[BLOCKING] Detected anonymous admin via sender_chat")
            return True
    
    return await is_user_admin(chat_id, user_id, context)

async def handle_blocking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles all blocking logic for messages."""
    if not update.effective_chat or update.effective_chat.type == "private":
        return False

    chat_id = update.effective_chat.id
    settings = get_chat_settings(chat_id)
    
    # Merge with defaults
    for key, value in DEFAULT_BLOCKING_SETTINGS.items():
        if key not in settings:
            settings[key] = value
    
    # Check if blocking is enabled
    if not settings.get("blocking_enabled", True):
        return False
    
    msg = update.effective_message
    if not msg:
        return False

    logging.info(f"[BLOCKING] Checking message in chat {chat_id}")

    should_delete = False
    penalty_reason = ""
    
    # Check Message Length (just delete, no penalties)
    if msg.text or msg.caption:
        content = (msg.text or "") + (msg.caption or "")
        length = len(content)
        min_l = settings.get("msg_length_min", 0)
        max_l = settings.get("msg_length_max", 2000)
        
        logging.info(f"[BLOCKING] Message length check: length={length}, min={min_l}, max={max_l}")
        
        if length < min_l or length > max_l:
            logging.info(f"[BLOCKING] Message length {length} outside range {min_l}-{max_l}")
            
            # Check if user is admin - admins are exempt (including anonymous admins)
            is_admin = await is_admin_or_creator(context, chat_id, update.effective_user.id if update.effective_user else 0, msg)
            if not is_admin:
                # Delete message if enabled
                if settings.get("msg_length_delete"):
                    logging.info(f"[BLOCKING] Deleting message - msg_length_delete enabled")
                    should_delete = True

    # Check if user is freed from specific blocking
    if not update.effective_user:
        return False
        
    user_id = update.effective_user.id
    user_perms = settings.get("user_permissions", {}).get(user_id, {})

    # Helper to check if user is freed from a specific block
    def is_user_freed(block_key):
        return user_perms.get(block_key, False)

    # Check for basic types
    if msg.sticker:
        is_premium = bool(msg.sticker.premium_animation or msg.sticker.custom_emoji_id)
        
        logging.info(f"[BLOCKING] Sticker detected, block_stickers={settings.get('block_stickers')}, is_premium={is_premium}")
        
        if settings.get("block_stickers") and not is_user_freed("block_stickers"):
            should_delete = True
        elif is_premium and settings.get("block_premium_sticker") and not is_user_freed("block_premium_sticker"):
            should_delete = True
    
    # Check for custom emojis and links in entities
    entities = list(msg.entities or []) + list(msg.caption_entities or [])
    for entity in entities:
        if entity.type == MessageEntity.CUSTOM_EMOJI:
            if settings.get("block_premium_sticker") and not is_user_freed("block_premium_sticker"):
                should_delete = True
        elif entity.type == MessageEntity.URL:
            if settings.get("block_link") and not is_user_freed("block_link"):
                should_delete = True
        elif entity.type == MessageEntity.TEXT_LINK:
            if settings.get("block_embed_link") and not is_user_freed("block_embed_link"):
                should_delete = True

    if msg.photo or msg.video or msg.animation:
        if settings.get("block_media") and not is_user_freed("block_media"):
            should_delete = True
            
    if msg.document:
        if settings.get("block_documents") and not is_user_freed("block_documents"):
            should_delete = True
            
    # Check for forwarded messages
    is_forwarded = (hasattr(msg, 'forward_origin') and msg.forward_origin is not None) or \
                   (hasattr(msg, 'forward_from') and msg.forward_from is not None)
    
    # Check if message is from a channel
    is_channel_post = False
    if getattr(msg, 'sender_chat', None) and msg.sender_chat.type == "channel":
        is_channel_post = True
    elif getattr(msg, 'forward_origin', None) and getattr(msg.forward_origin, 'chat', None) and msg.forward_origin.chat.type == "channel":
        is_channel_post = True
    elif getattr(msg, 'forward_from_chat', None) and msg.forward_from_chat.type == "channel":
        is_channel_post = True
    
    # Block channel posts
    if is_channel_post and settings.get("block_channel_post") and not is_user_freed("block_channel_post"):
        should_delete = True
    
    # Block forwarded messages (non-channel)
    if is_forwarded and not is_channel_post:
        if settings.get("block_forward") and not is_user_freed("block_forward"):
            should_delete = True
            
    # Check for commands (block_command)
    if msg.text and settings.get("block_command") and not is_user_freed("block_command"):
        is_command = msg.text.startswith(('/', '!', '.', '#'))
        
        if is_command:
            # Allow essential bot commands
            allowed_cmds = ("/start", "/settings", "/free", "/help", "/rules", "/me", "/info", "/link", "/report")
            is_allowed = any(msg.text.startswith(cmd) for cmd in allowed_cmds)
            
            if not is_allowed:
                should_delete = True
            
    if msg.contact and settings.get("block_contact") and not is_user_freed("block_contact"):
        should_delete = True
        
    if msg.location and settings.get("block_location") and not is_user_freed("block_location"):
        should_delete = True
        
    if msg.voice and settings.get("block_voice") and not is_user_freed("block_voice"):
        should_delete = True

    # Block music/audio files
    if msg.audio and settings.get("block_audio") and not is_user_freed("block_audio"):
        should_delete = True
        
    if msg.video_note and settings.get("block_video_note") and not is_user_freed("block_video_note"):
        should_delete = True
        
    if msg.poll and settings.get("block_poll") and not is_user_freed("block_poll"):
        should_delete = True

    if msg.dice and settings.get("block_dice") and not is_user_freed("block_dice"):
        should_delete = True

    if msg.game and settings.get("block_game") and not is_user_freed("block_game"):
        should_delete = True

    # Custom Block List (text or caption) - applies to EVERYONE including owner
    content_to_check = (msg.text or "") + (msg.caption or "")
    custom_block_matched = False
    if content_to_check and settings.get("custom_block_list"):
        for blocked_word in settings["custom_block_list"]:
            if blocked_word.lower() in content_to_check.lower():
                should_delete = True
                custom_block_matched = True
                break
    
    # Custom Block Media
    if not should_delete and settings.get("custom_block_media"):
        custom_block_media = settings.get("custom_block_media", [])
        current_file_id = None
        
        if msg.photo:
            current_file_id = msg.photo[-1].file_id
        elif msg.video:
            current_file_id = msg.video.file_id
        elif msg.document:
            current_file_id = msg.document.file_id
        elif msg.audio:
            current_file_id = msg.audio.file_id
        elif msg.voice:
            current_file_id = msg.voice.file_id
        elif msg.video_note:
            current_file_id = msg.video_note.file_id
        
        if current_file_id:
            for blocked_media in custom_block_media:
                if blocked_media.get("file_id") == current_file_id:
                    should_delete = True
                    custom_block_matched = True
                    break
    
    # Custom Block Stickers
    if not should_delete and settings.get("custom_block_stickers"):
        custom_block_stickers = settings.get("custom_block_stickers", [])
        
        if msg.sticker and msg.sticker.file_id in custom_block_stickers:
            should_delete = True
            custom_block_matched = True

    if should_delete:
        try:
            # For custom block list, delete from EVERYONE including owner/admins
            # For other blocking rules, admins/creator are exempt
            if not custom_block_matched:
                is_admin = await is_admin_or_creator(context, chat_id, update.effective_user.id, msg)
                if is_admin:
                    return False
            
            # Send notification for blocked content
            is_forwarded_msg = (hasattr(msg, 'forward_origin') and msg.forward_origin is not None) or \
                              (hasattr(msg, 'forward_from') and msg.forward_from is not None)
            
            if msg.audio and settings.get("block_audio"):
                try:
                    await msg.reply_text(
                        f"🎵 <b>Music files are not allowed in this group.</b>\n\n"
                        f"<i>Your audio file has been automatically deleted.</i>",
                        parse_mode='HTML'
                    )
                except Exception:
                    pass
            elif is_forwarded_msg and settings.get("block_forward"):
                try:
                    await msg.reply_text(
                        f"⚠️ <b>Forwarded messages are not allowed in this group.</b>\n\n"
                        f"<i>Your forwarded message has been automatically deleted.</i>",
                        parse_mode='HTML'
                    )
                except Exception:
                    pass
                
            await msg.delete()
            return True
        except Exception as e:
            logging.error(f"Error deleting blocked message: {e}")
            
    return False

async def handle_clean_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles cleaning service messages."""
    if not update.effective_chat or update.effective_chat.type == "private":
        return False

    chat_id = update.effective_chat.id
    settings = get_chat_settings(chat_id)
    
    # Merge with defaults
    for key, value in DEFAULT_BLOCKING_SETTINGS.items():
        if key not in settings:
            settings[key] = value
    
    if not settings.get("clean_service_enabled", True):
        return False
    
    msg = update.effective_message
    if not msg:
        return False

    should_delete = False

    if msg.new_chat_members and settings.get("clean_join"):
        should_delete = True
    elif msg.left_chat_member and settings.get("clean_left"):
        should_delete = True
    elif msg.new_chat_title and settings.get("clean_title"):
        should_delete = True
    elif (msg.new_chat_photo or msg.delete_chat_photo) and settings.get("clean_photo"):
        should_delete = True
    elif (getattr(msg, 'video_chat_started', None) or getattr(msg, 'voice_chat_started', None)) and settings.get("clean_voice_start"):
        should_delete = True
    elif (getattr(msg, 'video_chat_ended', None) or getattr(msg, 'voice_chat_ended', None)) and settings.get("clean_voice_end"):
        should_delete = True
    elif (getattr(msg, 'video_chat_scheduled', None) or getattr(msg, 'voice_chat_scheduled', None)) and settings.get("clean_voice_schedule"):
        should_delete = True
    elif (getattr(msg, 'video_chat_participants_invited', None) or getattr(msg, 'voice_chat_participants_invited', None)) and settings.get("clean_voice_invite"):
        should_delete = True
    elif msg.pinned_message and settings.get("clean_pinned"):
        should_delete = True

    if should_delete:
        try:
            await msg.delete()
            return True
        except Exception as e:
            logging.error(f"Error deleting service message: {e}")
            
    return False

async def free_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to exempt a user from specific blocking rules."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Only admins can use this command
    if user_id != OWNER_ID and not await is_user_admin(chat_id, user_id, context):
        await send_bot_response(update, context, "Only admins can use the /free command.")
        return
    
    # Check if replying to a user
    if not update.message.reply_to_message:
        await send_bot_response(update, context, 
            "Usage: Reply to a user's message with /free\n\n"
            "This will exempt them from all blocking rules.")
        return
    
    target_user = update.message.reply_to_message.from_user
    if not target_user:
        await send_bot_response(update, context, "Could not find the user to free.")
        return
    
    # Get current settings
    settings = get_chat_settings(chat_id)
    user_permissions = settings.get("user_permissions", {})
    
    # Check if user is already freed
    already_freed = str(target_user.id) in user_permissions
    
    # Grant all exemptions
    exemptions = {
        "block_stickers": True,
        "block_premium_sticker": True,
        "block_link": True,
        "block_embed_link": True,
        "block_media": True,
        "block_documents": True,
        "block_forward": True,
        "block_channel_post": True,
        "block_command": True,
        "block_contact": True,
        "block_location": True,
        "block_voice": True,
        "block_audio": True,
        "block_video_note": True,
        "block_poll": True,
        "block_dice": True,
        "block_game": True,
    }
    
    # Store with string key for MongoDB compatibility
    user_permissions[str(target_user.id)] = exemptions
    
    # Update settings
    update_chat_setting(chat_id, "user_permissions", user_permissions)
    
    # Create keyboard with permission button
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛡 Permissions", callback_data=f"free_perms_{target_user.id}")]
    ])
    
    # Show different message based on whether user was already freed
    if already_freed:
        message_text = (
            f"[{target_user.id}] ᴡɪʟʟ ʙᴇ ᴀʟʀᴇᴀᴅʏ ꜰʀᴇᴇᴅ!\n\n"
            f"💡 ʏᴏᴜ ᴄᴀɴ ꜱᴛɪʟʟ ᴍᴀɴᴀɢᴇ ᴛʜᴇɪʀ ʙʟᴏᴄᴋɪɴɢ ᴘᴇʀᴍɪꜱꜱɪᴏɴꜱ ʙᴇʟᴏᴡ:"
        )
    else:
        message_text = (
            f"[{target_user.id}] ᴡɪʟʟ ʙᴇ ꜰʀᴇᴇᴅ ꜰʀᴏᴍ ʙʟᴏᴄᴋɪɴɢ :\n\n"
            f"💡 ʏᴏᴜ ᴄᴀɴ ꜱᴛɪʟʟ ᴍᴀɴᴀɢᴇ ᴛʜᴇɪʀ ʙʟᴏᴄᴋɪɴɢ ᴘᴇʀᴍɪꜱꜱɪᴏɴꜱ ʙᴇʟᴏᴡ:"
        )
    
    await send_bot_response(update, context, message_text, reply_markup=keyboard)

async def unfree_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to remove exemptions from a user."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Only admins can use this command
    if user_id != OWNER_ID and not await is_user_admin(chat_id, user_id, context):
        await send_bot_response(update, context, "Only admins can use the /unfree command.")
        return
    
    # Check if replying to a user
    if not update.message.reply_to_message:
        await send_bot_response(update, context, 
            "Usage: Reply to a user's message with /unfree\n\n"
            "This will remove all blocking exemptions from them.")
        return
    
    target_user = update.message.reply_to_message.from_user
    if not target_user:
        await send_bot_response(update, context, "Could not find the user.")
        return
    
    # Get current settings
    settings = get_chat_settings(chat_id)
    user_permissions = settings.get("user_permissions", {})
    
    # Remove user from permissions
    user_id_str = str(target_user.id)
    if user_id_str in user_permissions:
        del user_permissions[user_id_str]
        update_chat_setting(chat_id, "user_permissions", user_permissions)
        await send_bot_response(update, context, 
            f"❌ <b>{target_user.first_name}</b> is no longer exempt from blocking rules.")
    else:
        await send_bot_response(update, context, 
            f"ℹ️ <b>{target_user.first_name}</b> is not exempt from any blocking rules.")

def get_blocking_handlers():
    """Return all blocking handlers."""
    return [
        CommandHandler("free", free_command),
        CommandHandler("unfree", unfree_command),
        CallbackQueryHandler(free_permission_callback, pattern="^free_perms_"),
        CallbackQueryHandler(free_permission_toggle, pattern="^free_toggle_"),
        CallbackQueryHandler(free_permission_save, pattern="^free_save_"),
        MessageHandler(filters.ALL & filters.ChatType.GROUPS, handle_message_blocking),
    ]

async def handle_message_blocking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wrapper to handle both blocking and clean service."""
    # Cache user
    if update.effective_user:
        user = update.effective_user
        cache_user(user.id, user.username, user.first_name)
    
    # Handle blocking
    await handle_blocking(update, context)
    
    # Handle clean service
    await handle_clean_service(update, context)

def get_user_permission_keyboard(user_id, settings):
    """Get keyboard for user permission settings."""
    # Convert to string for MongoDB compatibility
    user_id_str = str(user_id)
    user_perms = settings.get("user_permissions", {}).get(user_id_str, {})
    
    logging.info(f"[KEYBOARD] Building keyboard for user {user_id_str}, perms: {user_perms}")
    
    # Blocking options in grid format - shortened for mobile
    # Default is True (blocked ❌), False means allowed ✅
    blocking_options = [
        ("block_stickers", "🎫 Stickers"),
        ("block_premium_sticker", "✨ Premium"),
        ("block_link", "🔗 Links"),
        ("block_embed_link", "🔘 Embed"),
        ("block_media", "🖼️ Media"),
        ("block_documents", "📄 Files"),
        ("block_audio", "🎵 Audio"),
        ("block_forward", "🔄 Fwd"),
        ("block_channel_post", "📢 Channel"),
        ("block_command", "⌨️ Cmds"),
        ("block_contact", "📱 Contact"),
        ("block_location", "📍 Location"),
        ("block_voice", "🎤 Voice"),
        ("block_video_note", "📹 Video"),
        ("block_poll", "📊 Poll"),
        ("block_dice", "🎲 Dice"),
        ("block_game", "🎮 Game"),
    ]
    
    keyboard = []
    for i in range(0, len(blocking_options), 2):
        row = []
        key1, label1 = blocking_options[i]
        # Default is True (blocked ❌), False means allowed ✅
        value1 = user_perms.get(key1, True)
        status1 = "❌" if value1 else "✅"
        logging.info(f"[KEYBOARD] {key1}: value={value1}, status={status1}")
        row.append(InlineKeyboardButton(f"{label1} {status1}", callback_data=f"free_toggle_{user_id}_{key1}"))
        
        if i + 1 < len(blocking_options):
            key2, label2 = blocking_options[i + 1]
            value2 = user_perms.get(key2, True)
            status2 = "❌" if value2 else "✅"
            logging.info(f"[KEYBOARD] {key2}: value={value2}, status={status2}")
            row.append(InlineKeyboardButton(f"{label2} {status2}", callback_data=f"free_toggle_{user_id}_{key2}"))
        
        keyboard.append(row)
    
    # Add save and back buttons
    keyboard.append([InlineKeyboardButton("💾 Save", callback_data=f"free_save_{user_id}")])
    
    return InlineKeyboardMarkup(keyboard)

async def free_permission_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show permission settings for a freed user."""
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split("_")[-1])
    chat_id = update.effective_chat.id
    
    settings = get_chat_settings(chat_id)
    
    try:
        chat = await context.bot.get_chat(user_id)
        user_name = chat.first_name or "Unknown"
    except:
        user_name = "Unknown User"
    
    message_text = (
        f"🛡 <b>ʙʟᴏᴄᴋɪɴɢ ꜱᴇᴛᴛɪɴɢꜱ 🛡</b>\n\n"
        f"[{user_id}] ᴡɪʟʟ ʙᴇ ᴇxᴇᴍᴘᴛᴇᴅ ꜰʀᴏᴍ:\n\n"
        f"ᴛᴏɢɢʟᴇ ꜰᴇᴀᴛᴜʀᴇꜱ ᴛᴏ ʙʟᴏᴄᴋ ᴄᴏɴᴛᴇɴᴛ:"
    )
    
    keyboard = get_user_permission_keyboard(user_id, settings)
    
    try:
        await query.edit_message_text(message_text, reply_markup=keyboard, parse_mode='HTML')
    except:
        await query.message.edit_text(message_text, reply_markup=keyboard, parse_mode='HTML')

async def free_permission_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle a permission for a user."""
    query = update.callback_query
    await query.answer()
    
    # Parse user_id and permission key
    # Callback data format: free_toggle_{user_id}_{perm_key}
    # perm_key can contain underscores (e.g., block_stickers), so we need to handle that
    parts = query.data.split("_")
    user_id = int(parts[2])
    user_id_str = str(user_id)
    # Join all parts after index 2 to get the full permission key
    perm_key = "_".join(parts[3:])
    
    chat_id = update.effective_chat.id
    settings = get_chat_settings(chat_id)
    
    logging.info(f"[TOGGLE] Starting toggle for user {user_id_str}, key: {perm_key}")
    logging.info(f"[TOGGLE] Callback data: {query.data}")
    logging.info(f"[TOGGLE] Split parts: {parts}")
    
    # Always get fresh permissions from database first
    user_permissions = settings.get("user_permissions", {})
    logging.info(f"[TOGGLE] DB permissions: {user_permissions.get(user_id_str, {})}")
    
    # If we have temporary changes, merge them
    temp_perms = context.user_data.get(f'free_perms_{chat_id}_{user_id_str}')
    if temp_perms:
        logging.info(f"[TOGGLE] Found temp perms: {temp_perms}")
        user_permissions[user_id_str] = temp_perms
    
    # Initialize user permissions if not exists
    if user_id_str not in user_permissions:
        user_permissions[user_id_str] = {}
    
    # Get current value and toggle it
    current_value = user_permissions[user_id_str].get(perm_key, True)
    new_value = not current_value
    user_permissions[user_id_str][perm_key] = new_value
    
    logging.info(f"[TOGGLE] {perm_key} changed from {current_value} to {new_value}")
    logging.info(f"[TOGGLE] Updated user perms: {user_permissions[user_id_str]}")
    
    # Store updated permissions in user_data temporarily
    context.user_data[f'free_perms_{chat_id}_{user_id_str}'] = user_permissions[user_id_str]
    
    # Refresh the keyboard with updated permissions
    # Create a deep copy of settings to avoid modifying the original
    import copy
    temp_settings = copy.deepcopy(settings)
    
    # Ensure user_permissions exists and has the updated values
    if 'user_permissions' not in temp_settings:
        temp_settings['user_permissions'] = {}
    
    # Update the specific user's permissions
    temp_settings['user_permissions'][user_id_str] = user_permissions[user_id_str]
    
    logging.info(f"[TOGGLE] Refreshing keyboard with permissions: {temp_settings['user_permissions'][user_id_str]}")
    
    keyboard = get_user_permission_keyboard(user_id, temp_settings)
    
    try:
        await query.edit_message_reply_markup(reply_markup=keyboard)
        logging.info(f"[TOGGLE] Keyboard updated successfully")
    except Exception as e:
        if "not modified" not in str(e).lower():
            logging.error(f"[TOGGLE] Error updating keyboard: {e}")
        pass

async def free_permission_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save permission changes for a user."""
    query = update.callback_query
    
    user_id = int(query.data.split("_")[-1])
    user_id_str = str(user_id)
    chat_id = update.effective_chat.id
    
    # Get temporary permissions from user_data or use current
    settings = get_chat_settings(chat_id)
    temp_perms = context.user_data.get(f'free_perms_{chat_id}_{user_id_str}')
    
    if temp_perms:
        user_permissions = settings.get("user_permissions", {})
        user_permissions[user_id_str] = temp_perms
        update_chat_setting(chat_id, "user_permissions", user_permissions)
        
        # Clear temporary data
        if f'free_perms_{chat_id}_{user_id_str}' in context.user_data:
            del context.user_data[f'free_perms_{chat_id}_{user_id_str}']
    
    await query.answer("✅ Permissions saved!", show_alert=True)
    
    # Delete the message after saving
    try:
        await query.message.delete()
    except:
        pass
