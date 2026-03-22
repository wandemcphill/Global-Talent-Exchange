part of 'gte_app_route_registry.dart';

Widget _publicFeatureScreen({
  required GteNavigationDependencies dependencies,
  required String loadingTitle,
  required IconData icon,
  required Color accentColor,
  required Future<GteFeatureRouteResult> Function() load,
}) {
  return _featureScreen(
    dependencies: dependencies,
    access: GteFeatureRouteAccess.public,
    loadingTitle: loadingTitle,
    lockedTitle: 'Sign in required',
    lockedMessage: '',
    forbiddenTitle: 'Feature unavailable',
    forbiddenMessage: '',
    icon: icon,
    accentColor: accentColor,
    load: load,
  );
}

Widget _authenticatedFeatureScreen({
  required GteNavigationDependencies dependencies,
  required String loadingTitle,
  required IconData icon,
  required Color accentColor,
  required Future<GteFeatureRouteResult> Function() load,
}) {
  return _featureScreen(
    dependencies: dependencies,
    access: GteFeatureRouteAccess.authenticated,
    loadingTitle: loadingTitle,
    lockedTitle: 'Sign in required',
    lockedMessage:
        'This route is available after authentication and will retry automatically after a successful login.',
    forbiddenTitle: 'You do not have access to this route',
    forbiddenMessage:
        'This feature is protected and requires a valid signed-in session.',
    icon: icon,
    accentColor: accentColor,
    load: load,
  );
}

Widget _adminFeatureScreen({
  required GteNavigationDependencies dependencies,
  required String loadingTitle,
  required IconData icon,
  required Color accentColor,
  required Future<GteFeatureRouteResult> Function() load,
}) {
  return _featureScreen(
    dependencies: dependencies,
    access: GteFeatureRouteAccess.admin,
    loadingTitle: loadingTitle,
    lockedTitle: 'Admin sign-in required',
    lockedMessage:
        'This admin route requires a signed-in account before the control surface can mount.',
    forbiddenTitle: 'Admin permission required',
    forbiddenMessage: 'This control surface is available only to admin roles.',
    icon: icon,
    accentColor: accentColor,
    load: load,
  );
}

Widget _featureScreen({
  required GteNavigationDependencies dependencies,
  required GteFeatureRouteAccess access,
  required String loadingTitle,
  required String lockedTitle,
  required String lockedMessage,
  required String forbiddenTitle,
  required String forbiddenMessage,
  required IconData icon,
  required Color accentColor,
  required Future<GteFeatureRouteResult> Function() load,
}) {
  return GteAsyncFeatureRouteScreen(
    dependencies: dependencies,
    access: access,
    loadingTitle: loadingTitle,
    lockedTitle: lockedTitle,
    lockedMessage: lockedMessage,
    lockedIcon: icon,
    lockedAccentColor: accentColor,
    forbiddenTitle: forbiddenTitle,
    forbiddenMessage: forbiddenMessage,
    forbiddenIcon: icon,
    forbiddenAccentColor: accentColor,
    load: load,
  );
}

VoidCallback? _loginAction(
  BuildContext context,
  GteNavigationDependencies dependencies,
) {
  if (dependencies.onOpenLogin == null) {
    return null;
  }
  return () {
    unawaited(dependencies.onOpenLogin!.call(context));
  };
}

Widget _authGuardedScreen({
  required BuildContext context,
  required GteNavigationDependencies dependencies,
  required Widget child,
  required IconData icon,
  bool adminOnly = false,
}) {
  if (!dependencies.isAuthenticated) {
    return _RouteStateScreen(
      title: adminOnly ? 'Admin sign-in required' : 'Sign in required',
      message: adminOnly
          ? 'This control surface requires an authenticated admin session.'
          : 'This feature becomes available after sign-in.',
      icon: icon,
      actionLabel: dependencies.onOpenLogin == null ? null : 'Sign in',
      onAction: _loginAction(context, dependencies),
    );
  }
  if (adminOnly && !dependencies.isAdminRole) {
    return _RouteStateScreen(
      title: 'Admin permission required',
      message:
          'This control surface is visible only to admin roles in the current session.',
      icon: icon,
    );
  }
  return child;
}

Future<T> _withApi<T>(
  GteNavigationDependencies dependencies,
  Future<T> Function(dynamic api) live,
  FutureOr<T> Function() fixture,
) async {
  final dynamic api = dependencies.createAuthedApi();
  switch (dependencies.backendMode) {
    case GteBackendMode.fixture:
      return await fixture();
    case GteBackendMode.live:
      return live(api);
    case GteBackendMode.liveThenFixture:
      try {
        return await live(api);
      } on GteApiException catch (error) {
        if (error.supportsFixtureFallback) {
          return await fixture();
        }
        rethrow;
      } catch (_) {
        return await fixture();
      }
  }
}

GteFeatureRouteResult _featureUnavailable({
  required String title,
  required IconData icon,
  required Color accentColor,
  required Object error,
}) {
  return GteFeatureRouteResult.unavailable(
    title: title,
    message: _errorMessage(error),
    icon: icon,
    accentColor: accentColor,
    actionLabel: 'Retry',
  );
}

