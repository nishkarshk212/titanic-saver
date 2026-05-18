"""
Manager Actions - Ban, Unban, Mute, Unmute, Kick, etc.
Ported from AnnieXMusic to python-telegram-bot
"""

import asyncio
import logging
from datetime import datetime, timedelta
from telegram import Update, ChatPermissions, ChatMemberAdministrator, ChatMemberOwner, ChatMemberBanned, ChatMemberRestricted
from telegram.ext import ContextTypes, CommandHandler
from telegram.constants import ChatMemberStatus
from settings_manager_mongo import get_chat_settings
from anonymous_admin import (
    is_anonymous_admin, 
    check_anonymous_admin_ban_permission, 
    check_anonymous_admin_mute_permission,
    check_anonymous_admin_promote_permission,
    check_anonymous_admin_pin_permission,
    check_anonymous_admin_delete_permission,
    check_anonymous_admin_invite_permission,
    check_anonymous_admin_change_info_permission
)
from config import OWNER_ID
from admin_manager_mongo import update_admin_cache, get_stored_admin_permissions

def parse_time(time_str):
    """Parse time string like '1h', '30m', '2d' into timedelta."""
    time_str = time_str.lower()
    if time_str.endswith('d'):
        return timedelta(days=int(time_str[:-1]))
    elif time_str.endswith('h'):
        return timedelta(hours=int(time_str[:-1]))
    elif time_str.endswith('m'):
        return timedelta(minutes=int(time_str[:-1]))
    elif time_str.endswith('s'):
        return timedelta(seconds=int(time_str[:-1]))
    return None

from user_manager_mongo import get_user_id

async def is_admin(chat, user_id):
    """Check if user is admin."""
    try:
        member = await chat.get_member(user_id)
        return isinstance(member, (ChatMemberAdministrator, ChatMemberOwner))
    except:
        return False

