import 'package:flutter/material.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/app_routes/gte_navigation_helpers.dart';
import 'package:gte_frontend/features/app_routes/gte_route_data.dart';
import 'package:gte_frontend/features/club_navigation/club_navigation.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/features/shell/shell.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

class HomeDashboardScreen extends StatelessWidget {
  const HomeDashboardScreen({
    super.key,
    required this.exchangeController,
    required this.apiBaseUrl,
    required this.backendMode,
    this.onOpenLogin,
    this.isCheckingCreatorAccess = false,
    this.canHostCompetitions = false,
    this.clubId,
    this.clubName,
    this.onOpenClubTab,
    this.onOpenCompetitionsTab,
    this.onOpenMarketTab,
    this.onOpenHubTab,
    this.onOpenWalletTab,
    this.onOpenClubSubtab,
    this.onOpenCreatorAccessRequest,
    this.navigationDependencies,
  });

  final GteExchangeController exchangeController;
  final String apiBaseUrl;
  final GteBackendMode backendMode;
  final VoidCallback? onOpenLogin;
  final bool isCheckingCreatorAccess;
  final bool canHostCompetitions;
  final String? clubId;
  final String? clubName;
  final VoidCallback? onOpenClubTab;
  final VoidCallback? onOpenCompetitionsTab;
  final VoidCallback? onOpenMarketTab;
  final VoidCallback? onOpenHubTab;
  final VoidCallback? onOpenWalletTab;
  final ValueChanged<ClubNavigationTab>? onOpenClubSubtab;
  final Future<void> Function()? onOpenCreatorAccessRequest;
  final GteNavigationDependencies? navigationDependencies;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: exchangeController,
      builder: (BuildContext context, Widget? child) {
        final _HomeDashboardSnapshot snapshot =
            _HomeDashboardSnapshot.fromController(
              controller: exchangeController,
              apiBaseUrl: apiBaseUrl,
              backendMode: backendMode,
              navigationDependencies: navigationDependencies,
              explicitClubId: clubId,
              explicitClubName: clubName,
              isCheckingCreatorAccess: isCheckingCreatorAccess,
              canHostCompetitions: canHostCompetitions,
            );
        final List<_DashboardPriority> priorities = _prioritiesFor(snapshot);
        return RefreshIndicator(
          onRefresh: _refresh,
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 120),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                _RoleHero(
                  snapshot: snapshot,
                  onPrimaryAction: _primaryActionFor(snapshot),
                  onRefresh: _refresh,
                ),
                const SizedBox(height: 16),
                GtexLiveTicker(
                  label: 'Operating pulse',
                  isSyncing: snapshot.isSyncing,
                  items: snapshot.livePulseItems,
                  accentColor: _roleColor(snapshot.role),
                ),
                const SizedBox(height: 16),
                _GlobalStatePanel(
                  snapshot: snapshot,
                  onRefresh: _refresh,
                  onOpenLogin: onOpenLogin,
                  onOpenClub: onOpenClubTab,
                ),
                const SizedBox(height: 18),
                _DashboardQuestionStrip(role: snapshot.role),
                const SizedBox(height: 18),
                _PriorityGrid(priorities: priorities),
                const SizedBox(height: 20),
                _ExpansionLanes(
                  onOpenPlayerCards: () => _openPlayerCards(context),
                  onOpenCompetitions: onOpenCompetitionsTab,
                ),
                if (snapshot.role == GtexHomeDashboardRole.fanNoClub) ...[
                  const SizedBox(height: 20),
                  _NoClubQuickLinks(
                    onOpenClub: onOpenClubTab,
                    onBrowseClubMarket: () => _openClubMarket(context),
                    onOpenMarket: onOpenMarketTab,
                    onOpenHub: onOpenHubTab,
                    onOpenCompetitions: onOpenCompetitionsTab,
                    onOpenWallet: onOpenWalletTab,
                  ),
                ],
              ],
            ),
          ),
        );
      },
    );
  }

  Future<void> _refresh() async {
    final List<Future<void>> work = <Future<void>>[
      exchangeController.loadMarket(reset: true),
    ];
    if (exchangeController.isAuthenticated) {
      work.add(exchangeController.loadPortfolio());
      work.add(exchangeController.loadOrders());
      work.add(exchangeController.refreshAccount());
    }
    await Future.wait<void>(work);
  }

  VoidCallback? _primaryActionFor(_HomeDashboardSnapshot snapshot) {
    switch (snapshot.role) {
      case GtexHomeDashboardRole.guest:
        return onOpenLogin;
      case GtexHomeDashboardRole.fanNoClub:
        return onOpenClubTab;
      case GtexHomeDashboardRole.clubOwner:
        return onOpenClubTab;
      case GtexHomeDashboardRole.coinTrader:
        return onOpenMarketTab;
      case GtexHomeDashboardRole.creator:
        return () {
          onOpenCreatorAccessRequest?.call();
        };
      case GtexHomeDashboardRole.competitionHost:
        return onOpenCompetitionsTab;
      case GtexHomeDashboardRole.admin:
        return onOpenHubTab;
    }
  }

  Future<void> _openPlayerCards(BuildContext context) async {
    if (onOpenMarketTab != null) {
      onOpenMarketTab!();
      return;
    }
    await GteNavigationHelpers.pushRoute<void>(
      context,
      route: const PlayerCardsBrowseRouteData(),
      dependencies: _navigationDependencies(),
    );
  }

  Future<void> _openClubMarket(BuildContext context) async {
    await GteNavigationHelpers.pushRoute<void>(
      context,
      route: const ClubSaleMarketListingsRouteData(),
      dependencies: _navigationDependencies(),
    );
  }

  GteNavigationDependencies _navigationDependencies() {
    final GteAuthSession? session = exchangeController.session;
    return navigationDependencies ??
        GteNavigationDependencies(
          apiBaseUrl: apiBaseUrl,
          backendMode: backendMode,
          currentUserId: session?.user.id ?? 'guest-user',
          currentUserName:
              session?.user.displayName ??
              session?.user.fullName ??
              session?.user.username,
          currentUserRole: session?.user.role,
          currentClubId:
              clubId ??
              _sessionString(session, <String>[
                'current_club_id',
                'currentClubId',
              ]),
          currentClubName:
              clubName ??
              _sessionString(session, <String>[
                'current_club_name',
                'currentClubName',
              ]),
          accessToken: exchangeController.accessToken,
          isAuthenticated: exchangeController.isAuthenticated,
          isCheckingCreatorAccess: isCheckingCreatorAccess,
          canHostCompetitions: canHostCompetitions,
          onOpenCreatorAccessRequest:
              onOpenCreatorAccessRequest == null
                  ? null
                  : (_) => onOpenCreatorAccessRequest!.call(),
        );
  }

  List<_DashboardPriority> _prioritiesFor(_HomeDashboardSnapshot snapshot) {
    return switch (snapshot.role) {
      GtexHomeDashboardRole.guest => <_DashboardPriority>[
        _DashboardPriority(
          label: 'Live ecosystem pulse',
          summary: 'Public GTEX activity needs a confirmed live feed.',
          state: snapshot.publicPulseState,
          icon: Icons.monitor_heart_outlined,
          accent: _roleColor(snapshot.role),
          actionLabel: 'Create account',
          onAction: onOpenLogin,
        ),
        _DashboardPriority(
          label: 'Public newsroom',
          summary:
              'Editorial and transfer stories render only from backend records.',
          state: GtexSurfaceState.empty,
          icon: Icons.newspaper_outlined,
          accent: GteShellTheme.accentClub,
        ),
        _DashboardPriority(
          label: 'Role cards',
          summary:
              'Account paths are visible without inventing wallet, club, or market data.',
          state: GtexSurfaceState.confirmed,
          icon: Icons.account_tree_outlined,
          accent: GteShellTheme.accentCapital,
        ),
        _DashboardPriority(
          label: 'Public competitions',
          summary:
              'Competition discovery waits for published backend competitions.',
          state: GtexSurfaceState.empty,
          icon: Icons.emoji_events_outlined,
          accent: GteShellTheme.accentArena,
          actionLabel: 'Open competitions',
          onAction: onOpenCompetitionsTab,
        ),
      ],
      GtexHomeDashboardRole.fanNoClub => <_DashboardPriority>[
        _DashboardPriority(
          label: 'National rentals',
          summary:
              'Eligible pools appear after the rental service returns confirmed records.',
          state: GtexSurfaceState.empty,
          icon: Icons.flag_outlined,
          accent: GteShellTheme.accentClub,
        ),
        _DashboardPriority(
          label: 'Player discovery',
          summary: 'Search and watchlists use loaded player records only.',
          state: snapshot.marketState,
          icon: Icons.travel_explore_outlined,
          accent: GteShellTheme.accent,
          actionLabel: 'Scout players',
          onAction: onOpenMarketTab,
        ),
        _DashboardPriority(
          label: 'Wallet setup',
          summary:
              'Deposits and gifting stay blocked until wallet truth is loaded.',
          state: snapshot.walletState,
          icon: Icons.account_balance_wallet_outlined,
          accent: GteShellTheme.accentCapital,
          actionLabel: 'Open funds',
          onAction: onOpenWalletTab,
        ),
        _DashboardPriority(
          label: 'Create club CTA',
          summary: 'No active club is attached to this session.',
          state: GtexSurfaceState.blocked,
          icon: Icons.add_business_outlined,
          accent: GteShellTheme.accentWarm,
          actionLabel: 'Create club',
          onAction: onOpenClubTab,
        ),
        _DashboardPriority(
          label: 'Creator content',
          summary: 'Creator feeds remain empty until backend content arrives.',
          state: GtexSurfaceState.empty,
          icon: Icons.movie_creation_outlined,
          accent: const Color(0xFF9B7CFF),
        ),
        _DashboardPriority(
          label: 'Community',
          summary:
              'Fan hubs and reports open without fabricated activity counts.',
          state: GtexSurfaceState.empty,
          icon: Icons.forum_outlined,
          accent: GteShellTheme.accentCommunity,
          actionLabel: 'Open world',
          onAction: onOpenHubTab,
        ),
      ],
      GtexHomeDashboardRole.clubOwner => <_DashboardPriority>[
        _DashboardPriority(
          label: 'Squad readiness',
          summary:
              snapshot.hasClub
                  ? 'Club context is confirmed for ${snapshot.clubName}.'
                  : 'A club must be selected before squad readiness can load.',
          state:
              snapshot.hasClub
                  ? GtexSurfaceState.confirmed
                  : GtexSurfaceState.blocked,
          icon: Icons.groups_2_outlined,
          accent: GteShellTheme.accent,
          actionLabel: 'Open club',
          onAction: onOpenClubTab,
        ),
        _DashboardPriority(
          label: 'Formation health',
          summary: 'Formation status needs backend squad and tactic records.',
          state: GtexSurfaceState.empty,
          icon: Icons.grid_view_outlined,
          accent: GteShellTheme.accentClub,
          actionLabel: 'Formation',
          onAction: () => onOpenClubSubtab?.call(ClubNavigationTab.squad),
        ),
        _DashboardPriority(
          label: 'Scouting',
          summary: 'Scouting notes and player fits use loaded market records.',
          state: snapshot.marketState,
          icon: Icons.manage_search_outlined,
          accent: GteShellTheme.accentWarm,
          actionLabel: 'Scout players',
          onAction: onOpenMarketTab,
        ),
        _DashboardPriority(
          label: 'Transfer pipeline',
          summary: snapshot.orderSummary,
          state: snapshot.ordersState,
          icon: Icons.swap_horiz_outlined,
          accent: GteShellTheme.accentCapital,
          actionLabel: 'Open market',
          onAction: onOpenMarketTab,
        ),
        _DashboardPriority(
          label: 'Competitions',
          summary:
              'Entries, fixtures, and settlement readiness wait for competition records.',
          state: GtexSurfaceState.empty,
          icon: Icons.emoji_events_outlined,
          accent: GteShellTheme.accentArena,
          actionLabel: 'Open matchday',
          onAction: onOpenCompetitionsTab,
        ),
        _DashboardPriority(
          label: 'Finance',
          summary:
              'Club finance is separated from wallet summary until the finance API confirms it.',
          state: snapshot.walletState,
          icon: Icons.account_balance_outlined,
          accent: GteShellTheme.accentCapital,
          actionLabel: 'Open funds',
          onAction: onOpenWalletTab,
        ),
        _DashboardPriority(
          label: 'Academy',
          summary:
              'Academy origin, development, and regen states remain backend-led.',
          state: GtexSurfaceState.empty,
          icon: Icons.school_outlined,
          accent: const Color(0xFF9B7CFF),
        ),
        _DashboardPriority(
          label: 'Sponsorships',
          summary:
              'Sponsor obligations need contract records before action is enabled.',
          state: GtexSurfaceState.empty,
          icon: Icons.handshake_outlined,
          accent: GteShellTheme.accentCommunity,
        ),
        _DashboardPriority(
          label: 'Injuries and morale',
          summary:
              'Player health, morale, and tactic pressure require live club data.',
          state: GtexSurfaceState.empty,
          icon: Icons.health_and_safety_outlined,
          accent: GteShellTheme.warning,
        ),
      ],
      GtexHomeDashboardRole.coinTrader => <_DashboardPriority>[
        _DashboardPriority(
          label: 'Order book',
          summary: 'Live bid/ask depth waits for trader market records.',
          state: snapshot.marketState,
          icon: Icons.stacked_line_chart_outlined,
          accent: GteShellTheme.accent,
          actionLabel: 'Open market',
          onAction: onOpenMarketTab,
        ),
        _DashboardPriority(
          label: 'Liquidity',
          summary:
              'Liquidity bars render only after backend trader metrics sync.',
          state: GtexSurfaceState.empty,
          icon: Icons.waterfall_chart_outlined,
          accent: GteShellTheme.accentCapital,
        ),
        _DashboardPriority(
          label: 'Disputes',
          summary:
              'Dispute history is empty until settlement records are loaded.',
          state: GtexSurfaceState.empty,
          icon: Icons.gavel_outlined,
          accent: GteShellTheme.accentAdmin,
        ),
        _DashboardPriority(
          label: 'Settlement status',
          summary:
              'Pending and confirmed settlement queues use backend state only.',
          state: snapshot.ordersState,
          icon: Icons.receipt_long_outlined,
          accent: GteShellTheme.accentWarm,
        ),
        _DashboardPriority(
          label: 'Trust score and ratings',
          summary:
              'Ratings remain unavailable until trader review records exist.',
          state: GtexSurfaceState.empty,
          icon: Icons.verified_user_outlined,
          accent: GteShellTheme.accentClub,
        ),
        _DashboardPriority(
          label: 'Online presence',
          summary:
              'Realtime availability is degraded until the trader socket reports presence.',
          state: GtexSurfaceState.degraded,
          icon: Icons.sensors_outlined,
          accent: GteShellTheme.warning,
        ),
      ],
      GtexHomeDashboardRole.creator => <_DashboardPriority>[
        _DashboardPriority(
          label: 'Campaigns',
          summary: 'Campaign cards require backend creator campaign records.',
          state: GtexSurfaceState.empty,
          icon: Icons.campaign_outlined,
          accent: const Color(0xFF9B7CFF),
        ),
        _DashboardPriority(
          label: 'Audience',
          summary:
              'Audience analytics stay empty until engagement events sync.',
          state: GtexSurfaceState.empty,
          icon: Icons.diversity_3_outlined,
          accent: GteShellTheme.accentClub,
        ),
        _DashboardPriority(
          label: 'Engagement',
          summary:
              'Realtime reactions and sponsored clips are not estimated here.',
          state: GtexSurfaceState.empty,
          icon: Icons.forum_outlined,
          accent: GteShellTheme.accentCommunity,
        ),
        _DashboardPriority(
          label: 'Moderation',
          summary: 'Creator review and moderation actions need queue data.',
          state: GtexSurfaceState.empty,
          icon: Icons.policy_outlined,
          accent: GteShellTheme.accentAdmin,
        ),
        _DashboardPriority(
          label: 'Earnings and settlements',
          summary:
              'Creator wallet settlement state is separate from estimated earnings.',
          state: snapshot.walletState,
          icon: Icons.payments_outlined,
          accent: GteShellTheme.accentCapital,
        ),
      ],
      GtexHomeDashboardRole.competitionHost => <_DashboardPriority>[
        _DashboardPriority(
          label: 'Entries',
          summary: 'Entry totals require hosted competition records.',
          state: GtexSurfaceState.empty,
          icon: Icons.how_to_reg_outlined,
          accent: GteShellTheme.accent,
        ),
        _DashboardPriority(
          label: 'Fixtures and brackets',
          summary:
              'Fixtures, brackets, and reschedules remain empty without backend schedule data.',
          state: GtexSurfaceState.empty,
          icon: Icons.account_tree_outlined,
          accent: GteShellTheme.accentClub,
          actionLabel: 'Open matchday',
          onAction: onOpenCompetitionsTab,
        ),
        _DashboardPriority(
          label: 'Prize pools',
          summary:
              'Prize setup waits for finance and settlement readiness records.',
          state: GtexSurfaceState.empty,
          icon: Icons.savings_outlined,
          accent: GteShellTheme.accentCapital,
        ),
        _DashboardPriority(
          label: 'Settlement readiness',
          summary:
              'Settlement controls stay blocked until hosted competition state confirms.',
          state: GtexSurfaceState.blocked,
          icon: Icons.fact_check_outlined,
          accent: GteShellTheme.warning,
        ),
        _DashboardPriority(
          label: 'Scheduling',
          summary:
              'Scheduling actions require confirmed competition ownership.',
          state: GtexSurfaceState.empty,
          icon: Icons.calendar_month_outlined,
          accent: GteShellTheme.accentWarm,
        ),
      ],
      GtexHomeDashboardRole.admin => <_DashboardPriority>[
        _DashboardPriority(
          label: 'Treasury',
          summary: 'Treasury posture renders only from admin finance records.',
          state: snapshot.walletState,
          icon: Icons.account_balance_outlined,
          accent: GteShellTheme.accentCapital,
        ),
        _DashboardPriority(
          label: 'Payment proofs',
          summary:
              'Manual bank transfer proof queues wait for admin review data.',
          state: GtexSurfaceState.empty,
          icon: Icons.upload_file_outlined,
          accent: GteShellTheme.accentClub,
        ),
        _DashboardPriority(
          label: 'Disputes',
          summary:
              'Dispute rows require actor, severity, timestamps, and audit trail records.',
          state: GtexSurfaceState.empty,
          icon: Icons.gavel_outlined,
          accent: GteShellTheme.accentAdmin,
        ),
        _DashboardPriority(
          label: 'Fraud alerts',
          summary: 'Risk alerts stay empty until backend fraud signals exist.',
          state: GtexSurfaceState.empty,
          icon: Icons.crisis_alert_outlined,
          accent: GteShellTheme.negative,
        ),
        _DashboardPriority(
          label: 'Liquidity monitoring',
          summary:
              'Trader liquidity visibility uses confirmed market infrastructure metrics.',
          state: GtexSurfaceState.empty,
          icon: Icons.query_stats_outlined,
          accent: GteShellTheme.accent,
        ),
        _DashboardPriority(
          label: 'KYC and settlements',
          summary: snapshot.complianceSummary,
          state: snapshot.complianceState,
          icon: Icons.assignment_ind_outlined,
          accent: GteShellTheme.accentWarm,
        ),
        _DashboardPriority(
          label: 'Abuse monitoring',
          summary:
              'Moderation and abuse queues require operational queue records.',
          state: GtexSurfaceState.empty,
          icon: Icons.report_outlined,
          accent: GteShellTheme.warning,
        ),
      ],
    };
  }
}

