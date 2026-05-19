from telegram import Update, MessageEntity, InlineKeyboardButton, InlineKeyboardMarkup, ReactionTypeEmoji
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, MessageReactionHandler, filters
from telegram.constants import ParseMode
from datetime import datetime, timedelta
import logging
import copy
import random
import asyncio
import re
import httpx

from config import OWNER_ID, send_bot_response
from settings_manager_mongo import get_chat_settings, update_chat_setting
from user_manager_mongo import is_user_admin, cache_user, can_user_configure_settings
from moderation import can_user_ban

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
    "block_reactions": False,
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

def get_random_premium_emoji():
    """Returns a random premium-looking emoji for UI enhancement."""
    emojis = ["💎", "✨", "🌟", "🛡️", "🔥", "👑", "⚡", "🎯", "🚀", "🌈", "✅"]
    return random.choice(emojis)

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
    
    # DEBUG: Log what get_chat_settings returns
    has_user_perms = 'user_permissions' in settings
    user_perms_count = len(settings.get('user_permissions', {}))
    logging.info(f"[DEBUG] get_chat_settings returned: has_user_permissions={has_user_perms}, count={user_perms_count}")
    
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
    user_perms = settings.get("user_permissions", {}).get(str(user_id), {})
    
    # Debug logging
    logging.info(f"[BLOCKING] User {user_id}, user_perms={user_perms}")

    # Helper to check if user is freed from a specific block
    def is_user_freed(block_key):
        # In user_permissions, True means freed/allowed, False/missing means blocked
        freed = user_perms.get(block_key, False)
        logging.info(f"[BLOCKING] is_user_freed({block_key}) = {freed}")
        return freed

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

async def resolve_user(context, chat_id, arg=None, reply_to_message=None):
    """Resolve a user from reply, user ID, or username."""
    # Method 1: Reply to a message
    if reply_to_message and reply_to_message.from_user:
        return reply_to_message.from_user
    
    # Method 2 & 3: User ID or username from argument
    if arg:
        # Check if it's a mention from entities
        if isinstance(arg, str) and arg.startswith('@'):
            from user_manager_mongo import resolve_username
            user_id, first_name = resolve_username(arg)
            if user_id:
                try:
                    chat = await context.bot.get_chat(user_id)
                    return chat
                except:
                    # If bot can't get chat, return a dummy object with id and first_name
                    class DummyUser:
                        def __init__(self, id, first_name):
                            self.id = id
                            self.first_name = first_name
                            self.username = arg.replace('@', '')
                    return DummyUser(user_id, first_name)

        # Remove @ if present for ID/Username lookup
        clean_arg = str(arg).replace('@', '')
        
        # Try to parse as user ID
        try:
            user_id = int(clean_arg)
            chat = await context.bot.get_chat(user_id)
            return chat
        except (ValueError, Exception) as e:
            logging.info(f"Could not resolve as user ID: {e}")
        
        # Try to resolve as username via bot
        try:
            chat = await context.bot.get_chat(f'@{clean_arg}')
            return chat
        except Exception as e:
            logging.info(f"Could not resolve as username: {e}")
            
        # Try to resolve via database cache as last resort
        from user_manager_mongo import resolve_username
        user_id, first_name = resolve_username(clean_arg)
        if user_id:
            class DummyUser:
                def __init__(self, id, first_name):
                    self.id = id
                    self.first_name = first_name
                    self.username = clean_arg
            return DummyUser(user_id, first_name)
    
    return None

