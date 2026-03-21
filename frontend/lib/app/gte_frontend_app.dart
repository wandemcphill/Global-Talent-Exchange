import 'package:flutter/material.dart';

import '../core/gte_session_identity.dart';
import '../data/gte_exchange_api_client.dart';
import '../features/app_routes/gte_app_route_registry.dart';
import '../features/navigation/presentation/gte_navigation_shell_screen.dart';
import '../features/navigation_guards/gte_navigation_guards.dart';
import '../providers/gte_exchange_controller.dart';
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
    _ownsController = widget.controller == null;
    _ownsThemeController = widget.themeController == null;
    _controller = widget.controller ??
        GteExchangeController(
          api: GteExchangeApiClient.standard(
            baseUrl: _config.apiBaseUrl,
            mode: _config.backendMode,
          ),
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
    final GteNavigationDependencies dependencies = GteNavigationDependencies(
      apiBaseUrl: _config.apiBaseUrl,
      backendMode: _config.backendMode,
      currentUserId: identity.userId,
      currentUserName: identity.userName,
      isAuthenticated: _controller.isAuthenticated,
      onOpenLogin: null,
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
            title: 'Global Talent Exchange',
            theme: GteShellTheme.build(_themeController.activeTheme),
            home: GteNavigationShellScreen.fromPath(
              controller: _controller,
              apiBaseUrl: _config.apiBaseUrl,
              backendMode: _config.backendMode,
              initialPath: '/app/home',
            ),
            onGenerateRoute: (RouteSettings settings) {
              final String? name = settings.name;
              if (name != null && name.startsWith('/app')) {
                return MaterialPageRoute<void>(
                  settings: settings,
                  builder: (BuildContext context) =>
                      GteNavigationShellScreen.fromPath(
                    controller: _controller,
                    apiBaseUrl: _config.apiBaseUrl,
                    backendMode: _config.backendMode,
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