enum GtexHomeDashboardRole {
  guest,
  fanNoClub,
  clubOwner,
  coinTrader,
  creator,
  competitionHost,
  admin,
}

extension GtexHomeDashboardRoleX on GtexHomeDashboardRole {
  String get label {
    return switch (this) {
      GtexHomeDashboardRole.guest => 'Guest',
      GtexHomeDashboardRole.fanNoClub => 'Fan / No club',
      GtexHomeDashboardRole.clubOwner => 'Club owner',
      GtexHomeDashboardRole.coinTrader => 'Coin trader',
      GtexHomeDashboardRole.creator => 'Creator',
      GtexHomeDashboardRole.competitionHost => 'Competition host',
      GtexHomeDashboardRole.admin => 'Admin',
    };
  }

  String get title {
    return switch (this) {
      GtexHomeDashboardRole.guest => 'GTEX public operating board',
      GtexHomeDashboardRole.fanNoClub => 'Build your football footprint',
      GtexHomeDashboardRole.clubOwner => 'Club operating command',
      GtexHomeDashboardRole.coinTrader => 'Liquidity desk',
      GtexHomeDashboardRole.creator => 'Creator operating studio',
      GtexHomeDashboardRole.competitionHost => 'Competition control room',
      GtexHomeDashboardRole.admin => 'Operational command system',
    };
  }

