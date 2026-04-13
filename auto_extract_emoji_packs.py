"""
Auto-Extract ALL Premium Emojis from Account
Gets all installed emoji packs and extracts every emoji
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
mongo_client = MongoClient(MONGO_URI)
db = mongo_client['GROUPHELP']
emojis_collection = db['premium_emojis']

async def extract_all_premium_emoji_packs():
    """Extract all premium emoji packs from account"""
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
        
        logger.info("🔑 Connecting to premium account...")
        
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
        logger.info(f"✅ Connected as: {me.first_name} (@{me.username or 'No username'})")
        logger.info(f"⭐ Premium: {me.premium}")
        logger.info("=" * 60)
        
        # Get ALL installed sticker/emoji sets
        logger.info("📦 Fetching all installed packs...")
        all_stickers = await client(functions.messages.GetAllStickersRequest(hash=0))
        
        logger.info(f"📊 Found {len(all_stickers.sets)} total packs")
        logger.info("=" * 60)
        
        emoji_pack_count = 0
        total_emojis_saved = 0
        
        # Process each pack
        for idx, stickerset in enumerate(all_stickers.sets, 1):
            try:
                # Check if it's a custom emoji pack (not regular stickers)
                # Custom emoji packs have: installed_date attribute or are marked differently
                is_emoji_pack = False
                
                # Method 1: Check emojis attribute (count > 0 and not regular stickers)
                if hasattr(stickerset, 'emojis') and stickerset.emojis:
                    is_emoji_pack = True
                
                # Method 2: Check if it's marked as custom emoji pack
                if hasattr(stickerset, 'custom_emoji') and stickerset.custom_emoji:
                    is_emoji_pack = True
                
                # Method 3: Check by title/name patterns
                if any(keyword in stickerset.title.lower() for keyword in ['emoji', 'emojis']):
                    is_emoji_pack = True
                
                if not is_emoji_pack:
                    continue
                
                emoji_pack_count += 1
                logger.info(f"\n📦 [{idx}/{len(all_stickers.sets)}] Pack: {stickerset.title}")
                logger.info(f"   Short name: {stickerset.short_name}")
                logger.info(f"   Emojis count: {stickerset.count}")
                
                # Get full sticker set with documents
                try:
                    full_set = await client(functions.messages.GetStickerSetRequest(
                        stickerset=types.InputStickerSetID(
                            id=stickerset.id,
                            access_hash=stickerset.access_hash
                        ),
                        hash=0
                    ))
                    
                    logger.info(f"   📊 Retrieved {len(full_set.documents)} emojis")
                    
                    # Extract each emoji
                    for doc in full_set.documents:
                        try:
                            # Get emoji character from attributes
                            emoji_char = None
                            for attr in doc.attributes:
                                if hasattr(attr, 'alt'):
                                    emoji_char = attr.alt
                                    break
                            
                            # Prepare emoji data
                            emoji_data = {
                                'file_id': str(doc.id),
                                'access_hash': str(doc.access_hash),
                                'unique_id': f"{doc.id}_{doc.access_hash}",
                                'emoji_character': emoji_char,
                                'pack_name': stickerset.short_name,
                                'pack_title': stickerset.title,
                                'is_premium': True,
                                'is_animated': doc.mime_type == 'application/x-tgsticker',
                                'is_video': doc.mime_type == 'video/webm',
                                'mime_type': doc.mime_type or 'unknown',
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
                                total_emojis_saved += 1
                                if total_emojis_saved % 10 == 0:
                                    logger.info(f"   💾 Saved {total_emojis_saved} emojis so far...")
                            
                        except Exception as e:
                            logger.error(f"   ❌ Error saving emoji: {e}")
                            continue
                    
                    logger.info(f"   ✅ Pack processed!")
                    
                except Exception as e:
                    logger.error(f"   ❌ Error getting full set: {e}")
                    continue
                
            except Exception as e:
                logger.error(f"❌ Error processing pack {idx}: {e}")
                continue
        
        # Final statistics
        logger.info("\n" + "=" * 60)
        logger.info("🎉 EXTRACTION COMPLETE!")
        logger.info("=" * 60)
        logger.info(f"📦 Total emoji packs found: {emoji_pack_count}")
        logger.info(f"💾 New emojis saved: {total_emojis_saved}")
        
        total_in_db = emojis_collection.count_documents({})
        logger.info(f"🗄️  Total emojis in database: {total_in_db}")
        
        # Show pack breakdown
        packs = emojis_collection.distinct('pack_name')
        logger.info(f"\n📋 Emoji packs in database:")
        for pack in packs:
            count = emojis_collection.count_documents({'pack_name': pack})
            logger.info(f"   • {pack}: {count} emojis")
        
        logger.info("=" * 60)
        
        await client.disconnect()
        
    except ImportError:
        logger.error("❌ Telethon not installed. Run: pip install telethon")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(extract_all_premium_emoji_packs())
