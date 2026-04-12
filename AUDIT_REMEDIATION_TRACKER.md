# Audit Remediation Tracker

This tracker is the current-workspace execution board for the combined backend/frontend audit work.

It is based on verified code in this checkout, not the older audit snapshot. Stale findings are tracked in Phase 0 and should not be re-opened unless the code changes again.

## Status Legend

- `PENDING`: not started
- `IN_PROGRESS`: actively being verified, designed, or implemented
- `BLOCKED`: cannot proceed until a dependency is complete
- `DONE`: implemented and accepted

## Current Phase

- `A4 Placeholder, Fixture, and Config Truthfulness`

## Global Done Definition

- No user-visible feature is stubbed, placeholder-success, or silently fixture-backed without being labeled as such.
- No production state depends on process memory where persistence is required.
- No visible route lands on a placeholder wall.
- No backend module remains in implied-live status without an explicit ship, hide, or deprecate decision.
- CI covers the regression classes surfaced by the audit.

## Phase A0: Contract Re-Baseline

Phase acceptance criteria:
- A canonical backend-to-frontend matrix exists for this checkout.
- Every audit finding is marked `confirmed`, `stale`, or `reframed`.
- Every feature surface is classified as `live`, `read-only`, `hidden`, `fixture-backed`, `stubbed`, or `dead`.

| Task ID | Description | Owner/System | Dependency | Acceptance Test | Status |
|---|---|---|---|---|---|
| A0-001 | Inventory backend feature modules, routers, and deployment-critical subsystems. | Backend platform | None | Verified list of routers/modules exists with current route prefixes and feature owners. | DONE |
| A0-002 | Inventory frontend API clients, route registry, visible nav, hidden routes, and blocked screens. | Frontend shell | None | Verified list exists for visible, deep-linked, hidden, and blocked routes. | DONE |
| A0-003 | Build the API contract matrix for request/response fields and route names across wallet, club identity, competitions, replay, admin, and social surfaces. | Backend + frontend contract | A0-001, A0-002 | Matrix shows matched, mismatched, and stale-contract claims with file evidence. | DONE |
| A0-004 | Close stale audit claims already disproved in this checkout. | Audit triage | A0-001, A0-002, A0-003 | Stale items are recorded with evidence so they are not treated as open defects again. | DONE |
| A0-005 | Publish the canonical current-state matrix and use it as the source of truth for later phases. | Project-level | A0-001, A0-002, A0-003, A0-004 | One document exists and is referenced by later phases. | DONE |

## Phase A1: Payments and Financial Truthfulness

Phase acceptance criteria:
- Wallet discovery never presents a non-functional payment rail as usable.
- Mutable admin-finance runtime state is no longer tracked in source control.
- Fraud-critical payment paths are validated and tested.

| Task ID | Description | Owner/System | Dependency | Acceptance Test | Status |
|---|---|---|---|---|---|
| A1-001 | Remove or hard-disable stub wallet providers from backend entry points and payment-method discovery. | Backend wallets | A0-005 | Purchase-order/webhook entry points reject stub rails, and payment-method discovery no longer presents fake card-wallet rails as usable. | DONE |
| A1-002 | Add explicit provider availability metadata for non-live or region-gated rails. | Backend wallets + frontend wallet UI | A1-001 | Frontend can render `unavailable`, `coming_soon`, or equivalent state without pretending the rail is live. | DONE |
| A1-003 | Verify active webhook fraud protection and add missing fraud-path regression coverage. | Backend payments | A0-005 | Invalid webhook signature tests fail closed for every active provider. | DONE |
| A1-004 | Remove committed admin finance control files and audit logs from source control. | Backend admin-finance + repo hygiene | A0-005 | Mutable finance control files and audit logs are loaded externally and not tracked in git. | DONE |
| A1-005 | Align frontend wallet/payment UX with actual live rails and failure states. | Frontend wallet UI | A1-001, A1-002 | No payment UI path lets a user start a stub rail flow. | DONE |

## Phase A2: Schema, Startup, and Deployment Safety

Phase acceptance criteria:
- Schema drift fails fast.
- Alembic is the only schema evolution path.
- Runtime dependencies and degradation are explicit.

