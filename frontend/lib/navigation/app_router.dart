import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/actions/action_pipeline.dart';
import '../core/actions/event_service.dart';
import '../core/theme/app_motion.dart';
import '../features/competitions/live_competitions_hub_screen.dart';
import '../features/competitions/live_competitions_provider.dart';
import '../features/home/home_screen.dart';
import '../features/match/match_screen.dart';
import '../features/match/match_simulate_screen.dart';
import '../features/match/match_spectate_screen.dart';
import '../features/profile/profile_admin_screen.dart';
import '../features/profile/profile_login_screen.dart';
import '../features/profile/profile_screen.dart';
import '../features/profile/profile_signup_screen.dart';
import '../features/tasks/tasks_screen.dart';
import '../features/transfer_market/transfer_market_screen.dart';
import '../features/viral_feed/data/viral_feed_repository.dart';
import '../features/viral_feed/presentation/viral_feed_screen.dart';
import '../features/world/world_screen.dart';
import '../shared/models/auth_session.dart';
import '../shared/providers/auth_provider.dart';
import '../shared/widgets/app_shell_scaffold.dart';
import 'app_destinations.dart';

CompetitionFamilyRoute _competitionFamilyFromSegment(String value) {
  switch (value.trim().toLowerCase()) {
    case 'hosted':
      return CompetitionFamilyRoute.hosted;
    case 'streamer':
      return CompetitionFamilyRoute.streamer;
    default:
      return CompetitionFamilyRoute.gtex;
  }
}

final Provider<GoRouter> appRouterProvider = Provider<GoRouter>((Ref ref) {
  final AuthSession? authSession = ref.watch(authProvider);
  final String deviceId = ref.watch(deviceIdProvider);
  final EventService eventService = EventService.standard(
    authSessionStore: ref.watch(authSessionStoreProvider),
    deviceIdentityStore: ref.watch(deviceIdentityStoreProvider),
    deviceId: deviceId,
  );

  return GoRouter(
    initialLocation: AppRoutes.home,
    routes: <RouteBase>[
      GoRoute(
        path: AppRoutes.root,
        redirect: (BuildContext context, GoRouterState state) => AppRoutes.home,
      ),
      StatefulShellRoute.indexedStack(
        builder: (
          BuildContext context,
          GoRouterState state,
          StatefulNavigationShell navigationShell,
        ) {
          return AppShellScaffold(navigationShell: navigationShell);
        },
        branches: <StatefulShellBranch>[
          StatefulShellBranch(
            routes: <RouteBase>[
              GoRoute(
                path: AppRoutes.home,
                pageBuilder:
                    (BuildContext context, GoRouterState state) =>
                        const NoTransitionPage<void>(child: HomeScreen()),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: <RouteBase>[
              GoRoute(
                path: AppRoutes.matches,
                pageBuilder:
                    (BuildContext context, GoRouterState state) =>
                        const NoTransitionPage<void>(child: MatchScreen()),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: <RouteBase>[
              GoRoute(
                path: AppRoutes.market,
                pageBuilder:
                    (BuildContext context, GoRouterState state) =>
                        const NoTransitionPage<void>(
                          child: TransferMarketScreen(),
                        ),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: <RouteBase>[
              GoRoute(
                path: AppRoutes.world,
                pageBuilder:
                    (BuildContext context, GoRouterState state) =>
                        const NoTransitionPage<void>(child: WorldScreen()),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: <RouteBase>[
              GoRoute(
                path: AppRoutes.profile,
                pageBuilder:
                    (BuildContext context, GoRouterState state) =>
                        const NoTransitionPage<void>(child: ProfileScreen()),
              ),
            ],
          ),
        ],
      ),
      GoRoute(
        path: AppRoutes.tasks,
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                AppMotion.slidePage<void>(
                  state: state,
                  child: const TasksScreen(),
                ),
      ),
      GoRoute(
        path: AppRoutes.clips,
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                AppMotion.slidePage<void>(
                  state: state,
                  child: ViralFeedScreen(
                    currentUserId: authSession?.userId,
                    repository: ViralFeedApiRepository.standard(
                      authSession: authSession,
                      deviceId: deviceId,
                    ),
                    actionDispatcher: ActionPipeline(
                      eventService: eventService,
                    ),
                  ),
                ),
      ),
      GoRoute(
        path: AppRoutes.profileLogin,
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                AppMotion.slidePage<void>(
                  state: state,
                  child: const ProfileLoginScreen(),
                ),
      ),
      GoRoute(
        path: AppRoutes.profileSignup,
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                AppMotion.slidePage<void>(
                  state: state,
                  child: const ProfileSignupScreen(),
                ),
      ),
      GoRoute(
        path: AppRoutes.profileAdmin,
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                AppMotion.slidePage<void>(
                  state: state,
                  child: const ProfileAdminScreen(),
                ),
      ),
      GoRoute(
        path: AppRoutes.competitions,
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                AppMotion.slidePage<void>(
                  state: state,
                  child: const LiveCompetitionsHubScreen(),
                ),
      ),
      GoRoute(
        path: AppRoutes.competitionsFamily,
        pageBuilder: (BuildContext context, GoRouterState state) {
          final String family = state.pathParameters['family'] ?? 'gtex';
          return AppMotion.slidePage<void>(
            state: state,
            child: LiveCompetitionsHubScreen(
              family: _competitionFamilyFromSegment(family),
            ),
          );
        },
      ),
      GoRoute(
        path: AppRoutes.competitionsDetail,
        pageBuilder: (BuildContext context, GoRouterState state) {
          final String family = state.pathParameters['family'] ?? 'gtex';
          final String id = state.pathParameters['id'] ?? '';
          return AppMotion.slidePage<void>(
            state: state,
            child: LiveCompetitionDetailScreen(
              family: _competitionFamilyFromSegment(family),
              competitionId: id,
            ),
          );
        },
      ),
      GoRoute(
        path: AppRoutes.matchesSpectate,
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                AppMotion.slidePage<void>(
                  state: state,
                  child: const MatchSpectateScreen(),
                ),
      ),
      GoRoute(
        path: AppRoutes.matchesSimulate,
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                AppMotion.slidePage<void>(
                  state: state,
                  child: const MatchSimulateScreen(),
                ),
      ),
    ],
  );
});
