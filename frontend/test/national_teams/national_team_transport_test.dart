import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/national_team_api.dart';
import 'package:gte_frontend/features/national_teams/live_national_teams_provider.dart';
import 'package:gte_frontend/models/national_team_models.dart';
import 'package:gte_frontend/models/regen_universe_models.dart';

void main() {
  test('national team api uses canonical api routes', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(
          statusCode: 200,
          body: <Object?>[_competitionJson('comp-1')],
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            ..._entryJson('entry-1', 'comp-1'),
            'squad_members': <Object?>[_squadMemberJson('member-1', 'entry-1')],
            'manager_history': <Object?>[
              _managerHistoryJson('history-1', 'entry-1'),
            ],
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'managed_entries': <Object?>[_entryJson('entry-1', 'comp-1')],
            'squad_memberships': <Object?>[
              _squadMemberJson('member-1', 'entry-1'),
            ],
          },
        ),
      ],
    );
    final NationalTeamApi api = NationalTeamApi.standard(
      baseUrl: 'https://example.test',
      accessToken: 'token-1',
      mode: GteBackendMode.live,
      transport: transport,
    );

    await api.listCompetitions();
    await api.fetchEntryDetail('entry-1');
    await api.fetchUserHistory();

    expect(
      transport.requests.map((GteTransportRequest request) => request.uri.path),
      <String>[
        '/api/v2/national-team-engine/competitions',
        '/api/v2/national-team-engine/entries/entry-1',
        '/api/v2/national-team-engine/me/history',
      ],
    );
  });

  test('national teams live api uses canonical api routes', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(
          statusCode: 200,
          body: <Object?>[_competitionJson('comp-1')],
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <Object?>[_rankingJson('NG')],
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'items': <Object?>[_nationalRegenJson('regen-1', 'NG')],
            'total': 1,
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'items': <Object?>[_scoutingFeedJson('feed-1')],
            'total': 1,
          },
        ),
        GteTransportResponse(statusCode: 200, body: _competitionJson('comp-1')),
        const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'competition': <String, Object?>{'id': 'comp-1'},
          },
        ),
        const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'competition': <String, Object?>{'id': 'comp-1'},
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'managed_entries': <Object?>[_entryJson('entry-1', 'comp-1')],
            'squad_memberships': <Object?>[
              _squadMemberJson('member-1', 'entry-1'),
            ],
          },
        ),
        const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'entry_id': 'entry-1',
            'player_ids': <Object?>['player-1'],
            'budget_coin': 25,
          },
        ),
      ],
    );
    final NationalTeamsApi api = NationalTeamsApi(
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

    await api.listCompetitions();
    await api.listRankings(limit: 8);
    final regens = await api.listNationalRegens(limit: 6);
    final scoutingFeed = await api.listRegenScoutingFeed(limit: 5);
    await api.fetchCompetition('comp-1');
    await api.fetchLifecycle('comp-1');
    await api.fetchPresentation('comp-1');
    await api.fetchUserHistory();
    await api.buildAutoSquad(
      competitionId: 'comp-1',
      countryCode: 'NG',
      budgetCoin: 25,
      tactic: '4-3-3',
    );

    expect(
      transport.requests.map((GteTransportRequest request) => request.uri.path),
      <String>[
        '/api/v2/national-team-engine/competitions',
        '/api/v2/national-team-engine/rankings',
        '/api/v2/regen-universe/national-regens',
        '/api/v2/regen-universe/scouting-feed',
        '/api/v2/national-team-engine/competitions/comp-1',
        '/api/v2/national-team-engine/competitions/comp-1/lifecycle',
        '/api/v2/national-team-engine/competitions/comp-1/presentation',
        '/api/v2/national-team-engine/me/history',
        '/api/v2/national-team-engine/competitions/comp-1/auto-build-squad',
      ],
    );
    expect(transport.requests[1].uri.queryParameters['limit'], '8');
    expect(transport.requests[2].uri.queryParameters['limit'], '6');
    expect(transport.requests[2].uri.queryParameters['age_min'], '14');
    expect(transport.requests[2].uri.queryParameters['age_max'], '17');
    expect(
      transport.requests[2].uri.queryParameters['preseed_batch'],
      'u17_batch',
    );
    expect(transport.requests[3].uri.queryParameters['limit'], '5');
    expect(regens.single.confederationCode, 'CAF');
    expect(scoutingFeed.single.title, 'Ayo Future found');
  });

  test(
    'national teams hub derives prospects pipelines and academy signals',
    () {
      final NationalTeamsHubData data = NationalTeamsHubData(
        competitions: <NationalTeamCompetition>[],
        rankings: <NationalTeamCountryRankingRecord>[
          NationalTeamCountryRankingRecord.fromJson(_rankingJson('NG')),
        ],
        nationalRegens: <NationalRegenSeed>[
          NationalRegenSeed.fromJson(_nationalRegenJson('regen-1', 'NG')),
          NationalRegenSeed.fromJson(<String, Object?>{
            ..._nationalRegenJson('regen-2', 'NG'),
            'display_name': 'Future Captain',
            'potential_rating': 92,
            'primary_position': 'CAM',
          }),
        ],
        regenScoutingFeed: <RegenScoutingFeedItem>[
          RegenScoutingFeedItem.fromJson(_scoutingFeedJson('feed-1')),
        ],
        history: null,
      );

      expect(data.youthProspects.length, 2);
      expect(data.regenScoutingFeed.single.feedType, 'hidden_gem');
      expect(data.futureStars.first.displayName, 'Future Captain');
      expect(data.countryPipelines.single.countryCode, 'NG');
      expect(data.countryPipelines.single.eliteProspects, 2);
      expect(data.countryPipelines.single.rankingElo, 1825);
      expect(data.internationalAcademies.single.confederationCode, 'CAF');
      expect(data.internationalAcademies.single.countryCount, 1);
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

Map<String, Object?> _competitionJson(String id) => <String, Object?>{
  'id': id,
  'key': 'nations-cup',
  'title': 'Nations Cup',
  'season_label': 'Spring 2026',
  'region_type': 'global',
  'age_band': 'senior',
  'format_type': 'cup',
  'status': 'open',
  'notes': 'Regional qualifiers open now.',
  'active': true,
  'created_at': '2026-03-01T00:00:00Z',
  'updated_at': '2026-03-12T00:00:00Z',
};

Map<String, Object?> _entryJson(String id, String competitionId) =>
    <String, Object?>{
      'id': id,
      'competition_id': competitionId,
      'country_code': 'NG',
      'country_name': 'Nigeria',
      'manager_user_id': 'user-1',
      'squad_size': 5,
      'metadata_json': const <String, Object?>{'seed': 1},
      'created_at': '2026-03-05T00:00:00Z',
      'updated_at': '2026-03-12T00:00:00Z',
    };

Map<String, Object?> _squadMemberJson(String id, String entryId) =>
    <String, Object?>{
      'id': id,
      'entry_id': entryId,
      'user_id': 'user-22',
      'player_name': 'K. Midfield',
      'shirt_number': 8,
      'role_label': 'Captain',
      'status': 'selected',
      'created_at': '2026-03-05T00:00:00Z',
      'updated_at': '2026-03-12T00:00:00Z',
    };

Map<String, Object?> _managerHistoryJson(String id, String entryId) =>
    <String, Object?>{
      'id': id,
      'entry_id': entryId,
      'user_id': 'user-1',
      'action_type': 'created',
      'note': 'Entry created.',
      'created_at': '2026-03-05T00:00:00Z',
      'updated_at': '2026-03-12T00:00:00Z',
    };

Map<String, Object?> _rankingJson(String countryCode) => <String, Object?>{
  'country_code': countryCode,
  'country_name': 'Nigeria',
  'elo_rating': 1825,
  'matches_played': 24,
  'wins': 16,
  'draws': 4,
  'losses': 4,
  'titles': 2,
};

Map<String, Object?> _nationalRegenJson(String id, String countryCode) =>
    <String, Object?>{
      'id': id,
      'seed_key': 'u17_batch:$countryCode:$id',
      'display_name': 'Ayo Future',
      'age': 16,
      'age_band': 'u17',
      'country_code': countryCode,
      'country_name': 'Nigeria',
      'confederation_code': 'CAF',
      'seed_type': 'preseeded_national_pool',
      'generation_index': 1,
      'primary_position': 'ST',
      'secondary_positions': <Object?>['LW', 'RW'],
      'current_rating': 71,
      'potential_rating': 88,
      'growth_curve': 0.78,
      'rarity_tier': 'elite',
      'status': 'active',
      'preseed_batch': 'u17_batch',
      'metadata': const <String, Object?>{
        'source_generation': 'preseeded_u17_batch',
      },
      'market_eligible': false,
      'share_market_eligible': false,
      'tradable': false,
      'buyable': false,
      'transferable': false,
      'card_mint_eligible': false,
      'buy_cta_allowed': false,
      'is_preseeded_national_regen': true,
      'national_pool_only': true,
    };

Map<String, Object?> _scoutingFeedJson(String id) => <String, Object?>{
  'feed_id': id,
  'feed_type': 'hidden_gem',
  'title': 'Ayo Future found',
  'summary': 'Scouts flagged a national-pool striker with rare upside.',
  'occurred_at': '2026-05-01T00:00:00Z',
  'importance': 0.86,
  'badges': <Object?>['hidden_gem', 'national_pool'],
};
