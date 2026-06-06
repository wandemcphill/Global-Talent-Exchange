import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/features/capital/trader/presentation/trader_dashboard_screen.dart';

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

  testWidgets('trader dashboard blocks missing order-book truth', (
    WidgetTester tester,
  ) async {
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

    expect(find.text('Trader profile'), findsOneWidget);
    expect(find.text('Presence syncing'), findsOneWidget);
    expect(find.text('Rating blocked'), findsWidgets);
    expect(find.text('Dispute state blocked'), findsOneWidget);

    await tester.drag(
      find.byWidgetPredicate(
        (Widget widget) =>
            widget is ListView && widget.scrollDirection == Axis.vertical,
      ),
      const Offset(0, -900),
    );
    await tester.pump();

    expect(find.text('Order book blocked'), findsWidgets);
    expect(find.text('Awaiting auditable quote'), findsOneWidget);
    expect(find.text('ETA blocked'), findsOneWidget);
    expect(find.text('Settlement rail blocked'), findsOneWidget);
    expect(
      find.textContaining(
        'Buy '
        'wall',
      ),
      findsNothing,
    );
    expect(
      find.text(
        '1,000'
        '.00',
      ),
      findsNothing,
    );
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
