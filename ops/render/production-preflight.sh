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

# Supabase direct connection (db.<ref>.supabase.co) resolves to IPv6 only, which
# Render's IPv4-only egress cannot reach ("Network is unreachable"). Require the
# IPv4 connection pooler host instead.
_gte_db_url="${DATABASE_URL:-${GTE_DATABASE_URL:-}}"
if [[ "${_gte_db_url}" == *"db."*".supabase.co"* ]]; then
  echo "DATABASE_URL points at the Supabase DIRECT host (db.<ref>.supabase.co), which is" >&2
  echo "IPv6-only and unreachable from Render. Use the Supabase connection pooler instead:" >&2
  echo "  postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require" >&2
  echo "(Session pooler, port 5432 — has an IPv4 address and supports migrations.)" >&2
  exit 1
fi

# Postgres connections to Supabase must negotiate TLS.
if [[ "${_gte_db_url}" == postgres* && "${_gte_db_url}" != *"sslmode="* ]]; then
  echo "DATABASE_URL is missing sslmode. Append ?sslmode=require (Supabase requires TLS)." >&2
  exit 1
fi

# Redis is enabled but no connection string was provided.
if [[ "${REDIS_ENABLED:-false}" == "true" && -z "${GTE_REDIS_URL:-${REDIS_URL:-}}" ]]; then
  echo "REDIS_ENABLED=true but no GTE_REDIS_URL/REDIS_URL is set. Provide the Render Redis" >&2
  echo "connection string, or set REDIS_ENABLED=false to use in-process fallbacks." >&2
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
