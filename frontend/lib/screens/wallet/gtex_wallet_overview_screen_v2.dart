import 'package:flutter/material.dart';

import '../../data/gte_api_repository.dart';
import '../../data/gte_models.dart';
import '../../features/coin_trader_redesign/coin_trader_redesign.dart';
import '../../features/trust_ops_redesign/trust_ops_redesign.dart';
import '../../providers/gte_exchange_controller.dart';
import '../../ui_gtex/ui_gtex.dart';
import '../../widgets/gte_formatters.dart';

enum GtexWalletDeskModule {
  wallet,
  orders,
  holdings,
  coinTraders,
  traderDashboard,
}

/// Route-compatible V2 wrapper for the wallet route.
///
/// Production callers should pass [controller]. When no controller is provided
/// this falls back to the batch preview surface so existing isolated redesign
/// tests can keep rendering the package without a full app controller.
class GtexWalletOverviewScreenV2 extends StatelessWidget {
  const GtexWalletOverviewScreenV2({
    super.key,
    this.controller,
    this.onTopUp,
    this.onWithdraw,
    this.onOpenLogin,
    this.onOpenPlayer,
    this.onModuleChanged,
    this.initialModule = GtexWalletDeskModule.wallet,
    this.baseUrl = 'http://127.0.0.1:8000',
    this.backendMode = GteBackendMode.live,
  });

  final GteExchangeController? controller;
  final VoidCallback? onTopUp;
  final VoidCallback? onWithdraw;
  final VoidCallback? onOpenLogin;
  final ValueChanged<String>? onOpenPlayer;
  final ValueChanged<GtexWalletDeskModule>? onModuleChanged;
  final GtexWalletDeskModule initialModule;
  final String baseUrl;
  final GteBackendMode backendMode;

  @override
  Widget build(BuildContext context) {
    final GteExchangeController? liveController = controller;
    if (liveController == null) {
      return GtexWalletOrdersScreen(
        initialModule: GtexTrustModule.wallet,
        onTopUp: onTopUp,
        onWithdraw: onWithdraw,
      );
    }
    return _GtexLiveWalletOverview(
      controller: liveController,
      onTopUp: onTopUp,
      onWithdraw: onWithdraw,
      onOpenLogin: onOpenLogin,
      onOpenPlayer: onOpenPlayer,
      onModuleChanged: onModuleChanged,
      initialModule: initialModule,
      baseUrl: baseUrl,
      backendMode: backendMode,
    );
  }
}

class _GtexLiveWalletOverview extends StatefulWidget {
  const _GtexLiveWalletOverview({
    required this.controller,
    this.onTopUp,
    this.onWithdraw,
    this.onOpenLogin,
    this.onOpenPlayer,
    this.onModuleChanged,
    required this.initialModule,
    required this.baseUrl,
    required this.backendMode,
  });

  final GteExchangeController controller;
  final VoidCallback? onTopUp;
  final VoidCallback? onWithdraw;
  final VoidCallback? onOpenLogin;
  final ValueChanged<String>? onOpenPlayer;
  final ValueChanged<GtexWalletDeskModule>? onModuleChanged;
  final GtexWalletDeskModule initialModule;
  final String baseUrl;
  final GteBackendMode backendMode;

  @override
  State<_GtexLiveWalletOverview> createState() =>
      _GtexLiveWalletOverviewState();
}

class _GtexLiveWalletOverviewState extends State<_GtexLiveWalletOverview> {
  late GtexWalletDeskModule _module;

