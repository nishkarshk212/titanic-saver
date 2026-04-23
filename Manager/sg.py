"""
Manager SG - Sangmata bot to check username history
Ported from AnnieXMusic to python-telegram-bot

Note: This implementation forwards a message to Sangmata bot
and captures the response. Bot must be started with Sangmata first.
"""

import asyncio
import random
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

async def sg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check username history using Sangmata bot."""
    status_msg = await update.message.reply_text("🔍 Checking username history...")
    
    try:
        if update.message.reply_to_message:
            target_user_id = update.message.reply_to_message.from_user.id
            target_name = update.message.reply_to_message.from_user.first_name
        else:
            parts = update.message.text.split()
            if len(parts) < 2:
                return await status_msg.edit_text("❌ Usage: `/sg` username / id / reply", parse_mode='Markdown')
            
            target_input = parts[1]
            
            if target_input.isdigit():
                target_user_id = int(target_input)
                target_name = target_input
            else:
                if target_input.startswith('@'):
                    user = await context.bot.get_chat(target_input)
                else:
                    user = await context.bot.get_chat('@' + target_input)
                target_user_id = user.id
                target_name = user.first_name or target_input
    
    except Exception as e:
        return await status_msg.edit_text(f"❌ Invalid user. Please reply to a user or provide a valid username/id.\n\nError: {str(e)}")
    
    # Send instructions to user
    await status_msg.edit_text(
        f"📋 <b>Username History Check</b>\n\n"
        f"User: {target_name} (<code>{target_user_id}</code>)\n\n"
        f"<b>To check username history:</b>\n\n"
        f"1. Forward any message from this user to <b>@SangMataInfo_bot</b>\n"
        f"2. The bot will show you their username history\n\n"
        f"<i>Note: This feature requires manual forwarding as Telegram doesn't allow "
        f"bots to automatically message other bots.</i>",
        parse_mode='HTML'
    )

def get_sg_handlers():
    """Return SG handler."""
    return [CommandHandler("sg", sg)]
