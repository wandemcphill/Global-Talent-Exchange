# GTEX Club Legacy: Phase 0 Audit & Implementation Map

Status: DRAFT for owner approval. No Club Legacy code has been written yet.
Date: 2026-10-17

## 1. Current stack (as audited)
- **Backend:** FastAPI monolith in `gtex/backend/app`, around 150 domain packages. SQLAlchemy on Supabase PostgreSQL, with 207 Alembic migrations in `gtex/backend/migrations/versions`. Auth is JWT with roles (user / admin / super_admin), guarded by `get_current_user` and `get_current_admin`. There is no Postgres RLS; authorisation happens in the API layer.
- **Frontend:** the canonical Flutter app (`gtex/frontend`), now served at the main address by `frontend/flutter-server.js`. The React app has been removed.
- **Scheduled jobs:** `.emergent/crons.yml` runs two jobs: the share price snapshot and the owner alert sweep.

## 2. Existing systems to REUSE (no parallel builds)
| Plan requirement | Existing source of truth | Notes |
|---|---|---|
| Club identity and geography | `models/club_profile.py` (country_code, region_name, city_name, colours, crest, venue, founded_at), `club_identity/` | **Continent is missing.** Add it as a derived lookup table, not a free-text column. |
| Three-club limit | `owner_console/service.py` MAX_CLUBS = 3, enforced on the server | Already in place. Make it config-driven. |
| Owner/club money separation | `owner_console/ledger.py` (club, owner and platform accounts; GTEX_COIN and FAN_COIN; balance classes), `ledger/`, `wallets/`, `club_finance/` | **Risk: there are three ledgers.** Phase 1 must pick `owner_console/ledger.py` as canonical for club-economy events and map the others. |
| Audit and idempotency | Ledger events carry an idempotency key, admin review logs, `integrity_engine/`, `competitive_integrity/` | Add one common `audit_log` table for admin and catalogue changes. |
| Approval inbox | `owner_console` inbox (decisions, actions, deadlines, auto-expiry, alerts) | Base for the GM/HoYD approval queue. Extend it with `actor` and `policy_id` fields. |
| Feature flags and settings | `launch_control/`, `runtime_config/`, `admin_engine` | Use these for every new rate, cap and fee. |
| Managers | `manager_market/`, `manager_marketplace/`, `ai_manager/`, owner manager profiles (`/managers/catalog`) | Extend for careers and negotiations (Phase 7). |
| Youth / HoYD inputs | `academy/`, `models/youth_prospect*.py`, `youth_pipeline_snapshot.py`, `regen_*` packages, owner academy intake | HoYD becomes a new staff role on top of these. |
| Sponsorship and kits | `sponsorship_engine/` (offers, endorsements), `club_sponsor*`, `club_sponsorship_contract/asset/package/payout`, `club_jersey_design.py`, `ads_engine/` | Phase 6 mostly extends these. |
| Gifts | `gift_engine/`, `gift_transaction.py`, owner `/gifts/send` (Fan Coin 70/30) | Luxury gifts with recipient acceptance are new on top. |
| Cosmetics and catalogue | `club_cosmetic_catalog_item.py`, `club_cosmetic_purchase.py`, `club_branding_asset.py` | Starting point for the luxury catalogue. **Supply caps and unique instances are missing.** |
| Marketplace and resale | `marketplace/`, `club_sale_market/`, `transfer_market/` | Phase 4 resale reuses the order and settlement patterns. |
| Pre-season / friendlies | `calendar_engine/`, `competition_engine/`, `hosted_competition_engine/`, `fast_cups/` | **No pre-season window exists.** Build it on the calendar engine. |
| Governance and sanctions | `governance_engine/`, `dispute_engine/`, `risk_ops_engine/`, owner integrity flags, related-party rules | Phase 8 extends these with a case, sanction and appeal workflow. |
| Shareholding | `club_ownership/`, `ownership_groups/`, `creator_share_market.py` | Minority stakes are deferred until valuation rules are signed off. |
| 3D | `widgets/match_3d/` (match scene, Flutter) | **No showroom or asset viewer yet.** Reuse the scene utilities and lazy loading. |

## 3. Gaps (new work)
1. GM and HoYD staff profiles, attributes, personalities and contracts. Only managers exist today.
2. A delegation policy engine: per-task mode (owner-only / approval / auto), budgets, thresholds and a policy snapshot on each action.
3. Continent geography, plus separate prestige, development and financial-strength metrics.
4. Luxury asset instances: ownership class (owner / club / player / manager), supply caps, provenance and 3D model references.
5. Pre-season Exchange: a season window, invitations, counter-offers, host agreements and revenue splits that always add up to 100%.
6. Owner net worth computed from holdings and valuations, not from spend.
7. A sanction ladder with cases, evidence and appeals.

## 4. Proposed smallest vertical slice (needs your approval)
**Slice A (Phase 1 + the start of Phase 2):**
- Migration 1: `geo_continents` lookup plus a derived `club_profiles.continent_code`, backfilled from `country_code`. This is non-destructive.
- Migration 2: `club_staff` (role gm/hoyd, attributes JSON, personality JSON, contract, salary). Hiring flows reuse the owner ledger.
- Migration 3: `delegation_policies` (club, task, mode, budget_cap, threshold, version) and `delegated_actions` (policy_version, actor, recommendation, reason, confidence, outcome, ledger_event_id).
- The approval inbox reuses the `owner_inbox_items` kinds `staff_recommendation` and `staff_action_report`.
- Settings: every cap, fee and mode default lives in `runtime_config`, with an audit record.
- Flutter: a "Staff & Delegation" section in the Owner Console with hire GM/HoYD, per-task controls, presets and a recommendations feed.

**Exit tests:**
- An automated action can't exceed its budget or threshold.
- A policy change made between recommendation and execution is honoured.
- A club with no staff stays fully playable.
- Every delegated action traces to a policy version and an actor.

## 5. Risks
- Three overlapping ledgers. Wealth and net-worth figures will double-count unless Phase 1 fixes the canonical source.
- The DB connection pool is small (pool 6, overflow 4). New sweeps and recommendation jobs must run in cron background tasks, never on hot read paths.
- Real-world brands, logos, cars and aircraft in the luxury catalogue need licensing, or fictional designs.
- Limited editions must be enforced by database constraints (unique instance numbers, a supply counter updated under a row lock).

## 6. Test plan
- Unit: policy evaluation, supply caps, revenue split totals, valuation.
- Integration: hire → recommend → approve/auto → ledger event (idempotent on retry).
- Authorisation: non-owners and executives outside their scope get 403. Admin-only catalogue edits are audited.
- Concurrency: double purchase of the last capped item, and double settlement.
- Flutter widget tests for each new console section. Live-data testing stays read-only.

## 7. Decisions to lock before coding
1. Executive default permissions, and which matters stay reserved for the owner.
2. GM/HoYD salary ranges, and whether staff cost GTEX Coin from club cash.
3. Whether continent is shown publicly on club pages.
4. Which ledger is canonical for owner net worth (recommendation: `owner_console/ledger.py`).
5. Approval of Slice A as the first build.
