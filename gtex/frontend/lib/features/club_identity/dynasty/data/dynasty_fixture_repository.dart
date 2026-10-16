import 'dart:async';

import 'dynasty_era_dto.dart';
import 'dynasty_leaderboard_entry_dto.dart';
import 'dynasty_profile_dto.dart';
import 'dynasty_repository.dart';
import 'dynasty_types.dart';

class DynastyFixtureRepository implements DynastyRepository {
  DynastyFixtureRepository({
    this.latency = const Duration(milliseconds: 220),
  });

  final Duration latency;

  @override
  Future<DynastyProfileDto> fetchDynastyProfile(String clubId) async {
    await _delay();
    return _clubFor(clubId).profile;
  }

  @override
  Future<DynastyHistoryDto> fetchDynastyHistory(String clubId) async {
    await _delay();
    return _clubFor(clubId).history;
  }

  @override
  Future<List<DynastyEraDto>> fetchEras(String clubId) async {
    await _delay();
    return List<DynastyEraDto>.of(_clubFor(clubId).history.eras);
  }

  @override
  Future<List<DynastyLeaderboardEntryDto>> fetchDynastyLeaderboard({
    int limit = 25,
  }) async {
    await _delay();
    final List<DynastyLeaderboardEntryDto> entries = _fixtureClubs
        .map((_DynastyFixtureClub club) => club.leaderboardEntry)
        .toList()
      ..sort(
          (DynastyLeaderboardEntryDto left, DynastyLeaderboardEntryDto right) {
        if (left.activeDynastyFlag != right.activeDynastyFlag) {
          return left.activeDynastyFlag ? -1 : 1;
        }
        return right.dynastyScore.compareTo(left.dynastyScore);
      });
    return entries.take(limit).toList(growable: false);
  }

  Future<void> _delay() => Future<void>.delayed(latency);

  _DynastyFixtureClub _clubFor(String clubId) {
    for (final _DynastyFixtureClub club in _fixtureClubs) {
      if (club.profile.clubId == clubId) {
        return club;
      }
    }
    return _buildRisingClub(clubId, _humanizeClubId(clubId));
  }
}

class _DynastyFixtureClub {
  const _DynastyFixtureClub({
    required this.profile,
    required this.history,
    required this.leaderboardEntry,
  });

  final DynastyProfileDto profile;
  final DynastyHistoryDto history;
  final DynastyLeaderboardEntryDto leaderboardEntry;
}

final List<_DynastyFixtureClub> _fixtureClubs = <_DynastyFixtureClub>[
  _buildAtlasRepublic(),
  _buildMeridianUnited(),
  _buildHarborCity(),
  _buildWestbridgeAthletic(),
];

