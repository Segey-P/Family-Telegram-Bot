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
- [x] **P2-A: Oracle Cloud VM setup** ✅ COMPLETE
  - [x] Created deployment script (`scripts/deploy_vm.sh`)
  - [x] Created deployment guide (`VM_DEPLOYMENT.md`)
  - [x] Merged to main (PR #1)
  - Next: Run deployment script on VM with bot token
  
- [ ] **P2-A-verify: Deployment verification**
  - [ ] Run `bash deploy_family_bot.sh <TOKEN>` on Oracle VM
  - [ ] Verify service is running: `sudo systemctl status family-telegram-bot`
  - [ ] Check logs for startup: `sudo journalctl -u family-telegram-bot -f`
  - [ ] Test bot responds to `/help` command in test group

- [ ] **P2-B: Testing with full family group (5+ users)**
  - [ ] Add real family members to production bot group
  - [ ] Run 2–3 full weekly cycles (Friday invite → voting → Sunday reminder)
  - [ ] Monitor for edge cases (concurrent votes, timezone bugs, etc.)
  - [ ] Document findings in `docs/phase2-testing-log.md`
  - [ ] Collect feedback from family members

- [ ] P2-C: Enhancements (if time)
  - [ ] Delay button handling (first click wins, 2-3 min lock)
  - [ ] Transfer admin command (`/makeadmin @username`)
  - [ ] Recurrence settings (weekly, bi-weekly, monthly)
