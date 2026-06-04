import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_center/presentation/gtex_match_viewer_screen.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_type.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets(
    'quarantined viewer ignores native runtime requests before local playback',
    (WidgetTester tester) async {
      int loadCount = 0;
      final CompetitionSummary competition = _buildCompetition(
        id: 'match-viewer-native-runtime-quarantine',
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
            renderMode: Object(),
            entitlement: Object(),
            engineBridge: Object(),
            androidLiveBootstrapProvisioner: Object(),
          ),
        ),
      );

      await tester.pump();

      expect(loadCount, 0);
      expect(
        find.byKey(GtexMatchViewerScreen.quarantinePanelKey),
        findsOneWidget,
      );
      expect(find.byType(AndroidView, skipOffstage: false), findsNothing);
      expect(
        find.textContaining('Native 3D session', skipOffstage: false),
        findsNothing,
      );
      expect(
        find.textContaining('Flutter 3D fallback', skipOffstage: false),
        findsNothing,
      );
    },
    variant: const TargetPlatformVariant(<TargetPlatform>{
      TargetPlatform.android,
    }),
  );
}

CompetitionSummary _buildCompetition({required String id}) {
  return CompetitionSummary(
    id: id,
    name: 'GTEX Native Runtime Viewer Test',
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
    rulesSummary: 'Native runtime viewer fixture',
    matchType: MatchType.gtexHosted,
    joinEligibility: const CompetitionJoinEligibility(eligible: true),
    beginnerFriendly: true,
    createdAt: DateTime.utc(2026, 1, 1),
    updatedAt: DateTime.utc(2026, 1, 2),
  );
}
