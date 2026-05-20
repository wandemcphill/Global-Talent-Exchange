import 'package:flutter/material.dart';

import '../data/gte_models.dart';
import '../providers/gte_exchange_controller.dart';
import '../shared/widgets/gtex_premium_panels.dart';
import '../widgets/gte_formatters.dart';
import '../widgets/gte_metric_chip.dart';
import '../widgets/gte_order_detail_card.dart';
import '../widgets/gte_shell_theme.dart';
import '../widgets/gte_sync_status_card.dart';
import '../widgets/gte_state_panel.dart';
import '../widgets/gte_surface_panel.dart';
import '../widgets/gte_wallet_summary_card.dart';
import '../widgets/gtex_branding.dart';
import 'notifications/gte_notifications_screen.dart';
import 'support/gte_support_dispute_screens.dart';
import 'wallet/gte_deposit_history_screen.dart';
import 'wallet/gte_funding_flow_screen.dart';
import 'wallet/gte_wallet_overview_screen.dart';
import 'wallet/gte_withdrawal_flow_screen.dart';

class GtePortfolioScreen extends StatelessWidget {
  const GtePortfolioScreen({
    super.key,
    required this.controller,
    required this.onOpenPlayer,
    required this.onOpenLogin,
  });

  final GteExchangeController controller;
  final ValueChanged<String> onOpenPlayer;
  final VoidCallback onOpenLogin;

  @override
  Widget build(BuildContext context) {
    if (!controller.isAuthenticated) {
      return ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
        children: <Widget>[
          GtexHeroBanner(
            eyebrow: 'CAPITAL DESK',
            title: 'Your club funds stay protected until you sign in.',
            description:
                'Visitor mode shows the layout, not live balances. Sign in to view your balance, player holdings, and account history.',
            accent: GteShellTheme.accentCapital,
            chips: const <Widget>[
              GteMetricChip(label: 'Mode', value: 'VISITOR'),
              GteMetricChip(label: 'Balance', value: 'LOCKED'),
              GteMetricChip(label: 'Activity', value: 'PRIVATE'),
            ],
            actions: <Widget>[
              FilledButton(
                onPressed: onOpenLogin,
                child: const Text('Sign in'),
              ),
            ],
          ),
          const SizedBox(height: 20),
          const GteStatePanel(
            title: 'Protected account area',
            message:
                'Funds, holdings, and account history are protected. Sign in to continue.',
            icon: Icons.lock_outline,
          ),
        ],
      );
    }

