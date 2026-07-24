#!/usr/bin/env bash
# Render cron-job entrypoint: one-time SoFIFA / EA FC frozen player import.
# Runs in-region (fast, low-latency to the Supabase pooler) unlike a laptop.
# The importer is resume-safe: it skips already-imported players (upsert by
# source_player_key), so a retry after a dropped connection continues where it
# left off instead of redoing work.
#
# Required env (set in the Render dashboard, sync:false):
#   DATABASE_URL   Supabase Postgres URL (postgresql://...?sslmode=require)
#   CSV_URL        Public/temporary URL to the SoFIFA players CSV
#
# Optional:
#   IMAGES         none | url | cloudinary   (default: url)
#   MAX_ATTEMPTS   retry budget (default 50)
# When IMAGES=cloudinary, also set CLOUDINARY_CLOUD_NAME / CLOUDINARY_API_KEY /
# CLOUDINARY_API_SECRET.
set -u

cd "$(dirname "$0")/../../backend" || exit 1

if [ -z "${DATABASE_URL:-}" ]; then
  echo "FATAL: DATABASE_URL is not set" >&2
  exit 1
fi
if [ -z "${CSV_URL:-}" ]; then
  echo "FATAL: CSV_URL is not set" >&2
  exit 1
fi

IMAGES="${IMAGES:-url}"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-50}"
BACKOFF_START="${BACKOFF_START:-30}"
BACKOFF_MAX="${BACKOFF_MAX:-120}"
REPORT_PATH="tmp/render-sofifa-import-report.json"

echo "[$(date -u +%FT%TZ)] render SoFIFA import starting; images=$IMAGES"

attempt=0
backoff="$BACKOFF_START"
while [ "$attempt" -lt "$MAX_ATTEMPTS" ]; do
  attempt=$((attempt + 1))
  echo "[$(date -u +%FT%TZ)] attempt $attempt"

  python -u -m scripts.import_sofifa_players \
    --csv-url "$CSV_URL" \
    --database-url "$DATABASE_URL" \
    --images "$IMAGES" \
    --report-path "$REPORT_PATH"
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
