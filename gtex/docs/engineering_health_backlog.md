# Engineering Health Backlog

Updated: 2026-04-19

## Build Blockers

- Backend pytest collection was previously blocked by permission-denied temp directories under `backend/.pytest*` and `backend/.tmp*`. Discovery now ignores those paths and bootstraps the repo + `backend/` import roots from the top-level `conftest.py`.
- Backend collection also previously broke on stale test imports from `app.main`. Compatibility `INITIAL_ADMIN_*` constants are restored so existing smoke tests can authenticate the bootstrap admin again.
- The app-level backend harness is now green again after the mounted-app contract suite was split and hardened. Current verified signal:
  `python -m pytest backend/tests/app/test_main.py backend/tests/app/test_module_registration_openapi.py backend/tests/app/test_module_registration_routes.py backend/tests/app/test_module_registration_hydration.py -q`
  -> `496 passed in 666.84s`
- `python -m pytest backend/tests/app -q --collect-only` now completes successfully with `557 tests collected in 71.91s`.
- Frontend hard errors are currently cleared, with the remaining match-viewer blockers already addressed in the working tree:
  `frontend/lib/features/match/live_match_session_service.dart` restores the `GteBackendMode` import,
  the affected replay/competition tests now pass `matchType`,
  and `frontend/pubspec.yaml` declares the missing `web_socket_channel` and `fake_async` packages.
- CI now enforces two minimum gates:
  frontend hard analyzer errors must stay at zero,
  backend collection plus a small event/leaderboard smoke slice must stay green.
- CI now also runs the app-level backend harness:
  `backend/tests/app/test_main.py`,
  `backend/tests/app/test_module_registration_openapi.py`,
  `backend/tests/app/test_module_registration_routes.py`,
  and `backend/tests/app/test_module_registration_hydration.py`.

## Runtime-Risk Issues

- Backend consolidation `Batch A` is now closed in code. The remaining wallet namespace drift was removed by standardizing frontend calls onto `/api/wallets/...` and exposing matching plural compatibility aliases for wallet profile, transactions, and top-up operations in the backend. Verification now includes `frontend/test/wallet_api_route_transport_test.dart` plus the mounted-app OpenAPI contract slice.
- Event serialization previously coupled `app.core.events` to ORM-backed outbox imports. `make_json_safe` now lives in `backend/app/core/serialization.py`, and outbox model loading is lazy inside `build_outbox_event()`, which keeps the event stack import-safe for leaderboard startup wiring.
- The mounted-app contract harness now reuses a session-scoped migrated SQLite database, uses module-scoped app/client fixtures, skips lifespan startup for pure OpenAPI snapshots, and disables distributed rate limiting inside the harness. That keeps route-contract tests fast enough to run end to end without `429` noise.
- The app-level harness now also reuses a session-scoped migrated SQLite template database for both `test_main.py` and the mounted-app contract suite. Individual test DBs are copied from that template instead of replaying the full Alembic chain every time. On this machine that cut:
  `backend/tests/app/test_main.py` from about `21m` to about `5m38s`,
  the split mounted-app contract suite from about `15m` to about `4m51s`,
  and the combined app-level run to about `11m06s`.
- `frontend/lib/features/match/live_match_session_service.dart` still deserves direct behavioral coverage for malformed websocket paths, absolute websocket URLs, and relative path upgrades from HTTP(S) to WS(S).
- Backend collection now succeeds, but the warning surface still includes deprecated Pydantic V2 class-based config usage in dispute/governance schemas. That is not a build blocker today, but it is a near-term upgrade risk.

## Lint Hygiene

- `flutter analyze --no-pub` currently reports non-hard findings only. The main clusters are:
  unused private helpers and imports,
  deprecated Flutter widget APIs,
  `use_build_context_synchronously`,
  and public APIs exposing private helper types in the data layer.
- Cleanup priority should follow production leverage:
  lifecycle and async-context lints first,
  then deprecated UI API migrations,
  then dead-code/unused-element cleanup.
- The new frontend analyzer gate intentionally does not fail on warnings/info yet. That keeps active development unblocked while preventing a regression back to hard compile/analyzer failures.