async def check_admin_permission(update: Update, context: ContextTypes.DEFAULT_TYPE, permission: str = None):
    """
    Check if the user has the required administrative permission.
    Handles both regular and anonymous admins.
    
    Args:
        update: The Telegram update
        context: The bot context
        permission: The permission key to check (e.g., 'can_restrict_members')
                   If None, just checks if user is an admin.
    
    Returns:
        tuple: (has_permission, error_message)
    """
    user = update.effective_user
    chat = update.effective_chat
    
    if user.id == OWNER_ID:
        return True, None

    # Check cache first for high speed
    stored_perms = get_stored_admin_permissions(chat.id, user.id)
    if stored_perms:
        if not permission:
            return True, None
        if stored_perms.get(permission, False):
            # If they have the permission in cache, trust it for speed
            # We'll still update the cache in the background occasionally or on use
            return True, None

    # Check if it's an anonymous admin
    if is_anonymous_admin(user.id):
        if not permission:
            # For general admin check, if they are anonymous, they are an admin
            return True, None
        
        # Mapping permission strings to anonymous admin check functions
        anon_checks = {
            'can_restrict_members': check_anonymous_admin_ban_permission,
            'can_promote_members': check_anonymous_admin_promote_permission,
            'can_pin_messages': check_anonymous_admin_pin_permission,
            'can_delete_messages': check_anonymous_admin_delete_permission,
            'can_invite_users': check_anonymous_admin_invite_permission,
            'can_change_info': check_anonymous_admin_change_info_permission,
        }
        
        if permission in anon_checks:
            return await anon_checks[permission](chat.id, context)
        return False, f"❌ Unsupported permission check: {permission}"
    
    # Regular admin check
    try:
        member = await chat.get_member(user.id)
        
        # Save permissions to database
        permissions = {
            "can_change_info": getattr(member, "can_change_info", False),
            "can_delete_messages": getattr(member, "can_delete_messages", False),
            "can_restrict_members": getattr(member, "can_restrict_members", False),
            "can_invite_users": getattr(member, "can_invite_users", False),
            "can_pin_messages": getattr(member, "can_pin_messages", False),
            "can_promote_members": getattr(member, "can_promote_members", False),
            "can_manage_chat": getattr(member, "can_manage_chat", False),
            "can_manage_video_chats": getattr(member, "can_manage_video_chats", False),
            "is_anonymous": getattr(member, "is_anonymous", False),
        }
        
        if isinstance(member, ChatMemberOwner):
            for k in permissions: permissions[k] = True
            # Background task to update DB cache
            asyncio.create_task(asyncio.to_thread(update_admin_cache, chat.id, user.id, permissions))
            return True, None
        
        # Background task to update DB cache
        asyncio.create_task(asyncio.to_thread(update_admin_cache, chat.id, user.id, permissions))
        
        if not isinstance(member, ChatMemberAdministrator):
            return False, "You need to be an admin to use this command."
        
        if not permission:
            return True, None
        
        # Check specific permission for regular admin
        if getattr(member, permission, False):
            return True, None
        
        # Friendly error messages for specific permissions
        perm_names = {
            'can_restrict_members': "Ban Users",
            'can_promote_members': "Add New Admins",
            'can_pin_messages': "Pin Messages",
            'can_delete_messages': "Delete Messages",
            'can_invite_users': "Invite Users",
            'can_change_info': "Change Group Info",
        }
        perm_name = perm_names.get(permission, permission)
        return False, f"❌ You don't have the '{perm_name}' permission."
        
    except Exception as e:
        logging.error(f"Error checking admin permission (falling back to DB): {e}")
        
        # Fallback to database
        stored_perms = get_stored_admin_permissions(chat.id, user.id)
        if stored_perms:
            if not permission:
                return True, None
            if stored_perms.get(permission, False):
                return True, None
            
            perm_names = {
                'can_restrict_members': "Ban Users",
                'can_promote_members': "Add New Admins",
                'can_pin_messages': "Pin Messages",
                'can_delete_messages': "Delete Messages",
                'can_invite_users': "Invite Users",
                'can_change_info': "Change Group Info",
            }
            perm_name = perm_names.get(permission, permission)
            return False, f"❌ You don't have the '{perm_name}' permission (cached)."
            
        return False, "Error checking permissions."

async def check_bot_permission(update: Update, context: ContextTypes.DEFAULT_TYPE, permission: str):
    """
    Check if the bot itself has the required administrative permission.
    
    Args:
        update: The Telegram update
        context: The bot context
        permission: The permission key to check
        
    Returns:
        tuple: (has_permission, error_message)
    """
    chat = update.effective_chat
    try:
        bot_member = await chat.get_member(context.bot.id)
        if bot_member.status == 'creator':
            return True, None
            
        if bot_member.status != 'administrator':
            return False, "❌ I need to be an administrator to perform this action."
            
        if getattr(bot_member, permission, False):
            return True, None
            
        perm_names = {
            'can_restrict_members': "Ban Users",
            'can_promote_members': "Add New Admins",
            'can_pin_messages': "Pin Messages",
            'can_delete_messages': "Delete Messages",
            'can_invite_users': "Invite Users",
            'can_change_info': "Change Group Info",
        }
        perm_name = perm_names.get(permission, permission)
        return False, f"❌ I don't have the '{perm_name}' permission."
    except Exception as e:
        logging.error(f"Error checking bot permission: {e}")
        return False, "Error checking bot permissions."

