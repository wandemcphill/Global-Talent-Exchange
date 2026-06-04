# GTEX Boot Health Report

Generated: 2026-06-04

## Frontend Boot Evidence

Frontend app boot is canonical Flutter/Riverpod/GoRouter:

- `frontend/lib/main.dart` initializes Flutter, theme, app config, secure auth session store, stored session, and `GteExchangeController`.
- `frontend/lib/main.dart` starts `ProviderScope` with overrides for `authSessionStoreProvider`, `deviceIdentityStoreProvider`, and `initialAuthSessionProvider`.
- `frontend/lib/app/gte_frontend_app.dart` builds `GteFrontendApp`, configures reliable event queue, syncs `GteExchangeController` with `appSessionControllerProvider`, and wires `MaterialApp.router`.
- `frontend/lib/router/app_router.dart` defines the production `buildGtexAppRouter`.

Live boot proof:

- `flutter run -d web-server --web-hostname 127.0.0.1 --web-port 5317 --no-pub` served `lib/main.dart` at `http://127.0.0.1:5317`.
- `Invoke-WebRequest http://127.0.0.1:5317` returned HTTP `200`.
- Startup was slow: Web SDK download took 143.2s and the web-server debug connection wait took 1070.8s.

## Frontend Route Registration

Active production router:

- `frontend/lib/router/app_router.dart`
- canonical shell roots from `frontend/lib/router/route_constants.dart`:
  - `/app/world`
  - `/app/market`
  - `/app/club`
  - `/app/compete`
  - `/app/capital`
  - `/app/community`
  - `/app/creator`
  - `/app/admin`

Shell bootstrap:

- `frontend/lib/screens/gte_exchange_shell_screen.dart` delegates shell routes to `GteNavigationShellScreen.fromPath`.
- `frontend/lib/features/navigation/presentation/gte_navigation_shell_screen.dart` mounts `GtexOperatingShell`.
- The shell schedules `controller.bootstrap()`, competition bootstrap, creator access priming, and route data priming.
- Periodic live refresh is started outside test bindings.

## Provider and Auth Registration

Evidence:

- `frontend/lib/shared/providers/auth_provider.dart` defines `authSessionStoreProvider`, `appSessionControllerProvider`, `authProvider`, `authedApiProvider`, and `sessionHydrationProvider`.
- `GteFrontendApp` listens to `appSessionControllerProvider` and syncs auth state with `GteExchangeController`.
- `authedApiProvider` is built from API base URL, backend mode, auth session, session store, and device identity.

Concern:

- `sessionHydrationProvider` exists, but current static evidence did not show production boot explicitly watching it.
- `appRealtimeSyncProvider` exists, but current static evidence showed definitions/tests, not a clear production boot read.

## Backend Boot Evidence

Backend boot chain:

- `backend/app/asgi.py` exposes `app = get_asgi_app()`.
- `backend/app/main.py` `create_app` builds FastAPI, container, state, core routes, API contracts, modules, tracing, and CORS.
- `backend/app/main.py` `register_core` mounts health/static routes, middleware, and dependency overrides.
- `backend/app/main.py` startup initializes runtime context, binds app state, binds realtime loop, checks DB/Redis, starts outbox relay, refreshes metrics, and starts deferred startup.
- `backend/app/core/container.py` creates `RealtimeHub`, subscribes it to domain events, and binds it to `app.state.realtime`.

Targeted backend tests did start real app lifecycles and logged `app.shutdown.complete`, but route contract failures prevent a clean boot-health pass.

## Backend Route and Websocket Registration

Central module registration:

- `backend/app/modules.py` `register_modules`.
- Eager modules include `realtime`, `competitions`, `live_matches`, `matches`, `broadcast`, `match_viewer`, hosted competitions, streamer tournaments, and world simulation.

Websocket evidence:

- `backend/app/realtime/router.py` registers `/realtime/stream`, `/realtime/wallet/stream`, `/realtime/matches/{match_id}/stream`, and `/ws/match/{match_id}`.
- `backend/app/live_matches/router.py` registers `/matches/{match_id}/stream`, `/api/matches/{match_id}/stream`, commentary stream, and audio stems stream.
- `backend/app/api_v1/router.py` registers `/api/v2/ws/match/{match_id}`, `/api/v2/ws/market/{listing_id}`, and `/api/v2/ws/notifications`.
- `backend/app/transfer_market/router.py` registers `/api/transfer-market/listings/{listing_id}/stream`.
- `backend/app/broadcast_network/router.py` registers broadcast channel and audio websocket streams.

## Collisions and Hanging Paths

| Risk | Evidence | Impact |
|---|---|---|
| Parallel frontend routers | Production boot uses `frontend/lib/router/app_router.dart`; `frontend/lib/navigation/app_router.dart` still defines a separate `appRouterProvider` and route map. | Tests and features can drift from production navigation. |
| Realtime provider duplication | `shared/realtime`, `features/shell/realtime`, and shell providers define similar realtime provider families. | Duplicate connections or mixed contracts if imported together. |
| Backend websocket collision gap | Module registration collision fingerprinting covers HTTP routes, but websocket route collision protection was not evident. | Duplicate websocket paths may not be detected during module registration. |
| Lazy websocket risk | `api_v1` is lazy, while websocket-only access may not trigger HTTP middleware hydration. | `/api/v2/ws/*` availability can depend on prior HTTP/OpenAPI hydration. |
| Slow frontend web boot | Web-server launch took over 20 minutes before serving. | Developer/prod validation loops are too slow. |
| Route contract failures | Contract suite returned 20 failures, many `410 Gone` instead of expected live/auth responses. | Boot may succeed technically while production route surface is not healthy. |

## Boot Verdict

The application can boot far enough to serve Flutter web HTML and initialize backend app lifecycles in tests. It is not a healthy production boot: route contracts fail, router/provider duplication remains, websocket collision coverage is incomplete, and frontend web startup is too slow for a confident release gate.

