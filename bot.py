import logging
import os
import html
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ChatPermissions
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from admin import get_admin_handlers
from welcome import get_welcome_handlers
from block_content import get_block_content_handlers
from clean_service import get_clean_service_handlers
from auto_delete import get_auto_delete_handlers
from moderation import get_moderation_handlers
from filter import get_filter_handlers
from settings import get_settings_handlers
from help import get_help_handlers
from config import BOT_TOKEN, LOG_CHANNEL_ID, OWNER_ID, log_to_channel, send_bot_response, send_bot_media, START_VIDEOS
from user_manager import cache_user, increment_message_count, get_user_id, get_user_stats, is_user_admin
from settings_manager import get_chat_settings

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update, context):
    """Start command handler."""
    bot_info = await context.bot.get_me()
    bot_name = bot_info.first_name
    bot_username = bot_info.username
    add_to_group_url = f"https://t.me/{bot_username}?startgroup=true"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add to Group", url=add_to_group_url)]
    ])
    
    video_url = random.choice(START_VIDEOS)
    
    start_message = (
        f"๏ ᴛʜɪs ɪs {bot_name}\n\n"
        "➻ ᴀ ᴘᴏᴡᴇʀғᴜʟ sᴇᴄᴜʀɪᴛʏ ʙᴏᴛ ᴅᴇsɪɢɴᴇᴅ ᴛᴏ ᴘʀᴏᴛᴇᴄᴛ ʏᴏᴜʀ ᴛᴇʟᴇɢʀᴀᴍ ɢʀᴏᴜᴘ\n"
        "ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ & ɢɪᴠᴇ ᴍᴇ ᴀᴅᴍɪɴ & ᴅᴇʟᴇᴛᴇ ᴍᴇssᴀɢᴇ ʀɪɢʜᴛ ɪ sᴛᴀʀᴛ ᴘʀᴏᴛᴇᴄᴛɪɴɢ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ\n"
        "➻ ɢɪᴠᴇ ᴍᴇ ᴀ ᴄʜᴀɴᴄᴇ ʜᴀɴᴅʟᴇ ʏᴏᴜʀ ɢʀᴏᴜᴘ."
    )
    
    await send_bot_media(
        update, context,
        video=video_url,
        caption=start_message,
        reply_markup=keyboard
    )

