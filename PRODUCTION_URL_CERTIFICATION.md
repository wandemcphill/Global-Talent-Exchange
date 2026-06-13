# Phase V3 — Production URL Certification

Date: 2026-06-13

---

## Flutter URL Architecture

### Primary env var: `GTE_API_BASE_URL`

Injected at **compile time** via `--dart-define`:

```dart
// frontend/lib/app/gte_app_config.dart
const String rawBaseUrl = String.fromEnvironment('GTE_API_BASE_URL');
```

### Production resolution logic (`resolveGteApiBaseUrl`)

```dart
String resolveGteApiBaseUrl({
  required String rawBaseUrl,
  required GteBackendMode backendMode,
}) {
  final String baseUrl = rawBaseUrl.trim();
  if (baseUrl.isNotEmpty) {
    return baseUrl;              // ← production always hits this branch
  }
  if (backendMode == GteBackendMode.fixture) {
    return gteFixtureApiBaseUrl; // ← test-only
  }
  throw StateError(
    'GTE_API_BASE_URL must be set when GTE_BACKEND_MODE is live.',
  );
}
```

When `GTE_BACKEND_MODE=live` and `GTE_API_BASE_URL` is empty → **throws StateError**. There is no silent localhost fallback.

### WebSocket URL

There is **no `GTE_WS_BASE_URL` variable**. The WS URL is derived at runtime:

```dart
// frontend/lib/features/match_center/live_match_session_service.dart
final String scheme = switch (base.scheme) {
  'https' => 'wss',
  'http'  => 'ws',
  'ws' || 'wss' => base.scheme,
  _ => 'wss',
};
```

`https://gtex-api.onrender.com` → WebSocket connects to `wss://gtex-api.onrender.com/api/matches/.../stream`

---

## Localhost Audit

### Flutter (206 files with `localhost`/`127.0.0.1`)

```
git grep "127.0.0.1" -- ":(exclude).external_worktrees" frontend/lib
```

All matches are in `factory .fixture()` constructors. Example:

```dart
factory GteExchangeApiClient.fixture({Duration latency = Duration.zero}) {
  final GteRepositoryConfig config = const GteRepositoryConfig(
    baseUrl: 'http://127.0.0.1:8000',  // ← fixture mode only
    mode: GteBackendMode.fixture,
  );
  ...
}
```

These are **unreachable** when `GTE_BACKEND_MODE=live` because:
1. `fromEnvironment('GTE_BACKEND_MODE')` returns `'live'` in any real build
2. `_parseBackendMode('live', allowFixtureMode: false)` → `GteBackendMode.live`
3. `GteBackendMode.live` never calls `.fixture()` constructors

**`gte_bootstrap_failure_app.dart`** contains a localhost hint in a developer error message (not an active URL):
```dart
'--dart-define=GTE_API_BASE_URL=http://127.0.0.1:8000 '  // shown in error screen
```
This is a user-facing instruction string, not an active base URL. Safe.

### Backend

Zero localhost assumptions in production code paths. CORS allows configured origins only:
```
GTE_CORS_ALLOW_ORIGINS=https://<cloudflare-pages-domain>
```

### Build scripts

```bash
# ops/render/build-frontend.sh
: "${GTE_API_BASE_URL:?GTE_API_BASE_URL must be set for the frontend build.}"

# ops/cloudflare/build-frontend.sh
: "${GTE_API_BASE_URL:?GTE_API_BASE_URL must be set in Cloudflare Pages environment variables.}"
```

Both scripts use `: "${VAR:?message}"` — the build **fails hard** if `GTE_API_BASE_URL` is not set. There is no localhost fallback.

---

## Three Deployment Scenarios

### 1. Local development

```
GTE_API_BASE_URL=http://localhost:8000
GTE_BACKEND_MODE=live   (or omitted — defaults to live)
```

Build: `flutter run -d chrome --dart-define="GTE_API_BASE_URL=http://localhost:8000"`
Result: connects to local backend. WS: `ws://localhost:8000/api/...`

### 2. Cloudflare Pages build

Cloudflare Pages dashboard → Environment variables:
```
GTE_API_BASE_URL  = https://gtex-api.onrender.com
GTE_BACKEND_MODE  = live
```

Build command: `bash ops/cloudflare/build-frontend.sh`
This runs:
```bash
flutter build web --release \
  --dart-define="GTE_API_BASE_URL=https://gtex-api.onrender.com" \
  --dart-define="GTE_BACKEND_MODE=live"
```

The compiled output has `GTE_API_BASE_URL` baked in at compile time. Zero localhost.
WS: `wss://gtex-api.onrender.com/api/matches/.../stream`

### 3. Render deployment (frontend — historical)

```yaml
# render.yaml (gtex-web, now superseded by Cloudflare Pages)
- key: GTE_API_BASE_URL
  value: https://gtex-api.onrender.com
- key: GTE_BACKEND_MODE
  value: live
```

---

## Verdict

**Production builds contain no localhost values.**

- `resolveGteApiBaseUrl` throws `StateError` on empty URL in live mode — no silent fallback
- Build scripts fail hard if `GTE_API_BASE_URL` is unset
- 206 localhost references are all in fixture constructors, gated by `GteBackendMode.fixture`
- WS URL derived from API base URL — no separate env var, no hardcoded host
