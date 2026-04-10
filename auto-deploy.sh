#!/bin/bash

# Automated Server Deployment Script
# This script will SSH into your server and deploy the bot

set -e

# Server Configuration
SERVER_IP="161.118.250.195"
SERVER_USER="root"
SERVER_PORT="22"
SERVER_PASSWORD="Akshay343402355468"

echo "========================================="
echo "🚀 Automated Bot Deployment to Server"
echo "========================================="
echo ""
echo "Server: $SERVER_IP"
echo "User: $SERVER_USER"
echo "Port: $SERVER_PORT"
echo ""

# Check if sshpass is installed (for password-based SSH)
if ! command -v sshpass &> /dev/null; then
    echo "📦 Installing sshpass for automated SSH..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        brew install hudochenkov/sshpass/sshpass
    else
        # Linux
        sudo apt-get install -y sshpass
    fi
fi

echo ""
echo "🔌 Connecting to server..."
echo ""

# Deploy commands
sshpass -p "$SERVER_PASSWORD" ssh -o StrictHostKeyChecking=no -p $SERVER_PORT ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'

echo "========================================="
echo "📋 Starting Deployment on Server"
echo "========================================="
echo ""

# Step 1: Update system
echo "Step 1: Updating system packages..."
apt update && apt upgrade -y
echo "✅ System updated"
echo ""

# Step 2: Install dependencies
echo "Step 2: Installing dependencies..."
apt install -y python3 python3-pip python3-venv git curl
echo "✅ Dependencies installed"
echo ""

# Step 3: Clone repository
echo "Step 3: Cloning repository..."
cd ~
if [ -d "titanic-saver" ]; then
    echo "Repository exists, pulling latest changes..."
    cd titanic-saver
    git pull
else
    git clone https://github.com/nishkarshk212/titanic-saver.git
    cd titanic-saver
fi
echo "✅ Repository ready"
echo ""

# Step 4: Create virtual environment
echo "Step 4: Setting up virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
echo "✅ Virtual environment created"
echo ""

# Step 5: Install Python packages
echo "Step 5: Installing Python packages..."
pip install -r requirements.txt
echo "✅ Packages installed"
echo ""

# Step 6: Configure .env
echo "Step 6: Configuring environment..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "⚠️  Created .env from template"
    echo "⚠️  You MUST edit .env with your BOT_TOKEN and other credentials!"
    echo ""
    echo "Please edit .env now:"
    echo "  nano .env"
    echo ""
    echo "Required variables:"
    echo "  BOT_TOKEN=your_bot_token"
    echo "  OWNER_ID=your_telegram_user_id"
    echo ""
else
    echo "✅ .env file already exists"
fi
echo ""

# Step 7: Test MongoDB
echo "Step 7: Testing MongoDB connection..."
if python3 test_mongodb.py; then
    echo "✅ MongoDB connection successful"
else
    echo "⚠️  MongoDB test failed, trying to fix..."
    pip install --upgrade certifi
    python3 test_mongodb.py || echo "⚠️  Please check MONGODB_URI in .env"
fi
echo ""

# Step 8: Create systemd service
echo "Step 8: Creating systemd service..."
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

# Environment
Environment=PATH=/root/titanic-saver/venv/bin
EnvironmentFile=/root/titanic-saver/.env

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Service file created"
echo ""

# Step 9: Enable and start service
echo "Step 9: Starting bot service..."
systemctl daemon-reload
systemctl enable telegram-bot.service
systemctl start telegram-bot.service
sleep 3
echo "✅ Service started"
echo ""

# Step 10: Check status
echo "Step 10: Checking service status..."
systemctl status telegram-bot.service --no-pager -l
echo ""

echo "========================================="
echo "✅ Deployment Complete!"
echo "========================================="
echo ""
echo "📊 Useful Commands:"
echo "  Check status:    systemctl status telegram-bot.service"
echo "  View logs:       journalctl -u telegram-bot.service -f"
echo "  Restart bot:     systemctl restart telegram-bot.service"
echo "  Stop bot:        systemctl stop telegram-bot.service"
echo ""
echo "⚠️  IMPORTANT NEXT STEPS:"
echo "  1. Edit .env with your BOT_TOKEN: nano /root/titanic-saver/.env"
echo "  2. Restart bot after editing: systemctl restart telegram-bot.service"
echo "  3. Change root password: passwd"
echo "  4. Test bot in Telegram"
echo ""
echo "📁 Bot Directory: /root/titanic-saver"
echo "📝 Config File:   /root/titanic-saver/.env"
echo "📋 Logs:          journalctl -u telegram-bot.service -f"
echo ""

ENDSSH

echo ""
echo "========================================="
echo "🎉 Deployment Finished!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. SSH into server: ssh root@161.118.250.195 -p 22"
echo "2. Edit .env file: nano /root/titanic-saver/.env"
echo "3. Restart bot: systemctl restart telegram-bot.service"
echo "4. Check logs: journalctl -u telegram-bot.service -f"
echo "5. Test your bot in Telegram!"
echo ""
