# GTEX P7-FE Club + Player Identity + Progression Audit Report

**Repository:** `wandemcphill/Global-Talent-Exchange`
**Branch:** `main`
**Audit Context:** Session P7-FE — Club / Player Identity / Progression Vertical Verification & Implementation Brief
**Author:** Jules (Software Engineer)
**Date:** March 2025

---

## Executive Summary & Scope

This audit provides a precise, verified analysis of the current state of the **Club**, **Player**, and **Progression** verticals across the GTEX codebase (`main` branch).

### Scope Boundaries
- **In-Scope Verticals:**
  - **Club:** Club HQ, Club Identity, Club Profile, Club Readiness, Lineup/Tactics, Academy, Youth Prospects, Club Progression, Club Rankings, Club Honours/Trophies, Jersey/Badge design, Sponsoring, Finance.
  - **Player:** Player Detail, Player Cards, Discovery Identity, Attributes, Ownership/Holdings, Progression/Career, Prospects/Regens.
  - **Progression:** Rankings, Reputation/Prestige, Rewards, Achievements, Trophies, Progression Indicators, Fan/Club Status.
- **Out-of-Scope:**
  - Unity 3D match rendering pipeline modifications (`Gtex_Test_Migration/`).
  - Ingestion batch processing scripts and external API fetchers.
  - Production code edits (this audit serves as an authoritative implementation brief).

---

## 1. Verified Surface Inventory

### 1.1 Club Vertical Surfaces

| Surface Name | Route / Path | Primary Screen File | Active Provider / Controller | Backing Endpoints & Models | Status & Wiring |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Club HQ (Owner Dashboard)** | Top-level tab: `GtePrimaryDestination.club` (`/app`) | `GtexClubOwnerDashboardV2` in `gtex_club_owner_dashboard_v2.dart` | `GtexClubWorkspaceController`, `GteExchangeController` | GET `/api/clubs/{club_id}/v2-snapshot`<br/>Models: `ClubV2SnapshotResponse`, `ClubProfile` | **Live & Primary**. Replaces legacy `ClubOpsScreenHost`. |
| **Public Club Profile** | `/app/world` or feature route `GtexPublicClubProfileV2` | `GtexPublicClubProfileV2` in `gtex_public_club_profile_v2.dart` | `GtexClubWorkspaceController` | GET `/api/clubs/{club_id}`, GET `/api/clubs/{club_id}/trophy-cabinet/summary`<br/>Models: `ClubProfileResponse` | **Live**. Hydrated public view of any club. |
| **Club Identity & Jersey Editor** | `ClubIdentityJerseysRouteData` (`/club/identity`) | `ClubIdentityScreen` in `club_identity_screen.dart` | `ClubIdentityController` | GET/POST/PATCH `/{club_id}/branding`, GET/POST/PATCH `/{club_id}/jerseys`<br/>Models: `ClubIdentityDto`, `JerseySetDto` | **Live**. Full kit & badge designer with clash detection. |
| **Lineup & Tactics** | Tab inside `GtexClubOwnerDashboardV2` / `/lineup` | Built-in workspace subview / `GtexTacticsPanel` | `GtexClubWorkspaceController` / `MatchEngine` | GET/POST `/lineups/{club_id}`, GET `/squad-tiers/{club_id}`<br/>Models: `LineupResponse`, `SquadTier` | **Live**. Interactive pitch drag-and-drop for first_team & reserve. |
| **Academy & Youth Pipeline** | Tab inside `GtexClubOwnerDashboardV2` / `AcademyOverviewScreen` | `AcademyOverviewScreen` in `academy_overview_screen.dart` | `AcademyService` / API direct | GET/POST `/academy`, GET `/scouting/prospects`<br/>Models: `AcademyProgram`, `YouthProspect` | **Fragmented**. Legacy `AcademyOverviewScreen` exists alongside V2 dashboard tabs. |
| **Club Dynasty Overview** | `ClubDynastyOverviewRouteData` (`/dynasty`) | `DynastyScreen` in `dynasty_screen.dart` | `DynastyController` | GET `/dynasty`, GET `/dynasty/leaderboard`<br/>Models: `DynastyProfileDto` | **Live**. Tracks streaks, eras, and dynasty milestones. |

### 1.2 Player Vertical Surfaces

