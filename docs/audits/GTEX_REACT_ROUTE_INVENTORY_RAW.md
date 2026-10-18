# GTEX React Shell — Exhaustive Screen/Route Inventory

**Scope:** `/workspace/frontend/react-shell`  
**Commit:** `6711a545f06ec6bda28a03379028fb8d63c50a3c`  
**Package:** `gtex-react-shell@0.1.0`  
**Inventory date:** 2026-10-18  
**Mode:** Read-only inspection (no git changes)

---

## 0. Executive summary

| Metric | Count |
|--------|------:|
| Top-level `BrowserRouter` instances | 1 (`src/App.tsx`) |
| Declared `<Route>` entries (incl. index + catch-all) | 19 |
| Distinct page components under `src/pages/` | 16 |
| Nested console routes under `/app` (excl. layout) | 12 |
| Inventory IDs assigned (RX-001…RX-018) | 18 |
| Automated test files (`*.test.*` / `*.spec.*`) | **0** |
| `package.json` scripts | 3 (`start`, `build`, `test`) |
| Explicit `TODO` / `FIXME` / mock stubs in app code | **0** (none found) |
| Dead / hash links (`href="#"`) | 1 real dead link in fixtures + 1 intentional in-page anchor |
| Role gates (`admin` / `super_admin`) | AppShell nav + Admin page + NationalTeam seed |

**Product framing (from README):** Standalone React owner console + player-market shell, isolated from Flutter, calling canonical API. Production publish path is `/console/` via `PUBLIC_URL=/console`.

---

## 1. Architecture & shared infrastructure

### 1.1 Entry / providers

| Layer | File | Notes |
|-------|------|-------|
| Bootstrap | `src/index.js` | `QueryClientProvider` (TanStack Query; `staleTime` 60s, no refetch on focus) → `<App />` |
| App | `src/App.tsx` | `AuthProvider` → `BrowserRouter basename={ROUTER_BASENAME}` → routes → Sonner `Toaster` |
| Alias | `craco.config.js` | `@` → `src/` |

**Routers:** Only one router. No nested routers, no React Router data APIs beyond `useParams` / `useSearchParams`.

### 1.2 Basename / `PUBLIC_URL` (`src/lib/publicPath.ts`)

| Export | Behavior |
|--------|----------|
| `PUBLIC_URL` | `process.env.PUBLIC_URL` trimmed, no trailing slash. Empty locally; `/console` on Render. |
| `ROUTER_BASENAME` | `PUBLIC_URL \|\| "/"` — passed to `BrowserRouter`. |
| `publicUrl(path)` | Prefixes root-absolute paths/assets with `PUBLIC_URL`. |

**Implication:** All inventory paths below are **router-relative**. Under production they resolve as `/console` + path (e.g. `/console/app/market`). Landing CTAs and `Link`s use app-relative paths and inherit basename correctly. Full-page redirects that must survive outside the SPA use `publicUrl(...)` (Paystack callback, deposit success).

### 1.3 API client (`src/lib/api.ts`)

| Concern | Detail |
|---------|--------|
| HTTP lib | **axios** only (no raw `fetch` in app code) |
| Base URL | `${REACT_APP_BACKEND_URL}/api` — **required at module load**; throws if missing or if URL ends with `/api` |
| Auth header | Bearer from `localStorage` key `gtex_access` |
| Refresh | On 401: `POST /v2/auth/refresh` with `gtex_refresh`; single-flight; clears tokens on failure |
| Response unwrap | If body `{ success: true, data }`, interceptor replaces `r.data` with `data` |
| Errors | `errMsg()` maps known codes (`insufficient_funds`, `club_ownership_cap_reached`, Paystack missing, etc.) |

### 1.4 Auth / session (`src/lib/auth.tsx`)

| API | Endpoint |
|-----|----------|
| Session hydrate | `GET /v2/auth/me` |
| Login | `POST /v2/auth/login` |
| Signup | `POST /v2/auth/signup/user` (+ fallback login) |
| Logout | `POST /v2/auth/logout` (fire-and-forget) + clear tokens |