async def cache_user_handler(update, context):
    """Caches user information and tracks message counts."""
    if not update.effective_chat: return
    
    # 1. Cache the sender and increment message count
    if update.effective_user:
        user = update.effective_user
        cache_user(user.id, user.username, user.first_name)
        if update.message and not update.message.text.startswith('/'):
            increment_message_count(user.id)
    
    # 2. Cache any users mentioned in the message
    if update.message and update.message.entities:
        for entity in update.message.entities:
            if entity.type == 'text_mention':
                cache_user(entity.user.id, entity.user.username, entity.user.first_name)

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to show detailed user info."""
    chat_id = update.effective_chat.id
    settings = get_chat_settings(chat_id)
    
    # Check access (Admin only if setting enabled)
    if settings.get("command_access") == "admins":
        if not await is_user_admin(chat_id, update.effective_user.id, context):
            return # Silently ignore or send error

    user_id, first_name = await get_user_id(update, context)
    if not user_id:
        user = update.effective_user
        user_id, first_name = user.id, user.first_name
    
    stats = get_user_stats(user_id)
    username = stats.get("username") if stats else None
    joined_date = stats.get("joined_date", "Unknown") if stats else "Unknown"
    msg_count = stats.get("msg_count", 0) if stats else 0
    
    # Get user status and role in group
    user_status = "Unknown"
    user_role = "Member"
    is_muted = False
    
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        status = member.status
        
        # Determine Status & Role
        if status == 'creator':
            user_status = "Present"
            user_role = "Owner/Creator"
        elif status == 'administrator':
            user_status = "Present"
            user_role = "Administrator"
            if member.custom_title:
                user_role += f" ({member.custom_title})"
        elif status == 'member':
            user_status = "Present"
            user_role = "Member"
        elif status == 'restricted':
            user_status = "Present (Restricted)"
            user_role = "Restricted Member"
            if not member.can_send_messages:
                is_muted = True
        elif status == 'left':
            user_status = "Left"
            user_role = "None"
        elif status == 'kicked':
            user_status = "Banned"
            user_role = "None"
            
    except Exception as e:
        logging.error(f"Error getting member status for info: {e}")

    info_text = (
        f"👤 <b>User Information</b>\n\n"
        f"• <b>Name:</b> {html.escape(first_name)}\n"
        f"• <b>Username:</b> @{username if username else 'None'}\n"
        f"• <b>User ID:</b> <code>{user_id}</code>\n"
        f"• <b>Status:</b> {user_status}\n"
        f"• <b>Role:</b> {user_role}\n"
        f"• <b>Muted:</b> {'Yes 🔇' if is_muted else 'No 🔊'}\n"
        f"• <b>Joined Date:</b> {joined_date}\n"
        f"• <b>Total Messages:</b> {msg_count}"
    )
    
    # Create keyboard for admins
    reply_markup = None
    if await is_user_admin(chat_id, update.effective_user.id, context):
        keyboard = [
            [
                InlineKeyboardButton("⚠️ Warns", callback_data=f"info_warns_{user_id}"),
                InlineKeyboardButton("🎭 Roles", callback_data=f"info_roles_{user_id}")
            ],
            [
                InlineKeyboardButton("🔇 Mute" if not is_muted else "🔊 Unmute", callback_data=f"info_mute_{user_id}"),
                InlineKeyboardButton("🔨 Ban" if user_status != "Banned" else "🔓 Unban", callback_data=f"info_ban_{user_id}")
            ],
            [InlineKeyboardButton("❌ Close", callback_data="info_close")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

    await send_bot_response(update, context, info_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

async def info_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle management buttons from the /info command."""
    query = update.callback_query
    chat_id = update.effective_chat.id
    admin_id = update.effective_user.id
    
    # Permission check: only admins can use these buttons
    if not await is_user_admin(chat_id, admin_id, context):
        await query.answer("Admin only feature.", show_alert=True)
        return

    data = query.data.split("_")
    action = data[1]
    user_id = int(data[2])
    
    # Import handlers locally to avoid circular imports
    from moderation import mute_command, unmute_command, ban_command, warn_command, unwarn_command, unban_command, muter_command
    from moderation_manager import get_user_warns, is_muter as check_is_muter
    from admin import promote_command, demote_command, DEFAULT_PERMISSIONS, get_promotion_keyboard
    
    # Create a mock update to reuse existing command logic
    class MockMessage:
        def __init__(self, chat, from_user, reply_to_message=None):
            self.chat = chat
            self.from_user = from_user
            self.reply_to_message = reply_to_message
            self.text = ""
        async def reply_text(self, text, *args, **kwargs):
            # We don't want to spam the group when clicking buttons
            pass

    mock_update = Update(update.update_id, message=MockMessage(update.effective_chat, update.effective_user))
    context.args = [str(user_id)]

    keyboard = []
    text_override = None

    if action == "warns":
        warns = get_user_warns(chat_id, user_id)
        text_override = f"⚠️ <b>Warn Management</b> for user <code>{user_id}</code>\n\nCurrent Warns: <code>{warns}</code>"
        keyboard = [
            [
                InlineKeyboardButton("➕ Add Warn", callback_data=f"info_addwarn_{user_id}"),
                InlineKeyboardButton("🔄 Reset Warns", callback_data=f"info_resetwarn_{user_id}")
            ],
            [InlineKeyboardButton("🔙 Back", callback_data=f"info_back_{user_id}"), InlineKeyboardButton("❌ Close", callback_data="info_close")]
        ]
    elif action == "addwarn":
        await warn_command(mock_update, context)
        # Re-trigger warns view
        query.data = f"info_warns_{user_id}"
        await info_callback_handler(update, context)
        return
    elif action == "resetwarn":
        await unwarn_command(mock_update, context)
        # Re-trigger warns view
        query.data = f"info_warns_{user_id}"
        await info_callback_handler(update, context)
        return
    elif action == "mute":
        member = await context.bot.get_chat_member(chat_id, user_id)
        is_muted = member.status == 'restricted' and not member.can_send_messages
        text_override = f"🔇 <b>Mute Management</b> for user <code>{user_id}</code>\n\nStatus: {'Muted 🔇' if is_muted else 'Unmuted 🔊'}"
        keyboard = [
            [InlineKeyboardButton("🔊 Unmute" if is_muted else "🔇 Mute", callback_data=f"info_domute_{user_id}")],
            [InlineKeyboardButton("🔙 Back", callback_data=f"info_back_{user_id}"), InlineKeyboardButton("❌ Close", callback_data="info_close")]
        ]
    elif action == "domute":
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            if member.status == 'restricted' and not member.can_send_messages:
                # Unmute: grant basic permissions
                await context.bot.restrict_chat_member(chat_id, user_id, permissions=ChatPermissions(
                    can_send_messages=True, can_send_audios=True, can_send_documents=True,
                    can_send_photos=True, can_send_videos=True, can_send_video_notes=True,
                    can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True,
                    can_add_web_page_previews=True
                ))
                await query.answer("User unmuted.")
            else:
                # Mute: restrict sending messages
                await context.bot.restrict_chat_member(chat_id, user_id, permissions=ChatPermissions(can_send_messages=False))
                await query.answer("User muted.")
        except Exception as e:
            await query.answer(f"Action failed: {e}", show_alert=True)
        query.data = f"info_mute_{user_id}"
        await info_callback_handler(update, context)
        return
    elif action == "ban":
        member = await context.bot.get_chat_member(chat_id, user_id)
        is_banned = member.status == 'kicked'
        text_override = f"🔨 <b>Ban Management</b> for user <code>{user_id}</code>\n\nStatus: {'Banned ⛔' if is_banned else 'Active ✅'}"
        keyboard = [
            [InlineKeyboardButton("🔓 Unban" if is_banned else "🔨 Ban", callback_data=f"info_doban_{user_id}")],
            [InlineKeyboardButton("🔙 Back", callback_data=f"info_back_{user_id}"), InlineKeyboardButton("❌ Close", callback_data="info_close")]
        ]
    elif action == "doban":
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            if member.status == 'kicked':
                await context.bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
                await query.answer("User unbanned.")
            else:
                await context.bot.ban_chat_member(chat_id, user_id)
                await query.answer("User banned.")
        except Exception as e:
            await query.answer(f"Action failed: {e}", show_alert=True)
        query.data = f"info_ban_{user_id}"
        await info_callback_handler(update, context)
        return
    elif action == "roles":
        is_muter_role = check_is_muter(chat_id, user_id)
        
        # Get actual status of the user
        is_in_group = True
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            is_admin = member.status in ['administrator', 'creator']
            is_member = member.status in ['member', 'administrator', 'creator', 'restricted']
            if member.status in ['left', 'kicked']:
                is_in_group = False
                is_admin = False
                is_member = False
        except Exception:
            is_in_group = False
            is_admin = False
            is_member = False
        
        text_override = f"🎭 <b>Role Management</b> for user <code>{user_id}</code>"
        keyboard = [
            [InlineKeyboardButton(f"Admin: {'✅' if is_admin else '❌'}", callback_data=f"info_toadmin_{user_id}")],
            [InlineKeyboardButton(f"Member: {'✅' if is_member else '❌'}", callback_data=f"info_tomember_{user_id}")],
            [InlineKeyboardButton(f"Muter: {'✅' if is_muter_role else '❌'}", callback_data=f"info_tomuter_{user_id}")],
            [InlineKeyboardButton("🔙 Back", callback_data=f"info_back_{user_id}"), InlineKeyboardButton("❌ Close", callback_data="info_close")]
        ]
    elif action == "toadmin":
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            if member.status in ['left', 'kicked']:
                await query.answer("❌ This user is not in the group. Please add them first.", show_alert=True)
                return
            
            # Show promotion menu with permissions (even if already admin, to edit)
            promote_key = f"promote_{user_id}"
            
            # If already admin, try to get current perms
            current_perms = DEFAULT_PERMISSIONS.copy()
            if member.status == 'administrator':
                for key in DEFAULT_PERMISSIONS.keys():
                    current_perms[key] = getattr(member, key, False)
            
            context.user_data[promote_key] = current_perms
            context.user_data[promote_key]["back_to_info"] = True
            
            keyboard = get_promotion_keyboard(user_id, context.user_data[promote_key], back_to_info=True)
            text_override = f"🛡️ <b>Edit Admin Permissions</b> for user <code>{user_id}</code>\n\nSelect permissions to grant/revoke:"
            try:
                await query.edit_message_text(text_override, parse_mode=ParseMode.HTML, reply_markup=keyboard)
            except BadRequest: pass
            await query.answer()
            return
        except Exception as e:
            await query.answer(f"Error checking user status: {e}", show_alert=True)
            return

    elif action == "tomember":
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            if member.status in ['left', 'kicked']:
                # User not in group, show add/invite option
                chat = await context.bot.get_chat(chat_id)
                invite_link = chat.invite_link
                if not invite_link:
                    invite_link = await context.bot.export_chat_invite_link(chat_id)
                
                text_override = f"👤 <b>Add Member</b>\n\nUser <code>{user_id}</code> is not in this group.\n\nShare this invite link with them:\n{invite_link}"
                keyboard = [[InlineKeyboardButton("🔙 Back", callback_data=f"info_roles_{user_id}"), InlineKeyboardButton("❌ Close", callback_data="info_close")]]
                try:
                    await query.edit_message_text(text_override, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
                except BadRequest: pass
                await query.answer()
                return
            else:
                # Already a member, maybe demote from admin?
                if member.status == 'administrator':
                    await demote_command(mock_update, context)
                    await query.answer("Admin demoted to regular member.")
                else:
                    await query.answer("User is already a member.", show_alert=True)
        except Exception as e:
            await query.answer(f"Error: {e}", show_alert=True)
            
        query.data = f"info_roles_{user_id}"
        await info_callback_handler(update, context)
        return
    elif action == "tomuter":
        from moderation import add_muter, remove_muter
        if check_is_muter(chat_id, user_id):
            remove_muter(chat_id, user_id)
            await query.answer("Muter role removed.")
        else:
            add_muter(chat_id, user_id)
            await query.answer("Muter role granted.")
        query.data = f"info_roles_{user_id}"
        await info_callback_handler(update, context)
        return
    elif action == "perms":
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status in ['creator', 'administrator']:
            text_override = f"🛡️ <b>Permissions</b> for user <code>{user_id}</code>\n\nAdmin/Owner permissions cannot be toggled here. Use 🎭 Roles."
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data=f"info_back_{user_id}"), InlineKeyboardButton("❌ Close", callback_data="info_close")]]
        else:
            p = {
                "msg": member.can_send_messages if member.status == 'restricted' else True,
                "media": member.can_send_media_messages if member.status == 'restricted' else True,
                "voice": member.can_send_voice_notes if member.status == 'restricted' else True,
                "doc": member.can_send_documents if member.status == 'restricted' else True,
                "poll": member.can_send_polls if member.status == 'restricted' else True,
                "other": member.can_send_other_messages if member.status == 'restricted' else True,
                "music": member.can_send_audios if member.status == 'restricted' else True,
                "video": member.can_send_videos if member.status == 'restricted' else True
            }
            
            text_override = f"🛡️ <b>Permission Management</b> for user <code>{user_id}</code>"
            keyboard = [
                [InlineKeyboardButton(f"Send Message: {'✅' if p['msg'] else '❌'}", callback_data=f"info_toperm_msg_{user_id}")],
                [InlineKeyboardButton(f"Send Media: {'✅' if p['media'] else '❌'}", callback_data=f"info_toperm_media_{user_id}")],
                [InlineKeyboardButton(f"Send Voice: {'✅' if p['voice'] else '❌'}", callback_data=f"info_toperm_voice_{user_id}")],
                [InlineKeyboardButton(f"Send Document/File: {'✅' if p['doc'] else '❌'}", callback_data=f"info_toperm_doc_{user_id}")],
                [InlineKeyboardButton(f"Send Music: {'✅' if p['music'] else '❌'}", callback_data=f"info_toperm_music_{user_id}")],
                [InlineKeyboardButton(f"Send Poll: {'✅' if p['poll'] else '❌'}", callback_data=f"info_toperm_poll_{user_id}")],
                [InlineKeyboardButton(f"Send Stickers/GIFs: {'✅' if p['other'] else '❌'}", callback_data=f"info_toperm_other_{user_id}")],
                [InlineKeyboardButton("🔙 Back", callback_data=f"info_back_{user_id}"), InlineKeyboardButton("❌ Close", callback_data="info_close")]
            ]
    elif action.startswith("toperm"):
        perm_type = data[2]
        user_id = int(data[3])
        member = await context.bot.get_chat_member(chat_id, user_id)
        
        # Determine current state or default to True if not restricted
        is_restricted = member.status == 'restricted'
        
        # Build current permissions object
        current_p = {
            "can_send_messages": member.can_send_messages if is_restricted else True,
            "can_send_media_messages": member.can_send_media_messages if is_restricted else True,
            "can_send_audios": member.can_send_audios if is_restricted else True,
            "can_send_documents": member.can_send_documents if is_restricted else True,
            "can_send_photos": member.can_send_photos if is_restricted else True,
            "can_send_videos": member.can_send_videos if is_restricted else True,
            "can_send_video_notes": member.can_send_video_notes if is_restricted else True,
            "can_send_voice_notes": member.can_send_voice_notes if is_restricted else True,
            "can_send_polls": member.can_send_polls if is_restricted else True,
            "can_send_other_messages": member.can_send_other_messages if is_restricted else True,
            "can_add_web_page_previews": member.can_add_web_page_previews if is_restricted else True
        }
        
        # Toggle the specific permission
        if perm_type == "msg": current_p["can_send_messages"] = not current_p["can_send_messages"]
        elif perm_type == "media": current_p["can_send_media_messages"] = not current_p["can_send_media_messages"]
        elif perm_type == "voice": current_p["can_send_voice_notes"] = not current_p["can_send_voice_notes"]
        elif perm_type == "doc": current_p["can_send_documents"] = not current_p["can_send_documents"]
        elif perm_type == "music": current_p["can_send_audios"] = not current_p["can_send_audios"]
        elif perm_type == "poll": current_p["can_send_polls"] = not current_p["can_send_polls"]
        elif perm_type == "other": current_p["can_send_other_messages"] = not current_p["can_send_other_messages"]
        
        try:
            await context.bot.restrict_chat_member(chat_id, user_id, permissions=ChatPermissions(**current_p))
            await query.answer("Permissions updated.")
        except Exception as e:
            await query.answer(f"Failed to update permissions: {e}", show_alert=True)
            
        query.data = f"info_perms_{user_id}"
        await info_callback_handler(update, context)
        return
    elif action == "close":
        try:
            await query.message.delete()
        except:
            await query.edit_message_text("Menu closed.")
        return
    elif action == "back":
        # We need to reconstruct the original info message
        # Easiest way is to call info_command with a mock update
        mock_update.message.text = f"/info {user_id}"
        # We need to delete the current menu first or just edit it back
        # Let's just edit it back to the original info text and main buttons
        # For simplicity, we can reuse the code from info_command
        from user_manager import get_user_stats
        import html
        stats = get_user_stats(user_id)
        username = stats.get("username") if stats else None
        joined_date = stats.get("joined_date", "Unknown") if stats else "Unknown"
        msg_count = stats.get("msg_count", 0) if stats else 0
        
        # Get user status and role in group
        user_status = "Unknown"; user_role = "Member"; is_muted = False
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            status = member.status
            if status == 'creator': user_status = "Present"; user_role = "Owner/Creator"
            elif status == 'administrator': user_status = "Present"; user_role = "Administrator"
            elif status == 'member': user_status = "Present"; user_role = "Member"
            elif status == 'restricted': 
                user_status = "Present (Restricted)"; user_role = "Restricted Member"
                if not member.can_send_messages: is_muted = True
            elif status == 'left': user_status = "Left"; user_role = "None"
            elif status == 'kicked': user_status = "Banned"; user_role = "None"
        except: pass

        info_text = (
            f"👤 <b>User Information</b>\n\n"
            f"• <b>User ID:</b> <code>{user_id}</code>\n"
            f"• <b>Status:</b> {user_status}\n"
            f"• <b>Role:</b> {user_role}\n"
            f"• <b>Muted:</b> {'Yes 🔇' if is_muted else 'No 🔊'}\n"
            f"• <b>Joined Date:</b> {joined_date}\n"
            f"• <b>Total Messages:</b> {msg_count}"
        )
        
        keyboard = [
            [InlineKeyboardButton("⚠️ Warns", callback_data=f"info_warns_{user_id}"), InlineKeyboardButton("🎭 Roles", callback_data=f"info_roles_{user_id}")],
            [InlineKeyboardButton("🔇 Mute" if not is_muted else "🔊 Unmute", callback_data=f"info_mute_{user_id}"), InlineKeyboardButton("🔨 Ban", callback_data=f"info_ban_{user_id}")],
            [InlineKeyboardButton("❌ Close", callback_data="info_close")]
        ]
        
        await query.edit_message_text(info_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
        await query.answer()
        return


    if text_override and keyboard:
        try:
            await query.edit_message_text(text_override, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
        except BadRequest: pass
    
    await query.answer()

async def get_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simple command to show user ID and ensure they are cached."""
    chat_id = update.effective_chat.id
    settings = get_chat_settings(chat_id)
    
    # Check access
    if settings.get("command_access") == "admins":
        if not await is_user_admin(chat_id, update.effective_user.id, context):
            return

    user = update.effective_user
    chat = update.effective_chat
    
    # Use HTML and escape inputs to prevent parsing errors
    user_name = html.escape(user.first_name)
    chat_title = html.escape(chat.title) if chat.title else "Private Chat"
    
    await send_bot_response(
        update, context,
        f"👤 <b>User Info:</b>\n"
        f"• Name: {user_name}\n"
        f"• ID: <code>{user.id}</code>\n"
        f"• Username: @{user.username if user.username else 'None'}\n\n"
        f"📍 <b>Chat Info:</b>\n"
        f"• Title: {chat_title}\n"
        f"• ID: <code>{chat.id}</code>",
        parse_mode=ParseMode.HTML
    )

def main():
    """Main function to run the bot."""
    if not BOT_TOKEN:
        print("BOT_TOKEN not found in .env file. Please add it.")
        return

    # Initialize the bot application
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add general handlers (Group 0)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("id", get_id_command))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CallbackQueryHandler(info_callback_handler, pattern="^info_"))
    application.add_handler(MessageHandler(filters.ALL & (filters.ChatType.GROUPS | filters.ChatType.SUPERGROUP), cache_user_handler), group=-1)

    # Add admin handlers (Group 0)
    for handler in get_admin_handlers():
        application.add_handler(handler)

    # Add help handlers (Group 0)
    for handler in get_help_handlers():
        application.add_handler(handler)

    # Add settings handlers (Group 0)
    for handler in get_settings_handlers():
        application.add_handler(handler)

    # Add moderation handlers (Group 0)
    for handler in get_moderation_handlers():
        application.add_handler(handler)

    # Add welcome handlers (Group 0)
    for handler in get_welcome_handlers():
        application.add_handler(handler)

    # Add block content handlers (Group 0)
    for handler in get_block_content_handlers():
        # The MessageHandler for block content check should be in its own group to run concurrently
        if isinstance(handler, MessageHandler) and not isinstance(handler, CommandHandler):
            application.add_handler(handler, group=4)
        else:
            application.add_handler(handler)

    # Add clean service handlers in a separate group (Group 1)
    # This ensures they run even if other handlers match
    for handler in get_clean_service_handlers():
        application.add_handler(handler, group=1)

    # Add auto delete handlers in another separate group (Group 2)
    for handler in get_auto_delete_handlers():
        application.add_handler(handler, group=2)

    # Add filter handlers in another group (Group 3)
    for handler in get_filter_handlers():
        # The filter command handlers go to group 0 (default), 
        # but the MessageHandler for triggers should be in its own group to run concurrently
        if isinstance(handler, MessageHandler):
            application.add_handler(handler, group=3)
        else:
            application.add_handler(handler)

    # Start the bot
    print("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