| Surface Name | Route / Path | Primary Screen File | Active Provider / Controller | Backing Endpoints & Models | Status & Wiring |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **FM Player Profile** | `/players/:playerId/profile` (Canonical) | `GtexFmPlayerProfileScreen` in `gtex_fm_player_profile_screen.dart` | `GtexFmPlayerProfileController` | GET `/{player_id}/summary`, GET `/api/players/{player_id}/career`, GET `/api/players/{player_id}/overview`<br/>Models: `PlayerSummary`, `PlayerCareerSummary` | **Canonical Player Detail**. Rich football radar, contracts, market pricing. |
| **Player Cards Gallery** | `PlayerCardsBrowseRouteData` (`/player-cards`) | `PlayerCardMarketplaceBrowseScreen` | `PlayerCardMarketplaceController` | GET `/player-cards/players`, GET `/player-cards/collections`<br/>Models: `PlayerCardItem` | **Live**. Collectible cards separate from share trading. |
| **Regen Universe Hub** | `RegenUniverseRouteData` (`/regens`, `/world/regens`) | `RegensScreenV2` in `regens_screen_v2.dart` | `RegensController` | GET `/regen-universe/rankings`, GET `/regen-universe/national-regens`<br/>Models: `RegenProfileResponse` | **Live**. AI-generated players, birth years, and Create-a-Son flow. |
| **Scouting Prospects** | `ScoutingProspectsScreen` (Navigated from Club HQ) | `ScoutingProspectsScreen` in `scouting_prospects_screen.dart` | API direct | GET `/scouting/prospects/{prospect_id}`<br/>Models: `YouthProspectReport` | **Secondary Screen**. Accessible through Club HQ scouting action. |

### 1.3 Progression Vertical Surfaces

| Surface Name | Route / Path | Primary Screen File | Active Provider / Controller | Backing Endpoints & Models | Status & Wiring |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Reputation & Prestige** | `ClubReputationOverviewRouteData` | `ClubReputationOverviewScreen` | `ReputationController` | GET `/clubs/{club_id}/reputation`, GET `/clubs/{club_id}/reputation/history`<br/>Models: `ClubReputationSnapshot` | **Live**. Prestige points, rank tiers (Local Legend -> Global Powerhouse). |
| **Trophy Cabinet & Honors** | `ClubTrophyCabinetRouteData` | `TrophyCabinetScreen` | `TrophyCabinetRepository` | GET `/clubs/{club_id}/trophy-cabinet`<br/>Models: `TrophyCabinetDto` | **Live**. Displays major honors, cups, dynamic 3D trophy shelf. |
| **Trophy Leaderboard** | `ClubTrophyLeaderboardRouteData` | `TrophyLeaderboardScreen` | `TrophyCabinetRepository` | GET `/trophies/leaderboard`<br/>Models: `TrophyLeaderboardEntryDto` | **Live**. Global ranking by silverware volume and trophy weight. |
| **Prestige Leaderboard** | `ClubReputationLeaderboardRouteData` | `PrestigeLeaderboardScreen` | `ReputationController` | GET `/reputation/leaderboard`<br/>Models: `PrestigeLeaderboardEntry` | **Live**. Club ranking by prestige tier. |
| **World Awards & Ballon d'Or** | `WorldAwardsRouteData` (`/world/awards`) | `GtexAwardsScreenV2` | API direct | GET `/awards`, GET `/awards/ceremony`<br/>Models: `AwardWinnerDto` | **Live**. Annual player and manager award recognition. |

---

## 2. Backend / Frontend Parity & Integration Gaps

### 2.1 Backend Capability vs Frontend Exposure Analysis

1. **Staff Roles & Personal Managers (Phase 6F Backend Ready)**
   - *Backend Capability:* `PersonalManager` ORM model (`personal_managers` table) and `StaffRoleService` permit appointing permanent personal managers and coaching staff.
   - *Frontend Gap:* No staff management tab or personal manager card exists inside `GtexClubOwnerDashboardV2`.

2. **Academy Facility Upgrades & Economy (Phase 6E Backend Ready)**
   - *Backend Capability:* `AcademyFacilityEconomyService` supports upgrading facilities (`training`, `academy`, `medical`, `branding`, `youth_recruitment`) consuming Fan Coin (`CREDIT`).
   - *Frontend Gap:* The V2 Club Owner Dashboard shows facility levels as static metrics without upgrade triggers or progression progress bars.

3. **Private Transfer Negotiations & Contract Offers**
   - *Backend Capability:* `TransferMarketService.submit_contract_offer` and `PlayerLifecycleService.accept_bid` allow direct contract negotiations.
   - *Frontend Gap:* The `GtexFmPlayerProfileScreen` trade action bar exposes "Buy Shares" and "Place Share Order", but contract bid actions for transfer affiliation are tucked inside secondary modal sheets.

4. **Club Growth & Prospect Promotion**
   - *Backend Capability:* `ClubGrowthService.promote_prospect` creates an active contract and places player into `reserve` squad tier via `SquadTierService.ensure_membership`.
   - *Frontend Gap:* Prospect cards in scouting screens display "Promote" buttons that call legacy endpoints instead of `ClubGrowthService`.

