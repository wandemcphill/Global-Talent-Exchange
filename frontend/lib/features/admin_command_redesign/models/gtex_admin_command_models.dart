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

  factory GtexAdminCommandSnapshot.demo() {
    return const GtexAdminCommandSnapshot(
      metrics: [
        GtexAdminMetric(
          label: 'Users online',
          value: '1,284',
          delta: '+18% today',
        ),
        GtexAdminMetric(
          label: 'Open KYC',
          value: '74',
          delta: '22 urgent',
          severity: GtexAdminSeverity.watch,
        ),
        GtexAdminMetric(
          label: 'Orders today',
          value: '319',
          delta: '₵48.2M volume',
        ),
        GtexAdminMetric(
          label: 'Disputes',
          value: '11',
          delta: '3 high priority',
          severity: GtexAdminSeverity.warning,
        ),
        GtexAdminMetric(
          label: 'Coin risk',
          value: 'Stable',
          delta: 'No anomaly',
        ),
        GtexAdminMetric(
          label: 'Ingestion',
          value: 'Watch',
          delta: 'SportMonks queue check',
          severity: GtexAdminSeverity.watch,
        ),
      ],
      modules: [
        GtexAdminModule(
          type: GtexAdminModuleType.users,
          title: 'Users',
          description:
              'Accounts, roles, restrictions, onboarding, verification state.',
          countLabel: '18.4k',
        ),
        GtexAdminModule(
          type: GtexAdminModuleType.clubs,
          title: 'Clubs',
          description:
              'User-created clubs, public profiles, shares, squads, reputation.',
          countLabel: '3.1k',
        ),
        GtexAdminModule(
          type: GtexAdminModuleType.players,
          title: 'Players',
          description:
              'SportMonks players, images, market availability, orders.',
          countLabel: '8k+',
          severity: GtexAdminSeverity.watch,
        ),
        GtexAdminModule(
          type: GtexAdminModuleType.regens,
          title: 'Regens',
          description:
              'Regen universe, contracts, awards, create-a-son requests.',
          countLabel: '12.9k',
        ),
        GtexAdminModule(
          type: GtexAdminModuleType.kyc,
          title: 'KYC',
          description:
              'Identity queues, document review, audit history, escalation.',
          countLabel: '74',
          severity: GtexAdminSeverity.watch,
        ),
        GtexAdminModule(
          type: GtexAdminModuleType.orders,
          title: 'Orders',
          description:
              'Player purchases, rentals, refunds, failed payment follow-up.',
          countLabel: '319',
        ),
        GtexAdminModule(
          type: GtexAdminModuleType.disputes,
          title: 'Disputes',
          description: 'Case queues, evidence, refunds, support decisions.',
          countLabel: '11',
          severity: GtexAdminSeverity.warning,
        ),
        GtexAdminModule(
          type: GtexAdminModuleType.tournaments,
          title: 'Tournaments',
          description:
              'GTEX tournaments, user-hosted competitions, progress monitoring.',
          countLabel: '28 live',
        ),
        GtexAdminModule(
          type: GtexAdminModuleType.jackpot,
          title: 'Jackpot',
          description: 'Pools, draw status, winners, claims, fraud checks.',
          countLabel: '₵8.4M',
        ),
        GtexAdminModule(
          type: GtexAdminModuleType.coinEconomy,
          title: 'Coin Economy',
          description:
              'Top-ups, withdrawals, treasury, coin controls, anomaly checks.',
          countLabel: 'Stable',
        ),
        GtexAdminModule(
          type: GtexAdminModuleType.transferHub,
          title: 'Transfer Hub',
          description:
              'Loans, swaps, private bids, release clauses, and deadline controls.',
          countLabel: 'Gated',
        ),
        GtexAdminModule(
          type: GtexAdminModuleType.coinTraders,
          title: 'Coin Traders',
          description:
              'Liquidity partners, escrow windows, fiat order review, and disputes.',
          countLabel: 'Live',
        ),
        GtexAdminModule(
          type: GtexAdminModuleType.clubLifecycle,
          title: 'Club Lifecycle',
          description:
              'Readiness, squad registration, eligibility, and operating dashboards.',
          countLabel: 'Batch 24',
        ),
        GtexAdminModule(
          type: GtexAdminModuleType.staffMarketplace,
          title: 'Staff Marketplace',
          description:
              'Agents, managers, scouts, coaches, contracts, and assignments.',
          countLabel: 'Batch 25',
        ),
        GtexAdminModule(
          type: GtexAdminModuleType.academy,
          title: 'Academy Regens',
          description:
              'Academy generation, training plans, contracts, portraits, and promotion.',
          countLabel: 'Batch 26',
        ),
        GtexAdminModule(
          type: GtexAdminModuleType.sponsorships,
          title: 'Sponsorships',
          description:
              'Sponsor packages, brand assets, contract activation, and payouts.',
          countLabel: 'Batch 27',
        ),
        GtexAdminModule(
          type: GtexAdminModuleType.federations,
          title: 'Federations',
          description:
              'Federation rules, rankings, sanctions, and national eligibility.',
          countLabel: 'Batch 28',
        ),
        GtexAdminModule(
          type: GtexAdminModuleType.fanEconomy,
          title: 'Fan Economy',
          description:
              'Predictions, fan wars, gifts, Fan Coin rewards, and abuse controls.',
          countLabel: 'Batch 29',
        ),
        GtexAdminModule(
          type: GtexAdminModuleType.broadcast,
          title: 'Broadcast & Clips',
          description:
              'Rights, highlights, viral clips, sponsored media, and revenue share.',
          countLabel: 'Batch 30',
        ),
        GtexAdminModule(
          type: GtexAdminModuleType.ticketing,
          title: 'Ticketing',
          description:
              'Inventory, checkout, resale, attendance rewards, and stadium revenue.',
          countLabel: 'Batch 31',
        ),
        GtexAdminModule(
          type: GtexAdminModuleType.playerCards,
          title: 'Player Cards',
          description:
              'Collectible cards, packs, listings, offers, burn, and fuse.',
          countLabel: 'Batch 32',
        ),
        GtexAdminModule(
          type: GtexAdminModuleType.globalSearch,
          title: 'Global Search',
          description:
              'Role-aware search and notification matrix coverage across GTEX.',
          countLabel: 'Batch 33',
        ),
        GtexAdminModule(
          type: GtexAdminModuleType.newsroom,
          title: 'Newsroom',
          description:
              'AI news agency, announcements, editorial review, moderation.',
          countLabel: '42 drafts',
        ),
        GtexAdminModule(
          type: GtexAdminModuleType.launchControl,
          title: 'Launch Control',
          description:
              'Feature flags, rollout states, beta grants and kill switches.',
          countLabel: 'Batch 34',
          severity: GtexAdminSeverity.watch,
        ),
        GtexAdminModule(
          type: GtexAdminModuleType.operationsReadiness,
          title: 'Operations Readiness',
          description:
              'Diagnostics, ledger health, risk queues, launch gates, and workers.',
          countLabel: 'Live',
          severity: GtexAdminSeverity.watch,
        ),
        GtexAdminModule(
          type: GtexAdminModuleType.systemHealth,
          title: 'System Health',
          description: 'API, Render, ingestion, Redis, queues, deploy state.',
          countLabel: 'Watch',
          severity: GtexAdminSeverity.watch,
        ),
      ],
      queues: [
        GtexAdminQueueItem(
          id: 'kyc-1',
          title: 'KYC review: Ayo Daniels',
          subtitle: 'Identity submitted, address proof pending OCR check.',
          status: 'Pending review',
          createdAtLabel: '14 min ago',
          ownerLabel: 'KYC',
          severity: GtexAdminSeverity.watch,
        ),
        GtexAdminQueueItem(
          id: 'order-1',
          title: 'Large player purchase order',
          subtitle: 'Lagos Phoenix added 7 players to purchase basket.',
          status: 'Payment hold',
          createdAtLabel: '27 min ago',
          amountLabel: '₵4,820,000',
          ownerLabel: 'Orders',
          severity: GtexAdminSeverity.warning,
        ),
        GtexAdminQueueItem(
          id: 'dispute-1',
          title: 'Rental eligibility dispute',
          subtitle: 'National team rental conflict for U20 competition.',
          status: 'Evidence required',
          createdAtLabel: '38 min ago',
          ownerLabel: 'Disputes',
          severity: GtexAdminSeverity.warning,
        ),
        GtexAdminQueueItem(
          id: 'son-1',
          title: 'Create-a-son special request',
          subtitle: 'Custom personality + preferred position + premium naming.',
          status: 'Pricing needed',
          createdAtLabel: '1h ago',
          amountLabel: 'Premium',
          ownerLabel: 'Regens',
        ),
      ],
      jackpots: [
        GtexJackpotRound(
          id: 'jp-1',
          title: 'Weekend GTEX Jackpot',
          poolLabel: '₵8,400,000',
          status: 'Open',
          entriesLabel: '18,420 entries',
          drawTimeLabel: 'Draw in 2h 14m',
          winnerLabel: 'Pending draw',
        ),
        GtexJackpotRound(
          id: 'jp-2',
          title: 'National Cup Bonus Pool',
          poolLabel: '₵2,200,000',
          status: 'Claim review',
          entriesLabel: '4,820 entries',
          drawTimeLabel: 'Draw completed',
          winnerLabel: 'Kano Stars FC',
        ),
      ],
      coinEconomy: GtexCoinEconomySnapshot(
        circulatingSupply: '₵184.2M',
        treasuryBalance: '₵42.7M',
        pendingWithdrawals: '₵6.1M',
        topupVolumeToday: '₵18.9M',
        riskStatus: 'Stable',
      ),
      healthSignals: [
        GtexSystemHealthSignal(
          name: 'API',
          status: 'Online',
          detail: 'p95 184ms',
        ),
        GtexSystemHealthSignal(
          name: 'Web',
          status: 'Online',
          detail: 'latest build check required',
        ),
        GtexSystemHealthSignal(
          name: 'SportMonks ingestion',
          status: 'Watch',
          detail: 'queue and jobId health required',
          severity: GtexAdminSeverity.watch,
        ),
        GtexSystemHealthSignal(
          name: 'Redis/BullMQ',
          status: 'Watch',
          detail: 'policy must be noeviction',
          severity: GtexAdminSeverity.watch,
        ),
        GtexSystemHealthSignal(
          name: 'Payments',
          status: 'Online',
          detail: 'no abnormal failures',
        ),
      ],
    );
  }
}
