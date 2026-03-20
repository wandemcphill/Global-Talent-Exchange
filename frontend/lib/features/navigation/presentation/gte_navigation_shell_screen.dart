import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/creator_application_controller.dart';
import 'package:gte_frontend/controllers/creator_controller.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/controllers/referral_controller.dart';
import 'package:gte_frontend/core/gte_session_identity.dart';
import 'package:gte_frontend/data/competition_api.dart';
import 'package:gte_frontend/data/creator_application_api.dart';
import 'package:gte_frontend/data/creator_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/referral_api.dart';
import 'package:gte_frontend/features/competitions_hub/presentation/gte_competitions_hub_screen.dart';
import 'package:gte_frontend/features/competitions_hub/routing/competition_hub_destination.dart';
import 'package:gte_frontend/features/home_dashboard/home_dashboard_screen.dart';
import 'package:gte_frontend/features/navigation/routing/gte_navigation_route.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/features/shared/presentation/gte_no_club_onboarding_view.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/gte_exchange_player_detail_screen.dart';
import 'package:gte_frontend/screens/gte_login_screen.dart';
import 'package:gte_frontend/screens/gte_market_players_screen.dart';
import 'package:gte_frontend/screens/gte_portfolio_screen.dart';
import 'package:gte_frontend/screens/creators/creator_access_request_screen.dart';
import 'package:gte_frontend/screens/referrals/referral_hub_screen.dart';
import 'package:gte_frontend/screens/admin/manager_admin_screen.dart';
import 'package:gte_frontend/screens/admin/admin_command_center_screen.dart';
import 'package:gte_frontend/screens/manager_market_screen.dart';
import 'package:gte_frontend/theme/gte_theme_picker_sheet.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_route_integrity_screen.dart';
import 'package:gte_frontend/widgets/gte_sync_status_card.dart';
import 'package:gte_frontend/widgets/gtex_branding.dart';

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

const List<GtePrimaryDestination> _shellPrimaryDestinations =
    <GtePrimaryDestination>[
      GtePrimaryDestination.home,
      GtePrimaryDestination.competitions,
      GtePrimaryDestination.market,
      GtePrimaryDestination.hub,
      GtePrimaryDestination.club,
    ];

class _GteNavigationShellScreenState extends State<GteNavigationShellScreen> {
  late GteNavigationRoute _route;
  late GtePrimaryDestination _selectedPrimaryLane;
  late CompetitionController _competitionController;
  late CreatorApplicationController _creatorApplicationController;
  late CreatorController _creatorController;
  late ReferralController _referralController;
  late String _competitionUserId;
  late String? _competitionUserName;
  late String? _creatorAccessToken;
  final PageStorageBucket _pageStorageBucket = PageStorageBucket();

