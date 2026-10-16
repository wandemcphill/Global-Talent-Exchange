#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
flutter create . --platforms=android
flutter pub get
echo "Android scaffold regenerated. You can now run: flutter build apk --debug"
