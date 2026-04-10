# 🔧 Fix Bot Issues - Step by Step

## Issues Found:
1. ❌ Multiple bot instances running (4 bots!)
2. ❌ MongoDB not connected
3. ❌ Translation and AI not working due to conflicts

---

## ✅ **FIX: Run These Commands on Server**

### **SSH into Server:**
```bash
ssh root@161.118.250.195 -p 22
# Password: Akshay343402355468
```

### **Step 1: Stop All Running Bots**
```bash
# Stop your bot service
systemctl stop telegram-bot.service

# Kill ALL bot processes
pkill -f "bot.py"
pkill -f "bio_guard_bot.py"

# Verify no bots running
ps aux | grep bot.py | grep -v grep
# Should show nothing!
```

### **Step 2: Update Bot Code**
```bash
cd /root/titanic-saver

# Pull latest code
git pull

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt
pip install --upgrade certifi
```

### **Step 3: Check .env File**
```bash
# Check if .env exists
cat .env

# If missing or wrong, recreate it
nano .env
```

**Make sure .env has:**
```env
BOT_TOKEN=8655926587:AAH3PtUOEdvj81-Z8pKWOfytpKLHPmQ2nbc
LOG_CHANNEL_ID=-1001234567890
OWNER_ID=YOUR_USER_ID
MONGODB_URI=mongodb+srv://mybotpanda_db_user:hx0n5AI90lFGyl93@grouphelp.puxyti8.mongodb.net/?appName=GROUPHELP
```

### **Step 4: Test MongoDB Connection**
```bash
python3 test_mongodb.py
```

**If it fails with SSL error:**
```bash
pip install --upgrade certifi
python3 test_mongodb.py
```

### **Step 5: Test Bot Manually**
```bash
python3 bot.py
```

**You should see:**
```
Connecting to MongoDB...
✅ Successfully connected to MongoDB: GROUPHELP
✅ MongoDB database initialized successfully!
Bot is starting...
```

**If it works, press Ctrl+C to stop**

### **Step 6: Start Bot Service**
```bash
# Start the service
systemctl start telegram-bot.service

# Check status
systemctl status telegram-bot.service

# View logs
journalctl -u telegram-bot.service -f
```

### **Step 7: Verify Only ONE Bot is Running**
```bash
ps aux | grep bot.py | grep -v grep
```

**Should show ONLY:**
```
root  XXXXXX  0.0  0.6 431832 55376 ?  Ssl  18:49   0:00 /root/titanic-saver/venv/bin/python3 bot.py
```

---

## 🧪 **Test Features:**

### **Test AI (in private chat with bot):**
```
Hello!
What is Python?
```

### **Test Translation:**
```
/tr hi Hello World
```

### **Test Reply Translation:**
1. Send a message to a group
2. Reply to it with: `/tr`
3. Should translate to Hindi

---

## 🐛 **If Still Not Working:**

### **Check Logs:**
```bash
journalctl -u telegram-bot.service -n 100 --no-pager
```

### **Check for Errors:**
```bash
# Look for:
# - "Conflict" = Multiple bots running
# - "MongoDB not connected" = Database issue
# - "Error in ChatGPT API" = API issue
# - "Error in Translation API" = API issue
```

### **Restart Bot:**
```bash
systemctl restart telegram-bot.service
journalctl -u telegram-bot.service -f
```

---

## ⚠️ **Important Notes:**

### **Other Bots Running:**
You have these other bots on your server:
1. `/opt/security-bot/.venv/bin/python bot.py` (PID 506635)
2. `/root/bio-guard-bot/venv/bin/python3 bio_guard_bot.py` (PID 553250)
3. `/usr/bin/python3 bot.py` (PID 624369)

**These are DIFFERENT bots - DON'T kill them unless you want to stop those bots too!**

**Only kill if they're using the SAME bot token:**
```bash
# Check what token they're using
cat /opt/security-bot/.env 2>/dev/null | grep BOT_TOKEN
cat /root/bio-guard-bot/.env 2>/dev/null | grep BOT_TOKEN
```

### **If they use the SAME token:**
```bash
# Stop conflicting bots
systemctl stop security-bot 2>/dev/null
kill 506635 553250 624369

# Then restart your bot
systemctl restart telegram-bot.service
```

---

## ✅ **Success Checklist:**

- [ ] Only ONE bot instance running
- [ ] MongoDB connected successfully
- [ ] Bot starts without errors
- [ ] AI responds in private chat
- [ ] Translation works with /tr
- [ ] Reply translation works

---

**After fixing, your bot should work perfectly!** 🎉
