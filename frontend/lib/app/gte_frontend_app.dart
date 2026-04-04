import 'package:flutter/material.dart';

import '../core/gte_session_identity.dart';
import '../data/gte_api_repository.dart';
import '../data/gte_exchange_api_client.dart';
import '../data/gte_models.dart';
import '../features/app_routes/gte_app_route_registry.dart';
import '../features/navigation_guards/gte_navigation_guards.dart';
import '../providers/gte_exchange_controller.dart';
import '../screens/gte_login_screen.dart';
import '../screens/gte_exchange_shell_screen.dart';
import '../services/match_3d_monetization_service.dart';
import '../services/reliability/reliable_event_queue.dart';
import '../theme/gte_theme_controller.dart';
import '../theme/gte_theme_scope.dart';
import '../widgets/gte_shell_theme.dart';
import 'gte_app_config.dart';

class GteFrontendApp extends StatefulWidget {
  const GteFrontendApp({
    super.key,
    this.controller,
    this.config,
    this.themeController,
  });

  final GteExchangeController? controller;
  final GteAppConfig? config;
  final GteThemeController? themeController;

  @override
  State<GteFrontendApp> createState() => _GteFrontendAppState();
}

class _GteFrontendAppState extends State<GteFrontendApp> {
  late final GteAppConfig _config;
  late final GteExchangeController _controller;
  late final bool _ownsController;
  late final GteThemeController _themeController;
  late final bool _ownsThemeController;

  @override
  void initState() {
    super.initState();
    _config = widget.config ?? GteAppConfig.fromEnvironment();
    final GteBackendMode activeBackendMode = _config.activeShellBackendMode;
    _ownsController = widget.controller == null;
    _ownsThemeController = widget.themeController == null;
    _controller =
        widget.controller ??
        GteExchangeController(
          api: GteExchangeApiClient.standard(
            baseUrl: _config.apiBaseUrl,
            mode: activeBackendMode,
          ),
        );
    gteReliableEventQueue.configure(
      sender: (ReliableQueuedEvent event) async {
        await _controller.api.trackAnalyticsEvent(
          event.name,
          metadata: <String, Object?>{
            'client_event_id': event.id,
            'topic': event.topic,
            'queued_at': event.createdAt.toUtc().toIso8601String(),
            if (event.feedRefreshTrigger != null)
              'feed_refresh_trigger': event.feedRefreshTrigger!.name,
            ...event.payload,
          },
        );
      },
      canSend: () => _controller.isAuthenticated,
    );
    _themeController = widget.themeController ?? GteThemeController();
  }

  @override
  void dispose() {
    if (_ownsController) {
      _controller.dispose();
    }
    if (_ownsThemeController) {
      _themeController.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final GteSessionIdentity identity =
        GteSessionIdentity.fromExchangeController(_controller);
    final GteBackendMode activeBackendMode = _config.activeShellBackendMode;
    final GteNavigationDependencies dependencies = GteNavigationDependencies(
      apiBaseUrl: _config.apiBaseUrl,
      backendMode: activeBackendMode,
      currentUserId: identity.userId,
      currentUserName: identity.userName,
      currentUserRole: _controller.session?.user.role,
      currentClubId: identity.clubId,
      currentClubName: identity.clubName,
      accessToken: _controller.accessToken,
      isAuthenticated: _controller.isAuthenticated,
      onOpenLogin: (BuildContext context) async {
        final bool? signedIn = await Navigator.of(context).push<bool>(
          MaterialPageRoute<bool>(
            builder:
                (BuildContext context) =>
                    GteLoginScreen(controller: _controller),
          ),
        );
        return signedIn == true;
      },
      currentUserIdProvider:
          () => GteSessionIdentity.fromExchangeController(_controller).userId,
      currentUserNameProvider:
          () => GteSessionIdentity.fromExchangeController(_controller).userName,
      currentUserRoleProvider: () => _controller.session?.user.role,
      currentClubIdProvider:
          () => GteSessionIdentity.fromExchangeController(_controller).clubId,
      currentClubNameProvider:
          () => GteSessionIdentity.fromExchangeController(_controller).clubName,
      accessTokenProvider: () => _controller.accessToken,
      isAuthenticatedProvider: () => _controller.isAuthenticated,
      match3dEntitlementProvider:
          () => Match3dUserEntitlement(
            isPremiumUser: _controller.isAuthenticated,
            availableCoins: _controller.walletSummary?.availableBalance ?? 0,
            premiumCameraAccess: _controller.isAuthenticated,
            fastReplayAccess: _controller.isAuthenticated,
          ),
    );
    final GteAppRouteRegistry registry = GteAppRouteRegistry(
      dependencies: dependencies,
    );

    return GteThemeControllerScope(
      controller: _themeController,
      child: AnimatedBuilder(
        animation: _themeController,
        builder: (BuildContext context, Widget? child) {
          return MaterialApp(
            debugShowCheckedModeBanner: false,
            title: 'GTEX Football Universe',
            theme: GteShellTheme.build(_themeController.activeTheme),
            home: GteExchangeShellScreen.fromPath(
              controller: _controller,
              apiBaseUrl: _config.apiBaseUrl,
              backendMode: activeBackendMode,
              initialPath: '/app/home',
            ),
            onGenerateRoute: (RouteSettings settings) {
              final String? name = settings.name;
              if (name != null && name.startsWith('/app')) {
                return MaterialPageRoute<void>(
                  settings: settings,
                  builder:
                      (BuildContext context) => GteExchangeShellScreen.fromPath(
                        controller: _controller,
                        apiBaseUrl: _config.apiBaseUrl,
                        backendMode: activeBackendMode,
                        initialPath: name,
                      ),
                );
              }
              return registry.onGenerateRoute(settings);
            },
            onUnknownRoute: registry.onUnknownRoute,
            restorationScopeId: 'gtex-app',
          );
        },
      ),
    );
  }
}