  String get subtitle {
    return switch (this) {
      GtexHomeDashboardRole.guest =>
        'Public surfaces explain GTEX without exposing private economy records.',
      GtexHomeDashboardRole.fanNoClub =>
        'Player discovery, national rentals, gifting, creators, wallet setup, and club creation stay grounded in confirmed account state.',
      GtexHomeDashboardRole.clubOwner =>
        'Squad, tactics, scouting, transfer, finance, academy, sponsorship, morale, and competition priorities are visible in one operational board.',
      GtexHomeDashboardRole.coinTrader =>
        'Order book, liquidity, disputes, settlements, ratings, trust, presence, and payout work as an always-on desk.',
      GtexHomeDashboardRole.creator =>
        'Campaigns, audience, engagement, moderation, earnings, settlements, and sponsored content stay auditable.',
      GtexHomeDashboardRole.competitionHost =>
        'Entries, fixtures, brackets, prizes, settlement readiness, and scheduling move through confirmed competition state.',
      GtexHomeDashboardRole.admin =>
        'Treasury, payment proofs, disputes, fraud, liquidity, KYC, settlements, and abuse queues are treated as operational command surfaces.',
    };
  }

  String get primaryActionLabel {
    return switch (this) {
      GtexHomeDashboardRole.guest => 'Create account',
      GtexHomeDashboardRole.fanNoClub => 'Create club',
      GtexHomeDashboardRole.clubOwner => 'Open club',
      GtexHomeDashboardRole.coinTrader => 'Open market',
      GtexHomeDashboardRole.creator => 'Creator access',
      GtexHomeDashboardRole.competitionHost => 'Open matchday',
      GtexHomeDashboardRole.admin => 'Open command rail',
    };
  }
}

