# GTEX — Full App Audit & Design Context

> **Purpose of this document.** GTEX (Global Talent Exchange) is a large, live football-economy application. This file is the single source of truth for two collaborators who do **not** have repo access:
>
> - **Stitch (Google)** — designs the UI/UX for every screen. Read Sections 1–6. Each screen has a self-contained design brief you can paste directly into Stitch.
> - **Claude** — implements the designs into the real codebase. Read Sections 7–9 for stack, routing, API surface, and per-screen wiring.
>
> The app today is built in **Flutter** (Dart, Riverpod, go_router) with a **Unity** 3D match engine in progress. ~98 screen widgets + ~112 additional screens exist across ~50 feature modules. This audit describes what exists, what is fragmented, and the target redesign.

---

## 1. What GTEX Is (read this first, Stitch)

GTEX is a **persistent, multiplayer football universe that behaves like a real economy.** Think "Football Manager × a real trading exchange × a creator/streaming platform," all in one live world.

Players (the humans using the app) take on one or more **roles**:

| Role | What they do |
|------|--------------|
| **Club Owner** | Own and operate a football club: squad, tactics, transfers, academy, stadium, finances, trophies, dynasty. |
| **Trader** | Buy/sell **player cards** and **club shares** on live markets; profit from valuations. |
| **Creator / Streamer** | Run creator leagues, monetize stadiums, sell fan shares, host streamer tournaments. |
| **Fan** | Predict matches, join fan wars, gift, climb leaderboards, follow clubs and creators. |
| **Coin Trader** | KYC-verified peer-to-peer on/off-ramp for the in-game currency (GTEX Coin). |
| **Admin / Federation** | Govern the world: competitions, economy rules, moderation, trust & risk ops. |

The world is populated by two kinds of footballers:

- **Real-name players** (licensed/real footballers) traded on the market.
- **Regens** ("sons") — AI-generated next-generation players with portraits, that users can **request/create**, develop, and trade. This is a signature GTEX mechanic.

**Two currencies:** **GTEX Coin** (gold, the hard economy currency) and **Fan Coin / Fan points** (blue, the social/engagement currency).

**Matches:** A **2D match experience exists today**; a **3D Unity match engine is in development** (some 3D routes render a "blocked / coming soon" screen). Matches are event-driven 15-minute simulations.

### The core problem the redesign must solve
The current app is **fragmented and administrative** — dozens of sibling screens and a navigation shell with abstract labels (*Transfer Hub, Matchday, Community, Club operations, Player universe, GTEX world*). It reads like an internal tool, not a living football world. The redesign should make GTEX feel **cinematic, alive, and legible**: one coherent universe where a new user instantly understands "own a club, build a squad, trade talent, compete, and rise."

### Brand voice
Confident, sporting, slightly editorial. Real football gravitas (broadcast graphics, matchday energy) fused with fintech/exchange precision (tickers, valuations, order books). Never cartoonish. Copy is punchy and declarative: *"Return to your club, market, wallet and football universe."*

---

## 2. Design System (Stitch style guide)

The existing design bible is a **professional football-economy system: dark institutional surfaces, semantic accents, no decorative neon/gloss.** Keep that DNA. Support both **dark (primary)** and **light** themes.

### 2.1 Color tokens

**Dark theme (primary / default):**

| Token | Hex | Use |
|-------|-----|-----|
| `bg/base` | `#0A0C0F` | App background (near-black, cool) |
| `bg/surface` | `#111418` | Cards, panels |
| `bg/elevated` | `#181C22` | Raised/overlay panels |
| `bg/overlay` | `#1E232B` | Hover / popovers |
| `bg/input` | `#1C2128` | Inputs |
| `bg/border` | `#262C36` | Hairline borders |
| `border/strong` | `#313844` | Emphasized borders |
| `text/primary` | `#F0F2F5` | Headlines, primary text |
| `text/secondary` | `#8A93A2` | Secondary text |
| `text/muted` | `#4A5568` | Muted/tertiary text |

**Light theme:**

| Token | Hex |
|-------|-----|
| `bg/base` | `#F4F6F9` |
| `bg/surface` | `#FFFFFF` |
| `bg/elevated` | `#F9FAFB` |
| `bg/border` | `#DDE1E8` |
| `text/primary` | `#0F1319` |
| `text/secondary` | `#4A5568` |

