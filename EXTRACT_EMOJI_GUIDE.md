# 🎨 Extract Premium Emojis from SpicyEryx Pack

## 📋 Method 1: Easy Way (Recommended)

Since the pack requires bot interaction, the easiest way is:

### Step 1: Add the Pack to Your Account
1. Click: https://t.me/addemoji/SpicyEryx_by_TgEmojis_bot
2. Click "Add" to add the pack to your premium account

### Step 2: Send Emojis to Your Bot
1. Open your bot in private chat
2. Send 5-10 emojis from the SpicyEryx pack
3. For each emoji, reply with:
   ```
   /save_emoji premium_pack
   ```

### Step 3: Bot Saves Them
Bot will respond:
```
✅ Custom emoji saved!

📂 Category: premium_pack
🆔 ID: 5368374892347234
```

---

## 🔥 Method 2: Auto-Extract (Advanced)

### Option A: Use Messages with Emojis

```bash
ssh root@161.118.250.195 -p 22 "cd /root/titanic-saver && python3 << 'EOF'
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# Connect
client = TelegramClient(
    StringSession(os.getenv('PREMIUM_SESSION_STRING')),
    int(os.getenv('TELEGRAM_API_ID')),
    os.getenv('TELEGRAM_API_HASH')
)

async def main():
    await client.connect()
    
    # Get your saved messages or a chat where you used the emojis
    # Replace with actual chat ID or username
    chat = await client.get_entity('me')  # Saved messages
    
    # Get messages with custom emojis
    messages = await client.get_messages(chat, limit=100)
    
    mongo = MongoClient(os.getenv('MONGODB_URI', 'mongodb+srv://mybotpanda_db_user:hx0n5AI90lFGyl93@grouphelp.puxyti8.mongodb.net/?appName=GROUPHELP'))
    db = mongo['GROUPHELP']
    emojis_col = db['premium_emojis']
    
    saved = 0
    for msg in messages:
        if msg.entities:
            for entity in msg.entities:
                if entity.type == 'custom_emoji':
                    emoji_data = {
                        'file_id': str(entity.custom_emoji_id),
                        'unique_id': str(entity.custom_emoji_id),
                        'pack_name': 'SpicyEryx_by_TgEmojis',
                        'is_premium': True,
                        'category': 'premium_pack',
                        'usage_count': 0
                    }
                    
                    if not emojis_col.find_one({'unique_id': entity.custom_emoji_id}):
                        emojis_col.insert_one(emoji_data)
                        saved += 1
                        print(f'✅ Saved emoji: {entity.custom_emoji_id}')
    
    print(f'\\n🎉 Saved {saved} new emojis!')
    await client.disconnect()

asyncio.run(main())
EOF"
```

### Option B: Manual Pack Access

If you have the exact pack short name:

```bash
ssh root@161.118.250.195 -p 22 "cd /root/titanic-saver && python3 extract_premium_emojis.py"
```

---

## ✅ Verify Extraction

```bash
ssh root@161.118.250.195 -p 22 "python3 -c \"
from pymongo import MongoClient
client = MongoClient('mongodb+srv://mybotpanda_db_user:hx0n5AI90lFGyl93@grouphelp.puxyti8.mongodb.net/?appName=GROUPHELP')
db = client['GROUPHELP']
count = db['premium_emojis'].count_documents({'pack_name': 'SpicyEryx_by_TgEmojis'})
print(f'SpicyEryx emojis in database: {count}')
\""
```

---

## 🎯 Quickest Method

1. **Open Telegram**
2. **Click**: https://t.me/addemoji/SpicyEryx_by_TgEmojis_bot
3. **Add the pack**
4. **Go to your bot**
5. **Send 10 emojis** from the pack
6. **Reply to each**: `/save_emoji premium_pack`
7. **Done!** ✅

---

## 📊 After Extraction

Use the emojis in bot:
```
/get_emoji premium_pack    - Get random emoji from pack
/list_emojis               - List all emoji packs
/sticker_stats             - View statistics
```
