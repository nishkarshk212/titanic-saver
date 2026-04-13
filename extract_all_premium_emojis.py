"""
Extract ALL Premium Emoji Packs from Premium Account
Scans all dialogs and extracts custom emojis
"""
import logging
import asyncio
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# MongoDB connection
MONGO_URI = os.getenv('MONGODB_URI', 'mongodb+srv://mybotpanda_db_user:hx0n5AI90lFGyl93@grouphelp.puxyti8.mongodb.net/?appName=GROUPHELP')
client = MongoClient(MONGO_URI)
db = client['GROUPHELP']
emojis_collection = db['premium_emojis']

async def extract_all_premium_emojis():
    """Extract all premium emojis from account"""
    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        from telethon.tl import functions, types
        
        # Get credentials
        API_ID = os.getenv('TELEGRAM_API_ID')
        API_HASH = os.getenv('TELEGRAM_API_HASH')
        SESSION_STRING = os.getenv('PREMIUM_SESSION_STRING')
        
        if not all([API_ID, API_HASH, SESSION_STRING]):
            logger.error("❌ Missing credentials in .env")
            return
        
        # Connect to premium account
        tg_client = TelegramClient(
            StringSession(SESSION_STRING),
            int(API_ID),
            API_HASH
        )
        await tg_client.connect()
        
        if not await tg_client.is_user_authorized():
            logger.error("❌ Not authorized")
            return
        
        me = await tg_client.get_me()
        logger.info(f"✅ Connected as: {me.first_name} (Premium: {me.premium})")
        logger.info("=" * 60)
        logger.info("🔍 Scanning for premium emojis...")
        logger.info("=" * 60)
        
        # Get all dialogs
        dialogs = await tg_client.get_dialogs(limit=50)
        logger.info(f"📋 Scanning {len(dialogs)} dialogs...")
        
        emoji_ids = set()
        saved_count = 0
        
        for dialog in dialogs:
            try:
                # Get messages from dialog
                messages = await tg_client.get_messages(
                    dialog.entity,
                    limit=50
                )
                
                for msg in messages:
                    # Check for custom emoji entities
                    if msg.entities:
                        for entity in msg.entities:
                            if entity.type == 'custom_emoji':
                                emoji_id = entity.custom_emoji_id
                                
                                # Skip if already processed
                                if emoji_id in emoji_ids:
                                    continue
                                emoji_ids.add(emoji_id)
                                
                                # Save to MongoDB
                                emoji_data = {
                                    'file_id': str(emoji_id),
                                    'access_hash': str(emoji_id),
                                    'unique_id': str(emoji_id),
                                    'emoji_character': None,  # Will be added manually
                                    'pack_name': 'extracted',
                                    'pack_title': 'Extracted from dialogs',
                                    'is_premium': True,
                                    'is_animated': True,
                                    'is_video': False,
                                    'category': 'premium_pack',
                                    'saved_by': me.id,
                                    'extracted_from': dialog.entity.id,
                                    'message_id': msg.id,
                                    'usage_count': 0
                                }
                                
                                # Check if exists
                                existing = emojis_collection.find_one({'unique_id': str(emoji_id)})
                                if not existing:
                                    emojis_collection.insert_one(emoji_data)
                                    saved_count += 1
                                    logger.info(f"💾 Saved emoji #{saved_count}: ID {emoji_id}")
                                
            except Exception as e:
                continue
        
        logger.info("=" * 60)
        logger.info("✅ Extraction Complete!")
        logger.info("=" * 60)
        logger.info(f"📊 Unique emojis found: {len(emoji_ids)}")
        logger.info(f"💾 New emojis saved: {saved_count}")
        logger.info(f"🗄️  Total in database: {emojis_collection.count_documents({})}")
        logger.info("=" * 60)
        
        # Also try to get emoji packs directly
        logger.info("\n🔍 Trying to get sticker sets...")
        try:
            # Get all installed sticker sets
            all_stickers = await tg_client(functions.messages.GetAllStickersRequest(hash=0))
            
            for stickerset in all_stickers.sets:
                if stickerset.emojis:  # It's an emoji pack
                    logger.info(f"📦 Found emoji pack: {stickerset.title} ({stickerset.short_name})")
                    
                    try:
                        # Get full set
                        full_set = await tg_client(functions.messages.GetStickerSetRequest(
                            stickerset=types.InputStickerSetID(
                                id=stickerset.id,
                                access_hash=stickerset.access_hash
                            ),
                            hash=0
                        ))
                        
                        logger.info(f"   📊 Emojis in pack: {len(full_set.documents)}")
                        
                        # Save each emoji
                        for doc in full_set.documents:
                            emoji_data = {
                                'file_id': str(doc.id),
                                'access_hash': str(doc.access_hash),
                                'unique_id': f"{doc.id}_{doc.access_hash}",
                                'emoji_character': None,
                                'pack_name': stickerset.short_name,
                                'pack_title': stickerset.title,
                                'is_premium': True,
                                'is_animated': doc.mime_type == 'application/x-tgsticker',
                                'is_video': doc.mime_type == 'video/webm',
                                'mime_type': doc.mime_type,
                                'width': getattr(doc, 'width', 100),
                                'height': getattr(doc, 'height', 100),
                                'category': 'premium_pack',
                                'saved_by': me.id,
                                'usage_count': 0
                            }
                            
                            existing = emojis_collection.find_one({'unique_id': emoji_data['unique_id']})
                            if not existing:
                                emojis_collection.insert_one(emoji_data)
                                saved_count += 1
                                logger.info(f"   💾 Saved: {doc.id}")
                        
                    except Exception as e:
                        logger.error(f"   ❌ Error getting pack: {e}")
                        continue
            
            logger.info(f"\n🎉 Total emojis saved: {saved_count}")
            
        except Exception as e:
            logger.error(f"❌ Error getting sticker sets: {e}")
        
        await tg_client.disconnect()
        
    except ImportError:
        logger.error("❌ Telethon not installed")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(extract_all_premium_emojis())
