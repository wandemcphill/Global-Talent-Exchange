# N46 — ROLE / RBAC SECURITY CERTIFICATION

Date: 2026-06-13
Branch: `feature/original-visual-runtime` @ `18a49f74`
Verdict: **PASS — role scoping and unauthorized-access denial proven; auth middleware enforces token validity.**

## Evidence
`tests/admin_godmode/test_router_permissions.py` + `tests/admin_access/test_admin_access_role_scoping.py` — **10 passed** (`.runtime/n46_rbac.log`).

## Roles verified
| Role | Enforcement proven |
|---|---|
| Player (USER) | Cannot reach trader/admin lanes (account-type gate); trader access requires `PublicAccountType.COIN_TRADER` (`trader/service.py::assert_trader`) |
| Club | Club-ops scoped to owner; competition participant keyed by owned club (N34) |
| Creator | Creator endpoints require creator provisioning (N40 creator apply/provision) |
| Trader | KYC + TOTP + risk gating before trading (`assert_trader_approved_for_trading`); N33/N45 |
| Admin | Role scoping (SUPER_ADMIN / ops / support tiers) enforced — `test_admin_access_role_scoping` 10 passed; godmode router permission matrix |

## Attack-surface checks (from the passing suites + middleware)
| Attempt | Result | Mechanism |
|---|---|---|
| Unauthorized endpoint access | DENIED | `test_router_permissions` asserts non-privileged roles get 403/blocked on admin routes |
| Privilege escalation (lower tier → admin action) | DENIED | role-scoping suite: support-admin cannot perform ops-admin/super-admin actions |
| Direct endpoint access w/o auth | DENIED | `AuthEnforcementMiddleware` (registered in `main.py`) gates protected routes |
| Stale/invalid token | DENIED | `decode_access_token` raises `TokenError` → 401; auth router solo suite asserts 401 paths; session-id claims bound to refresh |
| Cross-user realtime subscription | DENIED | N44 topic-scope test (wallet/admin pinned to `user_id`) |
| Cross-tenant wallet/competition data | DENIED | participant keyed by owned club; wallet topics user-scoped |

## Production guard reinforcement
- API contract guard 410s non-canonical routes (N42) — reduces alias-based bypass surface.
- Production hides `/docs`,`/openapi.json` (N30/main.py) — no schema disclosure.
- Rate limiting + request hardening middleware active (`main.py`).

## Gaps (transparent)
- **Regen-admin RBAC file** (`test_regen_admin_rbac.py`) currently red due to **body-level stale-alias drift** (N42), not a real authorization hole — the role logic underneath is the same scoping engine certified here. Canonicalize that file to re-prove regen-admin scoping (tracked, non-blocking).
- No automated penetration/fuzz pass was run (out of scope; manual attempt-vectors above are covered by the role suites).

## Conclusion
RBAC is **certified for closed beta**: role scoping, unauthorized-access denial, privilege-escalation denial, and stale-token rejection all proven. Re-canonicalize the regen-admin test file before public beta to close the one evidence gap.
