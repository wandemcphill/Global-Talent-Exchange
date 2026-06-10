import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/features/app_routes/gte_app_route_registry.dart';
import 'package:gte_frontend/features/app_routes/gte_route_data.dart';
import 'package:gte_frontend/features/app_routes/gte_navigation_helpers.dart';
import 'package:gte_frontend/features/navigation/routing/gte_navigation_route.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/features/shell/presentation/gtex_public_home_screen.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/router/route_constants.dart';
import 'package:gte_frontend/screens/gte_exchange_shell_screen.dart';
import 'package:gte_frontend/screens/gte_login_screen.dart';
import 'package:gte_frontend/screens/gte_signup_screen.dart';
import 'package:gte_frontend/widgets/gte_route_integrity_screen.dart';

const String gteShellHomeRouteName = 'shell.home';
const String gteShellLaneRouteName = 'shell.lane';
const String gteShellSubLaneRouteName = 'shell.sub-lane';

GoRouter buildGtexAppRouter({
  required String initialLocation,
  required GteExchangeController controller,
  required GteAppConfig config,
  required GteNavigationDependencies Function(BuildContext context)
  dependenciesBuilder,
}) {
  return GoRouter(
    initialLocation: _normalizeInitialLocation(initialLocation),
    refreshListenable: controller,
    routes: <RouteBase>[
      GoRoute(
        path: '/',
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                const NoTransitionPage<void>(child: GtexPublicHomeScreen()),
      ),
      GoRoute(
        path: '/public',
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                const NoTransitionPage<void>(child: GtexPublicHomeScreen()),
      ),
      GoRoute(
        path: GtexCanonicalAppRoutes.app,
        redirect:
            (BuildContext context, GoRouterState state) =>
                const GteNavigationRoute.home().path,
      ),
      GoRoute(
        path: '/auth',
        redirect: (BuildContext context, GoRouterState state) => '/auth/signup',
      ),
      GoRoute(
        path: '/auth/login',
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                NoTransitionPage<void>(
                  child: GteLoginScreen(controller: controller),
                ),
      ),
      GoRoute(
        path: '/auth/region',
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                const NoTransitionPage<void>(
                  child: GtexRegionSelectionScreen(),
                ),
      ),
      GoRoute(
        path: '/auth/signup',
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                NoTransitionPage<void>(
                  child: GteSignupScreen(controller: controller),
                ),
      ),
      ..._buildLegacyCompetitionAliasRoutes(
        dependenciesBuilder: dependenciesBuilder,
      ),
      ..._buildRegisteredFeatureRoutes(
        dependenciesBuilder: dependenciesBuilder,
      ),
      ..._buildCanonicalAppRoutes(controller: controller, config: config),
    ],
    errorBuilder:
        (BuildContext context, GoRouterState state) =>
            GteRouteIntegrityScreen.blocked(
              eyebrow: 'ROUTE ERROR',
              title: 'Route unavailable',
              message:
                  state.error?.toString() ??
                  'The requested route is not registered in the GTEX router.',
              icon: Icons.alt_route_outlined,
            ),
  );
}

List<RouteBase> _buildCanonicalAppRoutes({
  required GteExchangeController controller,
  required GteAppConfig config,
}) {
  return GtexCanonicalAppRoutes.shellRoots
      .map((String path) {
        return GoRoute(
          path: path,
          pageBuilder:
              (BuildContext context, GoRouterState state) => _buildShellPage(
                state: state,
                controller: controller,
                config: config,
              ),
          routes: <RouteBase>[
            GoRoute(
              path: ':screen',
              pageBuilder:
                  (BuildContext context, GoRouterState state) =>
                      _buildShellPage(
                        state: state,
                        controller: controller,
                        config: config,
                      ),
            ),
            GoRoute(
              path: ':screen/:id',
              pageBuilder:
                  (BuildContext context, GoRouterState state) =>
                      _buildShellPage(
                        state: state,
                        controller: controller,
                        config: config,
                      ),
            ),
            GoRoute(
              path: ':screen/:id/:detail',
              pageBuilder:
                  (BuildContext context, GoRouterState state) =>
                      _buildShellPage(
                        state: state,
                        controller: controller,
                        config: config,
                      ),
            ),
          ],
        );
      })
      .toList(growable: false);
}

