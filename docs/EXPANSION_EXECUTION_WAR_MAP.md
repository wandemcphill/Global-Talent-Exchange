# GTEX Expansion Execution War Map

This document turns the expansion task grid into an execution order that matches the current repo surface area.

Status labels:

- `existing`: meaningful end-to-end surface already exists and should be hardened or expanded, not rebuilt
- `partial`: some primitives exist, but the product loop is incomplete
- `missing`: no meaningful implementation surface was found

## Current Footing

The repo already contains meaningful primitives for the next phase:

- live match caching and fan-out via `backend/app/live_matches/service.py`
- Redis and Kafka backbone wiring via `backend/app/core/config.py` and `backend/app/core/container.py`
- audit/risk scaffolding via `backend/app/observability/audit_service.py`, `backend/app/risk/fraud_service.py`, and `backend/app/risk_ops_engine/service.py`
- treasury, wallet, and admin finance surfaces via `backend/app/treasury/*`, `backend/app/wallets/*`, and `backend/app/admin_finance/*`
- replay, tournaments, and matchmaking surfaces via `backend/app/replay_archive/*`, `backend/app/streamer_tournament_engine/*`, and `backend/app/simulation_matchmaking/*`
- referral, daily reward, and engagement loops via `backend/app/routes/referrals.py`, `backend/app/services/referral_risk_service.py`, and `backend/app/daily_challenge_engine/*`

## Recommended Tranche Order

### Tranche 1: Money Safety And Operator Control

Build these first because they protect real-money flows and give operators a way to stop damage:

1. payment webhook verification and KoraPay HTTP webhook route
2. payment reconciliation and duplicate-deposit detection
3. wallet lock states and withdrawal batching
4. platform-wide rate limiting
5. normalized audit coverage
6. user freeze and ban controls
7. match kill switch

### Tranche 2: Live Scale And Integrity

Expand the backbone only after operator safety is in place:

1. Redis live-match cache promotion from local primitive to enforced runtime contract
2. Kafka topic contracts for live matches, payments, treasury, and economy events
3. match worker autoscaling policy and queue depth instrumentation
4. anti-cheat and tampering pipelines
5. centralized anomaly detection
6. device fingerprint capture outside the referral subsystem

### Tranche 3: Retention, Gameplay, And Social Loops

Once safety and scale are covered, increase reasons to play and share:

1. unified tournament brackets
2. persistent ranked ladder and matchmaking seasons
3. match-to-match fatigue and injury persistence
4. tactical presets marketplace
5. highlight export and social sharing
6. daily login streaks
7. influencer leaderboard
8. regional tournaments

### Tranche 4: Economy Governance And Data Intelligence

Do this after telemetry and controls are reliable:

1. automatic inflation governor
2. adaptive burn sinks and reward decay
3. whale surveillance and market circuit breakers
4. lifecycle segmentation
5. price prediction
6. match outcome analytics
7. anomaly model upgrades
8. agent learning / RL later

## Task Grid

### Core Infra Tasks

- Redis caching layer for live matches: `partial`
  - `LiveMatchHub` already snapshots match state into the cache layer, but production cache contracts, invalidation, and observability still need to be formalized.
  - Repo anchor: `backend/app/live_matches/service.py`
  - Tranche: `2`
- Kafka/queue for event streaming: `partial`
  - Redis and Kafka backbone wiring already exists, but topic ownership and domain event contracts are still incomplete.
  - Repo anchors: `backend/app/core/container.py`, `backend/app/backbone/*`
  - Tranche: `2`
- Match worker autoscaling: `missing`
  - Competition dispatch exists, but there is no autoscaling policy or worker control plane tied to queue depth or latency.
  - Repo anchor: `backend/app/competition_engine/match_dispatcher.py`
  - Tranche: `2`
