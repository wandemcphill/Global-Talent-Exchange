#!/usr/bin/env bash
# Populate the regen world: canonical countries, the national regen pool for
# every enabled country, and an active regen season.
#
# Triggered manually from Render (cron job "gtex-regen-world-bootstrap" ->
# Trigger Run) so it uses the service's own DATABASE_URL.
#
# Fixes the live symptoms where the Regen World screen shows a handful of
# Nigeria-only u21 regens and every metagame surface (rankings, hall of fame,
# awards, bloodlines) is empty.
#
# Both steps are idempotent and safe to re-run:
#   - seed-national-regen-pool upserts canonical countries, then tops each
#     enabled country up to SEEDS_PER_COUNTRY active slots
#   - open_regen_season exits without changes when a season is already active
set -euo pipefail

cd "$(dirname "$0")/../.." || exit 1

if [ -z "${DATABASE_URL:-}" ]; then
  echo "FATAL: DATABASE_URL is not set" >&2
  exit 1
fi

SEEDS_PER_COUNTRY="${SEEDS_PER_COUNTRY:-70}"
PRESEED_BATCH="${PRESEED_BATCH:-global_u21_batch}"

echo "== Seeding canonical countries + national regen pool (${SEEDS_PER_COUNTRY}/country) =="
# No --country-code: seeds every country flagged is_enabled_for_universe.
# --canonical-countries (default) upserts the 50 canonical country records
# first, which is what enables countries beyond the ones already present.
python backend/scripts/dev.py seed-national-regen-pool \
  --database-url "${DATABASE_URL}" \
  --seeds-per-country "${SEEDS_PER_COUNTRY}" \
  --preseed-batch "${PRESEED_BATCH}" \
  --canonical-countries

echo "== Repairing regen names + portraits for the seeded batch =="
python backend/scripts/dev.py repair-national-regen-names \
  --database-url "${DATABASE_URL}" \
  --preseed-batch "${PRESEED_BATCH}" \
  --refresh-portraits

echo "== Opening regen season (no-op if one is already active) =="
python backend/scripts/open_regen_season.py --database-url "${DATABASE_URL}"

echo "== Regen world bootstrap complete =="
