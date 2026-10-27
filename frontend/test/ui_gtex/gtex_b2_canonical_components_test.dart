import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

void main() {
  group('Phase B2 — GtexStatusPresenter (Document F10)', () {
    test('maps all warning / pending backend values to warning + clock', () {
      const List<String> pendingEnums = <String>[
        'pending',
        'requested',
        'awaiting_payment',
        'payment_submitted',
        'draft',
        'pending_kyc',
        'pending_review',
        'under_review',
        'reviewing',
        'open',
        'recommended',
        'scheduled',
      ];
      for (final String value in pendingEnums) {
        final GtexPresentedStatus status = GtexStatusPresenter.present(value);
        expect(
          status.kind,
          GtexSemanticStatusKind.warning,
          reason: '$value should map to warning',
        );
        expect(status.icon, Icons.schedule_rounded);
        expect(status.color, GtexColors.navy.warning);
        expect(status.isPendingLike, isTrue);
      }

      expect(
        GtexStatusPresenter.present('pending_review').label,
        'In review',
      );
      expect(
        GtexStatusPresenter.present(
          'recommended',
          context: GtexStatusContext.decisionRequired,
        ).label,
        'Awaiting you',
      );
      expect(
        GtexStatusPresenter.present('pending').label,
        'Pending',
      );
    });

    test('maps processing and held to info with spinner or pause icon', () {
      final GtexPresentedStatus processing = GtexStatusPresenter.present(
        'processing',
      );
      expect(processing.kind, GtexSemanticStatusKind.info);
      expect(processing.label, 'Processing');
      expect(processing.icon, Icons.sync_rounded);
      expect(processing.color, GtexColors.navy.info);

      final GtexPresentedStatus held = GtexStatusPresenter.present('held');
      expect(held.kind, GtexSemanticStatusKind.info);
      expect(held.label, 'On hold');
      expect(held.icon, Icons.pause_circle_outline_rounded);
    });

    test('maps all settled/confirmed backend values to success + check', () {
      const List<String> confirmedEnums = <String>[
        'verified',
        'committed',
        'confirmed',
        'completed',
        'paid',
        'approved',
        'accepted',
        'executed',
        'published',
        'finished',
      ];
      for (final String value in confirmedEnums) {
        final GtexPresentedStatus status = GtexStatusPresenter.present(value);
        expect(
          status.kind,
          GtexSemanticStatusKind.success,
          reason: '$value should map to success',
        );
        expect(status.icon, Icons.check_circle_outline_rounded);
        expect(status.color, GtexColors.navy.success);
        expect(status.isTerminal, isTrue);
      }
      expect(GtexStatusPresenter.present('completed').label, 'Done');
      expect(GtexStatusPresenter.present('confirmed').label, 'Confirmed');
    });

    test('maps failed, rejected, cancelled, expired, blocked to danger + x', () {
      const Map<String, String> expectedLabels = <String, String>{
        'failed': 'Failed',
        'rejected': 'Rejected',
        'cancelled': 'Cancelled',
        'expired': 'Expired',
        'blocked': 'Blocked',
      };
      for (final MapEntry<String, String> entry in expectedLabels.entries) {
        final GtexPresentedStatus status = GtexStatusPresenter.present(
          entry.key,
        );
        expect(status.kind, GtexSemanticStatusKind.danger);
        expect(status.label, entry.value);
        expect(status.icon, Icons.cancel_outlined);
        expect(status.color, GtexColors.navy.danger);
      }
    });

    test('maps reversed, retracted, disputed to outlined danger + undo/flag', () {
      final GtexPresentedStatus reversed = GtexStatusPresenter.present(
        'reversed',
      );
      expect(reversed.kind, GtexSemanticStatusKind.dangerOutline);
      expect(reversed.outlined, isTrue);
      expect(reversed.label, 'Reversed');
      expect(reversed.icon, Icons.undo_rounded);

      final GtexPresentedStatus retracted = GtexStatusPresenter.present(
        'retracted',
      );
      expect(retracted.outlined, isTrue);
      expect(retracted.label, 'Retracted');

      final GtexPresentedStatus disputed = GtexStatusPresenter.present(
        'disputed',
      );
      expect(disputed.outlined, isTrue);
      expect(disputed.label, 'Disputed');
      expect(disputed.icon, Icons.flag_outlined);
    });

    test('maps countered, live, and unknown backend values safely', () {
      final GtexPresentedStatus countered = GtexStatusPresenter.present(
        'countered',
      );
      expect(countered.kind, GtexSemanticStatusKind.info);
      expect(countered.label, 'Countered');
      expect(countered.icon, Icons.swap_horiz_rounded);

      final GtexPresentedStatus live = GtexStatusPresenter.present('live');
      expect(live.kind, GtexSemanticStatusKind.live);
      expect(live.label, 'Live');
      expect(live.pulsing, isTrue);
      expect(live.color, GtexColors.navy.live);

      final GtexPresentedStatus unknown = GtexStatusPresenter.present(
        'awaiting_medical_clearance',
      );
      expect(unknown.kind, GtexSemanticStatusKind.neutral);
      expect(unknown.isUnknown, isTrue);
      expect(unknown.label, 'Awaiting medical clearance');
    });
  });

  group('Phase B2 — GtexPortrait (Document F8 & F9)', () {
    testWidgets(
      'delegates to GtexRegenPortrait URL whitelist and passes DPR-scaled cacheWidth/cacheHeight',
      (WidgetTester tester) async {
        await tester.pumpWidget(
          const MediaQuery(
            data: MediaQueryData(devicePixelRatio: 2.0),
            child: MaterialApp(
              home: Scaffold(
                body: GtexPortrait(
                  portraitUrl:
                      'https://res.cloudinary.com/dvxiniqew/image/upload/regen_newgen_faces/script_skin_hair/West_african/Buzz/west-african-buzz-2.png',
                  seed: 'regen-101',
                  position: 'ST',
                  nationalityCode: 'NGA',
                  playerName: 'Victor Adeyemi',
                  size: GtexPortraitSize.md72,
                  aspect: GtexPortraitAspect.hero4x5,
                ),
              ),
            ),
          ),
        );

        final Image imageWidget = tester.widget<Image>(find.byType(Image));
        final ResizeImage resizeImage = imageWidget.image as ResizeImage;
        expect(resizeImage.width, 144); // 72 * 2.0 DPR
        expect(resizeImage.height, 180); // (72 / 0.8) * 2.0 DPR
        expect(find.text('PORTRAIT PENDING'), findsNothing);
      },
    );

    testWidgets(
      'rejects unapproved portrait URLs and renders deterministic pending plate',
      (WidgetTester tester) async {
        await tester.pumpWidget(
          const MaterialApp(
            home: Scaffold(
              body: GtexPortrait(
                portraitUrl: 'https://untrusted.example.com/fake-avatar.png',
                seed: 'regen-202',
                position: 'GK',
                nationalityCode: 'GHA',
                size: GtexPortraitSize.lg120,
              ),
            ),
          ),
        );

        expect(find.byType(Image), findsNothing);
        expect(find.text('PORTRAIT PENDING'), findsOneWidget);
        expect(find.text('GK'), findsOneWidget);
        expect(find.text('GHA'), findsOneWidget);
      },
    );
  });

  group('Phase B2 — GtexConfirmSheet (Document F8 & M2)', () {
    testWidgets(
      'prevents duplicate submissions on double-tap and passes idempotency key',
      (WidgetTester tester) async {
        int submitCount = 0;
        String? capturedKey;

        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: GtexConfirmSheet(
                title: 'Confirm Transfer Bid',
                summary: 'Submit official transfer offer for Victor Adeyemi.',
                confirmLabel: 'Submit Bid',
                variant: GtexConfirmVariant.financial,
                financialDetails: const GtexConfirmFinancialDetails(
                  amountLabel: '12,500',
                  currencyCode: 'GTC',
                  feeLabel: '125',
                  balanceAfterLabel: '35,575',
                  idempotencyKey: 'idem-bid-001',
                ),
                onConfirm: (String key) async {
                  submitCount += 1;
                  capturedKey = key;
                  await Future<void>.delayed(const Duration(milliseconds: 80));
                },
              ),
            ),
          ),
        );

        expect(find.byKey(const Key('gtex-confirm-financial-box')), findsOneWidget);
        expect(find.textContaining('12,500 GTC'), findsOneWidget);
        expect(find.text('Ref: idem-bid-001'), findsOneWidget);

        final Finder submitFinder = find.byKey(
          const Key('gtex-confirm-submit-button'),
        );
        // Simulate rapid double-tap while the first request is in flight.
        await tester.tap(submitFinder);
        await tester.pump();
        await tester.tap(submitFinder);
        await tester.pump(const Duration(milliseconds: 100));

        expect(submitCount, 1);
        expect(capturedKey, 'idem-bid-001');
        expect(
          find.byKey(const Key('gtex-confirm-success-banner')),
          findsOneWidget,
        );
      },
    );
  });

  group('Phase B2 — GtexMoney, GtexAttentionCard & GtexPolicyChip', () {
    testWidgets(
      'renders GtexMoney with explicit currency code and pending clock indicator',
      (WidgetTester tester) async {
        await tester.pumpWidget(
          const MaterialApp(
            home: Scaffold(
              body: Column(
                children: <Widget>[
                  GtexMoney(amount: 48200, unit: GtexCurrencyUnit.gtc),
                  GtexMoney(
                    amount: 1500,
                    unit: GtexCurrencyUnit.fnc,
                    isPending: true,
                  ),
                ],
              ),
            ),
          ),
        );

        expect(find.text('48,200 GTC'), findsOneWidget);
        expect(find.text('1,500 FNC'), findsOneWidget);
        expect(
          find.byKey(const Key('gtex-money-pending-icon')),
          findsOneWidget,
        );
      },
    );

    testWidgets(
      'renders GtexAttentionCard and GtexPolicyChip across delegation states',
      (WidgetTester tester) async {
        bool tapped = false;
        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: Column(
                children: <Widget>[
                  GtexAttentionCard(
                    title: 'Approve recruitment budget',
                    subtitle: 'Head Scout requests 2,000 GTC for West Africa assignment.',
                    variant: GtexAttentionVariant.approval,
                    state: GtexAttentionState.unread,
                    dueLabel: 'Due 1d',
                    whoActsNextLabel: 'OWNER ACTS NEXT',
                    onPrimaryAction: () {
                      tapped = true;
                    },
                  ),
                  GtexPolicyChip.fromBackendMode(
                    'automatic',
                    capLabel: '5,000 GTC',
                  ),
                ],
              ),
            ),
          ),
        );

        expect(find.text('Approve recruitment budget'), findsOneWidget);
        expect(find.text('Due 1d'), findsOneWidget);
        expect(find.text('OWNER ACTS NEXT'), findsOneWidget);
        expect(find.text('Automatic <= 5,000 GTC'), findsOneWidget);
        expect(
          find.byKey(const Key('gtex-attention-unread-dot')),
          findsOneWidget,
        );

        await tester.tap(find.text('Review'));
        expect(tapped, isTrue);
      },
    );
  });
}
