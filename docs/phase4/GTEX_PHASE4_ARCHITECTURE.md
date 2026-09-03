# GTEX PHASE 4 — IMPLEMENTATION CONTRACT

**Status:** APPROVED FOR PARALLEL IMPLEMENTATION
**Contract owner:** Master Architect (this document is authoritative)
**Baseline main SHA:** `8d0bf3c27735a50aca98727db2fe3ef34bb7b01e`
**Baseline date:** 2026-09-02
**PR #86 status:** MERGED into main at the baseline SHA. All P0 UX work is in the tree.

Any agent whose branch does not descend from `8d0bf3c2` must rebase before starting.

---

## 0. VERIFIED REPOSITORY STATE

This section is the result of direct inspection, not handover text. Treat it as fact.

### 0.1 Router architecture — SINGLE, CONSOLIDATED

- One router: `frontend/lib/router/app_router.dart` (1101 lines), `buildGtexAppRouter()`.
- Auth routes split into `frontend/lib/router/gtex_auth_routes.dart`.
- Path constants live in `frontend/lib/navigation/app_destinations.dart` (`AppRoutes`).
- The shell owns a parameterised lane route: `/app/:section` (`gteShellLaneRouteName`) with a
  nested `:subsection` (`gteShellSubLaneRouteName`). Everything else is a top-level legacy
  or deep-link route that redirects or hosts a standalone surface.
- `AppRouteSurfaceState { live, partiallyWired, placeholder, hidden }` is the existing
  disclosure mechanism. **Phase 4 must use it** rather than inventing a new "coming soon" idiom.

**Rule:** no workstream creates a second `GoRouter`, a second route-constant file, or a
parallel navigation shell.

### 0.2 Player card architecture — CANONICAL, SETTLED

- Canonical card: `frontend/lib/ui_gtex/football/gtex_player_card.dart`.
- Companion: `gtex_player_portrait.dart` (PR #86 replaced the drawn silhouette; portrait
  status / missing-reason is a first-class field).
- Regen variants: `gtex_regen_card.dart`, `gtex_regen_portrait.dart`.
- Card exposes `GtexPlayerCardVariant`, `GtexPlayerCardScale { full, compact, thumbnail }`,
  and a label-only prop surface (`priceLabel`, `gsiTrendLabel`, `valueDeltaLabel`,
  `formResults`, `marketHeatLabel`, `demandLabel`, `interestLabel`, `ownerLabel`,
  `potentialLabel`, `availabilityLabel`, ...) plus `GtexValueState`.
- Everything is exported through `frontend/lib/ui_gtex/ui_gtex.dart`.

**Rule:** the card takes **pre-formatted labels**, never raw models and never a repository.
Workstreams add meaning by supplying better labels, not by building new cards.

### 0.3 Player Detail — CANONICAL, SINGLE

- `frontend/lib/features/player_detail/gtex_fm_player_profile_screen.dart` (1506 lines) is
  the one Player Detail implementation.
- `frontend/lib/features/player_detail/gtex_player_navigator.dart` is the **only** sanctioned
  entry point into Player Detail. All surfaces route through it.
- `player_detail_screen.dart` + `widgets/player_detail_widgets.dart` remain as supporting code.
- Covered by `test/ux_refinement/canonical_player_detail_test.dart` and
  `test/ux_refinement/player_detail_actions_test.dart`.

**Rule:** no workstream may open Player Detail by any path other than `gtex_player_navigator.dart`.

### 0.4 Market architecture

- `frontend/lib/features/player_market_redesign/` — screen (524 lines),
  `widgets/gtex_market_player_grid.dart`, `widgets/gtex_market_context_panel.dart`,
  `widgets/gtex_market_selected_player_panel.dart`, `models/gtex_market_browse_models.dart`.
- Client: `frontend/lib/data/gte_exchange_api_client.dart` calls only
  `/api/market/players`, `/api/market/browse/catalog`, `/api/market/leagues`,
  `/api/market/nationalities`, `/api/market/national-teams`.
- Repository: `frontend/lib/data/gte_api_repository.dart` additionally reaches
  `/api/market/players/{id}`, `/api/market/players/{id}/candles`, `/api/market/ticker/{id}`.

### 0.5 Wallet / Portfolio architecture — TWO SURFACES, NOT YET UNIFIED