GteFeatureRouteAction _routeAction({
  required GteNavigationDependencies dependencies,
  required GteAppRouteData route,
  required String label,
  required IconData icon,
  bool primary = false,
}) {
  return GteFeatureRouteAction(
    label: label,
    icon: icon,
    primary: primary,
    onPressed: _pushRouteHandler(dependencies, route),
  );
}

GteFeatureRouteAction _noticeAction({
  required GteNavigationDependencies dependencies,
  required String label,
  required IconData icon,
  required String message,
  bool primary = false,
  bool requireAuthentication = false,
}) {
  return GteFeatureRouteAction(
    label: label,
    icon: icon,
    primary: primary,
    onPressed: (BuildContext context) async {
      if (requireAuthentication && !dependencies.isAuthenticated) {
        final bool signedIn =
            await dependencies.onOpenLogin?.call(context) ?? false;
        if (!signedIn || !context.mounted) {
          return;
        }
      }
      await _showRouteNotice(context, message);
    },
  );
}

Future<void> Function(BuildContext context) _pushRouteHandler(
  GteNavigationDependencies dependencies,
  GteAppRouteData route,
) {
  return (BuildContext context) {
    return GteNavigationHelpers.pushRoute<void>(
      context,
      route: route,
      dependencies: dependencies,
    );
  };
}

Future<void> _showRouteNotice(BuildContext context, String message) async {
  final ScaffoldMessengerState? messenger = ScaffoldMessenger.maybeOf(context);
  messenger?.showSnackBar(SnackBar(content: Text(message)));
}

Widget _featureLoadingShell(BuildContext context, {required String title}) {
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
            Text(title, style: Theme.of(context).textTheme.titleMedium),
          ],
        ),
      ),
    ),
  );
}

Map<String, dynamic> _asMap(Object? value) {
  if (value is Map<String, dynamic>) {
    return value;
  }
  if (value is Map) {
    return value.map(
      (Object? key, Object? entryValue) =>
          MapEntry<String, dynamic>(key.toString(), entryValue),
    );
  }
  return <String, dynamic>{};
}

List<dynamic> _asList(Object? value) {
  if (value is List<dynamic>) {
    return value;
  }
  if (value is List) {
    return value.toList(growable: false);
  }
  return const <dynamic>[];
}

Object? _pick(Map<String, dynamic> json, List<String> keys) {
  for (final String key in keys) {
    final Object? value = json[key];
    if (value != null) {
      return value;
    }
  }
  return null;
}

Map<String, dynamic> _mapFromMap(Map<String, dynamic> json, List<String> keys) {
  return _asMap(_pick(json, keys));
}

List<dynamic> _listFromMap(Map<String, dynamic> json, List<String> keys) {
  return _asList(_pick(json, keys));
}

String _stringFromMap(
  Map<String, dynamic> json,
  List<String> keys, {
  String fallback = '--',
}) {
  return _stringOrNull(_pick(json, keys)) ?? fallback;
}

String? _stringOrNull(Object? value) {
  if (value == null) {
    return null;
  }
  final String resolved = value.toString().trim();
  return resolved.isEmpty ? null : resolved;
}

double _numberFromMap(
  Map<String, dynamic> json,
  List<String> keys, {
  double fallback = 0,
}) {
  final Object? value = _pick(json, keys);
  if (value is num) {
    return value.toDouble();
  }
  return double.tryParse(value?.toString() ?? '') ?? fallback;
}

int _intFromMap(
  Map<String, dynamic> json,
  List<String> keys, {
  int fallback = 0,
}) {
  final Object? value = _pick(json, keys);
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  return int.tryParse(value?.toString() ?? '') ?? fallback;
}

bool _boolFromMap(
  Map<String, dynamic> json,
  List<String> keys, {
  bool fallback = false,
}) {
  final Object? value = _pick(json, keys);
  if (value is bool) {
    return value;
  }
  final String normalized = value?.toString().trim().toLowerCase() ?? '';
  if (<String>{'1', 'true', 'yes', 'on'}.contains(normalized)) {
    return true;
  }
  if (<String>{'0', 'false', 'no', 'off'}.contains(normalized)) {
    return false;
  }
  return fallback;
}

String _creditsLabel(num value) {
  final bool whole = value == value.roundToDouble();
  return '${value.toStringAsFixed(whole ? 0 : 2)} cr';
}

String _clubLabel(String? clubName, String clubId) {
  return clubName?.trim().isNotEmpty == true ? clubName!.trim() : clubId;
}

String _errorMessage(Object error) {
  if (error is GteApiException) {
    return error.message;
  }
  return AppFeedback.messageFor(error);
}

Map<String, dynamic> _latestTransfer(Map<String, dynamic> history) {
  final List<dynamic> transfers = _listFromMap(
    history,
    <String>['transfers', 'executions', 'completed_transfers', 'items'],
  );
  if (transfers.isEmpty) {
    return const <String, dynamic>{};
  }
  return _asMap(transfers.first);
}

