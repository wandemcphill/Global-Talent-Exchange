# GTEX — Stitch Design Brief

> **Read me first.** You are designing the UI/UX for **GTEX (Global Talent Exchange)**, a large, live football-economy app. You do **not** have access to the codebase — everything you need is in this file. Design **every screen** in Section 5, in the priority order given, using the design system in Section 3 and the reusable component kit in Section 4. Design **mobile-first**, but also provide a **desktop/web** layout (GTEX runs on web too). Support **dark (primary)** and **light** themes.
>
> A copy-paste **prompt prefix** for every generation is in Section 6 — prepend it to any single-screen brief.

---

## 1. What GTEX is

GTEX is a **persistent, multiplayer football universe that behaves like a real economy** — think **Football Manager × a live trading exchange × a creator/streaming platform**, all in one world.

Humans using the app take on one or more **roles**:

| Role | What they do |
|------|--------------|
| **Club Owner** | Own & run a football club: squad, tactics, transfers, academy, stadium, finances, trophies, dynasty. |
| **Trader** | Buy/sell **player cards** and **club/fan shares** on live markets; profit from valuations. |
| **Creator / Streamer** | Run creator leagues, monetize stadiums, sell fan shares, host streamer tournaments. |
| **Fan** | Predict matches, join fan wars, gift, climb leaderboards, follow clubs & creators. |
| **Coin Trader** | KYC-verified peer-to-peer on/off-ramp for the in-game currency. |
| **Admin / Federation** | Govern the world: competitions, economy rules, moderation, trust & risk ops. |

The world is populated by two kinds of footballers:
- **Real-name players** traded on the market.
- **Regens ("sons")** — AI-generated next-gen players with portraits that users can **request/create**, develop, and trade. A signature GTEX mechanic — make it feel special.

**Two currencies:** **GTEX Coin** (gold — the hard economy currency) and **Fan Coin / Fan points** (blue — the social/engagement currency).

**Matches:** a **2D live match experience exists today**; a **3D match engine is in development** (native-3D screens show a "coming soon / blocked" state). Matches are event-driven 15-minute simulations.

---

## 2. The design problem to solve

The current app is **fragmented and administrative** — dozens of sibling screens and abstract navigation labels (*Transfer Hub, Matchday, Community, Club operations, Player universe, GTEX world*). It reads like an internal tool, not a living football world.

**Your north star:** turn it into one **cinematic, alive, legible** universe where a new user instantly understands: **own a club, build a squad, trade talent, compete, and rise.**

**Brand voice:** confident, sporting, slightly editorial. Real football gravitas (broadcast graphics, matchday energy) fused with fintech/exchange precision (tickers, valuations, order books). Never cartoonish. Copy is punchy and declarative: *"Return to your club, market, wallet and football universe."*

---

## 3. Design system (use verbatim)

Aesthetic: **professional football-economy — dark institutional surfaces, semantic accents, no decorative neon/gloss.**

### 3.1 Colors

**Dark theme (primary / default):**

| Token | Hex | Use |
|-------|-----|-----|
| `bg/base` | `#0A0C0F` | App background (near-black, cool) |
| `bg/surface` | `#111418` | Cards, panels |
| `bg/elevated` | `#181C22` | Raised / overlay panels |
| `bg/overlay` | `#1E232B` | Hover / popovers |
| `bg/input` | `#1C2128` | Inputs |
| `border/hairline` | `#262C36` | Default 1px separators |
| `border/strong` | `#313844` | Emphasized borders |
| `text/primary` | `#F0F2F5` | Headlines, primary text |
| `text/secondary` | `#8A93A2` | Secondary text |
| `text/muted` | `#4A5568` | Tertiary / disabled |

**Light theme:** `bg/base #F4F6F9`, `bg/surface #FFFFFF`, `bg/elevated #F9FAFB`, `border #DDE1E8`, `text/primary #0F1319`, `text/secondary #4A5568`.

