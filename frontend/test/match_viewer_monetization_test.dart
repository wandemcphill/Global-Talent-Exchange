import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_viewer_presentation.dart';
import 'package:gte_frontend/models/match_type.dart';
import 'package:gte_frontend/screens/match/gtex_match_viewer_screen.dart';
import 'package:gte_frontend/services/match_3d_monetization_service.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/match/pitch_2d_widget.dart';

import 'support/gtex_match_broadcast_fixture.dart';

void main() {
  testWidgets('non-premium users stay on the 2D launch viewer', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1440, 1200);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

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
          entitlement: const Match3dUserEntitlement(availableCoins: 1),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 120));

    expect(find.byType(MatchPitch2D), findsOneWidget);
    expect(find.byKey(const Key('match-pitch-2d-canvas')), findsOneWidget);
    expect(find.text('3D lane'), findsNothing);
    expect(find.textContaining('Watch in Cinematic Mode'), findsNothing);
  });

  testWidgets(
    'premium render requests stay on 2D and spectator mode keeps gifting hidden',
    (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1440, 1200);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final CompetitionSummary competition = _buildCompetition(
        id: 'viewer-premium-spectator',
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
          ),
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 120));

      expect(find.byType(MatchPitch2D), findsOneWidget);
      expect(find.byKey(const Key('match-pitch-2d-canvas')), findsOneWidget);
      expect(find.text('Pro Manager'), findsNothing);
      expect(find.textContaining('Watch in Cinematic Mode'), findsNothing);
      expect(find.widgetWithText(FilledButton, 'Restart'), findsNothing);
      expect(find.textContaining('Gift'), findsNothing);
    },
  );

  testWidgets('fallback to 2D stays non-disruptive when gifting is disabled', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1440, 1200);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final CompetitionSummary competition = _buildCompetition(
      id: 'viewer-gifting',
    );
    final LiveMatchSnapshot snapshot = LiveMatchFixtures.buildSnapshot(
      competition,
    );
    final Match3dMonetizationService monetization = Match3dMonetizationService(
      entitlement: const Match3dUserEntitlement.proManager(availableCoins: 1),
      initialRenderMode: RenderMode.threeD,
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
          entitlement: monetization.effectiveEntitlement,
          monetizationService: monetization,
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 120));

    expect(find.byType(MatchPitch2D), findsOneWidget);
    expect(find.textContaining('Gift'), findsNothing);
    expect(find.byKey(const Key('match-2d-controls')), findsOneWidget);

    monetization.fallbackToTwoD(reason: Match3dFailureReason.performanceDrop);
    await _pumpForOverlayTransition(tester);

    expect(find.byType(MatchPitch2D), findsOneWidget);
    expect(find.byKey(const Key('match-2d-controls')), findsOneWidget);
  });

  testWidgets(
    'launch viewer hides sponsored clips, ad banners, and rewarded coins',
    (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1440, 1200);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final CompetitionSummary competition = _buildCompetition(
        id: 'viewer-ads',
      );

      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: GtexMatchViewerScreen(
            competition: competition,
            matchKey: competition.id,
            viewStateLoader:
                () async =>
                    buildBroadcastTestViewState(includeMonetization: true),
            entitlement: const Match3dUserEntitlement(availableCoins: 1),
          ),
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 120));

      expect(find.byType(MatchPitch2D), findsOneWidget);
      expect(find.byKey(const Key('match-ad-preroll')), findsNothing);
      expect(find.byKey(const Key('match-sponsored-highlight')), findsNothing);
      expect(find.byKey(const Key('match-rewarded-ad-card')), findsNothing);
      expect(find.byKey(const Key('match-ad-live-banner')), findsNothing);
    },
  );
}

Future<void> _pumpForOverlayTransition(WidgetTester tester) async {
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 300));
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
    matchType: MatchType.gtexHosted,
    joinEligibility: const CompetitionJoinEligibility(eligible: true),
    beginnerFriendly: true,
    createdAt: DateTime.utc(2026, 1, 1),
    updatedAt: DateTime.utc(2026, 1, 2),
  );
}