List<RouteBase> _buildLegacyCompetitionAliasRoutes({
  required GteNavigationDependencies Function(BuildContext context)
  dependenciesBuilder,
}) {
  return <RouteBase>[
    GoRoute(
      path: '/competitions/gtex',
      pageBuilder:
          (BuildContext context, GoRouterState state) => _buildFeatureRoutePage(
            context: context,
            state: state,
            route: CompetitionsDiscoveryRouteData(highlight: 'gtex'),
            dependencies: dependenciesBuilder(context),
          ),
    ),
    GoRoute(
      path: '/competitions/hosted',
      pageBuilder:
          (BuildContext context, GoRouterState state) => _buildFeatureRoutePage(
            context: context,
            state: state,
            route: CompetitionsDiscoveryRouteData(highlight: 'hosted'),
            dependencies: dependenciesBuilder(context),
          ),
    ),
    GoRoute(
      path: '/competitions/streamer',
      pageBuilder:
          (BuildContext context, GoRouterState state) => _buildFeatureRoutePage(
            context: context,
            state: state,
            route: const StreamerTournamentsListRouteData(),
            dependencies: dependenciesBuilder(context),
          ),
    ),
    GoRoute(
      path: '/competitions/gtex/:competitionId',
      pageBuilder: (BuildContext context, GoRouterState state) {
        final String? competitionId = state.pathParameters['competitionId'];
        if (competitionId == null || competitionId.trim().isEmpty) {
          return _buildUnavailablePage(
            state: state,
            message:
                'The requested competition route is missing a competition id.',
          );
        }
        return _buildFeatureRoutePage(
          context: context,
          state: state,
          route: CompetitionDetailRouteData(competitionId: competitionId),
          dependencies: dependenciesBuilder(context),
        );
      },
    ),
    GoRoute(
      path: '/competitions/hosted/:competitionId',
      pageBuilder: (BuildContext context, GoRouterState state) {
        final String? competitionId = state.pathParameters['competitionId'];
        if (competitionId == null || competitionId.trim().isEmpty) {
          return _buildUnavailablePage(
            state: state,
            message:
                'The requested competition route is missing a competition id.',
          );
        }
        return _buildFeatureRoutePage(
          context: context,
          state: state,
          route: CompetitionDetailRouteData(competitionId: competitionId),
          dependencies: dependenciesBuilder(context),
        );
      },
    ),
    GoRoute(
      path: '/competitions/streamer/:tournamentId',
      pageBuilder: (BuildContext context, GoRouterState state) {
        final String? tournamentId = state.pathParameters['tournamentId'];
        if (tournamentId == null || tournamentId.trim().isEmpty) {
          return _buildUnavailablePage(
            state: state,
            message:
                'The requested streamer tournament route is missing a tournament id.',
          );
        }
        return _buildFeatureRoutePage(
          context: context,
          state: state,
          route: StreamerTournamentDetailRouteData(tournamentId: tournamentId),
          dependencies: dependenciesBuilder(context),
        );
      },
    ),
  ];
}

List<RouteBase> _buildRegisteredFeatureRoutes({
  required GteNavigationDependencies Function(BuildContext context)
  dependenciesBuilder,
}) {
  final List<GteAppRouteRegistration> registrations = GteAppRouteCatalog
    .registrations
    .toList(growable: false)..sort(_compareRouteRegistrationSpecificity);
  return registrations
      .map(
        (GteAppRouteRegistration registration) => GoRoute(
          path: registration.path,
          pageBuilder: (BuildContext context, GoRouterState state) {
            final GteAppRouteData? route = GteNavigationHelpers.parseDeepLink(
              state.uri.toString(),
            );
            if (route == null) {
              return _buildUnavailablePage(
                state: state,
                message:
                    'The requested route is not registered in the GTEX router.',
              );
            }
            return _buildFeatureRoutePage(
              context: context,
              state: state,
              route: route,
              dependencies: dependenciesBuilder(context),
            );
          },
        ),
      )
      .toList(growable: false);
}

