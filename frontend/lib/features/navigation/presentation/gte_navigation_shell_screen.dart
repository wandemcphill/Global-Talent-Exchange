import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gte_frontend/controllers/creator_application_controller.dart';
import 'package:gte_frontend/controllers/creator_controller.dart';
import 'package:gte_frontend/features/compete/providers/competition_controller.dart';
import 'package:gte_frontend/controllers/referral_controller.dart';
import 'package:gte_frontend/core/gte_session_identity.dart';
import 'package:gte_frontend/data/club_creation_api.dart';
import 'package:gte_frontend/features/compete/repositories/competition_api.dart';
import 'package:gte_frontend/data/creator_application_api.dart';
import 'package:gte_frontend/data/creator_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/referral_api.dart';
import 'package:gte_frontend/features/compete/presentation/gte_compete_bracket_screen.dart';
import 'package:gte_frontend/features/compete/domain/competition_hub_destination.dart';
import 'package:gte_frontend/features/club_hub/presentation/club_hub_screen.dart';
import 'package:gte_frontend/features/app_routes/gte_navigation_helpers.dart';
import 'package:gte_frontend/features/app_routes/gte_route_data.dart';
import 'package:gte_frontend/features/home_dashboard/home_dashboard_screen.dart';
import 'package:gte_frontend/features/navigation/routing/gte_navigation_route.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/features/shell/gtex_shell_primitives.dart';
import 'package:gte_frontend/features/shared/presentation/gte_no_club_onboarding_view.dart';
import 'package:gte_frontend/features/social/social_screen.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/gte_exchange_player_detail_screen.dart';
import 'package:gte_frontend/screens/gte_login_screen.dart';
import 'package:gte_frontend/screens/gte_market_players_screen.dart';
import 'package:gte_frontend/screens/gte_portfolio_screen.dart';
import 'package:gte_frontend/screens/creators/creator_access_request_screen.dart';
import 'package:gte_frontend/screens/clubs/create_club_screen.dart';
import 'package:gte_frontend/screens/referrals/referral_hub_screen.dart';
import 'package:gte_frontend/screens/admin/admin_command_center_screen.dart';
import 'package:gte_frontend/theme/gte_theme_picker_sheet.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_sync_status_card.dart';

class GteNavigationShellScreen extends StatefulWidget {
  const GteNavigationShellScreen({
    super.key,
    required this.controller,
    required this.apiBaseUrl,
    required this.backendMode,
    this.initialRoute = const GteNavigationRoute.home(),
    this.onRouteChanged,
  });

  factory GteNavigationShellScreen.fromPath({
    Key? key,
    required GteExchangeController controller,
    required String apiBaseUrl,
    required GteBackendMode backendMode,
    required String initialPath,
    ValueChanged<GteNavigationRoute>? onRouteChanged,
  }) {
    return GteNavigationShellScreen(
      key: key,
      controller: controller,
      apiBaseUrl: apiBaseUrl,
      backendMode: backendMode,
      initialRoute: GteNavigationRoute.parse(initialPath),
      onRouteChanged: onRouteChanged,
    );
  }

  final GteExchangeController controller;
  final String apiBaseUrl;
  final GteBackendMode backendMode;
  final GteNavigationRoute initialRoute;
  final ValueChanged<GteNavigationRoute>? onRouteChanged;

  @override
  State<GteNavigationShellScreen> createState() =>
      _GteNavigationShellScreenState();
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
  ProviderContainer? _ownedContainer;

  @override
  void dispose() {
    _ownedContainer?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    try {
      ProviderScope.containerOf(context, listen: false);
      _ownedContainer?.dispose();
      _ownedContainer = null;
      return widget.child;
    } on StateError {
      final ProviderContainer container =
          _ownedContainer ??= ProviderContainer();
      return UncontrolledProviderScope(
        container: container,
        child: widget.child,
      );
    }
  }
}

Color _routeAccentFor(BuildContext context, GtePrimaryDestination destination) {
  final tokens = GteShellTheme.tokensOf(context);
  switch (destination) {
    case GtePrimaryDestination.home:
      return tokens.accent;
    case GtePrimaryDestination.market:
      return tokens.accentClub;
    case GtePrimaryDestination.competitions:
      return tokens.accentCapital;
    case GtePrimaryDestination.hub:
      return const Color(0xFFB26DFF);
    case GtePrimaryDestination.community:
      return tokens.accentCommunity;
    case GtePrimaryDestination.club:
      return tokens.accentArena;
    case GtePrimaryDestination.wallet:
      return tokens.accentCapital;
    case GtePrimaryDestination.admin:
      return tokens.accentAdmin;
  }
}