**Semantic / brand accents (dark → light):**

| Token | Meaning | Dark | Light |
|-------|---------|------|-------|
| `brand/pitch` | Football, live, positive, Club-Owner role | `#00C46A` | `#00924E` |
| `brand/coin` | GTEX Coin, Trader role, prices | `#FFB800` | `#CC9200` |
| `brand/fan` | Fan Coin, social | `#3D7EFF` | `#2563EB` |
| `brand/alert` | Errors, blocked, negative | `#FF4D4D` | `#DC2626` |
| `brand/warn` | Warnings, locked, pending | `#FF9500` | `#D97706` |
| `accent/creator` | Creator role | `#00B4D8` | — |
| `accent/admin` | Admin role | `#E040FB` | — |

**Position colors** (player cards / pitch): GK = amber, DEF = blue, MID = green, ATT = red.
**Status:** live = green, locked = warn-orange, blocked = red, idle = muted, loading = blue.

> **Rule:** no decorative neon, no gradients-for-gradient's-sake, no gloss. Accents are **semantic and load-bearing** — color communicates role, currency, and match state, never decoration.

### 3.2 Typography

| Family | Role |
|--------|------|
| **Barlow Condensed** | Display / headlines / big numbers on cards & scoreboards (`w600–w700`). Condensed = broadcast/sporting feel. |
| **Inter** | Body, labels, UI text. Body line-height 1.4–1.6. |
| **DM Mono** | **All economic numbers** — prices, valuations, coin balances, scores, timers, order books. Always tabular figures. |

Scale (px): Display 2XL 56 / XL 40 / LG 32 / MD 24 / SM 18 · Body LG 16 / MD 14 / SM 12 · Label LG 14 / MD 12 / SM 11 (letter-spacing 0.4, uppercase eyebrows) · Mono XL 28 / LG 20 / MD 14 / SM 12.

> **Rule:** any money, coins, %, valuation, score, or clock renders in **DM Mono** with tabular figures.

### 3.3 Spacing, radius, elevation
- Spacing scale: **4 / 6 / 8 / 12 / 16 / 20 / 24 / 32**.
- Radius: cards ~12–16px, chips/pills fully rounded, inputs ~10px.
- Elevation: subtle border + very soft shadow (`black @ 12–18%`, blur 12, y+4). **Hairline borders are the default separator, not heavy shadows.**

---

## 4. Signature component kit (design once, reuse everywhere)

- **Player Card** *(flagship object)* — portrait, name, position pill (position color), overall rating, club badge, live valuation (mono) with ▲/▼ delta, rarity/regen indicator.
- **Coin chip / balance pill** — currency icon + mono amount; gold = GTEX Coin, blue = Fan Coin.
- **Valuation delta** — mono number with ▲green / ▼red + tiny sparkline.
- **Status chip** — live / locked / pending / blocked, using status colors.
- **Metric tile** — big mono number + small uppercase label (dashboards).
- **Match scoreboard strip** — two badges, score in Barlow Condensed, live minute in mono, competition label.
- **World Pulse ticker** — live horizontal rail of world events (transfers, goals, market moves). A signature ambient element — keep it.
- **Panel** — bordered surface with header (eyebrow label + optional action) + body.
- **Role badge** — colored pill for the actor's role.
- **Leaderboard row** — rank, avatar/badge, name, mono metric, delta.

---

## 5. Screen inventory (design all of these)

"v2 / redesign" means a newer iteration already exists — design the **definitive** version. **P0** = design first (core loop), **P1** = important, **P2** = admin/ops.

### A. Onboarding & Identity — P0
Public landing (logged-out marketing entry) · Onboarding flow (signup → club path → region → player shortlist → KYC → first competition) · Login / Signup · Profile (public, own, live, settings).

### B. Home — P0
Home (living-world front page, role-adaptive): club snapshot, next match, market movers, rising regens, world pulse, news, leaderboards, daily challenges.