int _compareRouteRegistrationSpecificity(
  GteAppRouteRegistration left,
  GteAppRouteRegistration right,
) {
  final int leftParams = _routeParameterCount(left.path);
  final int rightParams = _routeParameterCount(right.path);
  if (leftParams != rightParams) {
    return leftParams.compareTo(rightParams);
  }

  final int leftSegments = _routeSegmentCount(left.path);
  final int rightSegments = _routeSegmentCount(right.path);
  if (leftSegments != rightSegments) {
    return rightSegments.compareTo(leftSegments);
  }

  final int leftStaticSegments = leftSegments - leftParams;
  final int rightStaticSegments = rightSegments - rightParams;
  if (leftStaticSegments != rightStaticSegments) {
    return rightStaticSegments.compareTo(leftStaticSegments);
  }

  return left.path.compareTo(right.path);
}

int _routeParameterCount(String path) {
  return path
      .split('/')
      .where((String segment) => segment.startsWith(':'))
      .length;
}

int _routeSegmentCount(String path) {
  return path.split('/').where((String segment) => segment.isNotEmpty).length;
}

Page<void> _buildFeatureRoutePage({
  required BuildContext context,
  required GoRouterState state,
  required GteAppRouteData route,
  required GteNavigationDependencies dependencies,
}) {
  final GteAppRouteRegistry registry = GteAppRouteRegistry(
    dependencies: dependencies,
  );
  return NoTransitionPage<void>(
    key: state.pageKey,
    child: registry.buildScreen(context, route),
  );
}

Page<void> _buildUnavailablePage({
  required GoRouterState state,
  required String message,
}) {
  return NoTransitionPage<void>(
    key: state.pageKey,
    child: GteRouteIntegrityScreen.blocked(
      eyebrow: 'ROUTE ERROR',
      title: 'Route unavailable',
      message: message,
      icon: Icons.alt_route_outlined,
    ),
  );
}

Page<void> _buildShellPage({
  required GoRouterState state,
  required GteExchangeController controller,
  required GteAppConfig config,
}) {
  return NoTransitionPage<void>(
    key: state.pageKey,
    child: GteExchangeShellScreen.fromPath(
      controller: controller,
      apiBaseUrl: config.apiBaseUrl,
      backendMode: config.activeShellBackendMode,
      initialPath: state.uri.toString(),
    ),
  );
}

String _normalizeInitialLocation(String location) {
  final String normalized = location.trim();
  if (normalized.isEmpty) {
    return '/public';
  }
  final String rooted =
      normalized.startsWith('/') ? normalized : '/$normalized';
  final Uri? uri = Uri.tryParse(rooted);
  if (uri == null) {
    return rooted;
  }
  final String? canonicalPath = _canonicalPathForLegacyReference(uri.path);
  if (canonicalPath == null) {
    return rooted;
  }
  return uri.replace(path: canonicalPath).toString();
}

String? _canonicalPathForLegacyReference(String path) {
  if (path == '/home' || path == '/world' || path.startsWith('/world/')) {
    return const GteNavigationRoute.home().path;
  }
  if (path == '/market' ||
      path == '/market/transfers' ||
      path == '/football/transfer-center' ||
      path == '/player-cards' ||
      path.startsWith('/player-cards/')) {
    return const GteNavigationRoute.market().path;
  }
  if (path == '/streamer-tournaments' ||
      path.startsWith('/streamer-tournaments/') ||
      path == '/competitions/streamer' ||
      path.startsWith('/competitions/streamer/')) {
    return path;
  }
  if (path == '/competitions' ||
      path.startsWith('/competitions/') ||
      path == '/national-team' ||
      path.startsWith('/national-team/')) {
    return const GteNavigationRoute.competitions().path;
  }
  if (path == '/news') {
    return const GteNavigationRoute.home().path;
  }
  if (path == '/clips') {
    return const GteNavigationRoute.community().path;
  }
  if (path == '/trader' || path.startsWith('/trader/')) {
    return const GteNavigationRoute.wallet().path;
  }
  return null;
}