**Semantic / brand accents (shared intent; dark → light values):**

| Token | Meaning | Dark | Light |
|-------|---------|------|-------|
| `brand/pitch` | Primary green — football, live, positive, club-owner role | `#00C46A` | `#00924E` |
| `brand/coin` | GTEX Coin, trader role, gold/amber, prices | `#FFB800` | `#CC9200` |
| `brand/fan` | Fan coin, social, blue | `#3D7EFF` | `#2563EB` |
| `brand/alert` | Errors, blocked, negative | `#FF4D4D` | `#DC2626` |
| `brand/warn` | Warnings, locked, pending | `#FF9500` | `#D97706` |
| `accent/violet` | Admin role | `#E040FB` | — |
| `accent/creator` | Creator role | `#00B4D8` | — |

**Role accents** (used to theme role-specific surfaces): Admin = violet `#E040FB`, Club Owner = pitch green, Trader = coin amber, Creator = cyan `#00B4D8`, User = `#8A93A2`, Guest = `#4A5568`.

**Position colors** (player cards / pitch): GK = amber, DEF = blue, MID = green, ATT = red.

**Status:** live = green, locked = warn-orange, blocked = red, idle = muted, loading = blue.

> Rule from the design bible: **no decorative neon, gradients-for-gradient's-sake, or gloss.** Accents are semantic and load-bearing. Use color to communicate role, currency, and match state — not decoration.

### 2.2 Typography

Two display + one mono + one body family:

| Family | Role |
|--------|------|
| **Barlow Condensed** | Display / headlines / big numbers on cards & scoreboards (`w600–w700`). Condensed = broadcast/sporting feel. |
| **Inter** | Body, labels, UI text. Body line-height 1.4–1.6. |
| **DM Mono** | Numeric/tabular data — **prices, valuations, coin balances, scores, timers, order books.** Always tabular figures. |

Scale (px): Display 2XL 56 / XL 40 / LG 32 / MD 24 / SM 18 · Body LG 16 / MD 14 / SM 12 · Label LG 14 / MD 12 / SM 11 (letter-spacing 0.4, uppercase for eyebrows) · Mono XL 28 / LG 20 / MD 14 / SM 12.

**Rule:** any economic number (money, coins, %, valuations, scores, clocks) renders in **DM Mono** with tabular figures.

### 2.3 Spacing, radius, elevation
- Spacing scale: 4 / 6 / 8 / 12 / 16 / 20 / 24 / 32.
- Radius: cards ~12–16px, chips/pills fully rounded, inputs ~10px.
- Elevation via subtle border + very soft shadow (`black @ 12–18% opacity, blur 12, y+4`). Avoid heavy drop shadows.
- Panels: 1px `bg/border` hairline is the default separator, not shadows.

### 2.4 Signature UI vocabulary (reusable across the app)
These recurring elements should be designed once and reused. Stitch should treat these as a component kit:

- **Player Card** — portrait, name, position pill (position color), overall rating, club badge, live valuation (mono, with up/down delta), and a rarity/regen indicator. The flagship object of the app.
- **Coin chip / balance pill** — currency icon + mono amount; gold for GTEX Coin, blue for Fan Coin.
- **Valuation delta** — mono number with ▲green / ▼red and a tiny sparkline.
- **Status chip** — live / locked / pending / blocked, using status colors.
- **Metric tile** — big mono number + small uppercase label (used on dashboards).
- **Match scoreboard strip** — two badges, score in Barlow Condensed, live minute in mono, competition label.
- **World Pulse ticker** — a live horizontal ticker/rail of world events (transfers, goals, market moves) — a signature ambient element in the current shell. Keep it.
- **Panel** — bordered surface with header (eyebrow label + optional action) and body.
- **Role badge** — colored pill indicating the actor's role.
- **Leaderboard row** — rank, avatar/badge, name, mono metric, delta.

---

## 3. Global Information Architecture

