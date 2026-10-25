# GTEX Shell Audit & Cross-Platform Experience Blueprint

**Audit snapshot:** 19 October 2026
**Repository:** `wandemcphill/Global-Talent-Exchange`
**Reviewed commit on main:** [`19f4bce49839e138cca086e8079212c38250a4f4`](https://github.com/wandemcphill/Global-Talent-Exchange/commit/19f4bce49839e138cca086e8079212c38250a4f4)
**Purpose:** Audit the current Flutter and React shells, identify the real systems already available for GTEX storytelling, and propose one coherent cross-platform shell that makes the football world, club stories and user decisions easy to discover.

---

## Executive Summary

Do not rebuild the GTEX frontend from scratch. Do not start a major Unity storytelling project. Treat this as a product-shell and event-presentation upgrade over GTEX's existing systems.

Use the Emergent-derived React shell as the visual/interaction reference for the desktop owner experience, and bring its visual hierarchy into Flutter using the existing `ui_gtex` design system. Keep each frontend native to its platform and preserve the existing backend, player and regen pipelines, face-bank rendering, competition logic, 2D match experience and currently working feature routes.

The product should feel like one living football universe with three connected spaces:

1. **The World** — public football news, live world activity and eligible breaking announcements.
2. **My Club** — each owner's distinct club story, schedule, history, assets, staff and problems.
3. **My Inbox** — private, actionable issues for this owner, filtered to the active club or all clubs the owner controls.

The same verified game event can appear in multiple places, but each projection serves a different purpose. A public announcement is not a private decision. An article is not an inbox item. A club timeline is not a second source of truth.

---

## 1. Scope and Confidence

This was a source-level audit of the current `main` commit, including Flutter routing and shell components, React routes and navigation, story/inbox clients, backend story and owner-console models, and relevant existing design/audit documents.

I did not complete a live authenticated browser session or production interaction test: deployed pages were not accessible to the browser tool in this pass. Consequently, statements below distinguish directly inspected code from older audit-document findings. I did not modify code, run the app, run test suites, change database schemas, or commit anything.

Key inspected sources:
- Flutter app entry point: `frontend/lib/app/gte_frontend_app.dart`
- Flutter router: `frontend/lib/router/app_router.dart`
- Flutter route inventory: `frontend/lib/router/app_destinations.dart`
- Flutter shell: `frontend/lib/ui_gtex/layout/gtex_app_shell.dart`
- Flutter world-pulse widgets: `frontend/lib/features/world/widgets/football_world_pulse_widgets.dart`
- Flutter world-pulse provider: `frontend/lib/features/world/providers/football_world_pulse_provider.dart`
- Flutter News Agency: `frontend/lib/features/news_agency/presentation/news_agency_screen.dart`
- React route map: `frontend/react-shell/src/App.tsx`
- React AppShell: `frontend/react-shell/src/components/gtex/AppShell.tsx`
- React Inbox: `frontend/react-shell/src/pages/InboxPage.tsx`
- Backend Story Feed service: `backend/app/story_feed_engine/service.py`
- Backend owner inbox and Control Center routes: `backend/app/owner_console/router.py`
- Existing visual-language decisions: `docs/audits/gtex-product-parity-ux-baseline.md`

---

## 2. Current Shell Architecture

### Flutter
Flutter is the main web app at `/` and is also the native-app foundation. The app uses `go_router`, Riverpod and `GtexAppShell`. The route inventory documents a much wider feature surface than the React console, including Home, Matchday, Market, World, Regens, transfer listings, federations, national teams, coaches, lineup, tasks, profile and competitions. The current shell also supports a responsive bottom navigation and a desktop navigation rail.

The canonical route inventory documents 32 primary-surface definitions, while the route catalog and router contain many more deep links and feature-specific routes. Older repository audit documents count 93 explicit GoRouter routes and 100 navigable surfaces when the feature-route registry is included; treat those as inventory figures, not proof that every feature is polished or production-verified.

### React
React is published as the separate `/console/` experience beside Flutter at `/`. It uses the same canonical GTEX API; it is not a second backend. The React shell is a narrower owner-management console. Current visible navigation includes:
- Control Center
- My Clubs
- Market & Transfers
- Competitions
- Manager & Squad
- Academy / Regens
- National Team
- Finance
- Inbox
- Admin Review for authorised admins

It has a compact dark-navy visual language with emerald active states, a left desktop sidebar, top-bar club switcher and currency balances, and a horizontal scroll strip for mobile navigation. It has useful owner-specific panels but does not currently expose a full Newsroom, World Pulse, Club Story timeline, or a dedicated prestige-asset purchase page in its route map.

### Design Foundation Already in GTEX
GTEX already has its own semantic design system: `GtexColors`, `GtexSpacing`, `GtexText`, `GtexPanel`, `GtexActionButton`, player-card primitives and the “Living Football OS” visual language. The documented design principles are sound: identity before inventory, make the next football decision primary, make ownership tangible, and never fake live state.

**Recommendation:** Extend these primitives and tokens; do not introduce a third unrelated design language. React can lead the desktop composition while Flutter implements platform-appropriate counterparts.

---

## 3. Audit Findings

*Severity here describes the impact on the shell/storytelling goal, not overall platform security.*

### P0 — The two shells do not yet present one coherent GTEX world
Flutter has the broader route and feature catalogue; React concentrates on the owner-console vertical. Their primary navigation does not offer the same product map. A user switching between the Flutter web app and React console can encounter different discovery paths for the same game systems.

- **Impact:** The product feels fragmented, and adding the newsroom in only one shell would deepen the split.
- **Action:** Establish one cross-platform information architecture and route/feature manifest, then implement the same information scent in both shells. Keep the native interaction patterns and existing URL paths; do not force Flutter and React to share component code.

### P0 — Flutter's `/inbox` path does not mean the same thing as React's owner inbox
The current Flutter `app_router.dart` redirects `/inbox` to Community. React has `/app/inbox`, which reads the private owner inbox from `/owner/inbox`. Flutter has owner-decision/inbox content within its owner console, but the standalone inbox path is not aligned to the private owner inbox.

- **Impact:** A critical football-management feature is easy to miss, and the two clients disagree on a basic destination.
- **Action:** Make Inbox a first-class destination in both shells. Retain old routes as safe aliases where necessary, but ensure the canonical inbox opens private owner items, not Community. Community and discussion threads should remain separate destinations.

### P0 — There is a world-pulse ticker, but it is not yet the requested breaking-announcement service
Flutter's `FootballWorldPulseTicker` currently assembles a compact rail from transfer listings, competition countdowns and global-activity summaries. The wider `FootballWorldPulseRail` contains transfer activity, negotiations, countdowns, market movers, discussion previews, rivalry activity, ranking movements and online competitions/clubs. This is valuable infrastructure, but these items are aggregate activity indicators rather than a durable, event-specific public announcement stream.

The shell's fallback pulse strip can also show current section/module badges rather than transaction announcements.

- **Action:** Reuse the existing strip and shell placement, but connect a new event-delivery projection to it. Do not build a brand-new ticker UI detached from the current shell.

### P0 — Story systems exist, but the newsroom does not represent all GTEX activity in one user-facing story experience
The durable Story Feed already stores published stories and supports idempotent publication, featured status, scheduled stories, rejection/moderation, and a digest endpoint. The Flutter News Agency reads `GET /api/story-feed`, supports category filtering/search, and has loading, error and empty states. The Home story ticker provider also reads the same feed.

Separately, World Pulse derives activity from the market, world/regen data, competitions and community threads. Older source audits also identify additional news-like surfaces such as `legend_layer` news, `ai_reporter`, and the viral feed. These are different product inputs; they are not yet clearly presented as one navigable newsroom taxonomy.

- **Action:** Unify the presentation and event references first. Keep specialised domain services if they remain authoritative; route their verified stories into the durable Story Feed/experience layer rather than creating another independent newsroom engine.

### P1 — React needs the world and club-story surfaces, not just management tabs
The React route map contains no first-class routes for Newsroom, World Pulse, Club Story/timeline or the owner prestige-asset catalogue. Control Center does show fixtures, club health, economy, decisions and a latest-inbox panel, which is a good basis for a personalised command centre, but the public world narrative is largely absent from its shell-level navigation.

- **Action:** Add the World/Newsroom and Club Story destinations, and make public news, personal club history and private decisions visibly distinct.

### P1 — Active-club context is not consistently carried through the Flutter legacy owner desk
The React shell has a club switcher. In Flutter, `OwnerConsoleApi.fetchShowroom()`, `fetchDesk()` and `performDesk()` select `clubs.first` returned by the Control Center rather than receiving the currently selected club ID. That means these showroom/desk operations can resolve to the first club even when a user expects to be acting on another club.

React's current private inbox also queries by status and current user but does not expose a club filter in the Inbox page, although the underlying `OwnerInboxItem` records have an optional `club_id`.

- **Action:** Make active-club context an explicit navigation/session dependency in both clients. Inbox must offer Active Club and All My Clubs views. Every action must carry the chosen club ID all the way to the backend; never silently substitute the first club.

### P1 — Prestige asset purchase and gifting are not proven end-to-end from the owner shell
The backend contains the catalogue/asset purchase and gift functions and separate owner routes for purchase/gift resolution. However, the generic `perform_desk_action` operation accepts actions such as hiring, sponsor offers, manager offers, cases, auction listing and bidding; it does not accept `purchase` or `gift`. The Flutter owner desk sends generic desk actions through this route. An older comprehensive audit flagged this gap; the inspected backend action dispatcher confirms it remains relevant.

- **Impact:** A visual shell can advertise the action while the canonical transaction path is still unwired. It would also be premature to claim that the new announcement can fire on a successful purchase/gift until the real transaction path has an event hook.
- **Action:** Wire the owner-facing catalogue to the canonical asset purchase/gift APIs (or explicitly add and test the appropriate action dispatch). Preserve ledger, ownership, supply-cap and idempotency checks. Publish a story/announcement only after the transaction has committed successfully.

### P1 — Story-feed records are not sufficient by themselves to model all shared-save and club-specific story scopes
`StoryFeedItem` has audience, subject type/ID, country, metadata, featured and moderation fields. The story bridge for general newsroom items records club information in metadata, while using the news-engine source/ID as the subject for non-player stories. The public feed endpoint can filter by story type, country, subject and featured status, but reliable club filtering needs a normalised relationship or a deliberate, tested metadata/query contract.

The `OwnerInboxItem` model has `user_id` and optional `club_id`, which is a good starting point for private ownership-specific information, but the inspected story/inbox models do not themselves expose a shared `save_id`/`world_id` field.

- **Action:** Before implementing shared multi-owner saves, identify the canonical GTEX world/save entity (if one exists elsewhere) and make every new event projection carry its scope. Do not make the public ticker global across unrelated saves by accident. A saved-world participant should see public events for their shared save; a private scouting report or negotiation should remain visible only to the relevant owner(s).

### P1 — Some existing content can vanish quietly from the Home ticker
Flutter's `storyFeedTickerProvider` returns an empty list on any feed error. That prevents a broken feed from crashing Home, but can make “the newsroom has no stories” look the same as “the story service failed”. The dedicated News Agency is more explicit about error and retry states.

- **Action:** Preserve resilient Home loading, but make the story module's state visible: loading, no stories yet, connection unavailable, and ready should look different. Never fabricate a story to fill the space.

### P2 — Mobile React navigation is currently too flat and too easy to miss
React places all primary destinations in a horizontally scrollable navigation row on small screens. This is compact, but some destinations are off-screen until the user scrolls and the hierarchy is flat. Flutter already uses an adaptive shell with bottom navigation for compact layouts.

- **Action:** Use five stable mobile anchors plus a labelled “More”/secondary destination sheet. Give Inbox an unread/action count and keep global announcements visible without occupying a full-screen modal.

### Documentation Hygiene — Deployment Alignment
The older `GTEX_COMPREHENSIVE_PLATFORM_AUDIT.md` says React at `/console/` is not deployed and references an unmerged deployment change. The current root `README.md` and `docs/REACT_CONSOLE_RENDER.md` describe both apps being published in the same static site, with Flutter at `/` and React at `/console/`; `App.tsx` imports the `ROUTER_BASENAME` used for nested deployment. The older audit's deployment statement should not be treated as present truth without reconciliation.

- **Action:** Maintain one dated, commit-pinned frontend architecture baseline. A code-path audit should supersede older observations when the deployment architecture changes.

---

## 4. What GTEX Already Has That We Should Reuse

| Existing Capability | Current Location / Contract | Use in the New Shell |
| :--- | :--- | :--- |
| **Cross-platform shell primitives** | Flutter `GtexAppShell`, `ui_gtex`, semantic theme tokens | Extend the existing shell; add equivalent React primitives and matching tokens |
| **Public story feed** | `GET /api/story-feed`, `GET /api/story-feed/digest` | Canonical article list and newsroom source |
| **Story publication/admin moderation** | `/api/admin/story-feed` and schedule/reject endpoints | Reuse moderation and scheduling instead of creating a second CMS |
| **AI-news and regen story bridges** | `backend/app/story_feed_engine/bridges.py`, regen-universe publisher | Preserve verified story sources and event provenance |
| **World Pulse** | `FootballWorldPulseTicker`, `FootballWorldPulseRail`, `footballWorldPulseProvider` | Keep market/world/community signals alongside true breaking notices |
| **Owner inbox and decisions** | `/owner/inbox`, `/owner/inbox/{id}/decide`, `OwnerInboxItem` | Real private tasks, decision buttons and resolution state |
| **Decision timers and warnings** | `backend/app/owner_console/alerts.py` | Show deadlines, six-hour warnings and expired outcomes clearly |
| **Control Center data** | `GET /owner/control-center` | Home's live club, fixture, economy, health and inbox summary |
| **Facility upgrades** | Owner-console facility-upgrade route and facility services | Emit an event after a committed upgrade; link to project/facility view |
| **Asset purchase/gift domain logic** | `club_legacy` purchase/gift endpoints and ownership records | Wire the existing catalogue correctly; don't invent a parallel asset database |
| **Club / player / regen visuals** | Existing crests, player cards, regen cards and face-bank mapping | Use rich static images and existing identities; no Unity scene is required |
| **2D matches and available 3D match viewer** | Existing match routes/runtime | Preserve as match experiences; don't conflate match rendering with world-storytelling scenes |

---

## 5. The Proposed Shell

### Desktop and Large Tablet: One Football Command Workspace
Use a 240–256 px collapsible navigation rail at desktop width; a sticky top bar; a narrow global breaking-event strip beneath it; and a scrollable workspace with deliberate columns. The UI should be football-first, dark navy/charcoal with restrained pitch green/cyan and metallic gold for prestige—not a finance dashboard decorated with football icons.

#### Global Top Bar
- GTEX logo and current world/save name (when shared-save functionality is available)
- Season/day or current matchday context from the authoritative service
- Active club switcher (plus an explicit “All My Clubs” selection for aggregate views)
- Global search across players, clubs, regens, competitions and stories
- Inbox/notification controls with distinct unread and action-required counts
- Wallet/currency balance where useful, profile/settings and admin tools by permission

#### Breaking Strip
A slim, live, dismissible strip for qualifying public events only. It is not the same thing as the general World Pulse rail.

*Example:*
`BREAKING · CLUB LEGACY  Lagos Lions have purchased a Gulfstream G700 private jet for £72m.  View story →`

The message must come from a verified event record and the committed transaction. It should show club crest and an optional small static picture, support a click through to the story, queue multiple events without overlap, and remember which event IDs the client has already shown. It should never interrupt a match view with a blocking modal.

For the proposed rules, broadcast announcements to participants in the same shared save/universe. Do not leak an event from one isolated save into a different save unless GTEX explicitly defines the world as globally shared.

#### Navigation Map
Organise the desktop rail into labelled groups rather than one flat list:

**COMMAND**
- Home / Command Centre
- Inbox (with action-required badge)

**WORLD**
- Newsroom
- World Pulse
- Matchday & Results
- Competitions
- World / Regens / National Teams / Federations

**MY CLUB**
- Club HQ
- Squad & Staff
- Academy & Regens
- Recruitment & Transfers
- Club Story (timeline)
- Facilities & Prestige Assets
- Finance & Sponsorship

**COMMUNITY**
- Fan activity / discussions / rivalry / creator surfaces that are confirmed live

**ACCOUNT / ADMIN**
- Profile, settings and verified admin destinations (role-gated)

Keep two different concepts explicit in naming: **Player Market** (player cards/shares/market trading) and **Transfer Room** (football squad recruitment and club-to-club transfers). Avoid hiding one under a vague “Market & Transfers” heading if they involve different user intents or economic rules.

### Mobile: Keep Five Stable Anchors, Not Nine Horizontal Labels
Recommended bottom navigation:
1. **Home**
2. **Inbox** (unread/action count)
3. **My Club**
4. **Matchday**
5. **World**

Search, Market/Transfers, Competitions, Squad, Academy, Finance, profile and other routes live in a labelled “More” sheet/drawer and in relevant contextual quick actions. The top bar keeps a small club switcher and notification affordance. Breaking announcements appear as a compact banner/toast with a clear “View” action, not an obstructive popup.

Flutter uses its native bottom navigation and adaptive shell; React uses an equivalent mobile bottom bar. Both should share the same labels, groupings, permissions, badges and semantics even though the components differ.

---

## 6. The Four Key Destinations

### A. Home / Command Centre — “What matters to me today?”
The dashboard should tell users what has happened, what matters now, and what they can do next. Put the club identity and next decision before wallet statistics.

#### Above the fold
- Club crest, name, owner's identity and club status
- One primary next action (for example, “Respond to contract offer by 18:00”)
- Next fixture / live-match status
- Top one or two new stories with rich static images

#### Below the fold, responsive columns
- **Needs your decision:** the most urgent inbox items, with due time and action buttons
- **World today:** two or three public headlines from the existing Story Feed
- **Your club's latest:** club-specific timeline items, not generic filler
- **Matchday:** next fixture, latest result and direct link to existing 2D match experience
- **Squad pulse:** injuries, player morale/contract status or regen milestones, only when real data exists
- **Club operations:** facility projects, budget/sponsorship requests and scheduled meetings
- **World pulse rail:** transfer/competition/activity signals from the existing pulse provider

Avoid turning the page into a grid of every possible module. Show two or three items per module and link to a full destination. Prioritise urgent matters above “interesting but not actionable” stories.

### B. Newsroom — “What is happening in the football world?”
Build one editorial home for public stories. Keep its feed backed by GTEX's existing Story Feed and bridge verified outputs from current specialist engines. Do not place private inbox items in this public feed.

#### Tabs / filters
- Top Stories
- Breaking
- My Club (public stories about the selected club)
- Transfers
- Rising Regens
- Competitions & Matchday
- Club Legacy (eligible public purchases, upgrades and gifts)
- World / National Teams

#### Story card
- Category/urgency label and publication time
- Rich static hero image, club crest or player portrait
- Headline and short summary
- Relevant entities (club/player/competition) as tap-through links
- A “why this matters” context line where the source data supports it
- Click to read the full article and inspect related records

The newsroom should avoid publishing a generic AI article for every state change. Public editorial stories should follow configured newsworthiness rules. Ordinary luxury purchases do not become breaking news just because they exist in the database.

### C. Inbox — “What needs my attention?”
This is an action workspace, not another news feed. Every message is private to the owner, and some messages may be specific to one club.

#### Default screen
- Active Club / All My Clubs switch
- Needs Action, Messages, Scouting, Contracts, Staff & Board, Schedule, Completed filters
- Sort by priority, response deadline and newest
- Search and archive/completion state

#### Each inbox card should show
- Category, sender and the club it belongs to
- Player/staff/club picture or crest where helpful
- One-sentence request, why it matters and the actual deadline
- Clear options such as approve, negotiate, reject, shortlist, request a report or open the relevant screen
- The resulting outcome after a decision is recorded

The current backend already models decision items, action options, resolution state and response windows. The shell should visualise them well rather than re-implement decision logic on the frontend. An inbox item can expire according to the domain's defined safe default; the UI must disclose the deadline and consequence clearly.

### D. My Club / Club Story — “What is the story of this club?”
Each owner's club should have a persistent story page, made from verified events and the club's actual state.

#### Club header
- Crest, club name, owner, status, league/competition context
- Club colours and existing identity assets
- Key real metrics only: reputation, trophies, current budget, stadium/facilities, next fixture

#### Tabs
- Overview
- Story Timeline
- Inbox for this club
- Squad & Staff
- Schedule
- Facilities & Prestige
- Transfers & Scouting
- Finances & Sponsorship
- Legacy / Honours

#### Timeline event types
- Transfer and contract events
- Manager/General Manager/Head of Youth Development decisions
- Player gifts and accepted/declined gift state
- Facility upgrade requested, started and completed
- Prestige asset purchase, transfer and gift
- Match results, competition milestones and trophies
- Sponsorship, budget and financial milestones
- Player morale, injury or development events where backed by real game state

Each entry gets a static editorial picture or relevant portrait/crest, a date/season context, a link to the affected entity, and visibility labeling such as Public, Club only or Private decision. An owner should be able to see the whole club's story without exposing another owner's confidential scouting or negotiation information.

---

## 7. Event-to-Story Rules for the Requested GTEX Experience

The important architecture rule is **one authoritative game event, multiple purpose-specific projections**. The story generator does not own the game state; it narrates an already committed fact.

| Verified Event | Instant Top Ticker | Public Newsroom Article | Club Timeline | Private Inbox |
| :--- | :--- | :--- | :--- | :--- |
| **Club buys a private jet** | Yes, after successful purchase commits | Yes, queued/generated after the ticker | Yes | Receipt/asset result if useful; not necessarily a decision item |
| **Club upgrades a facility** | Yes, on the successful upgrade event defined by GTEX | Yes, where news rules allow | Yes | Project/deadline or completion message where relevant |
| **Owner gifts a player a watch or other item** | Yes, after successful gift/transfer is recorded | Yes, with the player's club context | Yes | Gift outcome/acceptance state where relevant |
| **Owner merely buys an ordinary luxury item for personal use** | No | No automatic public story | Private owner asset history, if it is a club/owner-held asset | Receipt only if useful |
| **General Manager asks for more budget or new players** | No | No, unless a later public event makes it newsworthy | Yes, marked club-only | Yes, action required, with options/deadline |
| **Regen refuses a contract renewal** | No automatic breaking ticker | Maybe later, if the game rules make the refusal publicly newsworthy | Yes, club-only at first | Yes, for the affected owner/club |
| **Other club buys a jet** | Yes for participants in the same public/shared world scope | Yes | Visible on public world/club story if permitted | Private inbox only if relevant to this owner (watchlist, rivalry, scouting, etc.) |
| **Scout update about a shortlisted player** | No | Not automatically | Only if connected to club recruitment timeline | Yes, only to the relevant owner/club |
| **A player becomes a public rising regen star** | Existing newsroom/world feed path; ticker only if explicitly configured as a breaking category | Yes | Visible as a world story, and on the club timeline if relevant | Personal alert only for relevant shortlist/watchlist context |

### Technical Delivery Sequence
1. The domain command validates permissions and commits the actual transaction/state transition.
2. The same transaction emits a durable event/outbox record with a unique `event_id`, event type, world/save scope, club/player/asset IDs, verified monetary fields and visibility policy.
3. After commit, the event dispatcher delivers the eligible announcement to the participants of that world/save. Prefer the existing real-time delivery infrastructure if one is present and suitable; otherwise add a supported server push (WebSocket/SSE) or outbox-backed delivery. A pure frontend timer is not enough for an immediate multi-user announcement.
4. The client deduplicates by `event_id`, shows the compact strip and links to the event/story.
5. The newsroom worker generates an editorial article from the verified payload and stores it through the existing Story Feed service. If AI generation fails, keep the committed announcement and offer a deterministic factual fallback or retry; never invent missing price/model/player facts.
6. The club timeline receives the event. An owner inbox item is created only if a person needs to read, decide or respond to something.

**Idempotency matters:** retries must not debit the owner twice, send the banner twice, create duplicate stories, or duplicate player gifts. An announcement must never appear before the underlying purchase/gift/upgrade has committed.

### Scope and Privacy
A single fact can be public within a shared save, private to one club, or private to one owner. Visibility must be decided by the event policy, not by whichever screen happens to render it.

The audited `StoryFeedItem` and `OwnerInboxItem` surfaces do not themselves provide an explicit save/world identifier. Confirm whether another canonical save/universe model exists before adding one; if it does not, implement that scope deliberately before shared-save broadcasts. Never broadcast one private save's events into another.

---

## 8. Cross-Platform Visual System

### Shared Visual Rules
- **Canvas:** deep navy/charcoal, restrained stadium-light gradients, faint pitch/tactical texture only behind low-density areas.
- **Accents:** emerald/pitch green for live/positive football state; cyan for world/market information; muted gold for legacy/prestige; amber/red only for real urgency/risk.
- **Typography:** strong condensed display type for club/story headlines, highly readable body type for inbox decisions, monospaced numerals only for compact values/ledger references.
- **Imagery:** use existing player portraits/face bank, club crests, static jet/watch/car/facility product renders, stadium images and reusable editorial image treatments. No interactive 3D scene is required for this plan.
- **Cards:** image + category + headline + consequence/action. Avoid decorative empty cards and overuse of tiny bordered boxes.
- **State design:** distinct loading, no-data, unavailable, permission-locked and success states. Do not render missing values as zero or fill empty news with invented headlines.
- **Accessibility:** large tap targets, visible focus state, screen-reader names for icon-only controls, text labels for urgency, reduced-motion preference and adequate contrast.

### React Implementation
Keep the current React/Tailwind/Lucide foundation. Refactor `AppShell` into clear units:
- `WorldScopeBar` (save/day and selected club context)
- `BreakingAnnouncementStrip`
- `PrimaryNavigation` with desktop groups and a dedicated mobile bottom bar
- `GlobalSearch`
- `NotificationInboxActions`
- `PageHeader` / `HeroStoryCard` / `TimelineItem` / `DecisionCard` / `EmptyState`

Use the existing `@/lib/api` and TanStack Query. Add routes for `/app/newsroom`, `/app/world`, `/app/club-story` (club-scoped or a route parameter), and improve `/app/inbox` filtering. Keep old route URLs working; do not create a second API client, ledger or auth source.

### Flutter Implementation
Keep `GtexAppShell`, `GtexColors`, `GtexSpacing`, `GtexPanel`, current route guards, Riverpod providers and native navigation patterns. Replace the ticker's data content with the event-delivery stream while retaining useful World Pulse signals and rail. Introduce matching reusable Flutter widgets for hero story cards, inbox decision cards, club timeline events and the world/club visibility chip.

Make Newsroom and Inbox first-class discoverable routes. Re-route `/inbox` to the real owner inbox, keeping Community under its own route. Do not remove any live/deep routes without a route manifest and regression coverage.

---

## 9. Recommended Implementation Order

### Phase 0 — Baseline and parity map
- Pin the main-branch revision and create one current shell/route inventory.
- Tag every route as live and tested, live but not recently verified, deep link, permission-gated, placeholder/blocked, or legacy alias.
- Resolve documentation that contradicts the current deployment.
- Confirm the canonical world/save ownership model and available real-time server-push mechanism.

*Exit gate:* a route matrix for Flutter and React; no critical feature removed; a test plan for current deep links.

### Phase 1 — Fix the foundations
- Align the private Inbox entry point across shells.
- Pass active club context into Flutter owner showroom/desk operations rather than defaulting to `clubs.first`.
- Add active-club / all-clubs filtering to private inbox.
- Wire asset purchase and gift actions to real catalogue endpoints and test the ledger/ownership/idempotency path.
- Normalise the club relation on story records or provide a tested way to query club-specific stories.

*Exit gate:* owners can safely switch between two clubs, act on the intended club, and see only authorised inbox items; purchase/gift works end-to-end or is truthfully marked unavailable.

### Phase 2 — One public story experience
- Add Newsroom/World/Club Story routes to React and primary discoverability in Flutter.
- Reuse the existing Story Feed, digest, newsroom bridge and world-pulse providers.
- Build rich-picture cards and an editorial story detail page.
- Add club-story filtering from canonical structured relationships, not headline-string matching.

*Exit gate:* stories from currently enabled sources appear once with source, timestamp, category, related club/player and correct visibility; empty/error/loading states are distinct.

### Phase 3 — Instant announcement events
Start with one vertical slice: club purchases a private jet. Then apply the same pattern to facility upgrade and owner-to-player gift.
- Implement durable event/outbox record and stable `event_id`.
- Emit after successful commit, dispatch to the right world/save participants, show a compact ticker in React and Flutter, and track deduplication.
- Queue/generate the newsroom article after the immediate banner.
- Add the record to the correct club timeline.

*Exit gate:* banner arrives to another signed-in participant in the same save within the agreed latency target; a participant in a separate save does not receive it; no duplicate banner/article; a failed transaction produces no announcement.

### Phase 4 — Complete the owner story workspace
- Make club timeline filters and links to the underlying players, staff, facilities, finances and transactions.
- Surface contracts, GM/HYD requests, scouting, schedule and club issues as actionable inbox items.
- Add role-aware personalization without allowing the AI to make owner decisions.

*Exit gate:* every card has a valid action/deep link or is clearly informational; decision outcomes refresh the inbox, club details and timeline; public stories never expose private inbox content.

### Phase 5 — Visual validation and regression
Test both Flutter and React at:
- `390 × 844`: phone
- `768 × 1024`: tablet / narrow desktop
- `1440 × 900`: desktop

Test at least: first-time user with no club, owner with one club, owner with multiple clubs, admin, empty newsroom, unavailable story API, pending decision, expired decision, eligible jet purchase, ordinary luxury purchase, facility upgrade, player gift and two participants sharing one save.

Run the relevant frontend and backend tests in the repository before claiming an implementation is complete. Static review is not a substitute for authenticated browser validation.

---

## 10. Acceptance Criteria — What “The Perfect Shell” Means

1. A first-time user can understand where to go in under a minute: Home, Inbox, My Club, Matchday, World and More are obvious.
2. Public world events, public articles, club-only history and private decisions are visually distinct and correctly scoped.
3. The three global announcement triggers are precisely controlled: private jet purchase, facility upgrade, player gift. Ordinary luxury purchases do not fire the global ticker.
4. Each event is based on authoritative backend state and has a deep link to the relevant entity/transaction/story.
5. Every owner has a unique club story and private inbox. In a shared save, public world state is shared but confidential scouting and club decisions remain private.
6. Changing the selected club changes all relevant summaries, timeline views and action targets. No operation silently defaults to the first club.
7. No fake fixture, AI-created price, invented club reaction or fabricated player state is rendered when data is missing.
8. The same action works consistently in Flutter and React; the surfaces use one canonical backend action and ledger.
9. Static rich pictures make the world feel premium without adding a new Unity storytelling workload.
10. Existing regens, portraits, face-bank mapping, 2D match gameplay, current match viewer routes and working features remain intact.

---

## Final Recommendation

Make the shell the storytelling layer, not the gameplay engine. First fix cross-shell navigation and active-club context, then wire the existing public Story Feed, World Pulse and private owner inbox into one clear experience. Add the new event/outbox delivery path for the three approved broadcast event types, using static rich pictures in the cards.

This approach gives GTEX a visible, living football world while preserving the game logic that already exists. It is a staged shell and event-system upgrade—not a rebuild of GTEX and not a new Unity project.
