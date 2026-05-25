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
    this.onTopUp,
    this.api,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;
  final VoidCallback? onTopUp;
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
    this.onTopUp,
    this.api,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;
  final VoidCallback? onTopUp;
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
      return ListView(
        children: <Widget>[
          _TraderLiquidityTopUpPanel(onTopUp: widget.onTopUp),
          const SizedBox(height: GtexSpacing.md),
          GtexEmptyState(
            title: 'Trader dashboard unavailable',
            message: _error!,
            icon: Icons.currency_exchange_outlined,
            accent: GtexColors.gold,
            actionLabel: 'Retry',
            onAction: _load,
          ),
        ],
      );
    }
    if (_profile == null || _canApply) {
      return _TraderApplyPanel(
        api: _api,
        onApplied: _load,
        onTopUp: widget.onTopUp,
      );
    }

    return ListView(
      children: <Widget>[
        _TraderLiquidityTopUpPanel(onTopUp: widget.onTopUp),
        const SizedBox(height: GtexSpacing.md),
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

class _TraderLiquidityTopUpPanel extends StatelessWidget {
  const _TraderLiquidityTopUpPanel({this.onTopUp});

  final VoidCallback? onTopUp;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      title: 'Trader liquidity',
      subtitle:
          'Fund your wallet through the same reviewed bank transfer rail.',
      accent: GtexColors.gold,
      child: Wrap(
        spacing: GtexSpacing.sm,
        runSpacing: GtexSpacing.sm,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: <Widget>[
          const GtexStatusChip(
            label: 'Manual bank transfer',
            icon: Icons.account_balance_outlined,
            color: GtexColors.gold,
          ),
          GtexActionButton(
            label: 'Request bank transfer top-up',
            icon: Icons.receipt_long_outlined,
            accent: GtexColors.gold,
            onPressed: onTopUp,
          ),
        ],
      ),
    );
  }
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
              label: Text('GTC'),
              icon: Icon(Icons.hexagon_outlined),
            ),
            ButtonSegment<String>(
              value: 'CREDIT',
              label: Text('FNC'),
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
        return _TraderCard(
          trader: trader,
          rate: trader.primaryRateFor(coinUnit),
          selected: trader.id == selected?.id,
          onTap: () => onSelect(trader),
        );
      },
    );
  }
}

class _TraderCard extends StatelessWidget {
  const _TraderCard({
    required this.trader,
    required this.rate,
    required this.selected,
    required this.onTap,
  });