### 3.1 Current (fragmented) navigation
The live shell exposes 7 abstract primary destinations: `home`, `market`, `competitions`, `hub`, `community`, `club`, `wallet` — with wordy labels (Transfer Hub, Matchday, Community, Club operations, Player universe, GTEX world) plus a toolbar crowded with icon buttons (search, profile, creator request, creator community, notifications, transfer hub, admin, theme, ambient audio, capital/wallet, sign out). The **home destination is role-adaptive**: admins see the Admin Command Center, coin traders see a wallet/trader desk, club owners see their club dashboard, and everyone else sees the generic home.

### 3.2 Recommended target IA (redesign)
Collapse to a clean primary nav with human labels. Proposed 6 primary destinations + persistent utilities:

1. **Home** — the living GTEX world (your personalized front page).
2. **Play** — matches: today's fixtures, live matches, match center, 2D viewer (3D "coming soon"), competitions & tournaments.
3. **Market** — player card marketplace, transfer market, club sale market, creator/fan share markets.
4. **Club** — your club: squad, tactics/lineup, academy, identity, dynasty, finances, trophies.
5. **Discover** — regens/create-a-son, players, clubs, federations, world simulation, news agency, global search.
6. **Social** — viral feed, fan hub, fan wars, fan predictions, awards, creators.

**Persistent utilities:** Wallet (coin balances, always visible), Notifications, Global Search, Profile/Settings, and a role switcher. **Admin** is a separate gated surface, not a primary tab.

Keep the **World Pulse ticker** as an ambient live strip. Keep **role-adaptive Home**, but make the role switch explicit and legible rather than silently swapping the whole screen.

---

## 4. Screen Inventory (grouped by domain)

Every screen below exists in the codebase today (file paths in Section 8). "v2 / redesign" suffixes mean a newer iteration already exists — Stitch should design the definitive version. **P0** = design first (core loop), **P1** = important, **P2** = admin/ops/advanced.

### A. Onboarding & Identity — P0
- **Public landing** — logged-out marketing entry; explains GTEX, CTA to sign up / sign in.
- **Onboarding flow** — signup → club path → region selection → player shortlist → KYC → first competition. Guided, multi-step.
- **Login / Signup** (v2 exists).
- **Profile** — public + own profile, live profile, settings.

### B. Home — P0
- **Home** (living world front page) — role-adaptive. Personalized: your club snapshot, next match, market movers, rising regens, world pulse, news, leaderboards, tasks/daily challenges.

### C. Club (ownership & operations) — P0
- **Club owner dashboard (v2)** — command center: next match, form, squad health, finances, transfers, academy, trophies.
- **Club hub**, **Club screen**.
- **Lineup / tactics editor** — pitch formation editor, drag players into positions.
- **Squad registration** — register/lock squad for competitions.
- **Club growth** — academy: generate prospects, offer contracts, promote; staff hiring.
- **Club lifecycle** — advance club through eras/stages.
- **Club identity** — badge editor, jersey editor, identity preview.
- **Dynasty** — dynasty overview, era history, dynasty leaderboard.
- **Reputation / Prestige** — reputation screen + history, prestige leaderboard.
- **Trophies** — trophy cabinet, honors timeline, trophy leaderboard.
- **Club sale market** — list your club for sale, offers, inquiries, transfer ownership.

### D. Market & Trading — P0
- **Player card marketplace** — browse/buy/sell player cards; filters, order book, valuations.
- **Player market (redesign)** — the primary talent exchange browse experience.
- **Transfer market** — transfer listings.
- **Transfer center** — manage your transfers (in/out, offers, negotiations).
- **Transfer news calendar** — scheduled transfer windows/events.
- **Creator share market** — buy/sell shares in creators.
- **Fan share market** — buy/sell fan shares in clubs; distributions, holdings.
- **Portfolio** — your holdings across cards/shares.

### E. Players & Regens — P0
- **Player detail / profile (FM-style)** — flagship player profile: attributes, form, history, valuation chart, ownership, actions (buy/sell/offer).
- **Regen world** — browse AI-generated regens.
- **Create a son / Request a son** (v2) — request/generate a regen player (signature mechanic). Admin create-son variant too.

