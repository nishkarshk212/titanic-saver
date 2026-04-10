# 📋 Quick Reference Card

## 🚀 Start Commands

```bash
# Clone repo
git clone https://github.com/nishkarshk212/titanic-saver.git
cd titanic-saver

# Install
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your credentials

# Test
python test_mongodb.py

# Run
python bot.py
```

---

## 🤖 AI Commands

| Command | Example |
|---------|---------|
| `/ai <text>` | `/ai What is Python?` |
| `/gpt <text>` | `/gpt Write a poem` |
| `/clearchat` | `/clearchat` |

---

## 🌐 Translation Commands

| Command | Example |
|---------|---------|
| `/translate <lang> <text>` | `/translate es Hello` |
| `/tr <lang> <text>` | `/tr fr Hello` |
| `/tl <text>` | `/tl Hello` |
| `/langs` | `/langs` |

### Popular Language Codes
- `en` - English
- `es` - Spanish
- `fr` - French
- `de` - German
- `it` - Italian
- `ru` - Russian
- `zh` - Chinese
- `ja` - Japanese
- `hi` - Hindi
- `ar` - Arabic

---

## 🔧 Useful Commands

```bash
# Check Git status
git status

# Pull latest changes
git pull

# View bot logs (systemd)
sudo journalctl -u telegram-bot.service -f

# Restart bot (systemd)
sudo systemctl restart telegram-bot.service

# Test MongoDB
python test_mongodb.py

# Migrate data
python migrate_to_mongodb.py
```

---

## 📁 Important Files

| File | Purpose |
|------|---------|
| `bot.py` | Main bot file |
| `.env` | Configuration |
| `database.py` | MongoDB connection |
| `ai_chat.py` | AI Chat feature |
| `translator.py` | Translation feature |
| `requirements.txt` | Dependencies |

---

## 🗄️ MongoDB Collections

- `users` - User data
- `chat_settings` - Group settings
- `warns` - User warnings
- `muters` - Mute permissions
- `banned_channels` - Banned channels
- `blocked_content` - Blocked content
- `filters` - Auto-filters
- `voice_chat_managers` - Voice managers

---

## 🔑 API Keys Location

Currently hardcoded in:
- `ai_chat.py` (line 13)
- `translator.py` (line 15)

For production, move to `.env`:
```env
RAPIDAPI_KEY=your_key_here
```

---

## 🐛 Quick Troubleshooting

**Bot won't start:**
```bash
python bot.py 2>&1 | tee error.log
```

**MongoDB error:**
```bash
python test_mongodb.py
```

**Check logs:**
```bash
sudo journalctl -u telegram-bot.service -n 50
```

---

## 📚 Documentation Links

- [Full README](README.md)
- [AI & Translation Guide](AI_TRANSLATION_GUIDE.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)
- [MongoDB Setup](MONGODB_SETUP.md)
- [Quick Start](QUICK_START.md)

---

## 🔐 Security Checklist

- [ ] .env file created
- [ ] .env not committed to Git
- [ ] MongoDB IP restricted
- [ ] API keys secured
- [ ] Bot token secure

---

**Print this page for quick reference! 📄**
