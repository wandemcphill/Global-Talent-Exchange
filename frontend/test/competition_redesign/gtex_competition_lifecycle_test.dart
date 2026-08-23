import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/competition_redesign/models/gtex_competition_models.dart';
import 'package:gte_frontend/features/competition_redesign/widgets/gtex_competition_lifecycle_rail.dart';

GtexCompetitionSummary _summary({
  GtexCompetitionStatus status = GtexCompetitionStatus.live,
  GtexCompetitionViewerOutcome viewerOutcome =
      GtexCompetitionViewerOutcome.unknown,
  String? winnerClubName,
  bool prizeSettled = false,
  int registeredClubs = 12,
  int maxClubs = 32,
}) {
  return GtexCompetitionSummary(
    id: 'comp-1',
    title: 'Global Talent Cup',
    kind: GtexCompetitionKind.gtexTournament,
    status: status,
    regionLabel: 'Worldwide',
    entryFeeCredits: 500,
    prizePoolCredits: 45000,
    registeredClubs: registeredClubs,
    maxClubs: maxClubs,
    progressPercent: .5,
    currentStage: 'Group Stage',
    startsAtLabel: 'Live now',
    description: 'Premier GTEX club tournament.',
    viewerOutcome: viewerOutcome,
    winnerClubName: winnerClubName,
    prizeSettled: prizeSettled,
  );
}

void main() {
  group('lifecycleStage', () {
    test('draft reads as upcoming', () {
      expect(
        _summary(status: GtexCompetitionStatus.draft).lifecycleStage,
        GtexCompetitionLifecycleStage.upcoming,
      );
    });

    test('both registration states collapse to registration', () {
      expect(
        _summary(status: GtexCompetitionStatus.registrationOpen).lifecycleStage,
        GtexCompetitionLifecycleStage.registration,
      );
      expect(
        _summary(
          status: GtexCompetitionStatus.registrationClosed,
        ).lifecycleStage,
        GtexCompetitionLifecycleStage.registration,
      );
    });

    test('completed but unpaid stops short of settlement', () {
      final GtexCompetitionSummary summary = _summary(
        status: GtexCompetitionStatus.completed,
      );
      expect(summary.lifecycleStage, GtexCompetitionLifecycleStage.completed);
      expect(summary.isAwaitingSettlement, isTrue);
    });

    test('completed and paid reaches settlement', () {
      final GtexCompetitionSummary summary = _summary(
        status: GtexCompetitionStatus.completed,
        prizeSettled: true,
      );
      expect(summary.lifecycleStage, GtexCompetitionLifecycleStage.settlement);
      expect(summary.isAwaitingSettlement, isFalse);
    });

    test('stage ranks increase along the journey', () {
      expect(
        GtexCompetitionLifecycleStage.upcoming.rank,
        lessThan(GtexCompetitionLifecycleStage.registration.rank),
      );
      expect(
        GtexCompetitionLifecycleStage.live.rank,
        lessThan(GtexCompetitionLifecycleStage.settlement.rank),
      );
    });
  });

  group('viewer outcome', () {
    test('unknown stays unlabelled rather than guessing', () {
      expect(_summary().viewerOutcomeLabel, isNull);
    });

    test('eliminated and winner are labelled', () {
      expect(
        _summary(
          viewerOutcome: GtexCompetitionViewerOutcome.eliminated,
        ).viewerOutcomeLabel,
        'Eliminated',
      );
      expect(
        _summary(
          viewerOutcome: GtexCompetitionViewerOutcome.winner,
        ).viewerOutcomeLabel,
        'Winner',
      );
    });
  });

  group('isJoinable', () {
    test('open with room is joinable', () {
      expect(
        _summary(
          status: GtexCompetitionStatus.registrationOpen,
          registeredClubs: 10,
          maxClubs: 32,
        ).isJoinable,
        isTrue,
      );
    });

    test('a full competition is not joinable', () {
      expect(
        _summary(
          status: GtexCompetitionStatus.registrationOpen,
          registeredClubs: 32,
          maxClubs: 32,
        ).isJoinable,
        isFalse,
      );
    });
  });

  group('GtexCompetitionLifecycleRail', () {
    Future<void> pumpRail(
      WidgetTester tester,
      GtexCompetitionSummary summary,
    ) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: GtexCompetitionLifecycleRail(summary: summary),
          ),
        ),
      );
    }

    testWidgets('shows the current stage', (tester) async {
      await pumpRail(tester, _summary(status: GtexCompetitionStatus.live));
      expect(find.text('Live'), findsOneWidget);
    });

    testWidgets('flags pending prize settlement', (tester) async {
      await pumpRail(
        tester,
        _summary(status: GtexCompetitionStatus.completed),
      );
      expect(find.text('Prize settlement pending'), findsOneWidget);
    });

    testWidgets('names the winner once known', (tester) async {
      await pumpRail(
        tester,
        _summary(
          status: GtexCompetitionStatus.completed,
          prizeSettled: true,
          winnerClubName: 'Lagos Crown',
        ),
      );
      expect(find.text('Winner: Lagos Crown'), findsOneWidget);
    });

    testWidgets('shows the viewer as eliminated', (tester) async {
      await pumpRail(
        tester,
        _summary(viewerOutcome: GtexCompetitionViewerOutcome.eliminated),
      );
      expect(find.text('Eliminated'), findsOneWidget);
    });

    testWidgets('stays quiet when the viewer outcome is unknown', (
      tester,
    ) async {
      await pumpRail(tester, _summary());
      expect(find.text('Eliminated'), findsNothing);
      expect(find.text('Still in'), findsNothing);
      expect(find.text('Not entered'), findsNothing);
    });
  });
}
