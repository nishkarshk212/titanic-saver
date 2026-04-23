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

def get_purge_handlers():
    """Return purge handlers."""
    return [
        CommandHandler("purge", purge),
        CommandHandler("spurge", spurge),
        CommandHandler("del", delete_msg),
    ]
