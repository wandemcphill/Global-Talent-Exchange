# GTEX Production Certification Ledger

**Single cumulative ledger.** Items marked CLOSED are certified and must not be
re-audited from scratch in later passes. Items marked OPEN or DEFERRED carry the
reason and the evidence needed to resolve them.

Every CLOSED entry below was verified against the code on `main` at the stated
commit — not inferred from tests passing.

| Field | Value |
| --- | --- |
| Ledger opened | 2026-08-30 |
| Last updated | 2026-08-31 |
| Baseline commit | `82894885` (main) |
| Backend tests collected | 2832 |

---

## Severity definitions

| Level | Meaning |
| --- | --- |
| **P0** | Direct, unauthorised movement or loss of real funds; total outage. |
| **P1** | Unauthorised mutation of valuable state; integrity break with economic consequence. |
| **P2** | Real reachable defect with bounded blast radius, or a hardening gap. |
| **P3** | Correctness/robustness nit; no economic consequence. |

---

## CLOSED — certified

| # | Area | Finding | Evidence |
| --- | --- | --- | --- |
| C-01 | Withdrawals / money-out | Payout path is correctly hardened. | `request_payout` enforces positive amount, `source_scope` allowlist, balance-inclusive-of-fee check, competition-reward sub-balance check, **user-scoped** idempotency replay (global unique index alone would leak another user's payout), and collapses a replay onto the same ledger reference instead of minting a second hold. Double-entry postings balance. `wallets/service.py:895`. |
| C-02 | Fan Coin withdrawal guard | Fan Coin cannot be withdrawn. | `treasury/service.py:622` hardcodes `unit=LedgerUnit.COIN`; the request schema exposes only `amount_coin`. No path accepts CREDIT. |
| C-03 | GTEX Coin / Fan Coin separation | Fan Coin cannot be converted into GTEX Coin. | `wallets/service.py:769` raises `LedgerError("Fan Coin cannot be converted into GTEX Coin.")`. `convert_wallet_units` calls `quote_conversion` first, so the mutation path inherits the guard. `economy/governor_service.py:484` delegates to the same quote, so the bonus path cannot bypass it. |
| C-04 | Gift economy Fan Coin → Coin | The one legitimate Fan Coin → Coin bridge is conservation-checked and non-self-dealing. | `economy/conversion_service.py`: rejects unless `fee + burn + destination == gross` exactly; rejects `source_user_id == recipient_user_id` (blocks self-laundering); idempotent on both `conversion_key` and `idempotency_key`. Fees come from the DB-resolved economic policy (`split.rule_key`/`policy_version`), **not** caller input, so the rake cannot be zeroed. |
| C-05 | Payment webhooks | Signature verification is fail-closed in production. | `_verify_paystack_webhook` / `_verify_korapay_webhook` raise `ValueError` (→ 401) on missing secret, missing header, or bad HMAC. The dev bypass (`GTE_*_WEBHOOK_SIGNATURE_OPTIONAL`) is hard-disabled by `_signature_optional` → `_is_protected_environment()` for `production/prod/staging/release`. All 9 services in `render.yaml` set `GTE_APP_ENV=production`, and `SIGNATURE_OPTIONAL` is set nowhere in deploy config. Applies to all three webhook entry points (`admin_finance` ×2, `wallets/router.py:1494`). |
| C-06 | Player-share oversell | Share supply cannot be oversold under concurrency. | `legacy_token_service.py:253` takes `SELECT … FOR UPDATE` on the market row *before* the `available = total - circulating` check (:264) and the mutation (:332). Serialised on Postgres. |
| C-07 | Money-surface test suite | Green. | 349 passed / 0 failed across `tests/economy`, `wallets`, `treasury`, `admin_finance`, `admin_godmode`, `gift_engine`, `ultimate_league`, `players` at `82894885`. |
| C-08 | `bf91a6ba` ingestion change | Verified; does not break existing behaviour. | 16 passed across `test_real_player_canonical_mapping_service.py`, `test_footballsquads_canonical_backfill.py`, `test_real_player_import_validation.py`. Premise confirmed correct: `_club_auto_create_is_safe` (`real_player_canonical_mapping_service.py:76-84`) hard-requires a competition with a non-continental country, so the previous `country_id=None` really did block all club auto-creation. See O-01 for the residual issue it introduces. |
| C-09 | Quality Gates on main | Green. | Pre-existing Black violation from `a8d29498` (N61) surfaced when `bf91a6ba` touched the same file; the changed-files gate formats whole files. Fixed in `82894885` (one blank line, no behaviour change). Quality Gates = success. |
| C-10 | `update_match_v2_tactics` | Not a defect despite being unauthenticated. | `live_matches/router.py:1246` unconditionally raises 501 `NOT_IMPLEMENTED`; no state mutation is reachable. |
| C-11 | Club-ops mutations | Properly authorised. | `segments/clubs/segment_club_ops.py` mutations carry decorator `dependencies=[Depends(require_bound_organization_access(OrganizationRole.CLUB, …))]` — role-bound, not merely authenticated. |
| C-12 | Player-lifecycle auth boundary | **Fixed** — see F-01. | Was P1. Now authenticated + regression-pinned. |

---

## FIXED THIS PASS

### F-01 — P1 — Unauthenticated mutation of player contracts and transfers

**Commit:** `2b2c186f`

Every mutation on the player-lifecycle segment router was reachable with **no
credentials at all**. Three independent layers all missed it:

- the router declares no `dependencies`;
- none of the 13 POST handlers took an auth dependency;
- `/api/transfers` and `/api/players` are absent from
  `AuthEnforcementMiddleware.PROTECTED_PATH_PREFIXES` (`auth/middleware.py:10`),
  which is an allowlist, not a denylist.

The module is unconditionally registered (`modules.py:772` →
`app/routes/player_lifecycle.py`, which re-exports the segment router).

**Reproduced** against the real app at `82894885`, no credentials:

```
POST /api/transfers/windows/{id}/bids          -> 422  bid_amount: Field required
POST /api/transfers/windows/{id}/bids/{b}/accept -> 422  contract_ends_on: Field required
POST /api/transfers/windows/{id}/bids/{b}/reject -> 404  Transfer bid ... was not found in window ...
```

The `reject` result is decisive: a **domain** 404 (not a routing 404) proves the
request reached `service.reject_bid()` and executed a database lookup with zero
credentials.

**Impact.** `accept_bid` (`services/player_lifecycle_service.py:1692`) terminates
the selling club's contract and writes a new `PlayerContract` for the buying club
— it moves a tradeable player, an asset with real Coin value. `GET
/api/transfers/windows/{id}/bids` is also public, so window and bid ids are
enumerable: the whole exploit chain needs no account.

**Fix.** Added `_: User = Depends(get_current_user)` to all 13 POST handlers,
matching the codebase's existing convention. GET handlers were left untouched
(changing read visibility is a separate product decision — see O-02).

**Regression coverage.** `backend/tests/players/test_player_lifecycle_auth_boundary.py`
— 13 anonymous cases assert `401 / unauthorized`, 13 authenticated cases assert
the request clears the auth boundary.

---

## OPEN — real, classified, not fixed

### O-01 — P2 — Auto-created leagues inherit the first player's nationality

`bf91a6ba` passes the **player's** nationality as the **competition's** country
(`real_player_ingestion_service.py:576-578`). `_resolve_country_reference`
resolves strictly from `payload.nationality` / `nationality_code`, and
`RealPlayerSeedInput` has **no league-country field at all**.

Consequence: whichever player is ingested first for a league permanently sets
that league's `country_id` (`real_player_canonical_mapping_service.py:557`,
auto-create only — existing seeded competitions are not mutated). Ingesting the
English Premier League starting from a Nigerian player labels the EPL as Nigeria.
That country then feeds `_club_auto_create_is_safe` and league-country display.

