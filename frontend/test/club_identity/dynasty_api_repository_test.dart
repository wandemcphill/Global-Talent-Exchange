import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_api_repository.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_era_dto.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_fixture_repository.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_profile_dto.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_response_mapper.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_types.dart';

void main() {
  test('fetchDynastyProfile enriches legacy payloads with history-backed data',
      () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(statusCode: 200, body: _legacyProfilePayload()),
        GteTransportResponse(statusCode: 200, body: _historyPayload()),
        GteTransportResponse(
          statusCode: 404,
          body: <String, Object?>{'detail': 'not found'},
        ),
      ],
    );
    final DynastyApiRepository repository = DynastyApiRepository(
      config: const GteRepositoryConfig(
        baseUrl: 'http://127.0.0.1:8000',
        mode: GteBackendMode.live,
      ),
      transport: transport,
      fixtures: DynastyFixtureRepository(),
    );

    final DynastyProfileDto profile =
        await repository.fetchDynastyProfile('atlas-fc');

    expect(
      transport.requests.map((GteTransportRequest request) => request.uri.path),
      <String>[
        '/api/clubs/atlas-fc/dynasty',
        '/api/clubs/atlas-fc/dynasty/history',
        '/api/clubs/atlas-fc/eras',
      ],
    );
    expect(profile.clubId, 'atlas-fc');
    expect(profile.clubName, 'Atlas FC');
    expect(profile.dynastyScore, 78);
    expect(profile.currentEraLabel, DynastyEraType.dominantEra);
    expect(profile.activeStreaks.topFour, 4);
    expect(profile.activeStreaks.trophySeasons, 3);
    expect(
        profile.lastFourSeasonSummary.map((season) => season.seasonId),
        <String>[
          '2019',
          '2020',
          '2021',
          '2022',
        ]);
    expect(
        profile.eras.map((DynastyEraDto era) => era.eraLabel), <DynastyEraType>[
      DynastyEraType.emergingPower,
      DynastyEraType.dominantEra,
    ]);
  });

  test('fetchDynastyHistory normalizes timeline ordering and derives eras',
      () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(statusCode: 200, body: _historyPayload()),
      ],
    );
    final DynastyApiRepository repository = DynastyApiRepository(
      config: const GteRepositoryConfig(
        baseUrl: 'http://127.0.0.1:8000',
        mode: GteBackendMode.live,
      ),
      transport: transport,
      fixtures: DynastyFixtureRepository(),
    );

    final DynastyHistoryDto history =
        await repository.fetchDynastyHistory('atlas-fc');

    expect(
      history.dynastyTimeline.map(
          (DynastySnapshotDto snapshot) => snapshot.metrics.windowEndSeasonId),
      <String>['2020', '2021', '2022'],
    );
    expect(
      history.events.map((DynastyEventDto event) => event.seasonId),
      <String>['2020', '2021', '2022'],
    );
    expect(history.eras.length, 2);
    expect(history.eras.first.startSeasonId, '2020');
    expect(history.eras.last.endSeasonId, '2022');
  });

  test('applyEraOverride prefers explicit eras over history-derived eras', () {
    final DynastyHistoryDto history =
        dynastyResponseMapper.mapHistory(_historyPayload());
    final List<DynastyEraDto> explicitEras = <DynastyEraDto>[
      const DynastyEraDto(
        eraLabel: DynastyEraType.globalDynasty,
        dynastyStatus: DynastyStatus.active,
        startSeasonId: '2021',
        startSeasonLabel: '2021/22',
        endSeasonId: '2022',
        endSeasonLabel: '2022/23',
        peakScore: 99,
        active: true,
        reasons: <String>['Explicit era override'],
      ),
    ];

    final DynastyHistoryDto resolvedHistory =
        dynastyResponseMapper.applyEraOverride(
      history,
      explicitEras: explicitEras,
    );

    expect(resolvedHistory.eras.length, 1);
    expect(resolvedHistory.eras.single.eraLabel, DynastyEraType.globalDynasty);
    expect(
      resolvedHistory.eras.single.reasons,
      <String>['Explicit era override'],
    );
  });

  test('fetchEras applies safe defaults when optional fields are missing',
      () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'eras': <Object?>[
              <String, Object?>{
                'era_label': 'Dominant Era',
                'dynasty_status': 'active',
                'start_season_id': '2021',
                'peak_score': 78,
                'active': true,
                'reasons': <Object?>['Won the league', null, '  '],
              },
            ],
          },
        ),
      ],
    );
    final DynastyApiRepository repository = DynastyApiRepository(
      config: const GteRepositoryConfig(
        baseUrl: 'http://127.0.0.1:8000',
        mode: GteBackendMode.live,
      ),
      transport: transport,
      fixtures: DynastyFixtureRepository(),
    );

    final List<DynastyEraDto> eras = await repository.fetchEras('atlas-fc');

    expect(eras.single.startSeasonLabel, '2021');
    expect(eras.single.endSeasonId, '2021');
    expect(eras.single.endSeasonLabel, '2021');
    expect(eras.single.reasons, <String>['Won the league']);
  });

  test('fetchDynastyLeaderboard maps rows without region metadata', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'entries': <Object?>[
              <String, Object?>{
                'club_id': 'harbor-city',
                'club_name': 'Harbor City',
                'dynasty_status': 'fallen',
                'current_era_label': 'Fallen Giant',
                'active_dynasty_flag': false,
                'dynasty_score': 58,
                'reasons': <String>['Historic peak remains respected.'],
              },
              <String, Object?>{
                'club_id': 'atlas-fc',
                'club_name': 'Atlas FC',
                'dynasty_status': 'active',
                'current_era_label': 'Dominant Era',
                'active_dynasty_flag': true,
                'dynasty_score': 78,
                'reasons': <String>['Three titles in four seasons.'],
              },
            ],
          },
        ),
      ],
    );
    final DynastyApiRepository repository = DynastyApiRepository(
      config: const GteRepositoryConfig(
        baseUrl: 'http://127.0.0.1:8000',
        mode: GteBackendMode.live,
      ),
      transport: transport,
      fixtures: DynastyFixtureRepository(),
    );

    final entries = await repository.fetchDynastyLeaderboard(limit: 2);

    expect(transport.requests.single.uri.queryParameters['limit'], '2');
    expect(entries.length, 2);
    expect(entries.first.clubId, 'atlas-fc');
    expect(entries.first.clubName, 'Atlas FC');
    expect(entries.first.reasons, <String>['Three titles in four seasons.']);
    expect(entries.last.clubId, 'harbor-city');
  });
}

