import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/trader_api.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/router/gtex_auth_routes.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';

class TraderDashboardScreen extends StatelessWidget {
  const TraderDashboardScreen({
    super.key,
    required this.controller,
    required this.config,
  });

  final GteExchangeController controller;
  final GteAppConfig config;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (BuildContext context, Widget? child) {
        final String accountType =
            controller.session?.user.accountType.trim().toLowerCase() ?? '';
        if (!controller.isAuthenticated) {
          return _TraderGate(
            title: 'Trader access required',
            message:
                'Choose Coin Trader during signup to open markets, orders, P2P, watchlists, wallet security, and analytics.',
            actionLabel: 'Choose account type',
            onAction: () => context.go(gtexAccountSelectRoute),
          );
        }
        if (accountType != 'coin_trader') {
          return _TraderGate(
            title: 'Coin trading is a separate account lane',
            message:
                'This dashboard is restricted to COIN_TRADER accounts. Football users and creators keep their own dashboards and cannot place coin-market orders here.',
            actionLabel: 'Go home',
            onAction: () => context.go('/app/home'),
          );
        }
        return _TraderDashboardSurface(
          api: TraderApi.standard(
            baseUrl: config.apiBaseUrl,
            accessToken: controller.accessToken,
            mode: config.backendMode,
            transport: controller.api.transport,
          ),
          accessToken: controller.accessToken,
        );
      },
    );
  }
}

class _TraderGate extends StatelessWidget {
  const _TraderGate({
    required this.title,
    required this.message,
    required this.actionLabel,
    required this.onAction,
  });

