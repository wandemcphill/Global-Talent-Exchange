#!/usr/bin/env bash
set -euo pipefail

# Controlled application rollback checklist.
# This script never changes production automatically. It prints the exact
# evidence that an operator must capture before selecting a prior release.

: "${CURRENT_COMMIT:?CURRENT_COMMIT must identify the deployed commit}"
: "${TARGET_COMMIT:?TARGET_COMMIT must identify the known-good commit}"
: "${MIGRATION_STATE:?MIGRATION_STATE must identify the deployed schema revision}"
: "${TARGET_MIGRATION_STATE:?TARGET_MIGRATION_STATE must identify the target schema revision}"
: "${HEALTH_URL:?HEALTH_URL must be the public health endpoint}"

printf '%s\n' 'GTEX production rollback preflight'
printf 'Current commit:        %s\n' "$CURRENT_COMMIT"
printf 'Target commit:         %s\n' "$TARGET_COMMIT"
printf 'Current migration:     %s\n' "$MIGRATION_STATE"
printf 'Target migration:      %s\n' "$TARGET_MIGRATION_STATE"
printf 'Health endpoint:       %s\n' "$HEALTH_URL"

if [[ "$MIGRATION_STATE" != "$TARGET_MIGRATION_STATE" ]]; then
  cat <<'EOF'

SCHEMA MISMATCH: do not roll back application code until the migration plan
explicitly proves that the target application is compatible with the current
schema, or the database restore procedure has been approved and rehearsed.
EOF
  exit 2
fi

if command -v curl >/dev/null 2>&1; then
  printf '\nPreflight health check:\n'
  curl --fail --silent --show-error --max-time 15 "$HEALTH_URL" >/dev/null
  printf 'Health endpoint reachable.\n'
fi

cat <<'EOF'

ROLLBACK READY:
1. Freeze new production deploys.
2. Capture current logs, commit SHA and migration revision.
3. Select TARGET_COMMIT only after schema compatibility is confirmed.
4. Deploy the known-good application release through the normal deployment path.
5. Run health, authentication, wallet and live-match smoke checks.
6. If schema rollback is required, use the separately rehearsed backup restore.
7. Record the incident, evidence and final state before unfreezing deploys.
EOF
