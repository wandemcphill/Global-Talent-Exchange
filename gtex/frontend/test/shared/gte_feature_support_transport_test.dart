import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/shared/data/gte_feature_support.dart';

void main() {
  test(
    'feature support fixture transport resolves canonical api broadcast and world routes',
    () async {
      final api = createFeatureApi(
        baseUrl: 'http://127.0.0.1:8000',
        mode: GteBackendMode.fixture,
        accessToken: 'fixture-token',
      );

      final Map<String, dynamic> broadcastHome = await api.getMap(
        '/api/broadcast/home',
        auth: false,
      );
      final List<dynamic> cultures = await api.getList(
        '/api/world/cultures',
        auth: false,
      );
      final Map<String, dynamic> clubContext = await api.getMap(
        '/api/world/clubs/ibadan-lions/context',
        auth: false,
      );
      final Map<String, dynamic> updatedNarrative = Map<String, dynamic>.from(
        (await api.request(
              'PUT',
              '/api/admin/world/narratives/title-race',
              body: const <String, Object?>{
                'headline': 'Title race goes global',
                'summary': 'Canonical api fixture route exercised.',
              },
            ))
            as Map,
      );

      expect(
        (broadcastHome['featured_channel']
            as Map<String, dynamic>)['channel_id'],
        'fixture-featured',
      );
      expect(cultures, isNotEmpty);
      expect(
        (cultures.first as Map<String, dynamic>)['culture_key'],
        'lagos_press',
      );
      expect(clubContext['club_id'], 'ibadan-lions');
      expect(updatedNarrative['slug'], 'title-race');
      expect(updatedNarrative['headline'], 'Title race goes global');
    },
  );
}