- `frontend/lib/screens/gte_portfolio_screen.dart` (1252 lines) — holdings / accountancy view.
- `frontend/lib/screens/wallet/gtex_wallet_overview_screen_v2.dart` (1039 lines) — wallet desk.
- Shell routes both through
  `GtexWalletDeskModule { wallet, orders, holdings, coinTraders, traderDashboard }`
  in `gte_navigation_shell_screen.dart`.
- Backed by `/api/portfolio`, `/api/portfolio/summary`, `/api/wallets/*`, `/api/orders/*`.

This is **not** a duplicate-system violation — they are two modules of one desk. Phase 4-B
must keep them as modules of that desk and must not fork a third portfolio surface.

### 0.6 Regen architecture

- `frontend/lib/features/regen_redesign/` — `presentation/gtex_regen_world_screen_v2.dart`,
  `presentation/gtex_create_son_screen_v2.dart`, `presentation/gtex_admin_create_son_screen_v2.dart`,
  `data/gtex_regen_repository.dart`, `models/gtex_regen_models.dart`.
- Integrated into the shell as `GtePrimaryDestination.regens` (commit `ae197f03`), covered by
  `test/ux_refinement/regen_world_shell_test.dart`.

### 0.7 Club / Club-share architecture

- `frontend/lib/features/club_redesign/` — `presentation/gtex_club_owner_dashboard_v2.dart`
  (1751 lines), `presentation/gtex_club_workspace_controller.dart`,
  `widgets/gtex_club_workspace_widgets.dart`.
- Also `club_growth_redesign`, `club_lifecycle_redesign`, `club_sale_market`, `club_identity`,
  `club_hub`, `club_navigation`. These are distinct concerns, not duplicates — **but Phase 4-D
  must not add a seventh club directory.**

### 0.8 Matchday / performance architecture

- `frontend/lib/features/match_redesign/` (incl. `widgets/gtex_match_lineups.dart`, touched by
  PR #86) and `frontend/lib/features/matchday_economy_redesign/` (api + controller + models +
  screen + widgets).

### 0.9 Community architecture

- `creator_social_redesign/`, `viral_feed/`, `engagement_redesign/`, `social/`, `fan_wars/`.
  Fragmented; today it is unconnected to the football economy.

### 0.10 Responsive infrastructure — EXISTS, DO NOT REBUILD

- `frontend/lib/ui_gtex/layout/gtex_master_detail_scaffold.dart` — the width ladder
  (`leftPanelWidth`, `rightPanelWidth`, `detailMinWidth`, `detailWidthFor`), compact break at 420.
- `gtex_app_shell.dart`, `gtex_focus_flow_scaffold.dart`, `gtex_production_flow_scaffold.dart`,
  `gtex_shell_bridge.dart`.
- Locked by `test/ux_refinement/master_detail_width_ladder_test.dart`,
  `master_detail_right_panel_test.dart`, `master_detail_header_overflow_test.dart`.

### 0.11 Existing test baseline

`flutter analyze` clean; `flutter test --exclude-tags golden` = **796 passing** at `8d0bf3c2`.
Goldens under `test/goldens/` and `test/ux_refinement/visual_qa_golden_test.dart` are a known
pre-existing failure lane inherited from Phase 3A. **Phase 4 does not inherit responsibility
for pre-existing golden failures, but must not add new ones.**

---

## 1. PHASE 4 GOALS

Phase 3 delivered surfaces. Phase 4 makes them an **economy**.

1. Turn Market from a directory into an economy with visible price causality.
2. Turn Portfolio from accountancy into ownership with narrative and consequence.
3. Promote Regen to a first-class product world with lineage → potential → value.
4. Connect club ownership and club-share value into the portfolio.
5. Make match performance visibly drive form, and form visibly drive value.
6. Make Home report what happened to the user's football assets.
7. Establish one daily retention loop.
8. Connect community to the football economy.
9. Finish responsive / visual hardening.

**Non-goal:** new visual languages, new navigation systems, new player cards, new backend
economics. Phase 4 is *surfacing and connecting*, not re-architecting.

---

## 2. PRODUCT PRINCIPLES (BINDING)

- **P1 — One visual system.** Everything renders through `lib/ui_gtex/`. A workstream that
  needs a component it does not have proposes it to `ui_gtex/components/`; it does not build
  a local one.
