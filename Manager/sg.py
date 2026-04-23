"""
Manager SG - Sangmata bot to check username history
Ported from AnnieXMusic to python-telegram-bot

Note: This requires a userbot assistant to work properly.
Since python-telegram-bot doesn't support userbots natively,
this implementation uses the bot directly with Sangmata bot.
"""

import asyncio
import random
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

async def sg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check username history using Sangmata bot."""
    status_msg = await update.message.reply_text("👀")
    
    try:
        if update.message.reply_to_message:
            target_user_id = update.message.reply_to_message.from_user.id
        else:
            parts = update.message.text.split()
            if len(parts) < 2:
                return await status_msg.edit_text("❌ Usage: `/sg` username / id / reply", parse_mode='Markdown')
            
            target_input = parts[1]
            
            if target_input.isdigit():
                target_user_id = int(target_input)
            else:
                user = await context.bot.get_chat(target_input)
                target_user_id = user.id
    
    except Exception as e:
        return await status_msg.edit_text("❌ Invalid user. Please reply to a user or provide a valid username/id.")
    
    sangmata_bots = ["@SangMataInfo_bot", "@SangMata_beta_bot"]
    sg_bot = random.choice(sangmata_bots)
    
    try:
        # Forward message to Sangmata bot
        await context.bot.send_message(sg_bot, str(target_user_id))
    except Exception as e:
        return await status_msg.edit_text(f"❌ Failed to contact {sg_bot}\n`{str(e)}`", parse_mode='Markdown')
    
    await asyncio.sleep(2)
    
    # Get updates from the bot
    try:
        # Try to get response from Sangmata
        updates = await context.bot.get_updates(timeout=30)
        
        found = False
        for upd in updates:
            if upd.message and upd.message.chat.username in ['SangMataInfo_bot', 'SangMata_beta_bot']:
                if upd.message.text and str(target_user_id) in str(upd.message.text):
                    await update.message.reply_text(upd.message.text)
                    found = True
                    # Mark update as processed
                    await context.bot.get_updates(offset=upd.update_id + 1)
                    break
        
        if not found:
            await update.message.reply_text("🤖 Bot didn't return any username history.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Could not retrieve results: {str(e)}")
    
    await status_msg.delete()

def get_sg_handlers():
    """Return SG handler."""
    return [CommandHandler("sg", sg)]
