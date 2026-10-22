# GTEX Experience Design Reset — Audit and Screen Contracts

**Purpose:** Replace generic page-by-page polishing with a deliberate redesign of GTEX’s defining product experiences. This document is a design and architecture brief, not a claim that the screens have been implemented, tested, or visually approved.

**Repository:** wandemcphill/Global-Talent-Exchange  
**Baseline inspected:** 22 October 2026  
**Implementation owner:** Antigravity  
**Product principle:** One GTEX world and one set of canonical services, presented through distinctive, purpose-built interfaces.

---

## 1. Executive finding

The problem is not solved by adding spacing, rounding cards, changing accent colours, or polishing the shell. The newer React console is structurally clean, but its key experiences still use a generic admin/dashboard vocabulary. At the same time, it does not expose every specialist football experience that exists in the Flutter application. That creates both a **design gap** and a **feature-parity/navigation gap**.

The redesign should preserve the React shell’s useful application frame and the existing backend, authentication, payments, economy, player identity, regen-generation, portrait/face-bank and transfer lifecycle systems. Replace generic page layouts with art-directed experiences built around what each screen is for.

GTEX should feel like a premium football universe and a working club-ownership simulation—not a standard SaaS admin panel with football data added to cards.

### Confirmed repository evidence

| Area | Current code evidence | Audit conclusion |
|---|---|---|
| App frame | **frontend/react-shell/src/components/gtex/AppShell.tsx** | Fixed side navigation and top bar work as an application frame, but the frame cannot provide the identity for every feature by itself. |
| Owner dashboard | **frontend/react-shell/src/pages/ControlCenter.tsx** | Panels, stat blocks, fixture rail and club portfolio cards are useful foundations; the owner-command-centre hierarchy and club identity need to be stronger. |
| Player cards | **frontend/react-shell/src/components/gtex/PlayerCard.tsx** | Rating and position hierarchy exist, but this is essentially a compact gradient card with a small portrait treatment. |
| Existing player-card concept | **design-concepts/components/cards/player-card.tsx** | A more expressive portrait-led collectible card already exists as a concept, but it uses a different component/model stack and is not drop-in code. |
| Regen cards | **frontend/react-shell/src/pages/Academy.tsx** | A generic layout combines PlayerCard with trait bars, progress and growth information. It does not yet create a distinctive discovery/collectible experience. |
| Existing regen concept | **design-concepts/components/cards/regen-card.tsx** | A unique chalk/blueprint-inspired regen concept with lineage and potential exists. Adapt its visual idea, not its incompatible types or image-loading path. |
| Regen World / Awards | **frontend/lib/features/regen_redesign/presentation/gtex_regen_world_screen_v2.dart** and the regen API/model layers | Dedicated Flutter implementation/domain logic exists. The React route table does not expose a matching Regen World or Regen Awards route. |
| Transfer Hub | **frontend/lib/features/transfer_center/presentation/gtex_transfers_hub_panel.dart** | Flutter provides five segments: Listings, Offers, Negotiations, Window Bids and Shortlist. React Market is not an equivalent experience. |
| React Market | **frontend/react-shell/src/pages/Market.tsx** | General player market, player-share market and sister-club transfer are grouped on one page. Sporting negotiation workflows need their own experience. |
| AI Newsroom | **frontend/react-shell/src/pages/Newsroom.tsx** | Category filtering and grounding language are useful foundations, but the layout is closer to a filtered feed than a premium sports editorial desk. |
| Club identity | **frontend/react-shell/src/pages/ClubStory.tsx** and Flutter club redesign/profile files | Club Story/timeline and public Club Home are different product surfaces. Do not substitute a generic management view for a distinctive public club identity. |
| Deployment | **docs/REACT_CONSOLE_RENDER.md** | Repository documentation describes Flutter at the site root and React at /console/. Treat them as separate frontends sharing the API, not a single component tree. Confirm deployment wiring before route/hosting changes. |

This is a static code audit, not browser certification. Screens still need to be inspected at real viewport sizes with authenticated data.

---

## 2. Design direction

### Product personality

