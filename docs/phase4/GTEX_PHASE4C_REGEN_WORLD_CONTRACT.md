# GTEX PHASE 4C — REGEN WORLD

**Status:** IMPLEMENTED, PENDING REVIEW
**Branch:** `phase4/regen-world`
**Baseline:** `8d0bf3c2` (per Phase 4 architecture contract §0)
**Scope:** DISCOVER → UNDERSTAND LINEAGE → EVALUATE POTENTIAL → DEVELOP → OWN → TRACK

This is the §9.3 filing required of PHASE4-C. Everything the regen world now
shows traces to a backend field; everything it cannot show is listed in §4
rather than fabricated.

---

## 1. WHAT WAS ACTUALLY THERE

Direct inspection of the tree at the baseline, not handover text.

| Layer | State before |
|---|---|
| Shell integration | **Already done.** `GtePrimaryDestination.regens`, covered by `test/ux_refinement/regen_world_shell_test.dart`. Contract §0.6. No routing work was needed, and §7.4/§7.5 reserve the router and shell for H in any case. |
| Regen card | `gtex_regen_card.dart` already accepted `lineageLabel`, `generationLabel`, `traitLabels`, `awardLabels`. **All four were unused by the world screen** — the card could express lineage and nobody passed it. |
| API client | `RegenUniverseApi` reached exactly **5** endpoints: `rising-stars`, `scouting-feed`, `national-regens`, `awards`, `tracking`. |
| Lineage | **Unreached.** No Flutter call to `/regen-universe/players/{id}`, `/bloodlines`, or `/regens/{id}/lineage`. |
| Personality | **Unreached.** `RegenPersonalityView` carries 14 real 0-100 traits plus tags. Nothing in Dart read it. |
| Potential | Reduced to a single `potentialRating` int. The backend's `potential_range` band and `scout_confidence` were dropped on the floor. |
| Development | **Unreached.** `RegenStoryEvent` timeline, achievements and `RegenLegacyRecord` were never requested. |
| Contracts / ownership | `GtexRegenContractOffer` is rendered by two panels and a whole lane; `LiveGtexRegenRepository` returned `const <GtexRegenContractOffer>[]`. The real surface in `segments/player_lifecycle` — lifecycle phase, free agency, transfer listing, pressure state, offer market — was **unreached**. Now wired; see §4.2. |

The regen was a database row because the client asked for one row's worth of
fields, not because the data was missing.

---

## 2. WHAT THIS CHANGE WIRES

All of these existed on the backend and were listed as safe surfacing work in
Phase 4 contract §9.1.

| Endpoint | Now feeds |
|---|---|
| `GET /regen-universe/players/{id}` | The whole dossier: profile (personality, origin, lineage, ability/potential bands, scout confidence, growth curve, uniqueness), prestige, legacy, latest value snapshot, timeline, achievements, discovery badges |
| `GET /regens/{regen_id}/lineage` | The multi-generation bloodline chain on a selected regen |
| `GET /regen-universe/bloodlines` | The Bloodlines lane — origins and their descendants |
| `GET /regen-universe/rankings` | The Rankings lane |
| `GET /regen-universe/hall-of-fame` | The Hall of Fame lane |
| `GET /api/players/{id}/regen` | The dossier's Ownership section: contract phase, free agency, transfer listing, agency message, pressure state, and the offer market (floor terms plus a count of competing clubs) |

### 2.1 New files (all inside C's boundary, §6)

```
lib/features/regen_redesign/models/gtex_regen_wire_models.dart   response DTOs
lib/features/regen_redesign/models/gtex_regen_dossier.dart       C's view model
lib/features/regen_redesign/data/gtex_regen_world_api.dart       the 5 calls
lib/features/regen_redesign/data/gtex_regen_demo_dossier.dart    fixtures
lib/features/regen_redesign/widgets/gtex_regen_dossier_panel.dart
lib/features/regen_redesign/widgets/gtex_regen_discovery_boards.dart
```

`gtex_regen_world_api.dart` borrows the `GteAuthedApi` that `RegenUniverseApi`
already owns, so base url, auth, refresh and backend mode stay in one place.
It is not a second networking system, and §4.4 places regen networking in this
directory.

### 2.2 Honesty rules, enforced by test

`test/regen_redesign/gtex_regen_dossier_panel_test.dart` (20 cases) and
`gtex_regen_world_discovery_test.dart` (22 cases) defend these:

1. **Unknown potential is not zero headroom.** `growthHeadroom` and
   `potentialBandLabel` are null when the backend gave no potential; the panel
   says "Not rated".
2. **Potential is a band, not a point.** `84-93` with the backend's own
   `scout_confidence` beside it, because a single number would claim a
   precision the backend does not.
3. **No parent is not an invented parent.** A regen with no lineage says
   "Starts their own line".
4. **A stated relationship is not always a navigable one.** A celebrity or
   external legend reference is shown but offers no Player Detail control,
   because there is no player row behind it.
5. **No matches is not a row of zeroes.** A regen who has not played says "No
   recorded matches" rather than `0 matches / 0 goals`, which would read as
   "played and did nothing" — a different and false claim.
