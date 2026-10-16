# GTEX Android Build Troubleshooting

## Baseline build order

Flutter was not installed in this audit environment, so run these locally on a machine with the Flutter SDK:

```powershell
cd frontend
flutter pub get
flutter analyze
flutter test
flutter build apk --debug
```

If the Android wrapper is incomplete, regenerate it locally:

```powershell
flutter create . --platforms=android
```

After a successful debug build, configure signing and run:

```powershell
flutter build apk --release
```

## Windows file-lock recovery for `mergeDebugNativeLibs` or `libflutter.so`

These failures are usually environmental. Typical lock holders are the emulator, `adb`, a stale Gradle daemon, a Flutter debugger, Windows Explorer, or antivirus scanning `frontend\build\`.

1. Close the running app, emulator, Android Studio, and any Explorer window open inside `frontend\build`.
2. Inspect likely lock holders:

```powershell
Get-Process adb, dart, flutter, java, gradle -ErrorAction SilentlyContinue
```

3. Stop stale build or debug processes only if they are not needed:

```powershell
Stop-Process -Name adb, dart, flutter, java, gradle -Force -ErrorAction SilentlyContinue
```

4. Clean transient build state:

```powershell
cd frontend
flutter clean
Remove-Item -Recurse -Force .dart_tool, build -ErrorAction SilentlyContinue
flutter pub get
```

5. Retry the debug build:

```powershell
flutter build apk --debug
```

6. If Windows still refuses to release `libflutter.so`, reboot or sign out before retrying. That usually indicates an OS-level handle, not a GTEX source issue.

## When the failure is probably code, not environment

- `flutter analyze` fails before Gradle starts.
- `flutter test` fails consistently on the same source or test file.
- `flutter create . --platforms=android` completes, but Gradle still fails on a checked-in Android file. That lane is merge-owned; hand it back to GTEX MERGE instead of editing `frontend/android/*` from a parallel doc thread.

## Current limits for this thread

- This thread did not retry APK builds.
- This thread did not edit `frontend/android/*`, `frontend/pubspec.yaml`, or `frontend/pubspec.lock`.
