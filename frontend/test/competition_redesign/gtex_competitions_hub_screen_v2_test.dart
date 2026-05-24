import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/competition_redesign/data/gtex_competition_repository.dart';
import 'package:gte_frontend/features/competition_redesign/models/gtex_competition_models.dart';
import 'package:gte_frontend/features/competition_redesign/presentation/gtex_competitions_hub_screen_v2.dart';

void main() {
  testWidgets('competitions hub renders browse panel and action button', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: GtexCompetitionsHubScreenV2(allowFixtureData: true),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('GTEX Competitions'), findsWidgets);
    expect(find.text('Create competition'), findsOneWidget);
    expect(find.text('Global Talent Cup'), findsWidgets);
  });

  testWidgets('competitions hub blocks fixture repository by default', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(home: Scaffold(body: GtexCompetitionsHubScreenV2())),
    );
    await tester.pumpAndSettle();

    expect(find.text('Live competitions unavailable'), findsOneWidget);
    expect(find.text('Global Talent Cup'), findsNothing);
  });

  testWidgets('open monitor does not submit a join request', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1440, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final _FakeCompetitionRepository repository = _FakeCompetitionRepository();
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: GtexCompetitionsHubScreenV2(repository: repository),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('Open monitor'));
    await tester.pumpAndSettle();

    expect(repository.joinCalls, isZero);
    expect(find.text('Progress'), findsWidgets);
  });
}

class _FakeCompetitionRepository implements GtexCompetitionRepository {
  static const GtexCompetitionSummary _summary = GtexCompetitionSummary(
    id: 'live-cup',
    title: 'Live Cup',
    kind: GtexCompetitionKind.gtexTournament,
    status: GtexCompetitionStatus.live,
    regionLabel: 'Worldwide',
    entryFeeCredits: 500,
    prizePoolCredits: 5000,
    registeredClubs: 16,
    maxClubs: 16,
    progressPercent: .5,
    currentStage: 'Semi Final',
    startsAtLabel: 'Live now',
    description: 'A live competition that should open monitoring only.',
  );

  int joinCalls = 0;

  @override
  Future<void> createCompetition(GtexCompetitionDraft draft) async {}

  @override
  Future<GtexCompetitionDetail> getCompetitionDetail(
    String competitionId,
  ) async {
    return const GtexCompetitionDetail(
      summary: _summary,
      fixtures: <GtexCompetitionFixture>[],
      standings: <GtexCompetitionStanding>[],
      stages: <GtexTournamentStageProgress>[
        GtexTournamentStageProgress(
          title: 'Semi Final',
          statusLabel: 'Live',
          progressPercent: .5,
          summary: 'Two fixtures in progress.',
        ),
      ],
      rules: <GtexCompetitionRule>[],
      newsSignals: <String>[],
    );
  }

  @override
  Future<void> joinCompetition(String competitionId) async {
    joinCalls += 1;
  }

  @override
  Future<List<GtexCompetitionSummary>> listCompetitions() async {
    return const <GtexCompetitionSummary>[_summary];
  }
}
