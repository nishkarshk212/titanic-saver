from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.error import BadRequest
from settings_manager_mongo import get_chat_settings, update_chat_setting
from config import OWNER_ID, send_bot_response, edit_bot_response
from user_manager_mongo import can_user_configure_settings
from anonymous_admin import is_anonymous_admin, check_anonymous_admin_change_info_permission
from blocking_handler import DEFAULT_BLOCKING_SETTINGS
import logging
import asyncio

async def delete_saved_message(context, message):
    """Delete the saved message job."""
    try:
        await message.delete()
    except Exception as e:
        logging.warning(f"Failed to delete saved message: {e}")

async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Settings command handler - shows option to open in group or private."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Check command access for settings
    from settings_manager_mongo import check_command_access
    if not await check_command_access(chat_id, user_id, 'settings', context):
        await send_bot_response(update, context, "You don't have permission to use the /settings command.")
        return
    
    # Check granular permissions (Change Info + Ban Users)
    if not await can_user_configure_settings(chat_id, user_id, context):
        await send_bot_response(update, context, "You need both 'Change Group Info' and 'Ban Users' permissions to configure settings.")
        return
    
    # Create bot URL for private chat
    bot_info = await context.bot.get_me()
    bot_username = bot_info.username
    
    # Store chat_id in user_data to retrieve later
    context.user_data['settings_chat_id'] = chat_id
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 Open Here", callback_data=f"settings_open_here_{chat_id}")],
        [InlineKeyboardButton("💬 Open in Private", url=f"https://t.me/{bot_username}?start=settings_{chat_id}")]
    ])
    
    settings_text = (
        f"How would you like to open the settings?"
    )
    
    await send_bot_response(update, context, settings_text, reply_markup=keyboard)