### 2.2 Orphan & Disconnected Endpoints

- **`GET /api/players/{player_id}/injuries` & `POST /api/players/{player_id}/injuries/{injury_id}/recover`**: Backend injury recovery engine is fully implemented, but Flutter player profile UI displays static availability badges without injury duration tickers or medical recovery actions.
- **`GET /dynasty/leaderboard`**: `DynastyLeaderboardScreen` is registered in `GteAppRouteRegistry`, but lacks direct navigation links from the primary Home command grid.

---

## 3. Lifecycle, Permissions & State Matrix

### 3.1 Session & Role Handling Matrix

| Surface / Action | Guest (Unauthenticated) | Standard Signed-In User | Club Owner | Admin Role |
| :--- | :--- | :--- | :--- | :--- |
| **Club HQ (`/app` -> Club tab)** | Displays `_GtexCommandHomeEntry` with CTA to Sign In / Create Club. | Shows Create Club CTA if no club owned. | Opens `GtexClubOwnerDashboardV2` for owned club. | Opens `GtexClubOwnerDashboardV2` with Admin override controls. |
| **Player Profile (`/players/:id/profile`)** | Full read-only access to attributes & radar. CTAs trigger Login sheet. | Can trade player shares & view contract details. | Same as User + highlight transfer bid option if seller. | Full access + Admin force-edit capabilities. |
| **Lineup & Squad Management** | Read-only squad viewing in public club profile. | View-only unless managing own squad. | Full interactive pitch drag-and-drop & tactic edits. | Full editing capabilities. |
| **Kit & Jersey Designer** | Preview mode with mock saving disabled. | Prompts to create/claim club. | Full edit, save, and publish kit changes to backend. | Moderation & direct edit rights. |
| **Regen Creation (Build-a-Son)** | View public regens. CTA prompts Login. | Opens Build-a-Son modal (requires wallet coins). | Opens Build-a-Son modal (auto-assigns son to club reserve). | Free test minting enabled via admin command panel. |

### 3.2 State Handling Audit (Empty, Loading, Error)

1. **Empty States:**
   - **No Club Owned:** Properly rendered via `_GtexCommandHomeEntry` with clean call-to-action buttons.
   - **Trophy Cabinet empty:** Handled cleanly with `GtexEmptyState` showing "No Trophies Won Yet".
   - **Lineup Unassigned:** Pitch renders empty slot markers with "Tap to assign player" guidance.
2. **Loading States:**
   - Skeleton loaders (`GtexSkeleton`, `ReputationLoadingSkeleton`) are used effectively across V2 screens.
3. **Error States:**
   - Network or server errors fall back to `GteStatePanel` or `GtexErrorBanner` with clear retry callbacks (`onAction`).

---

## 4. Responsive Layout & Viewport Analysis

Audit tested across two target viewports: **Desktop (1440 × 900)** and **Mobile (390 × 844)**.

### 4.1 Layout Behavior Summary

| Viewport | Component / Screen | Observed Behavior | Finding / Issue |
| :--- | :--- | :--- | :--- |
| **Desktop (1440x900)** | `GtexClubOwnerDashboardV2` | Multi-column grid layout expands cleanly across workspace. | High-density information display; sidebar navigation scales well. |
| **Desktop (1440x900)** | `GtexFmPlayerProfileScreen` | Master-detail split view with radar on left and contract/market on right. | Ideal desktop presentation. Local `BoxConstraints` preserved. |
| **Mobile (390x844)** | `GtexClubOwnerDashboardV2` | Collapses into single-column vertical scroll. | Tactical pitch widget requires horizontal scrolling if grid is narrow. |
| **Mobile (390x844)** | `ClubIdentityScreen` (Jerseys) | Single column vertical stack for color pickers & badge selector. | Color picker rows overflow horizontally if non-scrollable. Needs flex wraps. |
| **Mobile (390x844)** | `TrophyCabinetScreen` | Grid shifts from 4-columns to 2-columns. | Dynamic shelf presentation scales correctly. |

---

## 5. Design-System Opportunities & Proposed Reusable Components

### 5.1 Identified Reusable Patterns

To unify Club, Player, and Progression surfaces into a single cohesive system, four new atomic widgets should be standardized in `frontend/lib/ui_gtex/`:

1. **`GtexIdentityHeader`**: A unified club/player banner displaying badge/avatar, country flag, prestige tier badge, and quick action bar.
2. **`GtexProgressionBar`**: A standardized progress meter for reputation, academy level, and dynasty streaks with animated glowing status indicators.
3. **`GtexOwnershipIndicatorTile`**: A compact widget rendering holding position (`quantity × share_price`), contract duration, and squad role.
4. **`GtexSilverwareShelf`**: An inline horizontal ribbon rendering major trophies with metal shine shaders and trophy count badges.

