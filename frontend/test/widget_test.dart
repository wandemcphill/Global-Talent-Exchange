import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/app/gte_frontend_app.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';

void main() {
  testWidgets('app smoke test renders new GTEX shell', (WidgetTester tester) async {
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
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('Command Center'), findsOneWidget);

    await tester.tap(find.text('Market'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('Transfer Market'), findsOneWidget);
    expect(find.text('Search players, positions, countries'), findsOneWidget);
  });
}