- **P2 — One player card.** `gtex_player_card.dart`. No feature-specific card.
- **P3 — One Player Detail.** Reached only via `gtex_player_navigator.dart`.
- **P4 — One router.** `app_router.dart` + `AppRoutes`.
- **P5 — No invented data.** If a number cannot be traced to a backend field or an explicitly
  documented client-side derivation, it does not ship. See §9.
- **P6 — Absent data is stated, not faked.** Use `GtexEmptyState` / `GtexBlockedState` /
  `AppRouteSurfaceState.partiallyWired`. Never render `0.0%` where the truth is "unknown"
  (this was a proven P0 defect — do not reintroduce it).
- **P7 — Causality is the product.** Every value number should be one tap from its cause.
- **P8 — Labels at the edge.** Formatting happens in the feature layer; `ui_gtex` receives strings.
- **P9 — No resurrection.** Deleted UI systems stay deleted. Do not restore anything from
  `lib/legacy/`, `v1_original/`, or `desktop_salvage_*`.

---

## 3. CANONICAL DOMAIN OBJECTS

| Object | Canonical model | Owner |
|---|---|---|
| Player (market row) | `lib/features/player_market_redesign/models/gtex_market_browse_models.dart` | A |
| Player (detail) | `lib/data/gte_exchange_models.dart` | A (shared) |
| Value snapshot / trend | **new** `lib/domain/value/gtex_value_models.dart` | E |
| Holding / portfolio | `lib/data/gte_models.dart` (portfolio views) | B |
| Regen | `lib/features/regen_redesign/models/gtex_regen_models.dart` | C |
| Club | `lib/features/club_redesign/models/gtex_club_redesign_models.dart` | D |
| Club share / valuation | `lib/features/club_sale_market/` models | D |
| Match / performance | `lib/features/matchday_economy_redesign/matchday_economy_models.dart` | E |
| Home digest | **new** `lib/features/home_dashboard/models/gtex_home_digest_models.dart` | F |
| Community post | `lib/features/viral_feed/data/` | G |

**Cross-cutting rule:** a workstream may *read* another's canonical model. It may not
*edit* it without an integration-contract entry (§7).

---

## 4. SHARED UI / DATA CONTRACTS

### 4.1 `GtexPlayerCard` (frozen surface)

Phase 4 may add **at most three** optional fields, and only by the owner listed:

| Field | Type | Owner | Meaning |
|---|---|---|---|
| `formTrendLabel` | `String?` | E | e.g. `"Form +0.4"` — derived from real match events only |
| `ownershipLabel` | `String?` | B | e.g. `"You own 2.5 shares"` |
| `lineageLabel` | `String?` | C | e.g. `"Son of A. Okoye"` |

All three default to `null` and must render the card unchanged when absent.
`test/ui_gtex/gtex_player_card_test.dart` must be extended, never rewritten.

### 4.2 Value contract (produced by E, consumed by A / B / F)

`lib/domain/value/gtex_value_models.dart` (new, owned by E):

```
GtexValueTrend {
  String playerId;
  Decimal? currentValue;      // null == unknown, never 0
  Decimal? changeAbsolute;
  double?  changePercent;     // null == unknown, never 0.0
  GtexValueState state;       // reuse existing enum
  List<GtexValuePoint> series;
  List<String> reasonCodes;   // straight from backend value_engine reason_codes
}
```

`reasonCodes` are **backend-authored**. No workstream invents a reason code.

### 4.3 Ownership contract (produced by B, consumed by A / C / D / F)

`lib/domain/ownership/gtex_ownership_models.dart` (new, owned by B): a lookup
`playerId -> GtexOwnershipStake { quantity, averageCost, marketValue, unrealizedPl }`,
sourced from `/api/portfolio`. Consumers read it; only B writes it.

### 4.4 Networking contracts

- Market / catalog reads → `lib/data/gte_exchange_api_client.dart`
- Portfolio / wallet / orders / value → `lib/data/gte_api_repository.dart`
- Regen → `lib/features/regen_redesign/data/gtex_regen_repository.dart`
- Club → `lib/features/club_redesign/` + `club_lifecycle_api.dart`
- Matchday → `lib/features/matchday_economy_redesign/matchday_economy_api.dart`

`gte_api_repository.dart` and `gte_exchange_api_client.dart` are **shared hot files** — see §8.

---

## 5. DEPENDENCY GRAPH

