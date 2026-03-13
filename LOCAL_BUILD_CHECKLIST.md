# GTEX Local Build Checklist

## Backend
1. Create a virtual environment.
2. Install dependencies with `pip install -r backend/requirements.txt`.
3. Copy `backend/.env.example` to `backend/.env` and adjust values if needed.
4. Start the API from the repo root with `uvicorn backend.app.main:app --reload`.
5. Check:
   - `GET /health`
   - `GET /ready`
   - `GET /version`
   - `GET /diagnostics`

## Frontend
1. Install Flutter SDK and confirm `flutter doctor` is clean enough for Android.
2. From `frontend/`, run `flutter pub get`.
3. Regenerate Android wrapper pieces if needed:
   - `flutter create . --platforms=android`
4. Run the app:
   - `flutter run`
5. Build an APK:
   - `flutter build apk --debug`

## High-priority click tests
- Normal login
- Admin auto-routing after normal login
- Manager catalog search and filters
- Recruit, assign, release, list, cancel listing, buy, swap
- Super admin create admin, edit permissions, disable admin
- Competition toggle behavior
- Fast League runtime preview

## Known local prerequisites
- `frontend/android/gradle/wrapper/gradle-wrapper.jar` may need regeneration by Flutter.
- The backend relies on TOML config files inside `backend/config`.
