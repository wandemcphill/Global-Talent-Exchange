import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/controllers/creator_application_controller.dart';
import 'package:gte_frontend/controllers/creator_controller.dart';
import 'package:gte_frontend/controllers/referral_controller.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/core/gte_session_identity.dart';
import 'package:gte_frontend/data/club_creation_api.dart';
import 'package:gte_frontend/data/community_api.dart';
import 'package:gte_frontend/data/competition_api.dart';
import 'package:gte_frontend/data/creator_api.dart';
import 'package:gte_frontend/data/creator_application_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/referral_api.dart';
import 'package:gte_frontend/features/app_routes/gte_navigation_helpers.dart';
import 'package:gte_frontend/features/app_routes/gte_route_data.dart';
import 'package:gte_frontend/features/competitions/presentation/gtex_live_competitions_command_screen.dart';
import 'package:gte_frontend/features/competitions_hub/routing/competition_hub_destination.dart';
import 'package:gte_frontend/features/global_search_redesign/global_search_redesign.dart';
import 'package:gte_frontend/features/home/home_screen.dart';
import 'package:gte_frontend/features/launch_control_redesign/launch_control_feature_gate.dart';
import 'package:gte_frontend/features/club_redesign/widgets/gtex_empire_club_switcher.dart';
import 'package:gte_frontend/features/navigation/model/gtex_shell_navigation_model.dart';
import 'package:gte_frontend/features/navigation/presentation/gtex_shell_command_home_entry.dart';
import 'package:gte_frontend/features/navigation/presentation/gtex_shell_sync_status_builder.dart';
import 'package:gte_frontend/features/navigation/routing/gte_navigation_route.dart';
import 'package:gte_frontend/ui_gtex/layout/gtex_shell_scaffold.dart';
import 'package:gte_frontend/ui_gtex/layout/gtex_top_bar.dart';
import 'package:gte_frontend/features/owner_console/data/owner_console_api.dart';
import 'package:gte_frontend/features/owner_console/presentation/owner_console_screen.dart';
import 'package:gte_frontend/features/regen_redesign/data/gtex_share_market_api.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/features/player_detail/gtex_fm_player_profile_screen.dart';
import 'package:gte_frontend/features/player_detail/gtex_player_navigator.dart';
import 'package:gte_frontend/features/regens/regens_screen_v2.dart';
import 'package:gte_frontend/features/social/social_screen.dart';
import 'package:gte_frontend/features/world/widgets/football_world_pulse_widgets.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/admin/admin_command_center_screen.dart';
import 'package:gte_frontend/shared/auth/gtex_admin_capabilities.dart';
import 'package:gte_frontend/screens/clubs/create_club_screen.dart';
import 'package:gte_frontend/features/club_redesign/presentation/gtex_empire_club_workspace.dart';
import 'package:gte_frontend/screens/clubs/gtex_club_owner_dashboard_screen_v2.dart';
import 'package:gte_frontend/screens/creators/creator_access_request_screen.dart';
import 'package:gte_frontend/screens/creators/gtex_studio_hub_screen_v2.dart';
import 'package:gte_frontend/screens/gte_login_screen.dart';
import 'package:gte_frontend/screens/gte_market_players_screen_v2.dart';
import 'package:gte_frontend/screens/notifications/gte_notifications_screen_v2.dart';
import 'package:gte_frontend/screens/profile/gtex_live_profile_screen.dart';
import 'package:gte_frontend/screens/wallet/gte_funding_flow_screen.dart';
import 'package:gte_frontend/screens/wallet/gte_withdrawal_flow_screen.dart';
import 'package:gte_frontend/screens/wallet/gtex_wallet_overview_screen_v2.dart';
import 'package:gte_frontend/services/ambient_audio_controller.dart';
import 'package:gte_frontend/services/audio/gtex_audio_context.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';
import 'package:gte_frontend/theme/gte_theme_picker_sheet.dart';
import 'package:gte_frontend/ui_gtex/routes/gtex_current_route_adapter.dart';
import 'package:gte_frontend/ui_gtex/theme/gtex_colors.dart';
import 'package:gte_frontend/ui_gtex/theme/gtex_spacing.dart';
import 'package:gte_frontend/widgets/ambient_audio_toggle_button.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_sync_status_card.dart';

