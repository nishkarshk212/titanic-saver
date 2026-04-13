# 🎨 Premium Sticker & Emoji Extractor Setup Guide

## 📋 Overview

This system allows you to:
1. **Extract** all premium stickers from your premium Telegram account
2. **Save** stickers/emojis manually by replying in bot DM
3. **Store** them in MongoDB for later use
4. **Use** them in bot messages automatically

---

## 🚀 Quick Setup (Manual Mode - No Session Needed)

### Step 1: Install Dependencies
```bash
cd "/Users/nishkarshkr/Desktop/group help"
pip install -r requirements.txt
```

### Step 2: Add OWNER_ID to .env
```bash
echo "OWNER_ID=your_telegram_user_id" >> .env
```

Get your user ID by messaging [@userinfobot](https://t.me/userinfobot) on Telegram

### Step 3: Deploy to Server
```bash
git add -A
git commit -m "Add premium sticker manager"
git push origin main

ssh root@161.118.250.195 -p 22 "cd /root/titanic-saver && git pull && systemctl restart telegram-bot.service"
```

### Step 4: Use Commands in Private DM

**Send a sticker to bot in private chat, then:**

```
/save_sticker welcome      - Save as welcome sticker
/save_sticker reaction     - Save as reaction sticker
/save_sticker ban          - Save as ban notification sticker
/save_sticker general      - Save as general sticker
```

**Get stickers:**
```
/get_sticker welcome       - Get random welcome sticker
/get_sticker reaction      - Get random reaction sticker
/list_stickers             - List all saved stickers
/sticker_stats             - Show statistics
```

---

## 🔥 Advanced Setup (Auto-Extract All Premium Stickers)

### Step 1: Get Telegram API Credentials

1. Go to https://my.telegram.org
2. Login with your premium account
3. Go to "API development tools"
4. Create an application
5. Note your `api_id` and `api_hash`

### Step 2: Generate Session String

```bash
# Create session generator script
cat > generate_session.py << 'EOF'
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = YOUR_API_ID
api_hash = 'YOUR_API_HASH'

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print("Your Session String:")
    print(client.session.save())
EOF

# Run it
python3 generate_session.py
```

**Enter your phone number when prompted** - you'll receive a Telegram login code

### Step 3: Add to .env

```bash
# Add these lines to your .env file
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash_here
PREMIUM_SESSION_STRING=1ApWapzMBu7xK...
OWNER_ID=your_user_id
```

### Step 4: Run Extractor

```bash
python3 premium_sticker_extractor.py
```

This will:
- Connect to your premium account
- Scan all chats for stickers
- Extract and save to MongoDB
- Show statistics

---

## 📊 Available Commands

### Owner Commands (Private DM)

| Command | Description | Example |
|---------|-------------|---------|
| `/save_sticker <category>` | Save replied sticker | `/save_sticker welcome` |
| `/save_emoji <category>` | Save custom emoji | `/save_emoji reactions` |
| `/list_stickers` | List all saved stickers | `/list_stickers` |
| `/list_emojis` | List all saved emojis | `/list_emojis` |
| `/delete_sticker <id>` | Delete sticker by ID | `/delete_sticker abc123` |
| `/sticker_stats` | Show statistics | `/sticker_stats` |
| `/get_sticker <category>` | Get random sticker | `/get_sticker welcome` |
| `/get_emoji <category>` | Get emoji info | `/get_emoji reactions` |

### Categories

- `welcome` - Welcome message stickers
- `goodbye` - Goodbye/leave stickers
- `reaction` - Reaction stickers
- `ban` - Ban notification stickers
- `mute` - Mute notification stickers
- `general` - General purpose stickers

---

## 💡 Usage Examples

### Save Stickers from DM

1. **Open bot private chat**
2. **Forward/send a premium sticker**
3. **Reply to it with:**
   ```
   /save_sticker welcome
   ```
4. **Bot confirms:**
   ```
   ✅ Sticker saved!
   
   📂 Category: welcome
   🎭 Emoji: 👋
   🆔 ID: CAACAgEAAx...
   ⭐ Premium: True
   🎬 Animated: True
   ```

### Use Stickers in Code

```python
from sticker_manager import send_sticker_by_category

# In your welcome message handler
def send_welcome_message(chat_id, context):
    context.bot.send_message(chat_id, "Welcome to the group!")
    
    # Send random welcome sticker
    send_sticker_by_category(chat_id, context, 'welcome')
```

### Get Sticker Statistics

```
/sticker_stats

📊 Sticker & Emoji Statistics

💾 Total Stickers: 150
⭐ Premium Stickers: 85
🎬 Animated Stickers: 120
✨ Custom Emojis: 45

Top Categories:
  • welcome: 35
  • reaction: 28
  • ban: 20
  • general: 67
```

---

## 🎯 Integration with Bot Features

### Welcome Messages with Stickers

The bot will automatically attach a random welcome sticker when new users join!

### Ban Notifications

Ban messages will include a random "ban" category sticker.

### Custom Reactions

Use `/get_sticker reaction` to get random reaction stickers.

---

## 📦 MongoDB Collections

### `premium_stickers` Collection
```json
{
  "file_id": "CAACAgEAAx...",
  "unique_id": "AgADAg...",
  "emoji": "👋",
  "set_name": "PremiumWelcome",
  "width": 512,
  "height": 512,
  "is_premium": true,
  "is_animated": true,
  "is_video": false,
  "category": "welcome",
  "saved_by": 123456789,
  "usage_count": 15
}
```

### `premium_emojis` Collection
```json
{
  "file_id": "5368374...",
  "unique_id": "5368374...",
  "category": "reactions",
  "saved_by": 123456789,
  "usage_count": 8
}
```

---

## 🔧 Troubleshooting

### Error: "Only bot owner can save stickers"
- Make sure `OWNER_ID` is set correctly in `.env`
- Get your ID from [@userinfobot](https://t.me/userinfobot)

### Error: "Telethon not installed"
```bash
pip install telethon
```

### Session not authorized
- Regenerate session string
- Make sure you're using premium account

### No stickers found in category
- Save some stickers first using `/save_sticker <category>`

---

## 🎉 Next Steps

1. **Start saving stickers** in private DM
2. **Organize by categories** for better management
3. **Integrate with bot features** (welcome, ban, etc.)
4. **Monitor usage** with `/sticker_stats`

---

## 📝 Notes

- ✅ Stickers are stored in MongoDB (persistent)
- ✅ Works with animated, video, and static stickers
- ✅ Premium stickers fully supported
- ✅ Custom emojis supported
- ✅ Usage tracking for analytics
- ✅ Category-based organization

**Happy sticker collecting!** 🎨✨
