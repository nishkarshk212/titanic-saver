import logging
from telegram import Update, ChatPermissions
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, CommandHandler
from telegram.error import BadRequest
from config import OWNER_ID, log_to_channel, send_bot_response
from settings_manager import get_chat_settings
from moderation_manager import (
    get_user_warns, add_warn, reset_warns, 
    is_muter as check_is_muter, add_muter, remove_muter, get_all_muters,
    is_voice_chat_manager as check_is_voice_chat_manager,
    add_voice_chat_manager, remove_voice_chat_manager, get_all_voice_chat_managers
)
from user_manager import resolve_username, get_user_id, is_user_admin, load_users
from anonymous_admin import is_anonymous_admin, check_anonymous_admin_ban_permission, check_anonymous_admin_mute_permission

async def can_user_mute(chat_id, user_id, context):
    """Check if a user can mute/unmute (Admin or Muter)."""
    # Check if it's an anonymous admin
    if is_anonymous_admin(user_id):
        has_perm, error_msg = await check_anonymous_admin_mute_permission(chat_id, context)
        return has_perm
    
    if await is_user_admin(chat_id, user_id, context):
        return True
    return check_is_muter(chat_id, user_id)

async def can_user_manage_voice_chat(chat_id, user_id, context):
    """Check if a user can manage voice chats (Admin, Muter, or Voice Chat Manager)."""
    # Admins can always manage voice chats
    if await is_user_admin(chat_id, user_id, context):
        return True
    # Muters can manage voice chats
    if check_is_muter(chat_id, user_id):
        return True
    # Voice chat managers can manage voice chats
    if check_is_voice_chat_manager(chat_id, user_id):
        return True
    return False

