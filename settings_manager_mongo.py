import logging
import datetime
from database import get_collection, COLLECTIONS

DEFAULT_CHAT_SETTINGS = {
    "welcome_enabled": True,
    "welcome_media_enabled": True,
    "welcome_button_enabled": True,
    "welcome_rejoin_enabled": True,
    "welcome_text": "Welcome {NAME} to the group!",
    "welcome_media": None,
    "welcome_media_type": "photo",
    "welcome_delete_time": 60,
    "welcome_buttons": [],
    "welcome_button_text": "Join Channel",
    "welcome_button_url": None,
    "clean_service_enabled": True,
    "clean_join": True,
    "clean_left": True,
    "clean_video_chat_started": True,
    "clean_video_chat_ended": True,
    "clean_video_chat_invited": True,
    "clean_video_chat_scheduled": True,
    "clean_pinned_message": True,
    "auto_delete_enabled": False,
    "auto_delete_time": 60,
    "warn_limit": 3,
    "warn_penalty": "ban",
    "block_warn_limit": 3,
    "block_warn_penalty": "warn",
    "msg_length_limit": 0, # 0 means disabled
    "command_deletion": False,
    "command_access": "all",
    "bot_protection_enabled": False,
    "link_spam_protection_enabled": False,
    "forward_protection_enabled": False,
    # Language filter settings
    "language_filter_enabled": False,
    "allowed_languages": ["en", "hi", "hinglish"]
}

def get_chat_settings(chat_id):
    """Get chat settings from MongoDB."""
    try:
        settings_col = get_collection(COLLECTIONS["settings"])
        if settings_col is None:
            logging.error("MongoDB not connected - returning default settings")
            return DEFAULT_CHAT_SETTINGS.copy()
        
        chat_id_str = str(chat_id)
        settings_doc = settings_col.find_one({"chat_id": chat_id_str})
        
        if settings_doc:
            # Merge with defaults to ensure all keys exist
            current_settings = settings_doc.get("settings", {})
            for key, default_value in DEFAULT_CHAT_SETTINGS.items():
                if key not in current_settings:
                    current_settings[key] = default_value
            
            # Update the document with any new defaults
            settings_col.update_one(
                {"chat_id": chat_id_str},
                {"$set": {"settings": current_settings, "updated_at": datetime.datetime.now()}}
            )
            
            return current_settings
        else:
            # Create new settings with defaults
            new_settings = DEFAULT_CHAT_SETTINGS.copy()
            settings_col.insert_one({
                "chat_id": chat_id_str,
                "settings": new_settings,
                "created_at": datetime.datetime.now(),
                "updated_at": datetime.datetime.now()
            })
            return new_settings
    except Exception as e:
        logging.error(f"Error getting chat settings: {e}")
        return DEFAULT_CHAT_SETTINGS.copy()

def update_chat_setting(chat_id, key, value):
    """Update a specific chat setting in MongoDB."""
    try:
        settings_col = get_collection(COLLECTIONS["settings"])
        if settings_col is None:
            logging.error("MongoDB not connected - cannot update setting")
            return False
        
        chat_id_str = str(chat_id)
        
        # Ensure the document exists
        settings_doc = settings_col.find_one({"chat_id": chat_id_str})
        if not settings_doc:
            # Create the document first
            settings_col.insert_one({
                "chat_id": chat_id_str,
                "settings": DEFAULT_CHAT_SETTINGS.copy(),
                "created_at": datetime.datetime.now(),
                "updated_at": datetime.datetime.now()
            })
        
        # Update the specific setting
        result = settings_col.update_one(
            {"chat_id": chat_id_str},
            {
                "$set": {
                    f"settings.{key}": value,
                    "updated_at": datetime.datetime.now()
                }
            }
        )
        
        return result.modified_count > 0 or result.upserted_id is not None
    except Exception as e:
        logging.error(f"Error updating chat setting: {e}")
        return False

def delete_chat_settings(chat_id):
    """Delete all settings for a chat."""
    try:
        settings_col = get_collection(COLLECTIONS["settings"])
        if settings_col is None:
            return False
        
        chat_id_str = str(chat_id)
        result = settings_col.delete_one({"chat_id": chat_id_str})
        return result.deleted_count > 0
    except Exception as e:
        logging.error(f"Error deleting chat settings: {e}")
        return False

def get_all_chat_settings():
    """Get all chat settings (useful for admin functions)."""
    try:
        settings_col = get_collection(COLLECTIONS["settings"])
        if settings_col is None:
            return {}
        
        all_settings = {}
        cursor = settings_col.find({})
        
        for doc in cursor:
            all_settings[doc["chat_id"]] = doc.get("settings", {})
        
        return all_settings
    except Exception as e:
        logging.error(f"Error getting all chat settings: {e}")
        return {}