def get_user_from_args(update, context):
    """Extract user ID and name from command args or reply."""
    # This is a legacy function, we should use get_user_id from user_manager_mongo
    return None, None, None

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban a user from the group."""
    chat = update.effective_chat
    user = update.effective_user
    
    # Check if command is enabled
    settings = get_chat_settings(chat.id)
    if not settings.get("manager_ban_enabled", True):
        return await update.message.reply_text("❌ The /ban command is currently disabled.")
    
    # Permission check
    has_perm, error_msg = await check_admin_permission(update, context, 'can_restrict_members')
    if not has_perm:
        return await update.message.reply_text(error_msg)
    
    # Bot permission check
    has_bot_perm, bot_error_msg = await check_bot_permission(update, context, 'can_restrict_members')
    if not has_bot_perm:
        return await update.message.reply_text(bot_error_msg)
    
    user_id, name = await get_user_id(update, context)
    reason = " ".join(context.args[1:]) if context.args and len(context.args) > 1 else " ".join(context.args) if context.args and not str(context.args[0]).startswith('@') and not str(context.args[0]).isdigit() else None
    
    if not user_id:
        return await update.message.reply_text("Usage: /ban @username or reply to a user with /ban [reason]")
    
    try:
        member = await chat.get_member(user_id)
        if isinstance(member, (ChatMemberAdministrator, ChatMemberOwner)):
            return await update.message.reply_text("I cannot ban an admin or the group owner.")
        
        if isinstance(member, ChatMemberBanned):
            return await update.message.reply_text("User is already banned.")
        
        await chat.ban_member(user_id)
        
        admin_name = user.full_name
        text = f"» Ban a user in {chat.title}\n"
        text += f" User  : {name}\n"
        text += f" Admin : {admin_name}"
        if reason:
            text += f"\nReason: {reason}"
        
        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f"Failed to ban user: {str(e)}")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unban a user from the group."""
    chat = update.effective_chat
    user = update.effective_user
    
    # Check if command is enabled
    settings = get_chat_settings(chat.id)
    if not settings.get("manager_unban_enabled", True):
        return await update.message.reply_text("❌ The /unban command is currently disabled.")
    
    # Permission check
    has_perm, error_msg = await check_admin_permission(update, context, 'can_restrict_members')
    if not has_perm:
        return await update.message.reply_text(error_msg)
    
    # Bot permission check
    has_bot_perm, bot_error_msg = await check_bot_permission(update, context, 'can_restrict_members')
    if not has_bot_perm:
        return await update.message.reply_text(bot_error_msg)
    
    user_id, name = await get_user_id(update, context)
    reason = " ".join(context.args[1:]) if context.args and len(context.args) > 1 else " ".join(context.args) if context.args and not str(context.args[0]).startswith('@') and not str(context.args[0]).isdigit() else None
    
    if not user_id:
        return await update.message.reply_text("Usage: /unban @username or reply to a user with /unban [reason]")
    
    try:
        member = await chat.get_member(user_id)
        if not isinstance(member, ChatMemberBanned):
            return await update.message.reply_text("User is not banned.")
        
        await chat.unban_member(user_id)
        
        admin_name = user.full_name
        text = f"» Unban a user in {chat.title}\n"
        text += f" User  : {name}\n"
        text += f" Admin : {admin_name}"
        if reason:
            text += f"\nReason: {reason}"
        
        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f"Failed to unban user: {str(e)}")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mute a user in the group."""
    chat = update.effective_chat
    user = update.effective_user
    
    # Check if command is enabled
    settings = get_chat_settings(chat.id)
    if not settings.get("manager_mute_enabled", True):
        return await update.message.reply_text("❌ The /mute command is currently disabled.")
    
    # Permission check
    has_perm, error_msg = await check_admin_permission(update, context, 'can_restrict_members')
    if not has_perm:
        return await update.message.reply_text(error_msg)
    
    # Bot permission check
    has_bot_perm, bot_error_msg = await check_bot_permission(update, context, 'can_restrict_members')
    if not has_bot_perm:
        return await update.message.reply_text(bot_error_msg)
    
    user_id, name = await get_user_id(update, context)
    reason = " ".join(context.args[1:]) if context.args and len(context.args) > 1 else " ".join(context.args) if context.args and not str(context.args[0]).startswith('@') and not str(context.args[0]).isdigit() else None
    
    if not user_id:
        return await update.message.reply_text("Usage: /mute @username or reply to a user with /mute [reason]")
    
    try:
        member = await chat.get_member(user_id)
        if isinstance(member, (ChatMemberAdministrator, ChatMemberOwner)):
            return await update.message.reply_text("I cannot mute an admin or the group owner.")
        
        if isinstance(member, ChatMemberRestricted) and not member.can_send_messages:
            return await update.message.reply_text("User is already muted.")
        
        permissions = ChatPermissions(
            can_send_messages=False,
            can_send_media_messages=False,
            can_send_polls=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False
        )
        
        await chat.restrict_member(user_id, permissions)
        
        admin_name = user.full_name
        text = f"» Mute a user in {chat.title}\n"
        text += f" User  : {name}\n"
        text += f" Admin : {admin_name}"
        if reason:
            text += f"\nReason: {reason}"
        
        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f"Failed to mute user: {str(e)}")

async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unmute a user in the group."""
    chat = update.effective_chat
    user = update.effective_user
    
    # Permission check
    has_perm, error_msg = await check_admin_permission(update, context, 'can_restrict_members')
    if not has_perm:
        return await update.message.reply_text(error_msg)
    
    # Bot permission check
    has_bot_perm, bot_error_msg = await check_bot_permission(update, context, 'can_restrict_members')
    if not has_bot_perm:
        return await update.message.reply_text(bot_error_msg)
    
    user_id, name = await get_user_id(update, context)
    reason = " ".join(context.args[1:]) if context.args and len(context.args) > 1 else " ".join(context.args) if context.args and not str(context.args[0]).startswith('@') and not str(context.args[0]).isdigit() else None
    
    if not user_id:
        return await update.message.reply_text("Usage: /unmute @username or reply to a user with /unmute [reason]")
    
    try:
        member = await chat.get_member(user_id)
        if not isinstance(member, ChatMemberRestricted):
            return await update.message.reply_text("User is not muted.")
        
        permissions = ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_invite_users=True,
        )
        
        await chat.restrict_member(user_id, permissions)
        
        admin_name = user.full_name
        text = f"» Unmute a user in {chat.title}\n"
        text += f" User  : {name}\n"
        text += f" Admin : {admin_name}"
        if reason:
            text += f"\nReason: {reason}"
        
        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f"Failed to unmute user: {str(e)}")

