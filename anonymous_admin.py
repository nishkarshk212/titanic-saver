"""
Anonymous Admin Permission Handler

This module handles permission checking for anonymous admins in Telegram groups.
When an admin sends messages anonymously, Telegram uses the special ID 1087968824
(Group Anonymous Bot). This module checks the actual permissions of the anonymous
admin by examining the chat's admin list and the anonymous admin configuration.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from config import OWNER_ID

# Telegram's ID for anonymous admins (Group Anonymous Bot)
ANONYMOUS_ADMIN_ID = 1087968824


def is_anonymous_admin(user_id):
    """Check if the user ID belongs to an anonymous admin."""
    return user_id == ANONYMOUS_ADMIN_ID


async def get_anonymous_admin_permissions(chat_id, context):
    """
    Get the permissions of the anonymous admin in a specific chat.
    
    Returns a dict with permission booleans or None if anonymous admin is not configured.
    """
    try:
        # Get chat info to check if it has anonymous admins enabled
        chat = await context.bot.get_chat(chat_id)
        
        # Get all administrators in the chat
        admins = await context.bot.get_chat_administrators(chat_id)
        
        # Find anonymous admins (those with is_anonymous=True)
        anonymous_admins = [admin for admin in admins if admin.is_anonymous]
        
        if not anonymous_admins:
            return None
        
        # For anonymous admins, we need to check the bot's own permissions as a reference
        # since we can't directly identify which anonymous admin is acting
        # The safest approach is to check if ANY admin has the required permission
        # and assume the anonymous admin might have it
        
        # Get the first anonymous admin's permissions as reference
        # Note: This is a limitation - we can't know WHICH anonymous admin is acting
        anon_admin = anonymous_admins[0]
        
        return {
            'can_change_info': anon_admin.can_change_info,
            'can_delete_messages': anon_admin.can_delete_messages,
            'can_restrict_members': anon_admin.can_restrict_members,
            'can_invite_users': anon_admin.can_invite_users,
            'can_pin_messages': anon_admin.can_pin_messages,
            'can_post_stories': anon_admin.can_post_stories,
            'can_edit_stories': anon_admin.can_edit_stories,
            'can_delete_stories': anon_admin.can_delete_stories,
            'can_manage_video_chats': anon_admin.can_manage_video_chats,
            'can_promote_members': anon_admin.can_promote_members,
            'is_anonymous': anon_admin.is_anonymous,
        }
    except Exception as e:
        logging.error(f"Error getting anonymous admin permissions: {e}")
        return None


async def anonymous_admin_has_permission(chat_id, context, permission_key):
    """
    Check if the anonymous admin has a specific permission.
    
    Args:
        chat_id: The chat ID
        context: The bot context
        permission_key: The permission to check (e.g., 'can_restrict_members')
    
    Returns:
        bool: True if anonymous admin has the permission, False otherwise
    """
    permissions = await get_anonymous_admin_permissions(chat_id, context)
    
    if permissions is None:
        # No anonymous admins configured
        return False
    
    return permissions.get(permission_key, False)


async def check_anonymous_admin_ban_permission(chat_id, context):
    """
    Check if anonymous admin can ban/restrict members.
    
    Returns:
        tuple: (has_permission, error_message)
    """
    if await anonymous_admin_has_permission(chat_id, context, 'can_restrict_members'):
        return True, None
    return False, "❌ Anonymous admin doesn't have 'Ban Users' permission."


async def check_anonymous_admin_mute_permission(chat_id, context):
    """
    Check if anonymous admin can mute/restrict members.
    
    Returns:
        tuple: (has_permission, error_message)
    """
    if await anonymous_admin_has_permission(chat_id, context, 'can_restrict_members'):
        return True, None
    return False, "❌ Anonymous admin doesn't have 'Ban Users' permission."


async def check_anonymous_admin_promote_permission(chat_id, context):
    """
    Check if anonymous admin can promote/demote members.
    
    Returns:
        tuple: (has_permission, error_message)
    """
    if await anonymous_admin_has_permission(chat_id, context, 'can_promote_members'):
        return True, None
    return False, "❌ Anonymous admin doesn't have 'Add New Admins' permission."


async def check_anonymous_admin_pin_permission(chat_id, context):
    """
    Check if anonymous admin can pin messages.
    
    Returns:
        tuple: (has_permission, error_message)
    """
    if await anonymous_admin_has_permission(chat_id, context, 'can_pin_messages'):
        return True, None
    return False, "❌ Anonymous admin doesn't have 'Pin Messages' permission."


async def check_anonymous_admin_delete_permission(chat_id, context):
    """
    Check if anonymous admin can delete messages.
    
    Returns:
        tuple: (has_permission, error_message)
    """
    if await anonymous_admin_has_permission(chat_id, context, 'can_delete_messages'):
        return True, None
    return False, "❌ Anonymous admin doesn't have 'Delete Messages' permission."


async def check_anonymous_admin_invite_permission(chat_id, context):
    """
    Check if anonymous admin can invite users.
    
    Returns:
        tuple: (has_permission, error_message)
    """
    if await anonymous_admin_has_permission(chat_id, context, 'can_invite_users'):
        return True, None
    return False, "❌ Anonymous admin doesn't have 'Invite Users' permission."


async def check_anonymous_admin_change_info_permission(chat_id, context):
    """
    Check if anonymous admin can change group info.
    
    Returns:
        tuple: (has_permission, error_message)
    """
    if await anonymous_admin_has_permission(chat_id, context, 'can_change_info'):
        return True, None
    return False, "❌ Anonymous admin doesn't have 'Change Group Info' permission."


async def check_anonymous_admin_video_chat_permission(chat_id, context):
    """
    Check if anonymous admin can manage video chats.
    
    Returns:
        tuple: (has_permission, error_message)
    """
    if await anonymous_admin_has_permission(chat_id, context, 'can_manage_video_chats'):
        return True, None
    return False, "❌ Anonymous admin doesn't have 'Manage Video Chats' permission."


async def validate_anonymous_admin_action(chat_id, context, action, required_permission):
    """
    Generic validator for anonymous admin actions.
    
    Args:
        chat_id: The chat ID
        context: The bot context
        action: The action being performed (for logging)
        required_permission: The permission key required
    
    Returns:
        tuple: (is_allowed, error_message)
    """
    has_perm, error_msg = await globals()[f"check_anonymous_admin_{required_permission}_permission"](chat_id, context)
    
    if not has_perm:
        logging.warning(f"Anonymous admin attempted {action} without required permission in chat {chat_id}")
        return False, error_msg
    
    logging.info(f"Anonymous admin performed {action} in chat {chat_id}")
    return True, None
