import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/trust_ops_redesign/trust_ops_redesign.dart';
import 'package:gte_frontend/features/trust_ops_redesign/widgets/gtex_wallet_order_widgets.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

void main() {
  testWidgets('wallet and trust center renders core sections', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: ThemeData.dark(useMaterial3: true),
        home: const Scaffold(
          body: GtexWalletOrdersScreen(
            repository: GtexTrustOpsDemoRepository(),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Wallet, Orders & Trust Center'), findsOneWidget);
    expect(find.text('Wallet'), findsWidgets);
    expect(find.text('Orders'), findsWidgets);
    expect(find.text('KYC'), findsWidgets);
    expect(find.text('Disputes'), findsWidgets);
  });

  testWidgets('admin trust ops renders queues', (WidgetTester tester) async {
    await tester.binding.setSurfaceSize(const Size(1400, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      MaterialApp(
        theme: ThemeData.dark(useMaterial3: true),
        home: const Scaffold(
          body: GtexAdminTrustOpsScreen(backendMode: GteBackendMode.fixture),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Admin Trust Operations'), findsOneWidget);
    expect(find.text('KYC Queue'), findsOneWidget);
    expect(find.text('Disputes'), findsWidgets);
    expect(find.text('Approve KYC'), findsOneWidget);
    expect(find.text('Reject KYC'), findsOneWidget);
  });

  testWidgets('admin trust ops approve calls live review adapter', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1400, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final _RecordingTrustOpsRepository repository =
        _RecordingTrustOpsRepository();
    await tester.pumpWidget(
      MaterialApp(
        theme: ThemeData.dark(useMaterial3: true),
        home: Scaffold(
          body: GtexAdminTrustOpsScreen(repository: repository),
        ),
      ),
    );

    await tester.pumpAndSettle();
    await tester.tap(find.text('Approve KYC'));
    await tester.pumpAndSettle();

    expect(repository.reviewCalls.length, 1);
    expect(repository.reviewCalls.single.$1, 'kyc-201');
    expect(repository.reviewCalls.single.$2, isTrue);
    expect(find.text('KYC kyc-201 verified.'), findsOneWidget);
  });

  testWidgets('admin trust ops reply posts dispute message', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1400, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final _RecordingTrustOpsRepository repository =
        _RecordingTrustOpsRepository();
    await tester.pumpWidget(
      MaterialApp(
        theme: ThemeData.dark(useMaterial3: true),
        home: Scaffold(
          body: GtexAdminTrustOpsScreen(repository: repository),
        ),
      ),
    );

    await tester.pumpAndSettle();
    await tester.tap(find.text('Disputes').first);
    await tester.pumpAndSettle();
    expect(find.text('Reply to dispute'), findsOneWidget);
    await tester.tap(find.text('Reply to dispute'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Send reply'));
    await tester.pumpAndSettle();

    expect(repository.replyCalls.length, 1);
    expect(repository.replyCalls.single.$1, 'dsp-301');
    expect(repository.replyCalls.single.$2, contains('dsp-301'));
    expect(find.text('Reply sent on dispute dsp-301.'), findsOneWidget);
  });

  testWidgets('admin trust ops approve withdrawal order', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1400, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final _RecordingTrustOpsRepository repository =
        _RecordingTrustOpsRepository();
    await tester.pumpWidget(
      MaterialApp(
        theme: ThemeData.dark(useMaterial3: true),
        home: Scaffold(
          body: GtexAdminTrustOpsScreen(repository: repository),
        ),
      ),
    );

    await tester.pumpAndSettle();
    await tester.tap(find.text('Orders / Withdrawals'));
    await tester.pumpAndSettle();
    expect(find.text('Approve'), findsOneWidget);
    await tester.tap(find.text('Approve'));
    await tester.pumpAndSettle();

    expect(repository.orderReviewCalls.length, 1);
    expect(repository.orderReviewCalls.single.$1, 'wd-901');
    expect(repository.orderReviewCalls.single.$2, isTrue);
    expect(repository.orderReviewCalls.single.$3, GtexOrderKind.withdrawal);
    expect(find.text('Withdrawal wd-901 approved.'), findsOneWidget);
  });

  test('operations readiness JSON parses live admin snapshot', () {
    final GtexOperationsReadinessSnapshot snapshot =
        GtexOperationsReadinessSnapshot.fromJson(<String, Object?>{
          'generated_at': '2026-05-11T10:00:00Z',
          'status': 'attention',
          'totals': <String, Object?>{'queues': 1, 'alerts': 1},
          'queues': <Object?>[
            <String, Object?>{
              'key': 'risk_compliance',
              'title': 'Risk, KYC And Compliance',
              'description': 'KYC review load.',
              'status': 'attention',
              'route': '/admin/risk-ops',
              'owner': 'risk_ops_engine',
              'alerts': <Object?>['1 pending KYC'],
              'action_routes': <Object?>['/admin/risk-ops'],
              'metrics': <Object?>[
                <String, Object?>{
                  'key': 'pending_kyc',
                  'label': 'Pending KYC',
                  'value': 1,
                  'display_value': '1',
                  'status': 'attention',
                  'metadata': <String, Object?>{},
                },
              ],
            },
          ],
          'launch_gates': <Object?>[
            <String, Object?>{
              'feature_key': 'broadcast',
              'title': 'Broadcast',
              'enabled': true,
              'launch_state': 'maintenance',
              'audience': 'internal',
              'kill_switch_enabled': true,
              'maintenance_message': 'Paused',
              'route': '/broadcast',
            },
          ],
        });

    expect(snapshot.status, 'attention');
    expect(snapshot.queues.single.metric('pending_kyc')?.value, 1);
    expect(snapshot.launchGates.single.killSwitchEnabled, isTrue);
  });

  test('admin KYC JSON maps treasury verified and under_review statuses', () {
    final GteAdminKyc underReview = GteAdminKyc.fromJson(<String, Object?>{
      'id': 'kyc-1',
      'user_id': 'user-1',
      'status': 'under_review',
      'nin': null,
      'bvn': null,
      'address_line1': '12 Stadium Rd',
      'city': 'Lagos',
      'state': 'LA',
      'country': 'Nigeria',
      'submitted_at': '2026-05-11T10:00:00Z',
      'reviewed_at': null,
      'rejection_reason': null,
      'user_email': 'ayo@example.com',
      'user_full_name': 'Ayo Clubhouse',
      'user_phone_number': null,
    });
    final GteAdminKyc verified = GteAdminKyc.fromJson(<String, Object?>{
      'id': 'kyc-2',
      'user_id': 'user-2',
      'status': 'verified',
      'nin': null,
      'bvn': null,
      'address_line1': null,
      'city': null,
      'state': null,
      'country': 'Nigeria',
      'submitted_at': '2026-05-11T10:00:00Z',
      'reviewed_at': '2026-05-11T11:00:00Z',
      'rejection_reason': null,
      'user_email': 'cleared@example.com',
      'user_full_name': null,
      'user_phone_number': null,
    });

    expect(underReview.status, GteKycStatus.pending);
    expect(verified.status, GteKycStatus.fullyVerified);
    expect(
      const GteKycReviewRequest(status: GteKycStatus.fullyVerified).toJson(),
      <String, Object?>{'status': 'verified'},
    );
  });

  testWidgets('trust summary can render live operations readiness summary', (
    WidgetTester tester,
  ) async {
    final GtexTrustOpsState state = await const _ReadinessRepository().load();
    await tester.pumpWidget(
      MaterialApp(
        theme: ThemeData.dark(useMaterial3: true),
        home: Scaffold(
          body: GtexTrustRightSummaryPanel(
            state: state,
            onTopUp: () {},
            onWithdraw: () {},
            adminMode: true,
            selectedKycCase: state.kycCases.first,
            onApproveKyc: () {},
            onRejectKyc: () {},
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Operations readiness'), findsOneWidget);
    expect(find.text('Risk, KYC And Compliance'), findsWidgets);
    expect(find.text('Approve KYC'), findsOneWidget);
    expect(find.text('KYC LIVE'), findsOneWidget);
  });
}

class _RecordingTrustOpsRepository extends GtexTrustOpsRepository {
  final List<(String, bool)> reviewCalls = <(String, bool)>[];
  final List<(String, String)> replyCalls = <(String, String)>[];
  final List<(String, bool, GtexOrderKind)> orderReviewCalls =
      <(String, bool, GtexOrderKind)>[];

  @override
  Future<GtexTrustOpsState> load() async {
    return const GtexTrustOpsState(
      wallet: GtexWalletSummary(
        balanceCredits: 0,
        availableCredits: 0,
        pendingWithdrawalCredits: 750000,
        kycStatus: 'Needs attention',
        lastUpdatedLabel: 'Live',
      ),
      transactions: <GtexTransactionRecord>[],
      orders: <GtexOrderRecord>[
        GtexOrderRecord(
          id: 'wd-901',
          title: 'Withdrawal WD-901',
          subtitle: 'GTBank · pending review',
          totalCredits: 750000,
          status: GtexTrustStatus.pending,
          createdLabel: 'Today',
          itemCount: 1,
          kind: GtexOrderKind.withdrawal,
        ),
      ],
      kycCases: <GtexKycCaseRecord>[
        GtexKycCaseRecord(
          id: 'kyc-201',
          userName: 'Ayo Clubhouse',
          country: 'Nigeria',
          level: 'Under review',
          status: GtexTrustStatus.pending,
          submittedLabel: 'Live',
          riskLabel: 'Manual review',
          notes: 'Address document needs operator confirmation.',
        ),
      ],
      disputes: <GtexDisputeRecord>[
        GtexDisputeRecord(
          id: 'dsp-301',
          title: 'Order escrow clarification',
          counterparty: 'Lagos Titans FC',
          status: GtexTrustStatus.attention,
          amountCredits: 2200000,
          openedLabel: 'Today',
          summary: 'Buyer claims basket payment was captured.',
        ),
      ],
    );
  }

  @override
  Future<void> reviewKyc(
    String profileId, {
    required bool approve,
    String? rejectionReason,
  }) async {
    reviewCalls.add((profileId, approve));
  }

  @override
  Future<void> replyToDispute(
    String disputeId, {
    required String message,
  }) async {
    replyCalls.add((disputeId, message));
  }

  @override
  Future<void> reviewOrder(
    String orderId, {
    required bool approve,
    required GtexOrderKind kind,
    String? notes,
  }) async {
    orderReviewCalls.add((orderId, approve, kind));
  }
}

class _ReadinessRepository extends GtexTrustOpsRepository {
  const _ReadinessRepository();

  @override
  Future<GtexTrustOpsState> load() async {
    final GtexOperationsReadinessSnapshot snapshot =
        GtexOperationsReadinessSnapshot.fromJson(<String, Object?>{
          'generated_at': '2026-05-11T10:00:00Z',
          'status': 'attention',
          'totals': <String, Object?>{'queues': 1, 'alerts': 1},
          'queues': <Object?>[
            <String, Object?>{
              'key': 'risk_compliance',
              'title': 'Risk, KYC And Compliance',
              'description': 'KYC review load.',
              'status': 'attention',
              'route': '/admin/risk-ops',
              'owner': 'risk_ops_engine',
              'alerts': <Object?>['1 pending KYC'],
              'action_routes': <Object?>['/admin/risk-ops'],
              'metrics': <Object?>[
                <String, Object?>{
                  'key': 'pending_kyc',
                  'label': 'Pending KYC',
                  'value': 1,
                  'display_value': '1',
                  'status': 'attention',
                  'metadata': <String, Object?>{},
                },
              ],
            },
          ],
          'launch_gates': const <Object?>[],
        });
    return GtexTrustOpsState(
      wallet: const GtexWalletSummary(
        balanceCredits: 0,
        availableCredits: 0,
        pendingWithdrawalCredits: 0,
        kycStatus: 'Needs attention',
        lastUpdatedLabel: 'Live',
      ),
      transactions: const <GtexTransactionRecord>[],
      orders: const <GtexOrderRecord>[],
      kycCases: const <GtexKycCaseRecord>[
        GtexKycCaseRecord(
          id: 'risk-compliance',
          userName: 'Risk, KYC And Compliance',
          country: 'Global',
          level: '1 pending KYC',
          status: GtexTrustStatus.attention,
          submittedLabel: 'Live',
          riskLabel: 'Needs attention',
          notes: 'KYC review load.',
        ),
      ],
      disputes: const <GtexDisputeRecord>[],
      operationsReadiness: snapshot,
    );
  }
}
