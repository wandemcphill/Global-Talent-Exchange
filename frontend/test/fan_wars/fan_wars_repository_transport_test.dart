import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/fan_wars/data/fan_wars_models.dart';
import 'package:gte_frontend/features/fan_wars/data/fan_wars_repository.dart';

void main() {
  test('fan wars repository uses canonical api routes', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(
          statusCode: 200,
          body: const <String, Object?>{
            'board_type': 'global',
            'period_type': 'weekly',
            'window_start': '2026-03-10',
            'window_end': '2026-03-17',
            'entries': <Object?>[],
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: const <String, Object?>{
            'board_type': 'global',
            'period_type': 'weekly',
            'entries': <Object?>[],
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: const <String, Object?>{
            'profile': <String, Object?>{'id': 'profile-1'},
            'period_type': 'weekly',
            'window_start': '2026-03-10',
            'window_end': '2026-03-17',
            'summary': <String, Object?>{},
            'rivalry_entries': <Object?>[],
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: const <String, Object?>{
            'competition_id': 'cup-1',
            'title': 'Nations Cup',
            'status': 'open',
            'start_date': '2026-03-20',
            'groups': <Object?>[],
            'records': <Object?>[],
            'entries': <Object?>[],
          },
        ),
        GteTransportResponse(statusCode: 200, body: _fanWarProfileJson),
        GteTransportResponse(
          statusCode: 200,
          body: const <Object?>[_fanWarProfileJson],
        ),
        GteTransportResponse(
          statusCode: 200,
          body: const <Object?>[
            <String, Object?>{'id': 'points-1'},
          ],
        ),
        GteTransportResponse(
          statusCode: 200,
          body: const <String, Object?>{
            'id': 'assignment-1',
            'creator_profile_id': 'creator-1',
            'creator_user_id': 'user-1',
            'represented_country_code': 'NG',
            'represented_country_name': 'Nigeria',
            'eligible_country_codes': <Object?>['NG'],
            'assignment_rule': 'admin_approved',
            'allow_admin_override': false,
            'effective_from': '2026-03-12',
            'metadata_json': <String, Object?>{},
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: const <String, Object?>{
            'competition_id': 'cup-2',
            'title': 'Nations Cup',
            'status': 'draft',
            'start_date': '2026-03-20',
            'groups': <Object?>[],
            'records': <Object?>[],
            'entries': <Object?>[],
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: const <String, Object?>{
            'competition_id': 'cup-2',
            'title': 'Nations Cup',
            'status': 'live',
            'start_date': '2026-03-20',
            'groups': <Object?>[],
            'records': <Object?>[],
            'entries': <Object?>[],
          },
        ),
      ],
    );
    final FanWarsApiRepository repository = FanWarsApiRepository(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'https://example.test',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        accessToken: 'token-1',
        mode: GteBackendMode.live,
      ),
    );

    await repository.fetchLeaderboard(
      'global',
      const FanWarsPeriodQuery(periodType: 'weekly', limit: 10),
    );
    await repository.fetchRivalries(
      'global',
      const FanWarsPeriodQuery(periodType: 'weekly', limit: 10),
    );
    await repository.fetchDashboard(
      'profile-1',
      const FanWarsDashboardQuery(periodType: 'weekly'),
    );
    await repository.fetchNationsCup('cup-1');
    await repository.upsertProfile(
      const FanWarProfileUpsertRequest(
        profileType: 'club',
        displayName: 'Lagos United',
      ),
    );
    await repository.linkRivals('profile-1', 'profile-2');
    await repository.recordPoints(
      const FanWarPointRecordRequest(sourceType: 'gift'),
    );
    await repository.assignCreatorCountry(
      const CreatorCountryAssignmentRequest(
        creatorProfileId: 'creator-1',
        representedCountryCode: 'NG',
      ),
    );
    await repository.createNationsCup(
      NationsCupCreateRequest(startDate: DateTime.utc(2026, 3, 20)),
    );
    await repository.advanceNationsCup('cup-2', force: true);

    expect(
      transport.requests.map((GteTransportRequest request) => request.uri.path),
      <String>[
        '/api/v1/fan-wars/leaderboards/global',
        '/api/v1/fan-wars/rivalries/global',
        '/api/v1/fan-wars/profiles/profile-1/dashboard',
        '/api/v1/fan-wars/nations-cup/cup-1',
        '/api/v1/admin/fan-wars/profiles',
        '/api/v1/admin/fan-wars/profiles/profile-1/rivals/profile-2',
        '/api/v1/admin/fan-wars/points',
        '/api/v1/admin/fan-wars/creator-country-assignments',
        '/api/v1/admin/fan-wars/nations-cup',
        '/api/v1/admin/fan-wars/nations-cup/cup-2/advance',
      ],
    );
  });
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

const Map<String, Object?> _fanWarProfileJson = <String, Object?>{
  'id': 'profile-1',
  'profile_type': 'club',
  'display_name': 'Lagos United',
  'slug': 'lagos-united',
  'prestige_points': 1200,
  'rival_profile_ids': <Object?>['profile-2'],
  'scoring_config_json': <String, Object?>{},
  'metadata_json': <String, Object?>{},
};
