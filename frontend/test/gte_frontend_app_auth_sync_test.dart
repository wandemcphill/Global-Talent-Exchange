import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/app/gte_frontend_app.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/shared/auth/auth_identity_store.dart';
import 'package:gte_frontend/shared/models/auth_session.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';

void main() {
  testWidgets('frontend app keeps controller and provider auth in sync', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1600, 2200);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final MemoryAuthSessionStore store = MemoryAuthSessionStore();
    final ProviderContainer container = ProviderContainer(
      overrides: [
        authSessionStoreProvider.overrideWithValue(store),
        deviceIdentityStoreProvider.overrideWithValue(
          MemoryDeviceIdentityStore(),
        ),
        appConfigProvider.overrideWithValue(
          const GteAppConfig(
            apiBaseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.fixture,
          ),
        ),
        initialAuthSessionProvider.overrideWithValue(null),
      ],
    );
    addTearDown(container.dispose);

    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: GteFrontendApp(
          controller: controller,
          config: const GteAppConfig(
            apiBaseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.fixture,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    controller.syncSession(
      _controllerSession(
        accessToken: 'controller-token',
        userId: 'controller-user',
        userName: 'Controller User',
      ),
    );
    await tester.pumpAndSettle();

    expect(container.read(authProvider)?.accessToken, 'controller-token');
    expect(container.read(authProvider)?.userId, 'controller-user');

    await container
        .read(appSessionControllerProvider.notifier)
        .updateSession(
          const AuthSession(
            userId: 'provider-user',
            accessToken: 'provider-token',
            refreshToken: 'provider-refresh',
            sessionId: 'provider-session',
            role: 'user',
            userName: 'provider-user',
            displayName: 'Provider User',
            rawJson: <String, Object?>{
              'user': <String, Object?>{
                'id': 'provider-user',
                'email': 'provider-user@gtex.test',
                'username': 'provider-user',
                'display_name': 'Provider User',
                'role': 'user',
              },
            },
          ),
        );
    await tester.pumpAndSettle();

    expect(controller.session?.accessToken, 'provider-token');
    expect(controller.session?.user.id, 'provider-user');
    expect(controller.session?.user.displayName, 'Provider User');
  });
}

GteAuthSession _controllerSession({
  required String accessToken,
  required String userId,
  required String userName,
}) {
  return GteAuthSession.fromJson(<String, Object?>{
    'access_token': accessToken,
    'refresh_token': 'refresh-$accessToken',
    'session_id': 'session-$userId',
    'token_type': 'bearer',
    'expires_in': 3600,
    'refresh_expires_in': 7200,
    'permissions': const <String>[],
    'user': <String, Object?>{
      'id': userId,
      'email': '$userId@gtex.test',
      'username': userId,
      'display_name': userName,
      'role': 'user',
    },
  });
}