Combine:
- the drama and polish of a premium football-management game;
- the data density and decision clarity of a serious scouting/trading workstation;
- the editorial rhythm of a major football newsroom;
- the prestige of a collectible player-card economy;
- the identity and scale of a living football world.

Do not make every page look like the same dark panel grid. Reuse components for consistency, but give each experience its own composition, media balance, density and interaction model.

### Shared visual system

- **Foundation:** midnight navy, graphite and restrained layered dark surfaces.
- **Primary accent:** premium gold for prestige, ownership, elite cards, awards and meaningful financial emphasis.
- **Secondary accent:** emerald for live states, healthy/positive performance, growth and confirmed success.
- **Neutral text:** high-contrast warm white for key facts; muted slate for secondary metadata.
- **Alerts:** reserve red/amber for real warnings, risk and time-sensitive states.
- **Typography:** expressive display type for club/player identity and editorial headlines; highly legible numeric/monospaced treatment for ratings, valuations and financial metrics.
- **Media:** player portraits and football imagery should carry the design when the content is about players, clubs, matches or awards. Avoid placeholder initials as the primary visual when a known portrait exists.
- **Depth:** use layered image overlays, subtle pitch/tactics marks, tonal gradients, deliberate borders and selective light. Avoid a glow on every card, excessive pills and an indiscriminate grid of rounded rectangles.
- **Motion:** restrained and purposeful. Use reveals, selections, market updates or story transitions only when they help explain the experience. Respect reduced-motion preferences.

Gold is the signature accent, not a replacement for hierarchy. Do not use decorative metrics, fake active events, invented valuations or illustrative rows that could be mistaken for live platform data.

### Design rules

1. Purpose before components: decide what the user must notice and do before selecting cards, charts, tabs or tables.
2. Identity before chrome: a club or player should be recognisable immediately.
3. Different surfaces need different compositions: player card, award stage, newsroom lead story and owner command centre should not be interchangeable templates.
4. Show the real state: API-backed data, timestamps, calculation rules and empty states must remain honest. Never manufacture balances, fixtures, votes, nominees, transfer interest or award winners to fill a mock-up.
5. Preserve existing logic: visual work must not bypass auth, role checks, financial confirmations, ledger posting, transfer permissions, privacy or event-grounding safeguards.
6. No second source of truth: do not create a parallel frontend-only regen, awards, club or transfer model when canonical services already exist.
7. Keep the fast path fast: preserve the regen face-bank mapping, loading behaviour and player identities. Do not replace the working regen rendering/data path with an unrelated concept implementation.

---

## 3. Screen contract: player cards

### Desired experience

Player cards are a signature GTEX object, not just a compact record in a list. The full-size treatment should look collectible and unmistakable: a strong portrait, large rating, position, nationality/club identity, supported tier/rarity and a restrained stat/value region. Standard, Elite, Legendary and other supported tiers should have visually distinct treatment driven by actual tier rules.

### Information hierarchy

1. Portrait and overall rating.
2. Position and player identity.
3. Club/nationality identity.
4. Supported rarity/tier and verified form/market signals.
5. Football attributes, potential, current value and value change only when data is available.
6. Click affordance and explicit status (injured, listed, unavailable) when supplied by real data.

### Interaction and layout

- Provide **full, compact and thumbnail** variants. Full cards serve discovery, collection and spotlight use; compact variants serve dense tables or comparison lists.
- Full cards use a portrait-led composition rather than a tiny image beside text. Rating and position remain readable on small mobile screens.
- Comparison cards align the same fields in the same locations.
- Missing images get an intentional fallback and correct identity, not a broken-image glyph. Preserve current portrait mapping and error handling.
- Keyboard users can focus and activate cards. Do not make an inaccessible non-semantic click target.
- Do not show unsupported stats or invent attributes to fill space.
- A player-card click opens the correct detail/dossier; it must not silently fail for regen variants.
- Use current domain models and identity references. Do not copy the concept component’s incompatible demo model wholesale.

### Acceptance checks