- Rate limiting (anti-bot, anti-spam): `partial`
  - Point protections already exist for gifts, downloads, creator chat, and imports, but there is no global route policy or device/IP-aware limiter.
  - Repo anchors: `backend/app/gift_engine/service.py`, `backend/app/services/media_access_service.py`, `backend/app/community_engine/router.py`
  - Tranche: `1`
- Audit logging system: `partial`
  - Audit services exist, but they are not yet enforced consistently across treasury, economy, live ops, admin overrides, and payment mutations.
  - Repo anchors: `backend/app/observability/audit_service.py`, `backend/app/risk_ops_engine/service.py`
  - Tranche: `1`

### Payments + Fintech Tasks

- Webhook handler (Paystack/KoraPay): `partial`
  - Paystack has an HTTP webhook route and both provider adapters exist, but KoraPay lacks its own HTTP endpoint and webhook signature verification is not wired.
  - Repo anchors: `backend/app/admin_finance/router.py`, `backend/app/wallets/providers/paystack.py`, `backend/app/wallets/providers/korapay.py`
  - Tranche: `1`
- Reconciliation engine: `partial`
  - Admin finance can compute supply and cash snapshots, but payment-ledger-bank reconciliation is not yet a closed-loop workflow with mismatch states.
  - Repo anchors: `backend/app/admin_finance/service.py`, `backend/app/services/payment_gateway_service.py`
  - Tranche: `1`
- Fraud detection (duplicate deposits): `partial`
  - Fraud rules cover large movements, velocity spikes, rapid cash-out, and withdrawal bursts, but duplicate provider reference and duplicate deposit replay detection still need dedicated checks.
  - Repo anchor: `backend/app/risk/fraud_service.py`
  - Tranche: `1`
- Withdrawal batching system: `missing`
  - Treasury withdrawals exist, but batching, grouping, approval waves, and bank export flows do not.
  - Repo anchors: `backend/app/treasury/*`, `backend/app/admin_godmode/*`
  - Tranche: `1`
- Wallet locking during transactions: `partial`
  - Ledger balance projections already use row locks when supported, but explicit wallet lock states for review, payout hold, or exploit containment are missing.
  - Repo anchor: `backend/app/wallets/service.py`
  - Tranche: `1`

### Economy Tasks

- Dynamic inflation control: `partial`
  - Burn/mint ratios, supply snapshots, and simulation already exist, but there is no automatic governor that feeds back into rewards, fees, or reward multipliers.
  - Repo anchor: `backend/app/admin_finance/service.py`
  - Tranche: `4`
- Burn mechanisms (fees, taxes): `partial`
  - Burn accounts and burn events exist, but adaptive burn sinks tied to market stress, tournaments, and treasury policy are still missing.
  - Repo anchors: `backend/app/models/economy_burn_event.py`, `backend/app/economy/*`
  - Tranche: `4`
- Reward decay system: `missing`
  - Decay exists in reputation and market-style scoring surfaces, but not in platform reward emissions or farming prevention.
  - Repo anchors: `backend/app/club_identity/reputation/inactivity_decay_service.py`, `backend/app/services/regen_market_service.py`
  - Tranche: `4`
- Whale detection (large holders): `partial`
  - Spend tiers already classify whales for fairness, but holder surveillance, portfolio concentration alerts, and treasury responses are missing.
  - Repo anchor: `backend/app/fairness/spend_balance_controller.py`
  - Tranche: `4`
- Market circuit breakers: `missing`
  - There are anomaly signals in player-card sales, but no market halt or throttling controls for broader exchange shocks.
  - Repo anchor: `backend/app/player_cards/marketplace_service.py`
  - Tranche: `4`

### Gameplay Tasks

- Tournament brackets: `partial`
  - Fast cups, streamer tournaments, world competitions, and linked competition services exist, but there is no unified bracket contract across the product.
  - Repo anchors: `backend/app/fast_cups/*`, `backend/app/streamer_tournament_engine/*`, `backend/app/world_super_cup/*`
  - Tranche: `3`