/// Window width at which there is room for the 318px world-pulse rail on top
/// of the nav rail *and* a workspace wide enough for a master/detail screen
/// to still show its browse panel, its summary panel and a full-width
/// content pane. Below it the rail is dropped rather than taken out of the
/// content.
const double _worldPulseRailMinWidth = 1700;

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
    this.enableShellV3,
    this.customLaneBuilders,
    this.initialOwnedClubs = const <GtexOwnedClubOption>[],
    this.attentionBadgeCount = 0,
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
  final bool? enableShellV3;
  final Map<GtePrimaryDestination, WidgetBuilder>? customLaneBuilders;
  final List<GtexOwnedClubOption> initialOwnedClubs;
  final int attentionBadgeCount;

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
    case GtePrimaryDestination.regens:
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
  const _NavigationProviderScopeBoundary({
    required this.config,
    required this.child,
  });

  /// Seeds the fallback container when the shell is hosted without a
  /// [ProviderScope]. Without it Riverpod surfaces inside the shell resolve
  /// `appConfigProvider` to its unroutable default host.
  final GteAppConfig config;
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
      final ProviderContainer container =
          _container ??= ProviderContainer(
            overrides: [appConfigProvider.overrideWithValue(widget.config)],
          );
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
  final Map<GtePrimaryDestination, Widget> _retainedLaneWidgets =
      <GtePrimaryDestination, Widget>{};
  late List<GtexOwnedClubOption> _ownedClubs;
  GtexWorkspaceKind? _selectedWorkspaceOverride;
  bool _startupWorkScheduled = false;
  Timer? _liveRefreshTimer;

  bool get _isTestBinding =>
      WidgetsBinding.instance.runtimeType.toString().contains('Test');

  @override
  void initState() {
    super.initState();
    _route = widget.initialRoute;
    _ownedClubs = List<GtexOwnedClubOption>.from(widget.initialOwnedClubs);
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
    // The world-pulse rail is ambient context, so it yields on horizontal
    // budget rather than viewport height: it is the first thing dropped when
    // the workspace it sits beside would otherwise be squeezed. Below this
    // width the rail's 318px came straight out of the primary content pane,
    // which is what left the Transfer Hub with unreadable player cards at
    // every common laptop width. The live pulse ticker stays at all widths,
    // so world activity is never fully hidden.
    final bool showWorldPulseRail =
        !compactViewport && viewport.width >= _worldPulseRailMinWidth;
    final EdgeInsets topSectionPadding =
        compactViewport
            ? const EdgeInsets.fromLTRB(16, 6, 16, 0)
            : const EdgeInsets.fromLTRB(20, 12, 20, 0);
    final bool showShellStatusCard = !compactViewport;
    return _NavigationProviderScopeBoundary(
      config: GteAppConfig(
        apiBaseUrl: widget.apiBaseUrl,
        backendMode: widget.backendMode,
      ),
      child: AnimatedBuilder(
        animation: widget.controller,
        builder: (BuildContext context, Widget? child) {
          // Every surface below the shell opens a player the same way, so a
          // squad row, a lineup name and a market card all resolve to the
          // one canonical player detail.
          final Widget workspace = GtexPlayerNavigator(
            openPlayer: _openPlayer,
            child: PageStorage(
              bucket: _pageStorageBucket,
              child: _buildRetainedLaneStack(context),
            ),
          );

          final ShellNavigationModel navModel = _buildShellNavigationModel();
          return GtexShellScaffold(
            navigationModel: navModel,
            selectedSlotId: _selectedSlotIdForRoute(navModel),
            onSelectSlot: _handleSelectShellSlot,
            onSelectSecondary: _handleSelectSecondaryDestination,
            activeRoute: _route.path,
            status:
                showShellStatusCard
                    ? Padding(
                      padding: topSectionPadding,
                      child: _buildModeSyncCard(context),
                    )
                    : null,
            livePulseStrip: const FootballWorldPulseTicker(),
            worldPulseRail:
                showWorldPulseRail ? const FootballWorldPulseRail() : null,
            topBar: GtexTopBar(
              title: _routeTitle(),
              subtitle: '${_routeSubtitle()} - ${_routeContextLine()}',
              availableWorkspaces: navModel.availableWorkspaces,
              activeWorkspace: navModel.activeWorkspace,
              onWorkspaceSelected: (GtexWorkspaceKind nextWorkspace) {
                setState(() {
                  _selectedWorkspaceOverride = nextWorkspace;
                });
              },
              ownedClubs:
                  navModel.capabilities.isClubOwner
                      ? _effectiveOwnedClubs()
                      : const <GtexOwnedClubOption>[],
              activeClubId:
                  navModel.capabilities.isClubOwner ? _canonicalClubId() : null,
              activeClubName:
                  navModel.capabilities.isClubOwner ? _canonicalClubName() : null,
              onClubSelected: (GtexOwnedClubOption club) {
                unawaited(_handleTopBarClubSwitch(club));
              },
              attentionCount: navModel.topBarAttentionCount,
              onOpenAttention: _openNotifications,
              onOpenSearch: _openGlobalSearch,
              walletBalanceGtc:
                  widget.controller.walletSummary?.availableBalance,
              onOpenWallet:
                  () => _openPrimaryDestination(GtePrimaryDestination.wallet),
              onOpenAdmin: _isAdminSession ? _openAdminCommandCenter : null,
              onOpenProfile:
                  widget.controller.isAuthenticated
                      ? _openProfileSettings
                      : () => _openLogin(),
              isAuthenticated: widget.controller.isAuthenticated,
              extraActions: _buildShellV3ExtraActions(context),
            ),
            child: workspace,
          );
        },
      ),
    );
  }

  Widget _buildClubDestination() {
    if (_isCoinTraderSession || _isCreatorSession) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(GtexSpacing.lg),
          child: Text(
            'Club ownership tools belong to normal GTEX member accounts. This account remains in its dedicated lane.',
            textAlign: TextAlign.center,
          ),
        ),
      );
    }
    final String? canonicalClubId = _canonicalClubId()?.trim();
    if (canonicalClubId == null || canonicalClubId.isEmpty) {
      return GtexCommandHomeEntry(
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
    final GteAuthedApi shellApi = _createShellAuthedApi();
    return GtexEmpireClubWorkspace(
      key: PageStorageKey<String>('empire-club-$canonicalClubId'),
      controller: widget.controller,
      activeClubId: canonicalClubId,
      activeClubName: _canonicalClubName(),
      authedApi: shellApi,
      onClubsLoaded: (List<GtexOwnedClubOption> loadedClubs) {
        if (!mounted) {
          return;
        }
        setState(() {
          _ownedClubs = loadedClubs;
        });
      },
      child: GtexClubOwnerDashboardScreenV2(
        key: const PageStorageKey<String>('club-owner-dashboard-v2'),
        clubId: canonicalClubId,
        clubName: _canonicalClubName(),
        baseUrl: widget.apiBaseUrl,
        backendMode: widget.backendMode,
        accessToken: widget.controller.accessToken,
        authedApi: shellApi,
        ownerName: widget.controller.session?.user.username,
        walletCredits:
            widget.controller.walletSummary?.availableBalance.round() ?? 0,
        isAuthenticated: widget.controller.isAuthenticated,
        onOpenLogin:
            () => _openLogin(targetRoute: const GteNavigationRoute.club()),
      ),
    );
  }

  Widget _buildHomeDestination() {
    // Home is the personalised command surface for every session state.
    return const HomeScreen(key: PageStorageKey<String>('home-command'));
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

  String get _accountType =>
      widget.controller.session?.user.accountType.trim().toLowerCase() ?? 'user';

  bool get _isCoinTraderSession =>
      _accountType == 'coin_trader' ||
      <String>{'coin_trader', 'coin-trader', 'trader'}.contains(_sessionRole);

  bool get _isCreatorSession =>
      _accountType == 'creator' || _sessionRole == 'creator';

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

  List<GtePrimaryDestination> _primaryDestinationsForWorkspace() {
    if (!widget.controller.isAuthenticated) {
      return const <GtePrimaryDestination>[
        GtePrimaryDestination.home,
        GtePrimaryDestination.club,
        GtePrimaryDestination.market,
        GtePrimaryDestination.regens,
        GtePrimaryDestination.competitions,
        GtePrimaryDestination.community,
      ];
    }
    if (_isAdminSession) {
      return const <GtePrimaryDestination>[
        GtePrimaryDestination.home,
        GtePrimaryDestination.market,
        GtePrimaryDestination.regens,
        GtePrimaryDestination.competitions,
        GtePrimaryDestination.club,
        GtePrimaryDestination.wallet,
        GtePrimaryDestination.hub,
        GtePrimaryDestination.community,
      ];
    }
    if (_isCoinTraderSession && _isCreatorSession) {
      return const <GtePrimaryDestination>[
        GtePrimaryDestination.home,
        GtePrimaryDestination.wallet,
        GtePrimaryDestination.hub,
        GtePrimaryDestination.market,
        GtePrimaryDestination.regens,
        GtePrimaryDestination.community,
      ];
    }
    if (_isCoinTraderSession) {
      return const <GtePrimaryDestination>[
        GtePrimaryDestination.home,
        GtePrimaryDestination.wallet,
        GtePrimaryDestination.market,
        GtePrimaryDestination.regens,
        GtePrimaryDestination.community,
      ];
    }
    if (_isCreatorSession) {
      return const <GtePrimaryDestination>[
        GtePrimaryDestination.home,
        GtePrimaryDestination.hub,
        GtePrimaryDestination.community,
        GtePrimaryDestination.market,
        GtePrimaryDestination.regens,
        GtePrimaryDestination.wallet,
      ];
    }
    if (_canonicalClubId()?.trim().isNotEmpty ?? false) {
      return const <GtePrimaryDestination>[
        GtePrimaryDestination.home,
        GtePrimaryDestination.club,
        GtePrimaryDestination.market,
        GtePrimaryDestination.regens,
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
        GtePrimaryDestination.regens,
        GtePrimaryDestination.club,
        GtePrimaryDestination.wallet,
        GtePrimaryDestination.community,
      ];
    }
    return const <GtePrimaryDestination>[
      GtePrimaryDestination.home,
      GtePrimaryDestination.market,
      GtePrimaryDestination.regens,
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
      // Existing shell destinations, handed to community signals so a club,
      // market or regen item routes into the canonical surface instead of
      // rendering a dead control. No new route or destination is introduced.
      onOpenClub: () => _openPrimaryDestination(GtePrimaryDestination.club),
      onOpenMarket: () => _openPrimaryDestination(GtePrimaryDestination.market),
      onOpenRegens: () => _openPrimaryDestination(GtePrimaryDestination.regens),
    );
  }

  Widget _buildCurrentDestinationFor(GtePrimaryDestination destination) {
    switch (destination) {
      case GtePrimaryDestination.home:
        return _buildHomeDestination();
      case GtePrimaryDestination.competitions:
        return _buildCompetitionsDestination();
      case GtePrimaryDestination.market:
        return _buildMarketDestination();
      case GtePrimaryDestination.regens:
        return _buildRegensDestination();
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
    return GtexLiveCompetitionsCommandScreen(
      key: const PageStorageKey<String>('competitions-command'),
      isAuthenticated: widget.controller.isAuthenticated,
      onOpenLogin:
          () => _openLogin(
            targetRoute: GteNavigationRoute.competitions(
              destination: _route.effectiveCompetitionDestination,
            ),
          ),
    );
  }

  Widget _buildMarketDestination() {
    return GteMarketPlayersScreenV2(
      key: ValueKey<String>('market-screen-${_route.marketDeskMode.name}'),
      controller: widget.controller,
      initialMode: _route.marketDeskMode,
      onOpenPlayer: _openPlayer,
      onOpenLogin: () => _openLogin(targetRoute: _route),
      onModeChanged: (GtexMarketDeskMode mode) {
        _setRoute(GteNavigationRoute.market(mode: mode));
      },
      navigationDependencies: _navigationDependencies(),
    );
  }

  Widget _buildRegensDestination() {
    // The canonical regen surface, mounted inside the shell so it finally
    // inherits the GTEX dark canvas, the navigation rail and back behaviour.
    // It used to be a top-level GoRoute rendering on a bare white page.
    return RegensScreenV2(
      key: const PageStorageKey<String>('regen-world-v2'),
      baseUrl: widget.apiBaseUrl,
      backendMode: widget.backendMode,
      accessToken: widget.controller.accessToken,
      isAuthenticated: widget.controller.isAuthenticated,
      isAdmin: widget.controller.isAdmin,
      onOpenAwards: () => _openFeatureRoute(const WorldAwardsRouteData()),
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
      case GtePrimaryDestination.regens:
        {
          // Regen World owns its own future-backed load and refreshes from
          // its own retry affordance; the shell has nothing to poll here.
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
    _syncAudioContextForDestination(destination);
  }

  void _syncAudioContextForDestination(GtePrimaryDestination destination) {
    final AmbientAudioState? audioController = widget.ambientAudioController;
    if (audioController == null) {
      return;
    }
    switch (destination) {
      case GtePrimaryDestination.home:
        audioController.setAudioContext(GtexAudioContext.home);
        break;
      case GtePrimaryDestination.club:
        audioController.setAudioContext(GtexAudioContext.club);
        break;
      case GtePrimaryDestination.market:
        audioController.setAudioContext(GtexAudioContext.market);
        break;
      case GtePrimaryDestination.competitions:
        audioController.setAudioContext(GtexAudioContext.competition);
        break;
      case GtePrimaryDestination.regens:
        audioController.setAudioContext(GtexAudioContext.world);
        break;
      case GtePrimaryDestination.hub:
      case GtePrimaryDestination.community:
        audioController.setAudioContext(GtexAudioContext.home);
        break;
      case GtePrimaryDestination.wallet:
        audioController.setAudioContext(GtexAudioContext.market);
        break;
    }
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
              capabilities: GtexAdminCapabilities.fromSession(session),
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
            (BuildContext context) => GtexFmPlayerProfileScreen(
              playerId: playerId,
              baseUrl: widget.apiBaseUrl,
              backendMode: widget.backendMode,
              controller: widget.controller,
              onOpenLogin: () => _openLogin(targetRoute: _route),
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

  List<GtexOwnedClubOption> _effectiveOwnedClubs() {
    if (_ownedClubs.isNotEmpty) {
      return _ownedClubs;
    }
    final String? clubId = _canonicalClubId()?.trim();
    if (clubId == null || clubId.isEmpty) {
      return const <GtexOwnedClubOption>[];
    }
    return <GtexOwnedClubOption>[
      GtexOwnedClubOption(
        id: clubId,
        name:
            _canonicalClubName()?.trim().isNotEmpty == true
                ? _canonicalClubName()!.trim()
                : clubId,
      ),
    ];
  }

  ShellNavigationModel _buildShellNavigationModel() {
    final List<String> ownedIds = _effectiveOwnedClubs()
        .map((GtexOwnedClubOption club) => club.id)
        .toList(growable: false);
    final GtexShellCapabilities capabilities = GtexShellCapabilities(
      isAuthenticated: widget.controller.isAuthenticated,
      accountType: _accountType,
      ownedClubIds: ownedIds,
      activeClubId: _canonicalClubId(),
      isOrgScoutOrAgent: _isStaffSession,
      isCoinTrader: _isCoinTraderSession,
      isCreator: _isCreatorSession,
      isAdmin: _isAdminSession,
      clubLegacyEnabled: true,
      unreadNotificationCount: widget.attentionBadgeCount,
    );
    return ShellNavigationModel(
      capabilities: capabilities,
      selectedWorkspace: _selectedWorkspaceOverride,
    );
  }

  GtexShellSlotId _selectedSlotIdForRoute(ShellNavigationModel model) {
    final GtexShellSlotId candidate = switch (_route.primaryDestination) {
      GtePrimaryDestination.home =>
        model.activeWorkspace == GtexWorkspaceKind.admin
            ? GtexShellSlotId.ops
            : model.activeWorkspace == GtexWorkspaceKind.explore
            ? GtexShellSlotId.explore
            : GtexShellSlotId.home,
      GtePrimaryDestination.club =>
        model.activeWorkspace == GtexWorkspaceKind.scouting
            ? GtexShellSlotId.recruitment
            : GtexShellSlotId.club,
      GtePrimaryDestination.competitions => GtexShellSlotId.matchday,
      GtePrimaryDestination.market => GtexShellSlotId.market,
      GtePrimaryDestination.regens => GtexShellSlotId.world,
      GtePrimaryDestination.hub => GtexShellSlotId.studio,
      GtePrimaryDestination.community => GtexShellSlotId.community,
      GtePrimaryDestination.wallet =>
        model.activeWorkspace == GtexWorkspaceKind.admin
            ? GtexShellSlotId.treasury
            : GtexShellSlotId.wallet,
    };
    final bool existsInPrimary = model.primarySlots.any(
      (GtexShellSlotSpec slot) => slot.id == candidate,
    );
    return existsInPrimary ? candidate : GtexShellSlotId.more;
  }

  void _handleSelectShellSlot(GtexShellSlotSpec slot) {
    switch (slot.id) {
      case GtexShellSlotId.home:
      case GtexShellSlotId.explore:
      case GtexShellSlotId.ops:
      case GtexShellSlotId.queues:
        _openPrimaryDestination(GtePrimaryDestination.home);
        return;
      case GtexShellSlotId.club:
      case GtexShellSlotId.recruitment:
        _openPrimaryDestination(GtePrimaryDestination.club);
        return;
      case GtexShellSlotId.matchday:
        _openPrimaryDestination(GtePrimaryDestination.competitions);
        return;
      case GtexShellSlotId.market:
        _openPrimaryDestination(GtePrimaryDestination.market);
        return;
      case GtexShellSlotId.world:
        _openPrimaryDestination(GtePrimaryDestination.regens);
        return;
      case GtexShellSlotId.studio:
        _openPrimaryDestination(GtePrimaryDestination.hub);
        return;
      case GtexShellSlotId.community:
        _openPrimaryDestination(GtePrimaryDestination.community);
        return;
      case GtexShellSlotId.traderDesk:
      case GtexShellSlotId.wallet:
      case GtexShellSlotId.treasury:
        _openPrimaryDestination(GtePrimaryDestination.wallet);
        return;
      case GtexShellSlotId.signIn:
        unawaited(_openLogin());
        return;
      case GtexShellSlotId.more:
        return;
    }
  }

  List<Widget> _buildShellV3ExtraActions(BuildContext context) {
    final List<Widget> actions = <Widget>[
      _buildThemePickerAction(context),
      _buildAmbientAction(),
    ];
    if (widget.controller.isAuthenticated) {
      actions.add(
        IconButton(
          tooltip: 'Creator access request',
          onPressed: () => _pushCreatorAccessRequest(context),
          icon: const Icon(Icons.how_to_reg_outlined, color: GtexColors.text),
        ),
      );
      if (_hasApprovedCreatorAccess) {
        actions.add(
          IconButton(
            tooltip: 'Creator community',
            onPressed: () => _openPrimaryDestination(GtePrimaryDestination.hub),
            icon: const Icon(Icons.campaign_outlined, color: GtexColors.text),
          ),
        );
      }
    }
    return actions;
  }

  void _openBoardroom() {
    if (!widget.controller.isAuthenticated) {
      _openPrimaryDestination(GtePrimaryDestination.club);
      return;
    }
    final GteAuthedApi authedApi = _createShellAuthedApi();
    Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (BuildContext context) => OwnerConsoleScreen(
              reader: OwnerConsoleApi(client: authedApi),
              shareMarket: GtexShareMarketApi(client: authedApi),
              role: _sessionRole,
              signedInAs:
                  widget.controller.session?.user.username ?? 'Club Owner',
              walletBalance: widget.controller.walletSummary?.availableBalance,
              onNavigate: _openGlobalSearchRoute,
            ),
      ),
    );
  }

  void _handleSelectSecondaryDestination(GtexSecondaryDestinationSpec item) {
    switch (item.id) {
      case GtexSecondaryDestinationId.world:
        _openPrimaryDestination(GtePrimaryDestination.regens);
        return;
      case GtexSecondaryDestinationId.community:
        _openPrimaryDestination(GtePrimaryDestination.community);
        return;
      case GtexSecondaryDestinationId.wallet:
        _openPrimaryDestination(GtePrimaryDestination.wallet);
        return;
      case GtexSecondaryDestinationId.boardroom:
        _openBoardroom();
        return;
      case GtexSecondaryDestinationId.you:
      case GtexSecondaryDestinationId.rewards:
        _openProfileSettings();
        return;
      case GtexSecondaryDestinationId.admin:
        _openAdminCommandCenter();
        return;
      case GtexSecondaryDestinationId.newsroom:
        unawaited(_openFeatureRoute(const NewsDeskRouteData()));
        return;
    }
  }

  Future<void> _handleTopBarClubSwitch(GtexOwnedClubOption club) async {
    try {
      await GtexEmpireClubWorkspace.activateClub(
        api: _createShellAuthedApi(),
        controller: widget.controller,
        club: club,
      );
    } catch (_) {
      // Fallback to local binding in fixture/offline test contexts where
      // `/api/clubs/owned/{id}/activate` is not mounted.
      widget.controller.bindCurrentClub(
        clubId: club.id,
        clubName: club.name,
        clubSlug: club.slug,
      );
    }
    if (!mounted) {
      return;
    }
    setState(() {
      _retainedLaneWidgets.remove(GtePrimaryDestination.club);
    });
  }

  Widget _buildRetainedLaneStack(BuildContext context) {
    final List<GtePrimaryDestination> destinations =
        _primaryDestinationsForWorkspace();
    final GtePrimaryDestination active = _route.primaryDestination;
    final List<GtePrimaryDestination> stackOrder =
        destinations.contains(active)
            ? destinations
            : <GtePrimaryDestination>[...destinations, active];
    _retainedLaneWidgets[active] ??= KeyedSubtree(
      key: ValueKey<String>('shell-retained-${active.name}'),
      child: _buildDestinationFor(context, active),
    );
    final int activeIndex = stackOrder.indexOf(active);
    return IndexedStack(
      index: activeIndex < 0 ? 0 : activeIndex,
      children: stackOrder
          .map(
            (GtePrimaryDestination destination) =>
                _retainedLaneWidgets[destination] ?? const SizedBox.shrink(),
          )
          .toList(growable: false),
    );
  }

  Widget _buildDestinationFor(
    BuildContext context,
    GtePrimaryDestination destination,
  ) {
    final WidgetBuilder? customBuilder =
        widget.customLaneBuilders?[destination];
    if (customBuilder != null) {
      return customBuilder(context);
    }
    return _buildCurrentDestinationFor(destination);
  }

  GteSyncStatusCard _buildModeSyncCard(BuildContext context) {
    final Color accent = _routeAccentFor(context, _route.primaryDestination);
    return GtexShellSyncStatusBuilder.build(
      destination: _route.primaryDestination,
      accent: accent,
      exchangeController: widget.controller,
      competitionController: _competitionController,
      creatorController: _creatorController,
      referralController: _referralController,
      isReferralRuntimeAvailable: _isReferralRuntimeAvailable,
      runtimeModeLabel: _runtimeModeLabel(),
      apiHostLabel: _apiHostLabel(),
      runtimeAudienceLabel: _runtimeAudienceLabel(),
    );
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