class _HomeDashboardSnapshot {
  const _HomeDashboardSnapshot({
    required this.role,
    required this.isAuthenticated,
    required this.userLabel,
    required this.clubId,
    required this.clubName,
    required this.backendMode,
    required this.apiHost,
    required this.marketState,
    required this.ordersState,
    required this.walletState,
    required this.complianceState,
    required this.publicPulseState,
    required this.isSyncing,
    required this.errorMessages,
    required this.playerRecordCount,
    required this.openOrderCount,
    required this.recentOrderCount,
    required this.hasWalletSummary,
    required this.walletTotalLabel,
    required this.complianceSummary,
    required this.orderSummary,
    required this.livePulseItems,
  });

  final GtexHomeDashboardRole role;
  final bool isAuthenticated;
  final String userLabel;
  final String? clubId;
  final String? clubName;
  final GteBackendMode backendMode;
  final String apiHost;
  final GtexSurfaceState marketState;
  final GtexSurfaceState ordersState;
  final GtexSurfaceState walletState;
  final GtexSurfaceState complianceState;
  final GtexSurfaceState publicPulseState;
  final bool isSyncing;
  final List<String> errorMessages;
  final int playerRecordCount;
  final int openOrderCount;
  final int recentOrderCount;
  final bool hasWalletSummary;
  final String walletTotalLabel;
  final String complianceSummary;
  final String orderSummary;
  final List<String> livePulseItems;

  bool get hasClub => clubId != null && clubId!.trim().isNotEmpty;
  bool get hasErrors => errorMessages.isNotEmpty;
  bool get isLiveBackend => backendMode == GteBackendMode.live;

