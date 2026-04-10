"""
Migration script to transfer data from JSON files to MongoDB.
Run this script once to migrate all existing data.
"""

import json
import os
import logging
from database import connect_to_mongodb, initialize_collections, get_collection, COLLECTIONS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def migrate_users():
    """Migrate user_cache.json to MongoDB."""
    users_file = "user_cache.json"
    if not os.path.exists(users_file):
        logging.info(f"⏭️  {users_file} not found, skipping...")
        return False
    
    logging.info(f"📦 Migrating {users_file}...")
    try:
        with open(users_file, "r") as f:
            users_data = json.load(f)
        
        users_col = get_collection(COLLECTIONS["users"])
        if users_col is None:
            logging.error("MongoDB not connected!")
            return False
        
        migrated_count = 0
        seen_ids = set()
        
        for key, user_info in users_data.items():
            user_id = user_info.get("id")
            if not user_id or user_id in seen_ids:
                continue
            
            seen_ids.add(user_id)
            
            # Prepare document
            doc = {
                "id": user_id,
                "name": user_info.get("name", ""),
                "username": user_info.get("username"),
                "joined_date": user_info.get("joined_date", "Unknown"),
                "msg_count": user_info.get("msg_count", 0)
            }
            
            # Insert or update
            users_col.update_one(
                {"id": user_id},
                {"$set": doc},
                upsert=True
            )
            migrated_count += 1
        
        logging.info(f"✅ Migrated {migrated_count} users to MongoDB")
        return True
    except Exception as e:
        logging.error(f"❌ Error migrating users: {e}")
        return False

def migrate_settings():
    """Migrate group_settings.json to MongoDB."""
    settings_file = "group_settings.json"
    if not os.path.exists(settings_file):
        logging.info(f"⏭️  {settings_file} not found, skipping...")
        return False
    
    logging.info(f"📦 Migrating {settings_file}...")
    try:
        with open(settings_file, "r") as f:
            settings_data = json.load(f)
        
        settings_col = get_collection(COLLECTIONS["settings"])
        if settings_col is None:
            logging.error("MongoDB not connected!")
            return False
        
        migrated_count = 0
        
        for chat_id_str, settings in settings_data.items():
            settings_col.update_one(
                {"chat_id": chat_id_str},
                {"$set": {"settings": settings}},
                upsert=True
            )
            migrated_count += 1
        
        logging.info(f"✅ Migrated {migrated_count} chat settings to MongoDB")
        return True
    except Exception as e:
        logging.error(f"❌ Error migrating settings: {e}")
        return False

def migrate_warns():
    """Migrate group_warns.json to MongoDB."""
    warns_file = "group_warns.json"
    if not os.path.exists(warns_file):
        logging.info(f"⏭️  {warns_file} not found, skipping...")
        return False
    
    logging.info(f"📦 Migrating {warns_file}...")
    try:
        with open(warns_file, "r") as f:
            warns_data = json.load(f)
        
        warns_col = get_collection(COLLECTIONS["warns"])
        if warns_col is None:
            logging.error("MongoDB not connected!")
            return False
        
        migrated_count = 0
        
        for chat_id_str, users in warns_data.items():
            for user_id_str, warn_count in users.items():
                warns_col.update_one(
                    {"chat_id": chat_id_str, "user_id": user_id_str},
                    {"$set": {"warn_count": warn_count}},
                    upsert=True
                )
                migrated_count += 1
        
        logging.info(f"✅ Migrated {migrated_count} warn records to MongoDB")
        return True
    except Exception as e:
        logging.error(f"❌ Error migrating warns: {e}")
        return False

def migrate_muters():
    """Migrate group_muters.json to MongoDB."""
    muters_file = "group_muters.json"
    if not os.path.exists(muters_file):
        logging.info(f"⏭️  {muters_file} not found, skipping...")
        return False
    
    logging.info(f"📦 Migrating {muters_file}...")
    try:
        with open(muters_file, "r") as f:
            muters_data = json.load(f)
        
        muters_col = get_collection(COLLECTIONS["muters"])
        if muters_col is None:
            logging.error("MongoDB not connected!")
            return False
        
        migrated_count = 0
        
        for chat_id_str, user_list in muters_data.items():
            for user_id_str in user_list:
                muters_col.update_one(
                    {"chat_id": chat_id_str, "user_id": user_id_str},
                    {"$setOnInsert": {"chat_id": chat_id_str, "user_id": user_id_str}},
                    upsert=True
                )
                migrated_count += 1
        
        logging.info(f"✅ Migrated {migrated_count} muter records to MongoDB")
        return True
    except Exception as e:
        logging.error(f"❌ Error migrating muters: {e}")
        return False

