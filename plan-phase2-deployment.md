# Phase 2: Deployment & Multi-User Testing Plan

**Goal:** Move bot from local laptop to Oracle Cloud VM, test with real family group (5+ users), and solidify reliability before long-term use.

---

## Phase 2A: Oracle Cloud VM Setup

### Prerequisites
- Oracle Cloud account with VPS quota
- SSH key pair (generated locally)
- DNS or static IP for the VPS
- Bot token stored in Bitwarden (safe from git)

### Steps

#### 1. Provision VM (Ubuntu 22.04 LTS)
```bash
# Oracle Cloud Console: Compute → Instances
# Image: Ubuntu 22.04 Minimal
# Shape: Ampere (free tier: 4 CPU, 24 GB RAM, 200 GB storage)
# VCN: default
# Public IP: Assign
```

#### 2. SSH Setup
```bash
# Local: Copy public key
cat ~/.ssh/id_rsa.pub

# Cloud console: Paste into "SSH Key" field during instance creation

# SSH in:
ssh ubuntu@<VM_PUBLIC_IP>
sudo apt update && sudo apt upgrade -y
```

#### 3. Install Dependencies
```bash
sudo apt install -y python3.10 python3-pip python3-venv git

# Clone repo
cd ~
git clone https://github.com/Segey-P/Family-Telegram-Bot.git
cd Family-Telegram-Bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 4. Environment Setup
```bash
# Create .env.local with token (NOT committed)
cat > .env.local <<EOF
TELEGRAM_BOT_TOKEN=<token_from_bitwarden>
EOF

chmod 600 .env.local
```

#### 5. Create Systemd Service
```bash
sudo cat > /etc/systemd/system/family-bot.service <<EOF
[Unit]
Description=Family Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/Family-Telegram-Bot
Environment="PATH=/home/ubuntu/Family-Telegram-Bot/venv/bin"
ExecStart=/home/ubuntu/Family-Telegram-Bot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable family-bot
sudo systemctl start family-bot
sudo systemctl status family-bot
```

#### 6. Logging & Monitoring
```bash
# View logs
sudo journalctl -u family-bot -f

# Log rotation (optional)
sudo cat > /etc/logrotate.d/family-bot <<EOF
/var/log/family-bot/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
}
EOF
```

### Checklist
- [ ] VM provisioned with public IP
- [ ] SSH access confirmed
- [ ] Python + dependencies installed
- [ ] Repo cloned, venv created, pip install done
- [ ] `.env.local` created with bot token
- [ ] Systemd service installed and running
- [ ] Logs viewable via `journalctl`

---

## Phase 2B: Multi-User Testing (5+ Users, 2–3 Weeks)

### Participants
- **Serge** (operator, admin)
- **Family member 1** (different timezone, e.g., Europe)
- **Family member 2** (different timezone, e.g., Asia)
- **Family member 3** (same timezone as Serge)
- **Optional: 1–2 more** (extended family)

### Test Plan

#### Week 1: Functionality
1. **Friday invite** — Bot sends proposal at 12:00
   - All members receive + set timezone (if not already)
   - Test: `/tz`, `/mytime`

2. **Time proposal** — One member clicks "Предложить другое"
   - Verify private message shows correct times in their timezone
   - Select alternative time
   - Verify group sees proposal with correct timezone context

3. **Voting** — All members vote yes/no
   - Verify buttons work without crashes
   - Verify auto-confirm at 12-hour mark
   - Check responses are tracked correctly

#### Week 2: Edge Cases
1. **Concurrent votes** — Multiple people click buttons simultaneously
   - No race conditions, no duplicate messages
2. **Rapid proposal changes** — Person proposes 2x in 5 minutes
   - Responses reset correctly
3. **Timezone DST changes** — If applicable
   - Times still convert correctly
4. **Offline/re-join** — User leaves group, re-joins
   - Session persists, timezone remembered

#### Week 3: Reliability
1. **VM uptime** — No crashes for 7+ days
2. **Long message threads** — Verify no performance degradation
3. **Multiple groups** (optional) — Add bot to 2nd family group
   - Sessions don't collide

### Feedback Collection
- Document issues/crashes in `docs/phase2-testing-log.md`
- Note any UX confusion (bad wording, unclear buttons, etc.)
- Track bugs in GitHub Issues

---

## Phase 2C: Enhancements (If Time)

### Low-Priority Features (Post-MVP)
- [ ] **Delay button handling** — First click wins, 2-3 min lock (prevent double-votes)
- [ ] **Transfer admin** — `/makeadmin @username` command
- [ ] **Recurring intervals** — Support bi-weekly, monthly calls (not just weekly)
- [ ] **Notifications** — Optional SMS/email reminder (integrations later)

---

## Rollback Plan

If deployment fails or issues arise:
1. Stop systemd service: `sudo systemctl stop family-bot`
2. Revert to local bot (use old laptop as fallback)
3. Debug in local test group
4. Redeploy once fixed

---

## Success Criteria

✅ Phase 2 is done when:
- VM is stable for 2+ weeks with zero unplanned restarts
- 5+ family members tested all flows without confusion
- No critical bugs (crashes, lost data, timezone errors)
- Ops guide written for handoff (restart procedures, logs, etc.)
- Ready for long-term production use

---

## Timeline Estimate

| Task | Est. Time |
|------|-----------|
| Provision + setup VM | 1 hour |
| Systemd service | 0.5 hour |
| Multi-user coordination + testing | 2 weeks |
| Bug fixes (if any) | 0.5 – 2 hours |
| Documentation | 1 hour |
| **Total** | ~2 weeks + 4 hours |

