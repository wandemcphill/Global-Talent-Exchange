import 'package:flutter/material.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import 'coin_trader_api.dart';
import 'coin_trader_models.dart';

class GtexCoinTraderMarketplacePanel extends StatefulWidget {
  const GtexCoinTraderMarketplacePanel({
    super.key,
    required this.baseUrl,
    required this.backendMode,
    required this.accessToken,
    required this.isAuthenticated,
    this.onOpenLogin,
    this.api,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;
  final GtexCoinTraderApi? api;

  @override
  State<GtexCoinTraderMarketplacePanel> createState() =>
      _GtexCoinTraderMarketplacePanelState();
}

class _GtexCoinTraderMarketplacePanelState
    extends State<GtexCoinTraderMarketplacePanel> {
  late GtexCoinTraderApi _api;
  List<GtexCoinTraderProfile> _traders = const <GtexCoinTraderProfile>[];
  List<GtexCoinTradeOrder> _myOrders = const <GtexCoinTradeOrder>[];
  GtexCoinTraderProfile? _selectedTrader;
  bool _loading = true;
  bool _loadingOrders = false;
  String? _error;
  String? _ordersError;
  String _coinUnit = 'COIN';

  @override
  void initState() {
    super.initState();
    _api = _resolveApi();
    _load();
  }

  @override
  void didUpdateWidget(covariant GtexCoinTraderMarketplacePanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.baseUrl != widget.baseUrl ||
        oldWidget.backendMode != widget.backendMode ||
        oldWidget.accessToken != widget.accessToken ||
        oldWidget.api != widget.api) {
      _api = _resolveApi();
      _load();
    }
  }

  GtexCoinTraderApi _resolveApi() {
    return widget.api ??
        GtexCoinTraderApi.standard(
          baseUrl: widget.baseUrl,
          accessToken: widget.accessToken,
          mode: widget.backendMode,
        );
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
      _ordersError = null;
      _loadingOrders = widget.isAuthenticated;
    });
    try {
      final List<GtexCoinTraderProfile> traders = await _api.listTraders(
        coinUnit: _coinUnit,
      );
      List<GtexCoinTradeOrder> myOrders = const <GtexCoinTradeOrder>[];
      String? ordersError;
      if (widget.isAuthenticated) {
        try {
          myOrders = await _api.listMyOrders();
        } catch (error) {
          ordersError = _messageFor(error);
        }
      }
      if (!mounted) {
        return;
      }
      setState(() {
        _traders = traders;
        _myOrders = myOrders;
        _ordersError = ordersError;
        _selectedTrader =
            traders.contains(_selectedTrader)
                ? _selectedTrader
                : traders.isEmpty
                ? null
                : traders.first;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = _messageFor(error);
      });
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
          _loadingOrders = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading && _traders.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null && _traders.isEmpty) {
      return GtexEmptyState(
        title: 'Coin Trader feed unavailable',
        message: _error!,
        icon: Icons.currency_exchange_outlined,
        accent: GtexColors.gold,
        actionLabel: 'Retry',
        onAction: _load,
      );
    }
    if (_traders.isEmpty) {
      return GtexEmptyState(
        title: 'No approved coin traders yet',
        message:
            'The live marketplace is connected, but the backend has no approved liquidity partners for this coin lane.',
        icon: Icons.verified_user_outlined,
        accent: GtexColors.gold,
        actionLabel: 'Refresh',
        onAction: _load,
      );
    }

    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool wide = constraints.maxWidth >= 900;
        final Widget list = _TraderList(
          traders: _traders,
          selected: _selectedTrader,
          coinUnit: _coinUnit,
          onSelect:
              (GtexCoinTraderProfile trader) =>
                  setState(() => _selectedTrader = trader),
        );
        final Widget detail = _TraderDetail(
          trader: _selectedTrader ?? _traders.first,
          coinUnit: _coinUnit,
          isAuthenticated: widget.isAuthenticated,
          scrollable: wide,
          onBuy: () => _openOrderSheet(direction: 'user_buys'),
          onSell: () => _openOrderSheet(direction: 'user_sells'),
          onOpenLogin: widget.onOpenLogin,
        );
        final Widget content =
            wide
                ? Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: <Widget>[
                    SizedBox(width: 360, child: list),
                    const SizedBox(width: GtexSpacing.md),
                    Expanded(child: detail),
                  ],
                )
                : ListView(
                  children: <Widget>[
                    SizedBox(height: 420, child: list),
                    const SizedBox(height: GtexSpacing.md),
                    detail,
                  ],
                );
        return Column(
          children: <Widget>[
            _CoinTraderToolbar(
              coinUnit: _coinUnit,
              isLoading: _loading,
              onCoinUnitChanged: (String value) {
                setState(() => _coinUnit = value);
                _load();
              },
              onRefresh: _load,
            ),
            const SizedBox(height: GtexSpacing.md),
            if (widget.isAuthenticated) ...<Widget>[
              SizedBox(height: 280, child: _buildMyOrdersPanel()),
              const SizedBox(height: GtexSpacing.md),
            ],
            Expanded(child: content),
          ],
        );
      },
    );
  }

  Widget _buildMyOrdersPanel() {
    if (_loadingOrders && _myOrders.isEmpty) {
      return const GtexPanel(
        title: 'My coin orders',
        accent: GtexColors.gold,
        child: Center(child: CircularProgressIndicator()),
      );
    }
    if (_ordersError != null) {
      return GtexEmptyState(
        title: 'My coin orders unavailable',
        message: _ordersError!,
        icon: Icons.receipt_long_outlined,
        accent: GtexColors.gold,
        actionLabel: 'Retry',
        onAction: _load,
      );
    }
    return _OrdersPanel(
      orders: _myOrders,
      title: 'My coin orders',
      api: _api,
      onChanged: _load,
    );
  }

  Future<void> _openOrderSheet({required String direction}) async {
    final GtexCoinTraderProfile? trader = _selectedTrader;
    if (trader == null) {
      return;
    }
    if (!widget.isAuthenticated) {
      widget.onOpenLogin?.call();
      return;
    }
    final GtexCoinTradeOrder? order =
        await showModalBottomSheet<GtexCoinTradeOrder>(
          context: context,
          isScrollControlled: true,
          backgroundColor: GtexColors.panel,
          builder:
              (BuildContext context) => _CreateCoinTradeOrderSheet(
                api: _api,
                trader: trader,
                direction: direction,
                coinUnit: _coinUnit,
              ),
        );
    if (!mounted || order == null) {
      return;
    }
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text('Coin trade ${order.id} created.')));
    _load();
  }
}

