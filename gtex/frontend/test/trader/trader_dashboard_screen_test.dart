import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/trader/trader_dashboard_screen.dart';

void main() {
  testWidgets('admin role cannot bypass coin trader account gate', (
    WidgetTester tester,
  ) async {
    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );
    controller.syncSession(
      GteAuthSession.fromJson(<String, Object?>{
        'access_token': 'admin-token',
        'session_id': 'session-admin',
        'token_type': 'bearer',
        'expires_in': 3600,
        'user': <String, Object?>{
          'id': 'admin-1',
          'email': 'admin@gtex.test',
          'username': 'admin',
          'role': 'admin',
          'account_type': 'user',
        },
      }),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: TraderDashboardScreen(
          controller: controller,
          config: const GteAppConfig(
            apiBaseUrl: gteFixtureApiBaseUrl,
            backendMode: GteBackendMode.fixture,
          ),
        ),
      ),
    );

    expect(
      find.text('Coin trading is a separate account lane'),
      findsOneWidget,
    );
    expect(find.text('Trader command center'), findsNothing);
  });

  testWidgets('coin trader can view security-gated dashboard state', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1280, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );
    controller.syncSession(
      GteAuthSession.fromJson(<String, Object?>{
        'access_token': 'trader-token',
        'session_id': 'session-trader',
        'token_type': 'bearer',
        'expires_in': 3600,
        'user': <String, Object?>{
          'id': 'trader-1',
          'email': 'trader@gtex.test',
          'username': 'trader',
          'role': 'user',
          'account_type': 'coin_trader',
        },
      }),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: TraderDashboardScreen(
          controller: controller,
          config: const GteAppConfig(
            apiBaseUrl: gteFixtureApiBaseUrl,
            backendMode: GteBackendMode.fixture,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // 591461ca ("UX: de-jargon residual dashboard copy") renamed this header
    // from "Trader command center" to "Your trading desk"; hold that.
    expect(find.text('Your trading desk'), findsOneWidget);
    expect(find.text('Trader command center'), findsNothing);

    await tester.tap(find.widgetWithText(FilledButton, 'Security'));
    await tester.pumpAndSettle();

    expect(find.text('Trader security'), findsOneWidget);
    expect(find.text('2FA'), findsOneWidget);
    expect(find.text('Enabled'), findsOneWidget);
    expect(find.text('Backup Codes'), findsOneWidget);
    expect(find.text('8'), findsOneWidget);
    expect(find.text('Recent security events'), findsOneWidget);
    expect(find.text('Authenticator confirmed'), findsOneWidget);
    expect(find.text('JBSWY3DPEHPK3PXP'), findsNothing);
  });
}
