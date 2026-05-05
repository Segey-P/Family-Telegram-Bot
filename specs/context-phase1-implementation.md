# Phase 1 Implementation Context — Family Telegram Bot

**Scope:** MVP for single weekly family call coordination across timezones.

**Target:** Collect user timezones, send Friday invite, handle time proposals, auto-confirm by Sunday.

---

## Data Model (Phase 1)

```yaml
# settings.json (committed, admin-editable)
settings:
  default_time: "10:00"           # base time (America/Vancouver)
  base_timezone: "America/Vancouver"
  poll_enabled: true
  poll_day: "Friday"
  poll_time: "12:00"              # when to send invite
  auto_confirm_hours: 12          # deadline for auto-confirm
  call_day: "Sunday"
  call_time: "10:00"              # base time of the actual call

# sessions.json (runtime, NOT committed)
sessions:
  <chat_id>:
    members:
      <user_id>:
        name: string
        timezone: string
        first_seen: timestamp
    event:
      proposal_id: string          # e.g., "event_2026_05_05"
      status: idle | proposed | confirmed
      current_time: "HH:MM"        # in base_timezone
      proposal_author: <user_id>
      deadline: timestamp
      responses:
        <user_id>: yes | no | pending
    last_active: timestamp
```

---

## Phase 1 Commands (Russian)

### User Commands

| Command | Behavior |
|---------|----------|
| `/таймзона Европа/Берлин` | Store user's timezone. Validate tz name. Reply "✅ Сохранено" |
| `/моевремя` | Show what time it is in user's timezone right now + next Sunday call time in user local |
| `/помощь` | List all commands |

### Admin Commands

Admin = user who started the bot or was invited first (store `is_admin: true` on first join).

| Command | Behavior |
|---------|----------|
| `/время 10:00 Америка/Ванкувер` | Update base time + timezone. Requires admin. |
| `/опрос вкл` | Enable Friday invites. Requires admin. |
| `/опрос выкл` | Disable Friday invites. Requires admin. |

---

## Weekly Flow (Phase 1)

### Friday (trigger time set in settings.json)

1. **Scheduler sends group message (RU):**
   ```
   Созвон в воскресенье:
   
   Базовое время: 10:00
   
   Подходит?
   ```
   Buttons: ✅ Подходит | 🔄 Предложить другое | ❌ Не смогу

2. **On proposal (user taps 🔄):**
   - Private message with time options (base_time ± 2h to +3h)
   - UI shows time in **user's local timezone**
   - Re-renders on each click
   - **Example (RU):**
     ```
     Выберите время:
     
     🕗 08:00
     🕘 09:00
     👉 🕙 10:00
     🕚 11:00
     🕛 12:00
     🕐 13:00
     ```

3. **On time selection:**
   - Private feedback: `Принято 👍 Уведомил всех`
   - Group message: `[Name] предлагает новое время: ➡️ 11:00 — Подходит?`
   - **Resets** all pending responses

4. **Response accumulation:**
   - Track ✅ (yes), ❌ (no), 🔄 (propose new)
   - Any ❌ → proposal rejected (do nothing, await new proposal)
   - All ✅ → confirmed (show status)
   - Timeout (`auto_confirm_hours`) with no ❌ → auto-confirm

### Sunday (5 min before call)

- Reminder: `⏰ Созвон через 5 минут. Готовы?`
- Buttons: ✅ Да | ⏳ +5 минут | ⏳ +15 минут
- First click wins; lock further delays for 2–3 min

---

## Session Initialization

When bot joins group chat:
1. Create `session[chat_id]`
2. For each member: `members[user_id] = {name: first_name, timezone: null, first_seen: now}`
3. Mark first user as `is_admin: true`
4. Event state: `idle`

When new user joins:
- Add to `members` with `timezone: null`
- Prompt: `/таймзона Европа/Берлин`

---

## Error Handling (Phase 1)

| Situation | Response (RU) |
|-----------|--------------|
| Invalid timezone | Suggest correct format: "Используйте формат: Европа/Берлин. Список: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones" |
| User missing timezone | Prompt on next interaction: "Пожалуйста, установите вашу временную зону: `/таймзона Европа/Берлин`" |
| Admin command from non-admin | "Только администратор может это делать." |
| Malformed `/время` command | "Формат: `/время HH:MM Америка/Ванкувер`" |

---

## No Hardcoded Users

- Bot discovers members via `group_chat_member_update` (new members, left members)
- Admin = user who sent the first command (store `is_admin: true`)
- Admin can be transferred via `/сделать_админ @username` (Phase 2)

---

## Files to Create (Phase 1)

```
bot/
├── bot.py                 # Main async bot + handlers
├── session.py             # Session load/save + state mgmt
├── config.py              # Config file handling (settings.json)
├── tz_utils.py            # Timezone validation + conversion
├── requirements.txt       # Dependencies
├── settings.json          # Default settings (committed)
├── .gitignore             # Exclude sessions.json, .env, venv
└── deploy/
    └── systemd.service    # Service file for Oracle Cloud
```

---

## Dependencies (Phase 1)

- `python-telegram-bot>=21.0`
- `pytz` (timezone handling)
- `apscheduler>=3.10` (scheduler for Friday/Sunday jobs)
- `python-dotenv` (local .env for TELEGRAM_BOT_TOKEN)

---

## Testing Strategy

1. **Local test:** Add bot to small private group (you + 1–2 test users)
2. **Commands:** Test `/таймзона`, `/моевремя`, `/помощь` with different timezones
3. **Friday flow:** Manually trigger scheduler, verify invite + button responses
4. **Proposal flow:** Test time selection in private chat
5. **Auto-confirm:** Verify timeout logic + group message status

---

## Exit Criteria (Phase 1 Done)

- ✅ Bot joins group, initializes session
- ✅ `/таймзона` stores timezone, validates tz name
- ✅ `/моевремя` shows correct local time
- ✅ Friday at poll_time: group invite with buttons
- ✅ Time proposal UI (private, re-renders on click)
- ✅ Response tracking + auto-confirm timeout
- ✅ Sunday -5min reminder (manual trigger for now)
- ✅ All messages in Russian
- ✅ Sessions saved/loaded from `sessions.json`
- ✅ Error messages in Russian
