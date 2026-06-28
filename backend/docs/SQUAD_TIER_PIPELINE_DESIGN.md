# Squad-Tier Development Pipeline — Design Doc

Status: **DRAFT — awaiting sign-off** · Owner: GTEX backend · Scope: backend gap #2 (squad tiers) + gap #1 (real-player multi-position)

This document specifies the *full pipeline* the user approved: every club operates
**first team / U21 / reserve** rosters, regens/newgens enter through the academy, age
and develop, and graduate up the tiers. It is grounded in the current models — file
references are exact so the build connects to what already exists.

---

## 0. Implementation note — relationship to the existing academy system (discovered 2026-06-28)

A full **academy** system already exists and is separate from this: `AcademyPlayer`
(`academy_players`) with an `AcademyPlayerStatus` lifecycle
(TRIALIST→ENROLLED→DEVELOPING→STANDOUT→PROMOTED→RELEASED), `AcademyPlayerProgress`,
`AcademyGraduationEvent`, plus training cycles/programs. `AcademyPlayer` is its own entity,
**not** the tradeable `ingestion_players.Player`.

Reconciliation: the academy is the **youth feeder** (develops AcademyPlayers until PROMOTED);
the squad-tier system here rosters the club's **owned tradeable Players** into
first_team/u21/reserve. They are complementary layers, built to coexist:
- Academy `PROMOTED` ⇒ (future hook) create a `first_team`/`reserve` tier membership for the
  resulting Player.
- The "Academy intake view" (§7) surfaces both youth-rank tier members AND promotable
  `AcademyPlayer`s.
This module ships the tier layer for owned Players; the academy auto-promotion hook is a
documented integration point (service method), not wired into every creation site yet.

## 1. Why (vision mapping)

From the GTEX vision:
- "Each club operates an academy, U21, reserve etc."
- "Regens/newgens come through club academies."
- "Club owners can also build a son" (already supported — see §9).

Today GTEX has the *pieces* but not the *pipeline*:
- Regens are generated **for a club** (`regen_profiles.generated_for_club_id`, [regen.py:46](../app/models/regen.py)).
- An **academy competition** exists (`app/academy`, fixtures/standings/champions-league flow).
- A club's match squad is resolved from **active contracts** (`list_club_squad_status`, [player_lifecycle_service.py:297](../app/services/player_lifecycle_service.py)).

What's missing is the connective tissue: a record of **which tier a contracted player
sits in**, and an engine that **moves players up the tiers** as they age/develop. That
is what this pipeline adds.

---

## 2. Current-state facts (the integration surface)

| Concern | Source of truth today | File |
| --- | --- | --- |
| Player belongs to a club | `PlayerContract` (active/expiring), read via `get_club_contracts(club_id)` | `player_lifecycle_service.py:232,297` |
| Card ownership (by user) | `player_card_holdings` (player_card_id ↔ owner_user_id) | `player_cards.py:124` |
| Season squad submission | `club_squad_registrations` (club_id, player_ids_json) | `club_lifecycle.py:53` |
| Regen → club | `regen_profiles.generated_for_club_id`, `current_gsi`, `potential_range_json` | `regen.py:46,57,59` |
| Regen multi-position | `regen_profiles.secondary_positions_json` (already exists) | `regen.py:55` |
| Real-player position | single `position` / `normalized_position` (no secondaries) | `ingestion/models.py:431` |

**Design consequence:** tier membership is a **layer on top of the club↔player
contract relationship**, not a replacement for it. A player is eligible for a tier only
while they hold an active contract at that club. Match selection draws from the
**first-team** tier.

---

## 3. Data model — `club_squad_tier_memberships`

New table (per the approved "new membership table" option).

| Column | Type | Notes |
| --- | --- | --- |
| `id` | uuid PK | |
| `club_id` | FK `club_profiles.id` (CASCADE) | the club |
| `player_id` | FK `ingestion_players.id` (CASCADE) | works for real players AND regens (regens link to `ingestion_players`) |
| `tier` | enum `first_team` \| `u21` \| `reserve` | current tier |
| `source` | enum `academy` \| `transfer` \| `son` \| `mint` \| `manual` | how they entered the club |
| `joined_club_at` | datetime | first entry to this club |
| `joined_tier_at` | datetime | last tier change (drives "time at tier" rules) |
| `status` | enum `active` \| `released` \| `promoted_out` | promoted_out = graduated past first team / left |
| `last_evaluated_at` | datetime null | last time the graduation engine looked at this row |
| `metadata_json` | JSON | dev snapshots, manual-override flags, audit |

