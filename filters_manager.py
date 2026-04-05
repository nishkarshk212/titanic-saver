import json
import os

FILTERS_FILE = "group_filters.json"

def load_filters():
    if os.path.exists(FILTERS_FILE):
        try:
            with open(FILTERS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_filters(filters_data):
    with open(FILTERS_FILE, "w") as f:
        json.dump(filters_data, f, indent=4)

def get_chat_filters(chat_id):
    filters_data = load_filters()
    return filters_data.get(str(chat_id), {})

def add_chat_filter(chat_id, trigger, content):
    filters_data = load_filters()
    chat_id_str = str(chat_id)
    if chat_id_str not in filters_data:
        filters_data[chat_id_str] = {}
    
    filters_data[chat_id_str][trigger.lower()] = content
    save_filters(filters_data)

def remove_chat_filter(chat_id, trigger):
    filters_data = load_filters()
    chat_id_str = str(chat_id)
    if chat_id_str in filters_data and trigger.lower() in filters_data[chat_id_str]:
        del filters_data[chat_id_str][trigger.lower()]
        save_filters(filters_data)
        return True
    return False

def remove_all_chat_filters(chat_id):
    filters_data = load_filters()
    chat_id_str = str(chat_id)
    if chat_id_str in filters_data:
        filters_data[chat_id_str] = {}
        save_filters(filters_data)
        return True
    return False
