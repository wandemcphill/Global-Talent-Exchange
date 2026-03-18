import 'dart:async';

import 'package:flutter/material.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/app_routes/gte_route_data.dart';
import 'package:gte_frontend/features/app_routes/gte_feature_route_support.dart';
import 'package:gte_frontend/features/app_routes/gte_navigation_helpers.dart';
import 'package:gte_frontend/features/club_identity/dynasty/presentation/dynasty_leaderboard_screen.dart';
import 'package:gte_frontend/features/club_identity/dynasty/presentation/dynasty_screen.dart';
import 'package:gte_frontend/features/club_identity/dynasty/presentation/era_history_screen.dart';
import 'package:gte_frontend/features/club_identity/jerseys/presentation/club_identity_controller.dart';
import 'package:gte_frontend/features/club_identity/jerseys/presentation/club_identity_screen.dart';
import 'package:gte_frontend/features/club_identity/jerseys/presentation/identity_preview_screen.dart';
import 'package:gte_frontend/features/club_identity/reputation/presentation/prestige_leaderboard_screen.dart';
import 'package:gte_frontend/features/club_identity/reputation/presentation/reputation_controller.dart';
import 'package:gte_frontend/features/club_identity/reputation/presentation/reputation_history_screen.dart';
import 'package:gte_frontend/features/club_identity/reputation/presentation/reputation_screen.dart';
import 'package:gte_frontend/features/club_identity/trophies/presentation/honors_timeline_screen.dart';
import 'package:gte_frontend/features/club_identity/trophies/presentation/trophy_cabinet_screen.dart';
import 'package:gte_frontend/features/club_identity/trophies/presentation/trophy_leaderboard_screen.dart';
import 'package:gte_frontend/features/club_sale_market/club_sale_market.dart';
import 'package:gte_frontend/features/creator_league_admin/creator_league_admin.dart';
import 'package:gte_frontend/features/creator_share_market/creator_share_market.dart';
import 'package:gte_frontend/features/creator_stadium_monetization/creator_stadium_monetization.dart';
import 'package:gte_frontend/features/fan_prediction/fan_prediction.dart';
import 'package:gte_frontend/features/football_world_simulation/football_world_simulation.dart';
import 'package:gte_frontend/features/gift_economy_admin/gift_economy_admin.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/features/player_card_marketplace/player_card_marketplace.dart';
import 'package:gte_frontend/features/streamer_tournament_engine/streamer_tournament_engine.dart';
import 'package:gte_frontend/screens/competitions/competition_create_screen.dart';
import 'package:gte_frontend/screens/competitions/competition_detail_screen.dart';
import 'package:gte_frontend/screens/competitions/competition_discovery_screen.dart';
import 'package:gte_frontend/screens/competitions/competition_join_screen.dart';
import 'package:gte_frontend/screens/competitions/competition_share_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';

part 'gte_feature_route_builders.dart';

class GteAppRouteRegistry {
  const GteAppRouteRegistry({
    required this.dependencies,
  });

  final GteNavigationDependencies dependencies;

  List<GteAppRouteRegistration> get registrations =>
      GteAppRouteCatalog.registrations;

  Route<T> routeFor<T>(
    GteAppRouteData route, {
    RouteSettings? settings,
  }) {
    return MaterialPageRoute<T>(
      settings: settings ??
          RouteSettings(
            name: route.toUri().toString(),
            arguments: route,
          ),
      builder: (BuildContext context) => _GteGuardedRouteHost(
        registry: this,
        route: route,
      ),
    );
  }

  Route<dynamic>? onGenerateRoute(RouteSettings settings) {
    final GteAppRouteData? route = parseSettings(settings);
    if (route == null) {
      return null;
    }
    return routeFor<dynamic>(route, settings: settings);
  }

  Route<dynamic> onUnknownRoute(RouteSettings settings) {
    return MaterialPageRoute<dynamic>(
      settings: settings,
      builder: (BuildContext context) => _RouteStateScreen(
        title: 'Route unavailable',
        message: settings.name == null
            ? 'No route information was provided.'
            : 'No screen is registered for ${settings.name}.',
        icon: Icons.alt_route_outlined,
      ),
    );
  }

  GteAppRouteData? parseSettings(RouteSettings settings) {
    final GteAppRouteData? routeFromArguments =
        GteAppRouteParser.parse(settings.arguments);
    if (routeFromArguments != null) {
      return routeFromArguments;
    }
    return GteAppRouteParser.parse(settings.name);
  }

