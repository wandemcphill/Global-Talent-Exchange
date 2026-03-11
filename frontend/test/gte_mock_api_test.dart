import 'package:flutter_test/flutter_test.dart';

import '../lib/providers/gte_mock_api.dart';

void main() {
  test('mock api exposes seeded players and market pulse', () async {
    const GteMockApi api = GteMockApi(latency: Duration.zero);

    final List<PlayerSnapshot> players = await api.fetchPlayers();
    final MarketPulse pulse = await api.fetchMarketPulse();

    expect(players, hasLength(4));
    expect(players.first.name, 'Lamine Yamal');
    expect(players.last.inTransferRoom, isTrue);
    expect(pulse.transferRoom, hasLength(3));
    expect(pulse.hottestLeague, 'UEFA Club Championship');
  });

  test('mock api throws for unknown player ids', () async {
    const GteMockApi api = GteMockApi(latency: Duration.zero);

    expect(
      () => api.fetchPlayerProfile('unknown-player'),
      throwsA(isA<StateError>()),
    );
  });
}