| Task ID | Description | Owner/System | Dependency | Acceptance Test | Status |
|---|---|---|---|---|---|
| A2-001 | Remove startup fallback that repairs schema via `metadata.create_all()`. | Backend startup | A0-005 | Startup fails on schema mismatch instead of mutating the schema. | DONE |
| A2-002 | Enforce Alembic-only schema evolution in deployment and local startup flows. | Backend DB + ops | A2-001 | A fresh deploy and an upgrade both run through Alembic only. | DONE |
| A2-003 | Add migration verification to CI. | CI + backend DB | A2-002 | CI fails when models and migrations drift or migration head is invalid. | DONE |
| A2-004 | Pin one supported Python runtime and clean version drift from build/deploy assumptions. | Runtime + CI | A0-005 | Docker, local docs, and CI all target the same Python version. | DONE |
| A2-005 | Expose Kafka/Redis/degraded-mode readiness explicitly in diagnostics. | Backend backbone + health | A0-005 | Health output shows dependency state and degraded mode rather than silently idling. | DONE |

## Phase A3: Durable State Conversion

Phase acceptance criteria:
- Creator/referral/runtime state survives restart and scale-out.
- Live flows no longer depend on app-scoped process memory.

| Task ID | Description | Owner/System | Dependency | Acceptance Test | Status |
|---|---|---|---|---|---|
| A3-001 | Replace in-memory creator profile service with DB-backed repository usage. | Backend creator services | A0-005, A2-002 | Create profile, restart app, and read profile successfully. | DONE |
| A3-002 | Replace in-memory referral attribution service with DB-backed repository usage. | Backend referral services | A0-005, A2-002 | Attribution survives restart and is consistent across multiple app instances. | DONE |
| A3-003 | Replace in-memory creator-competition link service with DB-backed repository usage. | Backend creator services | A0-005, A2-002 | Competition links survive restart and scale-out. | DONE |
| A3-004 | Remove or isolate misleading production-path storage abstractions. | Backend + frontend storage | A0-005 | No production storage class name implies durability while using in-memory state. | DONE |
| A3-005 | Add restart and horizontal-scale regression coverage for durable services. | Tests | A3-001, A3-002, A3-003 | Automated tests prove durable behavior after restart and across instances. | DONE |

## Phase A4: Placeholder, Fixture, and Config Truthfulness

Phase acceptance criteria:
- Placeholder outputs are not treated as live success.
- Live production paths fail loudly instead of silently falling back.
- Release config cannot silently point to localhost.

| Task ID | Description | Owner/System | Dependency | Acceptance Test | Status |
|---|---|---|---|---|---|
| A4-001 | Change highlight rendering to return `pending` or `unavailable` when source footage is missing. | Backend highlights | A0-005 | Triggering a highlight without source footage does not produce a successful black clip. | DONE |
| A4-002 | Stop highlight workers from recording placeholder renders as successful deliverables. | Backend highlights | A4-001 | Worker records a non-success or non-deliverable state for placeholder renders. | DONE |
| A4-003 | Remove `liveThenFixture` from production-bound secondary APIs. | Frontend data layer | A0-005 | Live-path API errors surface as real failures instead of seeded fixture data. | DONE |
| A4-004 | Re-enable globally suppressed Flutter lints and fix the underlying async-context issues. | Frontend app | A0-005 | `use_build_context_synchronously` is not globally ignored and code passes lint with explicit mounted handling. | DONE |
| A4-005 | Remove or gate localhost defaults from release-capable frontend config. | Frontend config | A0-005 | Release configuration fails fast when API base URL is missing. | DONE |
| A4-006 | Align task/challenge reward UX with real backend claim payloads instead of shallow local-only demos where applicable. | Frontend tasks | A4-003 | Claim flows show backend-driven reward/streak state or are clearly marked as demo-only. | PENDING |

## Phase A5: Route Integrity and Shell Cleanup

Phase acceptance criteria:
- No visible route lands on a placeholder wall.
- Hidden or blocked routes are either implemented or removed from active user discovery.

