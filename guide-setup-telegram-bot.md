# Setup Guide: Telegram Bot API & Local Testing

**Goal:** Create a Telegram bot, get its API token, store it securely, and run it locally.

---

## Part 1: Create Bot in Telegram (5 minutes)

### Step 1: Open BotFather

In Telegram, search for **@BotFather** (official Telegram bot manager).

Click **Start** or send `/start`

### Step 2: Create New Bot

Send `/newbot`

BotFather will ask:

1. **"Alright, a new bot. How are we going to call it? Please choose a name for your bot."**
   - Enter: `Family Call Coordinator` (or any name you like)
   - ✅ Reply: Family Call Coordinator

2. **"Good. Now let's choose a username for your bot. It must end in bot (e.g. TetrisBot or tetris_bot)."**
   - Enter: `family_call_bot` (or something unique like `sergey_family_bot`)
   - ✅ Reply: family_call_bot
   - Telegram checks availability. If taken, try a variation with numbers/underscores.

### Step 3: Receive Your Token

BotFather will send:

```
Done! Congratulations on your new bot. You will find it at t.me/YOUR_BOT_NAME. 
You can now add a description, about section, and commands. 
Commands are listed by the /setcommands command.

Use this token to access the HTTP API:
🔐 1234567890:ABCDefGHijKLmnoPQRstUVwxyz_AbCdEfGH
Keep your token secure and store it safely!
```

**⚠️ SAVE THIS TOKEN IMMEDIATELY** — you'll need it in the next step.

---

## Part 2: Store Token Securely (5 minutes)

### Option 1: Bitwarden (Recommended) 🏆

**Why:** Encrypted, searchable, syncs across devices, you won't lose it.

1. Open **Bitwarden** (or your password manager)
2. Create a new **Login** item:
   - **Name:** `Telegram Family Bot Token`
   - **Username:** `family_call_bot`
   - **Password:** `1234567890:ABCDefGHijKLmnoPQRstUVwxyz_AbCdEfGH` (paste the token from BotFather)
   - **Notes:** 
     ```
     Bot created: 2026-05-05
     Telegram handle: @family_call_bot
     Github: https://github.com/Segey-P/Family-Telegram-Bot
     ```
3. Save

**Later:** When you need it, search Bitwarden for "Telegram Family Bot" → copy password.

### Option 2: Encrypted Notes (Fallback)

If you don't use Bitwarden:

1. Open **Apple Notes** (or any notes app)
2. Create note: "Telegram Bots"
3. Add:
   ```
   Family Call Bot (@family_call_bot)
   Token: 1234567890:ABCDefGHijKLmnoPQRstUVwxyz_AbCdEfGH
   Created: 2026-05-05
   ```
4. Lock the note (or password-protect it)

**⚠️ Never commit the token to GitHub or paste in code.**

---

## Part 3: Local Environment Setup (10 minutes)

### Step 1: Create `.env.local` file

In the project root (`6. Family-Telegram-Bot/`), create a file called `.env.local`:

```bash
cd "/Users/sergeypochikovskiy/AI_workspace/Projects/6. Family-Telegram-Bot"
nano .env.local
```

(Or use any editor: VS Code, TextEdit with plain text mode, etc.)

### Step 2: Paste Token

Inside `.env.local`, add:

```
TELEGRAM_BOT_TOKEN=1234567890:ABCDefGHijKLmnoPQRstUVwxyz_AbCdEfGH
```

Replace with your actual token from BotFather.

### Step 3: Save & Verify

- **Save the file** (Ctrl+S or Cmd+S)
- Verify it's in the right place:

```bash
ls -la "/Users/sergeypochikovskiy/AI_workspace/Projects/6. Family-Telegram-Bot/.env.local"
```

Should show the file exists.

### Step 4: Confirm `.gitignore`

Verify `.env.local` is in `.gitignore` so it never gets committed:

```bash
grep ".env.local" "/Users/sergeypochikovskiy/AI_workspace/Projects/6. Family-Telegram-Bot/.gitignore"
```

Should output: `.env.local` ✅