  final String title;
  final String message;
  final String actionLabel;
  final VoidCallback onAction;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        body: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 640),
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: GteStatePanel(
                eyebrow: 'TRADER',
                title: title,
                message: message,
                icon: Icons.candlestick_chart_outlined,
                accentColor: const Color(0xFF79A7FF),
                actionLabel: actionLabel,
                onAction: onAction,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _TraderDashboardSurface extends StatefulWidget {
  const _TraderDashboardSurface({required this.api, required this.accessToken});

  final TraderApi api;
  final String? accessToken;

  @override
  State<_TraderDashboardSurface> createState() =>
      _TraderDashboardSurfaceState();
}

class _TraderDashboardSurfaceState extends State<_TraderDashboardSurface> {
  String _selectedSection = 'Markets';
  String _selectedTimeframe = '1D';
  String _tradeTab = 'Buy';
  late Future<TraderOverview> _overviewFuture;
  late Future<TraderSecurityStatus> _securityFuture;

  static const List<String> _sections = <String>[
    'Markets',
    'Fan Coins',
    'Portfolio',
    'Wallet',
    'Buy/Sell',
    'Orders',
    'P2P',
    'Watchlist',
    'News',
    'Security',
  ];

  @override
  void initState() {
    super.initState();
    _overviewFuture = widget.api.overview();
    _securityFuture = widget.api.security();
  }

  @override
  void didUpdateWidget(covariant _TraderDashboardSurface oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.accessToken != widget.accessToken) {
      _overviewFuture = widget.api.overview();
      _securityFuture = widget.api.security();
    }
  }

  Future<void> _refreshOverview() async {
    final Future<TraderOverview> nextOverview = widget.api.overview();
    final Future<TraderSecurityStatus> nextSecurity = widget.api.security();
    setState(() => _overviewFuture = nextOverview);
    setState(() => _securityFuture = nextSecurity);
    try {
      await Future.wait<Object>(<Future<Object>>[nextOverview, nextSecurity]);
    } catch (_) {
      // FutureBuilder renders the actionable error panel.
    }
  }

  @override
  Widget build(BuildContext context) {
    final bool wide = MediaQuery.sizeOf(context).width >= 1000;
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        body: SafeArea(
          child: Row(
            children: <Widget>[
              if (wide)
                _TraderSidebar(
                  selected: _selectedSection,
                  sections: _sections,
                  onSelected:
                      (String value) =>
                          setState(() => _selectedSection = value),
                ),
              Expanded(
                child: RefreshIndicator(
                  onRefresh: _refreshOverview,
                  child: ListView(
                    padding: EdgeInsets.fromLTRB(
                      wide ? 24 : 16,
                      18,
                      wide ? 28 : 16,
                      42,
                    ),
                    children: <Widget>[
                      _TraderHeader(
                        selectedSection: _selectedSection,
                        onSecurityPressed:
                            () => setState(() => _selectedSection = 'Security'),
                      ),
                      if (!wide) ...<Widget>[
                        const SizedBox(height: 14),
                        _TraderSectionBar(
                          selected: _selectedSection,
                          sections: _sections,
                          onSelected:
                              (String value) =>
                                  setState(() => _selectedSection = value),
                        ),
                      ],
                      const SizedBox(height: 18),
                      FutureBuilder<TraderOverview>(
                        future: _overviewFuture,
                        builder: (
                          BuildContext context,
                          AsyncSnapshot<TraderOverview> snapshot,
                        ) {
                          if (snapshot.hasError && !snapshot.hasData) {
                            return GteStatePanel(
                              eyebrow: 'TRADER API',
                              title: 'Market desk unavailable',
                              message:
                                  'The trader API could not load overview data. Check the session, account type, or backend route registration.',
                              icon: Icons.cloud_off_outlined,
                              accentColor: const Color(0xFFFFD66B),
                              actionLabel: 'Retry',
                              onAction: _refreshOverview,
                            );
                          }
                          final TraderOverview? overview = snapshot.data;
                          if (overview == null) {
                            return const _TraderLoadingPanel();
                          }
                          return _TraderOverviewBody(
                            overview: overview,
                            selectedSection: _selectedSection,
                            securityFuture: _securityFuture,
                            onSecurityRetry: () {
                              setState(
                                () => _securityFuture = widget.api.security(),
                              );
                            },
                            selectedTimeframe: _selectedTimeframe,
                            onTimeframeChanged:
                                (String value) =>
                                    setState(() => _selectedTimeframe = value),
                            tradeTab: _tradeTab,
                            onTradeTabChanged:
                                (String value) =>
                                    setState(() => _tradeTab = value),
                          );
                        },
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _TraderOverviewBody extends StatelessWidget {
  const _TraderOverviewBody({
    required this.overview,
    required this.selectedSection,
    required this.securityFuture,
    required this.onSecurityRetry,
    required this.selectedTimeframe,
    required this.onTimeframeChanged,
    required this.tradeTab,
    required this.onTradeTabChanged,
  });

  final TraderOverview overview;
  final String selectedSection;
  final Future<TraderSecurityStatus> securityFuture;
  final VoidCallback onSecurityRetry;
  final String selectedTimeframe;
  final ValueChanged<String> onTimeframeChanged;
  final String tradeTab;
  final ValueChanged<String> onTradeTabChanged;

  @override
  Widget build(BuildContext context) {
    final TraderMarket? primaryMarket =
        overview.trending.isEmpty ? null : overview.trending.first;
    if (selectedSection == 'Security') {
      return FutureBuilder<TraderSecurityStatus>(
        future: securityFuture,
        builder: (
          BuildContext context,
          AsyncSnapshot<TraderSecurityStatus> snapshot,
        ) {
          if (snapshot.hasError && !snapshot.hasData) {
            return GteStatePanel(
              eyebrow: 'TRADER SECURITY',
              title: 'Security center unavailable',
              message:
                  'The trader security endpoint could not load. Check the session or backend route registration.',
              icon: Icons.security_outlined,
              accentColor: const Color(0xFFFFD66B),
              actionLabel: 'Retry',
              onAction: onSecurityRetry,
            );
          }
          final TraderSecurityStatus? security = snapshot.data;
          if (security == null) {
            return const _TraderLoadingPanel();
          }
          return _SecurityPanel(security: security);
        },
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        _TopStrip(overview: overview),
        const SizedBox(height: 18),
        _MarketGrid(overview: overview),
        const SizedBox(height: 18),
        LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            final bool split = constraints.maxWidth >= 980;
            final Widget chart = _TradingPanel(
              market: primaryMarket,
              timeframe: selectedTimeframe,
              onTimeframeChanged: onTimeframeChanged,
            );
            final Widget quickTrade = _QuickTradePanel(
              market: primaryMarket,
              selectedTab: tradeTab,
              onTabChanged: onTradeTabChanged,
            );
            if (!split) {
              return Column(
                children: <Widget>[
                  chart,
                  const SizedBox(height: 18),
                  quickTrade,
                ],
              );
            }
            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Expanded(flex: 3, child: chart),
                const SizedBox(width: 18),
                Expanded(child: quickTrade),
              ],
            );
          },
        ),
      ],
    );
  }
}

class _TraderLoadingPanel extends StatelessWidget {
  const _TraderLoadingPanel();

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      height: 260,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: tokens.panel.withValues(alpha: 0.86),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tokens.stroke.withValues(alpha: 0.55)),
      ),
      child: const Center(
        child: SizedBox(
          width: 220,
          child: LinearProgressIndicator(minHeight: 4),
        ),
      ),
    );
  }
}

class _TraderSidebar extends StatelessWidget {
  const _TraderSidebar({
    required this.selected,
    required this.sections,
    required this.onSelected,
  });

  final String selected;
  final List<String> sections;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      width: 236,
      margin: const EdgeInsets.fromLTRB(18, 18, 0, 18),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: tokens.panel.withValues(alpha: 0.88),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tokens.stroke.withValues(alpha: 0.55)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              const Icon(Icons.candlestick_chart_outlined),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  'GTEX Trader',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          for (final String section in sections)
            _TraderNavItem(
              label: section,
              selected: selected == section,
              onTap: () => onSelected(section),
            ),
        ],
      ),
    );
  }
}