async def tmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Temporarily mute a user."""
    chat = update.effective_chat
    user = update.effective_user
    
    # Permission check
    has_perm, error_msg = await check_admin_permission(update, context, 'can_restrict_members')
    if not has_perm:
        return await update.message.reply_text(error_msg)
    
    # Bot permission check
    has_bot_perm, bot_error_msg = await check_bot_permission(update, context, 'can_restrict_members')
    if not has_bot_perm:
        return await update.message.reply_text(bot_error_msg)
    
    user_id, name = await get_user_id(update, context)
    
    if update.message.reply_to_message:
        if len(context.args) < 1:
            return await update.message.reply_text("Usage: /tmute @username <time> [reason] or reply with /tmute <time> [reason]")
        time_str = context.args[0]
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else None
    else:
        if len(context.args) < 2:
            return await update.message.reply_text("Usage: /tmute @username <time> [reason] or reply with /tmute <time> [reason]")
        time_str = context.args[1]
        reason = " ".join(context.args[2:]) if len(context.args) > 2 else None
    
    if not user_id:
        return await update.message.reply_text("User not found.")
    
    try:
        member = await chat.get_member(user_id)
        if isinstance(member, (ChatMemberAdministrator, ChatMemberOwner)):
            return await update.message.reply_text("I cannot mute an admin or the group owner.")
        
        delta = parse_time(time_str)
        if not delta:
            return await update.message.reply_text("Invalid time format. Use s/m/h/d suffix (e.g., 1h, 30m, 2d).")
        
        until_date = datetime.utcnow() + delta
        
        permissions = ChatPermissions(
            can_send_messages=False,
            can_send_media_messages=False,
            can_send_polls=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False
        )
        
        await chat.restrict_member(user_id, permissions, until_date=until_date)
        
        admin_name = user.full_name
        text = f"» Mute for {time_str} in {chat.title}\n"
        text += f" User  : {name}\n"
        text += f" Admin : {admin_name}"
        if reason:
            text += f"\nReason: {reason}"
        
        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f"Failed to temporarily mute user: {str(e)}")

async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kick a user from the group."""
    chat = update.effective_chat
    user = update.effective_user
    
    # Check if command is enabled
    settings = get_chat_settings(chat.id)
    if not settings.get("manager_kick_enabled", True):
        return await update.message.reply_text("❌ The /kick command is currently disabled.")
    
    # Permission check
    has_perm, error_msg = await check_admin_permission(update, context, 'can_restrict_members')
    if not has_perm:
        return await update.message.reply_text(error_msg)
    
    # Bot permission check
    has_bot_perm, bot_error_msg = await check_bot_permission(update, context, 'can_restrict_members')
    if not has_bot_perm:
        return await update.message.reply_text(bot_error_msg)
    
    user_id, name = await get_user_id(update, context)
    reason = " ".join(context.args[1:]) if context.args and len(context.args) > 1 else " ".join(context.args) if context.args and not str(context.args[0]).startswith('@') and not str(context.args[0]).isdigit() else None
    
    if not user_id:
        return await update.message.reply_text("Usage: /kick @username or reply to a user with /kick [reason]")
    
    try:
        member = await chat.get_member(user_id)
        if isinstance(member, (ChatMemberAdministrator, ChatMemberOwner)):
            return await update.message.reply_text("I cannot kick an admin or the group owner.")
        
        await chat.ban_member(user_id)
        await asyncio.sleep(2)
        await chat.unban_member(user_id)
        
        admin_name = user.full_name
        text = f"» Kick a user in {chat.title}\n"
        text += f" User  : {name}\n"
        text += f" Admin : {admin_name}"
        if reason:
            text += f"\nReason: {reason}"
        
        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f"Failed to kick user: {str(e)}")