  @override
  void initState() {
    super.initState();
    _route = widget.initialRoute;
    _selectedPrimaryLane = _resolvePrimaryLane(_route.primaryDestination);
    widget.controller.addListener(_handleExchangeControllerChanged);
    _competitionUserId = _resolveCompetitionUserId();
    _competitionUserName = _resolveCompetitionUserName();
    _creatorAccessToken = widget.controller.accessToken;
    _competitionController = _buildCompetitionController();
    _creatorApplicationController = _buildCreatorApplicationController();
    _creatorApplicationController.addListener(_handleCreatorAccessChanged);
    _creatorController = _buildCreatorController();
    _referralController = _buildReferralController();
    widget.controller.bootstrap();
    _competitionController.bootstrap();
    _primeCreatorAccessState(force: true);
    _primeRouteData();
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
      _competitionController.bootstrap();
      _primeCreatorAccessState(force: true);
    }
    if (widget.initialRoute != oldWidget.initialRoute &&
        widget.initialRoute != _route) {
      setState(() {
        _route = widget.initialRoute;
        _selectedPrimaryLane =
            _resolvePrimaryLane(widget.initialRoute.primaryDestination);
      });
      _primeRouteData();
    }
  }

  @override
  void dispose() {
    widget.controller.removeListener(_handleExchangeControllerChanged);
    _competitionController.dispose();
    _disposeCreatorAccessController();
    _creatorController.dispose();
    _referralController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final bool compactViewport = MediaQuery.sizeOf(context).height < 720;
    final tokens = GteShellTheme.tokensOf(context);
    final EdgeInsets topSectionPadding =
        compactViewport
            ? const EdgeInsets.fromLTRB(16, 6, 16, 0)
            : const EdgeInsets.fromLTRB(20, 12, 20, 0);
    final double sectionGap = compactViewport ? 0 : 8;
    final bool showShellStatusCard =
        _route.primaryDestination != GtePrimaryDestination.home;
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          toolbarHeight: compactViewport ? 72 : 82,
          titleSpacing: compactViewport ? 12 : 16,
          title: Row(
            children: <Widget>[
              const GtexLogoMark(size: 38, compact: true),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(_routeTitle()),
                    Text(
                      _routeContextLine(),
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
            ],
          ),
          actions: <Widget>[
            AnimatedBuilder(
              animation: widget.controller,
              builder: (BuildContext context, Widget? child) {
                if (widget.controller.isAuthenticated) {
                  return Row(
                    children: <Widget>[
                      _buildThemePickerAction(context),
                      _buildCapitalAction(),
                      Padding(
                        padding: const EdgeInsets.only(right: 12),
                        child: Center(
                          child: Text(widget.controller.session!.user.username),
                        ),
                      ),
                      Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: IconButton(
                          tooltip: 'Creator access request',
                          onPressed: () => _pushCreatorAccessRequest(context),
                          icon: const Icon(Icons.how_to_reg_outlined),
                        ),
                      ),
                      if (_hasApprovedCreatorAccess)
                        Padding(
                          padding: const EdgeInsets.only(right: 8),
                          child: IconButton(
                            tooltip: 'Creator community',
                            onPressed: () {
                              Navigator.of(context).push<void>(
                                MaterialPageRoute<void>(
                                  builder:
                                      (
                                        BuildContext context,
                                      ) => ReferralHubScreen(
                                        referralController: _referralController,
                                        creatorController: _creatorController,
                                        isAuthenticated:
                                            widget.controller.isAuthenticated,
                                        hasApprovedCreatorAccess:
                                            _hasApprovedCreatorAccess,
                                        isReferralRuntimeAvailable:
                                            _isReferralRuntimeAvailable,
                                        onOpenCreatorAccessRequest:
                                            () => _pushCreatorAccessRequest(
                                              context,
                                            ),
                                      ),
                                ),
                              );
                            },
                            icon: const Icon(Icons.campaign_outlined),
                          ),
                        ),
                      Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: IconButton(
                          tooltip: 'Managers market',
                          onPressed: () {
                            final session = widget.controller.session;
                            if (session == null) {
                              return;
                            }
                            Navigator.of(context).push<void>(
                              MaterialPageRoute<void>(
                                builder:
                                    (BuildContext context) =>
                                        ManagerMarketScreen(
                                          baseUrl: widget.apiBaseUrl,
                                          accessToken: session.accessToken,
                                          isAdmin: <String>{
                                            'admin',
                                            'super_admin',
                                          }.contains(
                                            session.user.role.toLowerCase(),
                                          ),
                                          onOpenAdmin: () {
                                            Navigator.of(context).push<void>(
                                              MaterialPageRoute<void>(
                                                builder:
                                                    (
                                                      BuildContext context,
                                                    ) => ManagerAdminScreen(
                                                      baseUrl:
                                                          widget.apiBaseUrl,
                                                      accessToken:
                                                          session.accessToken,
                                                      role: session.user.role,
                                                    ),
                                              ),
                                            );
                                          },
                                        ),
                              ),
                            );
                          },
                          icon: const Icon(Icons.sports_soccer_outlined),
                        ),
                      ),
                      Padding(
                        padding: const EdgeInsets.only(right: 16),
                        child: FilledButton.tonal(
                          onPressed: () async {
                            await widget.controller.signOut();
                            if (!mounted) {
                              return;
                            }
                            _setRoute(const GteNavigationRoute.home());
                          },
                          child: const Text('Sign out'),
                        ),
                      ),
                    ],
                  );
                }
                return Padding(
                  padding: const EdgeInsets.only(right: 16),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: <Widget>[
                      _buildThemePickerAction(context),
                      _buildCapitalAction(),
                      FilledButton(
                        onPressed: () {
                          _openLogin();
                        },
                        child: const Text('Sign in'),
                      ),
                    ],
                  ),
                );
              },
            ),
          ],
        ),
        body: AnimatedBuilder(
          animation: widget.controller,
          builder: (BuildContext context, Widget? child) {
            if (widget.controller.isBootstrapping &&
                widget.controller.players.isEmpty) {
              return const Center(child: CircularProgressIndicator());
            }

            return Column(
              children: <Widget>[
                if (showShellStatusCard) ...<Widget>[
                  Padding(
                    padding: topSectionPadding,
                    child: _buildModeSyncCard(context),
                  ),
                  SizedBox(height: sectionGap),
                ],
                Expanded(
                  child: PageStorage(
                    bucket: _pageStorageBucket,
                    child: IndexedStack(
                      index: GtePrimaryDestination.values.indexOf(
                        _route.primaryDestination,
                      ),
                      children: <Widget>[
                        _buildHomeDestination(),
                        GteMarketPlayersScreen(
                          key: const PageStorageKey<String>('market-screen'),
                          controller: widget.controller,
                          onOpenPlayer: _openPlayer,
                          onOpenLogin:
                              () => _openLogin(
                                targetRoute: const GteNavigationRoute.market(),
                              ),
                          navigationDependencies: _navigationDependencies(),
                        ),
                        GteCompetitionsHubScreen(
                          key: const PageStorageKey<String>('competitions-hub'),
                          controller: _competitionController,
                          currentDestination:
                              _route.effectiveCompetitionDestination,
                          onDestinationChanged: _openCompetitionDestination,
                          isAuthenticated: widget.controller.isAuthenticated,
                          isCheckingCreatorAccess: _isCheckingCreatorAccess,
                          canHostCompetitions: _canHostCompetitions,
                          onOpenLogin:
                              () => _openLogin(
                                targetRoute: GteNavigationRoute.competitions(
                                  destination:
                                      _route.effectiveCompetitionDestination,
                                ),
                              ),
                          onOpenCreatorAccessRequest:
                              () => _pushCreatorAccessRequest(context),
                          navigationDependencies: _navigationDependencies(),
                        ),
                        const GteRouteIntegrityScreen.hidden(
                          key: PageStorageKey<String>('community-hub'),
                          title: 'Community removed from active shell',
                          message:
                              'Community, discovery, and governance routes are hidden until the real backend replaces the seeded fallback rails.',
                          icon: Icons.forum_outlined,
                        ),
                        _buildClubDestination(),
                        GtePortfolioScreen(
                          key: const PageStorageKey<String>('portfolio-screen'),
                          controller: widget.controller,
                          onOpenPlayer: _openPlayer,
                          onOpenLogin:
                              () => _openLogin(
                                targetRoute: const GteNavigationRoute.wallet(),
                              ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            );
          },
        ),
        bottomNavigationBar: Container(
          decoration: BoxDecoration(
            color: tokens.panel.withValues(alpha: 0.96),
            border: Border(
              top: BorderSide(color: tokens.stroke.withValues(alpha: 0.45)),
            ),
            boxShadow: <BoxShadow>[
              BoxShadow(
                color: tokens.shadow.withValues(alpha: 0.28),
                blurRadius: 24,
                offset: const Offset(0, -10),
              ),
            ],
          ),
          child: _ShellBottomNav(
            currentDestination: _route.primaryDestination,
            onOpenPrimaryDestination: _openPrimaryDestination,
          ),
        ),
      ),
    );
  }

  Widget _buildClubDestination() {
    return const GteRouteIntegrityScreen.hidden(
      title: 'Club workspace removed from active shell',
      message:
          'Club hub routes are hidden until the real club backend replaces the mock, stub, and local-only fallback stack.',
      icon: Icons.shield_outlined,
    );
  }

  Widget _buildHomeDestination() {
    final String? canonicalClubId = _canonicalClubId()?.trim();
    if (canonicalClubId == null || canonicalClubId.isEmpty) {
      if (!widget.controller.isAuthenticated) {
        return Padding(
          padding: const EdgeInsets.all(20),
          child: GteStatePanel(
            eyebrow: 'CLUB SCOPE',
            title: 'Sign in to open club-scoped home',
            message:
                'Guest preview mode does not expose a canonical club. Sign in to continue with a real club context or create one first.',
            icon: Icons.login_outlined,
            accentColor: _routeAccentFor(context, GtePrimaryDestination.home),
            actionLabel: 'Sign in',
            onAction: () {
              _openLogin(targetRoute: const GteNavigationRoute.home());
            },
          ),
        );
      }
    }
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
      onOpenClubTab: null,
      onOpenCompetitionsTab:
          () => _openPrimaryDestination(GtePrimaryDestination.competitions),
      onOpenMarketTab:
          () => _openPrimaryDestination(GtePrimaryDestination.market),
      onOpenHubTab: null,
      onOpenWalletTab:
          () => _openPrimaryDestination(GtePrimaryDestination.wallet),
      onOpenClubSubtab: null,
      onOpenCreatorAccessRequest: () => _pushCreatorAccessRequest(context),
      navigationDependencies: _navigationDependencies().liveOnly(),
    );
  }

  void _handleExchangeControllerChanged() {
    final String? nextAccessToken = widget.controller.accessToken;
    if (nextAccessToken != _creatorAccessToken) {
      _creatorAccessToken = nextAccessToken;
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
    if (!_hasApprovedCreatorAccess) {
      return false;
    }
    final String? provisionStatus =
        _creatorApplicationController
            .application
            ?.provisioning
            ?.provisionStatus;
    if (provisionStatus == null || provisionStatus.trim().isEmpty) {
      return true;
    }
    return provisionStatus.trim().toLowerCase() == 'active';
  }

  bool get _isReferralRuntimeAvailable => false;

  GteBackendMode get _liveBackendMode => GteBackendMode.live;

  CompetitionController _buildCompetitionController() {
    return CompetitionController(
      api: CompetitionApi.standard(
        baseUrl: widget.apiBaseUrl,
        mode: _liveBackendMode,
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

  Widget _buildHubDestination() {
    if (!widget.controller.isAuthenticated) {
      return Padding(
        padding: const EdgeInsets.all(20),
        child: GteStatePanel(
          eyebrow: 'HUB ACCESS',
          title: 'Sign in to open Hub',
          message:
              'Hub keeps creator invites, referral milestones, and community momentum in one lane. Sign in to load the live data behind it.',
          icon: Icons.groups_outlined,
          accentColor: const Color(0xFF5FE3A1),
          actionLabel: 'Sign in',
          onAction: () =>
              _openLogin(targetRoute: const GteNavigationRoute.hub()),
        ),
      );
    }

    return ReferralHubScreen(
      key: const PageStorageKey<String>('hub-screen'),
      referralController: _referralController,
      creatorController: _creatorController,
    );
  }

  GtePrimaryDestination _resolvePrimaryLane(GtePrimaryDestination destination) {
    return _shellPrimaryDestinations.contains(destination)
        ? destination
        : GtePrimaryDestination.home;
  }

  void _setRoute(GteNavigationRoute route) {
    setState(() {
      _route = route;
      _selectedPrimaryLane = _resolvePrimaryLane(route.primaryDestination);
    });
    widget.onRouteChanged?.call(_route);
    _primeRouteData();
  }

  void _openPrimaryDestination(GtePrimaryDestination destination) {
    _setRoute(_route.withPrimaryDestination(destination));
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
      _primeRouteData();
    }
    return true;
  }

  void _primeRouteData() {
    if (_route.primaryDestination == GtePrimaryDestination.wallet &&
        widget.controller.isAuthenticated) {
      widget.controller.refreshAccount();
    }
    return true;
  }

  void _openCoachMarket() {
    final session = widget.controller.session;
    if (session == null) {
      _openLogin(targetRoute: _route);
      return;
    }
    Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => ManagerMarketScreen(
          baseUrl: widget.apiBaseUrl,
          accessToken: session.accessToken,
          isAdmin: <String>{'admin', 'super_admin'}
              .contains(session.user.role.toLowerCase()),
          onOpenAdmin: _openManagerAdmin,
        ),
      ),
    );
  }

  void _openManagerAdmin() {
    final session = widget.controller.session;
    if (session == null) {
      return;
    }
    Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => ManagerAdminScreen(
          baseUrl: widget.apiBaseUrl,
          accessToken: session.accessToken,
          role: session.user.role,
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

  Widget _buildCapitalAction() {
    final bool isActive =
        _route.primaryDestination == GtePrimaryDestination.wallet;
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: IconButton(
        tooltip: 'Capital room',
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

  String _routeTitle() {
    if (_route.primaryDestination == GtePrimaryDestination.home) {
      return 'Home Lobby';
    }
    if (_route.primaryDestination == GtePrimaryDestination.wallet) {
      return 'Capital Room';
    }
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
    return 'Guest preview';
  }

  GteSyncStatusCard _buildModeSyncCard(BuildContext context) {
    final Color accent = _routeAccentFor(context, _route.primaryDestination);
    switch (_route.primaryDestination) {
      case GtePrimaryDestination.competitions:
        return GteSyncStatusCard(
          title: 'Play lane',
          status: _competitionController.discoveryError == null
              ? 'Fixtures, brackets, and replay narratives are synced.'
              : 'Play feed degraded. Showing the latest competition snapshot.',
          syncedAt: _competitionController.discoverySyncedAt,
          accent: accent,
          isRefreshing: _competitionController.isLoadingDiscovery,
          onRefresh: _competitionController.loadDiscovery,
        );
      case GtePrimaryDestination.market:
        return GteSyncStatusCard(
          title: 'Transfer market',
          status:
              widget.controller.marketError == null
                  ? 'Quotes, order rails, and price tape are ready.'
                  : 'Market feed degraded. Last good tape is still visible.',
          syncedAt: widget.controller.marketSyncedAt,
          accent: accent,
          isRefreshing: widget.controller.isLoadingMarket,
          onRefresh: () => widget.controller.loadMarket(reset: true),
        );
      case GtePrimaryDestination.hub:
        return GteSyncStatusCard(
          title: 'Play center',
          status:
              _competitionController.discoveryError == null
                  ? 'Fixtures, brackets, and replay narratives are synced.'
                  : 'Arena feed degraded. Showing the latest competition snapshot.',
          syncedAt: _competitionController.discoverySyncedAt,
          accent: accent,
          isRefreshing:
              _referralController.isLoading || _creatorController.isLoading,
          onRefresh: widget.controller.isAuthenticated
              ? () {
                  _referralController.load();
                  _creatorController.load();
                }
              : null,
        );
      case GtePrimaryDestination.community:
        return GteSyncStatusCard(
          title: 'Hub pulse',
          status:
              'Community routes are not connected in the active shell. Hidden surfaces stay offline until the real backend path is ready.',
          syncedAt: widget.controller.marketSyncedAt,
          accent: accent,
          isRefreshing: false,
          onRefresh: null,
        );
      case GtePrimaryDestination.club:
        return GteSyncStatusCard(
          title: 'Club builder',
          status:
              'Club routes are hidden from the active shell until the club backend can run without fixture, mock, or local-only fallback.',
          syncedAt: widget.controller.marketSyncedAt,
          accent: accent,
          isRefreshing: false,
          onRefresh: null,
        );
      case GtePrimaryDestination.wallet:
        return GteSyncStatusCard(
          title: 'Capital room',
          status:
              widget.controller.isAuthenticated
                  ? 'Balances, holdings, and ledgers are being protected and reconciled.'
                  : 'Wallet is in preview mode. Sign in to unlock funding and execution.',
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
          title: 'Premium command deck',
          status:
              'Every major GTEX surface stays visually distinct while sharing one premium shell.',
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
}

class _ShellBottomNav extends StatelessWidget {
  const _ShellBottomNav({
    required this.currentDestination,
    required this.onOpenPrimaryDestination,
  });

  final GtePrimaryDestination currentDestination;
  final ValueChanged<GtePrimaryDestination> onOpenPrimaryDestination;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return SafeArea(
      top: false,
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.fromLTRB(16, 10, 16, 12),
        child: Row(
          children: <Widget>[
            ..._shellPrimaryDestinations.map(
              (GtePrimaryDestination destination) => Padding(
                padding: const EdgeInsets.only(right: 10),
                child: _ShellNavChip(
                  destination: destination,
                  isActive: currentDestination == destination,
                  onTap: () => onOpenPrimaryDestination(destination),
                ),
              ),
            ),
            Container(
              width: 1,
              height: 26,
              margin: const EdgeInsets.symmetric(horizontal: 6),
              color: tokens.stroke.withValues(alpha: 0.5),
            ),
            _ShellNavChip(
              destination: GtePrimaryDestination.wallet,
              isActive: currentDestination == GtePrimaryDestination.wallet,
              onTap:
                  () => onOpenPrimaryDestination(GtePrimaryDestination.wallet),
            ),
          ],
        ),
      ),
    );
  }
}

class _ShellNavChip extends StatelessWidget {
  const _ShellNavChip({
    required this.destination,
    required this.isActive,
    required this.onTap,
  });

  final GtePrimaryDestination destination;
  final bool isActive;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final Color tone = _routeAccentFor(context, destination);
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOutCubic,
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(18),
            color:
                isActive
                    ? tone.withValues(alpha: 0.18)
                    : tokens.panelElevated.withValues(alpha: 0.78),
            border: Border.all(
              color:
                  isActive
                      ? tone.withValues(alpha: 0.45)
                      : tokens.stroke.withValues(alpha: 0.65),
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Icon(
                isActive ? destination.selectedIcon : destination.icon,
                size: 18,
                color: isActive ? tone : tokens.textMuted,
              ),
              const SizedBox(width: 8),
              Text(
                destination.label,
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: isActive ? tone : tokens.textPrimary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
