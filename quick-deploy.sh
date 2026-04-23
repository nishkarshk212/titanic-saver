#!/bin/bash

# Quick deployment commands - Copy and paste this entire block

# Step 1: Navigate to bot directory and stop old bot
cd /root/telegram-bot && pkill -f 'python3 bot.py'

# Step 2: Pull latest changes
git pull origin main

# Step 3: Wait 2 seconds
sleep 2

# Step 4: Start bot permanently with systemd
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

# Step 5: Enable and start service
systemctl daemon-reload
systemctl enable titanic-bot.service
systemctl start titanic-bot.service

# Step 6: Check status
sleep 3
echo "========================================="
echo "Bot Status:"
systemctl status titanic-bot.service --no-pager -l
echo "========================================="
echo ""
echo "Recent Logs:"
tail -30 /root/telegram-bot/bot.log