_DynastyFixtureClub _buildAtlasRepublic() {
  const String clubId = 'atlas-republic';
  const String clubName = 'Atlas Republic';
  final List<DynastySeasonSummaryDto> seasons = <DynastySeasonSummaryDto>[
    _season(
      clubId: clubId,
      clubName: clubName,
      seasonId: '2029',
      seasonLabel: '2029/30',
      seasonIndex: 2029,
      leagueFinish: 1,
      leagueTitle: true,
      championsLeagueTitle: true,
      worldSuperCupQualified: true,
      trophyCount: 3,
      reputationGain: 11,
    ),
    _season(
      clubId: clubId,
      clubName: clubName,
      seasonId: '2030',
      seasonLabel: '2030/31',
      seasonIndex: 2030,
      leagueFinish: 1,
      leagueTitle: true,
      worldSuperCupQualified: true,
      trophyCount: 2,
      reputationGain: 8,
    ),
    _season(
      clubId: clubId,
      clubName: clubName,
      seasonId: '2031',
      seasonLabel: '2031/32',
      seasonIndex: 2031,
      leagueFinish: 2,
      worldSuperCupQualified: true,
      worldSuperCupWinner: true,
      trophyCount: 2,
      reputationGain: 7,
    ),
    _season(
      clubId: clubId,
      clubName: clubName,
      seasonId: '2032',
      seasonLabel: '2032/33',
      seasonIndex: 2032,
      leagueFinish: 1,
      leagueTitle: true,
      worldSuperCupQualified: true,
      trophyCount: 2,
      reputationGain: 9,
    ),
  ];

  final List<DynastySnapshotDto> timeline = <DynastySnapshotDto>[
    _snapshot(
      clubId: clubId,
      clubName: clubName,
      eraLabel: DynastyEraType.emergingPower,
      dynastyStatus: DynastyStatus.active,
      activeDynasty: true,
      dynastyScore: 56,
      reasons: const <String>[
        'Back-to-back title runs turned momentum into belief.',
        'European nights started ending in silverware.',
      ],
      seasons: seasons.sublist(0, 2),
    ),
    _snapshot(
      clubId: clubId,
      clubName: clubName,
      eraLabel: DynastyEraType.continentalDynasty,
      dynastyStatus: DynastyStatus.active,
      activeDynasty: true,
      dynastyScore: 82,
      reasons: const <String>[
        'A Champions League crown and elite finishes made the club feared across the continent.',
        'Three straight top-two league finishes sustained the standard.',
      ],
      seasons: seasons.sublist(0, 3),
    ),
    _snapshot(
      clubId: clubId,
      clubName: clubName,
      eraLabel: DynastyEraType.globalDynasty,
      dynastyStatus: DynastyStatus.active,
      activeDynasty: true,
      dynastyScore: 96,
      reasons: const <String>[
        'World Super Cup success completed the global case.',
        'Three league titles in four years made the reign undeniable.',
      ],
      seasons: seasons,
    ),
  ];

  final List<DynastyEraDto> eras = <DynastyEraDto>[
    DynastyEraDto(
      eraLabel: DynastyEraType.emergingPower,
      dynastyStatus: DynastyStatus.active,
      startSeasonId: '2029',
      startSeasonLabel: '2029/30',
      endSeasonId: '2030',
      endSeasonLabel: '2030/31',
      peakScore: 56,
      active: false,
      reasons: const <String>[
        'The climb started with consecutive league titles.',
      ],
    ),
    DynastyEraDto(
      eraLabel: DynastyEraType.continentalDynasty,
      dynastyStatus: DynastyStatus.active,
      startSeasonId: '2030',
      startSeasonLabel: '2030/31',
      endSeasonId: '2031',
      endSeasonLabel: '2031/32',
      peakScore: 82,
      active: false,
      reasons: const <String>[
        'Continental silver made the project feel permanent.',
      ],
    ),
    DynastyEraDto(
      eraLabel: DynastyEraType.globalDynasty,
      dynastyStatus: DynastyStatus.active,
      startSeasonId: '2031',
      startSeasonLabel: '2031/32',
      endSeasonId: '2032',
      endSeasonLabel: '2032/33',
      peakScore: 96,
      active: true,
      reasons: const <String>[
        'World-stage success pushed the club beyond continental dominance.',
      ],
    ),
  ];

  const List<DynastyEventDto> events = <DynastyEventDto>[
    DynastyEventDto(
      seasonId: '2029',
      seasonLabel: '2029/30',
      eventType: 'title',
      title: 'Champions of Europe',
      detail: 'The first continental title changed the club ceiling overnight.',
      scoreImpact: 18,
    ),
    DynastyEventDto(
      seasonId: '2031',
      seasonLabel: '2031/32',
      eventType: 'global_breakthrough',
      title: 'World Super Cup triumph',
      detail: 'The badge became recognizable everywhere football mattered.',
      scoreImpact: 20,
    ),
  ];

  final DynastyHistoryDto history = DynastyHistoryDto(
    clubId: clubId,
    clubName: clubName,
    dynastyTimeline: timeline,
    eras: eras,
    events: events,
  );

  final DynastyProfileDto profile = DynastyProfileDto(
    clubId: clubId,
    clubName: clubName,
    dynastyStatus: DynastyStatus.active,
    currentEraLabel: DynastyEraType.globalDynasty,
    activeDynastyFlag: true,
    dynastyScore: 96,
    activeStreaks: const DynastyStreaksDto(
      topFour: 4,
      trophySeasons: 4,
      worldSuperCupQualification: 4,
      positiveReputation: 4,
    ),
    lastFourSeasonSummary: seasons,
    reasons: const <String>[
      'Three league titles in four seasons.',
      'Champions League and World Super Cup silver in the same cycle.',
      'No drop-off in top-tier finishes during the run.',
    ],
    currentSnapshot: timeline.last,
    dynastyTimeline: timeline,
    eras: eras,
    events: events,
  );

  return _DynastyFixtureClub(
    profile: profile,
    history: history,
    leaderboardEntry: DynastyLeaderboardEntryDto(
      clubId: clubId,
      clubName: clubName,
      dynastyStatus: DynastyStatus.active,
      currentEraLabel: DynastyEraType.globalDynasty,
      activeDynastyFlag: true,
      dynastyScore: 96,
      reasons: profile.reasons,
    ),
  );
}