```
                  PHASE4-E  Matchday → Form → Value
                   (produces GtexValueTrend)
                        |
          +-------------+-------------+
          v             v             v
   PHASE4-A        PHASE4-C      PHASE4-D
   Market          Regen World   Club Ownership
   Intelligence         |             |
          |             |             |
          +------+------+-------------+
                 v
          PHASE4-B  Portfolio / Ownership
          (produces GtexOwnershipStake)
                 |
                 v
          PHASE4-F  Personalized Home
          (consumes E + B + A + D)
                 |
                 v
          PHASE4-G  Community  (consumes F's digest + A's market events)

          PHASE4-H  Final UX Hardening  (consumes ALL; runs last)
```

Hard edges:

- **E → A, C, D, B, F** — E defines the value contract; nobody else may define it.
- **B → F**, and **B → A / C / D** for ownership badges.
- **A → F** for market-event feed shape.
- **D → B** for club-share holdings appearing in the portfolio.
- **G → F** — Community consumes the home digest; it does not build its own.
- **H → everything.**

**Unblocked at t0 (may start immediately, in parallel): E, A, C, D.**
**B starts when E's `gtex_value_models.dart` and D's club-holding shape have landed.**
**F starts when B and A have landed. G after F. H last.**

---

## 6. WORKSTREAM BOUNDARIES

### PHASE4-A — Market Intelligence

**Goal:** Market stops being a directory. Price movement, heat, and cause are visible.

MAY OWN:
- `lib/features/player_market_redesign/**`
- `lib/data/gte_exchange_api_client.dart` (market methods only)
- `test/player_market_redesign/**`, `test/ux_refinement/harvested_market_flows_test.dart`

MUST NOT MODIFY:
- `lib/ui_gtex/football/**` (A consumes the card as-is)
- `lib/features/player_detail/**`
- `lib/router/app_router.dart`
- `lib/screens/gte_portfolio_screen.dart` or any wallet file

Deliverables: surface `/api/market/movers` (exists, unused by the client), wire
`/api/market/players/{id}/history` and `/candles` into the browse grid and context panel,
show real gainers / losers / heat, and give every price a "why" affordance that opens Player
Detail via `gtex_player_navigator.dart`.

### PHASE4-B — Portfolio / Ownership

**Goal:** Portfolio reads as ownership, not a ledger.

MAY OWN:
- `lib/screens/gte_portfolio_screen.dart`
- `lib/screens/wallet/gtex_wallet_overview_screen_v2.dart` (holdings module only)
- `lib/domain/ownership/**` (new)
- `lib/data/gte_api_repository.dart` (portfolio methods only)
- `test/ux_refinement/portfolio_holding_identity_test.dart`, `test/wallet*`

MUST NOT MODIFY:
- `lib/features/player_market_redesign/**`
- `lib/ui_gtex/layout/**`
- `lib/features/navigation/**` (wallet-desk module enum changes require §7 sign-off)

Deliverables: surface `/api/portfolio/snapshot` (exists, unused), render each holding as a
player with `gtex_player_card` at `GtexPlayerCardScale.compact`, publish `GtexOwnershipStake`,
and include club-share holdings from D.

### PHASE4-C — Regen World

**Goal:** Regen is a product world, not a feature.

MAY OWN:
- `lib/features/regen_redesign/**`
- `lib/ui_gtex/football/gtex_regen_card.dart`, `gtex_regen_portrait.dart`
- `test/regen_redesign/**`, `test/ux_refinement/regen_world_shell_test.dart`

MUST NOT MODIFY:
- `gtex_player_card.dart` (may only *request* `lineageLabel` via §4.1)
- market, portfolio, club, home files

Deliverables: wire the unused backend surface — `/regens/{id}/lineage`, `/bloodlines`,
`/regens/rising`, `/regens/top`, `/regens/feed`, `/rankings`, `/players/{id}/timeline`,
`/players/{id}/career-events`, `/scout/report/{id}`, `/hall-of-fame` — into the regen world;
make lineage → potential → development → value legible; keep the existing create-son flow intact.

### PHASE4-D — Club Ownership

**Goal:** Club ownership and club-share value connect to the user's portfolio.

MAY OWN:
- `lib/features/club_redesign/**`, `lib/features/club_sale_market/**`,
  `lib/features/club_growth_redesign/**`
- `test/club_redesign/**`, `test/club_sale_market/**`, `test/clubs/**`

MUST NOT MODIFY:
- `lib/screens/gte_portfolio_screen.dart` (publish a model to B instead)
- market, regen, home, router files

