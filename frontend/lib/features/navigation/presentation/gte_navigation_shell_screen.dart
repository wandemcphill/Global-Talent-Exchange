import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/data/competition_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/competitions_hub/presentation/gte_competitions_hub_screen.dart';
import 'package:gte_frontend/features/competitions_hub/routing/competition_hub_destination.dart';
import 'package:gte_frontend/features/navigation/presentation/gte_home_screen.dart';
import 'package:gte_frontend/features/navigation/routing/gte_navigation_route.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/gte_club_identity_hub_screen.dart';
import 'package:gte_frontend/screens/gte_exchange_player_detail_screen.dart';
import 'package:gte_frontend/screens/gte_login_screen.dart';
import 'package:gte_frontend/screens/gte_market_players_screen.dart';
import 'package:gte_frontend/screens/gte_portfolio_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

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

class _GteNavigationShellScreenState extends State<GteNavigationShellScreen> {
  late GteNavigationRoute _route;
  late CompetitionController _competitionController;
  late String _competitionUserId;
  late String _competitionUserName;

  @override
  void initState() {
    super.initState();
    _route = widget.initialRoute;
    widget.controller.addListener(_handleExchangeControllerChanged);
    _competitionUserId = _resolveCompetitionUserId();
    _competitionUserName = _resolveCompetitionUserName();
    _competitionController = _buildCompetitionController();
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
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const Text('Global Talent Exchange'),
              Text(
                widget.apiBaseUrl,
                style: const TextStyle(fontSize: 12),
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
                        padding: const EdgeInsets.only(right: 16),
                        child: FilledButton.tonal(
                          onPressed: () async {
                            await widget.controller.signOut();
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

            switch (_route.primaryDestination) {
              case GtePrimaryDestination.home:
                return GteHomeScreen(
                  controller: widget.controller,
                  competitionController: _competitionController,
                  onOpenPrimaryDestination: _openPrimaryDestination,
                  onOpenCompetitionDestination: _openCompetitionDestination,
                );
              case GtePrimaryDestination.market:
                return GteMarketPlayersScreen(
                  controller: widget.controller,
                  onOpenPlayer: _openPlayer,
                  onOpenLogin: () => _openLogin(
                    targetRoute: const GteNavigationRoute.market(),
                  ),
                );
              case GtePrimaryDestination.competitions:
                return GteCompetitionsHubScreen(
                  controller: _competitionController,
                  currentDestination: _route.effectiveCompetitionDestination,
                  onDestinationChanged: _openCompetitionDestination,
                  isAuthenticated: widget.controller.isAuthenticated,
                  onOpenLogin: () => _openLogin(
                    targetRoute: GteNavigationRoute.competitions(
                      destination: _route.effectiveCompetitionDestination,
                    ),
                  ),
                );
              case GtePrimaryDestination.club:
                return GteClubIdentityHubScreen(
                  controller: widget.controller,
                  apiBaseUrl: widget.apiBaseUrl,
                  backendMode: widget.backendMode,
                  onOpenLogin: () => _openLogin(
                    targetRoute: const GteNavigationRoute.club(),
                  ),
                );
              case GtePrimaryDestination.wallet:
                return GtePortfolioScreen(
                  controller: widget.controller,
                  onOpenPlayer: _openPlayer,
                  onOpenLogin: () => _openLogin(
                    targetRoute: const GteNavigationRoute.wallet(),
                  ),
                );
            }
          },
        ),
        bottomNavigationBar: NavigationBar(
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
    );
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

  void _handleExchangeControllerChanged() {
    final String nextUserId = _resolveCompetitionUserId();
    final String nextUserName = _resolveCompetitionUserName();
    if (nextUserId == _competitionUserId &&
        nextUserName == _competitionUserName) {
      return;
    }
    _competitionUserId = nextUserId;
    _competitionUserName = nextUserName;
    _competitionController.updateCurrentUser(
      userId: nextUserId,
      userName: nextUserName,
    );
    _competitionController.loadDiscovery();
  }

  void _openPrimaryDestination(GtePrimaryDestination destination) {
    _setRoute(_route.withPrimaryDestination(destination));
    if (destination == GtePrimaryDestination.wallet &&
        widget.controller.isAuthenticated) {
      widget.controller.refreshAccount();
    }
    if (destination == GtePrimaryDestination.competitions) {
      _competitionController.bootstrap();
    }
  }

  void _openCompetitionDestination(CompetitionHubDestination destination) {
    _competitionController.bootstrap();
    _setRoute(_route.withCompetitionDestination(destination));
  }

  void _setRoute(GteNavigationRoute nextRoute) {
    if (_route == nextRoute) {
      return;
    }
    setState(() {
      _route = nextRoute;
    });
    widget.onRouteChanged?.call(nextRoute);
  }

  Future<void> _openLogin({
    GteNavigationRoute? targetRoute,
  }) async {
    final bool? signedIn = await Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (BuildContext context) =>
            GteLoginScreen(controller: widget.controller),
      ),
    );
    if (!mounted || signedIn != true) {
      return;
    }
    if (targetRoute != null) {
      _setRoute(targetRoute);
    }
  }

  Future<void> _openPlayer(String playerId) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => GteExchangePlayerDetailScreen(
          controller: widget.controller,
          playerId: playerId,
          onRequireLogin: () {
            _openLogin(
              targetRoute: const GteNavigationRoute.market(),
            );
          },
        ),
      ),
    );
  }

  String _resolveCompetitionUserId() {
    final String? sessionUserId = widget.controller.session?.user.id.trim();
    if (sessionUserId != null && sessionUserId.isNotEmpty) {
      return sessionUserId;
    }
    return 'demo-user';
  }

  String _resolveCompetitionUserName() {
    final String? displayName =
        widget.controller.session?.user.displayName?.trim();
    if (displayName != null && displayName.isNotEmpty) {
      return displayName;
    }
    final String username =
        widget.controller.session?.user.username.trim() ?? '';
    if (username.isNotEmpty) {
      return username;
    }
    return 'Demo Fan';
  }
}