Constraints / indexes:
- `UNIQUE(club_id, player_id)` where `status = active` — a player sits in exactly one tier per club.
- Index `(club_id, tier, status)` — the hot read for "show me this club's U21".
- Index `(status, last_evaluated_at)` — the graduation worker's scan.

**Why a new table, not a column on registration:** season registration is transient
(per-season, lockable), while tier membership is a **persistent rostering fact** that
outlives any single season and must survive squad re-registration. Keeping them separate
avoids overloading the registration concept (the user's chosen option).

---

## 4. Tier definitions & rules

| Tier | Meaning | Match eligibility | Academy competition | Capacity |
| --- | --- | --- | --- | --- |
| `first_team` | Senior squad | ✅ feeds `list_club_squad_status` selection | ❌ | unbounded (v1) |
| `u21` | Under-21 development | ❌ (senior comps) | ✅ | unbounded (v1) |
| `reserve` | Intake / fringe / recovering | ❌ | ✅ | unbounded (v1) |

**Capacity (OQ-3 — resolved):** no caps in v1. Tiers are unbounded; limits can be added later.

**Tier moves are owner-driven (OQ-7 — resolved).** The owner promotes/demotes both
real players and regens. The engine only *recommends* (§6); it never moves a player by
itself. Move validation:
- → `reserve`: allowed for a player of **any age**.
- → `u21`: allowed only if **age ≤ 21** (OQ-1 — resolved: strict ≤21).
- → `first_team`: allowed for any age (this is "signing a youth player up").

Rules:
- A player can only be **selected for a senior match** if they are `first_team` **and**
  have an active contract **and** are available (not injured/suspended). This ANDs onto
  the existing `list_club_squad_status` logic — see §8.
- U21/reserve players are visible in the squad UI and eligible for **academy** fixtures
  only.

---

## 5. Entry sources (how players land in a tier)

| Event | Lands in tier | source | Where wired |
| --- | --- | --- | --- |
| Regen generated for club | `u21` if age ≤ 21 else `reserve` (the "youth rank") | `academy` | `regen_creation/service.py` `_generate_order` after `generated_for_club_id` is set |
| "Build a son" | `reserve` | `son` | `regen_creation` request-son completion (§9) |
| Buy/transfer a real player | `first_team` (default; owner may move) | `transfer` | wherever a `PlayerContract` is created for a club |
| Admin mint to club | `first_team` (default) | `mint` | admin godmode player grant |
| Owner move | n/a (tier change) | `manual` | new endpoints (§7) |

A membership row is created **at the same time** the club↔player contract is
established, so the two never drift. (Contract creation sites become the hook points.)
Regens arrive in the **youth rank** (u21/reserve) and surface in the **Academy intake
view** (§7) where the owner signs them up to the first team.

---

## 6. Recommendation engine (no auto-moves)

**OQ-4 — resolved: recommend, owner confirms.** The engine never moves a player. It
computes a `promotion_readiness` signal per membership and surfaces it in the squad/
academy UI; the owner decides. This keeps owners engaged (FM-like).

A service (`SquadTierRecommendationService`) computes, per active membership:

1. **Age flag:** `u21` player who has turned 22 → flag "aged out of U21, move to first
   team or reserve" (shown as a nudge; **not** auto-applied).
2. **Ready for first team (merit):** `current_gsi ≥ first_team_floor` (default 70 — OQ-2)
   → flag "ready to sign up".
3. **Promising youth:** `age ≤ 21` and `potential_ceiling ≥ 75` → highlighted in the
   Academy intake view as a top prospect.

Inputs available today: `regen_profiles.current_gsi`, `potential_range_json`, player
`date_of_birth` (age). No new analytics needed for v1.

### Cadence
- Recommendations are computed **on read** (cheap) and/or refreshed on the existing
  daily lifecycle job; no new scheduler. `last_evaluated_at` caches the last compute.
- Owner moves write a `metadata_json` audit entry and may emit an AI-news event
  ("X signed to the first team").

Because moves are owner-driven, there is no auto-undo and **OQ-5 (cooldown) is moot**.

---

## 7. API surface

Under the club namespace (mirroring existing club routers):

- `GET  /api/clubs/{club_id}/squad/tiers` → squad grouped by tier (first_team/u21/reserve), each player with summary, eligibility, and `promotion_readiness`.
- `GET  /api/clubs/{club_id}/academy/intake` → **the academy view**: regens/youth coming through the ranks (u21 + reserve), with prospect highlights, signable to the first team.
- `POST /api/clubs/{club_id}/squad/tiers/{player_id}/assign` → owner sets the player's tier. Validates age rule (§4): →u21 requires age ≤ 21; →reserve any age; →first_team any age.
- `POST /api/clubs/{club_id}/academy/intake/{player_id}/sign-up` → convenience: move a youth-rank player straight to `first_team`.

All mutations: owner-or-admin gated, write audit, and validate the player has an active
contract at the club. `promote`/`demote` are thin wrappers over `assign`.

---

## 8. Match & competition eligibility integration

- `list_club_squad_status` gains an **optional tier filter**; senior match selection
  passes `tier=first_team`. Backward-compatible: default (no filter) keeps current
  behaviour so nothing breaks before data is backfilled.
- Academy fixture team-building reads `tier in (u21, reserve)`.
- A backfill step assigns every currently-contracted player to `first_team` on
  migration day (so existing clubs keep working with no behaviour change).

---

## 9. "Build a son" — already supported, just connect it

`/request-son/options` + `/request-son` already exist ([regen_creation/router.py:40-58](../app/regen_creation/router.py)),
and `regen_profiles.is_special_lineage` flags lineage. The only new work: when a son is
created, also create a tier membership (`source=son`, tier `reserve`). No new son model needed.

---

## 10. Gap #1 — Real-player multi-position (bundled)

- Add `secondary_positions_json: list[str]` to `ingestion_players.Player`
  (mirrors `regen_profiles.secondary_positions_json`).
- Ingestion service populates it from SportMonks `player.detailedposition`
  (same nested-include fix as N77) on the next re-ingest.
- Read API returns `position` (natural) + `secondary_positions` so the FM-style
  card renders the position list for real players, as it already can for regens.

---

## 11. Migration plan

One Alembic revision:
1. `create table club_squad_tier_memberships` (+ indexes/constraints).
2. `add column ingestion_players.secondary_positions_json` (JSON, default `[]`).
3. Data backfill: insert a `first_team` membership for every player with an active
   contract at a club (`source=transfer`, `joined_*` = now).

Written but **not applied to prod** — given the prod DB's incident history, the user
runs it. Will be validated against a local/test DB first.

---

## 12. Edge cases

- **Sell/loan a U21 player:** selling clears the contract → membership `status=released`.
- **Ownership transfer of the club:** memberships are keyed by `club_id`, so they
  follow the club, not the owner. ✅
- **Club deletion:** CASCADE on `club_id` removes memberships.
- **Player at two clubs:** impossible — one active contract drives one membership;
  loans are modelled separately and do not create a second `active` membership (OQ-6).
- **Regen retrain changes position:** independent of tier; no interaction.

---

## 13. Open questions

**Resolved:**
- **OQ-1 — U21 age band:** strict `age ≤ 21`. ✅
- **OQ-3 — Capacities:** no caps in v1. ✅
- **OQ-4 — Promotion:** recommend only; owner confirms all moves. ✅
- **OQ-5 — Override cooldown:** moot (no auto-moves). ✅
- **OQ-7 — Tier movement:** owner-driven for both real players and regens; regens
  arrive in the youth rank and are signed up via the Academy intake view. ✅

**Still open (non-blocking — proceeding with the stated default):**
- **OQ-2 — Recommendation threshold:** "ready for first team" defaults to `current_gsi ≥ 70`. Tune later.
- **OQ-6 — Loans:** v1 assumption — loaned-in players sit **outside** the tier system (no membership row); revisit when the loan/match-eligibility interplay is built out.