**Storage:** `gtex_access`, `gtex_refresh` in `localStorage`.  
**No** dedicated `ProtectedRoute` component — protection is inline in `AppShell` / `Onboarding` / `Admin`.

### 1.5 Role checks

| Location | Rule |
|----------|------|
| `AppShell` | `user.role ∈ {admin, super_admin}` → show Admin nav; non-admins without club stage `competition`/`active` → force `/onboarding` |
| `Admin` page | Same role check; else `<Navigate to="/app" />` |
| `NationalTeam` | Admin-only **Seed default tournaments** button + empty-state copy |

**No other RBAC** (no trader/creator roles in shell UI despite Flutter having trader signup routes). Coin trader desk infers trader status from `GET /coin-traders/me` status `approved`.

### 1.6 Owner helpers (`src/lib/owner.ts`)

| Hook | Source |
|------|--------|
| `useControlCenter()` | `GET /owner/control-center` |
| `useActiveClub()` | Control-center clubs + `localStorage gtex_active_club` |
| `useClub(id)` | `GET /owner/clubs/:id` |
| `useRefreshOwner()` | Invalidates `cc`, `club`, `finance`, `inbox`, `competition(s)` |
| `fmt` / `label` | `en-NG` locale formatting; underscore → space |

### 1.7 Environment variables

| Variable | Where | Required | Notes |
|----------|-------|----------|-------|
| `REACT_APP_BACKEND_URL` | `api.ts`, `.env.example` | **Yes** | API origin without `/api`. Example: `https://gtex-api-opea.onrender.com` |
| `PUBLIC_URL` | `publicPath.ts` (CRA build-time) | Prod publish | Empty locally; `/console` for Render |

No other `REACT_APP_*` / `process.env` usages in `src/`.

### 1.8 Layout shell (`src/components/gtex/AppShell.tsx`) — RX layout gate

- Auth required; loads control-center.
- Primary nav (desktop + mobile scroll): Control Center, My Clubs, Market, Competitions, Manager & Squad, Academy, National Team, Finance, Inbox; Admin if privileged.
- Club switcher, wallet GTX/FAN balances, integrity score, logout.
- Renders `<Outlet />` for nested `/app/*` pages.
- Eyebrow copy: **"Owner Console · NG"** (Nigeria launch branding).

---

## 2. Route inventory (RX-001 … RX-018)

Convention: **Route path** is React Router path. **Console basename:** when `PUBLIC_URL=/console`, full browser path is `/console` + path.

---

### RX-001 — Landing

| Field | Detail |
|-------|--------|
| **1. ID** | RX-001 |
| **2. Route** | `/` — under `/console` when published |
| **3. Component** | `Landing` — `src/pages/Landing.tsx` |
| **4. Role/purpose** | Marketing / acquisition landing; explains owner loop, trust, money |
| **5. Data sources** | None (static). Uses `useAuth()` only to toggle Sign in vs Open console |
| **6. Mutations** | None |
| **7. Auth** | Public |
| **8. TODOs / mocks / dead links / hardcoded** | Hardcoded Nigeria launch copy; boardroom demo is **static markup** (Approve/Reject `pointer-events-none`); `href="#how"` is intentional in-page anchor (works). Mentions “2D live feed” in copy (product claim; MatchCenter is event replay, not 2D pitch). Images via `publicUrl("/img/...")`. |
| **9. Status hint** | **Shipped marketing.** No API. CTA → signup/login/app. |

---

### RX-002 — Login

