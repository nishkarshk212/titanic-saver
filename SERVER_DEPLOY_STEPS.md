# Server Deployment Instructions
# Server: 161.118.250.195
# User: root
# Port: 22

## Step 1: Connect to Server

Open your terminal and run:
```bash
ssh root@161.118.250.195 -p 22
# Password: Akshay343402355468
```

## Step 2: Update System

```bash
apt update && apt upgrade -y
```

## Step 3: Install Dependencies

```bash
apt install -y python3 python3-pip python3-venv git curl nano
```

## Step 4: Clone Repository

```bash
cd ~
git clone https://github.com/nishkarshk212/titanic-saver.git
cd titanic-saver
```

## Step 5: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

## Step 6: Install Python Packages

```bash
pip install -r requirements.txt
```

## Step 7: Configure Environment Variables

```bash
# Create .env file
nano .env
```

Add the following content (replace with your actual values):

```env
# Telegram Bot Configuration
BOT_TOKEN=YOUR_BOT_TOKEN_HERE
LOG_CHANNEL_ID=YOUR_LOG_CHANNEL_ID_HERE
OWNER_ID=YOUR_TELEGRAM_USER_ID_HERE

# MongoDB Configuration
MONGODB_URI=mongodb+srv://mybotpanda_db_user:hx0n5AI90lFGyl93@grouphelp.puxyti8.mongodb.net/?appName=GROUPHELP
```

**IMPORTANT**: Replace:
- `YOUR_BOT_TOKEN_HERE` with your actual bot token from @BotFather
- `YOUR_LOG_CHANNEL_ID_HERE` with your log channel ID
- `YOUR_TELEGRAM_USER_ID_HERE` with your Telegram user ID

Save with: `Ctrl+X`, then `Y`, then `Enter`

## Step 8: Test MongoDB Connection

```bash
python3 test_mongodb.py
```

If you see SSL errors, run:
```bash
pip install --upgrade certifi
```

Then test again.

## Step 9: Test the Bot

```bash
# Run the bot manually to test
python3 bot.py
```

You should see:
```
Connecting to MongoDB...
✅ Successfully connected to MongoDB: GROUPHELP
✅ MongoDB database initialized successfully!
Bot is starting...
```

Test the bot in Telegram:
- Send `/start`
- Send `/ai Hello`
- Send `/translate es Hello`

Stop the bot with: `Ctrl+C`

## Step 10: Set Up Systemd Service (Auto-Start)

Create service file:
```bash
nano /etc/systemd/system/telegram-bot.service
```

Add this content:

```ini
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

# Environment
Environment=PATH=/root/titanic-saver/venv/bin
EnvironmentFile=/root/titanic-saver/.env

[Install]
WantedBy=multi-user.target
```

Save with: `Ctrl+X`, then `Y`, then `Enter`

## Step 11: Enable and Start Service

```bash
# Reload systemd
systemctl daemon-reload

# Enable service (start on boot)
systemctl enable telegram-bot.service

# Start the bot
systemctl start telegram-bot.service

# Check status
systemctl status telegram-bot.service
```

## Step 12: Monitor the Bot

```bash
# View logs in real-time
journalctl -u telegram-bot.service -f

# Check recent logs
journalctl -u telegram-bot.service -n 100

# Check service status
systemctl status telegram-bot.service
```

## Useful Commands

```bash
# Start bot
systemctl start telegram-bot.service

# Stop bot
systemctl stop telegram-bot.service

# Restart bot
systemctl restart telegram-bot.service

# View logs
journalctl -u telegram-bot.service -f

# Check if bot is running
ps aux | grep bot.py
```

## Security Hardening (IMPORTANT!)

After deployment, secure your server:

### 1. Change Root Password
```bash
passwd
```

### 2. Create Non-Root User (Recommended)
```bash
# Create new user
adduser botuser

# Add to sudo group
usermod -aG sudo botuser

# Switch to new user
su - botuser

# Then re-deploy the bot under this user
```

### 3. Set Up SSH Keys (Optional but Recommended)
```bash
# On your local machine
ssh-keygen -t rsa -b 4096

# Copy to server
ssh-copy-id root@161.118.250.195

# Disable password authentication (after testing SSH keys work)
nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
# Restart SSH: systemctl restart sshd
```

### 4. Configure Firewall
```bash
# Install UFW
apt install -y ufw

# Allow SSH
ufw allow 22/tcp

# Enable firewall
ufw enable

# Check status
ufw status
```

## Troubleshooting

### Bot Won't Start
```bash
# Check logs
journalctl -u telegram-bot.service -n 50

# Test manually
cd /root/titanic-saver
source venv/bin/activate
python3 bot.py
```

### MongoDB Connection Failed
```bash
# Test connection
python3 test_mongodb.py

# Check MongoDB URI in .env
cat .env

# Update certifi
pip install --upgrade certifi
```

### API Errors
```bash
# Check if APIs are accessible
curl -H "x-rapidapi-key: 79115cebe8msh7aeb0698c33cb2bp140b6cjsn20d3c311c6f4" \
     -H "x-rapidapi-host: chatgpt-42.p.rapidapi.com" \
     https://chatgpt-42.p.rapidapi.com/
```

### High Memory Usage
```bash
# Monitor resources
htop
free -m
df -h
```

## Monitoring Setup

### Auto-Restart on Crash
The systemd service already has `Restart=always`, so the bot will auto-restart.

### Health Check Script
```bash
# Create health check
nano ~/check-bot.sh
```

Add:
```bash
#!/bin/bash
if systemctl is-active --quiet telegram-bot.service; then
    echo "$(date): Bot is running" >> /var/log/bot-check.log
else
    echo "$(date): Bot is DOWN! Restarting..." >> /var/log/bot-check.log
    systemctl restart telegram-bot.service
fi
```

Make executable and add to cron:
```bash
chmod +x ~/check-bot.sh
crontab -e
```

Add this line:
```
*/5 * * * * /root/check-bot.sh
```

## Next Steps After Deployment

1. ✅ Change root password
2. ✅ Test all bot commands
3. ✅ Monitor logs for 24 hours
4. ✅ Check MongoDB Atlas dashboard
5. ✅ Monitor RapidAPI usage
6. ✅ Set up backups
7. ✅ Configure alerts

## Support

If you encounter issues:
1. Check logs: `journalctl -u telegram-bot.service -f`
2. Test MongoDB: `python3 test_mongodb.py`
3. Verify .env configuration
4. Check API dashboards

---

**Your bot should now be running on the server! 🎉**