| Task ID | Description | Owner/System | Dependency | Acceptance Test | Status |
|---|---|---|---|---|---|
| A5-001 | Audit all blocked and hidden routes in the active shell and admin shell. | Frontend routing | A0-005 | Every blocked/hidden route is listed with keep/remove/implement decision. | PENDING |
| A5-002 | Remove dead routes from visible navigation and quick actions. | Frontend navigation | A5-001 | No visible nav item routes to an integrity wall. | PENDING |
| A5-003 | Wire or intentionally disable admin surfaces such as God Mode, treasury ops, admin finance, creator leaderboard, and club admin. | Frontend admin + backend admin APIs | A5-001 | Admin routes either work end-to-end behind role checks or are removed from the active shell. | PENDING |
| A5-004 | Resolve community hub status by wiring it or removing it from active shell exposure. | Frontend community | A5-001 | Community route no longer lands on `GteRouteIntegrityScreen.hidden` in production-visible flows. | PENDING |
| A5-005 | Add route-integrity regression tests for visible route surfaces. | Frontend tests | A5-002, A5-003, A5-004 | Test suite fails if a visible route regresses to a blocked or hidden wall. | PENDING |

## Phase A6: Missing Action Wiring for Shipping Features

Phase acceptance criteria:
- High-value backend features that are meant to ship have reachable UI action paths.
- Read-only surfaces are not presented as complete if key actions are missing.

| Task ID | Description | Owner/System | Dependency | Acceptance Test | Status |
|---|---|---|---|---|---|
| A6-001 | Wire gifting from reachable broadcast/match UI into the backend gift send flow. | Frontend match UI + backend gift engine | A0-005, A1-005 | A user can open gifting from a live screen and successfully send a gift through the backend. | PENDING |
| A6-002 | Add sponsorship offer discovery and application flow if sponsorship engine is a shipping feature. | Frontend sponsorship + backend sponsorship engine | A0-005 | Users can browse offers and submit an application from the frontend. | PENDING |
| A6-003 | Add actionable governance UI where governance is meant to be interactive. | Frontend governance/federations + backend governance | A0-005 | Users can complete the intended governance action set, not just read proposal data. | PENDING |
| A6-004 | Add intended community actions that already have backend support. | Frontend community + backend community/club-social | A0-005, A5-004 | Exposed community actions map to real backend endpoints and error handling. | PENDING |
| A6-005 | Wire creator/media finance surfaces that currently rely on coarser summaries when more specific backend endpoints exist. | Frontend creator/media finance | A0-005 | Frontend uses the intended endpoint for clip or media earnings where the backend provides it. | PENDING |

## Phase A7: Backend Module Portfolio Decision

Phase acceptance criteria:
- Every backend-only or mostly-unwired module has an explicit ship/hide/deprecate decision.
- No product claim implies a live frontend surface without a decision and owner.

| Task ID | Description | Owner/System | Dependency | Acceptance Test | Status |
|---|---|---|---|---|---|
| A7-001 | Decide ship/hide/deprecate for commercial and monetization modules still lacking real UI paths, including `reward_engine`, `broadcast_rights`, `creator_campaign_engine`, and `ticketing`. | Product + backend + frontend | A0-005 | Each module has an owner, status, and either a UI plan or a hide/deprecate plan. | PENDING |
| A7-002 | Decide ship/hide/deprecate for competitive/meta modules including `manager_duels`, `simulation_matchmaking`, `ultimate_league`, `infinite_league`, and `fast_cups`. | Product + gameplay systems | A0-005 | Each module is either scheduled for UI work or explicitly removed from active product claims. | PENDING |
| A7-003 | Decide ship/hide/deprecate for social/engagement modules including `club_social`, `history_engagement`, `legend_layer`, `live_ops`, and `moments`. | Product + social systems | A0-005 | Each module has a disposition and no orphaned implied-live status remains. | PENDING |
| A7-004 | Decide ship/hide/deprecate for infrastructure/admin-sensitive modules including `club_infra_engine`, `regen_ecosystem`, `surveillance`, and `betting`. | Product + platform + compliance | A0-005 | Risk-sensitive modules are either deliberately exposed with scope or explicitly hidden/deprecated. | PENDING |

## Phase A8: Partial Feature Completion

Phase acceptance criteria:
- Partially wired features have their intended core action set.
- Read-only implementation gaps are either closed or clearly labeled as limited scope.

