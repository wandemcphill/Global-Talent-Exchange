import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app/gte_app_config.dart';
import 'app/gte_bootstrap_failure_app.dart';
import 'app/gte_frontend_app.dart';
import 'core/runtime/gtex_runtime_graph.dart';
import 'data/gte_exchange_api_client.dart';
import 'data/gte_models.dart';
import 'providers/gte_exchange_controller.dart';
import 'shared/auth/auth_identity_store.dart';
import 'shared/models/auth_session.dart';
import 'shared/providers/auth_provider.dart';
import 'theme/gte_theme_controller.dart';
import 'theme/gte_theme_registry.dart';

late GteAppConfig _bootstrapConfig;
late GteExchangeController _bootstrapController;

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final GteThemeController themeController = await GteThemeController.bootstrap(
    initialThemeId: GteThemeRegistry.defaultTheme.metadata.id,
  );
  try {
    final GteAppConfig appConfig = GteAppConfig.fromEnvironment();
    validateGtexStrictLiveStartup(appConfig);
    final SecureAuthSessionStore authSessionStore = SecureAuthSessionStore();
    final AuthSession? storedSession = await authSessionStore.readSession();
    // Ship the richer GTEX football shell by default on web builds.
    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.standard(
        baseUrl: appConfig.apiBaseUrl,
        mode: appConfig.activeShellBackendMode,
        authSessionStore: authSessionStore,
      ),
    );
    if (storedSession != null) {
      controller.session = GteAuthSession.fromJson(
        storedSession.rawJson.isNotEmpty
            ? storedSession.rawJson
            : storedSession.toJson(),
      );
      unawaited(controller.refreshAccount());
    }
    _bootstrapConfig = appConfig;
    _bootstrapController = controller;

    runApp(
      ProviderScope(
        overrides: [
          authSessionStoreProvider.overrideWithValue(authSessionStore),
          deviceIdentityStoreProvider.overrideWithValue(
            SecureDeviceIdentityStore(),
          ),
          initialAuthSessionProvider.overrideWithValue(storedSession),
        ],
        child: GtexApp(themeController: themeController),
      ),
    );
  } on StateError catch (error, stackTrace) {
    FlutterError.reportError(
      FlutterErrorDetails(
        exception: error,
        stack: stackTrace,
        library: 'GTEX bootstrap',
        context: ErrorDescription('while bootstrapping the app configuration'),
      ),
    );
    runApp(
      GteBootstrapFailureApp(
        themeController: themeController,
        failure: GteBootstrapFailure.fromError(error),
      ),
    );
  }
}

class GtexApp extends StatelessWidget {
  const GtexApp({
    super.key,
    this.themeController,
    this.config,
    this.controller,
  });

  final GteThemeController? themeController;
  final GteAppConfig? config;
  final GteExchangeController? controller;

  @override
  Widget build(BuildContext context) {
    return GteFrontendApp(
      config: config ?? _bootstrapConfig,
      controller: controller ?? _bootstrapController,
      themeController: themeController,
      initialPath: _resolveInitialAppPath(),
    );
  }
}

String _resolveInitialAppPath() {
  final Uri uri = Uri.base;
  final String fragment = uri.fragment.trim();
  if (fragment.startsWith('/')) {
    return _withQuery(fragment, uri.query);
  }
  final String path = uri.path.trim();
  if (path.isNotEmpty && path != '/') {
    return _withQuery(path, uri.query);
  }
  return '/';
}

String _withQuery(String path, String query) {
  if (query.trim().isEmpty || path.contains('?')) {
    return path;
  }
  return '$path?$query';
}
