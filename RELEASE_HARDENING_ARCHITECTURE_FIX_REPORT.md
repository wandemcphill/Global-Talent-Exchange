# Release Hardening Architecture Fix Report

Implemented in this pass:
- replaced direct screen-level HTTP in manager market and manager admin screens with repository-backed data access
- introduced a shared frontend feedback utility for standardized success and error messaging
- normalized error handling in major controllers and admin screens to use shared messaging
- unified competition runtime/admin orchestration access behind dedicated competition control repository and backend competition admin/runtime endpoints
- routed fast league runtime preview and competition orchestration preview through the shared competition control surface instead of split ad hoc calls
- preserved manager market and admin flows while reducing route drift risk

Backend unification added:
- `GET /api/competitions/runtime/{code}`
- `GET /api/competitions/admin`
- `PATCH /api/competitions/admin/{code}`
- `GET /api/competitions/admin/{code}/orchestrate`

Frontend shared utilities added:
- `frontend/lib/core/app_feedback.dart`
- `frontend/lib/data/manager_market_repository.dart`
- `frontend/lib/data/competition_control_repository.dart`

Primary screens refactored:
- `frontend/lib/screens/manager_market_screen.dart`
- `frontend/lib/screens/admin/manager_admin_screen.dart`
- `frontend/lib/screens/admin/god_mode_admin_screen.dart`

Controllers standardized for app-wide messaging:
- competition controller
- exchange controller
- creator controller
- referral controller
- club ops controller
- dynasty/reputation/trophy presentation controllers

Known honest boundary:
- this pass materially reduces architectural drift and screen-level request duplication, but full live runtime verification still requires local app execution.
