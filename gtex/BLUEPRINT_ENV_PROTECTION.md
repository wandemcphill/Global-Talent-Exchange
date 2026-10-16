# Blueprint Environment Variable Protection — render.yaml

Date: 2026-08-25
Branch: main

## Goal

Keep operator-managed secrets and external connection strings out of source
control while allowing Blueprint to own infrastructure-managed configuration.

## Protected dashboard-managed values

| Key | Category | Blueprint ownership |
|---|---|---|
| DATABASE_URL | Supabase connection | `sync: false` |
| GTE_AUTH_SECRET | JWT secret | `sync: false` on every consumer |
| GTE_MEDIA_SIGNING_SECRET | Signing secret | `sync: false` on every consumer |
| GTE_PAYSTACK_SECRET_KEY | Paystack credential | `sync: false` |
| GTE_PAYSTACK_WEBHOOK_SECRET | Paystack webhook secret | `sync: false` |
| GTE_PAYSTACK_CALLBACK_URL | Frontend callback URL | `sync: false` |
| GTE_KORAPAY_* | Payment credentials | `sync: false` |
| TREASURY_* | Treasury configuration | `sync: false` |
| CLOUDINARY_* | Media credentials | `sync: false` |
| SPORTMONKS_API_TOKEN | Ingestion credential | `sync: false` |
| ELEVENLABS_API_KEY | Media credential | `sync: false` |
| SENTRY_DSN | Observability credential | `sync: false` |

## Blueprint-managed infrastructure values

`gtex-cache` is now a Blueprint-managed Render Key Value resource. Redis
consumers receive `GTE_REDIS_URL` through `fromService`, because the connection
string belongs to infrastructure provisioned by the Blueprint rather than an
operator-supplied secret.

The shared Redis consumers are:

- gtex-api
- gtex-rq-worker
- gtex-simulation-worker
- gtex-outbox-relay
- gtex-player-ingestion-worker

## Environment groups

The repository does **not** use Render `envVarGroups` / `fromGroup` today.
Environment values are declared directly per service. Existing dashboard values
not represented in the Blueprint should be reviewed separately before any future
cleanup or migration into environment groups.

## Operator rule

Never commit real credentials into `render.yaml`, `.env.production.example`, or
any other repository file. `sync: false` entries are populated from the Render
Dashboard.

## Verification target

- No production payment secret is hardcoded.
- Supabase remains the database owner.
- Render Key Value owns the production Redis connection.
- Paystack can only become ready when its runtime flag and credentials are
  present.