Map<String, dynamic> _highestPricedOffer(List<dynamic> offers) {
  Map<String, dynamic> winner = const <String, dynamic>{};
  double bestPrice = -1;
  for (final dynamic item in offers) {
    final Map<String, dynamic> offer = _asMap(item);
    final double price = _numberFromMap(
      offer,
      <String>['offer_price_credits', 'offerPriceCredits'],
      fallback: -1,
    );
    if (price > bestPrice) {
      bestPrice = price;
      winner = offer;
    }
  }
  return winner;
}

String? _extractCreatorLeagueSeasonId(Map<String, dynamic> overview) {
  final Map<String, dynamic> current =
      _mapFromMap(overview, <String>['current_season', 'currentSeason']);
  if (current.isNotEmpty) {
    return _stringOrNull(
        _pick(current, <String>['id', 'season_id', 'seasonId']));
  }
  return _stringOrNull(
    _pick(
      overview,
      <String>['current_season_id', 'currentSeasonId', 'season_id', 'seasonId'],
    ),
  );
}

Widget _buildStreamerTournamentsListScreen(
  BuildContext context,
  GteNavigationDependencies dependencies,
) {
  return StreamerTournamentEngineScreen(
    baseUrl: dependencies.apiBaseUrl,
    backendMode: dependencies.backendMode,
    accessToken: dependencies.accessToken,
    currentUserId: dependencies.currentUserId,
    currentUserRole: dependencies.currentUserRole,
    onOpenLogin: dependencies.onOpenLogin == null
        ? null
        : () {
            dependencies.onOpenLogin!.call(context);
          },
  );
}

Widget _buildStreamerTournamentDetailScreen(
  BuildContext context,
  GteNavigationDependencies dependencies,
  StreamerTournamentDetailRouteData route,
) {
  return StreamerTournamentEngineScreen(
    baseUrl: dependencies.apiBaseUrl,
    backendMode: dependencies.backendMode,
    accessToken: dependencies.accessToken,
    currentUserId: dependencies.currentUserId,
    currentUserRole: dependencies.currentUserRole,
    tournamentId: route.tournamentId,
    onOpenLogin: dependencies.onOpenLogin == null
        ? null
        : () {
            dependencies.onOpenLogin!.call(context);
          },
  );
}

Widget _buildFanPredictionMatchScreen(
  BuildContext context,
  GteNavigationDependencies dependencies,
  FanPredictionMatchRouteData route,
) {
  return FanPredictionScreen(
    baseUrl: dependencies.apiBaseUrl,
    backendMode: dependencies.backendMode,
    accessToken: dependencies.accessToken,
    currentUserRole: dependencies.currentUserRole,
    matchId: route.matchId,
    onOpenLogin: dependencies.onOpenLogin == null
        ? null
        : () {
            dependencies.onOpenLogin!.call(context);
          },
  );
}

Widget _buildPlayerCardsBrowseScreen(
  BuildContext context,
  GteNavigationDependencies dependencies,
) {
  return PlayerCardMarketplaceScreen(
    baseUrl: dependencies.apiBaseUrl,
    backendMode: dependencies.backendMode,
    accessToken: dependencies.accessToken,
    currentUserId: dependencies.currentUserId,
    onOpenLogin: dependencies.onOpenLogin == null
        ? null
        : () {
            dependencies.onOpenLogin!.call(context);
          },
  );
}

Widget _buildPlayerCardDetailScreen(
  BuildContext context,
  GteNavigationDependencies dependencies,
  PlayerCardDetailRouteData route,
) {
  return _publicFeatureScreen(
    dependencies: dependencies,
    loadingTitle: 'Loading player card',
    icon: Icons.badge_outlined,
    accentColor: GteShellTheme.accent,
    load: () async {
      try {
        final Map<String, dynamic> detail = await _withApi(
          dependencies,
          (dynamic api) => api.getMap(
            '/player-cards/players/${route.playerId}',
            auth: false,
          ),
          () async => <String, dynamic>{
            'player_id': route.playerId,
            'display_name': 'Ayo Adeyemi',
            'overall_rating': 89,
            'position': 'FW',
            'nationality': 'Nigeria',
            'floor_price_credits': 1200,
          },
        );
        return GteFeatureRouteResult.ready(
          GteFeatureRouteContent(
            eyebrow: 'CARD DETAIL',
            title: _stringFromMap(
              detail,
              <String>['display_name', 'displayName', 'player_name'],
            ),
            description:
                'Detail routes stay stable even when broader marketplace surfaces are still being layered in by other threads.',
            icon: Icons.badge_outlined,
            accentColor: GteShellTheme.accent,
            metrics: <GteFeatureRouteMetric>[
              GteFeatureRouteMetric(
                label: 'Overall',
                value: _stringFromMap(
                  detail,
                  <String>['overall_rating', 'overallRating'],
                ),
              ),
              GteFeatureRouteMetric(
                label: 'Position',
                value: _stringFromMap(detail, <String>['position']),
              ),
              GteFeatureRouteMetric(
                label: 'Floor',
                value: _creditsLabel(
                  _numberFromMap(
                    detail,
                    <String>['floor_price_credits', 'floorPriceCredits'],
                  ),
                ),
              ),
            ],
            highlights: <String>[
              'The route is canonical for card details and safe to deep link directly.',
            ],
            actions: <GteFeatureRouteAction>[
              _routeAction(
                dependencies: dependencies,
                route: const PlayerCardsBrowseRouteData(),
                label: 'Back to player cards',
                icon: Icons.arrow_back_outlined,
              ),
            ],
          ),
        );
      } on GteApiException catch (error) {
        if (error.type == GteApiErrorType.notFound) {
          return GteFeatureRouteResult.empty(
            title: 'Player card not found',
            message:
                'No card detail record is available for `${route.playerId}`.',
            icon: Icons.search_off_outlined,
            accentColor: GteShellTheme.accent,
            actionLabel: 'Browse cards',
            onAction: _pushRouteHandler(
              dependencies,
              const PlayerCardsBrowseRouteData(),
            ),
          );
        }
        return _featureUnavailable(
          title: 'Player card unavailable',
          icon: Icons.badge_outlined,
          accentColor: GteShellTheme.accent,
          error: error,
        );
      }
    },
  );
}

