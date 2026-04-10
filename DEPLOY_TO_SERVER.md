# 🚀 Quick Deploy to Server (161.118.250.195)

## ⚡ Method 1: One-Click Automated Deploy (Easiest)

### On your Mac, run this command:

```bash
cd "/Users/nishkarshkr/Desktop/group help"
./auto-deploy.sh
```

This will automatically:
- ✅ SSH into your server
- ✅ Install all dependencies
- ✅ Clone the repository
- ✅ Set up the bot
- ✅ Create systemd service
- ✅ Start the bot

**After it completes:**
1. SSH into server: `ssh root@161.118.250.195 -p 22`
2. Edit .env: `nano /root/titanic-saver/.env`
3. Add your BOT_TOKEN
4. Restart: `systemctl restart telegram-bot.service`
5. Test your bot!

---

## 📝 Method 2: Manual Deploy (More Control)

### Step 1: SSH into Server

```bash
ssh root@161.118.250.195 -p 22
# Password: Akshay343402355468
```

### Step 2: Copy-Paste This Entire Block

```bash
# Update system
apt update && apt upgrade -y

# Install dependencies
apt install -y python3 python3-pip python3-venv git curl

# Clone repository
cd ~
git clone https://github.com/nishkarshk212/titanic-saver.git
cd titanic-saver

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env (add your BOT_TOKEN)
nano .env
```

### Step 3: Edit .env File

In the nano editor, add:

```env
BOT_TOKEN=your_bot_token_from_botfather
LOG_CHANNEL_ID=-1001234567890
OWNER_ID=123456789
MONGODB_URI=mongodb+srv://mybotpanda_db_user:hx0n5AI90lFGyl93@grouphelp.puxyti8.mongodb.net/?appName=GROUPHELP
```

**Save:** Press `Ctrl+X`, then `Y`, then `Enter`

### Step 4: Test MongoDB

```bash
python3 test_mongodb.py
```

### Step 5: Test Bot

```bash
python3 bot.py
```

If it starts successfully, press `Ctrl+C` to stop it.

### Step 6: Set Up Auto-Start

```bash
# Create service file
cat > /etc/systemd/system/telegram-bot.service << 'EOF'
[Unit]
Description=Telegram Group Help Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/titanic-saver
ExecStart=/root/titanic-saver/venv/bin/python3 bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment=PATH=/root/titanic-saver/venv/bin
EnvironmentFile=/root/titanic-saver/.env

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
systemctl daemon-reload
systemctl enable telegram-bot.service
systemctl start telegram-bot.service

# Check status
systemctl status telegram-bot.service
```

---

## ✅ Verify Deployment

### Check if Bot is Running

```bash
systemctl status telegram-bot.service
```

### View Logs

```bash
journalctl -u telegram-bot.service -f
```

### Test in Telegram

Send to your bot:
- `/start`
- `/ai Hello`
- `/translate es Hello`

---

## 🔧 Useful Commands

```bash
# Check bot status
systemctl status telegram-bot.service

# View logs
journalctl -u telegram-bot.service -f

# Restart bot
systemctl restart telegram-bot.service

# Stop bot
systemctl stop telegram-bot.service

# Start bot
systemctl start telegram-bot.service
```

---

## 🐛 Troubleshooting

### Bot Not Starting?

```bash
# Check logs
journalctl -u telegram-bot.service -n 50

# Test manually
cd /root/titanic-saver
source venv/bin/activate
python3 bot.py
```

### MongoDB Error?

```bash
# Upgrade certifi
pip install --upgrade certifi

# Test connection
python3 test_mongodb.py
```

### Need to Edit .env?

```bash
nano /root/titanic-saver/.env
# After saving, restart:
systemctl restart telegram-bot.service
```

---

## 🔐 Security Steps (DO AFTER DEPLOYMENT!)

### 1. Change Root Password

```bash
passwd
# Enter new password
```

### 2. Or Create New User (Better)

```bash
# Create user
adduser botuser

# Give sudo access
usermod -aG sudo botuser

# Switch to new user
su - botuser

# Re-deploy bot under this user
```

---

## 📊 What Gets Installed

- ✅ Python 3
- ✅ Git
- ✅ Virtual environment
- ✅ All Python packages
- ✅ MongoDB connection
- ✅ Systemd service (auto-start)
- ✅ Bot running in background

---

## 🎯 After Successful Deployment

1. ✅ Bot is running 24/7
2. ✅ Auto-restarts on crash
3. ✅ Auto-starts on boot
4. ✅ Logs saved to journal
5. ✅ MongoDB connected
6. ✅ AI Chat working
7. ✅ Translation working

---

## 📞 Need Help?

Check these files:
- [SERVER_DEPLOY_STEPS.md](SERVER_DEPLOY_STEPS.md) - Detailed steps
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Complete guide
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Quick commands

---

**That's it! Your bot should be running on the server! 🎉**
