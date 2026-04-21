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
      message:
          adminOnly
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
  final dynamic api = dependencies.liveOnly().createAuthedApi();
  return await live(api);
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

String _creditsLabel(num value) {
  final bool whole = value == value.roundToDouble();
  return '${value.toStringAsFixed(whole ? 0 : 2)} cr';
}

String _errorMessage(Object error) {
  if (error is GteApiException) {
    return error.message;
  }
  return AppFeedback.messageFor(error);
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
    onOpenLogin:
        dependencies.onOpenLogin == null
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
    onOpenLogin:
        dependencies.onOpenLogin == null
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
    onOpenLogin:
        dependencies.onOpenLogin == null
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
    onOpenLogin:
        dependencies.onOpenLogin == null
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
          () => throw StateError('Route-level fixture fallback is disabled.'),
        );
        return GteFeatureRouteResult.ready(
          GteFeatureRouteContent(
            eyebrow: 'CARD DETAIL',
            title: _stringFromMap(detail, <String>[
              'display_name',
              'displayName',
              'player_name',
            ]),
            description:
                'Detail routes stay stable even when broader marketplace surfaces are still being layered in by other threads.',
            icon: Icons.badge_outlined,
            accentColor: GteShellTheme.accent,
            metrics: <GteFeatureRouteMetric>[
              GteFeatureRouteMetric(
                label: 'Overall',
                value: _stringFromMap(detail, <String>[
                  'overall_rating',
                  'overallRating',
                ]),
              ),
              GteFeatureRouteMetric(
                label: 'Position',
                value: _stringFromMap(detail, <String>['position']),
              ),
              GteFeatureRouteMetric(
                label: 'Floor',
                value: _creditsLabel(
                  _numberFromMap(detail, <String>[
                    'floor_price_credits',
                    'floorPriceCredits',
                  ]),
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
      return _featureLoadingShell(context, title: 'Loading owner offer inbox');
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
    clubId: dependencies.currentClubId,
    clubName: dependencies.currentClubName,
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
        final List<Object?> payload = await Future.wait<Object?>(
          <Future<Object?>>[
            _withApi(
              dependencies,
              (dynamic api) => api.getList(
                '/api/national-team-engine/competitions',
                auth: false,
              ),
              () async => <Map<String, Object?>>[
                <String, Object?>{
                  'id': 'nations-cup',
                  'name': 'Nations Cup',
                  'status': 'active',
                  'entry_count': 24,
                },
              ],
            ),
            _withApi(
              dependencies,
              (dynamic api) async {
                final Map<String, dynamic> payload = await api.getMap(
                  '/regen-universe/national-regens',
                  auth: false,
                );
                return _asList(payload['items']);
              },
              () async => <Map<String, Object?>>[
                <String, Object?>{
                  'id': 'seed-naija-1',
                  'display_name': 'Kazeem Afolabi',
                  'country_name': 'Nigeria',
                  'primary_position': 'RW',
                  'current_rating': 69,
                  'potential_rating': 88,
                  'rarity_tier': 'elite',
                },
                <String, Object?>{
                  'id': 'seed-ghana-1',
                  'display_name': 'Kojo Mensah',
                  'country_name': 'Ghana',
                  'primary_position': 'CB',
                  'current_rating': 71,
                  'potential_rating': 87,
                  'rarity_tier': 'elite',
                },
              ],
            ),
          ],
        );
        final List<dynamic> competitions = payload[0] as List<dynamic>;
        final List<dynamic> nationalRegens = payload[1] as List<dynamic>;
        if (competitions.isEmpty && nationalRegens.isEmpty) {
          return GteFeatureRouteResult.empty(
            title: 'No national-team pool is available',
            message:
                'National-team competitions and pre-seeded regen categories are currently empty.',
            icon: Icons.flag_outlined,
            accentColor: const Color(0xFFFFD166),
            actionLabel: 'Retry',
          );
        }
        final Map<String, dynamic>? featured =
            competitions.isEmpty ? null : _asMap(competitions.first);
        final Map<String, List<Map<String, dynamic>>> regensByCountry =
            <String, List<Map<String, dynamic>>>{};
        for (final Object? item in nationalRegens) {
          final Map<String, dynamic> seed = _asMap(item);
          final String country = _stringFromMap(seed, <String>[
            'country_name',
            'countryName',
          ], fallback: 'Unknown');
          regensByCountry.putIfAbsent(country, () => <Map<String, dynamic>>[]);
          regensByCountry[country]!.add(seed);
        }
        final List<MapEntry<String, List<Map<String, dynamic>>>>
        groupedCountries = regensByCountry.entries.toList(growable: false)
          ..sort(
            (
              MapEntry<String, List<Map<String, dynamic>>> left,
              MapEntry<String, List<Map<String, dynamic>>> right,
            ) => right.value.length.compareTo(left.value.length),
          );
        final List<String> countryHighlights = groupedCountries
            .take(4)
            .map((MapEntry<String, List<Map<String, dynamic>>> entry) {
              final List<String> names = entry.value
                  .take(3)
                  .map(
                    (Map<String, dynamic> seed) => _stringFromMap(
                      seed,
                      <String>['display_name', 'displayName'],
                      fallback: 'Unknown prospect',
                    ),
                  )
                  .toList(growable: false);
              return '${entry.key}: ${names.join(', ')}';
            })
            .toList(growable: false);
        return GteFeatureRouteResult.ready(
          GteFeatureRouteContent(
            eyebrow: 'NATIONAL TEAM',
            title: 'National-team pool',
            description:
                'National-team competition routes now surface pre-seeded regens by country so the pool is visible before and during tournaments.',
            icon: Icons.flag_outlined,
            accentColor: const Color(0xFFFFD166),
            metrics: <GteFeatureRouteMetric>[
              GteFeatureRouteMetric(
                label: 'Competitions',
                value: competitions.length.toString(),
              ),
              GteFeatureRouteMetric(
                label: 'Seeded countries',
                value: groupedCountries.length.toString(),
              ),
              GteFeatureRouteMetric(
                label: 'Visible regens',
                value: nationalRegens.length.toString(),
              ),
              GteFeatureRouteMetric(
                label: 'Featured',
                value:
                    featured == null
                        ? 'National pool'
                        : _stringFromMap(featured, <String>['name', 'title']),
              ),
            ],
            highlights: <String>[
              if (featured != null)
                'Current live competition: ${_stringFromMap(featured, <String>['name', 'title'])} with ${_stringFromMap(featured, <String>['entry_count', 'entryCount'])} entries.',
              if (countryHighlights.isNotEmpty) ...countryHighlights,
              if (countryHighlights.isEmpty)
                'National-team overview, entry, and history routes are now discoverable from arena and deep links.',
            ],
            notes: <String>[
              'Pre-seeded regens are now visible under their national-team countries on this route.',
              'Club-generated prospects continue from the world regen desk and remain tradable once listed on the exchange.',
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
            '/api/national-team-engine/entries/${route.entryId}',
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
            title: _stringFromMap(entry, <String>[
              'country_name',
              'countryName',
            ]),
            description:
                'Entry deep links land safely even before richer national-team detail screens are wired.',
            icon: Icons.assignment_ind_outlined,
            accentColor: const Color(0xFFFFD166),
            metrics: <GteFeatureRouteMetric>[
              GteFeatureRouteMetric(
                label: 'Competition',
                value: _stringFromMap(entry, <String>[
                  'competition_name',
                  'competitionName',
                ]),
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
          (dynamic api) => api.getMap('/api/national-team-engine/me/history'),
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
        final List<dynamic> entries = _listFromMap(history, <String>[
          'entries',
          'history',
        ]);
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
                value: _stringFromMap(latest, <String>[
                  'country_name',
                  'countryName',
                ]),
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
            final List<dynamic> live = await Future.wait<dynamic>(
              <Future<dynamic>>[
                api.getList('/api/transfers/windows', auth: false),
                api.getMap('/api/calendar-engine/dashboard', auth: false),
                api.getList(
                  '/api/world/narratives',
                  auth: false,
                  query: const <String, Object?>{'limit': 6},
                ),
              ],
            );
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
        final List<dynamic> windows = _listFromMap(payload, <String>[
          'windows',
        ]);
        final Map<String, dynamic> dashboard = _mapFromMap(payload, <String>[
          'dashboard',
        ]);
        final List<dynamic> narratives = _listFromMap(payload, <String>[
          'narratives',
        ]);
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
        final List<dynamic> upcomingEvents = _listFromMap(dashboard, <String>[
          'upcoming_events',
          'upcomingEvents',
        ]);
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
                'Featured window: ${_stringFromMap(featuredWindow, <String>['name', 'title'])}.',
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

Widget _buildBroadcastDeskScreen(
  BuildContext context,
  GteNavigationDependencies dependencies,
) {
  return _authenticatedFeatureScreen(
    dependencies: dependencies,
    loadingTitle: 'Loading broadcast desk',
    icon: Icons.podcasts_outlined,
    accentColor: const Color(0xFF8ED8FF),
    load: () async {
      try {
        final Map<String, dynamic> payload = await _withApi(
          dependencies,
          (dynamic api) async {
            final Map<String, dynamic> home = await api.getMap(
              '/api/broadcast/home',
              auth: false,
            );
            final List<dynamic> channels = await api.getList(
              '/api/broadcast/channels',
            );
            final List<dynamic> commentaryProfiles = await api.getList(
              '/api/commentary/profiles',
              auth: false,
            );
            final Map<String, dynamic> featuredChannel = _asMap(
              home['featured_channel'],
            );
            final String? channelId =
                _stringOrNull(
                  _pick(featuredChannel, <String>['channel_id', 'channelId']),
                ) ??
                _stringOrNull(
                  _pick(
                    channels.isEmpty
                        ? const <String, dynamic>{}
                        : _asMap(channels.first),
                    <String>['channel_id', 'channelId'],
                  ),
                );
            Map<String, dynamic> session = <String, dynamic>{};
            if (channelId != null) {
              session = _asMap(
                await api.post('/api/broadcast/channels/$channelId/join'),
              );
            }
            return <String, dynamic>{
              'home': home,
              'channels': channels,
              'commentary_profiles': commentaryProfiles,
              'session': session,
            };
          },
          () async => <String, dynamic>{
            'home': <String, Object?>{
              'featured_channel': <String, Object?>{
                'channel_id': 'matchday-prime',
                'name': 'Matchday Prime',
                'is_live': true,
                'viewer_count': 18420,
                'current_program': <String, Object?>{
                  'match_id': 'fixture-final',
                  'title': 'GTEX Final',
                  'subtitle': 'Rivalry night with title implications',
                  'watch_route': '/matches/broadcast/fixture-final',
                  'replay_route': '/api/matches/fixture-final/replay',
                },
              },
            },
            'channels': <Map<String, Object?>>[
              <String, Object?>{
                'channel_id': 'matchday-prime',
                'name': 'Matchday Prime',
                'is_live': true,
                'viewer_count': 18420,
                'auto_switch_enabled': true,
              },
              <String, Object?>{
                'channel_id': 'creator-cuts',
                'name': 'Creator Cuts',
                'is_live': true,
                'viewer_count': 6120,
                'auto_switch_enabled': true,
              },
            ],
            'commentary_profiles': <Map<String, Object?>>[
              <String, Object?>{
                'id': 'play-by-play',
                'name': 'Play by Play',
                'style': 'sharp',
              },
              <String, Object?>{
                'id': 'analyst',
                'name': 'Analyst',
                'style': 'tactical',
              },
            ],
            'session': <String, Object?>{
              'current_program': <String, Object?>{
                'match_id': 'fixture-final',
                'title': 'GTEX Final',
                'subtitle': 'Rivalry night with title implications',
              },
              'director_focus': <String, Object?>{
                'momentum': 'surging',
                'focus_target': 'final third',
                'focus_reason': 'title race drama',
              },
              'watch_reward': <String, Object?>{
                'xp_awarded': 25,
                'reward_value_coin': '1.5000',
              },
              'audio_stem_websocket_path':
                  '/api/broadcast/channels/matchday-prime/audio/stems/stream?session_id=broadcast-fixture',
              'match_session': <String, Object?>{
                'commentary_websocket_path':
                    '/api/matches/fixture-final/commentary/stream',
                'audio_stem_websocket_path':
                    '/api/matches/fixture-final/audio/stems/stream',
                'sync_strategy': 'deterministic_playback',
                'sponsored_overlays': <Map<String, Object?>>[
                  <String, Object?>{'id': 'brand-1'},
                ],
                'stadium_ads': <Map<String, Object?>>[
                  <String, Object?>{'id': 'stadium-1'},
                ],
              },
            },
          },
        );
        final Map<String, dynamic> home = _mapFromMap(payload, <String>[
          'home',
        ]);
        final List<dynamic> channels = _listFromMap(payload, <String>[
          'channels',
        ]);
        final List<dynamic> commentaryProfiles = _listFromMap(payload, <String>[
          'commentary_profiles',
          'commentaryProfiles',
        ]);
        final Map<String, dynamic> session = _mapFromMap(payload, <String>[
          'session',
        ]);
        final Map<String, dynamic> featuredChannel = _mapFromMap(home, <String>[
          'featured_channel',
          'featuredChannel',
        ]);
        final Map<String, dynamic> currentProgram = _mapFromMap(
          session,
          <String>['current_program', 'currentProgram'],
        );
        final Map<String, dynamic> directorFocus = _mapFromMap(
          session,
          <String>['director_focus', 'directorFocus'],
        );
        final Map<String, dynamic> watchReward = _mapFromMap(session, <String>[
          'watch_reward',
          'watchReward',
        ]);
        final Map<String, dynamic> matchSession = _mapFromMap(session, <String>[
          'match_session',
          'matchSession',
        ]);
        final int liveChannels =
            channels
                .where((Object? item) => _asMap(item)['is_live'] == true)
                .length;
        final List<String> highlights = <String>[
          if (currentProgram.isNotEmpty)
            'Current program: ${_stringFromMap(currentProgram, <String>['title'])} - ${_stringFromMap(currentProgram, <String>['subtitle'], fallback: 'Broadcast package is live.')}',
          if (directorFocus.isNotEmpty)
            'Director focus: ${_stringFromMap(directorFocus, <String>['momentum'])} momentum on ${_stringFromMap(directorFocus, <String>['focus_target', 'focusTarget'])} because ${_stringFromMap(directorFocus, <String>['focus_reason', 'focusReason'])}.',
          if (_stringOrNull(
                _pick(matchSession, <String>['sync_strategy', 'syncStrategy']),
              ) !=
              null)
            'Match session sync strategy: ${_stringFromMap(matchSession, <String>['sync_strategy', 'syncStrategy'])}.',
          if (_stringOrNull(
                _pick(matchSession, <String>[
                  'commentary_websocket_path',
                  'commentaryWebsocketPath',
                ]),
              ) !=
              null)
            'Rich commentary transport is mounted for this channel session.',
          if (_stringOrNull(
                _pick(matchSession, <String>[
                  'audio_stem_websocket_path',
                  'audioStemWebsocketPath',
                ]),
              ) !=
              null)
            'Audio stem transport is exposed for layered commentary, crowd, and stadium FX.',
          if (_asList(matchSession['sponsored_overlays']).isNotEmpty ||
              _asList(matchSession['stadium_ads']).isNotEmpty)
            'Viewer monetization payload is mounted with ${_asList(matchSession['sponsored_overlays']).length} sponsored overlays and ${_asList(matchSession['stadium_ads']).length} stadium ads.',
          if (commentaryProfiles.isNotEmpty)
            'Available commentary profiles: ${commentaryProfiles.take(3).map((Object? item) => _stringFromMap(_asMap(item), <String>['name', 'style'], fallback: 'Commentary profile')).join(', ')}.',
        ];
        return GteFeatureRouteResult.ready(
          GteFeatureRouteContent(
            eyebrow: 'BROADCAST DESK',
            title: _stringFromMap(
              currentProgram.isEmpty ? featuredChannel : currentProgram,
              <String>['title', 'name'],
              fallback: 'Live broadcast network',
            ),
            description:
                'This desk now consumes the broadcast-network home, channel join session, director focus, and commentary-profile surfaces that were previously left behind the live shell.',
            icon: Icons.podcasts_outlined,
            accentColor: const Color(0xFF8ED8FF),
            metrics: <GteFeatureRouteMetric>[
              GteFeatureRouteMetric(
                label: 'Channels',
                value: channels.length.toString(),
              ),
              GteFeatureRouteMetric(
                label: 'Live now',
                value: liveChannels.toString(),
              ),
              GteFeatureRouteMetric(
                label: 'Commentary voices',
                value: commentaryProfiles.length.toString(),
              ),
              GteFeatureRouteMetric(
                label: 'Watch reward',
                value:
                    '${_stringFromMap(watchReward, <String>['xp_awarded', 'xpAwarded'], fallback: '0')} XP / ${_stringFromMap(watchReward, <String>['reward_value_coin', 'rewardValueCoin'], fallback: '0.0000')} coin',
              ),
            ],
            highlights: highlights,
            notes: <String>[
              'This route reads /api/broadcast/home, /api/broadcast/channels, /api/broadcast/channels/{channelId}/join, and /api/commentary/profiles directly.',
              if (_stringOrNull(
                    _pick(currentProgram, <String>[
                      'watch_route',
                      'watchRoute',
                    ]),
                  ) !=
                  null)
                'Current watch route: ${_stringFromMap(currentProgram, <String>['watch_route', 'watchRoute'])}.',
              if (_stringOrNull(
                    _pick(currentProgram, <String>[
                      'replay_route',
                      'replayRoute',
                    ]),
                  ) !=
                  null)
                'Current replay route: ${_stringFromMap(currentProgram, <String>['replay_route', 'replayRoute'])}.',
            ],
          ),
        );
      } on GteApiException catch (error) {
        return _featureUnavailable(
          title: 'Broadcast desk unavailable',
          icon: Icons.podcasts_outlined,
          accentColor: const Color(0xFF8ED8FF),
          error: error,
        );
      }
    },
  );
}

Widget _buildGtexJackpotScreen(
  BuildContext context,
  GteNavigationDependencies dependencies,
) {
  return GtexJackpotRouteScreen(
    dependencies: dependencies,
    onOpenLogin: _loginAction(context, dependencies),
  );
}

String _humanizeRouteValue(String raw) {
  final String candidate = raw.trim();
  if (candidate.isEmpty || candidate == '--') {
    return raw;
  }
  return candidate
      .split(RegExp(r'[_\s-]+'))
      .where((String part) => part.trim().isNotEmpty)
      .map(
        (String part) =>
            '${part[0].toUpperCase()}${part.substring(1).toLowerCase()}',
      )
      .join(' ');
}

Widget _buildClubAiAssistantScreen(
  BuildContext context,
  GteNavigationDependencies dependencies,
  ClubAiAssistantRouteData route,
) {
  return _authenticatedFeatureScreen(
    dependencies: dependencies,
    loadingTitle: 'Loading club AI assistant',
    icon: Icons.smart_toy_outlined,
    accentColor: const Color(0xFF72F0D8),
    load: () async {
      try {
        final Map<String, dynamic> payload = await _withApi(
          dependencies,
          (dynamic api) async {
            final List<dynamic> live =
                await Future.wait<dynamic>(<Future<dynamic>>[
                  api.getMap(
                    '/api/ai-manager/profiles/${route.clubId}',
                    auth: true,
                  ),
                  api.post(
                    '/api/ai-manager/autopilot/run',
                    body: _buildAiAutopilotRequest(
                      clubId: route.clubId,
                      clubName: route.clubName ?? route.clubId,
                    ),
                    auth: true,
                  ),
                  api.post(
                    '/api/ai-manager/autopilot/live-decision',
                    body: _buildAiLiveDecisionRequest(clubId: route.clubId),
                    auth: true,
                  ),
                  api.post(
                    '/api/ai-manager/economy/reward-preview',
                    body: _buildAiRewardPreviewRequest(),
                    auth: true,
                  ),
                ]);
            return <String, dynamic>{
              'profile': _asMap(live[0]),
              'autopilot': _asMap(live[1]),
              'live_decision': _asMap(live[2]),
              'reward_preview': _asMap(live[3]),
            };
          },
          () async => <String, dynamic>{
            'profile': <String, Object?>{
              'club_id': route.clubId,
              'tactical_style': 'balanced',
              'financial_strategy': 'sustainable',
            },
            'autopilot': <String, Object?>{
              'activation': <String, Object?>{
                'ai_active': true,
                'mode': 'autonomous',
                'summary':
                    'AI manager is in autonomous mode because the user has been inactive past the offline threshold.',
              },
              'squad_plan': <String, Object?>{
                'formation': '4-3-3',
                'tempo': 'normal',
                'pressing': 'medium',
                'rationale': <String>[
                  'Attacking variant selected because the squad is stable enough to lean into the manager style.',
                ],
              },
              'transfer_actions': <Map<String, Object?>>[
                <String, Object?>{
                  'action': 'promote_youth',
                  'player_name': 'Kai Forge',
                  'rationale':
                      'Strong youth bias promotes an internal prospect instead of forcing another external buy.',
                },
              ],
              'training_plan': <Map<String, Object?>>[
                <String, Object?>{
                  'player_name': 'Micah Vale',
                  'focus': 'development',
                },
              ],
              'finance_actions': <Map<String, Object?>>[
                <String, Object?>{
                  'action': 'hold_budget',
                  'rationale':
                      'Budget reserve is healthy, so no emergency sale is needed.',
                },
              ],
              'decision_log': <String>[
                'AI manager is in autonomous mode because the user has been inactive past the offline threshold.',
              ],
            },
            'live_decision': <String, Object?>{
              'directive': 'increase_pressing',
              'tempo': 'fast',
              'pressing': 'high',
              'substitution_reason': 'Fresh attacking legs are needed.',
            },
            'reward_preview': <String, Object?>{
              'base_reward': 200,
              'final_reward': 472,
              'reward_multiplier': 2.36,
              'blocked_pay_to_win_paths': <String>[
                'buying wins',
                'wallet-based stat boosts',
              ],
            },
          },
        );
        final Map<String, dynamic> profile = _mapFromMap(payload, <String>[
          'profile',
        ]);
        final Map<String, dynamic> autopilot = _mapFromMap(payload, <String>[
          'autopilot',
        ]);
        final Map<String, dynamic> activation = _mapFromMap(autopilot, <String>[
          'activation',
        ]);
        final Map<String, dynamic> squadPlan = _mapFromMap(autopilot, <String>[
          'squad_plan',
          'squadPlan',
        ]);
        final List<dynamic> transferActions = _listFromMap(autopilot, <String>[
          'transfer_actions',
          'transferActions',
        ]);
        final List<dynamic> trainingPlan = _listFromMap(autopilot, <String>[
          'training_plan',
          'trainingPlan',
        ]);
        final List<dynamic> financeActions = _listFromMap(autopilot, <String>[
          'finance_actions',
          'financeActions',
        ]);
        final List<dynamic> decisionLog = _listFromMap(autopilot, <String>[
          'decision_log',
          'decisionLog',
        ]);
        final Map<String, dynamic> liveDecision = _mapFromMap(payload, <String>[
          'live_decision',
          'liveDecision',
        ]);
        final Map<String, dynamic> rewardPreview = _mapFromMap(
          payload,
          <String>['reward_preview', 'rewardPreview'],
        );
        final Map<String, dynamic> firstTransfer =
            transferActions.isEmpty
                ? const <String, dynamic>{}
                : _asMap(transferActions.first);
        final Map<String, dynamic> firstTraining =
            trainingPlan.isEmpty
                ? const <String, dynamic>{}
                : _asMap(trainingPlan.first);
        final Map<String, dynamic> firstFinance =
            financeActions.isEmpty
                ? const <String, dynamic>{}
                : _asMap(financeActions.first);
        final List<dynamic> blockedPaths = _listFromMap(rewardPreview, <String>[
          'blocked_pay_to_win_paths',
          'blockedPayToWinPaths',
        ]);
        return GteFeatureRouteResult.ready(
          GteFeatureRouteContent(
            eyebrow: 'AI ASSISTANT',
            title:
                route.clubName == null || route.clubName!.trim().isEmpty
                    ? 'Club AI assistant'
                    : '${route.clubName} AI assistant',
            description:
                'The backend AI manager is now reflected as a routed club surface with profile, autopilot, live decision, and reward policy previews.',
            icon: Icons.smart_toy_outlined,
            accentColor: const Color(0xFF72F0D8),
            metrics: <GteFeatureRouteMetric>[
              GteFeatureRouteMetric(
                label: 'Tactical style',
                value: _humanizeRouteValue(
                  _stringFromMap(profile, <String>[
                    'tactical_style',
                    'tacticalStyle',
                  ]),
                ),
              ),
              GteFeatureRouteMetric(
                label: 'Finance',
                value: _humanizeRouteValue(
                  _stringFromMap(profile, <String>[
                    'financial_strategy',
                    'financialStrategy',
                  ]),
                ),
              ),
              GteFeatureRouteMetric(
                label: 'Autopilot mode',
                value: _humanizeRouteValue(
                  _stringFromMap(activation, <String>['mode']),
                ),
              ),
              GteFeatureRouteMetric(
                label: 'Live directive',
                value: _humanizeRouteValue(
                  _stringFromMap(liveDecision, <String>['directive']),
                ),
              ),
            ],
            highlights: <String>[
              if (decisionLog.isNotEmpty) decisionLog.first.toString(),
              if (_stringOrNull(_pick(squadPlan, <String>['formation'])) !=
                  null)
                'Autopilot squad plan: ${_stringFromMap(squadPlan, <String>['formation'])} with ${_humanizeRouteValue(_stringFromMap(squadPlan, <String>['tempo']))} tempo and ${_humanizeRouteValue(_stringFromMap(squadPlan, <String>['pressing']))} pressing.',
              if (_listFromMap(squadPlan, <String>['rationale']).isNotEmpty)
                _listFromMap(squadPlan, <String>['rationale']).first.toString(),
              if (firstTransfer.isNotEmpty)
                'Transfer call: ${_humanizeRouteValue(_stringFromMap(firstTransfer, <String>['action']))} ${_stringFromMap(firstTransfer, <String>['player_name', 'playerName'], fallback: '').trim()} ${_stringFromMap(firstTransfer, <String>['rationale'])}'
                    .trim(),
              if (firstTraining.isNotEmpty)
                'Training focus: ${_stringFromMap(firstTraining, <String>['player_name', 'playerName'])} on ${_humanizeRouteValue(_stringFromMap(firstTraining, <String>['focus']))}.',
              if (firstFinance.isNotEmpty)
                'Finance posture: ${_humanizeRouteValue(_stringFromMap(firstFinance, <String>['action']))} because ${_stringFromMap(firstFinance, <String>['rationale'])}.',
              if (_stringOrNull(
                    _pick(liveDecision, <String>[
                      'substitution_reason',
                      'substitutionReason',
                    ]),
                  ) !=
                  null)
                'Live match switch: ${_stringFromMap(liveDecision, <String>['substitution_reason', 'substitutionReason'])}',
              'Reward preview: ${_stringFromMap(rewardPreview, <String>['final_reward', 'finalReward'])} final from base ${_stringFromMap(rewardPreview, <String>['base_reward', 'baseReward'])} with multiplier ${_stringFromMap(rewardPreview, <String>['reward_multiplier', 'rewardMultiplier'])}.',
            ],
            notes: <String>[
              'This route runs /api/ai-manager/profiles/{clubId}, /autopilot/run, /autopilot/live-decision, and /economy/reward-preview directly.',
              if (blockedPaths.isNotEmpty)
                'Competitive integrity guardrails stay explicit: ${blockedPaths.take(3).join(', ')}.',
            ],
          ),
        );
      } on GteApiException catch (error) {
        return _featureUnavailable(
          title: 'Club AI assistant unavailable',
          icon: Icons.smart_toy_outlined,
          accentColor: const Color(0xFF72F0D8),
          error: error,
        );
      }
    },
  );
}

Map<String, Object?> _buildAiAutopilotRequest({
  required String clubId,
  required String clubName,
}) {
  final List<Map<String, Object?>> squad = _buildAiSquadSeed(
    clubId: clubId,
    clubName: clubName,
  );
  return <String, Object?>{
    'club_id': clubId,
    'user_last_active_hours': 42,
    'club_strength': 82,
    'opponent': <String, Object?>{
      'club_name': '${_buildAiClubAlias(clubName)} Select',
      'strength': 79,
      'tactical_style': 'balanced',
    },
    'squad': squad,
    'finance': <String, Object?>{
      'revenue': 780000,
      'wage_bill': 420000,
      'transfer_budget': 250000,
      'cash_balance': 910000,
      'scouting_budget': 85000,
      'training_budget': 65000,
    },
    'market': <String, Object?>{
      'hours_since_last_transfer': 72,
      'targets': <Map<String, Object?>>[
        <String, Object?>{
          'player_id': '$clubId-target-anchor-9',
          'name': 'Ayo Balance',
          'position': 'CM',
          'skill': 80,
          'potential': 86,
          'fit_to_tactic': 0.84,
          'wage_cost': 34000,
          'asking_price': 175000,
          'age': 22,
          'is_free_agent': false,
        },
        <String, Object?>{
          'player_id': '$clubId-target-finisher-10',
          'name': 'Timo Edge',
          'position': 'ST',
          'skill': 78,
          'potential': 84,
          'fit_to_tactic': 0.81,
          'wage_cost': 30000,
          'asking_price': 150000,
          'age': 21,
          'is_free_agent': false,
        },
        <String, Object?>{
          'player_id': '$clubId-target-utility-11',
          'name': 'Musa Vale',
          'position': 'RW',
          'skill': 75,
          'potential': 82,
          'fit_to_tactic': 0.76,
          'wage_cost': 22000,
          'asking_price': 0,
          'age': 19,
          'is_free_agent': true,
        },
      ],
    },
    'bench_size': 7,
  };
}

Map<String, Object?> _buildAiLiveDecisionRequest({required String clubId}) {
  return <String, Object?>{
    'club_id': clubId,
    'minute': 67,
    'score_for': 1,
    'score_against': 1,
    'xg_for': 1.42,
    'xg_against': 1.11,
    'possession_share': 0.56,
    'red_cards_for': 0,
    'red_cards_against': 0,
    'average_stamina': 0.63,
    'average_fatigue': 0.34,
    'opponent_switched_shape': true,
    'substitutions_used': 2,
    'maximum_substitutions': 5,
  };
}

Map<String, Object?> _buildAiRewardPreviewRequest() {
  return <String, Object?>{
    'base_reward': 350,
    'difficulty_multiplier': 1.35,
    'division': 'open',
    'win_streak': 4,
    'tournament_stage_weight': 0.2,
    'entry_fee_pool': 120,
    'entry_fee_multiplier': 1.0,
    'ai_active': true,
    'premium_features_enabled': true,
  };
}

List<Map<String, Object?>> _buildAiSquadSeed({
  required String clubId,
  required String clubName,
}) {
  final String alias = _buildAiClubAlias(clubName);
  final List<Map<String, Object?>> players = <Map<String, Object?>>[
    _buildAiSquadPlayer(
      clubId: clubId,
      suffix: 'keeper-1',
      name: '$alias Atlas',
      primaryPosition: 'GK',
      secondaryPositions: const <String>[],
      rating: 82,
      potential: 86,
      age: 26,
      fatigue: 0.17,
      stamina: 0.79,
      form: 0.73,
      injuryRisk: 0.14,
      wageCost: 52000,
      transferValue: 340000,
      morale: 0.72,
    ),
    _buildAiSquadPlayer(
      clubId: clubId,
      suffix: 'right-back-2',
      name: 'Kelechi Run',
      primaryPosition: 'RB',
      secondaryPositions: const <String>['RWB'],
      rating: 78,
      potential: 82,
      age: 24,
      fatigue: 0.28,
      stamina: 0.84,
      form: 0.68,
      injuryRisk: 0.19,
      wageCost: 34000,
      transferValue: 210000,
      morale: 0.7,
    ),
    _buildAiSquadPlayer(
      clubId: clubId,
      suffix: 'center-back-3',
      name: 'Omar Shield',
      primaryPosition: 'CB',
      secondaryPositions: const <String>['RB'],
      rating: 81,
      potential: 84,
      age: 27,
      fatigue: 0.22,
      stamina: 0.77,
      form: 0.74,
      injuryRisk: 0.13,
      wageCost: 46000,
      transferValue: 295000,
      morale: 0.76,
    ),
    _buildAiSquadPlayer(
      clubId: clubId,
      suffix: 'center-back-4',
      name: 'Victor Stone',
      primaryPosition: 'CB',
      secondaryPositions: const <String>['DM'],
      rating: 80,
      potential: 83,
      age: 25,
      fatigue: 0.24,
      stamina: 0.8,
      form: 0.71,
      injuryRisk: 0.16,
      wageCost: 42000,
      transferValue: 270000,
      morale: 0.73,
    ),
    _buildAiSquadPlayer(
      clubId: clubId,
      suffix: 'left-back-5',
      name: 'Dara Glide',
      primaryPosition: 'LB',
      secondaryPositions: const <String>['LWB'],
      rating: 77,
      potential: 81,
      age: 23,
      fatigue: 0.29,
      stamina: 0.86,
      form: 0.66,
      injuryRisk: 0.2,
      wageCost: 32000,
      transferValue: 205000,
      morale: 0.69,
    ),
    _buildAiSquadPlayer(
      clubId: clubId,
      suffix: 'midfield-6',
      name: 'Seyi Anchor',
      primaryPosition: 'DM',
      secondaryPositions: const <String>['CM'],
      rating: 80,
      potential: 84,
      age: 24,
      fatigue: 0.26,
      stamina: 0.82,
      form: 0.75,
      injuryRisk: 0.12,
      wageCost: 41000,
      transferValue: 255000,
      morale: 0.77,
    ),
    _buildAiSquadPlayer(
      clubId: clubId,
      suffix: 'midfield-7',
      name: 'Tobi Pulse',
      primaryPosition: 'CM',
      secondaryPositions: const <String>['AM'],
      rating: 81,
      potential: 87,
      age: 22,
      fatigue: 0.23,
      stamina: 0.83,
      form: 0.79,
      injuryRisk: 0.11,
      wageCost: 47000,
      transferValue: 315000,
      morale: 0.81,
    ),
    _buildAiSquadPlayer(
      clubId: clubId,
      suffix: 'midfield-8',
      name: 'Micah Vale',
      primaryPosition: 'CM',
      secondaryPositions: const <String>['RW'],
      rating: 79,
      potential: 88,
      age: 20,
      fatigue: 0.25,
      stamina: 0.8,
      form: 0.78,
      injuryRisk: 0.1,
      wageCost: 29000,
      transferValue: 280000,
      morale: 0.82,
    ),
    _buildAiSquadPlayer(
      clubId: clubId,
      suffix: 'wing-9',
      name: 'Enzo Flash',
      primaryPosition: 'RW',
      secondaryPositions: const <String>['LW'],
      rating: 80,
      potential: 85,
      age: 23,
      fatigue: 0.31,
      stamina: 0.85,
      form: 0.76,
      injuryRisk: 0.18,
      wageCost: 39000,
      transferValue: 265000,
      morale: 0.74,
    ),
    _buildAiSquadPlayer(
      clubId: clubId,
      suffix: 'striker-10',
      name: 'Kai Forge',
      primaryPosition: 'ST',
      secondaryPositions: const <String>['RW'],
      rating: 83,
      potential: 87,
      age: 24,
      fatigue: 0.27,
      stamina: 0.81,
      form: 0.8,
      injuryRisk: 0.15,
      wageCost: 56000,
      transferValue: 360000,
      morale: 0.79,
    ),
    _buildAiSquadPlayer(
      clubId: clubId,
      suffix: 'wing-11',
      name: 'Luka Drift',
      primaryPosition: 'LW',
      secondaryPositions: const <String>['AM'],
      rating: 79,
      potential: 84,
      age: 21,
      fatigue: 0.3,
      stamina: 0.84,
      form: 0.72,
      injuryRisk: 0.17,
      wageCost: 35000,
      transferValue: 245000,
      morale: 0.75,
    ),
    _buildAiSquadPlayer(
      clubId: clubId,
      suffix: 'bench-12',
      name: 'Rico Wall',
      primaryPosition: 'CB',
      secondaryPositions: const <String>['LB'],
      rating: 75,
      potential: 80,
      age: 28,
      fatigue: 0.18,
      stamina: 0.76,
      form: 0.64,
      injuryRisk: 0.14,
      wageCost: 26000,
      transferValue: 165000,
      morale: 0.7,
    ),
    _buildAiSquadPlayer(
      clubId: clubId,
      suffix: 'bench-13',
      name: 'Noah Craft',
      primaryPosition: 'CM',
      secondaryPositions: const <String>['DM'],
      rating: 74,
      potential: 79,
      age: 25,
      fatigue: 0.16,
      stamina: 0.78,
      form: 0.67,
      injuryRisk: 0.12,
      wageCost: 23000,
      transferValue: 150000,
      morale: 0.71,
    ),
    _buildAiSquadPlayer(
      clubId: clubId,
      suffix: 'bench-14',
      name: 'Jules Dash',
      primaryPosition: 'RW',
      secondaryPositions: const <String>['LW'],
      rating: 73,
      potential: 81,
      age: 20,
      fatigue: 0.21,
      stamina: 0.83,
      form: 0.69,
      injuryRisk: 0.12,
      wageCost: 21000,
      transferValue: 172000,
      morale: 0.76,
    ),
    _buildAiSquadPlayer(
      clubId: clubId,
      suffix: 'bench-15',
      name: 'Femi Link',
      primaryPosition: 'AM',
      secondaryPositions: const <String>['CM'],
      rating: 76,
      potential: 82,
      age: 23,
      fatigue: 0.19,
      stamina: 0.79,
      form: 0.73,
      injuryRisk: 0.11,
      wageCost: 27000,
      transferValue: 188000,
      morale: 0.78,
    ),
    _buildAiSquadPlayer(
      clubId: clubId,
      suffix: 'bench-16',
      name: 'Tade Bolt',
      primaryPosition: 'ST',
      secondaryPositions: const <String>['LW'],
      rating: 77,
      potential: 83,
      age: 22,
      fatigue: 0.24,
      stamina: 0.82,
      form: 0.74,
      injuryRisk: 0.13,
      wageCost: 30000,
      transferValue: 205000,
      morale: 0.77,
    ),
    _buildAiSquadPlayer(
      clubId: clubId,
      suffix: 'bench-17',
      name: 'Ibrahim Guard',
      primaryPosition: 'GK',
      secondaryPositions: const <String>[],
      rating: 72,
      potential: 78,
      age: 29,
      fatigue: 0.1,
      stamina: 0.7,
      form: 0.63,
      injuryRisk: 0.09,
      wageCost: 18000,
      transferValue: 110000,
      morale: 0.68,
    ),
    _buildAiSquadPlayer(
      clubId: clubId,
      suffix: 'bench-18',
      name: 'Milan Crest',
      primaryPosition: 'LB',
      secondaryPositions: const <String>['CB'],
      rating: 74,
      potential: 79,
      age: 24,
      fatigue: 0.22,
      stamina: 0.81,
      form: 0.65,
      injuryRisk: 0.14,
      wageCost: 22000,
      transferValue: 142000,
      morale: 0.72,
    ),
  ];
  return players;
}

Map<String, Object?> _buildAiSquadPlayer({
  required String clubId,
  required String suffix,
  required String name,
  required String primaryPosition,
  required List<String> secondaryPositions,
  required int rating,
  required int potential,
  required int age,
  required double fatigue,
  required double stamina,
  required double form,
  required double injuryRisk,
  required int wageCost,
  required int transferValue,
  required double morale,
}) {
  return <String, Object?>{
    'player_id': '$clubId-$suffix',
    'name': name,
    'primary_position': primaryPosition,
    'secondary_positions': secondaryPositions,
    'rating': rating,
    'potential': potential,
    'age': age,
    'fatigue': fatigue,
    'stamina': stamina,
    'form': form,
    'injury_risk': injuryRisk,
    'availability': 'available',
    'wage_cost': wageCost,
    'transfer_value': transferValue,
    'morale': morale,
  };
}

String _buildAiClubAlias(String clubName) {
  final List<String> parts = clubName
      .split(RegExp(r'[\s_-]+'))
      .where((String part) => part.trim().isNotEmpty)
      .toList(growable: false);
  if (parts.isEmpty) {
    return 'GTEX';
  }
  if (parts.length == 1) {
    final String single = parts.first.trim();
    return single.length <= 12 ? single : single.substring(0, 12);
  }
  return parts.take(2).join(' ');
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
    onOpenLogin:
        dependencies.onOpenLogin == null
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
    onOpenLogin:
        dependencies.onOpenLogin == null
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
      onOpenLogin:
          dependencies.onOpenLogin == null
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
      onOpenLogin:
          dependencies.onOpenLogin == null
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
      onOpenLogin:
          dependencies.onOpenLogin == null
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
      onOpenLogin:
          dependencies.onOpenLogin == null
              ? null
              : () {
                dependencies.onOpenLogin!.call(context);
              },
    ),
  );
}
