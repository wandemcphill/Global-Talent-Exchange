# Gemini 3.8 Flash High — Parallel GTEX Implementation Prompts

Use one independent Gemini session per prompt. Each session should work on its own branch and open its own focused PR. These prompts implement the frontend half of the two-agent plan in [PR #341](https://github.com/wandemcphill/Global-Talent-Exchange/pull/341).

## Global rules for every session

- Repository: **wandemcphill/Global-Talent-Exchange**
- Read the relevant tracking issue and inspect current main before editing. Reproduce the actual behavior; do not assume audit labels are still current.
- Do not edit backend code, database migrations or server-side business rules. ChatGPT / Agent A owns those.
- Do not edit UI files assigned to another session. Keep to the explicit file boundary below.
- Use the same authoritative API response and canonical IDs across React and Flutter. No fake success states, invented records, client-side authoritative world time, duplicated prices, or alternate game logic.
- Preserve the existing GTEX Navy/premium visual system, Flutter-native interaction patterns, regen generation, portrait/face-bank mappings, career history and 2D match pipeline.
- Use focused commits and a small PR. Run real tests and report exact commands/results; clearly identify anything not run, unsupported or blocked by a backend contract.
- Do not use live money transfers, production mutations or real payouts to test.

---

## Session B1 — Club origin fields

**Branch:** gemini/club-origin-forms  
**Issue:** [#343](https://github.com/wandemcphill/Global-Talent-Exchange/issues/343)

Implement validated club country, city and region selection instead of silently submitting Nigeria/Lagos as the default.

**Own files:** React frontend/react-shell/src/pages/Onboarding.tsx, MyClubs.tsx and directly related location form components/tests; Flutter first-club/add-club forms and their tests. Do not edit router, inbox, clock or unrelated pages.

Requirements:
1. Trace the existing create-club request and reuse supported geography/country-code conventions.
2. Implement usable country/city/region selection, required-field validation and useful server errors.
3. Fix both first-club onboarding and add-club flows in React and Flutter.
4. Remove hardcoded Nigeria/Lagos submission defaults rather than replacing them with another hardcoded location.
5. Verify two distinct country/city combinations persist and survive refresh using the real contract or integration test.
6. Preserve club identity, ownership, onboarding and responsive/accessibility behavior.

Deliver a small PR with test evidence.

---

## Session B2 — Owner decision inbox and navigation

**Branch:** gemini/owner-inbox-parity  
**Issue:** [#343](https://github.com/wandemcphill/Global-Talent-Exchange/issues/343)

Make the private owner decision inbox discoverable and consistent in React and Flutter without hijacking community chat.

**Own files:** Flutter frontend/lib/router/app_router.dart, owner inbox/decision-inbox navigation and directly related widgets/tests; React inbox entry-point links and inbox-specific tests only. Do not edit club creation forms, backend files or other sessions' pages.

Requirements:
1. Trace the actual private owner decision inbox and separate community inbox/chat routes.
2. Correct the legacy /inbox route if it redirects to Community instead of the owner decision inbox.
3. Ensure links reach the actionable owner queue and that community chat stays separately discoverable.
4. Preserve authentication, active-club context, deep links, refresh/back navigation and authorization.
5. Check persistent read/unread, archive and decision states plus loading/empty/error cases.
6. Do not claim production persistence based on mocks.

Deliver a small PR with route/widget tests and Flutter analyzer evidence.

---

## Session B3 — Authoritative world clock and owner briefing UI

**Branch:** gemini/world-clock-briefing-ui  
**Issue:** [#345](https://github.com/wandemcphill/Global-Talent-Exchange/issues/345)  
**Backend contract:** draft [PR #347](https://github.com/wandemcphill/Global-Talent-Exchange/pull/347)

Render the shared GTEX world clock in the primary owner surface of React and Flutter. Prepare briefing cards only against verified persisted event data.

**Own files:** React owner landing/control-centre page, typed clock client and dedicated tests; Flutter owner dashboard/presentation, API client and dedicated tests. Do not edit backend, onboarding, inbox routes or Regen/contract pages.

The intended clock route is **GET /api/world/clock**. Inspect PR #347 and verify its response before integrating. It exposes clock_id, UTC world_time, world_date, is_paused, progression_rate and virtual_months_per_season; it is not yet merged.

Requirements:
1. Render actual returned virtual time, pause state, loading and error states.
2. Never use browser/device time or client timers as authoritative GTEX time.
3. Do not guess a season label; use an approved backend season contract.
4. Briefings must use persisted verified events. If that contract is unavailable, show an honest empty/unavailable state rather than invented stories.
5. Link verified items to the relevant decision, match result or club history.
6. Preserve responsive/accessibility behavior and current design system.

**Important cadence decision:** draft PR #348 proposes one owner simulation step per virtual world date instead of the old six-hour/page-visit gate. That change is explicitly pending product approval. Do not build client-side ticking or imply the scheduler has deployed.

Deliver a focused PR with client/component tests and blocked contract details.

---

## Session B4 — Regen discovery to contract journey

**Branch:** gemini/regen-contract-journey  
**Issue:** [#345](https://github.com/wandemcphill/Global-Talent-Exchange/issues/345)

Connect discovery, dossier, scouting, watchlist, offers, contract decisions, squad registration and player history in React and Flutter.

**Own files:** React Regen World, dossiers, scouting/watchlist and relevant transfer/contract pages; corresponding Flutter surfaces and their dedicated tests. Do not edit backend, owner-clock pages, inbox routes or club-creation files.

Requirements:
1. Audit current endpoints and existing player identity/provenance before changing routes.
2. Carry the same canonical player ID through the whole journey.
3. Respect player/agent/coach decisions; show honest intermediate states supported by the API.
4. Preserve regen generation, face-bank/portrait mapping, provenance and career history. Never create a duplicate player to bridge a screen.
5. Cover permission, loading, empty, validation and server failure states.
6. Do not locally mark contracts complete or players registered before server confirmation.
7. If a step lacks a backend contract, report the exact missing request/response and add typed client boundaries/tests without faking production success.

Deliver a focused PR with React and Flutter tests.

---

## Session B5 — Showroom, gifts and story presentation

**Branch:** gemini/prestige-story-parity  
**Issue:** [#345](https://github.com/wandemcphill/Global-Talent-Exchange/issues/345)  
**Catalogue dependency:** [#353](https://github.com/wandemcphill/Global-Talent-Exchange/issues/353)

Improve discovery and presentation of owner showroom assets, luxury gifting, world news and club history.

**Own files:** React showroom/catalogue, luxury gift and club-story/news components; Flutter counterparts and their unit/widget tests. Do not edit backend, onboarding, inbox routing, world-clock pages or Regen/contract pages. Do not own the dedicated Playwright release-test files assigned to B6.

Requirements:
1. Consume authoritative catalogue, stock, purchase, inventory, gift and receipt data. Do not duplicate prices or scarcity logic.
2. Keep owner-to-player luxury gifts distinct from community/FanCoin gifts.
3. Clearly separate public world news, private owner decisions, club history and daily briefings.
4. Display only verified persisted transactions and events.
5. Preserve GTEX Navy/premium gold styling and mobile/tablet/desktop usability.
6. Do not invent mappings between owner showroom SKUs and legacy luxury-asset SKUs. That backend reconciliation is tracked in #353.
7. Add component-level tests and accessibility checks; B6 owns cross-shell release E2E tests.

Deliver a focused PR and document any catalogue/API dependency.

---

## Session B6 — Cross-shell release E2E and parity tests

**Branch:** gemini/owner-journey-e2e  
**Issues:** [#345](https://github.com/wandemcphill/Global-Talent-Exchange/issues/345), [#352](https://github.com/wandemcphill/Global-Talent-Exchange/issues/352)

Work on the test harness and dedicated acceptance test files only. Do not edit React/Flutter application components, backend services or migrations. Coordinate by reading other sessions' PRs and testing the actual supported contracts.

**Own files:** dedicated Playwright E2E specs, test helpers/fixtures and dedicated parity test documentation. Avoid modifying shared test configuration if another active PR changes it; report conflicts before rewriting common helpers.

Required owner journey:
Create/claim club → persistent owner world clock/briefing → appoint appropriate staff → facilities/academy → discover/scout a regen → offer and contract decision → squad/lineup → canonical scheduled fixture executes → same result in match centre/standings/history/news → approved settlement event → refreshed owner briefing.

Requirements:
1. Use deterministic test accounts and isolated test state; never make real charges, payouts or refunds.
2. Test desktop and responsive widths 360, 390, 768 and 1280 CSS pixels where applicable.
3. Assert backend-persisted identity and outcomes, not just visible labels. Refresh/deep-link and confirm state remains consistent.
4. Verify errors, empty states, permissions, duplicate submissions and session expiry.
5. Test the same domain results across React and Flutter using their available integration harnesses; do not demand identical component markup.
6. If the full journey is blocked by a missing endpoint or an unresolved canonical competition path, create a focused failing/blocked test with explicit evidence and name the exact dependency. Do not mock a success to make the suite green.
7. Re-check current shared Playwright helpers first; do not dismiss failures as baseline without reproducing them.

Deliver a test-only PR with exact commands, logs/evidence and a matrix of supported vs blocked journey steps.

---

## Handoff and PR review

Each session must name its branch, changed-file list, test results and backend contract dependencies in its PR. Agent A owns backend persistence and domain decisions; Agent B sessions own only their assigned frontend/test areas. A second session may review another session's PR, but must not independently edit the same files. None of these prompts authorizes production database changes or real financial transactions.
