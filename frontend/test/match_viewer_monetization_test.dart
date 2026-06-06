import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_center/presentation/gtex_match_viewer_screen.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_type.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('quarantined viewer ignores premium playback and ad controls', (
    WidgetTester tester,
  ) async {
    int loadCount = 0;
    tester.view.physicalSize = const Size(1440, 1200);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final CompetitionSummary competition = _buildCompetition(
      id: 'viewer-monetization-quarantine',
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GtexMatchViewerScreen(
          competition: competition,
          matchKey: competition.id,
          viewStateLoader: () async {
            loadCount += 1;
            throw StateError('legacy viewer loader should stay quarantined');
          },
          presentationMode: Object(),
          renderMode: Object(),
          entitlement: Object(),
        ),
      ),
    );

    await tester.pump();

    expect(loadCount, 0);
    expect(
      find.byKey(GtexMatchViewerScreen.quarantinePanelKey),
      findsOneWidget,
    );
    expect(find.byKey(const Key('match-pitch-2d-canvas')), findsNothing);
    expect(find.byKey(const Key('match-2d-controls')), findsNothing);
    expect(find.byKey(const Key('match-ad-preroll')), findsNothing);
    expect(find.byKey(const Key('match-sponsored-highlight')), findsNothing);
    expect(find.byKey(const Key('match-rewarded-ad-card')), findsNothing);
    expect(find.byKey(const Key('match-ad-live-banner')), findsNothing);
    expect(find.textContaining('Gift'), findsNothing);
    expect(find.textContaining('Watch in Cinematic Mode'), findsNothing);
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
    matchType: MatchType.gtexHosted,
    joinEligibility: const CompetitionJoinEligibility(eligible: true),
    beginnerFriendly: true,
    createdAt: DateTime.utc(2026, 1, 1),
    updatedAt: DateTime.utc(2026, 1, 2),
  );
}