  static _HomeDashboardSnapshot fromController({
    required GteExchangeController controller,
    required String apiBaseUrl,
    required GteBackendMode backendMode,
    required GteNavigationDependencies? navigationDependencies,
    required String? explicitClubId,
    required String? explicitClubName,
    required bool isCheckingCreatorAccess,
    required bool canHostCompetitions,
  }) {
    final GteAuthSession? session = controller.session;
    final bool isAuthenticated =
        controller.isAuthenticated ||
        (navigationDependencies?.isAuthenticated ?? false);
    final String? clubId =
        _clean(explicitClubId) ??
        _clean(navigationDependencies?.currentClubId) ??
        _sessionString(session, <String>['current_club_id', 'currentClubId']) ??
        _userString(session, <String>['current_club_id', 'currentClubId']);
    final String? clubName =
        _clean(explicitClubName) ??
        _clean(navigationDependencies?.currentClubName) ??
        _sessionString(session, <String>[
          'current_club_name',
          'currentClubName',
        ]) ??
        _userString(session, <String>['current_club_name', 'currentClubName']);
    final String? roleHint =
        _clean(navigationDependencies?.currentUserRole) ??
        _clean(session?.user.role) ??
        _clean(session?.user.accountType) ??
        _userString(session, <String>[
          'primary_role',
          'primaryRole',
          'profile_type',
          'profileType',
        ]);
    final bool hasClub = clubId != null && clubId.isNotEmpty;
    final GtexHomeDashboardRole role = _resolveRole(
      isAuthenticated: isAuthenticated,
      roleHint: roleHint,
      accountType: session?.user.accountType,
      hasClub: hasClub,
      canHostCompetitions:
          canHostCompetitions ||
          (navigationDependencies?.canHostCompetitions ?? false),
    );
    final List<String> errors = <String>[
      if (_clean(controller.marketError) != null) controller.marketError!,
      if (_clean(controller.portfolioError) != null) controller.portfolioError!,
      if (_clean(controller.ordersError) != null) controller.ordersError!,
      if (_clean(controller.complianceError) != null)
        controller.complianceError!,
    ];
    final bool isSyncing =
        controller.isBootstrapping ||
        controller.isLoadingMarket ||
        controller.isLoadingMoreMarket ||
        controller.isLoadingPortfolio ||
        controller.isLoadingOrders ||
        controller.isLoadingCompliance ||
        isCheckingCreatorAccess;
    final GtexSurfaceState marketState = _stateFor(
      isLoading: controller.isLoadingMarket || controller.isLoadingMoreMarket,
      error: controller.marketError,
      hasData: controller.marketPage != null,
      hasRecords: (controller.marketPage?.items.length ?? 0) > 0,
    );
    final GtexSurfaceState ordersState = _stateFor(
      isLoading: controller.isLoadingOrders,
      error: controller.ordersError,
      hasData: controller.hasLoadedOrders,
      hasRecords:
          controller.openOrderTotal > 0 || controller.recentOrderTotal > 0,
    );
    final GtexSurfaceState walletState = _stateFor(
      isLoading: controller.isLoadingPortfolio,
      error: controller.portfolioError,
      hasData: controller.walletDisplay != null,
      hasRecords: controller.walletDisplay != null,
      unauthenticatedState: GtexSurfaceState.blocked,
      isAuthenticated: isAuthenticated,
    );
    final GtexSurfaceState complianceState = _complianceState(controller);
    final String userLabel =
        _clean(navigationDependencies?.currentUserName) ??
        _clean(session?.user.displayName) ??
        _clean(session?.user.fullName) ??
        _clean(session?.user.username) ??
        'Guest';
    final String walletTotalLabel =
        controller.walletDisplay == null
            ? 'Awaiting wallet'
            : '${controller.walletDisplay!.totalBalance.toStringAsFixed(0)} ${controller.walletDisplay!.currencyCode}';
    final String orderSummary =
        controller.hasLoadedOrders
            ? '${controller.openOrderTotal} open / ${controller.recentOrderTotal} recent orders from backend state.'
            : 'Transfer pipeline waits for order records.';
    final String complianceSummary =
        controller.complianceStatus == null
            ? 'Compliance and policy state has not loaded for this account.'
            : controller.complianceStatus!.hasMissingRequiredPolicies
            ? '${controller.complianceStatus!.requiredPolicyAcceptancesMissing} policy requirements need action.'
            : 'Compliance state is ${controller.complianceStatus!.complianceStatus}.';
    final List<String> pulse = <String>[
      if (errors.isNotEmpty) 'Attention: ${errors.first}',
      if (isSyncing) 'Syncing confirmed account surfaces',
      if (hasClub && clubName != null) 'Active club confirmed: $clubName',
      if (isAuthenticated && !hasClub)
        'No active club attached to this session',
      if (!isAuthenticated)
        'Public mode active: private economy data is hidden',
      'Market records loaded: ${controller.marketPage?.items.length ?? 0}',
      'Open order records: ${controller.openOrderTotal}',
      controller.walletDisplay == null
          ? 'Wallet summary not loaded'
          : 'Wallet summary confirmed',
    ];
    return _HomeDashboardSnapshot(
      role: role,
      isAuthenticated: isAuthenticated,
      userLabel: userLabel,
      clubId: clubId,
      clubName: clubName,
      backendMode: backendMode,
      apiHost:
          Uri.tryParse(apiBaseUrl)?.host.isNotEmpty == true
              ? Uri.parse(apiBaseUrl).host
              : apiBaseUrl,
      marketState: marketState,
      ordersState: ordersState,
      walletState: walletState,
      complianceState: complianceState,
      publicPulseState:
          isSyncing ? GtexSurfaceState.syncing : GtexSurfaceState.empty,
      isSyncing: isSyncing,
      errorMessages: errors,
      playerRecordCount: controller.marketPage?.items.length ?? 0,
      openOrderCount: controller.openOrderTotal,
      recentOrderCount: controller.recentOrderTotal,
      hasWalletSummary: controller.walletDisplay != null,
      walletTotalLabel: walletTotalLabel,
      complianceSummary: complianceSummary,
      orderSummary: orderSummary,
      livePulseItems: pulse,
    );
  }
}

class _DashboardPriority {
  const _DashboardPriority({
    required this.label,
    required this.summary,
    required this.state,
    required this.icon,
    required this.accent,
    this.actionLabel,
    this.onAction,
  });