### C. Club (ownership & operations) — P0
Club owner dashboard · Club hub / Club screen · Lineup & tactics editor · Squad registration · Club growth (academy: prospects, contracts, promote; staff) · Club lifecycle (eras/stages) · Club identity (badge + jersey editor + preview) · Dynasty (overview, era history, leaderboard) · Reputation / Prestige (+history, leaderboard) · Trophies (cabinet, honors timeline, leaderboard) · Club sale market (list club, offers, inquiries, transfer ownership).

### D. Market & Trading — P0
Player card marketplace · Player market (redesign — primary talent exchange) · Transfer market · Transfer center (your deals in/out, offers, negotiations) · Transfer news calendar · Creator share market · Fan share market (holdings, distributions) · Portfolio (holdings across cards/shares).

### E. Players & Regens — P0
Player detail / profile (FM-style flagship) · Regen world (browse AI regens) · Create-a-son / Request-a-son (signature generator).

### F. Matches & Competitions — P0/P1
Match center · Live match viewer (2D; 3D "coming soon") · Match simulate / spectate / broadcast / pre-match · Competitions hub (leagues, cups, standings, fixtures) · Live competitions hub · Tournaments (intro, screen, list) · National teams + national-team rental · Federations (governance, proposals, votes, rankings, regional tournaments) · Football world simulation.

### G. Social, Fans & Creators — P1
Viral feed (vertical clips; 3D clips "coming soon") · Social / fan hub · Fan wars (nation-vs-nation leaderboards + battle UI) · Fan prediction (pick fixtures, stake, rewards) · Awards (ceremony, categories, nominees, winners) · News agency (in-world journalism) · Creator league admin · Creator stadium monetization · Streamer tournament engine · Tasks / daily challenges.

### H. Wallet & Economy — P0/P1
Wallet overview (GTEX Coin + Fan Coin, transactions, fund/withdraw) · Funding flow · Withdrawal flow · Coin trader (P2P on/off-ramp: apply, rates, order lifecycle) · Matchday economy (tickets, prediction rewards, listings) · Jackpot · Gift economy (catalog, combos).

### I. Discovery & Utilities — P1
Global search (players, clubs, creators, competitions) · Notifications · Agent conversations / chat · Referrals · Support.

### J. Admin & Ops (gated) — P2
Dense, data-first, **violet-accented** ops consoles: Admin command center, launch control / feature flags, moderation & disputes, risk-ops, trust-ops (KYC, wallet orders), economy (burn events, gift rules, stabilizer), leaderboard season reset/archive, jackpot runtime, fan-prediction settlement, football-events engine, calendar engine, coin-trader admin, fan-wars admin, creator financials/settlements, media engine (broadcast, analytics, settlement), streamer-tournament policy/review/settle, world admin (clubs/cultures/narratives), regen portrait moderation, operations readiness. Prioritize legibility, audit trails, and safe destructive actions over flourish.

---

## 6. Prompt prefix (prepend to every screen brief)

> *"Design a screen for **GTEX**, a dark, cinematic football-economy app (Football Manager × trading exchange × creator platform). Dark UI: bg `#0A0C0F`, surfaces `#111418`/`#181C22`, hairline borders `#262C36`, text `#F0F2F5`/`#8A93A2`. Accents are semantic: green `#00C46A` = football/live/positive, gold `#FFB800` = GTEX Coin/prices, blue `#3D7EFF` = fan/social, red `#FF4D4D` = negative, orange `#FF9500` = warning. Headlines in **Barlow Condensed** (condensed sporting), body in **Inter**, all numbers/prices/scores in **DM Mono** tabular. No decorative gradients or gloss; accents are load-bearing. Reuse the GTEX component kit: player card, coin chip, valuation delta, status chip, metric tile, scoreboard strip, world-pulse ticker. Mobile-first + a desktop layout. Then design: [SCREEN BRIEF below]."*

---

## 7. Per-screen briefs

### P0 — design these first (the core loop)