Deliverables: surface `/api/clubs/{id}/valuation`, `/clubs/marketplace`,
`/api/me/clubs/sale-market/listings`, `/api/clubs/{id}/finance`; expose club performance →
share value; publish a club-holding model for B to fold into the portfolio.

### PHASE4-E — Matchday → Form → Value  (**critical path; start first**)

**Goal:** Performance visibly produces form, form visibly produces value.

MAY OWN:
- `lib/features/matchday_economy_redesign/**`
- `lib/features/match_redesign/**`
- `lib/domain/value/**` (new)
- `lib/data/gte_api_repository.dart` (value-engine methods only)
- `test/matchday_economy_redesign/**`, `test/match_redesign/**`

MUST NOT MODIFY:
- market, portfolio, regen, club, home files
- `lib/ui_gtex/football/gtex_player_card.dart` beyond adding `formTrendLabel` per §4.1

Deliverables: wire `/api/value/snapshots/{id}/latest`, `/history`, `/daily-closes`,
`/trend-summary` (all exist, none reached from Flutter); render backend `reason_codes`
verbatim as the causal explanation; publish `GtexValueTrend`.

### PHASE4-F — Personalized Home

**Goal:** Home tells the user what happened to their football assets, and gives one daily loop.

MAY OWN:
- `lib/features/home_dashboard/**` (4299 lines — refactor into `models/` + `widgets/` is
  expected and sanctioned)
- `lib/features/home/**`
- `test/home/**`

MUST NOT MODIFY:
- any market, portfolio, regen, club, matchday file — F composes their published models only
- `lib/router/app_router.dart`

Deliverables: an asset digest built strictly from B's ownership + E's value trends + A's
movers + D's club holdings. The daily loop must be built on the existing
`app/daily_challenge_engine` backend. **If a digest item has no backing data, it is omitted,
not stubbed.**

### PHASE4-G — Community

**Goal:** Community connects to the football economy.

MAY OWN:
- `lib/features/viral_feed/**`, `lib/features/creator_social_redesign/**`,
  `lib/features/engagement_redesign/**`, `lib/features/social/**`
- `test/social/**`, `test/viral_feed/**`, `test/engagement_redesign/**`

MUST NOT MODIFY: everything outside those directories.

Deliverables: economy-aware feed entries (a trade, a value move, a regen birth, a club sale)
rendered with `gtex_player_card` / `gtex_regen_card`; entry points that route into Player
Detail via `gtex_player_navigator.dart`. **Backend gap — see §9.3.**

### PHASE4-H — Final UX Hardening  (**runs last, alone**)

**Goal:** one coherent product at every width.

MAY OWN: `lib/ui_gtex/**`, `test/ui_gtex/**`, `test/ux_refinement/**`, `test/goldens/**`,
plus narrow cross-feature layout fixes, and (exclusively) `lib/router/app_router.dart`,
`lib/navigation/app_destinations.dart`,
`lib/features/navigation/presentation/gte_navigation_shell_screen.dart`.

MUST NOT: add features, change data flow, or alter any published model contract.

---

## 7. INTEGRATION CONTRACTS

1. **Model publication.** A workstream that produces a cross-stream model lands that model
   file *first*, in its own commit, before consumers begin. E and B each open a "contract
   commit" PR ahead of feature work.
2. **Shared-file protocol.** `gte_api_repository.dart` and `gte_exchange_api_client.dart` are
   append-only in Phase 4: add new methods at the end of the class, never reorder or
   reformat existing ones. This keeps merge conflicts to single hunks.
3. **Card field additions** (§4.1) require the owning workstream to also extend
   `test/ui_gtex/gtex_player_card_test.dart` in the same commit.
4. **Router changes.** Only H may touch `app_router.dart`. A workstream needing a route files
   a request; H batches route changes into one commit at merge time.
5. **Shell destination changes.** Only H may touch `gte_navigation_shell_screen.dart` and
   `app_destinations.dart`.
6. **Empty-data protocol.** Missing backend data → `GtexEmptyState` / `GtexBlockedState` /
   `AppRouteSurfaceState.partiallyWired`. Never a zero, never a placeholder number.

---

## 8. INTEGRATION HAZARDS

