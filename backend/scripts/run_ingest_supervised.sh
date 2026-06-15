#!/usr/bin/env bash
# Supervised real-player ingest: auto-restarts on non-zero exit so the run
# survives intermittent idle-in-tx / connection-reap deaths unattended.
#
# Usage:  bash scripts/run_ingest_supervised.sh
# Resumes from state.json each attempt (skips already-completed clubs).
# Stops cleanly on exit 0 (run completed) or after MAX_ATTEMPTS.
#
# Requires backend/.env with GTE_DATABASE_URL + SPORTMONKS_API_TOKEN.
set -u

cd "$(dirname "$0")/.." || exit 1
set -a; . ./.env; set +a

STATE_PATH="tmp/seven-league-refresh/state.json"
REPORT_PATH="tmp/seven-league-report.json"
LOG="tmp/ingest-supervised.log"
PAUSE_MS="${PAUSE_MS:-750}"          # ease connection pressure between club writes
MAX_ATTEMPTS="${MAX_ATTEMPTS:-200}"
BACKOFF_START="${BACKOFF_START:-15}" # seconds; grows then caps
BACKOFF_MAX="${BACKOFF_MAX:-120}"

# Leagues covered by the active SportMonks plan. Süper Lig (Turkey) is omitted
# until coverage returns; re-add  --league "Super Lig"  once confirmed.
LEAGUES=(
  --league "Premier League"
  --league "La Liga"
  --league "Serie A"
  --league "Ligue 1"
  --league "Bundesliga"
  --league "Eredivisie"
)

attempt=0
backoff="$BACKOFF_START"
echo "[$(date -u +%FT%TZ)] supervised ingest starting (pause_ms=$PAUSE_MS)" | tee -a "$LOG"

while [ "$attempt" -lt "$MAX_ATTEMPTS" ]; do
  attempt=$((attempt + 1))
  echo "[$(date -u +%FT%TZ)] attempt $attempt" | tee -a "$LOG"

  python -u scripts/refresh_target_league_real_players.py \
    --database-url "$GTE_DATABASE_URL" \
    --state-path "$STATE_PATH" \
    --report-path "$REPORT_PATH" \
    --pause-ms "$PAUSE_MS" \
    "${LEAGUES[@]}" >> "$LOG" 2>&1
  code=$?

  if [ "$code" -eq 0 ]; then
    echo "[$(date -u +%FT%TZ)] run completed cleanly (exit 0) after $attempt attempt(s)" | tee -a "$LOG"
    exit 0
  fi

  echo "[$(date -u +%FT%TZ)] exited code=$code; retrying in ${backoff}s" | tee -a "$LOG"
  sleep "$backoff"
  backoff=$(( backoff * 2 )); [ "$backoff" -gt "$BACKOFF_MAX" ] && backoff="$BACKOFF_MAX"
done

echo "[$(date -u +%FT%TZ)] gave up after $MAX_ATTEMPTS attempts" | tee -a "$LOG"
exit 1
