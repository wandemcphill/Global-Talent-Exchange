# GTEX Production Signoff Checklist

Date: 2026-06-06

Use this checklist per release candidate. A feature is not signed off until its evidence is attached and its blocked/degraded behavior is explicit.

| Feature | Signoff gate | Evidence command or artifact | Pass criteria | Status |
| --- | --- | --- | --- | --- |
| Auth and session | Backend smoke plus manual login | Staging smoke JSON, manual tester note | Login uses backend session/token; no fixture mode | Pending |
| KYC | Manual review flow | Admin/user KYC screenshots or API trace | Submitted, under-review, approved/rejected states are backend-sourced | Pending |
| Deposits | KoraPay/manual bank only | Payment rail truth test evidence, finance smoke | No Paystack/crypto rail visible; KoraPay/manual states are clear | Pending |
| Wallet ledger | Ledger read and reconciliation | Wallet summary/ledger API evidence | Balances, reserved funds, and ledger rows come from backend | Pending |
| Withdrawals | Manual/admin payout review | Treasury withdrawal evidence | Eligibility, quote, request, review, and status are persisted | Pending |
| Club creation | User onboarding | User journey note | Club is created through backend and visible after reload | Pending |
| Player marketplace | Market read/load | `tools/load/gtex_load_probe.py` market report | Market endpoints meet p95/error thresholds or render degraded | Pending |
| Transfer bids | Bid lifecycle | Backend/frontend focused evidence | Submit/counter/accept/reject never invents wallet or bid state | Pending |
| Player ownership | Holdings/portfolio read | Portfolio/holding API evidence | Ownership changes persist and survive reload | Pending |
| Regen pipeline | Regen world and jobs | Regen API/job evidence | Generated/regenerated data is backend-sourced; blocked when absent | Pending |
| Build-a-Son | Paid creation flow | Wizard evidence and wallet deduction trace | Cost, eligibility, payment, and generated son are backend-sourced | Pending |
| Regen World | Browse/discovery | Visual QA route screenshots | Empty/syncing/degraded states are explicit when data is absent | Pending |
| 2D match center | Backend-authored match | Match-center load report with `--require-match` | No local fake clock/score/event truth; p95 within threshold | Pending |
| Match scheduling/results | Fixture lifecycle | Scheduler/result API evidence | Scheduled fixture records result and standings from backend | Pending |
| Competitions | Admin/user creation and join | Competition smoke/manual evidence | Fees/prizes/brackets/fixtures are persisted or blocked | Pending |
| GTEX-hosted competitions | Hosted comp launch | Admin hosted competition evidence | Launch does not expose 3D/native/pseudo-3D production route | Pending |
| User-hosted competitions | User creation/join | User-hosted competition evidence | Entry and participant states persist | Pending |
| Prize payouts | Competition settlement | Ledger/payout evidence | Payout writes ledger rows and audit trail | Pending |
| Trader marketplace | Order book/trade settlement | Load report and trader evidence | Order book is backend-sourced; escrow/settlement is not faked | Pending |
| GTC/FNC price feed | Ticker/candles/FX | Market load report | Missing feed renders degraded, not fabricated | Pending |
| Jackpot | Pool/contribution/admin trigger | Jackpot route evidence | Pool, trigger, and payout are backend-sourced or blocked | Pending |
| Notifications | In-app push/sync | Notification API evidence | In-app notifications persist; external push not assumed unless proven | Pending |
| Admin dashboard | Finance/user/moderation | Admin smoke/manual evidence | Admin actions audit who/when/what changed | Pending |
| Leaderboards | Ranking reads | Leaderboard screenshots/API evidence | Empty/stale state is explicit; no hardcoded winners | Pending |
| Newsroom/creator content | Story/feed/admin publish | Story feed evidence | Content is backend/stored or clearly syncing/degraded | Pending |
| Visual QA | Desktop/tablet/mobile screenshots | `tools/visual/capture_gtex_visual_qa.ps1` manifest | All screenshots captured and reviewed; no production 3D CTA/nav | Pending |
| Staging smoke | Core API health | `tools/staging/invoke_gtex_staging_smoke.ps1` summary | Required endpoints pass | Pending |
| Rollback | Rehearsal complete | `tools/staging/invoke_gtex_rollback_rehearsal.ps1` summary | Current and rollback candidates pass core smoke | Pending |
| Load/perf | Market and match-center load | `tools/load/gtex_load_probe.py` reports | Required p95/error thresholds pass | Pending |

## Release Captain Rules

- Mark `Pending`, `Pass`, `Blocked`, or `Fail`; do not use ambiguous "looks fine" language.
- A blocked feature can ship only if product scope explicitly excludes it from the release.
- A failed payment, wallet, KYC, withdrawal, match authority, or admin audit gate blocks GA.
- Keep KoraPay/manual bank transfer as the only money rail unless backend owners explicitly ship and verify another approved rail in a later release.
