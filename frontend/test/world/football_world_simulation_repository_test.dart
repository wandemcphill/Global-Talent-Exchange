import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/football_world_simulation/data/football_world_simulation_models.dart';
import 'package:gte_frontend/features/football_world_simulation/data/football_world_simulation_repository.dart';

void main() {
  test(
    'world simulation admin writes use canonical api admin routes',
    () async {
      final _RecordingTransport transport = _RecordingTransport(
        <GteTransportResponse>[
          GteTransportResponse(
            statusCode: 200,
            body: const <Object?>[
              <String, Object?>{
                'id': 'west-africa',
                'name': 'West Africa Federation',
                'ranking_score': 88,
                'reputation_score': 81,
                'members_json': <Object?>[],
                'is_public': true,
              },
            ],
          ),
          GteTransportResponse(
            statusCode: 200,
            body: const <String, Object?>{
              'id': 'culture-lagos',
              'culture_key': 'lagos',
              'display_name': 'Lagos Tempo',
              'scope_type': 'archetype',
              'active': true,
            },
          ),
          GteTransportResponse(
            statusCode: 200,
            body: const <String, Object?>{
              'club_id': 'ibadan-lions',
              'club_name': 'Ibadan Lions FC',
              'world_profile': <String, Object?>{'supporter_mood': 'electric'},
            },
          ),
          GteTransportResponse(
            statusCode: 200,
            body: const <String, Object?>{
              'id': 'membership-west-africa-ibadan-lions',
              'federation_id': 'west-africa',
              'club_id': 'ibadan-lions',
              'role': 'member_club',
              'status': 'active',
              'metadata_json': <String, Object?>{},
            },
          ),
          GteTransportResponse(
            statusCode: 200,
            body: const <String, Object?>{
              'id': 'narrative-race',
              'slug': 'title-race',
              'headline': 'Title race pressure',
              'arc_type': 'title_race',
            },
          ),
        ],
      );
      final FootballWorldSimulationApiRepository repository =
          FootballWorldSimulationApiRepository(
            client: GteAuthedApi(
              config: const GteRepositoryConfig(
                baseUrl: 'http://127.0.0.1:8000',
                mode: GteBackendMode.live,
              ),
              transport: transport,
              accessToken: 'admin-token',
              mode: GteBackendMode.live,
            ),
          );

      await repository.listFederations();
      await repository.upsertCulture(
        'lagos',
        const FootballCultureUpsertRequest(displayName: 'Lagos Tempo'),
      );
      await repository.upsertClubContext(
        'ibadan-lions',
        const ClubWorldProfileUpsertRequest(supporterMood: 'electric'),
      );
      await repository.joinFederation('west-africa', clubId: 'ibadan-lions');
      await repository.upsertNarrative(
        'title-race',
        const WorldNarrativeUpsertRequest(
          arcType: 'title_race',
          headline: 'Title race pressure',
        ),
      );

      expect(
        transport.requests.map(
          (GteTransportRequest request) => request.uri.path,
        ),
        <String>[
          '/api/v2/federations',
          '/api/v2/admin/world/cultures/lagos',
          '/api/v2/admin/world/clubs/ibadan-lions/context',
          '/api/v2/federations/west-africa/memberships',
          '/api/v2/admin/world/narratives/title-race',
        ],
      );
    },
  );
}

class _RecordingTransport implements GteTransport {
  _RecordingTransport(this._responses);

  final List<GteTransportResponse> _responses;
  final List<GteTransportRequest> requests = <GteTransportRequest>[];

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    requests.add(request);
    return _responses.removeAt(0);
  }
}

