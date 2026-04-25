from telegram import Update, MessageEntity, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.constants import ParseMode
from datetime import datetime, timedelta
import logging
import copy
import random

# List of premium emojis for random selection
PREMIUM_EMOJIS = [
    ('✈️', '6028346797368283073'), ('🍏', '5775870512127283512'), ('⭐️', '6028338546736107668'), ('⭐️', '5767199127775481841'), 
    ('🎁', '5773677501825945508'), ('🔣', '6035162669948867129'), ('🖥', '5942734685976138521'), ('⚙️', '5904258298764334001'), 
    ('⚙', '6032742198179532882'), ('⚙️', '5850309953293653168'), ('⚙️', '5850332476102153487'), ('⚙️', '5850392884817172292'), 
    ('⚙️', '5850224242926295392'), ('⚙️', '5924722061288150929'), ('🎛', '5776424837786374634'), ('🎛', '5771449289972650710'), 
    ('📰', '5895519358871932592'), ('📰', '5893444447286334441'), ('📰', '5886437972647088483'), ('📰', '5893236738372932548'), 
    ('📰', '5893057118545646106'), ('📝', '5920046907782074235'), ('📝', '5922693616953725714'), ('🗂', '5766994197705921104'), 
    ('↔️', '5893316448670978477'), ('↔️', '5895534923833413814'), ('⬅️', '5960671702059848143'), ('🔁', '6030657343744644592'), 
    ('⏫', '5938437708635443119'), ('✏️', '6039779802741739617'), ('✏', '6039614175917903752'), ('❌', '6030757850274336631'), 
    ('⌨', '6039404727542747508'), ('📎', '6039451237743595514'), ('🔧', '5962952497197748583'), ('🔨', '5940433880585605708'), 
    ('🚪', '6035130900075777681'), ('🔎', '6032850693348399258'), ('🏷', '5888620056551625531'), ('🏷', '5886285355279193209'), 
    ('🏷', '5884050696679986441'), ('🏷', '5884090188904272855'), ('🏷', '5886473311637999700'), ('🏷', '5888880224195581055'), 
    ('🏷', '5884491244360438851'), ('↩️', '5895507195524550741'), ('⬅️', '6039539366177541657'), ('➡️', '5895383238473421210'), 
    ('➡️', '6037622221625626773'), ('📺', '6039391078136681499'), ('🔗', '6028171274939797252'), ('🔗', '6030864215139422409'), 
    ('🔗', '5776078972659962594'), ('🔗', '5778455936410588193'), ('🔗', '5895364284782743985'), ('🔗', '5769289093221454192'), 
    ('🔗', '5766902139376898645'), ('➕', '6032924188828767321'), ('ℹ', '6028435952299413210'), ('❓', '6030848053177486888'), 
    ('❗️', '6030563507299160824'), ('▶️', '5773626993010546707'), ('▶️', '5850346984501680054'), ('❌', '5774077015388852135'), 
    ('✅', '5774022692642492953'), ('⬆️', '6028205772117118673'), ('🔓', '6037496202990194718'), ('🔒', '6037249452824072506'), 
    ('🖼', '6030466823290360017'), ('🖼', '6035128606563241721'), ('🤖', '6030400221232501136'), ('⭐️', '6030425896546996257'), 
    ('⭐️', '6030680867280522811'), ('📁', '6037475557082403885'), ('📁', '5904219717073114606'), ('📄', '6034969813032374911'), 
    ('🗑', '6039522349517115015'), ('🎶', '6037364759811068375'), ('🎶', '6037460610596212193'), ('👁', '6037397706505195857'), 
    ('👁', '6037243349675544634'), ('👁', '5884097155341226387'), ('👁', '5935757052042285202'), ('⬇️', '6037157012242960559'), 
    ('⬇️', '5884218166044791498'), ('⬇️', '6039802767931871481'), ('☁', '6028115612163641653'), ('⬇️', '6032745346390560408'), 
    ('⬆️', '5963103826075456248'), ('⬇️', '5963087934696459905'), ('⬆️', '6039391666547201160'), ('📤', '6039573425268201570'), 
    ('⬆️', '5776288820467077551'), ('🛡', '6030537007350944596'), ('🛡', '6032636795387121097'), ('🛡', '6030445631921721471'), 
    ('📂', '6039630677182254664'), ('📂', '6039800856671424701'), ('📂', '6037373985400819577'), ('📂', '6039348811363520645'), 
    ('🎀', '6203713520404534016'), ('🐱', '6204045487016777174'), ('💗', '6203957637755703921'), ('✔️', '6204030394501698406'), 
    ('💞', '6203931026138337360'), ('👑', '6203939590303126095'), ('🦋', '6203907128940303118'), ('🦋', '6204072317677474379'), 
    ('🦋', '6203875011174863133'), ('🦋', '6203745767018992790'), ('💜', '6203936708380070286'), ('✨', '6203899763071390887'), 
    ('💉', '6203887329141068076'), ('💕', '6204052023957000629'), ('🤔', '6203905544097371034'), ('🤡', '6203981303025504824'), 
    ('😴', '6204050267315376719'), ('😙', '6204152715170288194'), ('😶', '6203708993509003455'), ('🔪', '6113753222776623363'), 
    ('🤍', '6111936872517211640'), ('🤍', '6113637391803617981'), ('✨', '6113795352110830398'), ('❤️', '6113688832626922396'), 
    ('❤️', '6113698345979483267'), ('💘', '6114138580127322092'), ('💗', '6114072948732073970'), ('💖', '6113887809871811027'), 
    ('💖', '6113710612406080874'), ('🦋', '6114079915169026233'), ('✨', '6111831431070094156'), ('💗', '6113785254642717557'), 
    ('🤩', '6203863685346103678'), ('🤩', '6111458468995011881'), ('🤩', '6111766143272228751'), ('🤩', '6111737740653499149'), 
    ('🤩', '6111389470345400787'), ('🎀', '6120419797999032200'), ('🌸', '6120813143988900580'), ('⭐', '6120787219566302525'), 
    ('🔪', '6120838815008429932'), ('🌸', '6120658890238465040'), ('🌸', '6120707814210933929'), ('🤍', '6120533799315969969')
]

