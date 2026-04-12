import logging
import datetime
from database import get_collection, COLLECTIONS
from config import OWNER_ID
from telegram import Update
from telegram.ext import ContextTypes

def cache_user(user_id, username, first_name):
    """Saves user mapping for later resolution and tracks stats using MongoDB."""
    try:
        users_col = get_collection(COLLECTIONS["users"])
        if users_col is None:
            logging.error("MongoDB not connected - cannot cache user")
            return False
        
        uid_str = str(user_id)
        now = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Find existing user by ID
        existing_user = users_col.find_one({"id": user_id})
        
        if existing_user:
            # Update existing user
            update_data = {
                "name": first_name,
                "last_updated": datetime.datetime.now()
            }
            if username:
                update_data["username"] = username.lower().replace('@', '')
            
            users_col.update_one(
                {"id": user_id},
                {"$set": update_data}
            )
        else:
            # Create new user
            user_doc = {
                "id": user_id,
                "name": first_name,
                "username": username.lower().replace('@', '') if username else None,
                "joined_date": now,
                "msg_count": 0,
                "created_at": datetime.datetime.now(),
                "last_updated": datetime.datetime.now()
            }
            users_col.insert_one(user_doc)
        
        return True
    except Exception as e:
        logging.error(f"Error caching user: {e}")
        return False

def increment_message_count(user_id):
    """Increments the message count for a user using MongoDB."""
    try:
        users_col = get_collection(COLLECTIONS["users"])
        if users_col is None:
            return False
        
        result = users_col.update_one(
            {"id": user_id},
            {"$inc": {"msg_count": 1}}
        )
        return result.modified_count > 0
    except Exception as e:
        logging.error(f"Error incrementing message count: {e}")
        return False

def get_user_stats(user_id):
    """Returns user stats from MongoDB."""
    try:
        users_col = get_collection(COLLECTIONS["users"])
        if users_col is None:
            return None
        
        user_doc = users_col.find_one({"id": user_id})
        if user_doc:
            return {
                "id": user_doc["id"],
                "name": user_doc.get("name"),
                "username": user_doc.get("username"),
                "joined_date": user_doc.get("joined_date", "Unknown"),
                "msg_count": user_doc.get("msg_count", 0)
            }
        return None
    except Exception as e:
        logging.error(f"Error getting user stats: {e}")
        return None

def resolve_username(username):
    """Returns (user_id, first_name) if found in MongoDB."""
    try:
        users_col = get_collection(COLLECTIONS["users"])
        if users_col is None:
            return None, None
        
        username = username.lower().replace('@', '')
        user_doc = users_col.find_one({"username": username})
        
        if user_doc:
            return user_doc["id"], user_doc.get("name")
        return None, None
    except Exception as e:
        logging.error(f"Error resolving username: {e}")
        return None, None

async def get_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Extracts user ID or Chat ID from reply, mention, or argument."""
    # 1. Check if it's a reply
    if update.message.reply_to_message:
        reply = update.message.reply_to_message
        # Check if it's a post from a channel or anonymous admin
        if reply.sender_chat:
            return reply.sender_chat.id, reply.sender_chat.title or reply.sender_chat.username
        user = reply.from_user
        return user.id, user.first_name
    
    # 2. Check for mentions in entities
    if update.message.entities:
        for entity in update.message.entities:
            if entity.type == 'mention':
                username_text = update.message.text[entity.offset:entity.offset+entity.length]
                user_id, user_name = resolve_username(username_text)
                if user_id: return user_id, user_name
                
                # If not in cache, try to get chat info directly
                try:
                    chat = await context.bot.get_chat(username_text)
                    return chat.id, chat.title or chat.username
                except: pass
            elif entity.type == 'text_mention':
                return entity.user.id, entity.user.first_name

    # 3. Check arguments (ID or Username)
    if context.args:
        arg = context.args[0]
        # Safety check: arg could be None
        if arg is None:
            return None, None
            
        # Check if ID
        if str(arg).startswith('-') or str(arg).isdigit():
            try:
                chat_id = int(arg)
                # Try to get chat info
                try:
                    chat = await context.bot.get_chat(chat_id)
                    return chat.id, chat.title or chat.username or str(chat.id)
                except:
                    # Fallback to just the ID
                    return chat_id, str(chat_id)
            except:
                pass
        
        # If it's a username but not found in entities
        if str(arg).startswith('@'):
            user_id, user_name = resolve_username(arg)
            if user_id: return user_id, user_name
            
            # Try to resolve via bot
            try:
                chat = await context.bot.get_chat(arg)
                return chat.id, chat.title or chat.username
            except: pass
            
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