class _TraderNavItem extends StatelessWidget {
  const _TraderNavItem({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final Color accent = const Color(0xFF79A7FF);
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: onTap,
        child: Container(
          height: 42,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(8),
            color:
                selected ? accent.withValues(alpha: 0.16) : Colors.transparent,
            border: Border.all(
              color:
                  selected
                      ? accent.withValues(alpha: 0.38)
                      : Colors.transparent,
            ),
          ),
          child: Row(
            children: <Widget>[
              Icon(
                _iconForSection(label),
                size: 18,
                color: selected ? accent : null,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: selected ? accent : null,
                    fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _TraderSectionBar extends StatelessWidget {
  const _TraderSectionBar({
    required this.selected,
    required this.sections,
    required this.onSelected,
  });

  final String selected;
  final List<String> sections;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 44,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: sections.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (BuildContext context, int index) {
          final String section = sections[index];
          final bool active = section == selected;
          return ChoiceChip(
            selected: active,
            label: Text(section),
            avatar: Icon(_iconForSection(section), size: 16),
            onSelected: (_) => onSelected(section),
          );
        },
      ),
    );
  }
}

class _TraderHeader extends StatelessWidget {
  const _TraderHeader({
    required this.selectedSection,
    required this.onSecurityPressed,
  });

  final String selectedSection;
  final VoidCallback onSecurityPressed;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: <Widget>[
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Trader command center',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                '$selectedSection | GTEX Coin, fan coins, P2P, wallet security',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
          ),
        ),
        FilledButton.icon(
          onPressed: onSecurityPressed,
          icon: const Icon(Icons.lock_outline),
          label: const Text('Security'),
        ),
      ],
    );
  }
}

class _TopStrip extends StatelessWidget {
  const _TopStrip({required this.overview});

  final TraderOverview overview;

  @override
  Widget build(BuildContext context) {
    final String currency = overview.profile.preferredCurrency;
    final List<_Metric> metrics = <_Metric>[
      _Metric(
        'Portfolio Value',
        _compactNumber(overview.portfolioValue),
        'GTEX',
      ),
      _Metric(
        'GTEX Coin Price',
        '${_fixedPrice(overview.gtexCoinPrice)} $currency',
        _signedPercent(_marketSignal(overview.trending)),
      ),
      _Metric('Daily P/L', _signedAmount(overview.dailyPl), 'today'),
      _Metric(
        'Wallet Balance',
        _compactNumber(overview.walletBalance),
        'ready',
      ),
      _Metric('Market Cap', _compactCurrency(overview.marketCap), currency),
      _Metric(
        'Trading Volume',
        _compactCurrency(overview.tradingVolume),
        '24h',
      ),
    ];
    return Wrap(
      spacing: 12,
      runSpacing: 12,
      children: metrics
          .map(
            (_Metric metric) =>
                SizedBox(width: 178, child: _MetricPanel(metric: metric)),
          )
          .toList(growable: false),
    );
  }
}

