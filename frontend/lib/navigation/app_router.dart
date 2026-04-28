import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/actions/action_pipeline.dart';
import '../core/actions/event_service.dart';
import '../core/theme/app_motion.dart';
import '../controllers/competition_controller.dart';
import '../data/competition_api.dart';
import '../data/gte_api_repository.dart';
import '../features/competitions/live_competitions_hub_screen.dart';
import '../features/competitions/live_competitions_provider.dart';
import '../features/home/home_screen.dart';
import '../features/match/match_screen.dart';
import '../features/match/match_viewer_route_screen.dart';
import '../features/national_teams/national_teams_screen.dart';
import '../features/profile/profile_admin_screen.dart';
import '../features/profile/profile_login_screen.dart';
import '../features/profile/profile_screen.dart';
import '../features/profile/profile_signup_screen.dart';
import '../features/regens/regens_screen.dart';
import '../features/tasks/tasks_screen.dart';
import '../features/transfer_center/transfer_center_screen.dart';
import '../features/transfer_market/transfer_market_screen.dart';
import '../features/viral_feed/data/viral_feed_repository.dart';
import '../features/viral_feed/presentation/clips_blocked_screen.dart';
import '../features/viral_feed/presentation/viral_feed_screen.dart';
import '../features/federations/federations_hub_screen.dart';
import '../features/world/world_screen.dart';
import '../shared/models/auth_session.dart';
import '../shared/providers/auth_provider.dart';
import '../shared/widgets/app_shell_scaffold.dart';
import '../widgets/gte_route_integrity_screen.dart';
import '../screens/competitions/competition_create_screen.dart';
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
  final String apiBaseUrl = ref.watch(apiBaseUrlProvider);
  final EventService eventService = EventService.standard(
    baseUrl: apiBaseUrl,
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
                path: AppRoutes.competitions,
                pageBuilder:
                    (BuildContext context, GoRouterState state) =>
                        const NoTransitionPage<void>(
                          child: LiveCompetitionsHubScreen(),
                        ),
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
        path: AppRoutes.world,
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                AppMotion.slidePage<void>(
                  state: state,
                  child: const WorldScreen(),
                ),
      ),
      GoRoute(
        path: AppRoutes.transferCenter,
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                AppMotion.slidePage<void>(
                  state: state,
                  child: const TransferCenterScreen(),
                ),
      ),
      GoRoute(
        path: AppRoutes.transferCenterDetail,
        pageBuilder: (BuildContext context, GoRouterState state) {
          final String listingId = state.pathParameters['listingId'] ?? '';
          return AppMotion.slidePage<void>(
            state: state,
            child: TransferCenterDetailScreen(listingId: listingId),
          );
        },
      ),
      GoRoute(
        path: AppRoutes.regens,
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                AppMotion.slidePage<void>(
                  state: state,
                  child: const RegensScreen(),
                ),
      ),
      GoRoute(
        path: AppRoutes.federations,
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                AppMotion.slidePage<void>(
                  state: state,
                  child: const FederationsHubScreen(),
                ),
      ),
      GoRoute(
        path: AppRoutes.federationDetail,
        pageBuilder: (BuildContext context, GoRouterState state) {
          final String federationId =
              state.pathParameters['federationId'] ?? '';
          return AppMotion.slidePage<void>(
            state: state,
            child: FederationDetailScreen(federationId: federationId),
          );
        },
      ),
      GoRoute(
        path: AppRoutes.nationalTeams,
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                AppMotion.slidePage<void>(
                  state: state,
                  child: const NationalTeamsScreen(),
                ),
      ),
      GoRoute(
        path: AppRoutes.nationalTeamDetail,
        pageBuilder: (BuildContext context, GoRouterState state) {
          final String competitionId =
              state.pathParameters['competitionId'] ?? '';
          return AppMotion.slidePage<void>(
            state: state,
            child: NationalTeamCompetitionDetailScreen(
              competitionId: competitionId,
            ),
          );
        },
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
        pageBuilder: (BuildContext context, GoRouterState state) {
          final bool canOpenClips = authSession?.isAuthenticated ?? false;
          return AppMotion.slidePage<void>(
            state: state,
            child:
                canOpenClips
                    ? ViralFeedScreen(
                      currentUserId: authSession?.userId,
                      repository: ViralFeedApiRepository.standard(
                        baseUrl: apiBaseUrl,
                        authSession: authSession,
                        deviceId: deviceId,
                      ),
                      actionDispatcher: ActionPipeline(
                        eventService: eventService,
                      ),
                    )
                    : const ClipsBlockedScreen(),
          );
        },
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
        path: AppRoutes.competitionsCreate,
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                AppMotion.slidePage<void>(
                  state: state,
                  child: _CompetitionCreateRouteScreen(
                    baseUrl: apiBaseUrl,
                    backendMode: ref.watch(criticalBackendModeProvider),
                    accessToken: authSession?.accessToken,
                    currentUserId: authSession?.userId ?? '',
                    currentUserName: authSession?.resolvedUserName,
                    isAuthenticated: authSession?.isAuthenticated ?? false,
                  ),
                ),
      ),
      GoRoute(
        path: AppRoutes.streamerEngine,
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                _comingSoonPage(state, title: 'Streamer tournaments'),
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
        path: AppRoutes.matchesViewer,
        pageBuilder: (BuildContext context, GoRouterState state) {
          final String matchKey = state.pathParameters['matchKey'] ?? '';
          return AppMotion.slidePage<void>(
            state: state,
            child: MatchViewerRouteScreen(matchKey: matchKey),
          );
        },
      ),
      GoRoute(
        path: AppRoutes.matchesBroadcast,
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                _comingSoonPage(state, title: 'Broadcast package'),
      ),
      GoRoute(
        path: AppRoutes.matchesThreeD,
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                _comingSoonPage(state, title: 'Advanced match viewing'),
      ),
      GoRoute(
        path: AppRoutes.matchesNativeThreeD,
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                _comingSoonPage(state, title: 'Advanced match viewing'),
      ),
      GoRoute(
        path: AppRoutes.matchesSpectate,
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                _comingSoonPage(state, title: 'Spectate mode'),
      ),
      GoRoute(
        path: AppRoutes.matchesSimulate,
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                _comingSoonPage(state, title: 'Match simulation tools'),
      ),
    ],
  );
});

Page<void> _comingSoonPage(GoRouterState state, {required String title}) {
  return AppMotion.slidePage<void>(
    state: state,
    child: GteRouteIntegrityScreen.blocked(
      eyebrow: 'COMING SOON',
      title: '$title coming soon',
      message:
          'This route is blocked for launch while GTEX focuses on the 2D football manager experience.',
      icon: Icons.lock_clock_outlined,
    ),
  );
}

class _CompetitionCreateRouteScreen extends StatefulWidget {
  const _CompetitionCreateRouteScreen({
    required this.baseUrl,
    required this.backendMode,
    required this.accessToken,
    required this.currentUserId,
    required this.currentUserName,
    required this.isAuthenticated,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final String currentUserId;
  final String? currentUserName;
  final bool isAuthenticated;

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
      api: CompetitionApi.standard(
        baseUrl: widget.baseUrl,
        mode: widget.backendMode,
        accessToken: widget.accessToken,
      ),
      currentUserId: widget.currentUserId,
      currentUserName: widget.currentUserName,
    )..startNewDraft();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return CompetitionCreateScreen(
      controller: _controller,
      isAuthenticated: widget.isAuthenticated,
      isCheckingHostEligibility: false,
      hostEligible: widget.isAuthenticated,
      onOpenLogin: () => context.push(AppRoutes.profileLogin),
    );
  }
}
