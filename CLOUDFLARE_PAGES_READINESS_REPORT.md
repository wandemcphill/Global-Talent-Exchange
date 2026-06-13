# Task F — Cloudflare Pages Readiness Report

## Verdict: READY — Build script created; no localhost leaks in production paths

---

## Flutter Web Build

### Build output path
```
frontend/build/web/
```

### Build command
```sh
bash ops/cloudflare/build-frontend.sh
```

Or manually:
```sh
cd frontend
flutter build web --release \
  --dart-define="GTE_API_BASE_URL=https://gtex-api.onrender.com" \
  --dart-define="GTE_BACKEND_MODE=live"
```

### Cloudflare Pages settings

| Setting | Value |
|---|---|
| **Framework preset** | None |
| **Build command** | `bash ops/cloudflare/build-frontend.sh` |
| **Build output directory** | `frontend/build/web` |
| **Root directory** | `/` (repo root) |

### Environment variables (Cloudflare Pages → Settings → Environment variables)

| Variable | Value |
|---|---|
| `GTE_API_BASE_URL` | `https://gtex-api.onrender.com` (or your Render URL) |
| `GTE_BACKEND_MODE` | `live` |
| `FLUTTER_ROOT` | `/opt/buildhome/flutter` (or Cloudflare default) |

---

## API Base URL Strategy

`GteAppConfig.fromEnvironment()` reads `GTE_API_BASE_URL` via `String.fromEnvironment()` which is injected at **compile time** with `--dart-define`. The Cloudflare build script passes this from the shell env var set in the Pages dashboard.

This means:
- No hardcoded backend URL in the compiled output
- Changing the Render URL only requires updating the Pages env var + re-triggering a build

## WebSocket URL Strategy

The match broadcast WebSocket URL is derived from the API base URL at runtime:
```dart
// wss:// when https://, ws:// when http://
final wsUrl = apiBaseUrl.replaceFirst('https://', 'wss://').replaceFirst('http://', 'ws://');
```

No separate WebSocket env var is needed.

## Localhost Audit

`ENV_AUDIT.md` flagged **206 files** with `127.0.0.1` references. Audit result:

- All `localhost` references appear in **`factory .fixture()`** constructors
- These constructors are gated by `GteBackendMode.fixture`
- `GTE_BACKEND_MODE=live` in production never reaches these constructors
- The 3D service at `features/3d/` has a localhost guard — this is quarantined per canonical direction

**Conclusion:** No localhost assumption reaches a production build with `GTE_BACKEND_MODE=live`.

## CORS

The Render backend must allow the Cloudflare Pages domain:
```
GTE_CORS_ALLOW_ORIGINS=https://<your-pages-subdomain>.pages.dev
```

For custom domains, add the custom domain to `GTE_CORS_ALLOW_ORIGINS` (comma-separated).

## Custom Domain

Point your custom domain's CNAME to Cloudflare Pages. SSL is handled automatically by Cloudflare.
