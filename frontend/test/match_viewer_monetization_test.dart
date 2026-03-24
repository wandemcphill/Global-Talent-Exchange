import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_viewer_presentation.dart';
import 'package:gte_frontend/screens/match/gtex_match_viewer_screen.dart';
import 'package:gte_frontend/services/match_3d_monetization_service.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/match/pitch_2d_widget.dart';
import 'package:gte_frontend/widgets/match_3d/gtex_3d_scene.dart';

void main() {
  testWidgets('viewer monetization stays soft-disabled by default', (
    WidgetTester tester,
  ) async {
    final CompetitionSummary competition = _buildCompetition(
      id: 'viewer-monetization-default-off',
    );
    final LiveMatchSnapshot snapshot = LiveMatchFixtures.buildSnapshot(
      competition,
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GtexMatchViewerScreen(
          competition: competition,
          matchKey: competition.id,
          fallbackSnapshot: snapshot,
          preferFallback: true,
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 120));

    expect(find.byType(Pitch2dWidget), findsOneWidget);
    expect(find.byType(Gtex3dScene), findsNothing);
    expect(find.text('Match controls'), findsNothing);
    expect(find.textContaining('Gift'), findsNothing);
    expect(find.textContaining('Cinematic Mode'), findsNothing);
  });

  testWidgets('explicit 3D render mode stays additive and replay-safe', (
    WidgetTester tester,
  ) async {
    final CompetitionSummary competition = _buildCompetition(
      id: 'viewer-explicit-3d',
    );
    final LiveMatchSnapshot snapshot = LiveMatchFixtures.buildSnapshot(
      competition,
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GtexMatchViewerScreen(
          competition: competition,
          matchKey: competition.id,
          fallbackSnapshot: snapshot,
          preferFallback: true,
          renderMode: RenderMode.threeD,
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 120));

    expect(find.byType(Gtex3dScene), findsOneWidget);
    expect(find.byType(Pitch2dWidget), findsNothing);
    expect(find.text('Restart'), findsOneWidget);
    expect(find.text('Next event'), findsOneWidget);
    expect(find.text('Match controls'), findsNothing);
    expect(find.textContaining('Gift'), findsNothing);
  });

  testWidgets('broadcast mode stays presentation-only even when hooks exist', (
    WidgetTester tester,
  ) async {
    const MatchViewerMonetizationFlags enabledViewerMonetization =
        MatchViewerMonetizationFlags(
      enableUpgradePrompt: true,
      enableTournamentUpgrade: true,
      enablePremiumControls: true,
      enableGifting: true,
      enableReactions: true,
    );

    final CompetitionSummary competition = _buildCompetition(
      id: 'viewer-broadcast-presentation-only',
    );
    final LiveMatchSnapshot snapshot = LiveMatchFixtures.buildSnapshot(
      competition,
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GtexMatchViewerScreen(
          competition: competition,
          matchKey: competition.id,
          fallbackSnapshot: snapshot,
          preferFallback: true,
          presentationMode: MatchViewerPresentationMode.broadcast,
          renderMode: RenderMode.threeD,
          isSpectator: true,
          entitlement: const Match3dUserEntitlement.proManager(),
          viewerMonetizationFlags: enabledViewerMonetization,
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 120));

    expect(find.byType(Gtex3dScene), findsOneWidget);
    expect(find.text('Live broadcast'), findsOneWidget);
    expect(find.text('Restart'), findsNothing);
    expect(find.text('Match controls'), findsNothing);
    expect(find.textContaining('Gift'), findsNothing);
    expect(find.textContaining('Official broadcast playback'), findsOneWidget);
  });
}

CompetitionSummary _buildCompetition({required String id}) {
  return CompetitionSummary(
    id: id,
    name: 'GTEX Replay Test',
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
    rulesSummary: 'Replay validation fixture',
    joinEligibility: const CompetitionJoinEligibility(eligible: true),
    beginnerFriendly: true,
    createdAt: DateTime.utc(2026, 1, 1),
    updatedAt: DateTime.utc(2026, 1, 2),
  );
}