  final String label;
  final String summary;
  final GtexSurfaceState state;
  final IconData icon;
  final Color accent;
  final String? actionLabel;
  final VoidCallback? onAction;
}

class _RoleHero extends StatelessWidget {
  const _RoleHero({
    required this.snapshot,
    required this.onPrimaryAction,
    required this.onRefresh,
  });

  final _HomeDashboardSnapshot snapshot;
  final VoidCallback? onPrimaryAction;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final Color tone = _roleColor(snapshot.role);
    return _DashboardPanel(
      accent: tone,
      emphasized: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Wrap(
            spacing: 10,
            runSpacing: 10,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: <Widget>[
              _Pill(label: snapshot.role.label, color: tone),
              _Pill(
                label:
                    snapshot.isAuthenticated
                        ? 'Session confirmed'
                        : 'Public session',
                color:
                    snapshot.isAuthenticated
                        ? GteShellTheme.positive
                        : GteShellTheme.warning,
              ),
              _Pill(
                label:
                    snapshot.isLiveBackend
                        ? 'Live backend'
                        : 'Non-live transport',
                color:
                    snapshot.isLiveBackend
                        ? GteShellTheme.positive
                        : GteShellTheme.warning,
              ),
            ],
          ),
          const SizedBox(height: 18),
          Text(
            snapshot.role.title,
            style: theme.textTheme.displaySmall?.copyWith(
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            snapshot.role.subtitle,
            style: theme.textTheme.titleMedium?.copyWith(
              color: GteShellTheme.textPrimary.withValues(alpha: 0.78),
              height: 1.35,
            ),
          ),
          const SizedBox(height: 18),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              _Fact(label: 'User', value: snapshot.userLabel),
              _Fact(
                label: 'Club',
                value: snapshot.clubName ?? 'No club selected',
              ),
              _Fact(
                label: 'Players',
                value: snapshot.playerRecordCount.toString(),
              ),
              _Fact(label: 'Orders', value: snapshot.openOrderCount.toString()),
              _Fact(label: 'Wallet', value: snapshot.walletTotalLabel),
              _Fact(label: 'API host', value: snapshot.apiHost),
            ],
          ),
          const SizedBox(height: 20),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton.icon(
                onPressed: onPrimaryAction,
                icon: const Icon(Icons.arrow_outward_rounded),
                label: Text(snapshot.role.primaryActionLabel),
              ),
              OutlinedButton.icon(
                onPressed: () {
                  onRefresh();
                },
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('Pull latest state'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _GlobalStatePanel extends StatelessWidget {
  const _GlobalStatePanel({
    required this.snapshot,
    required this.onRefresh,
    required this.onOpenLogin,
    required this.onOpenClub,
  });

  final _HomeDashboardSnapshot snapshot;
  final Future<void> Function() onRefresh;
  final VoidCallback? onOpenLogin;
  final VoidCallback? onOpenClub;

  @override
  Widget build(BuildContext context) {
    if (snapshot.hasErrors) {
      return GtexStatePanel(
        state: GtexSurfaceState.error,
        eyebrow: 'Dashboard state',
        title: 'One or more role surfaces failed to load',
        message: snapshot.errorMessages.join(' '),
        actionLabel: 'Retry',
        onAction: () {
          onRefresh();
        },
      );
    }
    if (!snapshot.isAuthenticated) {
      return GtexStatePanel(
        state: GtexSurfaceState.blocked,
        eyebrow: 'Public mode',
        title: 'Private economy state is blocked',
        message:
            'Create an account to unlock wallet setup, club ownership, creator tools, trader workflows, and admin-grade operational state.',
        actionLabel: 'Create account',
        onAction: onOpenLogin,
      );
    }
    if (snapshot.role == GtexHomeDashboardRole.fanNoClub) {
      return GtexStatePanel(
        state: GtexSurfaceState.blocked,
        eyebrow: 'Club context',
        title: 'This account has no club yet',
        message:
            'Create or select a club before club operations, squad health, formation, finance, and competition actions can become active.',
        actionLabel: 'Create club',
        onAction: onOpenClub,
      );
    }
    if (snapshot.isSyncing) {
      return GtexStatePanel(
        state: GtexSurfaceState.syncing,
        eyebrow: 'Realtime state',
        title: 'Syncing role dashboard',
        message:
            'GTEX is reconciling the latest account, market, wallet, compliance, and order records.',
      );
    }
    return GtexStatePanel(
      state: GtexSurfaceState.confirmed,
      eyebrow: 'Dashboard state',
      title: 'Role scaffold is ready',
      message:
          'This board is using session-derived context and shows empty or blocked states where backend records are missing.',
    );
  }
}

class _DashboardQuestionStrip extends StatelessWidget {
  const _DashboardQuestionStrip({required this.role});

  final GtexHomeDashboardRole role;

  @override
  Widget build(BuildContext context) {
    return _DashboardPanel(
      accent: _roleColor(role),
      child: Wrap(
        spacing: 10,
        runSpacing: 10,
        children: const <Widget>[
          _QuestionChip(label: 'What changed?'),
          _QuestionChip(label: 'What matters now?'),
          _QuestionChip(label: 'What is blocked?'),
          _QuestionChip(label: 'What requires action?'),
          _QuestionChip(label: 'What impacts reputation?'),
          _QuestionChip(label: 'What can I do next?'),
        ],
      ),
    );
  }
}

class _PriorityGrid extends StatelessWidget {
  const _PriorityGrid({required this.priorities});

  final List<_DashboardPriority> priorities;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final int columns =
            constraints.maxWidth >= 1180
                ? 3
                : constraints.maxWidth >= 760
                ? 2
                : 1;
        const double spacing = 14;
        final double cardWidth =
            (constraints.maxWidth - (spacing * (columns - 1))) / columns;
        return Wrap(
          spacing: spacing,
          runSpacing: spacing,
          children: priorities
              .map(
                (_DashboardPriority priority) => SizedBox(
                  width: cardWidth,
                  child: _PriorityCard(priority: priority),
                ),
              )
              .toList(growable: false),
        );
      },
    );
  }
}

class _PriorityCard extends StatelessWidget {
  const _PriorityCard({required this.priority});

