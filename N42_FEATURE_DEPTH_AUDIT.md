# N42 — FEATURE DEPTH AUDIT (Phase D)

Date: 2026-06-13 · `feature/original-visual-runtime` @ `b5b19730`

Goal: separate **real depth** from **scaffolds pretending to be features**. Evidence: source inspection + executed tests this session.

## Headline: this is a mature backend, not a scaffold farm

- `backend/app` carries **159 `_module()` registrations** across ~100 domain packages, **431 backend test files**, **261 frontend test files**.
- Stub/`NotImplementedError`/`TODO`/`FIXME`/`placeholder` markers across the entire `backend/app`: **29 total** (4 in `services`, 2 in `providers`, rest scattered). For a surface this size that is **low** — most features have real service/repository/route layers, not stubs.
- The money spine is genuinely implemented: `trader/matching.py` performs real escrow settlement (cash leg buyer-escrow→liquidity→seller-net-of-fee; position leg seller-escrow→platform→buyer) via `WalletService.settle_reserved_funds` / `settle_reserved_position_units`, and `tests/trader` is **19/19 green**.

## Scaffolds / quarantined-but-present (not wired to production)

| Item | Finding | Disposition |
|---|---|---|
| `frontend/lib/features/3d/` | Has `controllers/models/services/widgets` + README but **zero imports from production code** outside its own dir; `match_center` references no Unity/3D. | Correctly quarantined. Keep out of build; do not delete under N42 scope. |
| Quarantine worktree `.external_worktrees/GTEX_FRONTEND_REDESIGN_WORKTREE` | `493098ae` / `codex/strict-live-phase-2`, diverged redesign. | Historical quarantine only. Never merge/build. |

## Partial implementations / blocked workflows (real, evidence-backed)

| Surface | Gap | Evidence |
|---|---|---|
| **Regen Universe** | Expansion routes (player story-DNA, rivalries, youth-tournament jobs) and **regen admin RBAC** (super-admin run, ops preseed/close-season, portrait management, support-admin negative cases) fail/error. | `BACKEND_VERIFICATION_REPORT` regen section (62 passed / 2 failed / 5 errors). |
| **Competitions** | Two sibling route-test files red (alias→410 + envelope shape). No **E2E “complete → distribute payout → wallet credit”** route test. | N42 Phase B; N39 #10. |
| **Transfer Market** | Reserved-balance-first settlement edge raises `InsufficientBalanceError`; two auth-message contracts mismatched (`*_club_access_required` vs `*_watchlist/bidder_club_access_required`). | `BACKEND_VERIFICATION_REPORT`. |
| **Creator** | Several creator / creator-market / stadium / share flows are blocked or render duplicated states; in-scope set not finalized. | `FEATURE_DEPTH_SCORECARD` Creator note. |
| **Trader (P2P offers)** | Order-book path is automated; **P2P offer path still settles manually** (no automated escrow), and disputes are partly audit-row-backed rather than fully first-class. | N39 #14/#19; `dispute_engine` module exists (router/schemas/service with `DisputeCreateRequest`/`DisputeView`) so general disputes ARE modeled — but trader-specific dispute promotion is incomplete. |

## Missing / thin by category

| Category | Status | Note |
|---|---|---|
| Missing backend contracts | **Mostly present** | `shared/api_contract.json` declares 1,276 canonical paths; contract guard live. Gap is test reconciliation, not missing contracts. |
| Missing repositories | **Low** | Domain packages have service+model layers; 29 stub markers only. |
| Missing UI flows | **Some** | Creator sub-flows, community depth, club_identity quick-link routing. |
| Missing error states | **Some** | Match Center has blocked/degraded states (strong); trader had duplicate “Order book blocked” copy (UI); community thinner. |
| Missing audit trails | **Strong where it matters** | Admin/finance/wallet auditability rated high; trader disputes the weak spot. |
| Missing settlement logic | **Implemented for order book; partial for P2P** | See trader rows above. |
| **Missing websocket authority/collision** | **Real gap** | Module registration fingerprints **HTTP** route collisions; no evidence of **WS** route-collision protection in `core/module.py`/`modules.py`. Lazy `api_v1` WS routes may depend on prior HTTP hydration. Match Center WS truth-guards exist at the app layer, but registration-time WS collision safety is unproven. |

## Depth verdict

GTEX is **feature-deep, not feature-faked**. The risks are concentrated and nameable: (1) regen expansion/RBAC route failures, (2) competition test-contract + missing payout E2E, (3) transfer reservation/auth-message edges, (4) trader P2P manual settlement + dispute promotion, (5) websocket collision authority. None of these are “redesign” problems; all are finite hardening tasks. The 3D/redesign quarantine boundaries are intact.
