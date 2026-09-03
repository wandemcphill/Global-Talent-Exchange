# GTEX Phase 4 — API Contract Drift Audit

**Date:** 2026-09-03
**Measured against:** `origin/main` @ `2abe01fd` (Merge PR #91)
**Rebased onto:** `origin/main` @ `7f7dfdc1` (Merge PR #94)
**Branch:** `phase4/contract-drift-hardening` — merged as PR #96 (`1b138034`)
**Scope:** API contract integrity only. No application architecture, Player Card, router, Home, Market UX, Regen UX, or Club UX changes.

---

## -1. Follow-up — §6 (Class A) fixed on `phase4/get-write-side-effects`

PR #96 (§0–§8 below) shipped with §5.1 fixed and §5.2/§5.3/§6 documented but open. Two follow-ups exist:

- `phase4/ws-match-collision-fix` (PR #97, open) fixes §5.2.
- `phase4/get-write-side-effects` (this branch) fixes the one genuine bug in §6 — see the rewritten §6 for the full account. Investigating it also **reversed §6's own "sweep Class B" recommendation**: what looked like 43 pointless no-op commits turned out to depend on a real, shared write (an auth-session `last_used_at` touch) that a naive per-handler scan couldn't see. Sweeping them, as originally suggested, would have been a regression, not a cleanup.

§5.3 remains open, unowned.

---

## 0. Status — read this before §1

**The route drift documented in §1–§3 has been absorbed by `main` since this audit was measured.** PR #94 (`7f7dfdc1`, merged mid-audit) ran the full pipeline and regenerated the artifacts, picking up all 27 routes. On current `main`, `shared/api_contract.json` declares them, `ROUTE_MAP.json` reports a consistent `route_count` of 1697, and `check_api_contract_violations.py` is green.

§1–§3 are retained as the **root-cause record**, not as a description of current `main`. They are why the 27 routes went undeclared for two months, and the numbers in them are as measured at `2abe01fd`.

What this PR still delivers, all live against `7f7dfdc1`:

| | |
|---|---|
| **§5.1 — the `/api/v2/admin` middleware gap** | **Fixed.** Still present on `main`. This is now the PR's primary change. |
| **§7 — the regression guard** | **New.** Nothing on `main` prevents the drift recurring; PR #94 absorbed the backlog by luck of timing, not by a gate. |
| **§5.2, §5.3, §6** | Documented, not fixed at merge time. §6 (Class A) fixed since, §5.2 fixed on a separate open PR -- see §-1. |
| Residual artifact regeneration | ~40 lines. `main`'s frontend-derived docs are *already* stale again — `gtex_regen_world_api.dart` call sites landed after the last stage-1 run. A live instance of the same pattern, caught by the pipeline here. |

The absorption is itself evidence for §2: PR #94 fixed the drift as a side effect of touching the same generated files, with no gate involved and nothing recording that it happened. The next agent who does not happen to regenerate re-opens it.

---

## 1. Verdict

Measured at `2abe01fd`, the 2,406-line generated diff was **legitimate accumulated route drift**, not generator noise. (Since absorbed by `main` — see §0.)

Three independent checks establish this:

| Check | Result |
|---|---|
| Determinism — pipeline run twice, outputs byte-compared | All 6 artifacts **identical**. No ordering/timestamp noise. |
| `shared/api_contract.json` delta | **+27 routes, 0 removed, 0 modified.** Purely additive. |
| `docs/ROUTE_MAP.json` delta | **+28 route rows, 0 removed.** The 70 "modified" rows change `request_shape.parameters` only. |

The drift is real backend routes that exist in source and were never registered in the contract. Nothing is being deleted or redefined, so committing the regenerated artifacts carries no removal risk.

The 70 `request_shape` modifications are also legitimate: every one is a handler signature that gained a dependency, overwhelmingly an **auth guard** added during Phase B hardening. Examples:

```
GET /api/clubs/{club_id}/identity/metrics   ['club_id','service'] → ['club_id','current_user','service']
GET /api/competitions/{competition_id}/invites  +['request','actor']
GET /admin/economy/burn-events              +['_']            (admin guard, result discarded)
```

---

## 2. Root cause

### 2.1 Primary: CI never runs stage 1 of the pipeline

`.github/workflows/quality-gates.yml` runs only two of the three steps:

```yaml
- run: python tools/audit/generate_api_contract_bindings.py   # stage 2
- run: python tools/audit/check_api_contract_violations.py    # gate
```

`tools/audit/generate_contract_audit.py` — **stage 1, the only stage that reads `backend/app/**/*.py`** — is never executed in CI.

The consequence is structural:

```
backend/app/**.py  ──(stage 1, NEVER RUNS IN CI)──▶  docs/ROUTE_MAP.json
                                                            │
                                     (stage 2, runs in CI)  ▼
                                                   shared/api_contract.json
                                                            │
                                                    (gate)  ▼
                                              check_api_contract_violations.py
```

CI regenerates the contract from a **committed, stale** `ROUTE_MAP.json`. Backend source is never consulted. A new backend route is therefore invisible to every gate in the pipeline until someone regenerates by hand.

### 2.2 Secondary: the gate only inspects the frontend

`check_api_contract_violations.py` walks `frontend/lib/**/*.dart` and flags string literals that do not resolve against the contract. It never enumerates backend routes. A backend route is only ever noticed when a Dart file happens to call it.

This is why the gate reported **1** violation while **27** routes were undeclared: 26 of the 27 had no Dart consumer yet. The gate measures frontend compliance, not contract completeness.

### 2.3 The drift window

`shared/api_contract.json` was last regenerated on **2026-07-02** (`2310e987`). Four feature commits have landed backend routes since:

| Commit | Date | Contributed |
|---|---|---|
| `6846d579` Add admin player editor | 2026-07-24 | 2 routes (`/admin/players/{id}`) |
| `1329853f` phase B: talent discovery foundation | 2026-08-23 | 24 routes (`/talent/*`, `/admin/talent/*`) |
| `cc00e677` Phase B runtime hardening (#82) | — | signature/auth changes |
| `fbc112ce` GTEX Phase 4E performance value economy | 2026-09-03 | 1 route (`/players/{id}/form`) |

**Phase 4 is not the cause.** 26 of the 27 undeclared routes predate Phase 4 by weeks; Phase 4E contributed exactly one. The drift is a two-month accumulation that Phase 4E merely made visible by being the first to add a route with a Dart caller.

### 2.4 Generated artifacts were hand-edited

`2310e987` edited `docs/ROUTE_MAP.json` by hand to inject `POST /api/kyc/documents`, because a prior hand-edit of `shared/api_contract.json` had been overwritten by CI's stage-2 regeneration. The commit message states this openly.

The tell is still in the file on `main`: `route_count: 1667` against 1668 actual route entries. The counter was not updated because a generator did not produce the file.

This hand-edit is now **self-healing** — stage 1 finds the route in `backend/app/treasury/router.py:124` and emits it from source. The regeneration keeps it. But the episode shows `ROUTE_MAP.json` has been treated as a hand-maintained source file even though it is generated output, which is exactly the failure mode a drift audit must close.

---

## 3. Generated files

The table below is the regeneration **as measured at `2abe01fd`**. PR #94 has since committed an equivalent regeneration to `main`, so this PR no longer carries most of it — what remains after the rebase is ~40 lines in the frontend-derived artifacts (see §0). The breakdown is kept because it is the evidence for the §1 verdict.

All produced by the sanctioned pipeline. **None were hand-edited.**

```bash
python tools/audit/generate_contract_audit.py       # ~3 min: scans backend/app + frontend/lib
python tools/audit/generate_api_contract_bindings.py
```

| File | +/− | Nature |
|---|---|---|
| `docs/ROUTE_MAP.json` | +981 / −38 | +28 routes, 70 `request_shape` updates, `route_count` 1667→1696 |
| `shared/api_contract.json` | +432 / −0 | +27 routes; `canonical_paths` 1399→1419; `deprecated_aliases` 4077→4138 |
| `frontend/lib/data/generated/gte_api_contract.g.dart` | +160 / −0 | Dart mirror of the above |
| `docs/FINAL_API_SCHEMA.json` | +320 / −6 | derived |
| `docs/FRONTEND_API_MAP.json` | +436 / −172 | derived from the frontend scan |
| `docs/DEPRECATION_MAP.json` | +12 / −18 | derived from the frontend scan |
| `docs/WEB_MOBILE_DIFF.md` | +26 / −2 | derived |
| `docs/MISMATCH_REPORT.md` | +22 / −22 | truncation-list shift |
| `docs/ROUTE_CLASSIFICATION.md` | +14 / −14 | counters + new talent routes |
| `docs/PRE_DELETION_VALIDATION.md` | +2 / −2 | counters (blocking mismatches 1009→1056) |
| `docs/ENV_AUDIT.md` | +1 / −1 | counter (277→304) |
| **Total** | **+2406 / −275** | |

**On the 275 deletions.** None is a removed route. They fall into two buckets: counter lines that moved (`route_count`, the `... and N more` truncation markers), and — for `FRONTEND_API_MAP.json` and `DEPRECATION_MAP.json` — *consumer* entries. Those two files are derived from the **frontend** scan and track which Dart file calls which path, so a deletion means a call site changed or was removed since 2026-07-02, e.g. `transfer_provider.dart` no longer referencing `/api/v2/transfer-market/listings`. Route inventory itself is strictly additive in every artifact.

### The 27 newly-declared routes

`backend/app/talent/router.py` (24) — Phase B talent discovery:

```
GET    /api/v2/talent/search                    POST   /api/v2/talent/search
POST   /api/v2/talent/compare                   GET    /api/v2/talent/{player_id}
GET    /api/v2/talent/{player_id}/ranking       GET    /api/v2/talent/{player_id}/signals
GET    /api/v2/talent/shortlists                POST   /api/v2/talent/shortlists
GET    /api/v2/talent/shortlists/{id}           PATCH  /api/v2/talent/shortlists/{id}
DELETE /api/v2/talent/shortlists/{id}           POST   /api/v2/talent/shortlists/{id}/entries
PATCH  /api/v2/talent/shortlists/{id}/entries/{entry_id}
DELETE /api/v2/talent/shortlists/{id}/entries/{entry_id}
GET    /api/v2/admin/talent/{player_id}         POST   /api/v2/admin/talent/{player_id}/correction
POST   /api/v2/admin/talent/{player_id}/feature POST   /api/v2/admin/talent/{player_id}/moderation
GET    /api/v2/admin/talent/{player_id}/moderation-log
POST   /api/v2/admin/talent/{player_id}/recompute
POST   /api/v2/admin/talent/{player_id}/sync
GET    /api/v2/admin/talent/{player_id}/verification
POST   /api/v2/admin/talent/{player_id}/verification
POST   /api/v2/admin/talent/{player_id}/visibility
```

`backend/app/admin_players/router.py` (2): `GET`, `PATCH /api/v2/admin/players/{player_id}`
`backend/app/players/router.py` (1): `GET /api/v2/players/{player_id}/form` *(Phase 4E)*

### Why the undeclared route was a live production bug, not a bookkeeping gap

`config.uriFor` routes every Dart request through `gteCanonicalApiPath`, which **raises `StateError` for any path absent from the contract**. `_sendPublicGet` catches broadly and re-emits `GteApiException(network, "Unable to reach the backend")`.

`GET /players/{id}/form` was undeclared, so the Phase 4E matchday form card could never have loaded in production — it would have shown its empty state for every player, permanently, while reporting a network fault. Widget tests feed the model directly and never touch the client, and a runtime contract lookup is invisible to `flutter analyze`, so nothing caught it.

**An undeclared route is a runtime failure, not a lint warning.** That is the severity this audit's regression guard is calibrated to.

---

## 4. Required changes

Implemented in this PR:

1. **Regenerate all contract artifacts from source** via the sanctioned pipeline. At `2abe01fd` this alone took `check_api_contract_violations.py` from 1 violation to 0. PR #94 has since done the equivalent on `main`; after the rebase this PR carries only the ~40-line residual (§0).
2. **Add `backend/tests/app/test_api_contract_route_declarations.py`** — three guards, described in §7. **This is now the load-bearing part of item 1:** regeneration fixed the backlog once, the guard is what stops it returning.
3. **Close the `/api/v2/admin` middleware gap** — §5.1. Still present on `main`; the primary change in this PR.

Recommended but **deliberately not done here** (each is owned elsewhere; see §8):

4. Add `generate_contract_audit.py` to `quality-gates.yml`, or better, leave CI as-is and rely on the new test. Adding stage 1 to CI would make the pipeline *silently self-heal* — it would regenerate `ROUTE_MAP.json` in the runner, never commit it, and never fail. A test that **fails loudly** is the correct gate; a regeneration step would mask the drift it is meant to catch.
5. Resolve the `/api/v2/ws/match/{match_id}` handler collision (§5.2).
6. ~~Sweep the Class B defensive commits in §6.~~ **Reversed, not done -- see §-1 and the rewritten §6.** Tracing the shared auth dependency chain found Class B's commits are not no-ops; sweeping them would have broken auth-session touch persistence on read-only traffic.

---

## 5. Unsafe routes discovered

Scanned all 1,676 handler-routes in `backend/app` by AST, checking handler signatures, decorators, and router-level `dependencies=`.

**Headline: only 4 of 194 admin-ish routes lack an auth dependency, and 3 of those are payment webhooks that authenticate by provider signature.** The per-route guard discipline is good. The problems are in the layer above it.

### 5.1 All 321 canonical `/api/v2/admin*` paths bypassed `AuthEnforcementMiddleware` — **FIXED**

`backend/app/auth/middleware.py` enforces auth against a **hardcoded prefix list** that is entirely disconnected from the contract:

```python
PROTECTED_PATH_PREFIXES = (
    "/api/admin",        # ← no "/api/v2/admin" counterpart
    "/api/profile",  "/api/v2/profile",
    "/api/session",  "/api/v2/session",
    "/api/wallet",   "/api/v2/wallet",
    ...
)
```

`v2` variants were added for `profile`, `session`, and `wallet` — **but not for `admin`**. Meanwhile `app/core/api_contract.py::register_versioned_route_aliases` registers a live `/api/v2/...` alias for every route. So for all 321 admin paths, the legacy `/api/admin/...` form is guarded and the **canonical** `/api/v2/admin/...` form is not.

For 317 of them this is only a lost layer of defence-in-depth — the handler still holds `Depends(get_current_admin)`.

**One route has no other guard:**

| Route | Handler | Exposure |
|---|---|---|
| `GET /api/v2/admin/access/permissions` | `list_permission_catalog` (`admin_access/router.py:56`) | Takes no parameters at all — no session, no user, no guard. Reachable unauthenticated via the canonical v2 path. Discloses the full admin permission and capability catalog. |

Severity is limited (it leaks a permission-name catalog, not data or access), but it is an unauthenticated admin endpoint and the middleware gap that exposes it is systemic.

**Root cause is the same as the contract drift**: a second, hand-maintained list of routes that nothing reconciles against the generated contract.

#### Fix

Confirmed live before changing anything, against the real app:

```
401  GET /api/admin/access/permissions
200  GET /api/v2/admin/access/permissions     ← full permission catalogue, no credentials
```

The prefix list is no longer hand-maintained. Each entry is now declared once, in the form a router actually mounts, and its versioned alias is **derived** with `build_versioned_path` — the same function `register_versioned_route_aliases` uses to create the alias. The two cannot disagree again:

```python
PROTECTED_PATH_PREFIXES = tuple(sorted(_with_versioned_aliases(_PROTECTED_PATH_PREFIX_SOURCES)))
```

The derived set is a strict superset of the old hand-written one. Nothing lost; `/api/v2/admin`, `/api/v2/internal`, `/api/v2/users/me`, and `/api/v2/policies/me` gained. `/api/v2/policies/me` and `/api/v2/users/me` were the same latent bug as admin, not yet exploited.

After the fix, the same probe returns `401` on both paths, and an authenticated admin still gets `200`.

Tests:

- `test_admin_versioned_auth_boundary.py` — drives the real app: anonymous callers get 401 on both the legacy and versioned form of three admin routes, the permission catalogue is not readable anonymously, **and an authenticated admin still reaches it**. That last one matters: tightening the prefix list until everything 401s would otherwise look like a passing security fix while breaking every admin screen.
- `test_auth_middleware.py` — adds admin path coverage plus `test_every_protected_prefix_also_protects_its_versioned_alias`, which guards the *class* of bug: adding a prefix without its v2 alias is exactly how this happened.

Not fixed, and out of scope here: prefix matching cannot cover admin surfaces mounted outside an admin prefix, e.g. `/api/competitions/admin`. Those rely entirely on their handler guard.

### 5.2 Three handlers claim `/api/v2/ws/match/{match_id}`

| Handler | File | Declared as |
|---|---|---|
| `stream_live_match_events` | `realtime/router.py` | `/ws/match/{match_id}` → aliased to v2 — **wins in the contract** |
| `stream_match_commentary` | `api_v1/router.py:512` | `/ws/match/{match_id}` |
| `stream_unity_spatial_match` | `live_matches/router.py:1792` | `/api/v2/ws/match/{match_id}` — **hardcoded v2 prefix in the decorator** |

The contract's `route_key` collapses all three into one entry; only `stream_live_match_events` survives. This is why 28 `ROUTE_MAP` rows produce 27 contract entries, and why `ROUTE_CLASSIFICATION.md` gains a "shadowed" line in this regeneration.

`live_matches/router.py` hardcoding `/api/v2/` in a `@router.websocket` decorator bypasses the alias machinery entirely and is the direct cause of the collision. Which handler actually serves the path depends on router registration order — it is not determined by the contract.

Not fixed here: this is live match routing, outside this PR's scope.

### 5.3 Mutating routes without a handler-level auth dependency

Of 801 `POST/PUT/PATCH/DELETE` routes, **63** have no auth-looking dependency in their signature. Excluding legitimate unauthenticated intake (login, signup, password reset, recovery, email confirmation, provider webhooks) leaves **28 distinct handlers**:

| Group | Count | Assessment |
|---|---|---|
| `academy/api/router.py` — `preview_*`, `season_summary` | 6 | Stateless calculators. `POST` used for a request body, not to write. Low risk. |
| `champions_league/api/router.py` — `build_*`, `*_preview` | 5 | Same pattern: bracket/table computation from a posted payload. |
| `match_engine/api/router.py` — `create_match_replay`, `simulate_match`, `create_match_timeline`, `create_match_summary`, `create_match_render_sync`, `create_post_match_analytics` | 6 | Named `create_*`; worth confirming these are pure renderers and not persisting match records. |
| `live_matches/router.py:1247` — `update_match_v2_tactics` | 1 | **Highest concern here.** Mutates in-flight match tactics; not behind a protected middleware prefix. |
| `national_team_engine` — `auto_build_squad` | 1 | Builds a squad for a competition entry. |
| `club_social` — `record_challenge_share_event`, `record_match_share_event` | 2 | Share-link telemetry; unauthenticated by design, but unbounded write paths. |
| Others (`federations`, `integrations/payments/quote`, `real_world_hub/normalize`, `player_agency` ×2, `sponsorship_engine`, `ultimate_league` payout preview) | 7 | Mostly preview/validation endpoints. |

**Caveats — this list is a lead list, not a finding of confirmed vulnerabilities.** The scan reads handler signatures, decorators, and router-level `dependencies=`. It cannot see auth applied through `LazyModuleMiddleware`, module-mount configuration in `modules.py`, or service-layer checks.

An earlier pass of this scan reported 120 routes because its pattern missed `get_current_trading_user`; the entire `market/router.py` trade surface (`/buy`, `/sell`, `/offers`, `/trade-intents`) is in fact properly guarded by `Depends(get_current_trading_user)`. The `wallets` surface is guarded both by signature and by the middleware's `/api/wallet*` and `/api/v2/wallet*` prefixes. Recorded here because it is the reason the number should be verified per-route rather than trusted in aggregate.

`update_match_v2_tactics` and the six `match_engine` `create_*` handlers are the two groups worth a security-owned look. Neither is fixed here.

## 6. GET endpoints with write side effects -- one fixed, one earlier recommendation reversed

AST-scanned every handler whose only HTTP method is `GET` for transaction writes. **51 GET handlers commit.** Splitting by whether an identifiable state-changing call precedes the commit:

### Class A -- GET performs a real write (8)

| Canonical path | Mutation |
|---|---|
| `GET /api/v2/players/{player_id}/shares/market` | `get_or_create_market_view` -- creates a share market row |
| `GET /api/v2/notifications/preferences` | `get_or_create_preferences` |
| `GET /api/v2/real-world/settings/me` | `get_or_create_settings` |
| `GET /api/v2/clubs/{club_id}/identity/metrics` | `refresh_identity_metrics_for_actor` |
| `GET /api/v2/fast-cups/{cup_id}/result-summary` | `settle_result_summary` -- settles a result |
| `GET /api/v2/feed/for-you` | `record_delivery` -- **FIXED, see below** |
| `GET /api/v2/feed/following` | `record_delivery` -- **FIXED, see below** |
| `GET /api/v2/feed/for-you/refresh` | `record_refresh_delivery`, `refresh_for_you` -- **FIXED, see below** |

Six of the eight are lazy-materialisation patterns (`get_or_create_*`, `refresh_identity_metrics_for_actor`) or a settlement handler with its own idempotency key (`settle_result_summary` -- traced: `_settle_reward` looks up an existing `FastCupPayout` by `idempotency_key` before writing, and it's the only call site anywhere in the codebase, i.e. the deliberate settlement trigger, not an accidental one). All six are safe against retries and confirmed intentional-by-design. Not fixed, not needing a fix.

#### Fixed: creator-earnings double-crediting on every repeat feed delivery

The other two write paths -- `record_delivery` (used by both `/feed/for-you` and `/feed/following`) and `record_refresh_delivery` -- funnel into `PersonalizedFeedRankingService._record_clip_delivery`, which calls `creator_earnings_service.track_impression(reference_key=f"personalized-feed:{feed_source}:{user_id}:{slot_index}:{clip.clip_id}:{delivered_at.isoformat()}")`.

`_record_event` (the method behind `track_impression`) already implements its own idempotency guard -- it looks up an existing `ClipEarningsLog` by `reference_key` and returns early if found -- but `delivered_at.isoformat()` is a fresh wall-clock timestamp on *every call*, so the guard could never fire: every repeat delivery of the same clip to the same user generated a distinct key and credited the creator again.

This wasn't a hypothetical: `record_delivery` runs unconditionally on every GET to `/feed/for-you` and `/feed/following`, **including a plain, non-`refresh` request that serves the exact same cached items again** (`get_following`'s `_build_response` sets `cache_hit=True` and returns the cached top-N without recomputing anything). A page reload, a retried request, or a proxy prefetch of either endpoint re-credited the creator on every hit.

Fix: bucket `delivered_at` to the minute before building the reference key (`backend/app/viral/personalized_feed_service.py::_record_clip_delivery`). Same-instant repeats -- retries, double-clicks, prefetch, a cache-hit response -- collapse into one credited impression; a genuinely later re-view (a different minute) still counts. This makes the dedup guard the code already tries to run actually work, rather than inventing new crediting policy -- no product decision about *how often* a re-view should count was made here, only that duplicate-instant deliveries of the same clip shouldn't double-pay.

Regression test: `backend/tests/viral/test_personalized_feed_service.py::test_personalized_feed_repeat_delivery_within_a_minute_does_not_double_credit` -- two `record_delivery` calls 47 seconds apart, same clip, same user; asserts `wallet.total_impressions == 1` and one `ClipEarningsLog` row, not two.

### Class B -- GET commits with no identifiable mutation in the handler body (43)

The original framing of this class -- "no identifiable mutation... the commit is a no-op on a read-only transaction... sweep Class B to drop the defensive commits" -- was wrong, and fixing this item is what surfaced why.

Tracing beyond the handler body (into every called service method, every `Depends(...)` dependency, and the shared auth chain those dependencies run through) found that **every one of these 43 is reachable from a real, if intermittent, ORM write**, not from the handler's own logic but from the auth machinery every authenticated route depends on:

```
# backend/app/auth/dependencies.py::_resolve_authenticated_user -- runs on every
# Depends(get_current_user) call, i.e. on nearly every authenticated route in the app
if _should_touch_auth_session(auth_session):
    auth_session.last_used_at = _utcnow()   # staged ORM write, needs a commit to persist
```

`_should_touch_auth_session` throttles this to once per 60 seconds per session -- so it is not on *every* request, but it is a genuine, expected write on most of them, and it depends entirely on **some** commit happening in the request to persist. For a GET handler with no business-logic write of its own, that `session.commit()` at the end of the handler is not defensive dead code -- it is the *only* thing that persists the session's `last_used_at` touch. Sweeping it, as originally recommended, would have silently broken "last active" tracking for any user who only ever reads (browses leaderboards, rankings, news, their own notification preferences) without hitting a mutating endpoint -- a real, if minor, regression, introduced in the name of removing a no-op that turned out not to be one.

Four of the 43 (`segment_clubs.py`'s `list_scouting_intelligence_*` / `get_scouting_intelligence_*`) have a second, separate real write, also invisible at the handler level: `_require_owned_club`/`_require_scouting_club_access` call `AccessControlService.require_club_access`, which -- for a legacy club owner with no `OrganizationMembership` row yet -- calls `ensure_club_organization`, which does `session.add(Organization(...)); session.flush()`. Rare (first access by a legacy-owned club), but real, and also depends on the handler's commit to persist.

**Nothing in Class B is touched here.** The audit's own hedge -- "a few may commit writes made inside a service call that this scan could not attribute" -- undersold it: not a few, all of them, via a dependency the original AST scan (and my first attempt at fixing this) never traced into. The corrected recommendation: **leave Class B exactly as it is.** If a future pass wants to make GETs in this app provably side-effect-free, the auth-session touch needs its own commit boundary independent of the handler's -- a real, if small, architectural change, and out of scope here.

---

## 7. The regression guard

`backend/tests/app/test_api_contract_route_declarations.py`. It imports the audit tools by path rather than reimplementing them, so the test can never disagree with the generator about what a route is or how a canonical path is derived.

| Test | Catches | Cost |
|---|---|---|
| `test_every_backend_route_is_declared_in_the_api_contract` | A backend router exposing a route the contract does not declare — **the exact drift this audit found**. Scans `backend/app` from source rather than trusting `ROUTE_MAP.json`, because a stale `ROUTE_MAP.json` is itself the drift being guarded against. | ~31 s |
| `test_generated_contract_artifacts_match_their_source` | `shared/api_contract.json` or `gte_api_contract.g.dart` hand-edited or left stale relative to `ROUTE_MAP.json`. | <1 s |
| `test_route_map_route_count_matches_its_routes` | `ROUTE_MAP.json` hand-edited — the cheapest possible tell, and precisely what `2310e987` left behind. | <1 s |

Failure messages name the offending routes and print the exact two-command pipeline to regenerate.

**Verified against the pre-fix state.** Reverting the artifacts to `2abe01fd` and re-running:

```
FAILED test_every_backend_route_is_declared_in_the_api_contract   (27 routes listed)
FAILED test_route_map_route_count_matches_its_routes              (1667 != 1668)
PASSED test_generated_contract_artifacts_match_their_source
```

The third correctly passes on that stale state: the stale contract *was* self-consistent with the stale `ROUTE_MAP.json`. The three tests cover genuinely distinct failure modes, and test 1 is the one that closes the hole.

All 3 pass on the rebased branch (`7f7dfdc1` + this PR) in 24 s.

Note what this means now that PR #94 has absorbed the backlog: **test 1 would have failed on `main` for two months and does not fail today only because someone happened to regenerate.** The guard is the whole point of the PR — the regeneration was the symptom.

---

## 8. Recommended ownership for future contract changes

### The rule

> `docs/ROUTE_MAP.json`, `shared/api_contract.json`, `docs/FINAL_API_SCHEMA.json`, `docs/DEPRECATION_MAP.json`, `docs/FRONTEND_API_MAP.json`, and `frontend/lib/data/generated/gte_api_contract.g.dart` are **generated artifacts**. They are never hand-edited. The only way to change them is:
>
> ```bash
> python tools/audit/generate_contract_audit.py
> python tools/audit/generate_api_contract_bindings.py
> ```
>
> To add a route to the contract, **add the route to a backend router.** The contract follows source; source never follows the contract.

`2310e987` violated this in good faith and the violation survived two months. The `route_count` guard now makes that specific violation fail in CI.

### Ownership model

| Change | Owner | Obligation |
|---|---|---|
| Adding/changing a backend route | The feature agent | Run the pipeline in the same PR. The new test fails otherwise. |
| Adding a Dart call to an API | The feature agent | Contract must already declare the path, or `gteCanonicalApiPath` throws at runtime. |
| Editing a generated artifact | **Nobody.** | Regenerate instead. |
| `AuthEnforcementMiddleware` prefix list | Security owner | Reconcile against `canonical_paths` — see §5.1. |
| Pipeline/generator changes | Contract integrity owner | Must keep output deterministic; the guard depends on it. |

### For 4B/4F, which add API consumers

1. **Backend route first, pipeline second, Dart call third.** A Dart call to an undeclared path is a runtime `StateError`, not a compile error — `flutter analyze` will not save you.
2. **Regenerate in the same PR as the route.** The contract diff belongs with the change that caused it. Batched regenerations are how a 2,400-line diff accumulates.
3. **Expect a large diff the first time only.** This PR absorbs the two-month backlog. Post-baseline, a single new route should produce roughly 30 lines across the artifacts. **A regeneration diff much larger than the routes you added means someone before you skipped step 2 — stop and investigate rather than committing it.**
4. **Never hand-edit to make the gate green.** If `check_api_contract_violations.py` flags your endpoint, the route is missing from the backend or the pipeline was not run. Both are fixed at the source.

### Residual risk after this PR

- CI still does not run stage 1; the new test is the only thing consulting backend source. If the test is skipped, marked xfail, or its 31-second scan is trimmed for speed, the drift returns silently. **Do not weaken it without replacing the coverage.**
- §5.3 is documented, not fixed. It needs an owner outside this PR's scope. §5.1 and §6 (Class A) are fixed here; §5.2 is fixed on a separate open PR (#97) -- see §-1.
- Admin surfaces mounted outside an admin prefix (e.g. `/api/competitions/admin`) are still invisible to prefix matching and depend solely on their handler guard.