Widget _buildPlayerCardsInventoryScreen(
  BuildContext context,
  GteNavigationDependencies dependencies,
) {
  return _authGuardedScreen(
    context: context,
    dependencies: dependencies,
    icon: Icons.inventory_2_outlined,
    child: PlayerCardMarketplaceScreen(
      baseUrl: dependencies.apiBaseUrl,
      backendMode: dependencies.backendMode,
      accessToken: dependencies.accessToken,
      currentUserId: dependencies.currentUserId,
      onOpenLogin: _loginAction(context, dependencies),
    ),
  );
}

Widget _buildCreatorShareMarketClubScreen(
  BuildContext context,
  GteNavigationDependencies dependencies,
  CreatorShareMarketClubRouteData route,
) {
  return _authGuardedScreen(
    context: context,
    dependencies: dependencies,
    icon: Icons.candlestick_chart_outlined,
    child: CreatorShareMarketScreen(
      clubId: route.clubId,
      clubName: route.clubName,
      baseUrl: dependencies.apiBaseUrl,
      backendMode: dependencies.backendMode,
      accessToken: dependencies.accessToken,
      currentClubId: dependencies.currentClubId,
      currentUserRole: dependencies.currentUserRole,
      onOpenLogin: _loginAction(context, dependencies),
    ),
  );
}

Widget _buildCreatorShareMarketAdminControlScreen(
  BuildContext context,
  GteNavigationDependencies dependencies,
) {
  return _authGuardedScreen(
    context: context,
    dependencies: dependencies,
    icon: Icons.settings_outlined,
    adminOnly: true,
    child: CreatorShareMarketAdminControlScreen(
      baseUrl: dependencies.apiBaseUrl,
      backendMode: dependencies.backendMode,
      accessToken: dependencies.accessToken,
      currentUserRole: dependencies.currentUserRole,
      onOpenLogin: _loginAction(context, dependencies),
    ),
  );
}

Widget _buildClubSaleMarketListingsScreen(
  BuildContext context,
  GteNavigationDependencies dependencies,
) {
  return ClubSaleMarketScreen(
    baseUrl: dependencies.apiBaseUrl,
    backendMode: dependencies.backendMode,
    accessToken: dependencies.accessToken,
    currentUserId: dependencies.currentUserId,
    currentClubId: dependencies.currentClubId,
    onOpenLogin: _loginAction(context, dependencies),
  );
}

Widget _buildClubSaleMarketDetailScreen(
  BuildContext context,
  GteNavigationDependencies dependencies,
  ClubSaleMarketDetailRouteData route,
) {
  return ClubSaleMarketScreen(
    clubId: route.clubId,
    clubName: route.clubName,
    baseUrl: dependencies.apiBaseUrl,
    backendMode: dependencies.backendMode,
    accessToken: dependencies.accessToken,
    currentUserId: dependencies.currentUserId,
    currentClubId: dependencies.currentClubId,
    onOpenLogin: _loginAction(context, dependencies),
  );
}

Widget _buildClubSaleMarketOwnerOffersScreen(
  BuildContext context,
  GteNavigationDependencies dependencies,
  ClubSaleMarketOwnerOffersRouteData route,
) {
  return _authGuardedScreen(
    context: context,
    dependencies: dependencies,
    icon: Icons.inbox_outlined,
    child: _ClubSaleOwnerOffersGateScreen(
      dependencies: dependencies,
      route: route,
      onOpenLogin: _loginAction(context, dependencies),
    ),
  );
}

class _ClubSaleOwnerOffersGateScreen extends StatefulWidget {
  const _ClubSaleOwnerOffersGateScreen({
    required this.dependencies,
    required this.route,
    required this.onOpenLogin,
  });

