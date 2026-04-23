#!/bin/bash

# Fix Multiple Bot Instances
# Run this on the server: bash fix_instances.sh

echo "========================================="
echo "  🔧 Fixing Multiple Bot Instances"
echo "========================================="
echo ""

# Step 1: Stop systemd service
echo "🛑 Stopping systemd service..."
systemctl stop titanic-bot.service
sleep 1

# Step 2: Kill ALL bot processes
echo "💀 Killing all bot processes..."
pkill -9 -f '/root/telegram-bot/venv/bin/python3 bot.py'
sleep 2

# Step 3: Verify all killed
echo "🔍 Checking for remaining processes..."
REMAINING=$(ps aux | grep 'telegram-bot.*bot.py' | grep -v grep | wc -l)

if [ "$REMAINING" -gt 0 ]; then
    echo "⚠️  Found $REMAINING remaining processes. Force killing..."
    pkill -9 -f 'bot.py'
    sleep 2
fi

# Step 4: Start fresh with systemd
echo "🚀 Starting bot with systemd..."
systemctl start titanic-bot.service
sleep 3

# Step 5: Verify
echo ""
echo "✅ Verification:"
echo "-----------------------------------------"
COUNT=$(ps aux | grep 'telegram-bot.*bot.py' | grep -v grep | wc -l)
echo "Bot instances running: $COUNT"
echo ""

if [ "$COUNT" -eq 1 ]; then
    echo "✅ Perfect! Only 1 instance running."
    echo ""
    echo "📊 Service Status:"
    systemctl status titanic-bot.service --no-pager -l | head -10
else
    echo "⚠️  Warning: $COUNT instances found!"
    echo "Running processes:"
    ps aux | grep 'telegram-bot.*bot.py' | grep -v grep
fi

echo ""
echo "========================================="
echo "  ✅ Fix Complete!"
echo "========================================="
