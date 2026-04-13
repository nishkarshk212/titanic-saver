"""
Extract Premium Emojis from Specific Pack
Extracts all emojis from: https://t.me/addemoji/SpicyEryx_by_TgEmojis_bot
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

async def extract_emoji_pack():
    """Extract emojis from SpicyEryx_by_TgEmojis pack"""
    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        from telethon.tl.functions.messages import GetStickerSetRequest
        from telethon.tl.types import InputStickerSetShortName
        
        # Get credentials
        API_ID = os.getenv('TELEGRAM_API_ID')
        API_HASH = os.getenv('TELEGRAM_API_HASH')
        SESSION_STRING = os.getenv('PREMIUM_SESSION_STRING')
        
        if not all([API_ID, API_HASH, SESSION_STRING]):
            logger.error("❌ Missing credentials in .env")
            return
        
        # Connect to premium account
        client = TelegramClient(
            StringSession(SESSION_STRING),
            int(API_ID),
            API_HASH
        )
        await client.connect()
        
        if not await client.is_user_authorized():
            logger.error("❌ Not authorized")
            return
        
        me = await client.get_me()
        logger.info(f"✅ Connected as: {me.first_name} (Premium: {me.premium})")
        
        # Get the sticker set
        pack_name = "SpicyEryx_by_TgEmojis"
        logger.info(f"📦 Extracting emoji pack: {pack_name}")
        
        try:
            # Get sticker set by short name
            sticker_set = await client(GetStickerSetRequest(
                stickerset=InputStickerSetShortName(pack_name),
                hash=0
            ))
            
            logger.info(f"📋 Found pack: {sticker_set.set.title}")
            logger.info(f"📊 Total emojis: {len(sticker_set.documents)}")
            
            # Extract each emoji
            saved_count = 0
            for doc in sticker_set.documents:
                try:
                    # Get emoji from attributes
                    emoji_char = None
                    for attr in doc.attributes:
                        if hasattr(attr, 'alt'):
                            emoji_char = attr.alt
                            break
                    
                    emoji_data = {
                        'file_id': str(doc.id),
                        'access_hash': str(doc.access_hash),
                        'unique_id': f"{doc.id}_{doc.access_hash}",
                        'emoji_character': emoji_char or '🎭',
                        'pack_name': pack_name,
                        'pack_title': sticker_set.set.title,
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
                    
                    # Check if exists
                    existing = emojis_collection.find_one({'unique_id': emoji_data['unique_id']})
                    if not existing:
                        emojis_collection.insert_one(emoji_data)
                        saved_count += 1
                        logger.info(f"💾 Saved emoji #{saved_count}: {emoji_char} (ID: {doc.id})")
                    else:
                        logger.info(f"⏭️  Already exists: {emoji_char}")
                        
                except Exception as e:
                    logger.error(f"❌ Error saving emoji: {e}")
                    continue
            
            logger.info("=" * 60)
            logger.info(f"✅ Extraction Complete!")
            logger.info(f"📊 Saved: {saved_count} new emojis")
            logger.info(f"📦 Pack: {sticker_set.set.title}")
            logger.info(f"💾 Total in database: {emojis_collection.count_documents({})}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"❌ Error getting sticker set: {e}")
            logger.info("\nTrying alternative method...")
            
            # Try accessing via link
            try:
                # Get entity from link
                entity = await client.get_entity('SpicyEryx_by_TgEmojis')
                logger.info(f"Found entity: {entity}")
            except Exception as e2:
                logger.error(f"❌ Alternative method also failed: {e2}")
        
        await client.disconnect()
        
    except ImportError:
        logger.error("❌ Telethon not installed")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(extract_emoji_pack())