  final GteNavigationDependencies dependencies;
  final ClubSaleMarketOwnerOffersRouteData route;
  final VoidCallback? onOpenLogin;

  @override
  State<_ClubSaleOwnerOffersGateScreen> createState() =>
      _ClubSaleOwnerOffersGateScreenState();
}

class _ClubSaleOwnerOffersGateScreenState
    extends State<_ClubSaleOwnerOffersGateScreen> {
  Object? _error;
  bool _isChecking = true;

  @override
  void initState() {
    super.initState();
    _authorizeOwnerInbox();
  }

  Future<void> _authorizeOwnerInbox() async {
    setState(() {
      _error = null;
      _isChecking = true;
    });
    final ClubSaleMarketRepository repository = ClubSaleMarketApiRepository(
      client: widget.dependencies.createAuthedApi(),
    );
    try {
      await repository.listOffers(widget.route.clubId);
      if (!mounted) {
        return;
      }
      setState(() {
        _isChecking = false;
      });
    } on GteApiException catch (error) {
      if (!mounted) {
        return;
      }
      if (error.type == GteApiErrorType.notFound) {
        setState(() {
          _error = null;
          _isChecking = false;
        });
        return;
      }
      setState(() {
        _error = error;
        _isChecking = false;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = error;
        _isChecking = false;
      });
    }
  }

  Future<void> _openPublicListing() {
    return GteNavigationHelpers.pushRoute<void>(
      context,
      route: ClubSaleMarketDetailRouteData(
        clubId: widget.route.clubId,
        clubName: widget.route.clubName,
      ),
      dependencies: widget.dependencies,
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isChecking) {
      return _featureLoadingShell(
        context,
        title: 'Loading owner offer inbox',
      );
    }

    if (_error is GteApiException &&
        (_error as GteApiException).type == GteApiErrorType.unauthorized) {
      return _RouteStateScreen(
        title: 'You do not have access to this offer inbox',
        message:
            'Owner offer routes rely on the canonical authorized offers endpoint and cannot be inferred from local holdings.',
        actionLabel: 'Open public listing',
        onAction: _openPublicListing,
        icon: Icons.lock_outline,
      );
    }

    if (_error != null) {
      return _RouteStateScreen(
        title: 'Owner offer inbox unavailable',
        message: _errorMessage(_error!),
        actionLabel: 'Retry',
        onAction: _authorizeOwnerInbox,
        icon: Icons.inbox_outlined,
      );
    }

    return ClubSaleMarketScreen(
      clubId: widget.route.clubId,
      clubName: widget.route.clubName,
      baseUrl: widget.dependencies.apiBaseUrl,
      backendMode: widget.dependencies.backendMode,
      accessToken: widget.dependencies.accessToken,
      currentUserId: widget.dependencies.currentUserId,
      currentClubId: widget.dependencies.currentClubId,
      forceOwnerWorkspace: true,
      onOpenLogin: widget.onOpenLogin,
    );
  }
}

Widget _buildWorldOverviewScreen(
  BuildContext context,
  GteNavigationDependencies dependencies,
) {
  return FootballWorldSimulationScreen(
    baseUrl: dependencies.apiBaseUrl,
    backendMode: dependencies.backendMode,
    accessToken: dependencies.accessToken,
    currentUserRole: dependencies.currentUserRole,
  );
}

Widget _buildWorldClubContextScreen(
  BuildContext context,
  GteNavigationDependencies dependencies,
  WorldClubContextRouteData route,
) {
  return FootballWorldSimulationScreen(
    baseUrl: dependencies.apiBaseUrl,
    backendMode: dependencies.backendMode,
    accessToken: dependencies.accessToken,
    currentUserRole: dependencies.currentUserRole,
    clubId: route.clubId,
    clubName: route.clubName,
  );
}

Widget _buildWorldCompetitionContextScreen(
  BuildContext context,
  GteNavigationDependencies dependencies,
  WorldCompetitionContextRouteData route,
) {
  return FootballWorldSimulationScreen(
    baseUrl: dependencies.apiBaseUrl,
    backendMode: dependencies.backendMode,
    accessToken: dependencies.accessToken,
    currentUserRole: dependencies.currentUserRole,
    competitionId: route.competitionId,
  );
}

