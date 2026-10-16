# GTEX: Owner Control Center (web-first launch surface)

## Original problem statement
"GTEX Nigeria Launch Plan: A web-first football club-owner platform where users build, run, and monetize clubs in a persistent football world through players, managers, facilities, competitions, and platform-native economy systems." It must be positioned as a club-owner simulator, not FM/FIFA/eFootball. The home is the Owner Control Center with 6 blocks: My Clubs, Owner Inbox, Today's Decisions, Live Club Health, Competition & Fixtures Rail, Club Economy Snapshot. Manager and regen realism engines, competitions (GTEX-hosted and user-hosted), club-building systems, and a 2D match experience with light owner controls. A unified financial ledger is the single source of truth. Two currency rails: GTEX Coin and Fan Coin, with labelled balances. Club shares are reframed as Club Support Units (not investments). Anti-collusion rules for 3-club ownership. Nigeria launch with payout eligibility, KYC thresholds, fraud review and feature-level restrictions. Football-native gifting, sponsor slots with a 70/30 split, 2D now and 3D later. Stack: React + TypeScript, FastAPI, MongoDB (the user's existing repo actually uses SQLAlchemy/SQLite/Postgres).
User choices: work inside the existing repo (github.com/wandemcphill/Global-Talent-Exchange) with no parallel app; keep its FastAPI backend as the source of truth and build a new React web frontend; JWT auth (existing); Claude Sonnet 4.5 for light AI; Paystack (live keys provided); use the repo's existing coin conversions (1 GTEX Coin = ₦100 = 100 Fan Coin); payouts follow the repo's withdrawal_controls (manual_bank_transfer).

## Architecture
- /app/gtex = user's repo (excluding .git, ops, zips, Gtex_Test_Migration). /app/backend/server.py imports `app.main.get_asgi_app()` from /app/gtex/backend. DB: SQLite at /app/gtex/data_local/gte_backend.db (DATABASE_URL). Backend changes in /app/gtex need `supervisorctl restart backend`.
- New domain module: /app/gtex/backend/app/owner_console (models, ledger, engine, service, competitions, money, ai, router), registered in app/modules.py (api_only, /api/owner/*). Alembic migration 20261016_0130_owner_console_foundation.
- Frontend: /app/frontend (CRA + TypeScript 4.9): pages Landing, Auth, Onboarding, ControlCenter, MyClubs, Market, Competitions, CompetitionDetail, MatchCenter, Squad, Academy, Finance, Inbox, Admin, PaymentCallback.

## Implemented (2026-10-16)
- Ownership-first landing; signup with club; first-club activation wizard (activate grant, then sign 11 players incl. a GK from the repo market, then appoint a manager from the repo catalog, then enter a competition).
- Owner Control Center with all 6 blocks; world-day ticks; inbox with what/why/actions; Claude-voiced messages.
- Manager traits/mood, hire/fire; regens with personality and growth drivers plus explanations; facilities; academy intake.
- GTEX-hosted plus user-hosted competitions (invite codes), league/knockout, AI fill, 2D match center (commentary, momentum, narrative, gift rail).
- Unified ledger (gross/fee/net/status/class) with labelled balances; club treasuries; capital inject/distribute (earned-only) and a capped sister-club capital move.
- Anti-collusion: same-owner bracket block, knockout auto-routing, related-party transfer fair-value band and cooldown, shuffle flags, rotation/forfeit flags, payout holds, integrity score, admin review desk.
- Withdrawals: country/KYC/integrity/balance checks, pending review, admin approve/hold/reject (manual bank transfer).
- Paystack LIVE deposits: initialize, verify on callback, webhook (/api/owner/deposits/webhook, HMAC with secret key), credited as "deposited" at ₦100 = 1 GTX.
- Fan Coin conversion at the repo rate 1:100; Club Support Units (non-investment framing); sponsor and endorsement deals (70/30); read-only coin traders directory.

## Implemented (2026-10-16, iteration 2)
- One Wallet: every owner-console LedgerEvent now also posts balanced double-entry transactions into the repo wallet ledger (WalletService.append_transaction, idempotency oc:<event>:<phase>). The owner wallet is the repo user COIN/CREDIT account, and club cash is the repo club treasury account. Pending/held money sits in owner_console:held until release or reversal. Existing events were backfilled.
- Fiat rates come from the repo's admin-controlled TreasurySettings (deposit ₦900, withdrawal ₦880 per GTEX Coin), used for Paystack deposits and withdrawals.
- Coin Trader Orders on the Finance page: buy/sell with verified traders through the repo coin_traders API (create, accept with escrow, proof, confirm/release, cancel, dispute) plus a trader desk view. Demo trader seeded by scripts/seed_demo_coin_trader.py.

## Iteration 3 (2026-10-16): run the user's own GTEX app
- User direction: no parallel app. Make the existing GTEX (Flutter frontend + FastAPI backend) functional and audit the planned items.
- The repo's Flutter web app is built (`/root/flutter`, `cd /app/gtex/frontend && flutter build web --release --dart-define=GTE_API_BASE_URL=<preview url> --dart-define=GTE_BACKEND_MODE=strict_live`) and served on port 3000 by `/app/frontend/flutter-server.js` (`yarn start`). The React console is no longer served (`yarn start:react-console`).
- Fixes in repo: gtex_universe dataclass super() TypeError (jackpot/world pulse), /api/v2/auth/* aliases for the Flutter contract, POSIX-locale boot crash in web/index.html.
- Parity audit: /app/gtex/docs/EMERGENT_PARITY_AUDIT_2026-10-16.md
- Open: /api/v2/players/markets returns 503 (API v1 demo facade); lineup AI auto-draft fallback; owner_console module removal pending the user's decision.

## Backlog
- P0: Bridge the owner-console ledger with the repo's existing wallet ledger: DONE (iteration 2).
- P0: Register the Paystack webhook URL in the dashboard for the production domain.
- P1: KYC submission UI (/api/kyc); Paystack transfer payouts if processor mode changes; remove the demo trader and its 2,000 GTX demo float before launch.
- P1: Fix the pre-existing GtexUniverseService super() TypeError in the repo's gtex runtime hook.
- P2: Club identity editor (crest/colours), supporter-only competitions, 3D/season passes.
