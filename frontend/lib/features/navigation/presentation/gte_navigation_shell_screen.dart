import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/creator_controller.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/controllers/referral_controller.dart';
import 'package:gte_frontend/core/gte_session_identity.dart';
import 'package:gte_frontend/data/competition_api.dart';
import 'package:gte_frontend/data/creator_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/referral_api.dart';
import 'package:gte_frontend/features/club_hub/presentation/club_hub_screen.dart';
import 'package:gte_frontend/features/club_navigation/club_navigation.dart';
import 'package:gte_frontend/features/competitions_hub/presentation/gte_competitions_hub_screen.dart';
import 'package:gte_frontend/features/competitions_hub/routing/competition_hub_destination.dart';
import 'package:gte_frontend/features/home_dashboard/home_dashboard_screen.dart';
import 'package:gte_frontend/features/navigation/routing/gte_navigation_route.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/gte_exchange_player_detail_screen.dart';
import 'package:gte_frontend/screens/gte_login_screen.dart';
import 'package:gte_frontend/screens/gte_market_players_screen.dart';
import 'package:gte_frontend/screens/gte_portfolio_screen.dart';
import 'package:gte_frontend/screens/community/community_hub_screen.dart';
import 'package:gte_frontend/screens/referrals/referral_hub_screen.dart';
import 'package:gte_frontend/screens/admin/god_mode_admin_screen.dart';
import 'package:gte_frontend/screens/admin/manager_admin_screen.dart';
import 'package:gte_frontend/screens/admin/admin_command_center_screen.dart';
import 'package:gte_frontend/screens/manager_market_screen.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
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

class _ShellRouteHeader extends StatelessWidget {
  const _ShellRouteHeader({
    required this.route,
    required this.isAuthenticated,
    required this.openOrderCount,
    required this.onOpenLogin,
  });

  final GteNavigationRoute route;
  final bool isAuthenticated;
  final int openOrderCount;
  final Future<bool> Function({GteNavigationRoute? targetRoute}) onOpenLogin;

  @override
  Widget build(BuildContext context) {
    final _ShellHeaderCopy copy =
        _ShellHeaderCopy.fromRoute(route, isAuthenticated, openOrderCount);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        color: Colors.white.withValues(alpha: 0.035),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            copy.eyebrow,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: route.primaryDestination.accentColor,
                  letterSpacing: 1.1,
                ),
          ),
          const SizedBox(height: 8),
          Text(copy.title, style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 6),
          Text(copy.detail, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 14),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              ...copy.chips.map((String chip) => _ShellHeaderChip(
                  label: chip, tone: route.primaryDestination.accentColor)),
              if (!isAuthenticated)
                FilledButton.tonal(
                  onPressed: () => onOpenLogin(targetRoute: route),
                  child: const Text('Sign in for full access'),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ShellHeaderChip extends StatelessWidget {
  const _ShellHeaderChip({required this.label, required this.tone});

  final String label;
  final Color tone;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: tone.withValues(alpha: 0.12),
        border: Border.all(color: tone.withValues(alpha: 0.22)),
      ),
      child: Text(label,
          style: Theme.of(context).textTheme.labelLarge?.copyWith(color: tone)),
    );
  }
}

class _ShellHeaderCopy {
  const _ShellHeaderCopy({
    required this.eyebrow,
    required this.title,
    required this.detail,
    required this.chips,
  });

  final String eyebrow;
  final String title;
  final String detail;
  final List<String> chips;