### F. Matches & Competitions — P0/P1
- **Match center (v2)** — hub for a match: pre-match, live, post-match.
- **Live match viewer** — 2D live match experience (3D Unity in progress → blocked screen for native 3D).
- **Match simulate / spectate / broadcast** — simulation, spectating, broadcast package, pre-match package.
- **Competitions hub (v2)** — leagues, cups, standings, fixtures.
- **Live competitions hub**.
- **Tournaments** — tournament intro, tournament screen, tournaments list.
- **National teams** + **national team rental** (rent players to national teams).
- **Federations / federation** — governance, proposals, votes, rankings, regional tournaments.
- **Football world simulation** — the macro world sim view.

### G. Social, Fans & Creators — P1
- **Viral feed** — social feed of clips/moments (clips 3D → blocked screen).
- **Social / fan hub (v2)** — community home.
- **Fan wars** — nation vs nation / rivalry competition with leaderboards.
- **Fan prediction** — predict match outcomes for rewards.
- **Awards (v2)** — award ceremony, categories, nominees, winners.
- **News agency (v2)** — in-world sports journalism/news.
- **Creator league admin**, **creator stadium monetization**, **streamer tournament engine**.
- **Tasks / daily challenges** — engagement quests.

### H. Wallet & Economy — P0/P1
- **Wallet overview (v2)** — GTEX Coin + Fan Coin balances, transactions, funding/withdrawal.
- **Funding flow** / **Withdrawal flow**.
- **Coin trader** (redesign) — P2P coin on/off-ramp: apply, rates, orders (accept/confirm/dispute/proof).
- **Matchday economy** — matchday-driven economic activity (tickets, predictions rewards, card listings).
- **Jackpot** — jackpot feature.
- **Gift economy** — gifting (catalog, combos).

### I. Discovery & Utilities — P1
- **Global search (redesign)** — search across players, clubs, creators, competitions.
- **Notifications (v2)**.
- **Agent conversations / chat** — messaging.
- **Referrals**, **support**.

### J. Admin & Ops (gated) — P2
Extensive admin surface (violet role accent). Key areas: **Admin command center**, launch control / feature flags, moderation, disputes, policies, risk-ops, trust-ops (KYC disputes, wallet orders), economy (burn events, gift combo/revenue-share rules, gift stabilizer), leaderboard season reset/archive, jackpot runtime/trigger, fan-prediction settlement, football-events engine (categories/effects/rules/review/severity), calendar engine (seasons, hosted/national competition launch), coin-trader admin (approve/freeze/reject, order resolution), fan-wars admin (nations cup, points, profiles, rivals), creator-league financials/settlements, creator share/stadium control, media-engine (broadcast modes, stadium controls, match analytics/settlement), streamer-tournament policy/risk/review/settle, world admin (clubs/cultures/narratives), regen-universe portrait ban/override, operations readiness.

---

## 5. Priority Order for Design (recommended)

Design in this order so the **core loop** (own a club → build a squad → trade talent → compete) is coherent first:

1. **P0 Core loop:** Public landing → Onboarding → Home → Club owner dashboard → Lineup editor → Player marketplace → Player profile → Wallet → Match center + live 2D viewer.
2. **P0 Support:** Login/Signup, Profile, Regen world + Create-a-son, Transfer center, Competitions hub.
3. **P1:** Social/fan hub, Viral feed, Fan wars, Fan predictions, Awards, News agency, Tournaments, National teams, Federations, Coin trader, Global search, Notifications, Portfolio, Club identity/dynasty/trophies, Club sale market, Creator/fan share markets, Matchday economy, Jackpot, Gifts, Tasks.
4. **P2:** Full admin/ops suite.

---

## 6. Per-screen design briefs for Stitch

Each brief is written so it can be pasted into Stitch on its own. All share the **Section 2 design system** (dark football-economy, Barlow Condensed / Inter / DM Mono, semantic accents). Assume **mobile-first**, but also design a **desktop/web** layout since GTEX runs on web too.

> Template Stitch prompt prefix (prepend to any brief):
> *"Design a screen for GTEX, a dark, cinematic football-economy app (Football Manager × trading exchange × creator platform). Dark UI: bg #0A0C0F, surfaces #111418/#181C22, hairline borders #262C36, text #F0F2F5/#8A93A2. Accents are semantic: green #00C46A = football/live/positive, gold #FFB800 = GTEX Coin/prices, blue #3D7EFF = fan/social, red #FF4D4D = negative, orange #FF9500 = warning. Headlines in condensed sporting type (Barlow Condensed), body in Inter, all numbers/prices/scores in DM Mono tabular. No decorative gradients or gloss; accents are load-bearing. Then: [SCREEN BRIEF]."*

