import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/match_gift_api.dart';
import 'package:gte_frontend/features/match/presentation/broadcast_package_screen.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_monetization.dart';
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
            competition: CompetitionSummary(
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
              joinEligibility: const CompetitionJoinEligibility(
                eligible: false,
              ),
              beginnerFriendly: true,
              createdAt: DateTime.utc(2026, 1, 1),
              updatedAt: DateTime.utc(2026, 1, 1),
            ),
            viewStateLoader:
                () async => buildBroadcastTestViewState().copyWith(
                  monetization: const MatchViewerMonetization(
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

      // The redesigned picker requires an explicit gift selection followed by
      // the send action; it must not send the default selection automatically.
      await tester.tap(find.byKey(const Key('gtex-gift-card-goal_celebration')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('gtex-gift-send-button')));
      await tester.pumpAndSettle();

      expect(giftClient.lastTarget?.recipientUserId, 'creator-user-1');
      expect(giftClient.lastGift?.key, 'goal_celebration');
      expect(find.text('Delivered to Studio Kai'), findsOneWidget);
      expect(find.text('10.0000 Fan Coin'), findsOneWidget);
      expect(find.byKey(const Key('gtex-gift-delivery-close')), findsOneWidget);

      await tester.tap(find.byKey(const Key('gtex-gift-delivery-close')));
      await tester.pumpAndSettle();
      expect(
        find.text('Goal Celebration sent to Studio Kai for 10.0000 Fan Coin.'),
        findsOneWidget,
      );
    },
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
