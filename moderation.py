import logging
from telegram import Update, ChatPermissions
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, CommandHandler
from telegram.error import BadRequest
from config import OWNER_ID, log_to_channel, send_bot_response
from settings_manager import get_chat_settings
from moderation_manager import (
    get_user_warns, add_warn, reset_warns, 
    is_muter as check_is_muter, add_muter, remove_muter, get_all_muters
)
from user_manager import resolve_username, get_user_id, is_user_admin, load_users

async def can_user_mute(chat_id, user_id, context):
    """Check if a user can mute/unmute (Admin or Muter)."""
    if await is_user_admin(chat_id, user_id, context):
        return True
    return check_is_muter(chat_id, user_id)

async def check_bot_admin_rights(chat_id, context, required_rights=None):
    """Checks if the bot has the required administrative rights."""
    try:
        bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        if bot_member.status == 'creator':
            return True, None
        if bot_member.status != 'administrator':
            return False, "❌ I am not an administrator in this group."
        
        if required_rights:
            missing = []
            for right in required_rights:
                if not getattr(bot_member, right, False):
                    missing.append(right)
            if missing:
                return False, f"❌ I am missing the following rights: {', '.join(missing)}"
        return True, None
    except Exception as e:
        return False, f"❌ Error checking bot rights: {str(e)}"

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bans a user from the chat."""
    chat_id = update.effective_chat.id
    sender_id = update.effective_user.id
    
    if not await is_user_admin(chat_id, sender_id, context):
        await send_bot_response(update, context, "You must be an admin to ban users.")
        return

    # Check bot rights
    has_rights, error_msg = await check_bot_admin_rights(chat_id, context, ['can_restrict_members'])
    if not has_rights:
        await send_bot_response(update, context, error_msg)
        return

    user_id, user_name = await get_user_id(update, context)
    if not user_id:
        await send_bot_response(update, context, "Please reply to a user or provide a user ID to ban.")
        return

    try:
        await context.bot.ban_chat_member(chat_id, user_id)
        await send_bot_response(update, context, f"✅ Banned {user_name}.")
        await log_to_channel(context, f"🔨 #BAN\nUser: {user_name} ({user_id})\nAdmin: {update.effective_user.first_name}")
    except Exception as e:
        await send_bot_response(update, context, f"Error: {e}")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    sender_id = update.effective_user.id
    
    if not await is_user_admin(chat_id, sender_id, context):
        return

    user_id, user_name = await get_user_id(update, context)
    if not user_id: return

    try:
        await context.bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
        await send_bot_response(update, context, f"✅ Unbanned {user_name}.")
    except Exception as e:
        await send_bot_response(update, context, f"Error: {e}")

async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mutes a user by restricting their permissions."""
    chat_id = update.effective_chat.id
    sender_id = update.effective_user.id
    
    # Check if user is admin or muter
    if not await can_user_mute(chat_id, sender_id, context):
        await send_bot_response(update, context, "You must be an admin or have the 'Muter' role to mute users.")
        return

    # Check bot rights
    has_rights, error_msg = await check_bot_admin_rights(chat_id, context, ['can_restrict_members'])
    if not has_rights:
        await send_bot_response(update, context, error_msg)
        return

    user_id, user_name = await get_user_id(update, context)
    if not user_id: return

    try:
        await context.bot.restrict_chat_member(chat_id, user_id, permissions=ChatPermissions(can_send_messages=False))
        await send_bot_response(update, context, f"🔇 Muted {user_name}.")
    except Exception as e:
        await send_bot_response(update, context, f"Error: {e}")

async def unmute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    sender_id = update.effective_user.id
    
    if not await can_user_mute(chat_id, sender_id, context):
        await send_bot_response(update, context, "You don't have permission to unmute users.")
        return

    user_id, user_name = await get_user_id(update, context)
    if not user_id: return

    try:
        await context.bot.restrict_chat_member(chat_id, user_id, permissions=ChatPermissions(
            can_send_messages=True, 
            can_send_audios=True,
            can_send_documents=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_video_notes=True,
            can_send_voice_notes=True,
            can_send_polls=True, 
            can_send_other_messages=True,
            can_add_web_page_previews=True
        ))
        await send_bot_response(update, context, f"🔊 Unmuted {user_name}.")
    except Exception as e:
        await send_bot_response(update, context, f"Error: {e}")

