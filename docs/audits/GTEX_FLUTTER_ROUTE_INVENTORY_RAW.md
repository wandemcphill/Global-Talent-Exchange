# GTEX Flutter Screen/Route Inventory

- **Repo path:** `/workspace/frontend` (excludes react-shell)
- **Commit:** `6711a545f06ec6bda28a03379028fb8d63c50a3c`
- **Generated:** code-static inventory (read-only)
- **Primary router:** `lib/router/app_router.dart` (`buildGtexAppRouter`)
- **Feature catalog:** `lib/features/app_routes/gte_route_data.dart` (`GteAppRouteCatalog`, 51 registrations)
- **Registry/builders:** `lib/features/app_routes/gte_app_route_registry.dart` + `gte_feature_route_builders.dart`
- **Published inventory:** `lib/navigation/app_destinations.dart` (`appRouteInventory`)
- **Auth constants:** `lib/router/gtex_auth_routes.dart`

## Summary counts

| Metric | Count |
|---|---:|
| Inventory entries (FL-xxx) | 167 |
| Unique GoRoute path literals (resolved) | ~96 |
| Feature catalog registrations | 51 |
| `appRouteInventory` published surfaces | 32 |
| Public `*Screen` widget classes under lib/ | ~218 |
| Redirect-only aliases | 54 (approx status tag) |
| Status hint `NOT VERIFIED` | 79 |
| Status hint `PARTIAL` | 26 |
| Status hint `NOT IMPLEMENTED` | 8 |
| Status hint `DUPLICATED` | 54 |
| Status hint `BROKEN` | 0 |

## Navigation chrome (drawers / rails / tabs)

### Primary shell rail (`GtePrimaryDestination`)

| Destination | Path | Widget | Notes |
|---|---|---|---|
| Home | `/app/home` | `HomeScreen` | Persona-aware quick actions |
| Matchday | `/app/play/...` | `GtexLiveCompetitionsCommandScreen` | Tabs via `CompetitionHubDestination` |
| Transfer Hub | `/app/market` | `GteMarketPlayersScreenV2` | `?mode=ownership` |
| Regen World | `/app/regens` | `RegensScreenV2` | |
| Studio | `/app/hub` | `GtexStudioHubScreenV2` | Auth-gated |
| Community | `/app/community` | `CommunityScreen` | |
| Club | `/app/club` | Club workspace / owner dashboard | |
| Wallet | `/app/capital` | `GtexWalletOverviewScreenV2` | Modules: orders, holdings, coin-traders, trader-dashboard |

Rail order is **role-dependent** (guest / admin / trader / creator / club owner / default) in `gte_navigation_shell_screen.dart`.

### Matchday / competitions tabs (`CompetitionHubDestination`)

- `/app/play/overview` — Competitions Hub
- `/app/play/leagues` — Leagues
- `/app/play/champions-league` — Champions League
- `/app/play/gtex-fast-cup` — GTEX Fast Cup
- `/app/play/world-super-cup` — World Super Cup
- `/app/play/academy` — Academy

### Wallet modules (`GteCapitalDestination`)

- `/app/capital` — wallet overview
- `/app/capital/orders` — orders
- `/app/capital/holdings` — holdings
- `/app/coin-traders` — coin traders
- `/app/trader-dashboard` — trader dashboard

### Published primary nav (`appDestinations` from `appRouteInventory`)

Home (`/home`), Matchday (`/matches`), Market (`/market`), Arena (`/competitions`), Profile (`/profile`) — these are **legacy path labels**; live shell uses `/app/*` and redirects.

### Auth / signup flow

```
/ → landing (or /app/home if authed)
/account/select → role cards →
  /auth/signup/user | /auth/signup/creator | /auth/signup/trader
/auth/login
Aliases: /auth → select; /profile/login → select; /profile/signup → user signup
```

### Admin routes

| Path | Screen | Guard |
|---|---|---|
| `/admin` | `AdminCommandCenterScreen` | `isAdmin && session` |
| `/admin/launch-control` | `GtexFeatureFlagsLaunchControlScreenV2` | admin |
| `/admin/trust-ops` | `GtexAdminTrustOpsScreenV2` | admin |
| `/admin/matchday-economy` | `GtexMatchdayEconomyAdminScreen` | admin |
| `/admin/notifications` | `GtexAdminNotificationMatrixScreen` | admin |
| `/admin/coin-traders` | `GtexCoinTraderAdminScreen` | admin |
| `/admin/creator-share-market/control` | feature registry | admin role via `_authGuardedScreen` |
| `/admin/creator-stadium/control` | feature registry | admin |
| `/admin/creator-league/financial-report` | feature registry | admin |
| `/admin/creator-league/settlements` | feature registry | admin |
| `/admin/gift-stabilizer` | feature registry | admin |
| `/profile/admin` | redirect → `/admin` | |

Command center also remaps legacy internal paths (`/admin/ops`, `/admin/risk-ops`, `/admin/policies`, `/admin/moderation`, `/admin/disputes`, `/admin/ops/audit`) to `/admin/trust-ops`.

### Auth / Launch Control guards

1. **Shell routes** (`/app/*`): `GtexLaunchControlFeatureGate.resolveRoutePath` — blocked → `GteRouteIntegrityScreen`.
2. **Feature routes**: `_GteGuardedRouteHost` + `GteNavigationGuardResolver` (World Super Cup fallback + feature gate).
3. **Per-builder**: `_authGuardedScreen` / `_authenticatedFeatureScreen` for inventory, share market, owner offers, broadcast builder (unused).
4. **Admin GoRoutes**: explicit `controller.isAdmin && session != null`.
5. **Studio hub**: in-shell sign-in panel if unauthenticated.

### Major redirects map

| From | To |
|---|---|
| `/wallet` | `/app/capital` |
| `/capital` | `/app/capital` |
| `/home` | `/app/home` |
| `/market` | `/app/market` |
| `/competitions` | `/app/play/overview` |
| `/player-cards` | `/app/market` |
| `/world/regens` | `/app/regens` |
| `/clips` | `/news` |
| `/profile/admin` | `/admin` |
| `/profile/login` | `/account/select` |
| `/matches/3d/:matchKey` | `/matches/viewer/:matchKey` |
| `/matches/broadcast/:matchKey` | `/matches/viewer/:matchKey` |
| `/matches/simulate|/spectate|/native-3d` | `/matches` |
| `/national-teams*` | `/national-team` |
| `/market/transfers/:listingId` | `/football/transfer-center` |
| `/managers` | `/coaches` |
| `/match|/match-center|/match/live|/broadcast` | `/broadcast/live` |

---

## Full route/screen inventory

### FL-001: `/`

| Field | Value |
|---|---|
| Widget / screen | `GtexPublicLandingRouteScreenV2` |
| Source | `lib/screens/gtex_public_landing_screen_v2.dart` |
| Intended role | Public landing; redirects to /app/home if authenticated |
| Primary actions | Signup, Login, Creator signup, Trader signup, Explore market |
| API endpoints | None on landing itself |
| Auth guard | Redirect if authenticated → /app/home |
| TODO / stub / redirect / notes | Uses go_router push/go; not imperative Navigator |
| Status hint | **NOT VERIFIED** |

### FL-002: `/landing`

| Field | Value |
|---|---|
| Widget / screen | `GtexPublicLandingRouteScreenV2` |
| Source | `lib/screens/gtex_public_landing_screen_v2.dart` |
| Intended role | Alias of landing |
| Primary actions | Same as FL-001 |
| API endpoints | None |
| Auth guard | Public |
| TODO / stub / redirect / notes | — |
| Status hint | **DUPLICATED** |

### FL-003: `/design-lab`

| Field | Value |
|---|---|
| Widget / screen | `GtexDesignLabScreen` |
| Source | `lib/design_lab/gtex_design_lab_screen.dart` |
| Intended role | Unlinked fixture-only design review |
| Primary actions | Direction query param |
| API endpoints | None (fixtures) |
| Auth guard | Public / unlinked |
| TODO / stub / redirect / notes | Deliberately unlinked; never supplies fixtures to live shell |
| Status hint | **PARTIAL** |

### FL-004: `/design-lab/club-player-progression`

| Field | Value |
|---|---|
| Widget / screen | `GtexClubPlayerProgressionDesignLabScreen` |
| Source | `lib/design_lab/gtex_club_player_progression_design_lab_screen.dart` |
| Intended role | Design lab fixture |
| Primary actions | Browse directions |
| API endpoints | None |
| Auth guard | Public / unlinked |
| TODO / stub / redirect / notes | — |
| Status hint | **PARTIAL** |

### FL-005: `/design-lab/market-ownership`