- Ranked matchmaking: `partial`
  - Matchmaking services and matchmaking ratings exist, but a persistent ranked season loop, promotion rules, and leaderboard surfaces are incomplete.
  - Repo anchors: `backend/app/simulation_matchmaking/*`, `backend/app/competitive_integrity/service.py`
  - Tranche: `3`
- Player injuries + fatigue: `partial`
  - Fatigue and injury signals already influence AI manager choices, but long-lived persistence and competitive consequences still need productization.
  - Repo anchors: `backend/app/ai_manager/service.py`, `backend/app/ingestion/models.py`, `backend/app/football_events_engine/service.py`
  - Tranche: `3`
- Tactical presets marketplace: `missing`
  - Tactical logic exists, but there is no tradable preset catalog, pricing model, or ownership flow.
  - Repo anchor: `backend/app/ai_manager/*`
  - Tranche: `3`
- Replay system: `existing`
  - Replay archive, replay builder, live match replay surfaces, and frontend replay viewers already exist.
  - Repo anchors: `backend/app/replay_archive/*`, `backend/app/match_engine/services/replay_builder.py`, `backend/app/live_matches/*`
  - Tranche: `3` hardening only

### AI + Data Tasks

- Agent learning system (RL later): `missing`
  - Current AI logic is rules-based and heuristic-driven.
  - Repo anchor: `backend/app/ai_manager/service.py`
  - Tranche: `4`
- Price prediction model: `missing`
  - Value and pricing surfaces exist, but there is no predictive model serving future price direction or confidence.
  - Repo anchors: `backend/app/pricing/*`, `backend/app/value_engine/*`
  - Tranche: `4`
- User segmentation (whales, casuals): `partial`
  - There are spend tiers and creator/fan segment hooks, but there is no platform-wide segmentation model that feeds rewards, offers, and risk.
  - Repo anchors: `backend/app/fairness/spend_balance_controller.py`, `backend/app/fan_predictions/service.py`
  - Tranche: `4`
- Match outcome analytics: `partial`
  - Match execution, replay payloads, and integrity scoring already exist, but there is no dedicated analytics layer for outcome features and trend reporting.
  - Repo anchors: `backend/app/match_engine/*`, `backend/app/competitive_integrity/*`
  - Tranche: `4`
- Anomaly detection: `partial`
  - The repo already flags player-card price anomalies, ingestion anomalies, and wallet/fraud anomalies, but the detections are not centralized.
  - Repo anchors: `backend/app/player_cards/marketplace_service.py`, `backend/app/risk/fraud_service.py`, `backend/app/ingestion/real_player_batch_audit.py`
  - Tranche: `2`

### Security Tasks

- Anti-cheat validation engine: `partial`
  - Fairness and match-integrity proofing already exist, but explicit cheat rule packs and real-time enforcement paths are still missing.
  - Repo anchors: `backend/app/fairness/*`, `backend/app/competitive_integrity/*`
  - Tranche: `2`
- Match tampering detection: `partial`
  - Competitive integrity exists, but cross-surface tampering detection for duels, tournaments, and live-match operations is incomplete.
  - Repo anchor: `backend/app/competitive_integrity/service.py`
  - Tranche: `2`
- Wallet exploit prevention: `partial`
  - Double-entry ledgering, row locks, fraud scans, and treasury reviews exist, but freeze/hold flows and exploit-specific guardrails still need implementation.
  - Repo anchors: `backend/app/wallets/service.py`, `backend/app/risk/fraud_service.py`, `backend/app/treasury/*`
  - Tranche: `1`
- API signature verification: `missing`
  - Shared signing primitives exist, but external payment webhook verification is not wired into request handling.
  - Repo anchors: `backend/app/services/signing_service.py`, `backend/app/admin_finance/router.py`
  - Tranche: `1`
- Device fingerprinting: `partial`
  - Referral risk already accepts device fingerprints, but platform-wide capture, storage, and policy enforcement are not implemented.
  - Repo anchor: `backend/app/services/referral_risk_service.py`
  - Tranche: `2`

