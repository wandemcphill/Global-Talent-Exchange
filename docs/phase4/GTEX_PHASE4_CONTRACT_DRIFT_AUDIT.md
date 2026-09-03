# GTEX Phase 4 — API Contract Drift Audit

**Date:** 2026-09-03
**Measured against:** `origin/main` @ `2abe01fd` (Merge PR #91)
**Rebased onto:** `origin/main` @ `7f7dfdc1` (Merge PR #94)
**Branch:** `phase4/contract-drift-hardening` — merged as PR #96 (`1b138034`)
**Scope:** API contract integrity only. No application architecture, Player Card, router, Home, Market UX, Regen UX, or Club UX changes.

---

## -1. Follow-up — all three items originally left open are now addressed

PR #96 shipped with §5.1 fixed and §5.2/§5.3/§6 documented but open. Three follow-ups closed the rest, all now merged to `main`:

- `phase4/ws-match-collision-fix` (PR #97) fixed §5.2 — not the static ambiguity originally described, but a deterministic runtime bug already failing 5 tests in `backend/tests/api_v1/test_router.py`. Full account in the rewritten §5.2.
- `phase4/get-write-side-effects` (PR #98) fixed the one genuine bug in §6 (creator-earnings double-crediting on repeat feed delivery) and **reversed** §6's own "sweep Class B" recommendation after tracing showed it would have been a regression, not a cleanup. Full account in the rewritten §6.
- `phase4/mutating-routes-auth` (this branch) traced every one of §5.3's 28 flagged handlers into its actual body and call chain. 26 turn out to be false positives — 25 have no database session anywhere in their path (pure computation/preview endpoints, correctly public) and 2 are deliberately anonymous, rate-limited telemetry writes. **One real gap:** `evaluate_contract_decision`/`evaluate_transfer_decision` in `routes/player_agency.py` write to a player's shared persistent agent state with no caller identity at all — fixed by requiring authentication. See the rewritten §5.3 for the full per-handler account.

---

## 0. Status — read this before §1

**The route drift documented in §1–§3 has been absorbed by `main` since this audit was measured.** PR #94 (`7f7dfdc1`, merged mid-audit) ran the full pipeline and regenerated the artifacts, picking up all 27 routes. On current `main`, `shared/api_contract.json` declares them, `ROUTE_MAP.json` reports a consistent `route_count` of 1697, and `check_api_contract_violations.py` is green.

§1–§3 are retained as the **root-cause record**, not as a description of current `main`. They are why the 27 routes went undeclared for two months, and the numbers in them are as measured at `2abe01fd`.

What this PR still delivers, all live against `7f7dfdc1`:

| | |
|---|---|
| **§5.1 — the `/api/v2/admin` middleware gap** | **Fixed.** Still present on `main`. This is now the PR's primary change. |
| **§7 — the regression guard** | **New.** Nothing on `main` prevents the drift recurring; PR #94 absorbed the backlog by luck of timing, not by a gate. |
| **§5.2, §5.3, §6** | Documented, not fixed at merge time. All three fixed since, on separate PRs (#97, #98, and this branch) — see §-1. |
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
5. ~~Resolve the `/api/v2/ws/match/{match_id}` handler collision (§5.2).~~ **Done — see §-1 and §5.2.**
6. Sweep the Class B defensive commits in §6.

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

### 5.2 Three handlers claimed `/api/v2/ws/match/{match_id}` — **FIXED**

At the static-source level, three handlers declared this path:

| Handler | File | Declared as |
|---|---|---|
| `stream_live_match_events` | `realtime/router.py` | `/ws/match/{match_id}` → aliased to v2 |
| `stream_match_commentary` | `api_v1/router.py:512` | `/ws/match/{match_id}` (router prefix bakes in `/api/v2`) |
| `stream_unity_spatial_match` | `live_matches/router.py:1792` | `/api/v2/ws/match/{match_id}` — hardcoded v2 prefix in the decorator |

This was originally written up as a contract-generation ambiguity — "which handler serves the path depends on registration order, it is not determined by the contract." That understated it. It is a **genuine runtime bug**, deterministic and already failing tests.

#### What was actually happening

`register_domain_modules` (`app/core/module.py`) treats a route collision on a path starting with `/api/` as non-fatal: whichever module registers first is kept, and any later module's route at the same `(path, methods)` fingerprint is **silently dropped** — no error, no warning outside DEBUG logs. `live_matches` is eager (registers at app startup); `api_v1` is lazy (registers on first request). Eager always wins, so `live_matches.stream_unity_spatial_match` was the sole route ever bound to `/api/v2/ws/match/{match_id}` — confirmed empirically:

```python
>>> [r for r in app.router.routes if r.path == "/api/v2/ws/match/{match_id}"]
[<APIWebSocketRoute app.live_matches.router.stream_unity_spatial_match>]
```

`api_v1.stream_match_commentary` — declared, imported, unit-testable, reviewable — never ran. And it was the better implementation: it branches on `?format=unity` to serve both plain commentary and the Unity spatial bridge (the *only* codepath either handler has for plain, non-unity commentary), and its unity branch has delivery deduplication (send only on payload change, not unconditionally every 50ms) and metrics recording that `stream_unity_spatial_match` lacked entirely. `_issue_unity_live_access_view` and `_build_active_live_match_view` (`live_matches/router.py`) hand every client `websocket_path=".../api/v2/ws/match/{match_id}?format=unity"` — so this was the client-facing contract, being served by the wrong, worse implementation.

This was independently visible in `backend/tests/api_v1/test_router.py`, whose 5 websocket tests target exactly this path and assume `stream_match_commentary` answers it. Before this fix, **5 of them failed** — e.g. a plain (non-unity) connection got rejected with `"Unity live access token is required."`, because the shadowed handler's own unity-only access gate was answering instead.

#### Fix

Deleted `stream_unity_spatial_match` from `live_matches/router.py` (17 lines: the duplicate `@router.websocket("/api/v2/ws/match/{match_id}")` declaration and its body). It had zero other callers or test references. `_require_unity_live_access_for_websocket` and `build_unity_live_payload_for_app` — defined in the same file — remain in place and in use; `api_v1.router` already imports and calls both from its own, superior implementation.

After the fix, exactly one route is bound to the path, and it is the correct one:

```
routes bound to /api/v2/ws/match/{match_id}: 1
   app.api_v1.router stream_match_commentary
```

5→2 failures in `backend/tests/api_v1/test_router.py`. The remaining 2 are unrelated (a match-liveness timing issue in test setup, `409 Match is not currently live for spectating`) — confirmed pre-existing by reproducing them on clean `origin/main` before this fix.

Regression guard: `backend/tests/app/test_websocket_route_collisions.py` hydrates the real app and asserts exactly one route answers `/api/v2/ws/match/{match_id}`, and that it is `api_v1.router.stream_match_commentary` by module and qualname. Deliberately scoped to this one path rather than a blanket "no router may duplicate another's route" — `with_api_alias` modules legitimately register the same handler two or three times under different prefixes (`/`, `/api/...`, `/api/v2/...`), and `register_versioned_route_aliases` independently derives its own alias from those, frequently duplicating the module's own registration. That produces genuine route-table duplication across large parts of the app — but every one of those duplicates dispatches to the *same* endpoint, so it's wasteful, not wrong, and fixing it is a distinct, much larger change than the two-different-implementations collision this section is about.

#### Residual: the static contract still misattributes the handler

`shared/api_contract.json` records this path's owner as `stream_live_match_events` (`realtime/router.py`) both before and after this fix — unchanged, because `generate_contract_audit.py`'s dedup heuristic (`route_key` + last-write-wins) has no model of `register_domain_modules`'s eager/lazy collision resolution or the `_reserved_versioned_fingerprints` mechanism that stops `realtime`'s alias from ever being created at this path in the first place. At runtime, `realtime.stream_live_match_events` is **not** reachable at `/api/v2/ws/match/{match_id}` — only at the bare `/ws/match/{match_id}` and `/ws/matches/{match_id}`. The static contract's canonical-handler attribution for this path was wrong before this PR and remains wrong after it; only the *runtime* collision (two different implementations competing for the same request) is fixed here. Bringing the generator's model in line with `register_domain_modules` is a distinct piece of work, out of scope for a route-level fix.

### 5.3 Mutating routes without a handler-level auth dependency -- **investigated, one fixed, 26 were false positives**

Of 801 `POST/PUT/PATCH/DELETE` routes, **63** have no auth-looking dependency in their signature. Excluding legitimate unauthenticated intake (login, signup, password reset, recovery, email confirmation, provider webhooks) left **28 distinct handlers**, listed at merge time as a lead list, not confirmed vulnerabilities, with two groups singled out for a closer look: `update_match_v2_tactics` and the six `match_engine` `create_*` handlers.

That closer look is what this fix delivers -- every one of the 28 was traced into its actual body and, where the handler itself showed nothing, into the service methods and `Depends(...)` dependencies it calls, checking for `session.add`/`delete`/`merge`/direct ORM attribute assignment.

#### 25 of 28: no database session anywhere in the call path

`academy/api/router.py`'s 6 `preview_*`/`season_summary` handlers, `champions_league/api/router.py`'s 5 `build_*`/`*_preview` handlers, all 6 `match_engine/api/router.py` handlers (`create_match_replay`, `simulate_match`, `create_match_timeline`, `create_match_summary`, `create_match_render_sync`, `create_post_match_analytics`), `national_team_engine`'s `auto_build_squad`, `real_world_hub`'s `normalize_player`, `integrations/payments`'s `quote_payment`, `ultimate_league`'s `preview_payouts`, and `federations`'s `validate_action` -- **25 handlers in total** -- take a posted payload, compute a result (a bracket, a simulated match, a squad suggestion, a price quote, a compliance check), and return it. None of them accept a `Session`, and tracing one level into their called services confirmed none of the services do either (`match_engine`'s `MatchSimulationService()` takes no session at construction at all). They cannot write to the database. They are `POST` because the input is a body, not because they mutate.

`update_match_v2_tactics` -- the one the original list called "highest concern" -- turned out to be a stub: `raise HTTPException(501, "Live tactical instruction persistence is not mounted.")`, unconditionally, after loading (never writing) match state. It cannot currently mutate anything either.

None of these 25 need or get an auth dependency. Adding one would not close a vulnerability -- there is nothing to protect -- and would just as likely break legitimate anonymous callers of what are, by design, public calculators.

#### 2 of 28: real writes, correctly public, protected by the existing rate limiter

`club_social`'s `record_challenge_share_event` and `record_match_share_event` do write -- `service.session.add(ChallengeShareEvent(...)); service.session.commit()` -- and take no auth dependency, `actor_user_id` hardcoded to `None`. This is deliberate: a share link is meant to be clickable by someone who isn't logged in, and the event needs recording regardless. Requiring auth would break the actual product feature. The residual risk is abuse volume (unbounded anonymous writes), not authorization, and it is already covered by the app-wide `RateLimitMiddleware` (`app/core/rate_limit.py`) that every request passes through. Not fixed here, correctly.

#### 1 of 28: **fixed** -- two handlers that write to shared player state with no caller identity at all

`routes/player_agency.py`'s `evaluate_contract_decision` and `evaluate_transfer_decision` stage a real ORM write with no auth dependency: `PlayerAgencyService.evaluate_contract_decision`/`evaluate_transfer_decision` set `state.contract_stance`, `state.recent_offer_cooldown_until`, `state.next_review_at`, `state.transfer_appetite`, and a cached-decision blob directly on the loaded `state` object, then `self.session.flush()`. That `state` is the player's persistent agent-decision state -- the same one `player_lifecycle_service.py` and `transfer_market/service.py` write to when a real, authenticated club submits an actual offer, since both reuse this exact evaluation engine. `offering_club_id`/`destination_club_id` in the request body are caller-supplied, not derived from an authenticated identity.

One mitigating fact and why it doesn't change the fix: neither handler, nor `PlayerAgencyService`, nor anything else in the call chain calls `.commit()` -- only `.flush()`. `get_session`'s teardown is a bare `session.close()` with no commit, so today these writes roll back at the end of the request and never persist. That is a real, separate bug (the decision cache and cooldown timers this code clearly means to persist across requests currently never do), but it is not a reason to leave the auth gap open: fixing the missing commit as an unrelated piece of future work would silently turn this into a live anonymous-write vulnerability, by someone who has no reason to know this thread exists.

Fixed by requiring `Depends(get_current_user)` on both handlers -- no club-ownership check added (that would mean deciding, without product input, whether "any authenticated user" or "the authenticated user's own club" is the right bar, and the existing codebase is not consistent enough on that point to infer it safely). This closes the anonymous-write path; it does not change who can evaluate what once authenticated, which is exactly the boundary every comparable mutation in this codebase draws (see `test_player_lifecycle_auth_boundary.py`, the direct precedent this fix's test file is modelled on).

The read-only `GET /api/players/{player_id}/agency` snapshot is untouched -- it doesn't write, and doesn't need to.

Regression test: `backend/tests/players/test_player_agency_auth_boundary.py` -- both mutations return 401 with `code: "unauthorized"` for anonymous callers and clear the auth boundary (any non-401) once authenticated; the GET snapshot stays reachable anonymously.

#### On the earlier `120` figure

An earlier pass of this scan reported 120 unauthenticated mutating routes because its pattern missed `get_current_trading_user`; the entire `market/router.py` trade surface (`/buy`, `/sell`, `/offers`, `/trade-intents`) is in fact properly guarded by it, and the `wallets` surface is guarded both by signature and by the middleware's `/api/wallet*` and `/api/v2/wallet*` prefixes. Kept here as the reason this whole finding needed per-route verification rather than aggregate trust -- which is what this fix did.

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
- §5.1, §5.2, §5.3, and §6 are all fixed — §5.1 in this PR, the rest on separate follow-up PRs (#97, #98, and this branch). See §-1.
- Admin surfaces mounted outside an admin prefix (e.g. `/api/competitions/admin`) are still invisible to prefix matching and depend solely on their handler guard.
