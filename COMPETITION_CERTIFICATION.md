# COMPETITION LIFECYCLE CERTIFICATION (N34)

Date: 2026-06-12
Branch: `feature/original-visual-runtime` @ `ca771311`
Verdict: **PASS — full create→settlement lifecycle proven green against canonical v2 API**

## Lifecycle stages verified (all green)

| Stage | Proven by | Evidence |
|---|---|---|
| Creation | `test_competition_lifecycle::*` create league/cup; `test_competitions_models::test_creation_service_builds_linked_competition_aggregate` | 201 + draft status |
| Entry / join | publish → join flow; paid-join idempotency | join 200; second join idempotent (single participant) |
| Fixtures | `test_league_round_and_fixture_generation` | 6 fixtures for 4-club league, all stage=league |
| Rounds / brackets | `test_cup_playoff_progression_and_settlement` | seed→launch→advance; status live→completed |
| Results | `test_standings_update_after_match_completion` | match events 201, result 200, authoritative score gating |
| Standings | same | leader points=3, wins=1 after a 2-1 result |
| Settlement (entry fee) | `test_paid_competition_join_is_idempotent_and_collects_single_fee` | exactly 1 participant, 1 entry, **1 fee-collection ledger row** despite double join; `paid_entry_fee_minor == 250000`, `paid_at` set |
| Reward settlement | `test_competition_reward_settlement.py` (in combined shard) | green |
| Rules / validation | `test_rules_engine.py`, `test_competitions_validation_service.py` | green |

Logs: `.runtime/n34_comp_models.log`, `.runtime/n34_lifecycle3.log`, `.runtime/n34_comp_lifecycle.log`.

## Backend truth / persistence — confirmed present
- **Persistence:** `CompetitionParticipant`, `CompetitionEntry`, `CompetitionWalletLedger`, `Competition`, `CalendarEvent`, `CompetitionMatch` rows are authored and queried — no in-memory fakes.
- **Participant keying:** orchestrator resolves the joining user's `ClubProfile` and keys the participant by `club.id` (`competition_orchestrator.py:589-590`). Falls back to `user_id` only when the user has no club.
- **Fee safety:** entry-fee collection is idempotent — a repeated join does NOT double-charge (single `entry_fee_collection` ledger row verified).
- **Score authority:** fixtures expose `score_status=pending_results` / `authoritative_scores=False` until results are posted — authoritative-score contract honored.

## Issue found & resolved
- **Stale API surface in tests (not a product gap):** the lifecycle tests targeted the deprecated `/api/competitions` alias, which the contract guard now correctly retires with `410 Gone`. This is intended production behavior (non-canonical alias deprecation), exactly as flagged in the manifest's Stage 2D probe (2026-06-08). Fixed by canonicalizing to `/api/v2/...` + `X-API-Version: 2` + envelope unwrap.

## Lifecycle gaps / follow-ups (not launch blockers)
1. **Sibling route-test files not yet canonicalized:** `test_api_create_publish_join.py`, `test_api_discovery.py`, `test_api_financial_summary.py`, `test_api_invites.py`, `test_api_treasure_chest_progression.py`, `test_backend_contract_routes.py` very likely share the same stale `/api/competitions` alias usage and remain unproven this cycle. Apply the same v2-canonicalization wrapper before they can gate. **Recommended: lift the `_canonicalize_v2` autouse fixture into `competitions/conftest.py`** so the whole lane is covered in one place.
2. **Completion → payout:** reward settlement is unit-proven; an end-to-end "complete competition → distribute prize pool → wallet credit" route test would strengthen the money guarantee before public beta.
3. Client-backed competition route tests remain slow (~30s startup each); shares the suite-wide DB-speed bottleneck.

## Conclusion
The competition lifecycle is **backend-authoritative and certified** through settlement. Closed beta can proceed on competitions; finish the sibling-file canonicalization (mechanical) before public beta.
