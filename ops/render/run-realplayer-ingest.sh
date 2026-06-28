#!/usr/bin/env bash
# Render cron-job entrypoint: ingest real players for the leagues that still
# need them. Runs on a stable network (unlike a laptop session) and retries
# transient pooler/connection deaths in-process. Writes are DB-idempotent
# (upsert by source_player_key), so re-runs are safe even though Render's
# filesystem (and thus state.json) does not persist across cron invocations.
#
# Required env (set in the Render dashboard, sync:false):
#   DATABASE_URL          Supabase Postgres URL (postgresql://...?sslmode=require)
#   SPORTMONKS_API_TOKEN  SportMonks v3 token
#
# Optional:
#   INGEST_LEAGUES   newline/`;`-separated league names to override the default set
#   PAUSE_MS         pause between club writes (default 1500)
#   MAX_ATTEMPTS     retry budget (default 50)
set -u

cd "$(dirname "$0")/../../backend" || exit 1

if [ -z "${DATABASE_URL:-}" ]; then
  echo "FATAL: DATABASE_URL is not set" >&2
  exit 1
fi

PAUSE_MS="${PAUSE_MS:-1500}"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-50}"
BACKOFF_START="${BACKOFF_START:-30}"
BACKOFF_MAX="${BACKOFF_MAX:-120}"
STATE_PATH="tmp/render-realplayer-ingest/state.json"
REPORT_PATH="tmp/render-realplayer-ingest-report.json"

# Leagues that still need real players (the original 6 are already populated).
# Override via INGEST_LEAGUES if needed.
DEFAULT_LEAGUES=$'Championship\nSuper Lig\nLa Liga 2\nChance Liga\nBrasileiro Serie A\nLiga Profesional de Futbol\nAdmiral Bundesliga'
LEAGUE_SOURCE="${INGEST_LEAGUES:-$DEFAULT_LEAGUES}"

LEAGUE_ARGS=()
while IFS= read -r line; do
  # allow ';' as an alternate separator
  line="${line//;/$'\n'}"
  while IFS= read -r name; do
    name="$(printf '%s' "$name" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
    [ -n "$name" ] && LEAGUE_ARGS+=(--league "$name")
  done <<< "$line"
done <<< "$LEAGUE_SOURCE"

echo "[$(date -u +%FT%TZ)] render real-player ingest starting; leagues: ${LEAGUE_ARGS[*]}"

attempt=0
backoff="$BACKOFF_START"
while [ "$attempt" -lt "$MAX_ATTEMPTS" ]; do
  attempt=$((attempt + 1))
  echo "[$(date -u +%FT%TZ)] attempt $attempt"

  python -u scripts/refresh_target_league_real_players.py \
    --database-url "$DATABASE_URL" \
    --state-path "$STATE_PATH" \
    --report-path "$REPORT_PATH" \
    --pause-ms "$PAUSE_MS" \
    "${LEAGUE_ARGS[@]}"
  code=$?

  if [ "$code" -eq 0 ]; then
    echo "[$(date -u +%FT%TZ)] completed cleanly (exit 0) after $attempt attempt(s)"
    exit 0
  fi

  echo "[$(date -u +%FT%TZ)] exited code=$code; retrying in ${backoff}s"
  sleep "$backoff"
  backoff=$(( backoff * 2 )); [ "$backoff" -gt "$BACKOFF_MAX" ] && backoff="$BACKOFF_MAX"
done

echo "[$(date -u +%FT%TZ)] gave up after $MAX_ATTEMPTS attempts"
exit 1
