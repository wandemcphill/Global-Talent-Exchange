# GTEX Revamp — Master Backlog

Living tracker for the FM-aligned revamp. Status: **planning** (no app code written yet).
Decisions captured from the planning sessions. See
[SQUAD_TIER_PIPELINE_DESIGN.md](../backend/docs/SQUAD_TIER_PIPELINE_DESIGN.md) for the
detailed squad-tier/multi-position spec.

## North star
Football Manager information architecture + depth, with a premium collectible treatment
reserved for regens. Honest data (no fabricated stats). Mass-market readable for FM / FIFA
/ Fantasy players. Visual target: **FM layout, FM + premium regen cards**. Live code = this
repo's `main`.

---

## Track A — Player card / profile (UI)  — IN PROGRESS
Canonical widget = `lib/ui_gtex/football/gtex_player_card.dart` (`GtexPlayerCard`), already
used by Transfer Hub + rental/market redesigns. Retire `FootballPlayerCard`, core `PlayerCard`,
`PlayerCardAvatar`.
- [x] **FM silhouette** fallback — replaced geometric/initials painters with `_FmSilhouettePainter`
      (grey head-and-shoulders bust, accent-tinted for regens). Analyzes clean.
- [x] **Always-on height + foot bio row** (`_BioRail`, degrades to "—" when absent).
- [x] **Multi-position chips** (`_PositionRail`: natural + up to 3 secondaries) — new `secondaryPositions` param.
- [x] Regen **salary** + contract surfaced in footer signals (new `salaryLabel` param).
- [ ] **Plumb height + foot**: backend market payload → raw model (`gtex_market_browse_models.dart`)
      → presentation labels → grid/panel call sites. (foot supports Either/Both)
- [x] **FM-style profile screen BUILT + wired** — `gtex_fm_player_profile_screen.dart`: header (GSI + POT),
      bio (height/foot/positions incl. secondary chips), 6 colour-coded stat bars, market panel. Route
      `/players/:playerId/profile`; live nav-shell `_openPlayer` opens it (replacing the old detail screen).
      Backend: `derive_player_attributes` exposes the 6 FIFA stats on the `/players/{id}` detail API
      (archetype-derived from GSI+position, prefers `dna_profile`); `secondary_positions` added to identity.
      All analyzes/compiles clean. *Not run/visually verified.*
- [ ] Regen premium card: rarity frame, 1-of-1 badge, lineage/dynasty, award, **salary per year**, retrainable tag.
- [~] Consolidate duplicate cards — **live screens only**:
  - [x] `PlayerCardMarketplaceScreen` (live, 2 sites) → migrated to `GtexPlayerCard` (compact + actions). Analyzes clean. *Needs a visual check when the app runs.*
  - `PlayerCardAvatar` = KEEP (shared primitive, 18 uses — not a duplicate card).
  - Dead (leave alone): `regens_screen.dart` (live = `RegensScreenV2`), `exchange_hub_widgets.dart` (0 imports), `legacy/gte_players_screen.dart`, `scouting_dashboard_screen.dart` + `gte_club_identity_hub_screen.dart` (0 refs), ui_system demo cards.
  - `TournamentScreen` (core `PlayerCard`) — confirmed NOT in live routing → dead/demo, left alone.
  - **Result: all live duplicate-card usage now consolidated onto `GtexPlayerCard`.** Main Transfer Hub (`player_market_redesign`) already used it; `PlayerCardMarketplaceScreen` now migrated. Remaining `FootballPlayerCard`/core `PlayerCard` refs are all dead/demo/legacy — deletion deferred (would need those dead files removed too).
- Deferred to Track B: potential (POT) + secondary_positions data plumbing.
- Decision: layout approved via mockups v1/v2.

## Track B — LINEUP/FORMATION — DONE (2026-06-29)
- [x] **Seam fix**: `team_factory` derives the employed coach's formation (mentality/tactics → 4-3-3 /
      4-4-2 / 4-5-1 / 5-3-2) and plays it, falling back to 4-3-3 only if the squad can't fill it
      (never breaks a match). Replaces the hardcoded `formation="4-3-3"`.
