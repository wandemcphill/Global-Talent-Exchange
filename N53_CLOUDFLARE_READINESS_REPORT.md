# N53 — Cloudflare Pages Readiness Report

Date: 2026-06-14
Branch: main (working branch `deployment/supabase-cloudflare`)

The contract gate that blocked the deployment pipeline is now green (see
`N53_CONTRACT_FIX_REPORT.md`). This report confirms Cloudflare Pages build
readiness is intact and was not disturbed by the N53 fix.

## 1. Flutter project location

```
$ test -f frontend/pubspec.yaml → YES
$ test -f pubspec.yaml (repo root) → NO
```

The Flutter app lives in **`frontend/`**. Cloudflare Pages must use `frontend` as
the build root (or invoke the build script from repo root, which `cd`s into it).

## 2. Build command and output

`ops/cloudflare/build-frontend.sh` (unchanged by N53):

```bash
cd "${FRONTEND_DIR}"
flutter pub get
flutter build web --release \
  --dart-define="GTE_API_BASE_URL=${GTE_API_BASE_URL}" \
  --dart-define="GTE_BACKEND_MODE=${GTE_BACKEND_MODE}"
```

- Build output: **`frontend/build/web`** (Flutter's default `build/web` relative to
  the frontend dir). This is the Cloudflare Pages output directory.
- `GTE_API_BASE_URL` is **required** — the script hard-fails with
  `: "${GTE_API_BASE_URL:?...}"` if unset.
- `GTE_BACKEND_MODE` defaults to `live`.

## 3. `--dart-define` injection

`GTE_API_BASE_URL` is injected at compile time via `--dart-define` and read in
Dart through `String.fromEnvironment('GTE_API_BASE_URL')`. Production builds bake
the value in; there is no localhost fallback in live mode
(`resolveGteApiBaseUrl` throws `StateError` on an empty URL when backend mode is
live). Unchanged by N53.

## 4. WebSocket scheme derivation

Derived from the API base URL scheme — no separate env var. Verified intact in
both realtime entry points:

`frontend/lib/core/runtime/gtex_realtime_client.dart:242` and
`frontend/lib/features/match/live_match_session_service.dart:46`:

```dart
final String scheme = switch (base.scheme) {
  'https' => 'wss',
  'http'  => 'ws',
  'ws' || 'wss' => base.scheme,
  _ => 'wss',
};
```

So `https://api.gtex.com` → `wss://api.gtex.com/...`, `http://localhost:8000` →
`ws://localhost:8000/...`. Unchanged by N53.

## 5. N53 impact on deployment

N53 touched only:
- `frontend/lib/data/national_team_api.dart` (two endpoint string literals)
- `frontend/lib/screens/gtex_national_team_rental_screen_v2.dart` (two key lists)

No deployment scripts, build config, env handling, or WS derivation were modified.

## Verdict: CLOUDFLARE READY

- `frontend/pubspec.yaml` present ✅
- Build output `frontend/build/web` ✅
- `GTE_API_BASE_URL` dart-define required and wired ✅
- WS derivation `https→wss` / `http→ws` intact ✅
- Contract gate unblocked (0 violations) ✅
