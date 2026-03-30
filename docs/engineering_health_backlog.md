# Engineering Health Backlog

Updated: 2026-03-30

## Build Blockers

- Backend pytest collection was blocked by permission-denied temp directories under `backend/.pytest*` and `backend/.tmp*`. Discovery now ignores those paths and bootstraps the repo + `backend/` import roots from the top-level `conftest.py`.
- Backend collection also broke on stale test imports from `app.main`. Compatibility `INITIAL_ADMIN_*` constants are restored so existing smoke tests can authenticate the bootstrap admin again.
- Frontend hard errors are currently cleared, with the remaining match-viewer blockers already addressed in the working tree:
  `frontend/lib/features/match/live_match_session_service.dart` restores the `GteBackendMode` import,
  the affected replay/competition tests now pass `matchType`,
  and `frontend/pubspec.yaml` declares the missing `web_socket_channel` and `fake_async` packages.
- CI now enforces two minimum gates:
  frontend hard analyzer errors must stay at zero,
  backend collection plus a small event/leaderboard smoke slice must stay green.

## Runtime-Risk Issues

- Event serialization previously coupled `app.core.events` to ORM-backed outbox imports. `make_json_safe` now lives in `backend/app/core/serialization.py`, and outbox model loading is lazy inside `build_outbox_event()`, which keeps the event stack import-safe for leaderboard startup wiring.
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