- [x] **Persist owner lineup**: `ClubMatchPlan` model + migration `0105` + `app/lineups` service/router
      (`GET`/`PUT /clubs/{id}/lineup`, formation validated to sum 10), ownership-gated.
- [x] **Match consumption**: `team_factory._resolve_lineup` = saved exact XI (if all 11 eligible) →
      saved formation → coach formation → 4-3-3, each with fallback.
- [x] **Frontend editor**: `ClubLineupRepository` + `GtexLineupEditorScreen` (formation chips +
      tap-to-assign slots + auto-fill + save); `/lineup` route; club-owner "Set lineup" quick action.
- Migration 0105 written, NOT applied. Editor needs device verification (tap-to-assign/save).

## Track B — Backend gaps (design locked)
- [ ] **Real-player multi-position** — add `secondary_positions_json` to `ingestion_players`,
      populate on re-ingest, expose on read API.
- [ ] **Squad-tier pipeline** — `club_squad_tier_memberships` (first_team/u21/reserve, no caps);
      owner-driven moves (→u21 needs ≤21; →reserve/→first-team any age); recommendation engine
      (no auto-move); **Academy intake view** (regens through youth ranks, sign-up to first team);
      "build a son" adds `source=son` membership; migration backfills first_team.
- [ ] **Lineup / formation pipeline (FULL)** — persist a club's starting XI + formation;
      `team_factory` consumes it, **falling back to the employed coach's AI auto-draft**
      (`ai_manager.SquadPlanner`) instead of hardcoded `4-3-3`; **drag-into-formation UI**.
- [ ] **Coach "free to acquire"** — flip `manager_market` recruit off service pricing (stays tradable).
- Migrations written but **not applied to prod** (user runs them).

## Track C — Coach market (UI; backend ready)  — DONE (wired)
- [x] Discovery: `ManagerMarketScreen` (1384 lines) + `ManagerMarketRepository` (full endpoint coverage)
      already existed but were **referenced nowhere** — built yet unreachable.
- [x] Wired live: added `AppRoutes.coaches` + `/coaches` route (+`/managers` alias) →
      `ManagerMarketScreen`; added "Hire coaches" club-owner home quick action. All files analyze clean.
- [x] Screen confirmed full-featured: catalog + filters, recruit ("Coach recruited for free" — the
      free-to-acquire rule is already implemented), trade-listings/buy/cancel, swap, compare, and
      main/academy/bench slots. Real coaches seeded (Ferguson, Mourinho, Cruyff…).
- Note: this also satisfies Track B's "coaches free to acquire" item.
- [ ] Optional polish later: align visual style with the new design system (it predates it).

## Track D — Data / ops
- [x] FM silhouette: card fallback fixed (Track A); shared `PlayerCardAvatar` primitive already had a
      silhouette fallback (`_FootballSilhouette`) — no change needed.

### ⚙️ OPS — you must run these (I can't run prod jobs / migrations from here)
1. **Apply the two new Alembic migrations to the DB** (written, NOT applied):
   - `20260628_0103_player_secondary_positions` — adds `ingestion_players.secondary_positions_json`.
   - `20260628_0104_club_squad_tier_memberships` — adds the squad-tier table.
   - Run: `alembic upgrade head` (after backing up). They chain off head `20260523_0102`.
2. **Re-run real-player ingestion** — corrects existing positions (N77 striker-as-GK fix) AND now
   populates `secondary_positions_json` on `Player` (the ingest hook I added) so the card's
   multi-position chips + height/foot fill in for existing rows.
3. **Regen portrait + read-model rebuild** — so regens load with faces (pipeline exists;
   `RegenPortraitService`). Regen read-models rebuild was already pending.
4. (Optional) **Squad-tier backfill** — insert a `first_team` membership for every currently
   contracted player, once you're ready to use the tier system (see SQUAD_TIER_PIPELINE_DESIGN.md §11).