async def muter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to add or remove a muter."""
    chat_id = update.effective_chat.id
    sender_id = update.effective_user.id
    
    if not await is_user_admin(chat_id, sender_id, context):
        await send_bot_response(update, context, "Admin only command.")
        return

    # Check if we should list all muters
    if not context.args and not update.message.reply_to_message:
        muter_ids = get_all_muters(chat_id)
        if not muter_ids:
            await send_bot_response(update, context, "No muters set in this group.")
            return
        
        muter_list = []
        users_data = load_users()
        for mid in muter_ids:
            user_name = f"<code>{mid}</code>"
            # Try to resolve username or use ID
            found = False
            for username, info in users_data.items():
                if str(info["id"]) == str(mid):
                    user_name = f"{info['name']} (@{username})"
                    found = True
                    break
            if not found:
                # If not in cache, just show ID
                user_name = f"<code>{mid}</code>"
            muter_list.append(f"• {user_name}")
        
        await send_bot_response(
            update, context,
            "🛡️ <b>Muter List:</b>\n" + "\n".join(muter_list),
            parse_mode=ParseMode.HTML
        )
        return

    user_id, user_name = await get_user_id(update, context)
    if not user_id:
        await send_bot_response(update, context, "Please reply to a user or provide a username/ID to set as muter.")
        return

    if check_is_muter(chat_id, user_id):
        remove_muter(chat_id, user_id)
        await send_bot_response(update, context, f"✅ Removed {user_name} from muters.")
    else:
        add_muter(chat_id, user_id)
        await send_bot_response(update, context, f"✅ {user_name} is now a muter. They can use /mute and /unmute.")

async def unmuter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to remove a muter specifically."""
    chat_id = update.effective_chat.id
    sender_id = update.effective_user.id
    
    if not await is_user_admin(chat_id, sender_id, context):
        await send_bot_response(update, context, "Admin only command.")
        return

    user_id, user_name = await get_user_id(update, context)
    if not user_id:
        await send_bot_response(update, context, "Please reply to a user or provide a username/ID to remove from muters.")
        return

    if check_is_muter(chat_id, user_id):
        remove_muter(chat_id, user_id)
        await send_bot_response(update, context, f"✅ Removed {user_name} from muters.")
    else:
        await send_bot_response(update, context, f"❌ {user_name} is not a muter.")

async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    sender_id = update.effective_user.id
    
    if not await is_user_admin(chat_id, sender_id, context): return

    user_id, user_name = await get_user_id(update, context)
    if not user_id: return

    settings = get_chat_settings(chat_id)
    limit = settings.get("warn_limit", 3)
    penalty = settings.get("warn_penalty", "ban")

    current_warns = add_warn(chat_id, user_id)
    
    if current_warns >= limit:
        reset_warns(chat_id, user_id)
        if penalty == "ban":
            await context.bot.ban_chat_member(chat_id, user_id)
            await send_bot_response(update, context, f"⛔ {user_name} reached warn limit ({limit}/{limit}) and was banned.")
        elif penalty == "mute":
            await context.bot.restrict_chat_member(chat_id, user_id, permissions=ChatPermissions(can_send_messages=False))
            await send_bot_response(update, context, f"⛔ {user_name} reached warn limit ({limit}/{limit}) and was muted.")
        elif penalty == "kick":
            await context.bot.ban_chat_member(chat_id, user_id)
            await context.bot.unban_chat_member(chat_id, user_id)
            await send_bot_response(update, context, f"⛔ {user_name} reached warn limit ({limit}/{limit}) and was kicked.")
    else:
        await send_bot_response(update, context, f"⚠️ Warned {user_name}. ({current_warns}/{limit})")

async def unwarn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    sender_id = update.effective_user.id
    
    if not await is_user_admin(chat_id, sender_id, context): return

    user_id, user_name = await get_user_id(update, context)
    if not user_id: return

    reset_warns(chat_id, user_id)
    await send_bot_response(update, context, f"✅ Reset warnings for {user_name}.")

def get_moderation_handlers():
    return [
        CommandHandler("ban", ban_command),
        CommandHandler("unban", unban_command),
        CommandHandler("mute", mute_command),
        CommandHandler("unmute", unmute_command),
        CommandHandler("muter", muter_command),
        CommandHandler("unmuter", unmuter_command),
        CommandHandler("warn", warn_command),
        CommandHandler("unwarn", unwarn_command)
    ]
