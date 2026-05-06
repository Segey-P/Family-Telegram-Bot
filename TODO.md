# Family Telegram Bot — TODO


## Phase 1.5: Polish Before Deployment
- [ ] **P1.5-A: Sunday reminder (5 min before call)**
  - Include: final time, vote counts (who said yes/no)
  - No intermediate auto-confirm messages (already removed)

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
