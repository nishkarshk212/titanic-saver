import json
import os

SETTINGS_FILE = "group_settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)

def get_chat_settings(chat_id):
    settings = load_settings()
    chat_id_str = str(chat_id)
    if chat_id_str not in settings:
        settings[chat_id_str] = {
            "welcome_enabled": True,
            "welcome_media_enabled": True,
            "welcome_button_enabled": True,
            "welcome_rejoin_enabled": True,
            "welcome_text": "Welcome {NAME} to the group!",
            "welcome_media": None,
            "welcome_button_text": "Join Channel",
            "welcome_button_url": "https://t.me/yourchannel",
            "goodbye_enabled": True,
            "goodbye_media_enabled": True,
            "goodbye_button_enabled": True,
            "goodbye_text": "Goodbye {NAME}, we will miss you!",
            "goodbye_media": None,
            "goodbye_button_text": "Visit Website",
            "goodbye_button_url": "https://example.com",
            "clean_service_enabled": True,
            "clean_join": True,
            "clean_left": True,
            "clean_video_chat_started": True,
            "clean_video_chat_ended": True,
            "clean_video_chat_invited": True,
            "clean_video_chat_scheduled": True,
            "auto_delete_enabled": False,
            "auto_delete_time": 60,
            "warn_limit": 3,
            "warn_penalty": "ban", # ban, mute, kick
            "command_deletion": False
        }
        save_settings(settings)
    return settings[chat_id_str]

def update_chat_setting(chat_id, key, value):
    settings = load_settings()
    chat_id_str = str(chat_id)
    if chat_id_str not in settings:
        get_chat_settings(chat_id)
        settings = load_settings()
    
    settings[chat_id_str][key] = value
    save_settings(settings)
