# N42 — ALIAS DRIFT REPORT (Phase B)

Date: 2026-06-13
Branch: `feature/original-visual-runtime` @ `b5b19730`
Basis: live grep + actual middleware read + executed pytest. No estimation.

---

## How canonicalization is actually enforced (verified)

The authoritative rule lives in `backend/app/core/api_contract.py` → `ApiContractGuardMiddleware` (installed in production via `install_api_contracts(app)` at `backend/app/main.py:112`, which the **test** app also runs through `create_app`). Rules, in order:

1. `path.startswith("/api/v1")` → **410 `DEPRECATED_ROUTE`** (legacy version prefix).
2. `resolve_contract_path(path) is None` **and** path is contract-managed → **410**.
3. `path != canonical_path` and not a concrete canonical match and not in `PUBLIC_NON_CANONICAL_API_PATHS` (which is **empty**, `frozenset()`) → **410** (non-canonical alias).
4. `/api/v2/*` requires header `X-API-Version: 2`, else **400 `API_VERSION_REQUIRED`**.

The shared contract (`shared/api_contract.json`) carries **3,475 deprecated aliases** mapping to **1,276 canonical `/api/v2/*` paths**. Example: `/api/competitions → /api/v2/competitions`, `/competitions → /api/v2/competitions`. **Deprecated aliases are therefore actively rejected at runtime** — the directive’s requirement holds.

---

## Frontend source — CLEAN (verified)

- `python tools/audit/check_api_contract_violations.py` → **`No contract violations detected`** (exit 0).
- No `/api/v1` usage and no undeclared endpoints in `frontend/lib`. The generated transport (`gte_api_contract.g.dart`) is the single source and is contract-aligned.

## Backend/frontend tests — `/api/v1` — CLEAN

- `grep /api/v1/ backend/tests frontend/test` → **0 matches**. No legacy-version drift in any test.

---

## The one real drift cluster: competition sibling route tests

A raw grep finds 745 non-v2 `/api/` literals across tests and 167 `/api/competitions` literals — **but most are not drift**: the green competition suite passes those literals **through** the `api_v2_path()` + `api_headers()` helpers in `backend/tests/competitions/api_helpers.py`, which rewrite to `/api/v2/...` and attach `X-API-Version: 2` at call time. Filtering to *raw* client calls that bypass the helper (`client.<verb>("/api/competitions"...)`):

| File | Raw `/api/competitions` call sites | Status (executed) |
|---|---:|---|
| `backend/tests/competitions/test_api_discovery.py` | 17 | ❌ 6 failed (410, then envelope `KeyError: 'id'`) |
| `backend/tests/competitions/test_backend_contract_routes.py` | 4 | ❌ broken (asserts `status_code == 200` on `/api/competitions/.../fixtures`, gets 410) |

These are the **only** two competition test files making raw deprecated-alias calls. Both were verified failing this session.

---

## Categorization

| Severity | Finding | Count | Disposition |
|---|---|---|---|
| **Critical** | none | 0 | — |
| **High** | Competition sibling route tests on deprecated `/api/competitions` alias → 410, masking real v2 discovery/contract coverage; gates the “full competition” verification claim | 2 files | **Fix in N43** — see recipe below. Not a product-money defect; a test-contract gap. |
| **Medium** | Per-endpoint response-envelope inconsistency surfaced while fixing the above: create returns `{success,data:{id}}` (enveloped) while discovery `GET` tests assert a **bare** dict `{"total":0,"items":[]}`. Indicates envelope coverage is not uniform across competition read vs write routes. | — | Confirm intended envelope contract per route; reconcile tests in N43. |
| **Low** | 743 other non-v2 `/api/` literals in tests are **helper-canonicalized** (routed via `api_v2_path`) or address genuinely-canonical non-v2 routes (e.g. `/api/admin/...`, `/api/wallets/...` that have no v2 form). Not drift; cosmetic only. | ~743 | No action — would be churn. |

---

## Fix applied vs. deferred

Per directive (“Fix ONLY safe mechanical canonicalization issues; do not change product behavior”):

- **Mechanical part is proven but insufficient alone.** A localized autouse canonicalizer (rewrite non-v2/non-v1 `/api/` → `/api/v2/` + inject `X-API-Version: 2`) was prototyped in `competitions/conftest.py` and **verified** to flip `POST /api/competitions` from `410 Gone` to `201 Created`. It is safe to green siblings (header injected via `setdefault`; no 410-intent tests exist in that dir).
- **But it does not green the lane** — the two files also carry response-shape assertions (`["id"]` direct indexing, bare-dict equality) that predate the `{success,data}` envelope. Greening them requires per-test envelope reconciliation, which is **test-contract work, not pure alias canonicalization**. To avoid leaving a half-fix in the tree, the prototype was **reverted**; the tree is clean. **No fabricated green.**

### Recipe for N43 (deterministic, low-risk)
1. In each red file, route every `client.<verb>("/api/...")` through `api_v2_path(...)` and pass `headers=api_headers(existing_headers)` (mirror the green sibling pattern already in the same directory).
2. Unwrap enveloped reads with `api_payload(response)` before indexing (`api_payload(resp)["id"]`).
3. For the bare-dict discovery assertions, assert against `api_payload(resp)` rather than `resp.json()`.
4. Re-run both files to green; then run the full `tests/competitions` dir to confirm no sibling regression.

**Bottom line:** runtime alias enforcement is correct and live; frontend source is contract-clean; the only true test drift is two competition sibling files, scoped with an exact, verified fix recipe for N43.
