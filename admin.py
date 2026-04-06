import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions, ChatAdministratorRights
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler
from telegram.error import BadRequest
from user_manager import get_user_id, is_user_admin
from config import OWNER_ID, log_to_channel, send_bot_response, edit_bot_response

# Permission names to display
PERMISSIONS_MAP = {
    "can_change_info": "Change Group Info",
    "can_delete_messages": "Delete Messages",
    "can_restrict_members": "Ban Users",
    "can_invite_users": "Invite Users via Link",
    "can_pin_messages": "Pin Messages",
    "can_post_stories": "Post Stories",
    "can_edit_stories": "Edit Stories",
    "can_delete_stories": "Delete Stories",
    "can_manage_video_chats": "Manage Video Chats",
    "is_anonymous": "Remain Anonymous",
    "can_promote_members": "Add New Admins"
}

# Initial default permissions for a new admin
DEFAULT_PERMISSIONS = {
    "can_change_info": False,
    "can_delete_messages": False,
    "can_restrict_members": False,
    "can_invite_users": False,
    "can_pin_messages": False,
    "can_post_stories": False,
    "can_edit_stories": False,
    "can_delete_stories": False,
    "can_manage_video_chats": False,
    "is_anonymous": False,
    "can_promote_members": False
}

async def promote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the promotion process for a user."""
    chat_id = update.effective_chat.id
    sender_id = update.effective_user.id
    
    # Check if user is admin/owner
    if not await is_user_admin(chat_id, sender_id, context):
        await send_bot_response(update, context, "You must be an admin to promote others.")
        return

    # Check bot permissions (can_promote_members)
    bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
    if not (bot_member.status == 'creator' or (bot_member.status == 'administrator' and bot_member.can_promote_members)):
        await send_bot_response(update, context, "❌ I don't have the 'Add New Admins' permission to promote anyone.")
        return

    user_id, user_name = await get_user_id(update, context)
    if not user_id:
        # If username was provided but not found in cache
        if context.args and context.args[0].startswith('@'):
            await send_bot_response(
                update, context,
                f"❌ Could not find user {context.args[0]} in my database.\n\n"
                "**Why?** I only remember users who have spoken or joined since I was added.\n"
                "**Fix:** Please reply to one of their messages instead."
            )
        else:
            await send_bot_response(update, context, "Please reply to a user's message or provide a username/ID to promote them.")
        return

    context.user_data[f"promote_{user_id}"] = DEFAULT_PERMISSIONS.copy()
    
    keyboard = get_promotion_keyboard(user_id, context.user_data[f"promote_{user_id}"])
    await send_bot_response(
        update, context,
        f"Promoting {user_name}. Select permissions:",
        reply_markup=keyboard
    )

def get_promotion_keyboard(user_id, current_perms, back_to_info=False):
    """Generate the keyboard with toggle buttons in 2 columns."""
    keyboard = []
    perm_items = list(PERMISSIONS_MAP.items())
    
    # Create 2-column grid for permissions
    for i in range(0, len(perm_items), 2):
        row = []
        # First column
        key1, label1 = perm_items[i]
        status1 = "✅" if current_perms.get(key1) else "❌"
        row.append(InlineKeyboardButton(f"{label1}: {status1}", callback_data=f"toggle_{user_id}_{key1}"))
        
        # Second column (if exists)
        if i + 1 < len(perm_items):
            key2, label2 = perm_items[i+1]
            status2 = "✅" if current_perms.get(key2) else "❌"
            row.append(InlineKeyboardButton(f"{label2}: {status2}", callback_data=f"toggle_{user_id}_{key2}"))
        
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("Confirm Promotion", callback_data=f"confirm_{user_id}")])
    
    if back_to_info:
        keyboard.append([InlineKeyboardButton("🔙 Back to Roles", callback_data=f"info_roles_{user_id}")])
    else:
        keyboard.append([InlineKeyboardButton("Cancel", callback_data=f"cancel_{user_id}")])
    
    return InlineKeyboardMarkup(keyboard)

async def toggle_permission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle permission toggle buttons."""
    query = update.callback_query
    data = query.data.split("_")
    
    # Format: toggle_user_id_permission_key
    user_id = int(data[1])
    perm_key = "_".join(data[2:])
    
    # Security check: only the person who started the promotion should be able to toggle (simplified here)
    
    promote_key = f"promote_{user_id}"
    if promote_key not in context.user_data:
        await query.answer("Promotion session expired.")
        return

    context.user_data[promote_key][perm_key] = not context.user_data[promote_key][perm_key]
    
    keyboard = get_promotion_keyboard(
        user_id, 
        context.user_data[promote_key], 
        back_to_info=context.user_data[promote_key].get("back_to_info", False)
    )
    try:
        await query.edit_message_reply_markup(reply_markup=keyboard)
    except BadRequest:
        # Message might be the same, ignore
        pass
    await query.answer()