**P0 briefs:**

- **Public landing:** Cinematic hero establishing "own a club, trade talent, rule the football world." Live world-pulse ticker, featured players/regens, market movers, social proof. Primary CTA "Enter GTEX" / "Create account", secondary "Sign in."
- **Onboarding flow:** Multi-step guided setup — welcome → choose entry (create club / join club / trade) → region selection → player shortlist → KYC step → first competition. Progress indicator, one decision per step, big confident CTAs.
- **Home (living world):** Personalized front page. Top: your club snapshot (badge, form, next match countdown) + wallet pill. Then modular feed: market movers, rising regens, live/next matches, world pulse, news headlines, leaderboards, daily challenges. Role-adaptive.
- **Club owner dashboard:** Command center. Hero: club identity + next fixture + form. Grid of metric tiles (squad rating, finances/coin balance, morale, academy). Sections: squad health, transfers in/out, academy prospects, trophies, quick actions (lineup, register squad).
- **Lineup / tactics editor:** Football pitch with formation slots; drag players from bench/squad list into positions colored by role. Formation selector, per-player role, save/lock. Squad list side panel with ratings.
- **Player card marketplace:** Exchange-style browse. Filters (position, rating, price, real/regen). Grid or list of Player Cards with live valuation + delta + sparkline. Sort by movers/volume/price. A selected card opens an order-book / buy panel.
- **Player profile (FM-style):** Flagship. Portrait + name + position pill + club badge + overall. Attribute breakdown (radar or bars), form, match history, valuation chart (mono), ownership, and action bar (buy / sell / make offer / add to shortlist).
- **Wallet overview:** Two currency balances (GTEX Coin gold, Fan Coin blue) as hero mono figures. Transactions list, funding/withdraw CTAs, and (if coin trader) trader desk module. Clear on/off-ramp entry.
- **Match center + live 2D viewer:** Scoreboard strip (badges, score in condensed, live minute in mono, competition). Live 2D pitch/event feed, momentum bar, key events timeline, lineups, tactics, stats tabs. A "3D coming soon" state for native-3D matches.
- **Regen world + Create-a-son:** Gallery of AI-generated regen players with portraits + potential. Create-a-son flow: a signature, almost ceremonial generator — choose parameters, generate portrait + attributes, name, confirm. Make it feel special.

**P1 (brief-per-screen, same system):** Transfer center (deal pipeline/negotiation cards), Competitions hub (leagues/cups with standings + fixtures tabs), Tournaments, National teams + rental, Federations (governance/proposals/rankings), Social fan hub (community feed), Viral feed (vertical clip feed), Fan wars (nation rivalry leaderboards + battle UI), Fan predictions (pick fixtures, stake, rewards), Awards (broadcast-style ceremony), News agency (editorial article layout), Coin trader (rates + order lifecycle), Global search (universal search with grouped results), Notifications, Portfolio (holdings + P/L), Club identity (badge/jersey editor with live preview), Dynasty/Reputation/Trophies (timeline + leaderboards), Club sale market (listing + offers), Creator/Fan share markets (share order books + holdings + distributions), Matchday economy (tickets/predictions/listings), Jackpot, Gift economy (gift catalog + combos), Tasks/daily challenges.

**P2 admin:** Dense, data-first, violet-accented ops consoles — tables, filters, audit trails, action buttons with confirmations, settlement/review workflows. Prioritize legibility and safe destructive actions over flourish.

---

## 7. Implementation Notes (Claude)

