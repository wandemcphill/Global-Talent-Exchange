import 'dart:async';

import 'package:flutter/material.dart';

import 'app/gte_app_config.dart';
import 'app/gte_frontend_app.dart';
import 'data/gte_exchange_api_client.dart';
import 'data/gte_models.dart';
import 'providers/gte_exchange_controller.dart';
import 'shared/auth/auth_identity_store.dart';
import 'shared/models/auth_session.dart';
import 'theme/gte_theme_controller.dart';
import 'theme/gte_theme_metadata.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final GteAppConfig appConfig = GteAppConfig.fromEnvironment();
  final SecureAuthSessionStore authSessionStore = SecureAuthSessionStore();
  final AuthSession? storedSession = await authSessionStore.readSession();
  // Ship the richer GTEX football shell by default on web builds.
  final GteThemeController themeController = await GteThemeController.bootstrap(
    initialThemeId: GteThemeId.foundersBlack,
  );
  final GteExchangeController controller = GteExchangeController(
    api: GteExchangeApiClient.standard(
      baseUrl: appConfig.apiBaseUrl,
      mode: appConfig.activeShellBackendMode,
      authSessionStore: authSessionStore,
    ),
  );
  if (storedSession != null) {
    controller.session = GteAuthSession.fromJson(
      storedSession.rawJson.isNotEmpty ? storedSession.rawJson : storedSession.toJson(),
    );
    unawaited(controller.refreshAccount());
  }

  runApp(
    GteFrontendApp(
      config: appConfig,
      themeController: themeController,
      controller: controller,
    ),
  );
}