**Not fixed deliberately.** Reverting re-breaks club auto-creation (the real bug
`bf91a6ba` fixed), and fixing it properly requires a league→country data source
that does not exist in the payload — that is new data modelling, which the
instruction for this pass explicitly excludes. The same conflation already exists
on the club path (`_resolve_club_reference` passes `payload.nationality` as the
club country), so this extends a pre-existing pattern rather than introducing a
new one.

**Reachability:** `real_player_mapping_auto_create_missing_entities` defaults to
`False` and is set only in `.runtime/genesis.env` (operator backfill), **not** in
`render.yaml`. So the deployed API is unaffected; this manifests during
operator-run backfills.

### O-02 — P2 — Horizontal authorisation on player-lifecycle mutations

F-01 closed *authentication*. It did not add *authorisation*: an authenticated
user can still accept or reject a bid belonging to a club they do not control,
and the bid-list GET remains public. The correct primitive already exists —
`require_bound_organization_access(OrganizationRole.CLUB)`, as used by
`segment_club_ops` — but these routes are keyed by `player_id` / `window_id`, so
the club must be derived from the bid/contract rather than a path parameter.
That is a scoped design change, not a drop-in, and improvising it under time
pressure on the transfer path is exactly the kind of change that should be
reviewed on its own.

### O-03 — P2 — Player-share trade idempotency is opt-in

