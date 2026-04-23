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
    
    # Sangmata bot usernames (multiple options)
    sangmata_bots = ["@SangMataInfo_bot", "@SangmataInfo_bot"]
    
    # Try each Sangmata bot
    last_error = None
    for sg_bot in sangmata_bots:
        try:
            # Send the user ID to Sangmata bot
            await context.bot.send_message(sg_bot, str(target_user_id))
            await asyncio.sleep(3)
            
            # Try to get the response
            try:
                updates = await context.bot.get_updates(timeout=10)
                
                for upd in reversed(updates):  # Check from latest
                    if (upd.message and 
                        upd.message.chat.username and 
                        'sangmata' in upd.message.chat.username.lower()):
                        
                        # Found response from Sangmata
                        response_text = upd.message.text or upd.message.html
                        if response_text and len(response_text) > 50:  # Valid response
                            await status_msg.edit_text(
                                f"👤 <b>Username History</b>\n\n"
                                f"User: {target_name} (<code>{target_user_id}</code>)\n\n"
                                f"{response_text}",
                                parse_mode='HTML'
                            )
                            # Mark update as processed
                            await context.bot.get_updates(offset=upd.update_id + 1)
                            return
            except Exception as e:
                last_error = str(e)
                continue
                
        except Exception as e:
            last_error = str(e)
            continue
    
    # If all attempts failed
    await status_msg.edit_text(
        f"❌ Could not retrieve username history.\n\n"
        f"This could be because:\n"
        f"• Sangmata bot is temporarily unavailable\n"
        f"• The user has no username history\n"
        f"• Rate limit reached\n\n"
        f"Try again in a few moments.\n\n"
        f"<i>Error: {last_error}</i>",
        parse_mode='HTML'
    )

def get_sg_handlers():
    """Return SG handler."""
    return [CommandHandler("sg", sg)]