class _MetricPanel extends StatelessWidget {
  const _MetricPanel({required this.metric});

  final _Metric metric;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      height: 124,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: tokens.panelElevated.withValues(alpha: 0.84),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tokens.stroke.withValues(alpha: 0.55)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(metric.label, style: Theme.of(context).textTheme.labelMedium),
          const Spacer(),
          Text(
            metric.value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(
              context,
            ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w900),
          ),
          Text(
            metric.detail,
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: const Color(0xFF5FE3A1),
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}

class _MarketGrid extends StatelessWidget {
  const _MarketGrid({required this.overview});

  final TraderOverview overview;

  @override
  Widget build(BuildContext context) {
    final List<_MarketBucket> buckets = <_MarketBucket>[
      _MarketBucket(
        'Trending Coins',
        _symbols(overview.trending),
        _signedPercent(_marketSignal(overview.trending)),
      ),
      _MarketBucket(
        'Top Gainers',
        _symbols(overview.topGainers),
        _signedPercent(_marketSignal(overview.topGainers)),
      ),
      _MarketBucket(
        'Top Losers',
        _symbols(overview.topLosers),
        _signedPercent(_marketSignal(overview.topLosers)),
      ),
      _MarketBucket(
        'Most Traded Fan Coins',
        _volumeLeader(overview.mostTradedFanCoins),
        'High',
      ),
      _MarketBucket(
        'Liquidity Activity',
        '${overview.liquidityActivity.length} active markets',
        _liquiditySignal(overview.liquidityActivity),
      ),
    ];
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final int columns =
            constraints.maxWidth >= 1160
                ? 5
                : constraints.maxWidth >= 760
                ? 3
                : 1;
        final double gap = 12;
        final double width =
            (constraints.maxWidth - (gap * (columns - 1))) / columns;
        return Wrap(
          spacing: gap,
          runSpacing: gap,
          children: buckets
              .map(
                (_MarketBucket bucket) => SizedBox(
                  width: width,
                  child: _MarketBucketPanel(bucket: bucket),
                ),
              )
              .toList(growable: false),
        );
      },
    );
  }
}

class _MarketBucketPanel extends StatelessWidget {
  const _MarketBucketPanel({required this.bucket});

  final _MarketBucket bucket;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      height: 136,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        color: tokens.panel.withValues(alpha: 0.84),
        border: Border.all(color: tokens.stroke.withValues(alpha: 0.55)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(Icons.auto_graph_outlined, color: const Color(0xFFFFD66B)),
          const Spacer(),
          Text(
            bucket.title,
            style: Theme.of(
              context,
            ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w900),
          ),
          Text(bucket.summary, maxLines: 1, overflow: TextOverflow.ellipsis),
          Text(bucket.signal, style: Theme.of(context).textTheme.labelMedium),
        ],
      ),
    );
  }
}

class _TradingPanel extends StatelessWidget {
  const _TradingPanel({
    required this.market,
    required this.timeframe,
    required this.onTimeframeChanged,
  });

