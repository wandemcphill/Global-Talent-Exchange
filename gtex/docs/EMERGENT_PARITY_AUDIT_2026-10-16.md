# GTEX Parity Audit (2026-10-16)

Scope: repo planning docs vs. what actually runs. Sources: NEXT_IMPLEMENTATION_TODO.md, docs/GTEX_PARTIAL_COMPLETION_BACKLOG.md, docs/GTEX_REVAMP_BACKLOG.md, GTEX_P6_PRODUCTION_GAP_BACKLOG.md, IMPLEMENTATION_GAP_REPORT.md.

## Runtime status in this environment
- The repo's own Flutter app (`frontend/`) is now built with `flutter build web` and served at the preview URL against the repo's own FastAPI backend (`backend/`). The separate React console is no longer served.
- Verified live: landing, sign-in, signed-in Club Operations home with the user's club.

## Fixed in this pass (repo code)
| Area | Problem | Fix |
|---|---|---|
| GTEX runtime / jackpot / world pulse | `GtexUniverseService` is `@dataclass(slots=True)` and used zero-arg `super()` -> `TypeError` on every `/api/v2/jackpot/state` and gtex runtime call ("Loading World Pulse" / OFFLINE panels) | `gtex_universe/service.py`: explicit `GtexBaseService.__init__(self, ...)` |
| Auth / profile | Flutter contract canonicalises `/api/auth/me` (and other `/api/auth/*`) to `/api/v2/auth/*`, but only login/signup existed on v2 -> 404 on `/api/v2/auth/me` | `auth/router.py`: mirror all missing `/api/auth/*` routes onto `/api/v2/auth/*` |
| Web boot | Browsers that report POSIX locales (`en-US@posix`) crash Flutter web with `RangeError: Incorrect locale information` (blank screen) | `frontend/web/index.html`: normalise `navigator.languages` before boot |

## Planned items: status
| Item (source) | Status |
|---|---|
| 10% withdrawal fee on trade + e-game withdrawals (NEXT_IMPLEMENTATION_TODO) | Implemented in backend policy (`admin_godmode` `withdrawal_fee_bps=1000`, `economy/economic_policy.py`) |
| Partial-surface backlog items 1–8 (regen create-a-son, newsroom, ad overlay, personal manager office, jackpot admin, KYC queue, disputes, withdrawals/purchase orders) | Marked DONE in repo; dispute hard-resolve endpoint still absent (by design note) |
| Coin trader UX + trading (System A) | Marked complete in repo |
| Lineup pipeline: AI auto-draft fallback (`ai_manager.SquadPlanner`) instead of hardcoded 4-3-3 (REVAMP Track B) | NOT done: `match_engine/services/team_factory.py::_resolve_lineup` falls back saved XI -> saved formation -> coach formation -> 4-3-3 |
| Real-player multi-position `secondary_positions_json` (Track B) | Migration present; needs re-ingest to populate |
| Squad-tier pipeline (Track B) | Router/schemas present (`squad_tiers/`); backfill is an ops step |
| Home: `_TransferTicker` BLOCKED badge / `_RouteLaunchButton` copy (Track E) | No remaining "BLOCKED"/"remains blocked" strings found in `features/home/home_screen.dart` |
| Persistent LOADING / "market unavailable" states (Track E) | PARTIAL: world pulse fixed (above). `/api/v2/players/markets` returns 503 because it routes to the API v1 demo facade (`api_v1/service.py`) while demo fixtures are disabled; needs wiring to the real market service |
| P6 #0 inputs: production `GTE_API_BASE_URL`, bootstrap admin password in vault | BLOCKED on owner input |
| P6 #3 KoraPay webhook contract | Needs KoraPay keys + `GTE_KORAPAY_NOTIFICATION_URL` |

## Work added earlier in this session that sits outside the original design
- `backend/app/owner_console/` (+ migration `20261016_0130`) and the React app in the Emergent `/app/frontend` workspace. They duplicate surfaces GTEX already has. The React app is no longer served; the owner_console module is still registered and can be removed on request.
