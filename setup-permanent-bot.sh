#!/bin/bash

# =====================================================
# RUN THIS ON THE SERVER (after SSH)
# =====================================================
# This script will:
# 1. Stop the old bot
# 2. Set up systemd service
# 3. Start the bot permanently
# 4. Send update to log group
# =====================================================

echo "🚀 Starting Permanent Bot Deployment..."
echo ""

# Configuration
BOT_DIR="/root/telegram-bot"
LOG_CHANNEL="-1003757375746"

# Step 1: Stop old bot
echo "🛑 Stopping old bot..."
pkill -f 'python3 bot.py' 2>/dev/null
sleep 2
echo "✅ Old bot stopped"
echo ""

# Step 2: Navigate to bot directory
cd $BOT_DIR || exit

# Step 3: Pull latest code (already pulled, but just in case)
echo "📦 Ensuring latest code..."
git pull origin main 2>/dev/null
echo ""

# Step 4: Create systemd service
echo "📝 Creating systemd service..."
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

echo "✅ Service file created"
echo ""

# Step 5: Enable and start
echo "⚙️  Enabling service..."
systemctl daemon-reload
systemctl enable titanic-bot.service

echo "🚀 Starting bot..."
systemctl start titanic-bot.service
sleep 3

echo ""
echo "✅ Bot started!"
echo ""

# Step 6: Check status
echo "📊 Service Status:"
systemctl status titanic-bot.service --no-pager -l | head -20
echo ""

# Step 7: Get bot info for log message
BOT_TOKEN=$(grep BOT_TOKEN .env | cut -d '=' -f2)
HOSTNAME=$(hostname)
UPTIME=$(uptime -p)
DEPLOY_TIME=$(date '+%Y-%m-%d %H:%M:%S')

# Step 8: Send update to log group
echo "📤 Sending update to log group..."

if [ -n "$BOT_TOKEN" ]; then
    # Create log message
    LOG_MESSAGE="🚀 *BOT DEPLOYMENT UPDATE*

📦 *Version:* Command Permissions Feature
✅ *Status:* Successfully Deployed
🖥️ *Server:* $HOSTNAME (161.118.250.195)
⏰ *Deployed:* $DEPLOY_TIME
🔧 *Service:* titanic-bot.service
🔄 *Auto-Restart:* Enabled
📝 *Logs:* /root/telegram-bot/bot.log

*New Features:*
• 🎛️ Command Permissions Panel
• 22 Configurable Commands
• 3 Access Levels (All/Admin/Owner)
• Systemd Service (Permanent)
• Auto-Restart on Crash

*Management Commands:*
• Status: systemctl status titanic-bot
• Logs: journalctl -u titanic-bot -f
• Restart: systemctl restart titanic-bot"

    # Send to log group
    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d "chat_id=$LOG_CHANNEL" \
        -d "text=$LOG_MESSAGE" \
        -d "parse_mode=Markdown" \
        -d "disable_web_page_preview=true" > /dev/null

    echo "✅ Log message sent to group!"
else
    echo "⚠️  Could not send log message (BOT_TOKEN not found)"
fi

echo ""
echo "========================================="
echo "  ✅ DEPLOYMENT COMPLETE!"
echo "========================================="
echo ""
echo "📋 Quick Commands:"
echo "  • Status:   systemctl status titanic-bot"
echo "  • Logs:     journalctl -u titanic-bot -f"
echo "  • Restart:  systemctl restart titanic-bot"
echo "  • Stop:     systemctl stop titanic-bot"
echo "  • File Log: tail -f /root/telegram-bot/bot.log"
echo ""
echo "🎯 Bot is now running permanently!"
echo "   It will auto-start on reboot and auto-restart on crash."
echo ""