(If not, it's already there—we added it earlier.)

---

## Part 4: Install Dependencies (5 minutes)

### Step 1: Create Virtual Environment

```fish
cd "/Users/sergeypochikovskiy/AI_workspace/Projects/6. Family-Telegram-Bot"
python3 -m venv venv
```

This creates a `venv/` folder with isolated Python.

### Step 2: Activate Virtual Environment (Fish Shell)

Fish shell has different syntax than bash. Use:

```fish
source venv/bin/activate.fish
```

You should see `(venv)` at the start of your terminal prompt.

**Note:** If you're using bash instead of fish, use: `source venv/bin/activate`

### Step 3: Install Requirements

```fish
pip install -r requirements.txt
```

Output should show:
```
Successfully installed python-telegram-bot-21.x.x pytz-2024.x apscheduler-3.x.x python-dotenv-1.x.x
```

---

## Part 5: Run Bot Locally (5 minutes)

### Step 1: Start the Bot

```fish
cd "/Users/sergeypochikovskiy/AI_workspace/Projects/6. Family-Telegram-Bot"
source venv/bin/activate.fish  # Activate venv (fish syntax)
python bot.py
```

Expected output:

```
2026-05-05 10:30:45,123 INFO bot — Starting bot...
2026-05-05 10:30:47,456 INFO bot — Scheduler initialized with Friday invite + auto-confirm jobs
2026-05-05 10:30:48,789 INFO telegram.ext._application — Application initialized
```

**The bot is now running and listening for messages.**

### Step 2: Keep the Terminal Open

- Leave this terminal running the whole time you're testing
- If you close it → bot stops
- If your Mac goes to sleep → connection pauses

### Step 3: Stop the Bot (When Done)

Press **Ctrl+C** in the terminal.

---

## Part 6: Test the Bot (10 minutes)

### Step 1: Open Telegram

On your phone or desktop, open **Telegram**.

### Step 2: Find Your Bot

Search for your bot by its handle: `@family_call_bot` (or whatever you named it).

Click on the bot name → **Open Chat**.

### Step 3: Send `/start`

Type `/start` and send.

Expected response:

```
👋 Привет! Я помогу координировать еженедельный созвон.

Сначала установите вашу временную зону:
/таймзона Европа/Берлин

Для справки: /помощь
```

✅ **Bot is working!**

### Step 4: Test Commands

Try these commands in the chat:

| Command | Expected Response |
|---------|---|
| `/таймзона America/Vancouver` | ✅ Сохранено: America/Vancouver |
| `/таймзона Europe/Berlin` | ✅ Сохранено: Europe/Berlin |
| `/моевремя` | Shows your current local time + next Sunday call time |
| `/помощь` | Lists all commands |
| `/опрос вкл` | ⚠️ "Только администратор может это делать" (you're admin in group, not in private chat) |

### Step 5: Test with Group

To test with others:

1. **Create a private test group** (Telegram: new group, add you + 1–2 test people)
2. **Add bot to group:** Search for `@family_call_bot` → **Add bot**
3. **In the group, send commands:**
   - `/таймзона Европа/Берлин` (each person sets their timezone)
   - `/моевремя` (verify each person sees their local time)
   - `/опрос вкл` (you're admin if you created the group)

---

## Part 7: Token Safety Checklist ✅

- [ ] Token stored in Bitwarden (or password manager) ✅
- [ ] `.env.local` created with token ✅
- [ ] `.env.local` is in `.gitignore` ✅
- [ ] `git status` shows `.env.local` is NOT staged ✅
- [ ] Token has NEVER been pushed to GitHub ✅
- [ ] No token in code (`bot.py`, `settings.json`, etc.) ✅

**To verify:**

```bash
# Check .env.local is ignored
git status | grep ".env.local"
# (Should output nothing or "ignored")

# Check no token in git
git log -p | grep "ABCDef"
# (Should output nothing—no token in history)
```

---

## Part 8: Troubleshooting

| Problem | Solution |
|---------|----------|
| **Bot not responding** | Check terminal—is `python bot.py` still running? Press Ctrl+C and restart. |
| **"TELEGRAM_BOT_TOKEN not set"** | Check `.env.local` exists and has correct token. Restart bot. |
| **"Invalid token"** | Double-check token in `.env.local` matches BotFather's message (no extra spaces). |
| **Bot says "only admin"** | In private chat, you can't use admin commands. Test in group chat. |
| **Commands not showing in Telegram UI** | Restart bot: Ctrl+C, then `python bot.py`. Give Telegram 10 seconds to refresh. |
| **"ModuleNotFoundError: No module named telegram"** | Did you run `pip install -r requirements.txt`? Check `venv` is activated (`(venv)` in prompt). |
| **Lost the token** | Check Bitwarden. If lost: Go back to BotFather `/revoke` and `/newbot` to generate a new one. |

---

## Next Steps

Once bot is running and responding:

1. **Add real test users** (family/friends via test group)
2. **Test Friday invite flow:**
   - Manually trigger Friday job (we'll add a debug command for this)
   - Verify group gets invite message
   - Click buttons, test proposals
3. **Run through full flow:**
   - Friday: Invite sent
   - User proposes different time
   - Auto-confirm checks (wait up to 12 hours, or we speed it up for testing)
   - Sunday reminder (Phase 1.5)

---

## Quick Reference (Fish Shell)

**Start bot:**
```fish
cd "/Users/sergeypochikovskiy/AI_workspace/Projects/6. Family-Telegram-Bot"
source venv/bin/activate.fish
python bot.py
```

**Stop bot:** Ctrl+C

**Get token:** Bitwarden → search "Telegram Family Bot" → copy password

**Reset venv:** `rm -rf venv` → `python3 -m venv venv` → `source venv/bin/activate.fish` → `pip install -r requirements.txt`

**Note:** All commands use **fish** shell syntax. If using bash, replace `source venv/bin/activate.fish` with `source venv/bin/activate`

---

**Status:** Ready for local testing  
**Next:** Add debug command to manually trigger Friday job for faster testing
