import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/core/runtime/gtex_runtime_graph.dart';
import 'package:gte_frontend/core/runtime/gtex_runtime_models.dart';
import 'package:gte_frontend/features/app_routes/gte_app_route_registry.dart';
import 'package:gte_frontend/features/app_routes/gte_navigation_helpers.dart';
import 'package:gte_frontend/features/app_routes/gte_route_data.dart';
import 'package:gte_frontend/features/coin_trader_redesign/coin_trader_redesign.dart';
import 'package:gte_frontend/features/launch_control_redesign/gtex_feature_flags_launch_control_screen_v2.dart';
import 'package:gte_frontend/features/launch_control_redesign/launch_control_feature_gate.dart';
import 'package:gte_frontend/features/match/gte_live_match_hub_route_screen.dart';
import 'package:gte_frontend/features/match/match_viewer_route_screen.dart';
import 'package:gte_frontend/features/matchday_economy_redesign/matchday_economy_screen.dart';
import 'package:gte_frontend/features/navigation/routing/gte_navigation_route.dart';
import 'package:gte_frontend/features/federations/federations_hub_screen.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/router/gtex_auth_routes.dart';
import 'package:gte_frontend/screens/auth/gtex_account_signup_screens.dart';
import 'package:gte_frontend/navigation/app_destinations.dart';
import 'package:gte_frontend/screens/admin/admin_command_center_screen.dart';
import 'package:gte_frontend/shared/auth/gtex_admin_capabilities.dart';
import 'package:gte_frontend/screens/admin/gtex_admin_notification_matrix_screen.dart';
import 'package:gte_frontend/screens/admin/gtex_admin_trust_ops_screen_v2.dart';
import 'package:gte_frontend/screens/gte_login_screen.dart';
import 'package:gte_frontend/screens/gte_exchange_shell_screen.dart';
import 'package:gte_frontend/screens/gtex_public_landing_screen_v2.dart';
import 'package:gte_frontend/screens/gtex_national_team_rental_screen_v2.dart';
import 'package:gte_frontend/screens/manager_market_screen.dart';
import 'package:gte_frontend/features/player_detail/gtex_fm_player_profile_screen.dart';
import 'package:gte_frontend/features/club/gtex_lineup_editor_screen.dart';
import 'package:gte_frontend/screens/match/gtex_match_center_screen_v2.dart';
import 'package:gte_frontend/screens/notifications/gte_notifications_screen_v2.dart';
import 'package:gte_frontend/screens/profile/gtex_live_profile_screen.dart';
import 'package:gte_frontend/screens/support/gte_support_dispute_screens.dart';
import 'package:gte_frontend/screens/wallet/gte_kyc_screen.dart';
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
                controller.isAuthenticated
                    ? const GteNavigationRoute.home().path
                    : null,
        pageBuilder:
            (BuildContext context, GoRouterState state) => _landingPage(
              context: context,
              state: state,
              controller: controller,
            ),
      ),
      GoRoute(
        path: '/landing',
        pageBuilder:
            (BuildContext context, GoRouterState state) => _landingPage(
              context: context,
              state: state,
              controller: controller,
            ),
      ),
      GoRoute(
        path: '/app',
        redirect:
            (BuildContext context, GoRouterState state) =>
                const GteNavigationRoute.home().path,
      ),
      GoRoute(
        path: '/auth',
        redirect:
            (BuildContext context, GoRouterState state) =>
                gtexAccountSelectRoute,
      ),
      GoRoute(
        path: gtexAccountSelectRoute,
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                const NoTransitionPage<void>(
                  child: GtexAccountSelectorScreen(),
                ),
      ),
      GoRoute(
        path: gtexLoginRoute,
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                NoTransitionPage<void>(
                  key: state.pageKey,
                  child: GteLoginScreen(controller: controller),
                ),
      ),
      GoRoute(
        path: gtexLegacyAccountSelectRoute,
        redirect:
            (BuildContext context, GoRouterState state) =>
                gtexAccountSelectRoute,
      ),
      GoRoute(
        path: gtexUserSignupRoute,
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                NoTransitionPage<void>(
                  key: state.pageKey,
                  child: GtexUserSignupScreen(
                    controller: controller,
                    config: config,
                  ),
                ),
      ),
      GoRoute(
        path: gtexCreatorSignupRoute,
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                NoTransitionPage<void>(
                  key: state.pageKey,
                  child: GtexCreatorSignupScreen(
                    controller: controller,
                    config: config,
                  ),
                ),
      ),
      GoRoute(
        path: gtexTraderSignupRoute,
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                NoTransitionPage<void>(
                  key: state.pageKey,
                  child: GtexTraderSignupScreen(
                    controller: controller,
                    config: config,
                  ),
                ),
      ),
      GoRoute(
        path: '/trader',
        redirect:
            (BuildContext context, GoRouterState state) =>
                const GteNavigationRoute.wallet(
                  capitalDestination: GteCapitalDestination.coinTraders,
                ).path,
      ),
      GoRoute(
        path: '/app/transfer-hub',
        redirect:
            (BuildContext context, GoRouterState state) =>
                const GteNavigationRoute.market().path,
      ),
      GoRoute(
        path: '/app/coin-traders',
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                NoTransitionPage<void>(
                  key: state.pageKey,
                  child: _GtexLaunchControlledShellRoute(
                    controller: controller,
                    ambientAudioController: ambientAudioController,
                    config: config,
                    initialPath: state.uri.toString(),
                    dependenciesBuilder: dependenciesBuilder,
                  ),
                ),
      ),
      GoRoute(
        path: '/app/trader-dashboard',
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                NoTransitionPage<void>(
                  key: state.pageKey,
                  child: _GtexLaunchControlledShellRoute(
                    controller: controller,
                    ambientAudioController: ambientAudioController,
                    config: config,
                    initialPath: state.uri.toString(),
                    dependenciesBuilder: dependenciesBuilder,
                  ),
                ),
      ),
      GoRoute(
        path: '/app/:section',
        name: gteShellLaneRouteName,
        pageBuilder:
            (BuildContext context, GoRouterState state) =>
                NoTransitionPage<void>(
                  key: state.pageKey,
                  child: _GtexLaunchControlledShellRoute(
                    controller: controller,
                    ambientAudioController: ambientAudioController,
                    config: config,
                    initialPath: state.uri.toString(),
                    dependenciesBuilder: dependenciesBuilder,
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
                      child: _GtexLaunchControlledShellRoute(
                        controller: controller,
                        ambientAudioController: ambientAudioController,
                        config: config,
                        initialPath: state.uri.toString(),
                        dependenciesBuilder: dependenciesBuilder,
                      ),
                    ),
          ),
        ],
      ),
      ..._buildLegacyAliasRoutes(
        controller: controller,
        config: config,
        dependenciesBuilder: dependenciesBuilder,
      ),
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

