import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/features/owner_console/data/owner_console_api.dart';
import 'package:gte_frontend/features/owner_console/widgets/owner_admin_review_section.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

class _FakeOwnerConsoleReader extends OwnerConsoleApi {
  _FakeOwnerConsoleReader()
    : super(
        client: GteAuthedApi(
          config: const GteRepositoryConfig(
            baseUrl: 'http://127.0.0.1:8000',
            mode: GteBackendMode.fixture,
          ),
          transport: GteHttpTransport(),
          accessToken: 'fixture-admin-token',
          mode: GteBackendMode.fixture,
        ),
      );

  final List<String> reviewedWithdrawals = <String>[];
  final List<String> decidedFlags = <String>[];
  final List<String> releasedPayouts = <String>[];

  @override
  Future<OwnerReviewQueue> fetchReviewQueue() async {
    return const OwnerReviewQueue(
      withdrawals: <OwnerWithdrawalReview>[
        OwnerWithdrawalReview(
          id: 'wd-1',
          userId: 'owner-1',
          amountCoin: 250,
          amountNgn: 375000,
          bankName: 'Zenith Bank',
          accountLast4: '4821',
          accountName: 'Lagos Royalty Sports Ltd',
          status: 'pending_review',
          risk: 'medium',
        ),
      ],
      flags: <OwnerRiskFlag>[
        OwnerRiskFlag(
          id: 'flag-1',
          flagType: 'velocity_spike',
          severity: 'high',
          scoreImpact: 35,
          clubId: 'lagos-royals',
          detail: 'Rapid showroom transfers within 15m',
        ),
      ],
      heldPayouts: <OwnerHeldPayout>[
        OwnerHeldPayout(
          id: 'payout-1',
          eventType: 'mini_league_prize',
          netAmount: 120,
          currency: 'GTX',
          clubId: 'lagos-royals',
          memo: 'Held pending KYC check',
        ),
      ],
    );
  }

  @override
  Future<void> reviewWithdrawal(
    String withdrawalId,
    String decision, {
    String? note,
  }) async {
    reviewedWithdrawals.add('$withdrawalId:$decision:${note ?? ''}');
  }

  @override
  Future<void> decideFlag(String flagId, String decision) async {
    decidedFlags.add('$flagId:$decision');
  }

  @override
  Future<void> releasePayout(String eventId) async {
    releasedPayouts.add(eventId);
  }
}

void main() {
  group('Phase D2 — Role Workspaces & Admin Owner Review (D7)', () {
    testWidgets(
      'AdminReviewSection enforces capability gating when canReviewOwnerQueue is false',
      (WidgetTester tester) async {
        final _FakeOwnerConsoleReader reader = _FakeOwnerConsoleReader();
        await tester.pumpWidget(
          MaterialApp(
            theme: GteShellTheme.build(),
            home: Scaffold(
              body: AdminReviewSection(
                reader: reader,
                canReviewOwnerQueue: false,
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();

        expect(
          find.byKey(const Key('owner-admin-capability-blocked')),
          findsOneWidget,
        );
        expect(find.text('Owner review queue restricted'), findsOneWidget);
        expect(find.byKey(const Key('owner-admin-review')), findsNothing);
      },
    );

    testWidgets(
      'AdminReviewSection renders O-02 GTX ledger badge, status chips, and executes withdrawal/flag/payout reviews',
      (WidgetTester tester) async {
        tester.view.physicalSize = const Size(1280, 1000);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        final _FakeOwnerConsoleReader reader = _FakeOwnerConsoleReader();
        await tester.pumpWidget(
          MaterialApp(
            theme: GteShellTheme.build(),
            home: Scaffold(body: AdminReviewSection(reader: reader)),
          ),
        );
        await tester.pumpAndSettle();

        expect(
          find.byKey(const Key('owner-admin-ledger-badge')),
          findsOneWidget,
        );
        expect(find.text('Owner Console Ledger (GTX)'), findsOneWidget);
        expect(
          find.byKey(const Key('owner-admin-withdrawal-wd-1')),
          findsOneWidget,
        );
        expect(find.text('In review'), findsOneWidget);
        expect(find.text('On hold'), findsOneWidget);

        // Approve withdrawal with note
        await tester.tap(
          find.byKey(const Key('owner-admin-withdrawal-wd-1-approve')),
        );
        await tester.pumpAndSettle();
        await tester.enterText(
          find.byKey(const Key('owner-confirm-note')),
          'Bank transfer verified',
        );
        await tester.tap(find.byKey(const Key('owner-confirm-ok')));
        await tester.pumpAndSettle();
        expect(
          reader.reviewedWithdrawals,
          contains('wd-1:approve:Bank transfer verified'),
        );

        // Clear risk flag
        await tester.tap(
          find.byKey(const Key('owner-admin-flag-flag-1-clear')),
        );
        await tester.pumpAndSettle();
        expect(reader.decidedFlags, contains('flag-1:clear'));

        // Release held payout
        await tester.tap(
          find.byKey(const Key('owner-admin-payout-payout-1-release')),
        );
        await tester.pumpAndSettle();
        await tester.tap(find.byKey(const Key('owner-confirm-ok')));
        await tester.pumpAndSettle();
        expect(reader.releasedPayouts, contains('payout-1'));
      },
    );
  });
}
