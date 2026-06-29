#!/usr/bin/env bash
# One-off: backfill first_team squad-tier memberships for every contracted player.
# Run AFTER gtex-api has deployed (migration 0104 must have created the table).
# Triggered manually from Render (cron job "gtex-squad-tier-backfill" -> Trigger Run).
set -euo pipefail

cd "$(dirname "$0")/../../backend" || exit 1

if [ -z "${DATABASE_URL:-}" ]; then
  echo "FATAL: DATABASE_URL is not set" >&2
  exit 1
fi

echo "== Backfilling first_team squad-tier memberships =="
python scripts/backfill_squad_tiers.py --database-url "${DATABASE_URL}"

echo "== Squad-tier backfill complete =="
