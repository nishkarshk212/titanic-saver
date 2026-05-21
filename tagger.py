import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from telegram.constants import ParseMode
from telethon import functions, types
from voice_chat import telethon_client
from settings_manager_mongo import get_chat_settings
from user_manager_mongo import is_user_admin
from config import delete_message_job

logger = logging.getLogger(__name__)

# Track active tagging tasks per chat to allow stopping them
# Format: {chat_id: stop_event}
ACTIVE_TAGS = {}

async def tag_everyone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tags everyone in the group in batches."""
    chat = update.effective_chat
    user = update.effective_user
    
    if not chat or chat.type not in ["group", "supergroup"]:
        return

    # Check if feature is enabled
    settings = get_chat_settings(chat.id)
    if not settings.get("tagger_enabled", True):
        return await update.message.reply_text("❌ Tagger feature is disabled in this group.")

    # Check if user is admin
    if not await is_user_admin(chat.id, user.id, context):
        return await update.message.reply_text("❌ Only admins can use this command.")

    # Telethon check
    if not telethon_client or not telethon_client.is_connected():
        return await update.message.reply_text("❌ Voice Monitor (Telethon) is not connected. Tagger unavailable.")

    # Check for stop command
    if context.args and context.args[0].lower() == "stop":
        if chat.id in ACTIVE_TAGS:
            ACTIVE_TAGS[chat.id].set()
            return await update.message.reply_text("🛑 Tagging process stopped.")
        return await update.message.reply_text("❌ No active tagging process found.")

    if chat.id in ACTIVE_TAGS:
        return await update.message.reply_text("❌ A tagging process is already running. Use <code>/tag stop</code> to cancel it.", parse_mode=ParseMode.HTML)

    custom_message = " ".join(context.args) if context.args else "Attention everyone! 📢"
    
    # Start tagging
    stop_event = asyncio.Event()
    ACTIVE_TAGS[chat.id] = stop_event
    
    try:
        # Normalize chat_id for Telethon
        tele_chat_id = int(str(chat.id).replace('-100', ''))
        
        # Get all participants
        participants = await telethon_client.get_participants(tele_chat_id)
        
        if not participants:
            return await update.message.reply_text("❌ Could not find any participants to tag.")

        # Filter out bots and the bot itself
        me = await telethon_client.get_me()
        users_to_tag = [p for p in participants if not p.bot and p.id != me.id]
        
        total = len(users_to_tag)
        await update.message.reply_text(f"🚀 Starting to tag {total} users...")

        # Tag in batches of 5
        batch_size = 5
        for i in range(0, total, batch_size):
            if stop_event.is_set():
                break
                
            batch = users_to_tag[i:i+batch_size]
            mentions = []
            for u in batch:
                name = u.first_name or "User"
                mentions.append(f'<a href="tg://user?id={u.id}">{name}</a>')
            
            tag_text = f"{custom_message}\n\n" + " ".join(mentions)
            
            try:
                await context.bot.send_message(
                    chat_id=chat.id,
                    text=tag_text,
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                logger.error(f"Error sending tag batch: {e}")
                if "Flood control exceeded" in str(e):
                    # Extract wait time if possible, or just wait 10s
                    await asyncio.sleep(10)
                else:
                    break
            
            # Wait between batches to avoid flood
            await asyncio.sleep(2)
            
        if stop_event.is_set():
            await update.message.reply_text("🛑 Tagging stopped by admin.")
        else:
            await update.message.reply_text("✅ All users have been tagged.")
            
    except Exception as e:
        logger.error(f"Error in tag_everyone: {e}")
        await update.message.reply_text(f"❌ An error occurred: {str(e)}")
    finally:
        if chat.id in ACTIVE_TAGS:
            del ACTIVE_TAGS[chat.id]

async def tag_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tags all admins in the group."""
    chat = update.effective_chat
    user = update.effective_user
    
    if not chat or chat.type not in ["group", "supergroup"]:
        return

    # Check if user is admin
    if not await is_user_admin(chat.id, user.id, context):
        return await update.message.reply_text("❌ Only admins can use this command.")

    custom_message = " ".join(context.args) if context.args else "Admins, attention needed! 🛠"
    
    try:
        admins = await chat.get_administrators()
        if not admins:
            return await update.message.reply_text("❌ Could not find any admins.")

        mentions = []
        for admin in admins:
            if admin.user.is_bot:
                continue
            name = admin.user.first_name
            mentions.append(f'<a href="tg://user?id={admin.user.id}">{name}</a>')
        
        # Tag admins in one or two messages (usually not many admins)
        batch_size = 10
        for i in range(0, len(mentions), batch_size):
            batch = mentions[i:i+batch_size]
            tag_text = f"{custom_message}\n\n" + " ".join(batch)
            
            await context.bot.send_message(
                chat_id=chat.id,
                text=tag_text,
                parse_mode=ParseMode.HTML
            )
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"Error in tag_admins: {e}")
        await update.message.reply_text(f"❌ An error occurred: {str(e)}")

def get_tagger_handlers():
    """Returns tagger handlers."""
    return [
        CommandHandler(["tag", "all", "everyone"], tag_everyone),
        CommandHandler(["atag", "admins", "adm"], tag_admins),
    ]
