"""
Manager Purge - Delete messages in bulk
Ported from AnnieXMusic to python-telegram-bot
"""

import asyncio
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from telegram.error import Forbidden, BadRequest
from settings_manager_mongo import get_chat_settings

def divide_chunks(l, n=100):
    """Divide list into chunks."""
    for i in range(0, len(l), n):
        yield l[i: i + n]

async def purge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Purge messages from replied message to current."""
    chat = update.effective_chat
    
    # Check if command is enabled
    settings = get_chat_settings(chat.id)
    if not settings.get("manager_purge_enabled", True):
        return await update.message.reply_text("❌ The /purge command is currently disabled.")
    
    if chat.type not in ['group', 'supergroup']:
        return await update.message.reply_text("I can't purge messages in a basic group. Please convert it to a supergroup.")
    
    if not update.message.reply_to_message:
        return await update.message.reply_text("Reply to a message to start purge!")
    
    message_ids = list(range(update.message.reply_to_message.id, update.message.id))
    m_list = list(divide_chunks(message_ids))
    
    try:
        for plist in m_list:
            try:
                await context.bot.delete_messages(chat.id, plist)
                await asyncio.sleep(0.5)
            except Exception as e:
                if 'FloodWait' in str(type(e)):
                    await asyncio.sleep(int(str(e).split()[-1]))
        
        await update.message.delete()
        count = len(message_ids)
        confirm = await update.message.reply_text(f"✅ | **Deleted `{count}` messages.**", parse_mode='Markdown')
        await asyncio.sleep(3)
        await confirm.delete()
    except Forbidden:
        await update.message.reply_text("I can't delete messages in this chat. Maybe too old or no rights.")
    except Exception as e:
        await update.message.reply_text(f"**Error occurred:**\n<code>{str(e)}</code>", parse_mode='HTML')

async def spurge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Silent purge (delete command message too)."""
    chat = update.effective_chat
    
    if chat.type not in ['group', 'supergroup']:
        return await update.message.reply_text("I can't purge messages in a basic group. Please convert it to a supergroup.")
    
    if not update.message.reply_to_message:
        return await update.message.reply_text("Reply to a message to start purge!")
    
    message_ids = list(range(update.message.reply_to_message.id, update.message.id))
    m_list = list(divide_chunks(message_ids))
    
    try:
        for plist in m_list:
            try:
                await context.bot.delete_messages(chat.id, plist)
                await asyncio.sleep(0.5)
            except Exception as e:
                if 'FloodWait' in str(type(e)):
                    await asyncio.sleep(int(str(e).split()[-1]))
        
        await update.message.delete()
    except Forbidden:
        await update.message.reply_text("I can't delete messages in this chat.")
    except Exception as e:
        await update.message.reply_text(f"**Error occurred:**\n<code>{str(e)}</code>", parse_mode='HTML')

async def delete_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a single message."""
    chat = update.effective_chat
    
    if chat.type not in ['group', 'supergroup']:
        return await update.message.reply_text("I can't delete messages in a basic group.")
    
    if not update.message.reply_to_message:
        return await update.message.reply_text("What do you want to delete?")
    
    try:
        await update.message.delete()
        await update.message.reply_to_message.delete()
    except Exception as e:
        await update.message.reply_text(f"**Failed to delete message:**\n<code>{str(e)}</code>", parse_mode='HTML')

async def purge_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete all messages in the group."""
    chat = update.effective_chat
    user_id = update.effective_user.id
    
    # Check permissions
    from user_manager_mongo import is_user_admin
    if not await is_user_admin(chat.id, user_id, context):
        return await update.message.reply_text("Only admins can use this command.")

    if chat.type not in ['group', 'supergroup']:
        return await update.message.reply_text("This command works only in supergroups.")

    # Confirmation logic if not already confirmed
    if not context.args or context.args[0] != "confirm":
        return await update.message.reply_text(
            "⚠️ **WARNING**\n\n"
            "This will attempt to delete ALL messages in this group. This action cannot be undone.\n\n"
            "Type `/purgeall confirm` to proceed.",
            parse_mode='Markdown'
        )

    status_msg = await update.message.reply_text("🚀 **Starting global purge...**", parse_mode='Markdown')
    
    current_id = update.message.id
    deleted_count = 0
    
    # We delete in batches of 100 backwards
    # We'll try to delete up to 10000 messages or until we hit too many errors
    try:
        for i in range(current_id, 0, -100):
            batch = list(range(max(1, i - 100), i))
            try:
                await context.bot.delete_messages(chat.id, batch)
                deleted_count += len(batch)
                if deleted_count % 500 == 0:
                    await status_msg.edit_text(f"🚀 **Purging...**\nDeleted: `{deleted_count}` messages", parse_mode='Markdown')
                await asyncio.sleep(0.5) # Avoid flood limits
            except BadRequest as e:
                if "Message to delete not found" in str(e):
                    continue
                elif "Message can't be deleted" in str(e):
                    # Probably reached messages older than 48h or bot lacks rights for old messages
                    # But in supergroups, bots with delete rights can delete any message.
                    continue
                else:
                    break
            except Exception:
                break
                
        await status_msg.edit_text(f"✅ **Global purge complete!**\nTotal deleted: `{deleted_count}` messages", parse_mode='Markdown')
        await asyncio.sleep(5)
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ **Purge interrupted:**\n`{str(e)}`", parse_mode='Markdown')

