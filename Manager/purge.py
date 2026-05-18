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

def get_purge_handlers():
    """Return purge handlers."""
    return [
        CommandHandler("purge", purge),
        CommandHandler("spurge", spurge),
        CommandHandler("del", delete_msg),
        CommandHandler(["purgeall", "cleanall"], purge_all),
    ]
