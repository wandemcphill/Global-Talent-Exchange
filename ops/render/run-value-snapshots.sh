#!/usr/bin/env bash
# Render cron: scheduled valuation rebuild.
#
# This is what makes the matchday economy live. Player performances are persisted
# at competition-match settlement and form is derived from them, but the published
# valuation only changes when the value snapshot job runs. Without this cron the
# chain match -> performance -> form -> valuation -> market -> ownership is inert
# between manual operator rebuilds.
#
# Runs the SAME IngestionValueEngineBridge.run() the API's
# POST /api/value/snapshots/rebuild uses - not a second pipeline. The bridge wires
# MatchdayValuationSignalProvider itself, so scheduled and manual runs compute
# identical numbers by construction.
#
# Idempotent: snapshots are upserted on (player_id, as_of, snapshot_type).
#
# Required env (dashboard, sync:false):
#   DATABASE_URL   Supabase Postgres URL (postgresql://...?sslmode=require)
set -u

cd "$(dirname "$0")/../../backend" || exit 1

if [ -z "${DATABASE_URL:-}" ]; then
  echo "FATAL: DATABASE_URL is not set" >&2
  exit 1
fi

echo "[$(date -u +%FT%TZ)] value snapshot rebuild starting"
PYTHONPATH=. python -u scripts/rebuild_value_snapshots.py --database-url "$DATABASE_URL"
echo "[$(date -u +%FT%TZ)] value snapshot rebuild done (exit $?)"
