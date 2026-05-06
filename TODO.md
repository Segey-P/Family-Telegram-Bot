# Family Telegram Bot — TODO

## Phase 1: MVP (Single Weekly Call Coordination) ✅ COMPLETE

### Core Implementation (DONE)
- [x] M2: Session management (`session.py` utilities)
- [x] M3: Core commands (`/tz`, `/mytime`, `/help`, etc.)
- [x] M4: Timezone math validation + conversion
- [x] M5: Friday invite scheduler + group message
- [x] M6: Time proposal UI (private chat, re-rendering, "change choice")
- [x] M7: Response tracking (yes/no/propose buttons in group)
- [x] M8: Auto-confirm timeout logic (silently, no group message)
- [x] UX polish: Remove 'Base/Your' labels, immediate auto-accept for admins/proposers
- [x] Fix: Immediate group message update on full confirmation

### Testing & Iteration
- [ ] **M9: Local testing with 3 users, document findings**
  - [x] Create test group on Telegram
  - [x] Add bot to test group
  - [x] Set timezones (Europe/Minsk, America/Vancouver, +1 more)
  - [x] Test `/tz`, `/mytime`, `/help` commands
  - [x] Manual trigger `/debug_invite` (Friday invite)
  - [x] Test all button flows: yes/no/propose/change
  - [x] Verify timezone conversions in all contexts
  - [x] Test auto-confirm (1 min deadline in test mode)
  - [ ] Document any remaining issues
  - [ ] Fix bugs if found

## Phase 1.5: Polish Before Deployment
- [ ] **P1.5-A: Sunday reminder (5 min before call)**
  - Include: final time, vote counts (who said yes/no)
  - No intermediate auto-confirm messages (already removed)

## Phase 2: Deployment + Multi-User Testing
- [ ] **P2-A: Oracle Cloud VM setup**
  - Provision VPS with public IP
  - Setup systemd service (auto-restart)
  - Configure logging (daily rotation)
  - Use environment variables for secrets
  
- [ ] **P2-B: Testing with full family group (5+ users)**
  - Add real family members to production bot
  - Run 2–3 full weekly cycles
  - Monitor for edge cases (concurrent votes, timezone bugs, etc.)
  - Collect feedback

- [ ] P2-C: Enhancements (if time)
  - Delay button handling (first click wins, 2-3 min lock)
  - Transfer admin command (`/makeadmin @username`)
  - Recurrence settings (weekly, bi-weekly, monthly)
