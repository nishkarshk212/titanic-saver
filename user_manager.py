import json
import os
import logging

from telegram import Update
from telegram.ext import ContextTypes

from config import OWNER_ID

USERS_FILE = "user_cache.json"

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_users(users_data):
    with open(USERS_FILE, "w") as f:
        json.dump(users_data, f, indent=4)

def cache_user(user_id, username, first_name):
    """Saves user mapping for later resolution."""
    if not username: return
    
    users_data = load_users()
    username = username.lower().replace('@', '')
    
    # Only save if changed or new
    if username not in users_data or users_data[username]["id"] != user_id:
        logging.info(f"Caching user: @{username} -> {user_id}")
        users_data[username] = {"id": user_id, "name": first_name}
        save_users(users_data)

def resolve_username(username):
    """Returns (user_id, first_name) if found in cache."""
    users_data = load_users()
    username = username.lower().replace('@', '')
    user_info = users_data.get(username)
    if user_info:
        return user_info["id"], user_info["name"]
    return None, None

async def get_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Extracts user ID from reply, mention, or argument."""
    # 1. Check if it's a reply
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        return user.id, user.first_name
    
    # 2. Check for mentions in entities
    if update.message.entities:
        for entity in update.message.entities:
            if entity.type == 'mention':
                username_text = update.message.text[entity.offset:entity.offset+entity.length]
                user_id, user_name = resolve_username(username_text)
                if user_id: return user_id, user_name
            elif entity.type == 'text_mention':
                return entity.user.id, entity.user.first_name

    # 3. Check arguments (ID or Username)
    if context.args:
        arg = context.args[0]
        # Check if ID
        if arg.isdigit():
            try:
                user_id = int(arg)
                chat_member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
                return user_id, chat_member.user.first_name
            except:
                return int(arg), arg
        
        # If it's a username but not found in entities
        if arg.startswith('@'):
            user_id, user_name = resolve_username(arg)
            if user_id: return user_id, user_name
            
    return None, None

async def is_user_admin(chat_id, user_id, context):
    """Check if the user is an admin or owner."""
    if not user_id: return False
    if user_id == OWNER_ID:
        return True
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except:
        return False

async def can_user_configure_settings(chat_id, user_id, context):
    """Check if a user can configure settings (Owner, Creator, or Admin with Change Info + Ban perms)."""
    if not user_id: return False
    if user_id == OWNER_ID:
        return True
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status == 'creator':
            return True
        if member.status == 'administrator':
            # Check for both "Change Group Info" and "Ban Users" (can_restrict_members)
            return member.can_change_info and member.can_restrict_members
        return False
    except:
        return False
