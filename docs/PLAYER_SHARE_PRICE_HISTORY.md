# Player share price history and regen discovery

This integration adds a server-backed Wonderkid market sort, nation filtering, and player-share price history to the existing GTEX player-share API.

## API

- `GET /api/v2/players/markets?sort=wonderkid`: returns regen players aged 21 or under with a recorded potential, ranked by potential and then headroom.
- `GET /api/v2/players/markets?source=regen&nation=Nigeria`: filters the share market by regen source and nation.
- `GET /api/v2/players/markets/nations?source=regen`: returns available nations with active market counts.
- `GET /api/v2/players/{player_id}/shares/price-history?range=7d|30d|all`: combines recorded share events, daily closing snapshots and the current price.
- `POST /api/v2/players/markets/price-snapshots/cron`: starts a daily price snapshot. Supply `Authorization: Bearer <WEBHOOK_CRON_SECRET>`.

## Snapshot scheduling

Configure `WEBHOOK_CRON_SECRET` in the backend environment before enabling the cron endpoint. Requests fail closed when the secret is missing or invalid. Configure the deployment scheduler to invoke the endpoint daily at 00:05 UTC; do not commit the secret to source control. Historical chart granularity depends on the share events and snapshots that have actually been recorded. No market repricing or live-database repair is run automatically by this code change.

## Migration note

The price-history migrations continue directly from the current GTEX migration head. They do not depend on Emergent's separate Owner Console migrations.