  final TraderMarket? market;
  final String timeframe;
  final ValueChanged<String> onTimeframeChanged;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: tokens.panel.withValues(alpha: 0.9),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tokens.stroke.withValues(alpha: 0.55)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text(
                  '${market?.symbol ?? 'GTEX'}/USD professional chart',
                  style: Theme.of(
                    context,
                  ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w900),
                ),
              ),
              SegmentedButton<String>(
                segments: const <String>['15M', '1H', '1D', '1W']
                    .map(
                      (String value) => ButtonSegment<String>(
                        value: value,
                        label: Text(value),
                      ),
                    )
                    .toList(growable: false),
                selected: <String>{timeframe},
                onSelectionChanged:
                    (Set<String> next) => onTimeframeChanged(next.first),
              ),
            ],
          ),
          const SizedBox(height: 16),
          SizedBox(
            height: 260,
            child: CustomPaint(
              painter: _CandlestickPainter(),
              child: const SizedBox.expand(),
            ),
          ),
          const SizedBox(height: 14),
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final bool split = constraints.maxWidth >= 720;
              final Widget volume = _BookPanel(
                title: 'Volume chart',
                rows: <String>[
                  '24h ${_compactCurrency(market?.volume24h ?? 0)}',
                  'Market cap ${_compactCurrency(market?.marketCap ?? 0)}',
                  'Liquidity ${market?.liquidityScore ?? 0}/100',
                ],
              );
              final double price = market?.price ?? 1.42;
              final Widget orderBook = _BookPanel(
                title: 'Order book',
                rows: <String>[
                  'Buy wall ${_fixedPrice(price * 0.985)}',
                  'Sell wall ${_fixedPrice(price * 1.015)}',
                  'Spread ${_fixedPrice(price * 0.03)}',
                ],
              );
              if (!split) {
                return Column(
                  children: <Widget>[
                    volume,
                    const SizedBox(height: 12),
                    orderBook,
                  ],
                );
              }
              return Row(
                children: <Widget>[
                  Expanded(child: volume),
                  const SizedBox(width: 12),
                  Expanded(child: orderBook),
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}

class _QuickTradePanel extends StatelessWidget {
  const _QuickTradePanel({
    required this.market,
    required this.selectedTab,
    required this.onTabChanged,
  });

  final TraderMarket? market;
  final String selectedTab;
  final ValueChanged<String> onTabChanged;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: tokens.panel.withValues(alpha: 0.9),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tokens.stroke.withValues(alpha: 0.55)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Text(
            'Quick trade',
            style: Theme.of(
              context,
            ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 14),
          SegmentedButton<String>(
            segments: const <String>['Buy', 'Sell', 'Convert']
                .map(
                  (String value) =>
                      ButtonSegment<String>(value: value, label: Text(value)),
                )
                .toList(growable: false),
            selected: <String>{selectedTab},
            onSelectionChanged: (Set<String> next) => onTabChanged(next.first),
          ),
          const SizedBox(height: 14),
          _TradeField(
            label: 'Asset',
            value: market?.displayName ?? 'GTEX Coin',
          ),
          const SizedBox(height: 10),
          const _TradeField(label: 'Amount', value: '1,000.00'),
          const SizedBox(height: 10),
          _TradeField(
            label: 'Quote',
            value: '${_fixedPrice(market?.price ?? 1.42)} USD',
          ),
          const SizedBox(height: 14),
          FilledButton.icon(
            onPressed: () {},
            icon: const Icon(Icons.lock_outline),
            label: Text('$selectedTab ${market?.symbol ?? 'GTEX'}'),
          ),
          const SizedBox(height: 14),
          const _BookPanel(
            title: 'Execution guard',
            rows: <String>[
              'TOTP required',
              'KYC must be verified',
              'Recovery phrase never stored',
            ],
          ),
        ],
      ),
    );
  }
}

class _TradeField extends StatelessWidget {
  const _TradeField({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      height: 54,
      padding: const EdgeInsets.symmetric(horizontal: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tokens.stroke.withValues(alpha: 0.55)),
      ),
      child: Row(
        children: <Widget>[
          Text(label, style: Theme.of(context).textTheme.labelMedium),
          const Spacer(),
          Text(
            value,
            style: Theme.of(
              context,
            ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w900),
          ),
        ],
      ),
    );
  }
}

class _BookPanel extends StatelessWidget {
  const _BookPanel({required this.title, required this.rows});

  final String title;
  final List<String> rows;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        color: tokens.panelElevated.withValues(alpha: 0.74),
        border: Border.all(color: tokens.stroke.withValues(alpha: 0.5)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            title,
            style: Theme.of(
              context,
            ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 8),
          for (final String row in rows)
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Text(row, maxLines: 1, overflow: TextOverflow.ellipsis),
            ),
        ],
      ),
    );
  }
}

class _SecurityPanel extends StatelessWidget {
  const _SecurityPanel({required this.security});