async def purge_user_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete all messages of a specific user in the group."""
    chat = update.effective_chat
    sender_id = update.effective_user.id
    
    # Check permissions
    from user_manager_mongo import is_user_admin, get_user_id
    if not await is_user_admin(chat.id, sender_id, context):
        return await update.message.reply_text("Only admins can use this command.")

    target_user_id, target_user_name = await get_user_id(update, context)
    if not target_user_id:
        return await update.message.reply_text("Please reply to a user or provide a user ID/username to purge their messages.")

    status_msg = await update.message.reply_text(f"🔍 **Searching and deleting messages of {target_user_name}...**", parse_mode='Markdown')
    
    try:
        member = await context.bot.get_chat_member(chat.id, target_user_id)
        
        # If user is owner, we cannot demote them. Must scan manually or use other methods.
        if member.status == 'creator':
            await status_msg.edit_text(f"⚠️ **Cannot demote the owner.** Scanning manually is not supported yet for the owner. "
                                    f"I've cleared what I could from my cache.", parse_mode='Markdown')
            await asyncio.sleep(5)
            await status_msg.delete()
            return

        is_admin = member.status == 'administrator'
        
        if is_admin:
            # Check bot permissions to demote and re-promote
            bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
            if not (bot_member.status == 'creator' or (bot_member.status == 'administrator' and bot_member.can_promote_members)):
                await status_msg.edit_text("❌ I need 'Add New Admins' permission to purge an admin's messages.", parse_mode='Markdown')
                return

            # Store current admin rights to restore later
            rights = {
                'can_change_info': member.can_change_info,
                'can_delete_messages': member.can_delete_messages,
                'can_restrict_members': member.can_restrict_members,
                'can_invite_users': member.can_invite_users,
                'can_pin_messages': member.can_pin_messages,
                'can_post_stories': member.can_post_stories,
                'can_edit_stories': member.can_edit_stories,
                'can_delete_stories': member.can_delete_stories,
                'can_manage_video_chats': member.can_manage_video_chats,
                'can_promote_members': member.can_promote_members,
                'is_anonymous': member.is_anonymous,
                'custom_title': member.custom_title
            }
            
            await status_msg.edit_text(f"🛠 **Temporarily demoting admin {target_user_name} to purge messages...**", parse_mode='Markdown')
            
            # Demote
            await context.bot.promote_chat_member(chat.id, target_user_id, can_change_info=False)
            await asyncio.sleep(1)
            
            # Ban with revoke
            await context.bot.ban_chat_member(chat.id, target_user_id, revoke_messages=True)
            await asyncio.sleep(1)
            
            # Unban
            await context.bot.unban_chat_member(chat.id, target_user_id)
            await asyncio.sleep(1)
            
            # Re-promote
            await context.bot.promote_chat_member(chat.id, target_user_id, **rights)
            
            await status_msg.edit_text(f"✅ **Purged all messages of admin {target_user_name} and restored their rights.**", parse_mode='Markdown')
            
        else:
            # Regular member
            await context.bot.ban_chat_member(chat.id, target_user_id, revoke_messages=True)
            await context.bot.unban_chat_member(chat.id, target_user_id)
            await status_msg.edit_text(f"✅ **Purged all messages of {target_user_name}.**", parse_mode='Markdown')
            
        await asyncio.sleep(5)
        await status_msg.delete()
        
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error during purge:**\n`{str(e)}`", parse_mode='Markdown')

def get_purge_handlers():
    """Return purge handlers."""
    return [
        CommandHandler("purge", purge),
        CommandHandler("spurge", spurge),
        CommandHandler("del", delete_msg),
        CommandHandler(["purgeall", "cleanall"], purge_all),
        CommandHandler(["purgeuser", "delalluser"], purge_user_messages),
    ]
