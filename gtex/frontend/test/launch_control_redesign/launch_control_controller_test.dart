import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/launch_control_redesign/launch_control_api.dart';
import 'package:gte_frontend/features/launch_control_redesign/launch_control_controller.dart';
import 'package:gte_frontend/features/launch_control_redesign/launch_control_models.dart';

void main() {
  test('launch-control model parses Batch 34 dashboard payload', () {
    final snapshot = GtexLaunchControlSnapshot.fromJson(<String, Object?>{
      'flags': <Object?>[
        <String, Object?>{
          'id': 'flag-1',
          'feature_key': 'transfer_hub',
          'title': 'Transfer Hub',
          'description': 'Transfer hub rollout',
          'enabled': true,
          'audience': 'beta',
          'launch_state': 'beta',
          'allowed_roles': <String>['admin'],
          'allowed_regions': <String>['NG'],
          'beta_only': true,
          'kill_switch_enabled': false,
          'maintenance_message': null,
          'metadata': <String, Object?>{'route': '/app/market'},
          'route': '/app/market',
          'updated_at': '2026-05-11T09:00:00Z',
        },
      ],
      'beta_grants': <Object?>[],
      'recent_audit_events': <Object?>[],
      'command_routes': <Object?>[],
      'module_health': <Object?>[],
    });

    expect(snapshot.flags.single.featureKey, 'transfer_hub');
    expect(snapshot.flags.single.launchState, GtexLaunchState.beta);
    expect(snapshot.flags.single.route, '/app/market');
    expect(snapshot.gatedCount, 1);

    final clientFlag = GtexClientFeatureFlag.fromJson(<String, Object?>{
      'feature_key': 'fan_coin',
      'title': 'Fan Economy',
      'enabled': true,
      'launch_state': 'beta',
      'route': '/app/community',
      'maintenance_message': null,
    });
    expect(clientFlag.featureKey, 'fan_coin');
    expect(clientFlag.visible, isTrue);
    expect(clientFlag.route, '/app/community');
  });

  test(
    'controller uses fixture fallback, toggles flags, and manages beta',
    () async {
      final controller = GtexLaunchControlController(
        api: GtexLaunchControlApi.fixture(),
      );

      await controller.load();

      expect(controller.snapshot, isNotNull);
      expect(
        controller.clientFlags.any(
          (GtexClientFeatureFlag flag) => flag.featureKey == 'fan_coin',
        ),
        isTrue,
      );
      expect(
        controller.flags.any(
          (GtexLaunchControlFlag flag) => flag.featureKey == 'launch_control',
        ),
        isTrue,
      );

      final flag = controller.flags.firstWhere(
        (GtexLaunchControlFlag item) => item.featureKey == 'transfer_hub',
      );
      expect(flag.enabled, isFalse);

      await controller.toggleFlag(flag);

      final updated = controller.flags.firstWhere(
        (GtexLaunchControlFlag item) => item.featureKey == 'transfer_hub',
      );
      expect(updated.enabled, isTrue);
      expect(controller.actionMessage, contains('Transfer Hub'));

      await controller.changeLaunchState(updated, GtexLaunchState.public);

      final publicFlag = controller.flags.firstWhere(
        (GtexLaunchControlFlag item) => item.featureKey == 'transfer_hub',
      );
      expect(publicFlag.launchState, GtexLaunchState.public);

      await controller.setBetaOnly(publicFlag, betaOnly: true);

      final betaOnlyFlag = controller.flags.firstWhere(
        (GtexLaunchControlFlag item) => item.featureKey == 'transfer_hub',
      );
      expect(betaOnlyFlag.betaOnly, isTrue);

      await controller.grantBetaAccess(
        featureKey: 'fan_coin',
        userId: 'user-new',
        notes: 'fixture grant',
      );

      final granted = controller.snapshot!.betaGrants.firstWhere(
        (GtexBetaAccessGrant grant) =>
            grant.featureKey == 'fan_coin' && grant.userId == 'user-new',
      );
      expect(granted.active, isTrue);

      await controller.revokeBetaAccess(granted);

      final revoked = controller.snapshot!.betaGrants.firstWhere(
        (GtexBetaAccessGrant grant) =>
            grant.featureKey == 'fan_coin' && grant.userId == 'user-new',
      );
      expect(revoked.active, isFalse);
    },
  );
}