  final GtexCoinTraderProfile trader;
  final GtexCoinTraderRate? rate;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final GtexCoinTraderRate? activeRate = rate;
    final bool online = trader.isOnline == true;
    final Color statusColor = online ? GtexColors.pitch : GtexColors.textMuted;
    return GtexPanel(
      isSelected: selected,
      accent: statusColor,
      padding: const EdgeInsets.all(GtexSpacing.md),
      onTap: onTap,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              _TraderAvatar(name: trader.displayName, online: online),
              const SizedBox(width: GtexSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      trader.displayName,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: GtexColors.text,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      '${trader.countryCode ?? 'Global'} desk - ${_titleCase(trader.tier)}',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: GtexColors.textMuted),
                    ),
                  ],
                ),
              ),
              _OnlinePill(trader: trader),
            ],
          ),
          const SizedBox(height: GtexSpacing.sm),
          Wrap(
            spacing: GtexSpacing.xs,
            runSpacing: GtexSpacing.xs,
            children: <Widget>[
              _InfoPill(
                icon: Icons.star_rate_rounded,
                label: _ratingLabel(trader.rating),
                color: GtexColors.gold,
              ),
              if (_isVerifiedTier(trader.tier))
                const _InfoPill(
                  icon: Icons.verified_outlined,
                  label: 'Verified',
                  color: GtexColors.pitch,
                ),
              _InfoPill(
                icon: Icons.swap_horiz_outlined,
                label: trader.completedTradesLabel,
              ),
              _InfoPill(
                icon: Icons.schedule_outlined,
                label: trader.responseTimeLabel,
              ),
              _InfoPill(
                icon: Icons.history_outlined,
                label: trader.tradingSinceLabel,
              ),
            ],
          ),
          const SizedBox(height: GtexSpacing.sm),
          if (activeRate == null)
            const Text(
              'No active quote published for this coin lane.',
              style: TextStyle(color: GtexColors.textMuted),
            )
          else ...<Widget>[
            _QuoteLine(
              icon: Icons.south_west_outlined,
              label: 'Buy ${activeRate.coinLabel}',
              value:
                  '${_money(activeRate.sellRateFiat)} ${activeRate.fiatCurrency}',
            ),
            const SizedBox(height: 4),
            _QuoteLine(
              icon: Icons.north_east_outlined,
              label: 'Sell ${activeRate.coinLabel}',
              value:
                  '${_money(activeRate.buyRateFiat)} ${activeRate.fiatCurrency}',
            ),
            const SizedBox(height: 4),
            _QuoteLine(
              icon: Icons.account_balance_wallet_outlined,
              label: 'Liquidity',
              value:
                  '${_coin(activeRate.availableLiquidity)} ${activeRate.coinLabel}',
            ),
            const SizedBox(height: GtexSpacing.sm),
            Wrap(
              spacing: GtexSpacing.xs,
              runSpacing: GtexSpacing.xs,
              children: <Widget>[
                _InfoPill(
                  icon: Icons.call_received_rounded,
                  label: 'BUY ${activeRate.coinLabel} FROM TRADER',
                  color: GtexColors.gold,
                ),
                _InfoPill(
                  icon: Icons.call_made_rounded,
                  label: 'SELL ${activeRate.coinLabel} TO TRADER',
                  color: GtexColors.pitch,
                ),
              ],
            ),
          ],
          const SizedBox(height: GtexSpacing.sm),
          Row(
            children: <Widget>[
              Expanded(
                child: Text(
                  trader.onlineLabel,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: GtexColors.textMuted),
                ),
              ),
              if (trader.activeCoinCodes.isNotEmpty)
                _CoinLaneStrip(labels: trader.activeCoinCodes),
            ],
          ),
        ],
      ),
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
        subtitle: '${trader.countryCode ?? 'Global'} football coin market desk',
        accent: trader.isOnline == true ? GtexColors.pitch : GtexColors.gold,
        trailing: _OnlinePill(trader: trader),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                _TraderAvatar(
                  name: trader.displayName,
                  online: trader.isOnline == true,
                  large: true,
                ),
                const SizedBox(width: GtexSpacing.md),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        trader.bio?.trim().isNotEmpty == true
                            ? trader.bio!.trim()
                            : 'Public trader bio not published by backend.',
                        style: const TextStyle(color: GtexColors.textMuted),
                      ),
                      const SizedBox(height: GtexSpacing.sm),
                      _ChipWrap(
                        labels: <String>[
                          _titleCase(trader.verificationLevel),
                          trader.tradingSinceLabel,
                          trader.completedTradesLabel,
                          trader.responseTimeLabel,
                        ],
                        fallback: 'Trader profile metadata not published.',
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: GtexSpacing.md),
            Wrap(
              spacing: GtexSpacing.md,
              runSpacing: GtexSpacing.md,
              children: <Widget>[
                _metric(
                  'Completion',
                  '${trader.completionRate.toStringAsFixed(0)}%',
                ),
                _metric(
                  'Release speed',
                  '${trader.averageReleaseMinutes.toStringAsFixed(0)}m',
                ),
                _metric('Rating', _ratingLabel(trader.rating)),
                _metric('Liquidity', _coin(trader.totalLiquidity)),
                _metric('Volume', _money(trader.completedVolumeFiat)),
                _metric(
                  'Dispute score',
                  trader.disputeScore.toStringAsFixed(1),
                ),
              ],
            ),
          ],
        ),
      ),
      const SizedBox(height: GtexSpacing.md),
      if (rate != null) ...<Widget>[
        GtexPanel(
          title: '${rate.coinName} (${rate.coinLabel})',
          subtitle: '${rate.fiatCurrency} controlled football liquidity quote',
          accent: GtexColors.gold,
          trailing: GtexStatusChip(
            label: rate.governanceLabel,
            icon:
                rate.isRestricted
                    ? Icons.warning_amber_outlined
                    : Icons.verified_user_outlined,
            tone:
                rate.isRestricted
                    ? GtexStatusTone.danger
                    : GtexStatusTone.success,
            compact: true,
          ),
          child: Wrap(
            spacing: GtexSpacing.md,
            runSpacing: GtexSpacing.md,
            children: <Widget>[
              _metric(
                'BUY ${rate.coinLabel} FROM TRADER',
                _money(rate.sellRateFiat),
              ),
              _metric(
                'SELL ${rate.coinLabel} TO TRADER',
                _money(rate.buyRateFiat),
              ),
              _metric('Spread', _money(rate.spreadFiat)),
              _metric(
                'TREASURY TOP-UP',
                _nullableMoney(rate.treasuryDepositRateFiat),
              ),
              _metric(
                'TREASURY WITHDRAWAL',
                _nullableMoney(rate.treasuryWithdrawalRateFiat),
              ),
              _metric('Min', _coin(rate.minCoinAmount)),
              _metric('Max', _coin(rate.maxCoinAmount)),
              _metric('Available', _coin(rate.availableLiquidity)),
            ],
          ),
        ),
        if (rate.isRestricted) ...<Widget>[
          const SizedBox(height: GtexSpacing.sm),
          GtexPanel(
            accent: GtexColors.red,
            child: _ChipWrap(
              labels: rate.governanceReasons,
              fallback: 'This trader quote is restricted by treasury policy.',
            ),
          ),
        ],
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
            label: _traderActionLabel(
              rate: rate,
              coinUnit: coinUnit,
              direction: 'user_buys',
              isAuthenticated: isAuthenticated,
            ),
            icon: isAuthenticated ? Icons.call_received : Icons.login,
            accent: GtexColors.gold,
            onPressed:
                rate?.isRestricted == true
                    ? null
                    : isAuthenticated
                    ? onBuy
                    : onOpenLogin,
          ),
          GtexButton(
            label: _traderActionLabel(
              rate: rate,
              coinUnit: coinUnit,
              direction: 'user_sells',
              isAuthenticated: isAuthenticated,
            ),
            icon: Icons.call_made,
            variant: GtexButtonVariant.secondary,
            onPressed:
                rate?.isRestricted == true
                    ? null
                    : isAuthenticated
                    ? onSell
                    : onOpenLogin,
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
    final bool rateRestricted = rate?.isRestricted == true;
    final bool userSells = widget.direction == 'user_sells';
    final String coinLabel = rate?.coinLabel ?? 'coin';
    final String fiatCurrency = rate?.fiatCurrency ?? 'NGN';
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
              userSells
                  ? 'Sell $coinLabel to ${widget.trader.displayName}'
                  : 'Buy $coinLabel from ${widget.trader.displayName}',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                color: GtexColors.text,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: GtexSpacing.xs),
            Text(
              userSells
                  ? 'You send $coinLabel into escrow; the trader pays you after acceptance.'
                  : 'The trader locks $coinLabel for you after accepting the live order.',
              style: const TextStyle(color: GtexColors.textMuted),
            ),
            const SizedBox(height: GtexSpacing.md),
            _TraderOrderSummary(
              trader: widget.trader,
              rate: rate,
              direction: widget.direction,
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
                    label: rate.governanceLabel,
                    icon:
                        rateRestricted
                            ? Icons.warning_amber_outlined
                            : Icons.verified_user_outlined,
                    tone:
                        rateRestricted
                            ? GtexStatusTone.danger
                            : GtexStatusTone.success,
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
                      label:
                          '${_coin(amount)} $coinLabel = ${_money(fiatTotal)} ${rate.fiatCurrency}',
                      icon: Icons.receipt_long_outlined,
                      compact: true,
                    ),
                ],
              ),
              const SizedBox(height: GtexSpacing.sm),
              if (rateRestricted) ...<Widget>[
                Text(
                  rate.governanceReasons.isEmpty
                      ? 'This trader quote is restricted by treasury policy.'
                      : rate.governanceReasons.join(' '),
                  style: const TextStyle(color: GtexColors.red),
                ),
                const SizedBox(height: GtexSpacing.sm),
              ],
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
            if (fiatTotal > 0) ...<Widget>[
              const SizedBox(height: GtexSpacing.xs),
              Text(
                'Live quote: ${_coin(amount)} $coinLabel = ${_money(fiatTotal)} $fiatCurrency',
                style: const TextStyle(color: GtexColors.textMuted),
              ),
            ],
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
                labelText: 'Payment rail',
                prefixIcon: Icon(Icons.account_balance_outlined),
                helperText:
                    'Use a backend-published rail. Paystack is unavailable.',
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
                  label:
                      rateRestricted
                          ? 'Rate restricted'
                          : _submitting
                          ? 'Creating'
                          : userSells
                          ? 'Initiate sale'
                          : 'Proceed to order',
                  icon: Icons.lock_clock_outlined,
                  accent: GtexColors.gold,
                  onPressed: _submitting || rateRestricted ? null : _submit,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _submit() async {
    final GtexCoinTraderRate? rate = widget.trader.primaryRateFor(
      widget.coinUnit,
    );
    if (rate?.isRestricted == true) {
      setState(
        () =>
            _error =
                rate!.governanceReasons.isEmpty
                    ? 'This trader quote is restricted by treasury policy.'
                    : rate.governanceReasons.join(' '),
      );
      return;
    }
    final double? amount = double.tryParse(_amountController.text.trim());
    if (amount == null || amount <= 0) {
      setState(() => _error = 'Enter a valid coin amount.');
      return;
    }
    if (rate != null) {
      if (rate.minCoinAmount > 0 && amount < rate.minCoinAmount) {
        setState(
          () =>
              _error =
                  'Minimum order is ${_coin(rate.minCoinAmount)} ${rate.coinLabel}.',
        );
        return;
      }
      if (rate.maxCoinAmount > 0 && amount > rate.maxCoinAmount) {
        setState(
          () =>
              _error =
                  'Maximum order is ${_coin(rate.maxCoinAmount)} ${rate.coinLabel}.',
        );
        return;
      }
      if (widget.direction == 'user_buys' &&
          rate.availableLiquidity > 0 &&
          amount > rate.availableLiquidity) {
        setState(
          () =>
              _error =
                  'Trader has ${_coin(rate.availableLiquidity)} ${rate.coinLabel} available.',
        );
        return;
      }
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
  const _TraderApplyPanel({
    required this.api,
    required this.onApplied,
    this.onTopUp,
  });

  final GtexCoinTraderApi api;
  final VoidCallback onApplied;
  final VoidCallback? onTopUp;

  @override
  State<_TraderApplyPanel> createState() => _TraderApplyPanelState();
}

class _TraderApplyPanelState extends State<_TraderApplyPanel> {
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _bioController = TextEditingController();
  final TextEditingController _countryController = TextEditingController();
  final TextEditingController _paymentMethodsController = TextEditingController(
    text: 'Bank transfer',
  );
  final TextEditingController _banksController = TextEditingController();
  final TextEditingController _workingHoursController = TextEditingController();
  final Set<String> _preferredCoinUnits = <String>{'COIN', 'CREDIT'};
  bool _sameNameOnly = true;
  bool _kycRequired = true;
  bool _proofRequired = true;
  bool _submitting = false;
  String? _error;

  @override
  void dispose() {
    _nameController.dispose();
    _bioController.dispose();
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
        _TraderLiquidityTopUpPanel(onTopUp: widget.onTopUp),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Become a coin trader',
          subtitle:
              'Apply to operate a live GTC/FNC desk. Admin approval unlocks marketplace visibility.',
          accent: GtexColors.gold,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const _ApplicationStepHeader(
                step: '01',
                title: 'Marketplace identity',
                body:
                    'This is the public desk identity buyers and sellers will see.',
              ),
              TextField(
                controller: _nameController,
                decoration: const InputDecoration(
                  labelText: 'Display name',
                  prefixIcon: Icon(Icons.badge_outlined),
                ),
              ),
              const SizedBox(height: GtexSpacing.sm),
              TextField(
                controller: _bioController,
                maxLength: 160,
                decoration: const InputDecoration(
                  labelText: 'Trader bio',
                  prefixIcon: Icon(Icons.notes_outlined),
                  helperText: 'Optional. Keep it specific: desk, hours, rails.',
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
              const _ApplicationStepHeader(
                step: '02',
                title: 'Coin lanes',
                body:
                    'Choose which live coin markets this desk wants to quote.',
              ),
              Wrap(
                spacing: GtexSpacing.xs,
                runSpacing: GtexSpacing.xs,
                children: <Widget>[
                  FilterChip(
                    selected: _preferredCoinUnits.contains('COIN'),
                    label: const Text('GTC'),
                    avatar: const Icon(Icons.hexagon_outlined, size: 16),
                    onSelected:
                        (bool selected) =>
                            _togglePreferredCoin('COIN', selected),
                  ),
                  FilterChip(
                    selected: _preferredCoinUnits.contains('CREDIT'),
                    label: const Text('FNC'),
                    avatar: const Icon(Icons.stars_outlined, size: 16),
                    onSelected:
                        (bool selected) =>
                            _togglePreferredCoin('CREDIT', selected),
                  ),
                ],
              ),
              const SizedBox(height: GtexSpacing.sm),
              const _ApplicationStepHeader(
                step: '03',
                title: 'Settlement rails',
                body:
                    'Publish only the bank/payment rails you can support in live trading.',
              ),
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
              _SafeSwitchTile(
                value: _sameNameOnly,
                onChanged:
                    (bool value) => setState(() => _sameNameOnly = value),
                title: const Text('Same-name account only'),
                secondary: const Icon(Icons.verified_user_outlined),
              ),
              _SafeSwitchTile(
                value: _kycRequired,
                onChanged: (bool value) => setState(() => _kycRequired = value),
                title: const Text('KYC required'),
                secondary: const Icon(Icons.assignment_ind_outlined),
              ),
              _SafeSwitchTile(
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
    if (_preferredCoinUnits.isEmpty) {
      setState(() => _error = 'Choose at least one coin lane.');
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
        metadata: <String, Object?>{
          if (_bioController.text.trim().isNotEmpty)
            'bio': _bioController.text.trim(),
          'preferred_coin_units': _preferredCoinUnits.toList(growable: false),
          if (_workingHoursController.text.trim().isNotEmpty)
            'working_hours': _workingHoursController.text.trim(),
        },
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

  void _togglePreferredCoin(String coinUnit, bool selected) {
    setState(() {
      if (selected) {
        _preferredCoinUnits.add(coinUnit);
      } else {
        _preferredCoinUnits.remove(coinUnit);
      }
    });
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
          '${profile.countryCode ?? 'Global'} - ${_titleCase(profile.tier)} - ${profile.onlineLabel}',
      accent: profile.isOnline == true ? GtexColors.pitch : GtexColors.gold,
      trailing: _OnlinePill(trader: profile),
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
          _metric('Trades', profile.completedTrades?.toString() ?? '--'),
          _metric('Response', profile.responseTimeLabel),
          _metric('Verification', _titleCase(profile.verificationLevel)),
          _metric('Volume', _money(profile.completedVolumeFiat)),
          _metric('Dispute score', profile.disputeScore.toStringAsFixed(1)),
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
    final GtexCoinTraderRate? selectedRate = widget.profile.primaryRateFor(
      _coinUnit,
    );
    final List<String> guardrailLabels = _guardrailLabels(selectedRate);
    return GtexPanel(
      title: 'Rates and liquidity',
      accent: GtexColors.gold,
      child: Column(
        children: <Widget>[
          SegmentedButton<String>(
            segments: const <ButtonSegment<String>>[
              ButtonSegment<String>(
                value: 'COIN',
                label: Text('GTC'),
                icon: Icon(Icons.hexagon_outlined),
              ),
              ButtonSegment<String>(
                value: 'CREDIT',
                label: Text('FNC'),
                icon: Icon(Icons.stars_outlined),
              ),
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
          if (guardrailLabels.isNotEmpty) ...<Widget>[
            Align(
              alignment: Alignment.centerLeft,
              child: _ChipWrap(
                labels: guardrailLabels,
                fallback: 'No treasury guardrails published yet.',
              ),
            ),
            const SizedBox(height: GtexSpacing.md),
          ],
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
              _numberField(_buyController, 'Buy rate from user'),
              _numberField(_sellController, 'Sell rate to user'),
              _numberField(_minController, 'Min order'),
              _numberField(_maxController, 'Max order'),
              _numberField(_liquidityController, 'Liquidity'),
            ],
          ),
          _SafeSwitchTile(
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

  List<String> _guardrailLabels(GtexCoinTraderRate? rate) {
    if (_coinUnit != 'COIN') {
      return const <String>['FNC rates are separate from GTC'];
    }
    final List<String> labels = <String>[];
    final GtexCoinTraderRate? selectedRate = rate;
    final double? minBuy = selectedRate?.minTraderBuyRateFiat;
    final double? maxBuy = selectedRate?.maxTraderBuyRateFiat;
    final double? minSell = selectedRate?.minTraderSellRateFiat;
    final double? maxSell = selectedRate?.maxTraderSellRateFiat;
    final double? maxSpread = selectedRate?.maxTraderSpreadFiat;
    final double? treasuryDeposit = selectedRate?.treasuryDepositRateFiat;
    final double? treasuryWithdrawal = selectedRate?.treasuryWithdrawalRateFiat;
    if (minBuy != null && maxBuy != null) {
      labels.add('Buy from user ${_money(minBuy)}-${_money(maxBuy)}');
    }
    if (minSell != null && maxSell != null) {
      labels.add('Sell to user ${_money(minSell)}-${_money(maxSell)}');
    }
    if (maxSpread != null) {
      labels.add('Max spread ${_money(maxSpread)}');
    }
    if (treasuryDeposit != null) {
      labels.add('Treasury top-up ${_money(treasuryDeposit)}');
    }
    if (treasuryWithdrawal != null) {
      labels.add('Treasury withdrawal ${_money(treasuryWithdrawal)}');
    }
    if (labels.isEmpty) {
      labels.addAll(const <String>[
        'Default buy from user 820-890',
        'Default sell to user 900-980',
        'Default max spread 120',
      ]);
    }
    return labels;
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

class _TraderAvatar extends StatelessWidget {
  const _TraderAvatar({
    required this.name,
    required this.online,
    this.large = false,
  });

  final String name;
  final bool online;
  final bool large;

  @override
  Widget build(BuildContext context) {
    final double size = large ? 64 : 40;
    return Stack(
      clipBehavior: Clip.none,
      children: <Widget>[
        Container(
          width: size,
          height: size,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: GtexColors.gold.withValues(alpha: 0.14),
            borderRadius: BorderRadius.circular(large ? 18 : 12),
            border: Border.all(color: GtexColors.gold.withValues(alpha: 0.38)),
          ),
          child: Text(
            _initials(name),
            style: TextStyle(
              color: GtexColors.gold,
              fontSize: large ? 22 : 14,
              fontWeight: FontWeight.w900,
            ),
          ),
        ),
        Positioned(
          right: -2,
          bottom: -2,
          child: Container(
            width: large ? 16 : 12,
            height: large ? 16 : 12,
            decoration: BoxDecoration(
              color: online ? GtexColors.pitch : GtexColors.textMuted,
              shape: BoxShape.circle,
              border: Border.all(color: GtexColors.panel, width: 2),
            ),
          ),
        ),
      ],
    );
  }
}

class _OnlinePill extends StatelessWidget {
  const _OnlinePill({required this.trader});

  final GtexCoinTraderProfile trader;

  @override
  Widget build(BuildContext context) {
    final bool online = trader.isOnline == true;
    return GtexStatusChip(
      label:
          online
              ? 'LIVE'
              : trader.isOnline == false
              ? 'Offline'
              : 'Status --',
      icon: online ? Icons.radio_button_checked : Icons.radio_button_unchecked,
      color: online ? GtexColors.pitch : GtexColors.textMuted,
      compact: true,
    );
  }
}

class _InfoPill extends StatelessWidget {
  const _InfoPill({
    required this.icon,
    required this.label,
    this.color = GtexColors.textMuted,
  });

  final IconData icon;
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: GtexSpacing.sm,
        vertical: 6,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.24)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(icon, size: 14, color: color),
          const SizedBox(width: 4),
          Flexible(
            fit: FlexFit.loose,
            child: Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color:
                    color == GtexColors.textMuted
                        ? GtexColors.textMuted
                        : color,
                fontWeight: FontWeight.w700,
                fontSize: 12,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _CoinLaneStrip extends StatelessWidget {
  const _CoinLaneStrip({required this.labels});

  final List<String> labels;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 4,
      children: labels
          .map((String label) {
            final bool fan = label == 'FNC';
            return Container(
              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
              decoration: BoxDecoration(
                color: (fan ? Colors.blueAccent : GtexColors.gold).withValues(
                  alpha: 0.12,
                ),
                borderRadius: BorderRadius.circular(999),
              ),
              child: Text(
                label,
                style: TextStyle(
                  color: fan ? Colors.blueAccent : GtexColors.gold,
                  fontSize: 11,
                  fontWeight: FontWeight.w900,
                ),
              ),
            );
          })
          .toList(growable: false),
    );
  }
}

class _QuoteLine extends StatelessWidget {
  const _QuoteLine({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: <Widget>[
        Icon(icon, size: 16, color: GtexColors.gold),
        const SizedBox(width: 6),
        Expanded(
          child: Text(
            label,
            style: const TextStyle(color: GtexColors.textMuted),
          ),
        ),
        Text(
          value,
          style: const TextStyle(
            color: GtexColors.text,
            fontWeight: FontWeight.w900,
          ),
        ),
      ],
    );
  }
}

class _TraderOrderSummary extends StatelessWidget {
  const _TraderOrderSummary({
    required this.trader,
    required this.rate,
    required this.direction,
  });

  final GtexCoinTraderProfile trader;
  final GtexCoinTraderRate? rate;
  final String direction;

  @override
  Widget build(BuildContext context) {
    final GtexCoinTraderRate? activeRate = rate;
    final bool userSells = direction == 'user_sells';
    return Container(
      padding: const EdgeInsets.all(GtexSpacing.md),
      decoration: BoxDecoration(
        color: GtexColors.panelStrong.withValues(alpha: 0.72),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: GtexColors.gold.withValues(alpha: 0.22)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              _TraderAvatar(
                name: trader.displayName,
                online: trader.isOnline == true,
              ),
              const SizedBox(width: GtexSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      trader.displayName,
                      style: const TextStyle(
                        color: GtexColors.text,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    Text(
                      '${_ratingLabel(trader.rating)} - ${trader.completedTradesLabel}',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: GtexColors.textMuted),
                    ),
                  ],
                ),
              ),
              _OnlinePill(trader: trader),
            ],
          ),
          const SizedBox(height: GtexSpacing.sm),
          if (activeRate == null)
            const Text(
              'This trader has not published a live quote for the selected coin.',
              style: TextStyle(color: GtexColors.textMuted),
            )
          else
            Wrap(
              spacing: GtexSpacing.sm,
              runSpacing: GtexSpacing.xs,
              children: <Widget>[
                GtexStatusChip(
                  label:
                      '${activeRate.coinLabel} available ${_coin(activeRate.availableLiquidity)}',
                  icon: Icons.account_balance_wallet_outlined,
                  compact: true,
                ),
                GtexStatusChip(
                  label:
                      userSells
                          ? 'Trader buys @ ${_money(activeRate.buyRateFiat)}'
                          : 'Trader sells @ ${_money(activeRate.sellRateFiat)}',
                  icon: Icons.price_check_outlined,
                  compact: true,
                ),
                GtexStatusChip(
                  label: trader.responseTimeLabel,
                  icon: Icons.schedule_outlined,
                  compact: true,
                ),
              ],
            ),
        ],
      ),
    );
  }
}

class _ApplicationStepHeader extends StatelessWidget {
  const _ApplicationStepHeader({
    required this.step,
    required this.title,
    required this.body,
  });

  final String step;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(
        top: GtexSpacing.sm,
        bottom: GtexSpacing.sm,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          GtexStatusChip(label: step, color: GtexColors.gold, compact: true),
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
                const SizedBox(height: 2),
                Text(body, style: const TextStyle(color: GtexColors.textMuted)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _SafeSwitchTile extends StatelessWidget {
  const _SafeSwitchTile({
    required this.value,
    required this.onChanged,
    required this.title,
    required this.secondary,
  });

  final bool value;
  final ValueChanged<bool> onChanged;
  final Widget title;
  final Widget secondary;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: SwitchListTile.adaptive(
        value: value,
        onChanged: onChanged,
        title: title,
        secondary: secondary,
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
    if (error.type == GteApiErrorType.unauthorized) {
      return 'Your session expired. Sign in again to continue.';
    }
    return error.message;
  }
  return error.toString();
}

String _money(double value) {
  final bool whole = value == value.roundToDouble();
  return value.toStringAsFixed(whole ? 0 : 2);
}

String _nullableMoney(double? value) {
  if (value == null) {
    return 'n/a';
  }
  return _money(value);
}

String _coin(double value) {
  final bool whole = value == value.roundToDouble();
  return value.toStringAsFixed(whole ? 0 : 2);
}

String _ratingLabel(double value) {
  if (value <= 0) {
    return 'Rating --';
  }
  return '${value.toStringAsFixed(1)} rating';
}

bool _isVerifiedTier(String value) {
  final String normalized = value.trim().toLowerCase();
  return normalized == 'verified' ||
      normalized == 'gold' ||
      normalized == 'platinum' ||
      normalized == 'institutional';
}

String _traderActionLabel({
  required GtexCoinTraderRate? rate,
  required String coinUnit,
  required String direction,
  required bool isAuthenticated,
}) {
  if (!isAuthenticated) {
    return 'Sign in';
  }
  final String coinLabel = rate?.coinLabel ?? _fallbackCoinLabel(coinUnit);
  if (direction == 'user_sells') {
    return 'SELL $coinLabel TO TRADER';
  }
  return 'BUY $coinLabel FROM TRADER';
}

String _fallbackCoinLabel(String coinUnit) {
  return coinUnit == 'CREDIT' ? 'FNC' : 'GTC';
}

String _initials(String value) {
  final List<String> parts = value
      .trim()
      .split(RegExp(r'\s+'))
      .where((String item) => item.isNotEmpty)
      .toList(growable: false);
  if (parts.isEmpty) {
    return 'CT';
  }
  if (parts.length == 1) {
    return parts.first
        .substring(0, parts.first.length >= 2 ? 2 : 1)
        .toUpperCase();
  }
  return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
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