    return RefreshIndicator(
      onRefresh: controller.refreshAccount,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            GtexHeroBanner(
              eyebrow: 'CAPITAL DESK',
              title:
                  'Capital, holdings, and live transfer pressure sit on one executive board.',
              description:
                  'This is the money room for your club. Check deployable capital, active exposure, and pending moves without losing the premium football-trading feel.',
              accent: GteShellTheme.accentCapital,
              chips: <Widget>[
                GteMetricChip(
                  label: 'Holdings',
                  value:
                      (controller.portfolio?.holdings.length ?? 0).toString(),
                ),
                GteMetricChip(
                  label: 'Open orders',
                  value: controller.openOrders.length.toString(),
                ),
                GteMetricChip(
                  label: 'Recent orders',
                  value: controller.recentOrders.length.toString(),
                ),
              ],
              sidePanel: Column(
                children: <Widget>[
                  _CapitalSignalRow(
                    leftLabel: 'Balance',
                    leftValue:
                        controller.walletSummary == null ? 'SYNCING' : 'READY',
                    rightLabel: 'Pending moves',
                    rightValue:
                        controller.openOrders.isEmpty ? 'QUIET' : 'ACTIVE',
                  ),
                  const SizedBox(height: 12),
                  _CapitalSignalRow(
                    leftLabel: 'Players held',
                    leftValue: '${controller.portfolio?.holdings.length ?? 0}',
                    rightLabel: 'Status',
                    rightValue:
                        controller.portfolioSummary == null ? 'WAIT' : 'CLEAR',
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
            GtexLiveTickerBar(
              accentColor: GteShellTheme.accentCapital,
              items: <String>[
                if (controller.walletSummary == null)
                  'Capital desk is calibrating live balances and exposure',
                if (controller.walletSummary != null)
                  'Wallet balance is ${gteFormatCredits(controller.walletSummary!.totalBalance)} and ready for deployment',
                if (controller.openOrders.isNotEmpty)
                  '${controller.openOrders.length} pending capital moves are still working through the market',
                if (controller.recentOrders.isNotEmpty)
                  '${controller.recentOrders.length} recent executions are feeding the account tape',
              ],
            ),
            if (controller.portfolioError != null &&
                (controller.walletSummary != null ||
                    controller.portfolio != null ||
                    controller.portfolioSummary != null)) ...<Widget>[
              const SizedBox(height: 20),
              _InlineAccountNotice(
                icon: Icons.warning_amber_rounded,
                message:
                    'Some account data may be stale. ${controller.portfolioError!}',
              ),
            ],
            if (controller.ordersError != null &&
                controller.recentOrders.isNotEmpty) ...<Widget>[
              const SizedBox(height: 20),
              _InlineAccountNotice(
                icon: Icons.warning_amber_rounded,
                message:
                    'Order history refresh failed. Showing the latest successful order snapshot instead.',
              ),
            ],
            const SizedBox(height: 20),
            GteSyncStatusCard(
              title: 'Account sync',
              status:
                  controller.isAuthenticated
                      ? 'Balance, holdings, and move history are updating together.'
                      : 'Visitor mode is active. Sign in to unlock capital and live account updates.',
              syncedAt:
                  controller.portfolioSyncedAt ?? controller.ordersSyncedAt,
              accent: GteShellTheme.accentCapital,
              isRefreshing:
                  controller.isLoadingPortfolio || controller.isLoadingOrders,
              onRefresh:
                  controller.isAuthenticated
                      ? controller.refreshAccount
                      : onOpenLogin,
            ),
            const SizedBox(height: 20),
            if (controller.walletSummary != null) ...<Widget>[
              GteWalletSummaryCard(summary: controller.walletSummary!),
              const SizedBox(height: 20),
              _CapitalBreakdownCard(
                walletSummary: controller.walletSummary!,
                portfolioSummary: controller.portfolioSummary,
                openOrderCount: controller.openOrders.length,
              ),
              const SizedBox(height: 20),
              _WalletActionPanel(controller: controller),
            ] else if (controller.isLoadingPortfolio)
              const _LoadingCard(title: 'Wallet summary')
            else
              const GteStatePanel(
                title: 'Wallet unavailable',
                message:
                    'Wallet balances could not be loaded for this session.',
                icon: Icons.account_balance_wallet_outlined,
              ),
            const SizedBox(height: 20),
            if (controller.portfolioSummary != null)
              _PortfolioSummaryCard(
                summary: controller.portfolioSummary!,
                holdingCount: controller.portfolio?.holdings.length ?? 0,
              )
            else if (controller.isLoadingPortfolio)
              const _LoadingCard(title: 'Portfolio summary')
            else
              const GteStatePanel(
                title: 'Portfolio summary unavailable',
                message: 'The account summary endpoint did not return data.',
                icon: Icons.analytics_outlined,
              ),
            const SizedBox(height: 20),
            if (controller.portfolioError != null &&
                controller.portfolio == null)
              GteStatePanel(
                title: 'Portfolio unavailable',
                message: controller.portfolioError!,
                actionLabel: 'Retry',
                onAction: controller.refreshAccount,
                icon: Icons.warning_amber_rounded,
              )
            else if (controller.isLoadingPortfolio &&
                controller.portfolio == null)
              const _LoadingCard(title: 'Holdings')
            else if (controller.portfolio == null ||
                controller.portfolio!.holdings.isEmpty)
              const GteStatePanel(
                title: 'Capital is waiting for its first move',
                message:
                    'Your balance is live, but no player positions are open yet. The first signed asset will turn this desk into a real portfolio.',
                icon: Icons.account_balance_wallet_outlined,
              )
            else
              _HoldingsCard(
                controller: controller,
                portfolio: controller.portfolio!,
                onOpenPlayer: onOpenPlayer,
              ),
            const SizedBox(height: 20),
            _OrdersPanel(controller: controller, onOpenPlayer: onOpenPlayer),
          ],
        ),
      ),
    );
  }
}

