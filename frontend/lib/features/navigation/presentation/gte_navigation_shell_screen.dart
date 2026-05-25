import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:gte_frontend/controllers/creator_application_controller.dart';
import 'package:gte_frontend/controllers/creator_controller.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/controllers/referral_controller.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/core/gte_session_identity.dart';
import 'package:gte_frontend/data/club_creation_api.dart';
import 'package:gte_frontend/data/competition_api.dart';
import 'package:gte_frontend/data/creator_application_api.dart';
import 'package:gte_frontend/data/creator_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/referral_api.dart';
import 'package:gte_frontend/data/community_api.dart';
import 'package:gte_frontend/features/competitions_hub/presentation/gte_competitions_hub_screen_v2.dart';
import 'package:gte_frontend/features/competitions_hub/routing/competition_hub_destination.dart';
import 'package:gte_frontend/features/app_routes/gte_navigation_helpers.dart';
import 'package:gte_frontend/features/app_routes/gte_route_data.dart';
import 'package:gte_frontend/features/global_search_redesign/global_search_redesign.dart';
import 'package:gte_frontend/features/home/home_screen.dart';
import 'package:gte_frontend/features/launch_control_redesign/launch_control_feature_gate.dart';
import 'package:gte_frontend/features/navigation/routing/gte_navigation_route.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/features/social/social_screen.dart';
import 'package:gte_frontend/features/world/widgets/football_world_pulse_widgets.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/gte_exchange_player_detail_screen.dart';
import 'package:gte_frontend/screens/gte_login_screen.dart';
import 'package:gte_frontend/screens/gte_market_players_screen_v2.dart';
import 'package:gte_frontend/screens/creators/creator_access_request_screen.dart';
import 'package:gte_frontend/screens/creators/gtex_studio_hub_screen_v2.dart';
import 'package:gte_frontend/screens/clubs/create_club_screen.dart';
import 'package:gte_frontend/screens/clubs/gtex_club_owner_dashboard_screen_v2.dart';
import 'package:gte_frontend/screens/admin/admin_command_center_screen.dart';
import 'package:gte_frontend/screens/notifications/gte_notifications_screen_v2.dart';
import 'package:gte_frontend/screens/profile/gtex_live_profile_screen.dart';
import 'package:gte_frontend/screens/wallet/gte_funding_flow_screen.dart';
import 'package:gte_frontend/screens/wallet/gte_withdrawal_flow_screen.dart';
import 'package:gte_frontend/screens/wallet/gtex_wallet_overview_screen_v2.dart';
import 'package:gte_frontend/services/ambient_audio_controller.dart';
import 'package:gte_frontend/theme/gte_theme_picker_sheet.dart';
import 'package:gte_frontend/ui_gtex/components/gtex_button.dart';
import 'package:gte_frontend/ui_gtex/components/gtex_metric_tile.dart';
import 'package:gte_frontend/ui_gtex/components/gtex_panel.dart';
import 'package:gte_frontend/ui_gtex/layout/gtex_app_shell.dart';
import 'package:gte_frontend/ui_gtex/routes/gtex_current_route_adapter.dart';
import 'package:gte_frontend/ui_gtex/theme/gtex_colors.dart';
import 'package:gte_frontend/ui_gtex/theme/gtex_spacing.dart';
import 'package:gte_frontend/widgets/ambient_audio_toggle_button.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_sync_status_card.dart';

class GteNavigationShellScreen extends StatefulWidget {
  const GteNavigationShellScreen({
    super.key,
    required this.controller,
    required this.apiBaseUrl,
    required this.backendMode,
    this.ambientAudioController,
    this.initialRoute = const GteNavigationRoute.home(),
    this.onRouteChanged,
    this.navigationDependencies,
  });

  factory GteNavigationShellScreen.fromPath({
    Key? key,
    required GteExchangeController controller,
    required String apiBaseUrl,
    required GteBackendMode backendMode,
    AmbientAudioState? ambientAudioController,
    required String initialPath,
    ValueChanged<GteNavigationRoute>? onRouteChanged,
    GteNavigationDependencies? navigationDependencies,
  }) {
    return GteNavigationShellScreen(
      key: key,
      controller: controller,
      apiBaseUrl: apiBaseUrl,
      backendMode: backendMode,
      ambientAudioController: ambientAudioController,
      initialRoute: GteNavigationRoute.parse(initialPath),
      onRouteChanged: onRouteChanged,
      navigationDependencies: navigationDependencies,
    );
  }

  final GteExchangeController controller;
  final String apiBaseUrl;
  final GteBackendMode backendMode;
  final AmbientAudioState? ambientAudioController;
  final GteNavigationRoute initialRoute;
  final ValueChanged<GteNavigationRoute>? onRouteChanged;
  final GteNavigationDependencies? navigationDependencies;

  @override
  State<GteNavigationShellScreen> createState() =>
      _GteNavigationShellScreenState();
}

Color _routeAccentFor(BuildContext context, GtePrimaryDestination destination) {
  final tokens = GteShellTheme.tokensOf(context);
  switch (destination) {
    case GtePrimaryDestination.home:
    case GtePrimaryDestination.market:
      return tokens.accent;
    case GtePrimaryDestination.competitions:
      return tokens.accentArena;
    case GtePrimaryDestination.hub:
    case GtePrimaryDestination.community:
      return tokens.accentCommunity;
    case GtePrimaryDestination.club:
      return tokens.accentClub;
    case GtePrimaryDestination.wallet:
      return tokens.accentCapital;
  }
}

class _NavigationProviderScopeBoundary extends StatefulWidget {
  const _NavigationProviderScopeBoundary({required this.child});

  final Widget child;

  @override
  State<_NavigationProviderScopeBoundary> createState() =>
      _NavigationProviderScopeBoundaryState();
}

class _NavigationProviderScopeBoundaryState
    extends State<_NavigationProviderScopeBoundary> {
  ProviderContainer? _container;

  @override
  void dispose() {
    _container?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    try {
      ProviderScope.containerOf(context, listen: false);
      _container?.dispose();
      _container = null;
      return widget.child;
    } on StateError {
      final ProviderContainer container = _container ??= ProviderContainer();
      return UncontrolledProviderScope(
        container: container,
        child: widget.child,
      );
    }
  }
}

class _GteNavigationShellScreenState extends State<GteNavigationShellScreen> {
  late GteNavigationRoute _route;
  late CompetitionController _competitionController;
  late CreatorApplicationController _creatorApplicationController;
  late CreatorController _creatorController;
  late ReferralController _referralController;
  late String _competitionUserId;
  late String? _competitionUserName;
  late String? _creatorAccessToken;
  final PageStorageBucket _pageStorageBucket = PageStorageBucket();
  bool _startupWorkScheduled = false;
  Timer? _liveRefreshTimer;

  bool get _isTestBinding =>
      WidgetsBinding.instance.runtimeType.toString().contains('Test');

  @override
  void initState() {
    super.initState();
    _route = widget.initialRoute;
    widget.controller.addListener(_handleExchangeControllerChanged);
    _competitionUserId = _resolveCompetitionUserId();
    _competitionUserName = _resolveCompetitionUserName();
    _creatorAccessToken = widget.controller.accessToken;
    _competitionController = _buildCompetitionController();
    _creatorApplicationController = _buildCreatorApplicationController();
    _creatorApplicationController.addListener(_handleCreatorAccessChanged);
    _creatorController = _buildCreatorController();
    _referralController = _buildReferralController();
    _scheduleStartupWork();
    _startLiveRefreshLoop();
  }

