#!/bin/bash

# Permanent Bot Deployment Script with Systemd Service
# This script sets up the bot as a systemd service for permanent running

echo "========================================="
echo "  Permanent Bot Deployment"
echo "========================================="
echo ""

# Configuration
BOT_DIR="/root/telegram-bot"
SERVICE_FILE="/etc/systemd/system/titanic-bot.service"
LOG_CHANNEL_ID="-1003757375746"

# Step 1: Pull latest changes
echo "📦 Pulling latest changes..."
cd $BOT_DIR && git pull origin main
if [ $? -eq 0 ]; then
    echo "✅ Git pull successful!"
else
    echo "❌ Git pull failed!"
    exit 1
fi
echo ""

# Step 2: Stop old bot if running
echo "🛑 Stopping old bot process..."
pkill -f 'python3 bot.py' 2>/dev/null
sleep 2
echo "✅ Old bot stopped!"
echo ""

# Step 3: Create systemd service file
echo "📝 Creating systemd service file..."
cat > $SERVICE_FILE << 'EOF'
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

echo "✅ Service file created!"
echo ""

# Step 4: Reload systemd and enable service
echo "⚙️  Setting up systemd service..."
systemctl daemon-reload
systemctl enable titanic-bot.service
echo "✅ Systemd service enabled!"
echo ""

# Step 5: Start the service
echo "🚀 Starting bot service..."
systemctl start titanic-bot.service
sleep 3
echo "✅ Bot service started!"
echo ""

# Step 6: Check status
echo "🔍 Checking service status..."
systemctl status titanic-bot.service --no-pager -l
echo ""

# Step 7: Verify bot is running
echo "📊 Process check:"
ps aux | grep 'python3 bot.py' | grep -v grep
echo ""

# Step 8: Check logs
echo "📋 Recent logs (last 20 lines):"
tail -20 $BOT_DIR/bot.log
echo ""

echo "========================================="
echo "  ✅ Deployment Complete!"
echo "========================================="
echo ""
echo "Useful commands:"
echo "  • Check status: systemctl status titanic-bot"
echo "  • View logs: journalctl -u titanic-bot -f"
echo "  • Stop bot: systemctl stop titanic-bot"
echo "  • Restart bot: systemctl restart titanic-bot"
echo "  • Disable auto-start: systemctl disable titanic-bot"
echo ""
echo "Bot log file: $BOT_DIR/bot.log"
echo ""