  Widget buildScreen(BuildContext context, GteAppRouteData route) {
    final VoidCallback? openLogin = dependencies.onOpenLogin == null
        ? null
        : () {
            dependencies.onOpenLogin!.call(context);
          };
    if (route is CompetitionsDiscoveryRouteData) {
      return CompetitionDiscoveryScreen(
        baseUrl: dependencies.apiBaseUrl,
        backendMode: dependencies.backendMode,
        currentUserId: dependencies.currentUserId,
        currentUserName: dependencies.currentUserName,
        isAuthenticated: dependencies.isAuthenticated,
        onOpenLogin: openLogin,
      );
    }
    if (route is CompetitionCreateRouteData) {
      return _CompetitionCreateRouteScreen(
        dependencies: dependencies,
      );
    }
    if (route is CompetitionDetailRouteData) {
      return _CompetitionDetailRouteScreen(
        dependencies: dependencies,
        route: route,
      );
    }
    if (route is CompetitionJoinRouteData) {
      return _CompetitionPreloadRouteScreen(
        dependencies: dependencies,
        competitionId: route.competitionId,
        inviteCode: route.inviteCode,
        loadingTitle: 'Loading competition',
        builder: (CompetitionController controller) {
          return CompetitionJoinScreen(controller: controller);
        },
      );
    }
    if (route is CompetitionShareRouteData) {
      return _CompetitionPreloadRouteScreen(
        dependencies: dependencies,
        competitionId: route.competitionId,
        loadingTitle: 'Loading competition',
        builder: (CompetitionController controller) {
          return CompetitionShareScreen(controller: controller);
        },
      );
    }
    if (route is CompetitionWorldSuperCupRouteData) {
      return CompetitionDiscoveryScreen(
        baseUrl: dependencies.apiBaseUrl,
        backendMode: dependencies.backendMode,
        currentUserId: dependencies.currentUserId,
        currentUserName: dependencies.currentUserName,
        isAuthenticated: dependencies.isAuthenticated,
        onOpenLogin: openLogin,
      );
    }
    if (route is ClubIdentityJerseysRouteData) {
      return ClubIdentityScreen(
        clubId: route.clubId,
        initialClubName: route.clubName,
        apiBaseUrl: dependencies.apiBaseUrl,
        backendMode: dependencies.backendMode,
        repository: dependencies.clubIdentityRepository,
      );
    }
    if (route is ClubReputationOverviewRouteData) {
      return ClubReputationOverviewScreen(
        clubId: route.clubId,
        clubName: route.clubName,
        baseUrl: dependencies.apiBaseUrl,
        mode: dependencies.backendMode,
        repository: dependencies.reputationRepository,
      );
    }
    if (route is ClubReputationHistoryRouteData) {
      return _ReputationSubscreenRouteScreen(
        dependencies: dependencies,
        clubId: route.clubId,
        clubName: route.clubName,
        builder: (ReputationController controller) {
          return ReputationHistoryScreen(controller: controller);
        },
      );
    }
    if (route is ClubReputationLeaderboardRouteData) {
      return _ReputationSubscreenRouteScreen(
        dependencies: dependencies,
        clubId: route.clubId,
        clubName: route.clubName,
        builder: (ReputationController controller) {
          return PrestigeLeaderboardScreen(controller: controller);
        },
      );
    }
    if (route is ClubTrophyCabinetRouteData) {
      return TrophyCabinetScreen(
        clubId: route.clubId,
        clubName: route.clubName,
        repository: dependencies.createTrophyCabinetRepository(),
        initialFilter: route.filter,
      );
    }
    if (route is ClubTrophyTimelineRouteData) {
      return HonorsTimelineScreen(
        clubId: route.clubId,
        clubName: route.clubName,
        repository: dependencies.createTrophyCabinetRepository(),
        initialFilter: route.filter,
      );
    }
    if (route is ClubTrophyLeaderboardRouteData) {
      return TrophyLeaderboardScreen(
        repository: dependencies.createTrophyCabinetRepository(),
        initialFilter: route.filter,
      );
    }
    if (route is ClubDynastyOverviewRouteData) {
      return DynastyScreen(
        clubId: route.clubId,
        repository: dependencies.dynastyRepository,
        baseUrl: dependencies.apiBaseUrl,
        backendMode: dependencies.backendMode,
        onOpenTimeline: () {
          Navigator.of(context).push<void>(
            routeFor<void>(
              ClubDynastyHistoryRouteData(
                clubId: route.clubId,
                clubName: route.clubName,
              ),
            ),
          );
        },
        onOpenLeaderboard: () {
          Navigator.of(context).push<void>(
            routeFor<void>(
              ClubDynastyLeaderboardRouteData(
                clubId: route.clubId,
                clubName: route.clubName,
              ),
            ),
          );
        },
      );
    }
    if (route is ClubDynastyHistoryRouteData) {
      return EraHistoryScreen(
        clubId: route.clubId,
        repository: dependencies.dynastyRepository,
        baseUrl: dependencies.apiBaseUrl,
        backendMode: dependencies.backendMode,
      );
    }
    if (route is ClubDynastyLeaderboardRouteData) {
      return DynastyLeaderboardScreen(
        repository: dependencies.dynastyRepository,
        baseUrl: dependencies.apiBaseUrl,
        backendMode: dependencies.backendMode,
        onOpenClub: (String clubId) {
          Navigator.of(context).push<void>(
            routeFor<void>(
              ClubDynastyOverviewRouteData(clubId: clubId),
            ),
          );
        },
      );
    }
    if (route is ClubReplaysRouteData) {
      return _ReplayPreviewRouteScreen(
        dependencies: dependencies,
        clubId: route.clubId,
        clubName: route.clubName,
      );
    }
    if (route is StreamerTournamentsListRouteData) {
      return _buildStreamerTournamentsListScreen(
        context,
        dependencies,
      );
    }
    if (route is StreamerTournamentDetailRouteData) {
      return _buildStreamerTournamentDetailScreen(
        context,
        dependencies,
        route,
      );
    }
    if (route is FanPredictionMatchRouteData) {
      return _buildFanPredictionMatchScreen(
        context,
        dependencies,
        route,
      );
    }
    if (route is PlayerCardsBrowseRouteData) {
      return _buildPlayerCardsBrowseScreen(
        context,
        dependencies,
      );
    }
    if (route is PlayerCardDetailRouteData) {
      return _buildPlayerCardDetailScreen(
        context,
        dependencies,
        route,
      );
    }
    if (route is PlayerCardsInventoryRouteData) {
      return _buildPlayerCardsInventoryScreen(
        context,
        dependencies,
      );
    }
    if (route is CreatorShareMarketClubRouteData) {
      return _buildCreatorShareMarketClubScreen(
        context,
        dependencies,
        route,
      );
    }
    if (route is CreatorShareMarketAdminControlRouteData) {
      return _buildCreatorShareMarketAdminControlScreen(
        context,
        dependencies,
      );
    }
    if (route is ClubSaleMarketListingsRouteData) {
      return _buildClubSaleMarketListingsScreen(
        context,
        dependencies,
      );
    }
    if (route is ClubSaleMarketDetailRouteData) {
      return _buildClubSaleMarketDetailScreen(
        context,
        dependencies,
        route,
      );
    }
    if (route is ClubSaleMarketOwnerOffersRouteData) {
      return _buildClubSaleMarketOwnerOffersScreen(
        context,
        dependencies,
        route,
      );
    }
    if (route is WorldOverviewRouteData) {
      return _buildWorldOverviewScreen(
        context,
        dependencies,
      );
    }
    if (route is WorldClubContextRouteData) {
      return _buildWorldClubContextScreen(
        context,
        dependencies,
        route,
      );
    }
    if (route is WorldCompetitionContextRouteData) {
      return _buildWorldCompetitionContextScreen(
        context,
        dependencies,
        route,
      );
    }
    if (route is NationalTeamCompetitionsRouteData) {
      return _buildNationalTeamCompetitionsScreen(
        context,
        dependencies,
      );
    }
    if (route is NationalTeamEntryRouteData) {
      return _buildNationalTeamEntryScreen(
        context,
        dependencies,
        route,
      );
    }
    if (route is NationalTeamHistoryRouteData) {
      return _buildNationalTeamHistoryScreen(
        context,
        dependencies,
      );
    }
    if (route is FootballTransferCenterRouteData) {
      return _buildFootballTransferCenterScreen(
        context,
        dependencies,
        route,
      );
    }
    if (route is CreatorStadiumClubRouteData) {
      return _buildCreatorStadiumClubScreen(
        context,
        dependencies,
        route,
      );
    }
    if (route is CreatorStadiumMatchRouteData) {
      return _buildCreatorStadiumMatchScreen(
        context,
        dependencies,
        route,
      );
    }
    if (route is CreatorStadiumAdminControlRouteData) {
      return _buildCreatorStadiumAdminControlScreen(
        context,
        dependencies,
      );
    }
    if (route is CreatorLeagueFinancialReportRouteData) {
      return _buildCreatorLeagueFinancialReportScreen(
        context,
        dependencies,
        route,
      );
    }
    if (route is CreatorLeagueSettlementsRouteData) {
      return _buildCreatorLeagueSettlementsScreen(
        context,
        dependencies,
        route,
      );
    }
    if (route is GiftStabilizerRouteData) {
      return _buildGiftStabilizerScreen(
        context,
        dependencies,
      );
    }
    return _RouteStateScreen(
      title: 'Route unavailable',
      message: 'No renderer is registered for ${route.name}.',
      icon: Icons.alt_route_outlined,
    );
  }
}