| Task ID | Description | Owner/System | Dependency | Acceptance Test | Status |
|---|---|---|---|---|---|
| A8-001 | Complete Fan Wars action coverage or reduce product claims to read-only scope. | Frontend Fan Wars + backend fan wars | A0-005 | Users can complete the intended Fan Wars participation path, or UI copy clearly scopes it as read-only. | PENDING |
| A8-002 | Decide whether federation governance remains read-only or gains vote/action support. | Frontend federations + backend federation/governance | A6-003 | Federation governance surfaces align with the intended product capability. | PENDING |
| A8-003 | Align replay entry points with the intended replay/archive policy layer. | Frontend replay + backend matches/replay archive | A0-005 | Replay entry points use the approved backend policy surface and preserve access rules. | PENDING |
| A8-004 | Deepen sponsorship surfaces beyond package/contract read-only views where shipping scope requires it. | Frontend sponsorship | A6-002 | Sponsorship UI covers the intended end-to-end club flow. | PENDING |
| A8-005 | Review remaining read-only surfaces that visually imply complete functionality and either finish or relabel them. | Frontend product surfaces | A0-005 | No read-only surface is presented as a complete transactional feature without scope labeling. | PENDING |

## Phase A9: Testing and Observability

Phase acceptance criteria:
- CI catches the regression classes surfaced by the audit.
- Operators can see degraded mode, dependency failures, and contract drift clearly.

| Task ID | Description | Owner/System | Dependency | Acceptance Test | Status |
|---|---|---|---|---|---|
| A9-001 | Add regression tests for payment-provider exposure and webhook fraud paths. | Backend tests | A1-001, A1-003 | CI fails if stub providers become user-visible again or fraud validation regresses. | PENDING |
| A9-002 | Add restart/durability tests for creator/referral runtime state. | Backend tests | A3-001, A3-002, A3-003 | CI fails if durable services regress to in-memory behavior. | PENDING |
| A9-003 | Add highlight placeholder gating tests. | Backend tests | A4-001, A4-002 | CI fails if placeholder highlight renders are treated as successful live artifacts. | PENDING |
| A9-004 | Add tests that fail on silent fixture fallback in live production-bound paths. | Frontend tests | A4-003 | CI fails if live-path fallback silently reappears. | PENDING |
| A9-005 | Add route-integrity and shell-surface regression tests. | Frontend tests | A5-005 | CI fails if a visible route becomes blocked or hidden again. | PENDING |
| A9-006 | Improve health and diagnostics output for backbone availability, degraded mode, and config gaps. | Backend health + ops | A2-005 | Health endpoints clearly identify dependency and config problems. | PENDING |

## Phase A10: Code-Lie, Naming, and Documentation Cleanup

Phase acceptance criteria:
- Names describe actual runtime behavior.
- Product and engineering docs no longer imply capabilities that are not shipping.

| Task ID | Description | Owner/System | Dependency | Acceptance Test | Status |
|---|---|---|---|---|---|
| A10-001 | Rename or remove misleading abstractions that imply production support or durability when they are demo-only. | Backend + frontend codebase | A3-004, A4-003 | No production-path class or API name materially misdescribes its storage or behavior. | PENDING |
| A10-002 | Remove dead scaffolding, dead exports, and fake-complete surface area that survived refactors. | Backend + frontend codebase | A7-001, A7-002, A7-003, A7-004 | Dead or misleading scaffolding is either removed or explicitly marked non-production. | PENDING |
| A10-003 | Align docs, route descriptions, and product copy with actual runtime behavior and shipped scope. | Docs + frontend copy | A5-002, A7-001, A7-002, A7-003, A7-004 | Docs and in-app copy no longer claim features that are hidden, stubbed, or incomplete. | PENDING |

## Phase 0 Evidence Already Verified In This Checkout

Canonical matrix:

- `CURRENT_STATE_CONTRACT_MATRIX.md`

The following audit claims have already been verified as stale or reframed and should be treated as Phase A0 baseline evidence:

- Alembic versions are present in this checkout.
- Paystack signature verification exists outside the provider adapter path.
- Startup auth-secret validation now fails fast.
- Frontend platform directories exist in this checkout.
- Native Android 3D bridge/runtime exists in this checkout.
- Wallet top-up request/response field mismatches cited in the audit are stale here.
- Fan prediction routing is present in the current route registry.
- Hosted competition launch and finance surfaces are wired in the current UI.
- Transfer-market and world-simulation surfaces are wired in the current UI.

These remain open and drive later phases:

- Stub wallet providers are still exposed or ambiguously represented.
- Highlight placeholder renders are still treated as successful deliverables.
- Creator/referral runtime still uses in-memory state on live paths.
- Mutable admin-finance state is still tracked in git.
- Global async-context lint suppression and production fixture fallback remain real frontend risks.
- Multiple routes and modules still present as hidden, blocked, read-only, or incompletely wired surfaces.