_DynastyFixtureClub _buildMeridianUnited() {
  const String clubId = 'meridian-united';
  const String clubName = 'Meridian United';
  final List<DynastySeasonSummaryDto> seasons = <DynastySeasonSummaryDto>[
    _season(
      clubId: clubId,
      clubName: clubName,
      seasonId: '2029',
      seasonLabel: '2029/30',
      seasonIndex: 2029,
      leagueFinish: 2,
      worldSuperCupQualified: true,
      trophyCount: 1,
      reputationGain: 5,
    ),
    _season(
      clubId: clubId,
      clubName: clubName,
      seasonId: '2030',
      seasonLabel: '2030/31',
      seasonIndex: 2030,
      leagueFinish: 1,
      leagueTitle: true,
      worldSuperCupQualified: true,
      trophyCount: 2,
      reputationGain: 7,
    ),
    _season(
      clubId: clubId,
      clubName: clubName,
      seasonId: '2031',
      seasonLabel: '2031/32',
      seasonIndex: 2031,
      leagueFinish: 3,
      championsLeagueTitle: true,
      worldSuperCupQualified: true,
      trophyCount: 2,
      reputationGain: 9,
    ),
    _season(
      clubId: clubId,
      clubName: clubName,
      seasonId: '2032',
      seasonLabel: '2032/33',
      seasonIndex: 2032,
      leagueFinish: 2,
      worldSuperCupQualified: true,
      trophyCount: 1,
      reputationGain: 6,
    ),
  ];

  final List<DynastySnapshotDto> timeline = <DynastySnapshotDto>[
    _snapshot(
      clubId: clubId,
      clubName: clubName,
      eraLabel: DynastyEraType.dominantEra,
      dynastyStatus: DynastyStatus.active,
      activeDynasty: true,
      dynastyScore: 61,
      reasons: const <String>[
        'A title run and relentless top-four finishes made the rise repeatable.',
      ],
      seasons: seasons.sublist(0, 3),
    ),
    _snapshot(
      clubId: clubId,
      clubName: clubName,
      eraLabel: DynastyEraType.continentalDynasty,
      dynastyStatus: DynastyStatus.active,
      activeDynasty: true,
      dynastyScore: 84,
      reasons: const <String>[
        'Continental silver and four straight elite finishes gave the club staying power.',
      ],
      seasons: seasons,
    ),
  ];

  final List<DynastyEraDto> eras = <DynastyEraDto>[
    DynastyEraDto(
      eraLabel: DynastyEraType.dominantEra,
      dynastyStatus: DynastyStatus.active,
      startSeasonId: '2029',
      startSeasonLabel: '2029/30',
      endSeasonId: '2030',
      endSeasonLabel: '2030/31',
      peakScore: 61,
      active: false,
      reasons: const <String>[
        'Domestic control arrived before the continental breakthrough.',
      ],
    ),
    DynastyEraDto(
      eraLabel: DynastyEraType.continentalDynasty,
      dynastyStatus: DynastyStatus.active,
      startSeasonId: '2031',
      startSeasonLabel: '2031/32',
      endSeasonId: '2032',
      endSeasonLabel: '2032/33',
      peakScore: 84,
      active: true,
      reasons: const <String>[
        'The Champions League title confirmed that the club traveled well.',
      ],
    ),
  ];

  const List<DynastyEventDto> events = <DynastyEventDto>[
    DynastyEventDto(
      seasonId: '2031',
      seasonLabel: '2031/32',
      eventType: 'continental_title',
      title: 'European breakthrough',
      detail: 'Meridian finally turned domestic form into continental silver.',
      scoreImpact: 16,
    ),
  ];

  final DynastyHistoryDto history = DynastyHistoryDto(
    clubId: clubId,
    clubName: clubName,
    dynastyTimeline: timeline,
    eras: eras,
    events: events,
  );

  final DynastyProfileDto profile = DynastyProfileDto(
    clubId: clubId,
    clubName: clubName,
    dynastyStatus: DynastyStatus.active,
    currentEraLabel: DynastyEraType.continentalDynasty,
    activeDynastyFlag: true,
    dynastyScore: 84,
    activeStreaks: const DynastyStreaksDto(
      topFour: 4,
      trophySeasons: 4,
      worldSuperCupQualification: 4,
      positiveReputation: 4,
    ),
    lastFourSeasonSummary: seasons,
    reasons: const <String>[
      'A continental title arrived without any domestic collapse around it.',
      'Four straight top-four finishes kept the floor elite.',
    ],
    currentSnapshot: timeline.last,
    dynastyTimeline: timeline,
    eras: eras,
    events: events,
  );

  return _DynastyFixtureClub(
    profile: profile,
    history: history,
    leaderboardEntry: DynastyLeaderboardEntryDto(
      clubId: clubId,
      clubName: clubName,
      dynastyStatus: DynastyStatus.active,
      currentEraLabel: DynastyEraType.continentalDynasty,
      activeDynastyFlag: true,
      dynastyScore: 84,
      reasons: profile.reasons,
    ),
  );
}

