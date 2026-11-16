import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/admin_command_center_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';

void main() {
  test('admin operations readiness model parses live hub payload', () {
    final AdminOperationsReadinessSnapshot snapshot =
        AdminOperationsReadinessSnapshot.fromJson(<String, Object?>{
          'status': 'blocked',
          'totals': <String, Object?>{
            'queues': 5,
            'alerts': 3,
            'blocked_queues': 1,
            'attention_queues': 2,
            'kill_switches': 1,
          },
          'queues': <Object?>[
            <String, Object?>{
              'key': 'risk_compliance',
              'title': 'Risk, KYC And Compliance',
              'description': 'KYC review load.',
              'status': 'attention',
              'route': '/admin/risk-ops',
              'owner': 'risk_ops_engine',
              'alerts': <Object?>['1 KYC case needs review'],
              'action_routes': <Object?>['/admin/risk-ops', '/admin/policies'],
              'metrics': <Object?>[
                <String, Object?>{
                  'key': 'pending_kyc',
                  'label': 'Pending KYC',
                  'value': 1,
                  'display_value': '1',
                  'status': 'attention',
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
              'route': '/broadcast/live',
            },
          ],
        });

    expect(snapshot.status, 'blocked');
    expect(snapshot.alertCount, 3);
    expect(snapshot.killSwitchCount, 1);
    expect(snapshot.queues.single.metrics.single.displayValue, '1');
    expect(snapshot.queues.single.actionRoutes, contains('/admin/policies'));
    expect(snapshot.launchGates.single.featureKey, 'broadcast');
    expect(snapshot.launchGates.single.route, '/broadcast/live');
  });

  test(
    'admin operations readiness dispatch parses blocker notification payload',
    () {
      final AdminOperationsReadinessDispatch dispatch =
          AdminOperationsReadinessDispatch.fromJson(<String, Object?>{
            'status': 'sent',
            'notifications_created': 4,
            'queue_keys': <Object?>['risk_compliance', 'moderation_disputes'],
          });

      expect(dispatch.sent, isTrue);
      expect(dispatch.notificationsCreated, 4);
      expect(dispatch.queueKeys, contains('risk_compliance'));
    },
  );

  test(
    'admin economy search, dual-unit wallet credit/transfer, and isolated points transport contracts',
    () async {
      final _QueuedAdminTransport transport = _QueuedAdminTransport(
        <GteTransportResponse>[
          const GteTransportResponse(
            statusCode: 200,
            body: <Object?>[
              <String, Object?>{
                'id': 'usr-1',
                'email': 'fan1@gtex.local',
                'username': 'fan_one',
                'display_name': 'Fan One',
                'role': 'user',
                'is_active': true,
                'kyc_status': 'unverified',
              },
            ],
          ),
          const GteTransportResponse(
            statusCode: 201,
            body: <String, Object?>{
              'transaction_id': 'tx-credit-1',
              'reference': 'adm-credit-1',
              'user_id': 'usr-1',
              'username': 'fan_one',
              'unit': 'credit',
              'amount': 250,
              'balance_before': 1000,
              'balance_after': 1250,
              'reason': 'Fan Coin creator reward',
              'idempotency_key': 'admin-credit-fnc-001',
              'idempotent_replay': false,
            },
          ),
          const GteTransportResponse(
            statusCode: 201,
            body: <String, Object?>{
              'transaction_id': 'tx-xfer-1',
              'reference': 'adm-xfer-1',
              'from_user_id': 'usr-1',
              'from_username': 'fan_one',
              'to_user_id': 'usr-2',
              'to_username': 'fan_two',
              'unit': 'coin',
              'amount': 50,
              'from_balance_before': 100,
              'from_balance_after': 50,
              'to_balance_before': 10,
              'to_balance_after': 60,
              'reason': 'Settlement correction',
              'idempotency_key': 'admin-xfer-gtc-001',
              'idempotent_replay': false,
            },
          ),
          const GteTransportResponse(
            statusCode: 201,
            body: <String, Object?>{
              'entry_id': 'pt-1',
              'account_id': 'pt-acc-1',
              'reference': 'adm-pt-1',
              'user_id': 'usr-1',
              'username': 'fan_one',
              'amount': 300,
              'balance_before': 0,
              'balance_after': 300,
              'lifetime_earned': 300,
              'reason': 'Ambassador achievement',
              'source_scope': 'admin_grant',
              'idempotent_replay': false,
            },
          ),
          const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'user_id': 'usr-1',
              'account_id': 'pt-acc-1',
              'balance': 300,
              'lifetime_earned': 300,
              'lifetime_spent': 0,
              'source_scope': 'personal_reward_points',
            },
          ),
        ],
      );

      final AdminCommandCenterApi api = AdminCommandCenterApi(
        client: GteAuthedApi(
          config: const GteRepositoryConfig(
            baseUrl: 'https://example.test',
            mode: GteBackendMode.live,
          ),
          transport: transport,
          accessToken: 'admin-token-1',
          mode: GteBackendMode.live,
        ),
      );

      final List<AdminDirectoryUser> users = await api.searchUsers(query: 'fan');
      expect(users, hasLength(1));
      expect(users.single.username, 'fan_one');
      expect(transport.requests[0].method, 'GET');
      expect(transport.requests[0].uri.path, '/api/v2/admin/finance/users');
      expect(transport.requests[0].uri.queryParameters['search'], 'fan');

      final AdminGodModeWalletCreditResult creditResult = await api
          .adminCreditUserWallet(
            userId: 'usr-1',
            unit: 'CREDIT',
            amount: 250,
            reason: 'Fan Coin creator reward',
            idempotencyKey: 'admin-credit-fnc-001',
          );
      expect(creditResult.unit, 'credit');
      expect(creditResult.balanceAfter, 1250);
      expect(transport.requests[1].method, 'POST');
      expect(
        transport.requests[1].uri.path,
        '/api/v2/admin/god-mode/wallets/credit',
      );
      expect(
        (transport.requests[1].body as Map<String, Object?>)['unit'],
        'credit',
      );

      final AdminGodModeWalletTransferResult transferResult = await api
          .adminTransferUserWallet(
            fromUserId: 'usr-1',
            toUserId: 'usr-2',
            unit: 'COIN',
            amount: 50,
            reason: 'Settlement correction',
            idempotencyKey: 'admin-xfer-gtc-001',
          );
      expect(transferResult.unit, 'coin');
      expect(transferResult.fromBalanceAfter, 50);
      expect(transferResult.toBalanceAfter, 60);
      expect(
        transport.requests[2].uri.path,
        '/api/v2/admin/god-mode/wallets/transfer',
      );

      final AdminPointGrantResult pointGrant = await api.adminGrantUserPoints(
        userId: 'usr-1',
        amount: 300,
        reason: 'Ambassador achievement',
        idempotencyKey: 'admin-pt-001',
      );
      expect(pointGrant.sourceScope, 'admin_grant');
      expect(pointGrant.balanceAfter, 300);
      expect(
        transport.requests[3].uri.path,
        '/api/v2/admin/god-mode/points/grant',
      );

      final AdminUserPointsBalance balance = await api.fetchUserPoints('usr-1');
      expect(balance.sourceScope, 'personal_reward_points');
      expect(balance.balance, 300);
      expect(
        transport.requests[4].uri.path,
        '/api/v2/admin/god-mode/users/usr-1/points',
      );
    },
  );
}

class _QueuedAdminTransport implements GteTransport {
  _QueuedAdminTransport(this._responses);

  final List<GteTransportResponse> _responses;
  final List<GteTransportRequest> requests = <GteTransportRequest>[];

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    requests.add(request);
    return _responses.removeAt(0);
  }
}
