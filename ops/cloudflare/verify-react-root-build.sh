#!/usr/bin/env bash
# Validates a root-domain (playgtex.app) React build. Usage: verify-react-root-build.sh <build-dir>
set -euo pipefail
BUILD_DIR="${1:-build}"
API="${REACT_APP_BACKEND_URL:?REACT_APP_BACKEND_URL must be set}"

[[ -f "${BUILD_DIR}/index.html" ]] || { echo "missing index.html" >&2; exit 1; }
[[ -f "${BUILD_DIR}/_redirects" ]] || { echo "missing _redirects (SPA fallback)" >&2; exit 1; }
grep -qE '^/\*[[:space:]]+/index.html[[:space:]]+200' "${BUILD_DIR}/_redirects" || { echo "SPA fallback rule missing" >&2; exit 1; }
grep -q '^/console' "${BUILD_DIR}/_redirects" || { echo "legacy /console redirect missing" >&2; exit 1; }

if grep -qE '(src|href)="/console/' "${BUILD_DIR}/index.html"; then
  echo "index.html references /console/ assets; root build expected" >&2; exit 1
fi
grep -qE '(src|href)="/static/' "${BUILD_DIR}/index.html" || { echo "index.html has no root-absolute /static/ assets" >&2; exit 1; }
grep -rq "${API}" "${BUILD_DIR}/static/js" || { echo "canonical API origin ${API} not found in bundle" >&2; exit 1; }
if grep -rqE 'flutter_bootstrap|main\.dart\.js' "${BUILD_DIR}/index.html"; then
  echo "Flutter host detected in React build" >&2; exit 1
fi
echo "React root build OK (${BUILD_DIR})"
