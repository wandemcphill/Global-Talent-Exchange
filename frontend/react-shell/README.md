# GTEX React shell

This is a standalone React UI target imported from the Emergent design branch and isolated from the existing Flutter app. It uses the canonical API in `../../backend`; it does not include a duplicate backend or a nested copy of GTEX.

## Local development

1. Copy `.env.example` to `.env.local` and verify `REACT_APP_BACKEND_URL` points to the environment you intend to use. The value is the API origin without a trailing slash or `/api`.
2. Install dependencies with `npm ci --legacy-peer-deps --include=dev` (or `npm install --legacy-peer-deps` when you are refreshing the lockfile).
3. Start with `npm start`. The dev server stays at `/`. `PUBLIC_URL` is empty locally.
4. Create a production bundle for the Render `/console/` path with `PUBLIC_URL=/console` and `REACT_APP_BACKEND_URL` set. See `docs/REACT_CONSOLE_RENDER.md`.

`REACT_APP_BACKEND_URL` is required. The client does not fall back to the page origin, because the static site does not host the API. Local and preview origins must be allowed by the backend CORS configuration.

## Deployment

The Render static site publishes Flutter at `/` and this shell at `/console/`. `ops/render/build-frontend.sh` builds Flutter, then `ops/render/publish-react-shell.sh` builds this package with `PUBLIC_URL=/console` and copies `build/` to `frontend/build/web/console/`.

Router basename, public images, and the Paystack return path share `src/lib/publicPath.ts`. Nested routes such as `/console/login` depend on the `/console` and `/console/*` rewrites in `render.yaml`.

The shell calls `GTE_API_BASE_URL` (production: `https://gtex-api-opea.onrender.com`). It is served from the same web origin as Flutter, so the existing API CORS allow-list already covers it.

Emergent-specific overlays, injected runtime scripts, remote analytics snippets, its hosted-backend test file, duplicate backend wrapper, and nested duplicate `gtex/` repository have been excluded.