| Field | Detail |
|-------|--------|
| **1. ID** | RX-002 |
| **2. Route** | `/login` |
| **3. Component** | `AuthPage` (`mode="login"`) — `src/pages/AuthPage.tsx` |
| **4. Role/purpose** | Owner sign-in |
| **5. Data sources** | Via auth: `POST /v2/auth/login`, then `GET /v2/auth/me` |
| **6. Mutations** | Login |
| **7. Auth** | Public (unauthenticated form) |
| **8. Issues** | Shared component with signup; login fields only email/password. `constants/testIds/auth.js` defines `LOGIN.*` but page uses inline `data-testid` strings (`login-email-input` etc.) — registry partially unused / Emergent leftover (`forgotPasswordLink` not implemented). |
| **9. Status** | **Live** against API. Success → `/app`. |

---

### RX-003 — Signup

| Field | Detail |
|-------|--------|
| **1. ID** | RX-003 |
| **2. Route** | `/signup` |
| **3. Component** | `AuthPage` (`mode="signup"`) — `src/pages/AuthPage.tsx` |
| **4. Role/purpose** | Claim club + create user |
| **5. Data sources** | `POST /v2/auth/signup/user` |
| **6. Mutations** | Signup with club identity |
| **7. Auth** | Public |
| **8. Issues** | **Hardcoded** `country: "Nigeria"`, `club_country: "Nigeria"`; default city `"Lagos"`; “Nigeria launch terms”; placeholders “Lagos Lions FC”. Over-18 checkbox required client-side. |
| **9. Status** | **Live.** Success → `/onboarding`. |

---

### RX-004 — Onboarding / first-club activation

| Field | Detail |
|-------|--------|
| **1. ID** | RX-004 |
| **2. Route** | `/onboarding` |
| **3. Component** | `Onboarding` — `src/pages/Onboarding.tsx` (+ steps) |
| **4. Role/purpose** | First-club activation funnel: identity → squad → manager → competition |
| **5. Data sources** | `GET /owner/onboarding`; `useClub`; `GET /managers/catalog`; `GET /owner/competitions`; market via `MarketTable` |
| **6. Mutations** | `POST /owner/clubs/:id/activate`; sign players; `POST /owner/clubs/:id/manager`; `POST /owner/competitions/:id/enter`; `POST /owner/clubs/:id/finish-onboarding`; `POST /clubs` (create first club if none) |
| **7. Auth** | Required (`Navigate` → `/login`) |
| **8. Issues** | Create-club hardcodes `country_code: "NG"`, `city_name: "Lagos"`, fixed colors. Manager catalog limited to 3. Skip competition allowed. |
| **9. Status** | **Live multi-step.** Also reachable when AppShell redirects incomplete owners. |

---

### RX-005 — Payment callback

| Field | Detail |
|-------|--------|
| **1. ID** | RX-005 |
| **2. Route** | `/payment/callback` |
| **3. Component** | `PaymentCallback` — `src/pages/PaymentCallback.tsx` |
| **4. Role/purpose** | Paystack return URL; verify deposit |
| **5. Data sources** | `GET /owner/deposits/verify/:ref` (`reference` or `trxref` query) |
| **6. Mutations** | None (verify is GET); success full-page nav to `publicUrl("/app/finance?deposit=success")` |
| **7. Auth** | **No explicit gate** — relies on axios Bearer if tokens present (user should still be logged in) |
| **8. Issues** | Uses `window.location.href` (full reload). Failures stay on page with message. |
| **9. Status** | **Live** Paystack integration path. |

---

### RX-006 — App shell layout (not a page)

| Field | Detail |
|-------|--------|
| **1. ID** | RX-006 |
| **2. Route** | `/app` (layout parent) |
| **3. Component** | `AppShell` — `src/components/gtex/AppShell.tsx` |
| **4. Role/purpose** | Authenticated owner console chrome + outlet |
| **5. Data sources** | `useAuth`, `useControlCenter` |
| **6. Mutations** | Logout |
| **7. Auth** | Required; onboarding gate for non-admins |
| **8. Issues** | Mobile nav omits Admin link (admin only in desktop sidebar). Nigeria branding. |
| **9. Status** | **Live.** |

---

### RX-007 — Control Center (owner home)