### Admin + Control Tasks

- Admin dashboard (economy control): `partial`
  - Admin finance control tower and treasury ops already exist, but there is no single economy governor surface with override controls and safe rollout policy.
  - Repo anchors: `backend/app/admin_finance/*`, `backend/app/treasury/*`, `frontend/lib/screens/admin/treasury_ops_screen.dart`
  - Tranche: `1` for consolidation, `4` for automated policy
- Kill switch for matches: `missing`
  - Live matches can be streamed and replayed, but there is no operator kill switch for active match lanes.
  - Repo anchors: `backend/app/live_matches/*`, `backend/app/match_engine/*`
  - Tranche: `1`
- Manual price override: `missing`
  - Admin economics tooling exposes simulation, but not manual spot overrides for player or market pricing.
  - Repo anchors: `backend/app/admin_finance/*`, `backend/app/pricing/*`
  - Tranche: `1`
- User ban / freeze system: `missing`
  - Moderation and creator suspension surfaces exist, but there is no general user freeze/ban control tied to wallet, match, and social capabilities.
  - Repo anchors: `backend/app/moderation/*`, `backend/app/admin_access/*`
  - Tranche: `1`
- Treasury monitoring panel: `existing`
  - Treasury dashboard, God Mode treasury views, and frontend treasury screens already exist.
  - Repo anchors: `backend/app/treasury/router.py`, `backend/app/admin_godmode/router.py`, `frontend/lib/screens/admin/treasury_ops_screen.dart`
  - Tranche: `1` hardening only

### Growth Systems

- Referral engine (earn GTex): `existing`
  - The referral backend, risk flags, admin views, and frontend referral hub already exist.
  - Repo anchors: `backend/app/routes/referrals.py`, `backend/app/services/referral_risk_service.py`, `frontend/lib/screens/referrals/*`
  - Tranche: `3` reward tuning only
- Influencer leaderboard: `missing`
  - Creator and referral metrics exist, but there is no leaderboard product around them yet.
  - Repo anchors: `backend/app/creator_campaign_engine/*`, `backend/app/services/referral_analytics_service.py`
  - Tranche: `3`
- Social sharing (match highlights): `partial`
  - Replay and highlight pipelines exist, but export packaging, share metadata, and growth ranking are incomplete.
  - Repo anchors: `backend/app/live_matches/highlights.py`, `backend/app/media_engine/*`, `backend/app/replay_archive/*`
  - Tranche: `3`
- Daily login rewards: `partial`
  - Daily challenge seeding already includes a login bonus, but streak logic and dedicated retention presentation are not complete.
  - Repo anchors: `backend/app/daily_challenge_engine/__init__.py`, `backend/app/daily_challenge_engine/service.py`
  - Tranche: `3`
- Regional tournaments: `partial`
  - Federation, national-team, and world competition modules already exist, but region-aware tournament scheduling and discovery still need to be built.
  - Repo anchors: `backend/app/federations/*`, `backend/app/national_team_engine/*`, `backend/app/world_super_cup/*`
  - Tranche: `3`

## Default Build Sequence

If execution starts immediately, use this order:

1. signed payment webhooks, KoraPay webhook route, and duplicate-deposit fraud rules
2. wallet freeze and withdrawal batching
3. global rate limiting and audit normalization
4. match kill switch plus user freeze and ban controls
5. Redis and Kafka contracts for live matches and treasury events
6. anti-cheat, tamper, and anomaly consolidation
7. unified tournament brackets and ranked ladder
8. social sharing, daily login streaks, and influencer leaderboard
9. automatic economy governor, whale surveillance, and circuit breakers

## Deliberate Defers

Do not start these before the earlier tranches are stable:

- agent learning / RL
- price prediction
- tactical presets marketplace
- economy automation that can move prices or rewards without operator override
