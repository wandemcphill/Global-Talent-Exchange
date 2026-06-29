#!/usr/bin/env bash
# Rebuild the regen cohort and (re)generate their portraits.
# Triggered manually from Render (cron job "gtex-regen-rebuild" -> Trigger Run).
set -euo pipefail

cd "$(dirname "$0")/../../backend" || exit 1

if [ -z "${DATABASE_URL:-}" ]; then
  echo "FATAL: DATABASE_URL is not set" >&2
  exit 1
fi

TARGET="${REGEN_TARGET:-12000}"

echo "== Rebuilding regens (target=${TARGET}) =="
python scripts/seed_coherent_regens.py --database-url "${DATABASE_URL}" --target "${TARGET}"

echo "== Repairing / generating regen portraits =="
python scripts/audit_repair_regen_portrait_lane.py --database-url "${DATABASE_URL}" --apply

echo "== Regen rebuild complete =="