const List<GtePrimaryDestination> _canonicalPrimaryDestinations =
    <GtePrimaryDestination>[
      GtePrimaryDestination.home,
      GtePrimaryDestination.market,
      GtePrimaryDestination.club,
      GtePrimaryDestination.competitions,
      GtePrimaryDestination.wallet,
      GtePrimaryDestination.community,
      GtePrimaryDestination.hub,
      GtePrimaryDestination.admin,
    ];

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
    final Size viewportSize = MediaQuery.sizeOf(context);
    final bool showShellStatusCard =
        viewportSize.width >= 760 && viewportSize.height >= 720;
    return _NavigationProviderScopeBoundary(
      child: Container(
        decoration: gteBackdropDecoration(),
        child: AnimatedBuilder(
          animation: widget.controller,
          builder: (BuildContext context, Widget? child) {
            return GtexOperatingShell(
              destinations: _shellDestinations(),
              activeDestinationId: _route.primaryDestination.pathSegment,
              onDestinationSelected: _openDestinationById,
              title: _routeTitle(),
              contextLine: _routeContextLine(),
              tickerItems: _shellTickerItems(),
              contextItems: _shellContextItems(),
              commandActions: _shellCommandActions(),
              walletBalance: widget.controller.walletDisplay?.availableBalance,
              walletCurrency: widget.controller.walletDisplay?.currency.name,
              walletIsLoading: widget.controller.isLoadingPortfolio,
              walletIsBlocked: widget.controller.portfolioError != null,
              roleLabel: _roleLabel(),
              clubLabel: _canonicalClubName() ?? 'No active club',
              connectionLabel: _shellConnectionLabel(),
              connectionState: _shellConnectionState(),
              isSyncing: _isShellSyncing,
              notificationCount: _shellAttentionCount(),
              onOpenWallet:
                  () => _openPrimaryDestination(GtePrimaryDestination.wallet),
              onToggleTheme: () => _openThemePicker(context),
              onQuickAction: _openQuickAction,
              onNotifications:
                  () =>
                      _openPrimaryDestination(GtePrimaryDestination.community),
              onRoleSwitcher:
                  () => _openPrimaryDestination(GtePrimaryDestination.home),
              onClubSelector:
                  () => _openPrimaryDestination(GtePrimaryDestination.club),
              body: _buildShellBody(showShellStatusCard),
            );
          },
        ),
      ),
    );
  }

  Widget _buildShellBody(bool showShellStatusCard) {
    if (widget.controller.isBootstrapping &&
        widget.controller.players.isEmpty) {
      return const GtexAsyncSurface(
        state: GtexSurfaceState.loading,
        eyebrow: 'BOOTSTRAP',
        title: 'Loading GTEX operating shell',
        message:
            'The shell is syncing session, market, club, and wallet state.',
        child: SizedBox.shrink(),
      );
    }
    return Column(
      children: <Widget>[
        if (showShellStatusCard)
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 8),
            child: _buildModeSyncCard(context),
          ),
        Expanded(
          child: PageStorage(
            bucket: _pageStorageBucket,
            child: KeyedSubtree(
              key: ValueKey<String>('shell-${_route.primaryDestination.name}'),
              child: _buildCurrentDestination(),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildClubDestination() {
    if (!_canUseClubOperations) {
      return _buildAccountLaneBlockedPanel(
        eyebrow: 'CLUB',
        title: 'Club operations belong to Football User accounts',
        message:
            'Creator and Coin Trader accounts cannot create clubs, manage squads, operate academies, or enter club operations from this lane.',
        icon: Icons.shield_outlined,
        actionLabel: 'Open Home',
        onAction: () => _openPrimaryDestination(GtePrimaryDestination.home),
      );
    }
    final String? canonicalClubId = _canonicalClubId()?.trim();
    if (canonicalClubId == null || canonicalClubId.isEmpty) {
      return GteNoClubOnboardingView(
        isAuthenticated: widget.controller.isAuthenticated,
        onCreateClub:
            widget.controller.isAuthenticated
                ? _openCreateClubFlow
                : () =>
                    _openLogin(targetRoute: const GteNavigationRoute.club()),
        onBrowseClubMarket:
            () => _openFeatureRoute(const ClubSaleMarketListingsRouteData()),
        onExploreArena:
            () => _openPrimaryDestination(GtePrimaryDestination.competitions),
        onOpenMatchday: _openNoClubMatchdayHub,
        onOpenPlayerUniverse:
            () => _openFeatureRoute(const PlayerCardsBrowseRouteData()),
        onOpenWorld: () => _openFeatureRoute(const WorldOverviewRouteData()),
        onOpenWallet:
            () => _openPrimaryDestination(GtePrimaryDestination.wallet),
      );
    }
    return ClubHubScreen(
      key: const PageStorageKey<String>('club-hub-screen'),
      clubId: canonicalClubId,
      clubName: _canonicalClubName(),
      baseUrl: widget.apiBaseUrl,
      backendMode: widget.backendMode,
      isAuthenticated: widget.controller.isAuthenticated,
      onOpenLogin:
          () => _openLogin(targetRoute: const GteNavigationRoute.club()),
      navigationDependencies: _navigationDependencies(),
    );
  }

  Widget _buildHomeDestination() {
    return HomeDashboardScreen(
      key: const PageStorageKey<String>('home-dashboard'),
      exchangeController: widget.controller,
      apiBaseUrl: widget.apiBaseUrl,
      backendMode: _liveBackendMode,
      onOpenLogin:
          () => _openLogin(targetRoute: const GteNavigationRoute.home()),
      isCheckingCreatorAccess: _isCheckingCreatorAccess,
      canHostCompetitions: _canHostCompetitions,
      clubId: _canonicalClubId(),
      clubName: _canonicalClubName(),
      onOpenClubTab: () => _openPrimaryDestination(GtePrimaryDestination.club),
      onOpenCompetitionsTab:
          () => _openPrimaryDestination(GtePrimaryDestination.competitions),
      onOpenMarketTab:
          () => _openPrimaryDestination(GtePrimaryDestination.market),
      onOpenHubTab: () => _openPrimaryDestination(GtePrimaryDestination.hub),
      onOpenWalletTab:
          () => _openPrimaryDestination(GtePrimaryDestination.wallet),
      onOpenClubSubtab: null,
      onOpenCreatorAccessRequest: () => _pushCreatorAccessRequest(context),
      navigationDependencies: _navigationDependencies(),
    );
  }

  void _handleExchangeControllerChanged() {
    final GtePrimaryDestination resolvedLane = _resolvePrimaryLane(
      _route.primaryDestination,
    );
    if (resolvedLane != _route.primaryDestination) {
      _route = _route.withPrimaryDestination(resolvedLane);
      widget.onRouteChanged?.call(_route);
      if (mounted) {
        setState(() {});
      }
    }
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
    return widget.controller.isAuthenticated && _canUseClubCompetitions;
  }

  bool get _isReferralRuntimeAvailable {
    return widget.backendMode == GteBackendMode.fixture ||
        _referralController.hub != null;
  }

  GteBackendMode get _liveBackendMode => widget.backendMode;

  bool get _isAdminSession {
    final String role =
        widget.controller.session?.user.role.trim().toLowerCase() ?? '';
    return <String>{
      'admin',
      'super_admin',
      'god_mode',
      'scoped_admin',
    }.contains(role);
  }

  String get _accountType {
    return widget.controller.session?.user.accountType.trim().toLowerCase() ??
        'user';
  }

  bool get _isCreatorAccount => _accountType == 'creator';

  bool get _isTraderAccount => _accountType == 'coin_trader';

  bool get _isFootballAccount =>
      !_isCreatorAccount && !_isTraderAccount || _isAdminSession;

  bool get _canUseClubOperations => _isFootballAccount;

  bool get _canUseFootballMarket => _isFootballAccount;

  bool get _canUseClubCompetitions => _isFootballAccount;

  bool get _showWalletDestination => true;

  List<GtePrimaryDestination> get _visiblePrimaryDestinations {
    return _canonicalPrimaryDestinations;
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
      ),
    );
  }

  CreatorController _buildCreatorController() {
    return CreatorController(
      api: CreatorApi.standard(
        baseUrl: widget.apiBaseUrl,
        accessToken: widget.controller.session?.accessToken,
        mode: _liveBackendMode,
      ),
    );
  }

  ReferralController _buildReferralController() {
    return ReferralController(
      api: ReferralApi.standard(
        baseUrl: widget.apiBaseUrl,
        mode: _liveBackendMode,
      ),
    );
  }

  GteNavigationDependencies _navigationDependencies() {
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
      onRegenCreationSettled: widget.controller.refreshAccount,
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

  Widget _buildAccountLaneBlockedPanel({
    required String eyebrow,
    required String title,
    required String message,
    required IconData icon,
    required String actionLabel,
    required VoidCallback onAction,
  }) {
    return _buildScrollableShellStatePanel(
      GteStatePanel(
        eyebrow: eyebrow,
        title: title,
        message: message,
        icon: icon,
        accentColor: _routeAccentFor(context, GtePrimaryDestination.home),
        actionLabel: actionLabel,
        onAction: onAction,
      ),
    );
  }

  List<GtexShellDestination> _shellDestinations() {
    return _visiblePrimaryDestinations
        .map(
          (GtePrimaryDestination destination) => GtexShellDestination(
            id: destination.pathSegment,
            label: destination.label,
            icon: destination.icon,
            selectedIcon: destination.selectedIcon,
            tone: _routeAccentFor(context, destination),
          ),
        )
        .toList(growable: false);
  }

  void _openDestinationById(String destinationId) {
    for (final GtePrimaryDestination destination
        in _visiblePrimaryDestinations) {
      if (destination.pathSegment == destinationId) {
        _openPrimaryDestination(destination);
        return;
      }
    }
    _openPrimaryDestination(GtePrimaryDestination.home);
  }

  List<GtexCommandAction> _shellCommandActions() {
    return <GtexCommandAction>[
      for (final GtePrimaryDestination destination
          in _visiblePrimaryDestinations)
        GtexCommandAction(
          id: destination.pathSegment,
          label: 'Open ${destination.label}',
          description: 'Switch to ${destination.label} operations',
          icon: destination.icon,
          onSelected: () => _openPrimaryDestination(destination),
        ),
      GtexCommandAction(
        id: 'theme',
        label: 'Theme',
        description: 'Open shell theme controls',
        icon: Icons.contrast_rounded,
        onSelected: () => _openThemePicker(context),
      ),
      if (widget.controller.isAuthenticated)
        GtexCommandAction(
          id: 'sign-out',
          label: 'Sign out',
          description: 'End this GTEX session',
          icon: Icons.logout_rounded,
          onSelected: () async {
            await widget.controller.signOut();
            if (!mounted) {
              return;
            }
            _setRoute(const GteNavigationRoute.home());
          },
        )
      else
        GtexCommandAction(
          id: 'sign-in',
          label: 'Sign in',
          description: 'Open account login',
          icon: Icons.login_rounded,
          onSelected: _openLogin,
        ),
    ];
  }

  List<String> _shellTickerItems() {
    final List<String> items = <String>[
      if (widget.controller.marketSyncedAt != null)
        'Market synced ${_timeLabel(widget.controller.marketSyncedAt!)}',
      if (_competitionController.discoverySyncedAt != null)
        'Compete synced ${_timeLabel(_competitionController.discoverySyncedAt!)}',
      if (widget.controller.walletDisplay != null) 'Wallet confirmed',
      if (_canonicalClubName()?.trim().isNotEmpty ?? false)
        'Active club ${_canonicalClubName()}',
      if (widget.controller.marketError != null) 'Market degraded',
      if (_competitionController.discoveryError != null)
        'Competition feed degraded',
      if (widget.controller.portfolioError != null) 'Capital feed degraded',
    ];
    if (items.isEmpty) {
      items.add(
        widget.controller.isAuthenticated
            ? 'Session pending sync'
            : 'Guest preview',
      );
    }
    return items;
  }

  List<GtexContextRailItem> _shellContextItems() {
    return <GtexContextRailItem>[
      GtexContextRailItem(
        id: 'module',
        eyebrow: _route.primaryDestination.label,
        title: _routeTitle(),
        detail: _modeStateDetail(),
        state: _moduleSurfaceState(),
        icon: _route.primaryDestination.icon,
      ),
      GtexContextRailItem(
        id: 'club',
        eyebrow: 'Club',
        title: _canonicalClubName() ?? 'Club scope pending',
        detail:
            _canonicalClubId()?.trim().isNotEmpty == true
                ? 'Club identity is attached to this session.'
                : 'Create or select a club to unlock club operations.',
        state:
            _canonicalClubId()?.trim().isNotEmpty == true
                ? GtexSurfaceState.confirmed
                : GtexSurfaceState.blocked,
        icon: Icons.shield_outlined,
        onTap: () => _openPrimaryDestination(GtePrimaryDestination.club),
      ),
      GtexContextRailItem(
        id: 'capital',
        eyebrow: 'Capital',
        title:
            widget.controller.walletDisplay == null
                ? 'Wallet pending'
                : '${widget.controller.walletDisplay!.currencyCode} ${widget.controller.walletDisplay!.availableBalance.toStringAsFixed(2)} available',
        detail:
            widget.controller.portfolioError == null
                ? 'KoraPay and manual bank transfer are the active payment rails.'
                : 'Capital surface is degraded. Confirmed records remain visible.',
        state:
            widget.controller.portfolioError != null
                ? GtexSurfaceState.degraded
                : widget.controller.walletDisplay == null
                ? GtexSurfaceState.empty
                : GtexSurfaceState.confirmed,
        icon: Icons.account_balance_wallet_outlined,
        onTap: () => _openPrimaryDestination(GtePrimaryDestination.wallet),
      ),
    ];
  }

  bool get _isShellSyncing {
    return widget.controller.isBootstrapping ||
        widget.controller.isLoadingMarket ||
        widget.controller.isLoadingPortfolio ||
        widget.controller.isLoadingOrders ||
        _competitionController.isLoadingDiscovery ||
        _creatorController.isLoading ||
        _referralController.isLoading;
  }

  int _shellAttentionCount() {
    int count = 0;
    if (widget.controller.marketError != null) {
      count += 1;
    }
    if (_competitionController.discoveryError != null) {
      count += 1;
    }
    if (widget.controller.portfolioError != null) {
      count += 1;
    }
    if (widget.controller.ordersError != null) {
      count += 1;
    }
    return count;
  }

  GtexSurfaceState _shellConnectionState() {
    if (_isShellSyncing) {
      return GtexSurfaceState.syncing;
    }
    if (_shellAttentionCount() > 0) {
      return GtexSurfaceState.degraded;
    }
    return GtexSurfaceState.confirmed;
  }

  String _shellConnectionLabel() {
    switch (_shellConnectionState()) {
      case GtexSurfaceState.syncing:
      case GtexSurfaceState.loading:
        return 'Syncing';
      case GtexSurfaceState.degraded:
        return 'Degraded';
      case GtexSurfaceState.confirmed:
        return 'Live';
      case GtexSurfaceState.reconnecting:
        return 'Reconnecting';
      case GtexSurfaceState.empty:
        return 'Empty';
      case GtexSurfaceState.blocked:
        return 'Blocked';
      case GtexSurfaceState.pending:
        return 'Pending';
      case GtexSurfaceState.error:
        return 'Error';
    }
  }

  GtexSurfaceState _moduleSurfaceState() {
    switch (_route.primaryDestination) {
      case GtePrimaryDestination.market:
        if (widget.controller.marketError != null) {
          return GtexSurfaceState.degraded;
        }
        return widget.controller.isLoadingMarket
            ? GtexSurfaceState.syncing
            : GtexSurfaceState.confirmed;
      case GtePrimaryDestination.competitions:
        if (_competitionController.discoveryError != null) {
          return GtexSurfaceState.degraded;
        }
        return _competitionController.isLoadingDiscovery
            ? GtexSurfaceState.syncing
            : GtexSurfaceState.confirmed;
      case GtePrimaryDestination.wallet:
        if (widget.controller.portfolioError != null) {
          return GtexSurfaceState.degraded;
        }
        return widget.controller.isLoadingPortfolio
            ? GtexSurfaceState.syncing
            : GtexSurfaceState.confirmed;
      case GtePrimaryDestination.admin:
        return _isAdminSession
            ? GtexSurfaceState.confirmed
            : GtexSurfaceState.blocked;
      case GtePrimaryDestination.club:
        return _canonicalClubId()?.trim().isNotEmpty == true
            ? GtexSurfaceState.confirmed
            : GtexSurfaceState.blocked;
      case GtePrimaryDestination.home:
      case GtePrimaryDestination.hub:
      case GtePrimaryDestination.community:
        return _isShellSyncing
            ? GtexSurfaceState.syncing
            : GtexSurfaceState.confirmed;
    }
  }

  String _modeStateDetail() {
    switch (_moduleSurfaceState()) {
      case GtexSurfaceState.syncing:
      case GtexSurfaceState.loading:
        return 'This module is reconciling with live backend state.';
      case GtexSurfaceState.degraded:
        return 'Latest confirmed data remains visible while the feed recovers.';
      case GtexSurfaceState.blocked:
        return 'This module requires an eligible role, account, or club scope.';
      case GtexSurfaceState.empty:
        return 'No confirmed records are available for this module yet.';
      case GtexSurfaceState.pending:
        return 'This module is waiting for the next backend confirmation.';
      case GtexSurfaceState.reconnecting:
        return 'Realtime activity is reconnecting.';
      case GtexSurfaceState.confirmed:
        return 'This module is ready for operational decisions.';
      case GtexSurfaceState.error:
        return 'This module could not load from GTEX services.';
    }
  }

  String _roleLabel() {
    if (!widget.controller.isAuthenticated) {
      return 'Guest';
    }
    final String accountType = _accountType.replaceAll('_', ' ');
    if (_isAdminSession) {
      return 'Admin';
    }
    if (accountType.trim().isEmpty || accountType == 'user') {
      return 'Fan';
    }
    return accountType
        .split(' ')
        .where((String part) => part.isNotEmpty)
        .map((String part) => '${part[0].toUpperCase()}${part.substring(1)}')
        .join(' ');
  }

  String _timeLabel(DateTime value) {
    final Duration delta = DateTime.now().difference(value);
    if (delta.inSeconds < 60) {
      return 'now';
    }
    if (delta.inMinutes < 60) {
      return '${delta.inMinutes}m ago';
    }
    if (delta.inHours < 24) {
      return '${delta.inHours}h ago';
    }
    return '${delta.inDays}d ago';
  }

  void _openQuickAction() {
    if (!widget.controller.isAuthenticated) {
      _openLogin(targetRoute: _route);
      return;
    }
    if (_route.primaryDestination == GtePrimaryDestination.admin &&
        _isAdminSession) {
      _openAdminCommandCenter();
      return;
    }
    if (_route.primaryDestination == GtePrimaryDestination.club) {
      _openCreateClubFlow();
      return;
    }
    _openFeatureRoute(const PlayerCardsBrowseRouteData());
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

    return ReferralHubScreen(
      key: const PageStorageKey<String>('hub-screen'),
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
      api: null,
      baseUrl: widget.apiBaseUrl,
      backendMode: _liveBackendMode,
      accessToken: widget.controller.accessToken,
      isAuthenticated: widget.controller.isAuthenticated,
      currentClubId: _canonicalClubId(),
      currentClubName: _canonicalClubName(),
      onOpenLogin:
          () => _openLogin(targetRoute: const GteNavigationRoute.community()),
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
      case GtePrimaryDestination.admin:
        return _buildAdminDestination();
    }
  }

  Widget _buildAdminDestination() {
    final String? accessToken = widget.controller.accessToken;
    if (!_isAdminSession || accessToken == null || accessToken.trim().isEmpty) {
      return _buildAccountLaneBlockedPanel(
        eyebrow: 'ADMIN',
        title: 'Admin command requires scoped access',
        message:
            'Treasury, payment review, disputes, fraud alerts, moderation, and settlements require an eligible admin session.',
        icon: Icons.admin_panel_settings_outlined,
        actionLabel: 'Open World',
        onAction: () => _openPrimaryDestination(GtePrimaryDestination.home),
      );
    }
    return AdminCommandCenterScreen(
      key: const PageStorageKey<String>('admin-command-center'),
      baseUrl: widget.apiBaseUrl,
      accessToken: accessToken,
      backendMode: widget.backendMode,
    );
  }

  Widget _buildCompetitionsDestination() {
    if (!_canUseClubCompetitions) {
      return _buildAccountLaneBlockedPanel(
        eyebrow: 'MATCHDAY',
        title: 'Club tournaments require a Football User account',
        message:
            'Creator and Coin Trader accounts cannot host, join, or manage tournaments as clubs from this lane.',
        icon: Icons.play_circle_outline,
        actionLabel: 'Open Home',
        onAction: () => _openPrimaryDestination(GtePrimaryDestination.home),
      );
    }
    return GteCompeteBracketScreen(
      key: const PageStorageKey<String>('compete-bracket-screen'),
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

  void _openNoClubMatchdayHub() {
    _openFeatureRoute(const LiveMatchHubRouteData());
  }

  Widget _buildMarketDestination() {
    if (!_canUseFootballMarket) {
      return _buildAccountLaneBlockedPanel(
        eyebrow: 'PLAYER MARKET',
        title: 'Player trading is a Football User lane',
        message:
            'Creators and Coin Traders cannot buy or sell football players. Coin trading lives in the dedicated Trader dashboard.',
        icon: Icons.storefront_outlined,
        actionLabel: 'Open Home',
        onAction: () => _openPrimaryDestination(GtePrimaryDestination.home),
      );
    }
    return GteMarketPlayersScreen(
      key: const PageStorageKey<String>('market-screen'),
      controller: widget.controller,
      onOpenPlayer: _openPlayer,
      onOpenLogin:
          () => _openLogin(targetRoute: const GteNavigationRoute.market()),
      navigationDependencies: _navigationDependencies(),
    );
  }

  Widget _buildWalletDestination() {
    return GtePortfolioScreen(
      key: const PageStorageKey<String>('portfolio-screen'),
      controller: widget.controller,
      onOpenPlayer: _openPlayer,
      onOpenLogin:
          () => _openLogin(targetRoute: const GteNavigationRoute.wallet()),
    );
  }

  GtePrimaryDestination _resolvePrimaryLane(GtePrimaryDestination destination) {
    return _visiblePrimaryDestinations.contains(destination)
        ? destination
        : GtePrimaryDestination.home;
  }

  void _setRoute(GteNavigationRoute route) {
    setState(() {
      _route = route;
    });
    widget.onRouteChanged?.call(_route);
    _scheduleStartupWork(force: true);
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
      case GtePrimaryDestination.admin:
        {
          if (widget.controller.isAuthenticated) {
            await widget.controller.refreshAccount();
          }
          return;
        }
    }
  }

  void _openPrimaryDestination(GtePrimaryDestination destination) {
    if (!_visiblePrimaryDestinations.contains(destination)) {
      _setRoute(const GteNavigationRoute.home());
      return;
    }
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
      setState(() {
        _route = targetRoute;
      });
      widget.onRouteChanged?.call(_route);
      _scheduleStartupWork(force: true);
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
      if (_isTestBinding &&
          widget.backendMode == GteBackendMode.fixture &&
          _route.primaryDestination == GtePrimaryDestination.wallet &&
          (widget.controller.walletDisplay != null ||
              widget.controller.portfolioSummary != null)) {
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

  String _routeTitle() {
    return _route.primaryDestination.label;
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
          title: 'Player market',
          status:
              widget.controller.marketError == null
                  ? 'Players, regens, prices, and club context are ready.'
                  : 'Player board degraded. The last confirmed board is still visible.',
          syncedAt: widget.controller.marketSyncedAt,
          accent: accent,
          isRefreshing: widget.controller.isLoadingMarket,
          onRefresh: () => widget.controller.loadMarket(reset: true),
        );
      case GtePrimaryDestination.hub:
        final bool creatorHealthy = _creatorController.errorMessage == null;
        return GteSyncStatusCard(
          title: 'Creator',
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
          title: 'Capital',
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
          title: 'World sync',
          status:
              'World keeps your club, matchday, scouting, and market routes aligned.',
          detail:
              'Runtime ${_runtimeModeLabel()} on ${_apiHostLabel()} - ${_runtimeAudienceLabel()}',
          syncedAt: widget.controller.marketSyncedAt,
          accent: accent,
          isRefreshing: widget.controller.isBootstrapping,
          onRefresh: widget.controller.bootstrap,
        );
      case GtePrimaryDestination.admin:
        return GteSyncStatusCard(
          title: 'Admin command',
          status:
              _isAdminSession
                  ? 'Payment review, disputes, moderation, and settlement queues are available for this admin session.'
                  : 'Admin command is blocked until an eligible session is active.',
          detail:
              'Runtime ${_runtimeModeLabel()} on ${_apiHostLabel()} - ${_runtimeAudienceLabel()}',
          syncedAt:
              widget.controller.portfolioSyncedAt ??
              widget.controller.ordersSyncedAt,
          accent: accent,
          isRefreshing: widget.controller.isLoadingPortfolio,
          onRefresh:
              widget.controller.isAuthenticated
                  ? widget.controller.refreshAccount
                  : null,
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
