# N47 — END-TO-END USER FLOW CERTIFICATION

Date: 2026-06-13
Branch: `feature/original-visual-runtime` @ `18a49f74`
Verdict: **PASS — all four journeys complete at the backend-truth level; no BLOCKED steps for closed beta.**

Legend: PASS = proven by passing test/evidence · FAIL = proven broken · BLOCKED = cannot execute.

## Journey A — signup → wallet → Build-a-Son → squad
| Step | Result | Evidence |
|---|---|---|
| Signup (player) | PASS | auth router solo 13/13 (`.runtime/n42_authrouter.log`); N40 `LOCAL_AUTH_CERTIFICATION` |
| Login / session persist | PASS | N40 auth cert (frontend session/device store 4 passed); refresh-token claims asserted |
| Wallet (balance/reserve) | PASS | N33 100 money tests; N45 reserve/leak invariants |
| Build-a-Son (regen creation) | PASS | N40 starter-regens fixed & green; regen creation orders tests |
| Squad management | PASS | N40 squad/formation backend checks passed |

## Journey B — competition create → join → standings → settlement
| Step | Result | Evidence |
|---|---|---|
| Create | PASS | N34 lifecycle 6/6 (`.runtime/n34_lifecycle3.log`) |
| Join (+ paid entry) | PASS | N34 single-fee idempotent join |
| Fixtures / rounds | PASS | N34 league fixtures (6 for 4 clubs), cup progression |
| Standings | PASS | N34 standings update after result |
| Settlement | PASS | N34 reward settlement; entry-fee ledger truth |

## Journey C — transfer list → bid → reserve → accept
| Step | Result | Evidence |
|---|---|---|
| List player | PASS | N35 transfer market (77 passed incl. `test_transfer_market`) |
| Place bid | PASS | N33/N35 bid reservation parity |
| Reserve funds | PASS | N45 reserve invariant (exact hold, leak-free release) |
| Withdraw bid | PASS | bid withdrawal release (N33/N35) |
| Accept transfer / settle | PASS | settlement handoff (N33 settlement service) |

## Journey D — creator apply → campaign → payout
| Step | Result | Evidence |
|---|---|---|
| Apply (creator access) | PASS | N40 creator backend 10 passed; creator frontend 9 passed |
| Provision creator assets | PASS | N40 creator provisioning/journey slices green |
| Create campaign | PASS | creator module contracts (N40) |
| Payout / settlement | PASS | **N40 fixed payout fee handoff** (net+fee consistent); N45 fee-drift prevented; 30 payout tests green |

## Cross-cutting
- **No BLOCKED steps.** Every journey step maps to a passing backend test or certification.
- **Surface caveat:** these are **backend-truth + widget-level** proofs. A live click-through over the tunnel (browser, real device) is the remaining manual smoke (N40 access plan) — recommended as the alpha day-1 activity, not a blocker.

## Conclusion
All four directive journeys (A–D) are **end-to-end green at the backend/contract level**. Closed beta can exercise them for real; capture a live browser walkthrough during the first alpha session to close the UI-level loop.
