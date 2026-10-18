# GTEX Player, Legend-Regen, FM23 Regen, and Staff Ingestion V2

**Status:** implementation contract / proposed work plan  
**Repository:** `wandemcphill/Global-Talent-Exchange`  
**Scope:** replace the old FM23 Genie Scout founding-player snapshot as the sole seed path with a source-aware pipeline for current footballers, FM23-generated regens, legend-derived regens, and football staff.

## 1. Product decisions

GTEX should have distinct ingestion lanes. A single CSV normalizer must not decide whether a row is a real footballer, a fictional regen, a historical legend reference, or a member of staff.

1. **Current real-world players** are refreshed from the current-data provider (the repository already has a Sportmonks worker and a Python real-player bulk-import service). The current provider is authoritative for current squad, club, competition, nationality, date of birth, and sourced current metrics.
2. **FM23 regens/newgens** are imported as GTEX regen-classified players, never as verified real-world footballers. Preserve the save/export ID where available, the save/snapshot identity, source attributes, and provenance. An FM-generated player must not enter the real-player universe just because Genie Scout exported it.
3. **Historical legends feed the legend-regen system.** A historical legend catalogue is a reference/seed source for era, nationality, position, foot, signature traits and attribute archetype. The intended playable GTEX entity is a unique `legend_regen` with a link back to the historical reference—not a second, accidental copy of the legend in the ordinary current-player pool. The existing direct-materialization/market path in the legendary registry must be reconciled with this product rule before a bulk launch. Do not silently mint both forms for the same seed.
4. **Managers, coaches, Head of Youth Development, General Managers/Directors of Football, and scouts** are personnel, not footballers. Import them through a staff lane and project them into GTEX's existing manager and club-staff systems. They must not be inserted into `ingestion_players`.
5. **Never wipe and reload the existing universe as a first step.** Use idempotent upserts, a dry-run report, explicit duplicate resolution, and a separate retirement/deactivation report. Existing player IDs, cards, share holdings, markets, career history and club relationships must remain stable.

## 2. Existing repository surfaces to preserve and connect

These existing areas were found in the repository and should be reused rather than replaced:

- `services/player-ingestion/`: Node worker for Sportmonks league/team/player ingestion, stable-hash upserts, sync checkpoints, queues and image handling.
- `backend/app/ingestion/real_player_ingestion_service.py`, `real_player_import_service.py`, and `real_player_import_sources.py`: Python bulk ingestion/normalization paths for real players.
- `backend/app/ingestion/fm23_genie_scout.py` and `backend/scripts/prepare_fm23_genie_scout_import.py`: existing legacy FM23 Genie Scout CSV parser. It currently emits a **real-player** bulk manifest, defaults to the dated FM23 founding snapshot and uses an FM23/Genie Scout provider identity. It must not be reused unchanged for newgen rows.
- `backend/app/models/regen.py`, `backend/app/services/regen_service.py`, `backend/app/services/regen_lineage_service.py`, `backend/app/services/regen_market_service.py`, and `backend/app/regen_universe/`: existing regen lifecycle, profiles, unique cards, lineage, portraits, scouting and market paths. Imported regens must be integrated with the appropriate full lifecycle—not left as bare `ingestion_players` rows.
- `backend/app/models/legendary_player.py`, `backend/app/services/legendary_player_service.py`, and `backend/app/legend_layer/`: historical/legend catalogue and current materialization paths. Reconcile their direct tradable-player assumptions with the product decision in §1.3.
- `backend/app/models/club_growth.py` and `backend/app/club_growth/`: canonical club staff market, skills, salary, contract and assignment models (`ClubStaffProfile`, `ClubStaffContract`, `ClubStaffAssignment`).
- `backend/app/models/manager_marketplace.py` and `backend/app/manager_marketplace/`: manager-specific tactical/personality and marketplace contracts. Do not duplicate its gameplay responsibilities in a new manager engine.

## 3. Canonical lanes

### A. Current real-world players

**Source of truth:** configured current provider (Sportmonks worker for live/current squad data, or a separately approved current-data provider).

Required behaviour:

- Store provider name, external player ID, source version, fetched-at/as-of timestamp, and source hash.
- Match/upsert on a stable provider ID and a maintained cross-provider identity map. Names alone are not identity. Where no reliable external ID exists, send ambiguous rows to review rather than auto-merging.
- Keep current real-world club/league and current metrics separate from GTEX-only ratings, reputation, card supply, shares, contract and career state.
- Use incremental refresh and report provider omissions. A player missing from one page or one failed API request must not be deactivated.
- Avoid overwriting user-owned market and lifecycle fields when updating external facts.
- Treat images and portraits as separate fields with source and rights metadata; never assume a URL is cleared for redistribution.

### B. FM23 regen/newgen export

Create a separate parser/import adapter (for example `fm23_genie_scout_regens.py`) with a versioned manifest and tests. The existing FM23 parser can remain for historical migration/audit, but it is not the new regen importer.

