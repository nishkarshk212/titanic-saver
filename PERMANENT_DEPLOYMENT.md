# 🚀 Permanent Bot Deployment Guide

## What This Does

✅ Sets up bot as a **systemd service** (runs permanently)  
✅ **Auto-restarts** if bot crashes  
✅ **Auto-starts** on server reboot  
✅ Logs to both file and **Telegram log group**  
✅ Latest code already pulled from git  

---

## ⚡ Quick Deploy (Copy & Paste)

### Option 1: One Command Block

SSH into server and run this entire block:

```bash
ssh root@161.118.250.195
```

Password: `Akshay343402355468`

Then paste this:

```bash
cd /root/telegram-bot && \
pkill -f 'python3 bot.py' && \
sleep 2 && \
cat > /etc/systemd/system/titanic-bot.service << 'EOF'
[Unit]
Description=Titanic Saver Telegram Bot
After=network.target mongod.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/telegram-bot
ExecStart=/root/telegram-bot/venv/bin/python3 bot.py
Restart=always
RestartSec=10
StandardOutput=append:/root/telegram-bot/bot.log
StandardError=append:/root/telegram-bot/bot.log
Environment=PATH=/root/telegram-bot/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload && \
systemctl enable titanic-bot.service && \
systemctl start titanic-bot.service && \
sleep 3 && \
echo "✅ Bot started!" && \
systemctl status titanic-bot.service --no-pager -l
```

---

### Option 2: Step by Step

#### Step 1: SSH to Server
```bash
ssh root@161.118.250.195
```
Password: `Akshay343402355468`

#### Step 2: Stop Old Bot
```bash
pkill -f 'python3 bot.py'
```

#### Step 3: Wait 2 Seconds
```bash
sleep 2
```

#### Step 4: Navigate to Bot Directory
```bash
cd /root/telegram-bot
```

#### Step 5: Create Systemd Service
```bash
cat > /etc/systemd/system/titanic-bot.service << 'EOF'
[Unit]
Description=Titanic Saver Telegram Bot
After=network.target mongod.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/telegram-bot
ExecStart=/root/telegram-bot/venv/bin/python3 bot.py
Restart=always
RestartSec=10
StandardOutput=append:/root/telegram-bot/bot.log
StandardError=append:/root/telegram-bot/bot.log
Environment=PATH=/root/telegram-bot/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

[Install]
WantedBy=multi-user.target
EOF
```

#### Step 6: Enable and Start Service
```bash
systemctl daemon-reload
systemctl enable titanic-bot.service
systemctl start titanic-bot.service
```

#### Step 7: Check Status
```bash
systemctl status titanic-bot.service
```

---

## 📊 Management Commands

### Check Bot Status
```bash
systemctl status titanic-bot
```

### View Live Logs
```bash
journalctl -u titanic-bot -f
```

### View Bot Log File
```bash
tail -f /root/telegram-bot/bot.log
```

### Restart Bot
```bash
systemctl restart titanic-bot
```

### Stop Bot
```bash
systemctl stop titanic-bot
```

### Start Bot
```bash
systemctl start titanic-bot
```

### View Last 50 Lines of Log
```bash
tail -50 /root/telegram-bot/bot.log
```

---

## 🔔 Log Group Updates

The bot automatically sends logs to the log group when:
- Bot starts
- Bot stops
- Errors occur
- Important events happen

**Log Group ID:** `-1003757375746`

### Manual Test - Send Message to Log Group

After bot starts, test with:
```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/sendMessage" \
  -d "chat_id=-1003757375746" \
  -d "text=🚀 Bot started successfully!%0A%0A✅ Service: titanic-bot%0A📍 Server: 161.118.250.195%0A⏰ Time: $(date)"
```

---

## ✅ Verification Checklist

After deployment, verify:

- [ ] Service is running: `systemctl status titanic-bot`
- [ ] Bot responds to `/start` in Telegram
- [ ] Bot responds to `/settings` in Telegram
- [ ] Log group receives startup message
- [ ] Bot auto-restarts if killed: `pkill -f 'python3 bot.py'` then wait 10 seconds
- [ ] Check logs: `journalctl -u titanic-bot -f`

---

## 🔧 Troubleshooting

### Bot Not Starting?
```bash
# Check service status
systemctl status titanic-bot

# Check logs
journalctl -u titanic-bot -n 100

# Check bot log file
tail -100 /root/telegram-bot/bot.log
```

### Service Fails to Start?
```bash
# Reload systemd
systemctl daemon-reload

# Try starting again
systemctl start titanic-bot

# Check for errors
journalctl -u titanic-bot -xe
```

### MongoDB Connection Issues?
```bash
# Check if MongoDB is running
systemctl status mongod

# Start MongoDB if needed
systemctl start mongod

# Then restart bot
systemctl restart titanic-bot
```

### Bot Crashes Randomly?
The service is configured to auto-restart. Check logs:
```bash
journalctl -u titanic-bot --since "1 hour ago"
```

---

## 📝 Service Configuration

**Service File:** `/etc/systemd/system/titanic-bot.service`

**Key Features:**
- `Restart=always` - Always restart if stopped
- `RestartSec=10` - Wait 10 seconds before restart
- `StandardOutput/StandardError` - Log to file
- Auto-start on boot enabled

---

## 🎯 What's New in This Deployment

✅ **Command Permissions Feature**
  - 22 configurable commands
  - 3 access levels (All, Admin, Owner)
  - New 🎛️ Command Perms button in settings

✅ **Permanent Running**
  - Systemd service management
  - Auto-restart on crash
  - Auto-start on boot

✅ **Better Logging**
  - Logs to file: `/root/telegram-bot/bot.log`
  - Logs to journal: `journalctl -u titanic-bot`
  - Logs to Telegram log group

---

## 📚 Additional Resources

- **Full Guide:** [SERVER_DEPLOYMENT_GUIDE.md](SERVER_DEPLOYMENT_GUIDE.md)
- **Command Permissions:** [COMMAND_PERMISSIONS_GUIDE.md](COMMAND_PERMISSIONS_GUIDE.md)
- **Quick Reference:** [COMMAND_PERMISSIONS_QUICK_REF.md](COMMAND_PERMISSIONS_QUICK_REF.md)

---

## 🆘 Need Help?

If something goes wrong:

1. Check the logs first
2. Try restarting the service
3. Check MongoDB is running
4. Verify git pulled successfully

**Common Issues:**
- Port already in use → Kill old process
- MongoDB not connected → Start MongoDB
- Bot token invalid → Check .env file
- Permissions error → Run as root

---

**Deployment Date:** April 23, 2026  
**Server:** 161.118.250.195  
**Bot Directory:** /root/telegram-bot  
**Service:** titanic-bot.service