  final _DashboardPriority priority;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final bool confirmed = priority.state == GtexSurfaceState.confirmed;
    return _DashboardPanel(
      accent: priority.accent,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Container(
                width: 42,
                height: 42,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(8),
                  color: priority.accent.withValues(alpha: 0.14),
                  border: Border.all(
                    color: priority.accent.withValues(alpha: 0.28),
                  ),
                ),
                child: Icon(priority.icon, color: priority.accent, size: 22),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    _StateTag(state: priority.state, color: priority.accent),
                    const SizedBox(height: 8),
                    Text(
                      priority.label,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            priority.summary,
            maxLines: confirmed ? 3 : 2,
            overflow: TextOverflow.ellipsis,
            style: theme.textTheme.bodyMedium?.copyWith(height: 1.34),
          ),
          const SizedBox(height: 8),
          if (!confirmed) ...<Widget>[
            const SizedBox(height: 10),
            _CompactStateNotice(state: priority.state, color: priority.accent),
          ],
          if (priority.actionLabel != null) ...<Widget>[
            const SizedBox(height: 10),
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton.icon(
                onPressed: priority.onAction,
                icon: const Icon(Icons.arrow_forward_rounded, size: 18),
                label: Text(priority.actionLabel!),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _ExpansionLanes extends StatelessWidget {
  const _ExpansionLanes({
    required this.onOpenPlayerCards,
    required this.onOpenCompetitions,
  });

  final VoidCallback onOpenPlayerCards;
  final VoidCallback? onOpenCompetitions;

  @override
  Widget build(BuildContext context) {
    return _DashboardPanel(
      accent: GteShellTheme.accentWarm,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Expansion lanes',
            style: Theme.of(
              context,
            ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 10),
          Text(
            'Migration routes stay visible, but live-only workflows remain blocked until a canonical backend record exists.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton(
                onPressed: null,
                child: const Text('Fan predictions (live match only)'),
              ),
              OutlinedButton(
                onPressed: onOpenPlayerCards,
                child: const Text('Player cards'),
              ),
              OutlinedButton(
                onPressed: onOpenCompetitions,
                child: const Text('Open matchday'),
              ),
            ],
          ),
          const SizedBox(height: 10),
          const Text(
            'Fan predictions unlock from live-match routes after a canonical match id is present.',
          ),
        ],
      ),
    );
  }
}

class _NoClubQuickLinks extends StatelessWidget {
  const _NoClubQuickLinks({
    required this.onOpenClub,
    required this.onBrowseClubMarket,
    required this.onOpenMarket,
    required this.onOpenHub,
    required this.onOpenCompetitions,
    required this.onOpenWallet,
  });

  final VoidCallback? onOpenClub;
  final VoidCallback? onBrowseClubMarket;
  final VoidCallback? onOpenMarket;
  final VoidCallback? onOpenHub;
  final VoidCallback? onOpenCompetitions;
  final VoidCallback? onOpenWallet;

  @override
  Widget build(BuildContext context) {
    return _DashboardPanel(
      accent: GteShellTheme.accentClub,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'CLUB SETUP',
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: GteShellTheme.accentClub,
              fontWeight: FontWeight.w900,
              letterSpacing: 1.1,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            'Create, take over, or scout first',
            style: Theme.of(
              context,
            ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 8),
          Text(
            'Create a new club, take over an existing club, or keep scouting the football world while club-scoped operations remain blocked.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton.icon(
                onPressed: onBrowseClubMarket,
                icon: const Icon(Icons.storefront_outlined),
                label: const Text('Browse club market'),
              ),
              OutlinedButton.icon(
                onPressed: onOpenClub,
                icon: const Icon(Icons.add_business_outlined),
                label: const Text('Create club'),
              ),
              OutlinedButton.icon(
                onPressed: onOpenCompetitions,
                icon: const Icon(Icons.emoji_events_outlined),
                label: const Text('Explore competitions'),
              ),
              OutlinedButton(
                onPressed: onOpenMarket,
                child: const Text('Scout players'),
              ),
              OutlinedButton(
                onPressed: onOpenHub,
                child: const Text('Open world'),
              ),
              OutlinedButton(
                onPressed: onOpenWallet,
                child: const Text('Open funds'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _DashboardPanel extends StatelessWidget {
  const _DashboardPanel({
    required this.child,
    required this.accent,
    this.emphasized = false,
  });

  final Widget child;
  final Color accent;
  final bool emphasized;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Color.alphaBlend(
          accent.withValues(alpha: emphasized ? 0.08 : 0.04),
          theme.colorScheme.surface.withValues(alpha: 0.94),
        ),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: accent.withValues(alpha: 0.22)),
      ),
      child: child,
    );
  }
}

class _Fact extends StatelessWidget {
  const _Fact({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minWidth: 118),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        color: Colors.white.withValues(alpha: 0.04),
        border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Text(
            label.toUpperCase(),
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: GteShellTheme.textMuted,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(
              context,
            ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w900),
          ),
        ],
      ),
    );
  }
}

class _Pill extends StatelessWidget {
  const _Pill({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: color.withValues(alpha: 0.12),
        border: Border.all(color: color.withValues(alpha: 0.26)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
          color: color,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }
}

class _StateTag extends StatelessWidget {
  const _StateTag({required this.state, required this.color});

  final GtexSurfaceState state;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return _Pill(label: state.name, color: color);
  }
}

class _CompactStateNotice extends StatelessWidget {
  const _CompactStateNotice({required this.state, required this.color});

