import 'package:flutter/material.dart';

import '../data/gte_models.dart';
import '../providers/gte_exchange_controller.dart';
import '../widgets/gte_formatters.dart';
import '../widgets/gte_metric_chip.dart';
import '../widgets/gte_order_detail_card.dart';
import '../widgets/gte_state_panel.dart';
import '../widgets/gte_surface_panel.dart';
import '../widgets/gte_wallet_summary_card.dart';

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
      return Padding(
        padding: const EdgeInsets.all(20),
        child: GteStatePanel(
          title: 'Sign in required',
          message:
              'Portfolio, wallet, and order routes are protected. Sign in to load `/api/portfolio`, `/api/portfolio/summary`, `/api/wallets/summary`, and `/api/orders`.',
          actionLabel: 'Open login',
          onAction: onOpenLogin,
          icon: Icons.lock_outline,
        ),
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
            GteSurfacePanel(
              emphasized: true,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('Portfolio',
                      style: Theme.of(context).textTheme.headlineSmall),
                  const SizedBox(height: 8),
                  Text(
                    'Track wallet balances, holdings, and recent order activity from one protected trading view.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 18),
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: <Widget>[
                      GteMetricChip(
                        label: 'Holdings',
                        value: (controller.portfolio?.holdings.length ?? 0)
                            .toString(),
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
                  ),
                  const SizedBox(height: 18),
                  FilledButton.tonalIcon(
                    onPressed: controller.isLoadingPortfolio ||
                            controller.isLoadingOrders
                        ? null
                        : () {
                            controller.refreshAccount();
                          },
                    icon: const Icon(Icons.refresh),
                    label: const Text('Refresh account'),
                  ),
                  if (controller.isLoadingPortfolio ||
                      controller.isLoadingOrders) ...<Widget>[
                    const SizedBox(height: 16),
                    const LinearProgressIndicator(),
                  ],
                ],
              ),
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
            if (controller.walletSummary != null)
              GteWalletSummaryCard(summary: controller.walletSummary!)
            else if (controller.isLoadingPortfolio)
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
                onAction: () {
                  controller.refreshAccount();
                },
                icon: Icons.warning_amber_rounded,
              )
            else if (controller.isLoadingPortfolio &&
                controller.portfolio == null)
              const _LoadingCard(title: 'Holdings')
            else if (controller.portfolio == null ||
                controller.portfolio!.holdings.isEmpty)
              const GteStatePanel(
                title: 'No holdings yet',
                message:
                    'Place an order from a player detail screen to start building the portfolio.',
                icon: Icons.account_balance_wallet_outlined,
              )
            else
              _HoldingsCard(
                controller: controller,
                portfolio: controller.portfolio!,
                onOpenPlayer: onOpenPlayer,
              ),
            const SizedBox(height: 20),
            _OrdersPanel(
              controller: controller,
              onOpenPlayer: onOpenPlayer,
            ),
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
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Portfolio summary',
              style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 14),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              GteMetricChip(
                label: 'Market value',
                value: gteFormatCredits(summary.totalMarketValue),
              ),
              GteMetricChip(
                label: 'Cash',
                value: gteFormatCredits(summary.cashBalance),
              ),
              GteMetricChip(
                label: 'Total equity',
                value: gteFormatCredits(summary.totalEquity),
              ),
              GteMetricChip(
                label: 'Unrealized P/L',
                value: gteFormatCredits(summary.unrealizedPlTotal),
                positive: summary.unrealizedPlTotal >= 0,
              ),
              GteMetricChip(
                label: 'Realized P/L',
                value: gteFormatCredits(summary.realizedPlTotal),
                positive: summary.realizedPlTotal >= 0,
              ),
              GteMetricChip(
                label: 'Positions',
                value: holdingCount.toString(),
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
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Holdings', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 8),
          Text(
            'Latest revalued positions with current mark and unrealized performance.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          ...portfolio.holdings.map(
            (GtePortfolioHolding holding) => Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: GteSurfacePanel(
                padding: const EdgeInsets.all(16),
                onTap: () => onOpenPlayer(holding.playerId),
                child: Row(
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
                            'Qty ${holding.quantity.toStringAsFixed(2)} | Avg ${gteFormatCredits(holding.averageCost)} | Mark ${gteFormatCredits(holding.currentPrice)}',
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                          const SizedBox(height: 12),
                          Wrap(
                            spacing: 12,
                            runSpacing: 12,
                            children: <Widget>[
                              GteMetricChip(
                                label: 'Market value',
                                value: gteFormatCredits(holding.marketValue),
                              ),
                              GteMetricChip(
                                label: 'Unrealized P/L',
                                value: gteFormatCredits(holding.unrealizedPl),
                                positive: holding.unrealizedPl >= 0,
                              ),
                              GteMetricChip(
                                label: 'Unrealized %',
                                value: gteFormatMovement(
                                    holding.unrealizedPlPercent / 100),
                                positive: holding.unrealizedPlPercent >= 0,
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 16),
                    Icon(
                      Icons.chevron_right,
                      color: Theme.of(context)
                          .colorScheme
                          .onSurface
                          .withValues(alpha: 0.7),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

enum _OrdersPanelMode {
  open,
  recent,
}

class _OrdersPanel extends StatefulWidget {
  const _OrdersPanel({
    required this.controller,
    required this.onOpenPlayer,
  });

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
                    child: Text('Open and recent orders',
                        style: Theme.of(context).textTheme.headlineSmall),
                  ),
                  FilledButton.tonalIcon(
                    onPressed: controller.isLoadingOrders
                        ? null
                        : () {
                            controller.loadOrders();
                          },
                    icon: const Icon(Icons.refresh),
                    label: const Text('Refresh orders'),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                showOpenView
                    ? 'Focused on resting orders from `GET /api/orders?status=open&status=partially_filled`.'
                    : 'Focused on recent settled activity from `GET /api/orders`.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 14),
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: <Widget>[
                  GteMetricChip(
                    label: 'Open',
                    value: openOrders.length.toString(),
                  ),
                  GteMetricChip(
                    label: 'Recent',
                    value: recentClosedOrders.length.toString(),
                  ),
                  GteMetricChip(
                    label: 'API total',
                    value: controller.recentOrderTotal.toString(),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              SegmentedButton<_OrdersPanelMode>(
                segments: const <ButtonSegment<_OrdersPanelMode>>[
                  ButtonSegment<_OrdersPanelMode>(
                    value: _OrdersPanelMode.open,
                    label: Text('Open'),
                  ),
                  ButtonSegment<_OrdersPanelMode>(
                    value: _OrdersPanelMode.recent,
                    label: Text('Recent'),
                  ),
                ],
                selected: <_OrdersPanelMode>{effectiveMode},
                onSelectionChanged: (Set<_OrdersPanelMode> selection) {
                  setState(() {
                    _mode = selection.first;
                  });
                },
              ),
              if (controller.isLoadingOrders) ...<Widget>[
                const SizedBox(height: 16),
                const LinearProgressIndicator(),
              ],
              if (controller.ordersError != null &&
                  visibleOrders.isEmpty) ...<Widget>[
                const SizedBox(height: 16),
                GteStatePanel(
                  title: 'Orders unavailable',
                  message: controller.ordersError!,
                  actionLabel: 'Retry',
                  onAction: () {
                    controller.loadOrders();
                  },
                  icon: Icons.receipt_long_outlined,
                ),
              ] else if (!controller.hasLoadedOrders &&
                  controller.isLoadingOrders) ...<Widget>[
                const SizedBox(height: 16),
                const _LoadingCard(title: 'Orders'),
              ] else if (visibleOrders.isEmpty) ...<Widget>[
                const SizedBox(height: 16),
                GteStatePanel(
                  title: showOpenView ? 'No open orders' : 'No recent orders',
                  message: showOpenView
                      ? 'Resting and partially filled orders will appear here after the next submit.'
                      : 'Closed or cancelled activity will appear here after your first completed order loop.',
                  icon: Icons.receipt_long_outlined,
                ),
              ] else ...<Widget>[
                const SizedBox(height: 12),
                Text(
                  showOpenView
                      ? 'Showing ${openOrders.length} visible open orders from ${controller.openOrderTotal} total open records.'
                      : 'Showing ${recentClosedOrders.length} recent closed orders from the latest API window.',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ],
            ],
          ),
        ),
        if (controller.ordersError != null &&
            visibleOrders.isNotEmpty) ...<Widget>[
          const SizedBox(height: 16),
          _InlineAccountNotice(
            icon: Icons.warning_amber_rounded,
            message:
                'Order refresh partially failed. Showing the latest successful snapshot instead.',
          ),
        ],
        if (visibleOrders.isNotEmpty) ...<Widget>[
          const SizedBox(height: 16),
          Text(
            showOpenView ? 'Open orders' : 'Recent orders',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 12),
          ...visibleOrders.map(
            (GteOrderRecord order) => Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: _OrderCardWrapper(
                controller: controller,
                order: order,
                onOpenPlayer: widget.onOpenPlayer,
              ),
            ),
          ),
        ],
      ],
    );
  }
}

class _OrderCardWrapper extends StatelessWidget {
  const _OrderCardWrapper({
    required this.controller,
    required this.order,
    required this.onOpenPlayer,
  });

  final GteExchangeController controller;
  final GteOrderRecord order;
  final ValueChanged<String> onOpenPlayer;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        GteOrderDetailCard(
          order: order,
          playerLabel: controller.playerLabel(order.playerId),
          isRefreshing: controller.isRefreshingOrder,
          isCancelling: controller.isCancellingOrder,
          onRefresh: () {
            _refreshOrder(context);
          },
          onCancel: () {
            _cancelOrder(context);
          },
          showPlayerLabel: true,
        ),
        const SizedBox(height: 8),
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton.icon(
            onPressed: () => onOpenPlayer(order.playerId),
            icon: const Icon(Icons.open_in_new),
            label: const Text('Open player'),
          ),
        ),
      ],
    );
  }

  Future<void> _refreshOrder(BuildContext context) async {
    final GteOrderRecord? refreshed = await controller.refreshOrder(order.id);
    if (!context.mounted || refreshed == null) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
            'Order status refreshed: ${gteFormatOrderStatus(refreshed.status.name)}.'),
      ),
    );
  }

  Future<void> _cancelOrder(BuildContext context) async {
    final GteOrderRecord? cancelled = await controller.cancelOrder(order.id);
    if (!context.mounted || cancelled == null) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
            'Order updated: ${gteFormatOrderStatus(cancelled.status.name)}.'),
      ),
    );
  }
}

class _InlineAccountNotice extends StatelessWidget {
  const _InlineAccountNotice({
    required this.icon,
    required this.message,
  });

  final IconData icon;
  final String message;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Padding(
            padding: const EdgeInsets.only(top: 2),
            child: Icon(icon),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              message,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
        ],
      ),
    );
  }
}

class _LoadingCard extends StatelessWidget {
  const _LoadingCard({
    required this.title,
  });

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
