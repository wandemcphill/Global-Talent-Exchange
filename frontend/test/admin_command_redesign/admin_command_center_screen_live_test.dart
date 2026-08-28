import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/admin_command_center_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/screens/admin/admin_command_center_screen.dart';
import 'package:gte_frontend/shared/auth/gtex_admin_capabilities.dart';

void main() {
  testWidgets(
    'production admin command center renders launch gates and notifies blockers',
    (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1600, 2600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        MaterialApp(
          home: AdminCommandCenterScreen(
            baseUrl: 'http://127.0.0.1:8000',
            accessToken: 'fixture-token',
            backendMode: GteBackendMode.fixture,
            api: _FakeAdminCommandCenterApi(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Operations readiness'), findsOneWidget);
      expect(find.text('Launch gates'), findsOneWidget);
      expect(find.text('Broadcast'), findsWidgets);
      expect(find.text('Notify blockers'), findsOneWidget);
      expect(find.text('Launch Control'), findsWidgets);
      expect(find.text('Matchday economy'), findsOneWidget);
      expect(find.text('Coin trader ops'), findsOneWidget);
      expect(find.text('Notification matrix'), findsOneWidget);

      await tester.tap(find.text('Notify blockers'));
      await tester.pumpAndSettle();

      expect(
        find.text('2 readiness notification(s) sent for 1 queue(s).'),
        findsWidgets,
      );
    },
  );

  // The backend enforces these capabilities per-route
  // (backend/app/admin/capabilities.py). The command center must not advertise
  // an action the session's effective permission list cannot perform.
  testWidgets('scoped admin without finance capabilities cannot act', (
    WidgetTester tester,
  ) async {
    await _pumpCommandCenter(
      tester,
      capabilities: _capabilitiesFor(<String>['manage_manager_supply']),
    );

    expect(_isEnabled(tester, 'Save payment rails'), isFalse);
    expect(_isEnabled(tester, 'Save payout controls'), isFalse);
    expect(_isEnabled(tester, 'Create GTEX competition'), isFalse);
    expect(
      find.textContaining('does not carry the manage_payment_rails'),
      findsWidgets,
    );
  });

  testWidgets('capabilities enable exactly the actions they grant', (
    WidgetTester tester,
  ) async {
    await _pumpCommandCenter(
      tester,
      capabilities: _capabilitiesFor(<String>[
        'manage_payment_rails',
        'manage_competitions',
      ]),
    );

    expect(_isEnabled(tester, 'Save payment rails'), isTrue);
    expect(_isEnabled(tester, 'Create GTEX competition'), isTrue);
    // Granted neither -- must stay blocked.
    expect(_isEnabled(tester, 'Save payout controls'), isFalse);
  });

  testWidgets('unchecked capabilities leave controls enabled', (
    WidgetTester tester,
  ) async {
    await _pumpCommandCenter(
      tester,
      capabilities: const GtexAdminCapabilities.unchecked(),
    );

    expect(_isEnabled(tester, 'Save payment rails'), isTrue);
    expect(_isEnabled(tester, 'Save payout controls'), isTrue);
  });
}

GtexAdminCapabilities _capabilitiesFor(List<String> permissions) {
  return GtexAdminCapabilities.fromSession(
    GteAuthSession.fromJson(<String, Object?>{
      'access_token': 'fixture-token',
      'session_id': 'session-scoped',
      'token_type': 'bearer',
      'expires_in': 3600,
      'permissions': permissions,
      'user': <String, Object?>{
        'id': 'scoped-admin-1',
        'email': 'scoped@gtex.test',
        'username': 'scoped',
        'display_name': 'Scoped Admin',
        'role': 'scoped_admin',
      },
    }),
  );
}

Future<void> _pumpCommandCenter(
  WidgetTester tester, {
  required GtexAdminCapabilities capabilities,
}) async {
  // The panels live in a lazy sliver, so the surface must be tall enough for
  // the finance controls to build before they can be asserted on.
  tester.view.physicalSize = const Size(1600, 9000);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });

  await tester.pumpWidget(
    MaterialApp(
      home: AdminCommandCenterScreen(
        baseUrl: 'http://127.0.0.1:8000',
        accessToken: 'fixture-token',
        backendMode: GteBackendMode.fixture,
        api: _FakeAdminCommandCenterApi(),
        capabilities: capabilities,
      ),
    ),
  );
  await tester.pumpAndSettle();
}

bool _isEnabled(WidgetTester tester, String label) {
  final Finder button =
      find
          .ancestor(
            of: find.text(label),
            matching: find.byType(FilledButton),
          )
          .first;
  expect(button, findsOneWidget, reason: 'no FilledButton for "$label"');
  return tester.widget<FilledButton>(button).onPressed != null;
}

class _FakeAdminCommandCenterApi extends AdminCommandCenterApi {
  _FakeAdminCommandCenterApi()
    : super(
        client: GteAuthedApi(
          config: const GteRepositoryConfig(
            baseUrl: 'http://127.0.0.1:8000',
            mode: GteBackendMode.fixture,
          ),
          transport: GteHttpTransport(),
          accessToken: 'fixture-token',
          mode: GteBackendMode.fixture,
        ),
      );

  @override
  Future<GteTreasurySettings> fetchTreasurySettings() async {
    return GteTreasurySettings.fromJson(<String, Object?>{
      'id': 'treasury-fixture',
      'settings_key': 'default',
      'currency_code': 'NGN',
      'deposit_rate_value': 1000,
      'deposit_rate_direction': 'fiat_per_coin',
      'withdrawal_rate_value': 1000,
      'withdrawal_rate_direction': 'fiat_per_coin',
      'min_deposit': 1000,
      'max_deposit': 1000000,
      'min_withdrawal': 1000,
      'max_withdrawal': 500000,
      'deposit_mode': 'manual',
      'withdrawal_mode': 'manual',
      'maintenance_message': null,
      'whatsapp_number': null,
      'active_bank_account': null,
    });
  }

  @override
  Future<List<GteTreasuryBankAccount>> listTreasuryBankAccounts() async {
    return const <GteTreasuryBankAccount>[];
  }

  @override
  Future<GteAdminQueuePage<GteAdminDeposit>> fetchAdminDeposits({
    int limit = 20,
    int offset = 0,
    String? status,
    String? query,
  }) async {
    return GteAdminQueuePage<GteAdminDeposit>(
      items: const <GteAdminDeposit>[],
      total: 0,
      limit: limit,
      offset: offset,
    );
  }

  @override
  Future<AdminPaymentRailsState> fetchPaymentRails() async {
    return const AdminPaymentRailsState(rails: <AdminPaymentRail>[]);
  }

  @override
  Future<AdminWithdrawalControls> fetchWithdrawalControls() async {
    return const AdminWithdrawalControls(
      egameWithdrawalsEnabled: true,
      tradeWithdrawalsEnabled: true,
      processorMode: 'manual_bank_transfer',
      depositsViaBankTransfer: true,
      payoutsViaBankTransfer: true,
    );
  }

  @override
  Future<AdminOperationsReadinessSnapshot> fetchOperationsReadiness() async {
    return AdminOperationsReadinessSnapshot.fromJson(<String, Object?>{
      'status': 'blocked',
      'totals': <String, Object?>{
        'queues': 1,
        'alerts': 1,
        'blocked_queues': 1,
        'attention_queues': 0,
        'kill_switches': 1,
      },
      'queues': <Object?>[
        <String, Object?>{
          'key': 'policy_launch_control',
          'title': 'Policy And Launch Control',
          'description': 'Feature gates, country policy, beta access.',
          'status': 'blocked',
          'route': '/admin/launch-control',
          'owner': 'launch_control_policies',
          'alerts': <Object?>['1 kill switch is active.'],
          'action_routes': <Object?>['/admin/launch-control', '/admin/ops'],
          'metrics': <Object?>[
            <String, Object?>{
              'key': 'kill_switches',
              'label': 'Kill switches',
              'value': 1,
              'display_value': '1',
              'status': 'blocked',
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
          'maintenance_message': 'Rights worker review.',
          'route': '/broadcast/live',
        },
      ],
    });
  }

  @override
  Future<AdminOperationsReadinessDispatch>
  notifyOperationsReadinessBlockers() async {
    return const AdminOperationsReadinessDispatch(
      status: 'sent',
      notificationsCreated: 2,
      queueKeys: <String>['policy_launch_control'],
    );
  }
}
