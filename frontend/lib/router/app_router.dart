import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/features/app_routes/gte_app_route_registry.dart';
import 'package:gte_frontend/features/app_routes/gte_route_data.dart';
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
      GoRoute(
        path: '/matches',
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                _buildFeatureRoutePage(
                  context: context,
                  state: state,
                  route: const LiveMatchHubRouteData(),
                  dependencies: dependenciesBuilder(context),
                ),
      ),
      GoRoute(
        path: '/matches/viewer/:matchKey',
        pageBuilder: (BuildContext context, GoRouterState state) {
          final String? matchKey = state.pathParameters['matchKey'];
          if (matchKey == null || matchKey.trim().isEmpty) {
            return _buildUnavailablePage(
              state: state,
              message:
                  'The requested match center route is missing a match key.',
            );
          }
          return _buildFeatureRoutePage(
            context: context,
            state: state,
            route: LiveMatchViewerRouteData(matchKey: matchKey),
            dependencies: dependenciesBuilder(context),
          );
        },
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
  if (path == '/competitions' ||
      path.startsWith('/competitions/') ||
      path == '/national-team' ||
      path.startsWith('/national-team/') ||
      path == '/streamer-tournaments' ||
      path.startsWith('/streamer-tournaments/')) {
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
