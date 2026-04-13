"""
Extract SpicyEryx Emoji Pack Directly
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

MONGO_URI = os.getenv('MONGODB_URI', 'mongodb+srv://mybotpanda_db_user:hx0n5AI90lFGyl93@grouphelp.puxyti8.mongodb.net/?appName=GROUPHELP')
mongo_client = MongoClient(MONGO_URI)
db = mongo_client['GROUPHELP']
emojis_collection = db['premium_emojis']

async def extract_spicyeryx_pack():
    """Extract SpicyEryx emoji pack directly"""
    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        from telethon.tl import functions, types
        
        API_ID = os.getenv('TELEGRAM_API_ID')
        API_HASH = os.getenv('TELEGRAM_API_HASH')
        SESSION_STRING = os.getenv('PREMIUM_SESSION_STRING')
        
        client = TelegramClient(
            StringSession(SESSION_STRING),
            int(API_ID),
            API_HASH
        )
        await client.connect()
        
        if await client.is_user_authorized():
            me = await client.get_me()
            logger.info(f"✅ Connected as: {me.first_name} (Premium: {me.premium})")
            logger.info("=" * 60)
            
            # Try to get the SpicyEryx pack directly
            pack_names = [
                "SpicyEryx_by_TgEmojis",
                "SpicyEryx",
            ]
            
            for pack_name in pack_names:
                try:
                    logger.info(f"🔍 Trying pack: {pack_name}")
                    
                    # Get sticker set by short name
                    stickerset = await client(functions.messages.GetStickerSetRequest(
                        stickerset=types.InputStickerSetShortName(pack_name),
                        hash=0
                    ))
                    
                    logger.info(f"✅ Found pack: {stickerset.set.title}")
                    logger.info(f"📊 Total emojis: {stickerset.set.count}")
                    logger.info(f"📦 Documents: {len(stickerset.documents)}")
                    logger.info("=" * 60)
                    
                    # Extract all emojis
                    saved_count = 0
                    for idx, doc in enumerate(stickerset.documents, 1):
                        try:
                            # Get emoji character
                            emoji_char = None
                            for attr in doc.attributes:
                                if hasattr(attr, 'alt'):
                                    emoji_char = attr.alt
                                    break
                            
                            emoji_data = {
                                'file_id': str(doc.id),
                                'access_hash': str(doc.access_hash),
                                'unique_id': f"{doc.id}_{doc.access_hash}",
                                'emoji_character': emoji_char,
                                'pack_name': pack_name,
                                'pack_title': stickerset.set.title,
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
                                saved_count += 1
                                logger.info(f"[{idx}/{len(stickerset.documents)}] 💾 Saved: {emoji_char or 'N/A'} (ID: {doc.id})")
                            else:
                                logger.info(f"[{idx}/{len(stickerset.documents)}] ⏭️  Exists: {emoji_char or 'N/A'}")
                            
                        except Exception as e:
                            logger.error(f"❌ Error saving emoji {idx}: {e}")
                            continue
                    
                    logger.info("=" * 60)
                    logger.info(f"🎉 EXTRACTION COMPLETE!")
                    logger.info(f"💾 New emojis saved: {saved_count}")
                    logger.info(f"🗄️  Total in database: {emojis_collection.count_documents({})}")
                    logger.info("=" * 60)
                    
                    await client.disconnect()
                    return
                    
                except Exception as e:
                    logger.warning(f"❌ Pack '{pack_name}' not found: {e}")
                    continue
            
            logger.error("❌ Could not find SpicyEryx pack!")
            logger.info("\n💡 Alternative approaches:")
            logger.info("1. Make sure you added the pack in Telegram")
            logger.info("2. Try sending an emoji from the pack to @Stickers bot")
            logger.info("3. Check the exact pack name from Telegram")
            
            await client.disconnect()
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(extract_spicyeryx_pack())