class _RecordingTransport implements GteTransport {
  _RecordingTransport(this.responses);

  final List<GteTransportResponse> responses;
  final List<GteTransportRequest> requests = <GteTransportRequest>[];

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    requests.add(request);
    return responses.removeAt(0);
  }
}

Map<String, Object?> _legacyProfilePayload() {
  return <String, Object?>{
    'progress': <String, Object?>{
      'club_id': 'atlas-fc',
      'club_name': 'Atlas FC',
      'dynasty_score': 410,
    },
    'milestones': <Object?>[
      <String, Object?>{
        'title': 'Five-season foundation',
        'description': 'History is starting to stick.',
        'is_unlocked': true,
      },
    ],
  };
}

Map<String, Object?> _historyPayload() {
  return <String, Object?>{
    'club_id': 'atlas-fc',
    'club_name': 'Atlas FC',
    'dynasty_timeline': <Object?>[
      _snapshotPayload(
        seasonId: '2022',
        seasonLabel: '2022/23',
        eraLabel: 'Dominant Era',
        dynastyStatus: 'active',
        activeDynasty: true,
        dynastyScore: 78,
        reasons: <String>['Two league titles completed the dominant run.'],
        seasons: <Map<String, Object?>>[
          _seasonPayload(
            seasonId: '2019',
            seasonLabel: '2019/20',
            seasonIndex: 2019,
            leagueFinish: 4,
            trophyCount: 0,
            reputationGain: 2,
          ),
          _seasonPayload(
            seasonId: '2020',
            seasonLabel: '2020/21',
            seasonIndex: 2020,
            leagueFinish: 2,
            trophyCount: 1,
            reputationGain: 4,
          ),
          _seasonPayload(
            seasonId: '2021',
            seasonLabel: '2021/22',
            seasonIndex: 2021,
            leagueFinish: 1,
            leagueTitle: true,
            trophyCount: 2,
            reputationGain: 6,
            worldSuperCupQualified: true,
          ),
          _seasonPayload(
            seasonId: '2022',
            seasonLabel: '2022/23',
            seasonIndex: 2022,
            leagueFinish: 1,
            leagueTitle: true,
            trophyCount: 3,
            reputationGain: 8,
            worldSuperCupQualified: true,
            worldSuperCupWinner: true,
          ),
        ],
      ),
      _snapshotPayload(
        seasonId: '2020',
        seasonLabel: '2020/21',
        eraLabel: 'Emerging Power',
        dynastyStatus: 'active',
        activeDynasty: true,
        dynastyScore: 52,
        reasons: <String>['The rise became sustained.'],
        seasons: <Map<String, Object?>>[
          _seasonPayload(
            seasonId: '2019',
            seasonLabel: '2019/20',
            seasonIndex: 2019,
            leagueFinish: 4,
            trophyCount: 0,
            reputationGain: 2,
          ),
          _seasonPayload(
            seasonId: '2020',
            seasonLabel: '2020/21',
            seasonIndex: 2020,
            leagueFinish: 2,
            trophyCount: 1,
            reputationGain: 4,
          ),
        ],
      ),
      _snapshotPayload(
        seasonId: '2021',
        seasonLabel: '2021/22',
        eraLabel: 'Dominant Era',
        dynastyStatus: 'active',
        activeDynasty: true,
        dynastyScore: 70,
        reasons: <String>['The club stopped looking temporary.'],
        seasons: <Map<String, Object?>>[
          _seasonPayload(
            seasonId: '2019',
            seasonLabel: '2019/20',
            seasonIndex: 2019,
            leagueFinish: 4,
            trophyCount: 0,
            reputationGain: 2,
          ),
          _seasonPayload(
            seasonId: '2020',
            seasonLabel: '2020/21',
            seasonIndex: 2020,
            leagueFinish: 2,
            trophyCount: 1,
            reputationGain: 4,
          ),
          _seasonPayload(
            seasonId: '2021',
            seasonLabel: '2021/22',
            seasonIndex: 2021,
            leagueFinish: 1,
            leagueTitle: true,
            trophyCount: 2,
            reputationGain: 6,
            worldSuperCupQualified: true,
          ),
        ],
      ),
    ],
    'eras': const <Object?>[],
    'events': <Object?>[
      <String, Object?>{
        'season_id': '2022',
        'season_label': '2022/23',
        'event_type': 'world_super_cup_title',
        'title': 'World Super Cup Winner',
        'detail': 'Reached the global peak.',
        'score_impact': 42,
      },
      <String, Object?>{
        'season_id': '2020',
        'season_label': '2020/21',
        'event_type': 'era_change',
        'title': 'Emerging Power',
        'detail': 'Dynasty criteria crossed a new threshold.',
        'score_impact': 52,
      },
      <String, Object?>{
        'season_id': '2021',
        'season_label': '2021/22',
        'event_type': 'league_title',
        'title': 'League Title',
        'detail': 'Won the domestic title.',
        'score_impact': 24,
      },
    ],
  };
}