class _GtexLaunchControlledShellRoute extends StatefulWidget {
  const _GtexLaunchControlledShellRoute({
    required this.controller,
    required this.config,
    required this.ambientAudioController,
    required this.initialPath,
    required this.dependenciesBuilder,
  });

  final GteExchangeController controller;
  final GteAppConfig config;
  final AmbientAudioState ambientAudioController;
  final String initialPath;
  final GteNavigationDependencies Function(BuildContext context)
  dependenciesBuilder;

  @override
  State<_GtexLaunchControlledShellRoute> createState() =>
      _GtexLaunchControlledShellRouteState();
}

class _GtexLaunchControlledShellRouteState
    extends State<_GtexLaunchControlledShellRoute> {
  late Future<GtexFeatureGateDecision> _decisionFuture;

  @override
  void initState() {
    super.initState();
    _decisionFuture = _resolveGate();
  }

  @override
  void didUpdateWidget(covariant _GtexLaunchControlledShellRoute oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.initialPath != widget.initialPath ||
        oldWidget.controller.accessToken != widget.controller.accessToken ||
        oldWidget.controller.isAdmin != widget.controller.isAdmin ||
        oldWidget.config.apiBaseUrl != widget.config.apiBaseUrl ||
        oldWidget.config.activeShellBackendMode !=
            widget.config.activeShellBackendMode) {
      _decisionFuture = _resolveGate();
    }
  }

  Future<GtexFeatureGateDecision> _resolveGate() {
    return GtexLaunchControlFeatureGate.resolveRoutePath(
      route: widget.initialPath,
      baseUrl: widget.config.apiBaseUrl,
      backendMode: widget.config.activeShellBackendMode,
      accessToken: widget.controller.accessToken,
      isAdmin: widget.controller.isAdmin,
    );
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<GtexFeatureGateDecision>(
      future: _decisionFuture,
      builder: (
        BuildContext context,
        AsyncSnapshot<GtexFeatureGateDecision> snapshot,
      ) {
        final GtexFeatureGateDecision? decision = snapshot.data;
        if (snapshot.connectionState != ConnectionState.done &&
            decision == null) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return GteRouteIntegrityScreen.blocked(
            eyebrow: 'LAUNCH CONTROL',
            title: 'Navigation unavailable',
            message: snapshot.error.toString(),
            icon: Icons.lock_clock_outlined,
          );
        }
        if (decision != null && decision.blocked) {
          return GteRouteIntegrityScreen.blocked(
            eyebrow: 'LAUNCH CONTROL',
            title: '${decision.title} unavailable',
            message:
                decision.message ??
                'This route is controlled by Launch Control and is not available right now.',
            icon: Icons.lock_clock_outlined,
          );
        }
        final GteNavigationDependencies dependencies = widget
            .dependenciesBuilder(context);
        return GteExchangeShellScreen.fromPath(
          controller: widget.controller,
          apiBaseUrl: widget.config.apiBaseUrl,
          backendMode: widget.config.activeShellBackendMode,
          ambientAudioController: widget.ambientAudioController,
          initialPath: widget.initialPath,
          navigationDependencies: dependencies,
        );
      },
    );
  }
}

