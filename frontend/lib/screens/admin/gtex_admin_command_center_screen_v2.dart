import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../features/admin_command_redesign/models/gtex_admin_command_models.dart';
import '../../features/admin_command_redesign/presentation/gtex_admin_command_controller.dart';
import '../../features/admin_command_redesign/widgets/gtex_admin_metric_grid.dart';
import '../../features/admin_command_redesign/widgets/gtex_admin_module_list.dart';
import '../../features/admin_command_redesign/widgets/gtex_admin_queue_panel.dart';
import '../../features/admin_command_redesign/widgets/gtex_admin_visuals.dart';
import '../../features/admin_command_redesign/widgets/gtex_coin_economy_panel.dart';
import '../../features/admin_command_redesign/widgets/gtex_jackpot_admin_panel.dart';
import '../../features/admin_command_redesign/widgets/gtex_system_health_panel.dart';
import '../../features/owner_console/data/owner_console_api.dart';
import '../../features/owner_console/widgets/owner_admin_review_section.dart';
import '../../ui_gtex/ui_gtex.dart';
import 'gtex_admin_newsroom_screen_v2.dart';

class GtexAdminCommandCenterScreenV2 extends StatefulWidget {
  const GtexAdminCommandCenterScreenV2({
    super.key,
    this.controller,
    this.ownerConsoleReader,
    this.canReviewOwnerQueue = true,
  });

  final GtexAdminCommandController? controller;
  final OwnerConsoleReader? ownerConsoleReader;
  final bool canReviewOwnerQueue;

  @override
  State<GtexAdminCommandCenterScreenV2> createState() =>
      _GtexAdminCommandCenterScreenV2State();
}

class _GtexAdminCommandCenterScreenV2State
    extends State<GtexAdminCommandCenterScreenV2> {
  GtexAdminCommandController? controller;

  @override
  void initState() {
    super.initState();
    controller = widget.controller;
  }

  @override
  void dispose() {
    controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    final GtexAdminCommandController? activeController = controller;
    if (activeController == null) {
      return Scaffold(
        backgroundColor: navy.bgBase,
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(
              'Live admin command data required. Use the production admin command center with authenticated API wiring.',
              textAlign: TextAlign.center,
              style: TextStyle(color: navy.textSecondary),
            ),
          ),
        ),
      );
    }
    return AnimatedBuilder(
      animation: activeController,
      builder: (context, _) {
        return Theme(
          data: Theme.of(context).copyWith(
            scaffoldBackgroundColor: navy.bgBase,
            textTheme: Theme.of(context).textTheme.apply(
              bodyColor: navy.textPrimary,
              displayColor: navy.textPrimary,
            ),
          ),
          child: Scaffold(
            backgroundColor: navy.bgBase,
            body: SafeArea(
              child: LayoutBuilder(
                builder: (context, constraints) {
                  final isWide = constraints.maxWidth >= 1100;
                  if (!isWide) {
                    return _MobileAdminCommand(
                      controller: activeController,
                      ownerConsoleReader: widget.ownerConsoleReader,
                      canReviewOwnerQueue: widget.canReviewOwnerQueue,
                    );
                  }

                  return Row(
                    children: [
                      SizedBox(
                        width: 360,
                        child: _LeftPanel(controller: activeController),
                      ),
                      Expanded(
                        child: _MainWorkspace(
                          controller: activeController,
                          ownerConsoleReader: widget.ownerConsoleReader,
                          canReviewOwnerQueue: widget.canReviewOwnerQueue,
                        ),
                      ),
                      SizedBox(
                        width: 360,
                        child: _RightPanel(controller: activeController),
                      ),
                    ],
                  );
                },
              ),
            ),
          ),
        );
      },
    );
  }
}

class _LeftPanel extends StatelessWidget {
  const _LeftPanel({required this.controller});

  final GtexAdminCommandController controller;

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    return Container(
      padding: const EdgeInsets.fromLTRB(18, 18, 12, 18),
      decoration: BoxDecoration(
        color: navy.bgRaised,
        border: Border(right: BorderSide(color: navy.lineSubtle)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'GTEX Admin',
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 4),
          Text('Command center', style: TextStyle(color: navy.textSecondary)),
          const SizedBox(height: 18),
          TextField(
            onChanged: controller.updateSearch,
            decoration: InputDecoration(
              hintText: 'Search modules, users, orders...',
              prefixIcon: const Icon(Icons.search_rounded),
              filled: true,
              fillColor: navy.bgInset,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(18),
                borderSide: BorderSide.none,
              ),
            ),
          ),
          const SizedBox(height: 16),
          Expanded(
            child: GtexAdminModuleList(
              modules: controller.modules,
              selected: controller.selectedModule,
              onSelected: controller.selectModule,
            ),
          ),
        ],
      ),
    );
  }
}