| Field | Value |
|---|---|
| Widget / screen | `GtexMarketOwnershipDesignLabScreen` |
| Source | `lib/design_lab/gtex_market_ownership_design_lab_screen.dart` |
| Intended role | Design lab fixture |
| Primary actions | Browse |
| API endpoints | None |
| Auth guard | Public / unlinked |
| TODO / stub / redirect / notes | — |
| Status hint | **PARTIAL** |

### FL-006: `/design-lab/competitions`

| Field | Value |
|---|---|
| Widget / screen | `GtexCompetitionDesignLabScreen` |
| Source | `lib/design_lab/gtex_competition_design_lab_screen.dart` |
| Intended role | Competition design exploration |
| Primary actions | Direction query |
| API endpoints | None |
| Auth guard | Public / unlinked |
| TODO / stub / redirect / notes | — |
| Status hint | **PARTIAL** |

### FL-007: `/showroom/:code`

| Field | Value |
|---|---|
| Widget / screen | `PublicShowroomScreen` |
| Source | `lib/features/owner_console/presentation/public_showroom_screen.dart` |
| Intended role | Public owner showroom by code |
| Primary actions | View showroom |
| API endpoints | OwnerConsoleApi.fetchPublicShowroom(code) |
| Auth guard | Public (uses authed API client) |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-008: `/auth`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Auth entry redirect |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /account/select |
| Status hint | **NOT VERIFIED** |

### FL-009: `/account/select`

| Field | Value |
|---|---|
| Widget / screen | `GtexAccountSelectorScreen` |
| Source | `lib/screens/auth/gtex_account_signup_screens.dart` |
| Intended role | Role picker: Player/Club, Creator, Trader |
| Primary actions | Choose role → signup path; Sign in → /auth/login |
| API endpoints | None |
| Auth guard | Public |
| TODO / stub / redirect / notes | Hardcoded role cards |
| Status hint | **NOT VERIFIED** |

### FL-010: `/auth/login`

| Field | Value |
|---|---|
| Widget / screen | `GteLoginScreen` |
| Source | `lib/screens/gte_login_screen.dart` |
| Intended role | Login |
| Primary actions | Email/password login, navigate to app |
| API endpoints | GteExchangeController.login → exchange auth API |
| Auth guard | Public; post-login into shell |
| TODO / stub / redirect / notes | GteLoginScreenV2 lightly referenced (possible legacy) |
| Status hint | **NOT VERIFIED** |

### FL-011: `/auth/signup/user`

| Field | Value |
|---|---|
| Widget / screen | `GtexUserSignupScreen` |
| Source | `lib/screens/auth/gtex_account_signup_screens.dart` |
| Intended role | Player/club signup |
| Primary actions | Register, TOTP setup |
| API endpoints | Signup via exchange API client |
| Auth guard | Public |
| TODO / stub / redirect / notes | TOTP secret generated client-side |
| Status hint | **NOT VERIFIED** |

### FL-012: `/auth/signup/creator`

| Field | Value |
|---|---|
| Widget / screen | `GtexCreatorSignupScreen` |
| Source | `lib/screens/auth/gtex_account_signup_screens.dart` |
| Intended role | Creator signup |
| Primary actions | Register as creator |
| API endpoints | Signup API |
| Auth guard | Public |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-013: `/auth/signup/trader`