| # | Hazard | Mitigation |
|---|---|---|
| H1 | `gte_api_repository.dart` touched by B and E | Append-only protocol (§7.2); E lands first |
| H2 | `gte_exchange_api_client.dart` touched by A | A is sole owner; others request via A |
| H3 | `home_dashboard_screen.dart` is 4299 lines | F refactors it alone, last among feature streams |
| H4 | `gte_navigation_shell_screen.dart` is 1987 lines and central | Frozen for all streams except H |
| H5 | `gtex_player_card.dart` is the single most-shared file | Only the three §4.1 fields; each added by exactly one owner |
| H6 | Six club directories already exist | D must extend, never add a seventh |
| H7 | Portfolio + wallet-v2 look like duplicates | They are one desk; B keeps them as modules |
| H8 | Goldens already fail (pre-existing, Phase 3A) | Baseline captured before Phase 4; H owns golden re-baselining |
| H9 | Value semantics could be defined twice | E owns `GtexValueTrend` exclusively; A / B / F consume |
| H10 | `lib/legacy/`, `v1_original/`, `desktop_salvage_*` invite resurrection | P9: no imports from these paths; H audits |

---

## 9. DATA THAT EXISTS vs DATA THAT MUST BE CONTRACTED

### 9.1 Exists in backend, **not yet reached from Flutter** (pure surfacing work — safe)

- `GET /api/market/movers` — gainers / losers (A)
- `GET /api/market/players/{id}/history` — price history (A)
- `GET /api/market/summary/{asset_id}` (A)
- `GET /api/value/snapshots/{id}/latest | /history | /daily-closes | /trend-summary` (E)
- Backend `reason_codes` incl. `strong_recent_form`, `man_of_the_match` (E)
- `GET /api/portfolio/snapshot` (B)
- `GET /api/clubs/{id}/valuation`, `/clubs/marketplace`, `/api/clubs/{id}/finance`,
  `/api/me/clubs/sale-market/listings` (D)
- Regen: `/regens/{id}/lineage`, `/bloodlines`, `/regens/rising`, `/regens/top`,
  `/regens/feed`, `/rankings`, `/players/{id}/timeline`, `/players/{id}/career-events`,
  `/scout/report/{id}`, `/hall-of-fame` (C)

### 9.2 Exists in the value engine and is authoritative — do not recompute client-side

`backend/app/value_engine/scoring.py` already computes `performance_adjustment_pct` from
`match_events`, a `recent_form_factor` from `recent_form_rating`, and emits `reason_codes`.
**Form and value causality are backend-owned.** No workstream may compute its own form
number in Dart.

### 9.3 Does NOT exist — must be contracted, not invented

| Need | Stream | Required contract | Interim behaviour |
|---|---|---|---|
| Per-user personalized home digest | F | `GET /api/home/digest` returning owned-asset events since last visit | Compose client-side from B + E + A + D; ship nothing that isn't backed |
| Economy-linked community feed | G | `app/community_engine/` exposed **no** `@router` verbs under inspection. G must confirm and, if absent, specify `GET /api/community/feed` with typed economy events | Render only viral-feed data that already exists; do not fabricate economy posts |
| Club-share → user-portfolio join | D → B | Portfolio must return club-share holdings alongside player holdings, or a companion `GET /api/portfolio/clubs` | Render club holdings as a separate, explicitly-labelled section |

**§9.3 resolution — Club-share → user-portfolio join (D, landed):** the companion
option was taken. `GET /api/portfolio/clubs` (read-only, `backend/app/club_ownership/router.py`,
`ClubOwnershipService.list_user_club_portfolio`) returns `ClubPortfolioView` — every club
in which the user holds ownership tokens, valued at the live club-token price, with
`unrealized_pl_pct` / `ownership_pct` left `null` (never `0`) when the denominator is
unknown. Frontend contract published for B to consume:
`lib/features/club_redesign/models/gtex_club_ownership_models.dart`
(`GtexClubShareHolding`, `GtexClubOwnershipPortfolio`), read via
`lib/features/club_redesign/data/gtex_club_ownership_api.dart`. D renders it in-club through
`GtexClubOwnershipPanel` (club-share identity, live share price, the user's stake, and the
settled-match performance signal behind the price); B folds the same model into the portfolio
surface as the explicitly-labelled club-ownership section.
| Daily retention loop rewards | F | Confirm `app/daily_challenge_engine` exposes per-user claim/state | Read-only streak display until confirmed |
| Player → match-performance history keyed by market player id | E | Confirm the id join between market players and match events | If the join fails for a player, show "no recent matches", never a zero rating |

