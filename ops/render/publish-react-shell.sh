#!/usr/bin/env bash
# Build the Emergent React shell and copy it into the Flutter web output at console/.
# Called by ops/render/build-frontend.sh after `flutter build web` succeeds.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
FRONTEND_DIR="${REPO_ROOT}/frontend"
REACT_DIR="${FRONTEND_DIR}/react-shell"

# Render sets RENDER=true. An override is only for the local smoke test; on
# Render the shell must land in the Flutter publish directory.
if [[ -n "${RENDER:-}" && -n "${GTEX_WEB_PUBLISH_DIR:-}" ]]; then
  echo "Refusing GTEX_WEB_PUBLISH_DIR on Render. The React shell publishes into frontend/build/web/console." >&2
  exit 1
fi

WEB_DIR="${GTEX_WEB_PUBLISH_DIR:-${FRONTEND_DIR}/build/web}"
CONSOLE_DIR="${WEB_DIR}/console"

: "${GTE_API_BASE_URL:?GTE_API_BASE_URL must be set for the React shell build.}"

# The shell appends /api itself. An origin that already ends in /api would
# call /api/api/... and miss the canonical routes.
case "${GTE_API_BASE_URL}" in
  */api|*/api/)
    echo "GTE_API_BASE_URL must be the API origin without a /api suffix (got ${GTE_API_BASE_URL})." >&2
    exit 1
    ;;
esac

if [[ -z "${WEB_DIR}" || "${CONSOLE_DIR}" != "${WEB_DIR}/console" ]]; then
  echo "Unsafe React publish directory: ${CONSOLE_DIR}" >&2
  exit 1
fi

if [[ ! -f "${WEB_DIR}/index.html" ]]; then
  echo "Flutter web output is missing at ${WEB_DIR}/index.html. Refusing to publish the React shell alone." >&2
  exit 1
fi

if ! grep -q 'flutter_bootstrap.js' "${WEB_DIR}/index.html"; then
  echo "Site-root index.html is not the Flutter host. Refusing to publish the React shell over it." >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required to build the React shell." >&2
  exit 1
fi

if [[ ! -f "${REACT_DIR}/package-lock.json" ]]; then
  echo "frontend/react-shell/package-lock.json is required for a deterministic Render build." >&2
  exit 1
fi

cd "${REACT_DIR}"
npm ci --legacy-peer-deps --include=dev

# Force the production path and API origin. Dashboard leftovers must not
# publish the shell at / or point it at another backend.
export PUBLIC_URL="/console"
export REACT_APP_BACKEND_URL="${GTE_API_BASE_URL}"
# CRA fails the production build on warnings when CI=true, and Render exports
# CI=true. This package's GitHub workflow builds with CI=false.
export CI=false
export NODE_OPTIONS="${NODE_OPTIONS:---openssl-legacy-provider}"

npm run build

if [[ ! -f "${REACT_DIR}/build/index.html" ]]; then
  echo "React build did not produce build/index.html." >&2
  exit 1
fi

rm -rf "${CONSOLE_DIR}"
mkdir -p "${CONSOLE_DIR}"
cp -a "${REACT_DIR}/build/." "${CONSOLE_DIR}/"

if [[ ! -f "${WEB_DIR}/index.html" ]] || ! grep -q 'flutter_bootstrap.js' "${WEB_DIR}/index.html"; then
  echo "Flutter index.html at the site root was overwritten while publishing the React shell." >&2
  exit 1
fi

GTE_API_BASE_URL="${GTE_API_BASE_URL}" bash "${SCRIPT_DIR}/verify-console-bundle.sh" "${CONSOLE_DIR}"
