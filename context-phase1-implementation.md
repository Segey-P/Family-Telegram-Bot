# Implementation Context — Family Telegram Bot

**Status:** Deployed and in testing with family group.

**Purpose:** Weekly family video call coordinator. Bot lives in a Telegram group, sends a Friday poll asking who can join Sunday's call, handles time-zone-aware voting, and auto-confirms the time.

---

## Architecture

Single-file bot (`bot.py`) using `python-telegram-bot` with `APScheduler` for scheduled jobs. State persisted in JSON files (no database).

### Files

| File | Purpose |
|---|---|
| `bot.py` | All handlers, scheduler, helpers |
| `session.py` | Session init helpers (used by debug command) |
| `settings.json` | Admin-editable config (committed) |
| `sessions.json` | Runtime state — chat members, event status (NOT committed) |
| `user_timezones.json` | Global user tz cache — survives across sessions (NOT committed) |
| `pending_proposals.json` | Tracks which group a user is mid-proposal for (NOT committed) |

---

## Data Model

```yaml
# settings.json
call_time: "10:00"            # base call time (HH:MM in base_timezone)
base_timezone: "Europe/Minsk" # internal reference timezone
poll_enabled: true
test_mode: false              # speeds up all timers for testing

# sessions.json
<chat_id>:
  members:
    <user_id>:
      name: string
      timezone: string          # defaults to Europe/Minsk if not set
      first_seen: timestamp
      is_admin: bool
  event:
    status: idle | proposed | confirmed
    current_time: "HH:MM"       # in base_timezone
    proposal_author: <user_id>
    deadline: timestamp          # UTC ISO datetime — when auto-confirm fires
    responses:
      <user_id>: yes | no | pending
    last_poll_id: int            # Telegram message_id of latest control message (for cleanup)
    reminder_30_sent: bool       # true after 30-min reminder fires (one-shot per cycle)
    reminder_5_sent: bool        # true after 5-min reminder fires (one-shot per cycle)
    call_date: "YYYY-MM-DD"      # intended date of the call — without this, reminders
                                 # would fire a day early when confirmation happens before
                                 # the call time on the invite day (historical bug, fixed)
  last_active: timestamp
```

---

## Commands

### User (anyone in group)

| Command | Behavior |
|---|---|
| `/tz Europe/Berlin` | Set timezone. Fuzzy-matched (e.g. "Berlin" works). Saved globally — applies to all chats. |
| `/mytime` | Show current time + next Sunday call time in user's local timezone |
| `/help` | List commands (admin commands shown only to admins) |

### Admin (first user to interact)

| Command | Behavior |
|---|---|
| `/time 10:00 Europe/Minsk` | Update base call time + timezone |
| `/poll on\|off` | Enable/disable Friday invites |
| `/test_mode on\|off` | Speed up all timers (poll every 10 min, deadline 1 min) |
| `/debug_invite` | Trigger Friday invite manually |

---

## Default Timezone

New users default to `Europe/Minsk`. No setup required — they can interact with the bot immediately. Override any time with `/tz`.

---

## Weekly Flow

### Friday (12:00, or every 10 min in test mode)

Bot sends group message:
```
Созвон в воскресенье:

• Сергей: 10:00 (Europe/Minsk)
• Аня: 09:00 (Europe/Berlin)
• Миша: 01:00 (America/Vancouver)

Подходит?
```
Buttons: ✅ Подходит | 🔄 Предложить другое | ❌ Не смогу

### Time Proposal Flow

1. User taps "🔄 Предложить другое" in group chat
2. Bot sends **private message** with 6 time options (base ± 1h to +4h) in user's local timezone
3. User either **clicks a button** or **types a time** (e.g. `7:20`, `7.20`, `7 20`, `720`, `19:30`)
4. Typed time is treated as user's local timezone, converted to base timezone
5. Bot sends group notification with time in all members' timezones:
   ```
   Сергей предлагает новое время:

   • Сергей: 11:00 (Europe/Minsk)
   • Аня: 10:00 (Europe/Berlin)
   ...

   Подходит?
   ```
6. Others vote ✅ / ❌ / 🔄
7. All ✅ → immediate confirmation. Any ❌ → proposal rejected.
8. Timeout (12h, or 1 min in test mode) with no ❌ → auto-confirm

### Auto-Register

Any user who clicks a group button is auto-registered with `Europe/Minsk` as default timezone (or their previously set global timezone if they ran `/tz` in private chat with the bot). No manual registration required.

---

## Timezone Display

**All group messages show time in every member's local timezone.** The internal "base timezone" used for storage is never shown to users.

Format:
```
• Name: HH:MM (Timezone/Name)
```

Members sharing the same timezone are each listed separately (same time shown).

---

## Scheduled Jobs

| Job | Schedule | Purpose |
|---|---|---|
| `friday_invite` | Cron (configurable, default Sat 08:00 Minsk) | Sends weekly invite with voting buttons |
| `check_autoconfirm_job` | Interval, every 60s | Checks for expired deadlines; auto-confirms if no rejections |
| `reminder_check_job` | Interval, every 5min | Sends 30-min and 5-min reminders for confirmed events |

### Reminder Logic (`reminder_check_job`)

- Only processes events with `status == "confirmed"`
- Uses `call_date` + `current_time` to determine target datetime
- Without `call_date` (legacy events), falls back to "today or tomorrow" heuristic
- Resets reminder flags when state transitions happen mid-week (handles re-proposals)

### Known Fixes

- **Reminders firing a day early** (Jun 2026): The job previously assumed the call was "today" at the stored time. When confirmation happened on Saturday (invite day) before 17:00, reminders fired for Saturday 17:00 instead of Sunday 17:00. Fixed by adding `call_date` to the event dict — `friday_invite_job` sets it to Sunday, `handle_trigger` sets it to today.
- **Stale reminder flags** (Jun 2026): In-place event transitions (re-proposals, auto-confirm, text input) now reset `reminder_30_sent` and `reminder_5_sent` to `False`, preventing permanent reminder suppression after mid-week time changes.

## Outstanding Work

See `TODO.md`.