def migrate_voice_chat_managers():
    """Migrate voice_chat_managers.json to MongoDB."""
    vcm_file = "voice_chat_managers.json"
    if not os.path.exists(vcm_file):
        logging.info(f"⏭️  {vcm_file} not found, skipping...")
        return False
    
    logging.info(f"📦 Migrating {vcm_file}...")
    try:
        with open(vcm_file, "r") as f:
            vcm_data = json.load(f)
        
        vcm_col = get_collection(COLLECTIONS["voice_chat_managers"])
        if vcm_col is None:
            logging.error("MongoDB not connected!")
            return False
        
        migrated_count = 0
        
        for chat_id_str, user_list in vcm_data.items():
            for user_id_str in user_list:
                vcm_col.update_one(
                    {"chat_id": chat_id_str, "user_id": user_id_str},
                    {"$setOnInsert": {"chat_id": chat_id_str, "user_id": user_id_str}},
                    upsert=True
                )
                migrated_count += 1
        
        logging.info(f"✅ Migrated {migrated_count} voice chat manager records to MongoDB")
        return True
    except Exception as e:
        logging.error(f"❌ Error migrating voice chat managers: {e}")
        return False

def migrate_banned_channels():
    """Migrate banned_channels.json to MongoDB."""
    banned_file = "banned_channels.json"
    if not os.path.exists(banned_file):
        logging.info(f"⏭️  {banned_file} not found, skipping...")
        return False
    
    logging.info(f"📦 Migrating {banned_file}...")
    try:
        with open(banned_file, "r") as f:
            banned_data = json.load(f)
        
        banned_col = get_collection(COLLECTIONS["banned_channels"])
        if banned_col is None:
            logging.error("MongoDB not connected!")
            return False
        
        migrated_count = 0
        
        for chat_id_str, channel_list in banned_data.items():
            for channel_id_str in channel_list:
                banned_col.update_one(
                    {"chat_id": chat_id_str, "channel_id": channel_id_str},
                    {"$setOnInsert": {"chat_id": chat_id_str, "channel_id": channel_id_str}},
                    upsert=True
                )
                migrated_count += 1
        
        logging.info(f"✅ Migrated {migrated_count} banned channel records to MongoDB")
        return True
    except Exception as e:
        logging.error(f"❌ Error migrating banned channels: {e}")
        return False

def migrate_blocked_content():
    """Migrate blocked_content.json to MongoDB."""
    blocked_file = "blocked_content.json"
    if not os.path.exists(blocked_file):
        logging.info(f"⏭️  {blocked_file} not found, skipping...")
        return False
    
    logging.info(f"📦 Migrating {blocked_file}...")
    try:
        with open(blocked_file, "r") as f:
            blocked_data = json.load(f)
        
        blocked_col = get_collection(COLLECTIONS["blocked_content"])
        if blocked_col is None:
            logging.error("MongoDB not connected!")
            return False
        
        migrated_count = 0
        
        for chat_id_str, content in blocked_data.items():
            blocked_col.update_one(
                {"chat_id": chat_id_str},
                {"$set": {
                    "text": content.get("text", []),
                    "media": content.get("media", [])
                }},
                upsert=True
            )
            migrated_count += 1
        
        logging.info(f"✅ Migrated {migrated_count} blocked content records to MongoDB")
        return True
    except Exception as e:
        logging.error(f"❌ Error migrating blocked content: {e}")
        return False

def migrate_filters():
    """Migrate group_filters.json to MongoDB."""
    filters_file = "group_filters.json"
    if not os.path.exists(filters_file):
        logging.info(f"⏭️  {filters_file} not found, skipping...")
        return False
    
    logging.info(f"📦 Migrating {filters_file}...")
    try:
        with open(filters_file, "r") as f:
            filters_data = json.load(f)
        
        filters_col = get_collection(COLLECTIONS["filters"])
        if filters_col is None:
            logging.error("MongoDB not connected!")
            return False
        
        migrated_count = 0
        
        for chat_id_str, triggers in filters_data.items():
            for trigger, content in triggers.items():
                filters_col.update_one(
                    {"chat_id": chat_id_str, "trigger": trigger},
                    {"$set": {"content": content}},
                    upsert=True
                )
                migrated_count += 1
        
        logging.info(f"✅ Migrated {migrated_count} filter records to MongoDB")
        return True
    except Exception as e:
        logging.error(f"❌ Error migrating filters: {e}")
        return False

def main():
    """Run all migrations."""
    print("=" * 60)
    print("🚀 MongoDB Migration Script")
    print("=" * 60)
    print()
    
    # Connect to MongoDB
    print("Connecting to MongoDB...")
    if not connect_to_mongodb():
        print("❌ Failed to connect to MongoDB. Please check your connection string.")
        return
    
    # Initialize collections
    print("Initializing collections...")
    initialize_collections()
    print()
    
    # Run migrations
    migrations = [
        ("Users", migrate_users),
        ("Settings", migrate_settings),
        ("Warns", migrate_warns),
        ("Muters", migrate_muters),
        ("Voice Chat Managers", migrate_voice_chat_managers),
        ("Banned Channels", migrate_banned_channels),
        ("Blocked Content", migrate_blocked_content),
        ("Filters", migrate_filters),
    ]
    
    success_count = 0
    for name, migration_func in migrations:
        try:
            if migration_func():
                success_count += 1
        except Exception as e:
            logging.error(f"❌ Migration failed for {name}: {e}")
    
    print()
    print("=" * 60)
    print(f"✅ Migration completed! {success_count}/{len(migrations)} migrations successful")
    print("=" * 60)
    print()
    print("📝 Note: Your JSON files are still intact. You can delete them")
    print("   after verifying that the migration was successful.")
    print()

if __name__ == "__main__":
    main()
