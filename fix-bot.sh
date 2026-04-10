#!/bin/bash

# Quick Fix Script for Bot Issues
# Run this on your server: bash fix-bot.sh

echo "========================================="
echo "🔧 Fixing Bot Issues..."
echo "========================================="
echo ""

# Stop your bot
echo "Step 1: Stopping bot service..."
systemctl stop telegram-bot.service
echo "✅ Service stopped"
echo ""

# Kill any duplicate processes
echo "Step 2: Killing duplicate bot processes..."
pkill -f "titanic-saver.*bot.py" 2>/dev/null
sleep 2
echo "✅ Duplicates killed"
echo ""

# Update code
echo "Step 3: Updating code..."
cd /root/titanic-saver
git pull
echo "✅ Code updated"
echo ""

# Upgrade dependencies
echo "Step 4: Updating dependencies..."
source venv/bin/activate
pip install -r requirements.txt
pip install --upgrade certifi
echo "✅ Dependencies updated"
echo ""

# Test MongoDB
echo "Step 5: Testing MongoDB..."
if python3 test_mongodb.py; then
    echo "✅ MongoDB working!"
else
    echo "⚠️  MongoDB test failed, but continuing..."
fi
echo ""

# Start bot
echo "Step 6: Starting bot..."
systemctl start telegram-bot.service
sleep 3
echo "✅ Bot started"
echo ""

# Check status
echo "Step 7: Checking status..."
systemctl status telegram-bot.service --no-pager -l
echo ""

# Show recent logs
echo "========================================="
echo "📋 Recent Logs:"
echo "========================================="
journalctl -u telegram-bot.service -n 20 --no-pager
echo ""

echo "========================================="
echo "✅ Fix Complete!"
echo "========================================="
echo ""
echo "📊 Useful Commands:"
echo "  View logs:    journalctl -u telegram-bot.service -f"
echo "  Check status: systemctl status telegram-bot.service"
echo "  Restart:      systemctl restart telegram-bot.service"
echo ""
echo "🧪 Test Your Bot:"
echo "  1. Open private chat with bot"
echo "  2. Send: Hello"
echo "  3. Bot should auto-reply!"
echo ""
echo "  4. Send: /tr hi Hello World"
echo "  5. Should translate to Hindi"
echo ""
