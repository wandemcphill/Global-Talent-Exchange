# GTEX APK prep checklist

## What was hardened in this package
- restored a baseline Flutter `android/` scaffold
- added missing `http` dependency to the Flutter pubspec
- cleaned transient caches and build artifacts from the source package
- added Android regeneration scripts for local Flutter SDK usage
- kept admin login hidden from public UI while preserving auto-routing for admin accounts

## Local build order
1. unzip the package
2. open `frontend/`
3. run `flutter pub get`
4. run `flutter create . --platforms=android` if the Android wrapper is incomplete
5. run `flutter build apk --debug`
6. after debug success, configure signing and run `flutter build apk --release`

## Highest-risk items still needing local runtime validation
- manager market buttons against your live backend
- admin dashboard permission flows
- competition toggle flows
- any route that depends on backend data not seeded locally
