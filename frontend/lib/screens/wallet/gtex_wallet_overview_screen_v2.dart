import 'package:flutter/material.dart';

import '../../data/gte_authed_api.dart';
import '../../data/gte_api_repository.dart';
import '../../data/gte_exchange_models.dart';
import '../../data/gte_models.dart';
import '../../domain/ownership/gtex_ownership_models.dart';
import '../../features/club_redesign/data/gtex_club_ownership_api.dart';
import '../../features/club_redesign/models/gtex_club_ownership_models.dart';
import '../../features/coin_trader_redesign/coin_trader_redesign.dart';
import '../../features/trust_ops_redesign/trust_ops_redesign.dart';
import '../../providers/gte_exchange_controller.dart';
import '../../ui_gtex/ui_gtex.dart';
import '../../widgets/gte_formatters.dart';
import 'gtex_capital_desk_api.dart';
import 'gtex_ownership_experience.dart';

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
    this.authedApi,
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
  final GteAuthedApi? authedApi;

  @override
  Widget build(BuildContext context) {
    final GteExchangeController? liveController = controller;
    if (liveController == null) {
      if (backendMode != GteBackendMode.fixture) {
        return const GtexEmptyState(
          title: 'Wallet connection required',
          message:
              'The production wallet route needs the live exchange controller. Fixture wallet data is available only in explicit test mode.',
          icon: Icons.account_balance_wallet_outlined,
        );
      }
      return GtexWalletOrdersScreen(
        repository: const GtexTrustOpsDemoRepository(),
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
      authedApi: authedApi,
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
    this.authedApi,
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
  final GteAuthedApi? authedApi;

  @override
  State<_GtexLiveWalletOverview> createState() =>
      _GtexLiveWalletOverviewState();
}

class _GtexLiveWalletOverviewState extends State<_GtexLiveWalletOverview> {
  late GtexWalletDeskModule _module;
  List<GteDepositRequest> _depositRequests = const <GteDepositRequest>[];
  bool _isLoadingDeposits = false;
  String? _depositError;

  GtePortfolioSnapshot? _snapshot;
  GtexClubOwnershipPortfolio? _clubPortfolio;
  bool _isLoadingClubs = false;
  String? _clubError;

  @override
  void initState() {
    super.initState();
    _module = widget.initialModule;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !widget.controller.isAuthenticated) {
        return;
      }
      _refreshCapitalDesk();
    });
  }

  GtexCapitalDeskApi _capitalDeskApi() {
    final GteAuthedApi? authed = widget.authedApi;
    if (authed != null) {
      return GtexCapitalDeskApi(client: authed);
    }
    return GtexCapitalDeskApi.standard(
      baseUrl: widget.baseUrl,
      accessToken: widget.controller.accessToken,
      mode: widget.backendMode,
    );
  }

  GtexClubOwnershipApi _clubOwnershipApi() {
    final GteAuthedApi? authed = widget.authedApi;
    if (authed != null) {
      return GtexClubOwnershipApi(client: authed);
    }
    return GtexClubOwnershipApi.standard(
      baseUrl: widget.baseUrl,
      accessToken: widget.controller.accessToken,
      mode: widget.backendMode,
    );
  }

  Future<void> _loadOwnershipExtras() async {
    if (!widget.controller.isAuthenticated) {
      if (mounted) {
        setState(() {
          _snapshot = null;
          _clubPortfolio = null;
          _clubError = null;
          _isLoadingClubs = false;
        });
      }
      return;
    }
    setState(() {
      _isLoadingClubs = true;
      _clubError = null;
    });
    final List<Object?> results = await Future.wait<Object?>(<Future<Object?>>[
      _capitalDeskApi().fetchPortfolioSnapshot().then<Object?>(
            (GtePortfolioSnapshot s) => s,
            onError: (Object _) => null,
          ),
      _clubOwnershipApi().fetchMyClubPortfolio().then<Object?>(
            (GtexClubOwnershipPortfolio p) => p,
            onError: (Object error) => _ClubLoadError(error.toString()),
          ),
    ]);
    if (!mounted) {
      return;
    }
    setState(() {
      final Object? snapshot = results[0];
      if (snapshot is GtePortfolioSnapshot) {
        _snapshot = snapshot;
      }
      final Object? clubs = results[1];
      if (clubs is GtexClubOwnershipPortfolio) {
        _clubPortfolio = clubs;
        _clubError = null;
      } else if (clubs is _ClubLoadError) {
        _clubError = 'Club interests could not be synced right now.';
      }
      _isLoadingClubs = false;
    });
  }

  @override
  void didUpdateWidget(covariant _GtexLiveWalletOverview oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.initialModule != widget.initialModule) {
      setState(() => _module = widget.initialModule);
    }
  }

  Future<void> _refreshCapitalDesk() async {
    await Future.wait<void>(<Future<void>>[
      widget.controller.refreshAccount(),
      _loadDepositRequests(),
      _loadOwnershipExtras(),
    ]);
  }

  Future<void> _loadDepositRequests() async {
    if (!widget.controller.isAuthenticated) {
      if (mounted) {
        setState(() {
          _depositRequests = const <GteDepositRequest>[];
          _depositError = null;
          _isLoadingDeposits = false;
        });
      }
      return;
    }
    setState(() {
      _isLoadingDeposits = true;
      _depositError = null;
    });
    try {
      final List<GteDepositRequest> deposits =
          await widget.controller.api.listDepositRequests();
      if (!mounted) {
        return;
      }
      setState(() {
        _depositRequests = deposits;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _depositError =
            error is GteApiException &&
                    error.type == GteApiErrorType.unauthorized
                ? 'Sign in again to sync bank transfer requests.'
                : error.toString();
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoadingDeposits = false;
        });
      }
    }
  }

  Future<void> _cancelOrder(GteOrderRecord order) async {
    final GteOrderRecord? cancelled = await widget.controller.cancelOrder(
      order.id,
    );
    if (!mounted) {
      return;
    }
    final String label = widget.controller.playerLabel(order.playerId);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        backgroundColor: GtexColors.surfaceOverlay,
        content: Text(
          cancelled == null
              ? widget.controller.orderError ??
                  'That order could not be cancelled.'
              : 'Cancelled ${order.side.name} order for $label.',
          style: const TextStyle(color: GtexColors.text),
        ),
      ),
    );
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
              onPressed: _refreshCapitalDesk,
              icon: const Icon(Icons.sync),
            ),
          ],
          leftPanel: _buildModuleList(context),
          detail: _buildDetail(context),
          rightPanel: _WalletRightRail(
            controller: widget.controller,
            onTopUp: widget.onTopUp,
            onWithdraw: widget.onWithdraw,
            deposits: _depositRequests,
            isLoadingDeposits: _isLoadingDeposits,
            depositError: _depositError,
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
          controller: widget.controller,
          onCancel: _cancelOrder,
        );
      case GtexWalletDeskModule.holdings:
        return GtexOwnershipExperience(
          book: GtexOwnershipBook.fromPortfolio(widget.controller.portfolio),
          summary: widget.controller.portfolioSummary,
          walletSummary: widget.controller.walletSummary,
          snapshot: _snapshot,
          clubOwnership: _clubPortfolio,
          isLoadingClubs: _isLoadingClubs,
          clubError: _clubError,
          portfolioError: widget.controller.portfolioError,
          ownerName: widget.controller.session?.user.username,
          identityLookup: _identityFor,
          onOpenPlayer: widget.onOpenPlayer,
          onRetry: _refreshCapitalDesk,
        );
      case GtexWalletDeskModule.coinTraders:
        return GtexCoinTraderMarketplacePanel(
          baseUrl: widget.baseUrl,
          backendMode: widget.backendMode,
          accessToken: widget.controller.accessToken,
          isAuthenticated: widget.controller.isAuthenticated,
          onOpenLogin: widget.onOpenLogin,
          api:
              widget.authedApi == null
                  ? null
                  : GtexCoinTraderApi(client: widget.authedApi!),
        );
      case GtexWalletDeskModule.traderDashboard:
        return GtexCoinTraderDashboardPanel(
          baseUrl: widget.baseUrl,
          backendMode: widget.backendMode,
          accessToken: widget.controller.accessToken,
          isAuthenticated: widget.controller.isAuthenticated,
          onOpenLogin: widget.onOpenLogin,
          onTopUp: widget.onTopUp,
          api:
              widget.authedApi == null
                  ? null
                  : GtexCoinTraderApi(client: widget.authedApi!),
        );
    }
  }

  GteMarketPlayerListItem? _identityFor(String playerId) {
    for (final GteMarketPlayerListItem player in widget.controller.players) {
      if (player.playerId == playerId) {
        return player;
      }
    }
    return null;
  }
}

