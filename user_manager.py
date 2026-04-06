import json
import os
import logging

from telegram import Update
from telegram.ext import ContextTypes

from config import OWNER_ID

import datetime

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
    """Saves user mapping for later resolution and tracks stats."""
    users_data = load_users()
    
    # We use user_id as string for JSON keys to be consistent
    uid_str = str(user_id)
    
    # Find user entry (either by ID or username)
    user_entry = None
    
    # 1. Try to find by ID
    for key, data in users_data.items():
        if str(data.get("id")) == uid_str:
            user_entry = data
            break
            
    # If not found by ID, check if username exists and maps to this user
    if not user_entry and username:
        clean_username = username.lower().replace('@', '')
        if clean_username in users_data:
            user_entry = users_data[clean_username]

    now = datetime.datetime.now().strftime("%Y-%m-%d")
    
    if not user_entry:
        # New user
        user_entry = {
            "id": user_id,
            "name": first_name,
            "username": username.lower().replace('@', '') if username else None,
            "joined_date": now,
            "msg_count": 0
        }
    else:
        # Update existing user
        user_entry["name"] = first_name
        if username:
            user_entry["username"] = username.lower().replace('@', '')

    # Save by username for resolution and by ID for stats
    if user_entry.get("username"):
        users_data[user_entry["username"]] = user_entry
    
    # Also save a copy indexed by ID for faster lookups
    users_data[f"id_{uid_str}"] = user_entry
    
    save_users(users_data)

def increment_message_count(user_id):
    """Increments the message count for a user."""
    users_data = load_users()
    uid_str = f"id_{user_id}"
    if uid_str in users_data:
        users_data[uid_str]["msg_count"] = users_data[uid_str].get("msg_count", 0) + 1
        # Also update the username entry if it exists
        username = users_data[uid_str].get("username")
        if username and username in users_data:
            users_data[username]["msg_count"] = users_data[uid_str]["msg_count"]
        save_users(users_data)

def get_user_stats(user_id):
    """Returns user stats from cache."""
    users_data = load_users()
    uid_str = f"id_{user_id}"
    return users_data.get(uid_str)

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
    
    # Telegram's ID for anonymous admins (Group Anonymous Bot)
    ANONYMOUS_ADMIN_ID = 1087968824
    if user_id == ANONYMOUS_ADMIN_ID:
        return True
        
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
    
    # Anonymous admins are allowed to configure settings as we can't check specific rights easily
    ANONYMOUS_ADMIN_ID = 1087968824
    if user_id == ANONYMOUS_ADMIN_ID:
        return True
        
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
