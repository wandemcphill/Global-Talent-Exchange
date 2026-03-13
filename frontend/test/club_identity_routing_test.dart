import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/app/gte_frontend_app.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';

void main() {
  testWidgets(
      'club hub routes to reputation, trophies, dynasty, and jerseys',
      (WidgetTester tester) async {
    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );

    await tester.pumpWidget(
      GteFrontendApp(
        controller: controller,
        config: const GteAppConfig(
          apiBaseUrl: 'http://127.0.0.1:8000',
          backendMode: GteBackendMode.fixture,
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('Club').last);
    await tester.pumpAndSettle();
    expect(find.text('Club hub'), findsOneWidget);

    await tester.ensureVisible(find.text('Reputation'));
    await tester.tap(find.text('Reputation').last);
    await tester.pumpAndSettle();
    expect(find.text('Club reputation'), findsOneWidget);

    await tester.pageBack();
    await tester.pumpAndSettle();

    await tester.tap(find.text('Trophies').last);
    await tester.pumpAndSettle();
    expect(find.text('Trophy Cabinet'), findsOneWidget);

    await tester.pageBack();
    await tester.pumpAndSettle();

    await tester.tap(find.text('Dynasty').last);
    await tester.pumpAndSettle();
    expect(find.text('Dynasty Overview'), findsOneWidget);

    await tester.pageBack();
    await tester.pumpAndSettle();

    await tester.tap(find.text('Identity').last);
    await tester.pumpAndSettle();
    expect(find.text('Club Identity'), findsOneWidget);
  });
}
