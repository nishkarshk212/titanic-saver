"""
Premium Sticker & Emoji Extractor
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
                api_id,
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
    
    async def extract_all_sticker_packs(self):
        """Extract all sticker packs from premium account"""
        if not self.client:
            logger.error("❌ Client not initialized")
            return
        
        try:
            logger.info("📦 Extracting all sticker packs...")
            
            # Get all dialogs (channels, groups, private chats)
            dialogs = await self.client.get_dialogs()
            
            for dialog in dialogs:
                try:
                    messages = await self.client.get_messages(
                        dialog.entity,
                        limit=100
                    )
                    
                    for msg in messages:
                        if msg.sticker:
                            await self._save_sticker(msg.sticker, msg)
                            
                except Exception as e:
                    continue
            
            logger.info(f"✅ Extracted {self.extracted_stickers} stickers")
            
        except Exception as e:
            logger.error(f"❌ Error extracting stickers: {e}")
    
    async def extract_premium_emojis(self):
        """Extract all premium custom emojis"""
        if not self.client:
            logger.error("❌ Client not initialized")
            return
        
        try:
            logger.info("✨ Extracting premium emojis...")
            
            # Get all available emoji sets
            all_emojis = await self.client(functions.messages.GetCustomEmojiDocumentsRequest(
                # Premium emoji IDs will be extracted from messages
            ))
            
            for emoji in all_emojis:
                await self._save_emoji(emoji)
            
            logger.info(f"✅ Extracted {self.extracted_emojis} emojis")
            
        except Exception as e:
            logger.error(f"❌ Error extracting emojis: {e}")
    
    async def _save_sticker(self, sticker, message):
        """Save sticker to MongoDB"""
        try:
            sticker_data = {
                'file_id': sticker.file_id,
                'unique_id': sticker.unique_id,
                'emoji': sticker.emoji,
                'set_name': sticker.set_name if hasattr(sticker, 'set_name') else None,
                'width': sticker.width,
                'height': sticker.height,
                'is_premium': sticker.premium if hasattr(sticker, 'premium') else False,
                'is_animated': sticker.is_animated if hasattr(sticker, 'is_animated') else False,
                'is_video': sticker.is_video if hasattr(sticker, 'is_video') else False,
                'extracted_from': message.chat_id if message else None,
                'message_id': message.id if message else None,
                'category': 'general',
                'usage_count': 0
            }
            
            # Check if already exists
            existing = stickers_collection.find_one({'unique_id': sticker.unique_id})
            if not existing:
                stickers_collection.insert_one(sticker_data)
                self.extracted_stickers += 1
                logger.info(f"💾 Saved sticker: {sticker.emoji} ({sticker.unique_id})")
            
        except Exception as e:
            logger.error(f"❌ Error saving sticker: {e}")
    
    async def _save_emoji(self, emoji):
        """Save premium emoji to MongoDB"""
        try:
            emoji_data = {
                'file_id': emoji.file_id,
                'unique_id': emoji.unique_id,
                'emoji_character': None,  # Will be extracted from context
                'is_premium': True,
                'category': 'general',
                'usage_count': 0
            }
            
            # Check if already exists
            existing = emojis_collection.find_one({'unique_id': emoji.unique_id})
            if not existing:
                emojis_collection.insert_one(emoji_data)
                self.extracted_emojis += 1
                logger.info(f"💾 Saved emoji: {emoji.unique_id}")
            
        except Exception as e:
            logger.error(f"❌ Error saving emoji: {e}")
    
    def get_random_sticker(self, category='general'):
        """Get random sticker from category"""
        sticker = stickers_collection.aggregate([
            {'$match': {'category': category}},
            {'$sample': {'size': 1}}
        ]).next()
        
        # Update usage count
        stickers_collection.update_one(
            {'_id': sticker['_id']},
            {'$inc': {'usage_count': 1}}
        )
        
        return sticker
    
    def get_random_emoji(self, category='general'):
        """Get random emoji from category"""
        emoji = emojis_collection.aggregate([
            {'$match': {'category': category}},
            {'$sample': {'size': 1}}
        ]).next()
        
        # Update usage count
        emojis_collection.update_one(
            {'_id': emoji['_id']},
            {'$inc': {'usage_count': 1}}
        )
        
        return emoji
    
    def get_sticker_stats(self):
        """Get statistics about saved stickers and emojis"""
        total_stickers = stickers_collection.count_documents({})
        total_emojis = emojis_collection.count_documents({})
        premium_stickers = stickers_collection.count_documents({'is_premium': True})
        
        return {
            'total_stickers': total_stickers,
            'total_emojis': total_emojis,
            'premium_stickers': premium_stickers,
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
        # Extract all stickers
        await extractor.extract_all_sticker_packs()
        
        # Extract all emojis
        await extractor.extract_premium_emojis()
        
        # Show stats
        stats = extractor.get_sticker_stats()
        logger.info(f"📊 Stats: {stats}")

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
