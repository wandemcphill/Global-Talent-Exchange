import 'package:flutter/foundation.dart';

enum GtexAdminSeverity { calm, watch, warning, critical }

enum GtexAdminModuleType {
  overview,
  users,
  clubs,
  players,
  regens,
  kyc,
  orders,
  disputes,
  tournaments,
  jackpot,
  coinEconomy,
  transferHub,
  coinTraders,
  clubLifecycle,
  staffMarketplace,
  academy,
  sponsorships,
  federations,
  fanEconomy,
  broadcast,
  ticketing,
  playerCards,
  globalSearch,
  operationsReadiness,
  creators,
  newsroom,
  moderation,
  launchControl,
  systemHealth,
}

@immutable
class GtexAdminMetric {
  const GtexAdminMetric({
    required this.label,
    required this.value,
    this.delta,
    this.severity = GtexAdminSeverity.calm,
  });

  final String label;
  final String value;
  final String? delta;
  final GtexAdminSeverity severity;
}

@immutable
class GtexAdminQueueItem {
  const GtexAdminQueueItem({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.status,
    required this.createdAtLabel,
    this.amountLabel,
    this.severity = GtexAdminSeverity.calm,
    this.ownerLabel,
  });

  final String id;
  final String title;
  final String subtitle;
  final String status;
  final String createdAtLabel;
  final String? amountLabel;
  final String? ownerLabel;
  final GtexAdminSeverity severity;
}

@immutable
class GtexAdminModule {
  const GtexAdminModule({
    required this.type,
    required this.title,
    required this.description,
    required this.countLabel,
    this.severity = GtexAdminSeverity.calm,
  });

  final GtexAdminModuleType type;
  final String title;
  final String description;
  final String countLabel;
  final GtexAdminSeverity severity;
}

@immutable
class GtexJackpotRound {
  const GtexJackpotRound({
    required this.id,
    required this.title,
    required this.poolLabel,
    required this.status,
    required this.entriesLabel,
    required this.drawTimeLabel,
    required this.winnerLabel,
  });

  final String id;
  final String title;
  final String poolLabel;
  final String status;
  final String entriesLabel;
  final String drawTimeLabel;
  final String winnerLabel;
}

@immutable
class GtexCoinEconomySnapshot {
  const GtexCoinEconomySnapshot({
    required this.circulatingSupply,
    required this.treasuryBalance,
    required this.pendingWithdrawals,
    required this.topupVolumeToday,
    required this.riskStatus,
  });

  final String circulatingSupply;
  final String treasuryBalance;
  final String pendingWithdrawals;
  final String topupVolumeToday;
  final String riskStatus;
}

@immutable
class GtexSystemHealthSignal {
  const GtexSystemHealthSignal({
    required this.name,
    required this.status,
    required this.detail,
    this.severity = GtexAdminSeverity.calm,
  });

  final String name;
  final String status;
  final String detail;
  final GtexAdminSeverity severity;
}

@immutable
class GtexAdminCommandSnapshot {
  const GtexAdminCommandSnapshot({
    required this.metrics,
    required this.modules,
    required this.queues,
    required this.jackpots,
    required this.coinEconomy,
    required this.healthSignals,
  });

  final List<GtexAdminMetric> metrics;
  final List<GtexAdminModule> modules;
  final List<GtexAdminQueueItem> queues;
  final List<GtexJackpotRound> jackpots;
  final GtexCoinEconomySnapshot coinEconomy;
  final List<GtexSystemHealthSignal> healthSignals;

  factory GtexAdminCommandSnapshot.liveUnavailable() {
    return const GtexAdminCommandSnapshot(
      metrics: <GtexAdminMetric>[
        GtexAdminMetric(
          label: 'Readiness',
          value: 'Unavailable',
          delta: 'Awaiting live admin API',
          severity: GtexAdminSeverity.watch,
        ),
      ],
      modules: <GtexAdminModule>[
        GtexAdminModule(
          type: GtexAdminModuleType.overview,
          title: 'Overview',
          description:
              'Live admin readiness has not been loaded from the backend authority.',
          countLabel: 'Blocked',
          severity: GtexAdminSeverity.watch,
        ),
      ],
      queues: <GtexAdminQueueItem>[],
      jackpots: <GtexJackpotRound>[],
      coinEconomy: GtexCoinEconomySnapshot(
        circulatingSupply: 'Unavailable',
        treasuryBalance: 'Unavailable',
        pendingWithdrawals: 'Unavailable',
        topupVolumeToday: 'Unavailable',
        riskStatus: 'Live treasury endpoint required',
      ),
      healthSignals: <GtexSystemHealthSignal>[
        GtexSystemHealthSignal(
          name: 'Admin API',
          status: 'Blocked',
          detail: 'Load /api/admin/operations-readiness with an admin session.',
          severity: GtexAdminSeverity.watch,
        ),
      ],
    );
  }
}
