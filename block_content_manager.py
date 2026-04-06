import json
import os
import logging

BLOCK_CONTENT_FILE = "blocked_content.json"

def load_blocked_content():
    if os.path.exists(BLOCK_CONTENT_FILE):
        try:
            with open(BLOCK_CONTENT_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_blocked_content(data):
    with open(BLOCK_CONTENT_FILE, "w") as f:
        json.dump(data, f, indent=4)

def add_blocked_content(chat_id, content_type, content_value):
    """Adds a specific content to the block list for a chat."""
    data = load_blocked_content()
    chat_id_str = str(chat_id)
    
    if chat_id_str not in data:
        data[chat_id_str] = {
            "text": [],
            "media": [] # file_ids
        }
    
    if content_type == "text":
        content_value = content_value.lower().strip()
        if content_value not in data[chat_id_str]["text"]:
            data[chat_id_str]["text"].append(content_value)
            save_blocked_content(data)
            return True
    elif content_type == "media":
        if content_value not in data[chat_id_str]["media"]:
            data[chat_id_str]["media"].append(content_value)
            save_blocked_content(data)
            return True
    return False

def remove_blocked_content(chat_id, content_type, content_value):
    """Removes a specific content from the block list for a chat."""
    data = load_blocked_content()
    chat_id_str = str(chat_id)
    
    if chat_id_str not in data:
        return False
        
    if content_type == "text":
        content_value = content_value.lower().strip()
        if content_value in data[chat_id_str]["text"]:
            data[chat_id_str]["text"].remove(content_value)
            save_blocked_content(data)
            return True
    elif content_type == "media":
        if content_value in data[chat_id_str]["media"]:
            data[chat_id_str]["media"].remove(content_value)
            save_blocked_content(data)
            return True
    return False

def get_blocked_content(chat_id):
    """Returns all blocked content for a chat."""
    data = load_blocked_content()
    return data.get(str(chat_id), {"text": [], "media": []})

def is_content_blocked(chat_id, message):
    """Checks if a message contains blocked content."""
    blocked = get_blocked_content(chat_id)
    
    # Check text
    if message.text or message.caption:
        text = (message.text or message.caption).lower()
        for word in blocked.get("text", []):
            if word in text:
                return True, f"text: {word}"
                
    # Check media (photo, video, animation, document, sticker, audio, voice)
    media_file_id = None
    if message.photo: media_file_id = message.photo[-1].file_id
    elif message.video: media_file_id = message.video.file_id
    elif message.animation: media_file_id = message.animation.file_id
    elif message.document: media_file_id = message.document.file_id
    elif message.sticker: media_file_id = message.sticker.file_id
    elif message.audio: media_file_id = message.audio.file_id
    elif message.voice: media_file_id = message.voice.file_id
    
    if media_file_id and media_file_id in blocked.get("media", []):
        return True, "media"
        
    return False, None