class _PortfolioSummaryCard extends StatelessWidget {
  const _PortfolioSummaryCard({
    required this.summary,
    required this.holdingCount,
  });

  final GtePortfolioSummary summary;
  final int holdingCount;

  @override
  Widget build(BuildContext context) {
    final double deployedRatio =
        summary.totalEquity <= 0
            ? 0
            : (summary.totalMarketValue / summary.totalEquity).clamp(0, 1);
    final Color plColor =
        summary.unrealizedPlTotal >= 0
            ? GteShellTheme.positive
            : GteShellTheme.negative;

    return GteSurfacePanel(
      accentColor: GteShellTheme.accentCapital,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Ownership summary',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 14),
          Row(
            children: <Widget>[
              Expanded(
                flex: 3,
                child: Container(
                  padding: const EdgeInsets.all(18),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(24),
                    color: Colors.white.withValues(alpha: 0.03),
                    border: Border.all(
                      color: Colors.white.withValues(alpha: 0.08),
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Total equity',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        gteFormatCredits(summary.totalEquity),
                        style: Theme.of(
                          context,
                        ).textTheme.displaySmall?.copyWith(fontSize: 28),
                      ),
                      const SizedBox(height: 14),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(999),
                        child: LinearProgressIndicator(
                          value: deployedRatio,
                          minHeight: 10,
                          backgroundColor: Colors.white.withValues(alpha: 0.06),
                          valueColor: const AlwaysStoppedAnimation<Color>(
                            GteShellTheme.accentCapital,
                          ),
                        ),
                      ),
                      const SizedBox(height: 10),
                      Text(
                        'Capital deployed into active positions: ${(deployedRatio * 100).toStringAsFixed(0)}%',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                flex: 2,
                child: Container(
                  padding: const EdgeInsets.all(18),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(24),
                    color: plColor.withValues(alpha: 0.1),
                    border: Border.all(color: plColor.withValues(alpha: 0.22)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Unrealized P/L',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        gteFormatCredits(summary.unrealizedPlTotal),
                        style: Theme.of(
                          context,
                        ).textTheme.titleLarge?.copyWith(color: plColor),
                      ),
                      const SizedBox(height: 14),
                      Text(
                        'Realized P/L',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        gteFormatCredits(summary.realizedPlTotal),
                        style: Theme.of(
                          context,
                        ).textTheme.titleMedium?.copyWith(
                          color:
                              summary.realizedPlTotal >= 0
                                  ? GteShellTheme.positive
                                  : GteShellTheme.negative,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              GteMetricChip(
                label: 'Market value',
                value: gteFormatCredits(summary.totalMarketValue),
              ),
              GteMetricChip(
                label: 'GTEX Coin',
                value: gteFormatCredits(summary.cashBalance),
              ),
              GteMetricChip(label: 'Positions', value: holdingCount.toString()),
              GteMetricChip(
                label: 'Club posture',
                value: holdingCount == 0 ? 'GTEX HEAVY' : 'BALANCED',
                positive: holdingCount > 0,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _HoldingsCard extends StatelessWidget {
  const _HoldingsCard({
    required this.controller,
    required this.portfolio,
    required this.onOpenPlayer,
  });

  final GteExchangeController controller;
  final GtePortfolioView portfolio;
  final ValueChanged<String> onOpenPlayer;

  @override
  Widget build(BuildContext context) {
    final double totalValue = portfolio.holdings.fold<double>(
      0,
      (double sum, GtePortfolioHolding holding) => sum + holding.marketValue,
    );
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Holdings', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 8),
          Text(
            'Latest revalued positions with mark, unrealized performance, and squad-level allocation weight.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          ...portfolio.holdings.map((GtePortfolioHolding holding) {
            final double share =
                totalValue <= 0
                    ? 0
                    : (holding.marketValue / totalValue).clamp(0, 1);
            final Color tone =
                holding.unrealizedPl >= 0
                    ? GteShellTheme.positive
                    : GteShellTheme.negative;
            return Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: GteSurfacePanel(
                padding: const EdgeInsets.all(16),
                onTap: () => onOpenPlayer(holding.playerId),
                accentColor: tone,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Text(
                                controller.playerLabel(holding.playerId),
                                style: Theme.of(context).textTheme.titleLarge,
                              ),
                              const SizedBox(height: 6),
                              Text(
                                'Qty ${holding.quantity.toStringAsFixed(2)} - Avg ${gteFormatCredits(holding.averageCost)} - Mark ${gteFormatCredits(holding.currentPrice)}',
                                style: Theme.of(context).textTheme.bodyMedium,
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 16),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: <Widget>[
                            Text(
                              gteFormatCredits(holding.marketValue),
                              style: Theme.of(context).textTheme.titleLarge,
                            ),
                            const SizedBox(height: 6),
                            Text(
                              gteFormatCredits(holding.unrealizedPl),
                              style: Theme.of(
                                context,
                              ).textTheme.labelLarge?.copyWith(color: tone),
                            ),
                          ],
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    Row(
                      children: List<Widget>.generate(
                        4,
                        (int index) => Expanded(
                          child: Container(
                            height: 5,
                            margin: EdgeInsets.only(right: index == 3 ? 0 : 6),
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(999),
                              color:
                                  index < ((share * 4).ceil().clamp(1, 4))
                                      ? tone.withValues(
                                        alpha: 0.9 - (index * 0.14),
                                      )
                                      : Colors.white.withValues(alpha: 0.08),
                            ),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(999),
                      child: LinearProgressIndicator(
                        value: share,
                        minHeight: 8,
                        backgroundColor: Colors.white.withValues(alpha: 0.06),
                        valueColor: AlwaysStoppedAnimation<Color>(tone),
                      ),
                    ),
                    const SizedBox(height: 10),
                    Text(
                      'Allocation weight ${(share * 100).toStringAsFixed(0)}% of marked holdings.',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: <Widget>[
                        GteMetricChip(
                          label: 'Unrealized %',
                          value: gteFormatMovement(
                            holding.unrealizedPlPercent / 100,
                          ),
                          positive: holding.unrealizedPlPercent >= 0,
                        ),
                        GteMetricChip(
                          label: 'Cost basis',
                          value: gteFormatCredits(
                            holding.averageCost * holding.quantity,
                          ),
                        ),
                        GteMetricChip(
                          label: 'Position health',
                          value:
                              holding.unrealizedPl >= 0
                                  ? 'IN GREEN'
                                  : 'UNDER WATER',
                          positive: holding.unrealizedPl >= 0,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            );
          }),
        ],
      ),
    );
  }
}

enum _OrdersPanelMode { open, recent }

class _OrdersPanel extends StatefulWidget {
  const _OrdersPanel({required this.controller, required this.onOpenPlayer});

  final GteExchangeController controller;
  final ValueChanged<String> onOpenPlayer;

  @override
  State<_OrdersPanel> createState() => _OrdersPanelState();
}

class _OrdersPanelState extends State<_OrdersPanel> {
  _OrdersPanelMode _mode = _OrdersPanelMode.open;

  @override
  Widget build(BuildContext context) {
    final GteExchangeController controller = widget.controller;
    final List<GteOrderRecord> openOrders = controller.openOrders;
    final List<GteOrderRecord> recentClosedOrders = controller.recentOrders
        .where((GteOrderRecord order) => !order.canCancel)
        .toList(growable: false);
    final _OrdersPanelMode effectiveMode =
        _mode == _OrdersPanelMode.recent && recentClosedOrders.isNotEmpty
            ? _OrdersPanelMode.recent
            : _OrdersPanelMode.open;
    final bool showOpenView = effectiveMode == _OrdersPanelMode.open;
    final List<GteOrderRecord> visibleOrders =
        showOpenView ? openOrders : recentClosedOrders;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        GteSurfacePanel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Expanded(
                    child: Text(
                      'Open and recent orders',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                  ),
                  FilledButton.tonalIcon(
                    onPressed:
                        controller.isLoadingOrders
                            ? null
                            : controller.loadOrders,
                    icon: const Icon(Icons.sync),
                    label: const Text('Refresh orders'),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              Text(
                'Money states should be readable at a glance: reserved, filled, cancelled, and still working.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 16),
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: <Widget>[
                  GteMetricChip(
                    label: 'Working',
                    value: openOrders.length.toString(),
                    positive: openOrders.isNotEmpty,
                  ),
                  GteMetricChip(
                    label: 'Settled',
                    value: recentClosedOrders.length.toString(),
                  ),
                  GteMetricChip(
                    label: 'State key',
                    value: showOpenView ? 'RESERVE LIVE' : 'LEDGER VIEW',
                    positive: showOpenView,
                  ),
                ],
              ),
              const SizedBox(height: 16),
              const _LedgerLegendRow(),
              const SizedBox(height: 16),
              SegmentedButton<_OrdersPanelMode>(
                segments: const <ButtonSegment<_OrdersPanelMode>>[
                  ButtonSegment<_OrdersPanelMode>(
                    value: _OrdersPanelMode.open,
                    label: Text('Open orders'),
                  ),
                  ButtonSegment<_OrdersPanelMode>(
                    value: _OrdersPanelMode.recent,
                    label: Text('Recent ledger'),
                  ),
                ],
                selected: <_OrdersPanelMode>{effectiveMode},
                onSelectionChanged: (Set<_OrdersPanelMode> selection) {
                  setState(() {
                    _mode = selection.first;
                  });
                },
              ),
              const SizedBox(height: 16),
              if (controller.ordersError != null &&
                  controller.recentOrders.isEmpty)
                GteStatePanel(
                  title: 'Orders unavailable',
                  message: controller.ordersError!,
                  actionLabel: 'Retry',
                  onAction: controller.loadOrders,
                  icon: Icons.receipt_long_outlined,
                )
              else if (controller.isLoadingOrders &&
                  controller.recentOrders.isEmpty &&
                  controller.openOrders.isEmpty)
                const _LoadingCard(title: 'Order ledger')
              else if (visibleOrders.isEmpty)
                GteStatePanel(
                  title: showOpenView ? 'No open orders' : 'No recent orders',
                  message:
                      showOpenView
                          ? 'Working orders will appear here with reserve and execution state.'
                          : 'Filled, cancelled, and closed order history will appear here once activity starts.',
                  icon: Icons.receipt_long_outlined,
                )
              else
                ...visibleOrders.map(
                  (GteOrderRecord order) => Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: GteOrderDetailCard(
                      order: order,
                      playerLabel: controller.playerLabel(order.playerId),
                      isRefreshing: controller.isRefreshingOrder,
                      isCancelling: controller.isCancellingOrder,
                      onRefresh: () => controller.refreshOrder(order.id),
                      onCancel: () => controller.cancelOrder(order.id),
                      showPlayerLabel: true,
                    ),
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }
}

class _CapitalBreakdownCard extends StatelessWidget {
  const _CapitalBreakdownCard({
    required this.walletSummary,
    required this.portfolioSummary,
    required this.openOrderCount,
  });

  final GteWalletSummary walletSummary;
  final GtePortfolioSummary? portfolioSummary;
  final int openOrderCount;

  @override
  Widget build(BuildContext context) {
    final double totalAccountValue =
        (portfolioSummary?.totalEquity ?? 0) > 0
            ? portfolioSummary!.totalEquity
            : walletSummary.totalBalance;
    final double reserveRatio =
        totalAccountValue <= 0
            ? 0
            : (walletSummary.reservedBalance / totalAccountValue).clamp(0, 1);
    final double exposureRatio =
        totalAccountValue <= 0 || portfolioSummary == null
            ? 0
            : (portfolioSummary!.totalMarketValue / totalAccountValue).clamp(
              0,
              1,
            );
    return GteSurfacePanel(
      accentColor: GteShellTheme.accentCapital,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Capital breakdown',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 8),
          Text(
            'Available cash, reserved order funds, and invested exposure are separated here so the money story is easy to trust.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          _CapitalLane(
            label: 'Available cash',
            value: gteFormatCredits(walletSummary.availableBalance),
            ratio:
                totalAccountValue <= 0
                    ? 0
                    : (walletSummary.availableBalance / totalAccountValue)
                        .clamp(0, 1),
            tone: GteShellTheme.accentCapital,
            note:
                walletSummary.availableBalance > 0
                    ? 'Ready for new orders.'
                    : 'No free cash currently available.',
          ),
          const SizedBox(height: 12),
          _CapitalLane(
            label: 'Reserved by open orders',
            value: gteFormatCredits(walletSummary.reservedBalance),
            ratio: reserveRatio,
            tone: GteShellTheme.accentWarm,
            note:
                openOrderCount > 0
                    ? '$openOrderCount working orders are holding this cash.'
                    : 'No active reserve holds right now.',
          ),
          const SizedBox(height: 12),
          _CapitalLane(
            label: 'Invested exposure',
            value: gteFormatCredits(portfolioSummary?.totalMarketValue ?? 0),
            ratio: exposureRatio,
            tone: GteShellTheme.accent,
            note:
                portfolioSummary == null
                    ? 'Portfolio exposure is still syncing.'
                    : 'Marked value of current holdings.',
          ),
        ],
      ),
    );
  }
}

class _CapitalLane extends StatelessWidget {
  const _CapitalLane({
    required this.label,
    required this.value,
    required this.ratio,
    required this.tone,
    required this.note,
  });

  final String label;
  final String value;
  final double ratio;
  final Color tone;
  final String note;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        color: Colors.white.withValues(alpha: 0.03),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text(
                  label,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              Text(
                value,
                style: Theme.of(
                  context,
                ).textTheme.titleMedium?.copyWith(color: tone),
              ),
            ],
          ),
          const SizedBox(height: 10),
          ClipRRect(
            borderRadius: BorderRadius.circular(999),
            child: LinearProgressIndicator(
              value: ratio,
              minHeight: 8,
              backgroundColor: Colors.white.withValues(alpha: 0.06),
              valueColor: AlwaysStoppedAnimation<Color>(tone),
            ),
          ),
          const SizedBox(height: 8),
          Text(note, style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
    );
  }
}

class _LedgerLegendRow extends StatelessWidget {
  const _LedgerLegendRow();

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 12,
      runSpacing: 12,
      children: const <Widget>[
        _LedgerLegendChip(
          label: 'Open',
          tone: GteShellTheme.accent,
          note: 'Funds may still be reserved.',
        ),
        _LedgerLegendChip(
          label: 'Partial',
          tone: GteShellTheme.accentWarm,
          note: 'A slice has executed.',
        ),
        _LedgerLegendChip(
          label: 'Filled',
          tone: GteShellTheme.positive,
          note: 'Settled into holdings or cash.',
        ),
        _LedgerLegendChip(
          label: 'Cancelled/Rejected',
          tone: GteShellTheme.negative,
          note: 'Reserve should unwind.',
        ),
      ],
    );
  }
}

class _LedgerLegendChip extends StatelessWidget {
  const _LedgerLegendChip({
    required this.label,
    required this.tone,
    required this.note,
  });

  final String label;
  final Color tone;
  final String note;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        color: tone.withValues(alpha: 0.12),
        border: Border.all(color: tone.withValues(alpha: 0.22)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            label,
            style: Theme.of(
              context,
            ).textTheme.labelLarge?.copyWith(color: tone),
          ),
          const SizedBox(height: 4),
          Text(note, style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
    );
  }
}

class _InlineAccountNotice extends StatelessWidget {
  const _InlineAccountNotice({required this.icon, required this.message});

  final IconData icon;
  final String message;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      padding: const EdgeInsets.all(16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(icon),
          const SizedBox(width: 12),
          Expanded(
            child: Text(message, style: Theme.of(context).textTheme.bodyMedium),
          ),
        ],
      ),
    );
  }
}

class _LoadingCard extends StatelessWidget {
  const _LoadingCard({required this.title});

  final String title;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 16),
          const LinearProgressIndicator(),
        ],
      ),
    );
  }
}

