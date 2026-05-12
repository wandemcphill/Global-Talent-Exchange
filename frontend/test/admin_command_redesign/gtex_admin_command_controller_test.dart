import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/admin_command_center_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/features/admin_command_redesign/models/gtex_admin_command_models.dart';
import 'package:gte_frontend/features/admin_command_redesign/presentation/gtex_admin_command_controller.dart';

void main() {
  test('admin controller selects modules', () {
    final controller = GtexAdminCommandController();
    expect(controller.selectedModule, GtexAdminModuleType.overview);

    controller.selectModule(GtexAdminModuleType.jackpot);
    expect(controller.selectedModule, GtexAdminModuleType.jackpot);
  });

  test('admin controller filters modules by search query', () {
    final controller = GtexAdminCommandController();

    controller.updateSearch('coin');
    expect(
      controller.modules.any(
        (module) => module.type == GtexAdminModuleType.coinEconomy,
      ),
      isTrue,
    );
  });

  test('demo snapshot includes jackpot and coin economy data', () {
    final snapshot = GtexAdminCommandSnapshot.demo();

    expect(snapshot.jackpots, isNotEmpty);
    expect(snapshot.coinEconomy.circulatingSupply, isNotEmpty);
    expect(snapshot.healthSignals, isNotEmpty);
    expect(
      snapshot.modules.any(
        (module) => module.type == GtexAdminModuleType.clubLifecycle,
      ),
      isTrue,
    );
    expect(
      snapshot.modules.any(
        (module) => module.type == GtexAdminModuleType.fanEconomy,
      ),
      isTrue,
    );
  });

  test('controller maps operations readiness into live command modules', () {
    final controller = GtexAdminCommandController();
    final readiness = AdminOperationsReadinessSnapshot.fromJson(
      <String, Object?>{
        'status': 'blocked',
        'totals': <String, Object?>{
          'queues': 2,
          'alerts': 2,
          'blocked_queues': 1,
          'attention_queues': 1,
          'kill_switches': 1,
        },
        'queues': <Object?>[
          <String, Object?>{
            'key': 'production_data_diagnostics',
            'title': 'Production Data Diagnostics',
            'description': 'Player and module coverage.',
            'status': 'attention',
            'route': '/admin/ops',
            'owner': 'diagnostics',
            'alerts': <Object?>['Regen portrait coverage is below target.'],
            'metrics': <Object?>[
              <String, Object?>{
                'key': 'academy_prospects',
                'label': 'Academy prospects',
                'value': 12,
                'display_value': '12',
                'status': 'ok',
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
      },
    );

    controller.replaceWithOperationsReadiness(readiness);

    expect(controller.snapshot.metrics.first.value, 'blocked');
    expect(
      controller.snapshot.modules.any(
        (module) => module.type == GtexAdminModuleType.operationsReadiness,
      ),
      isTrue,
    );
    expect(
      controller.snapshot.modules.any(
        (module) => module.type == GtexAdminModuleType.broadcast,
      ),
      isTrue,
    );
    expect(controller.snapshot.queues.single.ownerLabel, 'diagnostics');
    expect(
      controller.snapshot.healthSignals.last.severity,
      GtexAdminSeverity.critical,
    );
  });

  test('controller escalates readiness blockers through admin API', () async {
    final controller = GtexAdminCommandController(
      api: _FakeAdminCommandCenterApi(
        const AdminOperationsReadinessDispatch(
          status: 'sent',
          notificationsCreated: 4,
          queueKeys: <String>['risk_compliance', 'ledger_worker_health'],
        ),
      ),
    );

    await controller.escalateSelectedQueueItem();

    expect(controller.actionLoading, isFalse);
    expect(controller.actionError, isNull);
    expect(
      controller.actionMessage,
      '4 readiness notification(s) sent for 2 queue(s).',
    );
  });
}

class _FakeAdminCommandCenterApi extends AdminCommandCenterApi {
  _FakeAdminCommandCenterApi(this.dispatch)
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

  final AdminOperationsReadinessDispatch dispatch;

  @override
  Future<AdminOperationsReadinessDispatch>
  notifyOperationsReadinessBlockers() async {
    return dispatch;
  }
}