_DynastyFixtureClub _buildHarborCity() {
  const String clubId = 'harbor-city';
  const String clubName = 'Harbor City';
  final List<DynastySeasonSummaryDto> seasons = <DynastySeasonSummaryDto>[
    _season(
      clubId: clubId,
      clubName: clubName,
      seasonId: '2029',
      seasonLabel: '2029/30',
      seasonIndex: 2029,
      leagueFinish: 6,
      trophyCount: 0,
      reputationGain: -1,
    ),
    _season(
      clubId: clubId,
      clubName: clubName,
      seasonId: '2030',
      seasonLabel: '2030/31',
      seasonIndex: 2030,
      leagueFinish: 8,
      trophyCount: 0,
      reputationGain: -2,
    ),
    _season(
      clubId: clubId,
      clubName: clubName,
      seasonId: '2031',
      seasonLabel: '2031/32',
      seasonIndex: 2031,
      leagueFinish: 7,
      trophyCount: 0,
      reputationGain: 0,
    ),
    _season(
      clubId: clubId,
      clubName: clubName,
      seasonId: '2032',
      seasonLabel: '2032/33',
      seasonIndex: 2032,
      leagueFinish: 9,
      trophyCount: 0,
      reputationGain: -1,
    ),
  ];

  final List<DynastySnapshotDto> timeline = <DynastySnapshotDto>[
    _snapshot(
      clubId: clubId,
      clubName: clubName,
      eraLabel: DynastyEraType.continentalDynasty,
      dynastyStatus: DynastyStatus.active,
      activeDynasty: true,
      dynastyScore: 88,
      reasons: const <String>[
        'Harbor City once ruled elite nights at home and abroad.',
      ],
      seasons: <DynastySeasonSummaryDto>[
        _season(
          clubId: clubId,
          clubName: clubName,
          seasonId: '2025',
          seasonLabel: '2025/26',
          seasonIndex: 2025,
          leagueFinish: 1,
          leagueTitle: true,
          championsLeagueTitle: true,
          worldSuperCupQualified: true,
          trophyCount: 3,
          reputationGain: 10,
        ),
        _season(
          clubId: clubId,
          clubName: clubName,
          seasonId: '2026',
          seasonLabel: '2026/27',
          seasonIndex: 2026,
          leagueFinish: 1,
          leagueTitle: true,
          worldSuperCupQualified: true,
          trophyCount: 2,
          reputationGain: 7,
        ),
        _season(
          clubId: clubId,
          clubName: clubName,
          seasonId: '2027',
          seasonLabel: '2027/28',
          seasonIndex: 2027,
          leagueFinish: 2,
          worldSuperCupQualified: true,
          trophyCount: 1,
          reputationGain: 5,
        ),
        _season(
          clubId: clubId,
          clubName: clubName,
          seasonId: '2028',
          seasonLabel: '2028/29',
          seasonIndex: 2028,
          leagueFinish: 1,
          leagueTitle: true,
          trophyCount: 1,
          reputationGain: 6,
        ),
      ],
    ),
    _snapshot(
      clubId: clubId,
      clubName: clubName,
      eraLabel: DynastyEraType.fallenGiant,
      dynastyStatus: DynastyStatus.fallen,
      activeDynasty: false,
      dynastyScore: 58,
      reasons: const <String>[
        'The trophy room still echoes, but the recent seasons no longer support a live dynasty claim.',
        'Four straight years without a title ended the reign.',
      ],
      seasons: seasons,
    ),
  ];

  final List<DynastyEraDto> eras = <DynastyEraDto>[
    DynastyEraDto(
      eraLabel: DynastyEraType.continentalDynasty,
      dynastyStatus: DynastyStatus.active,
      startSeasonId: '2025',
      startSeasonLabel: '2025/26',
      endSeasonId: '2028',
      endSeasonLabel: '2028/29',
      peakScore: 88,
      active: false,
      reasons: const <String>[
        'This was the age of silver-heavy springs and domestic authority.',
      ],
    ),
    DynastyEraDto(
      eraLabel: DynastyEraType.fallenGiant,
      dynastyStatus: DynastyStatus.fallen,
      startSeasonId: '2029',
      startSeasonLabel: '2029/30',
      endSeasonId: '2032',
      endSeasonLabel: '2032/33',
      peakScore: 58,
      active: true,
      reasons: const <String>[
        'The club is still respected because the peak was real.',
        'Recent seasons have been too quiet to keep the dynasty alive.',
      ],
    ),
  ];

  const List<DynastyEventDto> events = <DynastyEventDto>[
    DynastyEventDto(
      seasonId: '2028',
      seasonLabel: '2028/29',
      eventType: 'legacy_peak',
      title: 'Last title of the great run',
      detail: 'The crest was still feared, but the drop followed fast.',
      scoreImpact: 12,
    ),
    DynastyEventDto(
      seasonId: '2032',
      seasonLabel: '2032/33',
      eventType: 'decline',
      title: 'Era closed',
      detail:
          'Another empty season confirmed the shift from dynasty to memory.',
      scoreImpact: -14,
    ),
  ];

  final DynastyHistoryDto history = DynastyHistoryDto(
    clubId: clubId,
    clubName: clubName,
    dynastyTimeline: timeline,
    eras: eras,
    events: events,
  );

  final DynastyProfileDto profile = DynastyProfileDto(
    clubId: clubId,
    clubName: clubName,
    dynastyStatus: DynastyStatus.fallen,
    currentEraLabel: DynastyEraType.fallenGiant,
    activeDynastyFlag: false,
    dynastyScore: 58,
    activeStreaks: const DynastyStreaksDto(
      topFour: 0,
      trophySeasons: 0,
      worldSuperCupQualification: 0,
      positiveReputation: 0,
    ),
    lastFourSeasonSummary: seasons,
    reasons: const <String>[
      'A serious peak remains on record, even if the current group no longer matches it.',
      'The club needs a fresh title cycle before the era can be reopened.',
    ],
    currentSnapshot: timeline.last,
    dynastyTimeline: timeline,
    eras: eras,
    events: events,
  );

  return _DynastyFixtureClub(
    profile: profile,
    history: history,
    leaderboardEntry: DynastyLeaderboardEntryDto(
      clubId: clubId,
      clubName: clubName,
      dynastyStatus: DynastyStatus.fallen,
      currentEraLabel: DynastyEraType.fallenGiant,
      activeDynastyFlag: false,
      dynastyScore: 58,
      reasons: profile.reasons,
    ),
  );
}

