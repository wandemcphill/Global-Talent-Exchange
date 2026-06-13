# Phase S11 — Dart-Define Certification

Date: 2026-06-14

## Compile-Time Injection

GTEX injects production configuration via `--dart-define` (compile-time constants), never via a runtime
env file:

```dart
// frontend/lib/app/gte_app_config.dart
const String rawBaseUrl = String.fromEnvironment('GTE_API_BASE_URL');
const String rawMode    = String.fromEnvironment('GTE_BACKEND_MODE');
```

`String.fromEnvironment` is resolved by the Dart compiler — the value is **baked into the artifact**, not
read at runtime.

## Production Build Command

```sh
flutter build web --release \
  --dart-define=GTE_API_BASE_URL=https://api.gtex.com \
  --dart-define=GTE_BACKEND_MODE=live
```

Wrapped by `ops/cloudflare/build-frontend.sh`, which sources the values from Cloudflare Pages env vars
and hard-fails if `GTE_API_BASE_URL` is unset:
```bash
: "${GTE_API_BASE_URL:?GTE_API_BASE_URL must be set in Cloudflare Pages environment variables.}"
```

## No Localhost in Production Artifacts

- With `GTE_BACKEND_MODE=live`, fixture-mode constructors (the only place `localhost`/`127.0.0.1`
  literals appear) are unreachable — `_parseBackendMode('live', allowFixtureMode: false)` →
  `GteBackendMode.live`, which never calls `.fixture()`.
- With a non-empty `GTE_API_BASE_URL`, `resolveGteApiBaseUrl` returns it directly; with an empty one in
  live mode it throws `StateError`. There is no code path that yields a localhost base URL in a live build.

## Verdict: DART-DEFINE INJECTION CERTIFIED

Production config is compile-time injected; artifacts built with `GTE_BACKEND_MODE=live` and a real
`GTE_API_BASE_URL` contain no localhost values.
