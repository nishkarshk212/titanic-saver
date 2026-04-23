# ⚡ Quick Start - Deploy Bot Permanently

## 🎯 What You Need To Do

Just **2 simple steps**:

---

## Step 1: SSH to Server

```bash
ssh root@161.118.250.195
```

**Password:** `Akshay343402355468`

---

## Step 2: Run This Script

After connecting, run these commands:

```bash
cd /root/telegram-bot
bash << 'SCRIPT'
#!/bin/bash
pkill -f 'python3 bot.py'
sleep 2
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
systemctl daemon-reload
systemctl enable titanic-bot.service
systemctl start titanic-bot.service
sleep 3
systemctl status titanic-bot.service --no-pager -l
SCRIPT
```

That's it! The bot will start permanently.

---

## ✅ Verify It Worked

After running the script, you should see:

```
● titanic-bot.service - Titanic Saver Telegram Bot
     Loaded: loaded (/etc/systemd/system/titanic-bot.service; enabled)
     Active: active (running)
```

Then test in Telegram:
- Send `/start` to the bot
- Send `/settings` and click 🎛️ Command Perms

---

## 📊 Useful Commands

### Check if bot is running
```bash
systemctl status titanic-bot
```

### View logs
```bash
journalctl -u titanic-bot -f
```

### Restart bot
```bash
systemctl restart titanic-bot
```

### View bot log file
```bash
tail -f /root/telegram-bot/bot.log
```

---

## 🎁 What You Get

✅ Bot runs **permanently**  
✅ **Auto-restarts** if it crashes  
✅ **Auto-starts** on server reboot  
✅ Logs to **Telegram log group**  
✅ Latest **Command Permissions** feature  

---

## 🔔 Log Group

The bot will automatically send updates to log group: `-1003757375746`

When bot starts, it sends:
- Deployment status
- Server info
- Version info
- Management commands

---

**Need more details?** See [PERMANENT_DEPLOYMENT.md](PERMANENT_DEPLOYMENT.md)
