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
# Idempotent: players that already hold a market are skipped, so it is safe to
# re-run after an interruption.
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

# Large enough to cover the whole backlog in one pass; the script skips players
# that already have a market, so an oversized limit costs nothing.
ISSUANCE_LIMIT="${ISSUANCE_LIMIT:-50000}"

echo "== Dry run: planning issuance for up to ${ISSUANCE_LIMIT} players =="
python backend/scripts/issue_player_share_markets_strict.py \
  --database-url "${DATABASE_URL}" \
  --cohort-type all \
  --limit "${ISSUANCE_LIMIT}" \
  --actor-user-id "${ISSUANCE_ACTOR_USER_ID}" \
  --dry-run

if [ "${ISSUANCE_ACTIVATE:-false}" != "true" ]; then
  echo
  echo "== Dry run only.  Set ISSUANCE_ACTIVATE=true to actually issue. =="
  exit 0
fi

echo
echo "== Activating issuance =="
python backend/scripts/issue_player_share_markets_strict.py \
  --database-url "${DATABASE_URL}" \
  --cohort-type all \
  --limit "${ISSUANCE_LIMIT}" \
  --actor-user-id "${ISSUANCE_ACTOR_USER_ID}" \
  --activate

echo "== Player share issuance complete =="