Widget _buildNationalTeamCompetitionsScreen(
  BuildContext context,
  GteNavigationDependencies dependencies,
) {
  return _publicFeatureScreen(
    dependencies: dependencies,
    loadingTitle: 'Loading national-team competitions',
    icon: Icons.flag_outlined,
    accentColor: const Color(0xFFFFD166),
    load: () async {
      try {
        final List<dynamic> competitions = await _withApi(
          dependencies,
          (dynamic api) =>
              api.getList('/national-team-engine/competitions', auth: false),
          () async => <Map<String, Object?>>[
            <String, Object?>{
              'id': 'nations-cup',
              'name': 'Nations Cup',
              'status': 'active',
              'entry_count': 24,
            },
          ],
        );
        if (competitions.isEmpty) {
          return GteFeatureRouteResult.empty(
            title: 'No national-team competitions are available',
            message:
                'The Nations Cup route is wired, but there are no competitions to list right now.',
            icon: Icons.flag_outlined,
            accentColor: const Color(0xFFFFD166),
            actionLabel: 'Retry',
          );
        }
        final Map<String, dynamic> featured = _asMap(competitions.first);
        return GteFeatureRouteResult.ready(
          GteFeatureRouteContent(
            eyebrow: 'NATIONAL TEAM',
            title: 'National-team competitions',
            description:
                'Nations Cup routes now mount from the canonical national-team engine.',
            icon: Icons.flag_outlined,
            accentColor: const Color(0xFFFFD166),
            metrics: <GteFeatureRouteMetric>[
              GteFeatureRouteMetric(
                label: 'Competitions',
                value: competitions.length.toString(),
              ),
              GteFeatureRouteMetric(
                label: 'Featured',
                value: _stringFromMap(featured, <String>['name', 'title']),
              ),
              GteFeatureRouteMetric(
                label: 'Entries',
                value: _stringFromMap(
                  featured,
                  <String>['entry_count', 'entryCount'],
                ),
              ),
            ],
            highlights: <String>[
              'National-team overview, entry, and history routes are now discoverable from arena and deep links.',
            ],
          ),
        );
      } on GteApiException catch (error) {
        return _featureUnavailable(
          title: 'National-team competitions unavailable',
          icon: Icons.flag_outlined,
          accentColor: const Color(0xFFFFD166),
          error: error,
        );
      }
    },
  );
}

Widget _buildNationalTeamEntryScreen(
  BuildContext context,
  GteNavigationDependencies dependencies,
  NationalTeamEntryRouteData route,
) {
  return _publicFeatureScreen(
    dependencies: dependencies,
    loadingTitle: 'Loading national-team entry',
    icon: Icons.assignment_ind_outlined,
    accentColor: const Color(0xFFFFD166),
    load: () async {
      try {
        final Map<String, dynamic> entry = await _withApi(
          dependencies,
          (dynamic api) => api.getMap(
            '/national-team-engine/entries/${route.entryId}',
            auth: false,
          ),
          () async => <String, dynamic>{
            'id': route.entryId,
            'country_name': 'Nigeria',
            'competition_name': 'Nations Cup',
            'status': 'qualified',
            'points': 9,
          },
        );
        return GteFeatureRouteResult.ready(
          GteFeatureRouteContent(
            eyebrow: 'NATIONAL TEAM ENTRY',
            title: _stringFromMap(
              entry,
              <String>['country_name', 'countryName'],
            ),
            description:
                'Entry deep links land safely even before richer national-team detail screens are wired.',
            icon: Icons.assignment_ind_outlined,
            accentColor: const Color(0xFFFFD166),
            metrics: <GteFeatureRouteMetric>[
              GteFeatureRouteMetric(
                label: 'Competition',
                value: _stringFromMap(
                  entry,
                  <String>['competition_name', 'competitionName'],
                ),
              ),
              GteFeatureRouteMetric(
                label: 'Status',
                value: _stringFromMap(entry, <String>['status']),
              ),
              GteFeatureRouteMetric(
                label: 'Points',
                value: _stringFromMap(entry, <String>['points']),
              ),
            ],
          ),
        );
      } on GteApiException catch (error) {
        if (error.type == GteApiErrorType.notFound) {
          return GteFeatureRouteResult.empty(
            title: 'National-team entry not found',
            message:
                'No national-team entry is available for `${route.entryId}`.',
            icon: Icons.assignment_ind_outlined,
            accentColor: const Color(0xFFFFD166),
            actionLabel: 'Open competitions',
            onAction: _pushRouteHandler(
              dependencies,
              const NationalTeamCompetitionsRouteData(),
            ),
          );
        }
        return _featureUnavailable(
          title: 'National-team entry unavailable',
          icon: Icons.assignment_ind_outlined,
          accentColor: const Color(0xFFFFD166),
          error: error,
        );
      }
    },
  );
}

