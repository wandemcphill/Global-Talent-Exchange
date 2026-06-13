# LOCAL ALPHA READINESS REPORT

Date: 2026-06-12
Decision: **GO for 5 trusted local-alpha testers after final tunnel/browser smoke**

## Current State Confirmed

- Repository path: `C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE`
- Git toplevel: `C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE`
- Active branch: `feature/original-visual-runtime`
- HEAD: `ec231f2038bd0e8c7c98438201d924bf066b7423`
- N38/N39 report SHA `ca771311` is an ancestor of current HEAD.
- Active worktree is the requested repo. External redesign worktree exists at `.external_worktrees/GTEX_FRONTEND_REDESIGN_WORKTREE` but was not used.
- Visible dirty state before local-alpha fixes was untracked `.runtime` evidence only.
- Current source changes are local-alpha bug/harness fixes in wallet/creator/test schema files plus these reports.

## Status Matrix

| Subsystem | Status | Evidence |
| --- | --- | --- |
| Authentication | PASS | backend auth 5 passed; frontend auth/session 4 passed |
| Wallet | PASS | N33 100 passed; targeted payout invariants 2 passed; release gate money lane passed |
| Transfer | PASS | transfer market/reservation 60 passed; N35 77 passed |
| Competition | PASS | competition lifecycle 6 passed; N34 certified |
| Creator | PASS | creator backend 10 passed; creator frontend 9 passed; withdrawal fee handoff fixed |
| Realtime | PASS contract-level | realtime auth/wallet/regen 4 passed; N35 contract pass; reconnect/multi-device soak not run |
| Frontend artifact | PASS | `flutter build web --no-pub ...` built `frontend/build/web` in 479.2s |
| Local backend boot | PASS after migration delay | `/health`, `/ready`, `/version` responded on disposable local DB |
| External access | READY TO CONFIGURE | Cloudflare Tunnel named mode recommended; final tunnel smoke not yet run |

## Fixes Applied

1. `backend/app/wallets/service.py`: honored caller-provided withdrawal fee bps/minimum fee in payout requests.
2. `backend/app/creator/module7_service.py`: passed creator withdrawal total debit to wallet payout so requested net amount + fee is consistent.
3. `backend/tests/conftest.py`: shared test schema now uses `load_model_modules()`.
4. `backend/tests/clubs/conftest.py`: added `PlayerImageMetadata` table to the focused clubs schema fixture.

## Top 10 Alpha Risks

1. Realtime reconnect/stale-session/multi-device is contract-green but not soak-tested.
2. Cloudflare/ngrok public URL misconfiguration could break CORS or WebSocket upgrades.
3. Local SQLite migration boot is slow on a fresh DB.
4. Developer machine sleep/restart will drop the alpha.
5. Flutter web build requires compile-time API URL; URL changes require rebuild.
6. Disk pressure can still destabilize Flutter builds, though current free space was 19.6 GB.
7. Full backend suite remains sharded, not single-run proven.
8. Creator/wallet fee policy had a bug fixed in this pass; money paths should be watched closely.
9. Testers can create irreversible-looking local data unless DB reset/backup is disciplined.
10. Public tunnel exposes the dev machine app to the internet; keep cohort small and URLs private.

## Top 10 Expected User Issues

1. Session not restoring if browser storage is cleared or private mode is used.
2. Slow first load over tunnel while Flutter web assets download.
3. Wallet action blocked by missing backend compliance/bank details.
4. Build-a-Son blocked by unavailable backend preview/wallet state.
5. Competition join blocked by eligibility/capacity/fee state.
6. Transfer bids blocked by insufficient reserved balance.
7. Creator withdrawal blocked without payout destination or available ledger balance.
8. Realtime indicators showing degraded/syncing during tunnel/network drops.
9. App rebuild needed if API tunnel URL changes.
10. Operator confusion between seed/demo users and new tester accounts.

## Recommendation

Recommended testers: **5 first, then 10 if the first session is stable.**

Recommended duration: **3-5 days**, with the developer actively monitoring logs during the first 2 hours.

GO / NO-GO: **GO for local alpha after final Cloudflare Tunnel browser smoke.**

Do not deploy to staging or production from this state.

