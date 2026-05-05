# Family Telegram Bot — TODO

## Phase 1: MVP (Single Weekly Call Coordination)

### Core Implementation (DONE)
- [x] M2: Session management (`session.py` utilities)
- [x] M3: Core commands (`/таймзона`, `/моевремя`, `/помощь`)
- [x] M4: Timezone math validation + conversion
- [x] M5: Friday invite scheduler + group message
- [x] M6: Time proposal UI (private chat, re-rendering)
- [x] M7: Response tracking (yes/no/propose buttons in group)
- [x] M8: Auto-confirm timeout logic

### Testing & Deployment
- [ ] M9: Local testing in private test group (3 users, different timezones)
  - [ ] Create test group on Telegram
  - [ ] Add bot to test group
  - [ ] Each user: `/таймзона` with different timezone
  - [ ] Test `/моевремя` (verify local time conversion)
  - [ ] Admin: `/отправить_опрос` (manually trigger Friday invite)
  - [ ] Test all button flows (yes/no/propose)
  - [ ] Verify proposal reshows time in user's local timezone
  - [ ] Test auto-confirm (set deadline to 1 min for testing)
  - [ ] Fix any bugs
- [ ] M10: Update TODO.md, push to main (Phase 1 complete)

## Phase 2: Reliability + Enhancements (Later)
- [ ] Sunday -5min reminder (scheduled job)
- [ ] Delay button handling (first click wins, 2-3 min lock)
- [ ] Transfer admin command (`/сделать_админ @username`)
- [ ] Deploy to Oracle Cloud (systemd service)
- [ ] Production testing with real family group (5 users)