---

## 6. Implementation Dependency Graph

```
[Phase 1: Component Standardization]
   ├── GtexIdentityHeader
   ├── GtexProgressionBar
   ├── GtexOwnershipIndicatorTile
   └── GtexSilverwareShelf
           │
           ▼
[Phase 2: Core Vertical Alignment]
   ├── Alignment A: Club HQ V2 Refinement (Embed Staff & Facility Upgrades)
   ├── Alignment B: FM Player Profile Contract & Transfer Integration
   └── Alignment C: Progression Hub (Unified Dynasty + Trophies + Reputation)
           │
           ▼
[Phase 3: Cross-Vertical Wire-Up]
   ├── Lineup <-> Player Detail Navigation
   ├── Academy Prospect <-> Squad Tier Assignment
   └── Club Identity <-> Matchday Broadcast Overlay
```

---

## 7. Product Directions Analysis

Three coherent product directions were explored for the implementation phase:

### Direction A: CLUB UNIVERSE
*Focus:* Club identity, legacy, academy, facilities, and manager progression first.

- **Strengths:** High retention for tactical/managerial users; strong narrative connection to club growth and dynasty building.
- **Trade-offs:** De-emphasizes individual player share trading in favor of team-level management.
- **Dependencies:** Requires embedding Phase 6E facility upgrades and Phase 6F staff/manager appointments directly into the main Club HQ workspace.

### Direction B: PLAYER UNIVERSE
*Focus:* Players, collectible cards, regens, scouting, attributes, and share ownership first.

- **Strengths:** Drives high transaction volume in player card and share markets; appeals to trading-focused users.
- **Trade-offs:** Can feel disconnected from overall football club identity if club progress isn't tied to player performances.
- **Dependencies:** Requires deep integration of `GtexFmPlayerProfileScreen` with scouting reports, regen lineage, and direct contract bidding.

### Direction C: FOOTBALL IDENTITY
*Focus:* Club + Players + Progression presented as one fully connected, interdependent identity system.

- **Strengths:** Maximizes user immersion by linking individual player performance directly to club reputation, dynasty milestones, and financial rewards.
- **Trade-offs:** Higher UI surface complexity; requires meticulous state synchronization between market, squad, and club services.
- **Dependencies:** Leverages `GtexClubOwnerDashboardV2` as the central hub, referencing `GtexFmPlayerProfileScreen` for player drill-downs and `DynastyScreen` for progression tracking.

---

## 8. Exact Codex Implementation Prompt

The following exact prompt can be copy-pasted into future implementation sessions:

```markdown
### CODEX IMPLEMENTATION BRIEF: GTEX Club + Player Identity + Progression Vertical Unification

**Objective:**
Implement Phase 7 frontend unification for Club, Player, and Progression verticals in GTEX, connecting Club HQ, FM Player Profile, and Progression indicators into a seamless, high-fidelity experience without introducing fake capabilities or breaking backend contracts.

**Key Requirements:**
1. **Club HQ V2 Enhancements (`GtexClubOwnerDashboardV2`):**
   - Integrate Staff & Personal Manager management section leveraging `backend/app/services/player_agency_service.py` / `personal_managers`.
   - Add interactive Facility Upgrades card utilizing `AcademyFacilityEconomyService` (`training`, `academy`, `medical`, `branding`, `youth_recruitment`) with Fan Coin payment triggers.
   - Connect prospect promotion directly to `ClubGrowthService.promote_prospect`.

2. **Player Identity & Ownership Integration (`GtexFmPlayerProfileScreen`):**
   - Standardize Player Detail drill-downs from squad lineup tiles, academy lists, and market search to `/players/:playerId/profile`.
   - Embed contract renewal and transfer bidding actions directly into the profile action bar.
   - Display active injury recovery status and medical timelines.

3. **Progression System Unification:**
   - Create unified `GtexSilverwareShelf` and `GtexProgressionBar` components in `frontend/lib/ui_gtex/`.
   - Wire Dynasty streaks, Reputation tiers, and Trophy cabinet summaries into both Public Club Profiles and Owner Dashboards.

4. **Quality & Verifications:**
   - Maintain 100% responsive parity across Desktop (1440x900) and Mobile (390x844).
   - Ensure all network state transitions (loading, error, empty) use canonical GTEX UI system components (`GtexSkeleton`, `GtexEmptyState`, `GteStatePanel`).
   - All tests must pass: run `cd frontend && flutter test` (excluding golden tests if needed).
```
