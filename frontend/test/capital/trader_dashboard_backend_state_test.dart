import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/capital/trader/presentation/trader_dashboard_screen.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';

void main() {
  testWidgets('trader dashboard blocks backend-absent action surfaces', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1200, 1800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );
    controller.syncSession(_coinTraderSession());

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
    await tester.pump();
    await tester.pump();

    expect(find.text('Trader surfaces'), findsOneWidget);
    expect(find.text('Buy flow blocked'), findsOneWidget);
    expect(find.text('Sell flow blocked'), findsOneWidget);
    expect(find.text('Orders blocked'), findsOneWidget);
    expect(find.text('Disputes blocked'), findsWidgets);
    expect(find.text('Settlements blocked'), findsOneWidget);
    expect(find.text('Deposit blocked'), findsOneWidget);
    expect(find.text('Withdrawal blocked'), findsOneWidget);
    expect(find.text('Deposit rails ready'), findsNothing);
    expect(find.text('Orders visible'), findsNothing);
  });
}

GteAuthSession _coinTraderSession() {
  return GteAuthSession.fromJson(<String, Object?>{
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
  });
}
