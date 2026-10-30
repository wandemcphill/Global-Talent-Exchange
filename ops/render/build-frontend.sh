#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
FRONTEND_DIR="${REPO_ROOT}/frontend"
FLUTTER_ROOT="${FLUTTER_ROOT:-${HOME}/flutter}"
FLUTTER_REVISION="ff37bef603469fb030f2b72995ab929ccfc227f0"

: "${GTE_API_BASE_URL:?GTE_API_BASE_URL must be set for the frontend build.}"
GTE_BACKEND_MODE="${GTE_BACKEND_MODE:-live}"

# When launching React on Web first (bypassing Flutter Web / mobile apps), build React directly to site root
BUILD_REACT_ONLY="${BUILD_REACT_ONLY:-true}"
if [[ "${BUILD_REACT_ONLY}" == "true" ]]; then
  echo ">>> Building React Web Application as primary web root..."
  cd "${FRONTEND_DIR}/react-shell"
  export PUBLIC_URL=""
  export REACT_APP_BACKEND_URL="${GTE_API_BASE_URL}"
  export CI=false
  export NODE_OPTIONS="${NODE_OPTIONS:---openssl-legacy-provider}"
  npm ci --legacy-peer-deps --include=dev || npm install --legacy-peer-deps --include=dev
  npm run build
  mkdir -p "${FRONTEND_DIR}/build"
  rm -rf "${FRONTEND_DIR}/build/web"
  cp -r "${FRONTEND_DIR}/react-shell/build" "${FRONTEND_DIR}/build/web"
  echo ">>> React Web Application built and deployed to frontend/build/web successfully."
  exit 0
fi

# Fallback: legacy dual-host build
GTEX_SHELL_V3="${GTEX_SHELL_V3:-true}"
case "${GTEX_SHELL_V3}" in
  true|false) ;;
  *)
    echo "GTEX_SHELL_V3 must be 'true' or 'false'." >&2
    exit 1
    ;;
esac

if ! git -C "${FLUTTER_ROOT}" rev-parse --git-dir >/dev/null 2>&1; then
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

bash "${SCRIPT_DIR}/publish-react-shell.sh"
