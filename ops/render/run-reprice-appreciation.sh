#!/usr/bin/env bash
# Render cron: appreciation scheduler. Recomputes every player's frozen price from
# its potential-driven effective GSI as it ages (young players appreciate toward
# potential; veterans hold their tier). Feed-free and idempotent. Weekly is fine —
# appreciation is gradual.
#
# Required env (dashboard, sync:false):
#   DATABASE_URL   Supabase Postgres URL (postgresql://...?sslmode=require)
set -u

cd "$(dirname "$0")/../../backend" || exit 1

if [ -z "${DATABASE_URL:-}" ]; then
  echo "FATAL: DATABASE_URL is not set" >&2
  exit 1
fi

echo "[$(date -u +%FT%TZ)] appreciation reprice starting"
PYTHONPATH=. python -u scripts/reprice_appreciation.py --database-url "$DATABASE_URL"
echo "[$(date -u +%FT%TZ)] appreciation reprice done (exit $?)"
