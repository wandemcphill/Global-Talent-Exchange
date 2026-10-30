#!/usr/bin/env bash
set -euo pipefail

# Build the GTEX React Web Application for Render static hosting.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
FRONTEND_DIR="${REPO_ROOT}/frontend"
REACT_DIR="${FRONTEND_DIR}/react-shell"

: "${GTE_API_BASE_URL:?GTE_API_BASE_URL must be set for the frontend build.}"
GTE_BACKEND_MODE="${GTE_BACKEND_MODE:-live}"

# Prevent API origins ending in /api from causing /api/api
case "${GTE_API_BASE_URL}" in
  */api|*/api/)
    echo "GTE_API_BASE_URL must be the API origin without a /api suffix (got ${GTE_API_BASE_URL})." >&2
    exit 1
    ;;
esac

echo ">>> Building GTEX React Web Application as primary web build..."
cd "${REACT_DIR}"

if [[ ! -f "package-lock.json" ]]; then
  echo "frontend/react-shell/package-lock.json is required for a deterministic Render build." >&2
  exit 1
fi

npm ci --legacy-peer-deps --include=dev

# React Web build at the root of the domain
export PUBLIC_URL=""
export REACT_APP_BACKEND_URL="${GTE_API_BASE_URL}"
export REACT_APP_GTE_TURNSTILE_SITE_KEY="${GTE_TURNSTILE_SITE_KEY:-${REACT_APP_GTE_TURNSTILE_SITE_KEY:-}}"
export CI=false
export NODE_OPTIONS="${NODE_OPTIONS:---openssl-legacy-provider}"

npm run build

if [[ ! -f "build/index.html" ]]; then
  echo "React build did not produce build/index.html." >&2
  exit 1
fi

mkdir -p "${FRONTEND_DIR}/build"
rm -rf "${FRONTEND_DIR}/build/web"
cp -a "${REACT_DIR}/build" "${FRONTEND_DIR}/build/web"

# Also maintain console/ directory so /console routes and assets resolve seamlessly
mkdir -p "${FRONTEND_DIR}/build/web/console"
cp -a "${REACT_DIR}/build/." "${FRONTEND_DIR}/build/web/console/"

echo ">>> GTEX React Web Application deployed to frontend/build/web successfully."