| Field | Value |
|---|---|
| Widget / screen | `GtexTraderSignupScreen` |
| Source | `lib/screens/auth/gtex_account_signup_screens.dart` |
| Intended role | Trader signup |
| Primary actions | Register as trader |
| API endpoints | Signup API |
| Auth guard | Public |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-014: `/auth/select-account`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/gtex_auth_routes.dart` |
| Intended role | Legacy auth select |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /account/select |
| Status hint | **DUPLICATED** |

### FL-015: `/profile/login`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Legacy login deep link |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /account/select (not /auth/login) |
| Status hint | **NOT VERIFIED** |

### FL-016: `/profile/signup`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Legacy signup |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /auth/signup/user |
| Status hint | **NOT VERIFIED** |

### FL-017: `/app`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Shell root |
| Primary actions | — |
| API endpoints | — |
| Auth guard | Launch Control gate on child routes |
| TODO / stub / redirect / notes | → /app/home |
| Status hint | **NOT VERIFIED** |

### FL-018: `/app/:section`

| Field | Value |
|---|---|
| Widget / screen | `GteExchangeShellScreen → GteNavigationShellScreen` |
| Source | `lib/screens/gte_exchange_shell_screen.dart; lib/features/navigation/presentation/gte_navigation_shell_screen.dart` |
| Intended role | Primary app shell lane |
| Primary actions | Nav rail destinations; world-pulse rail ≥1700px |
| API endpoints | Shell APIs per destination |
| Auth guard | Launch Control FeatureGate on path; hub requires auth |
| TODO / stub / redirect / notes | Named shell.lane; wraps _GtexLaunchControlledShellRoute |
| Status hint | **NOT VERIFIED** |

### FL-019: `/app/:section/:subsection`

| Field | Value |
|---|---|
| Widget / screen | `GteExchangeShellScreen` |
| Source | `same` |
| Intended role | Shell sub-lane (play tabs, capital modules) |
| Primary actions | Competition hub tabs / capital modules |
| API endpoints | Per destination |
| Auth guard | Launch Control |
| TODO / stub / redirect / notes | Named shell.sub-lane |
| Status hint | **NOT VERIFIED** |

### FL-020: `/app/home`

| Field | Value |
|---|---|
| Widget / screen | `HomeScreen` |
| Source | `lib/features/home/home_screen.dart` |
| Intended role | Personalized Home / Club HQ |
| Primary actions | Quick actions from appRouteInventory; admin controls; persona panels |
| API endpoints | Home digest provider + exchange session |
| Auth guard | Guest OK with limited actions; sign-in CTA |
| TODO / stub / redirect / notes | Quick actions include matches, market, tasks, profileAdmin, coaches, lineup |
| Status hint | **NOT VERIFIED** |

### FL-021: `/app/play(/:tab)`

| Field | Value |
|---|---|
| Widget / screen | `GtexLiveCompetitionsCommandScreen` |
| Source | `lib/features/competitions/presentation/gtex_live_competitions_command_screen.dart` |
| Intended role | Matchday / competitions shell lane |
| Primary actions | Hub tabs: overview, leagues, CL, Fast Cup, WSC, academy |
| API endpoints | Competition APIs via shell |
| Auth guard | Login CTA for host actions |
| TODO / stub / redirect / notes | Tabs via CompetitionHubDestination path segments |
| Status hint | **NOT VERIFIED** |

### FL-022: `/app/market`

| Field | Value |
|---|---|
| Widget / screen | `GteMarketPlayersScreenV2` |
| Source | `lib/screens/gte_market_players_screen_v2.dart` |
| Intended role | Transfer Hub market desk |
| Primary actions | Buy/bid/list; mode=ownership query |
| API endpoints | Market/player APIs via controller |
| Auth guard | Login for trade actions |
| TODO / stub / redirect / notes | Alias /app/transfer-hub same shell |
| Status hint | **NOT VERIFIED** |

### FL-023: `/app/transfer-hub`

| Field | Value |
|---|---|
| Widget / screen | `GteMarketPlayersScreenV2 (via shell)` |
| Source | `lib/screens/gte_market_players_screen_v2.dart` |
| Intended role | Alias for market shell |
| Primary actions | Same as FL-022 |
| API endpoints | Same |
| Auth guard | Launch Control |
| TODO / stub / redirect / notes | NOT football transfer-center |
| Status hint | **DUPLICATED** |

### FL-024: `/app/regens`

| Field | Value |
|---|---|
| Widget / screen | `RegensScreenV2` |
| Source | `lib/features/regens/regens_screen_v2.dart` |
| Intended role | Regen World shell lane |
| Primary actions | Browse regens; Open awards |
| API endpoints | Regen APIs |
| Auth guard | Guest browse; admin create-son affordances |
| TODO / stub / redirect / notes | Formerly bare /world/regens white page |
| Status hint | **NOT VERIFIED** |

### FL-025: `/app/hub`

| Field | Value |
|---|---|
| Widget / screen | `GtexStudioHubScreenV2` |
| Source | `lib/screens/creators/gtex_studio_hub_screen_v2.dart` |
| Intended role | Creator Studio hub |
| Primary actions | Referrals, creator tools, access request |
| API endpoints | ReferralApi, CreatorApi |
| Auth guard | AUTH REQUIRED — sign-in panel if guest |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-026: `/app/community`

| Field | Value |
|---|---|
| Widget / screen | `CommunityScreen` |
| Source | `lib/features/social/social_screen.dart` |
| Intended role | Community / social feed |
| Primary actions | Open Fan Wars, Club, Market, Regens |
| API endpoints | CommunityApi |
| Auth guard | Guest OK; login for posts |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-027: `/app/club`

| Field | Value |
|---|---|
| Widget / screen | `GtexEmpireClubWorkspace / GtexClubOwnerDashboardScreenV2` |
| Source | `lib/features/club_redesign/presentation/gtex_empire_club_workspace.dart; lib/screens/clubs/gtex_club_owner_dashboard_screen_v2.dart` |
| Intended role | Club owner workspace |
| Primary actions | Create club, ops, identity |
| API endpoints | Club creation + club APIs |
| Auth guard | Auth preferred; create-club flow signs in |
| TODO / stub / redirect / notes | CreateClubScreen via MaterialPageRoute push |
| Status hint | **NOT VERIFIED** |

### FL-028: `/app/capital`

| Field | Value |
|---|---|
| Widget / screen | `GtexWalletOverviewScreenV2` |
| Source | `lib/screens/wallet/gtex_wallet_overview_screen_v2.dart` |
| Intended role | Wallet / capital desk |
| Primary actions | Top up, Withdraw, module tabs |
| API endpoints | Wallet/capital APIs via authedApi |
| Auth guard | Login for fund/withdraw |
| TODO / stub / redirect / notes | /wallet and /capital redirect here |
| Status hint | **NOT VERIFIED** |

### FL-029: `/app/capital/orders`

| Field | Value |
|---|---|
| Widget / screen | `GtexWalletOverviewScreenV2 (orders module)` |
| Source | `same` |
| Intended role | Orders module |
| Primary actions | View orders |
| API endpoints | Orders endpoints |
| Auth guard | Auth preferred |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-030: `/app/capital/holdings`

| Field | Value |
|---|---|
| Widget / screen | `GtexWalletOverviewScreenV2 (holdings)` |
| Source | `same` |
| Intended role | Holdings module |
| Primary actions | View holdings |
| API endpoints | Holdings |
| Auth guard | Auth preferred |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-031: `/app/coin-traders`

| Field | Value |
|---|---|
| Widget / screen | `GtexWalletOverviewScreenV2 (coin traders)` |
| Source | `same` |
| Intended role | Coin traders desk |
| Primary actions | Trade GTC/FNC |
| API endpoints | Coin trader APIs |
| Auth guard | Auth preferred |
| TODO / stub / redirect / notes | /trader, /coin-traders redirect here |
| Status hint | **NOT VERIFIED** |

### FL-032: `/app/trader-dashboard`

| Field | Value |
|---|---|
| Widget / screen | `GtexWalletOverviewScreenV2 (trader dashboard)` |
| Source | `same` |
| Intended role | Trader dashboard module |
| Primary actions | Trader ops |
| API endpoints | Trader APIs |
| Auth guard | Auth preferred |
| TODO / stub / redirect / notes | TraderDashboardScreen appears lightly wired / possibly orphaned |
| Status hint | **PARTIAL** |

### FL-033: `(push) Fund wallet`

| Field | Value |
|---|---|
| Widget / screen | `GteFundWalletScreen` |
| Source | `lib/screens/wallet/gte_funding_flow_screen.dart` |
| Intended role | Deposit / top-up flow |
| Primary actions | Select method, confirm deposit |
| API endpoints | Funding/deposit APIs via controller |
| Auth guard | Auth required (shell gates) |
| TODO / stub / redirect / notes | Navigator.push from wallet |
| Status hint | **NOT VERIFIED** |

### FL-034: `(push) Withdraw`

| Field | Value |
|---|---|
| Widget / screen | `GteWithdrawalFlowScreen` |
| Source | `lib/screens/wallet/gte_withdrawal_flow_screen.dart` |
| Intended role | Withdrawal flow |
| Primary actions | Bank details, withdraw |
| API endpoints | Withdrawal APIs |
| Auth guard | Auth required |
| TODO / stub / redirect / notes | Navigator.push from wallet |
| Status hint | **NOT VERIFIED** |

### FL-035: `(push) Creator access`

| Field | Value |
|---|---|
| Widget / screen | `CreatorAccessRequestScreen` |
| Source | `lib/screens/creators/creator_access_request_screen.dart` |
| Intended role | Request creator access |
| Primary actions | Submit application |
| API endpoints | Creator application API |
| Auth guard | Auth required |
| TODO / stub / redirect / notes | MaterialPageRoute from hub |
| Status hint | **NOT VERIFIED** |

### FL-036: `(push) Create club`

| Field | Value |
|---|---|
| Widget / screen | `CreateClubScreen` |
| Source | `lib/screens/clubs/create_club_screen.dart` |
| Intended role | Create club wizard |
| Primary actions | Name, branding, submit |
| API endpoints | ClubCreationApi |
| Auth guard | Auth required |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-037: `/home`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Legacy alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /app/home |
| Status hint | **DUPLICATED** |

### FL-038: `/market`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Legacy alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /app/market |
| Status hint | **DUPLICATED** |

### FL-039: `/player-market`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Legacy alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /app/market |
| Status hint | **DUPLICATED** |

### FL-040: `/player-cards`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Legacy alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /app/market |
| Status hint | **DUPLICATED** |

### FL-041: `/competitions`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Legacy alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /app/play/overview |
| Status hint | **DUPLICATED** |

### FL-042: `/competitions/hosted`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Legacy alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /app/play/overview |
| Status hint | **DUPLICATED** |

### FL-043: `/competitions/gtex`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Legacy alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /app/play/overview |
| Status hint | **DUPLICATED** |

### FL-044: `/competitions/streamer/engine`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Legacy alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /app/play/overview |
| Status hint | **DUPLICATED** |

### FL-045: `/streamer-tournaments`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Legacy alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /app/play/overview |
| Status hint | **DUPLICATED** |

### FL-046: `/play`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Legacy alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /app/play/overview |
| Status hint | **DUPLICATED** |

### FL-047: `/world/regens`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Legacy alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /app/regens |
| Status hint | **DUPLICATED** |

### FL-048: `/club`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Legacy alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /app/club |
| Status hint | **DUPLICATED** |

### FL-049: `/wallet`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Legacy alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /app/capital |
| Status hint | **DUPLICATED** |

### FL-050: `/capital`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Legacy alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /app/capital |
| Status hint | **DUPLICATED** |

### FL-051: `/coin-traders`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Legacy alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /app/coin-traders |
| Status hint | **DUPLICATED** |

### FL-052: `/trader`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Legacy alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /app/coin-traders |
| Status hint | **DUPLICATED** |

### FL-053: `/trader-dashboard`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Legacy alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /app/trader-dashboard |
| Status hint | **DUPLICATED** |

### FL-054: `/orders`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Legacy alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /app/capital/orders |
| Status hint | **DUPLICATED** |

### FL-055: `/payments`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Legacy alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /app/capital |
| Status hint | **DUPLICATED** |

### FL-056: `/community`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Legacy alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /app/community |
| Status hint | **DUPLICATED** |

### FL-057: `/social`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Legacy alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /app/community |
| Status hint | **DUPLICATED** |

### FL-058: `/chat`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Legacy alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /app/community |
| Status hint | **DUPLICATED** |

### FL-059: `/inbox`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Legacy alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /app/community |
| Status hint | **DUPLICATED** |

### FL-060: `/world`

| Field | Value |
|---|---|
| Widget / screen | `FootballWorldSimulationScreen (via registry)` |
| Source | `lib/features/football_world_simulation/` |
| Intended role | World overview desk |
| Primary actions | Open federations, clubs, competitions |
| API endpoints | World simulation APIs |
| Auth guard | Launch Control + guard |
| TODO / stub / redirect / notes | Also in catalog; guardedScreenFor |
| Status hint | **NOT VERIFIED** |

### FL-061: `/world/federations`

| Field | Value |
|---|---|
| Widget / screen | `FederationsHubRouteScreen` |
| Source | `lib/features/federations/federations_hub_screen.dart` |
| Intended role | Federations list/hub |
| Primary actions | Open federation detail |
| API endpoints | Federations via authed API |
| Auth guard | Public-ish |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-062: `/world/federations/:federationId`

| Field | Value |
|---|---|
| Widget / screen | `FederationDetailRouteScreen` |
| Source | `lib/features/federations/federations_hub_screen.dart` |
| Intended role | Federation detail |
| Primary actions | View ranking/governance |
| API endpoints | Federation detail API |
| Auth guard | Public-ish |
| TODO / stub / redirect / notes | Empty id redirects to federations list |
| Status hint | **NOT VERIFIED** |

### FL-063: `/world/awards`

| Field | Value |
|---|---|
| Widget / screen | `GtexAwardsScreenV2` |
| Source | `lib/features/awards/gtex_awards_screen_v2.dart` |
| Intended role | Awards desk |
| Primary actions | Browse awards |
| API endpoints | Awards API |
| Auth guard | Token optional |
| TODO / stub / redirect / notes | /awards redirects here |
| Status hint | **NOT VERIFIED** |

### FL-064: `/federations`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /world/federations |
| Status hint | **DUPLICATED** |

### FL-065: `/awards`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /world/awards |
| Status hint | **DUPLICATED** |

### FL-066: `/regens`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /world/regens (catalog) which then → /app/regens |
| Status hint | **DUPLICATED** |

### FL-067: `/regen-world`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → RegenUniverseRouteData URI /world/regens |
| Status hint | **DUPLICATED** |

### FL-068: `/market/transfers`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Legacy transfer listings |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /football/transfer-center |
| Status hint | **DUPLICATED** |

### FL-069: `/market/transfers/:listingId`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Deep transfer listing (no dedicated screen) |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /football/transfer-center (degrades; no listing detail UI) |
| Status hint | **NOT IMPLEMENTED** |

### FL-070: `/football/transfer-center`

| Field | Value |
|---|---|
| Widget / screen | `TransferNewsCalendarScreen` |
| Source | `lib/features/transfer_news_calendar/presentation/transfer_news_calendar_screen.dart` |
| Intended role | Transfer news calendar (windows/media/calendar tabs) |
| Primary actions | Tab switch via ?tab= |
| API endpoints | Transfer calendar APIs |
| Auth guard | Login CTA |
| TODO / stub / redirect / notes | Shell-owned path excluded from feature GoRoute auto-reg; explicit GoRoute |
| Status hint | **NOT VERIFIED** |

### FL-071: `/national-team`

| Field | Value |
|---|---|
| Widget / screen | `GtexNationalTeamRentalScreenV2` |
| Source | `lib/screens/gtex_national_team_rental_screen_v2.dart` |
| Intended role | National team rental surface |
| Primary actions | Browse competitions, rent, login |
| API endpoints | nationalTeams repository |
| Auth guard | Guest + login CTA |
| TODO / stub / redirect / notes | Catalog NationalTeamCompetitionsRouteData excluded (shellOwned); rental screen wins over feature builder |
| Status hint | **PARTIAL** |

### FL-072: `/national-teams`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Plural misspelling alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /national-team |
| Status hint | **DUPLICATED** |

### FL-073: `/national-teams/:competitionId`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Deep plural; no per-competition screen |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /national-team |
| Status hint | **NOT IMPLEMENTED** |

### FL-074: `/rentals`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /national-team |
| Status hint | **DUPLICATED** |

### FL-075: `/national-rentals`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /national-team |
| Status hint | **DUPLICATED** |

### FL-076: `/players/:playerId/profile`

| Field | Value |
|---|---|
| Widget / screen | `GtexFmPlayerProfileScreen` |
| Source | `lib/features/player_detail/gtex_fm_player_profile_screen.dart` |
| Intended role | FM-style player profile |
| Primary actions | View attributes, open market |
| API endpoints | Player profile APIs |
| Auth guard | Token optional |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-077: `/lineup`

| Field | Value |
|---|---|
| Widget / screen | `GtexLineupEditorScreen` |
| Source | `lib/features/club/gtex_lineup_editor_screen.dart` |
| Intended role | Formation / lineup editor |
| Primary actions | Set XI, save formation |
| API endpoints | Lineup club APIs |
| Auth guard | Needs clubId; blocked panel if no club |
| TODO / stub / redirect / notes | Home club-owner quick action |
| Status hint | **PARTIAL** |

### FL-078: `/coaches`

| Field | Value |
|---|---|
| Widget / screen | `ManagerMarketScreen` |
| Source | `lib/screens/manager_market_screen.dart` |
| Intended role | Manager/coach market |
| Primary actions | Hire/compare coaches; Open admin |
| API endpoints | Manager market APIs |
| Auth guard | Token; admin button → /admin |
| TODO / stub / redirect / notes | /managers redirects here |
| Status hint | **NOT VERIFIED** |

### FL-079: `/managers`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Alias |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /coaches |
| Status hint | **DUPLICATED** |

### FL-080: `/tasks`

| Field | Value |
|---|---|
| Widget / screen | `GtexDailyChallengesScreen` |
| Source | `lib/features/tasks/gtex_daily_challenges_screen.dart` |
| Intended role | Daily challenges / streaks |
| Primary actions | Claim tasks; Sign in |
| API endpoints | Tasks/challenges APIs |
| Auth guard | Sign-in CTA → profileLogin |
| TODO / stub / redirect / notes | Was published without screen; now registered |
| Status hint | **NOT VERIFIED** |

### FL-081: `/clips`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Clips → News desk |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /news |
| Status hint | **DUPLICATED** |

### FL-082: `/viral`

| Field | Value |
|---|---|
| Widget / screen | `ViralFeedScreen` |
| Source | `lib/features/viral_feed/presentation/viral_feed_screen.dart` |
| Intended role | Viral feed |
| Primary actions | Scroll feed |
| API endpoints | ViralFeedApiRepository |
| Auth guard | User id optional |
| TODO / stub / redirect / notes | Duplicate of /viral-feed |
| Status hint | **DUPLICATED** |

### FL-083: `/viral-feed`

| Field | Value |
|---|---|
| Widget / screen | `ViralFeedScreen` |
| Source | `lib/features/viral_feed/presentation/viral_feed_screen.dart` |
| Intended role | Canonical viral feed |
| Primary actions | Scroll feed |
| API endpoints | ViralFeedApiRepository |
| Auth guard | Optional |
| TODO / stub / redirect / notes | Also in catalog; shellOwned excludes auto feature route for /viral-feed but explicit GoRoute exists |
| Status hint | **NOT VERIFIED** |

### FL-084: `/profile`

| Field | Value |
|---|---|
| Widget / screen | `GtexLiveProfileScreen` |
| Source | `lib/screens/profile/gtex_live_profile_screen.dart` |
| Intended role | Profile / identity |
| Primary actions | Edit profile, wallet links, admin access |
| API endpoints | Profile/session APIs |
| Auth guard | Shows guest vs signed-in |
| TODO / stub / redirect / notes | /settings and /account duplicate same screen |
| Status hint | **NOT VERIFIED** |

### FL-085: `/settings`

| Field | Value |
|---|---|
| Widget / screen | `GtexLiveProfileScreen` |
| Source | `same` |
| Intended role | Settings alias |
| Primary actions | Same |
| API endpoints | Same |
| Auth guard | Same |
| TODO / stub / redirect / notes | DUPLICATED surface |
| Status hint | **DUPLICATED** |

### FL-086: `/account`

| Field | Value |
|---|---|
| Widget / screen | `GtexLiveProfileScreen` |
| Source | `same` |
| Intended role | Account alias |
| Primary actions | Same |
| API endpoints | Same |
| Auth guard | Same |
| TODO / stub / redirect / notes | DUPLICATED surface |
| Status hint | **DUPLICATED** |

### FL-087: `/notifications`

| Field | Value |
|---|---|
| Widget / screen | `GteNotificationsScreenV2` |
| Source | `lib/screens/notifications/gte_notifications_screen_v2.dart` |
| Intended role | Notifications center |
| Primary actions | Mark read, open items |
| API endpoints | Notifications API |
| Auth guard | Exchange controller session |
| TODO / stub / redirect / notes | V1 GteNotificationsScreen lightly referenced |
| Status hint | **NOT VERIFIED** |

### FL-088: `/kyc`

| Field | Value |
|---|---|
| Widget / screen | `GteKycScreen` |
| Source | `lib/screens/wallet/gte_kyc_screen.dart` |
| Intended role | KYC / identity verification |
| Primary actions | Submit KYC docs |
| API endpoints | KYC APIs |
| Auth guard | Auth expected |
| TODO / stub / redirect / notes | GtexKycScreenV2 lightly wired |
| Status hint | **PARTIAL** |

### FL-089: `/compliance`

| Field | Value |
|---|---|
| Widget / screen | `GteKycScreen` |
| Source | `same` |
| Intended role | Compliance alias of KYC |
| Primary actions | Same |
| API endpoints | Same |
| Auth guard | Same |
| TODO / stub / redirect / notes | DUPLICATED |
| Status hint | **DUPLICATED** |

### FL-090: `/disputes`

| Field | Value |
|---|---|
| Widget / screen | `GteDisputeHubScreen` |
| Source | `lib/screens/support/gte_support_dispute_screens.dart` |
| Intended role | Dispute hub |
| Primary actions | Open/create disputes |
| API endpoints | Dispute APIs |
| Auth guard | Auth expected |
| TODO / stub / redirect / notes | GtexDisputesScreenV2 lightly wired |
| Status hint | **PARTIAL** |

### FL-091: `/support`

| Field | Value |
|---|---|
| Widget / screen | `GteDisputeHubScreen` |
| Source | `same` |
| Intended role | Support alias |
| Primary actions | Same |
| API endpoints | Same |
| Auth guard | Same |
| TODO / stub / redirect / notes | DUPLICATED |
| Status hint | **DUPLICATED** |

### FL-092: `/matches`

| Field | Value |
|---|---|
| Widget / screen | `GteLiveMatchHubRouteScreen` |
| Source | `lib/features/match/gte_live_match_hub_route_screen.dart` |
| Intended role | Matchday hub (live fixtures) |
| Primary actions | Open viewer, fixtures |
| API endpoints | Match repository / live hub |
| Auth guard | Optional |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-093: `/matches/viewer/:matchKey`

| Field | Value |
|---|---|
| Widget / screen | `MatchViewerRouteScreen` |
| Source | `lib/features/match/match_viewer_route_screen.dart` |
| Intended role | Canonical 2D match viewer |
| Primary actions | Watch live/replay |
| API endpoints | Match session feed |
| Auth guard | Optional; fallback gate if unavailable |
| TODO / stub / redirect / notes | Truthful fallback when feed unavailable |
| Status hint | **NOT VERIFIED** |

### FL-094: `/match-viewer/:matchKey`

| Field | Value |
|---|---|
| Widget / screen | `MatchViewerRouteScreen` |
| Source | `same` |
| Intended role | Alias viewer |
| Primary actions | Same |
| API endpoints | Same |
| Auth guard | Same |
| TODO / stub / redirect / notes | DUPLICATED path |
| Status hint | **DUPLICATED** |

### FL-095: `/matches/broadcast/:matchKey`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Legacy broadcast |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /matches/viewer/:matchKey |
| Status hint | **DUPLICATED** |

### FL-096: `/matches/3d/:matchKey`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | 3D match (Unity blocked) |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | Hidden while Unity blocked → 2D viewer |
| Status hint | **NOT IMPLEMENTED** |

### FL-097: `/matches/native-3d`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Native 3D blocked |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /matches |
| Status hint | **NOT IMPLEMENTED** |

### FL-098: `/matches/spectate`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Legacy spectate |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /matches; MatchSpectateScreen orphaned |
| Status hint | **NOT IMPLEMENTED** |

### FL-099: `/matches/simulate`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Legacy simulate |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /matches; MatchSimulateRouteScreen orphaned |
| Status hint | **NOT IMPLEMENTED** |

### FL-100: `/match`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | → Broadcast desk |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /broadcast/live |
| Status hint | **DUPLICATED** |

### FL-101: `/match-center`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | → Broadcast desk |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /broadcast/live |
| Status hint | **DUPLICATED** |

### FL-102: `/match/live`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | → Broadcast desk |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /broadcast/live |
| Status hint | **DUPLICATED** |

### FL-103: `/live-match/:matchId`

| Field | Value |
|---|---|
| Widget / screen | `GtexMatchCenterScreenV2` |
| Source | `lib/screens/match/gtex_match_center_screen_v2.dart` |
| Intended role | Live match center / 2D surface |
| Primary actions | Watch; Open replay; Exit to broadcast desk |
| API endpoints | matches repository |
| Auth guard | Optional |
| TODO / stub / redirect / notes | Empty matchId → blocked integrity screen |
| Status hint | **NOT VERIFIED** |

### FL-104: `/broadcast`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | → /broadcast/live |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | — |
| Status hint | **DUPLICATED** |

### FL-105: `/admin`

| Field | Value |
|---|---|
| Widget / screen | `AdminCommandCenterScreen` |
| Source | `lib/screens/admin/admin_command_center_screen.dart` |
| Intended role | Admin command center |
| Primary actions | Ban user, jackpot ops, economy governor, open sub-admin routes, seed competitions |
| API endpoints | /api/admin/ban-user, /api/admin/jackpot/*, /admin/economy/governor*, /api/admin/hosted-competitions/seed |
| Auth guard | ADMIN + session required; else integrity blocked |
| TODO / stub / redirect / notes | Internal nav remaps /admin/ops|/risk-ops|/policies|/moderation|/disputes|/ops/audit → /admin/trust-ops |
| Status hint | **NOT VERIFIED** |

### FL-106: `/profile/admin`

| Field | Value |
|---|---|
| Widget / screen | `(redirect)` |
| Source | `lib/router/app_router.dart` |
| Intended role | Home admin quick action target |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | → /admin (was previously unregistered dead button) |
| Status hint | **DUPLICATED** |

### FL-107: `/admin/launch-control`

| Field | Value |
|---|---|
| Widget / screen | `GtexFeatureFlagsLaunchControlScreenV2` |
| Source | `lib/features/launch_control_redesign/gtex_feature_flags_launch_control_screen_v2.dart` |
| Intended role | Feature flags / rollout control |
| Primary actions | Toggle flags, kill switches |
| API endpoints | Launch control admin APIs |
| Auth guard | ADMIN + session |
| TODO / stub / redirect / notes | Gates shell routes via GtexLaunchControlFeatureGate |
| Status hint | **NOT VERIFIED** |

### FL-108: `/admin/trust-ops`

| Field | Value |
|---|---|
| Widget / screen | `GtexAdminTrustOpsScreenV2` |
| Source | `lib/screens/admin/gtex_admin_trust_ops_screen_v2.dart` |
| Intended role | KYC/disputes/risk/policies desk |
| Primary actions | Trust ops workflows |
| API endpoints | Trust ops APIs |
| Auth guard | ADMIN + session |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-109: `/admin/matchday-economy`

| Field | Value |
|---|---|
| Widget / screen | `GtexMatchdayEconomyAdminScreen` |
| Source | `lib/features/matchday_economy_redesign/matchday_economy_screen.dart` |
| Intended role | Matchday economy admin |
| Primary actions | Fan rewards, ticketing, collectibles signals |
| API endpoints | Matchday economy admin APIs |
| Auth guard | ADMIN + session |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-110: `/admin/notifications`

| Field | Value |
|---|---|
| Widget / screen | `GtexAdminNotificationMatrixScreen` |
| Source | `lib/screens/admin/gtex_admin_notification_matrix_screen.dart` |
| Intended role | Notification matrix / test events |
| Primary actions | Send test notifications |
| API endpoints | Admin notification APIs |
| Auth guard | ADMIN + session |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-111: `/admin/coin-traders`

| Field | Value |
|---|---|
| Widget / screen | `GtexCoinTraderAdminScreen` |
| Source | `lib/features/coin_trader_redesign/coin_trader_panels.dart` |
| Intended role | Coin trader approvals / escrow |
| Primary actions | Approve/reject/freeze traders |
| API endpoints | GtexCoinTraderApi admin endpoints |
| Auth guard | ADMIN + session |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-112: `/competitions/create`

| Field | Value |
|---|---|
| Widget / screen | `CompetitionCreateScreenV2` |
| Source | `lib/screens/competitions/competition_create_screen_v2.dart` |
| Intended role | Create hosted competition |
| Primary actions | Draft → publish |
| API endpoints | CompetitionApi |
| Auth guard | Auth preferred; login CTA |
| TODO / stub / redirect / notes | Feature catalog; /competitions itself redirects to shell |
| Status hint | **NOT VERIFIED** |

### FL-113: `/competitions/world-super-cup`

| Field | Value |
|---|---|
| Widget / screen | `GteCompetitionsHubScreenV2 (guarded)` |
| Source | `lib/features/competitions_hub/presentation/gte_competitions_hub_screen_v2.dart` |
| Intended role | World Super Cup deep link |
| Primary actions | Open active WSC or fallback discovery |
| API endpoints | CompetitionApi.fetchCompetitions |
| Auth guard | Guard may redirect to discovery if inactive |
| TODO / stub / redirect / notes | GteNavigationGuardResolver inactiveWorldSuperCup |
| Status hint | **PARTIAL** |

### FL-114: `/competitions/:competitionId`

| Field | Value |
|---|---|
| Widget / screen | `GteCompetitionsHubScreenV2` |
| Source | `same` |
| Intended role | Competition detail via hub |
| Primary actions | Join, share, manage |
| API endpoints | CompetitionApi |
| Auth guard | Auth for host/join |
| TODO / stub / redirect / notes | Detail/join/share all map to same hub screen with params |
| Status hint | **PARTIAL** |

### FL-115: `/competitions/:competitionId/join`

| Field | Value |
|---|---|
| Widget / screen | `GteCompetitionsHubScreenV2` |
| Source | `same` |
| Intended role | Join competition |
| Primary actions | Join with inviteCode |
| API endpoints | CompetitionApi |
| Auth guard | Auth |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-116: `/competitions/:competitionId/share`

| Field | Value |
|---|---|
| Widget / screen | `GteCompetitionsHubScreenV2` |
| Source | `same` |
| Intended role | Share competition |
| Primary actions | Share links |
| API endpoints | CompetitionApi |
| Auth guard | Optional |
| TODO / stub / redirect / notes | Legacy CompetitionShareScreen exists |
| Status hint | **DUPLICATED** |

### FL-117: `/streamer-tournaments/:tournamentId`

| Field | Value |
|---|---|
| Widget / screen | `StreamerTournamentEngineScreen` |
| Source | `lib/features/streamer_tournament_engine/presentation/streamer_tournament_engine_screen.dart` |
| Intended role | Streamer tournament detail |
| Primary actions | Manage tournament |
| API endpoints | Streamer tournament APIs |
| Auth guard | Login CTA |
| TODO / stub / redirect / notes | List path /streamer-tournaments redirects to shell play |
| Status hint | **PARTIAL** |

### FL-118: `/fan-predictions/matches/:matchId`

| Field | Value |
|---|---|
| Widget / screen | `FanPredictionScreen` |
| Source | `lib/features/fan_prediction/presentation/fan_prediction_screen.dart` |
| Intended role | Fan predictions for match |
| Primary actions | Place predictions |
| API endpoints | Fan prediction APIs |
| Auth guard | Login CTA |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-119: `/player-cards/players/:playerId`

| Field | Value |
|---|---|
| Widget / screen | `GteFeatureRouteContent (async)` |
| Source | `lib/features/app_routes/gte_feature_route_builders.dart` |
| Intended role | Player card detail metrics panel |
| Primary actions | Back to browse |
| API endpoints | GET /player-cards/players/:id |
| Auth guard | Public feature screen |
| TODO / stub / redirect / notes | Browse /player-cards redirects to market shell; inventory is auth-gated |
| Status hint | **PARTIAL** |

### FL-120: `/player-cards/inventory`

| Field | Value |
|---|---|
| Widget / screen | `PlayerCardMarketplaceScreen` |
| Source | `lib/features/player_card_marketplace/presentation/player_card_marketplace_screen.dart` |
| Intended role | Owned cards inventory |
| Primary actions | Open card detail |
| API endpoints | Marketplace APIs |
| Auth guard | AUTH required (_authGuardedScreen) |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-121: `/creator-share-market/clubs/:clubId`

| Field | Value |
|---|---|
| Widget / screen | `CreatorShareMarketScreen` |
| Source | `lib/features/creator_share_market/presentation/creator_share_market_screen.dart` |
| Intended role | Creator share market for club |
| Primary actions | Trade shares |
| API endpoints | Share market APIs |
| Auth guard | AUTH required |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-122: `/admin/creator-share-market/control`

| Field | Value |
|---|---|
| Widget / screen | `CreatorShareMarketAdminControlScreen` |
| Source | `lib/features/creator_share_market/presentation/creator_share_market_admin_control_screen.dart` |
| Intended role | Share market admin |
| Primary actions | Admin controls |
| API endpoints | Admin share market APIs |
| Auth guard | AUTH + ADMIN role |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-123: `/clubs/sale-market`

| Field | Value |
|---|---|
| Widget / screen | `ClubSaleMarketScreen` |
| Source | `lib/features/club_sale_market/presentation/club_sale_market_screen.dart` |
| Intended role | Club sale listings |
| Primary actions | Browse/buy clubs |
| API endpoints | ClubSaleMarketApiRepository |
| Auth guard | Login CTA |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-124: `/clubs/:clubId/sale-market`

| Field | Value |
|---|---|
| Widget / screen | `ClubSaleMarketScreen` |
| Source | `same` |
| Intended role | Club sale detail |
| Primary actions | Bid/offer |
| API endpoints | Sale market APIs |
| Auth guard | Login CTA |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-125: `/clubs/:clubId/sale-market/offers`

| Field | Value |
|---|---|
| Widget / screen | `ClubSaleMarketScreen (owner inbox)` |
| Source | `same` |
| Intended role | Owner offer inbox |
| Primary actions | Review offers |
| API endpoints | listOffers(clubId) |
| Auth guard | AUTH + owner authorization check |
| TODO / stub / redirect / notes | Unauthorized → lock panel |
| Status hint | **PARTIAL** |

### FL-126: `/news`

| Field | Value |
|---|---|
| Widget / screen | `GtexNewsAgencyScreenV2` |
| Source | `lib/features/news_agency/gtex_news_agency_screen_v2.dart` |
| Intended role | News desk / clips destination |
| Primary actions | Read stories |
| API endpoints | StoryFeedApi |
| Auth guard | Optional token |
| TODO / stub / redirect / notes | /clips redirects here |
| Status hint | **NOT VERIFIED** |

### FL-127: `/fan-wars`

| Field | Value |
|---|---|
| Widget / screen | `FanWarsScreen` |
| Source | `lib/features/fan_wars/presentation/fan_wars_screen.dart` |
| Intended role | Fan wars hub |
| Primary actions | Join wars; history query |
| API endpoints | Fan wars APIs |
| Auth guard | Token optional |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-128: `/world/clubs/:clubId`

| Field | Value |
|---|---|
| Widget / screen | `GtexPublicClubProfileScreenV2` |
| Source | `lib/screens/clubs/gtex_public_club_profile_screen_v2.dart` |
| Intended role | Public club profile |
| Primary actions | View club |
| API endpoints | Club profile APIs |
| Auth guard | Optional |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-129: `/world/competitions/:competitionId`

| Field | Value |
|---|---|
| Widget / screen | `FootballWorldSimulationScreen` |
| Source | `lib/features/football_world_simulation/` |
| Intended role | World competition context |
| Primary actions | View context |
| API endpoints | World APIs |
| Auth guard | Optional |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-130: `/national-team/entries/:entryId`

| Field | Value |
|---|---|
| Widget / screen | `GteFeatureRouteContent` |
| Source | `gte_feature_route_builders.dart` |
| Intended role | National team entry detail |
| Primary actions | View entry |
| API endpoints | GET /api/national-team-engine/entries/:id |
| Auth guard | Public feature |
| TODO / stub / redirect / notes | Fixture fallbacks exist in builder |
| Status hint | **PARTIAL** |

### FL-131: `/national-team/history`

| Field | Value |
|---|---|
| Widget / screen | `GteFeatureRouteContent` |
| Source | `gte_feature_route_builders.dart` |
| Intended role | National team history |
| Primary actions | View history |
| API endpoints | GET /api/national-team-engine/me/history |
| Auth guard | Public feature (may need auth for me) |
| TODO / stub / redirect / notes | Fixture fallbacks |
| Status hint | **PARTIAL** |

### FL-132: `/broadcast/live`

| Field | Value |
|---|---|
| Widget / screen | `GteLiveMatchHubRouteScreen` |
| Source | `lib/features/match/gte_live_match_hub_route_screen.dart` |
| Intended role | Broadcast desk (canonical registry mapping) |
| Primary actions | Open matches hub |
| API endpoints | Match hub APIs |
| Auth guard | Optional |
| TODO / stub / redirect / notes | _buildBroadcastDeskScreen exists with fixture data but is UNUSED by registry |
| Status hint | **DUPLICATED** |

### FL-133: `/gtex/jackpot`

| Field | Value |
|---|---|
| Widget / screen | `GtexJackpotRouteScreen` |
| Source | `lib/features/jackpot/presentation/gtex_jackpot_route_screen.dart` |
| Intended role | Jackpot desk |
| Primary actions | View pot; claim |
| API endpoints | Jackpot APIs |
| Auth guard | Login CTA |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-134: `/gtex/jackpot/win`

| Field | Value |
|---|---|
| Widget / screen | `GtexJackpotWinNotificationScreenV2` |
| Source | `lib/screens/jackpot/gtex_jackpot_win_notification_screen_v2.dart` |
| Intended role | Jackpot win celebration |
| Primary actions | Dismiss |
| API endpoints | None (query params amount/round/club) |
| Auth guard | Public |
| TODO / stub / redirect / notes | Hardcoded defaults if query empty |
| Status hint | **PARTIAL** |

### FL-135: `/clubs/:clubId/assistant`

| Field | Value |
|---|---|
| Widget / screen | `GteFeatureRouteContent (AI)` |
| Source | `gte_feature_route_builders.dart` |
| Intended role | Club AI assistant |
| Primary actions | Run autopilot/live-decision/reward-preview |
| API endpoints | /api/ai-manager/profiles/:clubId, /api/ai-manager/autopilot/run, live-decision, economy/reward-preview |
| Auth guard | Likely auth |
| TODO / stub / redirect / notes | Hardcoded AI squad seed payloads in builder |
| Status hint | **PARTIAL** |

### FL-136: `/creator-stadium/clubs/:clubId`

| Field | Value |
|---|---|
| Widget / screen | `Creator stadium club screen` |
| Source | `lib/features/creator_stadium_monetization/` |
| Intended role | Creator stadium club monetization |
| Primary actions | Manage stadium |
| API endpoints | Stadium APIs |
| Auth guard | Auth likely |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-137: `/creator-stadium/matches/:matchId`

| Field | Value |
|---|---|
| Widget / screen | `Creator stadium match` |
| Source | `same` |
| Intended role | Match stadium monetization |
| Primary actions | View match stadium |
| API endpoints | Stadium APIs |
| Auth guard | Auth likely |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-138: `/admin/creator-stadium/control`

| Field | Value |
|---|---|
| Widget / screen | `Creator stadium admin` |
| Source | `same` |
| Intended role | Admin stadium control |
| Primary actions | Admin controls |
| API endpoints | Admin APIs |
| Auth guard | AUTH + ADMIN |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-139: `/admin/creator-league/financial-report`

| Field | Value |
|---|---|
| Widget / screen | `Creator league financial report` |
| Source | `lib/features/creator_league_admin/` |
| Intended role | Season financial report |
| Primary actions | Filter seasonId |
| API endpoints | Creator league admin APIs |
| Auth guard | AUTH + ADMIN |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-140: `/admin/creator-league/settlements`

| Field | Value |
|---|---|
| Widget / screen | `Creator league settlements` |
| Source | `same` |
| Intended role | Settlements desk |
| Primary actions | Settle season |
| API endpoints | Settlements APIs |
| Auth guard | AUTH + ADMIN |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-141: `/admin/gift-stabilizer`

| Field | Value |
|---|---|
| Widget / screen | `GiftEconomyAdminScreen` |
| Source | `lib/features/gift_economy_admin/presentation/gift_economy_admin_screen.dart` |
| Intended role | Gift economy stabilizer |
| Primary actions | Tune gift economy |
| API endpoints | Gift admin APIs |
| Auth guard | AUTH + ADMIN |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-142: `/clubs/:clubId/identity/jerseys`

| Field | Value |
|---|---|
| Widget / screen | `ClubIdentityScreen` |
| Source | `lib/features/club_identity/jerseys/presentation/club_identity_screen.dart` |
| Intended role | Jersey / identity designer |
| Primary actions | Edit kits |
| API endpoints | ClubIdentityRepository |
| Auth guard | Optional |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-143: `/clubs/:clubId/identity/reputation`

| Field | Value |
|---|---|
| Widget / screen | `ClubReputationOverviewScreen` |
| Source | `lib/features/club_identity/reputation/presentation/reputation_screen.dart` |
| Intended role | Reputation overview |
| Primary actions | View prestige |
| API endpoints | ReputationRepository |
| Auth guard | Optional |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-144: `/clubs/:clubId/identity/reputation/history`

| Field | Value |
|---|---|
| Widget / screen | `ReputationHistoryScreen` |
| Source | `lib/features/club_identity/reputation/presentation/reputation_history_screen.dart` |
| Intended role | Reputation history |
| Primary actions | Browse history |
| API endpoints | ReputationController.load |
| Auth guard | Optional |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-145: `/clubs/:clubId/identity/reputation/leaderboard`

| Field | Value |
|---|---|
| Widget / screen | `PrestigeLeaderboardScreen` |
| Source | `lib/features/club_identity/reputation/presentation/prestige_leaderboard_screen.dart` |
| Intended role | Prestige leaderboard |
| Primary actions | Browse ranks |
| API endpoints | Reputation |
| Auth guard | Optional |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-146: `/clubs/:clubId/identity/trophies`

| Field | Value |
|---|---|
| Widget / screen | `TrophyCabinetScreen` |
| Source | `lib/features/club_identity/trophies/presentation/trophy_cabinet_screen.dart` |
| Intended role | Trophy cabinet |
| Primary actions | Filter scope |
| API endpoints | TrophyCabinetRepository |
| Auth guard | Optional; guard empty cabinet |
| TODO / stub / redirect / notes | Guard reasons emptyTrophyCabinet |
| Status hint | **PARTIAL** |

### FL-147: `/clubs/:clubId/identity/trophies/timeline`

| Field | Value |
|---|---|
| Widget / screen | `HonorsTimelineScreen` |
| Source | `lib/features/club_identity/trophies/presentation/honors_timeline_screen.dart` |
| Intended role | Honors timeline |
| Primary actions | Filter scope |
| API endpoints | TrophyCabinetRepository |
| Auth guard | Optional |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-148: `/clubs/:clubId/identity/trophies/leaderboard`

| Field | Value |
|---|---|
| Widget / screen | `TrophyLeaderboardScreen` |
| Source | `lib/features/club_identity/trophies/presentation/trophy_leaderboard_screen.dart` |
| Intended role | Trophy leaderboard |
| Primary actions | Filter |
| API endpoints | TrophyCabinetRepository |
| Auth guard | Optional |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-149: `/clubs/:clubId/identity/dynasty`

| Field | Value |
|---|---|
| Widget / screen | `DynastyScreen` |
| Source | `lib/features/club_identity/dynasty/presentation/dynasty_screen.dart` |
| Intended role | Dynasty overview |
| Primary actions | Open history/leaderboard |
| API endpoints | DynastyRepository |
| Auth guard | Optional; guard noDynastyYet |
| TODO / stub / redirect / notes | — |
| Status hint | **PARTIAL** |

### FL-150: `/clubs/:clubId/identity/dynasty/history`

| Field | Value |
|---|---|
| Widget / screen | `EraHistoryScreen` |
| Source | `lib/features/club_identity/dynasty/presentation/era_history_screen.dart` |
| Intended role | Dynasty era history |
| Primary actions | Browse eras |
| API endpoints | DynastyRepository |
| Auth guard | Optional |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-151: `/clubs/:clubId/identity/dynasty/leaderboard`

| Field | Value |
|---|---|
| Widget / screen | `DynastyLeaderboardScreen` |
| Source | `lib/features/club_identity/dynasty/presentation/dynasty_leaderboard_screen.dart` |
| Intended role | Dynasty leaderboard |
| Primary actions | Browse |
| API endpoints | DynastyRepository |
| Auth guard | Optional |
| TODO / stub / redirect / notes | — |
| Status hint | **NOT VERIFIED** |

### FL-152: `/clubs/:clubId/identity/replays`

| Field | Value |
|---|---|
| Widget / screen | `GteReplayArchiveRouteScreen` |
| Source | `lib/features/match/replay_archive_route_screen.dart` |
| Intended role | Club replay archive |
| Primary actions | Open replay surfaces |
| API endpoints | Replay APIs |
| Auth guard | Optional |
| TODO / stub / redirect / notes | surface query param |
| Status hint | **NOT VERIFIED** |

### FL-153: `/competitions (catalog name competitions.discovery)`

| Field | Value |
|---|---|
| Widget / screen | `(redirect to shell play; catalog excluded from feature GoRoutes)` |
| Source | `gte_route_data.dart + app_router shellOwnedPaths` |
| Intended role | Catalog path owned by shell redirect |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | shellOwnedPaths excludes from _buildFeatureRoutes |
| Status hint | **DUPLICATED** |

### FL-154: `/player-cards (catalog browse)`

| Field | Value |
|---|---|
| Widget / screen | `(redirect → /app/market)` |
| Source | `same` |
| Intended role | Catalog browse excluded; redirects to market |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | PlayerCardMarketplaceScreen reachable via inventory route only |
| Status hint | **DUPLICATED** |

### FL-155: `/streamer-tournaments (catalog list)`

| Field | Value |
|---|---|
| Widget / screen | `(redirect → /app/play)` |
| Source | `same` |
| Intended role | List excluded; detail still registered |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | StreamerTournamentEngineRouteScreen lightly referenced/orphan |
| Status hint | **PARTIAL** |

### FL-156: `/world/regens (catalog regenUniverse)`

| Field | Value |
|---|---|
| Widget / screen | `(redirect → /app/regens)` |
| Source | `same` |
| Intended role | Shell owns regen lane |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | — |
| Status hint | **DUPLICATED** |

### FL-157: `(unregistered)`

| Field | Value |
|---|---|
| Widget / screen | `GteRouteIntegrityScreen.blocked` |
| Source | `lib/widgets/gte_route_integrity_screen.dart` |
| Intended role | Router error / blocked gate UI |
| Primary actions | Back / retry |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | errorBuilder + Launch Control blocked panels |
| Status hint | **NOT VERIFIED** |

### FL-158: `(embedded admin)`

| Field | Value |
|---|---|
| Widget / screen | `ClubOpsAdminScreen / ClubAnalyticsScreen / ClubFinanceAnalyticsScreen / ClubSponsorshipAnalyticsScreen / ClubBrandingModerationScreen / AcademyAnalyticsScreen / ScoutingAnalyticsScreen` |
| Source | `lib/screens/admin/*.dart` |
| Intended role | Admin club ops subpanels |
| Primary actions | Various analytics actions |
| API endpoints | /api/v2/admin/clubs/* |
| Auth guard | Admin via command center |
| TODO / stub / redirect / notes | Lightly referenced; likely embedded not routed |
| Status hint | **PARTIAL** |

### FL-159: `(club ops host)`

| Field | Value |
|---|---|
| Widget / screen | `ClubOpsScreenHost + academy/scouting/finance/sponsorship/jersey screens` |
| Source | `lib/screens/clubs/*` |
| Intended role | Club operations suite |
| Primary actions | Budget, cashflow, scouting, youth, jerseys |
| API endpoints | Club ops APIs |
| Auth guard | Club owner context |
| TODO / stub / redirect / notes | Many screens ≤3 refs — may be dead or only host-pushed |
| Status hint | **PARTIAL** |

### FL-160: `(legacy)`

| Field | Value |
|---|---|
| Widget / screen | `GteDashboardScreen / GteMarketScreen / GteTransferRoomScreen` |
| Source | `lib/legacy/*` |
| Intended role | Legacy exchange screens |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | Likely dead legacy |
| Status hint | **NOT IMPLEMENTED** |

### FL-161: `(orphan match)`

| Field | Value |
|---|---|
| Widget / screen | `Match3dRouteScreen / GtexMatch3dScreen / MatchBroadcastScreen / MatchSimulateRouteScreen / MatchSpectateScreen / MatchNative3dBlockedScreen` |
| Source | `lib/features/match/*; lib/screens/match/*` |
| Intended role | Match 3D/sim/spectate implementations |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | Routes redirect away; screens lightly wired |
| Status hint | **NOT IMPLEMENTED** |

### FL-162: `(orphan auth v2)`

| Field | Value |
|---|---|
| Widget / screen | `GteLoginScreenV2 / GteSignupScreen / GteSignupScreenV2 / GtexCreatorSignupScreenV2` |
| Source | `lib/screens/*` |
| Intended role | Alternate auth UIs |
| Primary actions | — |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | Not registered in GoRouter |
| Status hint | **DUPLICATED** |

### FL-163: `(onboarding)`

| Field | Value |
|---|---|
| Widget / screen | `GteRegionSelectionScreen / GtexNewUserOnboardingScreenV2` |
| Source | `lib/screens/onboarding/*` |
| Intended role | Onboarding flows |
| Primary actions | Select region |
| API endpoints | — |
| Auth guard | — |
| TODO / stub / redirect / notes | Lightly referenced; may be push-only |
| Status hint | **PARTIAL** |

### FL-164: `(referrals push)`

| Field | Value |
|---|---|
| Widget / screen | `GtexReferralHubScreenV2 / ReferralHubScreen / ReferralInvitesScreen / ReferralRewardsScreen / ShareCodeScreen` |
| Source | `lib/screens/referrals/*` |
| Intended role | Referral surfaces |
| Primary actions | Share codes, invites |
| API endpoints | ReferralApi |
| Auth guard | Auth |
| TODO / stub / redirect / notes | Likely via Studio hub / push |
| Status hint | **PARTIAL** |

### FL-165: `(owner console)`

| Field | Value |
|---|---|
| Widget / screen | `OwnerConsoleScreen` |
| Source | `lib/features/owner_console/presentation/owner_console_screen.dart` |
| Intended role | Owner console (non-public) |
| Primary actions | Manage club showroom |
| API endpoints | OwnerConsoleApi |
| Auth guard | Auth |
| TODO / stub / redirect / notes | Showroom public is FL-007 |
| Status hint | **NOT VERIFIED** |

### FL-166: `(agent)`

| Field | Value |
|---|---|
| Widget / screen | `AgentConversationsScreen / AgentConversationScreen` |
| Source | `lib/screens/agent_*.dart` |
| Intended role | Agent chat |
| Primary actions | Send messages |
| API endpoints | Agent APIs |
| Auth guard | Auth |
| TODO / stub / redirect / notes | May be unrouted |
| Status hint | **NOT VERIFIED** |

### FL-167: `(system gallery)`

| Field | Value |
|---|---|
| Widget / screen | `GtexSystemStatesGalleryV2` |
| Source | `lib/screens/system/gtex_system_states_gallery_v2.dart` |
| Intended role | System state gallery |
| Primary actions | Browse states |
| API endpoints | None |
| Auth guard | — |
| TODO / stub / redirect / notes | Design/dev surface |
| Status hint | **PARTIAL** |

---

## 20 most critical findings

1. **Dual routing systems**: GoRouter (`app_router.dart`) + feature catalog (`GteAppRouteCatalog`) + shell lanes (`/app/:section`) — easy to drift; Phase 4H tests only cover `appRouteInventory` ∩ registered paths.
2. **`/wallet` → `/app/capital`**: canonical capital desk is shell wallet; many legacy aliases (`/payments`, `/capital`, `/orders`) funnel here.
3. **3D / Unity match routes are NOT IMPLEMENTED live**: `/matches/3d/:matchKey`, `/matches/native-3d` redirect to 2D; dedicated 3D screens are orphaned.
4. **`/profile/admin` was a dead Home button** (now redirects to `/admin`); inventory↔router drift historically shipped broken quick actions.
5. **Transfer listing deep link NOT IMPLEMENTED**: `/market/transfers/:listingId` degrades to transfer-center calendar — no listing detail screen.
6. **National team plural deep links NOT IMPLEMENTED**: `/national-teams/:competitionId` lands on `/national-team` rental screen only.
7. **Broadcast desk builder is dead code**: `_buildBroadcastDeskScreen` (with fixture/hardcoded match payloads) is unused; registry maps `BroadcastDeskRouteData` → `GteLiveMatchHubRouteScreen`.
8. **`/national-team` catalog builder vs rental screen conflict**: shellOwned excludes catalog; live GoRoute mounts `GtexNationalTeamRentalScreenV2`, while `_buildNationalTeamCompetitionsScreen` still exists with fixture fallbacks.
9. **Launch Control gates all `/app/*` shell routes** asynchronously; failures show integrity locked UI — can look BROKEN when flags/API unavailable.
10. **Admin surface is large and capability-sensitive**: command center + 5 top-level admin GoRoutes + feature-catalog admin paths; non-admin gets blocked panel.
11. **Many club ops / academy / scouting screens appear lightly wired** (≤3 refs) — likely push-only or dead relative to GoRouter.
12. **Auth V2 screens (`GteLoginScreenV2`, signup V2) are not on GoRouter** — duplicated UI risk.
13. **Jackpot win screen is query-param driven with hardcoded defaults** (`amount`/`round`/`club`) — PARTIAL celebration UI.
14. **Club AI assistant uses hardcoded squad seed payloads** in route builder posts to `/api/ai-manager/*` — PARTIAL / mock-ish request bodies.
15. **World Super Cup route can silently fall back** to competitions discovery when inactive — may surprise deep-link users.
16. **`/player-cards` redirects to market shell**, while card detail/inventory remain feature routes — browse UX is split/DUPLICATED.
17. **Match simulate/spectate/broadcast screen widgets exist but routes redirect away** — NOT IMPLEMENTED as navigable surfaces.
18. **Design-lab routes are deliberately unlinked fixture surfaces** — must not be treated as product.
19. **Hub (Studio) requires authentication** with an in-lane gate; other primary destinations remain guest-readable to varying degrees.
20. **`appRouteInventory` vs live shell labels diverge**: inventory still publishes `/home`, `/matches`, `/market` as primary nav while product chrome is `/app/home`, `/app/play`, `/app/market`.

---

## Source index (key files)

- `frontend/lib/router/app_router.dart`
- `frontend/lib/router/gtex_auth_routes.dart`
- `frontend/lib/features/app_routes/gte_route_data.dart`
- `frontend/lib/features/app_routes/gte_app_route_registry.dart`
- `frontend/lib/features/app_routes/gte_feature_route_builders.dart`
- `frontend/lib/features/navigation/routing/gte_navigation_route.dart`
- `frontend/lib/features/navigation/presentation/gte_navigation_shell_screen.dart`
- `frontend/lib/navigation/app_destinations.dart`
- `frontend/lib/features/navigation_guards/gte_navigation_guards.dart`
- `frontend/lib/features/launch_control_redesign/launch_control_feature_gate.dart`
- `frontend/test/ux_refinement/phase4h_route_inventory_test.dart`
