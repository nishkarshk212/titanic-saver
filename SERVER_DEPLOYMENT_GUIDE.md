# Server Deployment Guide

## ✅ What's Already Done

1. ✅ Code committed to git repository
2. ✅ Changes pushed to GitHub
3. ✅ Server has pulled the latest changes

## 🚀 Deploy to Server (Choose One Method)

### Method 1: Using the Deployment Script (Recommended)

Run this command in your terminal:

```bash
cd /Users/nishkarshkr/Desktop/update/titanic-saver
./deploy-to-server.sh
```

You'll be prompted for the server password: `Akshay343402355468`

### Method 2: Manual Commands

If you prefer to do it manually, run these commands one by one:

#### Step 1: SSH into the server
```bash
ssh root@161.118.250.195
```
Password: `Akshay343402355468`

#### Step 2: Navigate to bot directory
```bash
cd /root/telegram-bot
```

#### Step 3: Stop the running bot
```bash
pkill -f 'python3 bot.py'
```

#### Step 4: Wait 2 seconds
```bash
sleep 2
```

#### Step 5: Start the bot in background
```bash
nohup /root/telegram-bot/venv/bin/python3 bot.py > bot.log 2>&1 &
```

#### Step 6: Verify bot is running
```bash
ps aux | grep 'python3 bot.py' | grep -v grep
```

#### Step 7: Check bot logs (optional)
```bash
tail -f bot.log
```

Press `Ctrl+C` to exit the log view.

### Method 3: One-Liner Command

Copy and paste this entire command:

```bash
ssh root@161.118.250.195 "cd /root/telegram-bot && pkill -f 'python3 bot.py' && sleep 2 && nohup /root/telegram-bot/venv/bin/python3 bot.py > bot.log 2>&1 &"
```

Password: `Akshay343402355468`

## 📋 Verification Checklist

After deployment, verify:

- [ ] Bot is running: `ps aux | grep 'python3 bot.py'`
- [ ] Bot responds to `/start` command in Telegram
- [ ] Bot responds to `/settings` command
- [ ] Command Permissions button (🎛️) appears in settings
- [ ] Check logs for errors: `tail -f /root/telegram-bot/bot.log`

## 🔧 Troubleshooting

### Bot not starting?
Check the logs:
```bash
ssh root@161.118.250.195 "tail -100 /root/telegram-bot/bot.log"
```

### Need to restart again?
```bash
ssh root@161.118.250.195 "pkill -f 'python3 bot.py' && sleep 2 && cd /root/telegram-bot && nohup /root/telegram-bot/venv/bin/python3 bot.py > bot.log 2>&1 &"
```

### View real-time logs?
```bash
ssh root@161.118.250.195 "tail -f /root/telegram-bot/bot.log"
```

## 📝 Server Information

- **IP**: 161.118.250.195
- **Username**: root
- **Password**: Akshay343402355468
- **Port**: 22
- **Bot Directory**: /root/telegram-bot
- **Git Repo**: https://github.com/nishkarshk212/titanic-saver.git

## 🎯 What Was Deployed

✅ Command Permissions Feature
- 22 configurable commands
- 3 access levels (All, Admin, Owner)
- New settings panel button: 🎛️ Command Perms
- Granular control for each command

## 📊 Files Updated

- settings_manager_mongo.py
- settings.py
- bot.py
- help.py
- + New Manager module files
- + Documentation files

---

**Need Help?**
Check these files:
- COMMAND_PERMISSIONS_GUIDE.md - Full user guide
- COMMAND_PERMISSIONS_QUICK_REF.md - Quick reference