async def confirm_promotion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Apply the permissions and promote the user."""
    query = update.callback_query
    user_id = int(query.data.split("_")[1])
    chat_id = update.effective_chat.id
    
    promote_key = f"promote_{user_id}"
    if promote_key not in context.user_data:
        await query.answer("Promotion session expired.")
        return

    requested_perms = context.user_data[promote_key]
    
    try:
        # Get bot's own permissions to see what it can actually grant
        bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        
        # Determine effective perms: bot can only grant what it has
        # Note: 'creator' status has all perms
        is_creator = bot_member.status == 'creator'
        
        final_perms = {}
        missing_rights = []
        
        for key in PERMISSIONS_MAP.keys():
            requested_val = requested_perms.get(key, False)
            # Bot must have the right to grant it
            bot_has_right = is_creator or getattr(bot_member, key, False)
            
            if requested_val and not bot_has_right:
                missing_rights.append(PERMISSIONS_MAP[key])
                final_perms[key] = False
            else:
                final_perms[key] = requested_val

        if missing_rights:
            rights_str = ", ".join(missing_rights)
            await query.answer(f"⚠️ I cannot grant: {rights_str} (I don't have these rights myself)", show_alert=True)
            # We don't return here, we proceed with the rights I DO have
            # or the user can toggle them off.

        await context.bot.promote_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            can_change_info=final_perms.get('can_change_info', False),
            can_delete_messages=final_perms.get('can_delete_messages', False),
            can_restrict_members=final_perms.get('can_restrict_members', False),
            can_invite_users=final_perms.get('can_invite_users', False),
            can_pin_messages=final_perms.get('can_pin_messages', False),
            can_post_stories=final_perms.get('can_post_stories', False),
            can_edit_stories=final_perms.get('can_edit_stories', False),
            can_delete_stories=final_perms.get('can_delete_stories', False),
            can_manage_video_chats=final_perms.get('can_manage_video_chats', False),
            can_promote_members=final_perms.get('can_promote_members', False),
            is_anonymous=final_perms.get('is_anonymous', False)
        )
        
        if requested_perms.get("back_to_info"):
            await query.answer("Successfully promoted user.")
            query.data = f"info_roles_{user_id}"
            from bot import info_callback_handler
            await info_callback_handler(update, context)
            del context.user_data[promote_key]
            return

        await edit_bot_response(query, context, f"Successfully promoted user to administrator.")
        
        # Log to channel
        await log_to_channel(context, 
            f"👤 User: {user_id}\n"
            f"🛡️ Action: Promoted to Admin\n"
            f"📍 Group: {update.effective_chat.title} ({chat_id})\n"
            f"👤 Admin: {query.from_user.id}"
        )
        
        del context.user_data[promote_key]
    except Exception as e:
        error_msg = str(e)
        if "Right_forbidden" in error_msg:
            await edit_bot_response(
                query, context,
                "❌ **Promotion Failed (Right_forbidden)**\n\n"
                "**Reason:** You are trying to give this user a permission that I (the bot) do not have.\n\n"
                "**Fix:**\n"
                "1. Ensure I have ALL the permissions you are trying to give (like 'Remain Anonymous', 'Manage Video Chats', etc.).\n"
                "2. Ensure I have the 'Add New Admins' permission."
            )
        elif "Not_enough_rights" in error_msg:
             await edit_bot_response(query, context, "❌ I don't have enough rights to promote this user.")
        else:
            await edit_bot_response(query, context, f"Failed to promote: {error_msg}")
    
    await query.answer()

async def cancel_promotion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the promotion process."""
    query = update.callback_query
    user_id = int(query.data.split("_")[1])
    promote_key = f"promote_{user_id}"
    
    if promote_key in context.user_data:
        del context.user_data[promote_key]
    
    await edit_bot_response(query, context, "Promotion cancelled.")
    await query.answer()

async def demote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Demotes an administrator to a regular user."""
    chat_id = update.effective_chat.id
    sender_id = update.effective_user.id
    
    if not await is_user_admin(chat_id, sender_id, context):
        await send_bot_response(update, context, "You must be an admin to demote others.")
        return

    # Check bot permissions (can_promote_members)
    bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
    if not (bot_member.status == 'creator' or (bot_member.status == 'administrator' and bot_member.can_promote_members)):
        await send_bot_response(update, context, "❌ I don't have the 'Add New Admins' permission to demote anyone.")
        return

    user_id, user_name = await get_user_id(update, context)
    if not user_id:
        await send_bot_response(update, context, "Please reply to a user's message or provide a username/ID to demote them.")
        return

    try:
        # Check if user is actually an admin
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status not in ['administrator']:
            await send_bot_response(update, context, f"{user_name} is not an administrator or is the chat owner.")
            return

        # Demote by setting all permissions to False
        await context.bot.promote_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            can_change_info=False,
            can_delete_messages=False,
            can_restrict_members=False,
            can_invite_users=False,
            can_pin_messages=False,
            can_post_stories=False,
            can_edit_stories=False,
            can_delete_stories=False,
            can_manage_video_chats=False,
            can_promote_members=False,
            is_anonymous=False
        )
        await send_bot_response(update, context, f"✅ Successfully demoted {user_name} to a regular member.")
        
        # Log to channel
        await log_to_channel(context, 
            f"👤 User: {user_name} ({user_id})\n"
            f"📉 Action: Demoted from Admin\n"
            f"📍 Group: {update.effective_chat.title} ({chat_id})\n"
            f"👤 Admin: {update.effective_user.first_name}"
        )
    except Exception as e:
        await send_bot_response(update, context, f"Failed to demote: {str(e)}")

def get_admin_handlers():
    return [
        CommandHandler("promote", promote_command),
        CommandHandler("demote", demote_command),
        CallbackQueryHandler(toggle_permission, pattern="^toggle_"),
        CallbackQueryHandler(confirm_promotion, pattern="^confirm_"),
        CallbackQueryHandler(cancel_promotion, pattern="^cancel_")
    ]
