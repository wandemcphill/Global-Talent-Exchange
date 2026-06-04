import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_center/presentation/gtex_match_viewer_screen.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_type.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

import '../support/gtex_match_broadcast_fixture.dart';

void main() {
  testWidgets('quarantined viewer never loads or reveals locked score data', (
    WidgetTester tester,
  ) async {
    int loadCount = 0;
    final CompetitionSummary competition = _competition(
      id: 'match-viewer-score-locked',
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GtexMatchViewerScreen(
          competition: competition,
          matchKey: competition.id,
          viewStateLoader: () async {
            loadCount += 1;
            return buildBroadcastTestViewState().copyWith(
              scoreRevealLocked: true,
            );
          },
        ),
      ),
    );

    await tester.pump();

    expect(loadCount, 0);
    expect(
      find.byKey(GtexMatchViewerScreen.quarantinePanelKey),
      findsOneWidget,
    );
    expect(find.byKey(const Key('match-2d-score-strip')), findsNothing);
    expect(find.text('-- - --'), findsNothing);
    expect(find.text('--:--'), findsNothing);
    expect(find.text('1 - 0'), findsNothing);
    expect(find.text("6'  Home attack"), findsNothing);
    expect(find.text("11'  Lagos score"), findsNothing);
    expect(find.textContaining('scores the first GTEX goal'), findsNothing);
  });
}

CompetitionSummary _competition({required String id}) {
  return CompetitionSummary(
    id: id,
    name: 'GTEX 2D Match Test',
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
    rulesSummary: '2D viewer validation fixture',
    matchType: MatchType.gtexHosted,
    joinEligibility: const CompetitionJoinEligibility(eligible: true),
    beginnerFriendly: true,
    createdAt: DateTime.utc(2026, 1, 1),
    updatedAt: DateTime.utc(2026, 1, 2),
  );
}