async def free_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to exempt a user from specific blocking rules."""
    if not update.effective_chat:
        return
        
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    logging.info(f"[FREE] Processing command for chat {chat_id}, user {user_id}")
    
    # Only admins with specific permissions can use this command
    can_ban, error_msg = await can_user_ban(chat_id, user_id, context)
    logging.info(f"[FREE] Permission check result: {can_ban}, error: {error_msg}")
    if not can_ban:
        await send_bot_response(update, context, error_msg or "Only admins with 'Ban Users' permission can use the /free command.")
        return
    
    # Try to resolve the target user
    target_user = None
    
    # Check if there's an argument (user ID or username)
    if context.args:
        arg = context.args[0]
        target_user = await resolve_user(context, chat_id, arg=arg, reply_to_message=update.message.reply_to_message if update.message else None)
    elif update.message and update.message.reply_to_message:
        # No argument, check for reply
        target_user = await resolve_user(context, chat_id, reply_to_message=update.message.reply_to_message)
    
    if not target_user:
        await send_bot_response(update, context, 
            "Usage:\n"
            "• Reply to a user's message with /free\n"
            "• /free <user_id> - e.g., /free 123456789\n"
            "• /free @username - e.g., /free @exampleuser\n\n"
            "This will exempt them from all blocking rules.")
        return
    
    # Get current settings
    settings = get_chat_settings(chat_id)
    user_permissions = settings.get("user_permissions", {})
    
    # Check if user is already freed
    user_id_str = str(target_user.id)
    already_freed = user_id_str in user_permissions
    
    # Define labels for permissions
    blocking_labels = {
        "block_stickers": "🎫 Stickers",
        "block_premium_sticker": "✨ Premium",
        "block_link": "🔗 Links",
        "block_embed_link": "🔘 Embed",
        "block_media": "🖼️ Media",
        "block_documents": "📄 Files",
        "block_audio": "🎵 Audio",
        "block_forward": "🔄 Fwd",
        "block_channel_post": "📢 Channel",
        "block_command": "⌨️ Cmds",
        "block_contact": "📱 Contact",
        "block_location": "📍 Location",
        "block_voice": "🎤 Voice",
        "block_video_note": "📹 Video",
        "block_poll": "📊 Poll",
        "block_dice": "🎲 Dice",
        "block_game": "🎮 Game",
        "block_reactions": "⚡ React",
    }
    
    user_name = getattr(target_user, 'first_name', f"User {target_user.id}")
    if already_freed:
        # Get existing exemptions
        exemptions = user_permissions[user_id_str]
        
        # List which ones are freed (True)
        freed_list = []
        for key, label in blocking_labels.items():
            if exemptions.get(key, False):
                freed_list.append(f"• {label} ✅")
        
        random_emoji = get_random_premium_emoji()
        if freed_list:
            freed_text = "\n".join(freed_list)
            message_text = (
                f"{random_emoji} <b>{user_name}</b> (<code>{target_user.id}</code>) ɪꜱ ᴀʟʀᴇᴀᴅʏ ꜰʀᴇᴇᴅ!\n\n"
                f"<b>📊 ᴄᴜʀʀᴇɴᴛ ᴇxᴇᴍᴘᴛɪᴏɴꜱ:</b>\n{freed_text}\n\n"
                f"💡 ʏᴏᴜ ᴄᴀɴ ꜱᴛɪʟʟ ᴍᴀɴᴀɢᴇ ᴛʜᴇɪʀ ʙʟᴏᴄᴋɪɴɢ ᴘᴇʀᴍɪꜱꜱɪᴏɴꜱ ʙᴇʟᴏᴡ:"
            )
        else:
            message_text = (
                f"{random_emoji} <b>{user_name}</b> (<code>{target_user.id}</code>) ʜᴀꜱ ᴀ ꜰʀᴇᴇ ʀᴇᴄᴏʀᴅ ʙᴜᴛ ɴᴏ ᴀᴄᴛɪᴠᴇ ᴇxᴇᴍᴘᴛɪᴏɴꜱ.\n\n"
                f"💡 ꜱᴇʟᴇᴄᴛ ꜰᴇᴀᴛᴜʀᴇꜱ ᴛᴏ ᴇxᴇᴍᴘᴛ ᴛʜᴇᴍ ꜰʀᴏᴍ ʙʟᴏᴄᴋɪɴɢ:"
            )
    else:
        # New entry - start with no exemptions
        random_emoji = get_random_premium_emoji()
        message_text = (
            f"{random_emoji} ꜱᴇʟᴇᴄᴛ ʙʟᴏᴄᴋɪɴɢ ᴇxᴇᴍᴘᴛɪᴏɴꜱ ꜰᴏʀ <b>{user_name}</b> (<code>{target_user.id}</code>):\n\n"
            f"ᴛᴏɢɢʟᴇ ꜰᴇᴀᴛᴜʀᴇꜱ ᴛᴏ ᴀʟʟᴏᴡ ᴛʜᴇᴍ ᴛᴏ ꜱᴇɴᴅ ᴄᴏɴᴛᴇɴᴛ:"
        )
    
    # Create keyboard with permission button
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛡 Permissions", callback_data=f"free_perms_{chat_id}_{target_user.id}")]
    ])
    
    await send_bot_response(update, context, message_text, reply_markup=keyboard, parse_mode="HTML")

async def unfree_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to remove exemptions from a user."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Only admins with specific permissions can use this command
    can_ban, error_msg = await can_user_ban(chat_id, user_id, context)
    if not can_ban:
        await send_bot_response(update, context, error_msg or "Only admins with 'Ban Users' permission can use the /unfree command.")
        return
    
    # Try to resolve target user
    target_user = None
    if context.args:
        arg = context.args[0]
        target_user = await resolve_user(context, chat_id, arg=arg, reply_to_message=update.message.reply_to_message if update.message else None)
    elif update.message and update.message.reply_to_message:
        target_user = await resolve_user(context, chat_id, reply_to_message=update.message.reply_to_message)

    if not target_user:
        await send_bot_response(update, context, 
            "Usage:\n"
            "• Reply to a user's message with /unfree\n"
            "• /unfree <user_id>\n"
            "• /unfree @username\n\n"
            "This will remove all blocking exemptions from them.")
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
            f"❌ <b>{getattr(target_user, 'first_name', 'User')}</b> is no longer exempt from blocking rules.")
    else:
        await send_bot_response(update, context, 
            f"ℹ️ <b>{getattr(target_user, 'first_name', 'User')}</b> is not exempt from any blocking rules.")

async def list_freed_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback to show the list of freed members and their exemptions."""
    query = update.callback_query
    chat_id = context.user_data.get('settings_chat_id', update.effective_chat.id)
    user_id = update.effective_user.id
    
    # Only admins with specific permissions can use this
    can_ban, _ = await can_user_ban(chat_id, user_id, context)
    if not can_ban:
        await query.answer("You don't have permission to view freed members.", show_alert=True)
        return
    
    await query.answer()
    
    settings = get_chat_settings(chat_id)
    user_permissions = settings.get("user_permissions", {})
    
    if not user_permissions:
        text = "📋 <b>ꜰʀᴇᴇᴅ ᴍᴇᴍʙᴇʀꜱ ʟɪꜱᴛ</b>\n\nɴᴏ ᴍᴇᴍʙᴇʀꜱ ᴀʀᴇ ᴄᴜʀʀᴇɴᴛʟʏ ᴇxᴇᴍᴘᴛᴇᴅ ꜰʀᴏᴍ ʙʟᴏᴄᴋɪɴɢ ʀᴜʟᴇꜱ."
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="set_view_blocking")]])
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='HTML')
        return

    text = "📋 <b>ꜰʀᴇᴇᴅ ᴍᴇᴍʙᴇʀꜱ ʟɪꜱᴛ</b>\n\nꜱᴇʟᴇᴄᴛ ᴀ ᴍᴇᴍʙᴇʀ ᴛᴏ ᴍᴀɴᴀɢᴇ ᴛʜᴇɪʀ ᴇxᴇᴍᴘᴛɪᴏɴꜱ:\n\n"
    keyboard_buttons = []
    
    # Define labels for permissions (same as in free_command)
    blocking_labels = {
        "block_stickers": "🎫",
        "block_premium_sticker": "✨",
        "block_link": "🔗",
        "block_embed_link": "🔘",
        "block_media": "🖼️",
        "block_documents": "📄",
        "block_audio": "🎵",
        "block_forward": "🔄",
        "block_channel_post": "📢",
        "block_command": "⌨️",
        "block_contact": "📱",
        "block_location": "📍",
        "block_voice": "🎤",
        "block_video_note": "📹",
        "block_poll": "📊",
        "block_dice": "🎲",
        "block_game": "🎮",
        "block_reactions": "⚡",
    }

    from user_manager_mongo import resolve_username
    
    for uid_str, perms in user_permissions.items():
        # Get user name from cache or bot
        try:
            uid = int(uid_str)
            user_name = f"User {uid}"
            
            # Try cache first
            cached_id, cached_name = resolve_username(uid_str)
            if cached_name:
                user_name = cached_name
            else:
                # Try bot
                try:
                    chat = await context.bot.get_chat(uid)
                    user_name = chat.first_name or chat.title or user_name
                except:
                    pass
            
            # Count active exemptions
            active_exemptions = [blocking_labels[k] for k, v in perms.items() if v and k in blocking_labels]
            exempt_str = " ".join(active_exemptions) if active_exemptions else "None"
            
            keyboard_buttons.append([InlineKeyboardButton(f"👤 {user_name} ({len(active_exemptions)})", callback_data=f"free_perms_{chat_id}_{uid}")])
            text += f"• <b>{user_name}</b> (<code>{uid}</code>)\n  └ ᴇxᴇᴍᴘᴛ: {exempt_str}\n\n"
        except:
            continue

    keyboard_buttons.append([InlineKeyboardButton("🔙 Back", callback_data="set_view_blocking")])
    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode='HTML')

