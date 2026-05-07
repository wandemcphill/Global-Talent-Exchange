import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/features/app_routes/gte_app_route_registry.dart';
import 'package:gte_frontend/features/app_routes/gte_navigation_helpers.dart';
import 'package:gte_frontend/features/app_routes/gte_route_data.dart';
import 'package:gte_frontend/features/navigation/routing/gte_navigation_route.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/gte_exchange_shell_screen.dart';
import 'package:gte_frontend/services/ambient_audio_controller.dart';
import 'package:gte_frontend/widgets/gte_route_integrity_screen.dart';

const String gteShellHomeRouteName = 'shell.home';
const String gteShellLaneRouteName = 'shell.lane';
const String gteShellSubLaneRouteName = 'shell.sub-lane';

GoRouter buildGtexAppRouter({
  required String initialLocation,
  required GteExchangeController controller,
  required GteAppConfig config,
  required AmbientAudioState ambientAudioController,
  required GteNavigationDependencies Function(BuildContext context)
  dependenciesBuilder,
}) {
  return GoRouter(
    initialLocation: _normalizeInitialLocation(initialLocation),
    refreshListenable: controller,
    routes: <RouteBase>[
      GoRoute(
        path: '/',
        redirect:
            (BuildContext context, GoRouterState state) =>
                const GteNavigationRoute.home().path,
      ),
      GoRoute(
        path: '/app',
        redirect:
            (BuildContext context, GoRouterState state) =>
                const GteNavigationRoute.home().path,
      ),
      GoRoute(
        path: '/app/:section',
        name: gteShellLaneRouteName,
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                NoTransitionPage<void>(
                  key: state.pageKey,
                  child: GteExchangeShellScreen.fromPath(
                    controller: controller,
                    apiBaseUrl: config.apiBaseUrl,
                    backendMode: config.activeShellBackendMode,
                    ambientAudioController: ambientAudioController,
                    initialPath: state.uri.toString(),
                  ),
                ),
        routes: <RouteBase>[
          GoRoute(
            path: ':subsection',
            name: gteShellSubLaneRouteName,
            pageBuilder:
                (BuildContext context, GoRouterState state) =>
                    NoTransitionPage<void>(
                      key: state.pageKey,
                      child: GteExchangeShellScreen.fromPath(
                        controller: controller,
                        apiBaseUrl: config.apiBaseUrl,
                        backendMode: config.activeShellBackendMode,
                        ambientAudioController: ambientAudioController,
                        initialPath: state.uri.toString(),
                      ),
                    ),
          ),
        ],
      ),
      ..._buildLegacyAliasRoutes(),
      ..._buildFeatureRoutes(dependenciesBuilder: dependenciesBuilder),
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

List<RouteBase> _buildLegacyAliasRoutes() {
  return <RouteBase>[
    GoRoute(
      path: '/world',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const GteNavigationRoute.hub().path,
    ),
    GoRoute(
      path: '/market',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const GteNavigationRoute.market().path,
    ),
    GoRoute(
      path: '/market/transfers',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const GteNavigationRoute.market().path,
    ),
    GoRoute(
      path: '/football/transfer-center',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const GteNavigationRoute.market().path,
    ),
    GoRoute(
      path: '/player-cards',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const GteNavigationRoute.market().path,
    ),
    GoRoute(
      path: '/competitions',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const GteNavigationRoute.competitions().path,
    ),
    GoRoute(
      path: '/competitions/hosted',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const GteNavigationRoute.competitions().path,
    ),
    GoRoute(
      path: '/competitions/gtex',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const GteNavigationRoute.competitions().path,
    ),
    GoRoute(
      path: '/world/regens',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const GteNavigationRoute.hub().path,
    ),
    GoRoute(
      path: '/national-team',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const GteNavigationRoute.competitions().path,
    ),
    GoRoute(
      path: '/streamer-tournaments',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const GteNavigationRoute.competitions().path,
    ),
    GoRoute(
      path: '/news',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const GteNavigationRoute.hub().path,
    ),
    GoRoute(
      path: '/clips',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const GteNavigationRoute.hub().path,
    ),
  ];
}

List<RouteBase> _buildFeatureRoutes({
  required GteNavigationDependencies Function(BuildContext context)
  dependenciesBuilder,
}) {
  const Set<String> shellOwnedPaths = <String>{
    '/competitions',
    '/player-cards',
    '/world',
    '/world/regens',
    '/news',
    '/national-team',
    '/football/transfer-center',
    '/streamer-tournaments',
  };
  return GteAppRouteCatalog.registrations
      .where(
        (GteAppRouteRegistration route) =>
            !shellOwnedPaths.contains(route.path),
      )
      .map((GteAppRouteRegistration route) {
        return GoRoute(
          path: route.path,
          name: route.name,
          pageBuilder: (BuildContext context, GoRouterState state) {
            final GteNavigationDependencies dependencies = dependenciesBuilder(
              context,
            );
            final GteAppRouteRegistry registry = GteAppRouteRegistry(
              dependencies: dependencies,
            );
            final GteAppRouteData featureRoute =
                GteNavigationHelpers.requireNamedRoute(
                  route.name,
                  pathParameters: state.pathParameters,
                  queryParameters: state.uri.queryParameters,
                );
            return MaterialPage<void>(
              key: state.pageKey,
              child: registry.buildScreen(context, featureRoute),
            );
          },
        );
      })
      .toList(growable: false);
}

String _normalizeInitialLocation(String location) {
  final String normalized = location.trim();
  if (normalized.isEmpty) {
    return const GteNavigationRoute.home().path;
  }
  return normalized.startsWith('/') ? normalized : '/$normalized';
}
