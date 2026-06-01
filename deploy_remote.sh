#!/bin/bash

# Server Details
IP="140.245.56.100"
USER="root"
export SSHPASS="Akshay343402355468"
PORT="22"
REPO_URL="https://github.com/nishkarshk212/titanic-saver.git"
BOT_DIR="/root/bot"

# SSH Command with sshpass using environment variable
SSH_CMD="sshpass -e ssh -p $PORT -o StrictHostKeyChecking=no $USER@$IP"

echo "🚀 Starting deployment to $IP..."

# 1. Update and Install dependencies on the server
echo "📦 Installing dependencies on server..."
$SSH_CMD "apt-get update && apt-get install -y git python3 python3-pip screen"

# 2. Clone or Update Repo
echo "📂 Setting up project directory..."
$SSH_CMD "if [ ! -d '$BOT_DIR' ]; then git clone $REPO_URL $BOT_DIR; else cd $BOT_DIR && git pull; fi"

# 3. Upload .env file using cat
echo "📝 Uploading .env file..."
$SSH_CMD "cat <<EOF > $BOT_DIR/.env
BOT_TOKEN=8619991922:AAFgIOwAU7b2Tju48oK7JAu2l4_DcdY_SRY
MONGO_URI=mongodb+srv://mybotpanda_db_user:hx0n5AI90lFGyl93@grouphelp.puxyti8.mongodb.net/?appName=GROUPHELP
OWNER_ID=8791884726
LOG_CHANNEL_ID=-1003757375746

# Telethon Configuration
API_ID=39591192
API_HASH=93635783ddd5e3eacfc512effe2e3de2
STRING_SESSION=1AZWarzkBu8T9PwWZbTfLLCFe6m0fzTu3uKG8Qdoxl8HRDm5pfPL9N_ErhWJEUIDWEraDCTbGwjXHT8JA-eHL_G02isjBQK0Lst4kBeMpfaY6U-lhajnEAw9vtBS5ehjQX1uLF2X_VxgC1kr6AttHgspPwui-iohq_cl8v75PmWcUeGe4RrC4quSZBQ4D4rnoVBRArOsefFG7OERy1S8jeEDuR6M_LGLlQN4ZHi7bg2F0d3kvI9SR2gC36yKr7txmShFR5QiJfJK5hcatjKSCOBDmgD5ypvn9DFWRDYJFqpGAd0gdjamCk56XOcLmb-w4nYRusb61a5QxXEooWlrA8KZ5-U5r0kw=
EOF"

# 4. Install python requirements
echo "🐍 Installing requirements..."
$SSH_CMD "cd $BOT_DIR && pip3 install -r requirements.txt"

# 5. Run the bot using screen
echo "🤖 Starting the bot in screen..."
$SSH_CMD "screen -XS bot quit || true" # Kill existing screen if any
$SSH_CMD "cd $BOT_DIR && screen -dmS bot python3 bot.py"

echo "✅ Deployment successful!"
echo "You can check the bot status by logging into the server and running: screen -r bot"