Map<String, Object?> _snapshotPayload({
  required String seasonId,
  required String seasonLabel,
  required String eraLabel,
  required String dynastyStatus,
  required bool activeDynasty,
  required int dynastyScore,
  required List<String> reasons,
  required List<Map<String, Object?>> seasons,
}) {
  return <String, Object?>{
    'club_id': 'atlas-fc',
    'club_name': 'Atlas FC',
    'dynasty_status': dynastyStatus,
    'era_label': eraLabel,
    'active_dynasty': activeDynasty,
    'dynasty_score': dynastyScore,
    'reasons': reasons,
    'metrics': <String, Object?>{
      'club_id': 'atlas-fc',
      'club_name': 'Atlas FC',
      'season_count': seasons.length,
      'window_start_season_id': seasons.first['season_id'],
      'window_start_season_label': seasons.first['season_label'],
      'window_end_season_id': seasonId,
      'window_end_season_label': seasonLabel,
      'seasons': seasons,
      'league_titles': seasons
          .where(
              (Map<String, Object?> season) => season['league_title'] == true)
          .length,
      'champions_league_titles': 0,
      'world_super_cup_titles': seasons
          .where((Map<String, Object?> season) =>
              season['world_super_cup_winner'] == true)
          .length,
      'top_four_finishes': seasons
          .where((Map<String, Object?> season) =>
              season['top_four_finish'] == true)
          .length,
      'elite_finishes': seasons
          .where(
              (Map<String, Object?> season) => season['elite_finish'] == true)
          .length,
      'world_super_cup_qualifications': seasons
          .where((Map<String, Object?> season) =>
              season['world_super_cup_qualified'] == true)
          .length,
      'trophy_density': seasons.fold<int>(
        0,
        (int sum, Map<String, Object?> season) =>
            sum + (season['trophy_count'] as int? ?? 0),
      ),
      'reputation_gain_total': seasons.fold<int>(
        0,
        (int sum, Map<String, Object?> season) =>
            sum + (season['reputation_gain'] as int? ?? 0),
      ),
      'recent_two_top_four_finishes': seasons
          .skip(seasons.length > 2 ? seasons.length - 2 : 0)
          .where((Map<String, Object?> season) =>
              season['top_four_finish'] == true)
          .length,
      'recent_two_trophy_density':
          seasons.skip(seasons.length > 2 ? seasons.length - 2 : 0).fold<int>(
                0,
                (int sum, Map<String, Object?> season) =>
                    sum + (season['trophy_count'] as int? ?? 0),
              ),
      'recent_two_reputation_gain':
          seasons.skip(seasons.length > 2 ? seasons.length - 2 : 0).fold<int>(
                0,
                (int sum, Map<String, Object?> season) =>
                    sum + (season['reputation_gain'] as int? ?? 0),
              ),
      'recent_two_league_titles': seasons
          .skip(seasons.length > 2 ? seasons.length - 2 : 0)
          .where(
              (Map<String, Object?> season) => season['league_title'] == true)
          .length,
    },
  };
}

Map<String, Object?> _seasonPayload({
  required String seasonId,
  required String seasonLabel,
  required int seasonIndex,
  required int? leagueFinish,
  required int trophyCount,
  required int reputationGain,
  bool leagueTitle = false,
  bool worldSuperCupQualified = false,
  bool worldSuperCupWinner = false,
}) {
  return <String, Object?>{
    'club_id': 'atlas-fc',
    'club_name': 'Atlas FC',
    'season_id': seasonId,
    'season_label': seasonLabel,
    'season_index': seasonIndex,
    'league_finish': leagueFinish,
    'league_title': leagueTitle,
    'champions_league_title': false,
    'world_super_cup_qualified': worldSuperCupQualified,
    'world_super_cup_winner': worldSuperCupWinner,
    'trophy_count': trophyCount,
    'reputation_gain': reputationGain,
    'top_four_finish': leagueFinish != null && leagueFinish <= 4,
    'elite_finish': leagueFinish != null && leagueFinish <= 2,
  };
}
