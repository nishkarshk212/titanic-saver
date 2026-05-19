"""
Anti-Flood Module - Detect and penalize message flooding
"""

import logging
import time
from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes, MessageHandler, filters
from settings_manager_mongo import get_chat_settings
from user_manager_mongo import is_user_admin
from config import OWNER_ID

# In-memory storage for flood tracking: {chat_id: {user_id: [timestamps]}}
FLOOD_TRACKER = {}

async def handle_antiflood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles anti-flood detection and penalties."""
    if not update.effective_chat or not update.effective_user or update.effective_chat.type == "private":
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Skip admins and owner
    if user_id == OWNER_ID or await is_user_admin(chat_id, user_id, context):
        return

    settings = get_chat_settings(chat_id)
    if not settings.get("antiflood_enabled", False):
        return

    limit = settings.get("antiflood_limit", 5)
    window = settings.get("antiflood_window", 3)
    penalty = settings.get("antiflood_penalty", "mute")
    
    now = time.time()
    
    # Initialize tracker for chat if not exists
    if chat_id not in FLOOD_TRACKER:
        FLOOD_TRACKER[chat_id] = {}
    
    # Initialize user timestamps if not exists
    if user_id not in FLOOD_TRACKER[chat_id]:
        FLOOD_TRACKER[chat_id][user_id] = []
    
    # Add current timestamp
    user_times = FLOOD_TRACKER[chat_id][user_id]
    user_times.append(now)
    
    # Remove timestamps outside the window
    FLOOD_TRACKER[chat_id][user_id] = [t for t in user_times if now - t <= window]
    
    # Check if limit exceeded
    if len(FLOOD_TRACKER[chat_id][user_id]) >= limit:
        # Clear tracker for this user to avoid repeat penalties for the same flood
        FLOOD_TRACKER[chat_id][user_id] = []
        
        user_name = update.effective_user.first_name
        mention = f"<a href='tg://user?id={user_id}'>{user_name}</a>"
        
        try:
            # Apply penalty
            if penalty == "warn":
                await update.effective_message.reply_text(
                    f"⚠️ {mention}, please stop flooding! You are sending messages too fast.",
                    parse_mode='HTML'
                )
            elif penalty == "mute":
                await context.bot.restrict_chat_member(
                    chat_id, 
                    user_id, 
                    permissions=ChatPermissions(can_send_messages=False)
                )
                await context.bot.send_message(
                    chat_id,
                    f"🔇 {mention} has been muted for flooding.",
                    parse_mode='HTML'
                )
            elif penalty == "kick":
                await context.bot.ban_chat_member(chat_id, user_id)
                await context.bot.unban_chat_member(chat_id, user_id)
                await context.bot.send_message(
                    chat_id,
                    f"👞 {mention} has been kicked for flooding.",
                    parse_mode='HTML'
                )
            elif penalty == "ban":
                await context.bot.ban_chat_member(chat_id, user_id)
                await context.bot.send_message(
                    chat_id,
                    f"🚫 {mention} has been banned for flooding.",
                    parse_mode='HTML'
                )
            
            # Delete the flooding message
            await update.effective_message.delete()
            
        except Exception as e:
            logging.error(f"Error applying antiflood penalty: {e}")

def get_antiflood_handlers():
    """Returns antiflood message handler."""
    return [
        MessageHandler(filters.ALL & ~filters.COMMAND & filters.ChatType.GROUPS, handle_antiflood)
    ]
