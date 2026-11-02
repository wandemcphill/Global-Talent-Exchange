# React web on Cloudflare Pages (playgtex.app)

Independent of the Flutter site on Render (`gtex-web`, `https://gtex-web-np2t.onrender.com`), which is unchanged.

## Verified facts
- React app: `frontend/react-shell` (CRA + CRACO). Built at the domain root when `PUBLIC_URL` is empty (`ROUTER_BASENAME` = `/`).
- Public routes: `/`, `/login`, `/signup`, `/onboarding`, `/payment/callback`, `/club/:slug`.
- The authenticated "console" is the `/app/*` tree (market, match/:id, finance, admin, creator-access, coin-traders, ...). `/console` was only the Render sub-path prefix; on this domain `public/_redirects` 301s `/console/*` to `/app/*`.
- Canonical API: `https://gtex-api-2gtu.onrender.com` (agrees across `render.yaml`, `.env.example`, workflows).

## Cloudflare Pages project `gtex-react-web`
| Setting | Value |
|---|---|
| Repo / production branch | `wandemcphill/Global-Talent-Exchange` / `main` |
| Root directory | `frontend/react-shell` |
| Node | `NODE_VERSION=20` |
| Install | `npm ci --legacy-peer-deps --include=dev` |
| Build | `npm run build` |
| Output | `build` |
| Env | `PUBLIC_URL=` (empty), `REACT_APP_BACKEND_URL=https://gtex-api-2gtu.onrender.com`, `NODE_OPTIONS=--openssl-legacy-provider`, `CI=false`, optional `REACT_APP_GTE_TURNSTILE_SITE_KEY` |

SPA fallback: `public/_redirects` (`/* /index.html 200`).
Custom domains: `playgtex.app` (primary); `www.playgtex.app` redirect to apex.

## Backend CORS
`render.yaml` `GTE_CORS_ALLOW_ORIGINS` now includes `https://playgtex.app` and `https://www.playgtex.app` alongside the Render origin. Redeploy `gtex-api` (Blueprint sync) to apply.
Payment webhooks and secrets are untouched. Paystack callback URL (`GTE_PAYSTACK_CALLBACK_URL`) should be set to `https://playgtex.app/payment/callback` only when this domain becomes the payment return target.

## CI
`.github/workflows/react-cloudflare-pages.yml` runs tests, a root build and `ops/cloudflare/verify-react-root-build.sh`.