### 7.1 Stack
- **Flutter** app in `frontend/` (package `gte_frontend`). Dart.
- **State:** `flutter_riverpod` + bespoke `ChangeNotifier` controllers (e.g. `GteExchangeController`, `CompetitionController`, `CreatorController`).
- **Routing:** `go_router`. Central registry in `frontend/lib/features/app_routes/` (`gte_app_route_registry.dart`, `gte_feature_route_builders.dart`, `app_routes.dart`, `gte_route_data.dart`).
- **Nav shell:** `frontend/lib/features/navigation/presentation/gte_navigation_shell_screen.dart` (role-adaptive home; primary destinations enum `GtePrimaryDestination`).
- **Design system:** `frontend/lib/ui_gtex/` — `theme/gtex_colors.dart`, `theme/gtex_typography.dart`, `theme/gtex_spacing.dart`, `components/` (`gtex_button.dart`, `gtex_panel.dart`, `gtex_card.dart`, `gtex_metric_tile.dart`, `gtex_status_chip.dart`), `layout/gtex_app_shell.dart`. Also `frontend/lib/theme/` and `frontend/lib/core/theme/`.
- **Match engine:** Unity project at repo root (`Gtex_Test_Migration/`, see `AGENTS.md`), Windows batchmode builds. 3D matches in progress; native-3D routes render `match_native_3d_blocked_screen.dart` / `clips_blocked_screen.dart` until live.

### 7.2 Implementation approach (important)
- **v0 cannot preview or run Flutter.** When implementing Stitch designs into this Flutter codebase, build against the **existing `ui_gtex` design-system components and tokens** rather than raw Flutter widgets, so new screens match automatically.
- Many screens already have a **`_v2` / `_redesign`** variant — implement into/replace those rather than creating a third variant.
- Respect `AGENTS.md`: keep systems modular, don't break batchmode builds, prioritize performance.
- Wire screens to the **existing API surface** (Section 8.2) via the existing data layer (`frontend/lib/data/` — `gte_api_repository.dart`, `gte_authed_api.dart`, feature APIs). Do **not** invent new endpoints; reuse what exists.
- Keep the **role-adaptive home** and **World Pulse ticker** behaviors.

---

## 8. Reference: file & API map (Claude)

### 8.1 Key screen files (by domain)
- Onboarding/landing: `features/onboarding_redesign/gtex_public_landing_screen_v2.dart`, `gtex_onboarding_flow_screen_v2.dart`; `screens/auth/`, `screens/gte_login_screen_v2.dart`, `screens/gte_signup_screen_v2.dart`.
- Home: `features/home/home_screen.dart`, `features/home_dashboard/home_dashboard_screen.dart`.
- Club: `features/club_redesign/presentation/gtex_club_owner_dashboard_v2.dart`, `screens/clubs/gtex_club_owner_dashboard_screen_v2.dart`, `features/club/gtex_lineup_editor_screen.dart`, `features/club_hub/…`, `features/club_identity/…` (dynasty, jerseys, reputation, trophies), `features/club_growth_redesign/…`, `features/club_lifecycle_redesign/…`, `features/club_sale_market/…`.
- Market/trading: `features/player_market_redesign/presentation/gtex_player_market_redesign_screen.dart`, `features/player_card_marketplace/…`, `features/transfer_market/…`, `features/transfer_center/…`, `features/transfer_news_calendar/…`, `features/creator_share_market/…`, `screens/gte_portfolio_screen.dart`.
- Players/regens: `features/player_detail/gtex_fm_player_profile_screen.dart`, `features/regen_redesign/…` (`gtex_regen_world_screen_v2.dart`, `gtex_create_son_screen_v2.dart`, `gtex_admin_create_son_screen_v2.dart`), `features/regens/…`.
- Matches/competitions: `features/match_redesign/presentation/gtex_match_center_screen_v2.dart`, `features/match/…` (viewer, simulate, spectate, broadcast, 3D-blocked), `features/competition_redesign/…`, `features/competitions_hub/…`, `features/tournaments/…`, `features/national_teams/…`, `features/national_team_rental_redesign/…`, `features/federation(s)/…`, `features/football_world_simulation/…`.
- Social/creators: `features/viral_feed/…`, `features/social/gtex_social_fan_hub_screen_v2.dart`, `features/fan_wars/…`, `features/fan_prediction/…`, `features/awards/gtex_awards_screen_v2.dart`, `features/news_agency/gtex_news_agency_screen_v2.dart`, `features/creator_league_admin/…`, `features/creator_stadium_monetization/…`, `features/streamer_tournament_engine/…`, `features/tasks/…`.
- Wallet/economy: `screens/wallet/gtex_wallet_overview_screen_v2.dart`, `screens/wallet/gte_funding_flow_screen.dart`, `gte_withdrawal_flow_screen.dart`, `features/coin_trader_redesign/…`, `features/matchday_economy_redesign/…`, `features/jackpot/…`, `features/gift_economy_admin/…`.
- Utilities: `features/global_search_redesign/…`, `screens/notifications/gte_notifications_screen_v2.dart`, `screens/agent_conversations_screen.dart`, `screens/referrals/`, `screens/support/`.
- Admin: `screens/admin/admin_command_center_screen.dart`, `features/launch_control_redesign/…`, `features/trust_ops_redesign/…`, `features/gift_economy_admin/…`, plus admin routes in Section 8.2.