class _GteGuardedRouteHost extends StatefulWidget {
  const _GteGuardedRouteHost({
    required this.registry,
    required this.route,
  });

  final GteAppRouteRegistry registry;
  final GteAppRouteData route;

  @override
  State<_GteGuardedRouteHost> createState() => _GteGuardedRouteHostState();
}

class _GteGuardedRouteHostState extends State<_GteGuardedRouteHost> {
  GteGuardResolution? _resolution;
  Object? _resolutionError;

  @override
  void initState() {
    super.initState();
    _resolveRoute();
  }

  @override
  void didUpdateWidget(covariant _GteGuardedRouteHost oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.route.toUri() != widget.route.toUri()) {
      _resolveRoute();
    }
  }

  Future<void> _resolveRoute() async {
    setState(() {
      _resolution = null;
      _resolutionError = null;
    });
    try {
      final GteGuardResolution resolution = await GteNavigationGuardResolver(
        dependencies: widget.registry.dependencies,
      ).resolve(widget.route);
      if (!mounted) {
        return;
      }
      setState(() {
        _resolution = resolution;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _resolutionError = error;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_resolutionError != null) {
      return _RouteStateScreen(
        title: 'Navigation unavailable',
        message: _resolutionError.toString(),
        actionLabel: 'Retry',
        onAction: _resolveRoute,
        icon: Icons.route_outlined,
      );
    }
    if (_resolution == null) {
      return const _RouteLoadingScreen();
    }
    return widget.registry.buildScreen(context, _resolution!.route);
  }
}

class _CompetitionCreateRouteScreen extends StatefulWidget {
  const _CompetitionCreateRouteScreen({
    required this.dependencies,
  });

  final GteNavigationDependencies dependencies;

  @override
  State<_CompetitionCreateRouteScreen> createState() =>
      _CompetitionCreateRouteScreenState();
}

class _CompetitionCreateRouteScreenState
    extends State<_CompetitionCreateRouteScreen> {
  late final CompetitionController _controller;

  @override
  void initState() {
    super.initState();
    _controller = CompetitionController(
      api: widget.dependencies.createCompetitionApi(),
      currentUserId: widget.dependencies.currentUserId,
      currentUserName: widget.dependencies.currentUserName,
    )..startNewDraft();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return CompetitionCreateScreen(controller: _controller);
  }
}

class _CompetitionDetailRouteScreen extends StatefulWidget {
  const _CompetitionDetailRouteScreen({
    required this.dependencies,
    required this.route,
  });

  final GteNavigationDependencies dependencies;
  final CompetitionDetailRouteData route;

  @override
  State<_CompetitionDetailRouteScreen> createState() =>
      _CompetitionDetailRouteScreenState();
}

class _CompetitionDetailRouteScreenState
    extends State<_CompetitionDetailRouteScreen> {
  late final CompetitionController _controller;

  @override
  void initState() {
    super.initState();
    _controller = CompetitionController(
      api: widget.dependencies.createCompetitionApi(),
      currentUserId: widget.dependencies.currentUserId,
      currentUserName: widget.dependencies.currentUserName,
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return CompetitionDetailScreen(
      controller: _controller,
      competitionId: widget.route.competitionId,
      navigationDependencies: widget.dependencies,
    );
  }
}

class _CompetitionPreloadRouteScreen extends StatefulWidget {
  const _CompetitionPreloadRouteScreen({
    required this.dependencies,
    required this.competitionId,
    required this.loadingTitle,
    required this.builder,
    this.inviteCode,
  });

  final GteNavigationDependencies dependencies;
  final String competitionId;
  final String? inviteCode;
  final String loadingTitle;
  final Widget Function(CompetitionController controller) builder;

  @override
  State<_CompetitionPreloadRouteScreen> createState() =>
      _CompetitionPreloadRouteScreenState();
}

class _CompetitionPreloadRouteScreenState
    extends State<_CompetitionPreloadRouteScreen> {
  late final CompetitionController _controller;
  String? _errorMessage;
  bool _isPrimed = false;

  @override
  void initState() {
    super.initState();
    _controller = CompetitionController(
      api: widget.dependencies.createCompetitionApi(),
      currentUserId: widget.dependencies.currentUserId,
      currentUserName: widget.dependencies.currentUserName,
    );
    _primeCompetition();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _primeCompetition() async {
    setState(() {
      _isPrimed = false;
      _errorMessage = null;
    });
    try {
      await _controller.openCompetition(
        widget.competitionId,
        inviteCode: widget.inviteCode,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _isPrimed = true;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _errorMessage = AppFeedback.messageFor(error);
        _isPrimed = true;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_isPrimed && _controller.selectedCompetition == null) {
      return _RouteLoadingScreen(title: widget.loadingTitle);
    }
    if (_errorMessage != null && _controller.selectedCompetition == null) {
      return _RouteStateScreen(
        title: 'Competition unavailable',
        message: _errorMessage!,
        actionLabel: 'Retry',
        onAction: _primeCompetition,
        icon: Icons.groups_outlined,
      );
    }
    return widget.builder(_controller);
  }
}

class _ReputationSubscreenRouteScreen extends StatefulWidget {
  const _ReputationSubscreenRouteScreen({
    required this.dependencies,
    required this.clubId,
    required this.builder,
    this.clubName,
  });

  final GteNavigationDependencies dependencies;
  final String clubId;
  final String? clubName;
  final Widget Function(ReputationController controller) builder;

  @override
  State<_ReputationSubscreenRouteScreen> createState() =>
      _ReputationSubscreenRouteScreenState();
}

class _ReputationSubscreenRouteScreenState
    extends State<_ReputationSubscreenRouteScreen> {
  late final ReputationController _controller;
  String? _errorMessage;
  bool _isReady = false;

  @override
  void initState() {
    super.initState();
    _controller = ReputationController(
      repository: widget.dependencies.createReputationRepository(),
      clubId: widget.clubId,
      clubName: widget.clubName,
    );
    _prime();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _prime() async {
    setState(() {
      _isReady = false;
      _errorMessage = null;
    });
    try {
      await _controller.load();
      if (!mounted) {
        return;
      }
      setState(() {
        _isReady = true;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _errorMessage = AppFeedback.messageFor(error);
        _isReady = true;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_isReady && !_controller.hasData) {
      return const _RouteLoadingScreen(title: 'Loading reputation');
    }
    if (_errorMessage != null && !_controller.hasData) {
      return _RouteStateScreen(
        title: 'Reputation unavailable',
        message: _errorMessage!,
        actionLabel: 'Retry',
        onAction: _prime,
        icon: Icons.stars_outlined,
      );
    }
    return widget.builder(_controller);
  }
}

class _ReplayPreviewRouteScreen extends StatefulWidget {
  const _ReplayPreviewRouteScreen({
    required this.dependencies,
    required this.clubId,
    this.clubName,
  });

  final GteNavigationDependencies dependencies;
  final String clubId;
  final String? clubName;

  @override
  State<_ReplayPreviewRouteScreen> createState() =>
      _ReplayPreviewRouteScreenState();
}

class _ReplayPreviewRouteScreenState extends State<_ReplayPreviewRouteScreen> {
  late final ClubIdentityController _controller;
  String? _errorMessage;
  bool _isReady = false;

  @override
  void initState() {
    super.initState();
    _controller = ClubIdentityController(
      clubId: widget.clubId,
      initialClubName: widget.clubName,
      repository: widget.dependencies.createClubIdentityRepository(),
    );
    _prime();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _prime() async {
    setState(() {
      _isReady = false;
      _errorMessage = null;
    });
    try {
      await _controller.load();
      if (!mounted) {
        return;
      }
      setState(() {
        _isReady = true;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _errorMessage = AppFeedback.messageFor(error);
        _isReady = true;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_isReady && _controller.identity == null) {
      return const _RouteLoadingScreen(title: 'Loading replay surfaces');
    }
    if (_errorMessage != null && _controller.identity == null) {
      return _RouteStateScreen(
        title: 'Replay preview unavailable',
        message: _errorMessage!,
        actionLabel: 'Retry',
        onAction: _prime,
        icon: Icons.slideshow_outlined,
      );
    }
    return IdentityPreviewScreen(controller: _controller);
  }
}

class _RouteLoadingScreen extends StatelessWidget {
  const _RouteLoadingScreen({
    this.title = 'Opening route',
  });

  final String title;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              const CircularProgressIndicator(),
              const SizedBox(height: 16),
              Text(
                title,
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _RouteStateScreen extends StatelessWidget {
  const _RouteStateScreen({
    required this.title,
    required this.message,
    required this.icon,
    this.actionLabel,
    this.onAction,
  });

  final String title;
  final String message;
  final IconData icon;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 560),
              child: GteStatePanel(
                title: title,
                message: message,
                actionLabel: actionLabel,
                onAction: onAction,
                icon: icon,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