- Known portraits load reliably and are not distorted or awkwardly cropped.
- Rating, position, name, status and value remain legible on mobile.
- Tiers look meaningfully different without relying on colour alone.
- Current players and regens share a design grammar but remain distinguishable.
- Squad, market, share-market, academy and profile usages are checked for regressions.

---

## 4. Screen contract: regen cards and Regen World

### Regen card identity

A regen is a player whose story is still being written. Give it an unmistakable design language separate from normal player trading cards. Adapt the existing concept’s tactics-board/blueprint language—chalk geometry, lineage marks, generation identity, potential range and an intentional prospect portrait—while remaining consistent with GTEX navy, gold and emerald.

Only render lineage, bloodline, archetype, generation and potential details when canonical data actually supplies them. A current player’s value/rating and a regen’s projected ceiling are not interchangeable concepts.

### Regen World composition

The route should feel like a global scouting universe, not the Academy page enlarged.

**Top stage**
- Editorial title and concise explanation of the living regen ecosystem.
- Featured prospect or live world milestone only when returned by real data.
- Clear primary action into discovery or the selected player dossier.
- World/season context only when the API confirms an active season and provides the context.

**Discovery workspace**
- Main prospect field with portrait-forward cards.
- Filters for country/region, position, age, rating/potential, generation and supported availability/origin fields.
- Search, sort and filter reset with visible applied-filter count.
- Compact filter rail on wide screens; drawer/sheet on mobile.
- Selected prospect opens a dossier with profile, verified attributes, growth/history, scouting notes, ownership/market status and lineage when available.

**Connected lanes**
- Prospects/discovery.
- National pools or country views supported by the canonical API.
- Rankings/Hall of Fame or history.
- Awards.
- Create-a-Son/admin workflows only where role-gated and already supported.
- Clear navigation between world, award ceremony and player dossier rather than unrelated screens with repeated headers.

### Data and performance

- Audit the canonical repository/provider, endpoints, cache and error behaviour before connecting a React page.
- Preserve identity IDs, portrait/face-bank mapping, generation logic and backend season rules.
- Avoid fetching all expensive world-level surfaces during initial prospect browsing when lazy-loading is deliberate.
- Never claim a live ranking or active award season when the API reports no season/data.
- Provide honest loading, API error, no active season, no prospects and populated states.
- Fixture/demo repositories remain explicitly test-only; never display them as real production activity.

---

## 5. Screen contract: Regen Awards

This should feel like a prestigious football award ceremony embedded in the regen universe, not a normal list of definitions.

### Composition

- Strong title/season stage and clear ceremony identity.
- Featured winner/award spotlight only when an actual result exists.
- Distinct award-category navigation, with category name and criteria visible.
- Nominee cards using the regen-card treatment, plus concise evidence when the API supplies it.
- Clear voting state, eligibility, deadline and one-vote/action state only if part of the canonical contract.
- Past winners and honours as a separate archive, with season labels and links to player dossiers.
- When no winner exists yet, show nomination/voting/progress from actual API state. Never invent winners or fake live vote counts.

### Trust and interaction

- Voting and selection use backend permissions, season status and API results.
- Confirm consequential submissions; announce success only after the server confirms it.
- Prevent duplicate submissions in the client without treating client state as the authoritative voting rule.
- Use accessible semantics for categories and voting.
- Include loading, no-season, no-nominees, voting-closed and service-error states.

### Acceptance checks

- Visitors can distinguish category, current state, nominees and history at a glance.
- Winner spotlight is shown only when backed by a confirmed result.
- Award cards preserve player identity and open the correct dossier.
- Placeholder awards are never presented as live platform results.

---

## 6. Screen contract: Transfer Hub

### Separate the two markets

Sporting transfers and financial player-share trading are different product systems. Make the distinction obvious in naming, visual hierarchy and navigation. Do not hide the sporting negotiation lifecycle inside a generic page that also contains player shares and related-party transfers.

### Five sporting-transfer lanes

1. **Listings** — available players, asking price/valuation and contract facts, filters, listing freshness and a clear player-led action.
2. **Offers** — incoming/outgoing offers with amount, status, expiry only when defined, clubs involved and a prominent next action.
3. **Negotiations** — active negotiation workspace with offer/counter-offer history, current terms and timeline.
4. **Window Bids** — dedicated window/auction flow using existing rules and actual state; no mock bidding activity.
5. **Shortlist** — saved targets with notes, priority, comparison and a route back to the listing/dossier.