def get_random_premium_emoji():
    """Returns a random premium emoji in HTML format."""
    emoji_icon, emoji_id = random.choice(PREMIUM_EMOJIS)
    return f'<tg-emoji emoji-id="{emoji_id}">{emoji_icon}</tg-emoji>'

from config import OWNER_ID, send_bot_response
from settings_manager_mongo import get_chat_settings, update_chat_setting
from user_manager_mongo import is_user_admin, cache_user, can_user_configure_settings

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
        # Remove @ if present
        arg = arg.replace('@', '')
        
        # Try to parse as user ID
        try:
            user_id = int(arg)
            chat = await context.bot.get_chat(user_id)
            return chat
        except (ValueError, Exception) as e:
            logging.info(f"Could not resolve as user ID: {e}")
        
        # Try to resolve as username
        try:
            chat = await context.bot.get_chat(f'@{arg}')
            return chat
        except Exception as e:
            logging.info(f"Could not resolve as username: {e}")
    
    return None

async def free_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to exempt a user from specific blocking rules."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Only admins with specific permissions can use this command
    if not await can_user_configure_settings(chat_id, user_id, context):
        await send_bot_response(update, context, "Only admins with 'Ban Users' and 'Change Group Info' permissions can use the /free command.")
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
    }
    
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
                f"{random_emoji} [{target_user.id}] ᴡɪʟʟ ʙᴇ ᴀʟʀᴇᴀᴅʏ ꜰʀᴇᴇᴅ!\n\n"
                f"<b>📊 ᴄᴜʀʀᴇɴᴛ ᴇxᴇᴍᴘᴛɪᴏɴꜱ:</b>\n{freed_text}\n\n"
                f"💡 ʏᴏᴜ ᴄᴀɴ ꜱᴛɪʟʟ ᴍᴀɴᴀɢᴇ ᴛʜᴇɪʀ ʙʟᴏᴄᴋɪɴɢ ᴘᴇʀᴍɪꜱꜱɪᴏɴꜱ ʙᴇʟᴏᴡ:"
            )
        else:
            message_text = (
                f"{random_emoji} [{target_user.id}] ᴡɪʟʟ ʙᴇ ᴀʟʀᴇᴀᴅʏ ꜰʀᴇᴇᴅ!\n\n"
                f"💡 ʏᴏᴜ ᴄᴀɴ ꜱᴛɪʟʟ ᴍᴀɴᴀɢᴇ ᴛʜᴇɪʀ ʙʟᴏᴄᴋɪɴɢ ᴘᴇʀᴍɪꜱꜱɪᴏɴꜱ ʙᴇʟᴏᴡ:"
            )
    else:
        # Grant all exemptions (default to False/disabled)
        exemptions = {key: False for key in blocking_labels.keys()}
        
        # Store with string key for MongoDB compatibility
        user_permissions[user_id_str] = exemptions
        
        # Update settings
        update_chat_setting(chat_id, "user_permissions", user_permissions)
        
        random_emoji = get_random_premium_emoji()
        message_text = (
            f"{random_emoji} [{target_user.id}] ᴡɪʟʟ ʙᴇ ꜰʀᴇᴇᴅ ꜰʀᴏᴍ ʙʟᴏᴄᴋɪɴɢ :\n\n"
            f"💡 ʏᴏᴜ ᴄᴀɴ ꜱᴛɪʟʟ ᴍᴀɴᴀɢᴇ ᴛʜᴇɪʀ ʙʟᴏᴄᴋɪɴɢ ᴘᴇʀᴍɪꜱꜱɪᴏɴꜱ ʙᴇʟᴏᴡ:"
        )
    
    # Create keyboard with permission button
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛡 Permissions", callback_data=f"free_perms_{target_user.id}")]
    ])
    
    await send_bot_response(update, context, message_text, reply_markup=keyboard, parse_mode="HTML")

