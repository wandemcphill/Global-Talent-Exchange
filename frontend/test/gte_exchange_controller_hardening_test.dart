import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';

void main() {
  test('bootstrap reuses the same in-flight future and stamps market sync', () async {
    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(
        latency: const Duration(milliseconds: 10),
      ),
    );

    final Future<void> first = controller.bootstrap();
    final Future<void> second = controller.bootstrap();

    expect(identical(first, second), isTrue);

    await first;

    expect(controller.players, isNotEmpty);
    expect(controller.marketSyncedAt, isNotNull);
  });

  test('account refresh stamps both portfolio and order sync times', () async {
    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );

    await controller.signIn(email: 'demo@gtex.test', password: 'password');
    await controller.refreshAccount();

    expect(controller.walletSummary, isNotNull);
    expect(controller.portfolio, isNotNull);
    expect(controller.portfolioSyncedAt, isNotNull);
    expect(controller.ordersSyncedAt, isNotNull);
  });
}
