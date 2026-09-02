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
#   INGEST_LEAGUES             newline/`;`-separated league names to override the default set
#   PAUSE_MS                   pause between club writes (default 1500)
#   MAX_ATTEMPTS               retry budget (default 50)
#   MARKET_ISSUANCE_ACTOR_ID   admin user id credited for the post-ingest share-market
#                              backfill (default: known GTEX super-admin)
#   SKIP_MARKET_BACKFILL       set to any non-empty value to skip the backfill step
#
# After a clean ingest this also issues player-share markets for any real,
# league-assigned players that still lack one (ingestion prices players but never
# issues markets). The backfill is idempotent; a failure there is logged and
# surfaced via a distinct exit code but does NOT re-run the ingest.
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
MARKET_ISSUANCE_ACTOR_ID="${MARKET_ISSUANCE_ACTOR_ID:-09ed5191-7b2d-4eff-a656-f26b58408758}"

# Issue share markets for real, league-assigned players that still lack one.
# Called after a clean ingest. Idempotent; never re-runs the ingest.
run_market_backfill() {
  if [ -n "${SKIP_MARKET_BACKFILL:-}" ]; then
    echo "[$(date -u +%FT%TZ)] market backfill skipped (SKIP_MARKET_BACKFILL set)"
    return 0
  fi
  echo "[$(date -u +%FT%TZ)] issuing share markets for newly-ingested real players"
  python -u scripts/backfill_real_league_share_markets.py \
    --database-url "$DATABASE_URL" \
    --actor-user-id "$MARKET_ISSUANCE_ACTOR_ID" \
    --activate \
    --batch-size 200
}

# Leagues to keep in sync. Idempotent upserts make it safe to re-list
# already-populated leagues alongside new ones. Override via INGEST_LEAGUES if needed.
DEFAULT_LEAGUES=$'Championship\nSuper Lig\nLa Liga 2\nChance Liga\nBrasileiro Serie A\nLiga Profesional de Futbol\nAdmiral Bundesliga\nPro League\nPremiership\nLiga Portugal\nNPFL\nSouth Africa Premier League\nEgypt Premier League\nIvory Coast Ligue 1\nGhana Premier League\nBotola Pro\nSenegal Ligue 1\nLiga BetPlay\nLiga Pro\nPrimera Division Uruguay\nMajor League Soccer\nSaudi Pro League\nBrasileiro Serie B\nSerie B\nLigue 2'
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
    echo "[$(date -u +%FT%TZ)] ingest completed cleanly (exit 0) after $attempt attempt(s)"
    if run_market_backfill; then
      echo "[$(date -u +%FT%TZ)] done (ingest + market backfill clean)"
      exit 0
    fi
    echo "[$(date -u +%FT%TZ)] WARNING: market backfill failed; ingest is committed, re-run to retry issuance" >&2
    exit 3
  fi

  echo "[$(date -u +%FT%TZ)] exited code=$code; retrying in ${backoff}s"
  sleep "$backoff"
  backoff=$(( backoff * 2 )); [ "$backoff" -gt "$BACKOFF_MAX" ] && backoff="$BACKOFF_MAX"
done

echo "[$(date -u +%FT%TZ)] gave up after $MAX_ATTEMPTS attempts"
exit 1