async def unfree_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to remove exemptions from a user."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Only admins with specific permissions can use this command
    if not await can_user_configure_settings(chat_id, user_id, context):
        await send_bot_response(update, context, "Only admins with 'Ban Users' and 'Change Group Info' permissions can use the /unfree command.")
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
    ]
    
    keyboard = []
    for i in range(0, len(blocking_options), 2):
        row = []
        key1, label1 = blocking_options[i]
        # True = FREED/ALLOWED ✅, False = BLOCKED ❌
        value1 = user_perms.get(key1, False)
        status1 = "✅" if value1 else "❌"
        logging.info(f"[KEYBOARD] {key1}: value={value1}, status={status1}")
        row.append(InlineKeyboardButton(f"{label1} {status1}", callback_data=f"free_toggle_{user_id}_{key1}"))
        
        if i + 1 < len(blocking_options):
            key2, label2 = blocking_options[i + 1]
            value2 = user_perms.get(key2, False)
            status2 = "✅" if value2 else "❌"
            logging.info(f"[KEYBOARD] {key2}: value={value2}, status={status2}")
            row.append(InlineKeyboardButton(f"{label2} {status2}", callback_data=f"free_toggle_{user_id}_{key2}"))
        
        keyboard.append(row)
    
    # Add save and back buttons
    keyboard.append([InlineKeyboardButton("💾 Save", callback_data=f"free_save_{user_id}")])
    
    return InlineKeyboardMarkup(keyboard)

async def free_permission_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show permission settings for a freed user."""
    query = update.callback_query
    admin_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Check permissions
    if not await can_user_configure_settings(chat_id, admin_id, context):
        await query.answer("You don't have permission to manage blocking exemptions.", show_alert=True)
        return

    await query.answer()
    
    target_user_id = int(query.data.split("_")[-1])
    
    settings = get_chat_settings(chat_id)
    
    try:
        chat = await context.bot.get_chat(target_user_id)
        user_name = chat.first_name or "Unknown"
    except:
        user_name = "Unknown User"
    
    message_text = (
        f"🛡 <b>ʙʟᴏᴄᴋɪɴɢ ꜱᴇᴛᴛɪɴɢꜱ 🛡</b>\n\n"
        f"[{target_user_id}] ᴡɪʟʟ ʙᴇ ᴇxᴇᴍᴘᴛᴇᴅ ꜰʀᴏᴍ:\n\n"
        f"ᴛᴏɢɢʟᴇ ꜰᴇᴀᴛᴜʀᴇꜱ ᴛᴏ ʙʟᴏᴄᴋ ᴄᴏɴᴛᴇɴᴛ:"
    )
    
    keyboard = get_user_permission_keyboard(target_user_id, settings)
    
    try:
        await query.edit_message_text(message_text, reply_markup=keyboard, parse_mode='HTML')
    except:
        await query.message.edit_text(message_text, reply_markup=keyboard, parse_mode='HTML')

async def free_permission_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle a permission for a user and auto-save to database."""
    query = update.callback_query
    admin_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Check permissions
    if not await can_user_configure_settings(chat_id, admin_id, context):
        await query.answer("You don't have permission to manage blocking exemptions.", show_alert=True)
        return

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
    
    # Get current permissions from database
    user_permissions = settings.get("user_permissions", {})
    logging.info(f"[TOGGLE] DB permissions: {user_permissions.get(user_id_str, {})}")
    
    # Initialize user permissions if not exists
    if user_id_str not in user_permissions:
        user_permissions[user_id_str] = {}
    
    # Get current value and toggle it
    current_value = user_permissions[user_id_str].get(perm_key, False)
    new_value = not current_value
    user_permissions[user_id_str][perm_key] = new_value
    
    logging.info(f"[TOGGLE] {perm_key} changed from {current_value} to {new_value}")
    logging.info(f"[TOGGLE] Updated user perms: {user_permissions[user_id_str]}")
    
    # AUTO-SAVE to database immediately
    update_chat_setting(chat_id, "user_permissions", user_permissions)
    logging.info(f"[TOGGLE] Auto-saved to database for user {user_id_str}")
    
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
    """Save permission changes for a user (now just closes the panel since auto-save is enabled)."""
    query = update.callback_query
    admin_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Check permissions
    if not await can_user_configure_settings(chat_id, admin_id, context):
        await query.answer("You don't have permission to manage blocking exemptions.", show_alert=True)
        return
    
    user_id = int(query.data.split("_")[-1])
    user_id_str = str(user_id)
    
    # Clean up any temporary data (if exists from old sessions)
    if f'free_perms_{chat_id}_{user_id_str}' in context.user_data:
        del context.user_data[f'free_perms_{chat_id}_{user_id_str}']
    
    await query.answer("Settings saved!")
    
    # Delete the message after saving
    try:
        await query.message.delete()
    except:
        pass
