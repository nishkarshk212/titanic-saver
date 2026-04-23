"""
Manager Actions - Ban, Unban, Mute, Unmute, Kick, etc.
Ported from AnnieXMusic to python-telegram-bot
"""

import asyncio
from datetime import datetime, timedelta
from telegram import Update, ChatPermissions, ChatMemberAdministrator, ChatMemberOwner, ChatMemberBanned, ChatMemberRestricted
from telegram.ext import ContextTypes, CommandHandler
from telegram.constants import ChatMemberStatus
from settings_manager_mongo import get_chat_settings

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

async def is_admin(chat, user_id):
    """Check if user is admin."""
    member = await chat.get_member(user_id)
    return isinstance(member, (ChatMemberAdministrator, ChatMemberOwner))

def get_user_from_args(update, context):
    """Extract user ID and name from command args or reply."""
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        return user.id, user.full_name, " ".join(context.args) if context.args else None
    
    if not context.args:
        return None, None, None
    
    target = context.args[0]
    try:
        if target.isdigit():
            user_id = int(target)
            return user_id, str(user_id), " ".join(context.args[1:]) if len(context.args) > 1 else None
        else:
            # It's a username
            return target, target, " ".join(context.args[1:]) if len(context.args) > 1 else None
    except:
        return None, None, None

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban a user from the group."""
    chat = update.effective_chat
    user = update.effective_user
    
    # Check if command is enabled
    settings = get_chat_settings(chat.id)
    if not settings.get("manager_ban_enabled", True):
        return await update.message.reply_text("❌ The /ban command is currently disabled.")
    
    if not await is_admin(chat, user.id):
        return await update.message.reply_text("You need to be an admin to use this command.")
    
    user_id, name, reason = get_user_from_args(update, context)
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
    
    if not await is_admin(chat, user.id):
        return await update.message.reply_text("You need to be an admin to use this command.")
    
    user_id, name, reason = get_user_from_args(update, context)
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
    
    if not await is_admin(chat, user.id):
        return await update.message.reply_text("You need to be an admin to use this command.")
    
    user_id, name, reason = get_user_from_args(update, context)
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
    
    if not await is_admin(chat, user.id):
        return await update.message.reply_text("You need to be an admin to use this command.")
    
    user_id, name, reason = get_user_from_args(update, context)
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
    
    if not await is_admin(chat, user.id):
        return await update.message.reply_text("You need to be an admin to use this command.")
    
    if update.message.reply_to_message:
        if len(context.args) < 1:
            return await update.message.reply_text("Usage: /tmute @username <time> [reason] or reply with /tmute <time> [reason]")
        target_user = update.message.reply_to_message.from_user
        user_id = target_user.id
        name = target_user.full_name
        time_str = context.args[0]
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else None
    else:
        if len(context.args) < 2:
            return await update.message.reply_text("Usage: /tmute @username <time> [reason] or reply with /tmute <time> [reason]")
        user_id = context.args[0]
        name = user_id
        time_str = context.args[1]
        reason = " ".join(context.args[2:]) if len(context.args) > 2 else None
    
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
    
    if not await is_admin(chat, user.id):
        return await update.message.reply_text("You need to be an admin to use this command.")
    
    user_id, name, reason = get_user_from_args(update, context)
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
    
    if not await is_admin(chat, user.id):
        return await update.message.reply_text("You need to be an admin to use this command.")
    
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
    
    if not await is_admin(chat, user.id):
        return await update.message.reply_text("You need to be an admin to use this command.")
    
    user_id, name, reason = get_user_from_args(update, context)
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
    
    if not await is_admin(chat, user.id):
        return await update.message.reply_text("You need to be an admin to use this command.")
    
    if update.message.reply_to_message:
        if len(context.args) < 1:
            return await update.message.reply_text("Usage: /tban @username <time> [reason] or reply with /tban <time> [reason]")
        target_user = update.message.reply_to_message.from_user
        user_id = target_user.id
        name = target_user.full_name
        time_str = context.args[0]
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else None
    else:
        if len(context.args) < 2:
            return await update.message.reply_text("Usage: /tban @username <time> [reason] or reply with /tban <time> [reason]")
        user_id = context.args[0]
        name = user_id
        time_str = context.args[1]
        reason = " ".join(context.args[2:]) if len(context.args) > 2 else None
    
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