Widget _buildNationalTeamHistoryScreen(
  BuildContext context,
  GteNavigationDependencies dependencies,
) {
  return _authenticatedFeatureScreen(
    dependencies: dependencies,
    loadingTitle: 'Loading national-team history',
    icon: Icons.history_edu_outlined,
    accentColor: const Color(0xFFFFD166),
    load: () async {
      try {
        final Map<String, dynamic> history = await _withApi(
          dependencies,
          (dynamic api) => api.getMap('/national-team-engine/me/history'),
          () async => <String, dynamic>{
            'entries': <Map<String, Object?>>[
              <String, Object?>{
                'country_name': 'Nigeria',
                'caps': 12,
                'best_finish': 'Quarterfinal',
              },
            ],
          },
        );
        final List<dynamic> entries =
            _listFromMap(history, <String>['entries', 'history']);
        if (entries.isEmpty) {
          return GteFeatureRouteResult.empty(
            title: 'No national-team history yet',
            message:
                'Signed-in history routing is working, but this account has no national-team record yet.',
            icon: Icons.history_edu_outlined,
            accentColor: const Color(0xFFFFD166),
            actionLabel: 'Open competitions',
            onAction: _pushRouteHandler(
              dependencies,
              const NationalTeamCompetitionsRouteData(),
            ),
          );
        }
        final Map<String, dynamic> latest = _asMap(entries.first);
        return GteFeatureRouteResult.ready(
          GteFeatureRouteContent(
            eyebrow: 'NATIONAL TEAM HISTORY',
            title: 'My national-team history',
            description:
                'History routes now guard sign-in cleanly and fall back to explicit empty states.',
            icon: Icons.history_edu_outlined,
            accentColor: const Color(0xFFFFD166),
            metrics: <GteFeatureRouteMetric>[
              GteFeatureRouteMetric(
                label: 'Entries',
                value: entries.length.toString(),
              ),
              GteFeatureRouteMetric(
                label: 'Country',
                value: _stringFromMap(
                  latest,
                  <String>['country_name', 'countryName'],
                ),
              ),
              GteFeatureRouteMetric(
                label: 'Caps',
                value: _stringFromMap(latest, <String>['caps']),
              ),
            ],
          ),
        );
      } on GteApiException catch (error) {
        return _featureUnavailable(
          title: 'National-team history unavailable',
          icon: Icons.history_edu_outlined,
          accentColor: const Color(0xFFFFD166),
          error: error,
        );
      }
    },
  );
}

Widget _buildFootballTransferCenterScreen(
  BuildContext context,
  GteNavigationDependencies dependencies,
  FootballTransferCenterRouteData route,
) {
  return _publicFeatureScreen(
    dependencies: dependencies,
    loadingTitle: 'Loading transfer center',
    icon: Icons.event_note_outlined,
    accentColor: const Color(0xFF8ED8FF),
    load: () async {
      try {
        final Map<String, dynamic> payload = await _withApi(
          dependencies,
          (dynamic api) async {
            final List<dynamic> live =
                await Future.wait<dynamic>(<Future<dynamic>>[
              api.getList('/api/transfers/windows', auth: false),
              api.getMap('/calendar-engine/dashboard', auth: false),
              api.getList(
                '/api/world/narratives',
                auth: false,
                query: const <String, Object?>{'limit': 6},
              ),
            ]);
            return <String, dynamic>{
              'windows': _asList(live[0]),
              'dashboard': _asMap(live[1]),
              'narratives': _asList(live[2]),
            };
          },
          () async => <String, dynamic>{
            'windows': <Map<String, Object?>>[
              <String, Object?>{
                'id': 'summer-2026',
                'name': 'Summer 2026',
                'status': 'open',
                'closing_at': '2026-08-31T18:00:00Z',
              },
            ],
            'dashboard': <String, Object?>{
              'upcoming_events': <Map<String, Object?>>[
                <String, Object?>{'title': 'Deadline day', 'days_out': 12},
              ],
            },
            'narratives': <Map<String, Object?>>[
              <String, Object?>{'headline': 'Creator clubs are scouting early'},
            ],
          },
        );
        final List<dynamic> windows =
            _listFromMap(payload, <String>['windows']);
        final Map<String, dynamic> dashboard =
            _mapFromMap(payload, <String>['dashboard']);
        final List<dynamic> narratives =
            _listFromMap(payload, <String>['narratives']);
        if (windows.isEmpty && narratives.isEmpty) {
          return GteFeatureRouteResult.empty(
            title: 'No transfer center updates',
            message:
                'The transfer, media, and calendar route is wired, but there are no windows or narratives to show right now.',
            icon: Icons.event_note_outlined,
            accentColor: const Color(0xFF8ED8FF),
            actionLabel: 'Retry',
          );
        }
        final Map<String, dynamic> featuredWindow =
            windows.isEmpty ? const <String, dynamic>{} : _asMap(windows.first);
        final List<dynamic> upcomingEvents = _listFromMap(
            dashboard, <String>['upcoming_events', 'upcomingEvents']);
        return GteFeatureRouteResult.ready(
          GteFeatureRouteContent(
            eyebrow: 'TRANSFER CENTER',
            title: 'Football transfer center',
            description:
                'Transfer windows, media storylines, and calendar routing now mount in a single resilient deep-link surface.',
            icon: Icons.event_note_outlined,
            accentColor: const Color(0xFF8ED8FF),
            metrics: <GteFeatureRouteMetric>[
              GteFeatureRouteMetric(
                label: 'Windows',
                value: windows.length.toString(),
              ),
              GteFeatureRouteMetric(
                label: 'Calendar items',
                value: upcomingEvents.length.toString(),
              ),
              GteFeatureRouteMetric(
                label: 'Default tab',
                value: route.tab.slug,
              ),
            ],
            highlights: <String>[
              'Transfer center routing stays public and does not crash when one feed is empty.',
              if (featuredWindow.isNotEmpty)
                'Featured window: ${_stringFromMap(featuredWindow, <String>[
                      'name',
                      'title'
                    ])}.',
            ],
            notes: <String>[
              'Window, media, and calendar gaps resolve into explicit empty states instead of blank routes.',
            ],
          ),
        );
      } on GteApiException catch (error) {
        return _featureUnavailable(
          title: 'Transfer center unavailable',
          icon: Icons.event_note_outlined,
          accentColor: const Color(0xFF8ED8FF),
          error: error,
        );
      }
    },
  );
}