6. **An absent dossier is distinguished from a failed one.** `notPublished`
   explains itself and offers no retry; `loadFailed` offers a retry.
7. **A dead control is withheld, not drawn.** Every Player Detail entry point
   goes through `GtexPlayerNavigator.tapToOpen`, which returns null outside a
   shell, and the UI renders nothing rather than a button that does nothing.
8. **An absent offer market is not fabricated terms.** A regen with no
   published lifecycle says "No contract situation published"; no training fee
   or salary floor is drawn.
9. **A deliberate rule is labelled as one.** `hidden_competing_salary_amounts`
   means rival bids are withheld by design, and the UI says so, so it does not
   read as missing data.

### 2.3 Player Detail

Every route into Player Detail — the selected regen, a bloodline member, a
ranking row, a hall-of-fame row, a regen's parent — goes through
`gtex_player_navigator.dart`. No surface opens it any other way (§P3, §6).

### 2.4 The card

`gtex_player_card.dart` was **not** touched. §6 permits C only to *request*
`lineageLabel` on the canonical player card, and §4.1 assigns it to C; those
two clauses disagree, so this change takes the narrower reading and files the
request here instead:

> **Request to H / the card owner:** add `lineageLabel` (`String?`, default
> `null`) to `GtexPlayerCard` per §4.1, so a regen keeps its lineage when it is
> rendered as a market or portfolio row. C supplies the label; the field is not
> needed for anything in this change to work.

`gtex_regen_card.dart` (C-owned, §6) was changed in one place: its density
ladder keyed only on height, but in the side-by-side layout it is the details
*column* that runs out of room. A three-column grid on a wide screen leaves a
narrower column than a two-column grid on a small one, so chips wrapped onto
extra runs and overflowed a fixed cell. The ladder now also sheds the
least-load-bearing blocks when the column is narrow. The prospect grid's cell
height likewise now follows the width of a *card* rather than of the board.

---

## 3. WHAT THIS CHANGE DELIBERATELY DOES NOT DO

- **It does not touch `app_router.dart`, `gte_navigation_shell_screen.dart` or
  `app_destinations.dart`.** Those are H's alone (§7.4, §7.5). Regen was
  already a shell destination, so nothing was needed.
- **It does not consume `GtexValueTrend`.** E owns that contract (§4.2) and it
  has not merged to main. The regen value shown here is the regen economy's own
  `RegenValueSnapshot`, which is a different quantity — see §4.4.
- **It does not compute any rating, form or value in Dart.** Bands, growth
  curve, uniqueness, legacy and value components are rendered as the backend
  published them.
- **It does not call `GET /scout/report/{player_id}`.** See §4.3.
- **It does not wire the ownership *write* verbs** — offer quote, transfer
  listing, contract create/renew, transfer bids. They need auth and belong to a
  negotiation flow adjacent to D's club and B's wallet surfaces. See §4.2.
- **It does not touch market, portfolio, club or home files.**

---

## 4. MISSING CONTRACTS (§9.3 filings)

### 4.1 National-pool regens have no dossier — the largest population is dark

`GET /regen-universe/players/{id}` resolves through
`select(RegenProfile).where(RegenProfile.player_id == player_id)`
(`regen_universe/service.py:1257`). Rows in `national_regen_seeds` have **no
`RegenProfile`**, so for them lineage, personality, potential band, development
and value are all 404.

These are not a corner case: `LiveGtexRegenRepository.loadWorld` lists up to 48
of them, and per the operator notes the seeded national pools are the bulk of
the regen population.

**Interim behaviour:** the dossier panel states "No published dossier" and
explains that national-pool depth regens do not get one. Nothing is faked.

**Contract required — one of:**
- `GET /regen-universe/players/{id}` returns a showcase for seed rows, with the
  fields a seed genuinely has and nulls elsewhere; **or**
- `NationalRegenSeedPageView` carries a `has_published_profile: bool` so the
  client can render the correct state without a 404 round trip.

The second is cheaper and is the recommendation.

### 4.2 ~~Regen contracts are UI-only~~ — CORRECTED: they were unreached, not missing

**An earlier revision of this document claimed "no backend verb was found under
inspection" for regen contracts. That was wrong.** The search covered
`regen_universe/`, `regen_ecosystem/` and `regen_creation/` and missed
`app/segments/player_lifecycle/`, which exposes the whole surface:

| Endpoint | Returns |
|---|---|
| `GET /api/players/{id}/regen` | `RegenLifecycleView` — lifecycle phase, retirement pressure, free agency, transfer listing, agency message, personality traits, special training, **pressure state** and **offer market** |
| `GET /api/players/{id}/regen/offer-market` | `RegenContractOfferMarketView` — floor terms plus a visible count of competing offers |
| `POST /api/players/{id}/regen/contract-offers/quote` | currency conversion quote for an offer |
| `POST /api/players/{id}/regen/transfer-listing` | list / unlist |
| `GET`/`POST /api/players/{id}/contracts`, `/contracts/{id}/renew` | contract records |
| `/api/transfers/windows/...` bids, accept, reject | transfer market |

