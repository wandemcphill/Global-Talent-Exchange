# Phase 5K production recovery

## Current boundary

Player discovery is now independent of active share markets. Production recovery remains blocked by upstream data-population health, not by the transfer-market route.

The real-player Render cron currently retries SportMonks provider failures and can emit execution reports containing sensitive connection material. Production logs must never contain the database URL or provider credentials.

## Recovery order

1. Rotate any database/provider credentials that have appeared in logs or execution reports.
2. Keep the production database write block explicit. Do not bypass writes or fabricate freshness.
3. Recover a write-capable production database connection for ingestion and workers.
4. Remove duplicate runtime migration from the player-ingestion worker. Keep migration as an explicit deployment operation.
5. Run a controlled real-player ingestion pass with conservative provider pacing and verify successful writes.
6. Verify `/players`, clubs, leagues, countries and active player-share markets separately.
7. Verify representative real-player image URLs and Cloudinary delivery.
8. Run production trade/certification smoke checks only after the above evidence exists.

## Data honesty

Unknown, unavailable, rate-limited and empty are distinct states. A failed SportMonks call must never be represented as a successful zero-count dataset.
