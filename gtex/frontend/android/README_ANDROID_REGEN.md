# Android regeneration note

This repository was missing the Flutter `android/` project structure. A baseline Android scaffold has been restored here so the app is much closer to APK shape.

## Important

Because this environment cannot run the Flutter SDK, the Gradle wrapper JAR was not generated here. On your local machine, run one of these from `frontend/`:

```powershell
flutter create . --platforms=android
flutter pub get
flutter build apk --debug
```

or use the included script:

```powershell
./scripts/regenerate_android.ps1
```

That will refresh any missing Android wrapper files while preserving `lib/` and your Dart application code.
