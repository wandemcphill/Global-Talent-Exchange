import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/discovery_api.dart';

void main() {
  test(
    'discovery fixture live item points at the shipped viewer route',
    () async {
      final DiscoveryApi api = DiscoveryApi.fixture();

      final home = await api.fetchHome();
      final liveItem = home.liveNowItems.single;
      final metadata = liveItem.metadata;

      expect(metadata['match_id'], 'fixture-1');
      expect(metadata['watch_route'], '/matches/viewer/fixture-1');
    },
  );
}
