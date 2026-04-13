"""
Debug: List all installed packs and their types
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

async def list_all_packs():
    """List all installed packs"""
    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        from telethon.tl import functions
        
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
            
            # Get all packs
            all_stickers = await client(functions.messages.GetAllStickersRequest(hash=0))
            
            logger.info(f"\n📊 Total packs: {len(all_stickers.sets)}")
            logger.info("=" * 80)
            
            for idx, pack in enumerate(all_stickers.sets, 1):
                # Get all attributes
                attrs = []
                for attr_name in ['emojis', 'custom_emoji', 'masks', 'animated', 'video']:
                    if hasattr(pack, attr_name):
                        value = getattr(pack, attr_name)
                        attrs.append(f"{attr_name}={value}")
                
                logger.info(f"{idx:2d}. {pack.title:40s} | Count: {pack.count:3d} | {', '.join(attrs)}")
                logger.info(f"    Short: {pack.short_name}")
            
            logger.info("=" * 80)
            
            await client.disconnect()
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(list_all_packs())
