#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
FRONTEND_DIR="${REPO_ROOT}/frontend"
FLUTTER_ROOT="${FLUTTER_ROOT:-${HOME}/flutter}"
FLUTTER_REVISION="ff37bef603469fb030f2b72995ab929ccfc227f0"

: "${GTE_API_BASE_URL:?GTE_API_BASE_URL must be set for the frontend build.}"
GTE_BACKEND_MODE="${GTE_BACKEND_MODE:-live}"

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
  --dart-define="GTE_BACKEND_MODE=${GTE_BACKEND_MODE}"