  final TraderSecurityStatus security;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool split = constraints.maxWidth >= 900;
        final Widget status = Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: tokens.panel.withValues(alpha: 0.9),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: tokens.stroke.withValues(alpha: 0.55)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Icon(
                    security.totpEnabled
                        ? Icons.verified_user_outlined
                        : Icons.gpp_maybe_outlined,
                    color:
                        security.totpEnabled
                            ? const Color(0xFF5FE3A1)
                            : const Color(0xFFFFD66B),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'Trader security',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.w900,
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
                  _SecurityMetric(
                    label: '2FA',
                    value: security.totpEnabled ? 'Enabled' : 'Disabled',
                    detail:
                        security.totpEnabled
                            ? 'Authenticator required'
                            : 'Setup required',
                  ),
                  _SecurityMetric(
                    label: 'Backup Codes',
                    value: security.backupCodeCount.toString(),
                    detail:
                        security.backupCodeCount > 0
                            ? 'available'
                            : 'rotate after setup',
                  ),
                  _SecurityMetric(
                    label: 'Recent Events',
                    value: security.recentEvents.length.toString(),
                    detail: 'audit trail',
                  ),
                ],
              ),
              const SizedBox(height: 16),
              _BookPanel(
                title: 'Trade gate',
                rows: <String>[
                  security.totpEnabled
                      ? '2FA enabled for orders and withdrawals'
                      : 'Enable 2FA before high-risk actions',
                  '${security.backupCodeCount} backup codes remaining',
                  'Secrets stay inside setup and verification only',
                ],
              ),
            ],
          ),
        );
        final Widget events = _SecurityEventsPanel(
          events: security.recentEvents,
        );
        if (!split) {
          return Column(
            children: <Widget>[status, const SizedBox(height: 18), events],
          );
        }
        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Expanded(child: status),
            const SizedBox(width: 18),
            Expanded(child: events),
          ],
        );
      },
    );
  }
}

class _SecurityMetric extends StatelessWidget {
  const _SecurityMetric({
    required this.label,
    required this.value,
    required this.detail,
  });

  final String label;
  final String value;
  final String detail;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 154,
      child: _MetricPanel(metric: _Metric(label, value, detail)),
    );
  }
}

class _SecurityEventsPanel extends StatelessWidget {
  const _SecurityEventsPanel({required this.events});

  final List<TraderSecurityEvent> events;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: tokens.panel.withValues(alpha: 0.9),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tokens.stroke.withValues(alpha: 0.55)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Recent security events',
            style: Theme.of(
              context,
            ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 12),
          if (events.isEmpty)
            const _BookPanel(
              title: 'Audit trail',
              rows: <String>['No recent trader security events'],
            )
          else
            for (final TraderSecurityEvent event in events.take(4)) ...<Widget>[
              _SecurityEventRow(event: event),
              const SizedBox(height: 10),
            ],
        ],
      ),
    );
  }
}

class _SecurityEventRow extends StatelessWidget {
  const _SecurityEventRow({required this.event});