  @override
  void didUpdateWidget(covariant GteNavigationShellScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.controller != widget.controller) {
      oldWidget.controller.removeListener(_handleExchangeControllerChanged);
      widget.controller.addListener(_handleExchangeControllerChanged);
      _handleExchangeControllerChanged();
    }
    if (oldWidget.apiBaseUrl != widget.apiBaseUrl ||
        oldWidget.backendMode != widget.backendMode) {
      _competitionController.dispose();
      _competitionController = _buildCompetitionController();
      _disposeCreatorAccessController();
      _creatorApplicationController = _buildCreatorApplicationController();
      _creatorApplicationController.addListener(_handleCreatorAccessChanged);
      _creatorController.dispose();
      _creatorController = _buildCreatorController();
      _referralController.dispose();
      _referralController = _buildReferralController();
      _creatorAccessToken = widget.controller.accessToken;
      _scheduleStartupWork(force: true);
    }
    if (widget.initialRoute != oldWidget.initialRoute &&
        widget.initialRoute != _route) {
      setState(() {
        _route = widget.initialRoute;
      });
      _scheduleStartupWork(force: true);
    }
  }

  @override
  void dispose() {
    widget.controller.removeListener(_handleExchangeControllerChanged);
    _liveRefreshTimer?.cancel();
    _competitionController.dispose();
    _disposeCreatorAccessController();
    _creatorController.dispose();
    _referralController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final Size viewport = MediaQuery.sizeOf(context);
    final bool compactViewport = viewport.height < 720 || viewport.width < 480;
    final EdgeInsets topSectionPadding =
        compactViewport
            ? const EdgeInsets.fromLTRB(16, 6, 16, 0)
            : const EdgeInsets.fromLTRB(20, 12, 20, 0);
    final bool showShellStatusCard = !compactViewport;
    return _NavigationProviderScopeBoundary(
      child: AnimatedBuilder(
        animation: widget.controller,
        builder: (BuildContext context, Widget? child) {
          final Widget workspace = PageStorage(
            bucket: _pageStorageBucket,
            child: KeyedSubtree(
              key: ValueKey<String>('shell-${_route.primaryDestination.name}'),
              child: _buildCurrentDestination(),
            ),
          );

          return GtexAppShell(
            destinations: GtexCurrentRouteAdapter.destinations(
              current: _route.primaryDestination,
              onOpen: _openPrimaryDestination,
              badgeLabels: _destinationBadgesForWorkspace(),
              items: _primaryDestinationsForWorkspace(),
            ),
            title: _routeTitle(),
            subtitle: '${_routeSubtitle()} - ${_routeContextLine()}',
            actions: _buildGtexShellActions(context, compactViewport),
            status:
                showShellStatusCard
                    ? Padding(
                      padding: topSectionPadding,
                      child: _buildModeSyncCard(context),
                    )
                    : null,
            livePulseStrip: const FootballWorldPulseTicker(),
            worldPulseRail:
                compactViewport ? null : const FootballWorldPulseRail(),
            child: workspace,
          );
        },
      ),
    );
  }

  List<Widget> _buildGtexShellActions(
    BuildContext context,
    bool compactViewport,
  ) {
    if (compactViewport) {
      return <Widget>[
        if (widget.controller.isAuthenticated)
          IconButton(
            tooltip: 'Search GTEX',
            onPressed: _openGlobalSearch,
            icon: const Icon(
              Icons.manage_search_outlined,
              color: GtexColors.text,
            ),
          ),
        if (widget.controller.isAuthenticated)
          IconButton(
            tooltip: 'Profile and settings',
            onPressed: _openProfileSettings,
            icon: const Icon(
              Icons.account_circle_outlined,
              color: GtexColors.text,
            ),
          ),
        IconButton(
          tooltip: widget.controller.isAuthenticated ? 'Sign out' : 'Sign in',
          onPressed:
              widget.controller.isAuthenticated
                  ? () async {
                    await widget.controller.signOut();
                    if (!mounted) {
                      return;
                    }
                    _setRoute(const GteNavigationRoute.home());
                  }
                  : () => _openLogin(),
          icon: Icon(
            widget.controller.isAuthenticated ? Icons.logout : Icons.login,
            color: GtexColors.text,
          ),
        ),
      ];
    }

    final List<Widget> actions = <Widget>[
      _buildThemePickerAction(context),
      _buildAmbientAction(),
      _buildCapitalAction(),
    ];

    if (!widget.controller.isAuthenticated) {
      actions.add(
        GtexButton(
          label: 'Sign in',
          icon: Icons.login,
          compact: true,
          onPressed: () => _openLogin(),
        ),
      );
      return actions;
    }

    actions.addAll(<Widget>[
      IconButton(
        tooltip: 'Search GTEX',
        onPressed: _openGlobalSearch,
        icon: const Icon(Icons.manage_search_outlined, color: GtexColors.text),
      ),
      Padding(
        padding: const EdgeInsets.only(right: 8),
        child: Center(
          child: Text(
            widget.controller.session!.user.username,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: GtexColors.text,
              fontWeight: FontWeight.w800,
            ),
          ),
        ),
      ),
      IconButton(
        tooltip: 'Profile and settings',
        onPressed: _openProfileSettings,
        icon: const Icon(Icons.account_circle_outlined, color: GtexColors.text),
      ),
      IconButton(
        tooltip: 'Creator access request',
        onPressed: () => _pushCreatorAccessRequest(context),
        icon: const Icon(Icons.how_to_reg_outlined, color: GtexColors.text),
      ),
      if (_hasApprovedCreatorAccess)
        IconButton(
          tooltip: 'Creator community',
          onPressed: () => _openPrimaryDestination(GtePrimaryDestination.hub),
          icon: const Icon(Icons.campaign_outlined, color: GtexColors.text),
        ),
      IconButton(
        tooltip: 'Notifications',
        onPressed: _openNotifications,
        icon: const Icon(
          Icons.notifications_active_outlined,
          color: GtexColors.text,
        ),
      ),
      IconButton(
        tooltip: 'Transfer Hub',
        onPressed: _openCoachMarket,
        icon: const Icon(Icons.sports_soccer_outlined, color: GtexColors.text),
      ),
      if (_isAdminSession)
        IconButton(
          tooltip: 'Admin dashboard',
          onPressed: _openAdminCommandCenter,
          icon: const Icon(
            Icons.admin_panel_settings_outlined,
            color: GtexColors.text,
          ),
        ),
      GtexButton(
        label: 'Sign out',
        icon: Icons.logout,
        variant: GtexButtonVariant.secondary,
        compact: true,
        onPressed: () async {
          await widget.controller.signOut();
          if (!mounted) {
            return;
          }
          _setRoute(const GteNavigationRoute.home());
        },
      ),
    ]);

    return actions;
  }

  Widget _buildClubDestination() {
    final String? canonicalClubId = _canonicalClubId()?.trim();
    if (canonicalClubId == null || canonicalClubId.isEmpty) {
      return _GtexCommandHomeEntry(
        isAuthenticated: widget.controller.isAuthenticated,
        userLabel: widget.controller.session?.user.username ?? 'Preview scout',
        onSignIn:
            () => _openLogin(targetRoute: const GteNavigationRoute.club()),
        onCreateClub:
            widget.controller.isAuthenticated
                ? _openCreateClubFlow
                : () =>
                    _openLogin(targetRoute: const GteNavigationRoute.club()),
        onOpenMarket:
            () => _openPrimaryDestination(GtePrimaryDestination.market),
        onOpenCompetitions:
            () => _openPrimaryDestination(GtePrimaryDestination.competitions),
        onOpenWorld: () {
          unawaited(_openFeatureRoute(const WorldOverviewRouteData()));
        },
      );
    }
    return GtexClubOwnerDashboardScreenV2(
      key: const PageStorageKey<String>('club-owner-dashboard-v2'),
      clubId: canonicalClubId,
      clubName: _canonicalClubName(),
      baseUrl: widget.apiBaseUrl,
      backendMode: widget.backendMode,
      accessToken: widget.controller.accessToken,
      authedApi: _createShellAuthedApi(),
      ownerName: widget.controller.session?.user.username,
      walletCredits:
          widget.controller.walletSummary?.availableBalance.round() ?? 0,
      isAuthenticated: widget.controller.isAuthenticated,
      onOpenLogin:
          () => _openLogin(targetRoute: const GteNavigationRoute.club()),
    );
  }

  Widget _buildHomeDestination() {
    if (widget.controller.isAuthenticated && _isAdminSession) {
      final String? accessToken = widget.controller.accessToken;
      if (accessToken != null && accessToken.trim().isNotEmpty) {
        return AdminCommandCenterScreen(
          key: const PageStorageKey<String>('admin-command-center-home'),
          baseUrl: widget.apiBaseUrl,
          accessToken: accessToken,
          backendMode: widget.backendMode,
          authedApi: _createShellAuthedApi(),
        );
      }
    }
    if (widget.controller.isAuthenticated && _isCoinTraderSession) {
      return GtexWalletOverviewScreenV2(
        key: const PageStorageKey<String>('home-trader-dashboard-v2'),
        controller: widget.controller,
        baseUrl: widget.apiBaseUrl,
        backendMode: widget.backendMode,
        initialModule: GtexWalletDeskModule.traderDashboard,
        onTopUp: _openWalletTopUp,
        onWithdraw: _openWalletWithdraw,
        onOpenLogin:
            () => _openLogin(targetRoute: const GteNavigationRoute.home()),
        onOpenPlayer: _openPlayer,
        onModuleChanged: _openWalletModule,
        authedApi: _createShellAuthedApi(),
      );
    }
    final String? canonicalClubId = _canonicalClubId()?.trim();
    if (canonicalClubId == null || canonicalClubId.isEmpty) {
      if (widget.controller.isAuthenticated) {
        return const HomeScreen(key: PageStorageKey<String>('home-command'));
      }
      return const HomeScreen(key: PageStorageKey<String>('home-command'));
    }
    return GtexClubOwnerDashboardScreenV2(
      key: const PageStorageKey<String>('home-club-owner-dashboard-v2'),
      clubId: canonicalClubId,
      clubName: _canonicalClubName(),
      baseUrl: widget.apiBaseUrl,
      backendMode: widget.backendMode,
      accessToken: widget.controller.accessToken,
      authedApi: _createShellAuthedApi(),
      ownerName: widget.controller.session?.user.username,
      walletCredits:
          widget.controller.walletSummary?.availableBalance.round() ?? 0,
      isAuthenticated: widget.controller.isAuthenticated,
      onOpenLogin:
          () => _openLogin(targetRoute: const GteNavigationRoute.home()),
    );
  }

  void _handleExchangeControllerChanged() {
    final String? nextAccessToken = widget.controller.accessToken;
    if (nextAccessToken != _creatorAccessToken) {
      _creatorAccessToken = nextAccessToken;
      _competitionController.dispose();
      _competitionController = _buildCompetitionController();
      _competitionController.bootstrap();
      _rebuildCreatorRuntimeControllers();
      _primeRouteData();
    }
    final String nextUserId = _resolveCompetitionUserId();
    final String? nextUserName = _resolveCompetitionUserName();
    if (nextUserId != _competitionUserId ||
        nextUserName != _competitionUserName) {
      _competitionUserId = nextUserId;
      _competitionUserName = nextUserName;
      _competitionController.updateCurrentUser(
        userId: _competitionUserId,
        userName: _competitionUserName,
      );
      _competitionController.loadDiscovery();
    }
  }

  void _handleCreatorAccessChanged() {
    if (!mounted) {
      return;
    }
    setState(() {});
  }

  void _rebuildCreatorRuntimeControllers() {
    _disposeCreatorAccessController();
    _creatorApplicationController = _buildCreatorApplicationController();
    _creatorApplicationController.addListener(_handleCreatorAccessChanged);
    _creatorController.dispose();
    _creatorController = _buildCreatorController();
    _referralController.dispose();
    _referralController = _buildReferralController();
    _primeCreatorAccessState(force: true);
    if (mounted) {
      setState(() {});
    }
  }

  void _disposeCreatorAccessController() {
    _creatorApplicationController.removeListener(_handleCreatorAccessChanged);
    _creatorApplicationController.dispose();
  }

  void _primeCreatorAccessState({bool force = false}) {
    if (!widget.controller.isAuthenticated) {
      return;
    }
    _creatorApplicationController.load(force: force);
  }

  bool get _isCheckingCreatorAccess {
    if (!widget.controller.isAuthenticated) {
      return false;
    }
    return _creatorApplicationController.isLoading;
  }

  bool get _hasApprovedCreatorAccess {
    final application = _creatorApplicationController.application;
    return application?.isApproved == true;
  }

  bool get _canHostCompetitions {
    return widget.controller.isAuthenticated;
  }

  bool get _isReferralRuntimeAvailable {
    return widget.backendMode == GteBackendMode.fixture ||
        _referralController.hub != null;
  }

  GteBackendMode get _liveBackendMode => widget.backendMode;

  bool get _isAdminSession {
    return <String>{
      'admin',
      'super_admin',
      'god_mode',
      'scoped_admin',
    }.contains(_sessionRole);
  }

  bool get _isCoinTraderSession {
    final Set<String> permissions =
        widget.controller.session?.permissions
            .map((String value) => value.trim().toLowerCase())
            .where((String value) => value.isNotEmpty)
            .toSet() ??
        const <String>{};
    return <String>{
          'coin_trader',
          'coin-trader',
          'trader',
          'liquidity_partner',
        }.contains(_sessionRole) ||
        permissions.contains('coin_trader') ||
        permissions.contains('manage_coin_trades') ||
        permissions.contains('manage_coin_trader_rates');
  }

  bool get _isCreatorSession {
    final Set<String> permissions =
        widget.controller.session?.permissions
            .map((String value) => value.trim().toLowerCase())
            .where((String value) => value.isNotEmpty)
            .toSet() ??
        const <String>{};
    return _hasApprovedCreatorAccess ||
        <String>{
          'creator',
          'publisher',
          'content_creator',
          'creator_operator',
        }.contains(_sessionRole) ||
        permissions.contains('creator') ||
        permissions.contains('publish_content') ||
        permissions.contains('manage_creator_profile');
  }

  bool get _isStaffSession {
    return <String>{
      'agent',
      'scout',
      'manager',
      'coach',
      'analyst',
    }.contains(_sessionRole);
  }

  String get _sessionRole =>
      widget.controller.session?.user.role.trim().toLowerCase() ?? 'guest';

  String _routeTitle() {
    if (_route.primaryDestination != GtePrimaryDestination.home) {
      return GtexCurrentRouteAdapter.titleFor(_route.primaryDestination);
    }
    if (_isAdminSession) {
      return 'Admin Operations';
    }
    if (_isCoinTraderSession) {
      return 'Trader Market Desk';
    }
    if (_isCreatorSession) {
      return 'Creator Media Desk';
    }
    if (_canonicalClubId()?.trim().isNotEmpty ?? false) {
      return 'Club Operations';
    }
    if (widget.controller.isAuthenticated) {
      return 'Fan & Scout Desk';
    }
    return 'GTEX Explore';
  }

  String _routeSubtitle() {
    if (_route.primaryDestination != GtePrimaryDestination.home) {
      return GtexCurrentRouteAdapter.subtitleFor(_route.primaryDestination);
    }
    if (_isAdminSession) {
      return 'Payments, competitions, queues, traders, and settlement pressure';
    }
    if (_isCoinTraderSession) {
      return 'GTC and FNC liquidity, offers, wallet state, and buyer pressure';
    }
    if (_isCreatorSession) {
      return 'Newsroom, reactions, match stories, and creator wallet movement';
    }
    if (_canonicalClubId()?.trim().isNotEmpty ?? false) {
      return 'Squad, fixtures, transfers, club wallet, and ranking movement';
    }
    if (widget.controller.isAuthenticated) {
      return 'Transfers, regens, national rentals, wallet, and club onboarding';
    }
    return 'Browse clubs, transfers, competitions, regens, and GTEX economy news';
  }

  Map<GtePrimaryDestination, String> _destinationBadgesForWorkspace() {
    if (!widget.controller.isAuthenticated) {
      return const <GtePrimaryDestination, String>{
        GtePrimaryDestination.home: 'GUEST',
        GtePrimaryDestination.club: 'READ',
        GtePrimaryDestination.market: 'READ',
        GtePrimaryDestination.competitions: 'LIVE',
        GtePrimaryDestination.community: 'PUBLIC',
      };
    }
    if (_isAdminSession) {
      return const <GtePrimaryDestination, String>{
        GtePrimaryDestination.home: 'ADMIN',
        GtePrimaryDestination.competitions: 'HOST',
        GtePrimaryDestination.wallet: 'TREASURY',
        GtePrimaryDestination.hub: 'OPS',
      };
    }
    if (_isCoinTraderSession) {
      return const <GtePrimaryDestination, String>{
        GtePrimaryDestination.home: 'TRADER',
        GtePrimaryDestination.wallet: 'GTC/FNC',
        GtePrimaryDestination.market: 'LIVE',
        GtePrimaryDestination.community: 'ONLINE',
      };
    }
    if (_isCreatorSession) {
      return const <GtePrimaryDestination, String>{
        GtePrimaryDestination.home: 'CREATOR',
        GtePrimaryDestination.hub: 'STUDIO',
        GtePrimaryDestination.community: 'FEED',
        GtePrimaryDestination.wallet: 'EARN',
      };
    }
    if (_canonicalClubId()?.trim().isNotEmpty ?? false) {
      return const <GtePrimaryDestination, String>{
        GtePrimaryDestination.home: 'CLUB',
        GtePrimaryDestination.club: 'OWNER',
        GtePrimaryDestination.market: 'SCOUT',
        GtePrimaryDestination.competitions: 'ENTER',
        GtePrimaryDestination.wallet: 'GTC/FNC',
      };
    }
    return const <GtePrimaryDestination, String>{
      GtePrimaryDestination.home: 'USER',
      GtePrimaryDestination.club: 'START',
      GtePrimaryDestination.market: 'SCOUT',
      GtePrimaryDestination.wallet: 'GTC/FNC',
      GtePrimaryDestination.competitions: 'JOIN',
    };
  }

  List<GtePrimaryDestination> _primaryDestinationsForWorkspace() {
    if (!widget.controller.isAuthenticated) {
      return const <GtePrimaryDestination>[
        GtePrimaryDestination.home,
        GtePrimaryDestination.club,
        GtePrimaryDestination.market,
        GtePrimaryDestination.competitions,
        GtePrimaryDestination.community,
      ];
    }
    if (_isAdminSession) {
      return const <GtePrimaryDestination>[
        GtePrimaryDestination.home,
        GtePrimaryDestination.market,
        GtePrimaryDestination.competitions,
        GtePrimaryDestination.club,
        GtePrimaryDestination.wallet,
        GtePrimaryDestination.hub,
        GtePrimaryDestination.community,
      ];
    }
    if (_isCoinTraderSession) {
      return const <GtePrimaryDestination>[
        GtePrimaryDestination.home,
        GtePrimaryDestination.wallet,
        GtePrimaryDestination.market,
        GtePrimaryDestination.community,
      ];
    }
    if (_isCreatorSession) {
      return const <GtePrimaryDestination>[
        GtePrimaryDestination.home,
        GtePrimaryDestination.hub,
        GtePrimaryDestination.community,
        GtePrimaryDestination.market,
        GtePrimaryDestination.wallet,
      ];
    }
    if (_canonicalClubId()?.trim().isNotEmpty ?? false) {
      return const <GtePrimaryDestination>[
        GtePrimaryDestination.home,
        GtePrimaryDestination.club,
        GtePrimaryDestination.market,
        GtePrimaryDestination.competitions,
        GtePrimaryDestination.wallet,
        GtePrimaryDestination.hub,
        GtePrimaryDestination.community,
      ];
    }
    if (_isStaffSession) {
      return const <GtePrimaryDestination>[
        GtePrimaryDestination.home,
        GtePrimaryDestination.market,
        GtePrimaryDestination.club,
        GtePrimaryDestination.wallet,
        GtePrimaryDestination.community,
      ];
    }
    return const <GtePrimaryDestination>[
      GtePrimaryDestination.home,
      GtePrimaryDestination.market,
      GtePrimaryDestination.club,
      GtePrimaryDestination.competitions,
      GtePrimaryDestination.wallet,
      GtePrimaryDestination.community,
    ];
  }

  CompetitionController _buildCompetitionController() {
    return CompetitionController(
      api: CompetitionApi.standard(
        baseUrl: widget.apiBaseUrl,
        mode: _liveBackendMode,
        accessToken: widget.controller.accessToken,
      ),
      currentUserId: _competitionUserId,
      currentUserName: _competitionUserName,
    );
  }

  CreatorApplicationController _buildCreatorApplicationController() {
    return CreatorApplicationController(
      api: CreatorApplicationApi.standard(
        baseUrl: widget.apiBaseUrl,
        accessToken: widget.controller.accessToken,
        mode: _liveBackendMode,
        client: _createShellAuthedApi(),
      ),
    );
  }

  CreatorController _buildCreatorController() {
    return CreatorController(
      api: CreatorApi.standard(
        baseUrl: widget.apiBaseUrl,
        accessToken: widget.controller.session?.accessToken,
        mode: _liveBackendMode,
        client: _createShellAuthedApi(),
      ),
    );
  }

  ReferralController _buildReferralController() {
    return ReferralController(
      api: ReferralApi.standard(
        baseUrl: widget.apiBaseUrl,
        mode: _liveBackendMode,
        accessToken: widget.controller.accessToken,
        client: _createShellAuthedApi(),
      ),
    );
  }

  GteAuthedApi _createShellAuthedApi() {
    final GteNavigationDependencies? inherited = widget.navigationDependencies;
    return GteNavigationDependencies(
      apiBaseUrl: widget.apiBaseUrl,
      backendMode: _liveBackendMode,
      accessToken: widget.controller.accessToken,
      authSessionStore: inherited?.authSessionStore,
      fallbackAuthSessionStore: inherited?.fallbackAuthSessionStore,
      onAuthSessionChanged: inherited?.onAuthSessionChanged,
      deviceId: inherited?.deviceId,
      deviceIdProvider: inherited?.deviceIdProvider,
    ).createAuthedApi();
  }

  GteNavigationDependencies _navigationDependencies() {
    final GteNavigationDependencies? inherited = widget.navigationDependencies;
    return GteNavigationDependencies(
      apiBaseUrl: widget.apiBaseUrl,
      backendMode: _liveBackendMode,
      currentUserId: _competitionUserId,
      currentUserName: _competitionUserName,
      currentUserRole: widget.controller.session?.user.role,
      currentClubId: _canonicalClubId(),
      currentClubName: _canonicalClubName(),
      accessToken: widget.controller.accessToken,
      isAuthenticated: widget.controller.isAuthenticated,
      isCheckingCreatorAccess: _isCheckingCreatorAccess,
      hasApprovedCreatorAccess: _hasApprovedCreatorAccess,
      canHostCompetitions: _canHostCompetitions,
      onOpenLogin: (BuildContext _) => _openLogin(targetRoute: _route),
      onOpenCreatorAccessRequest:
          (BuildContext context) => _pushCreatorAccessRequest(context),
      currentUserIdProvider: _resolveCompetitionUserId,
      currentUserNameProvider: _resolveCompetitionUserName,
      currentUserRoleProvider: () => widget.controller.session?.user.role,
      currentClubIdProvider: _canonicalClubId,
      currentClubNameProvider: _canonicalClubName,
      accessTokenProvider: () => widget.controller.accessToken,
      isAuthenticatedProvider: () => widget.controller.isAuthenticated,
      isCheckingCreatorAccessProvider: () => _isCheckingCreatorAccess,
      hasApprovedCreatorAccessProvider: () => _hasApprovedCreatorAccess,
      canHostCompetitionsProvider: () => _canHostCompetitions,
      authSessionStore: inherited?.authSessionStore,
      fallbackAuthSessionStore: inherited?.fallbackAuthSessionStore,
      onAuthSessionChanged: inherited?.onAuthSessionChanged,
      deviceId: inherited?.deviceId,
      deviceIdProvider: inherited?.deviceIdProvider,
    );
  }

  Future<void> _pushCreatorAccessRequest(BuildContext context) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (BuildContext context) => CreatorAccessRequestScreen(
              exchangeController: widget.controller,
            ),
      ),
    );
  }

  Widget _buildScrollableShellStatePanel(Widget child) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: child,
    );
  }

  Widget _buildHubDestination() {
    if (!widget.controller.isAuthenticated) {
      return _buildScrollableShellStatePanel(
        GteStatePanel(
          eyebrow: 'HUB ACCESS',
          title: 'Sign in to open Creator Hub',
          message:
              'Creator Hub keeps invites, referral milestones, and community momentum in one live lane. Sign in to load the data behind it.',
          icon: Icons.groups_outlined,
          accentColor: const Color(0xFF5FE3A1),
          actionLabel: 'Sign in',
          onAction:
              () => _openLogin(targetRoute: const GteNavigationRoute.hub()),
        ),
      );
    }

    return GtexStudioHubScreenV2(
      key: const PageStorageKey<String>('studio-hub-v2'),
      referralController: _referralController,
      creatorController: _creatorController,
      isAuthenticated: widget.controller.isAuthenticated,
      hasApprovedCreatorAccess: _hasApprovedCreatorAccess,
      isReferralRuntimeAvailable: _isReferralRuntimeAvailable,
      onOpenLogin:
          () => _openLogin(targetRoute: const GteNavigationRoute.hub()),
      onOpenCreatorAccessRequest: () => _pushCreatorAccessRequest(context),
    );
  }

  Widget _buildCommunityDestination() {
    return CommunityScreen(
      key: const PageStorageKey<String>('community-screen'),
      baseUrl: widget.apiBaseUrl,
      backendMode: _liveBackendMode,
      accessToken: widget.controller.accessToken,
      api: CommunityApi.standard(
        baseUrl: widget.apiBaseUrl,
        accessToken: widget.controller.accessToken,
        mode: _liveBackendMode,
        client: _createShellAuthedApi(),
      ),
      isAuthenticated: widget.controller.isAuthenticated,
      currentClubId: _canonicalClubId(),
      currentClubName: _canonicalClubName(),
      onOpenLogin:
          () => _openLogin(targetRoute: const GteNavigationRoute.community()),
      onOpenFanWars: () => _openFeatureRoute(const FanWarsRouteData()),
    );
  }

  Widget _buildCurrentDestination() {
    switch (_route.primaryDestination) {
      case GtePrimaryDestination.home:
        return _buildHomeDestination();
      case GtePrimaryDestination.competitions:
        return _buildCompetitionsDestination();
      case GtePrimaryDestination.market:
        return _buildMarketDestination();
      case GtePrimaryDestination.hub:
        return _buildHubDestination();
      case GtePrimaryDestination.community:
        return _buildCommunityDestination();
      case GtePrimaryDestination.club:
        return _buildClubDestination();
      case GtePrimaryDestination.wallet:
        return _buildWalletDestination();
    }
  }

  Widget _buildCompetitionsDestination() {
    return GteCompetitionsHubScreenV2(
      key: const PageStorageKey<String>('competitions-hub-v2'),
      controller: _competitionController,
      currentDestination: _route.effectiveCompetitionDestination,
      onDestinationChanged: _openCompetitionDestination,
      isAuthenticated: widget.controller.isAuthenticated,
      isCheckingCreatorAccess: _isCheckingCreatorAccess,
      canHostCompetitions: _canHostCompetitions,
      onOpenLogin:
          () => _openLogin(
            targetRoute: GteNavigationRoute.competitions(
              destination: _route.effectiveCompetitionDestination,
            ),
          ),
      onOpenCreatorAccessRequest: () => _pushCreatorAccessRequest(context),
      navigationDependencies: _navigationDependencies(),
    );
  }

  Widget _buildMarketDestination() {
    return GteMarketPlayersScreenV2(
      key: const PageStorageKey<String>('market-screen'),
      controller: widget.controller,
      onOpenPlayer: _openPlayer,
      onOpenLogin:
          () => _openLogin(targetRoute: const GteNavigationRoute.market()),
      navigationDependencies: _navigationDependencies(),
    );
  }

  Widget _buildWalletDestination() {
    return GtexWalletOverviewScreenV2(
      key: const PageStorageKey<String>('wallet-overview-v2'),
      controller: widget.controller,
      baseUrl: widget.apiBaseUrl,
      backendMode: widget.backendMode,
      initialModule: _walletModuleForRoute(),
      onTopUp: _openWalletTopUp,
      onWithdraw: _openWalletWithdraw,
      onOpenLogin: () => _openLogin(targetRoute: _route),
      onOpenPlayer: _openPlayer,
      onModuleChanged: _openWalletModule,
      authedApi: _createShellAuthedApi(),
    );
  }

  GtexWalletDeskModule _walletModuleForRoute() {
    switch (_route.capitalDestination) {
      case GteCapitalDestination.orders:
        return GtexWalletDeskModule.orders;
      case GteCapitalDestination.holdings:
        return GtexWalletDeskModule.holdings;
      case GteCapitalDestination.coinTraders:
        return GtexWalletDeskModule.coinTraders;
      case GteCapitalDestination.traderDashboard:
        return GtexWalletDeskModule.traderDashboard;
      case GteCapitalDestination.wallet:
        return GtexWalletDeskModule.wallet;
    }
  }

  void _openWalletModule(GtexWalletDeskModule module) {
    switch (module) {
      case GtexWalletDeskModule.wallet:
        _setRoute(const GteNavigationRoute.wallet());
        return;
      case GtexWalletDeskModule.orders:
        _setRoute(
          const GteNavigationRoute.wallet(
            capitalDestination: GteCapitalDestination.orders,
          ),
        );
        return;
      case GtexWalletDeskModule.holdings:
        _setRoute(
          const GteNavigationRoute.wallet(
            capitalDestination: GteCapitalDestination.holdings,
          ),
        );
        return;
      case GtexWalletDeskModule.coinTraders:
        _setRoute(
          const GteNavigationRoute.wallet(
            capitalDestination: GteCapitalDestination.coinTraders,
          ),
        );
        return;
      case GtexWalletDeskModule.traderDashboard:
        _setRoute(
          const GteNavigationRoute.wallet(
            capitalDestination: GteCapitalDestination.traderDashboard,
          ),
        );
        return;
    }
  }

  void _openWalletTopUp() {
    if (!widget.controller.isAuthenticated) {
      _openLogin(targetRoute: const GteNavigationRoute.wallet());
      return;
    }
    Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (BuildContext context) =>
                GteFundWalletScreen(controller: widget.controller),
      ),
    );
  }

  void _openWalletWithdraw() {
    if (!widget.controller.isAuthenticated) {
      _openLogin(targetRoute: const GteNavigationRoute.wallet());
      return;
    }
    Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (BuildContext context) =>
                GteWithdrawalEligibilityScreen(controller: widget.controller),
      ),
    );
  }

  void _setRoute(GteNavigationRoute route) {
    final String? featureKey = GtexLaunchControlFeatureGate.featureKeyForPath(
      route.path,
    );
    if (featureKey != null && !widget.controller.isAdmin) {
      _setRouteAfterLaunchGate(route);
      return;
    }
    _commitRoute(route);
  }

  Future<void> _setRouteAfterLaunchGate(GteNavigationRoute route) async {
    final GtexFeatureGateDecision decision =
        await GtexLaunchControlFeatureGate.resolveRoutePath(
          route: route.path,
          baseUrl: widget.apiBaseUrl,
          backendMode: widget.backendMode,
          accessToken: widget.controller.accessToken,
          isAdmin: widget.controller.isAdmin,
        );
    if (!mounted) {
      return;
    }
    if (decision.blocked) {
      AppFeedback.showError(
        context,
        decision.message ??
            'This route is controlled by Launch Control and is not available right now.',
      );
      return;
    }
    _commitRoute(route);
  }

  void _commitRoute(GteNavigationRoute route) {
    setState(() {
      _route = route;
    });
    widget.onRouteChanged?.call(_route);
    _syncRouterPath(route);
    _scheduleStartupWork(force: true);
  }

  void _syncRouterPath(GteNavigationRoute route) {
    try {
      final GoRouter router = GoRouter.of(context);
      final String currentPath = router.routeInformationProvider.value.uri.path;
      if (currentPath != route.path) {
        router.go(route.path);
      }
    } catch (_) {
      // Some focused widget tests mount the shell without a GoRouter ancestor.
    }
  }

  void _startLiveRefreshLoop() {
    if (_isTestBinding) {
      return;
    }
    _liveRefreshTimer?.cancel();
    _liveRefreshTimer = Timer.periodic(const Duration(seconds: 24), (
      Timer timer,
    ) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      _runLiveRefreshCycle();
    });
  }

  Future<void> _runLiveRefreshCycle() async {
    switch (_route.primaryDestination) {
      case GtePrimaryDestination.home:
        {
          await widget.controller.bootstrap();
          return;
        }
      case GtePrimaryDestination.market:
        {
          await widget.controller.loadMarket(reset: false);
          return;
        }
      case GtePrimaryDestination.competitions:
        {
          await _competitionController.loadDiscovery();
          return;
        }
      case GtePrimaryDestination.club:
        {
          await widget.controller.refreshAccount();
          return;
        }
      case GtePrimaryDestination.hub:
      case GtePrimaryDestination.community:
        {
          if (widget.controller.isAuthenticated) {
            await Future.wait<void>(<Future<void>>[
              _creatorController.load(),
              _referralController.load(),
            ]);
          }
          return;
        }
      case GtePrimaryDestination.wallet:
        {
          if (widget.controller.isAuthenticated) {
            await widget.controller.refreshAccount();
          }
          return;
        }
    }
  }

  void _openPrimaryDestination(GtePrimaryDestination destination) {
    _setRoute(_route.withPrimaryDestination(destination));
  }

  Future<void> _openFeatureRoute(GteAppRouteData route) {
    return GteNavigationHelpers.pushRoute<void>(
      context,
      route: route,
      dependencies: _navigationDependencies(),
    );
  }

  void _openCompetitionDestination(CompetitionHubDestination destination) {
    _setRoute(_route.withCompetitionDestination(destination));
  }

  Future<bool> _openLogin({GteNavigationRoute? targetRoute}) async {
    final bool? signedIn = await Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder:
            (BuildContext context) =>
                GteLoginScreen(controller: widget.controller),
      ),
    );
    if (!mounted || signedIn != true) {
      return false;
    }
    if (targetRoute != null) {
      _setRoute(targetRoute);
    }
    return true;
  }

  void _scheduleStartupWork({bool force = false}) {
    if (_startupWorkScheduled && !force) {
      return;
    }
    _startupWorkScheduled = true;
    SchedulerBinding.instance.addPostFrameCallback((_) {
      _startupWorkScheduled = false;
      if (!mounted) {
        return;
      }
      widget.controller.bootstrap();
      _competitionController.bootstrap();
      _primeCreatorAccessState(force: true);
      _primeRouteData();
    });
  }

  void _primeRouteData() {
    if (_route.primaryDestination == GtePrimaryDestination.wallet &&
        widget.controller.isAuthenticated) {
      widget.controller.refreshAccount();
    }
  }

  void _openCoachMarket() {
    if (!widget.controller.isAuthenticated) {
      _openLogin(targetRoute: const GteNavigationRoute.market());
      return;
    }
    _setRoute(const GteNavigationRoute.market());
  }

  void _openAdminCommandCenter() {
    final session = widget.controller.session;
    if (session == null) {
      return;
    }
    Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (BuildContext context) => AdminCommandCenterScreen(
              baseUrl: widget.apiBaseUrl,
              accessToken: session.accessToken,
              backendMode: widget.backendMode,
            ),
      ),
    );
  }

  void _openNotifications() {
    Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (BuildContext context) =>
                GteNotificationsScreenV2(exchangeController: widget.controller),
      ),
    );
  }

  Future<void> _openGlobalSearch() {
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: GtexColors.panel,
      builder:
          (BuildContext context) => GtexGlobalSearchSheet(
            controller: GtexGlobalSearchController(
              api: GtexGlobalSearchApi.standard(
                baseUrl: widget.apiBaseUrl,
                accessToken: widget.controller.accessToken,
                mode: widget.backendMode,
              ),
              admin: _isAdminSession,
            ),
            onOpenRoute: _openGlobalSearchRoute,
          ),
    );
  }

  void _openGlobalSearchRoute(String route) {
    context.go(gtexCanonicalGlobalSearchRoute(route, isAdmin: _isAdminSession));
  }

  void _openProfileSettings() {
    Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (BuildContext context) =>
                GtexLiveProfileScreen(controller: widget.controller),
      ),
    );
  }

  Future<void> _openPlayer(String playerId) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (BuildContext context) => GteExchangePlayerDetailScreen(
              controller: widget.controller,
              playerId: playerId,
              onRequireLogin: () {
                _openLogin(targetRoute: _route);
              },
            ),
      ),
    );
  }

  Future<void> _openThemePicker(BuildContext context) {
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (BuildContext context) => const GteThemePickerSheet(),
    );
  }

  Widget _buildThemePickerAction(BuildContext context) {
    final String label = GteShellTheme.definitionOf(context).metadata.label;
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: IconButton(
        tooltip: 'Theme: $label',
        onPressed: () => _openThemePicker(context),
        icon: const Icon(Icons.palette_outlined),
      ),
    );
  }

  Widget _buildAmbientAction() {
    final AmbientAudioState? controller = widget.ambientAudioController;
    if (controller == null) {
      return const SizedBox.shrink();
    }
    return AmbientAudioToggleButton(controller: controller);
  }

  Widget _buildCapitalAction() {
    final bool isActive =
        _route.primaryDestination == GtePrimaryDestination.wallet;
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: IconButton(
        tooltip: 'Club funds',
        onPressed: () => _openPrimaryDestination(GtePrimaryDestination.wallet),
        icon: Icon(
          isActive
              ? GtePrimaryDestination.wallet.selectedIcon
              : GtePrimaryDestination.wallet.icon,
          color: isActive ? GtePrimaryDestination.wallet.accentColor : null,
        ),
      ),
    );
  }

  String _routeContextLine() {
    final String? clubName = _canonicalClubName()?.trim();
    if (clubName != null && clubName.isNotEmpty) {
      return clubName;
    }
    if (widget.controller.isAuthenticated) {
      return widget.controller.session?.user.username ?? 'Signed in';
    }
    return 'Preview mode';
  }

  GteSyncStatusCard _buildModeSyncCard(BuildContext context) {
    final Color accent = _routeAccentFor(context, _route.primaryDestination);
    switch (_route.primaryDestination) {
      case GtePrimaryDestination.competitions:
        return GteSyncStatusCard(
          title: 'Competitions',
          status:
              _competitionController.discoveryError == null
                  ? 'Fixtures, brackets, and competition updates are synced.'
                  : 'Competition feed degraded. Showing the latest available snapshot.',
          syncedAt: _competitionController.discoverySyncedAt,
          accent: accent,
          isRefreshing: _competitionController.isLoadingDiscovery,
          onRefresh: _competitionController.loadDiscovery,
        );
      case GtePrimaryDestination.market:
        return GteSyncStatusCard(
          title: 'Transfer Hub',
          status:
              widget.controller.marketError == null
                  ? 'Listings, prices, clubs, and negotiation context are ready.'
                  : 'Transfer board degraded. The last confirmed board is still visible.',
          syncedAt: widget.controller.marketSyncedAt,
          accent: accent,
          isRefreshing: widget.controller.isLoadingMarket,
          onRefresh: () => widget.controller.loadMarket(reset: true),
        );
      case GtePrimaryDestination.hub:
        final bool creatorHealthy = _creatorController.errorMessage == null;
        return GteSyncStatusCard(
          title: 'Community',
          status:
              creatorHealthy
                  ? _isReferralRuntimeAvailable
                      ? 'Creator tools, referral activity, and community signals are synced.'
                      : 'Creator tools are live. Referral rewards will appear here once that runtime is enabled.'
                  : 'Community feed degraded. Showing the latest available snapshot.',
          syncedAt: _creatorController.syncedAt,
          accent: accent,
          isRefreshing:
              _referralController.isLoading || _creatorController.isLoading,
          onRefresh:
              widget.controller.isAuthenticated
                  ? () {
                    _referralController.load();
                    _creatorController.load();
                  }
                  : null,
        );
      case GtePrimaryDestination.community:
        return GteSyncStatusCard(
          title: 'Community',
          status:
              widget.controller.isAuthenticated
                  ? 'Watchlists, live threads, direct messages, and creator-club follows are wired to live community endpoints.'
                  : 'Public live threads are visible. Sign in to manage watchlists, follows, and direct messages.',
          syncedAt: null,
          accent: accent,
          isRefreshing: false,
          onRefresh: null,
        );
      case GtePrimaryDestination.club:
        return GteSyncStatusCard(
          title: 'Club operations',
          status:
              'Club management opens here once this account owns or is linked to a club.',
          syncedAt: widget.controller.marketSyncedAt,
          accent: accent,
          isRefreshing: false,
          onRefresh: null,
        );
      case GtePrimaryDestination.wallet:
        return GteSyncStatusCard(
          title: 'Club funds',
          status:
              widget.controller.isAuthenticated
                  ? 'Balance, player holdings, and activity records are up to date.'
                  : 'Sign in to view funds, holdings, and account activity.',
          syncedAt:
              widget.controller.portfolioSyncedAt ??
              widget.controller.ordersSyncedAt,
          accent: accent,
          isRefreshing:
              widget.controller.isLoadingPortfolio ||
              widget.controller.isLoadingOrders,
          onRefresh:
              widget.controller.isAuthenticated
                  ? widget.controller.refreshAccount
                  : null,
        );
      case GtePrimaryDestination.home:
        return GteSyncStatusCard(
          title: 'Home sync',
          status:
              'Home keeps your club, matchday, scouting, and world routes aligned.',
          detail:
              'Runtime ${_runtimeModeLabel()} on ${_apiHostLabel()} - ${_runtimeAudienceLabel()}',
          syncedAt: widget.controller.marketSyncedAt,
          accent: accent,
          isRefreshing: widget.controller.isBootstrapping,
          onRefresh: widget.controller.bootstrap,
        );
    }
  }

  GteSessionIdentity _identity() {
    return GteSessionIdentity.fromExchangeController(widget.controller);
  }

  String _resolveCompetitionUserId() {
    return _identity().userId;
  }

  String? _resolveCompetitionUserName() {
    return _identity().userName;
  }

  String? _canonicalClubId() {
    return _identity().clubId;
  }

  String? _canonicalClubName() {
    return _identity().clubName;
  }

  String _apiHostLabel() {
    final Uri? uri = Uri.tryParse(widget.apiBaseUrl.trim());
    final String? host = uri?.host.trim();
    if (host != null && host.isNotEmpty) {
      return host;
    }
    final String raw = widget.apiBaseUrl.trim();
    if (raw.isEmpty) {
      return 'not configured';
    }
    return raw.replaceFirst(RegExp(r'^https?://'), '');
  }

  String _runtimeModeLabel() {
    switch (_liveBackendMode) {
      case GteBackendMode.live:
        return 'live';
      case GteBackendMode.fixture:
        return 'fixture';
      case GteBackendMode.liveThenFixture:
        return 'live';
    }
  }

  String _runtimeAudienceLabel() {
    final bool hasClubScope = (_canonicalClubId()?.trim().isNotEmpty ?? false);
    final String accessLabel =
        widget.controller.isAuthenticated
            ? 'signed-in access'
            : 'preview access';
    final String clubLabel =
        hasClubScope ? 'club scope ready' : 'club scope pending';
    return '$accessLabel, $clubLabel';
  }

  String _workspaceRoleLabel() {
    if (_isCoinTraderSession) {
      return 'Coin trader workspace';
    }
    if (_isStaffSession) {
      return 'Staff marketplace workspace';
    }
    final String rawRole = _sessionRole.replaceAll('_', ' ').trim();
    if (rawRole.isEmpty || rawRole == 'guest') {
      return 'Fan workspace';
    }
    return '${rawRole[0].toUpperCase()}${rawRole.substring(1)} workspace';
  }

  Future<void> _openCreateClubFlow() async {
    if (!widget.controller.isAuthenticated) {
      final bool signedIn = await _openLogin(
        targetRoute: const GteNavigationRoute.club(),
      );
      if (!signedIn || !mounted) {
        return;
      }
    }
    final String? accessToken = widget.controller.accessToken;
    if (accessToken == null || accessToken.trim().isEmpty) {
      return;
    }
    final GteCreatedClubProfile? created = await Navigator.of(
      context,
    ).push<GteCreatedClubProfile>(
      MaterialPageRoute<GteCreatedClubProfile>(
        builder:
            (BuildContext context) => CreateClubScreen(
              baseUrl: widget.apiBaseUrl,
              accessToken: accessToken,
              backendMode: widget.backendMode,
              onClubCreated: _adoptCreatedClub,
            ),
      ),
    );
    if (created != null) {
      _adoptCreatedClub(created);
    }
  }

  void _adoptCreatedClub(GteCreatedClubProfile club) {
    widget.controller.bindCurrentClub(
      clubId: club.id,
      clubName: club.clubName,
      clubSlug: club.slug,
    );
    _openPrimaryDestination(GtePrimaryDestination.club);
  }
}