## Track E — First impression (UI)  — IN PROGRESS
- [x] **Home guest desk red "blocked" walls → inviting teasers.** Added shared `_memberGateOrError`:
      guests get "Sign in to unlock {feature}" (lock-open icon, panel accent, Sign-in CTA);
      signed-in members hitting a real failure get a soft amber "We couldn't load X" (not red).
      Applied to `_LiveModule` (LIVE WORLD SIGNALS / LIVE COMPETITIONS / MARKET MOVERS) +
      `_WalletPanel` / `_RankingPanel` / `_TaskPanel`. Error badge "BLOCKED"→"MEMBERS"/"OFFLINE".
      Loading copy de-jargoned. Guest headline "WATCH THE MARKET BEFORE YOU OPERATE" →
      "YOUR CLUB. YOUR PLAYERS. YOUR GAME."; removed "backend identity/authority" language.
      `home_screen.dart` analyzes clean. *Needs visual check on next build.*
- [ ] Remaining home bits: `_TransferTicker` 'BLOCKED' badge (~line 420); `_RouteLaunchButton`
      "remains blocked until its live backend is mounted" copy.
- [x] **Landing de-jargon** (`gtex_public_landing_screen_v2.dart`): removed payment-rail leak
      (PAYSTACK BLOCKED / KORAPAY SERVER ENV → LIVE MATCHES / 17K+ PLAYERS / ONE-OF-A-KIND REGENS);
      headline "FOOTBALL HAS AN ECONOMY NOW" → "OWN A CLUB. SIGN THE STARS. WIN IT ALL.";
      chips STRICT LIVE/COMPETITION OS/TREASURY CONTROL → LIVE MATCHES/COMPETITIONS/TRANSFERS;
      "backend authority"/"feed is mounted"/"Numbers stay blank or blocked" → football copy;
      COMMAND VIEW → YOUR CLUB HQ; footer Paystack/KoraPay line → "Secure payments · Built for mobile".
      Analyzes clean.
- [x] **Sign-in de-jargon** (`gte_login_screen.dart`): "Enter the football operating system" →
      "Welcome back"; "command-center language…" → football copy; "Trade football assets" →
      "Sign the stars. Win it all."; "Role-aware access…" → "Sign in to your club, market, and wallet."
      Analyzes clean.
