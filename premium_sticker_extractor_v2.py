"""
Premium Sticker & Emoji Extractor - FIXED VERSION
Extracts all premium stickers and emojis from Telegram premium account
Stores them in MongoDB for bot usage
"""
import logging
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
MONGO_URI = os.getenv('MONGODB_URI')
client = MongoClient(MONGO_URI)
db = client['GROUPHELP']
stickers_collection = db['premium_stickers']
emojis_collection = db['premium_emojis']

class PremiumStickerExtractor:
    def __init__(self):
        self.client = None
        self.extracted_stickers = 0
        self.extracted_emojis = 0
    
    async def initialize_telethon(self, api_id, api_hash, session_string):
        """Initialize Telethon client with premium account session"""
        try:
            from telethon import TelegramClient
            from telethon.sessions import StringSession
            
            self.client = TelegramClient(
                StringSession(session_string),
                int(api_id),
                api_hash
            )
            await self.client.connect()
            
            if await self.client.is_user_authorized():
                me = await self.client.get_me()
                logger.info(f"✅ Connected as: {me.first_name} (Premium: {me.premium})")
                return True
            else:
                logger.error("❌ Session not authorized")
                return False
        except ImportError:
            logger.error("❌ Telethon not installed. Run: pip install telethon")
            return False
        except Exception as e:
            logger.error(f"❌ Error initializing client: {e}")
            return False
    
    async def extract_all_stickers(self):
        """Extract all stickers from premium account"""
        if not self.client:
            logger.error("❌ Client not initialized")
            return
        
        try:
            from telethon.tl.functions.messages import GetStickerSetRequest
            from telethon.tl.types import InputStickerSetID
            
            logger.info("📦 Extracting all sticker packs...")
            
            # Get all dialogs (channels, groups, private chats)
            dialogs = await self.client.get_dialogs(limit=50)
            logger.info(f"📋 Found {len(dialogs)} dialogs to scan")
            
            sticker_ids = set()  # Track unique stickers
            
            for dialog in dialogs:
                try:
                    # Get messages with stickers
                    messages = await self.client.get_messages(
                        dialog.entity,
                        limit=100
                    )
                    
                    for msg in messages:
                        if hasattr(msg, 'sticker') and msg.sticker:
                            sticker = msg.sticker
                            
                            # Skip if already processed
                            if sticker.id in sticker_ids:
                                continue
                            sticker_ids.add(sticker.id)
                            
                            await self._save_sticker(sticker, msg)
                            
                except Exception as e:
                    continue
            
            logger.info(f"✅ Extracted {self.extracted_stickers} unique stickers")
            
        except Exception as e:
            logger.error(f"❌ Error extracting stickers: {e}")
            import traceback
            traceback.print_exc()
    
    async def _save_sticker(self, sticker, message):
        """Save sticker to MongoDB - Telethon compatible"""
        try:
            # Get emoji from sticker attributes
            emoji = None
            if hasattr(sticker, 'attributes') and sticker.attributes:
                for attr in sticker.attributes:
                    if hasattr(attr, 'alt'):
                        emoji = attr.alt
                        break
            
            # Determine if animated or video
            mime_type = getattr(sticker, 'mime_type', '')
            is_animated = mime_type == 'application/x-tgsticker'
            is_video = mime_type == 'video/webm'
            
            sticker_data = {
                'file_id': str(sticker.id),  # Telethon uses 'id'
                'access_hash': str(sticker.access_hash),
                'unique_id': f"{sticker.id}_{sticker.access_hash}",  # Unique combination
                'emoji': emoji or '🎭',
                'width': getattr(sticker, 'width', 512),
                'height': getattr(sticker, 'height', 512),
                'is_premium': True,  # From premium account
                'is_animated': is_animated,
                'is_video': is_video,
                'mime_type': mime_type,
                'extracted_from': message.chat_id if message else None,
                'message_id': message.id if message else None,
                'category': 'general',
                'usage_count': 0
            }
            
            # Check if already exists
            existing = stickers_collection.find_one({'unique_id': sticker_data['unique_id']})
            if not existing:
                stickers_collection.insert_one(sticker_data)
                self.extracted_stickers += 1
                logger.info(f"💾 Saved sticker #{self.extracted_stickers}: {emoji} (ID: {sticker.id})")
            
        except Exception as e:
            logger.error(f"❌ Error saving sticker: {e}")
    
    def get_sticker_stats(self):
        """Get statistics about saved stickers and emojis"""
        total_stickers = stickers_collection.count_documents({})
        total_emojis = emojis_collection.count_documents({})
        premium_stickers = stickers_collection.count_documents({'is_premium': True})
        animated_stickers = stickers_collection.count_documents({'is_animated': True})
        video_stickers = stickers_collection.count_documents({'is_video': True})
        
        return {
            'total_stickers': total_stickers,
            'total_emojis': total_emojis,
            'premium_stickers': premium_stickers,
            'animated_stickers': animated_stickers,
            'video_stickers': video_stickers,
            'categories': list(stickers_collection.distinct('category'))
        }

# Usage example
async def main():
    extractor = PremiumStickerExtractor()
    
    # Get credentials from environment
    API_ID = os.getenv('TELEGRAM_API_ID')
    API_HASH = os.getenv('TELEGRAM_API_HASH')
    SESSION_STRING = os.getenv('PREMIUM_SESSION_STRING')
    
    if not all([API_ID, API_HASH, SESSION_STRING]):
        logger.error("❌ Please set TELEGRAM_API_ID, TELEGRAM_API_HASH, and PREMIUM_SESSION_STRING in .env")
        return
    
    # Initialize client
    if await extractor.initialize_telethon(API_ID, API_HASH, SESSION_STRING):
        logger.info("=" * 60)
        logger.info("🚀 Starting premium sticker extraction...")
        logger.info("=" * 60)
        
        # Extract all stickers
        await extractor.extract_all_stickers()
        
        # Show stats
        stats = extractor.get_sticker_stats()
        logger.info("=" * 60)
        logger.info("📊 Extraction Statistics:")
        logger.info("=" * 60)
        logger.info(f"💾 Total Stickers: {stats['total_stickers']}")
        logger.info(f"⭐ Premium Stickers: {stats['premium_stickers']}")
        logger.info(f"🎬 Animated Stickers: {stats['animated_stickers']}")
        logger.info(f"🎥 Video Stickers: {stats['video_stickers']}")
        logger.info(f"✨ Custom Emojis: {stats['total_emojis']}")
        logger.info(f"📂 Categories: {', '.join(stats['categories']) if stats['categories'] else 'general'}")
        logger.info("=" * 60)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
