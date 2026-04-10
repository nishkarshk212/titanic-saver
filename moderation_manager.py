import json
import os

WARNS_FILE = "group_warns.json"
MUTERS_FILE = "group_muters.json"

def load_data(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_data(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

# Warning Functions
def get_user_warns(chat_id, user_id):
    warns_data = load_data(WARNS_FILE)
    chat_id_str = str(chat_id)
    user_id_str = str(user_id)
    if chat_id_str in warns_data:
        return warns_data[chat_id_str].get(user_id_str, 0)
    return 0

def add_warn(chat_id, user_id):
    warns_data = load_data(WARNS_FILE)
    chat_id_str = str(chat_id)
    user_id_str = str(user_id)
    if chat_id_str not in warns_data:
        warns_data[chat_id_str] = {}
    
    current_warns = warns_data[chat_id_str].get(user_id_str, 0)
    new_warns = current_warns + 1
    warns_data[chat_id_str][user_id_str] = new_warns
    save_data(WARNS_FILE, warns_data)
    return new_warns

def reset_warns(chat_id, user_id):
    warns_data = load_data(WARNS_FILE)
    chat_id_str = str(chat_id)
    user_id_str = str(user_id)
    if chat_id_str in warns_data and user_id_str in warns_data[chat_id_str]:
        warns_data[chat_id_str][user_id_str] = 0
        save_data(WARNS_FILE, warns_data)
        return True
    return False

# Muter Functions
def is_muter(chat_id, user_id):
    muters_data = load_data(MUTERS_FILE)
    chat_id_str = str(chat_id)
    user_id_str = str(user_id)
    if chat_id_str in muters_data:
        return user_id_str in muters_data[chat_id_str]
    return False

def add_muter(chat_id, user_id):
    muters_data = load_data(MUTERS_FILE)
    chat_id_str = str(chat_id)
    user_id_str = str(user_id)
    if chat_id_str not in muters_data:
        muters_data[chat_id_str] = []
    
    if user_id_str not in muters_data[chat_id_str]:
        muters_data[chat_id_str].append(user_id_str)
        save_data(MUTERS_FILE, muters_data)
        return True
    return False

def remove_muter(chat_id, user_id):
    muters_data = load_data(MUTERS_FILE)
    chat_id_str = str(chat_id)
    user_id_str = str(user_id)
    if chat_id_str in muters_data and user_id_str in muters_data[chat_id_str]:
        muters_data[chat_id_str].remove(user_id_str)
        save_data(MUTERS_FILE, muters_data)
        return True
    return False

# Voice Chat Manager Functions
VOICE_CHAT_MANAGERS_FILE = "voice_chat_managers.json"

def is_voice_chat_manager(chat_id, user_id):
    """Check if a user can manage voice chats."""
    managers_data = load_data(VOICE_CHAT_MANAGERS_FILE)
    chat_id_str = str(chat_id)
    user_id_str = str(user_id)
    if chat_id_str in managers_data:
        return user_id_str in managers_data[chat_id_str]
    return False

def add_voice_chat_manager(chat_id, user_id):
    """Add a user as voice chat manager."""
    managers_data = load_data(VOICE_CHAT_MANAGERS_FILE)
    chat_id_str = str(chat_id)
    user_id_str = str(user_id)
    if chat_id_str not in managers_data:
        managers_data[chat_id_str] = []
    
    if user_id_str not in managers_data[chat_id_str]:
        managers_data[chat_id_str].append(user_id_str)
        save_data(VOICE_CHAT_MANAGERS_FILE, managers_data)
        return True
    return False

def remove_voice_chat_manager(chat_id, user_id):
    """Remove a user from voice chat managers."""
    managers_data = load_data(VOICE_CHAT_MANAGERS_FILE)
    chat_id_str = str(chat_id)
    user_id_str = str(user_id)
    if chat_id_str in managers_data and user_id_str in managers_data[chat_id_str]:
        managers_data[chat_id_str].remove(user_id_str)
        save_data(VOICE_CHAT_MANAGERS_FILE, managers_data)
        return True
    return False

def get_all_voice_chat_managers(chat_id):
    """Returns a list of user IDs for all voice chat managers in a chat."""
    managers_data = load_data(VOICE_CHAT_MANAGERS_FILE)
    chat_id_str = str(chat_id)
    return managers_data.get(chat_id_str, [])

BANNED_CHANNELS_FILE = "banned_channels.json"

# ... (rest of the code)

def get_all_muters(chat_id):
    """Returns a list of user IDs for all muters in a chat."""
    muters_data = load_data(MUTERS_FILE)
    chat_id_str = str(chat_id)
    return muters_data.get(chat_id_str, [])

# Banned Channels Functions
def is_channel_banned(chat_id, channel_id):
    """Checks if a channel (sender chat) is banned in a specific chat."""
    banned_data = load_data(BANNED_CHANNELS_FILE)
    chat_id_str = str(chat_id)
    channel_id_str = str(channel_id)
    if chat_id_str in banned_data:
        return channel_id_str in banned_data[chat_id_str]
    return False

def add_banned_channel(chat_id, channel_id):
    """Adds a channel to the banned list for a chat."""
    banned_data = load_data(BANNED_CHANNELS_FILE)
    chat_id_str = str(chat_id)
    channel_id_str = str(channel_id)
    if chat_id_str not in banned_data:
        banned_data[chat_id_str] = []
    
    if channel_id_str not in banned_data[chat_id_str]:
        banned_data[chat_id_str].append(channel_id_str)
        save_data(BANNED_CHANNELS_FILE, banned_data)
        return True
    return False

def remove_banned_channel(chat_id, channel_id):
    """Removes a channel from the banned list for a chat."""
    banned_data = load_data(BANNED_CHANNELS_FILE)
    chat_id_str = str(chat_id)
    channel_id_str = str(channel_id)
    if chat_id_str in banned_data and channel_id_str in banned_data[chat_id_str]:
        banned_data[chat_id_str].remove(channel_id_str)
        save_data(BANNED_CHANNELS_FILE, banned_data)
        return True
    return False
