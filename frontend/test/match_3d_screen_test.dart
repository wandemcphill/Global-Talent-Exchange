import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_type.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/screens/match/gtex_match_3d_screen.dart';
import 'package:gte_frontend/services/match_3d_monetization_service.dart';
import 'package:gte_frontend/services/match_viewer_mapper.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/match_3d/entities/pitch_entity.dart';
import 'package:gte_frontend/widgets/match_3d/gtex_3d_scene.dart';

void main() {
  testWidgets('3D match screen renders replay scene and controls', (
    WidgetTester tester,
  ) async {
    final CompetitionSummary competition = _buildCompetition(
      id: 'match-3d-viewer-test',
    );
    final LiveMatchSnapshot snapshot = LiveMatchFixtures.buildSnapshot(
      competition,
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GtexMatch3dScreen(
          competition: competition,
          matchKey: competition.id,
          fallbackSnapshot: snapshot,
          preferFallback: true,
          entitlement: const Match3dUserEntitlement.proManager(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 64));

    expect(find.text('3D Match Viewer'), findsOneWidget);
    expect(find.byType(Gtex3dScene), findsOneWidget);
    expect(find.byKey(const Key('real-match-scorebug')), findsOneWidget);
    expect(find.byKey(const Key('real-match-tactical-hud')), findsOneWidget);
    expect(find.byKey(const Key('commentary-ribbon')), findsOneWidget);
    expect(find.text('Restart'), findsAtLeastNWidgets(1));
    expect(find.text('Next event'), findsOneWidget);

    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump();
  });

  testWidgets('3D scene builds 22 players, one ball, and fixed aspect ratio', (
    WidgetTester tester,
  ) async {
    final CompetitionSummary competition = _buildCompetition(
      id: 'match-3d-scene-test',
    );
    final LiveMatchSnapshot snapshot = LiveMatchFixtures.buildSnapshot(
      competition,
    );
    final MatchViewState viewState = await MatchViewerMapper.load(
      competition: competition,
      matchKey: competition.id,
      fallbackSnapshot: snapshot,
      preferFallback: true,
    );

    final Gtex3dSceneSnapshot scene = Gtex3dScene.describeScene(
      viewState: viewState,
      frame: viewState.firstFrame,
    );

    expect(scene.players, hasLength(22));
    expect(scene.ball.radius, greaterThan(0));

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: Scaffold(
          body: Center(
            child: SizedBox(
              width: 420,
              child: Gtex3dScene(
                viewState: viewState,
                frame: viewState.firstFrame,
              ),
            ),
          ),
        ),
      ),
    );
    await tester.pump();

    final AspectRatio sceneAspectRatio = tester.widget<AspectRatio>(
      find.byKey(Gtex3dScene.aspectRatioKey),
    );
    expect(sceneAspectRatio.aspectRatio, PitchEntity.aspectRatio);
    expect(find.byKey(Gtex3dScene.paintKey), findsOneWidget);

    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump();
  });
}

CompetitionSummary _buildCompetition({required String id}) {
  return CompetitionSummary(
    id: id,
    name: 'GTEX 3D Replay Test',
    format: CompetitionFormat.league,
    visibility: CompetitionVisibility.public,
    status: CompetitionStatus.completed,
    creatorId: 'creator-1',
    creatorName: 'GTEX',
    participantCount: 8,
    capacity: 8,
    currency: 'USD',
    entryFee: 0,
    platformFeePct: 0,
    hostFeePct: 0,
    platformFeeAmount: 0,
    hostFeeAmount: 0,
    prizePool: 0,
    payoutStructure: const <CompetitionPayoutBreakdown>[],
    rulesSummary: '3D replay validation fixture',
    matchType: MatchType.gtexHosted,
    joinEligibility: const CompetitionJoinEligibility(eligible: true),
    beginnerFriendly: true,
    createdAt: DateTime.utc(2026, 1, 1),
    updatedAt: DateTime.utc(2026, 1, 2),
  );
}