_DynastyFixtureClub _buildWestbridgeAthletic() {
  const String clubId = 'westbridge-athletic';
  const String clubName = 'Westbridge Athletic';
  final List<DynastySeasonSummaryDto> seasons = <DynastySeasonSummaryDto>[
    _season(
      clubId: clubId,
      clubName: clubName,
      seasonId: '2031',
      seasonLabel: '2031/32',
      seasonIndex: 2031,
      leagueFinish: 4,
      trophyCount: 1,
      reputationGain: 5,
    ),
    _season(
      clubId: clubId,
      clubName: clubName,
      seasonId: '2032',
      seasonLabel: '2032/33',
      seasonIndex: 2032,
      leagueFinish: 2,
      trophyCount: 1,
      worldSuperCupQualified: true,
      reputationGain: 7,
    ),
  ];

  final List<DynastySnapshotDto> timeline = <DynastySnapshotDto>[
    _snapshot(
      clubId: clubId,
      clubName: clubName,
      eraLabel: DynastyEraType.emergingPower,
      dynastyStatus: DynastyStatus.active,
      activeDynasty: true,
      dynastyScore: 49,
      reasons: const <String>[
        'The climb is credible: trophies, top-four finishes, and a sharper reputation curve.',
      ],
      seasons: seasons,
    ),
  ];

  final List<DynastyEraDto> eras = <DynastyEraDto>[
    DynastyEraDto(
      eraLabel: DynastyEraType.emergingPower,
      dynastyStatus: DynastyStatus.active,
      startSeasonId: '2031',
      startSeasonLabel: '2031/32',
      endSeasonId: '2032',
      endSeasonLabel: '2032/33',
      peakScore: 49,
      active: true,
      reasons: const <String>[
        'Two strong seasons put the club on the dynasty radar.',
      ],
    ),
  ];

  const List<DynastyEventDto> events = <DynastyEventDto>[
    DynastyEventDto(
      seasonId: '2032',
      seasonLabel: '2032/33',
      eventType: 'rise',
      title: 'Rising power alert',
      detail: 'Westbridge is no longer a pleasant story. It is now a threat.',
      scoreImpact: 10,
    ),
  ];

  final DynastyHistoryDto history = DynastyHistoryDto(
    clubId: clubId,
    clubName: clubName,
    dynastyTimeline: timeline,
    eras: eras,
    events: events,
  );

  final DynastyProfileDto profile = DynastyProfileDto(
    clubId: clubId,
    clubName: clubName,
    dynastyStatus: DynastyStatus.active,
    currentEraLabel: DynastyEraType.emergingPower,
    activeDynastyFlag: true,
    dynastyScore: 49,
    activeStreaks: const DynastyStreaksDto(
      topFour: 2,
      trophySeasons: 2,
      worldSuperCupQualification: 1,
      positiveReputation: 2,
    ),
    lastFourSeasonSummary: seasons,
    reasons: const <String>[
      'Back-to-back strong finishes have the club trending upward fast.',
    ],
    currentSnapshot: timeline.last,
    dynastyTimeline: timeline,
    eras: eras,
    events: events,
  );

  return _DynastyFixtureClub(
    profile: profile,
    history: history,
    leaderboardEntry: DynastyLeaderboardEntryDto(
      clubId: clubId,
      clubName: clubName,
      dynastyStatus: DynastyStatus.active,
      currentEraLabel: DynastyEraType.emergingPower,
      activeDynastyFlag: true,
      dynastyScore: 49,
      reasons: profile.reasons,
    ),
  );
}