  final GtexSurfaceState state;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        color: color.withValues(alpha: 0.08),
        border: Border.all(color: color.withValues(alpha: 0.2)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(_stateIcon(state), size: 18, color: color),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                Text(
                  _stateTitle(state),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: color,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  _stateMessage(state),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  IconData _stateIcon(GtexSurfaceState state) {
    return switch (state) {
      GtexSurfaceState.loading => Icons.hourglass_empty_rounded,
      GtexSurfaceState.empty => Icons.inbox_outlined,
      GtexSurfaceState.blocked => Icons.lock_outline_rounded,
      GtexSurfaceState.pending => Icons.pending_actions_outlined,
      GtexSurfaceState.syncing => Icons.sync_rounded,
      GtexSurfaceState.reconnecting => Icons.wifi_find_rounded,
      GtexSurfaceState.degraded => Icons.warning_amber_rounded,
      GtexSurfaceState.confirmed => Icons.verified_outlined,
      GtexSurfaceState.error => Icons.error_outline_rounded,
    };
  }

  String _stateTitle(GtexSurfaceState state) {
    return switch (state) {
      GtexSurfaceState.loading => 'Loading backend data',
      GtexSurfaceState.empty => 'No backend records yet',
      GtexSurfaceState.blocked => 'Action blocked',
      GtexSurfaceState.pending => 'Waiting for confirmation',
      GtexSurfaceState.syncing => 'Syncing data',
      GtexSurfaceState.reconnecting => 'Realtime reconnecting',
      GtexSurfaceState.degraded => 'Live confidence reduced',
      GtexSurfaceState.confirmed => 'Confirmed',
      GtexSurfaceState.error => 'Unable to load',
    };
  }

  String _stateMessage(GtexSurfaceState state) {
    return switch (state) {
      GtexSurfaceState.loading =>
        'This surface is waiting for the latest backend response.',
      GtexSurfaceState.empty =>
        'No confirmed record has been returned for this priority.',
      GtexSurfaceState.blocked =>
        'Resolve account, club, eligibility, or review requirements first.',
      GtexSurfaceState.pending =>
        'A request exists and is waiting for the next confirmed event.',
      GtexSurfaceState.syncing =>
        'The surface is reconciling recent operational changes.',
      GtexSurfaceState.reconnecting =>
        'Realtime transport is reconnecting while confirmed data remains visible.',
      GtexSurfaceState.degraded =>
        'Confirmed records are visible, but one live signal is delayed.',
      GtexSurfaceState.confirmed => 'The backend has confirmed this surface.',
      GtexSurfaceState.error => 'Retry after the service is reachable.',
    };
  }
}

class _QuestionChip extends StatelessWidget {
  const _QuestionChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        color: Colors.white.withValues(alpha: 0.04),
        border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
      ),
      child: Text(
        label,
        style: Theme.of(
          context,
        ).textTheme.labelLarge?.copyWith(fontWeight: FontWeight.w800),
      ),
    );
  }
}

GtexHomeDashboardRole _resolveRole({
  required bool isAuthenticated,
  required String? roleHint,
  required String? accountType,
  required bool hasClub,
  required bool canHostCompetitions,
}) {
  if (!isAuthenticated) {
    return GtexHomeDashboardRole.guest;
  }
  final String normalized =
      '${roleHint ?? ''} ${accountType ?? ''}'.toLowerCase();
  if (normalized.contains('admin')) {
    return GtexHomeDashboardRole.admin;
  }
  if (normalized.contains('trader') || normalized.contains('liquidity')) {
    return GtexHomeDashboardRole.coinTrader;
  }
  if (normalized.contains('creator')) {
    return GtexHomeDashboardRole.creator;
  }
  if (canHostCompetitions ||
      normalized.contains('competition_host') ||
      normalized.contains('competition host') ||
      normalized.contains('host')) {
    return GtexHomeDashboardRole.competitionHost;
  }
  if (hasClub ||
      normalized.contains('club_owner') ||
      normalized.contains('club owner') ||
      normalized.contains('owner')) {
    return GtexHomeDashboardRole.clubOwner;
  }
  return GtexHomeDashboardRole.fanNoClub;
}

GtexSurfaceState _stateFor({
  required bool isLoading,
  required String? error,
  required bool hasData,
  required bool hasRecords,
  GtexSurfaceState unauthenticatedState = GtexSurfaceState.empty,
  bool isAuthenticated = true,
}) {
  if (!isAuthenticated) {
    return unauthenticatedState;
  }
  if (_clean(error) != null) {
    return GtexSurfaceState.error;
  }
  if (isLoading) {
    return GtexSurfaceState.syncing;
  }
  if (!hasData) {
    return GtexSurfaceState.empty;
  }
  if (!hasRecords) {
    return GtexSurfaceState.empty;
  }
  return GtexSurfaceState.confirmed;
}

GtexSurfaceState _complianceState(GteExchangeController controller) {
  if (!controller.isAuthenticated) {
    return GtexSurfaceState.blocked;
  }
  if (_clean(controller.complianceError) != null) {
    return GtexSurfaceState.error;
  }
  if (controller.isLoadingCompliance) {
    return GtexSurfaceState.syncing;
  }
  final GteComplianceStatus? status = controller.complianceStatus;
  if (status == null) {
    return GtexSurfaceState.empty;
  }
  if (status.hasMissingRequiredPolicies ||
      !status.canDeposit ||
      !status.canTradeMarket) {
    return GtexSurfaceState.blocked;
  }
  return GtexSurfaceState.confirmed;
}

Color _roleColor(GtexHomeDashboardRole role) {
  return switch (role) {
    GtexHomeDashboardRole.guest => GteShellTheme.accentClub,
    GtexHomeDashboardRole.fanNoClub => GteShellTheme.accentClub,
    GtexHomeDashboardRole.clubOwner => GteShellTheme.accent,
    GtexHomeDashboardRole.coinTrader => GteShellTheme.accentCapital,
    GtexHomeDashboardRole.creator => const Color(0xFF9B7CFF),
    GtexHomeDashboardRole.competitionHost => GteShellTheme.accentArena,
    GtexHomeDashboardRole.admin => GteShellTheme.accentAdmin,
  };
}

String? _clean(String? value) {
  final String? trimmed = value?.trim();
  if (trimmed == null || trimmed.isEmpty) {
    return null;
  }
  return trimmed;
}

String? _sessionString(GteAuthSession? session, List<String> keys) {
  if (session == null) {
    return null;
  }
  return _mapString(session.rawJson, keys);
}

String? _userString(GteAuthSession? session, List<String> keys) {
  if (session == null) {
    return null;
  }
  return _mapString(session.user.rawJson, keys);
}

String? _mapString(Map<String, Object?> map, List<String> keys) {
  for (final String key in keys) {
    final Object? value = map[key];
    if (value is String) {
      final String? trimmed = _clean(value);
      if (trimmed != null) {
        return trimmed;
      }
    }
  }
  return null;
}