/// Sentinel wrapper so `Future.wait` can carry a club-load failure without
/// aborting the sibling snapshot read.
class _ClubLoadError {
  const _ClubLoadError(this.message);
  final String message;
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
          title: 'GTC capital rail',
          subtitle:
              'GTEX Coin is live transfer capital for trades, signings, escrow and withdrawals.',
          accent: GtexColors.gold,
          child: Wrap(
            spacing: GtexSpacing.md,
            runSpacing: GtexSpacing.md,
            children: <Widget>[
              SizedBox(
                width: 210,
                child: GtexMetricTile(
                  label: 'Available',
                  value: gteFormatGtc(wallet.availableBalance),
                  icon: Icons.flash_on_outlined,
                  accent: GtexColors.gold,
                ),
              ),
              SizedBox(
                width: 210,
                child: GtexMetricTile(
                  label: 'Reserved',
                  value: gteFormatGtc(wallet.reservedBalance),
                  icon: Icons.lock_clock_outlined,
                  accent: GtexColors.cyan,
                ),
              ),
              SizedBox(
                width: 210,
                child: GtexMetricTile(
                  label: 'Total balance',
                  value: gteFormatGtc(wallet.totalBalance),
                  icon: Icons.account_balance_outlined,
                  accent: GtexColors.pitch,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Player-market exposure',
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
                  value: gteFormatGtc(portfolio?.totalMarketValue ?? 0),
                  icon: Icons.trending_up,
                  accent: GtexColors.pitch,
                ),
              ),
              SizedBox(
                width: 210,
                child: GtexMetricTile(
                  label: 'Equity',
                  value: gteFormatGtc(portfolio?.totalEquity ?? 0),
                  icon: Icons.stacked_line_chart,
                  accent: GtexColors.cyan,
                ),
              ),
              SizedBox(
                width: 210,
                child: GtexMetricTile(
                  label: 'Unrealized P/L',
                  value: gteFormatGtc(portfolio?.unrealizedPlTotal ?? 0),
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
              label: 'Top up GTC',
              icon: Icons.add_card_outlined,
              accent: GtexColors.gold,
              onPressed: onTopUp,
            ),
            GtexActionButton(
              label: 'Withdraw GTC',
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
  const _OrdersPanel({
    required this.orders,
    required this.controller,
    required this.onCancel,
  });

  final List<GteOrderRecord> orders;
  final GteExchangeController controller;
  final Future<void> Function(GteOrderRecord order) onCancel;

  @override
  Widget build(BuildContext context) {
    if (orders.isEmpty) {
      // Player-share trades settle instantly on the canonical market, so no
      // new orders are created here. This panel is the historical record.
      return const GtexEmptyState(
        title: 'No order history',
        message:
            'Player share trades settle immediately, so they appear in '
            'Holdings rather than as working orders. Any earlier orders you '
            'placed would be listed here.',
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
                      '${order.side.name.toUpperCase()} '
                      '${controller.playerLabel(order.playerId)}',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: GtexColors.text,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    Text(
                      '${_statusLabel(order.status)} - ${order.quantity.toStringAsFixed(2)} units',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: GtexColors.textMuted),
                    ),
                  ],
                ),
              ),
              Text(
                gteFormatGtc(order.reservedAmount),
                style: const TextStyle(
                  color: GtexColors.gold,
                  fontWeight: FontWeight.w900,
                ),
              ),
              // Cancelling is a real backend flow, so it is offered exactly
              // when the order is actually cancellable.
              if (order.canCancel) ...<Widget>[
                const SizedBox(width: GtexSpacing.xs),
                IconButton(
                  key: ValueKey<String>('capital-order-cancel-${order.id}'),
                  tooltip: 'Cancel order',
                  onPressed:
                      controller.isCancellingOrder
                          ? null
                          : () => onCancel(order),
                  icon: const Icon(
                    Icons.cancel_outlined,
                    color: GtexColors.red,
                  ),
                ),
              ],
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
    this.deposits = const <GteDepositRequest>[],
    this.isLoadingDeposits = false,
    this.depositError,
  });

  final GteExchangeController controller;
  final VoidCallback? onTopUp;
  final VoidCallback? onWithdraw;
  final List<GteDepositRequest> deposits;
  final bool isLoadingDeposits;
  final String? depositError;

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
              const SizedBox(height: GtexSpacing.xs),
              GtexStatusChip(
                label:
                    isLoadingDeposits
                        ? 'syncing bank transfers'
                        : '${_activeDepositCount(deposits)} active bank transfers',
                color: GtexColors.cyan,
              ),
              if (deposits.isNotEmpty) ...<Widget>[
                const SizedBox(height: GtexSpacing.sm),
                ...deposits
                    .take(2)
                    .map(
                      (GteDepositRequest deposit) => Padding(
                        padding: const EdgeInsets.only(bottom: GtexSpacing.xs),
                        child: Text(
                          '${deposit.reference} - ${_statusLabelForDeposit(deposit.status)}',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(color: GtexColors.textMuted),
                        ),
                      ),
                    ),
              ],
              if (depositError != null) ...<Widget>[
                const SizedBox(height: GtexSpacing.sm),
                Text(
                  depositError!,
                  style: const TextStyle(color: GtexColors.textMuted),
                ),
              ],
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

int _activeDepositCount(List<GteDepositRequest> deposits) {
  return deposits
      .where(
        (GteDepositRequest deposit) =>
            deposit.status == GteDepositStatus.awaitingPayment ||
            deposit.status == GteDepositStatus.paymentSubmitted ||
            deposit.status == GteDepositStatus.underReview,
      )
      .length;
}

String _statusLabelForDeposit(GteDepositStatus status) {
  switch (status) {
    case GteDepositStatus.awaitingPayment:
      return 'Awaiting payment';
    case GteDepositStatus.paymentSubmitted:
      return 'Payment submitted';
    case GteDepositStatus.underReview:
      return 'Under review';
    case GteDepositStatus.confirmed:
      return 'Confirmed';
    case GteDepositStatus.rejected:
      return 'Rejected';
    case GteDepositStatus.expired:
      return 'Expired';
    case GteDepositStatus.disputed:
      return 'Disputed';
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