  factory _ShellHeaderCopy.fromRoute(
      GteNavigationRoute route, bool isAuthenticated, int openOrderCount) {
    switch (route.primaryDestination) {
      case GtePrimaryDestination.home:
        return const _ShellHeaderCopy(
          eyebrow: 'COMMAND DECK',
          title: 'Start from the clearest route, not the loudest one.',
          detail:
              'Home now prioritizes the next best move, then lets quieter signals sit lower in the stack.',
          chips: <String>[
            'Market distinct',
            'Arena distinct',
            'Capital distinct'
          ],
        );
      case GtePrimaryDestination.market:
        return const _ShellHeaderCopy(
          eyebrow: 'TRADING FLOOR',
          title:
              'The tape is built for speed, confidence, and clean execution.',
          detail:
              'Market screens stay denser and sharper than the arena so price discovery never feels theatrical.',
          chips: <String>[
            'Terminal rhythm',
            'Liquidity cues',
            'Execution first'
          ],
        );
      case GtePrimaryDestination.competitions:
        return const _ShellHeaderCopy(
          eyebrow: 'LIVE MATCH CENTER',
          title:
              'Fixtures, replays, and broadcast-style storylines stay in one arena lane.',
          detail:
              'This route is designed to feel cinematic and alive, not like the market wearing football boots.',
          chips: <String>['Live now', 'Up next', 'Replay lane'],
        );
      case GtePrimaryDestination.community:
        return const _ShellHeaderCopy(
          eyebrow: 'COMMUNITY GRID',
          title:
              'Signals, governance, and creator activity stay social without losing structure.',
          detail:
              'Community surfaces keep discovery, moderation, and governance in one lane instead of scattering them across the shell.',
          chips: <String>['Discovery', 'Threads', 'Governance'],
        );
      case GtePrimaryDestination.club:
        return const _ShellHeaderCopy(
          eyebrow: 'CLUB SYSTEMS',
          title: 'Institution, identity, and culture have their own lane.',
          detail:
              'Club surfaces should feel aspirational and structured, separate from both market tension and match-night drama.',
          chips: <String>['Identity', 'Dynasty', 'Trophies'],
        );
      case GtePrimaryDestination.wallet:
        return _ShellHeaderCopy(
          eyebrow: 'CAPITAL LAYER',
          title: 'Cash, exposure, and ledger trust stay readable at a glance.',
          detail: isAuthenticated
              ? 'Open orders: $openOrderCount. Wallet surfaces are deliberately quieter than the market and cleaner than the arena.'
              : 'Preview mode keeps the capital room visible while balances and ledger actions stay protected until sign-in.',
          chips: <String>['Cash vs reserve', 'Holdings view', 'Ledger clarity'],
        );
    }
  }
}

class _GteNavigationShellScreenState extends State<GteNavigationShellScreen> {
  late GteNavigationRoute _route;
  late CompetitionController _competitionController;
  late CreatorController _creatorController;
  late ReferralController _referralController;
  late String _competitionUserId;
  late String? _competitionUserName;
  ClubNavigationTab _clubInitialTab = ClubNavigationTab.squad;
  int _clubHostSeed = 0;
  final PageStorageBucket _pageStorageBucket = PageStorageBucket();