  final TraderSecurityEvent event;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final String detail = <String>[
      _shortDate(event.createdAt),
      if (event.deviceLabel != null) event.deviceLabel!,
      if (event.ipAddress != null) event.ipAddress!,
    ].join(' | ');
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        color: tokens.panelElevated.withValues(alpha: 0.74),
        border: Border.all(color: tokens.stroke.withValues(alpha: 0.5)),
      ),
      child: Row(
        children: <Widget>[
          const Icon(Icons.shield_outlined, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  event.summary,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(
                    context,
                  ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w900),
                ),
                Text(
                  detail,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelMedium,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _CandlestickPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final Paint gridPaint =
        Paint()
          ..color = Colors.white.withValues(alpha: 0.08)
          ..strokeWidth = 1;
    for (int i = 1; i < 5; i++) {
      final double y = size.height * i / 5;
      canvas.drawLine(Offset(0, y), Offset(size.width, y), gridPaint);
    }

    final Paint upPaint = Paint()..color = const Color(0xFF5FE3A1);
    final Paint downPaint = Paint()..color = const Color(0xFFFF6B7A);
    final Paint wickPaint =
        Paint()
          ..color = Colors.white.withValues(alpha: 0.62)
          ..strokeWidth = 1.4;
    final int candles = 34;
    final double slot = size.width / candles;
    for (int i = 0; i < candles; i++) {
      final double wave = math.sin(i * 0.72) * 28;
      final double drift = (i - candles / 2) * -0.9;
      final double centerY = (size.height * 0.48) + wave + drift;
      final bool up = i % 3 != 0;
      final double bodyHeight = 18 + ((i * 7) % 24).toDouble();
      final double high = centerY - bodyHeight - 18 - (i % 5);
      final double low = centerY + bodyHeight + 18 + (i % 4);
      final double x = (slot * i) + (slot * 0.5);
      canvas.drawLine(
        Offset(x, high.clamp(8, size.height - 8).toDouble()),
        Offset(x, low.clamp(8, size.height - 8).toDouble()),
        wickPaint,
      );
      final Rect body = Rect.fromCenter(
        center: Offset(x, centerY.clamp(20, size.height - 20).toDouble()),
        width: math.max(5, slot * 0.42),
        height: bodyHeight,
      );
      canvas.drawRRect(
        RRect.fromRectAndRadius(body, const Radius.circular(2)),
        up ? upPaint : downPaint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _Metric {
  const _Metric(this.label, this.value, this.detail);

  final String label;
  final String value;
  final String detail;
}

class _MarketBucket {
  const _MarketBucket(this.title, this.summary, this.signal);

  final String title;
  final String summary;
  final String signal;
}

String _compactNumber(double value) {
  final double absValue = value.abs();
  final String sign = value < 0 ? '-' : '';
  if (absValue >= 1000000000) {
    return '$sign${(absValue / 1000000000).toStringAsFixed(1)}B';
  }
  if (absValue >= 1000000) {
    return '$sign${(absValue / 1000000).toStringAsFixed(1)}M';
  }
  if (absValue >= 1000) {
    return '$sign${(absValue / 1000).toStringAsFixed(1)}K';
  }
  return '$sign${absValue.toStringAsFixed(absValue >= 100 ? 0 : 2)}';
}

String _compactCurrency(double value) => '\$${_compactNumber(value)}';

String _fixedPrice(double value) => value.toStringAsFixed(value >= 10 ? 2 : 4);

String _signedAmount(double value) {
  final String sign = value >= 0 ? '+' : '-';
  return '$sign${_compactNumber(value.abs())}';
}

String _signedPercent(double value) {
  final String sign = value >= 0 ? '+' : '';
  return '$sign${value.toStringAsFixed(1)}%';
}

String _shortDate(DateTime value) {
  final DateTime local = value.toLocal();
  String twoDigits(int number) => number.toString().padLeft(2, '0');
  return '${twoDigits(local.month)}/${twoDigits(local.day)} '
      '${twoDigits(local.hour)}:${twoDigits(local.minute)}';
}

String _symbols(List<TraderMarket> markets) {
  if (markets.isEmpty) {
    return 'No active markets';
  }
  return markets.take(3).map((TraderMarket market) => market.symbol).join(', ');
}

double _marketSignal(List<TraderMarket> markets) {
  if (markets.isEmpty) {
    return 0;
  }
  final double total = markets.fold<double>(
    0,
    (double sum, TraderMarket market) => sum + market.dailyChangePercent,
  );
  return total / markets.length;
}

String _volumeLeader(List<TraderMarket> markets) {
  if (markets.isEmpty) {
    return 'No fan coin volume';
  }
  final List<TraderMarket> sorted = List<TraderMarket>.of(markets)..sort(
    (TraderMarket left, TraderMarket right) =>
        right.volume24h.compareTo(left.volume24h),
  );
  final TraderMarket leader = sorted.first;
  return '${leader.symbol} volume ${_compactCurrency(leader.volume24h)}';
}

String _liquiditySignal(List<TraderMarket> markets) {
  if (markets.isEmpty) {
    return 'Quiet';
  }
  final double average =
      markets.fold<double>(
        0,
        (double sum, TraderMarket market) => sum + market.liquidityScore,
      ) /
      markets.length;
  if (average >= 80) {
    return 'Deep';
  }
  if (average >= 60) {
    return 'Stable';
  }
  return 'Thin';
}

IconData _iconForSection(String label) {
  switch (label) {
    case 'Markets':
      return Icons.show_chart;
    case 'Fan Coins':
      return Icons.stars_outlined;
    case 'Portfolio':
      return Icons.pie_chart_outline;
    case 'Wallet':
      return Icons.account_balance_wallet_outlined;
    case 'Buy/Sell':
      return Icons.swap_vertical_circle_outlined;
    case 'Orders':
      return Icons.receipt_long_outlined;
    case 'P2P':
      return Icons.groups_2_outlined;
    case 'Watchlist':
      return Icons.visibility_outlined;
    case 'News':
      return Icons.newspaper_outlined;
    case 'Security':
      return Icons.security_outlined;
    default:
      return Icons.candlestick_chart_outlined;
  }
}
