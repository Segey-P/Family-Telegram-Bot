# Family Telegram Bot

Frictionless coordination for weekly family calls across time zones. No voting, no manual calculations—just buttons and timezone awareness.

---

## Features (MVP)

- ✅ Collect timezone preferences from group members (no hardcoded users)
- ✅ Display all times in user's local timezone
- ✅ Friday: Send weekly invite with buttons
- ✅ Time proposal UI with re-rendering
- ✅ Automatic confirmation with timeout
- ✅ Sunday reminder (5 minutes before)
- ✅ Admin commands for settings
- ✅ All messages in Russian

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| Bot Framework | `python-telegram-bot` (v21+) |
| Timezone handling | `pytz` |
| Scheduling | `apscheduler` |
| Storage | `sessions.json` (local, not committed) |
| Deploy | Oracle Cloud (systemd) |

---

## Local Setup

### 1. Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Get Telegram Bot Token

Create a bot via [@BotFather](https://t.me/botfather) on Telegram and copy the token.

### 3. Create `.env.local`

```bash
TELEGRAM_BOT_TOKEN=your_token_here
```

### 4. Run locally

```bash
python bot.py
```

The bot will start polling for messages.

---

## Testing (Local)

### 1. Create a test group

Create a private Telegram group with 2–3 people (you + test users).

### 2. Add the bot

Search for your bot in Telegram and add it to the group.

### 3. Test commands

**User commands:**
- `/таймзона Европа/Берлин` — Set your timezone
- `/моевремя` — Show your local time + next call time
- `/помощь` — Show all commands

**Admin commands (first user is admin):**
- `/время 10:00 Америка/Ванкувер` — Update call time + base timezone
- `/опрос вкл` — Enable weekly invites
- `/опрос выкл` — Disable weekly invites

### 4. Verify behavior

- Each user sets timezone independently
- `/моевремя` displays correct local time
- No hardcoded user list—bot discovers members dynamically
- Admin is the first user to set timezone

---

## Specs & Documentation

- **`specs/context-phase1-implementation.md`** — Detailed implementation spec
- **`specs/plan-phase1.md`** — Phase breakdown and milestones
- **`TODO.md`** — Current task list (updated as work progresses)

---

## Deployment (Phase 2)

Deployment to Oracle Cloud with systemd service (stub in `deploy/`).

---

## Files

```
bot/
├── bot.py                              # Main bot + handlers
├── session.py                          # Session state management
├── settings.json                       # Default settings (committed)
├── sessions.json                       # Runtime sessions (NOT committed)
├── requirements.txt                    # Dependencies
├── .gitignore                          # Exclude sessions, .env, venv
├── README.md                           # This file
├── CLAUDE.md                           # Agent instructions
├── AGENTS.md                           # Agent-neutral context
├── TODO.md                             # Current tasks
└── specs/
    ├── context-phase1-implementation.md
    └── plan-phase1.md
```

---

## Next Steps

- [ ] Finish M1–M3 (setup, session management, core commands)
- [ ] Implement M4–M5 (timezone math, Friday invite)
- [ ] Build M6–M8 (proposal UI, response tracking, auto-confirm)
- [ ] Test in private group, then move to family group

See `TODO.md` for current progress.

---

**Status:** Phase 1 in progress  
**Repo:** https://github.com/Segey-P/Family-Telegram-Bot  
**Last Updated:** 2026-05-05
