import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/admin_command_center_api.dart';

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
}
