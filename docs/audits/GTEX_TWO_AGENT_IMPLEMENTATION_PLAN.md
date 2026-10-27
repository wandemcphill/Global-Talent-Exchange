# GTEX Two-Agent Implementation Plan

**Purpose:** implement the GTEX product-vision gap audit with two coding agents—ChatGPT in the connected repository environment and Gemini 3.8 Flash High—without conflicting edits or competing sources of truth.

**Product authority:** the owner-first, persistent football world described in the Product Vision Gap Audit.  
**Audit/coordination PR:** [#341](https://github.com/wandemcphill/Global-Talent-Exchange/pull/341)  
**Umbrella tracking:** [#267](https://github.com/wandemcphill/Global-Talent-Exchange/issues/267)

## Operating rules

1. **One owner per file/domain per tranche.** The assigned agent owns the implementation. The other agent reviews it and may submit findings, but does not independently edit the same files.
2. **Small PRs, one coherent lifecycle per PR.** No mega-PR across unrelated systems. Every PR identifies source-of-truth models, migration/backfill needs, authorization, idempotency, UI surfaces, tests, rollout/rollback, and what was not verified.
3. **Current source beats old audit labels.** Reproduce findings against the branch being changed. Do not reopen fixed findings merely because an old audit calls them open.
4. **Backend state is authoritative.** React and Flutter must not duplicate competition engines, money, player contracts, staff decisions, world time, or durable event creation.
5. **React launches first; both shells remain in scope.** Every user-facing capability in scope must have a working React path and a corresponding Flutter path using the same service/data contract. “Parity” means equivalent action, permissions, state, feedback and persisted result—not identical component structure.
6. **No unapproved economic/time rules.** Do not invent withdrawal behavior, payout amounts, new fees, transfer escrow semantics, world rate or season/age cadence. If a policy choice is required, expose the choice in the product-decision register and use existing policy only until it is approved.
7. **Prove behavior, not screen presence.** A UI is done only when its authorized action mutates canonical state, persists, has a test, survives refresh, and agrees across both shells. AI may explain verified events; it cannot mutate domain state.

## Ownership map

### Agent A — ChatGPT in this repository environment
**Exclusive ownership: backend domain logic, persistence, API contracts, migrations and backend tests. Do not change React/Flutter presentation files in this tranche.**

| Work packet | Main focus | Required evidence |
|---|---|---|
| A1 — Transfer integrity (first) | Correct Transfer Hub cash-offer acceptance so an “accepted/completed” deal cannot stop at a status update; enforce seller/player ownership for club listings; separate free-agent/regen recruitment from club sales. | Buyer/seller ledger conservation under the approved policy; canonical player/contract movement; authorization; retry/concurrency; insufficient funds; unassigned player and wrong-seller tests. |
| A2 — Authoritative world time | Reconcile \`OwnerClubState.world_day\`/visit-driven \`maybe_auto_tick\` with \`WorldClockService\`; define shared virtual-day scheduling and catch-up semantics while preserving persisted clock state. | Time progression, pause/resume/rate changes, restart survival, overdue event catch-up, offline owner and concurrent worker tests. |
| A3 — Competition and match lifecycle ([#352](https://github.com/wandemcphill/Global-Talent-Exchange/issues/352)) | Establish which competition/match records drive persistent competitive play. Connect owner choices to canonical fixtures and lifecycle, or explicitly segregate any onboarding sandbox. Retire duplicate mutation paths only after parity gates prove replacement. | One fixture executes once; same final result/events/replay/standings/completion/settlement everywhere; offline execution and idempotency tests. |
| A4 — Staff and squad source of truth | Canonicalize staff roles/identity/assignments and downstream effects; GM must not silently alias to first-team manager. Define authoritative competitive player/contract/roster identity and adapters for legacy projections. | GM/manager/HOYD/scout role authorization and effects tests; academy promotion reuses canonical player identity; no shadow competitive roster writes. |
| A5 — Asset economy and owner intelligence | Reconcile showroom/legacy asset catalogues and gift lanes; add verified-event-backed daily owner briefing production after the canonical clock/event contract is agreed. | One SKU/price/scarcity/inventory source; owner-player gifts distinct from community gifts; idempotent purchases; one briefing per configured GTEX cadence from verified events only. |

**Agent A file boundary:** \`backend/**\`, backend migrations/tests, shared backend-owned API contract/schema files and the coordination/product-decision documentation. Avoid editing \`frontend/**\` and React page components. If a public endpoint changes, publish the request/response shape and generated-client consequences in the PR description so Agent B can integrate without guessing.

### Agent B — Gemini 3.8 Flash High
**Exclusive ownership: React and Flutter UI, navigation, generated client integration, client-side tests and responsive/visual parity. Do not edit backend business logic or database/migration files in this tranche.**

| Work packet | Main focus | Required evidence |
|---|---|---|
| B1 — Global club setup | Replace React's hardcoded Nigeria/Lagos club origin defaults with validated country/city/region fields; implement the equivalent Flutter form and shared contract behavior. | At least two country/city cases, validation, persisted origin after refresh, responsive test coverage. |
| B2 — Owner inbox/navigation | Make the Flutter owner inbox path resolve to the private decision inbox, without hijacking community chat; align React/Flutter item states and actionable links. | Same authorized persisted item IDs, read/unread/archive/action behavior and error/empty states across shells. |
| B3 — Owner world/briefing | Add a visible shared-world clock/current season indicator to React's primary owner surface and the corresponding Flutter surface; build daily briefing presentation only against Agent A's verified API contract. No fabricated fallback stories. | Same clock and briefing facts, link-through to affected decisions, stale/loading/error/empty states, no “success” before server confirmation. |
| B4 — Regen-to-contract journey | Join discovery, dossiers, scouting, watchlist, offers/negotiation, contract status and squad registration in React and Flutter, using existing authoritative APIs and Agent A's published contract changes. | Shared player identity, correct contract/status, action permission, empty/error/loading cases, deep-link and persistence tests. |
| B5 — Prestige, story and full-shell parity | Wire existing asset catalogue/gifts and verified world/club stories/inbox to canonical backend contracts; improve owner-first navigation and responsive layouts without introducing parallel business rules. | Equivalent supported purchase/gift/history flows across shells, accurate item metadata and receipts, viewport matrix and accessibility checks. |
| B6 — Release E2E | Complete authenticated Playwright flows against React launch routes and compare their domain assertions with the Flutter parity tests. | Create/claim club → owner briefing → staff/academy/scout → regen offer/signing → lineup/pre-match → canonical world fixture → same result/history/news/ledger. |

**Agent B file boundary:** \`frontend/react-shell/**\`, \`frontend/lib/**\` and \`frontend/test/**\` (including Flutter route/screen/client tests). Do not invent or duplicate server-side rules. If a backend capability is not yet available, prepare the UI using a typed interface/mock in tests and clearly mark the dependency; do not simulate successful production persistence.

## Sequence and parallelism

### Gate 0 — Shared contract before dependent work
- Keep the product decisions below visible and explicit.
- Agent A identifies canonical models/routes and publishes request/response shapes.
- Agent B can begin independent changes (global club origin fields and Flutter inbox route) while A works on transfer integrity. Do not build the global clock/briefing or completed-transfer UI against guessed contracts.

### Gate 1 — P0 financial and lifecycle integrity
1. A1 transfer acceptance and seller validation.
2. A2/A3 world clock and canonical competition lifecycle plan, then focused implementation.
3. A4 role/roster authority decisions and migrations/adapters.
4. Agent B consumes the stabilized API contracts and continues B1/B2.

### Gate 2 — Connected owner experience
1. A5 canonical assets and persisted daily briefing API/events.
2. Agent B builds B3/B4/B5 against those contracts.
3. Both agents review the other’s PR for contract violations and missing parity; only the owning agent pushes changes in that file area.

### Gate 3 — Release certification
- Run backend unit/integration and current quality gates on each PR.
- Run React type/lint/build and authenticated Playwright at 360, 390, 768 and 1280 CSS pixels.
- Run Flutter analyzer, relevant unit/widget/integration tests and parity scenarios.
- Verify the deployed clock row, simulation worker health, a persisted due fixture, event/replay, standings and settlement on a safe non-live environment. Production proof must not be inferred from a configured Render worker or passing CI alone.
- No live charges, real withdrawals, payouts or refunds as a test shortcut.

## Product-decision register — unresolved until explicitly approved

These affect durable game rules and must not be invented independently by either agent.

| ID | Decision needed | Implementation rule until resolved |
|---|---|---|
| D1 | World-clock progression rate and virtual calendar start | Preserve the persisted clock and current configured behavior. Do not change rate in production without an approved schedule. |
| D2 | GTEX season duration, regen ageing, retirement and career cadence | Keep current canonical age mapping; do not change cadence or retroactively age players without a migration plan. |
| D3 | Transfer Hub accepted-offer semantics and funds reservation/escrow | Make statuses honest. Do not mark a transfer complete unless player/contract movement and approved financial postings succeed. Require explicit policy for reservation timing if not already defined. |
| D4 | Club competition entry fees, prize pools and broadcast/TV money | Reuse the Economic Constitution and currently approved settlement path. No invented TV payout formula or currency. |
| D5 | General Manager vs first-team manager vs HOYD role definition, authority, salary and effect curves | Preserve existing data; do not coerce role identities. Add/modify role keys only with a documented game rule and migration. |
| D6 | Relationship between legacy asset SKUs and owner-console showroom products | Do not delete/mint/rename historical inventory until SKU mapping, currency and scarcity are reconciled. |
| D7 | Daily owner-briefing cadence | Implement through the canonical clock/event scheduler after the cadence is confirmed; never gate generation on page visits. |

## Definition of done for every work packet

- [ ] Source-of-truth models and write path named.
- [ ] Authorization is enforced server-side; caller-supplied club/player IDs are not trusted without membership/ownership resolution.
- [ ] Repeated and concurrent requests are safe; ledger/event writes are idempotent.
- [ ] Empty/loading/error/permission/success states are honest in both shells.
- [ ] Automated tests cover success, rejection, refresh persistence, cross-club isolation and relevant races.
- [ ] Existing regen generation, face-bank mapping, player identity/history and the canonical 2D match pipeline are preserved.
- [ ] CI results are linked; browser/worker/production claims have separate evidence.
- [ ] PR states known gaps, product decisions and rollback/migration behavior.
- [ ] The other agent reviewed the implementation without making conflicting edits.

## Handoff message for Gemini

Implement only the Agent B work packets from this plan, in a dedicated branch and small PRs. Start with B1 (global club origin) and B2 (Flutter owner inbox route) because they are relatively independent. Do not modify \`backend/**\` or invent business rules. Before implementing B3/B4/B5, read Agent A's merged or draft API-contract changes and use their actual endpoints/schemas. Preserve the React design system, Flutter-native interaction patterns, current regen generator and portrait/face-bank mapping, 2D match pipeline and existing canonical backend. Report exact changed files, test commands/results, any blocked contract, and screenshots/Playwright evidence.