async def dban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete message and ban user."""
    chat = update.effective_chat
    user = update.effective_user
    
    # Permission check
    has_perm, error_msg = await check_admin_permission(update, context, 'can_restrict_members')
    if not has_perm:
        return await update.message.reply_text(error_msg)
    
    # Bot permission check
    has_bot_perm, bot_error_msg = await check_bot_permission(update, context, 'can_restrict_members')
    if not has_bot_perm:
        return await update.message.reply_text(bot_error_msg)
    
    if not update.message.reply_to_message:
        return await update.message.reply_text("Usage: Reply to a user's message with /dban [reason]")
    
    target_user = update.message.reply_to_message.from_user
    user_id = target_user.id
    name = target_user.full_name
    reason = " ".join(context.args) if context.args else None
    
    try:
        member = await chat.get_member(user_id)
        if isinstance(member, (ChatMemberAdministrator, ChatMemberOwner)):
            return await update.message.reply_text("I cannot ban an admin or the group owner.")
        
        await chat.ban_member(user_id)
        await update.message.reply_to_message.delete()
        
        admin_name = user.full_name
        text = f"» Ban a user in {chat.title}\n"
        text += f" User  : {name}\n"
        text += f" Admin : {admin_name}"
        if reason:
            text += f"\nReason: {reason}"
        
        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f"Failed to delete and ban: {str(e)}")

async def sban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Silent ban (no notification)."""
    chat = update.effective_chat
    user = update.effective_user
    
    # Permission check
    has_perm, error_msg = await check_admin_permission(update, context, 'can_restrict_members')
    if not has_perm:
        return await update.message.reply_text(error_msg)
    
    # Bot permission check
    has_bot_perm, bot_error_msg = await check_bot_permission(update, context, 'can_restrict_members')
    if not has_bot_perm:
        return await update.message.reply_text(bot_error_msg)
    
    user_id, name = await get_user_id(update, context)
    if not user_id:
        return await update.message.reply_text("Usage: /sban @username or reply to a user with /sban")
    
    try:
        member = await chat.get_member(user_id)
        if isinstance(member, (ChatMemberAdministrator, ChatMemberOwner)):
            return await update.message.reply_text("I cannot ban an admin or the group owner.")
        
        await chat.ban_member(user_id)
        await update.message.delete()
    except Exception as e:
        await update.message.reply_text(f"Failed to silently ban: {str(e)}")

