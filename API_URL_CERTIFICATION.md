# Phase S10 — API & WebSocket URL Certification

Date: 2026-06-14

Target architecture:
- Frontend: `https://app.gtex.com` (Cloudflare Pages)
- Backend: `https://api.gtex.com` (Render)
- WebSocket: derived `https://` → `wss://`, `http://` → `ws://`

## API Base URL Resolution

`frontend/lib/app/gte_app_config.dart::resolveGteApiBaseUrl`:
```dart
final String baseUrl = rawBaseUrl.trim();
if (baseUrl.isNotEmpty) return baseUrl;          // production
if (backendMode == GteBackendMode.fixture) return gteFixtureApiBaseUrl;  // test only
throw StateError('GTE_API_BASE_URL must be set when GTE_BACKEND_MODE is live.');
```
In live mode with an empty URL it **throws** — no silent localhost fallback.

## WebSocket Derivation (proven)

`frontend/lib/features/match_center/live_match_session_service.dart:46`:
```dart
final String scheme = switch (base.scheme) {
  'https' => 'wss',
  'http'  => 'ws',
  'ws' || 'wss' => base.scheme,
  _ => 'wss',
};
```
Same derivation in `app_realtime_provider.dart`, `transfer_provider.dart`,
`gtex_realtime_providers.dart`. There is **no `GTE_WS_BASE_URL`** — the WS host always follows the API host.

`https://api.gtex.com` → `wss://api.gtex.com/api/matches/.../stream`

## Three Build Scenarios

### 1. Local
```
GTE_API_BASE_URL=http://localhost:8000   GTE_BACKEND_MODE=live
```
→ API `http://localhost:8000`, WS `ws://localhost:8000/...`

### 2. Cloudflare Pages
```
GTE_API_BASE_URL=https://api.gtex.com    GTE_BACKEND_MODE=live
```
Build: `bash ops/cloudflare/build-frontend.sh` → bakes the URL at compile time.
→ API `https://api.gtex.com`, WS `wss://api.gtex.com/...`

### 3. Production (release)
```
flutter build web --release --dart-define=GTE_API_BASE_URL=https://api.gtex.com --dart-define=GTE_BACKEND_MODE=live
```
Compiled artifact contains the production URL only — zero localhost.

## Drift / Leakage Checks

| Check | Result |
|---|---|
| Localhost in live path | ❌ none (see `WEB_DEPLOYMENT_AUDIT.md`) |
| Hardcoded Render URL in `frontend/lib` | ❌ none |
| Separate WS endpoint that could drift | ❌ none — derived |
| Empty URL silently defaulting | ❌ throws `StateError` |

## Verdict: API & WEBSOCKET ROUTING PRODUCTION-SAFE
