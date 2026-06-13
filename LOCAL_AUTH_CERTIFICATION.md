# LOCAL AUTH CERTIFICATION

Date: 2026-06-12
Repo: `C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE`
Branch / HEAD verified: `feature/original-visual-runtime` @ `ec231f2038bd0e8c7c98438201d924bf066b7423`
Verdict: **PASS for local alpha automated auth certification**

## Scope

This certification covers local, non-deployed alpha usage only:

- registration
- login
- logout
- session persistence / refresh
- password reset through recovery questions
- websocket auth contract wiring
- returning later after browser close, represented by persisted frontend session state plus backend refresh/session-bootstrap proof

## Evidence

| Area | Result | Evidence |
| --- | --- | --- |
| Register + login + current user | PASS | `python -B -m pytest -p no:cacheprovider -q backend/tests/auth/test_auth_router.py::test_register_login_and_me_flow ...` -> 5 passed |
| Refresh + session bootstrap + logout revocation | PASS | Same auth shard: `test_refresh_logout_and_session_bootstrap_flow` included; logout revokes bootstrap with old token |
| Password reset | PASS | Same auth shard: `test_recovery_questions_reset_password_and_revoke_existing_sessions` included |
| Recovery challenge privacy | PASS | Same auth shard: `test_recovery_challenge_does_not_disclose_account_or_prompt_text` included |
| Auth logging | PASS | Same auth shard: `test_login_user_logs_completion` included |
| Frontend session persistence | PASS | `flutter test --no-pub test\shared\auth_identity_store_test.dart test\active_session_provider_test.dart test\gte_frontend_app_auth_sync_test.dart` -> 4 passed |
| Websocket auth/route contracts | PASS | `python -B -m pytest -p no:cacheprovider -q backend/tests/realtime/test_websocket_route_contracts.py backend/tests/realtime/test_wallet_websocket_gateway.py backend/tests/realtime/test_regen_creation_realtime.py` -> 4 passed |

## New-User Flow

Automated proof shows a brand-new player signup can receive access and refresh tokens, bootstrap a session, refresh that session, and later be rejected after logout. Frontend proof shows auth sessions are written, read, merged, and cleared through the app session controller.

Manual browser close/reopen was not run with a human-controlled browser. The automated equivalent passed: backend refresh/session bootstrap plus frontend session-store persistence.

## Status

Authentication is **local-alpha ready**. Remaining manual pre-invite check: open the built web app, register a new account, close the browser tab, reopen the same URL, and verify the session hydrates without re-login.