class GtexCoinTraderDashboardPanel extends StatefulWidget {
  const GtexCoinTraderDashboardPanel({
    super.key,
    required this.baseUrl,
    required this.backendMode,
    required this.accessToken,
    required this.isAuthenticated,
    this.onOpenLogin,
    this.api,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;
  final GtexCoinTraderApi? api;

  @override
  State<GtexCoinTraderDashboardPanel> createState() =>
      _GtexCoinTraderDashboardPanelState();
}

class _GtexCoinTraderDashboardPanelState
    extends State<GtexCoinTraderDashboardPanel> {
  late GtexCoinTraderApi _api;
  GtexCoinTraderProfile? _profile;
  List<GtexCoinTradeOrder> _orders = const <GtexCoinTradeOrder>[];
  bool _loading = false;
  String? _error;
  bool _canApply = false;

  @override
  void initState() {
    super.initState();
    _api = _resolveApi();
    _load();
  }

  @override
  void didUpdateWidget(covariant GtexCoinTraderDashboardPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.baseUrl != widget.baseUrl ||
        oldWidget.backendMode != widget.backendMode ||
        oldWidget.accessToken != widget.accessToken ||
        oldWidget.api != widget.api) {
      _api = _resolveApi();
      _load();
    }
  }

  GtexCoinTraderApi _resolveApi() {
    return widget.api ??
        GtexCoinTraderApi.standard(
          baseUrl: widget.baseUrl,
          accessToken: widget.accessToken,
          mode: widget.backendMode,
        );
  }

  Future<void> _load() async {
    if (!widget.isAuthenticated) {
      setState(() {
        _loading = false;
        _profile = null;
        _orders = const <GtexCoinTradeOrder>[];
        _error = null;
        _canApply = false;
      });
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
      _canApply = false;
    });
    try {
      final GtexCoinTraderProfile profile = await _api.fetchMyProfile();
      final List<GtexCoinTradeOrder> orders = await _api.listMyOrders(
        asTrader: true,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _profile = profile;
        _orders = orders;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      final bool missingProfile =
          error is GteApiException &&
          (error.statusCode == 404 || error.statusCode == 403);
      setState(() {
        _profile = null;
        _orders = const <GtexCoinTradeOrder>[];
        _canApply = missingProfile;
        _error = missingProfile ? null : _messageFor(error);
      });
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.isAuthenticated) {
      return GtexEmptyState(
        title: 'Trader dashboard locked',
        message:
            'Sign in to manage trader profile, rates, liquidity and orders.',
        icon: Icons.lock_outline,
        accent: GtexColors.gold,
        actionLabel: 'Sign in',
        onAction: widget.onOpenLogin,
      );
    }
    if (_loading && _profile == null) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return GtexEmptyState(
        title: 'Trader dashboard unavailable',
        message: _error!,
        icon: Icons.currency_exchange_outlined,
        accent: GtexColors.gold,
        actionLabel: 'Retry',
        onAction: _load,
      );
    }
    if (_profile == null || _canApply) {
      return _TraderApplyPanel(api: _api, onApplied: _load);
    }

    return ListView(
      children: <Widget>[
        _ProfileSummaryPanel(profile: _profile!),
        const SizedBox(height: GtexSpacing.md),
        _RateEditorPanel(api: _api, profile: _profile!, onSaved: _load),
        const SizedBox(height: GtexSpacing.md),
        _OrdersPanel(
          orders: _orders,
          title: 'Trader orders',
          api: _api,
          onChanged: _load,
          isTrader: true,
        ),
      ],
    );
  }
}

class GtexCoinTraderAdminScreen extends StatefulWidget {
  const GtexCoinTraderAdminScreen({
    super.key,
    required this.baseUrl,
    required this.backendMode,
    required this.accessToken,
    required this.isAdmin,
    this.api,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final bool isAdmin;
  final GtexCoinTraderApi? api;

  @override
  State<GtexCoinTraderAdminScreen> createState() =>
      _GtexCoinTraderAdminScreenState();
}

class _GtexCoinTraderAdminScreenState extends State<GtexCoinTraderAdminScreen> {
  late GtexCoinTraderApi _api;
  List<GtexCoinTraderProfile> _profiles = const <GtexCoinTraderProfile>[];
  List<GtexCoinTradeOrder> _orders = const <GtexCoinTradeOrder>[];
  GtexCoinTraderProfile? _selected;
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _api = _resolveApi();
    _load();
  }

  @override
  void didUpdateWidget(covariant GtexCoinTraderAdminScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.baseUrl != widget.baseUrl ||
        oldWidget.backendMode != widget.backendMode ||
        oldWidget.accessToken != widget.accessToken ||
        oldWidget.api != widget.api) {
      _api = _resolveApi();
      _load();
    }
  }

  GtexCoinTraderApi _resolveApi() {
    return widget.api ??
        GtexCoinTraderApi.standard(
          baseUrl: widget.baseUrl,
          accessToken: widget.accessToken,
          mode: widget.backendMode,
        );
  }

  Future<void> _load() async {
    if (!widget.isAdmin) {
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final List<GtexCoinTraderProfile> profiles =
          await _api.adminListTraders();
      final List<GtexCoinTradeOrder> orders = await _api.adminListOrders();
      if (!mounted) {
        return;
      }
      setState(() {
        _profiles = profiles;
        _orders = orders;
        _selected =
            profiles.contains(_selected)
                ? _selected
                : profiles.isEmpty
                ? null
                : profiles.first;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() => _error = _messageFor(error));
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.isAdmin) {
      return const GtexEmptyState(
        title: 'Admin access required',
        message: 'Coin trader approvals and disputes require an admin session.',
        icon: Icons.admin_panel_settings_outlined,
        accent: GtexColors.gold,
      );
    }
    return GtexMasterDetailScaffold(
      title: 'Coin Trader Ops',
      subtitle: 'Approvals, freezes, liquidity checks and escrow disputes.',
      accent: GtexColors.gold,
      mobileLeftTitle: 'Trader ops',
      actions: <Widget>[
        IconButton.filledTonal(
          tooltip: 'Refresh coin traders',
          onPressed: _loading ? null : _load,
          icon: const Icon(Icons.sync),
        ),
      ],
      leftPanel:
          _profiles.isEmpty
              ? const GtexEmptyState(
                title: 'No trader profiles',
                message: 'Applications will appear after users submit them.',
                icon: Icons.manage_accounts_outlined,
                accent: GtexColors.gold,
              )
              : _TraderList(
                traders: _profiles,
                selected: _selected,
                coinUnit: 'COIN',
                onSelect:
                    (GtexCoinTraderProfile trader) =>
                        setState(() => _selected = trader),
              ),
      detail:
          _error != null
              ? GtexEmptyState(
                title: 'Admin feed unavailable',
                message: _error!,
                icon: Icons.warning_amber_outlined,
                accent: GtexColors.gold,
                actionLabel: 'Retry',
                onAction: _load,
              )
              : _selected == null
              ? const GtexEmptyState(
                title: 'No trader selected',
                message: 'Select a trader application when one is available.',
                icon: Icons.verified_outlined,
                accent: GtexColors.gold,
              )
              : _AdminTraderDetail(
                trader: _selected!,
                api: _api,
                onChanged: _load,
              ),
      rightPanel: _OrdersPanel(
        orders: _orders,
        title: 'Escrow orders',
        api: _api,
        onChanged: _load,
        isAdmin: true,
      ),
    );
  }
}

class _CoinTraderToolbar extends StatelessWidget {
  const _CoinTraderToolbar({
    required this.coinUnit,
    required this.isLoading,
    required this.onCoinUnitChanged,
    required this.onRefresh,
  });

  final String coinUnit;
  final bool isLoading;
  final ValueChanged<String> onCoinUnitChanged;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: <Widget>[
        SegmentedButton<String>(
          segments: const <ButtonSegment<String>>[
            ButtonSegment<String>(
              value: 'COIN',
              label: Text('GTEX Coin'),
              icon: Icon(Icons.monetization_on_outlined),
            ),
            ButtonSegment<String>(
              value: 'CREDIT',
              label: Text('Fan Coin'),
              icon: Icon(Icons.stars_outlined),
            ),
          ],
          selected: <String>{coinUnit},
          onSelectionChanged:
              (Set<String> values) => onCoinUnitChanged(values.first),
        ),
        const Spacer(),
        IconButton.filledTonal(
          tooltip: 'Refresh coin traders',
          onPressed: isLoading ? null : onRefresh,
          icon: const Icon(Icons.sync),
        ),
      ],
    );
  }
}

