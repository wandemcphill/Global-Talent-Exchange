#!/usr/bin/env bash
# Verify a production React shell bundle built for /console.
# Usage: verify-console-bundle.sh <bundle-dir>
set -euo pipefail

BUNDLE_DIR="${1:?bundle directory required}"

: "${GTE_API_BASE_URL:?GTE_API_BASE_URL must be set so the bundle can be checked against the canonical API origin.}"

if [[ ! -f "${BUNDLE_DIR}/index.html" ]]; then
  echo "Missing ${BUNDLE_DIR}/index.html" >&2
  exit 1
fi

if ! grep -q '/console/static/' "${BUNDLE_DIR}/index.html"; then
  echo "React index.html does not reference /console/static assets. Rebuild with PUBLIC_URL=/console." >&2
  exit 1
fi

if ! grep -q 'id="root"' "${BUNDLE_DIR}/index.html"; then
  echo "React index.html is missing the shell root node." >&2
  exit 1
fi

if grep -q 'flutter_bootstrap.js' "${BUNDLE_DIR}/index.html"; then
  echo "React bundle directory contains the Flutter host document." >&2
  exit 1
fi

if [[ ! -d "${BUNDLE_DIR}/static/js" ]]; then
  echo "React bundle is missing static/js." >&2
  exit 1
fi

if ! grep -R -q -F "${GTE_API_BASE_URL}" "${BUNDLE_DIR}/static/js"; then
  echo "React bundle does not contain the canonical API origin ${GTE_API_BASE_URL}." >&2
  exit 1
fi

if [[ ! -f "${BUNDLE_DIR}/img/hero.jpg" ]]; then
  echo "React public image img/hero.jpg was not copied into the bundle." >&2
  exit 1
fi
