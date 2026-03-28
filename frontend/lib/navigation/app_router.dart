import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/theme/app_motion.dart';
import '../features/home/home_screen.dart';
import '../features/match/match_screen.dart';
import '../features/profile/profile_screen.dart';
import '../features/tasks/tasks_screen.dart';
import '../features/transfer_market/transfer_market_screen.dart';
import '../features/viral_feed/presentation/viral_feed_screen.dart';
import '../features/world/world_screen.dart';
import '../shared/widgets/app_shell_scaffold.dart';
import 'app_destinations.dart';

final Provider<GoRouter> appRouterProvider = Provider<GoRouter>(
  (Ref ref) => GoRouter(
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
                  child: const ViralFeedScreen(),
                ),
      ),
    ],
  ),
);