async def kickme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User self-kick."""
    chat = update.effective_chat
    user = update.effective_user
    
    try:
        member = await chat.get_member(user.id)
        if isinstance(member, (ChatMemberAdministrator, ChatMemberOwner)):
            return await update.message.reply_text("Nice try, boss 😅 I can't kick admins or the owner.")
        
        await chat.ban_member(user.id)
        await asyncio.sleep(3)
        await chat.unban_member(user.id)
        
        await update.message.reply_text("Kicked so hard, your ancestors felt it. 👟💥")
    except Exception as e:
        await update.message.reply_text(f"Failed to kick you: {str(e)}")

async def tban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Temporarily ban a user."""
    chat = update.effective_chat
    user = update.effective_user
    
    # Permission check
    has_perm, error_msg = await check_admin_permission(update, context, 'can_restrict_members')
    if not has_perm:
        return await update.message.reply_text(error_msg)
    
    # Bot permission check
    has_bot_perm, bot_error_msg = await check_bot_permission(update, context, 'can_restrict_members')
    if not has_bot_perm:
        return await update.message.reply_text(bot_error_msg)
    
    user_id, name = await get_user_id(update, context)
    
    if update.message.reply_to_message:
        if len(context.args) < 1:
            return await update.message.reply_text("Usage: /tban @username <time> [reason] or reply with /tban <time> [reason]")
        time_str = context.args[0]
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else None
    else:
        if len(context.args) < 2:
            return await update.message.reply_text("Usage: /tban @username <time> [reason] or reply with /tban <time> [reason]")
        time_str = context.args[1]
        reason = " ".join(context.args[2:]) if len(context.args) > 2 else None
    
    if not user_id:
        return await update.message.reply_text("User not found.")
    
    try:
        member = await chat.get_member(user_id)
        if isinstance(member, (ChatMemberAdministrator, ChatMemberOwner)):
            return await update.message.reply_text("I cannot ban an admin or the group owner.")
        
        delta = parse_time(time_str)
        if not delta:
            return await update.message.reply_text("Invalid time format. Use s/m/h/d suffix (e.g., 1h, 30m, 2d).")
        
        until_date = datetime.utcnow() + delta
        
        await chat.ban_member(user_id, until_date=until_date)
        
        admin_name = user.full_name
        text = f"» Ban for {time_str} in {chat.title}\n"
        text += f" User  : {name}\n"
        text += f" Admin : {admin_name}"
        if reason:
            text += f"\nReason: {reason}"
        
        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f"Failed to temporarily ban user: {str(e)}")

def get_manager_actions_handlers():
    """Return all Manager action handlers."""
    return [
        CommandHandler("ban", ban_user),
        CommandHandler("unban", unban_user),
        CommandHandler("mute", mute_user),
        CommandHandler("unmute", unmute_user),
        CommandHandler("tmute", tmute_user),
        CommandHandler("kick", kick_user),
        CommandHandler("dban", dban_user),
        CommandHandler("sban", sban_user),
        CommandHandler("kickme", kickme),
        CommandHandler("tban", tban_user),
    ]
