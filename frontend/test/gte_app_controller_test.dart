import 'package:flutter_test/flutter_test.dart';

import '../lib/providers/gte_app_controller.dart';
import '../lib/providers/gte_mock_api.dart';

void main() {
  test('controller bootstrap loads players and derived market counts', () async {
    final GteAppController controller =
        GteAppController(api: const GteMockApi(latency: Duration.zero));

    await controller.bootstrap();

    expect(controller.players, hasLength(4));
    expect(controller.watchlistPlayers, hasLength(1));
    expect(controller.marketPulse?.activeWatchers, 204);
    expect(controller.marketPulse?.liveDeals, 4);
  });

  test('tracking actions update selected profile and market pulse', () async {
    final GteAppController controller =
        GteAppController(api: const GteMockApi(latency: Duration.zero));

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
}
