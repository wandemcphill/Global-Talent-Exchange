#!/usr/bin/env bash
# Cloudflare Pages build script for GTEX Flutter web frontend.
# Cloudflare Pages injects environment variables set in the Pages dashboard
# as shell env vars during the build — not as --dart-define flags automatically.
# This script bridges them.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
FRONTEND_DIR="${REPO_ROOT}/frontend"
FLUTTER_ROOT="${FLUTTER_ROOT:-${HOME}/flutter}"
FLUTTER_REVISION="ff37bef603469fb030f2b72995ab929ccfc227f0"

: "${GTE_API_BASE_URL:?GTE_API_BASE_URL must be set in Cloudflare Pages environment variables.}"
GTE_BACKEND_MODE="${GTE_BACKEND_MODE:-live}"
# P9-SHELL is the canonical production shell. Default it on; allow an explicit false for rollback.
GTEX_SHELL_V3="${GTEX_SHELL_V3:-true}"
case "${GTEX_SHELL_V3}" in
  true|false) ;;
  *)
    echo "GTEX_SHELL_V3 must be 'true' or 'false'." >&2
    exit 1
    ;;
esac

if [ ! -d "${FLUTTER_ROOT}/.git" ]; then
  rm -rf "${FLUTTER_ROOT}"
  git clone https://github.com/flutter/flutter.git "${FLUTTER_ROOT}"
fi

git -C "${FLUTTER_ROOT}" fetch origin "${FLUTTER_REVISION}" --depth 1
git -C "${FLUTTER_ROOT}" checkout "${FLUTTER_REVISION}"

export PATH="${FLUTTER_ROOT}/bin:${PATH}"

flutter config --enable-web
flutter precache --web

cd "${FRONTEND_DIR}"
flutter pub get
flutter build web --release \
  --dart-define="GTE_API_BASE_URL=${GTE_API_BASE_URL}" \
  --dart-define="GTE_BACKEND_MODE=${GTE_BACKEND_MODE}" \
  --dart-define="GTE_TURNSTILE_SITE_KEY=${GTE_TURNSTILE_SITE_KEY:-}" \
  --dart-define="GTEX_SHELL_V3=${GTEX_SHELL_V3}"