### 8.2 API surface (existing endpoints — reuse, don't reinvent)
Representative REST endpoints already routed in the app (prefix `/api`):
- **Auth/session:** `/auth/me`, `/club/current`.
- **Clubs:** `/clubs/{id}` badge, dynasty(+history), eras, honors-timeline, identity, jerseys, reputation(+history), sale-market(listing/offers/inquiries/transfer/history), season-honors, trophy-cabinet, valuation; `/clubs/{id}/growth` (academy prospects/contracts/promote, staff), `/operating-dashboard`, `/squad-registration`(+submit/lock), `/advance-lifecycle`; `/clubs/sale-market/listings`, `/me/clubs/sale-market/(listings|offers)`.
- **Competitions/calendar:** `/competitions/{id}/(fixtures|standings)`, `/competitions/creator-league`, `/calendar-engine/(dashboard|events|seasons|lifecycle-runs|pause-status)`.
- **Matches/media:** `/matches/{id}/(state|tactics|spectate)`, `/match-viewer/{key}(/session)`, `/matches/fixture-final/(replay|commentary/stream|audio/stems/stream)`, `/broadcast/(home|channels|channels/{id}/join)`, `/commentary/profiles`, `/media-engine/creator-league/…`.
- **Economy/wallet/traders:** `/economy/gift-catalog`, `/gifts/catalog`, `/matchday-economy/overview`, `/coin-traders`(+me/rates/apply/orders lifecycle), `/daily-challenges`(+me/claim).
- **Fans/awards/social:** `/fan-wars/(leaderboards|rivalries|nations-cup|profiles)`, `/awards/(categories|ceremony|nominees|winners)`, `/leaderboards/(dynasties|prestige|trophies)`.
- **Federations:** `/federations`(+{id}/governance/memberships/narratives/proposals), `/federations/(rankings|regional-tournaments|national-associations)`, `/federations/proposals/{id}/votes`.
- **Creator/fan shares:** `/creator/clubs/{id}/fan-share-market`(+holding/purchase/distributions).
- **AI manager:** `/ai-manager/autopilot/(run|live-decision)`, `/ai-manager/economy/reward-preview`.
- **Feature flags:** `/feature-flags/client`.
- **Admin (gated):** extensive `/admin/**` and `/api/admin/**` — beta-access, calendar-engine, coin-traders, creator, economy, fan-wars, feature-flags(+kill-switch), gifts, hosted-competitions, launch-control, matchday-economy, media-engine, operations-readiness, search, streamer-tournaments, world (clubs/cultures/narratives), regen-universe portrait moderation.

---

## 9. Summary for the team

- **Stitch:** GTEX is a dark, cinematic football-economy app. Use the Section 2 design system verbatim and the Section 6 briefs. Design every screen in Section 4, in the Section 5 priority order. Reuse the Section 2.4 component kit (Player Card, coin chips, valuation deltas, scoreboard strip, world-pulse ticker, metric tiles) everywhere. Mobile-first + desktop. Keep it semantic, never decorative.
- **Claude:** Implement into the existing Flutter `ui_gtex` design system and the `_v2`/`_redesign` screen variants, wired to the existing API surface (Section 8.2) via the existing data layer. Preserve role-adaptive home, the world-pulse ticker, and `AGENTS.md` build/perf rules. 3D match & clips stay behind their "coming soon" blocked screens until the Unity engine ships.
- **The redesign's north star:** turn a fragmented admin-feeling app into one **legible, living football universe** — own a club, build a squad, trade talent, compete, and rise.