| Field | Detail |
|-------|--------|
| **1. ID** | RX-007 |
| **2. Route** | `/app` (index) — under `/console/app` in prod |
| **3. Component** | `ControlCenter` — `src/pages/ControlCenter.tsx` |
| **4. Role/purpose** | Owner dashboard: fixtures rail, clubs, economy, decisions, inbox preview, health |
| **5. Data sources** | `GET /owner/control-center` (via `useControlCenter`); decisions/inbox via embedded `InboxItem` |
| **6. Mutations** | `POST /owner/clubs/:id/advance` (all clubs — “Advance world day”); inbox decide via `InboxItem` |
| **7. Auth** | Via AppShell |
| **8. Issues** | None critical; empty states link to competitions |
| **9. Status** | **Live core surface.** Closest Flutter analogue: owner console / home digest. |

---

### RX-008 — My Clubs

| Field | Detail |
|-------|--------|
| **1. ID** | RX-008 |
| **2. Route** | `/app/clubs` |
| **3. Component** | `MyClubs` — `src/pages/MyClubs.tsx` |
| **4. Role/purpose** | Club portfolio detail: facilities, treasury capital, sponsors, supporters, disclosures, add club |
| **5. Data sources** | `useClub`, `useControlCenter`, `GET /owner/clubs/:id/supporters` |
| **6. Mutations** | Facility upgrade; capital inject/distribute/sister-transfer; `POST /clubs` (new club → navigate onboarding) |
| **7. Auth** | Via AppShell |
| **8. Issues** | New club hardcodes NG/Lagos/colors; placeholder “Abuja Eagles FC” |
| **9. Status** | **Live.** |

---

### RX-009 — Market & Transfers

| Field | Detail |
|-------|--------|
| **1. ID** | RX-009 |
| **2. Route** | `/app/market` (+ optional `?position=` from manager request) |
| **3. Component** | `Market` — `src/pages/Market.tsx` + `MarketTable`, `ShareMarket`, sister transfer |
| **4. Role/purpose** | Sign players from world market; player share markets; related-party sister transfers |
| **5. Data sources** | `/v2/players`, `/owner/market/quote`, `/v2/players/markets`, nations, player drawer APIs |
| **6. Mutations** | Sign; sister transfer check/execute; share buy (drawer) |
| **7. Auth** | Via AppShell |
| **8. Issues** | Search placeholder “Osimhen” (hardcoded example). No free-agent listing / bid UI beyond sign + sister. |
| **9. Status** | **Live.** Broader than Flutter “transfer center” in share-market depth; thinner on social/viral market surfaces. |

---

### RX-010 — Competitions list

| Field | Detail |
|-------|--------|
| **1. ID** | RX-010 |
| **2. Route** | `/app/competitions` |
| **3. Component** | `Competitions` — `src/pages/Competitions.tsx` |
| **4. Role/purpose** | Browse GTEX-hosted + user-hosted cups; host; join by invite code |
| **5. Data sources** | `GET /owner/competitions` |
| **6. Mutations** | Enter; host (`POST /owner/competitions`); join-by-code |
| **7. Auth** | Via AppShell |
| **8. Issues** | Host formats limited to league/knockout; sizes 2–8. No World Super Cup / streamer tournament / fan-predictions routes. |
| **9. Status** | **Live owner-competition subset.** |

---

### RX-011 — Competition detail / matchday setup

| Field | Detail |
|-------|--------|
| **1. ID** | RX-011 |
| **2. Route** | `/app/competitions/:id` |
| **3. Component** | `CompetitionDetail` — `src/pages/CompetitionDetail.tsx` |
| **4. Role/purpose** | Standings, fixtures, play-next (mentality + lineup mode), forfeit |
| **5. Data sources** | `GET /owner/competitions/:id` |
| **6. Mutations** | `POST .../play-next`; `POST /owner/matches/:id/forfeit` |
| **7. Auth** | Via AppShell |
| **8. Issues** | **Dead link:** scheduled fixtures render `<Link to="#">` (no navigation). Lineup is only `strongest` \| `rotate` — not a full lineup editor. |
| **9. Status** | **Live sim path** into MatchCenter. |