**Identity and classification**

- Preferred source identity: stable FM player ID plus a stable save/export identifier.
- Fallback identity: deterministic source key based on save ID plus normalized name, nationality, date of birth/age, primary position and club context. Record that a fallback key was used. Do not rely on name alone.
- Target player classification: `source_provider='gtex_regen'` (or a formally migrated source mapping), `is_real_player=false`, with source-specific provider/save identity retained in metadata and/or a source-crosswalk table.
- Create the related regen lifecycle data through the existing services, including required regen profile, unique card, portrait/face-bank metadata, lineage/origin, and market/card initialization where the player is eligible.
- Imported players should be marked as imported, with `generation_source='fm23_import'` or an accepted bounded enum equivalent. This must not be confused with a natively generated academy intake.
- Preserve raw Football Manager attributes and the original CA/PA or Genie Scout rating fields in source metadata. Implement and test an explicit documented normalization to GTEX's 1–99 ratings; do not silently treat every FM field as the same scale.
- Retain age, birth date/year, nationality, foot, positions, club-at-snapshot, preferred role, personality/traits, height, and source availability where provided.
- Imported save clubs are **historical/source context by default**, not automatic contracts with current GTEX clubs. A mapping/review is required before assigning a GTEX club, league, or squad tier.
- Build a dry-run manifest with create/update/skip/conflict counts, validation errors, duplicate clusters, and rating-distribution checks before writes.

### C. Legend-derived regens

Keep the historical catalogue as structured seed metadata. One approved historical reference can produce a unique GTEX `legend_regen` with a traceable lineage link and fictional/non-replicative presentation under GTEX's portrait policy.

Seed fields should include:

- stable historical reference key and approved canonical/reference name;
- nationality/country code, era, date/year of birth if sourced, dominant foot, primary/secondary position, height;
- researched technical, physical and mental archetype, role, signature traits and evidence;
- editorial/catalogue/rights status and portrait-generation policy;
- explicit deterministic generation seed/version and a link from the resulting regen to its historical reference.

The generated regen is a GTEX in-world career entity: unique identity, regen age/birth year, independently generated face-bank/avatar parameters, GTEX attributes (derived from a reviewed legend archetype), personality, potential, career, contracts, cards and market lifecycle. Make the output deterministic and idempotent per reference + generation version. If the generation recipe changes, create an explicit versioned revision path rather than duplicating the same legacy regen on every import.

**Important conflict to resolve in implementation:** `docs/LEGENDARY_PLAYER_REGISTRY.md` and the current legendary launch/foundation services materialize historical profiles as ordinary tradeable `ingestion_players` records. That conflicts with the desired legend-as-regen treatment if both paths run for the same reference. The migration must decide whether historical records remain reference-only, are hidden/non-tradable catalogue entries, or are retired from the playable universe after linked regens are safely created. Do not delete existing legendary player rows, markets or holdings without a reviewed migration and impact report.

### D. Managers and club staff

Normalize source roles into a controlled taxonomy while retaining each source's original title:

| Canonical role | Typical source titles | GTEX integration |
|---|---|---|
| `manager` | manager, head coach | Existing manager tactical/personality/market path; link to appropriate club-staff assignment where the product needs both views |
| `assistant_manager` | assistant manager | Club staff profile/contract/assignment |
| `coach` | coach, first-team coach, technical coach | Club staff profile/contract/assignment with skill profile |
| `goalkeeping_coach` | goalkeeping coach | Club staff profile/assignment |
| `fitness_coach` | fitness coach, sports scientist where applicable | Club staff profile/assignment |
| `head_of_youth_development` | Head of Youth Development, youth development manager | Club staff role; feeds academy quality, intake recommendations and development effects |
| `scout` | scout, regional scout, youth scout | Club staff role; scouting skill profile and report-generation effects |
| `chief_scout` / `head_of_recruitment` | chief scout, head of recruitment | Club staff role; scouting-team leadership and recruitment recommendations |
| `general_manager` | general manager, director of football, sporting director | Club staff role; transfer strategy, roster planning, negotiation and owner-advisory effects |
| `technical_director` | technical director | Club staff role; coaching pathway, tactical/technical development |

If the exported data has additional roles, preserve them as source titles and put unknown roles in a review queue. Do not silently coerce every staff row to `coach`.

**Staff identity and profile**

