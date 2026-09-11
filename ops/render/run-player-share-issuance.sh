#!/usr/bin/env bash
# Automatically issue player-share markets for every eligible tradable player
# missing one. Runs co-located with the database so per-issuance latency does
# not make a laptop/manual operator run the normal path.
#
# The job is intentionally decoupled from ingestion. A player can be ingested
# successfully and be issued later by this independent, idempotent process.
#
# The strict issuer is bounded to 5,000 candidates per pass. Repeated passes
# therefore converge on a larger backlog without requiring an operator to
# trigger the job repeatedly.
#
# Production safety: while the production database is read-only,
# GTEX_PLAYER_ISSUANCE_WRITE_ENABLED must remain false. Once write access is
# restored, flipping that environment variable enables the already-scheduled
# automatic activation path without another code deployment.
set -euo pipefail

cd "$(dirname "$0")/../.." || exit 1

if [ -z "${DATABASE_URL:-}" ]; then
  echo "FATAL: DATABASE_URL is not set" >&2
  exit 1
fi

if [ -z "${ISSUANCE_ACTOR_USER_ID:-}" ]; then
  echo "FATAL: ISSUANCE_ACTOR_USER_ID is not set." >&2
  echo "Issuance is admin-attributed; set it to an admin/super-admin user id." >&2
  exit 1
fi

# The strict issuer hard-caps --limit at 5000. Clamp rather than forwarding a
# stale Render setting such as the historical 50000 value.
REQUESTED_ISSUANCE_LIMIT="${ISSUANCE_LIMIT:-5000}"
if ! [[ "${REQUESTED_ISSUANCE_LIMIT}" =~ ^[0-9]+$ ]] || [ "${REQUESTED_ISSUANCE_LIMIT}" -lt 1 ]; then
  echo "FATAL: ISSUANCE_LIMIT must be a positive integer" >&2
  exit 1
fi
ISSUANCE_LIMIT="${REQUESTED_ISSUANCE_LIMIT}"
if [ "${ISSUANCE_LIMIT}" -gt 5000 ]; then
  ISSUANCE_LIMIT=5000
fi

ISSUANCE_MAX_ITERATIONS="${ISSUANCE_MAX_ITERATIONS:-20}"
REPORT_FILE="$(mktemp)"
trap 'rm -f "${REPORT_FILE}"' EXIT

run_pass() {
  local mode_flag="$1"
  python backend/scripts/issue_player_share_markets_strict.py \
    --database-url "${DATABASE_URL}" \
    --cohort-type all \
    --limit "${ISSUANCE_LIMIT}" \
    --actor-user-id "${ISSUANCE_ACTOR_USER_ID}" \
    "${mode_flag}" | tee "${REPORT_FILE}"
}

created_count() {
  python -c "import json,sys; print(json.load(open(sys.argv[1]))['counts']['created'])" "${REPORT_FILE}"
}

echo "== Player-share issuance: dry-run planning (${ISSUANCE_LIMIT} players/pass) =="
run_pass --dry-run >/dev/null

# Safety gate. The schedule may run continuously while production writes are
# unavailable, but no activation is attempted until this explicit switch is on.
if [ "${ISSUANCE_ACTIVATE:-true}" != "true" ] || [ "${GTEX_PLAYER_ISSUANCE_WRITE_ENABLED:-false}" != "true" ]; then
  echo
  echo "== Planning only. Issuance activation is guarded by GTEX_PLAYER_ISSUANCE_WRITE_ENABLED. =="
  exit 0
fi

echo
total_created=0
for ((i = 1; i <= ISSUANCE_MAX_ITERATIONS; i++)); do
  echo "== Automatic issuance: pass ${i}/${ISSUANCE_MAX_ITERATIONS} =="
  run_pass --activate >/dev/null
  pass_created="$(created_count)"
  total_created=$((total_created + pass_created))
  echo "   issued this pass: ${pass_created} (running total: ${total_created})"
  if [ "${pass_created}" -eq 0 ]; then
    echo "== No markets issued this pass -- backlog clear or remaining players are blocked. =="
    break
  fi
done

echo
echo "== Player share automatic issuance complete: ${total_created} markets issued =="
