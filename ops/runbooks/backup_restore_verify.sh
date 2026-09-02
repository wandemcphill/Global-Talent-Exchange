#!/usr/bin/env bash
set -euo pipefail

# Safe, non-destructive backup/restore rehearsal helper.
# Required: SOURCE_DATABASE_URL and RESTORE_DATABASE_URL.
# The restore target must be an isolated disposable database.

: "${SOURCE_DATABASE_URL:?SOURCE_DATABASE_URL is required}"
: "${RESTORE_DATABASE_URL:?RESTORE_DATABASE_URL is required}"

OUT_DIR="${OUT_DIR:-./artifacts/gtex-db-backup}"
mkdir -p "$OUT_DIR"
DUMP_FILE="$OUT_DIR/gtex_$(date -u +%Y%m%dT%H%M%SZ).dump"

printf 'Creating compressed PostgreSQL backup...\n'
pg_dump --format=custom --no-owner --no-acl "$SOURCE_DATABASE_URL" > "$DUMP_FILE"

printf 'Verifying backup archive...\n'
pg_restore --list "$DUMP_FILE" >/dev/null

printf 'Restoring into isolated target...\n'
pg_restore \
  --clean \
  --if-exists \
  --no-owner \
  --no-acl \
  --exit-on-error \
  --dbname="$RESTORE_DATABASE_URL" \
  "$DUMP_FILE"

printf 'Running restore connectivity check...\n'
psql "$RESTORE_DATABASE_URL" -v ON_ERROR_STOP=1 -c 'select 1 as restore_verified;'

printf 'Backup/restore rehearsal passed: %s\n' "$DUMP_FILE"