async def can_user_ban(chat_id, user_id, context):
    """Check if a user can ban/unban (Admin with can_restrict_members permission)."""
    # Owner can always ban
    from config import OWNER_ID
    if user_id == OWNER_ID:
        return True, None
    
    # Check if it's an anonymous admin
    if is_anonymous_admin(user_id):
        return await check_anonymous_admin_ban_permission(chat_id, context)
    
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        
        # Must be admin or creator
        if member.status not in ['administrator', 'creator']:
            return False, "You must be an admin to ban users."
        
        # Creator has all permissions
        if member.status == 'creator':
            return True, None
        
        # Check if admin has can_restrict_members permission
        if not member.can_restrict_members:
            return False, "❌ You don't have permission to ban users. You need the 'Ban Users' permission."
        
        return True, None
    except Exception as e:
        return False, f"❌ Error checking permissions: {str(e)}"

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
    """Bans a user or channel from the chat or channel."""
    chat_id = update.effective_chat.id
    sender_id = update.effective_user.id if update.effective_user else None
    chat_type = update.effective_chat.type
    
    # Check if user has ban permission (not just admin status)
    if chat_type != 'channel':
        can_ban, error_msg = await can_user_ban(chat_id, sender_id, context)
        if not can_ban:
            await send_bot_response(update, context, error_msg)
            return
    
    # Check bot rights
    has_rights, error_msg = await check_bot_admin_rights(chat_id, context, ['can_restrict_members'])
    if not has_rights:
        await send_bot_response(update, context, error_msg)
        return

    target_id, target_name = await get_user_id(update, context)
    if not target_id:
        await send_bot_response(update, context, "Please reply to a user/channel or provide an ID/username to ban.")
        return

    try:
        if str(target_id).startswith('-100'):
            # It's a channel/chat
            await context.bot.ban_chat_sender_chat(chat_id, target_id)
            await send_bot_response(update, context, f"✅ Banned channel {target_name}.")
        else:
            # It's a user
            await context.bot.ban_chat_member(chat_id, target_id)
            await send_bot_response(update, context, f"✅ Banned {target_name}.")
            
        admin_name = update.effective_user.first_name if update.effective_user else "Channel Admin"
        await log_to_channel(context, f"🔨 #BAN\nTarget: {target_name} ({target_id})\nAdmin: {admin_name}")
    except Exception as e:
        await send_bot_response(update, context, f"Error: {e}")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unbans a user or channel from the chat or channel."""
    chat_id = update.effective_chat.id
    sender_id = update.effective_user.id if update.effective_user else None
    chat_type = update.effective_chat.type
    
    # Check if user has ban permission (not just admin status)
    if chat_type != 'channel':
        can_ban, error_msg = await can_user_ban(chat_id, sender_id, context)
        if not can_ban:
            await send_bot_response(update, context, error_msg)
            return
    
    target_id, target_name = await get_user_id(update, context)
    if not target_id: return

    try:
        if str(target_id).startswith('-100'):
            # It's a channel/chat
            await context.bot.unban_chat_sender_chat(chat_id, target_id)
            await send_bot_response(update, context, f"✅ Unbanned channel {target_name}.")
        else:
            # It's a user
            await context.bot.unban_chat_member(chat_id, target_id, only_if_banned=True)
            await send_bot_response(update, context, f"✅ Unbanned {target_name}.")
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
        await send_bot_response(update, context, f"✅ {user_name} is now a muter. They can use /mute, /unmute, and manage voice chats.")

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

async def voicechatmgr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to add or remove a voice chat manager."""
    chat_id = update.effective_chat.id
    sender_id = update.effective_user.id
    
    if not await is_user_admin(chat_id, sender_id, context):
        await send_bot_response(update, context, "Admin only command.")
        return

    # Check if we should list all voice chat managers
    if not context.args and not update.message.reply_to_message:
        manager_ids = get_all_voice_chat_managers(chat_id)
        if not manager_ids:
            await send_bot_response(update, context, "No voice chat managers set in this group.")
            return
        
        manager_list = []
        users_data = load_users()
        for mid in manager_ids:
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
            manager_list.append(f"• {user_name}")
        
        await send_bot_response(
            update, context,
            "🎙️ <b>Voice Chat Managers:</b>\n" + "\n".join(manager_list),
            parse_mode=ParseMode.HTML
        )
        return

    user_id, user_name = await get_user_id(update, context)
    if not user_id:
        await send_bot_response(update, context, "Please reply to a user or provide a username/ID to set as voice chat manager.")
        return

    if check_is_voice_chat_manager(chat_id, user_id):
        remove_voice_chat_manager(chat_id, user_id)
        await send_bot_response(update, context, f"✅ Removed {user_name} from voice chat managers.")
    else:
        add_voice_chat_manager(chat_id, user_id)
        await send_bot_response(update, context, f"✅ {user_name} is now a voice chat manager. They can manage voice/video chats.")

async def unvoicechatmgr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to remove a voice chat manager specifically."""
    chat_id = update.effective_chat.id
    sender_id = update.effective_user.id
    
    if not await is_user_admin(chat_id, sender_id, context):
        await send_bot_response(update, context, "Admin only command.")
        return

    user_id, user_name = await get_user_id(update, context)
    if not user_id:
        await send_bot_response(update, context, "Please reply to a user or provide a username/ID to remove from voice chat managers.")
        return

    if not check_is_voice_chat_manager(chat_id, user_id):
        await send_bot_response(update, context, f"❌ {user_name} is not a voice chat manager.")
        return

    remove_voice_chat_manager(chat_id, user_id)
    await send_bot_response(update, context, f"✅ Removed {user_name} from voice chat managers.")

def get_moderation_handlers():
    return [
        CommandHandler("ban", ban_command),
        CommandHandler("unban", unban_command),
        CommandHandler("mute", mute_command),
        CommandHandler("unmute", unmute_command),
        CommandHandler("muter", muter_command),
        CommandHandler("unmuter", unmuter_command),
        CommandHandler("warn", warn_command),
        CommandHandler("unwarn", unwarn_command),
        CommandHandler("voicechatmgr", voicechatmgr_command),
        CommandHandler("unvoicechatmgr", unvoicechatmgr_command)
    ]