- Preserve stable source ID, source/save version, name, aliases, nationality, birth date/year, role history, current club at snapshot, reputation, contract/salary data as reference values, preferred playing/tactical philosophy, and every available FM attribute.
- Map attributes to explicit skill dimensions, normalizing source scales into GTEX's documented scale; preserve raw values to allow recalibration.
- Staff are not automatically assigned to a GTEX club from the FM club field. Create a personnel catalogue first, then assign/contract only through an explicit GTEX mapping or staff market action.
- Upsert current staff identities independently from role/club assignments. A person changing club or role should update role history/current context, not produce a second person.
- Existing `ClubStaffProfile` has a unique `market_key`; staff imports need deterministic keys and source metadata. Existing `ManagerProfile` has separate manager-specific behaviour fields and cannot by itself be used as the universal identity registry. Implement a clear mapping between canonical imported identity and these role-specific gameplay projections.
- General Manager, Head of Youth Development and Scout data must actually affect club logic after assignment: GM informs owner decisions/transfer planning; HoYD influences academy intake and development; scouts influence discovery, report confidence and prospect recommendations. Ingestion-only fields are not a shipped feature unless consumed by their services.

## 4. Proposed input packages

Use separate, versioned manifests rather than an ambiguous all-in-one CSV:

1. `current_players`: current provider snapshot or provider API run.
2. `fm23_regens`: Genie Scout newgen/regens CSV plus a stable `save_id` and export timestamp.
3. `legend_catalogue`: curated JSON/CSV of legend reference profiles plus source evidence and governance statuses.
4. `fm23_staff`: staff/personnel export plus `save_id` and export timestamp.
5. Optional mapping manifests: provider-ID crosswalks, current-club mappings, and manually resolved duplicate/role conflicts.

Every import batch should have a batch ID, provider/version, as-of timestamp, source-file hash, dry-run/commit mode, row-level errors, audit output and idempotent rerun behaviour.

## 5. Data quality, safety and operational controls

- **Dry run by default** for first ingestion of every new batch/source. A commit flag must be explicit.
- Preflight duplicate reports across current-player providers, existing FM23 players, legend references, and regens.
- Keep old rows and all market/card/ownership/career references intact during comparison. Never use a bulk delete/reinsert.
- Do not reassign old player IDs; foreign keys may be referenced in markets, cards, match histories, holdings, national-team records, and Unity payloads.
- Require distribution checks: counts by source/role/nationality/position/age, missing IDs, implausible ages, rating histograms, unrecognized positions, duplicate identities and missing country/club links.
- Use transactions per validated batch or bounded chunk; record row-level success/failure and permit safe resumption.
- New imports should be reversible at the **source-membership** level: a failed or superseded source can be quarantined/deactivated without erasing user-owned or match-history data.
- Keep FM23 as a versioned historical simulation source. Do not call its data “current real-world” data or let a scheduled live refresh overwrite it.
- Before commercial distribution, review the rights/terms attached to each provider and game-data export, and treat real-person portraits as a distinct rights-controlled asset. A data source being exportable does not itself establish redistribution permission.

## 6. Suggested implementation sequence

1. **Inventory and protection:** record current counts and provider splits for current players, native regens, legend records, cards/markets and staff. Capture a restorable backup and audit export.
2. **Schemas/contracts:** specify versioned manifest shapes and source-identity rules for each lane; document GTEX rating/attribute conversion.
3. **FM23 regen adapter:** parser, normalizer, dry-run CLI, duplicate report, tests, and integration through existing regen/card/market services.
4. **Legend-to-regen adapter:** reconcile legacy direct materialization; generate unique linked `legend_regen` profiles with deterministic identity/attributes/portrait metadata; test lineage and duplicate protection.
5. **Staff/personnel adapter:** stable staff identity, role normalization, source attributes, manager/staff profile mappings, and dry-run/commit flows.
6. **Current player refresh:** confirm current provider coverage, identity crosswalks and non-destructive refresh behaviour; import only after staging and duplicate review.
7. **Gameplay integration:** wire manager personality/tactics; GM advisory and transfer-planning influence; HoYD academy/intake influence; scout discovery/report influence; coaches' training/development effects.
8. **Validation and rollout:** run unit/integration tests; stage a small representative batch; audit database/card/market counts; verify UI and match/Unity payloads; only then run the full import.

## 7. Acceptance criteria

- Re-running an identical batch creates no duplicate players, regens, staff, cards, markets, or legend links.
- A current footballer can be refreshed without changing their GTEX player ID or user-owned market/card/career state.
- An FM23 regen is never flagged as a verified current real-world player.
- Every imported legend-derived regen is uniquely linked to one approved historical reference, has generated non-replicative portrait metadata, and can be surfaced by regen/lineage APIs.
- A historical legend seed cannot accidentally produce both a direct ordinary-player market asset and a separate legend regen in the active universe unless an explicit approved product rule allows it.
- Imported staff never appear in player search/squads as footballers.
- Every staff role preserves the source title and maps to a reviewed canonical role; unknown roles are reported.
- Assigned managers, coaches, GMs, Heads of Youth Development, and scouts are consumed by their relevant gameplay systems.
- First run outputs a reconciliation report covering creates, updates, skipped rows, conflicts, invalid rows, unlinked roles, duplicate candidates, missing required data and market/card impact.
- No production mutation occurs until dry-run output is reviewed and a backup/rollback path is verified.
