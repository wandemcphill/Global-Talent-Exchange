# CODEX Test Matrix

| Feature area | Test type | Result | Status | Notes |
| --- | --- | --- | --- | --- |
| Backend full suite | Automated backend tests | `362 passed in 848.83s` | Pass | Final post-hardening run |
| Alembic migrations | Migration head and upgrade | Head `20260312_0016`, upgrade passed | Pass | SQLite-safe migration fix verified |
| Auth and session | Backend automated tests | Included in full suite | Pass | `backend/tests/auth/` passed |
| Market and trading | Backend automated tests | Included in full suite | Pass | `backend/tests/market/`, `backend/tests/orders/`, `backend/tests/integration/` passed |
| Portfolio and wallet | Backend automated tests | Included in full suite | Pass | `backend/tests/portfolio/`, `backend/tests/wallets/` passed |
| Withdrawal controls | Targeted backend tests | `4 passed` | Pass | `backend/tests/admin_godmode/test_withdrawal_controls.py -q` |
| Withdrawal HTTP contract | Targeted backend tests | `9 passed` | Pass | `backend/tests/wallets/test_wallet_http.py -q` |
| Competitions and e-game | Backend automated tests | Included in full suite | Pass | Discovery, publish, join, and pipeline tests passed |
| Live match and simulation | Backend automated tests | Included in full suite | Pass | Match engine helper regression fixed and verified |
| Club identity and club hub data | Backend automated tests | Included in full suite | Pass | Canonical reputation and dynasty routes fixed |
| Manager seed data | Targeted backend test | `1 passed` | Pass | Tunde Oni seed mapping verified |
| Backend route inventory | Inline route introspection | `ROUTE_COUNT=301` | Pass | Duplicate `/api/api/orders*` removed |
| Canonical shell route audit | Source audit | Reachability checked by code | Partial | Creator lane fixed, withdrawal lane still missing user action |
| Button and CTA audit | Source audit | No obvious empty live handlers found | Partial | Runtime tapping not possible without Flutter |
| Frontend dependency restore | `flutter pub get` | Tool missing | Blocked | `flutter` not installed |
| Frontend static analysis | `flutter analyze` | Tool missing | Blocked | `flutter` not installed |
| Frontend widget tests | `flutter test` | Tool missing | Blocked | `flutter` not installed |
| Frontend interactive click-through | Manual runtime audit | Could not execute | Blocked | No Flutter runtime or emulator in environment |
| Admin UI controls | Source audit plus backend tests | Controls present and backed by API | Partial | Runtime save interactions not executable in this environment |
| Wallet withdrawal UX | Source audit | Backend exists, user UI missing | Fail | Canonical wallet lane has no withdrawal request CTA |