---

### RX-012 — Match Center

| Field | Detail |
|-------|--------|
| **1. ID** | RX-012 |
| **2. Route** | `/app/match/:id` (+ `?club=` `?live=1`) |
| **3. Component** | `MatchCenter` — `src/pages/MatchCenter.tsx` |
| **4. Role/purpose** | Post-sim match narrative: timed event replay, momentum bars, gifts, post-match owner view |
| **5. Data sources** | `GET /owner/matches/:id` |
| **6. Mutations** | `POST /owner/gifts/send` (hardcoded gift catalog client-side) |
| **7. Auth** | Via AppShell (route nested under `/app`) |
| **8. Issues** | “Live” is **client timer** over precomputed events (not WebSocket/broadcast). Gift list hardcoded. No 3D/2D pitch viewer, no broadcast stems, no replay archive. Landing copy overclaims “2D live feed”. |
| **9. Status** | **Functional event-feed matchday** — not Flutter match viewer / 3D / broadcast parity. |

---

### RX-013 — Manager & Squad

| Field | Detail |
|-------|--------|
| **1. ID** | RX-013 |
| **2. Route** | `/app/squad` |
| **3. Component** | `Squad` — `src/pages/Squad.tsx` |
| **4. Role/purpose** | Manager sheet (fire/hire), squad cards/table, default mentality |
| **5. Data sources** | `useClub`; `GET /managers/catalog?limit=6`; player drawer |
| **6. Mutations** | Fire manager; appoint; `PUT /owner/clubs/:id/mentality` |
| **7. Auth** | Via AppShell |
| **8. Issues** | No formation editor, no shirt numbers, no substitute bench UI (contrast Flutter `/lineup`). |
| **9. Status** | **Live structural squad/manager.** |

---

### RX-014 — Academy / Regens

| Field | Detail |
|-------|--------|
| **1. ID** | RX-014 |
| **2. Route** | `/app/academy` |
| **3. Component** | `Academy` — `src/pages/Academy.tsx` + `PackReveal` |
| **4. Role/purpose** | Regen pipeline, intake, growth explanation, pack reveal UX |
| **5. Data sources** | Club squad (regen filter); facilities |
| **6. Mutations** | `POST .../academy/intake`; `POST .../advance` |
| **7. Auth** | Via AppShell |
| **8. Issues** | Seen-pack state in `localStorage` (`gtex.regens.seen.*`). Intake cost formula client-displayed `1500 * academyLevel`. |
| **9. Status** | **Live.** Flutter has broader `/world/regens` world surfaces not present here. |

---

### RX-015 — National Team

| Field | Detail |
|-------|--------|
| **1. ID** | RX-015 |
| **2. Route** | `/app/national` |
| **3. Component** | `NationalTeam` — `src/pages/NationalTeam.tsx` |
| **4. Role/purpose** | National-team rental tournaments: enter nation, rent players, auto-build suggestion, claim free players |
| **5. Data sources** | `/national-team-engine/competitions`, `/me/history`, rental-pool, entry detail |
| **6. Mutations** | Rental entry; rentals; auto-build (suggest only); claim free; admin `POST /admin/national-team-engine/competitions/seed-defaults` |
| **7. Auth** | Via AppShell; seed is admin-only |
| **8. Issues** | **Hardcoded** `COUNTRIES` list (NG default). Auto-build returns plan but UI does not one-click execute rentals from plan. No dedicated `/history` or `/entries/:id` deep routes (all on one page). |
| **9. Status** | **Live rental subset** aligned with Flutter national-team engine APIs. |

---

### RX-016 — Finance

