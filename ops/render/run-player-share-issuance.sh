#!/usr/bin/env bash
# Issue player-share markets for every eligible tradable player missing one.
#
# Triggered manually from Render (cron job "gtex-player-share-issuance" ->
# Trigger Run) so it runs co-located with the database.  Per-issuance latency
# over a remote pooler makes a laptop run impractical at this volume: each
# issuance writes a market, a wallet, a transaction and ledger entries.
#
# Context: the market listing used to lazily create a market per listed row
# inside a GET, then roll it back because a read path never commits -- so the
# work was redone on every request and never persisted.  The listing is now
# read-only and only shows issued markets, so unissued players are invisible
# until this runs.  Ingestion issues markets for new players from here on; this
# job closes the backlog that accumulated before that.
#
# issue_player_share_markets_strict.py hard-caps --limit at 5000 and commits
# once per invocation, so a backlog bigger than that needs multiple calls.
# This loops calls of ISSUANCE_LIMIT (<=5000) each, stopping once a call
# issues nothing more -- either the backlog is clear, or everything left is
# genuinely blocked (missing country/club context) and further calls would
# just repeat the same result.
#
# Idempotent: players that already hold a market are skipped, so it is safe to
# re-run after an interruption; a partial run picks up where it left off.
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

# issue_player_share_markets_strict.py rejects anything outside 1-5000.
ISSUANCE_LIMIT="${ISSUANCE_LIMIT:-5000}"
# Bounds how many 5000-player calls one trigger makes; 20 covers a 100k
# backlog. Loop still stops early once a call issues 0, so this is a safety
# ceiling, not a target.
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

echo "== Dry run: planning issuance (up to ${ISSUANCE_LIMIT} players per pass) =="
run_pass --dry-run >/dev/null

if [ "${ISSUANCE_ACTIVATE:-false}" != "true" ]; then
  echo
  echo "== Dry run only.  Set ISSUANCE_ACTIVATE=true to actually issue. =="
  exit 0
fi

echo
total_created=0
for ((i = 1; i <= ISSUANCE_MAX_ITERATIONS; i++)); do
  echo "== Activating issuance: pass ${i}/${ISSUANCE_MAX_ITERATIONS} =="
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
echo "== Player share issuance complete: ${total_created} markets issued =="
