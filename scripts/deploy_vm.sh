#!/bin/bash
set -e

# Family Telegram Bot — VM Deployment Script
# Run on Oracle VM: bash deploy_vm.sh <TELEGRAM_BOT_TOKEN>

if [ -z "$1" ]; then
    echo "Usage: bash deploy_vm.sh <TELEGRAM_BOT_TOKEN>"
    echo "Example: bash deploy_vm.sh 123456:ABCdef-GHIjkl"
    exit 1
fi

BOT_TOKEN="$1"
BOT_DIR="$HOME/family-telegram-bot"

echo "🚀 Deploying Family Telegram Bot..."

# 1. Clone repo (or pull if exists)
if [ -d "$BOT_DIR" ]; then
    echo "📁 Bot directory exists. Pulling latest..."
    cd "$BOT_DIR"
    git pull origin main
else
    echo "📁 Cloning repo..."
    git clone https://github.com/Segey-P/Family-Telegram-Bot.git "$BOT_DIR"
    cd "$BOT_DIR"
fi

# 2. Create virtual environment
if [ ! -d "venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv venv
fi

# 3. Activate and install dependencies
echo "📦 Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Create .env.local
echo "🔐 Creating .env.local..."
cat > .env.local <<EOF
TELEGRAM_BOT_TOKEN=$BOT_TOKEN
EOF
chmod 600 .env.local
echo "✓ Token saved securely (permissions: 600)"

# 5. Create systemd service
echo "⚙️  Creating systemd service..."
sudo tee /etc/systemd/system/family-telegram-bot.service > /dev/null <<EOF
[Unit]
Description=Family Telegram Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$BOT_DIR
Environment="PATH=$BOT_DIR/venv/bin"
ExecStart=$BOT_DIR/venv/bin/python bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 6. Reload systemd and start service
echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload
sudo systemctl enable family-telegram-bot
sudo systemctl start family-telegram-bot

# 7. Check status
echo "📊 Service status:"
sudo systemctl status family-telegram-bot --no-pager

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "  - View logs: sudo journalctl -u family-telegram-bot -f"
echo "  - Stop service: sudo systemctl stop family-telegram-bot"
echo "  - Restart service: sudo systemctl restart family-telegram-bot"
echo "  - Check status: sudo systemctl status family-telegram-bot"