| Field | Detail |
|-------|--------|
| **1. ID** | RX-016 |
| **2. Route** | `/app/finance` (+ `?deposit=success` after Paystack) |
| **3. Component** | `Finance` — `src/pages/Finance.tsx` + `CoinTraderDesk` |
| **4. Role/purpose** | Wallet balances, Paystack deposit, withdrawals, ledger, Fan Coin, Support Units, P2P coin traders |
| **5. Data sources** | `GET /owner/finance`; eligibility; `GET /owner/world/clubs`; coin-traders endpoints |
| **6. Mutations** | Deposit init; withdrawal; support-units buy; fan-coin buy; trader order lifecycle |
| **7. Auth** | Via AppShell |
| **8. Issues** | NUBAN/NGN-centric (Nigeria). Deposit default ₦5000. Paystack may be “not configured”. No separate KYC/compliance screens (eligibility chips only). |
| **9. Status** | **Live finance desk** — richer than a thin wallet; still missing Flutter KYC/disputes/support routes. |

---

### RX-017 — Inbox

| Field | Detail |
|-------|--------|
| **1. ID** | RX-017 |
| **2. Route** | `/app/inbox` |
| **3. Component** | `InboxPage` — `src/pages/Inbox.tsx` + `InboxItem` |
| **4. Role/purpose** | Owner messages & decisions (manager requests, unrest, sponsors, etc.) |
| **5. Data sources** | `GET /owner/inbox?status=` |
| **6. Mutations** | `POST /owner/inbox/:id/decide` |
| **7. Auth** | Via AppShell |
| **8. Issues** | Manager approve navigates to market with position filter. Filters: open/resolved/all. |
| **9. Status** | **Live.** |

---

### RX-018 — Admin Review

| Field | Detail |
|-------|--------|
| **1. ID** | RX-018 |
| **2. Route** | `/app/admin` |
| **3. Component** | `Admin` — `src/pages/Admin.tsx` |
| **4. Role/purpose** | Trust & payouts desk: withdrawals, integrity flags, held payouts |
| **5. Data sources** | `GET /owner/admin/review-queue` |
| **6. Mutations** | Withdrawal review approve/hold/reject; flag clear/action; payout release |
| **7. Auth** | `admin` \| `super_admin` only |
| **8. Issues** | Narrow vs Flutter admin command center / newsroom / creator-stadium control / gift stabilizer. |
| **9. Status** | **Live limited admin queue.** |

---

### Catch-all (not numbered as product screen)

| Route | Behavior |
|-------|----------|
| `*` | `<Navigate to="/" replace />` |

---

## 3. Shared / embedded components (not separate routes)

| Component | File | Used by | APIs / notes |
|-----------|------|---------|--------------|
| `MarketTable` | `components/gtex/MarketTable.tsx` | Market, Onboarding | `/v2/players`, quotes, sign |
| `ShareMarket` | `components/gtex/ShareMarket.tsx` | Market | markets + nations + wonderkid |
| `PlayerDrawer` | `components/gtex/PlayerDrawer.tsx` | Market, Squad, ShareMarket | real-universe / regen dossier / shares / form |
| `PriceHistoryChart` | `components/gtex/PriceHistoryChart.tsx` | PlayerDrawer | share price history |
| `InboxItem` | `components/gtex/InboxItem.tsx` | ControlCenter, Inbox | decide |
| `CoinTraderDesk` | `components/gtex/CoinTraderDesk.tsx` | Finance | P2P traders |
| `PackReveal` | `components/gtex/PackReveal.tsx` | Academy | local UX only |
| `PlayerCard` | `components/gtex/PlayerCard.tsx` | Many | presentational |
| `ui.tsx` | `components/gtex/ui.tsx` | Design system primitives | — |
| `components/ui/*` | Radix/shadcn stock | Mostly unused by GTEX pages | Emergent template residue |

---

## 4. API endpoint map (shell → backend)

### Auth
- `GET/POST /v2/auth/me|login|signup/user|logout|refresh`