  @override
  void initState() {
    super.initState();
    _module = widget.initialModule;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !widget.controller.isAuthenticated) {
        return;
      }
      widget.controller.refreshAccount();
    });
  }

  @override
  void didUpdateWidget(covariant _GtexLiveWalletOverview oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.initialModule != widget.initialModule) {
      setState(() => _module = widget.initialModule);
    }
  }

  void _selectModule(GtexWalletDeskModule module) {
    if (_module != module) {
      setState(() => _module = module);
    }
    widget.onModuleChanged?.call(module);
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.controller.isAuthenticated &&
        _module != GtexWalletDeskModule.coinTraders &&
        _module != GtexWalletDeskModule.traderDashboard) {
      return GtexFocusFlowScaffold(
        title: 'Wallet locked',
        subtitle: 'Sign in to open balances, orders, holdings and trust flows.',
        accent: GtexColors.gold,
        leading: const Icon(
          Icons.account_balance_wallet_outlined,
          color: GtexColors.gold,
          size: 54,
        ),
        footer: Align(
          alignment: Alignment.center,
          child: Wrap(
            spacing: GtexSpacing.sm,
            runSpacing: GtexSpacing.sm,
            alignment: WrapAlignment.center,
            children: <Widget>[
              GtexActionButton(
                label: 'Sign in',
                icon: Icons.login,
                accent: GtexColors.gold,
                onPressed: widget.onOpenLogin,
              ),
              GtexButton(
                label: 'Browse traders',
                icon: Icons.currency_exchange_outlined,
                variant: GtexButtonVariant.secondary,
                onPressed:
                    () => _selectModule(GtexWalletDeskModule.coinTraders),
              ),
            ],
          ),
        ),
        child: const Text(
          'GTEX keeps capital, player ownership and order history behind an authenticated account boundary.',
          textAlign: TextAlign.center,
          style: TextStyle(color: GtexColors.textMuted),
        ),
      );
    }

    return AnimatedBuilder(
      animation: widget.controller,
      builder: (BuildContext context, Widget? child) {
        return GtexMasterDetailScaffold(
          title: 'Wallet & Capital',
          subtitle:
              'Live balances, transfer orders, player holdings and payment actions.',
          accent: GtexColors.gold,
          mobileLeftTitle: 'Capital desk',
          leftPanelWidth: 300,
          rightPanelWidth: 350,
          actions: <Widget>[
            IconButton.filledTonal(
              tooltip: 'Refresh wallet',
              onPressed: widget.controller.refreshAccount,
              icon: const Icon(Icons.sync),
            ),
          ],
          leftPanel: _buildModuleList(context),
          detail: _buildDetail(context),
          rightPanel: _WalletRightRail(
            controller: widget.controller,
            onTopUp: widget.onTopUp,
            onWithdraw: widget.onWithdraw,
          ),
        );
      },
    );
  }

  Widget _buildModuleList(BuildContext context) {
    return ListView(
      children: <Widget>[
        _ModuleTile(
          key: const ValueKey<String>('capital-module-wallet'),
          title: 'Wallet',
          subtitle: 'Balances and payment actions',
          icon: Icons.account_balance_wallet_outlined,
          selected: _module == GtexWalletDeskModule.wallet,
          onTap: () => _selectModule(GtexWalletDeskModule.wallet),
        ),
        const SizedBox(height: GtexSpacing.xs),
        _ModuleTile(
          key: const ValueKey<String>('capital-module-orders'),
          title: 'Orders',
          subtitle: '${widget.controller.openOrders.length} open orders',
          icon: Icons.receipt_long_outlined,
          selected: _module == GtexWalletDeskModule.orders,
          onTap: () => _selectModule(GtexWalletDeskModule.orders),
        ),
        const SizedBox(height: GtexSpacing.xs),
        _ModuleTile(
          key: const ValueKey<String>('capital-module-holdings'),
          title: 'Holdings',
          subtitle:
              '${widget.controller.portfolio?.holdings.length ?? 0} player assets',
          icon: Icons.groups_2_outlined,
          selected: _module == GtexWalletDeskModule.holdings,
          onTap: () => _selectModule(GtexWalletDeskModule.holdings),
        ),
        const SizedBox(height: GtexSpacing.xs),
        _ModuleTile(
          key: const ValueKey<String>('capital-module-coin-traders'),
          title: 'Coin Traders',
          subtitle: 'P2P rates and escrow orders',
          icon: Icons.currency_exchange_outlined,
          selected: _module == GtexWalletDeskModule.coinTraders,
          onTap: () => _selectModule(GtexWalletDeskModule.coinTraders),
        ),
        const SizedBox(height: GtexSpacing.xs),
        _ModuleTile(
          key: const ValueKey<String>('capital-module-trader-dashboard'),
          title: 'Trader Dashboard',
          subtitle: 'Rates, liquidity and trader orders',
          icon: Icons.storefront_outlined,
          selected: _module == GtexWalletDeskModule.traderDashboard,
          onTap: () => _selectModule(GtexWalletDeskModule.traderDashboard),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Live account status',
          accent: GtexColors.gold,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              GtexStatusChip(
                label:
                    widget.controller.isLoadingPortfolio ||
                            widget.controller.isLoadingOrders
                        ? 'Syncing'
                        : 'Ready',
                color: GtexColors.gold,
              ),
              if (widget.controller.portfolioError != null) ...<Widget>[
                const SizedBox(height: GtexSpacing.sm),
                Text(
                  widget.controller.portfolioError!,
                  style: const TextStyle(color: GtexColors.red),
                ),
              ],
              if (widget.controller.ordersError != null) ...<Widget>[
                const SizedBox(height: GtexSpacing.sm),
                Text(
                  widget.controller.ordersError!,
                  style: const TextStyle(color: GtexColors.red),
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildDetail(BuildContext context) {
    switch (_module) {
      case GtexWalletDeskModule.wallet:
        return _WalletBalancePanel(
          controller: widget.controller,
          onTopUp: widget.onTopUp,
          onWithdraw: widget.onWithdraw,
        );
      case GtexWalletDeskModule.orders:
        return _OrdersPanel(
          orders: <GteOrderRecord>[
            ...widget.controller.openOrders,
            ...widget.controller.recentOrders,
          ],
        );
      case GtexWalletDeskModule.holdings:
        return _HoldingsPanel(
          holdings:
              widget.controller.portfolio?.holdings ??
              const <GtePortfolioHolding>[],
          onOpenPlayer: widget.onOpenPlayer,
        );
      case GtexWalletDeskModule.coinTraders:
        return GtexCoinTraderMarketplacePanel(
          baseUrl: widget.baseUrl,
          backendMode: widget.backendMode,
          accessToken: widget.controller.accessToken,
          isAuthenticated: widget.controller.isAuthenticated,
          onOpenLogin: widget.onOpenLogin,
        );
      case GtexWalletDeskModule.traderDashboard:
        return GtexCoinTraderDashboardPanel(
          baseUrl: widget.baseUrl,
          backendMode: widget.backendMode,
          accessToken: widget.controller.accessToken,
          isAuthenticated: widget.controller.isAuthenticated,
          onOpenLogin: widget.onOpenLogin,
        );
    }
  }
}

class _ModuleTile extends StatelessWidget {
  const _ModuleTile({
    super.key,
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.selected,
    required this.onTap,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      isSelected: selected,
      accent: GtexColors.gold,
      padding: const EdgeInsets.all(GtexSpacing.sm),
      onTap: onTap,
      child: Row(
        children: <Widget>[
          Icon(icon, color: selected ? GtexColors.gold : GtexColors.textMuted),
          const SizedBox(width: GtexSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  title,
                  style: const TextStyle(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                Text(
                  subtitle,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: GtexColors.textMuted),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _WalletBalancePanel extends StatelessWidget {
  const _WalletBalancePanel({
    required this.controller,
    this.onTopUp,
    this.onWithdraw,
  });

  final GteExchangeController controller;
  final VoidCallback? onTopUp;
  final VoidCallback? onWithdraw;

  @override
  Widget build(BuildContext context) {
    final GteWalletSummary? wallet = controller.walletSummary;
    final GtePortfolioSummary? portfolio = controller.portfolioSummary;
    if (wallet == null && controller.isLoadingPortfolio) {
      return const Center(child: CircularProgressIndicator());
    }
    if (wallet == null) {
      return GtexEmptyState(
        title: 'Wallet unavailable',
        message:
            controller.portfolioError ??
            'The live wallet endpoint did not return a balance yet.',
        icon: Icons.account_balance_wallet_outlined,
        actionLabel: 'Retry wallet',
        onAction: controller.refreshAccount,
      );
    }

    return ListView(
      children: <Widget>[
        GtexPanel(
          title: 'Capital position',
          subtitle: 'Real wallet data from the existing account API.',
          accent: GtexColors.gold,
          child: Wrap(
            spacing: GtexSpacing.md,
            runSpacing: GtexSpacing.md,
            children: <Widget>[
              SizedBox(
                width: 210,
                child: GtexMetricTile(
                  label: 'Available',
                  value: gteFormatCredits(wallet.availableBalance),
                  icon: Icons.flash_on_outlined,
                  accent: GtexColors.gold,
                ),
              ),
              SizedBox(
                width: 210,
                child: GtexMetricTile(
                  label: 'Reserved',
                  value: gteFormatCredits(wallet.reservedBalance),
                  icon: Icons.lock_clock_outlined,
                  accent: GtexColors.cyan,
                ),
              ),
              SizedBox(
                width: 210,
                child: GtexMetricTile(
                  label: 'Total balance',
                  value: gteFormatCredits(wallet.totalBalance),
                  icon: Icons.account_balance_outlined,
                  accent: GtexColors.pitch,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Portfolio exposure',
          subtitle: 'Player assets and cash posture from the portfolio API.',
          accent: GtexColors.pitch,
          child: Wrap(
            spacing: GtexSpacing.md,
            runSpacing: GtexSpacing.md,
            children: <Widget>[
              SizedBox(
                width: 210,
                child: GtexMetricTile(
                  label: 'Market value',
                  value: gteFormatCredits(portfolio?.totalMarketValue ?? 0),
                  icon: Icons.trending_up,
                  accent: GtexColors.pitch,
                ),
              ),
              SizedBox(
                width: 210,
                child: GtexMetricTile(
                  label: 'Equity',
                  value: gteFormatCredits(portfolio?.totalEquity ?? 0),
                  icon: Icons.stacked_line_chart,
                  accent: GtexColors.cyan,
                ),
              ),
              SizedBox(
                width: 210,
                child: GtexMetricTile(
                  label: 'Unrealized P/L',
                  value: gteFormatCredits(portfolio?.unrealizedPlTotal ?? 0),
                  icon: Icons.show_chart,
                  accent:
                      (portfolio?.unrealizedPlTotal ?? 0) >= 0
                          ? GtexColors.pitch
                          : GtexColors.red,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        Wrap(
          spacing: GtexSpacing.sm,
          runSpacing: GtexSpacing.sm,
          children: <Widget>[
            GtexActionButton(
              label: 'Top up',
              icon: Icons.add_card_outlined,
              accent: GtexColors.gold,
              onPressed: onTopUp,
            ),
            GtexActionButton(
              label: 'Withdraw',
              icon: Icons.account_balance_outlined,
              accent: GtexColors.cyan,
              onPressed: onWithdraw,
            ),
          ],
        ),
      ],
    );
  }
}

class _OrdersPanel extends StatelessWidget {
  const _OrdersPanel({required this.orders});

  final List<GteOrderRecord> orders;

  @override
  Widget build(BuildContext context) {
    if (orders.isEmpty) {
      return const GtexEmptyState(
        title: 'No orders yet',
        message:
            'Open and recent player orders will appear here from the live order API.',
        icon: Icons.receipt_long_outlined,
      );
    }
    return ListView.separated(
      itemCount: orders.length,
      separatorBuilder: (_, __) => const SizedBox(height: GtexSpacing.sm),
      itemBuilder: (BuildContext context, int index) {
        final GteOrderRecord order = orders[index];
        return GtexPanel(
          accent: order.canCancel ? GtexColors.gold : GtexColors.pitch,
          child: Row(
            children: <Widget>[
              Icon(
                order.side == GteOrderSide.buy
                    ? Icons.south_west
                    : Icons.north_east,
                color: order.canCancel ? GtexColors.gold : GtexColors.pitch,
              ),
              const SizedBox(width: GtexSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      '${order.side.name.toUpperCase()} ${order.playerId}',
                      style: const TextStyle(
                        color: GtexColors.text,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    Text(
                      '${_statusLabel(order.status)} - ${order.quantity.toStringAsFixed(2)} units',
                      style: const TextStyle(color: GtexColors.textMuted),
                    ),
                  ],
                ),
              ),
              Text(
                gteFormatCredits(order.reservedAmount),
                style: const TextStyle(
                  color: GtexColors.gold,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _HoldingsPanel extends StatelessWidget {
  const _HoldingsPanel({required this.holdings, this.onOpenPlayer});

  final List<GtePortfolioHolding> holdings;
  final ValueChanged<String>? onOpenPlayer;

  @override
  Widget build(BuildContext context) {
    if (holdings.isEmpty) {
      return const GtexEmptyState(
        title: 'No player holdings yet',
        message:
            'Purchased players will appear here once the portfolio API returns positions.',
        icon: Icons.groups_2_outlined,
      );
    }
    return ListView.separated(
      itemCount: holdings.length,
      separatorBuilder: (_, __) => const SizedBox(height: GtexSpacing.sm),
      itemBuilder: (BuildContext context, int index) {
        final GtePortfolioHolding holding = holdings[index];
        return GtexPanel(
          accent: holding.unrealizedPl >= 0 ? GtexColors.pitch : GtexColors.red,
          onTap:
              onOpenPlayer == null
                  ? null
                  : () => onOpenPlayer!(holding.playerId),
          child: Row(
            children: <Widget>[
              const Icon(Icons.person_outline, color: GtexColors.pitch),
              const SizedBox(width: GtexSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      holding.playerId,
                      style: const TextStyle(
                        color: GtexColors.text,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    Text(
                      'Qty ${holding.quantity.toStringAsFixed(2)} - Avg ${gteFormatCredits(holding.averageCost)}',
                      style: const TextStyle(color: GtexColors.textMuted),
                    ),
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: <Widget>[
                  Text(
                    gteFormatCredits(holding.marketValue),
                    style: const TextStyle(
                      color: GtexColors.text,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  Text(
                    '${holding.unrealizedPlPercent.toStringAsFixed(2)}%',
                    style: TextStyle(
                      color:
                          holding.unrealizedPl >= 0
                              ? GtexColors.pitch
                              : GtexColors.red,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }
}

class _WalletRightRail extends StatelessWidget {
  const _WalletRightRail({
    required this.controller,
    this.onTopUp,
    this.onWithdraw,
  });

  final GteExchangeController controller;
  final VoidCallback? onTopUp;
  final VoidCallback? onWithdraw;

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: <Widget>[
        GtexPanel(
          title: 'Capital actions',
          subtitle: 'Existing payment flows remain wired.',
          accent: GtexColors.gold,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              GtexActionButton(
                label: 'Top up wallet',
                icon: Icons.add_card_outlined,
                accent: GtexColors.gold,
                onPressed: onTopUp,
              ),
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(
                label: 'Withdraw funds',
                icon: Icons.account_balance_outlined,
                accent: GtexColors.cyan,
                onPressed: onWithdraw,
              ),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Account tape',
          accent: GtexColors.pitch,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              GtexStatusChip(
                label: '${controller.openOrders.length} open orders',
                color: GtexColors.gold,
              ),
              const SizedBox(height: GtexSpacing.xs),
              GtexStatusChip(
                label: '${controller.recentOrders.length} recent orders',
                color: GtexColors.cyan,
              ),
              const SizedBox(height: GtexSpacing.xs),
              GtexStatusChip(
                label: '${controller.portfolio?.holdings.length ?? 0} holdings',
                color: GtexColors.pitch,
              ),
            ],
          ),
        ),
        if (controller.portfolioError != null ||
            controller.ordersError != null) ...<Widget>[
          const SizedBox(height: GtexSpacing.md),
          GtexPanel(
            title: 'Sync notice',
            accent: GtexColors.red,
            child: Text(
              controller.portfolioError ??
                  controller.ordersError ??
                  'Account sync degraded.',
              style: const TextStyle(color: GtexColors.textMuted),
            ),
          ),
        ],
      ],
    );
  }
}

String _statusLabel(GteOrderStatus status) {
  switch (status) {
    case GteOrderStatus.open:
      return 'Open';
    case GteOrderStatus.partiallyFilled:
      return 'Partially filled';
    case GteOrderStatus.filled:
      return 'Filled';
    case GteOrderStatus.cancelled:
      return 'Cancelled';
    case GteOrderStatus.rejected:
      return 'Rejected';
    case GteOrderStatus.unknown:
      return 'Unknown';
  }
}
