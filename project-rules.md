# Project Rules — Family Telegram Bot

## Local Test Commands
- Run bot locally: `python bot.py` (requires `.env.local` with `TELEGRAM_BOT_TOKEN`)
- Run all tests: `python -m pytest tests/ -v`
- Run single file: `python -m pytest tests/test_bot_pure.py -v`

## Pre-Push Safety
Every push must be preceded by `./scripts/pre-push.sh` which runs the full test suite.
It exits non-zero on failure — treat this as a hard gate.

## Overrides to AGENTS.md

### File Creation Protocol
- File creation scripts (`validate_file_creation.sh`, `verify_file_compliance.sh`) in `scripts/` are symlinks to a template. The `specs/` directory has been flattened to root. Do not move files into `specs/`.

### Commit & Push
- This project does not use feature branches or PRs. Direct pushes to `main` are acceptable (single developer, no CI).
- Ensure `.env.local`, `sessions.json`, `user_timezones.json`, `pending_proposals.json`, and `venv/` are never committed.
- Run `./scripts/pre-push.sh` before every `git push`.

### Testing Policy
- `tests/test_session.py` — unit tests for `session.py` (Session class)
- `tests/test_bot_pure.py` — unit tests for pure functions: `parse_time_input`, `resolve_timezone`, `generate_time_options`, `format_time_in_tz`, `format_all_member_times`, `get_responses_text`
- `tests/test_bot_import.py` — import smoke tests
- Adding a new pure function? Add tests in `test_bot_pure.py`.

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