class _GtexCommandHomeEntry extends StatelessWidget {
  const _GtexCommandHomeEntry({
    required this.isAuthenticated,
    required this.userLabel,
    required this.onSignIn,
    required this.onCreateClub,
    required this.onOpenMarket,
    required this.onOpenCompetitions,
    required this.onOpenWorld,
  });

  final bool isAuthenticated;
  final String userLabel;
  final VoidCallback onSignIn;
  final VoidCallback onCreateClub;
  final VoidCallback onOpenMarket;
  final VoidCallback onOpenCompetitions;
  final VoidCallback onOpenWorld;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool compact = constraints.maxWidth < 760;
        final double metricWidth = compact ? constraints.maxWidth : 210;
        return SingleChildScrollView(
          padding: EdgeInsets.fromLTRB(
            compact ? GtexSpacing.md : GtexSpacing.xl,
            GtexSpacing.lg,
            compact ? GtexSpacing.md : GtexSpacing.xl,
            120,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Container(
                width: double.infinity,
                padding: EdgeInsets.all(compact ? GtexSpacing.lg : 30),
                decoration: BoxDecoration(
                  gradient: GtexColors.panelGlow(accent: GtexColors.pitch),
                  borderRadius: BorderRadius.circular(GtexSpacing.radiusLg),
                  border: Border.all(
                    color: GtexColors.pitch.withValues(alpha: 0.34),
                  ),
                  boxShadow: <BoxShadow>[
                    GtexColors.glow(GtexColors.pitch, opacity: 0.14),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'THE GLOBAL FOOTBALL TALENT MARKETPLACE',
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(
                        color: GtexColors.pitch,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 0.8,
                      ),
                    ),
                    const SizedBox(height: GtexSpacing.sm),
                    Text(
                      isAuthenticated
                          ? 'Build your club command center'
                          : 'Enter the football operating system',
                      maxLines: compact ? 3 : 2,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.displaySmall?.copyWith(
                        color: GtexColors.text,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: GtexSpacing.sm),
                    ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 860),
                      child: Text(
                        isAuthenticated
                            ? '$userLabel, create your club to unlock squad ownership, transfer trading, finances, competitions, news, and regen world activity from one GTEX command surface.'
                            : 'Create and own clubs, discover real players, browse the transfer universe, rent national-team talent, follow tournaments, and watch the GTEX news world move around the market.',
                        style: Theme.of(
                          context,
                        ).textTheme.titleMedium?.copyWith(
                          color: GtexColors.textSecondary,
                          height: 1.42,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    const SizedBox(height: GtexSpacing.lg),
                    Wrap(
                      spacing: GtexSpacing.sm,
                      runSpacing: GtexSpacing.sm,
                      children: <Widget>[
                        if (!isAuthenticated)
                          GtexButton(
                            label: 'Sign in',
                            icon: Icons.login,
                            onPressed: onSignIn,
                          ),
                        GtexButton(
                          label:
                              isAuthenticated
                                  ? 'Create club'
                                  : 'Create or join club',
                          icon: Icons.shield_outlined,
                          variant:
                              isAuthenticated
                                  ? GtexButtonVariant.primary
                                  : GtexButtonVariant.secondary,
                          onPressed: onCreateClub,
                        ),
                        GtexButton(
                          label: 'Transfer Hub',
                          icon: Icons.storefront_outlined,
                          variant: GtexButtonVariant.secondary,
                          onPressed: onOpenMarket,
                        ),
                        GtexButton(
                          label: 'Matchday',
                          icon: Icons.emoji_events_outlined,
                          variant: GtexButtonVariant.ghost,
                          onPressed: onOpenCompetitions,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: GtexSpacing.lg),
              Wrap(
                spacing: GtexSpacing.md,
                runSpacing: GtexSpacing.md,
                children: <Widget>[
                  SizedBox(
                    width: metricWidth,
                    child: const GtexMetricTile(
                      label: 'Player universe',
                      value: '17K+',
                      helper: 'Tradeable real players',
                      icon: Icons.groups_2_outlined,
                      accent: GtexColors.pitch,
                    ),
                  ),
                  SizedBox(
                    width: metricWidth,
                    child: const GtexMetricTile(
                      label: 'Transfer route',
                      value: 'Live',
                      helper: 'Country to club browsing',
                      icon: Icons.account_tree_outlined,
                      accent: GtexColors.cyan,
                    ),
                  ),
                  SizedBox(
                    width: metricWidth,
                    child: const GtexMetricTile(
                      label: 'Club layer',
                      value: 'Owner',
                      helper: 'Squad, wallet, orders',
                      icon: Icons.shield_outlined,
                      accent: GtexColors.gold,
                    ),
                  ),
                  SizedBox(
                    width: metricWidth,
                    child: const GtexMetricTile(
                      label: 'World state',
                      value: 'Active',
                      helper: 'Regens, news, awards',
                      icon: Icons.public_outlined,
                      accent: GtexColors.mint,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: GtexSpacing.lg),
              Wrap(
                spacing: GtexSpacing.md,
                runSpacing: GtexSpacing.md,
                children: <Widget>[
                  _HomeLanePanel(
                    width: compact ? constraints.maxWidth : 360,
                    title: 'Transfer room',
                    subtitle:
                        'Browse country, league, division, club, then shortlist real football assets.',
                    icon: Icons.compare_arrows_outlined,
                    accent: GtexColors.pitch,
                    onTap: onOpenMarket,
                  ),
                  _HomeLanePanel(
                    width: compact ? constraints.maxWidth : 360,
                    title: 'Club ownership',
                    subtitle:
                        'Create a badge, build a squad, manage finances, and enter competitions.',
                    icon: Icons.stadium_outlined,
                    accent: GtexColors.gold,
                    onTap: onCreateClub,
                  ),
                  _HomeLanePanel(
                    width: compact ? constraints.maxWidth : 360,
                    title: 'GTEX world',
                    subtitle:
                        'Follow regens, creator activity, football news, awards, and community signals.',
                    icon: Icons.auto_awesome_outlined,
                    accent: GtexColors.mint,
                    onTap: onOpenWorld,
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }
}

class _GtexUserWorkspaceHomeEntry extends StatelessWidget {
  const _GtexUserWorkspaceHomeEntry({
    required this.userLabel,
    required this.roleLabel,
    required this.onOpenMarket,
    required this.onOpenCompetitions,
    required this.onOpenWallet,
    required this.onOpenCommunity,
    required this.onOpenProfile,
    required this.onCreateClub,
  });

  final String userLabel;
  final String roleLabel;
  final VoidCallback onOpenMarket;
  final VoidCallback onOpenCompetitions;
  final VoidCallback onOpenWallet;
  final VoidCallback onOpenCommunity;
  final VoidCallback onOpenProfile;
  final VoidCallback onCreateClub;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool compact = constraints.maxWidth < 760;
        final double laneWidth = compact ? constraints.maxWidth : 360;
        return SingleChildScrollView(
          padding: EdgeInsets.fromLTRB(
            compact ? GtexSpacing.md : GtexSpacing.xl,
            GtexSpacing.lg,
            compact ? GtexSpacing.md : GtexSpacing.xl,
            120,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              GtexPanel(
                title: 'Build your club command center',
                subtitle: '$userLabel - $roleLabel',
                accent: GtexColors.pitch,
                trailing: const Icon(
                  Icons.account_circle_outlined,
                  color: GtexColors.pitch,
                ),
                child: Wrap(
                  spacing: GtexSpacing.sm,
                  runSpacing: GtexSpacing.sm,
                  children: <Widget>[
                    GtexButton(
                      label: 'Wallet readiness',
                      icon: Icons.account_balance_wallet_outlined,
                      onPressed: onOpenWallet,
                    ),
                    GtexButton(
                      label: 'Transfer Hub',
                      icon: Icons.storefront_outlined,
                      variant: GtexButtonVariant.secondary,
                      onPressed: onOpenMarket,
                    ),
                    GtexButton(
                      label: 'Create club',
                      icon: Icons.shield_outlined,
                      variant: GtexButtonVariant.secondary,
                      onPressed: onCreateClub,
                    ),
                    GtexButton(
                      label: 'Profile',
                      icon: Icons.manage_accounts_outlined,
                      variant: GtexButtonVariant.ghost,
                      onPressed: onOpenProfile,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: GtexSpacing.lg),
              Wrap(
                spacing: GtexSpacing.md,
                runSpacing: GtexSpacing.md,
                children: <Widget>[
                  _HomeLanePanel(
                    width: laneWidth,
                    title: 'Market',
                    subtitle:
                        'Browse players, coin traders, transfer activity and orders.',
                    icon: Icons.storefront_outlined,
                    accent: GtexColors.pitch,
                    onTap: onOpenMarket,
                  ),
                  _HomeLanePanel(
                    width: laneWidth,
                    title: 'Competitions',
                    subtitle:
                        'Join matchday, follow brackets, and host eligible tournaments.',
                    icon: Icons.emoji_events_outlined,
                    accent: GtexColors.cyan,
                    onTap: onOpenCompetitions,
                  ),
                  _HomeLanePanel(
                    width: laneWidth,
                    title: 'Community',
                    subtitle:
                        'Follow clubs, fan wars, creator activity, and social signals.',
                    icon: Icons.forum_outlined,
                    accent: GtexColors.mint,
                    onTap: onOpenCommunity,
                  ),
                  _HomeLanePanel(
                    width: laneWidth,
                    title: 'Create a club',
                    subtitle:
                        'Start the club owner loop when you are ready to build.',
                    icon: Icons.shield_outlined,
                    accent: GtePrimaryDestination.club.accentColor,
                    onTap: onCreateClub,
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }
}

class _HomeLanePanel extends StatelessWidget {
  const _HomeLanePanel({
    required this.width,
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.accent,
    required this.onTap,
  });

  final double width;
  final String title;
  final String subtitle;
  final IconData icon;
  final Color accent;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: width,
      child: GtexPanel(
        title: title,
        subtitle: subtitle,
        accent: accent,
        onTap: onTap,
        trailing: Icon(icon, color: accent),
        child: Row(
          children: <Widget>[
            Text(
              'Open lane',
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                color: accent,
                fontWeight: FontWeight.w900,
              ),
            ),
            const Spacer(),
            Icon(Icons.arrow_forward, color: accent, size: 18),
          ],
        ),
      ),
    );
  }
}