  @override
  void initState() {
    super.initState();
    _route = widget.initialRoute;
    widget.controller.addListener(_handleExchangeControllerChanged);
    _competitionUserId = _resolveCompetitionUserId();
    _competitionUserName = _resolveCompetitionUserName();
    _competitionController = _buildCompetitionController();
    _creatorController = _buildCreatorController();
    _referralController = _buildReferralController();
    widget.controller.bootstrap();
    _competitionController.bootstrap();
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
      _creatorController.dispose();
      _creatorController = _buildCreatorController();
      _referralController.dispose();
      _referralController = _buildReferralController();
      _competitionController.bootstrap();
    }
    if (widget.initialRoute != oldWidget.initialRoute &&
        widget.initialRoute != _route) {
      setState(() {
        _route = widget.initialRoute;
      });
    }
  }

  @override
  void dispose() {
    widget.controller.removeListener(_handleExchangeControllerChanged);
    _competitionController.dispose();
    _creatorController.dispose();
    _referralController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final bool compactViewport = MediaQuery.sizeOf(context).height < 720;
    final EdgeInsets topSectionPadding = compactViewport
        ? const EdgeInsets.fromLTRB(16, 6, 16, 0)
        : const EdgeInsets.fromLTRB(20, 12, 20, 0);
    final double sectionGap = compactViewport ? 0 : 8;
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
                    const Text('Global Talent Exchange'),
                    Text(
                      _route.path,
                      style: const TextStyle(fontSize: 12),
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
                      Padding(
                        padding: const EdgeInsets.only(right: 12),
                        child: Center(
                          child: Text(widget.controller.session!.user.username),
                        ),
                      ),
                      Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: IconButton(
                          tooltip: 'Creator community',
                          onPressed: () {
                            Navigator.of(context).push<void>(
                              MaterialPageRoute<void>(
                                builder: (BuildContext context) =>
                                    ReferralHubScreen(
                                  referralController: _referralController,
                                  creatorController: _creatorController,
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
                                builder: (BuildContext context) =>
                                    ManagerMarketScreen(
                                  baseUrl: widget.apiBaseUrl,
                                  accessToken: session.accessToken,
                                  isAdmin: <String>{
                                    'admin',
                                    'super_admin'
                                  }.contains(session.user.role.toLowerCase()),
                                  onOpenAdmin: () {
                                    Navigator.of(context).push<void>(
                                      MaterialPageRoute<void>(
                                        builder: (BuildContext context) =>
                                            ManagerAdminScreen(
                                          baseUrl: widget.apiBaseUrl,
                                          accessToken: session.accessToken,
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
                      if (<String>{'admin', 'super_admin'}.contains(
                          widget.controller.session?.user.role.toLowerCase() ??
                              'user'))
                        Padding(
                          padding: const EdgeInsets.only(right: 8),
                          child: IconButton(
                            tooltip: 'Admin command center',
                            onPressed: () {
                              final session = widget.controller.session;
                              if (session == null) {
                                return;
                              }
                              Navigator.of(context).push<void>(
                                MaterialPageRoute<void>(
                                  builder: (BuildContext context) =>
                                      AdminCommandCenterScreen(
                                    baseUrl: widget.apiBaseUrl,
                                    accessToken: session.accessToken,
                                    backendMode: widget.backendMode,
                                  ),
                                ),
                              );
                            },
                            icon:
                                const Icon(Icons.dashboard_customize_outlined),
                          ),
                        ),
                      if (<String>{'admin', 'super_admin'}.contains(
                          widget.controller.session?.user.role.toLowerCase() ??
                              'user'))
                        Padding(
                          padding: const EdgeInsets.only(right: 8),
                          child: IconButton(
                            tooltip: 'Admin God Mode',
                            onPressed: () {
                              final session = widget.controller.session;
                              if (session == null) {
                                return;
                              }
                              Navigator.of(context).push<void>(
                                MaterialPageRoute<void>(
                                  builder: (BuildContext context) =>
                                      GodModeAdminScreen(
                                    baseUrl: widget.apiBaseUrl,
                                    accessToken: session.accessToken,
                                    backendMode: widget.backendMode,
                                  ),
                                ),
                              );
                            },
                            icon:
                                const Icon(Icons.admin_panel_settings_outlined),
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
                            setState(() {
                              _route = const GteNavigationRoute.home();
                            });
                          },
                          child: const Text('Sign out'),
                        ),
                      ),
                    ],
                  );
                }
                return Padding(
                  padding: const EdgeInsets.only(right: 16),
                  child: FilledButton(
                    onPressed: () {
                      _openLogin();
                    },
                    child: const Text('Sign in'),
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
                Padding(
                  padding: topSectionPadding,
                  child: _ShellRouteHeader(
                    route: _route,
                    isAuthenticated: widget.controller.isAuthenticated,
                    openOrderCount: widget.controller.openOrders.length,
                    onOpenLogin: _openLogin,
                  ),
                ),
                Padding(
                  padding: topSectionPadding,
                  child: _buildModeSyncCard(),
                ),
                SizedBox(height: sectionGap),
                Expanded(
                  child: PageStorage(
                    bucket: _pageStorageBucket,
                    child: IndexedStack(
                      index: GtePrimaryDestination.values
                          .indexOf(_route.primaryDestination),
                      children: <Widget>[
                        _buildHomeDestination(),
                        GteMarketPlayersScreen(
                          key: const PageStorageKey<String>('market-screen'),
                          controller: widget.controller,
                          onOpenPlayer: _openPlayer,
                          onOpenLogin: () => _openLogin(
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
                          onOpenLogin: () => _openLogin(
                            targetRoute: GteNavigationRoute.competitions(
                              destination:
                                  _route.effectiveCompetitionDestination,
                            ),
                          ),
                          navigationDependencies: _navigationDependencies(),
                        ),
                        CommunityHubScreen(
                          key: const PageStorageKey<String>('community-hub'),
                          controller: widget.controller,
                          baseUrl: widget.apiBaseUrl,
                          backendMode: widget.backendMode,
                          onOpenAdmin:
                              <String>{'admin', 'super_admin'}.contains(
                            widget.controller.session?.user.role
                                    .toLowerCase() ??
                                'user',
                          )
                                  ? () {
                                      final session = widget.controller.session;
                                      if (session == null) {
                                        return;
                                      }
                                      Navigator.of(context).push<void>(
                                        MaterialPageRoute<void>(
                                          builder: (BuildContext context) =>
                                              AdminCommandCenterScreen(
                                            baseUrl: widget.apiBaseUrl,
                                            accessToken: session.accessToken,
                                            backendMode: widget.backendMode,
                                          ),
                                        ),
                                      );
                                    }
                                  : null,
                        ),
                        _buildClubDestination(),
                        GtePortfolioScreen(
                          key: const PageStorageKey<String>('portfolio-screen'),
                          controller: widget.controller,
                          onOpenPlayer: _openPlayer,
                          onOpenLogin: () => _openLogin(
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
            color: GteShellTheme.panel.withValues(alpha: 0.96),
            border: Border(
                top: BorderSide(color: Colors.white.withValues(alpha: 0.06))),
            boxShadow: <BoxShadow>[
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.28),
                blurRadius: 24,
                offset: const Offset(0, -10),
              ),
            ],
          ),
          child: NavigationBar(
            selectedIndex: GtePrimaryDestination.values.indexOf(
              _route.primaryDestination,
            ),
            onDestinationSelected: (int index) {
              _openPrimaryDestination(GtePrimaryDestination.values[index]);
            },
            destinations: GtePrimaryDestination.values
                .map(
                  (GtePrimaryDestination destination) => NavigationDestination(
                    icon: Icon(destination.icon),
                    selectedIcon: Icon(destination.selectedIcon),
                    label: destination.label,
                  ),
                )
                .toList(growable: false),
          ),
        ),
      ),
    );
  }

  Widget _buildClubDestination() {
    final String? canonicalClubId = _canonicalClubId()?.trim();
    final String? canonicalClubName = _canonicalClubName()?.trim();
    if (canonicalClubId != null && canonicalClubId.isNotEmpty) {
      return ClubHubScreen(
        key: ValueKey<String>('club-${_clubInitialTab.id}-$_clubHostSeed'),
        clubId: canonicalClubId,
        clubName: canonicalClubName != null && canonicalClubName.isNotEmpty
            ? canonicalClubName
            : null,
        baseUrl: widget.apiBaseUrl,
        backendMode: widget.backendMode,
        isAuthenticated: widget.controller.isAuthenticated,
        onOpenLogin: () => _openLogin(
          targetRoute: const GteNavigationRoute.club(),
        ),
        initialTab: _clubInitialTab,
        navigationDependencies: _navigationDependencies(),
      );
    }
    if (!widget.controller.isAuthenticated) {
      return Padding(
        padding: const EdgeInsets.all(20),
        child: GteStatePanel(
          eyebrow: 'CLUB SCOPE',
          title: 'Sign in to open a club workspace',
          message:
              'Guest preview mode does not expose a canonical club. Sign in to continue with a real club context or create one first.',
          icon: Icons.login_outlined,
          accentColor: const Color(0xFF85B8FF),
          actionLabel: 'Sign in',
          onAction: () {
            _openLogin(targetRoute: const GteNavigationRoute.club());
          },
        ),
      );
    }
    return Padding(
      padding: const EdgeInsets.all(20),
      child: GteStatePanel(
        eyebrow: 'CLUB SCOPE',
        title: 'No canonical club is selected',
        message:
            'This signed-in session does not expose a canonical current club. Select a club from the authenticated account context or create one before opening club-scoped surfaces.',
        icon: Icons.shield_outlined,
        accentColor: const Color(0xFF85B8FF),
        actionLabel: 'Open home',
        onAction: () => _openPrimaryDestination(GtePrimaryDestination.home),
      ),
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
            accentColor: const Color(0xFF72F0D8),
            actionLabel: 'Sign in',
            onAction: () {
              _openLogin(targetRoute: const GteNavigationRoute.home());
            },
          ),
        );
      }
      return const Padding(
        padding: EdgeInsets.all(20),
        child: GteStatePanel(
          eyebrow: 'CLUB SCOPE',
          title: 'No canonical club is selected',
          message:
              'This signed-in session does not expose a canonical current club. Select a club from the authenticated account context or create one before using club-scoped home surfaces.',
          icon: Icons.home_outlined,
          accentColor: Color(0xFF72F0D8),
        ),
      );
    }
    return HomeDashboardScreen(
      key: const PageStorageKey<String>('home-dashboard'),
      exchangeController: widget.controller,
      apiBaseUrl: widget.apiBaseUrl,
      backendMode: widget.backendMode,
      onOpenLogin: () => _openLogin(
        targetRoute: const GteNavigationRoute.home(),
      ),
      clubId: _canonicalClubId(),
      clubName: _canonicalClubName(),
      onOpenClubTab: () => _openPrimaryDestination(
        GtePrimaryDestination.club,
      ),
      onOpenCompetitionsTab: () => _openPrimaryDestination(
        GtePrimaryDestination.competitions,
      ),
      onOpenClubSubtab: _openClubSubtab,
      navigationDependencies: _navigationDependencies(),
    );
  }

  void _handleExchangeControllerChanged() {
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

  CompetitionController _buildCompetitionController() {
    return CompetitionController(
      api: CompetitionApi.standard(
        baseUrl: widget.apiBaseUrl,
        mode: widget.backendMode,
      ),
      currentUserId: _competitionUserId,
      currentUserName: _competitionUserName,
    );
  }

  CreatorController _buildCreatorController() {
    return CreatorController(
      api: CreatorApi.standard(
        baseUrl: widget.apiBaseUrl,
        accessToken: widget.controller.session?.accessToken,
        mode: widget.backendMode,
      ),
    );
  }

  ReferralController _buildReferralController() {
    return ReferralController(
      api: ReferralApi.standard(
        baseUrl: widget.apiBaseUrl,
        mode: widget.backendMode,
      ),
    );
  }

  GteNavigationDependencies _navigationDependencies() {
    return GteNavigationDependencies(
      apiBaseUrl: widget.apiBaseUrl,
      backendMode: widget.backendMode,
      currentUserId: _competitionUserId,
      currentUserName: _competitionUserName,
      currentUserRole: widget.controller.session?.user.role,
      currentClubId: _canonicalClubId(),
      currentClubName: _canonicalClubName(),
      accessToken: widget.controller.accessToken,
      isAuthenticated: widget.controller.isAuthenticated,
      onOpenLogin: (BuildContext _) => _openLogin(targetRoute: _route),
      currentUserIdProvider: _resolveCompetitionUserId,
      currentUserNameProvider: _resolveCompetitionUserName,
      currentUserRoleProvider: () => widget.controller.session?.user.role,
      currentClubIdProvider: _canonicalClubId,
      currentClubNameProvider: _canonicalClubName,
      accessTokenProvider: () => widget.controller.accessToken,
      isAuthenticatedProvider: () => widget.controller.isAuthenticated,
    );
  }

  void _openPrimaryDestination(GtePrimaryDestination destination) {
    setState(() {
      _route = _route.withPrimaryDestination(destination);
    });
    widget.onRouteChanged?.call(_route);
    if (destination == GtePrimaryDestination.wallet &&
        widget.controller.isAuthenticated) {
      widget.controller.refreshAccount();
    }
  }

  void _openCompetitionDestination(CompetitionHubDestination destination) {
    setState(() {
      _route = _route.withCompetitionDestination(destination);
    });
    widget.onRouteChanged?.call(_route);
  }

  void _openClubSubtab(ClubNavigationTab tab) {
    setState(() {
      _clubInitialTab = tab;
      _clubHostSeed += 1;
      _route = const GteNavigationRoute.club();
    });
    widget.onRouteChanged?.call(_route);
  }

  Future<bool> _openLogin({
    GteNavigationRoute? targetRoute,
  }) async {
    final bool? signedIn = await Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (BuildContext context) =>
            GteLoginScreen(controller: widget.controller),
      ),
    );
    if (!mounted || signedIn != true) {
      return false;
    }
    final String role =
        widget.controller.session?.user.role.toLowerCase() ?? 'user';
    if (<String>{'admin', 'super_admin'}.contains(role)) {
      Navigator.of(context).push<void>(
        MaterialPageRoute<void>(
          builder: (BuildContext context) => GodModeAdminScreen(
            baseUrl: widget.apiBaseUrl,
            accessToken: widget.controller.session!.accessToken,
            backendMode: widget.backendMode,
          ),
        ),
      );
      return true;
    }
    if (targetRoute != null) {
      setState(() {
        _route = targetRoute;
      });
      widget.onRouteChanged?.call(_route);
    }
    return true;
  }

  Future<void> _openPlayer(String playerId) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => GteExchangePlayerDetailScreen(
          controller: widget.controller,
          playerId: playerId,
          onRequireLogin: () {
            _openLogin(targetRoute: _route);
          },
        ),
      ),
    );
  }

  GteSyncStatusCard _buildModeSyncCard() {
    final Color accent = _route.primaryDestination.accentColor;
    switch (_route.primaryDestination) {
      case GtePrimaryDestination.market:
        return GteSyncStatusCard(
          title: 'Trading operations',
          status: widget.controller.marketError == null
              ? 'Quotes, order rails, and price tape are ready.'
              : 'Market feed degraded. Last good tape is still visible.',
          syncedAt: widget.controller.marketSyncedAt,
          accent: accent,
          isRefreshing: widget.controller.isLoadingMarket,
          onRefresh: () => widget.controller.loadMarket(reset: true),
        );
      case GtePrimaryDestination.competitions:
        return GteSyncStatusCard(
          title: 'Live match center',
          status: _competitionController.discoveryError == null
              ? 'Fixtures, brackets, and replay narratives are synced.'
              : 'Arena feed degraded. Showing the latest competition snapshot.',
          syncedAt: _competitionController.discoverySyncedAt,
          accent: accent,
          isRefreshing: _competitionController.isLoadingDiscovery,
          onRefresh: _competitionController.loadDiscovery,
        );
      case GtePrimaryDestination.community:
        return GteSyncStatusCard(
          title: 'Community network',
          status: widget.controller.isAuthenticated
              ? 'Discovery, creator, and governance surfaces are available.'
              : 'Community is in preview mode. Sign in to unlock participation rails.',
          syncedAt: widget.controller.marketSyncedAt,
          accent: accent,
          isRefreshing: widget.controller.isBootstrapping,
          onRefresh: widget.controller.bootstrap,
        );
      case GtePrimaryDestination.club:
        return GteSyncStatusCard(
          title: 'Club systems',
          status: widget.controller.isAuthenticated
              ? 'Identity, squad, and culture surfaces are unlocked.'
              : 'Guest preview mode is active. Sign in for writable club controls.',
          syncedAt: widget.controller.marketSyncedAt,
          accent: accent,
          isRefreshing: widget.controller.isBootstrapping,
          onRefresh: widget.controller.bootstrap,
        );
      case GtePrimaryDestination.wallet:
        return GteSyncStatusCard(
          title: 'Capital layer',
          status: widget.controller.isAuthenticated
              ? 'Balances, holdings, and ledgers are being protected and reconciled.'
              : 'Wallet is in preview mode. Sign in to unlock funding and execution.',
          syncedAt: widget.controller.portfolioSyncedAt ??
              widget.controller.ordersSyncedAt,
          accent: accent,
          isRefreshing: widget.controller.isLoadingPortfolio ||
              widget.controller.isLoadingOrders,
          onRefresh: widget.controller.isAuthenticated
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
