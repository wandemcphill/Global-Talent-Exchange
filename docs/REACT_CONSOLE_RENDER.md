# React shell on the Render static site

The production web service is still `gtex-web` (`https://gtex-web-tw6c.onrender.com`). One static publish contains both frontends:

| URL | App |
| --- | --- |
| `/` and existing Flutter files | Flutter web (`frontend/build/web`) |
| `/console/` and `/console/*` | Emergent React shell |

Both apps call the existing API at `https://gtex-api-opea.onrender.com`. This deploy does not add a backend, database, or auth bypass.

The Cloudflare Pages script (`ops/cloudflare/build-frontend.sh`) is unchanged and still publishes Flutter only.

## How the build is laid out

`ops/render/build-frontend.sh` builds Flutter first, then runs `ops/render/publish-react-shell.sh`.

1. Flutter `build/web` stays the site root. `index.html` there is still the Flutter host (`flutter_bootstrap.js`).
2. The React production bundle is copied to `frontend/build/web/console/`.
3. The script exits non-zero if Flutter output is missing, the site-root document is not Flutter, the React build fails, or the React bundle is not prefixed with `/console/`. `set -euo pipefail` fails the Render deploy before a partial tree is published. A failed build leaves the previous `gtex-web` deploy in place.

The React build sets:

- `PUBLIC_URL=/console` so JS, CSS, and `public/` assets resolve under `/console/`.
- `REACT_APP_BACKEND_URL` from `GTE_API_BASE_URL`. The shell appends `/api` itself. The value must be the API origin with no `/api` suffix.
- `CI=false`. Render exports `CI=true`, and Create React App turns that into warnings-as-errors. The React shell's GitHub workflow already builds with `CI=false`.
- `NODE_OPTIONS=--openssl-legacy-provider` when the build image has not set it.

`gtex-web` sets `NODE_VERSION=20` so the static-site image matches `.github/workflows/react-shell-build.yml`.

## Routing

`render.yaml` adds rewrite rules on `gtex-web` only:

| Source | Destination |
| --- | --- |
| `/console` | `/console/index.html` |
| `/console/` | `/console/index.html` |
| `/console/*` | `/console/index.html` |

Render serves a real file before applying a rewrite. `/console/static/*` and `/console/img/*` are files, so they are not rewritten. There is no `/*` rewrite. Flutter paths such as `/` and `/main.dart.js` are unchanged, and `/api` is not on this static site.

React Router's basename comes from `PUBLIC_URL` (`frontend/react-shell/src/lib/publicPath.ts`). Direct loads and browser refreshes of nested routes such as `/console/app/market` and `/console/login` receive the React `index.html` and the client router renders the screen.

## Environment variables

`gtex-web` (build time):

| Variable | Value | Used by |
| --- | --- | --- |
| `GTE_API_BASE_URL` | `https://gtex-api-opea.onrender.com` | Flutter `--dart-define` and the React shell's `REACT_APP_BACKEND_URL` |
| `GTE_BACKEND_MODE` | `live` | Flutter |
| `GTEX_SHELL_V3` | `true` by default; set `false` only for rollback | Flutter P9-SHELL activation |
| `NODE_VERSION` | `20` | React toolchain on the static-site build image |

No React secrets are added. Do not set `GTEX_WEB_PUBLISH_DIR` on Render; the publish script rejects that override when `RENDER=true`.

Local React development uses `frontend/react-shell/.env.local` (copied from `.env.example`). `PUBLIC_URL` stays empty, so `npm start` is served at `/`.

## CORS and authentication

The React shell is served from the same origin as Flutter: `https://gtex-web-tw6c.onrender.com`. CORS is origin-based, so `GTE_CORS_ALLOW_ORIGINS` on `gtex-api` already covers `/console/`. No backend CORS change is required.

The shell sends `Authorization: Bearer` to the canonical API. It does not add a cookie session, a second auth secret, or a mock API fallback. If `REACT_APP_BACKEND_URL` is missing at build time, the client throws instead of calling the static host.

Owner-console routes are mounted at `/api/owner` (`api_only` in `backend/app/modules.py`). Auth refresh and login use `/api/v2/auth`, which matches `backend/app/auth/router.py`. The client base URL is `${REACT_APP_BACKEND_URL}/api`.

## Build locally

React shell only (no Flutter SDK):

```bash
cd frontend/react-shell
npm ci --legacy-peer-deps --include=dev
PUBLIC_URL=/console \
REACT_APP_BACKEND_URL=https://gtex-api-opea.onrender.com \
CI=false \
NODE_OPTIONS=--openssl-legacy-provider \
npm run build
GTE_API_BASE_URL=https://gtex-api-opea.onrender.com \
  bash ../../ops/render/verify-console-bundle.sh build
```

`npm start` remains the local dev server at `/`. Copy `.env.example` to `.env.local` first and point `REACT_APP_BACKEND_URL` at the API you mean to call.

Both apps, the same command Render runs (requires git, a Flutter checkout, and Node 20):

```bash
export GTE_API_BASE_URL=https://gtex-api-opea.onrender.com
export GTE_BACKEND_MODE=live
bash ops/render/build-frontend.sh
```

Output:

- `frontend/build/web/index.html` — Flutter
- `frontend/build/web/console/index.html` — React, with asset URLs under `/console/static/`

Contract tests, without installing either toolchain:

```bash
python -m pytest backend/tests/security/test_react_console_static_publish.py backend/tests/security/test_deployment_contract.py
```

## Rollback

1. If the `gtex-web` build fails, Render keeps the last successful deploy. Flutter at `/` stays as it was.
2. To remove a bad successful deploy, roll `gtex-web` back in the Render dashboard to the previous successful static deploy. That restores the previous file tree. Do not roll back `gtex-api`; this change does not migrate or reconfigure the API.
3. Rewrite rules are Blueprint settings. After a rollback of files, confirm Redirects/Rewrites still match the deploy you intend. Removing `/console`, `/console/`, and `/console/*` is only required if those rules themselves are mis-routing. They do not replace Flutter files, because a real file is served before a rewrite.
4. To drop the shell from new builds, revert this change and redeploy `gtex-web`. The Cloudflare Flutter build does not need a matching revert.

## What to verify on Render after the Blueprint sync

This repository cannot apply the live service settings from here.

- Blueprint sync on `gtex-web` shows the three `/console` rewrites, and they sit above any pre-existing `/*` rewrite. A dashboard `/*` → `/index.html` rule that is evaluated first would send `/console/app/...` to the Flutter document. Render keeps redirect rules that are not listed in `render.yaml`.
- `https://gtex-web-tw6c.onrender.com/` still loads Flutter.
- `https://gtex-web-tw6c.onrender.com/console/` loads the React shell, and the document requests `/console/static/...` (not `/static/...`).
- Refresh `https://gtex-web-tw6c.onrender.com/console/login` and it still loads the React shell.
- A React API call goes to `https://gtex-api-opea.onrender.com` and not to the static host.
