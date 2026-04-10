from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.constants import ParseMode
from config import send_bot_response, edit_bot_response
from settings_manager import get_chat_settings
from user_manager import is_user_admin

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main help command."""
    chat_id = update.effective_chat.id
    settings = get_chat_settings(chat_id)
    
    # Check access
    if settings.get("command_access") == "admins":
        if not await is_user_admin(chat_id, update.effective_user.id, context):
            return

    keyboard = get_help_keyboard()
    await send_bot_response(
        update, context,
        "📚 <b>Bot Help Menu</b>\n\n"
        "Welcome to the help menu! Select a category below to see available commands and features.",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

def get_help_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🛡️ Moderation", callback_data="help_mod"),
            InlineKeyboardButton("⚙️ Settings", callback_data="help_settings")
        ],
        [
            InlineKeyboardButton("👋 Welcome/Goodbye", callback_data="help_welcome"),
            InlineKeyboardButton("🧹 Clean Service", callback_data="help_clean")
        ],
        [
            InlineKeyboardButton("💣 Auto Delete", callback_data="help_auto"),
            InlineKeyboardButton("🔍 Filters", callback_data="help_filters")
        ],
        [
            InlineKeyboardButton("🚫 Block Content", callback_data="help_block"),
            InlineKeyboardButton("📌 Pinned Messages", callback_data="help_pinned")
        ],
        [
            InlineKeyboardButton("🤖 Bot Protection", callback_data="help_bot_prot"),
            InlineKeyboardButton("❌ Close", callback_data="help_close")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "help_close":
        await query.message.delete()
        await query.answer()
        return

    help_text = ""
    if data == "help_mod":
        help_text = (
            "🛡️ <b>Moderation Commands</b>\n\n"
            "• /ban - Ban a user (reply, ID, or @username)\n"
            "• /unban - Unban a user\n"
            "• /mute - Mute a user (prevents sending messages)\n"
            "• /unmute - Unmute a user\n"
            "• /warn - Give a user a warning\n"
            "• /unwarn - Reset a user's warnings\n"
            "• /pin - Pin a message (reply only)\n"
            "• /unpin - Unpin a message (reply only) or all pinned messages\n"
            "• /promote - Promote a user to admin with custom perms\n"
            "• /demote - Remove admin rights from a user\n"
            "• /setadmintitle - Set custom admin title (16 chars max)\n"
            "• /deladmintitle - Remove admin title from a user\n"
            "• /muter - Toggle 'Muter' role (can only mute/unmute)\n"
            "• /unmuter - Remove 'Muter' role from a user\n"
            "• /voicechatmgr - Toggle 'Voice Chat Manager' role\n"
            "• /unvoicechatmgr - Remove 'Voice Chat Manager' role from a user"
        )
    elif data == "help_settings":
        help_text = (
            "⚙️ <b>Settings & Config</b>\n\n"
            "• /config - Open the interactive settings menu\n"
            "• /id - Get your user ID and current chat ID\n\n"
            "<i>Note: Only admins with 'Change Info' and 'Ban Users' can access settings.</i>"
        )
    elif data == "help_welcome":
        help_text = (
            "👋 <b>Welcome Message</b>\n\n"
            "Configure how new members are greeted via /config. Supports:\n"
            "• HTML formatting\n"
            "• Custom Media (Photos)\n"
            "• Custom Buttons (Text | URL)\n"
            "• Placeholders: {ID}, {NAME}, {USERNAME}, {MENTION}, etc.\n\n"
            "<i>Note: Goodbye messages are not supported by this bot.</i>"
        )
    elif data == "help_clean":
        help_text = (
            "🧹 <b>Clean Service</b>\n\n"
            "Automatically deletes system messages:\n"
            "• User Joined/Left\n"
            "• Voice Chat Started/Ended/Scheduled/Invited\n"
            "Enable specific types in /config > Clean Service."
        )
    elif data == "help_pinned":
        help_text = (
            "📌 <b>Pinned Messages</b>\n\n"
            "Automatically deletes 'X pinned a message' service notifications.\n"
            "Enable in /config > Pinned Messages."
        )
    elif data == "help_auto":
        help_text = (
            "💣 <b>Auto Delete</b>\n\n"
            "Automatically deletes every message in the group after a custom delay.\n"
            "• Set delay (H/M/S) in /config > Auto Delete.\n"
            "• Toggle ON/OFF as needed."
        )
    elif data == "help_filters":
        help_text = (
            "🔍 <b>Filters (Auto-Reply)</b>\n\n"
            "• /filter &lt;trigger&gt; &lt;reply&gt; - Set a custom auto-reply\n"
            "• /filters - List all active filters\n"
            "• /stop &lt;trigger&gt; - Remove a specific filter\n"
            "• /stopall - Remove all filters in the chat"
        )
    elif data == "help_block":
        help_text = (
            "🚫 <b>Block Content</b>\n\n"
            "• /block - Reply to a message (text/media) or use `/block &lt;text&gt;` to add content to the block list.\n"
            "• /unblock - Reply to a message or use `/unblock &lt;text&gt;` to remove content from the block list.\n"
            "• /listblock - List all blocked text content in the group.\n\n"
            "📏 <b>Message Length Limit</b>\n\n"
            "Configure a maximum character limit for messages in /config &gt; Message Length. Messages exceeding this limit will be automatically deleted.\n\n"
            "<i>Note: Admins are exempt from these checks.</i>"
        )
    elif data == "help_bot_prot":
        help_text = (
            "🤖 <b>Bot Protection</b>\n\n"
            "Prevents other bots from being added to the group.\n"
            "• If enabled, any bot added to the group will be automatically kicked.\n"
            "• Enable/Disable in /config > Bot Protection.\n\n"
            "<i>Note: This bot itself is exempt.</i>"
        )

    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="help_main")]]
    
    if data == "help_main":
        await edit_bot_response(
            query, context,
            "📚 <b>Bot Help Menu</b>\n\n"
            "Welcome to the help menu! Select a category below to see available commands and features.",
            parse_mode=ParseMode.HTML,
            reply_markup=get_help_keyboard()
        )
    else:
        await edit_bot_response(
            query, context,
            help_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    await query.answer()

def get_help_handlers():
    return [
        CommandHandler("help", help_command),
        CallbackQueryHandler(help_callback, pattern="^help_")
    ]