_DynastyFixtureClub _buildRisingClub(String clubId, String clubName) {
  final List<DynastySeasonSummaryDto> seasons = <DynastySeasonSummaryDto>[
    _season(
      clubId: clubId,
      clubName: clubName,
      seasonId: '2032',
      seasonLabel: '2032/33',
      seasonIndex: 2032,
      leagueFinish: 5,
      trophyCount: 0,
      reputationGain: 3,
    ),
  ];

  final DynastyHistoryDto history = DynastyHistoryDto(
    clubId: clubId,
    clubName: clubName,
    dynastyTimeline: const <DynastySnapshotDto>[],
    eras: const <DynastyEraDto>[],
    events: const <DynastyEventDto>[],
  );

  final DynastyProfileDto profile = DynastyProfileDto(
    clubId: clubId,
    clubName: clubName,
    dynastyStatus: DynastyStatus.none,
    currentEraLabel: DynastyEraType.none,
    activeDynastyFlag: false,
    dynastyScore: 24,
    activeStreaks: const DynastyStreaksDto(
      topFour: 0,
      trophySeasons: 0,
      worldSuperCupQualification: 0,
      positiveReputation: 1,
    ),
    lastFourSeasonSummary: seasons,
    reasons: const <String>[
      'The profile shows early progress, but not enough repeat dominance to declare an era.',
    ],
    currentSnapshot: null,
    dynastyTimeline: const <DynastySnapshotDto>[],
    eras: const <DynastyEraDto>[],
    events: const <DynastyEventDto>[],
  );

  return _DynastyFixtureClub(
    profile: profile,
    history: history,
    leaderboardEntry: DynastyLeaderboardEntryDto(
      clubId: clubId,
      clubName: clubName,
      dynastyStatus: DynastyStatus.none,
      currentEraLabel: DynastyEraType.none,
      activeDynastyFlag: false,
      dynastyScore: 24,
      reasons: profile.reasons,
    ),
  );
}

