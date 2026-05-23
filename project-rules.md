# Project Rules — Family Telegram Bot

## Local Test Commands
No test framework is set up. Testing is done manually in a Telegram group.
- Run locally: `python bot.py` (requires `.env.local` with `TELEGRAM_BOT_TOKEN`)
- No automated test suite exists yet

## Overrides to AGENTS.md

### File Creation Protocol
- File creation scripts (`validate_file_creation.sh`, `verify_file_compliance.sh`) in `scripts/` are symlinks to a template. The `specs/` directory has been flattened to root. Do not move files into `specs/`.

### Commit & Push
- This project does not use feature branches or PRs. Direct pushes to `main` are acceptable (single developer, no CI).
- Ensure `.env.local`, `sessions.json`, `user_timezones.json`, `pending_proposals.json`, and `venv/` are never committed.

## Python Conventions
- Single-file bot (`bot.py`) with a `session.py` helper
- `python-telegram-bot` v21+ async API with `ApplicationBuilder`
- All user-facing messages in Russian
- Async handlers with `async/await`
- `pytz` for timezone conversions; store as `pytz.timezone` objects
- `apscheduler` for cron-like scheduling
- Settings: `settings.json` (committed, loaded via `json.load`)
- Sessions: `sessions.json` (NOT committed, created at runtime)

## Session Model
See `session.py`. Each session has:
- `chat_id`, `members` dict (user_id → username)
- `user_timezones` dict (user_id → IANA timezone string)
- `admin_id` (first user to set timezone)
- `event` with `responses` dict and `proposal_state`
- Scheduling state flags (`invite_sent`, `reminder_1h_sent`, etc.)