### Visual and workflow design

- Information-rich market layout: top market context, distinct lane navigation, left filters on desktop, main player-led listings and detail/offer drawer or panel.
- Full listing card prioritises portrait, name, position, club, age, rating/potential where supported, actual asking price/valuation, contract status and action eligibility.
- Offer status is explicit and limited to server-supported states.
- Negotiation timelines distinguish event types and show time/context.
- Make active-club context unmistakable. Identify buyer/seller before consequential actions.
- Confirm acceptance, rejection, cancellation and consequential term submissions under the current interaction policy.
- Retain role/status-gated actions and accurate error messages. Do not present transfer success before API confirmation.
- Keep the financial player-share market separate and explain the handoff.

### Routing and data

React currently routes a general Market page at **/app/market**. Flutter’s dedicated transfer experience includes **GtexTransfersHubPanel** and the five segment model. Before implementation, inspect the canonical API/provider and route wiring for listings, offers, negotiations, window bids and shortlists. Reuse existing services and lifecycle rules. Do not create a parallel transfer engine or implement tabs backed by fake local arrays.

### Acceptance checks

- All five lanes have coherent loading, empty, error and populated states.
- Every consequential action identifies the player, clubs and terms involved.
- Sporting transfers cannot be mistaken for share trading.
- Existing lifecycle and permission tests continue to pass.

---

## 7. Screen contract: AI Newsroom

### Editorial hierarchy

The newsroom should look like a football publication/editorial desk, not a stack of same-sized filtered boxes.

**Desktop**
- Large lead story with editorial image, headline, category, timestamp and short standfirst.
- Two or three supporting story treatments with differentiated emphasis.
- Chronological news wire or results rail.
- Visible story filters and search where supported.
- Source/category context differentiates verified match events, club changes and editorial explanation.
- A story detail reading experience preserves provenance and context.

**Mobile**
- Lead story first, then an intentional single-column editorial sequence.
- Compact category controls with accessible overflow or a filter sheet.
- Headlines, timestamps and verified context remain easy to scan without sideways page overflow.

### Content grounding rules

- Ground stories in canonical event, ledger and pitch records. AI may narrate and contextualise; it must not manufacture scores, financial values, transfers, player gifts, facilities, dates or outcomes.
- Mark illustrative/generated editorial material as such if the source does not establish a real event.
- Preserve event-announcement policy: global instant announcements are reserved for designated high-significance events—private jet purchases, facility upgrades and owners gifting items to players. Ordinary luxury purchases must not become global breaking news.
- Keep public newsroom stories separate from the owner’s personalised private inbox, requests, unresolved issues and confidential scouting/contract information.
- Preserve filtering semantics and loading/empty/error states.

### Acceptance checks

- One lead story is clearly dominant; secondary stories do not compete equally.
- Provenance, timestamp and story type are visible.
- Private club-owner information never reaches global readers.
- Unverified stories are not styled as confirmed live events.
- Current grounding safeguards remain intact.

---

## 8. Screen contract: Owner Dashboard and role workspaces

### Owner Control Center

Replace the generic dashboard feeling with a club-owner command centre.

**First viewport**
- Active club identity: crest, club name, colours, status and competition/season where available.
- State-driven summary: what needs attention today, not generic welcome copy.
- Compact financial band using verified figures: available cash, meaningful obligations and actual TV/broadcast revenue when exposed by the API.
- Matchday spotlight: next scheduled fixture or latest result based on real data.
- Prioritised decision queue: pending owner requests, manager/staff recommendations, negotiations, unresolved issues or approvals genuinely available.
- Private inbox preview and action-needed count based on actual server state.

**Below the fold**
- Squad and manager state, only where supported by the model.
- Club operations/facilities and their real upgrade state.
- Financial trend or income composition only if valid history exists; distinguish actuals, estimates and forecasts.
- World activity/news relevant to the owner’s clubs without replacing the private inbox.
- Contextual actions based on selected club and role.

