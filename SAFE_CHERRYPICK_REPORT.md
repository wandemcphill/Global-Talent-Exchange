# Phase D2/D3 — Safe Infrastructure Port Report

Date: 2026-06-14

The feature branch's infra work spans many commits entangled with feature changes, so rather than
cherry-pick commits wholesale, each infrastructure change was **re-created surgically** on main. Below is
what was ported and what was deliberately excluded.

## Ported (infrastructure only)

| Change | Files | Safe? | Reason |
|---|---|---|---|
| Supabase DB + Render Redis blueprint | `render.yaml` | ✅ | Env-only; preserves main's Korapay/Treasury vars |
| Redis enable/disable toggle | `backend/app/core/config.py`, `cache.py` | ✅ | Additive `redis_enabled` field + 2-line cache short-circuit |
| Cloudinary resolver module | `services/player-ingestion/src/imageResolver.js` (new) | ✅ | Pure derivation, no uploads |
| Python image resolver | `backend/app/core/player_image.py` (new) | ✅ | Additive, derivation-only |
| Upload→derive swap | `jobs.js`, `importNamedPlayers.js`, `importYouthPlayers.js`, `importTopEuropeanLeagues.js`, `importLaunchLeagueBatch.js`, `backfillMarketplaceImages.js`, `config.js`, `queues.js` | ✅ | Media pipeline only — not auth/trader/wallets/treasury/frontend |
| Cloudflare build script | `ops/cloudflare/build-frontend.sh` (new) | ✅ | Build tooling |
| Env template | `.env.production.example` (new) | ✅ | Placeholders only |
| Boot unblock (import cycle) | `backend/app/admin/capabilities.py` | ✅ | Made 2 imports function-local; zero behavior change (see DEPLOYMENT_READY_REPORT) |

## Explicitly NOT ported (feature/business changes)

| Excluded | Reason |
|---|---|
| `jobIds`/`safeJobId` refactor in `jobs.js` | Behavioral; kept main's version |
| Import-script restructuring | Beyond cloudinary scope; only swapped upload calls |
| `health.py` Redis message change | Would break main's tests; main's config change already yields `skipped` |
| `config.py` feature deltas (crypto/startup/withdrawal) | Main is ahead here; not touched |
| All auth / trader / wallets / treasury / admin / frontend / competitions code | Out of scope by rule |

## Method note

For each mixed file, only the Cloudinary-resolver lines were recreated (`require("./imageResolver")` +
`resolvePlayerImage(...)`), leaving main's structure, `safeJobId`, and `isReusableImageUrl` intact.
All 9 edited JS files pass `node --check`.
