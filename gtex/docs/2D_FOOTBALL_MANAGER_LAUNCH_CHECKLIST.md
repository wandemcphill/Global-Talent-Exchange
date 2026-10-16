# 2D Football Manager Launch Checklist

## Works For Launch
- 2D shell routes: Club HQ, Fixtures, Transfer Market, Scout Prospects, Competitions, Manager.
- Transfer Market: View Player, Buy Now, List for Transfer, Remove Listing.
- Player and regen cards: football card/scouting card layout with rating, position, club, nationality, age, value, wage, and potential.
- Real player images: card payloads read approved licensed image metadata first.
- Regen portraits: deterministic faceSeed, stored faceRecipe JSON, generated 2D PNG portrait, portraitUrl saved on player DNA and visual profile metadata.
- Portrait fallback: frontend cards use portraitUrl/imageUrl first and a clean football silhouette if no image exists.
- Admin portrait controls: Regenerate Portrait, Upload/Override Portrait, Ban Bad Portrait.
- Wallet: Deposit, Withdraw, Transaction History; manual bank deposit is visible and usable.
- Competitions: authenticated managers can create competitions; admins can open controls, create competitions, and seed competition templates.
- Generated media: backend serves generated portraits from `/generated-media`.
- 2D match viewer: Flutter `CustomPaint` pitch, tiny numbered player circles, visible ball, pass trail, top score strip, bottom commentary bar, and compact playback controls.
- Match event contract: `/api/match-viewer/{match_key}` accepts and emits `pass` events with commentary, clamped `duration_ms`, optional player target positions, and optional ball target/owner.

## Blocked For Launch
- Public 3D match viewer routes.
- Native 3D match viewer route.
- Broadcast matchday route.
- Simulation and spectate utility routes.
- Streamer engine route.
- Creator stadium and broadcast desk deep routes.
- Raw 3D player heads/models on cards.
- Loan, swap, share-market, and order-book actions in the main Transfer Market UI.

## Notes
- Unity files and batchmode build paths are untouched.
- Verification on 2026-04-28:
  - Frontend tests passed: `test/transfer_market/transfer_market_screen_test.dart`, `test/regens/regens_screen_test.dart`, `test/profile_admin_visibility_test.dart`, `test/navigation_surface_truth_test.dart`.
  - 2D match viewer analysis passed: `flutter analyze` over the touched match viewer, pitch, playback, route blocking, and focused test files.
  - 2D match viewer tests passed: `test/pitch_2d_widget_telemetry_test.dart`, `test/match_viewer_screen_test.dart`, `test/active_shell_route_mount_test.dart`, `test/match_3d_route_truth_test.dart`, `test/match_3d_route_hardening_test.dart`, `test/match_broadcast_route_screen_test.dart`, `test/match_simulate_route_screen_test.dart`.
  - Backend tests passed: `backend/tests/regen/test_regen_admin_rbac.py`, `backend/tests/services/test_regen_portrait_service.py`, `backend/tests/player_cards/test_marketplace_service.py`, `backend/tests/player_cards/test_player_card_market.py`.
  - 2D match backend tests passed: `backend/tests/test_match_timeline_service.py`, `backend/tests/test_match_viewer_route.py`.
  - Unity was not rerun for the 2D match viewer pass; Unity files and batchmode paths were left untouched.
  - Unity batchmode Windows build succeeded. Log: [gtex_test_migration_windows_build.log](C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_test_migration_windows_build.log).
  - Build output: `Gtex_Test_Migration/Builds/WindowsProduction/GTEXMatch.exe`.
- The optional face pack at `c:\Users\ayomc\Downloads\ai generated face pack.7z` was present, but no local `7z`/`7za`/`7zr` extraction tool was available, so launch art falls back to generated 2D portraits and clean silhouettes.