### Owner core
- `GET /owner/control-center`, `/owner/onboarding`, `/owner/finance`, `/owner/inbox`, `/owner/competitions`, `/owner/competitions/:id`, `/owner/matches/:id`, `/owner/clubs/:id`, `/owner/clubs/:id/supporters`, `/owner/world/clubs`, `/owner/market/quote`, `/owner/admin/review-queue`
- Mutations: activate, advance, facilities upgrade, manager appoint/fire, mentality, sign, academy intake, capital inject/distribute/sister-transfer, competitions enter/host/join/play-next, forfeit, gifts, deposits init/verify, withdrawals (+ eligibility), support-units, fan-coin, inbox decide, transfers internal (+ check), admin withdrawal/flag/payout actions

### Clubs create
- `POST /clubs`

### Players / market / shares
- `/v2/players`, `/v2/players/real-universe/:id`, `/v2/players/:id/form`, `/v2/players/markets`, `/v2/players/markets/nations`, `/v2/players/:id/shares/*`, `/market/players/:id`

### Managers
- `GET /managers/catalog`

### National team
- `/national-team-engine/*` (+ admin seed)

### Coin traders
- `/coin-traders`, `/coin-traders/me`, `/coin-traders/orders` (+ accept/proof/confirm/cancel/dispute)

---

## 5. Feature coverage vs Flutter (typical surfaces)

| Flutter-typical area | React shell coverage | Verdict |
|----------------------|----------------------|---------|
| **Owner console** | Control Center + My Clubs + onboarding | **Strong** — purpose-built |
| **Market / transfers** | World market + shares + sister transfers | **Strong for owner signing**; missing Flutter transfer-hub breadth, player-cards, club sale-market |
| **Competitions** | GTEX + user-hosted owner comps | **Partial** — no streamer tournaments, World Super Cup, fan predictions, share/join deep links |
| **National team** | Single combined rental page | **Partial** — API-aligned; no separate entry/history routes |
| **Finance / wallet** | Full ledger + Paystack + traders | **Strong for owner money**; missing KYC/compliance/disputes/support screens |
| **Inbox** | Full decide UI | **Strong** |
| **Admin** | Withdrawals/flags/held payouts only | **Thin** vs Flutter admin command center |
| **Lineup** | Mentality + strongest/rotate only | **Gap** — Flutter has `/lineup` / `GtexLineupEditorScreen` |
| **Matchday** | Event-feed MatchCenter | **Gap** — no 3D, broadcast, live hub, replay archive |
| **Newsroom / news desk** | Absent | **Gap** — Flutter `/news`, admin newsroom |
| **Also absent vs Flutter** | Viral feed, community/social/chat, jackpot, creator stadium, federations/awards world, profile/settings, notifications, referrals, design-lab, trader-dedicated dashboards as first-class routes | Out of shell scope |

**Net:** React shell is an **owner-console + economy + market** web surface, not a Flutter replacement. Matchday/lineup/newsroom/social/admin depth are the largest gaps.

---

## 6. Hardcoded / launch-region findings

| Location | Hardcoding |
|----------|------------|
| Landing | “Launching in Nigeria”; NG trust/Paystack copy |
| AuthPage signup | `country`/`club_country` = `"Nigeria"`; city default Lagos |
| Onboarding / MyClubs create club | `country_code: "NG"`, `city_name: "Lagos"`, fixed palette |
| AppShell | “Owner Console · NG” |
| NationalTeam | Fixed `COUNTRIES` array; default `NG` |
| Finance | NGN / NUBAN / ₦; `en-NG` formatting in `fmt` and ledger |
| MatchCenter | Hardcoded gift catalog |
| CompetitionDetail | `to="#"` for scheduled fixtures |

---

## 7. TODOs, mocks, dead links, test residue

| Finding | Detail |
|---------|--------|
| Explicit TODOs/FIXMEs | **None** in `src/` app code |
| Mock data layers | **None** — pages call live API (empty states when API empty) |
| Dead link | Competition fixtures: scheduled → `to="#"` |
| Anchor (OK) | Landing `href="#how"` |
| Demo-only UI | Landing boardroom Approve/Reject non-interactive |
| Test ID registry | `constants/testIds/{auth,home}.js` largely **stale** (Emergent/`home-emergent-link`); pages use ad-hoc `data-testid`s instead |
| Unused UI kit | Large `components/ui/*` shadcn set unused by GTEX pages |

