import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
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
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Operations readiness'), findsOneWidget);
    expect(find.text('Risk, KYC And Compliance'), findsWidgets);
  });
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
