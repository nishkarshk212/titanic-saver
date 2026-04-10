# Deployment Guide - Server Setup

## 🚀 Complete Deployment Instructions

This guide will help you deploy your Telegram bot to a production server.

---

## 📋 Prerequisites

- Ubuntu/Debian server (or any Linux distribution)
- Python 3.8 or higher
- Git installed
- MongoDB Atlas account (already set up)
- Telegram Bot Token

---

## Step 1: Server Setup

### Update System Packages
```bash
sudo apt update
sudo apt upgrade -y
```

### Install Python and Dependencies
```bash
sudo apt install -y python3 python3-pip python3-venv git
```

### Install Git (if not installed)
```bash
sudo apt install -y git
```

---

## Step 2: Clone Repository

### Navigate to Home Directory
```bash
cd ~
```

### Clone Your Repository
```bash
git clone https://github.com/yourusername/your-repo.git
cd your-repo
```

Or if using a different Git service:
```bash
git clone <your-git-repo-url>
cd <your-repo-folder>
```

---

## Step 3: Set Up Virtual Environment

### Create Virtual Environment
```bash
python3 -m venv venv
```

### Activate Virtual Environment
```bash
source venv/bin/activate
```

### Upgrade pip
```bash
pip install --upgrade pip
```

---

## Step 4: Install Dependencies

### Install Python Packages
```bash
pip install -r requirements.txt
```

This will install:
- python-telegram-bot
- python-dotenv
- pymongo
- certifi (for SSL)

---

## Step 5: Configure Environment Variables

### Create .env File
```bash
nano .env
```

### Add Configuration
```env
# Telegram Bot
BOT_TOKEN=your_actual_bot_token_here
LOG_CHANNEL_ID=your_log_channel_id
OWNER_ID=your_telegram_user_id

# MongoDB
MONGODB_URI=mongodb+srv://mybotpanda_db_user:hx0n5AI90lFGyl93@grouphelp.puxyti8.mongodb.net/?appName=GROUPHELP

# RapidAPI (Optional - currently hardcoded in code)
# RAPIDAPI_KEY=79115cebe8msh7aeb0698c33cb2bp140b6cjsn20d3c311c6f4
```

Save and exit (Ctrl+X, Y, Enter).

---

## Step 6: Test the Bot

### Run Bot Manually
```bash
python3 bot.py
```

### Verify Bot Starts
You should see:
```
Connecting to MongoDB...
✅ Successfully connected to MongoDB: GROUPHELP
✅ MongoDB database initialized successfully!
Bot is starting...
```

### Test Commands
Send these to your bot:
- `/start` - Test basic functionality
- `/ai Hello` - Test AI chat
- `/translate es Hello` - Test translation

Stop the bot with `Ctrl+C`.

---

## Step 7: Set Up Systemd Service (Auto-Start)

### Create Service File
```bash
sudo nano /etc/systemd/system/telegram-bot.service
```

### Add Service Configuration
```ini
[Unit]
Description=Telegram Group Help Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/your-repo
ExecStart=/home/ubuntu/your-repo/venv/bin/python3 bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Environment
Environment=PATH=/home/ubuntu/your-repo/venv/bin
EnvironmentFile=/home/ubuntu/your-repo/.env

[Install]
WantedBy=multi-user.target
```

**Note**: Replace `ubuntu` with your username and `your-repo` with your folder name.

### Reload Systemd
```bash
sudo systemctl daemon-reload
```

### Enable Service (Start on Boot)
```bash
sudo systemctl enable telegram-bot.service
```

### Start Service
```bash
sudo systemctl start telegram-bot.service
```

### Check Status
```bash
sudo systemctl status telegram-bot.service
```

### View Logs
```bash
sudo journalctl -u telegram-bot.service -f
```

### Useful Commands
```bash
# Stop bot
sudo systemctl stop telegram-bot.service

# Restart bot
sudo systemctl restart telegram-bot.service

# View logs
sudo journalctl -u telegram-bot.service -n 100
```

---

## Step 8: Set Up Log Rotation (Optional)

### Create Logrotate Configuration
```bash
sudo nano /etc/logrotate.d/telegram-bot
```

### Add Configuration
```
/var/log/telegram-bot/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 ubuntu ubuntu
}
```

---

## Step 9: Firewall Configuration

### Allow HTTPS (for webhooks, if using)
```bash
sudo ufw allow 443/tcp
```

### Check Firewall Status
```bash
sudo ufw status
```

---

## Step 10: Monitor and Maintain

### Check Bot Status
```bash
sudo systemctl status telegram-bot.service
```

### Monitor Logs in Real-Time
```bash
sudo journalctl -u telegram-bot.service -f
```

### Check Python Process
```bash
ps aux | grep bot.py
```

### Monitor System Resources
```bash
# CPU and Memory
htop

# Disk Space
df -h
```

---

## 🔧 Advanced Configuration