DynastySeasonSummaryDto _season({
  required String clubId,
  required String clubName,
  required String seasonId,
  required String seasonLabel,
  required int seasonIndex,
  int? leagueFinish,
  bool leagueTitle = false,
  bool championsLeagueTitle = false,
  bool worldSuperCupQualified = false,
  bool worldSuperCupWinner = false,
  int trophyCount = 0,
  int reputationGain = 0,
}) {
  return DynastySeasonSummaryDto(
    clubId: clubId,
    clubName: clubName,
    seasonId: seasonId,
    seasonLabel: seasonLabel,
    seasonIndex: seasonIndex,
    leagueFinish: leagueFinish,
    leagueTitle: leagueTitle,
    championsLeagueTitle: championsLeagueTitle,
    worldSuperCupQualified: worldSuperCupQualified,
    worldSuperCupWinner: worldSuperCupWinner,
    trophyCount: trophyCount,
    reputationGain: reputationGain,
    topFourFinish: leagueFinish != null && leagueFinish <= 4,
    eliteFinish: leagueFinish != null && leagueFinish <= 2,
  );
}

DynastySnapshotDto _snapshot({
  required String clubId,
  required String clubName,
  required DynastyEraType eraLabel,
  required DynastyStatus dynastyStatus,
  required bool activeDynasty,
  required int dynastyScore,
  required List<String> reasons,
  required List<DynastySeasonSummaryDto> seasons,
}) {
  final List<DynastySeasonSummaryDto> ordered =
      List<DynastySeasonSummaryDto>.of(seasons)
        ..sort((DynastySeasonSummaryDto left, DynastySeasonSummaryDto right) {
          return left.seasonIndex.compareTo(right.seasonIndex);
        });
  final Iterable<DynastySeasonSummaryDto> recent =
      ordered.length <= 2 ? ordered : ordered.skip(ordered.length - 2);
  return DynastySnapshotDto(
    clubId: clubId,
    clubName: clubName,
    dynastyStatus: dynastyStatus,
    eraLabel: eraLabel,
    activeDynasty: activeDynasty,
    dynastyScore: dynastyScore,
    reasons: reasons,
    metrics: DynastyWindowMetricsDto(
      clubId: clubId,
      clubName: clubName,
      seasonCount: ordered.length,
      windowStartSeasonId: ordered.first.seasonId,
      windowStartSeasonLabel: ordered.first.seasonLabel,
      windowEndSeasonId: ordered.last.seasonId,
      windowEndSeasonLabel: ordered.last.seasonLabel,
      seasons: ordered,
      leagueTitles: ordered
          .where((DynastySeasonSummaryDto season) => season.leagueTitle)
          .length,
      championsLeagueTitles: ordered
          .where(
              (DynastySeasonSummaryDto season) => season.championsLeagueTitle)
          .length,
      worldSuperCupTitles: ordered
          .where((DynastySeasonSummaryDto season) => season.worldSuperCupWinner)
          .length,
      topFourFinishes: ordered
          .where((DynastySeasonSummaryDto season) => season.topFourFinish)
          .length,
      eliteFinishes: ordered
          .where((DynastySeasonSummaryDto season) => season.eliteFinish)
          .length,
      worldSuperCupQualifications: ordered
          .where(
              (DynastySeasonSummaryDto season) => season.worldSuperCupQualified)
          .length,
      trophyDensity: ordered.fold<int>(
        0,
        (int sum, DynastySeasonSummaryDto season) => sum + season.trophyCount,
      ),
      reputationGainTotal: ordered.fold<int>(
        0,
        (int sum, DynastySeasonSummaryDto season) =>
            sum + season.reputationGain,
      ),
      recentTwoTopFourFinishes: recent
          .where((DynastySeasonSummaryDto season) => season.topFourFinish)
          .length,
      recentTwoTrophyDensity: recent.fold<int>(
        0,
        (int sum, DynastySeasonSummaryDto season) => sum + season.trophyCount,
      ),
      recentTwoReputationGain: recent.fold<int>(
        0,
        (int sum, DynastySeasonSummaryDto season) =>
            sum + season.reputationGain,
      ),
      recentTwoLeagueTitles: recent
          .where((DynastySeasonSummaryDto season) => season.leagueTitle)
          .length,
    ),
  );
}

String _humanizeClubId(String clubId) {
  return clubId
      .split(RegExp(r'[-_]'))
      .where((String part) => part.isNotEmpty)
      .map(
        (String part) =>
            '${part[0].toUpperCase()}${part.substring(1).toLowerCase()}',
      )
      .join(' ');
}
