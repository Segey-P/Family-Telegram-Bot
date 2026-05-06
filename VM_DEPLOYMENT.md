# Family Telegram Bot — VM Deployment Guide

Deploy to your existing Oracle Cloud VM alongside bcscout bot.

---

## Prerequisites

- Oracle Cloud VM (already provisioned)
- SSH access via `ssh bcscout`
- Bot token from Telegram BotFather (stored in Bitwarden)
- Existing bot (bcscout) is running — this won't interfere

---

## Deployment Steps

### 1. Get the bot token from Bitwarden
Your Telegram bot token (secure, don't share).

### 2. SSH to your VM
```bash
ssh bcscout
```

### 3. Download and run deployment script
```bash
# Download the script
curl -sSL https://raw.githubusercontent.com/Segey-P/Family-Telegram-Bot/main/scripts/deploy_vm.sh -o deploy_family_bot.sh

# Run with your bot token
bash deploy_family_bot.sh <TELEGRAM_BOT_TOKEN>
```

**Example:**
```bash
bash deploy_family_bot.sh 123456:ABCdef-GHIjkl_MnopQR
```

The script will:
1. Clone/pull the repo to `~/family-telegram-bot`
2. Create a Python virtual environment
3. Install dependencies (`python-telegram-bot`, `pytz`, `apscheduler`)
4. Create `.env.local` with your token (permissions: `600` — readable only by you)
5. Create a systemd service `family-telegram-bot` (auto-restarts on crash)
6. Start the service and confirm it's running

**Output will show:**
```
✅ Deployment complete!

Next steps:
  - View logs: sudo journalctl -u family-telegram-bot -f
  - Stop service: sudo systemctl stop family-telegram-bot
  - Restart service: sudo systemctl restart family-telegram-bot
  - Check status: sudo systemctl status family-telegram-bot
```

---

## Verify It Works

### Check service is running
```bash
sudo systemctl status family-telegram-bot
```

Expected output:
```
● family-telegram-bot.service - Family Telegram Bot
   Loaded: loaded
   Active: active (running) since [timestamp]
```

### View live logs
```bash
sudo journalctl -u family-telegram-bot -f
```

Look for:
```
INFO [bot] Family Telegram Bot started
```

### Test in Telegram
1. Add bot to a test group
2. Send `/tz` — bot should respond with "Set your timezone"
3. Send `/help` — bot should list available commands

---

## Operations

### Stop the bot
```bash
sudo systemctl stop family-telegram-bot
```

### Restart the bot
```bash
sudo systemctl restart family-telegram-bot
```

### View last 50 lines of logs
```bash
sudo journalctl -u family-telegram-bot -n 50
```

### View logs from last hour
```bash
sudo journalctl -u family-telegram-bot --since "1 hour ago"
```

### Update to latest code
```bash
cd ~/family-telegram-bot
git pull origin main
sudo systemctl restart family-telegram-bot
```

---

## Troubleshooting

### Service won't start
Check logs:
```bash
sudo journalctl -u family-telegram-bot -n 100
```

Common issues:
- **Invalid token** — verify token in `~/.env.local` matches Bitwarden
- **Port conflict** — unlikely (bot uses Telegram API, not a local port)
- **Python not found** — verify venv was created: `ls ~/family-telegram-bot/venv`

### Bot running but not responding
1. Confirm bot is in the group chat
2. Check logs for errors: `sudo journalctl -u family-telegram-bot -f`
3. Verify token hasn't expired (check Bitwarden)

### Want to stop both bots temporarily
```bash
sudo systemctl stop family-telegram-bot
sudo systemctl stop bcscout  # if needed
```

---

## Rollback

If you need to remove this bot:
```bash
sudo systemctl stop family-telegram-bot
sudo systemctl disable family-telegram-bot
sudo systemctl daemon-reload
rm -rf ~/family-telegram-bot
```

The `bcscout` bot will continue running unaffected.

---

## Next: Multi-User Testing

Once deployed and verified working:
1. Add real family members to the test group
2. Run 2–3 weekly cycles (Friday invite → voting → Sunday reminder)
3. Document any issues in the GitHub repo

See `TODO.md` for **Phase 2B: Multi-User Testing** checklist.