### Using Screen/Tmux (Alternative to Systemd)

#### Install Screen
```bash
sudo apt install -y screen
```

#### Start Bot in Screen Session
```bash
screen -S bot
python3 bot.py
# Press Ctrl+A, then D to detach
```

#### Reattach to Session
```bash
screen -r bot
```

#### List Sessions
```bash
screen -ls
```

### Using PM2 (Process Manager)

#### Install PM2
```bash
sudo npm install -g pm2
```

#### Start Bot with PM2
```bash
pm2 start bot.py --name telegram-bot --interpreter python3
```

#### Save PM2 Configuration
```bash
pm2 save
pm2 startup
```

#### PM2 Commands
```bash
# View status
pm2 status

# View logs
pm2 logs telegram-bot

# Restart
pm2 restart telegram-bot

# Stop
pm2 stop telegram-bot
```

---

## 📊 Monitoring Setup

### Create Health Check Script
```bash
nano ~/check-bot.sh
```

### Add Health Check
```bash
#!/bin/bash
if systemctl is-active --quiet telegram-bot.service; then
    echo "Bot is running"
else
    echo "Bot is NOT running! Restarting..."
    sudo systemctl restart telegram-bot.service
fi
```

### Make Executable
```bash
chmod +x ~/check-bot.sh
```

### Add to Crontab (Check Every 5 Minutes)
```bash
crontab -e
```

Add:
```
*/5 * * * * /home/ubuntu/check-bot.sh >> /var/log/bot-check.log 2>&1
```

---

## 🔐 Security Best Practices

### 1. Secure .env File
```bash
chmod 600 .env
```

### 2. Regular Updates
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Update Python packages
pip install --upgrade -r requirements.txt
```

### 3. Backup .env File
```bash
cp .env .env.backup
# Store backup securely
```

### 4. Monitor API Usage
- Check RapidAPI dashboard regularly
- Monitor MongoDB Atlas usage
- Set up usage alerts

### 5. SSL Certificates
```bash
# Ensure certifi is updated
pip install --upgrade certifi
```

---

## 🐛 Troubleshooting

### Bot Won't Start

**Check Logs:**
```bash
sudo journalctl -u telegram-bot.service -n 50
```

**Common Issues:**
1. Missing dependencies: `pip install -r requirements.txt`
2. Wrong .env configuration: Check all variables
3. MongoDB connection: Test with `python3 test_mongodb.py`
4. Invalid bot token: Verify with BotFather

### MongoDB Connection Failed

**Test Connection:**
```bash
python3 test_mongodb.py
```

**Solutions:**
1. Check MONGODB_URI in .env
2. Whitelist server IP in MongoDB Atlas
3. Check internet connection
4. Verify SSL certificates

### High Memory Usage

**Monitor:**
```bash
htop
```

**Solutions:**
1. Restart bot periodically
2. Check for memory leaks
3. Increase server RAM
4. Optimize conversation history

### API Rate Limits

**Monitor Usage:**
- Check RapidAPI dashboard
- Review MongoDB Atlas metrics

**Solutions:**
1. Implement rate limiting
2. Upgrade API plans
3. Add request throttling
4. Cache responses

---

## 📈 Scaling

### Multiple Bot Instances

For high traffic, consider:
1. Load balancing
2. Database connection pooling
3. Redis caching
4. Message queue (Celery)

### Database Optimization

1. Monitor MongoDB indexes
2. Archive old data
3. Use MongoDB Atlas auto-scaling
4. Implement data retention policies

---

## 📝 Maintenance Checklist

### Daily
- [ ] Check bot status
- [ ] Monitor error logs
- [ ] Check API usage

### Weekly
- [ ] Review bot performance
- [ ] Check disk space
- [ ] Update dependencies

### Monthly
- [ ] Review MongoDB usage
- [ ] Audit API keys
- [ ] Backup configuration
- [ ] Security updates

---

## 🆘 Support

### Getting Help

1. Check logs: `sudo journalctl -u telegram-bot.service`
2. Test MongoDB: `python3 test_mongodb.py`
3. Verify .env configuration
4. Check API dashboards

### Useful Commands Summary

```bash
# Bot management
sudo systemctl status telegram-bot.service
sudo systemctl restart telegram-bot.service
sudo journalctl -u telegram-bot.service -f

# System monitoring
htop
df -h
free -m

# Git operations
git status
git pull
git log --oneline
```

---

## ✅ Deployment Checklist

Before going live:

- [ ] Server set up and updated
- [ ] Repository cloned
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] .env file configured
- [ ] Bot tested manually
- [ ] Systemd service created
- [ ] Bot starts on boot
- [ ] Logs configured
- [ ] Firewall configured
- [ ] Monitoring set up
- [ ] Backup strategy in place
- [ ] API keys secured
- [ ] MongoDB connected
- [ ] All features tested

---

**Your bot is now deployed and running! 🎉**