**Any workstream that cannot satisfy a deliverable from §9.1 / §9.2 must file the missing
contract here rather than manufacture the number.** This is non-negotiable — a fabricated
`0.0%` was a proven P0 defect in Phase 3.

---

## 10. ACCEPTANCE CRITERIA

**Global (all streams):**
- `flutter analyze` — no issues.
- `flutter test --exclude-tags golden` — at least 796 passing, zero regressions from baseline.
- No new file under `lib/` that duplicates a canonical system (card, router, Player Detail).
- No import from `lib/legacy/`, `v1_original/`, `desktop_salvage_*`.
- Every numeric on screen traces to §9.1 / §9.2, or is absent.

**Per stream:**
- **A** — every market row shows a real movement value or an explicit unknown; movers ranked
  from `/api/market/movers`; every price has a causal affordance.
- **B** — every holding renders as a player identity; `GtexOwnershipStake` published and
  consumed by at least A; club holdings present or explicitly labelled pending.
- **C** — lineage, potential, and development are reachable from any regen; regen world has a
  primary shell destination and a working create-son flow.
- **D** — club valuation and club performance are visible and connected to share value; the
  club-holding model is published to B.
- **E** — `GtexValueTrend` published; a player's value change is traceable to specific
  matches; `reason_codes` rendered verbatim.
- **F** — home shows owned-asset changes only, from real data; one daily loop present.
- **G** — feed entries link into the football economy through the canonical navigator.
- **H** — width ladder green at every breakpoint; goldens re-baselined or explicitly waived.

---

## 11. TEST REQUIREMENTS

- Every stream adds tests in its own `test/<feature>/` directory. Cross-stream test files are
  H's to arbitrate.
- **Extend, never rewrite:** `gtex_player_card_test.dart`, `canonical_player_detail_test.dart`,
  `master_detail_width_ladder_test.dart`, `browse_card_actions_test.dart`.
- Every new networking method gets a transport test in the pattern of the existing
  `*_api_transport_test.dart` files.
- Every "data absent" path gets an explicit test asserting the empty / blocked state renders
  and that **no zero is shown**.
- Strict-live fixture policy stands: `.standard()` APIs pass `fixtures: null`;
  `GteBackendMode.fixture` only under `FLUTTER_TEST`.

---

## 12. VISUAL QA REQUIREMENTS

- Widths to verify: 360, 420 (compact break), 768, 1024, 1440, 1920.
- Every surface renders through `ui_gtex` scaffolds; no bespoke page chrome.
- Player identity is rendered by `gtex_player_card` / `gtex_player_portrait` everywhere.
  **Hard rule (standing): never a stylized avatar fallback for a face — a real face or no
  picture at all.**
- No horizontal overflow; no truncated primary action.
- Goldens: H owns re-baselining. Feature streams that change pixels flag it in their PR.

---

## 13. MERGE ORDER

```
Wave 0  E contract commit   (lib/domain/value/gtex_value_models.dart)
Wave 1  E  ->  A  ->  C  ->  D      (parallel after E's contract lands; merge in this order)
Wave 2  B                            (needs E + D)
Wave 3  F                            (needs B + A + E + D)
Wave 4  G                            (needs F)
Wave 5  H                            (needs all; sole owner of router, shell, goldens)
```

Each wave rebases onto main and re-runs analyze + the non-golden suite before merge.

---

## 14. EXPLICITLY DEFERRED FROM PHASE 4

- Unity / 3D match rendering (remains quarantined).
- New backend economic models or pricing changes.
- Any redesign of the router, shell, or master-detail scaffold.
- Multi-currency FX surfacing.
- Hosted-competition finance UX.
- Admin / god-mode surfaces.
- Native mobile packaging and APK hardening.
- Golden-suite failures inherited from Phase 3A (H may re-baseline, but fixing Phase 3A's
  visual debt is not a Phase 4 acceptance gate).

---

## 15. VERDICT

**APPROVED FOR PARALLEL IMPLEMENTATION**, subject to:

1. PHASE4-E lands its contract commit before A, C, D begin feature work.
2. No stream other than H touches `app_router.dart`, `gte_navigation_shell_screen.dart`,
   or `app_destinations.dart`.
3. Every missing data need is filed in §9.3 rather than fabricated.