- [~] **New world-class landing** (designed, imagery sourced — build pending):
  - Mock approved: stadium/trophy hero + auto-play "How you play" showcase (scout→sign→XI→live→trophy)
    + live results ticker + account chooser (Player/Club = free·instant; Coin Trader + Creator =
    apply·verified, admin-granted; KYC only at withdrawal; Admin invite-only).
  - **Imagery optimized** (originals kept): `gtex_hero_trophy.webp` (43KB, clean trophy crop of the
    poster — no baked text), `gtex_match_live.webp` (124KB ← 2.4MB), `gtex_matchday_boot.webp`
    (91KB ← 2.9MB), `gtex_landing_poster.webp` (130KB static-splash fallback).
  - AI prompts captured for net-new plates (scout/sign, regen) if wanted later.
  - [x] **Built in Flutter** — rewrote `GtexPublicLandingScreenV2` (now stateful): trophy hero
    (`gtex_hero_trophy.webp`) under a dark gradient with GTEX bar + jackpot/live pills + headline;
    auto-advancing `PageView` showcase (5 steps, 2.8s, dots; "Play live" uses `gtex_match_live.webp`);
    animated results-ticker marquee; account chooser (primary Player/Club = free·instant CTA + KYC-at-
    withdrawal note; Coin Trader + Creator = apply·verified rows). Wired `onTraderSignup` →
    `gtexTraderSignupRoute` through the route wrapper + router. All three files analyze clean.
    *Needs a device/visual check (couldn't run Flutter here).*
- [ ] Fix persistent **LOADING / "market unavailable" / "unable to reach backend"** states
      (skeletons + the 30k market perf fix).

---

## Audit ledger (✅ works / ⚠️ gap)
- ✅ Coaches: employ (manager_market main/academy/bench) → match influence (team_factory reads employed coach).
- ✅ Player trades: player_cards/marketplace_service (list/buy/swap) + holdings + owner history.
- ✅ Payment + commission: economy_service `fee_bps` (match-entry + marketplace) + wallet ledger.
- ✅ AI coach auto-draft: ai_manager SquadPlanner (formation-by-style + slot scoring); MatchDecisionEngine (live calls); ActivationPolicy (autopilot when owner inactive).
- ✅ 2D match: goals, own-goals, offside, yellow/red, fouls, free kicks, corners, penalties, saves, shots (dist/angle/body-part), injuries, subs, xG, commentary (live_engine + timeline).
- ✅ Matchday entry: simulation_matchmaking + competition orchestration + match_engine api.
- ✅ Live match + watchlist + notify: CompetitionWatchlist + broadcast (room/spectator) + notifications (match_starts_10m / _1m).
- ⚠️ **Owner formation/XI** does not reach the pitch (engine supports it; no persistence; team_factory hardcodes 4-3-3 + auto-selects; formation board UI display-only). → Track B.
- ⚠️ AI coach formation discarded by team_factory hardcode. → Track B.
- ⚠️ Coaches not yet "free to acquire". → Track B.
- ✅ Jackpot: `JackpotService` rounds/contributions/payouts, eligibility-weighted, `is_active` filter.
- ✅ Leaderboard **gates premium comps**: `competition_orchestrator` `gtex_hosted_eligible = ranking_points >= 250` + eligibility tiers.
- ✅ Fast Match: streak logic, "play free until you lose or reach 10 matches".
- ✅ National rental: `pre_qualifier` → representative selection (one per country) → qualifier/tournament stages.
- ✅ Coins: `coin_traders` `user_buys` / `user_sells` with buy/sell rates (users sell own coins). GTEX + Fan coin.
- ✅ AI News: `news_engine` `/personalized` + `daily_news(user_id)` — user-specific.
- ✅ Regen lifecycle: `PlayerRivalry` (intensity/history), offer evaluation, big-club approaches, loyalty/pressure resolution.
- ✅ Regen awards: `awards_engine` — "GTEX World Player of the Year" (Ballon d'Or), Golden Boy, etc.

## Minor verify / tune (not blocking)
- ⚠️ Jackpot **"≥3 drops/day"** explicit cadence — only a 6h failsafe found; confirm/add a guaranteed 3×/day schedule.
- ⚠️ Jackpot **"must be actively playing to win"** — eligibility is contribution + `is_active` based; confirm it requires recent gameplay specifically.
- Coaches free-to-acquire (also in Track B).

## Admin command-centre audit (2026-06-29)
Live `/admin` route = `AdminCommandCenterScreen` (v1, 2687 lines) — **backend-wired**
(authedApi). Surfaces: trade queue, payment rails, withdrawals, deposits, ops readiness,
launch gates, and launchers → trust-ops, launch-control, matchday-economy, coin-traders,
notifications. Plus wired admin screens: trust ops, matchday economy, coin-trader, notification
matrix, create-son (regen).

**Parity gaps found (backend feature → no functional UI):**
- ⚠️ **Jackpot admin** — backend `app/gtex` has `/admin/jackpot/runtime|balance|trigger`. UI panel
  (`gtex_jackpot_admin_panel`) + `GtexAdminJackpotScreenV2` exist but are **orphaned demos** (no-arg
  constructors, static `gtex_admin_command_models` data, 1 ref each = self). Not reachable, not live-wired.
- ⚠️ **Ban user** — backend `POST /admin/ban-user` (`AdminBanUserRequest`: user_id, reason,
  deactivate/freeze_wallet/block_trading/block_withdrawals/manual_review). **Zero UI** (only in the
  generated contract). This is the vision's "admin can ban accounts".
- ⚠️ **Coin-economy admin** — `GtexAdminCoinEconomyScreenV2` orphaned demo (not live-wired).
- ⚠️ `GtexAdminCommandCenterScreenV2` (richer, has jackpot/coin/health/mint panels) — orphaned demo;
  the live admin uses v1 instead.
- ✅ Credit coins (admin_godmode target_user), buy-back, issue-to-traders, create-son, competitions,
  trust ops, matchday economy, notifications — all wired.

**Fixes:**
- [x] **Ban account** — added a launcher + confirm dialog (user_id + reason) in the live v1 admin
  command centre, hitting `POST /api/admin/ban-user` via the authed API. Analyzes clean. (Vision's
  "admin can ban accounts" now has a functional UI.)
- [x] **Jackpot admin** — added a **live "Jackpot control"** action in the v1 admin command centre:
  loads `GET /api/admin/jackpot/runtime` (balance/round/threshold/probability/contribution/distribution/
  failsafe), with **Set balance** (`PATCH /api/admin/jackpot/balance`), **Edit settings**
  (`POST /api/admin/jackpot/runtime`, all levers, validated 0–1 caps), and **Trigger round**
  (`POST /api/admin/jackpot/trigger`, confirm-gated) — all via the authed API, re-fetching after each
  action. The old static `gtex_jackpot_admin_panel` demo is bypassed; the public jackpot route remains
  as "GTEX jackpot (public)". Analyzes clean. Needs device verification.
- [x] **Coin-economy admin** — added a live **"Coin economy"** action in the v1 command centre
  wired to the economy governor: loads `GET /admin/economy/governor` (mode, GTEX/fan supply,
  treasury balance, daily mint/burn, inflation, all policy multipliers + bonus bps, recommended
  actions), with **Edit policy** (`POST /admin/economy/governor/policy`, mode + multipliers +
  price-limit 0–1 + bonus bps 0–5000, validated) and **Re-evaluate**
  (`POST /admin/economy/governor/evaluate`). All via the authed API, re-fetching after each action.
  The static `gtex_coin_economy_panel` demo is bypassed. Analyzes clean. Needs device verification.
> The orphaned v2 screens are mockups; routing them as-is would surface fake data — they must be wired to the live endpoints first.

## Persona journey audit (all ✅ in backend)
- **Coin trader:** apply/profile (`coin_traders`); buy/sell coins (`user_buys`/`user_sells` + buy/sell rates).
- **Admin:** credit BOTH coin types to any user (`admin_godmode` `target_user`, COIN+CREDIT); issue liquidity to traders (`admin_issue_coin_trader_liquidity`); **buy-back** ("Liquidity desk credited user for buyback").
- **Club owner:** trade players (`player_cards/marketplace`); buy club shares/tokens (`club_ownership` `buy-tokens` + `creator_share_market`); buy/sell clubs (`club_sale_market` offers → counter → accept/reject); create cup/league comps (`creator_league` + `hosted_competition_engine`).
- **User (no club):** watch matches/events (`broadcast` spectator); national-team rental (`national_team_engine`); gift coins (`gift_engine /send`, both units); read news (`news_engine`); buy club shares.
- **Withdrawals:** `TreasuryWithdrawalRequest` + `PayoutRequest` + `withdrawal_review` + bank/fee/net + manual-bank-transfer mode.

### Verify (not confirmed gaps)
- ⚠️ Confirm **jackpot + competition winnings** route into the *withdrawable* balance (withdrawal `source_scope` defaults to "trade").
- ⚠️ Confirm withdrawal KYC gating.

## Still to audit (lower priority)
KoraPay payout integration wiring · Club-vs-national competition role gating (user without club blocked from club comps).

## Meta-conclusion
Backend is ~90%+ complete against the full vision across all four personas. The revamp is
**predominantly UI/UX + the Track B gaps**, not missing capability. Highest-leverage work:
Track E (kill the "broken" first impression), Track A (player card/profile), Track C (coach
market UI), then Track B (squad tiers / lineup / multi-position).
