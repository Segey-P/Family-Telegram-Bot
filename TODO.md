# Family Telegram Bot — TODO

## Priority 1 — Must-have before full family rollout
- [ ] **Full family group testing (5+ users)**
  - Run 2–3 real weekly cycles: Friday invite → voting → reminders
  - Watch for edge cases: late joiners, concurrent votes, timezone edge cases

## Backlog
- [ ] Transfer admin (`/makeadmin @username`)

## Completed
- [x] **Removed test mode** — deleted `/test_mode`, all `test_mode` branches, cleaned `settings.json`
- [x] **Added `/trigger` command** — replaces 4 debug commands; optional time param (`/trigger 19:00`)
- [x] **Unified reminder system** — `reminder_check_job` runs every 5 min, works for any day (not just Sunday)
  - Sends 30-min and 5-min reminders based on next occurrence of confirmed call time
  - `handle_presence_callback` resets `reminder_5_sent` on delay so 5-min reminder re-fires
- [x] **Fixed duplicate invites** — `delete_message` before `save_sessions` in `friday_invite_job`
- [x] **Fixed confirmation cleanup** — delete old invite, send fresh confirmation (instead of edit-in-place)
  - Applied to: `check_autoconfirm_job`, `handle_friday_response`, `handle_proposal_yes`
- [x] **Hardened scheduler** — try/except on `remove_job`, `replace_existing=True` on all `add_job`
- [x] **Simplified `reschedule_jobs`** — only 3 jobs: friday_invite, reminder_check, autoconfirm_check
- [x] **Updated `/help` and bot commands** — removed old debug/test_mode entries
