import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_center/data/match_gift_api.dart';
import 'package:gte_frontend/features/match_center/models/match_engagement.dart';
import 'package:gte_frontend/features/match_center/presentation/broadcast_package_screen.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_type.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

import '../support/gtex_match_broadcast_fixture.dart';

void main() {
  testWidgets(
    'broadcast package sends live gifts through the backend contract',
    (WidgetTester tester) async {
      final _FakeMatchGiftClient giftClient = _FakeMatchGiftClient();

      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: BroadcastPackageScreen(
            matchKey: 'broadcast-package-gifting',
            competition: _broadcastCompetition(),
            viewStateLoader:
                () async => buildBroadcastTestViewState().copyWith(
                  source: 'backend-live',
                  engagement: const MatchViewerEngagement(
                    metadata: <String, Object?>{
                      'gift_recipient_user_id': 'creator-user-1',
                      'gift_recipient_label': 'Studio Kai',
                      'gift_source_scope': 'user_hosted',
                    },
                  ),
                ),
            giftClient: giftClient,
          ),
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 120));

      expect(find.widgetWithText(FilledButton, 'Send gift'), findsOneWidget);

      await tester.tap(find.widgetWithText(FilledButton, 'Send gift'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Crown'));
      await tester.pumpAndSettle();

      expect(giftClient.lastTarget?.recipientUserId, 'creator-user-1');
      expect(giftClient.lastGift?.key, 'crown');
      expect(
        find.text('Crown sent to Studio Kai for 20.0000 Fan Coin.'),
        findsOneWidget,
      );
    },
  );

  testWidgets('broadcast package blocks non-backend local timelines', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: BroadcastPackageScreen(
          matchKey: 'broadcast-package-local',
          competition: _broadcastCompetition(),
          viewStateLoader: () async => buildBroadcastTestViewState(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 120));

    expect(find.text('Backend package pending'), findsOneWidget);
    expect(
      find.textContaining('non-backend match data (fixture)'),
      findsOneWidget,
    );
  });

  testWidgets(
    'broadcast package stays on the backend-authored frame without controls',
    (WidgetTester tester) async {
      int loadCount = 0;

      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: BroadcastPackageScreen(
            matchKey: 'broadcast-package-static-backend',
            competition: _broadcastCompetition(),
            viewStateLoader: () async {
              loadCount += 1;
              return buildBroadcastTestViewState().copyWith(
                source: 'backend-live',
                segmentEndSeconds: 1,
              );
            },
          ),
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 120));

      expect(loadCount, 1);
      expect(find.text('Home attack'), findsWidgets);
      expect(find.text('Lagos score'), findsNothing);
      expect(find.text('2D BROADCAST'), findsOneWidget);
      expect(find.text('Refresh backend'), findsOneWidget);
      expect(find.text('Play'), findsNothing);
      expect(find.text('Pause'), findsNothing);
      expect(find.text('Speed'), findsNothing);
      expect(find.text('Simulate'), findsNothing);
      expect(find.text('Local simulation'), findsNothing);
      expect(find.text('3D'), findsNothing);

      await tester.pump(const Duration(seconds: 30));

      expect(loadCount, 1);
      expect(find.text('Home attack'), findsWidgets);
      expect(find.text('Lagos score'), findsNothing);
      expect(find.text('Play'), findsNothing);
      expect(find.text('Pause'), findsNothing);
    },
  );

  testWidgets('broadcast package blocks synthetic backend-labeled frames', (
    WidgetTester tester,
  ) async {
    final backendState = buildBroadcastTestViewState().copyWith(
      source: 'backend-live',
      segmentEndSeconds: 1,
    );
    final List<MatchTimelineFrame> frames = backendState.frames.toList(
      growable: false,
    );
    final List<MatchTimelineFrame> syntheticFrames = <MatchTimelineFrame>[
      frames.first,
      frames[1].copyWith(isSynthetic: true),
      ...frames.skip(2),
    ];

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: BroadcastPackageScreen(
          matchKey: 'broadcast-package-synthetic-frame',
          competition: _broadcastCompetition(),
          viewStateLoader:
              () async => backendState.copyWith(frames: syntheticFrames),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 120));

    expect(find.text('Generated timeline blocked'), findsOneWidget);
    expect(
      find.textContaining('synthetic or injected frame data'),
      findsOneWidget,
    );
    expect(find.text('2D BROADCAST'), findsNothing);
  });
}

CompetitionSummary _broadcastCompetition() {
  return CompetitionSummary(
    id: 'broadcast-package-gifting',
    name: 'Broadcast Package Gift Test',
    format: CompetitionFormat.league,
    visibility: CompetitionVisibility.public,
    status: CompetitionStatus.inProgress,
    creatorId: 'creator-1',
    creatorName: 'Studio Kai',
    participantCount: 2,
    capacity: 2,
    currency: 'coin',
    entryFee: 0,
    platformFeePct: 0,
    hostFeePct: 0,
    platformFeeAmount: 0,
    hostFeeAmount: 0,
    prizePool: 0,
    payoutStructure: const <CompetitionPayoutBreakdown>[],
    rulesSummary: 'Broadcast package gift fixture.',
    matchType: MatchType.userHosted,
    joinEligibility: const CompetitionJoinEligibility(eligible: false),
    beginnerFriendly: true,
    createdAt: DateTime.utc(2026, 1, 1),
    updatedAt: DateTime.utc(2026, 1, 1),
  );
}

class _FakeMatchGiftClient implements MatchGiftClient {
  MatchGiftTarget? lastTarget;
  MatchGiftCatalogItem? lastGift;

  @override
  Future<MatchGiftReceipt> sendGift({
    required MatchGiftTarget target,
    required MatchGiftCatalogItem gift,
  }) async {
    lastTarget = target;
    lastGift = gift;
    return MatchGiftReceipt(
      giftKey: gift.key,
      giftDisplayName: gift.label,
      grossAmount: gift.fanCoinAmount.toStringAsFixed(4),
      recipientLabel: target.recipientLabel,
      ledgerUnit: "Fan Coin",
    );
  }
}
