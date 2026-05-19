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

    expect(find.text('Coin trading is a separate account lane'), findsOneWidget);
    expect(find.text('Trader command center'), findsNothing);
  });
}
