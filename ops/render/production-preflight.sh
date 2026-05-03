#!/usr/bin/env bash
set -euo pipefail

if [[ "${GTE_APP_ENV:-}" != "production" ]]; then
  exit 0
fi

if [[ "${GTE_INGESTION_PROVIDER:-mock}" == "mock" ]]; then
  echo "GTE_INGESTION_PROVIDER must not be mock in production." >&2
  exit 1
fi

if [[ "${GTE_RUN_MIGRATION_CHECK:-false}" != "true" ]]; then
  echo "GTE_RUN_MIGRATION_CHECK must be true in production." >&2
  exit 1
fi

if [[ "${DATABASE_URL:-}" == sqlite* || "${GTE_DATABASE_URL:-}" == sqlite* ]]; then
  echo "Production DATABASE_URL must not point at SQLite." >&2
  exit 1
fi

if [[ -z "${GTE_AUTH_SECRET:-}" ]]; then
  echo "GTE_AUTH_SECRET is required in production." >&2
  exit 1
fi

if [[ -z "${GTE_MEDIA_SIGNING_SECRET:-}" ]]; then
  echo "GTE_MEDIA_SIGNING_SECRET is required in production." >&2
  exit 1
fi

echo "GTEX production preflight passed."
