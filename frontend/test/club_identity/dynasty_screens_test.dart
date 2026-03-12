import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_era_dto.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_leaderboard_entry_dto.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_profile_dto.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_repository.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_types.dart';
import 'package:gte_frontend/features/club_identity/dynasty/presentation/dynasty_leaderboard_screen.dart';
import 'package:gte_frontend/features/club_identity/dynasty/presentation/dynasty_screen.dart';
import 'package:gte_frontend/features/club_identity/dynasty/presentation/era_history_screen.dart';
import 'package:gte_frontend/features/club_identity/dynasty/widgets/dynasty_loading_panel.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('dynasty screen shows loading state while repository is pending',
      (WidgetTester tester) async {
    final Completer<DynastyProfileDto> completer =
        Completer<DynastyProfileDto>();
    final _StubDynastyRepository repository = _StubDynastyRepository(
      loadProfile: (_) => completer.future,
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: DynastyScreen(
          clubId: 'atlas-fc',
          repository: repository,
        ),
      ),
    );

    expect(find.byType(DynastyLoadingPanel), findsNWidgets(3));

    completer.complete(_sampleProfile(score: 78));
    await tester.pumpAndSettle();

    expect(find.text('Atlas FC'), findsOneWidget);
  });

  testWidgets('dynasty screen renders success state from repository data',
      (WidgetTester tester) async {
    final _StubDynastyRepository repository = _StubDynastyRepository(
      loadProfile: (_) async => _sampleProfile(score: 78),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: DynastyScreen(
          clubId: 'atlas-fc',
          repository: repository,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Atlas FC'), findsOneWidget);
    expect(find.text('Dynasty score'), findsOneWidget);
    expect(find.text('Tier: Dynasty'), findsOneWidget);
    expect(find.text('Last four seasons'), findsOneWidget);
  });

  testWidgets('dynasty screen shows error state and retries',
      (WidgetTester tester) async {
    int attempts = 0;
    final _StubDynastyRepository repository = _StubDynastyRepository(
      loadProfile: (_) async {
        attempts += 1;
        if (attempts == 1) {
          throw Exception('temporary failure');
        }
        return _sampleProfile(score: 52);
      },
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: DynastyScreen(
          clubId: 'atlas-fc',
          repository: repository,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Dynasty feed unavailable'), findsOneWidget);

    await tester.tap(find.text('Retry'));
    await tester.pumpAndSettle();

    expect(find.text('Dynasty feed unavailable'), findsNothing);
    expect(find.text('Tier: Big club'), findsOneWidget);
  });

  testWidgets('era history renders derived eras in chronological order',
      (WidgetTester tester) async {
    final _StubDynastyRepository repository = _StubDynastyRepository(
      loadHistory: (_) async =>
          _sampleHistory(ordered: false, includeEras: false),
      loadEras: (_) async => throw Exception('eras endpoint unavailable'),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: EraHistoryScreen(
          clubId: 'atlas-fc',
          repository: repository,
        ),
      ),
    );
    await tester.pumpAndSettle();

    final Finder firstEra = find.text('2020/21 - 2020/21');
    final Finder secondEra = find.text('2021/22 - 2022/23');

    expect(firstEra, findsOneWidget);
    expect(secondEra, findsOneWidget);
    expect(tester.getTopLeft(firstEra).dy,
        lessThan(tester.getTopLeft(secondEra).dy));
  });

  testWidgets('leaderboard renders mapped rows correctly',
      (WidgetTester tester) async {
    final _StubDynastyRepository repository = _StubDynastyRepository(
      loadLeaderboard: ({int limit = 25}) async => <DynastyLeaderboardEntryDto>[
        const DynastyLeaderboardEntryDto(
          clubId: 'harbor-city',
          clubName: 'Harbor City',
          dynastyStatus: DynastyStatus.active,
          currentEraLabel: DynastyEraType.continentalDynasty,
          activeDynastyFlag: true,
          dynastyScore: 88,
          reasons: <String>['Continental silver keeps the run alive.'],
        ),
        const DynastyLeaderboardEntryDto(
          clubId: 'atlas-fc',
          clubName: 'Atlas FC',
          dynastyStatus: DynastyStatus.active,
          currentEraLabel: DynastyEraType.dominantEra,
          activeDynastyFlag: true,
          dynastyScore: 78,
          reasons: <String>['Two league titles completed the dominant run.'],
        ),
      ],
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: DynastyLeaderboardScreen(
          repository: repository,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Dynasty leaderboard'), findsOneWidget);
    expect(find.text('Harbor City'), findsOneWidget);
    expect(find.text('Atlas FC'), findsOneWidget);
    expect(find.text('88'), findsOneWidget);
    expect(find.text('78'), findsOneWidget);
    expect(
        find.text('Continental silver keeps the run alive.'), findsOneWidget);
  });

  testWidgets('dynasty score card respects tier thresholds',
      (WidgetTester tester) async {
    Future<void> pumpForScore(int score) async {
      final _StubDynastyRepository repository = _StubDynastyRepository(
        loadProfile: (_) async => _sampleProfile(score: score),
      );
      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: DynastyScreen(
            key: ValueKey<int>(score),
            clubId: 'atlas-fc-$score',
            repository: repository,
          ),
        ),
      );
      await tester.pumpAndSettle();
    }

    await pumpForScore(44);
    expect(find.text('Tier: Good club'), findsOneWidget);

    await pumpForScore(45);
    expect(find.text('Tier: Big club'), findsOneWidget);

    await pumpForScore(70);
    expect(find.text('Tier: Dynasty'), findsOneWidget);
  });
}

class _StubDynastyRepository implements DynastyRepository {
  _StubDynastyRepository({
    Future<DynastyProfileDto> Function(String clubId)? loadProfile,
    Future<DynastyHistoryDto> Function(String clubId)? loadHistory,
    Future<List<DynastyEraDto>> Function(String clubId)? loadEras,
    Future<List<DynastyLeaderboardEntryDto>> Function({int limit})?
        loadLeaderboard,
  })  : _loadProfile = loadProfile,
        _loadHistory = loadHistory,
        _loadEras = loadEras,
        _loadLeaderboard = loadLeaderboard;

  final Future<DynastyProfileDto> Function(String clubId)? _loadProfile;
  final Future<DynastyHistoryDto> Function(String clubId)? _loadHistory;
  final Future<List<DynastyEraDto>> Function(String clubId)? _loadEras;
  final Future<List<DynastyLeaderboardEntryDto>> Function({int limit})?
      _loadLeaderboard;

  @override
  Future<DynastyProfileDto> fetchDynastyProfile(String clubId) {
    if (_loadProfile == null) {
      return Future<DynastyProfileDto>.value(_sampleProfile(score: 78));
    }
    return _loadProfile(clubId);
  }

  @override
  Future<DynastyHistoryDto> fetchDynastyHistory(String clubId) {
    if (_loadHistory == null) {
      return Future<DynastyHistoryDto>.value(_sampleHistory());
    }
    return _loadHistory(clubId);
  }

  @override
  Future<List<DynastyEraDto>> fetchEras(String clubId) {
    if (_loadEras == null) {
      return Future<List<DynastyEraDto>>.value(_sampleHistory().eras);
    }
    return _loadEras(clubId);
  }

  @override
  Future<List<DynastyLeaderboardEntryDto>> fetchDynastyLeaderboard({
    int limit = 25,
  }) {
    if (_loadLeaderboard == null) {
      return Future<List<DynastyLeaderboardEntryDto>>.value(
        const <DynastyLeaderboardEntryDto>[],
      );
    }
    return _loadLeaderboard(limit: limit);
  }
}

DynastyProfileDto _sampleProfile({
  required int score,
}) {
  final List<DynastySeasonSummaryDto> seasons = _sampleSeasons();
  final List<DynastySnapshotDto> timeline = _sampleTimeline(score: score);
  final List<DynastyEraDto> eras = <DynastyEraDto>[
    const DynastyEraDto(
      eraLabel: DynastyEraType.emergingPower,
      dynastyStatus: DynastyStatus.active,
      startSeasonId: '2020',
      startSeasonLabel: '2020/21',
      endSeasonId: '2020',
      endSeasonLabel: '2020/21',
      peakScore: 52,
      active: false,
      reasons: <String>['The rise became sustained.'],
    ),
    DynastyEraDto(
      eraLabel: score >= 70
          ? DynastyEraType.dominantEra
          : DynastyEraType.emergingPower,
      dynastyStatus: DynastyStatus.active,
      startSeasonId: '2021',
      startSeasonLabel: '2021/22',
      endSeasonId: '2022',
      endSeasonLabel: '2022/23',
      peakScore: score,
      active: true,
      reasons: const <String>['Two league titles completed the dominant run.'],
    ),
  ];
  return DynastyProfileDto(
    clubId: 'atlas-fc',
    clubName: 'Atlas FC',
    dynastyStatus: DynastyStatus.active,
    currentEraLabel:
        score >= 70 ? DynastyEraType.dominantEra : DynastyEraType.emergingPower,
    activeDynastyFlag: true,
    dynastyScore: score,
    activeStreaks: const DynastyStreaksDto(
      topFour: 4,
      trophySeasons: 3,
      worldSuperCupQualification: 2,
      positiveReputation: 4,
    ),
    lastFourSeasonSummary: seasons,
    reasons: const <String>['Two league titles completed the dominant run.'],
    currentSnapshot: timeline.last,
    dynastyTimeline: timeline,
    eras: eras,
    events: const <DynastyEventDto>[
      DynastyEventDto(
        seasonId: '2021',
        seasonLabel: '2021/22',
        eventType: 'league_title',
        title: 'League Title',
        detail: 'Won the domestic title.',
        scoreImpact: 24,
      ),
    ],
  );
}

DynastyHistoryDto _sampleHistory({
  bool ordered = true,
  bool includeEras = true,
}) {
  final List<DynastySnapshotDto> timeline = _sampleTimeline(score: 78);
  final List<DynastySnapshotDto> snapshots = ordered
      ? timeline
      : <DynastySnapshotDto>[timeline[2], timeline[0], timeline[1]];
  return DynastyHistoryDto(
    clubId: 'atlas-fc',
    clubName: 'Atlas FC',
    dynastyTimeline: snapshots,
    eras: includeEras
        ? <DynastyEraDto>[
            const DynastyEraDto(
              eraLabel: DynastyEraType.emergingPower,
              dynastyStatus: DynastyStatus.active,
              startSeasonId: '2020',
              startSeasonLabel: '2020/21',
              endSeasonId: '2020',
              endSeasonLabel: '2020/21',
              peakScore: 52,
              active: false,
              reasons: <String>['The rise became sustained.'],
            ),
            const DynastyEraDto(
              eraLabel: DynastyEraType.dominantEra,
              dynastyStatus: DynastyStatus.active,
              startSeasonId: '2021',
              startSeasonLabel: '2021/22',
              endSeasonId: '2022',
              endSeasonLabel: '2022/23',
              peakScore: 78,
              active: true,
              reasons: <String>[
                'Two league titles completed the dominant run.'
              ],
            ),
          ]
        : const <DynastyEraDto>[],
    events: const <DynastyEventDto>[
      DynastyEventDto(
        seasonId: '2022',
        seasonLabel: '2022/23',
        eventType: 'world_super_cup_title',
        title: 'World Super Cup Winner',
        detail: 'Reached the global peak.',
        scoreImpact: 42,
      ),
      DynastyEventDto(
        seasonId: '2020',
        seasonLabel: '2020/21',
        eventType: 'era_change',
        title: 'Emerging Power',
        detail: 'Dynasty criteria crossed a new threshold.',
        scoreImpact: 52,
      ),
    ],
  );
}

List<DynastySnapshotDto> _sampleTimeline({
  required int score,
}) {
  final List<DynastySeasonSummaryDto> seasons = _sampleSeasons();
  return <DynastySnapshotDto>[
    DynastySnapshotDto(
      clubId: 'atlas-fc',
      clubName: 'Atlas FC',
      dynastyStatus: DynastyStatus.active,
      eraLabel: DynastyEraType.emergingPower,
      activeDynasty: true,
      dynastyScore: 52,
      reasons: const <String>['The rise became sustained.'],
      metrics: DynastyWindowMetricsDto(
        clubId: 'atlas-fc',
        clubName: 'Atlas FC',
        seasonCount: 2,
        windowStartSeasonId: '2019',
        windowStartSeasonLabel: '2019/20',
        windowEndSeasonId: '2020',
        windowEndSeasonLabel: '2020/21',
        seasons: seasons.take(2).toList(growable: false),
        leagueTitles: 0,
        championsLeagueTitles: 0,
        worldSuperCupTitles: 0,
        topFourFinishes: 2,
        eliteFinishes: 1,
        worldSuperCupQualifications: 0,
        trophyDensity: 1,
        reputationGainTotal: 6,
        recentTwoTopFourFinishes: 2,
        recentTwoTrophyDensity: 1,
        recentTwoReputationGain: 6,
        recentTwoLeagueTitles: 0,
      ),
    ),
    DynastySnapshotDto(
      clubId: 'atlas-fc',
      clubName: 'Atlas FC',
      dynastyStatus: DynastyStatus.active,
      eraLabel: score >= 70
          ? DynastyEraType.dominantEra
          : DynastyEraType.emergingPower,
      activeDynasty: true,
      dynastyScore: score >= 70 ? 70 : score,
      reasons: const <String>['The club stopped looking temporary.'],
      metrics: DynastyWindowMetricsDto(
        clubId: 'atlas-fc',
        clubName: 'Atlas FC',
        seasonCount: 3,
        windowStartSeasonId: '2019',
        windowStartSeasonLabel: '2019/20',
        windowEndSeasonId: '2021',
        windowEndSeasonLabel: '2021/22',
        seasons: seasons.take(3).toList(growable: false),
        leagueTitles: 1,
        championsLeagueTitles: 0,
        worldSuperCupTitles: 0,
        topFourFinishes: 3,
        eliteFinishes: 2,
        worldSuperCupQualifications: 1,
        trophyDensity: 3,
        reputationGainTotal: 12,
        recentTwoTopFourFinishes: 2,
        recentTwoTrophyDensity: 3,
        recentTwoReputationGain: 10,
        recentTwoLeagueTitles: 1,
      ),
    ),
    DynastySnapshotDto(
      clubId: 'atlas-fc',
      clubName: 'Atlas FC',
      dynastyStatus: DynastyStatus.active,
      eraLabel: score >= 70
          ? DynastyEraType.dominantEra
          : DynastyEraType.emergingPower,
      activeDynasty: true,
      dynastyScore: score,
      reasons: const <String>['Two league titles completed the dominant run.'],
      metrics: DynastyWindowMetricsDto(
        clubId: 'atlas-fc',
        clubName: 'Atlas FC',
        seasonCount: 4,
        windowStartSeasonId: '2019',
        windowStartSeasonLabel: '2019/20',
        windowEndSeasonId: '2022',
        windowEndSeasonLabel: '2022/23',
        seasons: seasons,
        leagueTitles: 2,
        championsLeagueTitles: 0,
        worldSuperCupTitles: 1,
        topFourFinishes: 4,
        eliteFinishes: 3,
        worldSuperCupQualifications: 2,
        trophyDensity: 6,
        reputationGainTotal: 20,
        recentTwoTopFourFinishes: 2,
        recentTwoTrophyDensity: 5,
        recentTwoReputationGain: 14,
        recentTwoLeagueTitles: 2,
      ),
    ),
  ];
}

List<DynastySeasonSummaryDto> _sampleSeasons() {
  return const <DynastySeasonSummaryDto>[
    DynastySeasonSummaryDto(
      clubId: 'atlas-fc',
      clubName: 'Atlas FC',
      seasonId: '2019',
      seasonLabel: '2019/20',
      seasonIndex: 2019,
      leagueFinish: 4,
      leagueTitle: false,
      championsLeagueTitle: false,
      worldSuperCupQualified: false,
      worldSuperCupWinner: false,
      trophyCount: 0,
      reputationGain: 2,
      topFourFinish: true,
      eliteFinish: false,
    ),
    DynastySeasonSummaryDto(
      clubId: 'atlas-fc',
      clubName: 'Atlas FC',
      seasonId: '2020',
      seasonLabel: '2020/21',
      seasonIndex: 2020,
      leagueFinish: 2,
      leagueTitle: false,
      championsLeagueTitle: false,
      worldSuperCupQualified: false,
      worldSuperCupWinner: false,
      trophyCount: 1,
      reputationGain: 4,
      topFourFinish: true,
      eliteFinish: true,
    ),
    DynastySeasonSummaryDto(
      clubId: 'atlas-fc',
      clubName: 'Atlas FC',
      seasonId: '2021',
      seasonLabel: '2021/22',
      seasonIndex: 2021,
      leagueFinish: 1,
      leagueTitle: true,
      championsLeagueTitle: false,
      worldSuperCupQualified: true,
      worldSuperCupWinner: false,
      trophyCount: 2,
      reputationGain: 6,
      topFourFinish: true,
      eliteFinish: true,
    ),
    DynastySeasonSummaryDto(
      clubId: 'atlas-fc',
      clubName: 'Atlas FC',
      seasonId: '2022',
      seasonLabel: '2022/23',
      seasonIndex: 2022,
      leagueFinish: 1,
      leagueTitle: true,
      championsLeagueTitle: false,
      worldSuperCupQualified: true,
      worldSuperCupWinner: true,
      trophyCount: 3,
      reputationGain: 8,
      topFourFinish: true,
      eliteFinish: true,
    ),
  ];
}
