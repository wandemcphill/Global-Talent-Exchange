# Phase S9 — Cloudflare Pages Build Certification

Date: 2026-06-14

## Build Command

`ops/cloudflare/build-frontend.sh` (canonical GTEX Cloudflare build):

```bash
set -euo pipefail
: "${GTE_API_BASE_URL:?GTE_API_BASE_URL must be set in Cloudflare Pages environment variables.}"
GTE_BACKEND_MODE="${GTE_BACKEND_MODE:-live}"
# ... pin Flutter revision, precache web ...
flutter build web --release \
  --dart-define="GTE_API_BASE_URL=${GTE_API_BASE_URL}" \
  --dart-define="GTE_BACKEND_MODE=${GTE_BACKEND_MODE}"
```

## Output Directory

`flutter build web` emits to **`frontend/build/web`**.

Cloudflare Pages configuration:

| Setting | Value |
|---|---|
| Build command | `bash ops/cloudflare/build-frontend.sh` |
| Build output directory | `frontend/build/web` |
| Environment variables | `GTE_API_BASE_URL=https://api.gtex.com`, `GTE_BACKEND_MODE=live` |

## Platform-Assumption Scan

| Assumption | Present? |
|---|---|
| Vercel (`vercel.json`, `VERCEL_*`, `@vercel/*`) | ❌ none |
| Netlify (`netlify.toml`, `_redirects`, `NETLIFY_*`) | ❌ none |
| Render static specifics baked into build | ❌ none — build is platform-neutral Flutter web |

The build script bridges Cloudflare Pages dashboard env vars → `--dart-define` flags (Cloudflare injects
them as shell env, not as dart-defines automatically). It hard-fails if `GTE_API_BASE_URL` is unset, so a
misconfigured Pages project cannot silently ship a localhost build.

## SPA Routing Note

Flutter web is a single-page app. Cloudflare Pages serves `index.html` for unknown routes by default
(SPA fallback), which matches Flutter's client-side router. No extra config required.

## Verdict: CLOUDFLARE PAGES READY

Build command + `frontend/build/web` output confirmed. No Vercel/Netlify/Render static assumptions.
Env-var → dart-define bridge with hard-fail guard.