class _WalletActionPanel extends StatelessWidget {
  const _WalletActionPanel({required this.controller});

  final GteExchangeController controller;

  @override
  Widget build(BuildContext context) {
    final GteComplianceStatus? compliance = controller.complianceStatus;
    final bool fundWalletBlocked = compliance != null && !compliance.canDeposit;
    return GteSurfacePanel(
      emphasized: true,
      accentColor: GteShellTheme.accentCapital,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Wallet actions',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 12),
          if (fundWalletBlocked) ...<Widget>[
            Text(
              'Funding is locked until compliance review completes. Open Wallet overview for the current restriction and next steps.',
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: GteShellTheme.accentWarm),
            ),
            const SizedBox(height: 12),
          ],
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              OutlinedButton.icon(
                onPressed: () {
                  Navigator.of(context).push<void>(
                    MaterialPageRoute<void>(
                      builder:
                          (BuildContext context) =>
                              GteNotificationsScreen(controller: controller),
                    ),
                  );
                },
                icon: const Icon(Icons.notifications_outlined),
                label: const Text('Notifications'),
              ),
              OutlinedButton.icon(
                onPressed: () {
                  Navigator.of(context).push<void>(
                    MaterialPageRoute<void>(
                      builder:
                          (BuildContext context) =>
                              GteDisputeHubScreen(controller: controller),
                    ),
                  );
                },
                icon: const Icon(Icons.support_agent_outlined),
                label: const Text('Support'),
              ),
            ],
          ),
          const SizedBox(height: 12),
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final bool stacked = constraints.maxWidth < 720;
              final double tileWidth =
                  stacked
                      ? constraints.maxWidth
                      : (constraints.maxWidth - 12) / 2;
              return Wrap(
                spacing: 12,
                runSpacing: 12,
                children: <Widget>[
                  SizedBox(
                    width: tileWidth,
                    child: _WalletActionTile(
                      title: 'Wallet overview',
                      detail:
                          'Open balances, rails, and compliance posture in one place.',
                      icon: Icons.account_balance_wallet_outlined,
                      accent: GteShellTheme.accentCapital,
                      emphasized: true,
                      onTap: () {
                        Navigator.of(context).push<void>(
                          MaterialPageRoute<void>(
                            builder:
                                (BuildContext context) =>
                                    GteWalletOverviewScreen(
                                      controller: controller,
                                    ),
                          ),
                        );
                      },
                    ),
                  ),
                  SizedBox(
                    width: tileWidth,
                    child: _WalletActionTile(
                      title: 'Fund wallet',
                      detail:
                          fundWalletBlocked
                              ? 'Compliance review must clear before fresh deposits open.'
                              : 'Load GTEX Coin and keep transfer capital ready.',
                      icon: Icons.add_card_outlined,
                      accent: GteShellTheme.accent,
                      enabled: !fundWalletBlocked,
                      onTap:
                          fundWalletBlocked
                              ? null
                              : () {
                                Navigator.of(context).push<void>(
                                  MaterialPageRoute<void>(
                                    builder:
                                        (BuildContext context) =>
                                            GteFundWalletScreen(
                                              controller: controller,
                                            ),
                                  ),
                                );
                              },
                    ),
                  ),
                  SizedBox(
                    width: tileWidth,
                    child: _WalletActionTile(
                      title: 'Withdraw',
                      detail:
                          'Move settled GTEX Coin out through the live withdrawal lane.',
                      icon: Icons.payments_outlined,
                      accent: GteShellTheme.accentWarm,
                      onTap: () {
                        Navigator.of(context).push<void>(
                          MaterialPageRoute<void>(
                            builder:
                                (BuildContext context) =>
                                    GteWithdrawalEligibilityScreen(
                                      controller: controller,
                                    ),
                          ),
                        );
                      },
                    ),
                  ),
                  SizedBox(
                    width: tileWidth,
                    child: _WalletActionTile(
                      title: 'Deposit history',
                      detail:
                          'Inspect deposits and wallet activity without leaving the capital desk.',
                      icon: Icons.receipt_long_outlined,
                      accent: GteShellTheme.accentCommunity,
                      onTap: () {
                        Navigator.of(context).push<void>(
                          MaterialPageRoute<void>(
                            builder:
                                (BuildContext context) =>
                                    GteDepositHistoryScreen(
                                      controller: controller,
                                    ),
                          ),
                        );
                      },
                    ),
                  ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}

class _WalletActionTile extends StatelessWidget {
  const _WalletActionTile({
    required this.title,
    required this.detail,
    required this.icon,
    required this.accent,
    required this.onTap,
    this.enabled = true,
    this.emphasized = false,
  });

  final String title;
  final String detail;
  final IconData icon;
  final Color accent;
  final VoidCallback? onTap;
  final bool enabled;
  final bool emphasized;

  @override
  Widget build(BuildContext context) {
    final ButtonStyleButton actionButton =
        emphasized
            ? FilledButton.icon(
              onPressed: enabled ? onTap : null,
              icon: Icon(icon),
              label: Text(title),
            )
            : OutlinedButton.icon(
              onPressed: enabled ? onTap : null,
              icon: Icon(icon),
              label: Text(title),
            );
    return Opacity(
      opacity: enabled ? 1 : 0.58,
      child: GteSurfacePanel(
        onTap: enabled ? onTap : null,
        accentColor: accent,
        emphasized: emphasized,
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: accent.withValues(alpha: 0.14),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: accent.withValues(alpha: 0.22)),
              ),
              child: Icon(icon, color: accent, size: 18),
            ),
            const SizedBox(height: 14),
            Text(detail, style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: 14),
            Align(alignment: Alignment.centerLeft, child: actionButton),
          ],
        ),
      ),
    );
  }
}

class _CapitalSignalRow extends StatelessWidget {
  const _CapitalSignalRow({
    required this.leftLabel,
    required this.leftValue,
    required this.rightLabel,
    required this.rightValue,
  });

  final String leftLabel;
  final String leftValue;
  final String rightLabel;
  final String rightValue;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: <Widget>[
        Expanded(child: _CapitalSignalTile(label: leftLabel, value: leftValue)),
        const SizedBox(width: 12),
        Expanded(
          child: _CapitalSignalTile(label: rightLabel, value: rightValue),
        ),
      ],
    );
  }
}

class _CapitalSignalTile extends StatelessWidget {
  const _CapitalSignalTile({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        color: Colors.white.withValues(alpha: 0.04),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(label, style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 6),
          Text(
            value,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: GteShellTheme.accentCapital,
            ),
          ),
        ],
      ),
    );
  }
}