The models `RegenContractOffer` and `RegenOfferVisibilityState`
(`app/models/regen.py:689`) and the scoring in
`services/regen_transfer_addon.py` (`score_contract_offer`,
`compute_transfer_pressure`) all exist and are exercised.

**So this was a §9.1 surfacing gap, not a §9.3 contract gap**, and it is now
closed for the read path. The dossier's **Ownership** section renders
`GET /api/players/{id}/regen`: contract phase, free-agent / listed / retiring
state, the agency message, what the regen is agitating for (transfer request,
refusing terms, contract running down), and the offer market — training fee,
minimum salary and the count of competing clubs.

One product rule is surfaced explicitly rather than smoothed over:
`hidden_competing_salary_amounts` defaults true, so the backend publishes *how
many* clubs are in but not *what* they bid. The UI says that is by design, so
it does not read as missing data.

**Still not wired, deliberately:** the write verbs (`.../quote`,
`.../transfer-listing`, contract create/renew, transfer bids). They require
auth and belong to a negotiation flow, not a discovery screen; they are also
adjacent to club and wallet surfaces owned by D and B. **Filed as follow-up
work, not a missing contract.**

**Still genuinely absent:** a *world-level* aggregate of open regen contract
offers. `GtexRegenWorldData.contracts` remains empty from live data because
every endpoint above is keyed by a single player id. The Contracts lane
therefore still renders an empty board.

**Contract required (small):** `GET /api/regens/contract-offers?status=open`,
or equivalent, so the Contracts lane can list the market rather than requiring
a regen to be selected first. Until then that lane should be marked
`AppRouteSurfaceState.partiallyWired` — that flag lives in
`app_destinations.dart`, which only H may edit. **Filed for H.**

### 4.3 `GET /scout/report/{player_id}` writes on a GET

`RegenEcosystemService.get_scout_report` calls
`market_service.create_scout_report(...)` — it **persists a new scout report on
every GET** — and it requires a resolvable scout via `_resolve_report_scout`.

It was therefore **not** wired into a browse surface, where it would create a
row per card render. Scout confidence in the dossier comes from
`RegenProfileView.scout_confidence`, which is a stored field and free to read.

**Contract required:** either a read-only `GET /regens/{id}/scouting` that
returns the latest existing report, or make report generation an explicit
`POST`. Until then this endpoint is unsafe to call from a discovery screen.

### 4.4 Two value numbers for one regen

- `RegenValueSnapshot.current_value_coin` — the regen economy's valuation, with
  ability / potential / reputation / narrative / demand components.
- `PlayerSummaryReadModel.current_value_credits` — the market valuation that
  4E's matchday overlay feeds and that the portfolio prices against.

A tradable regen can therefore show one number in Regen World and a different
one in the Market for the same player. This pass renders the regen snapshot and
labels it "Value" inside the regen dossier only; it does not reconcile them.

**Contract required (C → E, A, B):** decide which number is authoritative for a
tradable regen, or name them distinctly in the UI. This is an economics
decision, not an engineering one, and it is flagged rather than papered over.

### 4.5 Lineage is keyed by regen profile id, browse is keyed by player id

`GET /regens/{regen_id}/lineage` takes a `regen_profile_id`; every browse
surface has a `player_id`. The client therefore resolves the profile id from
the showcase and issues a **second** request.

**Contract required (nice-to-have):** either accept a player id on that route,
or include the chain in `RegenUniversePlayerShowcaseView`, which already
carries the timeline and achievements. Until then the two requests are made
independently, and a failing chain degrades to "the full bloodline could not be
read" rather than discarding the dossier.

### 4.6 Rankings depend on a closed season

`/regen-universe/rankings` and `/hall-of-fame` are populated by season close
(`RegenUniverseCloseResultView`). If no season has closed, both are legitimately
empty. The lanes say so explicitly. No contract needed — recorded so the empty
state is not later mistaken for a bug.

---

## 5. VERIFICATION

| Check | Result |
|---|---|
| `flutter analyze` | No issues found |
| `test/regen_redesign/` | 42 passing |
| `flutter test --exclude-tags golden` | See PR body — run against the 796 baseline |
| Widths verified | 360, 420, 768, 1024, 1440, 1920 — no overflow, asserted by test |
| Router / shell / destinations touched | None |
| `gtex_player_card.dart` touched | No |
| Imports from `lib/legacy/`, `v1_original/`, `desktop_salvage_*` | None |

---

## 6. OPEN QUESTIONS FOR REVIEW

1. **§4.1 is the important one.** If national-pool seeds stay dossier-less, the
   regen world is a rich experience for a small minority of regens and a blocked
   state for the majority. That is honest but thin, and it is a product
   decision about whether seeds deserve profiles.
2. **§4.2 was filed wrong and is corrected.** Regen contracts *do* have a
   backend, in `segments/player_lifecycle`; the read path is now wired. What
   remains is a world-level list endpoint so the Contracts lane can show the
   market without a regen selected, and a decision on whether the write verbs
   belong to C or to D/B.
3. **§4.4 two value numbers.** Needs an owner before F builds a home digest
   that quotes one of them.
