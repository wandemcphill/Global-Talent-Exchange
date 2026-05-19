import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/regen_universe_api.dart';

void main() {
  test('regen universe awards use the live awards endpoint', () async {
    final _PathTransport transport = _PathTransport(
      <String, GteTransportResponse>{
        '/api/v2/regen-universe/awards': const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'items': <Object?>[
              <String, Object?>{
                'award': <String, Object?>{
                  'id': 'award-1',
                  'code': 'BALLON_DOR',
                  'name': 'GTEX World Player of the Year',
                  'description': 'Best regen in the world.',
                  'category': 'season',
                },
                'season': <String, Object?>{
                  'id': 'season-1',
                  'season_number': 2031,
                  'start_date': '2031-01-01',
                  'end_date': '2031-12-31',
                },
                'winners': <Object?>[
                  <String, Object?>{
                    'id': 'winner-1',
                    'player_id': 'player-1',
                    'player_name': 'Ayo Akin',
                    'ranking_score': 97.4,
                    'rank': 1,
                    'awarded_at': '2031-12-31T00:00:00Z',
                    'metadata_json': <String, Object?>{
                      'source_type': 'generated',
                      'club_id': 'club-1',
                    },
                  },
                ],
              },
            ],
          },
        ),
      },
    );
    final RegenUniverseApi api = RegenUniverseApi.withClient(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'https://example.test',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        mode: GteBackendMode.live,
      ),
    );

    final awards = await api.listAwards(limit: 3);

    expect(transport.requests, hasLength(1));
    expect(transport.requests.single.uri.path, '/api/v2/regen-universe/awards');
    expect(transport.requests.single.uri.queryParameters['limit'], '3');
    expect(awards, hasLength(1));
    expect(awards.single.award.name, 'GTEX World Player of the Year');
    expect(awards.single.winners.single.playerName, 'Ayo Akin');
  });

  test(
    'regen universe live mode does not fall back to fixture awards',
    () async {
      final RegenUniverseApi api = RegenUniverseApi.withClient(
        client: GteAuthedApi(
          config: const GteRepositoryConfig(
            baseUrl: 'https://example.test',
            mode: GteBackendMode.live,
          ),
          transport: _PathTransport(<String, GteTransportResponse>{
            '/api/v2/regen-universe/awards': const GteTransportResponse(
              statusCode: 503,
              body: <String, Object?>{'detail': 'Backend unavailable.'},
            ),
          }),
          mode: GteBackendMode.live,
        ),
      );

      await expectLater(api.listAwards(), throwsA(isA<GteApiException>()));
    },
  );
}

class _PathTransport implements GteTransport {
  _PathTransport(this.responses);

  final Map<String, GteTransportResponse> responses;
  final List<GteTransportRequest> requests = <GteTransportRequest>[];

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    requests.add(request);
    return responses[request.uri.path] ??
        const GteTransportResponse(
          statusCode: 404,
          body: <String, Object?>{'detail': 'Not found.'},
        );
  }
}

