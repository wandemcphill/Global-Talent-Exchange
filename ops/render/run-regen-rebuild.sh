#!/usr/bin/env bash
# Rebuild the regen cohort and (re)generate their portraits.
# Triggered manually from Render (cron job "gtex-regen-rebuild" -> Trigger Run).
set -euo pipefail

cd "$(dirname "$0")/../../backend" || exit 1

if [ -z "${DATABASE_URL:-}" ]; then
  echo "FATAL: DATABASE_URL is not set" >&2
  exit 1
fi

_clean_db_url="${DATABASE_URL}"
if [[ "${_clean_db_url}" == export\ * ]]; then
  _clean_db_url="${_clean_db_url#export }"
fi
if [[ "${_clean_db_url}" == DATABASE_URL=* ]]; then
  _clean_db_url="${_clean_db_url#DATABASE_URL=}"
fi
if [[ "${_clean_db_url}" == GTE_DATABASE_URL=* ]]; then
  _clean_db_url="${_clean_db_url#GTE_DATABASE_URL=}"
fi
while [[ "${_clean_db_url}" == \"*\" || "${_clean_db_url}" == \'*\' ]]; do
  _clean_db_url="${_clean_db_url:1:-1}"
done
_clean_db_url="$(echo "${_clean_db_url}" | sed -e 's/^[[:space:]"\'\'\ ]*//' -e 's/[[:space:]"\'\'\ ]*$//')"
DATABASE_URL="${_clean_db_url}"

TARGET="${REGEN_TARGET:-12000}"

echo "== Rebuilding regens (target=${TARGET}) =="
python scripts/seed_coherent_regens.py --database-url "${DATABASE_URL}" --target "${TARGET}"

echo "== Repairing / generating regen portraits =="
python scripts/audit_repair_regen_portrait_lane.py --database-url "${DATABASE_URL}" --apply

echo "== Regen rebuild complete =="
