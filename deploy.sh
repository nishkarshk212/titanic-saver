#!/bin/bash

# Telegram Bot Deployment Script
# This script automates the server setup process

set -e  # Exit on error

echo "========================================="
echo "🤖 Telegram Bot Deployment Script"
echo "========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo -e "${YELLOW}⚠️  Running as root is not recommended${NC}"
    echo "Please create a regular user and run this script"
    exit 1
fi

# Get username
USERNAME=$(whoami)
REPO_URL="https://github.com/nishkarshk212/titanic-saver.git"
BOT_DIR="$HOME/telegram-bot"

echo "📋 This script will:"
echo "  1. Update system packages"
echo "  2. Install Python and dependencies"
echo "  3. Clone the repository"
echo "  4. Set up virtual environment"
echo "  5. Install Python packages"
echo "  6. Create systemd service"
echo "  7. Configure auto-start"
echo ""

read -p "Do you want to continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Deployment cancelled"
    exit 1
fi

echo ""
echo "========================================="
echo "Step 1: Updating System Packages"
echo "========================================="
sudo apt update
sudo apt upgrade -y
echo -e "${GREEN}✅ System updated${NC}"
echo ""

echo "========================================="
echo "Step 2: Installing Dependencies"
echo "========================================="
sudo apt install -y python3 python3-pip python3-venv git curl
echo -e "${GREEN}✅ Dependencies installed${NC}"
echo ""

echo "========================================="
echo "Step 3: Cloning Repository"
echo "========================================="
if [ -d "$BOT_DIR" ]; then
    echo "Directory already exists, pulling latest changes..."
    cd $BOT_DIR
    git pull
else
    git clone $REPO_URL $BOT_DIR
    cd $BOT_DIR
fi
echo -e "${GREEN}✅ Repository ready${NC}"
echo ""

echo "========================================="
echo "Step 4: Setting Up Virtual Environment"
echo "========================================="
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
echo -e "${GREEN}✅ Virtual environment created${NC}"
echo ""

echo "========================================="
echo "Step 5: Installing Python Packages"
echo "========================================="
pip install -r requirements.txt
echo -e "${GREEN}✅ Python packages installed${NC}"
echo ""

echo "========================================="
echo "Step 6: Configuring Environment"
echo "========================================="
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Created .env file from template"
    echo -e "${YELLOW}⚠️  Please edit .env with your credentials:${NC}"
    echo "   nano .env"
    echo ""
    read -p "Press Enter after configuring .env..."
else
    echo ".env file already exists"
fi
echo -e "${GREEN}✅ Environment configured${NC}"
echo ""

echo "========================================="
echo "Step 7: Testing MongoDB Connection"
echo "========================================="
if python3 test_mongodb.py; then
    echo -e "${GREEN}✅ MongoDB connection successful${NC}"
else
    echo -e "${YELLOW}⚠️  MongoDB test failed. You can configure it later.${NC}"
    echo "   Edit .env file with your MongoDB URI"
fi
echo ""

echo "========================================="
echo "Step 8: Creating Systemd Service"
echo "========================================="

SERVICE_FILE="/etc/systemd/system/telegram-bot.service"

sudo tee $SERVICE_FILE > /dev/null <<EOL
[Unit]
Description=Telegram Group Help Bot
After=network.target

[Service]
Type=simple
User=$USERNAME
WorkingDirectory=$BOT_DIR
ExecStart=$BOT_DIR/venv/bin/python3 bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Environment
Environment=PATH=$BOT_DIR/venv/bin
EnvironmentFile=$BOT_DIR/.env

[Install]
WantedBy=multi-user.target
EOL

echo -e "${GREEN}✅ Service file created${NC}"
echo ""

echo "========================================="
echo "Step 9: Enabling and Starting Service"
echo "========================================="
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot.service
sudo systemctl start telegram-bot.service
echo -e "${GREEN}✅ Service started${NC}"
echo ""

echo "========================================="
echo "Step 10: Checking Service Status"
echo "========================================="
sleep 3
sudo systemctl status telegram-bot.service --no-pager -l
echo ""

echo "========================================="
echo "✅ Deployment Complete!"
echo "========================================="
echo ""
echo "📊 Useful Commands:"
echo "  Check status:    sudo systemctl status telegram-bot.service"
echo "  View logs:       sudo journalctl -u telegram-bot.service -f"
echo "  Restart bot:     sudo systemctl restart telegram-bot.service"
echo "  Stop bot:        sudo systemctl stop telegram-bot.service"
echo "  Start bot:       sudo systemctl start telegram-bot.service"
echo ""
echo "📁 Bot Directory: $BOT_DIR"
echo "📝 Config File:   $BOT_DIR/.env"
echo "📋 Logs:          sudo journalctl -u telegram-bot.service"
echo ""
echo "🔧 Next Steps:"
echo "  1. Verify .env configuration: nano $BOT_DIR/.env"
echo "  2. Check bot logs: sudo journalctl -u telegram-bot.service -f"
echo "  3. Test bot commands in Telegram"
echo "  4. Monitor MongoDB Atlas dashboard"
echo ""
echo -e "${GREEN}🎉 Your bot is now running and will start automatically on boot!${NC}"
echo ""