---

## 8. Scripts & tests

### `package.json` scripts

```json
"start": "craco start",
"build": "craco build",
"test": "craco test"
```

No `lint`, `typecheck`, `e2e`, or `ci` scripts.

### Tests

- **No** `*.test.*` / `*.spec.*` files under `react-shell/`.
- `npm test` would invoke CRA/Jest via craco but there is **no authored suite**.
- `data-testid` attributes are dense (qabot-oriented), but no in-repo automated tests consume them.

### Dependencies of note

- `react-router-dom@7.18.4`, `@tanstack/react-query@5.56.2`, `axios@1.20.0`, `swr@2.3.8` (**SWR listed but unused** in inspected `src/`), `recharts`, `framer-motion`, Radix UI.

---

## 9. Auth matrix (quick)

| Route | Public | Authed owner | Admin |
|-------|:------:|:------------:|:-----:|
| `/`, `/login`, `/signup` | ✓ | — | — |
| `/onboarding` | | ✓ | ✓ |
| `/payment/callback` | *tokens optional* | intended ✓ | ✓ |
| `/app/*` (non-admin) | | ✓ (+ onboarding gate) | ✓ |
| `/app/admin` | | | ✓ only |

---

## 10. Critical findings (prioritized)

1. **Production basename is `/console`** — all paths must be understood with `PUBLIC_URL`; Paystack callbacks correctly use `publicUrl`.
2. **`REACT_APP_BACKEND_URL` is hard-required** — app throws at import if unset; no same-origin fallback.
3. **Nigeria launch hardcoding** is pervasive (signup country, club create NG/Lagos, NGN wallet UX, AppShell “NG”).
4. **Matchday is not Flutter-class** — client-side event replay + gifts; marketing claims “2D live feed”; no 3D/broadcast.
5. **Lineup gap** — only strongest/rotate flags on play-next; no formation editor route.
6. **Newsroom absent** entirely.
7. **Dead fixture links** (`href="#"` / `to="#"`) on scheduled matches in CompetitionDetail.
8. **Admin surface is a payout/integrity queue only** — far thinner than Flutter admin.
9. **Zero automated tests** despite `test` script and many `data-testid`s; stale Emergent testId constants.
10. **Payment callback unauthenticated at UI layer** — works if session cookies/tokens persist; no explicit login redirect on verify failure due to 401.
11. **SWR dependency unused**; large unused shadcn `components/ui` tree adds noise.
12. **Mobile AppShell** does not expose Admin nav entry (desktop-only).

---

## 11. Inventory ID index

| ID | Path | Component |
|----|------|-----------|
| RX-001 | `/` | Landing |
| RX-002 | `/login` | AuthPage (login) |
| RX-003 | `/signup` | AuthPage (signup) |
| RX-004 | `/onboarding` | Onboarding |
| RX-005 | `/payment/callback` | PaymentCallback |
| RX-006 | `/app` (layout) | AppShell |
| RX-007 | `/app` (index) | ControlCenter |
| RX-008 | `/app/clubs` | MyClubs |
| RX-009 | `/app/market` | Market |
| RX-010 | `/app/competitions` | Competitions |
| RX-011 | `/app/competitions/:id` | CompetitionDetail |
| RX-012 | `/app/match/:id` | MatchCenter |
| RX-013 | `/app/squad` | Squad |
| RX-014 | `/app/academy` | Academy |
| RX-015 | `/app/national` | NationalTeam |
| RX-016 | `/app/finance` | Finance |
| RX-017 | `/app/inbox` | InboxPage |
| RX-018 | `/app/admin` | Admin |

**Totals:** 18 inventory entries · 16 page modules · 12 nested console screens · 1 layout · 5 pre-console routes (+ catch-all).
