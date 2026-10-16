import 'package:gte_frontend/features/admin_command_redesign/models/gtex_admin_command_models.dart';

GtexAdminCommandSnapshot adminCommandTestSnapshot() {
  return const GtexAdminCommandSnapshot(
    metrics: <GtexAdminMetric>[
      GtexAdminMetric(label: 'Readiness', value: 'test', delta: 'fixture'),
    ],
    modules: <GtexAdminModule>[
      GtexAdminModule(
        type: GtexAdminModuleType.users,
        title: 'Users',
        description: 'Fixture users module for widget coverage.',
        countLabel: '3',
      ),
      GtexAdminModule(
        type: GtexAdminModuleType.jackpot,
        title: 'Jackpot',
        description: 'Fixture jackpot module for widget coverage.',
        countLabel: 'Blocked',
      ),
      GtexAdminModule(
        type: GtexAdminModuleType.coinEconomy,
        title: 'Coin Economy',
        description: 'Fixture coin economy module for widget coverage.',
        countLabel: 'Blocked',
      ),
      GtexAdminModule(
        type: GtexAdminModuleType.clubLifecycle,
        title: 'Club Lifecycle',
        description: 'Fixture club lifecycle module for controller coverage.',
        countLabel: 'Live',
      ),
      GtexAdminModule(
        type: GtexAdminModuleType.fanEconomy,
        title: 'Fan Economy',
        description: 'Fixture fan economy module for controller coverage.',
        countLabel: 'Live',
      ),
    ],
    queues: <GtexAdminQueueItem>[
      GtexAdminQueueItem(
        id: 'queue-1',
        title: 'Fixture queue',
        subtitle: 'Injected from frontend/test only.',
        status: 'attention',
        createdAtLabel: 'test',
        ownerLabel: 'QA',
      ),
    ],
    jackpots: <GtexJackpotRound>[
      GtexJackpotRound(
        id: 'jackpot-test',
        title: 'Fixture jackpot',
        poolLabel: 'Unavailable',
        status: 'Blocked',
        entriesLabel: '0',
        drawTimeLabel: 'Live endpoint required',
        winnerLabel: 'Unavailable',
      ),
    ],
    coinEconomy: GtexCoinEconomySnapshot(
      circulatingSupply: 'Unavailable',
      treasuryBalance: 'Unavailable',
      pendingWithdrawals: 'Unavailable',
      topupVolumeToday: 'Unavailable',
      riskStatus: 'Live endpoint required',
    ),
    healthSignals: <GtexSystemHealthSignal>[
      GtexSystemHealthSignal(
        name: 'Admin API',
        status: 'Test',
        detail: 'Injected fixture from frontend/test only.',
      ),
    ],
  );
}