class _MainWorkspace extends StatelessWidget {
  const _MainWorkspace({
    required this.controller,
    this.ownerConsoleReader,
    this.canReviewOwnerQueue = true,
  });

  final GtexAdminCommandController controller;
  final OwnerConsoleReader? ownerConsoleReader;
  final bool canReviewOwnerQueue;

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    final snapshot = controller.snapshot;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(22),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          GtexAdminPanel(
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _titleFor(controller.selectedModule),
                        style: Theme.of(context).textTheme.headlineMedium
                            ?.copyWith(fontWeight: FontWeight.w900),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        _subtitleFor(controller.selectedModule),
                        style: TextStyle(color: navy.textSecondary),
                      ),
                    ],
                  ),
                ),
                const GtexAdminStatusPill(
                  label: 'Production aware',
                  severity: GtexAdminSeverity.watch,
                ),
                const SizedBox(width: 10),
                IconButton(
                  onPressed: controller.refresh,
                  icon: const Icon(Icons.refresh_rounded),
                  tooltip: 'Refresh admin snapshot',
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          GtexAdminMetricGrid(metrics: snapshot.metrics),
          const SizedBox(height: 16),
          if (controller.selectedModule == GtexAdminModuleType.jackpot)
            GtexJackpotAdminPanel(
              api: controller.jackpotAdminApi,
              rounds: snapshot.jackpots,
            )
          else if (controller.selectedModule == GtexAdminModuleType.coinEconomy)
            GtexCoinEconomyPanel(snapshot: snapshot.coinEconomy)
          else if (controller.selectedModule ==
              GtexAdminModuleType.systemHealth)
            GtexSystemHealthPanel(signals: snapshot.healthSignals)
          else if (controller.selectedModule == GtexAdminModuleType.newsroom)
            SizedBox(
              height: 720,
              child: GtexAdminNewsroomScreenV2(
                api: controller.storyFeedApi,
                embedded: true,
              ),
            )
          else
            GtexAdminQueuePanel(
              items: controller.queueItems,
              selectedItem: controller.selectedQueueItem,
              onSelected: controller.selectQueueItem,
              onApprove: controller.approveSelectedQueueItem,
              onEscalate: controller.escalateSelectedQueueItem,
              actionBusy: controller.actionLoading,
              actionMessage: controller.actionMessage,
              actionError: controller.actionError,
            ),
          if (ownerConsoleReader != null) ...[
            const SizedBox(height: 16),
            SizedBox(
              key: const Key('gtex-admin-owner-review-panel'),
              height: 520,
              child: AdminReviewSection(
                reader: ownerConsoleReader!,
                canReviewOwnerQueue: canReviewOwnerQueue,
              ),
            ),
          ],
          const SizedBox(height: 16),
          _OperationalPlaybook(module: controller.selectedModule),
        ],
      ),
    );
  }

  String _titleFor(GtexAdminModuleType type) {
    switch (type) {
      case GtexAdminModuleType.overview:
        return 'GTEX operational cockpit';
      case GtexAdminModuleType.jackpot:
        return 'Jackpot operations';
      case GtexAdminModuleType.coinEconomy:
        return 'Coin economy control';
      case GtexAdminModuleType.transferHub:
        return 'Transfer Hub operations';
      case GtexAdminModuleType.coinTraders:
        return 'Coin trader operations';
      case GtexAdminModuleType.clubLifecycle:
        return 'Club lifecycle operations';
      case GtexAdminModuleType.staffMarketplace:
        return 'Staff marketplace operations';
      case GtexAdminModuleType.academy:
        return 'Academy regen operations';
      case GtexAdminModuleType.sponsorships:
        return 'Sponsorship operations';
      case GtexAdminModuleType.federations:
        return 'Federation operations';
      case GtexAdminModuleType.fanEconomy:
        return 'Fan economy operations';
      case GtexAdminModuleType.broadcast:
        return 'Broadcast and clip operations';
      case GtexAdminModuleType.ticketing:
        return 'Ticketing operations';
      case GtexAdminModuleType.playerCards:
        return 'Player card operations';
      case GtexAdminModuleType.globalSearch:
        return 'Global search operations';
      case GtexAdminModuleType.operationsReadiness:
        return 'Operations readiness';
      case GtexAdminModuleType.systemHealth:
        return 'System health';
      case GtexAdminModuleType.launchControl:
        return 'Launch control';
      default:
        return '${type.name[0].toUpperCase()}${type.name.substring(1)} operations';
    }
  }

  String _subtitleFor(GtexAdminModuleType type) {
    switch (type) {
      case GtexAdminModuleType.jackpot:
        return 'Monitor the live pool, edit runtime settings, set balance, trigger settlement, and review winner history.';
      case GtexAdminModuleType.coinEconomy:
        return 'Control wallet risk, treasury balance, top-ups, withdrawals, ledger audits and coin supply.';
      case GtexAdminModuleType.transferHub:
        return 'Review transfer listings, swaps, loans, release clauses, payment state and disputes.';
      case GtexAdminModuleType.coinTraders:
        return 'Watch liquidity partners, escrow windows, fiat confirmation, disputes and risk checks.';
      case GtexAdminModuleType.clubLifecycle:
        return 'Monitor readiness, squad registration, eligibility blockers and club operating dashboards.';
      case GtexAdminModuleType.staffMarketplace:
        return 'Track staff contracts, commissions, assignments, performance logs and disputes.';
      case GtexAdminModuleType.academy:
        return 'Review academy generation, prospects, contracts, training plans, portraits and promotions.';
      case GtexAdminModuleType.sponsorships:
        return 'Moderate sponsor packages, brand assets, contracts, performance and payout queues.';
      case GtexAdminModuleType.federations:
        return 'Control federation rules, votes, sanctions, rankings and national eligibility oversight.';
      case GtexAdminModuleType.fanEconomy:
        return 'Watch predictions, fan wars, gifts, rewards, leaderboards and anti-abuse signals.';
      case GtexAdminModuleType.broadcast:
        return 'Operate rights, highlights, clip moderation, sponsored clips and creator revenue.';
      case GtexAdminModuleType.ticketing:
        return 'Inspect inventory, checkout, resale, attendance rewards and stadium revenue.';
      case GtexAdminModuleType.playerCards:
        return 'Monitor card templates, packs, listings, offers, burn/fuse and fraud reviews.';
      case GtexAdminModuleType.globalSearch:
        return 'Validate role-aware search, notification deep links, and command route discovery.';
      case GtexAdminModuleType.systemHealth:
        return 'Monitor Render deploy sync, API health, ingestion workers, Redis policy and queue safety.';
      case GtexAdminModuleType.launchControl:
        return 'Gate new GTEX modules with launch states, beta access grants, maintenance mode and kill switches.';
      default:
        return 'Review live queues, act on flagged items, and keep GTEX operations moving.';
    }
  }
}

