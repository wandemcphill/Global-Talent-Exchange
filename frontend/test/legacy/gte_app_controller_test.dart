import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_mock_api.dart';
import 'package:gte_frontend/legacy/gte_app_controller.dart';

void main() {
  test('controller bootstrap loads players and derived market counts',
      () async {
    final GteAppController controller =
        GteAppController(api: GteMockApi(latency: Duration.zero));

    await controller.bootstrap();

    expect(controller.players, hasLength(4));
    expect(controller.watchlistPlayers, hasLength(1));
    expect(controller.marketPulse?.activeWatchers, 204);
    expect(controller.marketPulse?.liveDeals, 4);
  });

  test('tracking actions update selected profile and market pulse', () async {
    final GteAppController controller =
        GteAppController(api: GteMockApi(latency: Duration.zero));

    await controller.bootstrap();
    await controller.openPlayer('jude-bellingham');
    controller.toggleWatchlist('jude-bellingham');
    controller.toggleTransferRoom('jude-bellingham');

    expect(controller.selectedProfile?.snapshot.isWatchlisted, isTrue);
    expect(controller.selectedProfile?.snapshot.inTransferRoom, isTrue);
    expect(controller.watchlistPlayers, hasLength(2));
    expect(controller.transferRoomPlayers, hasLength(2));
    expect(controller.marketPulse?.activeWatchers, 277);
    expect(controller.marketPulse?.liveDeals, 5);
  });

  test('sign in loads wallet, portfolio, and order state', () async {
    final GteAppController controller =
        GteAppController(api: GteMockApi(latency: Duration.zero));

    await controller.signIn(
      email: 'fixture.trader@gte.local',
      password: 'DemoPass123',
    );

    expect(controller.session?.user.username, 'fixture_trader');
    expect(controller.walletSummary?.availableBalance, 1200);
    expect(controller.portfolio?.holdings, isNotEmpty);
    expect(controller.portfolioSummary?.totalEquity, greaterThan(0));
    expect(controller.orders?.items, isNotEmpty);
  });
}