class _TraderList extends StatelessWidget {
  const _TraderList({
    required this.traders,
    required this.selected,
    required this.coinUnit,
    required this.onSelect,
  });

  final List<GtexCoinTraderProfile> traders;
  final GtexCoinTraderProfile? selected;
  final String coinUnit;
  final ValueChanged<GtexCoinTraderProfile> onSelect;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      itemCount: traders.length,
      separatorBuilder: (BuildContext context, int index) {
        return const SizedBox(height: GtexSpacing.sm);
      },
      itemBuilder: (BuildContext context, int index) {
        final GtexCoinTraderProfile trader = traders[index];
        final GtexCoinTraderRate? rate = trader.primaryRateFor(coinUnit);
        return GtexPanel(
          isSelected: trader.id == selected?.id,
          accent: GtexColors.gold,
          padding: const EdgeInsets.all(GtexSpacing.sm),
          onTap: () => onSelect(trader),
          child: Row(
            children: <Widget>[
              CircleAvatar(
                backgroundColor: GtexColors.gold.withValues(alpha: 0.14),
                foregroundColor: GtexColors.gold,
                child: const Icon(Icons.currency_exchange_outlined),
              ),
              const SizedBox(width: GtexSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Row(
                      children: <Widget>[
                        Expanded(
                          child: Text(
                            trader.displayName,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: GtexColors.text,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                        ),
                        GtexStatusChip(
                          label: trader.status,
                          compact: true,
                          tone:
                              trader.isApproved
                                  ? GtexStatusTone.success
                                  : GtexStatusTone.warning,
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      [
                        trader.countryCode ?? 'Global',
                        _titleCase(trader.tier),
                        if (rate != null)
                          '${_money(rate.sellRateFiat)} ${rate.fiatCurrency}',
                      ].join(' - '),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: GtexColors.textMuted),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _TraderDetail extends StatelessWidget {
  const _TraderDetail({
    required this.trader,
    required this.coinUnit,
    required this.isAuthenticated,
    required this.onBuy,
    required this.onSell,
    this.scrollable = true,
    this.onOpenLogin,
  });

  final GtexCoinTraderProfile trader;
  final String coinUnit;
  final bool isAuthenticated;
  final VoidCallback onBuy;
  final VoidCallback onSell;
  final bool scrollable;
  final VoidCallback? onOpenLogin;

  @override
  Widget build(BuildContext context) {
    final GtexCoinTraderRate? rate = trader.primaryRateFor(coinUnit);
    final List<Widget> children = <Widget>[
      GtexPanel(
        title: trader.displayName,
        subtitle: '${trader.countryCode ?? 'Global'} liquidity partner',
        accent: GtexColors.gold,
        trailing: GtexStatusChip(
          label: trader.isApproved ? 'Verified' : trader.status,
          icon: Icons.verified_outlined,
          tone:
              trader.isApproved
                  ? GtexStatusTone.success
                  : GtexStatusTone.warning,
        ),
        child: Wrap(
          spacing: GtexSpacing.md,
          runSpacing: GtexSpacing.md,
          children: <Widget>[
            _metric(
              'Completion',
              '${trader.completionRate.toStringAsFixed(0)}%',
            ),
            _metric(
              'Avg speed',
              '${trader.averageReleaseMinutes.toStringAsFixed(0)}m',
            ),
            _metric('Rating', trader.rating.toStringAsFixed(1)),
            _metric('Liquidity', _coin(trader.totalLiquidity)),
          ],
        ),
      ),
      const SizedBox(height: GtexSpacing.md),
      if (rate != null) ...<Widget>[
        GtexPanel(
          title: rate.coinLabel,
          subtitle: '${rate.fiatCurrency} live OTC quote',
          accent: GtexColors.gold,
          child: Wrap(
            spacing: GtexSpacing.md,
            runSpacing: GtexSpacing.md,
            children: <Widget>[
              _metric('Trader buys', _money(rate.buyRateFiat)),
              _metric('Trader sells', _money(rate.sellRateFiat)),
              _metric('Min', _coin(rate.minCoinAmount)),
              _metric('Max', _coin(rate.maxCoinAmount)),
              _metric('Available', _coin(rate.availableLiquidity)),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
      ],
      GtexPanel(
        title: 'Payment terms',
        accent: GtexColors.gold,
        child: _ChipWrap(
          labels: <String>[
            ...trader.paymentMethodLabels,
            ...trader.bankAccountLabels,
            ...trader.termLabels,
          ],
          fallback: 'No public payment terms yet.',
        ),
      ),
      const SizedBox(height: GtexSpacing.md),
      Wrap(
        spacing: GtexSpacing.sm,
        runSpacing: GtexSpacing.sm,
        children: <Widget>[
          GtexActionButton(
            label: isAuthenticated ? 'Buy coins' : 'Sign in',
            icon: isAuthenticated ? Icons.call_received : Icons.login,
            accent: GtexColors.gold,
            onPressed: isAuthenticated ? onBuy : onOpenLogin,
          ),
          GtexButton(
            label: 'Sell coins',
            icon: Icons.call_made,
            variant: GtexButtonVariant.secondary,
            onPressed: isAuthenticated ? onSell : onOpenLogin,
          ),
        ],
      ),
    ];
    if (scrollable) {
      return ListView(children: children);
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: children,
    );
  }

  Widget _metric(String label, String value) {
    return SizedBox(
      width: 150,
      child: GtexMetricTile(
        label: label,
        value: value,
        icon: Icons.toll_outlined,
        accent: GtexColors.gold,
      ),
    );
  }
}

class _CreateCoinTradeOrderSheet extends StatefulWidget {
  const _CreateCoinTradeOrderSheet({
    required this.api,
    required this.trader,
    required this.direction,
    required this.coinUnit,
  });

  final GtexCoinTraderApi api;
  final GtexCoinTraderProfile trader;
  final String direction;
  final String coinUnit;

  @override
  State<_CreateCoinTradeOrderSheet> createState() =>
      _CreateCoinTradeOrderSheetState();
}

class _CreateCoinTradeOrderSheetState
    extends State<_CreateCoinTradeOrderSheet> {
  final TextEditingController _amountController = TextEditingController();
  final TextEditingController _paymentMethodController =
      TextEditingController();
  bool _submitting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    final List<String> methods = widget.trader.paymentMethodLabels;
    if (methods.isNotEmpty) {
      _paymentMethodController.text = methods.first;
    }
    _amountController.addListener(_refreshQuote);
  }

  @override
  void dispose() {
    _amountController.removeListener(_refreshQuote);
    _amountController.dispose();
    _paymentMethodController.dispose();
    super.dispose();
  }

  void _refreshQuote() {
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final GtexCoinTraderRate? rate = widget.trader.primaryRateFor(
      widget.coinUnit,
    );
    final double amount = double.tryParse(_amountController.text.trim()) ?? 0;
    final double quotedRate =
        widget.direction == 'user_sells'
            ? rate?.buyRateFiat ?? 0
            : rate?.sellRateFiat ?? 0;
    final double fiatTotal = amount * quotedRate;
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.only(
          left: GtexSpacing.lg,
          right: GtexSpacing.lg,
          top: GtexSpacing.lg,
          bottom: MediaQuery.viewInsetsOf(context).bottom + GtexSpacing.lg,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              widget.direction == 'user_sells' ? 'Sell coins' : 'Buy coins',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                color: GtexColors.text,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: GtexSpacing.xs),
            Text(
              '${widget.trader.displayName} - ${rate?.fiatCurrency ?? 'NGN'} escrow order',
              style: const TextStyle(color: GtexColors.textMuted),
            ),
            const SizedBox(height: GtexSpacing.md),
            if (rate != null) ...<Widget>[
              Wrap(
                spacing: GtexSpacing.sm,
                runSpacing: GtexSpacing.sm,
                children: <Widget>[
                  GtexStatusChip(
                    label: 'Rate ${_money(quotedRate)} ${rate.fiatCurrency}',
                    icon: Icons.price_check_outlined,
                    compact: true,
                  ),
                  GtexStatusChip(
                    label:
                        'Limits ${_coin(rate.minCoinAmount)}-${_coin(rate.maxCoinAmount)}',
                    icon: Icons.rule_outlined,
                    compact: true,
                  ),
                  if (fiatTotal > 0)
                    GtexStatusChip(
                      label: 'Quote ${_money(fiatTotal)} ${rate.fiatCurrency}',
                      icon: Icons.receipt_long_outlined,
                      compact: true,
                    ),
                ],
              ),
              const SizedBox(height: GtexSpacing.sm),
            ],
            TextField(
              controller: _amountController,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              decoration: const InputDecoration(
                labelText: 'Coin amount',
                prefixIcon: Icon(Icons.toll_outlined),
              ),
            ),
            const SizedBox(height: GtexSpacing.sm),
            if (widget.trader.termLabels.isNotEmpty ||
                widget.trader.bankAccountLabels.isNotEmpty) ...<Widget>[
              _ChipWrap(
                labels: <String>[
                  ...widget.trader.bankAccountLabels,
                  ...widget.trader.termLabels,
                ],
                fallback: 'No payment terms published.',
              ),
              const SizedBox(height: GtexSpacing.sm),
            ],
            TextField(
              controller: _paymentMethodController,
              decoration: const InputDecoration(
                labelText: 'Payment method',
                prefixIcon: Icon(Icons.account_balance_outlined),
              ),
            ),
            if (_error != null) ...<Widget>[
              const SizedBox(height: GtexSpacing.sm),
              Text(_error!, style: const TextStyle(color: GtexColors.red)),
            ],
            const SizedBox(height: GtexSpacing.lg),
            Row(
              children: <Widget>[
                TextButton(
                  onPressed:
                      _submitting ? null : () => Navigator.of(context).pop(),
                  child: const Text('Cancel'),
                ),
                const Spacer(),
                GtexActionButton(
                  label: _submitting ? 'Creating' : 'Create order',
                  icon: Icons.lock_clock_outlined,
                  accent: GtexColors.gold,
                  onPressed: _submitting ? null : _submit,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _submit() async {
    final double? amount = double.tryParse(_amountController.text.trim());
    if (amount == null || amount <= 0) {
      setState(() => _error = 'Enter a valid coin amount.');
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final GtexCoinTradeOrder order = await widget.api.createOrder(
        traderProfileId: widget.trader.id,
        direction: widget.direction,
        coinUnit: widget.coinUnit,
        coinAmount: amount,
        fiatCurrency:
            widget.trader.primaryRateFor(widget.coinUnit)?.fiatCurrency ??
            'NGN',
        paymentMethod: _paymentMethodController.text.trim(),
      );
      if (!mounted) {
        return;
      }
      Navigator.of(context).pop(order);
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() => _error = _messageFor(error));
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }
}

class _TraderApplyPanel extends StatefulWidget {
  const _TraderApplyPanel({required this.api, required this.onApplied});

  final GtexCoinTraderApi api;
  final VoidCallback onApplied;

  @override
  State<_TraderApplyPanel> createState() => _TraderApplyPanelState();
}

class _TraderApplyPanelState extends State<_TraderApplyPanel> {
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _countryController = TextEditingController();
  final TextEditingController _paymentMethodsController = TextEditingController(
    text: 'Bank transfer',
  );
  final TextEditingController _banksController = TextEditingController();
  final TextEditingController _workingHoursController = TextEditingController();
  bool _sameNameOnly = true;
  bool _kycRequired = true;
  bool _proofRequired = true;
  bool _submitting = false;
  String? _error;

  @override
  void dispose() {
    _nameController.dispose();
    _countryController.dispose();
    _paymentMethodsController.dispose();
    _banksController.dispose();
    _workingHoursController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: <Widget>[
        GtexPanel(
          title: 'Trader application',
          subtitle: 'Applications require admin approval before trading.',
          accent: GtexColors.gold,
          child: Column(
            children: <Widget>[
              TextField(
                controller: _nameController,
                decoration: const InputDecoration(
                  labelText: 'Display name',
                  prefixIcon: Icon(Icons.badge_outlined),
                ),
              ),
              const SizedBox(height: GtexSpacing.sm),
              TextField(
                controller: _countryController,
                decoration: const InputDecoration(
                  labelText: 'Country code',
                  prefixIcon: Icon(Icons.flag_outlined),
                ),
              ),
              const SizedBox(height: GtexSpacing.sm),
              TextField(
                controller: _paymentMethodsController,
                decoration: const InputDecoration(
                  labelText: 'Payment methods',
                  prefixIcon: Icon(Icons.payments_outlined),
                  helperText: 'Separate multiple methods with commas',
                ),
              ),
              const SizedBox(height: GtexSpacing.sm),
              TextField(
                controller: _banksController,
                decoration: const InputDecoration(
                  labelText: 'Supported banks',
                  prefixIcon: Icon(Icons.account_balance_outlined),
                  helperText: 'Separate multiple banks with commas',
                ),
              ),
              const SizedBox(height: GtexSpacing.sm),
              TextField(
                controller: _workingHoursController,
                decoration: const InputDecoration(
                  labelText: 'Working hours',
                  prefixIcon: Icon(Icons.schedule_outlined),
                ),
              ),
              const SizedBox(height: GtexSpacing.sm),
              SwitchListTile.adaptive(
                value: _sameNameOnly,
                onChanged:
                    (bool value) => setState(() => _sameNameOnly = value),
                title: const Text('Same-name account only'),
                secondary: const Icon(Icons.verified_user_outlined),
              ),
              SwitchListTile.adaptive(
                value: _kycRequired,
                onChanged: (bool value) => setState(() => _kycRequired = value),
                title: const Text('KYC required'),
                secondary: const Icon(Icons.assignment_ind_outlined),
              ),
              SwitchListTile.adaptive(
                value: _proofRequired,
                onChanged:
                    (bool value) => setState(() => _proofRequired = value),
                title: const Text('Payment proof required'),
                secondary: const Icon(Icons.upload_file_outlined),
              ),
              if (_error != null) ...<Widget>[
                const SizedBox(height: GtexSpacing.sm),
                Text(_error!, style: const TextStyle(color: GtexColors.red)),
              ],
              const SizedBox(height: GtexSpacing.md),
              Align(
                alignment: Alignment.centerRight,
                child: GtexActionButton(
                  label: _submitting ? 'Submitting' : 'Submit application',
                  icon: Icons.verified_user_outlined,
                  accent: GtexColors.gold,
                  onPressed: _submitting ? null : _submit,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Future<void> _submit() async {
    final String displayName = _nameController.text.trim();
    if (displayName.length < 2) {
      setState(() => _error = 'Enter a display name.');
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      await widget.api.applyTraderProfile(
        displayName: displayName,
        countryCode: _countryController.text.trim(),
        terms: <String, Object?>{
          'same_name_account_only': _sameNameOnly,
          'payment_proof_required': _proofRequired,
          'kyc_required': _kycRequired,
          if (_workingHoursController.text.trim().isNotEmpty)
            'working_hours': _workingHoursController.text.trim(),
        },
        paymentMethods: _csvLabels(_paymentMethodsController.text)
            .map(
              (String label) => <String, Object?>{
                'label': label,
                'type': _slug(label),
              },
            )
            .toList(growable: false),
        bankAccounts: _csvLabels(_banksController.text)
            .map((String bank) => <String, Object?>{'bank': bank})
            .toList(growable: false),
      );
      widget.onApplied();
    } catch (error) {
      if (mounted) {
        setState(() => _error = _messageFor(error));
      }
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }
}

class _ProfileSummaryPanel extends StatelessWidget {
  const _ProfileSummaryPanel({required this.profile});

  final GtexCoinTraderProfile profile;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      title: profile.displayName,
      subtitle:
          '${profile.countryCode ?? 'Global'} - ${_titleCase(profile.tier)}',
      accent: GtexColors.gold,
      trailing: GtexStatusChip(
        label: profile.status,
        icon: Icons.verified_outlined,
        tone:
            profile.isApproved
                ? GtexStatusTone.success
                : GtexStatusTone.warning,
      ),
      child: Wrap(
        spacing: GtexSpacing.md,
        runSpacing: GtexSpacing.md,
        children: <Widget>[
          _metric(
            'Completion',
            '${profile.completionRate.toStringAsFixed(0)}%',
          ),
          _metric(
            'Speed',
            '${profile.averageReleaseMinutes.toStringAsFixed(0)}m',
          ),
          _metric('Rating', profile.rating.toStringAsFixed(1)),
          _metric('Liquidity', _coin(profile.totalLiquidity)),
        ],
      ),
    );
  }

  Widget _metric(String label, String value) {
    return SizedBox(
      width: 160,
      child: GtexMetricTile(
        label: label,
        value: value,
        icon: Icons.insights_outlined,
        accent: GtexColors.gold,
      ),
    );
  }
}

class _RateEditorPanel extends StatefulWidget {
  const _RateEditorPanel({
    required this.api,
    required this.profile,
    required this.onSaved,
  });

  final GtexCoinTraderApi api;
  final GtexCoinTraderProfile profile;
  final VoidCallback onSaved;

  @override
  State<_RateEditorPanel> createState() => _RateEditorPanelState();
}

class _RateEditorPanelState extends State<_RateEditorPanel> {
  final TextEditingController _fiatController = TextEditingController(
    text: 'NGN',
  );
  final TextEditingController _buyController = TextEditingController();
  final TextEditingController _sellController = TextEditingController();
  final TextEditingController _minController = TextEditingController();
  final TextEditingController _maxController = TextEditingController();
  final TextEditingController _liquidityController = TextEditingController();
  String _coinUnit = 'COIN';
  bool _isActive = true;
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _primeFromRate();
  }

  @override
  void didUpdateWidget(covariant _RateEditorPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.profile != widget.profile) {
      _primeFromRate();
    }
  }

  @override
  void dispose() {
    _fiatController.dispose();
    _buyController.dispose();
    _sellController.dispose();
    _minController.dispose();
    _maxController.dispose();
    _liquidityController.dispose();
    super.dispose();
  }

  void _primeFromRate() {
    final GtexCoinTraderRate? rate = widget.profile.primaryRateFor(_coinUnit);
    _fiatController.text = rate?.fiatCurrency ?? 'NGN';
    _buyController.text =
        rate == null || rate.buyRateFiat == 0
            ? ''
            : rate.buyRateFiat.toString();
    _sellController.text =
        rate == null || rate.sellRateFiat == 0
            ? ''
            : rate.sellRateFiat.toString();
    _minController.text =
        rate == null || rate.minCoinAmount == 0
            ? ''
            : rate.minCoinAmount.toString();
    _maxController.text =
        rate == null || rate.maxCoinAmount == 0
            ? ''
            : rate.maxCoinAmount.toString();
    _liquidityController.text =
        rate == null || rate.availableLiquidity == 0
            ? ''
            : rate.availableLiquidity.toString();
    _isActive = rate?.isActive ?? true;
  }

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      title: 'Rates and liquidity',
      accent: GtexColors.gold,
      child: Column(
        children: <Widget>[
          SegmentedButton<String>(
            segments: const <ButtonSegment<String>>[
              ButtonSegment<String>(value: 'COIN', label: Text('GTEX Coin')),
              ButtonSegment<String>(value: 'CREDIT', label: Text('Fan Coin')),
            ],
            selected: <String>{_coinUnit},
            onSelectionChanged: (Set<String> value) {
              setState(() {
                _coinUnit = value.first;
                _primeFromRate();
              });
            },
          ),
          const SizedBox(height: GtexSpacing.md),
          Wrap(
            spacing: GtexSpacing.sm,
            runSpacing: GtexSpacing.sm,
            children: <Widget>[
              SizedBox(
                width: 140,
                child: TextField(
                  controller: _fiatController,
                  decoration: const InputDecoration(labelText: 'Fiat'),
                ),
              ),
              _numberField(_buyController, 'Buy rate'),
              _numberField(_sellController, 'Sell rate'),
              _numberField(_minController, 'Min order'),
              _numberField(_maxController, 'Max order'),
              _numberField(_liquidityController, 'Liquidity'),
            ],
          ),
          SwitchListTile.adaptive(
            value: _isActive,
            onChanged: (bool value) => setState(() => _isActive = value),
            title: const Text('Rate active'),
            secondary: const Icon(Icons.toggle_on_outlined),
          ),
          if (_error != null) ...<Widget>[
            const SizedBox(height: GtexSpacing.sm),
            Text(_error!, style: const TextStyle(color: GtexColors.red)),
          ],
          const SizedBox(height: GtexSpacing.md),
          Align(
            alignment: Alignment.centerRight,
            child: GtexActionButton(
              label: _saving ? 'Saving' : 'Save rate',
              icon: Icons.save_outlined,
              accent: GtexColors.gold,
              onPressed: _saving ? null : _save,
            ),
          ),
        ],
      ),
    );
  }

  Widget _numberField(TextEditingController controller, String label) {
    return SizedBox(
      width: 180,
      child: TextField(
        controller: controller,
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        decoration: InputDecoration(labelText: label),
      ),
    );
  }

  Future<void> _save() async {
    final double? buy = double.tryParse(_buyController.text.trim());
    final double? sell = double.tryParse(_sellController.text.trim());
    final double min =
        double.tryParse(
          _minController.text.trim().isEmpty ? '0' : _minController.text.trim(),
        ) ??
        -1;
    final double max =
        double.tryParse(
          _maxController.text.trim().isEmpty ? '0' : _maxController.text.trim(),
        ) ??
        -1;
    final double? liquidity = double.tryParse(_liquidityController.text.trim());
    final String fiatCurrency = _fiatController.text.trim().toUpperCase();
    if (buy == null ||
        sell == null ||
        liquidity == null ||
        min < 0 ||
        max < 0 ||
        fiatCurrency.length < 3) {
      setState(
        () => _error = 'Enter valid fiat, rate, limit and liquidity values.',
      );
      return;
    }
    if (max > 0 && min > max) {
      setState(() => _error = 'Minimum order cannot exceed maximum order.');
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await widget.api.upsertRate(
        coinUnit: _coinUnit,
        fiatCurrency: fiatCurrency,
        buyRateFiat: buy,
        sellRateFiat: sell,
        minCoinAmount: min,
        maxCoinAmount: max,
        availableLiquidity: liquidity,
        isActive: _isActive,
      );
      widget.onSaved();
    } catch (error) {
      if (mounted) {
        setState(() => _error = _messageFor(error));
      }
    } finally {
      if (mounted) {
        setState(() => _saving = false);
      }
    }
  }
}

class _AdminTraderDetail extends StatelessWidget {
  const _AdminTraderDetail({
    required this.trader,
    required this.api,
    required this.onChanged,
  });

  final GtexCoinTraderProfile trader;
  final GtexCoinTraderApi api;
  final VoidCallback onChanged;

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: <Widget>[
        _ProfileSummaryPanel(profile: trader),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Admin actions',
          accent: GtexColors.gold,
          child: Wrap(
            spacing: GtexSpacing.sm,
            runSpacing: GtexSpacing.sm,
            children: <Widget>[
              GtexActionButton(
                label: 'Approve',
                icon: Icons.verified_outlined,
                accent: GtexColors.gold,
                onPressed:
                    () => _openDecisionSheet(context, decision: 'approve'),
              ),
              GtexButton(
                label: 'Reject',
                icon: Icons.block_outlined,
                variant: GtexButtonVariant.secondary,
                onPressed:
                    () => _openDecisionSheet(context, decision: 'reject'),
              ),
              GtexButton(
                label: 'Freeze',
                icon: Icons.ac_unit_outlined,
                variant: GtexButtonVariant.secondary,
                onPressed:
                    () => _openDecisionSheet(context, decision: 'freeze'),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Future<void> _openDecisionSheet(
    BuildContext context, {
    required String decision,
  }) async {
    final bool? changed = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: GtexColors.panel,
      builder:
          (BuildContext context) => _AdminTraderDecisionSheet(
            api: api,
            trader: trader,
            decision: decision,
          ),
    );
    if (changed == true && context.mounted) {
      onChanged();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${_titleCase(decision)} decision saved.')),
      );
    }
  }
}

class _AdminTraderDecisionSheet extends StatefulWidget {
  const _AdminTraderDecisionSheet({
    required this.api,
    required this.trader,
    required this.decision,
  });

  final GtexCoinTraderApi api;
  final GtexCoinTraderProfile trader;
  final String decision;

  @override
  State<_AdminTraderDecisionSheet> createState() =>
      _AdminTraderDecisionSheetState();
}

class _AdminTraderDecisionSheetState extends State<_AdminTraderDecisionSheet> {
  final TextEditingController _noteController = TextEditingController();
  String _tier = 'bronze';
  bool _submitting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _tier = widget.trader.tier.isEmpty ? 'bronze' : widget.trader.tier;
  }

  @override
  void dispose() {
    _noteController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final bool approving = widget.decision == 'approve';
    return _OrderActionSheetFrame(
      title: '${_titleCase(widget.decision)} trader',
      subtitle: widget.trader.displayName,
      error: _error,
      submitting: _submitting,
      submitLabel:
          approving
              ? 'Approve trader'
              : '${_titleCase(widget.decision)} trader',
      submitIcon:
          approving
              ? Icons.verified_outlined
              : widget.decision == 'freeze'
              ? Icons.ac_unit_outlined
              : Icons.block_outlined,
      onSubmit: _submit,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          if (approving) ...<Widget>[
            SegmentedButton<String>(
              segments: const <ButtonSegment<String>>[
                ButtonSegment<String>(value: 'bronze', label: Text('Bronze')),
                ButtonSegment<String>(value: 'silver', label: Text('Silver')),
                ButtonSegment<String>(value: 'gold', label: Text('Gold')),
                ButtonSegment<String>(value: 'premier', label: Text('Premier')),
              ],
              selected: <String>{_tier},
              onSelectionChanged:
                  (Set<String> value) => setState(() => _tier = value.first),
            ),
            const SizedBox(height: GtexSpacing.sm),
          ],
          TextField(
            controller: _noteController,
            maxLines: 3,
            decoration: InputDecoration(
              labelText:
                  approving
                      ? 'Approval note'
                      : '${_titleCase(widget.decision)} note',
              prefixIcon: const Icon(Icons.notes_outlined),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _submit() async {
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final String note = _noteController.text.trim();
      if (widget.decision == 'approve') {
        await widget.api.adminApproveTrader(
          widget.trader.id,
          tier: _tier,
          note: note,
        );
      } else if (widget.decision == 'freeze') {
        await widget.api.adminFreezeTrader(widget.trader.id, note: note);
      } else {
        await widget.api.adminRejectTrader(widget.trader.id, note: note);
      }
      if (mounted) {
        Navigator.of(context).pop(true);
      }
    } catch (error) {
      if (mounted) {
        setState(() => _error = _messageFor(error));
      }
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }
}

class _OrdersPanel extends StatefulWidget {
  const _OrdersPanel({
    required this.orders,
    required this.title,
    required this.api,
    required this.onChanged,
    this.isAdmin = false,
    this.isTrader = false,
  });

  final List<GtexCoinTradeOrder> orders;
  final String title;
  final GtexCoinTraderApi api;
  final VoidCallback onChanged;
  final bool isAdmin;
  final bool isTrader;

  @override
  State<_OrdersPanel> createState() => _OrdersPanelState();
}

class _OrdersPanelState extends State<_OrdersPanel> {
  @override
  Widget build(BuildContext context) {
    if (widget.orders.isEmpty) {
      return GtexEmptyState(
        title: 'No ${widget.title}',
        message: 'Escrow orders will appear after a live order is opened.',
        icon: Icons.receipt_long_outlined,
        accent: GtexColors.gold,
      );
    }
    return ListView.separated(
      primary: false,
      shrinkWrap: true,
      physics: const ClampingScrollPhysics(),
      itemCount: widget.orders.length + 1,
      separatorBuilder:
          (BuildContext context, int index) =>
              const SizedBox(height: GtexSpacing.sm),
      itemBuilder: (BuildContext context, int index) {
        if (index == 0) {
          return Text(
            widget.title,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: GtexColors.text,
              fontWeight: FontWeight.w900,
            ),
          );
        }
        final GtexCoinTradeOrder order = widget.orders[index - 1];
        return GtexPanel(
          accent: GtexColors.gold,
          padding: const EdgeInsets.all(GtexSpacing.sm),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Expanded(
                    child: Text(
                      '${order.directionLabel} ${order.coinLabel}',
                      style: const TextStyle(
                        color: GtexColors.text,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ),
                  GtexStatusChip(label: order.statusLabel, compact: true),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                '${_coin(order.coinAmount)} at ${_money(order.quotedRateFiat)} ${order.fiatCurrency}',
                style: const TextStyle(color: GtexColors.textMuted),
              ),
              const SizedBox(height: 4),
              Text(
                'Fiat total ${_money(order.fiatTotal)} ${order.fiatCurrency}${order.paymentMethod == null ? '' : ' - ${order.paymentMethod}'}',
                style: const TextStyle(color: GtexColors.textMuted),
              ),
              if (order.paymentWindowExpiresAt != null ||
                  order.acceptedAt != null ||
                  order.releasedAt != null ||
                  order.cancelledAt != null ||
                  order.disputedAt != null) ...<Widget>[
                const SizedBox(height: GtexSpacing.xs),
                _ChipWrap(
                  labels: <String>[
                    if (order.paymentWindowExpiresAt != null)
                      'Pay by ${_timestamp(order.paymentWindowExpiresAt!)}',
                    if (order.acceptedAt != null)
                      'Accepted ${_timestamp(order.acceptedAt!)}',
                    if (order.releasedAt != null)
                      'Released ${_timestamp(order.releasedAt!)}',
                    if (order.cancelledAt != null)
                      'Closed ${_timestamp(order.cancelledAt!)}',
                    if (order.disputedAt != null)
                      'Disputed ${_timestamp(order.disputedAt!)}',
                  ],
                  fallback: '',
                ),
              ],
              if (order.termsSnapshotLabels.isNotEmpty) ...<Widget>[
                const SizedBox(height: GtexSpacing.xs),
                _ChipWrap(
                  labels: order.termsSnapshotLabels,
                  fallback: 'No term snapshot.',
                ),
              ],
              if (order.proof.isNotEmpty) ...<Widget>[
                const SizedBox(height: GtexSpacing.xs),
                _ChipWrap(
                  labels: <String>[
                    'Proof submitted',
                    ...order.proofLabels.take(2),
                    if (order.proofSubmittedAt != null)
                      'Proof at ${_timestamp(order.proofSubmittedAt!)}',
                  ],
                  fallback: 'Proof submitted',
                ),
              ],
              if (widget.isAdmin &&
                  (order.ledgerLabels.isNotEmpty ||
                      order.metadataLabels.isNotEmpty)) ...<Widget>[
                const SizedBox(height: GtexSpacing.xs),
                _ChipWrap(
                  labels: <String>[
                    ...order.ledgerLabels,
                    ...order.metadataLabels,
                  ],
                  fallback: 'No audit refs.',
                ),
              ],
              if (_hasActions(order)) ...<Widget>[
                const SizedBox(height: GtexSpacing.sm),
                Wrap(
                  spacing: GtexSpacing.xs,
                  runSpacing: GtexSpacing.xs,
                  children: <Widget>[
                    if (order.canAccept && widget.isTrader && !widget.isAdmin)
                      GtexActionButton(
                        label: 'Accept',
                        icon: Icons.lock_clock_outlined,
                        accent: GtexColors.gold,
                        onPressed:
                            () => _run(
                              widget.api.acceptOrder(order.id),
                              success: 'Order accepted and escrow locked.',
                            ),
                      ),
                    if (order.canSubmitProofFor(isTrader: widget.isTrader) &&
                        !widget.isAdmin)
                      GtexButton(
                        label: 'Proof',
                        icon: Icons.upload_file_outlined,
                        variant: GtexButtonVariant.secondary,
                        onPressed: () => _openProofSheet(order),
                      ),
                    if (order.canConfirmReleaseFor(isTrader: widget.isTrader) &&
                        !widget.isAdmin)
                      GtexActionButton(
                        label: 'Confirm',
                        icon: Icons.verified_outlined,
                        accent: GtexColors.gold,
                        onPressed:
                            () => _run(
                              widget.api.confirmOrder(order.id),
                              success: 'Escrow release confirmed.',
                            ),
                      ),
                    if (order.canCancel && !widget.isAdmin)
                      GtexButton(
                        label: 'Cancel',
                        icon: Icons.cancel_outlined,
                        variant: GtexButtonVariant.secondary,
                        onPressed:
                            () => _run(
                              widget.api.cancelOrder(order.id),
                              success: 'Order cancelled.',
                            ),
                      ),
                    if (order.canDispute && !widget.isAdmin)
                      GtexButton(
                        label: 'Dispute',
                        icon: Icons.report_problem_outlined,
                        variant: GtexButtonVariant.secondary,
                        onPressed: () => _openDisputeSheet(order),
                      ),
                    if (order.canAdminResolve && widget.isAdmin)
                      GtexActionButton(
                        label: 'Resolve',
                        icon: Icons.gavel_outlined,
                        accent: GtexColors.gold,
                        onPressed: () => _openAdminResolveSheet(order),
                      ),
                  ],
                ),
              ],
            ],
          ),
        );
      },
    );
  }

  bool _hasActions(GtexCoinTradeOrder order) {
    if (widget.isAdmin) {
      return order.canAdminResolve;
    }
    if (widget.isTrader && order.canAccept) {
      return true;
    }
    return order.canSubmitProofFor(isTrader: widget.isTrader) ||
        order.canConfirmReleaseFor(isTrader: widget.isTrader) ||
        order.canCancel ||
        order.canDispute;
  }

  Future<void> _run(
    Future<GtexCoinTradeOrder> action, {
    required String success,
  }) async {
    try {
      await action;
      if (!mounted) {
        return;
      }
      widget.onChanged();
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(success)));
    } catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(_messageFor(error))));
    }
  }

  Future<void> _openProofSheet(GtexCoinTradeOrder order) async {
    final bool? submitted = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: GtexColors.panel,
      builder:
          (BuildContext context) =>
              _OrderProofSheet(api: widget.api, order: order),
    );
    if (submitted == true && mounted) {
      widget.onChanged();
    }
  }

  Future<void> _openDisputeSheet(GtexCoinTradeOrder order) async {
    final bool? submitted = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: GtexColors.panel,
      builder:
          (BuildContext context) =>
              _OrderDisputeSheet(api: widget.api, order: order),
    );
    if (submitted == true && mounted) {
      widget.onChanged();
    }
  }

  Future<void> _openAdminResolveSheet(GtexCoinTradeOrder order) async {
    final bool? submitted = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: GtexColors.panel,
      builder:
          (BuildContext context) =>
              _AdminResolveOrderSheet(api: widget.api, order: order),
    );
    if (submitted == true && mounted) {
      widget.onChanged();
    }
  }
}

class _OrderProofSheet extends StatefulWidget {
  const _OrderProofSheet({required this.api, required this.order});

  final GtexCoinTraderApi api;
  final GtexCoinTradeOrder order;

  @override
  State<_OrderProofSheet> createState() => _OrderProofSheetState();
}

class _OrderProofSheetState extends State<_OrderProofSheet> {
  final TextEditingController _referenceController = TextEditingController();
  final TextEditingController _urlController = TextEditingController();
  final TextEditingController _noteController = TextEditingController();
  bool _submitting = false;
  String? _error;

  @override
  void dispose() {
    _referenceController.dispose();
    _urlController.dispose();
    _noteController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return _OrderActionSheetFrame(
      title: 'Submit payment proof',
      subtitle: '${widget.order.coinLabel} order ${widget.order.id}',
      error: _error,
      submitting: _submitting,
      submitLabel: 'Submit proof',
      submitIcon: Icons.upload_file_outlined,
      onSubmit: _submit,
      child: Column(
        children: <Widget>[
          TextField(
            controller: _referenceController,
            decoration: const InputDecoration(
              labelText: 'Proof reference',
              prefixIcon: Icon(Icons.tag_outlined),
            ),
          ),
          const SizedBox(height: GtexSpacing.sm),
          TextField(
            controller: _urlController,
            decoration: const InputDecoration(
              labelText: 'Proof URL',
              prefixIcon: Icon(Icons.link_outlined),
            ),
          ),
          const SizedBox(height: GtexSpacing.sm),
          TextField(
            controller: _noteController,
            maxLines: 3,
            decoration: const InputDecoration(
              labelText: 'Note',
              prefixIcon: Icon(Icons.notes_outlined),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _submit() async {
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      await widget.api.submitProof(
        orderId: widget.order.id,
        proofReference: _referenceController.text.trim(),
        proofUrl: _urlController.text.trim(),
        note: _noteController.text.trim(),
      );
      if (mounted) {
        Navigator.of(context).pop(true);
      }
    } catch (error) {
      if (mounted) {
        setState(() => _error = _messageFor(error));
      }
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }
}

class _OrderDisputeSheet extends StatefulWidget {
  const _OrderDisputeSheet({required this.api, required this.order});

  final GtexCoinTraderApi api;
  final GtexCoinTradeOrder order;

  @override
  State<_OrderDisputeSheet> createState() => _OrderDisputeSheetState();
}

class _OrderDisputeSheetState extends State<_OrderDisputeSheet> {
  final TextEditingController _reasonController = TextEditingController();
  bool _submitting = false;
  String? _error;

  @override
  void dispose() {
    _reasonController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return _OrderActionSheetFrame(
      title: 'Open dispute',
      subtitle: '${widget.order.coinLabel} order ${widget.order.id}',
      error: _error,
      submitting: _submitting,
      submitLabel: 'Open dispute',
      submitIcon: Icons.report_problem_outlined,
      onSubmit: _submit,
      child: TextField(
        controller: _reasonController,
        maxLines: 4,
        decoration: const InputDecoration(
          labelText: 'Dispute reason',
          prefixIcon: Icon(Icons.notes_outlined),
        ),
      ),
    );
  }

  Future<void> _submit() async {
    final String reason = _reasonController.text.trim();
    if (reason.length < 3) {
      setState(() => _error = 'Enter a dispute reason.');
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      await widget.api.disputeOrder(orderId: widget.order.id, reason: reason);
      if (mounted) {
        Navigator.of(context).pop(true);
      }
    } catch (error) {
      if (mounted) {
        setState(() => _error = _messageFor(error));
      }
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }
}

class _AdminResolveOrderSheet extends StatefulWidget {
  const _AdminResolveOrderSheet({required this.api, required this.order});

  final GtexCoinTraderApi api;
  final GtexCoinTradeOrder order;

  @override
  State<_AdminResolveOrderSheet> createState() =>
      _AdminResolveOrderSheetState();
}

class _AdminResolveOrderSheetState extends State<_AdminResolveOrderSheet> {
  final TextEditingController _noteController = TextEditingController();
  String _resolution = 'release';
  bool _submitting = false;
  String? _error;

  @override
  void dispose() {
    _noteController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return _OrderActionSheetFrame(
      title: 'Resolve escrow',
      subtitle: '${widget.order.statusLabel} - ${widget.order.coinLabel}',
      error: _error,
      submitting: _submitting,
      submitLabel: _resolution == 'release' ? 'Release coins' : 'Refund escrow',
      submitIcon:
          _resolution == 'release'
              ? Icons.verified_outlined
              : Icons.assignment_return_outlined,
      onSubmit: _submit,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          SegmentedButton<String>(
            segments: const <ButtonSegment<String>>[
              ButtonSegment<String>(
                value: 'release',
                label: Text('Release'),
                icon: Icon(Icons.verified_outlined),
              ),
              ButtonSegment<String>(
                value: 'refund',
                label: Text('Refund'),
                icon: Icon(Icons.assignment_return_outlined),
              ),
            ],
            selected: <String>{_resolution},
            onSelectionChanged:
                (Set<String> value) =>
                    setState(() => _resolution = value.first),
          ),
          const SizedBox(height: GtexSpacing.sm),
          TextField(
            controller: _noteController,
            maxLines: 3,
            decoration: const InputDecoration(
              labelText: 'Resolution note',
              prefixIcon: Icon(Icons.notes_outlined),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _submit() async {
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      await widget.api.adminResolveOrder(
        widget.order.id,
        resolution: _resolution,
        note: _noteController.text.trim(),
      );
      if (mounted) {
        Navigator.of(context).pop(true);
      }
    } catch (error) {
      if (mounted) {
        setState(() => _error = _messageFor(error));
      }
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }
}

class _OrderActionSheetFrame extends StatelessWidget {
  const _OrderActionSheetFrame({
    required this.title,
    required this.subtitle,
    required this.child,
    required this.submitting,
    required this.submitLabel,
    required this.submitIcon,
    required this.onSubmit,
    this.error,
  });

  final String title;
  final String subtitle;
  final Widget child;
  final bool submitting;
  final String submitLabel;
  final IconData submitIcon;
  final VoidCallback onSubmit;
  final String? error;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.only(
          left: GtexSpacing.lg,
          right: GtexSpacing.lg,
          top: GtexSpacing.lg,
          bottom: MediaQuery.viewInsetsOf(context).bottom + GtexSpacing.lg,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              title,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                color: GtexColors.text,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: GtexSpacing.xs),
            Text(subtitle, style: const TextStyle(color: GtexColors.textMuted)),
            const SizedBox(height: GtexSpacing.md),
            child,
            if (error != null) ...<Widget>[
              const SizedBox(height: GtexSpacing.sm),
              Text(error!, style: const TextStyle(color: GtexColors.red)),
            ],
            const SizedBox(height: GtexSpacing.lg),
            Row(
              children: <Widget>[
                TextButton(
                  onPressed:
                      submitting ? null : () => Navigator.of(context).pop(),
                  child: const Text('Close'),
                ),
                const Spacer(),
                GtexActionButton(
                  label: submitting ? 'Working' : submitLabel,
                  icon: submitIcon,
                  accent: GtexColors.gold,
                  onPressed: submitting ? null : onSubmit,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _ChipWrap extends StatelessWidget {
  const _ChipWrap({required this.labels, required this.fallback});

  final List<String> labels;
  final String fallback;

  @override
  Widget build(BuildContext context) {
    if (labels.isEmpty) {
      return Text(
        fallback,
        style: const TextStyle(color: GtexColors.textMuted),
      );
    }
    return Wrap(
      spacing: GtexSpacing.xs,
      runSpacing: GtexSpacing.xs,
      children: labels
          .map((String label) => GtexStatusChip(label: label, compact: true))
          .toList(growable: false),
    );
  }
}

String _messageFor(Object error) {
  if (error is GteApiException) {
    return error.message;
  }
  return error.toString();
}

String _money(double value) {
  final bool whole = value == value.roundToDouble();
  return value.toStringAsFixed(whole ? 0 : 2);
}

String _coin(double value) {
  final bool whole = value == value.roundToDouble();
  return value.toStringAsFixed(whole ? 0 : 2);
}

List<String> _csvLabels(String value) {
  return value
      .split(',')
      .map((String item) => item.trim())
      .where((String item) => item.isNotEmpty)
      .toList(growable: false);
}

String _slug(String value) {
  return value
      .trim()
      .toLowerCase()
      .replaceAll(RegExp(r'[^a-z0-9]+'), '_')
      .replaceAll(RegExp(r'^_+|_+$'), '');
}

String _timestamp(DateTime value) {
  final DateTime local = value.toLocal();
  String two(int input) => input.toString().padLeft(2, '0');
  return '${local.year}-${two(local.month)}-${two(local.day)} ${two(local.hour)}:${two(local.minute)}';
}

String _titleCase(String value) {
  return value
      .split(RegExp(r'[\s_]+'))
      .where((String item) => item.isNotEmpty)
      .map(
        (String item) =>
            item.substring(0, 1).toUpperCase() +
            item.substring(1).toLowerCase(),
      )
      .join(' ');
}