**Role-specificity**
- Admin, club owner and standard user are not the same dashboard with cards hidden. Use role permissions/capabilities to decide available information and actions.
- Empty states guide users towards a real next action.
- Do not display sample values, fake charts or invented tasks in live workspaces.

### Private Club HQ vs Public Club Home

Treat these as two deliberate experiences.

**Private Club HQ**
- Squad needs, manager and general-manager advice, finances, facilities, staff, transfers, owner inbox, problems, commitments and decision history.
- Show source/status of recommendations so owners can delegate or act.
- Surface financial implications of consequential actions before confirmation.
- Overview first, focused drill-downs after; do not force every management area into one giant dashboard.

**Public Club Home**
- Club crest, name, colours, identity and stadium presentation.
- Season summary, active competition, upcoming fixture/recent result, public squad highlights, history/honours and public news.
- A memorable club-specific hero, not just a private dashboard with another title.
- Use actual club branding, crest and kit/venue imagery when available. Generic decoration cannot substitute for identity.
- TV/broadcast revenue belongs in the owner’s financial model and public economics story only when the platform makes the amount public. Private balances, contract expectations, inbox, internal watchlists and confidential notes must never leak into public Club Home.
- Maintain privacy redaction for non-owners and shared-save participants.

### Acceptance checks

- The first viewport answers: which club, what is happening, what needs attention and what can I do next?
- Owner workflows are prioritised by actual state, not decorative hierarchy.
- Public profile is visually distinctive and exposes public fields only.
- Broadcast revenue is a named revenue stream only when backed by canonical economics data; never hard-code an amount.
- Existing ownership, manager, finance and action APIs remain authoritative.

---

## 9. Shell and navigation

The shell should support the experiences, not make every feature look like the shell.