- **Public landing.** Cinematic hero: "own a club, trade talent, rule the football world." Live world-pulse ticker, featured players/regens, market movers, social proof. Primary CTA "Enter GTEX" / "Create account", secondary "Sign in."
- **Onboarding flow.** Multi-step guided setup: welcome → choose entry (create club / join club / trade) → region selection → player shortlist → KYC step → first competition. Progress indicator, one decision per step, big confident CTAs.
- **Home (living world).** Personalized, role-adaptive front page. Top: club snapshot (badge, form, next-match countdown) + wallet pill. Modular feed below: market movers, rising regens, live/next matches, world pulse, news headlines, leaderboards, daily challenges.
- **Club owner dashboard.** Command center. Hero: club identity + next fixture + form. Grid of metric tiles (squad rating, coin balance/finances, morale, academy). Sections: squad health, transfers in/out, academy prospects, trophies, quick actions (edit lineup, register squad).
- **Lineup / tactics editor.** Football pitch with formation slots; drag players from bench/squad list into positions colored by role. Formation selector, per-player role, save/lock. Side panel squad list with ratings.
- **Player card marketplace.** Exchange-style browse. Filters (position, rating, price, real/regen). Grid or list of Player Cards with live valuation + delta + sparkline. Sort by movers/volume/price. Selecting a card opens an order-book / buy panel.
- **Player profile (FM-style).** Flagship. Portrait + name + position pill + club badge + overall. Attribute breakdown (radar or bars), form, match history, valuation chart (mono), ownership, action bar (buy / sell / make offer / shortlist).
- **Wallet overview.** Two currency balances (GTEX Coin gold, Fan Coin blue) as hero mono figures. Transactions list, fund/withdraw CTAs, and (for coin traders) a trader-desk module. Clear on/off-ramp entry.
- **Match center + live 2D viewer.** Scoreboard strip (badges, condensed score, mono live minute, competition). Live 2D pitch/event feed, momentum bar, key-events timeline, lineups, tactics, stats tabs. Include a polished "3D coming soon" state for native-3D matches.
- **Regen world + Create-a-son.** Gallery of AI regen players with portraits + potential. Create-a-son flow: a signature, almost ceremonial generator — choose parameters, generate portrait + attributes, name, confirm. Make it feel momentous.

### P1 — important (same system + component kit)
Transfer center (deal pipeline / negotiation cards) · Competitions hub (leagues/cups, standings + fixtures tabs) · Tournaments · National teams + rental · Federations (governance / proposals / rankings) · Social fan hub (community feed) · Viral feed (vertical clip feed) · Fan wars (nation rivalry leaderboards + battle UI) · Fan predictions (pick fixtures, stake, rewards) · Awards (broadcast-style ceremony) · News agency (editorial article layout) · Coin trader (rates + order lifecycle) · Global search (universal search, grouped results) · Notifications · Portfolio (holdings + P/L) · Club identity (badge/jersey editor with live preview) · Dynasty / Reputation / Trophies (timelines + leaderboards) · Club sale market (listing + offers) · Creator/Fan share markets (share order books + holdings + distributions) · Matchday economy (tickets / predictions / listings) · Jackpot · Gift economy (catalog + combos) · Tasks / daily challenges.

### P2 — admin
Dense, data-first, violet-accented ops consoles: tables, filters, audit trails, action buttons with confirmations, settlement/review workflows. Legibility and safe destructive actions over flourish.

---

## 8. Priority order (recommended)

1. **P0 core loop:** Public landing → Onboarding → Home → Club owner dashboard → Lineup editor → Player marketplace → Player profile → Wallet → Match center + live 2D viewer.
2. **P0 support:** Login/Signup, Profile, Regen world + Create-a-son, Transfer center, Competitions hub.
3. **P1:** everything in Section 7's P1 list.
4. **P2:** the admin/ops suite.

Design the core loop first so "own a club → build a squad → trade talent → compete → rise" is coherent before the supporting and admin surfaces.
