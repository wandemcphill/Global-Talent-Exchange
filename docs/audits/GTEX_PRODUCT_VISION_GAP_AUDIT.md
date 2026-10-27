# GTEX Product Vision Gap Audit

**Audit date:** 27 October 2026  
**Repository:** Global Talent Exchange  
**Status:** Product/engineering gap assessment; not a production certification  
**Related umbrella:** [Issue #267 — Comprehensive Audit](https://github.com/wandemcphill/Global-Talent-Exchange/issues/267)

## Executive assessment

GTEX should be designed and shipped as a persistent football world in which users own clubs, appoint differentiated staff, shape long-term strategy, compete, build a legacy, and participate in a shared, auditable economy. It should not feel like a bundle of loosely connected football screens.

The codebase contains substantial building blocks: a persistent world-clock service and autonomous fixture scanner, club facilities and prestige concepts, an owner newsroom/inbox/story system, a transfer market, a regen universe, academy lifecycle work, national-team rentals, competition settlement policy, and React pages for many of these domains. Recent merges improved important foundations: [#326 match-centre integrity and parity](https://github.com/wandemcphill/Global-Talent-Exchange/pull/326), [#329 retirement of legacy tournament mutations](https://github.com/wandemcphill/Global-Talent-Exchange/pull/329), [#337 youth lifecycle](https://github.com/wandemcphill/Global-Talent-Exchange/pull/337), [#338 persistent world clock/autonomous fixtures](https://github.com/wandemcphill/Global-Talent-Exchange/pull/338), and [#339 scouting/watchlist integration](https://github.com/wandemcphill/Global-Talent-Exchange/pull/339).

The major risk is coherence. Current source paths still expose multiple models for the same concepts: a global clock plus an owner-console world-day tick; canonical competition/match models plus owner-console competitions/matches; canonical staff contracts plus legacy executives and a manager JSON snapshot; and more than one asset catalogue/purchase model. The React launch surface uses several owner-console APIs while the new world-clock worker operates on canonical competition models. A new backend capability therefore cannot be assumed to power the user-visible React journey.

The next engineering priority should not be to add more unrelated screens. It should be to join the existing systems into one verified owner journey, with a single authoritative lifecycle for time, competitions, staff, players, assets, and money.

## Scope and confidence

This review examined current default-branch source and docs for React routing and pages, owner-console services/models/routes, staff policy/contracts, world clock and autonomous execution, regen/academy work, prestige catalogues, transfer-market paths, economic policy, Render worker configuration, existing audit artefacts, and recent issue/PR status.

This is a source-level review. I did not authenticate into the deployed production app, inspect a live production database, verify Render worker logs, test real payment-provider callbacks, run live payouts/refunds, or complete the Playwright viewport matrix. Anything requiring those observations is marked **not verified**. Older audit spreadsheets are historical snapshots because material PRs merged after they were created.

## Product contract

### Owner-first strategy

The owner is the strategic principal. The user should be able to understand club health, cash commitments, reputation, squad strength, staff quality, academy potential, upcoming fixtures, and important choices without needing to micromanage the manager's daily duties.

The General Manager should primarily handle business and football operations: planning, budget discipline, recruitment strategy, negotiations, roster planning, and advice to the owner. The first-team manager should lead tactics, squad selection, training, player morale, and match preparation within their remit. The Head of Youth Development should own academy pathways, intake quality, player development plans, and readiness recommendations in collaboration with the first-team manager. Scouts, coaches, analysts, medical staff, and other roles should have separate, explainable effects.

Hiring should change what a club can do. Each candidate needs a durable identity, role-specific attributes and personality, salary/contract constraints, and downstream effects that can be traced to scouting, recruitment, training, academy promotion, match preparation, finances, and owner recommendations. Expensive staff should not be universally affordable; affordability and a candidate's interest should reflect defined club economics, stature, ambition, and relevant attributes.

### One persistent world

Every owner should see the same GTEX calendar and world time, independently of their local time zone. Fixtures, competition transitions, regen ageing, deadlines, career events, and recurring financial events must derive from that common clock. A newly registered user should join the current world, not start an isolated calendar.

The world clock's rate, starting calendar, season length, pause policy, and regen age conversion are product rules—not implementation details to guess. Real-player age should continue to follow sourced real-world identity data; regen/newgen careers should follow the explicitly approved GTEX age schedule.

### One auditable economy

Each financial event must have one authoritative currency, source, destination, state transition, idempotency rule, and persisted audit trail. GTEX Coin and FanCoin have distinct policy meanings and must not become interchangeable through presentation or settlement shortcuts. Screens should show consequences of transfers, rewards, prizes, club expenses, assets, and gifts only after the authoritative service confirms them.

Owner-to-player luxury gifting and community/fan gifting are distinct product lanes. Keep them distinct in eligibility, currency, ownership, inventory, and ledger treatment even if both create visible in-world events.

### A living story, not fictional state

AI can explain outcomes, surface risks, draft articles, summarize staff recommendations, and make staff conversations expressive. The model must be supplied with verified club/player/fixture/ledger facts and a clear set of allowed claims. A generated article, briefing, or conversation must not create a transfer, payment, player status, match result, or settlement. Those are domain events; AI is the presentation and reasoning layer.

## Confirmed architecture findings

### F-01 — Two different notions of world time are active in the codebase
**Priority: P0 — resolve before claiming the persistent-world loop is complete.**

The shared clock exists in [world_clock_service.py](https://github.com/wandemcphill/Global-Talent-Exchange/blob/main/backend/app/services/world_clock_service.py); its durable state is stored in the world_clock_state table, and autonomous fixtures use WorldClockService.now_virtual(). Render configuration sets progression to 1.0, meaning one virtual second per real second by default. The clock code supports pause/resume and a configurable rate, but current documentation correctly says the rate and season-age policy require a product decision.

Separately, OwnerClubState in [owner-console models](https://github.com/wandemcphill/Global-Talent-Exchange/blob/main/backend/app/owner_console/models.py) stores world_day and last_tick_at. tick_club() in [owner-console service](https://github.com/wandemcphill/Global-Talent-Exchange/blob/main/backend/app/owner_console/service.py) increments that per-club day. maybe_auto_tick() calls it when an owner opens the control centre and the previous tick is more than six real hours old. This is not the same contract as a globally scheduled world day. At least one owner-facing gameplay loop remains gated by a visit and a wall-clock threshold instead of advancing from the shared world clock.

No consumer-facing clock endpoint/display or React navigation display was found in the inspected paths. Recheck with a complete route inventory, but the source search did not find a clock display in either frontend.

**Required outcome:** one clock service and one defined virtual calendar, exposed through an authenticated/read-safe API and visible in the React owner experience, with the Flutter counterpart. Convert time-driven owner ticks, deadlines, ageing and reports to consume the canonical clock or explicitly retire their old tick model. Add restart, pause/rate-change, catch-up and concurrent-worker tests. Live worker health and production result persistence require separate operational verification.

Sources: [world-clock operational contract](https://github.com/wandemcphill/Global-Talent-Exchange/blob/main/docs/world-clock-and-autonomous-fixtures.md).

### F-02 — React competitions and autonomous fixtures do not yet demonstrate one shared lifecycle
**Priority: P0 — verify and reconcile before launch.**

The autonomous runner in [autonomous_match_service.py](https://github.com/wandemcphill/Global-Talent-Exchange/blob/main/backend/app/services/autonomous_match_service.py) selects canonical CompetitionMatch records and uses the shared virtual clock. React's current [CompetitionDetail.tsx](https://github.com/wandemcphill/Global-Talent-Exchange/blob/main/frontend/react-shell/src/pages/CompetitionDetail.tsx), however, reads /owner/competitions/{id}, shows owner-console competition state, and calls /owner/competitions/{id}/play-next. The owner-console module [competitions.py](https://github.com/wandemcphill/Global-Talent-Exchange/blob/main/backend/app/owner_console/competitions.py) operates on separate OwnerCompetition, OwnerCompetitionEntry, and OwnerMatch tables. React's Match Center reads /owner/matches/{id} while also polling the canonical /api/matches/{id}/state contract.

Those paths may serve intentionally different experiences, but no bridge proving that they refer to the same fixture, result, and settlement was found in the reviewed code. A user-facing manual “Play next match” path also needs an explicit relationship to autonomous world-clock execution.

**Required outcome:** select a canonical competition/match lifecycle. Owner choices should be persisted before kickoff, the world clock should trigger the match, and both shells should read the same match/result/event/replay/standings/settlement records. If an owner-console mode remains for onboarding or tutorial play, mark it explicitly as a sandbox and keep it separate from the persistent competitive economy. Ensure no second pathway can execute, score or settle the same match. Add an end-to-end test that proves a React fixture scheduled in the canonical world is executed once while the owner is offline and appears with the same result in React, Flutter, standings, history, news and ledger.

Sources: [owner-console competition models](https://github.com/wandemcphill/Global-Talent-Exchange/blob/main/backend/app/owner_console/models.py).

### F-03 — The staff model conflicts with the intended club hierarchy
**Priority: P0 — role correctness affects the core product.**

[staff_role_policy.py](https://github.com/wandemcphill/Global-Talent-Exchange/blob/main/backend/app/club_growth/staff_role_policy.py) maps both gm and general_manager to ROLE_FIRST_TEAM_MANAGER. A regression test in backend/tests/test_audit_fixes.py currently codifies that alias. This is inconsistent with the product's distinct General Manager and first-team manager responsibilities.

At the same time, [legacy phase2.py](https://github.com/wandemcphill/Global-Talent-Exchange/blob/main/backend/app/club_legacy/full/phase2.py) has distinct legacy roles for gm, hoyd and football_manager, role-specific attributes, and separate authorities. OwnerClubState.manager_json is another manager representation. The current club-growth staff system calculates coarse effects for scouts/academy directors, coaches/managers, and agents/negotiation specialists, but its staff-effects calculation does not include separate GM or Head of Youth Development effects.

The repo's staff-ingestion design document already describes the intended roles and need to connect GM advice/transfer planning, HOYD intake/development, scouting reports, and manager tactical/personality effects. The issue is not only a missing screen: it is the lack of one complete staff identity/contract/assignment/effect pipeline.

**Required outcome:** define one canonical personnel identity, role registry, qualification policy, offer/negotiation/acceptance lifecycle, active assignment, salary treatment, dismissal/expiry handling, permissions and effect projection. General Manager, first-team manager, Head of Youth Development and scout must be distinct roles, not aliases. Preserve historical staff and contract data through a migration/adapter; do not bulk-coerce role strings. Tests must prove that each role's effects reach its intended downstream service and that a club owner cannot appoint an unqualified candidate or use another club's staff.

Source: [staff-ingestion and integration design](https://github.com/wandemcphill/Global-Talent-Exchange/blob/main/docs/GTEX_PLAYER_AND_STAFF_INGESTION_V2.md).

### F-04 — The owner-console roster and canonical football roster need a documented source-of-truth boundary
**Priority: P0 — affects squad, contracts, transfers and match results.**

The owner-console model contains OwnerSquadPlayer rows with their own attributes, morale, minutes, injuries, regen flag, status and value; it is used by owner-console club and match workflows. Newer canonical flows also use player identities, player contracts, club squad/lineup APIs and the competition match pipeline. PR #340's stated parity work explicitly aims to use authoritative club roster endpoints rather than pass identifiers from a separate React owner-console projection.

The codebase needs to prove which roster is authoritative for recruitment, contract ownership, academy promotion, lineup submission, match simulation, post-match performance, transfer settlement, injuries and regen career state. Otherwise a screen can show a player in one projection without that exact player being eligible or present in the executor's roster.

**Required outcome:** make canonical Player/PlayerContract/club-squad state the authoritative competitive roster, or document and test an explicit adapter if an owner-facing projection remains. Avoid shadow writes. Academy promotion must create/activate the canonical identity and contract, and the same ID must appear in React, Flutter, squad selection, match execution, transfer offers, gifts and player history. Review [PR #337](https://github.com/wandemcphill/Global-Talent-Exchange/pull/337) and draft [PR #340](https://github.com/wandemcphill/Global-Talent-Exchange/pull/340) together.

Source: [owner-console roster model](https://github.com/wandemcphill/Global-Talent-Exchange/blob/main/backend/app/owner_console/models.py).

### F-05 — The prestige asset ecosystem has more than one catalogue and purchase model
**Priority: P1 — financial and inventory coherence.**

The owner-console showroom defines items such as the Sovereign 900X private jet at 4,800 GTEX and the Gulfstream G700 at 6,200 GTEX, with prestige and broadcast metadata, and persists showroom assets in its owner-console asset model. The legacy catalogue in [club_legacy/operations.py](https://github.com/wandemcphill/Global-Talent-Exchange/blob/main/backend/app/club_legacy/operations.py) defines a Harbour Jet at 50,000, a Lagoon Coach at 8,000, and an Icon Watch at 20,000, with supply caps and separate legacy asset/gift logic.

These names may represent intentionally different product lines, but the inspected source does not establish a clear separation of the two catalogues' intended audiences, prices, currency semantics, scarcity and prestige impact. The two paths have different identifiers, inventory models and operations, which can produce inconsistent pricing or duplicate ownership concepts if exposed as one showroom.

**Required outcome:** create one authoritative asset registry and SKU definition with category, price policy, scarcity/cap, owner type, eligibility to gift, prestige/reputation effects, visual asset, inventory state, resale/transfer rules if supported, and event/ledger behavior. Reconcile existing catalogue rows and purchases before retiring any path. Keep owner-to-player gifting separate from FanCoin gifting. Test sold-out items, duplicate requests, failed transactions, accepted/declined gifts, recipient eligibility, inventory updates, audit trail, and identical values across React and Flutter.

Source: [owner-console showroom](https://github.com/wandemcphill/Global-Talent-Exchange/blob/main/backend/app/owner_console/storytelling.py).

### F-06 — Daily owner reporting is not a verified, world-clock-driven capability
**Priority: P1 — central to owner experience and retention.**

GTEX already has an owner control centre, inbox categories (requests, deadlines, staff recommendations, player issues, scouting reports, negotiations and scheduling), club chronology and a newsroom that says it publishes grounded verified events. Those are useful foundations.

However, the inspected owner-console tick advances by incrementing OwnerClubState.world_day in tick_club() and can be triggered from the control-centre request after a six-real-hour threshold. I did not find a clearly scheduled, persisted daily owner briefing that is driven by the global GTEX calendar and combines finance, staff, squad, academy, regen, competition, transfer, prestige and deadline changes into actionable recommendations.

**Required outcome:** one persisted owner briefing per club per GTEX day (or another explicitly chosen cadence), produced from canonical events and current state. It should include what changed; what requires a decision; approaching deadlines; squad/contract risks; academy and scouting recommendations; next fixtures/preparation; financial movements/forecast; and likely consequences of investment options. Each item links to the relevant authoritative screen/action. AI can explain facts and prioritize options; the event source and action authorization remain deterministic. A briefing must not be generated just because the owner logs in, and must not report fictional events.

Sources: [owner-console control-centre route](https://github.com/wandemcphill/Global-Talent-Exchange/blob/main/backend/app/owner_console/router.py), [owner-console service tick](https://github.com/wandemcphill/Global-Talent-Exchange/blob/main/backend/app/owner_console/service.py), [React newsroom](https://github.com/wandemcphill/Global-Talent-Exchange/blob/main/frontend/react-shell/src/pages/Newsroom.tsx).

### F-07 — Competition and transfer economics need current-main end-to-end settlement certification
**Priority: P0 for paid/withdrawable flows; no real transactions during audit.**

The [economic constitution](https://github.com/wandemcphill/Global-Talent-Exchange/blob/main/docs/architecture/GTEX_ECONOMIC_CONSTITUTION.md) defines GTEX Coin as withdrawable subject to ordinary controls and FanCoin as non-withdrawable consumption currency. Recent [PR #297](https://github.com/wandemcphill/Global-Talent-Exchange/pull/297) addressed duplicate reward settlement, FanCoin/GTEX Coin boundary problems and eligibility-score manipulation. [PR #329](https://github.com/wandemcphill/Global-Talent-Exchange/pull/329) retired mutation routes for the duplicate legacy /api/tournaments engine and introduced an admin-only historical-fee dry-run/reconciliation path. These are important corrections, not proof that all current competition systems and transfers are certified.

The earlier [transfer audit issue #281](https://github.com/wandemcphill/Global-Talent-Exchange/issues/281) documented missing bid-time funding holds and transfer movements recorded in club-finance buckets rather than ledger postings. The current transfer service includes funding checks on offer acceptance; the complete current behavior for offer submission, reservation/hold, acceptance, seller credit, buyer debit, failure, cancellation and concurrent retries still needs an explicit re-test against the authoritative economy. Do not reuse the older finding as an unqualified current-main defect, but do not assume closure proves the whole path works.

The current visible React competition route also uses owner-console competition records, so it must be verified against the canonical settlement contract from F-02. Existing club-finance code has sponsorship, match and broadcast income buckets and a weekly cycle; that alone does not prove that canonical competition results generate appropriate persisted club-season/TV-type payouts.

**Required outcome:** map every currency and balance type to its ledger; define the source, eligibility, timing, split, failure and idempotency rules for competition entry fees, prizes, club-season revenue, broadcast/TV money, sponsorship, transfers and withdrawals; then use one canonical settlement service. Make missing product decisions rather than inventing fees or payout amounts. Add tests for repeated settlement, concurrent requests, failed/reversed states, cancelled competitions, unauthorized access, source/destination units, and full ledger conservation. Verify legacy tournament retirement/refund dry-run without issuing real refunds or payouts.

Source: [club finance service](https://github.com/wandemcphill/Global-Talent-Exchange/blob/main/backend/app/club_finance/service.py).

### F-08 — Regen World needs one continuous discovery-to-career-to-contract path
**Priority: P1 — the regen universe is GTEX's long-term differentiator.**

Current React Regen World includes scouting feed, rising stars, bloodlines, rankings, Hall of Fame, tracking and watchlist actions. Recent [PR #339](https://github.com/wandemcphill/Global-Talent-Exchange/pull/339) connected scout discovery/shortlists to authorized canonical watchlist behavior. [PR #337](https://github.com/wandemcphill/Global-Talent-Exchange/pull/337) improved youth intake, contracting and promotion into senior-roster identity. Preserve these capabilities.

The [Phase 4C Regen World contract](https://github.com/wandemcphill/Global-Talent-Exchange/blob/main/docs/phase4/GTEX_PHASE4C_REGEN_WORLD_CONTRACT.md) still records the absence of a world-level aggregate of open regen contract offers, and the current React Regen World query set does not visibly fetch a unified contract board. The Transfer Hub includes offers and negotiations, but owners should be able to move from discovery to a dossier, scouting report, watchlist, contract/transfer decision, acceptance, squad registration and history without losing identity or navigating disconnected feature islands.

**Required outcome:** one discover → scout → shortlist → negotiate/offer → accept/reject → contract/squad → career/history loop, with a shared player ID and truthful status across both shells. Display provenance, contract state, virtual career age, personality/agency, history, and relevant asking/offer data from authoritative models. Preserve the real-player/newgen distinction; regen uniqueness and history must not be destroyed by refresh or ingestion. AI may explain a player's motivation, but must not invent contract state or silently accept an offer.

Sources: [React Regen World](https://github.com/wandemcphill/Global-Talent-Exchange/blob/main/frontend/react-shell/src/pages/RegenWorld.tsx), [living-star regen specification](https://github.com/wandemcphill/Global-Talent-Exchange/blob/main/docs/GTEX_REGEN_LIVING_STAR.md).

### F-09 — Staff advice, club expectations and affordability need a visible consequence loop
**Priority: P1.**

The owner-console engine has manager traits and a youth-development quality input. Its player-growth drivers include facilities, manager youth-development quality, playing time, competition quality and club prestige. The legacy executive layer also models separate GM, HOYD and football-manager attributes. But these influences are spread across different projections and are not presented as one owner-facing explanation of why staff, prestige or club investment changed a decision.

**Required outcome:** publish a transparent, game-rule-backed staff impact model. Before hiring, show the candidate's role fit, qualities, weaknesses, wage/contract expectations and likely club effect; after appointment, show where the effect appears in scouting, academy, transfer, training, morale, tactical, or finance outcomes. Club expectations must be explainable from club stature and owner/board commitments rather than only a hidden rating. Do not hardcode new multipliers or promise guaranteed outcomes before the simulation policy is approved.

### F-10 — Launch verification is not complete
**Priority: P0 for release readiness.**

The React shell declares its routes in [App.tsx](https://github.com/wandemcphill/Global-Talent-Exchange/blob/main/frontend/react-shell/src/App.tsx) and is intended to ship under /console. Current pages are much more extensive than the early React-parity snapshot, but presence of a route or a test ID is not end-to-end proof. [Issue #228](https://github.com/wandemcphill/Global-Talent-Exchange/issues/228) remains the relevant authenticated browser-verification gate, and [PR #340](https://github.com/wandemcphill/Global-Talent-Exchange/pull/340) is a draft rather than a completed launch certification. The world-clock design document also explicitly warns that Render configuration and CI do not prove the deployed simulation worker has processed fixtures and settled outcomes.

**Required outcome:** run authenticated Playwright end-to-end flows on a production-like environment at desktop, tablet and mobile sizes. Verify nested /console deep links and refresh, auth/session expiry, no-club onboarding, multiple-club active context, owner permissions, every primary CTA, empty/error/loading/success states, keyboard/accessibility essentials, and persistence after reload. Test the complete competitive owner journey below and compare React and Flutter against the same API/data assertions. Record browser evidence and deployed worker evidence separately from unit-test results.

Source: [world-clock operational checks](https://github.com/wandemcphill/Global-Talent-Exchange/blob/main/docs/world-clock-and-autonomous-fixtures.md).

## Additional product requirements to make explicit

1. **One cross-shell feature contract.** React is the launch surface, but shared backend capability is not frontend parity. Each prioritized capability needs an owner, React route/action, Flutter counterpart, authoritative API/service, permission checks, loading/empty/error/success states, and automated acceptance tests. Parity means the same behavior and data access, not pixel-identical layouts.
2. **One domain-event source with three presentations.** World news is public activity; Club Story is the history of a selected club; Inbox is private and actionable; Daily Briefing is an owner-specific summary. These should be projections of persisted verified domain events, not four separate storytelling engines.
3. **Two gift lanes.** Keep owner-to-player luxury asset gifting separate from community/fan gifting. Both need persisted gift state, correct sender/recipient authorization, replay protection and event history.
4. **Real-world identity is a launch phase, not a second permanent universe.** Support current real players and regens at launch, with provenance and distinct contract/ownership rules. Make any later regen-focused transition non-destructive and explicit; prevent duplicate legendary entities or accidental player re-minting.
5. **Operational truth for a persistent game.** Show world time, current season, live/due fixtures, last successful simulation cycle, missed/failed fixture counts and latest settled competition state to trusted operators. Expose suitable read-only health in owner/admin surfaces, but not internal operational controls to ordinary owners.

## Required product decisions — do not guess these in code

| Decision | Why it blocks coherent implementation |
|---|---|
| World calendar start and progression rate | The clock default is currently 1:1 with wall time. Decide whether GTEX time advances faster than real time, and how restarts/pause/rate changes work. |
| Season duration and regen age mapping | The stored virtual-age index exists, but final cadence and career/retirement rules must be authoritative. |
| Staff roles, attributes, wages and authority | Distinguish GM, first-team manager, HOYD, scout and other roles; determine effects on outcomes and how clubs afford candidates. |
| Club competition revenue / TV money | Specify eligible competitions, cadence, funding source, payout basis, destination, unit and cancellation/settlement policy. |
| Transfer offers and funding | Decide whether accepted offers require funds at acceptance only or bids reserve/escrow funds; define cancellation and counteroffer behavior. |
| Prestige asset catalogues | Determine whether legacy SKUs are distinct limited editions or overlapping product lanes; then publish one authoritative SKU/price/scarcity/ownership policy. |
| Daily briefing cadence | Confirm whether the report runs per GTEX day, after a set of world events, or on another fixed schedule. It must not depend on a user visiting a page. |

## Recommended remediation order

### Phase 0 — Lock the contracts
- Close the product decisions above before adding new economic or time rules.
- Refresh screen/role/parity inventories against the current default branch and mark each item with current source evidence and a test. Do not carry forward old “missing React page” findings after the page ships.
- Identify the canonical model, write path, and read projection for clock, club roster, personnel, competition/match, asset inventory, and ledger. Record legacy adapters and retirement plans.

### Phase 1 — Make one world authoritative
- Reconcile owner-console tick with the global clock.
- Reconcile owner-console competitions/matches with the canonical autonomous competition lifecycle, or explicitly quarantine owner-console competitions as tutorial/sandbox data.
- Reconcile owner-console roster state with canonical player, contract and club-lineup state.
- Replace staff-role aliasing and separate executive/manager snapshots with canonical personnel contracts plus explicit projections/adapters.
- Unify showroom catalogue and ownership/transfer/gift state.

### Phase 2 — Finish the vertical slice
Prove this journey all the way through persistence:

**Create/claim a club → receive an owner briefing → appoint a qualified GM, manager and HOYD → invest in facilities/academy → scout a regen → negotiate and sign/promote the player → set squad/lineup and pre-match owner decisions → let the GTEX clock execute the fixture while the owner is offline → verify the same result in standings/history/news → settle the approved competition and financial effects once → explain the outcome in the owner briefing.**

The same acceptance contract must pass against both React and Flutter. React UX is the primary release surface; Flutter parity is still required before treating the capability as complete in the shared product.

### Phase 3 — Complete the shared economy and prestige loop
- Re-certify competition escrow, prize settlement, transfer settlement, withdrawal eligibility and currency separation with tests and current-main traces.
- Reconcile historical legacy tournament balances through the approved dry-run/report process; no live refunds during development.
- Connect prestige assets to canonical inventory, club display, published prestige effects, legitimate purchase/gift events and owner reports.
- Implement approved club-season and media/broadcast revenue policy through the authoritative ledger.

### Phase 4 — Make the world feel alive
- Build world-clock display and public world ticker from the canonical calendar/event source.
- Add persisted daily owner briefings, staff recommendation cards and action-specific conversational experiences grounded in each role's remit and actual club state.
- Finish Regen World's contract and career lifecycle, and make player agency/legacy visible in owner decisions without allowing AI to mutate domain state.

### Phase 5 — Launch gates
- Complete authenticated React Playwright matrix and compare shared domain assertions with Flutter.
- Verify /console deep links and refresh, mobile/tablet/desktop layout, session handling and no-club/multi-club journeys.
- Separately verify deployed simulation worker, durable clock row, successful due fixture, persisted events/replay, standings and idempotent settlement.
- Treat payment-provider, refund, withdrawal and payout paths as not production-verified until sandbox/production-equivalent evidence exists. Never use real transactions for release tests.

## Investor-facing product story

GTEX's strongest story is a persistent, owner-driven football economy with a living talent supply. Owners invest in clubs, appoint people with different capabilities, discover unique regens, create player legacies, compete in a shared calendar, and see success and failure change club finances and reputation. AI turns those real outcomes into useful management intelligence and a compelling football narrative.

A credible investor demonstration should show the complete loop rather than a catalogue of screens. The best evidence is that an owner's decision leads to a real persisted event, the autonomous world reacts, the correct club/player/competition state changes, the financial ledger reconciles, and both shells present the same fact. Product metrics should then measure the real loop: activation from signup to first meaningful owner decision, retained active club ownership, competition participation, scouting-to-signing conversion, briefing action rate, verified world-fixture completion, and the proportion of economic events reconciled without manual repair.

## Current conclusion

GTEX has meaningful foundations, and recent changes have reduced some old gaps. But the product should not yet be described as one verified persistent football world. The highest-value work is to canonicalize time, competition execution, club roster, staff identity and the economy; surface those contracts in an owner-first React experience; and prove one end-to-end owner journey with shared Flutter/React assertions. Features should be marked complete only after the actual route, authorized mutation, canonical persistence, downstream consequence, readback and regression test all agree.
