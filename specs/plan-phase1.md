# Phase 1 Implementation Plan

## Overview
Build MVP: single weekly call coordination. Bot joins group, collects timezones, sends Friday invite, manages proposals, auto-confirms by Sunday.

## Milestones

### M1: Project Setup
- [x] Specs written (`context-phase1-implementation.md`)
- [ ] Requirements.txt with dependencies
- [ ] `.gitignore` updated (sessions.json, .env, venv)
- [ ] `settings.json` created (defaults)
- [ ] README.md updated with setup + local testing steps

### M2: Session Management
- [ ] `session.py`: Load/save sessions from `sessions.json`
- [ ] Session model: chat_id → members → {user_id, name, timezone, is_admin}
- [ ] Group join/leave detection (`group_chat_member_update`)
- [ ] First user auto-promoted to admin

### M3: Core Commands
- [ ] `/таймзона <tz>` handler + validation (pytz)
- [ ] `/моевремя` handler (show user local time + next Sunday call in local)
- [ ] `/помощь` handler (list all commands)
- [ ] `/время`, `/опрос вкл`, `/опрос выкл` (admin-only stubs)
- [ ] Error messages in Russian

### M4: Timezone Math
- [ ] `tz_utils.py`: validate_timezone(tz_name) → bool
- [ ] `tz_utils.py`: convert_time(time_str, from_tz, to_tz) → time_str
- [ ] `tz_utils.py`: get_user_local_time(user_tz) → HH:MM
- [ ] Tests (manual, Python REPL)

### M5: Friday Invite Flow
- [ ] Scheduler setup: APScheduler for Friday `poll_time`
- [ ] Friday job: Load settings, send group message (RU) with buttons
- [ ] Buttons: ✅ Подходит | 🔄 Предложить другое | ❌ Не смогу
- [ ] Callback handlers for each button

### M6: Time Proposal UI
- [ ] Generate 6 time options (base ± 2h to +3h)
- [ ] Private message with time buttons
- [ ] Convert times to user's local timezone before display
- [ ] Re-render on each click (edit message, update state)
- [ ] Track selected time

### M7: Response Tracking
- [ ] Store responses in `event.responses[user_id]`
- [ ] Group message on proposal: `[Name] предлагает новое время: ➡️ HH:MM`
- [ ] Buttons: ✅ Подходит | ❌ Не подходит | 🔄 Предложить другое
- [ ] Reset responses on new proposal

### M8: Auto-Confirm Logic
- [ ] Timeout job: Check `auto_confirm_hours` from event deadline
- [ ] Rule: No ❌ votes → auto-confirm
- [ ] Send group message: `✅ Время подтверждено автоматически: ➡️ HH:MM`
- [ ] Update `event.status = confirmed`

### M9: Testing & Deployment
- [ ] Local test in small private group (3 users, different timezones)
- [ ] Test all Phase 1 commands + flows
- [ ] `.env.local` with `TELEGRAM_BOT_TOKEN` (local only)
- [ ] `.gitignore` confirmed
- [ ] Prepare systemd service for Oracle Cloud (stub for now)

### M10: Push & Ready for Phase 2
- [ ] All Phase 1 exit criteria met
- [ ] README updated with local test steps
- [ ] TODO.md updated (Phase 1 done, Phase 2 next)
- [ ] Push to main

## Task Dependencies

```
M1 (Setup)
  ↓
M2 (Session) ← M3 (Commands)
  ↓
M4 (TZ math) ← M5 (Friday)
  ↓
M6 (Proposal UI) → M7 (Responses) → M8 (Auto-confirm)
  ↓
M9 (Testing) → M10 (Push)
```

## Effort Estimate (Rough)

| Milestone | Est. Hours |
|-----------|-----------|
| M1 | 0.5h |
| M2 | 2h |
| M3 | 2h |
| M4 | 1h |
| M5 | 1.5h |
| M6 | 2h |
| M7 | 1.5h |
| M8 | 1h |
| M9 | 1.5h |
| M10 | 0.5h |
| **Total** | **~13.5h** |

---

## Notes

- No hardcoded users; bot discovers members dynamically
- Admin = first user (can transfer in Phase 2)
- All messages in Russian
- Sessions persist in `sessions.json` (in-memory during runtime, saved on exit)
- Scheduler (APScheduler) runs jobs in separate thread; must be thread-safe