`idempotency_key` is `default=None` on `PlayerSharePurchaseRequest` /
`PlayerShareSaleRequest` (`players/token_schemas.py:46,77`), whereas withdrawals
deliberately made it **required** ("a withdrawal is an economic submission, so
replay protection is mandatory at the public API boundary").

When a key *is* supplied the mechanism is sound (unique `idempotency_key`
column + `_replay_idempotent_trade`). When it is omitted, the service computes a
state-derived reference `market:…:side:…:before:{circulating}:shares:{n}` but
writes it only to `LedgerTransaction.reference`, which is **indexed, not unique**
(`models/wallet.py:175`). Only `idempotency_key` is unique (:178), and it is
bound solely when an explicit key was supplied (`token_service.py:218`). So a
double-submitted trade without a key has no database-level replay protection.

**The obvious fix is unsafe and was rejected.** Promoting the state-derived
reference into the unique column false-positives on a legitimate
buy → sell → re-buy of the same size: `circulating_shares` returns to its earlier
value, regenerating an identical key and blocking a valid trade. Making the key
required is a breaking API change and belongs in a versioned contract decision.

### O-04 — P2 — Permanently red `Final Platform Certification`

3 golden tests in `frontend/test/ux_refinement/visual_qa_golden_test.dart` fail
on every CI run (`browse_grid_mobile` 1.70%, `browse_grid_desktop` 0.60%,
`master_detail_tablet` 0.93%), with **identical** pixel deltas across four
unrelated backend-only commits (`cc00e677`, `a637f7bd`, `bf91a6ba`, `82894885`).
722 other Flutter tests pass. This masks any genuine future frontend regression.

Two hypotheses remain live and I could **not** discriminate them:

1. *Platform mismatch* — goldens generated on Windows, CI runs `ubuntu-latest`.
   Weakened by the fact that the repo's **other two** golden tests
   (`broadcast_package_screen_golden_test.dart`, `viral_feed_screen_test.dart`)
   pass on the same Linux runner.
2. *Stale goldens* — the committed PNGs predate later layout changes to
   `gtex_player_card.dart` / `gtex_master_detail_scaffold.dart`, all squashed
   into `b3626b48`.

The decisive local experiment (`flutter test` on the golden file, comparing
Windows vs CI) was **blocked by a network outage** — `pub get` could not resolve
`pub.dev`. Deliberately **not** "fixed" by excluding or deleting the tests: that
would manufacture a green check while destroying the signal.

**Recommended resolution:** run a one-off CI job with
`flutter test --update-goldens` on `ubuntu-latest` and commit the result. That
resolves both hypotheses at once and restores the gate.

---

## DEFERRED — needs individual reproduction

Unauthenticated mutation candidates surfaced by a static sweep that accounts for
signature deps, decorator `dependencies=[…]`, and router-level deps. These are
**candidates, not confirmed defects** — each needs the same reproduce-then-classify
treatment F-01 got. Listed highest-risk first.

| Route | Why it matters |
| --- | --- |
| `leagues/router.py:50` `register_league` | Persists a league season registration including `buy_in_tier` (economic). |
| `live_match/router.py:73` `tick_session` | Advances live match session state; needs a check on whether this engine is authoritative. |
| `match_engine/api/router.py:279,293,307,324` `create_match_timeline/summary/render_sync/post_match_analytics` | Write match records. (`create_match_replay` and `simulate_match` are **not** defects — they are public-by-design and pure, guarded by `fairness_guard.validate_public_request`.) |
| `national_team_engine/router.py:288` `auto_build_squad` | Builds squads. |
| `club_social/router.py:130,265,368` `record_*` | Write social / rivalry state. |
| `analytics/router.py:65` `create_frontend_event` | Unauthenticated analytics writes (pollution/spam; low). |
| `live_matches/router.py:1597` `refresh_unity_live_access` | Access-token refresh path. |

**Confirmed legitimately public** (no action): all `auth/router.py` entry points
(register/signup/login/refresh/confirm/recovery); all four webhook endpoints
(signature-verified, C-05); `academy` `preview_*` and `champions_league` `build_*`
(pure computation); `talent` `search`/`compare` and `players` `match_players`
(POST-as-query reads); `integrations/payments` `quote_payment` and
`ultimate_league` `preview_payouts` (quotes/previews).

---

## Not re-audited (already closed in earlier passes)

- PR #82 findings — Ultimate League `NameError` + auth, gift spend-tier
  `source_ledger_unit`, transfer-hub 500→403, competition lifecycle import,
  demo bootstrap import. Merged `cc00e677`.
- `wallet_top_up_verify` sync-vs-async — resolved as **intentionally
  synchronous**; regression coverage added in `a637f7bd`.
- Phase A economic foundation; Phase B threads C/D — all `phase/b-*` branches are
  merged into `main` (0 commits ahead).
