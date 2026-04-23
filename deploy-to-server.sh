#!/bin/bash

# Deployment Script for Titanic Saver Bot
# This script pulls latest changes and restarts the bot

SERVER_IP="161.118.250.195"
SERVER_USER="root"
BOT_DIR="/root/telegram-bot"

echo "========================================="
echo "  Titanic Saver Bot Deployment Script"
echo "========================================="
echo ""

# Step 1: Pull latest changes from git
echo "📦 Pulling latest changes from git..."
ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_IP} "cd ${BOT_DIR} && git pull origin main"

if [ $? -eq 0 ]; then
    echo "✅ Git pull successful!"
else
    echo "❌ Git pull failed!"
    exit 1
fi

echo ""

# Step 2: Stop the running bot
echo "🛑 Stopping the bot..."
ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_IP} "pkill -f 'python3 bot.py'"

if [ $? -eq 0 ]; then
    echo "✅ Bot stopped!"
else
    echo "⚠️  No running bot found or failed to stop"
fi

echo ""

# Step 3: Wait a moment
echo "⏳ Waiting 2 seconds..."
sleep 2

# Step 4: Start the bot
echo "🚀 Starting the bot..."
ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_IP} "cd ${BOT_DIR} && nohup ${BOT_DIR}/venv/bin/python3 bot.py > bot.log 2>&1 &"

if [ $? -eq 0 ]; then
    echo "✅ Bot started!"
else
    echo "❌ Failed to start bot!"
    exit 1
fi

echo ""

# Step 5: Verify bot is running
echo "🔍 Verifying bot is running..."
sleep 3
ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_IP} "ps aux | grep 'python3 bot.py' | grep -v grep"

echo ""
echo "========================================="
echo "  ✅ Deployment Complete!"
echo "========================================="
echo ""
echo "Check bot logs with:"
echo "  ssh root@${SERVER_IP} 'tail -f ${BOT_DIR}/bot.log'"
echo ""
