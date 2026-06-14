# Phase D7 — Cloudflare Pages Certification

Date: 2026-06-14

## Build
`ops/cloudflare/build-frontend.sh`:
```bash
set -euo pipefail
: "${GTE_API_BASE_URL:?GTE_API_BASE_URL must be set in Cloudflare Pages environment variables.}"
GTE_BACKEND_MODE="${GTE_BACKEND_MODE:-live}"
flutter build web --release \
  --dart-define="GTE_API_BASE_URL=${GTE_API_BASE_URL}" \
  --dart-define="GTE_BACKEND_MODE=${GTE_BACKEND_MODE}"
```

| Setting | Value |
|---|---|
| Build command | `bash ops/cloudflare/build-frontend.sh` |
| Output directory | `frontend/build/web` |
| Env vars | `GTE_API_BASE_URL=https://api.gtex.com`, `GTE_BACKEND_MODE=live` |

## Checks
- No Vercel (`vercel.json`/`@vercel`), Netlify (`netlify.toml`/`_redirects`), or Render-static assumptions.
- Hard-fails if `GTE_API_BASE_URL` unset → cannot ship a localhost build.
- WebSocket URL derived from API base (`https→wss`, `http→ws`); no separate var, no localhost leakage in
  live builds (localhost literals are confined to `GteBackendMode.fixture`).

## Verdict: CLOUDFLARE PAGES READY