Widget _buildCreatorStadiumClubScreen(
  BuildContext context,
  GteNavigationDependencies dependencies,
  CreatorStadiumClubRouteData route,
) {
  return CreatorStadiumMonetizationScreen(
    baseUrl: dependencies.apiBaseUrl,
    backendMode: dependencies.backendMode,
    accessToken: dependencies.accessToken,
    currentClubId: dependencies.currentClubId,
    currentUserRole: dependencies.currentUserRole,
    clubId: route.clubId,
    clubName: route.clubName,
    seasonId: route.seasonId,
    onOpenLogin: dependencies.onOpenLogin == null
        ? null
        : () {
            dependencies.onOpenLogin!.call(context);
          },
  );
}

Widget _buildCreatorStadiumMatchScreen(
  BuildContext context,
  GteNavigationDependencies dependencies,
  CreatorStadiumMatchRouteData route,
) {
  return CreatorStadiumMonetizationScreen(
    baseUrl: dependencies.apiBaseUrl,
    backendMode: dependencies.backendMode,
    accessToken: dependencies.accessToken,
    currentClubId: dependencies.currentClubId,
    currentUserRole: dependencies.currentUserRole,
    matchId: route.matchId,
    onOpenLogin: dependencies.onOpenLogin == null
        ? null
        : () {
            dependencies.onOpenLogin!.call(context);
          },
  );
}

Widget _buildCreatorStadiumAdminControlScreen(
  BuildContext context,
  GteNavigationDependencies dependencies,
) {
  return _authGuardedScreen(
    context: context,
    dependencies: dependencies,
    icon: Icons.stadium_outlined,
    adminOnly: true,
    child: CreatorStadiumMonetizationScreen(
      baseUrl: dependencies.apiBaseUrl,
      backendMode: dependencies.backendMode,
      accessToken: dependencies.accessToken,
      currentClubId: dependencies.currentClubId,
      currentUserRole: dependencies.currentUserRole,
      adminOnly: true,
      onOpenLogin: dependencies.onOpenLogin == null
          ? null
          : () {
              dependencies.onOpenLogin!.call(context);
            },
    ),
  );
}

Widget _buildCreatorLeagueFinancialReportScreen(
  BuildContext context,
  GteNavigationDependencies dependencies,
  CreatorLeagueFinancialReportRouteData route,
) {
  return _authGuardedScreen(
    context: context,
    dependencies: dependencies,
    icon: Icons.account_balance_outlined,
    adminOnly: true,
    child: CreatorLeagueAdminScreen(
      baseUrl: dependencies.apiBaseUrl,
      backendMode: dependencies.backendMode,
      accessToken: dependencies.accessToken,
      currentUserRole: dependencies.currentUserRole,
      onOpenLogin: dependencies.onOpenLogin == null
          ? null
          : () {
              dependencies.onOpenLogin!.call(context);
            },
      seasonId: route.seasonId,
      initialView: CreatorLeagueAdminView.finance,
    ),
  );
}

Widget _buildCreatorLeagueSettlementsScreen(
  BuildContext context,
  GteNavigationDependencies dependencies,
  CreatorLeagueSettlementsRouteData route,
) {
  return _authGuardedScreen(
    context: context,
    dependencies: dependencies,
    icon: Icons.payments_outlined,
    adminOnly: true,
    child: CreatorLeagueAdminScreen(
      baseUrl: dependencies.apiBaseUrl,
      backendMode: dependencies.backendMode,
      accessToken: dependencies.accessToken,
      currentUserRole: dependencies.currentUserRole,
      onOpenLogin: dependencies.onOpenLogin == null
          ? null
          : () {
              dependencies.onOpenLogin!.call(context);
            },
      seasonId: route.seasonId,
      initialView: CreatorLeagueAdminView.settlements,
    ),
  );
}

Widget _buildGiftStabilizerScreen(
  BuildContext context,
  GteNavigationDependencies dependencies,
) {
  return _authGuardedScreen(
    context: context,
    dependencies: dependencies,
    icon: Icons.tune_outlined,
    adminOnly: true,
    child: GiftEconomyAdminScreen(
      baseUrl: dependencies.apiBaseUrl,
      backendMode: dependencies.backendMode,
      accessToken: dependencies.accessToken,
      currentUserRole: dependencies.currentUserRole,
      onOpenLogin: dependencies.onOpenLogin == null
          ? null
          : () {
              dependencies.onOpenLogin!.call(context);
            },
    ),
  );
}