async def open_settings_here(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Open settings directly in the group."""
    query = update.callback_query
    
    # Extract chat_id from callback data
    chat_id = int(query.data.split("_")[-1])
    
    # Store chat_id in user_data
    context.user_data['settings_chat_id'] = chat_id
    
    try:
        await query.answer()
    except Exception as e:
        logging.warning(f"Callback query answer failed: {e}")
    
    await show_settings_panel(update, context, chat_id)

async def show_settings_panel(query_or_update, context, chat_id, is_private=False):
    """Show the actual settings panel."""
    # First check if it has message attribute (Update object from deep link)
    if hasattr(query_or_update, 'message') and hasattr(query_or_update, 'effective_user'):
        # It's an Update object (from deep link)
        update = query_or_update
        user_id = update.effective_user.id
        
        # Check permissions
        if not await can_user_configure_settings(chat_id, user_id, context):
            await send_bot_response(update, context, "You need both 'Change Group Info' and 'Ban Users' permissions to configure settings.")
            return
        
        keyboard = get_main_settings_keyboard(chat_id)
        
        # Get group info
        try:
            chat = await context.bot.get_chat(chat_id)
            group_name = chat.title or "Unknown"
        except:
            group_name = "Unknown"
        
        group_id = chat_id
        user_mention = f"<a href='tg://user?id={user_id}'>{update.effective_user.first_name}</a>"
        
        settings_text = (
            f"🛠 <b>ʙᴏᴛ ꜱᴇᴛᴛɪɴɢꜱ 🛠</b>\n\n"
            f"ɢʀᴏᴜᴘ: {group_name}\n"
            f"ɪᴅ: {group_id}\n"
            f"ᴏᴘᴇɴᴇᴅ ʙʏ: {user_mention}\n\n"
            f"ꜱᴇʟᴇᴄᴛ ᴏɴᴇ ᴏꜰ ᴛʜᴇ ꜱᴇᴛᴛɪɴɢꜱ ᴛʜᴀᴛ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴄʜᴀɴɢᴇ:"
        )
        
        # Send directly with HTML parse mode to preserve links
        try:
            msg = await update.message.reply_text(settings_text, reply_markup=keyboard, parse_mode='HTML')
        except:
            msg = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=settings_text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
    elif hasattr(query_or_update, 'callback_query'):
        # It's a CallbackQuery wrapped in Update
        query = query_or_update.callback_query
        if query is None:
            logging.error("callback_query is None")
            return
        user_id = query.from_user.id
        
        # Check permissions
        if not await can_user_configure_settings(chat_id, user_id, context):
            await query.answer("You don't have permission to access settings.", show_alert=True)
            return
        
        keyboard = get_main_settings_keyboard(chat_id)
        
        # Get group info
        try:
            chat = await context.bot.get_chat(chat_id)
            group_name = chat.title or "Unknown"
        except:
            group_name = "Unknown"
        
        group_id = chat_id
        user_mention = f"<a href='tg://user?id={user_id}'>{query.from_user.first_name}</a>"
        
        settings_text = (
            f"🛠 <b>ʙᴏᴛ ꜱᴇᴛᴛɪɴɢꜱ 🛠</b>\n\n"
            f"ɢʀᴏᴜᴘ: {group_name}\n"
            f"ɪᴅ: {group_id}\n"
            f"ᴏᴘᴇɴᴇᴅ ʙʏ: {user_mention}\n\n"
            f"ꜱᴇʟᴇᴄᴛ ᴏɴᴇ ᴏꜰ ᴛʜᴇ ꜱᴇᴛᴛɪɴɢꜱ ᴛʜᴀᴛ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴄʜᴀɴɢᴇ:"
        )
        
        try:
            await query.edit_message_text(settings_text, reply_markup=keyboard, parse_mode='HTML')
        except BadRequest:
            await query.message.edit_text(settings_text, reply_markup=keyboard, parse_mode='HTML')
    else:
        # It's a CallbackQuery directly
        query = query_or_update
        user_id = query.from_user.id
        
        # Check permissions
        if not await can_user_configure_settings(chat_id, user_id, context):
            await query.answer("You don't have permission to access settings.", show_alert=True)
            return
        
        keyboard = get_main_settings_keyboard(chat_id)
        
        # Get group info
        try:
            chat = await context.bot.get_chat(chat_id)
            group_name = chat.title or "Unknown"
        except:
            group_name = "Unknown"
        
        group_id = chat_id
        user_mention = f"<a href='tg://user?id={user_id}'>{query.from_user.first_name}</a>"
        
        settings_text = (
            f"🛠 <b>ʙᴏᴛ ꜱᴇᴛᴛɪɴɢꜱ 🛠</b>\n\n"
            f"ɢʀᴏᴜᴘ: {group_name}\n"
            f"ɪᴅ: {group_id}\n"
            f"ᴏᴘᴇɴᴇᴅ ʙʏ: {user_mention}\n\n"
            f"ꜱᴇʟᴇᴄᴛ ᴏɴᴇ ᴏꜰ ᴛʜᴇ ꜱᴇᴛᴛɪɴɢꜱ ᴛʜᴀᴛ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴄʜᴀɴɢᴇ:"
        )
        
        try:
            await query.edit_message_text(settings_text, reply_markup=keyboard, parse_mode='HTML')
        except BadRequest:
            await query.message.edit_text(settings_text, reply_markup=keyboard, parse_mode='HTML')

def get_main_settings_keyboard(chat_id=None):
    keyboard = [
        [InlineKeyboardButton("👋 Welcome", callback_data="set_view_welcome"), 
         InlineKeyboardButton("🧹 Clean Service", callback_data="set_view_clean")],
        [InlineKeyboardButton("💣 Auto Delete", callback_data="set_view_auto_delete"), 
         InlineKeyboardButton("📏 Msg Length", callback_data="set_view_msg_length")],
        [InlineKeyboardButton("🛡️ Moderation", callback_data="set_view_mod"), 
         InlineKeyboardButton("🗑️ Cmd Deletion", callback_data="set_view_command_deletion")],
        [InlineKeyboardButton("📌 Pinned Msg", callback_data="set_view_pinned_messages"), 
         InlineKeyboardButton("🤖 Bot Protection", callback_data="set_view_bot_protection")],
        [InlineKeyboardButton("🔗 Link Spam", callback_data="set_view_link_spam"), 
         InlineKeyboardButton("🔄 Forward Protect", callback_data="set_view_forward_protection")],
        [InlineKeyboardButton("🔑 Cmd Access", callback_data="set_view_command_access"), 
         InlineKeyboardButton("🎛️ Command Perms", callback_data="set_view_command_permissions")],
        [InlineKeyboardButton("🌐 Language Filter", callback_data="set_view_language_filter")],
        [InlineKeyboardButton("🚧 Blocking", callback_data="set_view_blocking"),
         InlineKeyboardButton("📋 Freed Members", callback_data="free_list_members")],
        [InlineKeyboardButton("👥 Manager", callback_data="set_view_manager")],
        [InlineKeyboardButton("❌ Close Menu", callback_data="set_close")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_welcome_settings_keyboard(settings):
    welcome_status = "✅" if settings.get("welcome_enabled", True) else "❌"
    rejoin_status = "✅" if settings.get("welcome_rejoin_enabled", True) else "❌"
    media_status = "✅" if settings.get("welcome_media_enabled", True) else "❌"
    button_status = "✅" if settings.get("welcome_button_enabled", True) else "❌"
    delete_time = settings.get("welcome_delete_time", 60)
    welcome_buttons = settings.get("welcome_buttons", [])
    
    keyboard = [
        [InlineKeyboardButton(f"Welcome: {welcome_status}", callback_data="set_toggle_welcome_enabled")],
        [InlineKeyboardButton(f"Welcome on Re-join: {rejoin_status}", callback_data="set_toggle_welcome_rejoin_enabled")],
        [
            InlineKeyboardButton(f"Media: {media_status}", callback_data="set_toggle_welcome_media_enabled"),
            InlineKeyboardButton("🖼️ Set Media", callback_data="set_config_welcome_media")
        ],
        [
            InlineKeyboardButton(f"Button: {button_status}", callback_data="set_toggle_welcome_button_enabled"),
            InlineKeyboardButton("➕ Add Button", callback_data="set_config_welcome_buttons_add"),
            InlineKeyboardButton("🗑️ Clear", callback_data="set_config_welcome_buttons_clear")
        ]
    ]
    
    # List added buttons if any
    if welcome_buttons:
        for idx, btn in enumerate(welcome_buttons, 1):
            btn_text = btn.get("text", f"Btn {idx}")
            keyboard.append([InlineKeyboardButton(f"Button {idx}: {btn_text}", callback_data="set_none")])
    
    keyboard.extend([
        [InlineKeyboardButton("📝 Set Welcome Text", callback_data="set_config_welcome_text")],
        [
            InlineKeyboardButton("-10s", callback_data="set_welcome_time_sub_10"),
            InlineKeyboardButton(f"🗑️ Delete: {delete_time}s", callback_data="set_none"),
            InlineKeyboardButton("+10s", callback_data="set_welcome_time_add_10")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="set_view_main")]
    ])
    return InlineKeyboardMarkup(keyboard)

def get_clean_settings_keyboard(settings):
    master_status = "✅" if settings.get("clean_service_enabled", True) else "❌"
    join_status = "✅" if settings.get("clean_join", True) else "❌"
    left_status = "✅" if settings.get("clean_left", True) else "❌"
    started_status = "✅" if settings.get("clean_video_chat_started", True) else "❌"
    ended_status = "✅" if settings.get("clean_video_chat_ended", True) else "❌"
    invited_status = "✅" if settings.get("clean_video_chat_invited", True) else "❌"
    scheduled_status = "✅" if settings.get("clean_video_chat_scheduled", True) else "❌"
    
    keyboard = [
        [InlineKeyboardButton(f"Master Clean: {master_status}", callback_data="set_toggle_clean_service_enabled")],
        [InlineKeyboardButton(f"Clean Join: {join_status}", callback_data="set_toggle_clean_join")],
        [InlineKeyboardButton(f"Clean Left: {left_status}", callback_data="set_toggle_clean_left")],
        [InlineKeyboardButton(f"Voice Chat Started: {started_status}", callback_data="set_toggle_clean_video_chat_started")],
        [InlineKeyboardButton(f"Voice Chat Ended: {ended_status}", callback_data="set_toggle_clean_video_chat_ended")],
        [InlineKeyboardButton(f"Voice Chat Invited: {invited_status}", callback_data="set_toggle_clean_video_chat_invited")],
        [InlineKeyboardButton(f"Voice Chat Scheduled: {scheduled_status}", callback_data="set_toggle_clean_video_chat_scheduled")],
        [InlineKeyboardButton("🔙 Back", callback_data="set_view_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_auto_delete_settings_keyboard(settings):
    status = "✅" if settings.get("auto_delete_enabled", False) else "❌"
    total_seconds = settings.get("auto_delete_time", 60)
    
    # Calculate H, M, S
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    
    keyboard = [
        [InlineKeyboardButton(f"Auto Delete: {status}", callback_data="set_toggle_auto_delete_enabled")],
        [
            InlineKeyboardButton("-H", callback_data="set_time_sub_3600"),
            InlineKeyboardButton(f"{h} Hours", callback_data="set_none"),
            InlineKeyboardButton("+H", callback_data="set_time_add_3600")
        ],
        [
            InlineKeyboardButton("-M", callback_data="set_time_sub_60"),
            InlineKeyboardButton(f"{m} Minutes", callback_data="set_none"),
            InlineKeyboardButton("+M", callback_data="set_time_add_60")
        ],
        [
            InlineKeyboardButton("-S", callback_data="set_time_sub_1"),
            InlineKeyboardButton(f"{s} Seconds", callback_data="set_none"),
            InlineKeyboardButton("+S", callback_data="set_time_add_1")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="set_view_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_msg_length_settings_keyboard(settings):
    current_limit = settings.get("msg_length_limit", 0)
    status = f"{current_limit} chars" if current_limit > 0 else "Disabled"
    
    keyboard = [
        [InlineKeyboardButton(f"Current Limit: {status}", callback_data="set_none")],
        [
            InlineKeyboardButton("100", callback_data="set_msg_length_100"),
            InlineKeyboardButton("200", callback_data="set_msg_length_200"),
            InlineKeyboardButton("300", callback_data="set_msg_length_300")
        ],
        [
            InlineKeyboardButton("Custom", callback_data="set_config_msg_length_limit"),
            InlineKeyboardButton("Disable", callback_data="set_msg_length_0")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="set_view_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_mod_settings_keyboard(settings):
    limit = settings.get("warn_limit", 3)
    penalty = settings.get("warn_penalty", "ban").title()
    
    keyboard = [
        [
            InlineKeyboardButton("-", callback_data="set_warn_limit_sub"),
            InlineKeyboardButton(f"Warn Limit: {limit}", callback_data="set_none"),
            InlineKeyboardButton("+", callback_data="set_warn_limit_add")
        ],
        [InlineKeyboardButton(f"Warn Penalty: {penalty}", callback_data="set_toggle_warn_penalty")],
        [InlineKeyboardButton("🔙 Back", callback_data="set_view_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_command_deletion_keyboard(settings):
    status = "✅" if settings.get("command_deletion", False) else "❌"
    keyboard = [
        [InlineKeyboardButton(f"Delete Admin Commands: {status}", callback_data="set_toggle_command_deletion")],
        [InlineKeyboardButton("🔙 Back", callback_data="set_view_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_command_access_keyboard(settings):
    access = settings.get("command_access", "all").title()
    keyboard = [
        [InlineKeyboardButton(f"Command Access: {access}", callback_data="set_toggle_command_access")],
        [InlineKeyboardButton("ℹ️ Global setting for basic commands", callback_data="set_none")],
        [InlineKeyboardButton("🔙 Back", callback_data="set_view_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_command_permissions_keyboard(settings):
    """Get detailed command permissions keyboard."""
    # Define command categories with their access levels
    commands = [
        ("📖 Basic Commands", [
            ("Start", "cmd_access_start"),
            ("Help", "cmd_access_help"),
            ("ID", "cmd_access_id"),
            ("Info", "cmd_access_info"),
            ("Report", "cmd_access_report"),
        ]),
        ("🛡️ Moderation Commands", [
            ("Ban", "cmd_access_ban"),
            ("Unban", "cmd_access_unban"),
            ("Mute", "cmd_access_mute"),
            ("Unmute", "cmd_access_unmute"),
            ("Warn", "cmd_access_warn"),
            ("Unwarn", "cmd_access_unwarn"),
            ("Kick", "cmd_access_kick"),
        ]),
        ("👥 Management Commands", [
            ("Purge", "cmd_access_purge"),
            ("Pin", "cmd_access_pin"),
            ("Unpin", "cmd_access_unpin"),
            ("Promote", "cmd_access_promote"),
            ("Demote", "cmd_access_demote"),
        ]),
        ("📋 Info & Utilities", [
            ("Staff", "cmd_access_staff"),
            ("Bots", "cmd_access_bots"),
            ("Zombies", "cmd_access_zombies"),
        ]),
        ("⚠️ Mass Actions", [
            ("Mass Actions", "cmd_access_mass_actions"),
        ]),
        ("⚙️ Settings", [
            ("Settings/Config", "cmd_access_settings"),
        ]),
    ]
    
    keyboard = []
    for category, cmds in commands:
        keyboard.append([InlineKeyboardButton(f"── {category} ──", callback_data="set_none")])
        for cmd_name, cmd_key in cmds:
            current_access = settings.get(cmd_key, "admin").title()
            keyboard.append([InlineKeyboardButton(f"/{cmd_name.lower()}: {current_access}", callback_data=f"set_cmd_perm_{cmd_key}")])
    
    keyboard.append([InlineKeyboardButton("ℹ️ Tap a command to toggle access level", callback_data="set_none")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="set_view_main")])
    
    return InlineKeyboardMarkup(keyboard)

def get_pinned_message_settings_keyboard(settings):
    pinned_status = "✅" if settings.get("clean_pinned_message", True) else "❌"
    keyboard = [
        [InlineKeyboardButton(f"Clean Pinned Message: {pinned_status}", callback_data="set_toggle_clean_pinned_message")],
        [InlineKeyboardButton("🔙 Back", callback_data="set_view_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_bot_protection_settings_keyboard(settings):
    status = "✅" if settings.get("bot_protection_enabled", False) else "❌"
    keyboard = [
        [InlineKeyboardButton(f"Bot Protection: {status}", callback_data="set_toggle_bot_protection_enabled")],
        [InlineKeyboardButton("ℹ️ Only affects members (not admins)", callback_data="set_none")],
        [InlineKeyboardButton("🔙 Back", callback_data="set_view_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_link_spam_settings_keyboard(settings):
    status = "✅" if settings.get("link_spam_protection_enabled", False) else "❌"
    keyboard = [
        [InlineKeyboardButton(f"Link Spam Protection: {status}", callback_data="set_toggle_link_spam_protection_enabled")],
        [InlineKeyboardButton("ℹ️ Only affects members (not admins)", callback_data="set_none")],
        [InlineKeyboardButton("🔙 Back", callback_data="set_view_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_forward_protection_settings_keyboard(settings):
    status = "✅" if settings.get("forward_protection_enabled", False) else "❌"
    keyboard = [
        [InlineKeyboardButton(f"Forward Protection: {status}", callback_data="set_toggle_forward_protection_enabled")],
        [InlineKeyboardButton("ℹ️ Only affects members (not admins)", callback_data="set_none")],
        [InlineKeyboardButton("🔙 Back", callback_data="set_view_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_language_filter_settings_keyboard(settings):
    """Get language filter settings keyboard."""
    status = "✅" if settings.get("language_filter_enabled", False) else "❌"
    allowed = settings.get("allowed_languages", ["en", "hi", "hinglish"])
    
    en_status = "✅" if "en" in allowed else "❌"
    hi_status = "✅" if "hi" in allowed else "❌"
    hinglish_status = "✅" if "hinglish" in allowed else "❌"
    
    # Emoji blocking settings
    emoji_block = "✅" if settings.get("emoji_block_enabled", False) else "❌"
    block_emoji_only = "✅" if settings.get("block_emoji_only", True) else "❌"
    block_punct_only = "✅" if settings.get("block_punctuation_only", True) else "❌"
    
    keyboard = [
        [InlineKeyboardButton(f"Language Filter: {status}", callback_data="set_toggle_language_filter_enabled")],
        [InlineKeyboardButton(f"🇬🇧 English: {en_status}", callback_data="set_toggle_lang_en")],
        [InlineKeyboardButton(f"🇮🇳 Hindi: {hi_status}", callback_data="set_toggle_lang_hi")],
        [InlineKeyboardButton(f"💬 Hinglish: {hinglish_status}", callback_data="set_toggle_lang_hinglish")],
        [InlineKeyboardButton("── Emoji & Symbols ──", callback_data="set_none")],
        [InlineKeyboardButton(f"Block Emojis: {emoji_block}", callback_data="set_toggle_emoji_block_enabled")],
        [InlineKeyboardButton(f"  Emoji Only: {block_emoji_only}", callback_data="set_toggle_block_emoji_only")],
        [InlineKeyboardButton(f"  Punctuation Only: {block_punct_only}", callback_data="set_toggle_block_punctuation_only")],
        [InlineKeyboardButton("ℹ️ Deletes messages in other languages", callback_data="set_none")],
        [InlineKeyboardButton("🔙 Back", callback_data="set_view_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_blocking_settings_keyboard(settings):
    """Get blocking settings keyboard."""
    # Merge with defaults if needed
    for key, value in DEFAULT_BLOCKING_SETTINGS.items():
        if key not in settings:
            settings[key] = value
    
    master_status = "✅" if settings.get("blocking_enabled", True) else "❌"
    stickers_status = "✅" if settings.get("block_stickers", False) else "❌"
    premium_sticker_status = "✅" if settings.get("block_premium_sticker", False) else "❌"
    link_status = "✅" if settings.get("block_link", False) else "❌"
    embed_link_status = "✅" if settings.get("block_embed_link", False) else "❌"
    media_status = "✅" if settings.get("block_media", False) else "❌"
    documents_status = "✅" if settings.get("block_documents", False) else "❌"
    forward_status = "✅" if settings.get("block_forward", False) else "❌"
    channel_post_status = "✅" if settings.get("block_channel_post", False) else "❌"
    command_status = "✅" if settings.get("block_command", False) else "❌"
    contact_status = "✅" if settings.get("block_contact", False) else "❌"
    location_status = "✅" if settings.get("block_location", False) else "❌"
    voice_status = "✅" if settings.get("block_voice", False) else "❌"
    audio_status = "✅" if settings.get("block_audio", False) else "❌"
    video_note_status = "✅" if settings.get("block_video_note", False) else "❌"
    poll_status = "✅" if settings.get("block_poll", False) else "❌"
    dice_status = "✅" if settings.get("block_dice", False) else "❌"
    game_status = "✅" if settings.get("block_game", False) else "❌"
    
    keyboard = [
        [InlineKeyboardButton(f"Master Blocking: {master_status}", callback_data="set_toggle_blocking_enabled")],
        [InlineKeyboardButton("── Stickers ──", callback_data="set_none")],
        [InlineKeyboardButton(f"Block Stickers: {stickers_status}", callback_data="set_toggle_block_stickers")],
        [InlineKeyboardButton(f"Block Premium Stickers: {premium_sticker_status}", callback_data="set_toggle_block_premium_sticker")],
        [InlineKeyboardButton("── Links ──", callback_data="set_none")],
        [InlineKeyboardButton(f"Block Links: {link_status}", callback_data="set_toggle_block_link")],
        [InlineKeyboardButton(f"Block Embed Links: {embed_link_status}", callback_data="set_toggle_block_embed_link")],
        [InlineKeyboardButton("── Media & Files ──", callback_data="set_none")],
        [InlineKeyboardButton(f"Block Media: {media_status}", callback_data="set_toggle_block_media")],
        [InlineKeyboardButton(f"Block Documents: {documents_status}", callback_data="set_toggle_block_documents")],
        [InlineKeyboardButton(f"Block Audio/Music: {audio_status}", callback_data="set_toggle_block_audio")],
        [InlineKeyboardButton("── Messages ──", callback_data="set_none")],
        [InlineKeyboardButton(f"Block Forward: {forward_status}", callback_data="set_toggle_block_forward")],
        [InlineKeyboardButton(f"Block Channel Posts: {channel_post_status}", callback_data="set_toggle_block_channel_post")],
        [InlineKeyboardButton(f"Block Commands: {command_status}", callback_data="set_toggle_block_command")],
        [InlineKeyboardButton("── Other ──", callback_data="set_none")],
        [InlineKeyboardButton(f"Block Contact: {contact_status}", callback_data="set_toggle_block_contact")],
        [InlineKeyboardButton(f"Block Location: {location_status}", callback_data="set_toggle_block_location")],
        [InlineKeyboardButton(f"Block Voice: {voice_status}", callback_data="set_toggle_block_voice")],
        [InlineKeyboardButton(f"Block Video Note: {video_note_status}", callback_data="set_toggle_block_video_note")],
        [InlineKeyboardButton(f"Block Poll: {poll_status}", callback_data="set_toggle_block_poll")],
        [InlineKeyboardButton(f"Block Dice: {dice_status}", callback_data="set_toggle_block_dice")],
        [InlineKeyboardButton(f"Block Game: {game_status}", callback_data="set_toggle_block_game")],
        [InlineKeyboardButton("ℹ️ Toggle to block content instantly", callback_data="set_none")],
        [InlineKeyboardButton("🔙 Back", callback_data="set_view_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_manager_settings_keyboard(settings):
    """Get Manager module settings keyboard."""
    ban_status = "✅" if settings.get("manager_ban_enabled", True) else "❌"
    unban_status = "✅" if settings.get("manager_unban_enabled", True) else "❌"
    mute_status = "✅" if settings.get("manager_mute_enabled", True) else "❌"
    unmute_status = "✅" if settings.get("manager_unmute_enabled", True) else "❌"
    kick_status = "✅" if settings.get("manager_kick_enabled", True) else "❌"
    promote_status = "✅" if settings.get("manager_promote_enabled", True) else "❌"
    demote_status = "✅" if settings.get("manager_demote_enabled", True) else "❌"
    purge_status = "✅" if settings.get("manager_purge_enabled", True) else "❌"
    pin_status = "✅" if settings.get("manager_pin_enabled", True) else "❌"
    mass_status = "✅" if settings.get("manager_mass_actions_enabled", True) else "❌"
    zombie_status = "✅" if settings.get("manager_zombie_enabled", True) else "❌"
    sg_status = "✅" if settings.get("manager_sg_enabled", True) else "❌"
    id_status = "✅" if settings.get("manager_id_enabled", True) else "❌"
    info_status = "✅" if settings.get("manager_info_enabled", True) else "❌"
    
    keyboard = [
        [InlineKeyboardButton("── Moderation Actions ──", callback_data="set_none")],
        [InlineKeyboardButton(f"Ban: {ban_status}", callback_data="set_toggle_manager_ban_enabled")],
        [InlineKeyboardButton(f"Unban: {unban_status}", callback_data="set_toggle_manager_unban_enabled")],
        [InlineKeyboardButton(f"Mute: {mute_status}", callback_data="set_toggle_manager_mute_enabled")],
        [InlineKeyboardButton(f"Unmute: {unmute_status}", callback_data="set_toggle_manager_unmute_enabled")],
        [InlineKeyboardButton(f"Kick: {kick_status}", callback_data="set_toggle_manager_kick_enabled")],
        [InlineKeyboardButton("── Admin Management ──", callback_data="set_none")],
        [InlineKeyboardButton(f"Promote: {promote_status}", callback_data="set_toggle_manager_promote_enabled")],
        [InlineKeyboardButton(f"Demote: {demote_status}", callback_data="set_toggle_manager_demote_enabled")],
        [InlineKeyboardButton("── Message Control ──", callback_data="set_none")],
        [InlineKeyboardButton(f"Purge: {purge_status}", callback_data="set_toggle_manager_purge_enabled")],
        [InlineKeyboardButton(f"Pin/Unpin: {pin_status}", callback_data="set_toggle_manager_pin_enabled")],
        [InlineKeyboardButton("── Mass Actions ──", callback_data="set_none")],
        [InlineKeyboardButton(f"Mass Actions: {mass_status}", callback_data="set_toggle_manager_mass_actions_enabled")],
        [InlineKeyboardButton("── Utilities ──", callback_data="set_none")],
        [InlineKeyboardButton(f"Zombie Clean: {zombie_status}", callback_data="set_toggle_manager_zombie_enabled")],
        [InlineKeyboardButton(f"Username History (SG): {sg_status}", callback_data="set_toggle_manager_sg_enabled")],
        [InlineKeyboardButton(f"ID Command: {id_status}", callback_data="set_toggle_manager_id_enabled")],
        [InlineKeyboardButton(f"Info Command: {info_status}", callback_data="set_toggle_manager_info_enabled")],
        [InlineKeyboardButton("ℹ️ Toggle to enable/disable commands", callback_data="set_none")],
        [InlineKeyboardButton("🔙 Back", callback_data="set_view_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Handle "Open Here" button
    if query.data.startswith("settings_open_here_"):
        await open_settings_here(update, context)
        return
    
    # Handle "Go to Private" button
    if query.data.startswith("settings_go_private_"):
        group_chat_id = int(query.data.split("_")[-1])
        bot_info = await context.bot.get_me()
        bot_username = bot_info.username
        
        await query.answer("Opening settings in private chat...", show_alert=False)
        
        # Send message with button to go to private
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Click Here to Open in Private", url=f"https://t.me/{bot_username}?start=settings_{group_chat_id}")]
        ])
        
        await query.edit_message_text(
            "💬 <b>Settings will be opened in private chat.</b>\n\n"
            "Click the button below to continue:",
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        return
    
    # Granular permission check
    if not await can_user_configure_settings(chat_id, user_id, context):
        await query.answer("You need 'Change Info' and 'Ban Users' permissions to access settings.", show_alert=True)
        return

    data = query.data
    
    if data == "set_close":
        chat_id = update.effective_chat.id
        
        # Delete the settings message
        try:
            await query.message.delete()
        except:
            pass
        
        # Send "Settings saved" message
        try:
            saved_msg = await context.bot.send_message(chat_id=chat_id, text="ꜱᴇᴛᴛɪɴɢ ꜱᴀᴠᴇᴅ ✅")
            
            # Delete the saved message after 5 seconds
            if context.job_queue:
                async def delete_job(ctx):
                    try:
                        await saved_msg.delete()
                    except:
                        pass
                
                context.job_queue.run_once(delete_job, 5)
        except:
            pass
        
        await query.answer()
        return
        
    if data == "set_view_main":
        # Determine the actual chat_id (could be from private chat with stored group_id)
        actual_chat_id = context.user_data.get('settings_chat_id', chat_id)
        await show_settings_panel(query, context, actual_chat_id)
        await query.answer()
        return

    if data == "set_view_welcome":
        settings = get_chat_settings(chat_id)
        try:
            await edit_bot_response(
                query, context,
                "👋 Welcome Configuration\n\nConfigure how new members are greeted:",
                reply_markup=get_welcome_settings_keyboard(settings)
            )
        except BadRequest: pass
        await query.answer()
        return

    if data == "set_view_clean":
        settings = get_chat_settings(chat_id)
        try:
            await edit_bot_response(
                query, context,
                "🧹 Clean Service Configuration\n\nAuto-delete service messages from the chat:",
                reply_markup=get_clean_settings_keyboard(settings)
            )
        except BadRequest: pass
        await query.answer()
        return

    if data == "set_view_auto_delete":
        settings = get_chat_settings(chat_id)
        try:
            await edit_bot_response(
                query, context,
                "💣 Auto Delete Configuration\n\nAutomatically delete group messages after a set time:",
                reply_markup=get_auto_delete_settings_keyboard(settings)
            )
        except BadRequest: pass
        await query.answer()
        return

    if data == "set_view_block_content":
        # Redirect to new blocking settings
        settings = get_chat_settings(chat_id)
        try:
            await query.edit_message_text(
                "🚧 <b>ʙʟᴏᴄᴋɪɴɢ ꜱᴇᴛᴛɪɴɢꜱ 🚧</b>\n\n"
                "ᴄᴏɴᴛʀᴏʟ ᴡʜᴀᴛ ᴛʏᴘᴇꜱ ᴏꜰ ᴄᴏɴᴛᴇɴᴛ ᴀʀᴇ ᴀʟʟᴏᴡᴇᴅ ɪɴ ʏᴏᴜʀ ɢʀᴏᴜᴘ.\n"
                "ᴛᴏɢɢʟᴇ ᴇᴀᴄʜ ꜱᴇᴛᴛɪɴɢ ᴛᴏ ʙʟᴏᴄᴋ ᴏʀ ᴀʟʟᴏᴡ ꜱᴘᴇᴄɪꜰɪᴄ ᴄᴏɴᴛᴇɴᴛ:",
                reply_markup=get_blocking_settings_keyboard(settings),
                parse_mode='HTML'
            )
        except BadRequest as e:
            logging.error(f"Error opening blocking settings: {e}")
            await query.answer("Error opening settings. Please try again.", show_alert=True)
        await query.answer()
        return

    if data == "set_view_msg_length":
        settings = get_chat_settings(chat_id)
        try:
            await edit_bot_response(
                query, context,
                "📏 Message Length Configuration\n\nSet the maximum character limit for messages:",
                reply_markup=get_msg_length_settings_keyboard(settings)
            )
        except BadRequest: pass
        await query.answer()
        return

    if data == "set_view_mod":
        settings = get_chat_settings(chat_id)
        try:
            await edit_bot_response(
                query, context,
                "🛡️ Moderation Settings\n\nConfigure warning limits and penalties:",
                reply_markup=get_mod_settings_keyboard(settings)
            )
        except BadRequest: pass
        await query.answer()
        return

    if data == "set_view_command_deletion":
        settings = get_chat_settings(chat_id)
        try:
            await edit_bot_response(
                query, context,
                "🗑️ Command Deletion\n\nAutomatically delete admin command messages if enabled:",
                reply_markup=get_command_deletion_keyboard(settings)
            )
        except BadRequest: pass
        await query.answer()
        return

    if data == "set_view_command_access":
        settings = get_chat_settings(chat_id)
        try:
            await edit_bot_response(
                query, context,
                "🔑 Command Access\n\nChoose who can use normal commands (help, id, info):",
                reply_markup=get_command_access_keyboard(settings)
            )
        except BadRequest: pass
        await query.answer()
        return

    if data == "set_view_command_permissions":
        settings = get_chat_settings(chat_id)
        try:
            await edit_bot_response(
                query, context,
                "🎛️ <b>Command Permissions</b>\n\nConfigure who can use each command:\n• <b>All</b> - Everyone can use it\n• <b>Admin</b> - Only admins can use it\n• <b>Owner</b> - Only group owner can use it\n\nTap a command to change its access level:",
                reply_markup=get_command_permissions_keyboard(settings)
            )
        except BadRequest: pass
        await query.answer()
        return

    if data == "set_view_pinned_messages":
        settings = get_chat_settings(chat_id)
        try:
            await edit_bot_response(
                query, context,
                "📌 Pinned Messages Settings\n\nConfigure how pinned messages are handled:",
                reply_markup=get_pinned_message_settings_keyboard(settings)
            )
        except BadRequest: pass
        await query.answer()
        return

    if data == "set_view_bot_protection":
        settings = get_chat_settings(chat_id)
        try:
            await edit_bot_response(
                query, context,
                "🤖 Bot Protection Settings\n\nConfigure how bots are handled when added to the group:",
                reply_markup=get_bot_protection_settings_keyboard(settings)
            )
        except BadRequest: pass
        await query.answer()
        return

    if data == "set_view_link_spam":
        settings = get_chat_settings(chat_id)
        try:
            await edit_bot_response(
                query, context,
                "🔗 Link Spam Protection Settings\n\nAutomatically delete messages containing links from members:",
                reply_markup=get_link_spam_settings_keyboard(settings)
            )
        except BadRequest: pass
        await query.answer()
        return

    if data == "set_view_forward_protection":
        settings = get_chat_settings(chat_id)
        try:
            await edit_bot_response(
                query, context,
                "🔄 Forward Protection Settings\n\nAutomatically delete forwarded messages from members:",
                reply_markup=get_forward_protection_settings_keyboard(settings)
            )
        except BadRequest: pass
        await query.answer()
        return

    if data == "set_view_language_filter":
        settings = get_chat_settings(chat_id)
        try:
            await edit_bot_response(
                query, context,
                "🌐 Language Filter Settings\n\nAutomatically delete messages in languages other than allowed ones.\n\nAllowed: English, Hindi, Hinglish\n\nEmoji & Symbol Blocking Options:",
                reply_markup=get_language_filter_settings_keyboard(settings)
            )
        except BadRequest: pass
        await query.answer()
        return

    if data == "set_view_blocking":
        settings = get_chat_settings(chat_id)
        try:
            await edit_bot_response(
                query, context,
                "🚧 Blocking Settings",
                reply_markup=get_blocking_settings_keyboard(settings)
            )
        except BadRequest: pass
        await query.answer()
        return

    if data == "set_view_manager":
        settings = get_chat_settings(chat_id)
        try:
            await edit_bot_response(
                query, context,
                "👥 Manager Module Settings\n\nEnable or disable Manager commands:",
                reply_markup=get_manager_settings_keyboard(settings)
            )
        except BadRequest: pass
        await query.answer()
        return

    if data.startswith("set_toggle_"):
        key = data.replace("set_toggle_", "")
        settings = get_chat_settings(chat_id)
        
        if key == "warn_penalty":
            # Rotate: ban -> mute -> kick -> ban
            current = settings.get("warn_penalty", "ban")
            new_val = "mute" if current == "ban" else "kick" if current == "mute" else "ban"
            update_chat_setting(chat_id, "warn_penalty", new_val)
        elif key == "command_access":
            # Toggle: all -> admins -> all
            current = settings.get("command_access", "all")
            new_val = "admins" if current == "all" else "all"
            update_chat_setting(chat_id, "command_access", new_val)
        else:
            # Welcome and Clean settings enabled by default, others disabled by default
            default_val = True if "welcome_enabled" in key or "media_enabled" in key or "button_enabled" in key or "clean_" in key else False
            new_val = not settings.get(key, default_val)
            update_chat_setting(chat_id, key, new_val)
        
        # Handle language toggles
        if key.startswith("lang_"):
            lang_code = key.replace("lang_", "")
            allowed = settings.get("allowed_languages", ["en", "hi", "hinglish"])
            if lang_code in allowed:
                allowed.remove(lang_code)
            else:
                allowed.append(lang_code)
            update_chat_setting(chat_id, "allowed_languages", allowed)
        
        # Refresh current menu
        new_settings = get_chat_settings(chat_id)
        try:
            if "welcome" in key: 
                await query.edit_message_reply_markup(reply_markup=get_welcome_settings_keyboard(new_settings))
            elif "clean" in key: 
                if "pinned" in key:
                    await query.edit_message_reply_markup(reply_markup=get_pinned_message_settings_keyboard(new_settings))
                else:
                    await query.edit_message_reply_markup(reply_markup=get_clean_settings_keyboard(new_settings))
            elif "auto_delete" in key: 
                await query.edit_message_reply_markup(reply_markup=get_auto_delete_settings_keyboard(new_settings))
            elif key.startswith("block_") or key == "blocking_enabled":
                await query.edit_message_reply_markup(reply_markup=get_blocking_settings_keyboard(new_settings))
            elif "warn" in key: 
                await query.edit_message_reply_markup(reply_markup=get_mod_settings_keyboard(new_settings))
            elif "command_deletion" in key: 
                await query.edit_message_reply_markup(reply_markup=get_command_deletion_keyboard(new_settings))
            elif "bot_protection" in key:
                await query.edit_message_reply_markup(reply_markup=get_bot_protection_settings_keyboard(new_settings))
            elif "link_spam" in key:
                await query.edit_message_reply_markup(reply_markup=get_link_spam_settings_keyboard(new_settings))
            elif "forward_protection" in key:
                await query.edit_message_reply_markup(reply_markup=get_forward_protection_settings_keyboard(new_settings))
            elif "language_filter" in key or key.startswith("lang_"):
                await query.edit_message_reply_markup(reply_markup=get_language_filter_settings_keyboard(new_settings))
            elif "command_access" in key: 
                await query.edit_message_reply_markup(reply_markup=get_command_access_keyboard(new_settings))
            elif key.startswith("block_") or key == "blocking_enabled":
                await query.edit_message_reply_markup(reply_markup=get_blocking_settings_keyboard(new_settings))
            elif key.startswith("manager_"):
                await query.edit_message_reply_markup(reply_markup=get_manager_settings_keyboard(new_settings))
        except BadRequest: pass
        await query.answer(f"Setting updated!")
        return

    # Handle command permission toggles
    if data.startswith("set_cmd_perm_"):
        cmd_key = data.replace("set_cmd_perm_", "")
        settings = get_chat_settings(chat_id)
        
        # Rotate: all -> admin -> owner -> all
        current = settings.get(cmd_key, "admin")
        if current == "all":
            new_val = "admin"
        elif current == "admin":
            new_val = "owner"
        else:
            new_val = "all"
        
        update_chat_setting(chat_id, cmd_key, new_val)
        
        # Refresh the command permissions menu
        new_settings = get_chat_settings(chat_id)
        try:
            await query.edit_message_reply_markup(reply_markup=get_command_permissions_keyboard(new_settings))
        except BadRequest: pass
        
        access_label = new_val.title()
        await query.answer(f"Command access set to: {access_label}")
        return

    if data.startswith("set_warn_limit_"):
        action = data.replace("set_warn_limit_", "")
        settings = get_chat_settings(chat_id)
        current = settings.get("warn_limit", 3)
        new_limit = current + 1 if action == "add" else max(1, current - 1)
        update_chat_setting(chat_id, "warn_limit", new_limit)
        new_settings = get_chat_settings(chat_id)
        try:
            await query.edit_message_reply_markup(reply_markup=get_mod_settings_keyboard(new_settings))
        except BadRequest: pass
        await query.answer(f"Warn limit set to {new_limit}")
        return

    if data.startswith("set_msg_length_"):
        new_limit = int(data.replace("set_msg_length_", ""))
        update_chat_setting(chat_id, "msg_length_limit", new_limit)
        new_settings = get_chat_settings(chat_id)
        try:
            await query.edit_message_reply_markup(reply_markup=get_msg_length_settings_keyboard(new_settings))
        except BadRequest: pass
        status = f"set to {new_limit} chars" if new_limit > 0 else "disabled"
        await query.answer(f"Message length limit {status}")
        return

    # Handle Time adjustment buttons
    if data.startswith("set_time_"):
        action, amount = data.replace("set_time_", "").split("_")
        amount = int(amount)
        settings = get_chat_settings(chat_id)
        current_time = settings.get("auto_delete_time", 60)
        new_time = current_time + amount if action == "add" else max(1, current_time - amount)
        update_chat_setting(chat_id, "auto_delete_time", new_time)
        new_settings = get_chat_settings(chat_id)
        try:
            await query.edit_message_reply_markup(reply_markup=get_auto_delete_settings_keyboard(new_settings))
        except BadRequest: pass
        await query.answer(f"Time updated to {new_time}s")
        return

    # Handle Welcome Time adjustment buttons
    if data.startswith("set_welcome_time_"):
        action, amount = data.replace("set_welcome_time_", "").split("_")
        amount = int(amount)
        settings = get_chat_settings(chat_id)
        current_time = settings.get("welcome_delete_time", 60)
        new_time = current_time + amount if action == "add" else max(0, current_time - amount)
        update_chat_setting(chat_id, "welcome_delete_time", new_time)
        new_settings = get_chat_settings(chat_id)
        try:
            await query.edit_message_reply_markup(reply_markup=get_welcome_settings_keyboard(new_settings))
        except BadRequest: pass
        await query.answer(f"Welcome deletion time set to {new_time}s")
        return

    # Handle Goodbye Time adjustment buttons
    if data == "set_none":
        await query.answer()
        return

    # Handle Config requests (Set Media, Text, Button)
    if data.startswith("set_config_"):
        config_full = data.replace("set_config_", "")
        
        # Handle clear buttons separately
        if config_full.endswith("_clear"):
            section = config_full.replace("_buttons_clear", "")
            update_chat_setting(chat_id, f"{section}_buttons", [])
            update_chat_setting(chat_id, f"{section}_button_text", None)
            update_chat_setting(chat_id, f"{section}_button_url", None)
            await query.answer("All buttons cleared!")
            new_settings = get_chat_settings(chat_id)
            if section == "welcome": await query.edit_message_reply_markup(reply_markup=get_welcome_settings_keyboard(new_settings))
            return

        if "welcome" in config_full: section = "welcome"
        elif "auto_delete" in config_full: section = "auto_delete"
        elif "msg_length" in config_full: section = "msg_length"
        else: section = "unknown"
        
        config_type = config_full.replace(f"{section}_", "")
        context.user_data["waiting_for_config"] = {"section": section, "type": config_type, "chat_id": chat_id, "user_id": user_id}
        
        prompt_map = {
            "media": f"Please send the photo you want to use as the {section} media.",
            "text": (
                f"˹{update.effective_user.first_name}˼, send now the message you want to set!\n\n"
                "You can use HTML and:\n"
                "• {ID} = user ID\n"
                "• {NAME} = user name\n"
                "• {SURNAME} = user surname\n"
                "• {NAMESURNAME} = name and surname\n"
                "• {LANG} = user language\n"
                "• {DATE} = current date\n"
                "• {TIME} = current time\n"
                "• {WEEKDAY} = week day\n"
                "• {MENTION} = link to the user profile\n"
                "• {USERNAME} = username\n"
                "• {GROUPNAME} = group name\n"
                "• {RULES} = group regulation\n\n"
                "Send /cancel to stop."
            ),
            "buttons_add": f"Please send the {section} button text and URL in this format:\n`Button Text | https://t.me/yourlink`",
            "button": f"Please send the {section} button text and URL in this format:\n`Button Text | https://t.me/yourlink`",
            "limit": f"Please send the maximum character limit for messages (e.g., 500)."
        }
        
        await edit_bot_response(
            query, context, 
            f"📥 **Configuring {section.title()} {config_type.replace('_', ' ').title()}**\n\n{prompt_map.get(config_type, 'Please send the value.')}", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data=f"set_view_{section}")]]),
            parse_mode="HTML"
        )
        await query.answer()

async def handle_setting_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "waiting_for_config" not in context.user_data: return
    config_data = context.user_data["waiting_for_config"]
    if update.effective_user.id != config_data["user_id"]: return
    chat_id, section, config_type = config_data["chat_id"], config_data["section"], config_data["type"]
    if update.message.text == "/cancel":
        del context.user_data["waiting_for_config"]
        await update.message.reply_text("Configuration cancelled.")
        return
    success = False
    setting_key = f"{section}_{config_type}"
    if config_type == "media":
        if update.message.photo:
            update_chat_setting(chat_id, setting_key, update.message.photo[-1].file_id)
            update_chat_setting(chat_id, f"{section}_media_type", "photo")
            success = True
        elif update.message.video:
            update_chat_setting(chat_id, setting_key, update.message.video.file_id)
            update_chat_setting(chat_id, f"{section}_media_type", "video")
            success = True
        elif update.message.animation:
            update_chat_setting(chat_id, setting_key, update.message.animation.file_id)
            update_chat_setting(chat_id, f"{section}_media_type", "animation")
            success = True
        elif update.message.document:
            # Check if it's a gif or video
            mime = update.message.document.mime_type
            if mime and ("video" in mime or "gif" in mime or "image" in mime):
                update_chat_setting(chat_id, setting_key, update.message.document.file_id)
                update_chat_setting(chat_id, f"{section}_media_type", "document")
                success = True
    elif config_type == "text":
        if update.message.text:
            update_chat_setting(chat_id, setting_key, update.message.text)
            success = True
    elif config_type == "buttons_add":
        if update.message.text and "|" in update.message.text:
            try:
                btn_text, btn_url = [x.strip() for x in update.message.text.split("|", 1)]
                if btn_url.startswith("http"):
                    settings = get_chat_settings(chat_id)
                    current_buttons = settings.get(f"{section}_buttons", [])
                    current_buttons.append({"text": btn_text, "url": btn_url})
                    update_chat_setting(chat_id, f"{section}_buttons", current_buttons)
                    success = True
            except Exception: pass
    elif config_type == "button":
        if update.message.text and "|" in update.message.text:
            try:
                btn_text, btn_url = [x.strip() for x in update.message.text.split("|", 1)]
                if btn_url.startswith("http"):
                    update_chat_setting(chat_id, f"{section}_button_text", btn_text)
                    update_chat_setting(chat_id, f"{section}_button_url", btn_url)
                    success = True
            except Exception: pass
    elif config_type == "time":
        if update.message.text and update.message.text.isdigit():
            update_chat_setting(chat_id, setting_key, int(update.message.text))
            success = True
    if success:
        del context.user_data["waiting_for_config"]
        await update.message.reply_text(f"✅ {section.title()} {config_type} updated successfully!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"Back to {section.title()} Settings", callback_data=f"set_view_{section}")]]))

def get_settings_handlers():
    return [
        CommandHandler(["settings", "config"], settings_menu),
        CallbackQueryHandler(open_settings_here, pattern="^settings_open_here_"),
        CallbackQueryHandler(settings_callback, pattern="^set_"),
        CallbackQueryHandler(settings_callback, pattern="^settings_"),
        MessageHandler(filters.ALL & ~filters.COMMAND, handle_setting_input)
    ]