List<RouteBase> _buildLegacyAliasRoutes({
  required GteExchangeController controller,
  required GteAppConfig config,
  required GteNavigationDependencies Function(BuildContext context)
  dependenciesBuilder,
}) {
  return <RouteBase>[
    GoRoute(
      path: '/home',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const GteNavigationRoute.home().path,
    ),
    GoRoute(
      path: '/world/federations',
      pageBuilder: (BuildContext context, GoRouterState state) {
        final GteNavigationDependencies dependencies = dependenciesBuilder(
          context,
        );
        return NoTransitionPage<void>(
          key: state.pageKey,
          child: GteAppRouteRegistry(
            dependencies: dependencies,
          ).buildScreen(context, const WorldFederationsRouteData()),
        );
      },
    ),
    GoRoute(
      path: '/world/awards',
      pageBuilder: (BuildContext context, GoRouterState state) {
        final GteNavigationDependencies dependencies = dependenciesBuilder(
          context,
        );
        return NoTransitionPage<void>(
          key: state.pageKey,
          child: GteAppRouteRegistry(
            dependencies: dependencies,
          ).buildScreen(context, const WorldAwardsRouteData()),
        );
      },
    ),
    GoRoute(
      path: '/world',
      pageBuilder: (BuildContext context, GoRouterState state) {
        final GteNavigationDependencies dependencies = dependenciesBuilder(
          context,
        );
        return NoTransitionPage<void>(
          key: state.pageKey,
          child: GteAppRouteRegistry(
            dependencies: dependencies,
          ).guardedScreenFor(const WorldOverviewRouteData()),
        );
      },
    ),
    GoRoute(
      path: '/market',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const GteNavigationRoute.market().path,
    ),
    GoRoute(
      path: '/player-market',
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
    // Published as "Legacy streamer-engine route redirects to the live
    // Competition OS hub", but never registered, so it reached the router's
    // error page instead. Sent where its own summary says, alongside the two
    // competition aliases above.
    // `FederationDetailRouteScreen` was written for exactly this route -
    // federation id in, detail screen out - and was referenced by nothing, so
    // the published deep route reached the error page instead of the screen
    // built for it. A blank id falls back to the federations list.
    GoRoute(
      path: AppRoutes.federationDetail,
      redirect: (BuildContext context, GoRouterState state) {
        final String federationId =
            state.pathParameters['federationId']?.trim() ?? '';
        return federationId.isEmpty ? AppRoutes.federations : null;
      },
      pageBuilder: (BuildContext context, GoRouterState state) {
        final String federationId =
            state.pathParameters['federationId']?.trim() ?? '';
        return NoTransitionPage<void>(
          key: state.pageKey,
          child: FederationDetailRouteScreen(
            client: dependenciesBuilder(context).createAuthedApi(),
            federationId: federationId,
          ),
        );
      },
    ),
    // The national-team surface is live at `/national-team`. The inventory
    // publishes the plural, which is the wrong spelling of it rather than a
    // feature that was never built, so both plural forms hand off to the
    // singular. There is no per-competition national-team screen - the
    // registry has entries and history - so the deep form lands on the
    // competitions list rather than on nothing.
    GoRoute(
      path: AppRoutes.nationalTeams,
      redirect: (BuildContext context, GoRouterState state) => '/national-team',
    ),
    GoRoute(
      path: AppRoutes.nationalTeamDetail,
      redirect: (BuildContext context, GoRouterState state) => '/national-team',
    ),
    // No screen anywhere renders a single transfer listing, but the deep link
    // is published all the same, so a shared one reached the error page. It
    // degrades to the transfer hub that does exist rather than 404ing.
    GoRoute(
      path: AppRoutes.transferCenterDetail,
      redirect:
          (BuildContext context, GoRouterState state) =>
              AppRoutes.transferCenter,
    ),
    GoRoute(
      path: AppRoutes.streamerEngine,
      redirect:
          (BuildContext context, GoRouterState state) =>
              const GteNavigationRoute.competitions().path,
    ),
    // Regen World is a shell lane now. /world/regens stays the public URL
    // and hands off to the shell lane route, so the screen inherits the
    // GTEX dark canvas, the navigation rail and back behaviour instead of
    // rendering as a bare top-level page on a white background.
    GoRoute(
      path: '/world/regens',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const GteNavigationRoute.regens().path,
    ),
    GoRoute(
      path: '/regens',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const RegenUniverseRouteData().toUri().toString(),
    ),
    GoRoute(
      path: '/federations',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const WorldFederationsRouteData().toUri().toString(),
    ),
    GoRoute(
      path: '/regen-world',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const RegenUniverseRouteData().toUri().toString(),
    ),
    GoRoute(
      path: '/awards',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const WorldAwardsRouteData().toUri().toString(),
    ),
    GoRoute(
      path: '/profile/login',
      redirect:
          (BuildContext context, GoRouterState state) => gtexAccountSelectRoute,
    ),
    GoRoute(
      path: '/profile/signup',
      redirect:
          (BuildContext context, GoRouterState state) => gtexUserSignupRoute,
    ),
    GoRoute(
      path: '/national-team',
      pageBuilder:
          (BuildContext context, GoRouterState state) => NoTransitionPage<void>(
            key: state.pageKey,
            child: GtexNationalTeamRentalScreenV2(
              controller: controller,
              apiBaseUrl: config.apiBaseUrl,
              backendMode: config.activeShellBackendMode,
              nationalTeamApi:
                  ProviderScope.containerOf(
                    context,
                    listen: false,
                  ).read(gtexRuntimeProvider).repositories.nationalTeams,
              isAuthenticated: controller.isAuthenticated,
              onOpenLogin: () => GoRouter.of(context).push(gtexLoginRoute),
            ),
          ),
    ),
    GoRoute(
      path: '/rentals',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const NationalTeamCompetitionsRouteData().toUri().toString(),
    ),
    GoRoute(
      path: '/national-rentals',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const NationalTeamCompetitionsRouteData().toUri().toString(),
    ),
    GoRoute(
      path: '/players/:playerId/profile',
      pageBuilder:
          (BuildContext context, GoRouterState state) => NoTransitionPage<void>(
            key: state.pageKey,
            child: GtexFmPlayerProfileScreen(
              playerId: state.pathParameters['playerId']?.trim() ?? '',
              baseUrl: config.apiBaseUrl,
              backendMode: config.activeShellBackendMode,
              controller: controller,
            ),
          ),
    ),
    GoRoute(
      path: '/lineup',
      pageBuilder: (BuildContext context, GoRouterState state) {
        final GteNavigationDependencies dependencies = dependenciesBuilder(
          context,
        );
        final String clubId = dependencies.currentClubId ?? '';
        return NoTransitionPage<void>(
          key: state.pageKey,
          child:
              clubId.isEmpty
                  ? GteRouteIntegrityScreen.blocked(
                    title: 'No club yet',
                    message:
                        'Open a club to set your formation and starting lineup.',
                    icon: Icons.groups_outlined,
                    actionLabel: 'Back to GTEX',
                    onAction:
                        () => context.go(const GteNavigationRoute.home().path),
                  )
                  : GtexLineupEditorScreen(
                    clubId: clubId,
                    baseUrl: config.apiBaseUrl,
                    accessToken: controller.accessToken ?? '',
                    backendMode: config.activeShellBackendMode,
                  ),
        );
      },
    ),
    GoRoute(
      path: '/managers',
      redirect: (BuildContext context, GoRouterState state) => '/coaches',
    ),
    GoRoute(
      path: '/coaches',
      pageBuilder:
          (BuildContext context, GoRouterState state) => NoTransitionPage<void>(
            key: state.pageKey,
            child: ManagerMarketScreen(
              baseUrl: config.apiBaseUrl,
              accessToken: controller.accessToken ?? '',
              isAdmin: controller.isAdmin,
              onOpenAdmin: () => context.go('/admin'),
            ),
          ),
    ),
    GoRoute(
      path: '/streamer-tournaments',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const GteNavigationRoute.competitions().path,
    ),
    GoRoute(
      path: '/clips',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const NewsDeskRouteData().toUri().toString(),
    ),
    GoRoute(
      path: '/viral',
      pageBuilder: (BuildContext context, GoRouterState state) {
        final GteNavigationDependencies dependencies = dependenciesBuilder(
          context,
        );
        return NoTransitionPage<void>(
          key: state.pageKey,
          child: GteAppRouteRegistry(
            dependencies: dependencies,
          ).buildScreen(context, const ViralFeedRouteData()),
        );
      },
    ),
    GoRoute(
      path: '/viral-feed',
      pageBuilder: (BuildContext context, GoRouterState state) {
        final GteNavigationDependencies dependencies = dependenciesBuilder(
          context,
        );
        return NoTransitionPage<void>(
          key: state.pageKey,
          child: GteAppRouteRegistry(
            dependencies: dependencies,
          ).buildScreen(context, const ViralFeedRouteData()),
        );
      },
    ),
    GoRoute(
      path: '/club',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const GteNavigationRoute.club().path,
    ),
    GoRoute(
      path: '/wallet',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const GteNavigationRoute.wallet().path,
    ),
    GoRoute(
      path: '/capital',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const GteNavigationRoute.wallet().path,
    ),
    GoRoute(
      path: '/coin-traders',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const GteNavigationRoute.wallet(
                capitalDestination: GteCapitalDestination.coinTraders,
              ).path,
    ),
    GoRoute(
      path: '/trader-dashboard',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const GteNavigationRoute.wallet(
                capitalDestination: GteCapitalDestination.traderDashboard,
              ).path,
    ),
    GoRoute(
      path: '/orders',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const GteNavigationRoute.wallet(
                capitalDestination: GteCapitalDestination.orders,
              ).path,
    ),
    GoRoute(
      path: '/payments',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const GteNavigationRoute.wallet().path,
    ),
    GoRoute(
      path: '/profile',
      pageBuilder:
          (BuildContext context, GoRouterState state) => NoTransitionPage<void>(
            key: state.pageKey,
            child: GtexLiveProfileScreen(controller: controller),
          ),
    ),
    GoRoute(
      path: '/settings',
      pageBuilder:
          (BuildContext context, GoRouterState state) => NoTransitionPage<void>(
            key: state.pageKey,
            child: GtexLiveProfileScreen(controller: controller),
          ),
    ),
    GoRoute(
      path: '/account',
      pageBuilder:
          (BuildContext context, GoRouterState state) => NoTransitionPage<void>(
            key: state.pageKey,
            child: GtexLiveProfileScreen(controller: controller),
          ),
    ),
    GoRoute(
      path: '/notifications',
      pageBuilder:
          (BuildContext context, GoRouterState state) => NoTransitionPage<void>(
            key: state.pageKey,
            child: GteNotificationsScreenV2(exchangeController: controller),
          ),
    ),
    GoRoute(
      path: '/kyc',
      pageBuilder:
          (BuildContext context, GoRouterState state) => NoTransitionPage<void>(
            key: state.pageKey,
            child: GteKycScreen(controller: controller),
          ),
    ),
    GoRoute(
      path: '/compliance',
      pageBuilder:
          (BuildContext context, GoRouterState state) => NoTransitionPage<void>(
            key: state.pageKey,
            child: GteKycScreen(controller: controller),
          ),
    ),
    GoRoute(
      path: '/disputes',
      pageBuilder:
          (BuildContext context, GoRouterState state) => NoTransitionPage<void>(
            key: state.pageKey,
            child: GteDisputeHubScreen(controller: controller),
          ),
    ),
    GoRoute(
      path: '/support',
      pageBuilder:
          (BuildContext context, GoRouterState state) => NoTransitionPage<void>(
            key: state.pageKey,
            child: GteDisputeHubScreen(controller: controller),
          ),
    ),
    GoRoute(
      path: '/community',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const GteNavigationRoute.community().path,
    ),
    GoRoute(
      path: '/social',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const GteNavigationRoute.community().path,
    ),
    GoRoute(
      path: '/chat',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const GteNavigationRoute.community().path,
    ),
    GoRoute(
      path: '/inbox',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const GteNavigationRoute.community().path,
    ),
    GoRoute(
      path: '/matches',
      pageBuilder: (BuildContext context, GoRouterState state) {
        final GteNavigationDependencies dependencies = dependenciesBuilder(
          context,
        );
        return NoTransitionPage<void>(
          key: state.pageKey,
          child: GteLiveMatchHubRouteScreen(
            dependencies: dependencies,
            clubId: dependencies.currentClubId,
            clubName: dependencies.currentClubName,
          ),
        );
      },
    ),
    GoRoute(
      path: '/matches/viewer/:matchKey',
      pageBuilder: (BuildContext context, GoRouterState state) {
        final String matchKey = state.pathParameters['matchKey']?.trim() ?? '';
        return NoTransitionPage<void>(
          key: state.pageKey,
          child: MatchViewerRouteScreen(matchKey: matchKey),
        );
      },
    ),
    // The five routes below were published in `appRouteInventory`, each with a
    // summary naming exactly where it was supposed to go, and none of them was
    // ever registered - so every one landed on the router's "Route
    // unavailable" page instead of redirecting. They are registered here to
    // the destinations their own summaries name; nothing new is decided.
    //
    // Matchday is `/matches`, the live match hub the inventory publishes under
    // that label, and the canonical viewer is `/matches/viewer/:matchKey`.
    GoRoute(
      path: AppRoutes.matchesBroadcast,
      redirect: (BuildContext context, GoRouterState state) {
        final String matchKey = state.pathParameters['matchKey']?.trim() ?? '';
        return matchKey.isEmpty
            ? AppRoutes.matches
            : AppRoutes.matchesViewerLocation(matchKey);
      },
    ),
    GoRoute(
      // Hidden while Unity is blocked: the 3D surface has no runtime, so the
      // route hands the match to the 2D viewer rather than to a dead end.
      path: AppRoutes.matchesThreeD,
      redirect: (BuildContext context, GoRouterState state) {
        final String matchKey = state.pathParameters['matchKey']?.trim() ?? '';
        return matchKey.isEmpty
            ? AppRoutes.matches
            : AppRoutes.matchesViewerLocation(matchKey);
      },
    ),
    GoRoute(
      path: AppRoutes.matchesNativeThreeD,
      redirect: (BuildContext context, GoRouterState state) => AppRoutes.matches,
    ),
    GoRoute(
      path: AppRoutes.matchesSpectate,
      redirect: (BuildContext context, GoRouterState state) => AppRoutes.matches,
    ),
    GoRoute(
      path: AppRoutes.matchesSimulate,
      redirect: (BuildContext context, GoRouterState state) => AppRoutes.matches,
    ),
    GoRoute(
      path: '/match-viewer/:matchKey',
      pageBuilder: (BuildContext context, GoRouterState state) {
        final String matchKey = state.pathParameters['matchKey']?.trim() ?? '';
        return NoTransitionPage<void>(
          key: state.pageKey,
          child: MatchViewerRouteScreen(matchKey: matchKey),
        );
      },
    ),
    GoRoute(
      path: '/match',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const BroadcastDeskRouteData().toUri().toString(),
    ),
    GoRoute(
      path: '/match-center',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const BroadcastDeskRouteData().toUri().toString(),
    ),
    GoRoute(
      path: '/match/live',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const BroadcastDeskRouteData().toUri().toString(),
    ),
    GoRoute(
      path: '/live-match/:matchId',
      pageBuilder: (BuildContext context, GoRouterState state) {
        final String matchId = state.pathParameters['matchId']?.trim() ?? '';
        if (matchId.isEmpty) {
          return NoTransitionPage<void>(
            key: state.pageKey,
            child: GteRouteIntegrityScreen.blocked(
              title: 'Live match unavailable',
              message:
                  'A persisted match id is required before the 2D live match surface can open.',
              icon: Icons.sports_soccer_outlined,
              actionLabel: 'Open Broadcast Desk',
              onAction:
                  () => context.go(
                    const BroadcastDeskRouteData().toUri().toString(),
                  ),
            ),
          );
        }
        final GtexRuntime runtime = ProviderScope.containerOf(
          context,
          listen: false,
        ).read(gtexRuntimeProvider);
        return NoTransitionPage<void>(
          key: state.pageKey,
          child: GtexMatchCenterScreenV2(
            matchId: matchId,
            repository: runtime.repositories.matches,
            // Full time hands off to the already-registered match viewer
            // route rather than dead-ending on the final scoreline.
            onOpenReplay: (String id) => context.go('/matches/viewer/$id'),
            onExit:
                () => context.go(
                  const BroadcastDeskRouteData().toUri().toString(),
                ),
          ),
        );
      },
    ),
    GoRoute(
      path: '/play',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const GteNavigationRoute.competitions().path,
    ),
    GoRoute(
      path: '/broadcast',
      redirect:
          (BuildContext context, GoRouterState state) =>
              const BroadcastDeskRouteData().toUri().toString(),
    ),
    GoRoute(
      path: '/admin/launch-control',
      pageBuilder:
          (BuildContext context, GoRouterState state) => NoTransitionPage<void>(
            key: state.pageKey,
            child:
                controller.isAdmin && controller.session != null
                    ? GtexFeatureFlagsLaunchControlScreenV2(
                      baseUrl: config.apiBaseUrl,
                      accessToken: controller.session!.accessToken,
                      backendMode: config.activeShellBackendMode,
                      authedApi: dependenciesBuilder(context).createAuthedApi(),
                    )
                    : GteRouteIntegrityScreen.blocked(
                      title: 'Admin access required',
                      message:
                          'Launch control changes rollout state and only opens for authenticated admin sessions.',
                      icon: Icons.tune_outlined,
                      actionLabel: 'Back to GTEX',
                      onAction:
                          () =>
                              context.go(const GteNavigationRoute.home().path),
                    ),
          ),
    ),
    GoRoute(
      path: '/admin/trust-ops',
      pageBuilder:
          (BuildContext context, GoRouterState state) => NoTransitionPage<void>(
            key: state.pageKey,
            child:
                controller.isAdmin && controller.session != null
                    ? GtexAdminTrustOpsScreenV2(
                      baseUrl: config.apiBaseUrl,
                      accessToken: controller.session!.accessToken,
                      backendMode: config.activeShellBackendMode,
                    )
                    : GteRouteIntegrityScreen.blocked(
                      title: 'Admin access required',
                      message:
                          'Trust operations combines KYC, disputes, risk, policies and readiness diagnostics for authenticated admins.',
                      icon: Icons.policy_outlined,
                      actionLabel: 'Back to GTEX',
                      onAction:
                          () =>
                              context.go(const GteNavigationRoute.home().path),
                    ),
          ),
    ),
    GoRoute(
      path: '/admin/matchday-economy',
      pageBuilder:
          (BuildContext context, GoRouterState state) => NoTransitionPage<void>(
            key: state.pageKey,
            child:
                controller.isAdmin && controller.session != null
                    ? GtexMatchdayEconomyAdminScreen(
                      baseUrl: config.apiBaseUrl,
                      accessToken: controller.session!.accessToken,
                      backendMode: config.activeShellBackendMode,
                    )
                    : GteRouteIntegrityScreen.blocked(
                      title: 'Admin access required',
                      message:
                          'Matchday economy operations combine fan rewards, federation, ticketing, broadcast and collectibles signals for authenticated admins.',
                      icon: Icons.query_stats_outlined,
                      actionLabel: 'Back to GTEX',
                      onAction:
                          () =>
                              context.go(const GteNavigationRoute.home().path),
                    ),
          ),
    ),
    GoRoute(
      path: '/admin/notifications',
      pageBuilder:
          (BuildContext context, GoRouterState state) => NoTransitionPage<void>(
            key: state.pageKey,
            child:
                controller.isAdmin && controller.session != null
                    ? GtexAdminNotificationMatrixScreen(
                      baseUrl: config.apiBaseUrl,
                      accessToken: controller.session!.accessToken,
                      backendMode: config.activeShellBackendMode,
                    )
                    : GteRouteIntegrityScreen.blocked(
                      title: 'Admin access required',
                      message:
                          'Notification matrix test events and template coverage only open for authenticated admin sessions.',
                      icon: Icons.notifications_active_outlined,
                      actionLabel: 'Back to GTEX',
                      onAction:
                          () =>
                              context.go(const GteNavigationRoute.home().path),
                    ),
          ),
    ),
    GoRoute(
      path: '/admin/coin-traders',
      pageBuilder:
          (BuildContext context, GoRouterState state) => NoTransitionPage<void>(
            key: state.pageKey,
            child:
                controller.isAdmin && controller.session != null
                    ? GtexCoinTraderAdminScreen(
                      baseUrl: config.apiBaseUrl,
                      accessToken: controller.session!.accessToken,
                      backendMode: config.activeShellBackendMode,
                      isAdmin: controller.isAdmin,
                      api: GtexCoinTraderApi(
                        client: dependenciesBuilder(context).createAuthedApi(),
                      ),
                    )
                    : GteRouteIntegrityScreen.blocked(
                      title: 'Admin access required',
                      message:
                          'Coin trader approvals and escrow dispute resolution require an authenticated admin session.',
                      icon: Icons.admin_panel_settings_outlined,
                      actionLabel: 'Back to GTEX',
                      onAction:
                          () =>
                              context.go(const GteNavigationRoute.home().path),
                    ),
          ),
    ),
    // `/profile/admin` is published in `appRouteInventory` as the
    // permission-gated admin entry and is where the personalised Home's
    // "Admin controls" action navigates, but it was never registered here, so
    // the tap fell through to the router's "Route unavailable" screen. It
    // redirects onto the canonical admin route rather than becoming a second
    // implementation of it - the same treatment every other legacy path in
    // this router gets.
    GoRoute(
      path: AppRoutes.profileAdmin,
      redirect: (BuildContext context, GoRouterState state) => '/admin',
    ),
    GoRoute(
      path: '/admin',
      pageBuilder:
          (BuildContext context, GoRouterState state) => NoTransitionPage<void>(
            key: state.pageKey,
            child:
                controller.isAdmin && controller.session != null
                    ? AdminCommandCenterScreen(
                      baseUrl: config.apiBaseUrl,
                      accessToken: controller.session!.accessToken,
                      backendMode: config.activeShellBackendMode,
                      authedApi: dependenciesBuilder(context).createAuthedApi(),
                      capabilities: GtexAdminCapabilities.fromSession(
                        controller.session,
                      ),
                    )
                    : GteRouteIntegrityScreen.blocked(
                      title: 'Admin access required',
                      message:
                          'The admin command center is a live operations surface and only opens for authenticated admin sessions.',
                      icon: Icons.admin_panel_settings_outlined,
                      actionLabel: 'Back to GTEX',
                      onAction:
                          () =>
                              context.go(const GteNavigationRoute.home().path),
                    ),
          ),
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
    '/world/awards',
    '/world/federations',
    '/world/regens',
    '/viral-feed',
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
              child: Material(
                type: MaterialType.transparency,
                child: registry.guardedScreenFor(featureRoute),
              ),
            );
          },
        );
      })
      .toList(growable: false);
}

String _normalizeInitialLocation(String location) {
  final String normalized = location.trim();
  if (normalized.isEmpty) {
    return '/';
  }
  return normalized.startsWith('/') ? normalized : '/$normalized';
}

Page<void> _landingPage({
  required BuildContext context,
  required GoRouterState state,
  required GteExchangeController controller,
}) {
  // Navigate through go_router routes (not imperative Navigator.push of legacy
  // screens, which never surfaced from the landing). Capture the stable router
  // instance so the callbacks don't depend on a possibly-rebuilt page context.
  final GoRouter router = GoRouter.of(context);
  return NoTransitionPage<void>(
    key: state.pageKey,
    child: GtexPublicLandingRouteScreenV2(
      onSignup: () => router.push(gtexUserSignupRoute),
      onLogin: () => router.push(gtexLoginRoute),
      onCreatorSignup: () => router.push(gtexCreatorSignupRoute),
      onTraderSignup: () => router.push(gtexTraderSignupRoute),
      onExploreMarket: () => router.go(const GteNavigationRoute.market().path),
    ),
  );
}
