from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.error import BadRequest
from settings_manager import get_chat_settings, update_chat_setting
from config import OWNER_ID, send_bot_response, edit_bot_response
from user_manager import can_user_configure_settings

async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Check granular permissions (Change Info + Ban Users)
    if not await can_user_configure_settings(chat_id, user_id, context):
        await send_bot_response(update, context, "You need both 'Change Group Info' and 'Ban Users' permissions to configure settings.")
        return

    keyboard = get_main_settings_keyboard()
    await send_bot_response(
        update, context,
        f"⚙️ Group Settings for: {update.effective_chat.title}\n\nSelect a section to configure:",
        reply_markup=keyboard
    )

def get_main_settings_keyboard():
    keyboard = [
        [InlineKeyboardButton("👋 Welcome Settings", callback_data="set_view_welcome")],
        [InlineKeyboardButton("🧹 Clean Service", callback_data="set_view_clean")],
        [InlineKeyboardButton("💣 Auto Delete", callback_data="set_view_auto_delete")],
        [InlineKeyboardButton("🚫 Block Content", callback_data="set_view_block_content")],
        [InlineKeyboardButton("📏 Message Length", callback_data="set_view_msg_length")],
        [InlineKeyboardButton("🛡️ Moderation Settings", callback_data="set_view_mod")],
        [InlineKeyboardButton("🗑️ Command Deletion", callback_data="set_view_command_deletion")],
        [InlineKeyboardButton("🔑 Command Access", callback_data="set_view_command_access")],
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

def get_block_content_settings_keyboard(settings):
    limit = settings.get("block_warn_limit", 3)
    penalty = settings.get("block_warn_penalty", "warn").title()
    
    keyboard = [
        [
            InlineKeyboardButton("-", callback_data="set_block_warn_limit_sub"),
            InlineKeyboardButton(f"Block Warn Limit: {limit}", callback_data="set_none"),
            InlineKeyboardButton("+", callback_data="set_block_warn_limit_add")
        ],
        [InlineKeyboardButton(f"Block Penalty: {penalty}", callback_data="set_toggle_block_warn_penalty")],
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
        [InlineKeyboardButton("🔙 Back", callback_data="set_view_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Granular permission check
    if not await can_user_configure_settings(chat_id, user_id, context):
        await query.answer("You need 'Change Info' and 'Ban Users' permissions to access settings.", show_alert=True)
        return

    data = query.data
    
    if data == "set_close":
        await query.message.delete()
        return
        
    if data == "set_view_main":
        try:
            await edit_bot_response(
                query, context,
                f"⚙️ Group Settings for: {update.effective_chat.title}\n\nSelect a section to configure:",
                reply_markup=get_main_settings_keyboard()
            )
        except BadRequest: pass
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
        settings = get_chat_settings(chat_id)
        try:
            await edit_bot_response(
                query, context,
                "🚫 Block Content Configuration\n\nConfigure penalties for using blocked words/media:",
                reply_markup=get_block_content_settings_keyboard(settings)
            )
        except BadRequest: pass
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

    if data.startswith("set_toggle_"):
        key = data.replace("set_toggle_", "")
        settings = get_chat_settings(chat_id)
        
        if key == "warn_penalty":
            # Rotate: ban -> mute -> kick -> ban
            current = settings.get("warn_penalty", "ban")
            new_val = "mute" if current == "ban" else "kick" if current == "mute" else "ban"
            update_chat_setting(chat_id, "warn_penalty", new_val)
        elif key == "block_warn_penalty":
            # Rotate: warn -> mute -> ban -> kick -> warn
            current = settings.get("block_warn_penalty", "warn")
            order = ["warn", "mute", "ban", "kick"]
            try:
                idx = order.index(current)
                new_val = order[(idx + 1) % len(order)]
            except ValueError:
                new_val = "warn"
            update_chat_setting(chat_id, "block_warn_penalty", new_val)
        elif key == "command_access":
            # Toggle: all -> admins -> all
            current = settings.get("command_access", "all")
            new_val = "admins" if current == "all" else "all"
            update_chat_setting(chat_id, "command_access", new_val)
        else:
            # Welcome enabled by default, others disabled by default
            default_val = True if "welcome_enabled" in key or "media_enabled" in key or "button_enabled" in key or "clean_service_enabled" in key else False
            new_val = not settings.get(key, default_val)
            update_chat_setting(chat_id, key, new_val)
        
        # Refresh current menu
        new_settings = get_chat_settings(chat_id)
        try:
            if "welcome" in key: await query.edit_message_reply_markup(reply_markup=get_welcome_settings_keyboard(new_settings))
            elif "clean" in key: await query.edit_message_reply_markup(reply_markup=get_clean_settings_keyboard(new_settings))
            elif "auto_delete" in key: await query.edit_message_reply_markup(reply_markup=get_auto_delete_settings_keyboard(new_settings))
            elif "block" in key: await query.edit_message_reply_markup(reply_markup=get_block_content_settings_keyboard(new_settings))
            elif "warn" in key: await query.edit_message_reply_markup(reply_markup=get_mod_settings_keyboard(new_settings))
            elif "command_deletion" in key: await query.edit_message_reply_markup(reply_markup=get_command_deletion_keyboard(new_settings))
            elif "command_access" in key: await query.edit_message_reply_markup(reply_markup=get_command_access_keyboard(new_settings))
        except BadRequest: pass
        await query.answer(f"Setting updated!")
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

    if data.startswith("set_block_warn_limit_"):
        action = data.replace("set_block_warn_limit_", "")
        settings = get_chat_settings(chat_id)
        current = settings.get("block_warn_limit", 3)
        new_limit = current + 1 if action == "add" else max(1, current - 1)
        update_chat_setting(chat_id, "block_warn_limit", new_limit)
        new_settings = get_chat_settings(chat_id)
        try:
            await query.edit_message_reply_markup(reply_markup=get_block_content_settings_keyboard(new_settings))
        except BadRequest: pass
        await query.answer(f"Block warn limit set to {new_limit}")
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
        CommandHandler("settings", settings_menu),
        CallbackQueryHandler(settings_callback, pattern="^set_"),
        MessageHandler(filters.ALL & ~filters.COMMAND, handle_setting_input)
    ]