async def handle_reaction_blocking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detects and warns about unauthorized reactions if blocking is enabled."""
    reaction_update = update.message_reaction
    if not reaction_update:
        return

    chat_id = reaction_update.chat.id
    user = reaction_update.user
    
    logging.info(f"[REACTION] Received reaction update in {chat_id} from {user.id if user else 'Unknown'}")

    # If it's an anonymous reaction or no user, we might not be able to identify
    if not user:
        return

    settings = get_chat_settings(chat_id)
    if not settings.get("blocking_enabled", True) or not settings.get("block_reactions", False):
        return

    logging.info(f"[REACTION] Reaction blocking is ENABLED in {chat_id}")

    # Admins are exempt
    is_admin = await is_user_admin(chat_id, user.id, context)
    if is_admin:
        logging.info(f"[REACTION] User {user.id} is admin, exempt.")
        return

    # Freed users are exempt
    user_perms = settings.get("user_permissions", {}).get(str(user.id), {})
    if user_perms.get("block_reactions", False):
        logging.info(f"[REACTION] User {user.id} is freed, exempt.")
        return

    # If we reached here, the reaction is unauthorized
    logging.info(f"[REACTION] Attempting to delete unauthorized reaction from {user.id} in {chat_id}")
    try:
        # Check if bot has permission to delete messages (required for reaction deletion)
        bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        if not (bot_member.status == 'administrator' and getattr(bot_member, 'can_delete_messages', False)):
            logging.warning(f"Bot lacks 'can_delete_messages' in {chat_id}, cannot delete reaction.")
            return

        # 1. Attempt to DELETE the reaction (Bot API 7.0+)
        # We use the built-in library method for speed and efficiency
        try:
            await context.bot.delete_message_reaction(
                chat_id=chat_id,
                message_id=reaction_update.message_id,
                user_id=user.id
            )
            logging.info(f"✅ Successfully deleted reaction from user {user.id} in chat {chat_id}")
        except Exception as e:
            logging.warning(f"Failed to delete reaction via library: {e}")
            # Fallback to direct API if needed (sometimes library methods might have issues with specific versions)
            from config import BOT_TOKEN
            async with httpx.AsyncClient() as client:
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessageReaction"
                params = {"chat_id": chat_id, "message_id": reaction_update.message_id, "user_id": user.id}
                resp = await client.post(url, json=params)
                if not resp.json().get("ok"):
                    logging.error(f"Fallback direct API also failed: {resp.json().get('description')}")
                    return

    except Exception as e:
        logging.error(f"Error handling reaction blocking in {chat_id}: {e}")

def get_blocking_handlers():
    """Return only the message blocking handler for Group 12."""
    return [
        MessageHandler(filters.ALL & filters.ChatType.GROUPS, handle_message_blocking),
    ]

def get_blocking_command_handlers():
    """Return blocking command and callback handlers for Group 0."""
    return [
        CommandHandler("free", free_command),
        CommandHandler("unfree", unfree_command),
        CallbackQueryHandler(free_permission_callback, pattern=r"^free_perms_"),
        CallbackQueryHandler(free_permission_toggle, pattern=r"^free_toggle_"),
        CallbackQueryHandler(free_permission_save, pattern=r"^free_save_"),
        CallbackQueryHandler(list_freed_members, pattern=r"^free_list_members$"),
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

def get_user_permission_keyboard(chat_id, user_id, settings):
    """Get keyboard for user permission settings."""
    # Convert to string for MongoDB compatibility
    user_id_str = str(user_id)
    user_perms = settings.get("user_permissions", {}).get(user_id_str, {})
    
    logging.info(f"[KEYBOARD] Building keyboard for chat {chat_id}, user {user_id_str}, perms: {user_perms}")
    
    # Blocking options in grid format - shortened for mobile
    # True = FREED/ALLOWED ✅, False = BLOCKED ❌
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
        ("block_reactions", "⚡ React"),
    ]
    
    keyboard = []
    for i in range(0, len(blocking_options), 2):
        row = []
        key1, label1 = blocking_options[i]
        # True = FREED/ALLOWED ✅, False = BLOCKED ❌
        value1 = user_perms.get(key1, False)
        status1 = "✅" if value1 else "❌"
        row.append(InlineKeyboardButton(f"{label1} {status1}", callback_data=f"free_toggle_{chat_id}_{user_id}_{key1}"))
        
        if i + 1 < len(blocking_options):
            key2, label2 = blocking_options[i + 1]
            value2 = user_perms.get(key2, False)
            status2 = "✅" if value2 else "❌"
            row.append(InlineKeyboardButton(f"{label2} {status2}", callback_data=f"free_toggle_{chat_id}_{user_id}_{key2}"))
        
        keyboard.append(row)
    
    # Add save and back buttons
    keyboard.append([InlineKeyboardButton("💾 Save", callback_data=f"free_save_{chat_id}_{user_id}")])
    
    return InlineKeyboardMarkup(keyboard)

async def free_permission_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show permission settings for a freed user."""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    # Callback data format: free_perms_{chat_id}_{user_id}
    parts = query.data.split("_")
    chat_id = int(parts[2])
    target_user_id = int(parts[3])
    
    # Check permissions
    can_ban, _ = await can_user_ban(chat_id, admin_id, context)
    if not can_ban:
        await query.answer("You don't have permission to manage exemptions.", show_alert=True)
        return

    await query.answer()
    
    settings = get_chat_settings(chat_id)
    
    try:
        chat = await context.bot.get_chat(target_user_id)
        user_name = chat.first_name or "Unknown"
    except:
        user_name = "Unknown User"
    
    message_text = (
        f"🛡 <b>ʙʟᴏᴄᴋɪɴɢ ꜱᴇᴛᴛɪɴɢꜱ 🛡</b>\n\n"
        f"<b>{user_name}</b> (<code>{target_user_id}</code>) ᴡɪʟʟ ʙᴇ ᴇxᴇᴍᴘᴛᴇᴅ ꜰʀᴏᴍ:\n\n"
        f"ᴛᴏɢɢʟᴇ ꜰᴇᴀᴛᴜʀᴇꜱ ᴛᴏ ʙʟᴏᴄᴋ ᴄᴏɴᴛᴇɴᴛ:"
    )
    
    keyboard = get_user_permission_keyboard(chat_id, target_user_id, settings)
    
    try:
        await query.edit_message_text(message_text, reply_markup=keyboard, parse_mode='HTML')
    except:
        await query.message.edit_text(message_text, reply_markup=keyboard, parse_mode='HTML')