class _RightPanel extends StatelessWidget {
  const _RightPanel({required this.controller});

  final GtexAdminCommandController controller;

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 18, 18, 18),
      decoration: BoxDecoration(
        color: navy.bgRaised,
        border: Border(left: BorderSide(color: navy.lineSubtle)),
      ),
      child: Column(
        children: [
          GtexAdminPanel(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const GtexAdminSectionHeader(
                  title: 'Critical controls',
                  subtitle:
                      'Restricted admin actions. Wired to existing permission checks.',
                ),
                const SizedBox(height: 14),
                _QuickControl(
                  label: 'Freeze wallet',
                  icon: Icons.lock_rounded,
                  route: '/admin/trust-ops',
                ),
                _QuickControl(
                  label: 'Pause jackpot draw',
                  icon: Icons.pause_circle_rounded,
                  route: '/admin/launch-control',
                ),
                _QuickControl(
                  label: 'Publish announcement',
                  icon: Icons.campaign_rounded,
                  route: '/admin/notifications',
                ),
                _QuickControl(
                  label: 'Open system health',
                  icon: Icons.monitor_heart_rounded,
                  route: '/admin/launch-control',
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          Expanded(
            child: GtexAdminPanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const GtexAdminSectionHeader(title: 'Health watch'),
                  const SizedBox(height: 12),
                  Expanded(
                    child: ListView(
                      children:
                          controller.snapshot.healthSignals
                              .map(
                                (signal) => Padding(
                                  padding: const EdgeInsets.only(bottom: 10),
                                  child: Row(
                                    children: [
                                      Icon(
                                        Icons.circle,
                                        size: 10,
                                        color: gtexAdminSeverityColor(
                                          signal.severity,
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      Expanded(
                                        child: Text(
                                          signal.name,
                                          style: const TextStyle(
                                            fontWeight: FontWeight.w800,
                                          ),
                                        ),
                                      ),
                                      GtexAdminStatusPill(
                                        label: signal.status,
                                        severity: signal.severity,
                                      ),
                                    ],
                                  ),
                                ),
                              )
                              .toList(),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _QuickControl extends StatelessWidget {
  const _QuickControl({
    required this.label,
    required this.icon,
    required this.route,
  });

  final String label;
  final IconData icon;
  final String route;

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    return Container(
      margin: const EdgeInsets.only(bottom: 9),
      child: OutlinedButton.icon(
        onPressed: () => context.go(route),
        icon: Icon(icon, size: 18),
        label: Align(alignment: Alignment.centerLeft, child: Text(label)),
        style: OutlinedButton.styleFrom(
          foregroundColor: navy.textPrimary,
          side: BorderSide(color: navy.lineSubtle),
          padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
        ),
      ),
    );
  }
}

class _OperationalPlaybook extends StatelessWidget {
  const _OperationalPlaybook({required this.module});

  final GtexAdminModuleType module;

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    return GtexAdminPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const GtexAdminSectionHeader(
            title: 'Operational playbook',
            subtitle: 'Route-safe notes for production integration.',
          ),
          const SizedBox(height: 12),
          Text(
            _copyFor(module),
            style: TextStyle(color: navy.textSecondary, height: 1.45),
          ),
        ],
      ),
    );
  }

  String _copyFor(GtexAdminModuleType module) {
    switch (module) {
      case GtexAdminModuleType.jackpot:
        return 'Live controls use GET/POST /api/admin/jackpot/runtime, PATCH /api/admin/jackpot/balance, POST /api/admin/jackpot/trigger, and GET /api/jackpot/history. Manual trigger settles the current round immediately.';
      case GtexAdminModuleType.coinEconomy:
        return 'Wire coin controls to wallet, ledger, withdrawal, treasury, and anomaly APIs. Every action should create an audit trail.';
      case GtexAdminModuleType.systemHealth:
        return 'Connect to /api/build-info, ingestion health, Redis policy, queue health, Render deploy state and smoke-test results.';
      case GtexAdminModuleType.launchControl:
        return 'Use the Batch 34 launch-control APIs as the canonical rollout surface. Do not create parallel flags outside AdminFeatureFlag.';
      default:
        return 'Connect each queue item to existing admin screens first. This command center should summarize and deep-link, not duplicate all admin business logic.';
    }
  }
}

class _MobileAdminCommand extends StatelessWidget {
  const _MobileAdminCommand({
    required this.controller,
    this.ownerConsoleReader,
    this.canReviewOwnerQueue = true,
  });

  final GtexAdminCommandController controller;
  final OwnerConsoleReader? ownerConsoleReader;
  final bool canReviewOwnerQueue;

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    final snapshot = controller.snapshot;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text(
          'GTEX Admin',
          style: TextStyle(fontSize: 26, fontWeight: FontWeight.w900),
        ),
        const SizedBox(height: 4),
        Text('Command center', style: TextStyle(color: navy.textSecondary)),
        const SizedBox(height: 16),
        GtexAdminModuleList(
          modules: controller.modules,
          selected: controller.selectedModule,
          onSelected: controller.selectModule,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
        ),
        const SizedBox(height: 16),
        GtexAdminMetricGrid(metrics: snapshot.metrics),
        const SizedBox(height: 16),
        GtexAdminQueuePanel(
          items: controller.queueItems,
          selectedItem: controller.selectedQueueItem,
          onSelected: controller.selectQueueItem,
          onApprove: controller.approveSelectedQueueItem,
          onEscalate: controller.escalateSelectedQueueItem,
          actionBusy: controller.actionLoading,
          actionMessage: controller.actionMessage,
          actionError: controller.actionError,
        ),
        if (ownerConsoleReader != null) ...[
          const SizedBox(height: 16),
          SizedBox(
            key: const Key('gtex-admin-owner-review-panel'),
            height: 480,
            child: AdminReviewSection(
              reader: ownerConsoleReader!,
              canReviewOwnerQueue: canReviewOwnerQueue,
            ),
          ),
        ],
      ],
    );
  }
}