- Keep navigation predictable, grouped by meaningful goals: Club HQ, Squad, Transfers, Regen World, Competitions/Matchday, Newsroom, Finances and Inbox.
- Keep labels short with clear active states. Avoid a long row of tiny, hard-to-control mobile tabs.
- Keep active-club context visible wherever actions depend on that club.
- Show wallet balances discreetly and accurately; avoid making every screen feel like a coin terminal.
- Ensure nested routes load on refresh and React Router basename handling remains intact beneath **/console/**.
- Do not silently remove or duplicate a route. Decide deliberately whether a screen lives in React, stays in Flutter, or uses a supported cross-app handoff, and document the decision.
- Do not change Render rewrites, Flutter root hosting, API origin or publishing as part of a visual-only change unless a separately reviewed architecture change calls for it.

---

## 10. Implementation sequence

### Phase A — Baseline and design lock

1. Confirm deployed React/Flutter route split and current main commit.
2. Run the React console locally and capture authenticated screenshots at **390×844, 768×1024 and 1440×900**.
3. Record route behaviour, data sources, loading/empty/error states and component reuse.
4. Produce target mockups or static prototypes for the signature surfaces: full player card, regen card, Owner Control Center first viewport, Regen World discovery, award spotlight, Transfer Hub listings/negotiation and newsroom lead layout.
5. Review those designs before refactoring screens. Prose alone is not visual acceptance.

### Phase B — Shared visual primitives, not a global template

1. Build/adjust tokens for colour, typography, spacing, media ratios, surfaces, borders, focus states and motion.
2. Implement full/compact player-card variants using canonical identity and portrait handling.
3. Implement distinct regen-card composition, preserving face-bank mapping and performance.
4. Standardise meaningful loading, empty, error, privacy and confirmation states.
5. Do not force all page types into the same panel layout.

### Phase C — Signature experiences

Implement in this order:
1. Player-card and regen-card foundation.
2. Regen World discovery and connected awards route using canonical regen API/provider models.
3. Transfer Hub using the existing transfer lifecycle and five lanes.
4. Newsroom editorial layout and story detail, preserving event grounding/privacy.
5. Owner Control Center and Private Club HQ.
6. Public Club Home with club-specific identity and privacy boundary.
7. Navigation, responsive polish and cross-route regression.

If discovery shows an API or route is missing, stop and report the dependency instead of inventing fake data or a parallel model.

---

## 11. Definition of done

A screen is not done just because it compiles or uses new colours.

### Visual review
- Screenshots exist at 390×844, 768×1024 and 1440×900 for every redesigned surface.
- Compositions are meaningfully different across cards, newsroom, market, awards and club dashboard.
- No clipped headings, awkwardly cropped portraits, horizontal page overflow or unreadable controls.
- The visual review compares implementation with design target and records deviations.

### Functional review
- Primary and secondary actions are real and connected to canonical APIs.
- Loading, empty, error, unauthenticated and permission-denied states are verified.
- Direct-load and refresh of nested routes work beneath /console/.
- Mobile tabs, filters and drawers work with touch and keyboard.
- Confirmations and server errors remain accurate; UI does not claim success early.

### Domain regression
- Regen identity, generation, image mapping, creation flow, season and award services remain intact.
- Player identifiers, profiles and dossier navigation remain stable.
- Sporting transfer lifecycle and financial player-share market remain separate.
- Club-owner privacy, public-profile redaction, balance and ledger semantics remain intact.
- TV/broadcast revenue is sourced from real economics data, not a frontend-only number.
- News events respect global-announcement policy and narration remains grounded in source events.
- Authentication, roles, payments and API environment remain unchanged unless separately reviewed.

### Delivery
- Antigravity reports changed files, canonical data source/API for each new surface, tests run, screenshots captured and unresolved dependencies.
- No claim of visual verification or production deployment without evidence.
- Use reviewable increments, starting with the signature card system and one representative page rather than one opaque all-at-once change.

---

## 12. Implementation-agent work order

Implement the GTEX Experience Design Reset specified in this document.

Before editing, inspect current main, deployment architecture, React /console/ route table, existing Flutter routes, canonical API/provider models and existing concept card files. Confirm which features exist in React and which exist only in Flutter. Do not assume feature parity.

Build screen-specific design targets and baseline screenshots for the player card, regen card, Owner Control Center, Regen World, Regen Awards, Transfer Hub, AI Newsroom and Public Club Home. Do not begin with a global restyle that puts every page into the same panel template.

Preserve the single backend and canonical identity, auth/role, payment/ledger, regen-generation/face-bank, award-season, club privacy, news-grounding and transfer-lifecycle rules. Adapt concept visuals to real domain models. Do not copy demo data/types or add parallel business logic. Never use fake data to make a page look complete. If an endpoint or route is missing, report that dependency and propose the smallest compatible integration.

Implement reviewable increments. Start with full/compact player cards and a distinct regen card, then connect Regen World/Awards, Transfer Hub, Newsroom, Owner Control Center and Public Club Home with purposeful responsive layouts. Maintain explicit separation between private Club HQ and public Club Home, sporting transfers and player-share trading, and global newsroom stories and the owner’s private inbox.

Validate at 390×844, 768×1024 and 1440×900 with screenshots. Run relevant React build/tests and available domain regression tests; state honestly when tooling is unavailable. Verify nested routes beneath /console/, mobile/keyboard interactions, empty/error/loading states, image fallbacks and privacy. Do not claim visual acceptance or production deployment without evidence. Do not alter Render routing or Flutter root deployment during a visual-only change.

Deliver a summary mapping acceptance criteria to evidence, including screenshots, tests, canonical API/service used, changed files, unresolved dependencies and regressions. Do not merge until visual and domain review is complete.

---

## 13. Scope boundaries

This brief does not authorise:
- replacing backend services or creating a second source of truth;
- changing payments, wallets, coin rules, settlement or ledger contracts;
- replacing regen face-bank mappings or player IDs;
- exposing private club-owner data on public pages;
- fabricating fixtures, awards, player stats, prices, balances or news events;
- collapsing sporting transfers into financial share trading;
- switching the production site root away from Flutter or altering /console/ deployment topology as an incidental UI fix.

The goal is a more imaginative, coherent GTEX—not a shell rewrite that makes the product less complete or less trustworthy.