async def free_permission_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle a permission for a user and auto-save to database."""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    # Callback data format: free_toggle_{chat_id}_{user_id}_{perm_key}
    parts = query.data.split("_")
    chat_id = int(parts[2])
    user_id = int(parts[3])
    user_id_str = str(user_id)
    # Join all parts after index 3 to get the full permission key
    perm_key = "_".join(parts[4:])
    
    # Check permissions
    can_ban, _ = await can_user_ban(chat_id, admin_id, context)
    if not can_ban:
        await query.answer("You don't have permission to manage exemptions.", show_alert=True)
        return

    await query.answer()
    
    settings = get_chat_settings(chat_id)
    
    logging.info(f"[TOGGLE] Starting toggle for chat {chat_id}, user {user_id_str}, key: {perm_key}")
    
    # Get current permissions from database
    user_permissions = settings.get("user_permissions", {})
    
    # Initialize user permissions if not exists
    if user_id_str not in user_permissions:
        user_permissions[user_id_str] = {}
    
    # Get current value and toggle it
    current_value = user_permissions[user_id_str].get(perm_key, False)
    new_value = not current_value
    user_permissions[user_id_str][perm_key] = new_value
    
    logging.info(f"[TOGGLE] {perm_key} changed from {current_value} to {new_value}")
    
    # AUTO-SAVE to database immediately
    update_chat_setting(chat_id, "user_permissions", user_permissions)
    logging.info(f"[TOGGLE] Auto-saved to database for user {user_id_str} in chat {chat_id}")
    
    # Refresh the keyboard with updated permissions
    import copy
    temp_settings = copy.deepcopy(settings)
    if 'user_permissions' not in temp_settings:
        temp_settings['user_permissions'] = {}
    temp_settings['user_permissions'][user_id_str] = user_permissions[user_id_str]
    
    keyboard = get_user_permission_keyboard(chat_id, user_id, temp_settings)
    
    try:
        await query.edit_message_reply_markup(reply_markup=keyboard)
    except Exception as e:
        if "not modified" not in str(e).lower():
            logging.error(f"[TOGGLE] Error updating keyboard: {e}")

async def free_permission_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save permission changes for a user (now just closes the panel since auto-save is enabled)."""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    # Callback data format: free_save_{chat_id}_{user_id}
    parts = query.data.split("_")
    chat_id = int(parts[2])
    user_id = int(parts[3])
    user_id_str = str(user_id)
    
    # Check permissions
    can_ban, _ = await can_user_ban(chat_id, admin_id, context)
    if not can_ban:
        await query.answer("You don't have permission to manage exemptions.", show_alert=True)
        return
    
    await query.answer("Settings saved!")
    
    # Delete the message after saving
    try:
        await query.message.delete()
    except:
        pass
