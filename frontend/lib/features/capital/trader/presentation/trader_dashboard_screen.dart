import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/features/capital/trader/data/trader_api.dart';
import 'package:gte_frontend/features/capital/trader/presentation/trader_balance_guard.dart';
import 'package:gte_frontend/features/capital/trader/presentation/trader_quote_lock.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/shared/state/gtex_async_surface_state.dart';
import 'package:gte_frontend/shared/widgets/async_state_widget.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';

const String _traderDepositEndpointBlockedReason =
    'Trader deposit backend state unavailable - route is not mounted.';
const String _traderWithdrawalEndpointBlockedReason =
    'Trader withdrawal backend state unavailable - route is not mounted.';

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
                'Create a GTEX account first. Trader tools unlock after GTEX confirms role, region, and compliance eligibility.',
            actionLabel: 'Create account',
            onAction: () => context.go('/auth/signup'),
          );
        }
        if (accountType != 'coin_trader') {
          return _TraderGate(
            title: 'Coin trading is a separate account lane',
            message:
                'This dashboard is restricted to COIN_TRADER accounts. Football users and creators keep their own dashboards and cannot place coin-market orders here.',
            actionLabel: 'Go home',
            onAction: () => context.go('/app/world'),
          );
        }
        return _TraderDashboardSurface(
          api: controller.createTraderApi(config),
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

  static const List<String> _sections = <String>[
    'Marketplace',
    'Profile',
    'Dashboard',
    'Buy/Sell',
    'Order Book',
    'Orders',
    'Disputes',
    'Settlements',
    'Deposit',
    'Withdrawal',
  ];

  @override
  void initState() {
    super.initState();
    _overviewFuture = widget.api.overview();
  }

  @override
  void didUpdateWidget(covariant _TraderDashboardSurface oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.accessToken != widget.accessToken) {
      _overviewFuture = widget.api.overview();
    }
  }

  Future<void> _refreshOverview() async {
    final Future<TraderOverview> nextOverview = widget.api.overview();
    setState(() => _overviewFuture = nextOverview);
    try {
      await nextOverview;
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
                      _TraderHeader(selectedSection: _selectedSection),
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
    required this.selectedTimeframe,
    required this.onTimeframeChanged,
    required this.tradeTab,
    required this.onTradeTabChanged,
  });

  final TraderOverview overview;
  final String selectedTimeframe;
  final ValueChanged<String> onTimeframeChanged;
  final String tradeTab;
  final ValueChanged<String> onTradeTabChanged;

  @override
  Widget build(BuildContext context) {
    final TraderMarket? primaryMarket = _primaryMarket(overview);
    final TraderDashboard dashboard = TraderDashboard.fromOverview(overview);
    final GtexSurfaceState<TraderBalanceSnapshot> balanceState =
        traderBalanceSurfaceFromBackend(
          TraderBalancePayload(
            available: overview.walletBalance,
            currency: overview.profile.preferredCurrency,
          ),
        );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        _TraderBalanceHero(balanceState: balanceState),
        const SizedBox(height: 18),
        _TopStrip(overview: overview),
        const SizedBox(height: 18),
        _ProfileTrustPanel(profile: overview.profile),
        const SizedBox(height: 18),
        _BackendTruthPanel(overview: overview, market: primaryMarket),
        const SizedBox(height: 18),
        _TraderSurfaceCoveragePanel(
          profile: overview.profile,
          market: primaryMarket,
          dashboard: dashboard,
          balanceState: balanceState,
        ),
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
              profile: overview.profile,
              balanceState: balanceState,
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
        const SizedBox(height: 18),
        _LiquidityDepthPanel(markets: overview.liquidityActivity),
        const SizedBox(height: 18),
        _DepositWithdrawalPanel(balanceState: balanceState),
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

class _TraderBalanceHero extends StatelessWidget {
  const _TraderBalanceHero({required this.balanceState});

  final GtexSurfaceState<TraderBalanceSnapshot> balanceState;

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
      child: AsyncStateWidget<TraderBalanceSnapshot>(
        state: balanceState,
        onLoading: () => const LinearProgressIndicator(minHeight: 4),
        onEmpty:
            (String? reason) => _BalanceBlockedContent(
              reason: reason ?? traderBalanceUnavailableReason,
            ),
        onBlocked: (String reason, String? ctaRoute) {
          return _BalanceBlockedContent(reason: reason);
        },
        onPending: (TraderBalanceSnapshot? stale) {
          return _BalanceReadyContent(snapshot: stale, label: 'Pending sync');
        },
        onSyncing: (TraderBalanceSnapshot current) {
          return _BalanceReadyContent(snapshot: current, label: 'Syncing');
        },
        onReconnecting: (TraderBalanceSnapshot? lastKnown, int attempt) {
          return _BalanceReadyContent(
            snapshot: lastKnown,
            label: 'Reconnecting $attempt',
          );
        },
        onDegraded: (TraderBalanceSnapshot current, String warning) {
          return _BalanceReadyContent(snapshot: current, label: warning);
        },
        onConfirmed: (TraderBalanceSnapshot data, String? auditRef) {
          return _BalanceReadyContent(
            snapshot: data,
            label: auditRef ?? 'Backend confirmed',
          );
        },
        onError: (String code, String message, VoidCallback retry) {
          return _BalanceBlockedContent(reason: '$code: $message');
        },
        onData: (TraderBalanceSnapshot data) {
          return _BalanceReadyContent(snapshot: data, label: 'Backend balance');
        },
      ),
    );
  }
}

class _BalanceReadyContent extends StatelessWidget {
  const _BalanceReadyContent({required this.snapshot, required this.label});

  final TraderBalanceSnapshot? snapshot;
  final String label;

  @override
  Widget build(BuildContext context) {
    final TraderBalanceSnapshot? data = snapshot;
    if (data == null) {
      return const _BalanceBlockedContent(
        reason: traderBalanceUnavailableReason,
      );
    }
    return Row(
      children: <Widget>[
        const Icon(Icons.account_balance_wallet_outlined),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Trader balance',
                style: Theme.of(
                  context,
                ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w900),
              ),
              const SizedBox(height: 4),
              Text(
                '${_compactNumber(data.available)} ${data.currency}',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w900,
                ),
              ),
            ],
          ),
        ),
        _SignalChip(
          icon: Icons.verified_outlined,
          label: label,
          color: GteShellTheme.positive,
        ),
      ],
    );
  }
}

class _BalanceBlockedContent extends StatelessWidget {
  const _BalanceBlockedContent({required this.reason});

  final String reason;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: <Widget>[
        const Icon(Icons.lock_outline, color: GteShellTheme.warning),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Balance data unavailable',
                style: Theme.of(
                  context,
                ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w900),
              ),
              const SizedBox(height: 4),
              Text(reason, style: Theme.of(context).textTheme.bodyMedium),
            ],
          ),
        ),
        const _SignalChip(
          icon: Icons.block_outlined,
          label: 'GtexBlocked',
          color: GteShellTheme.warning,
        ),
      ],
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
  const _TraderHeader({required this.selectedSection});

  final String selectedSection;

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
          onPressed: () {},
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
        _metricCompact(overview.portfolioValue),
        _metricTruth(overview.portfolioValue, 'GTEX', 'blocked'),
      ),
      _Metric(
        'GTEX Coin Price',
        _metricPrice(overview.gtexCoinPrice, currency),
        overview.trending.isEmpty
            ? 'market feed empty'
            : _signedPercent(_marketSignal(overview.trending)),
      ),
      _Metric(
        'Daily P/L',
        _signedAmountOrSyncing(overview.dailyPl),
        _metricTruth(overview.dailyPl, 'today', 'syncing'),
      ),
      _Metric(
        'Wallet Balance',
        overview.walletBalance == null
            ? 'Blocked'
            : _metricCompact(overview.walletBalance),
        _metricTruth(
          overview.walletBalance,
          'backend balance',
          'Balance data unavailable',
        ),
      ),
      _Metric(
        'Market Cap',
        _metricCurrency(overview.marketCap),
        _metricTruth(overview.marketCap, currency, 'syncing'),
      ),
      _Metric(
        'Trading Volume',
        _metricCurrency(overview.tradingVolume),
        _metricTruth(overview.tradingVolume, '24h', 'syncing'),
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
          Text(
            metric.label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.labelMedium,
          ),
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
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
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

class _ProfileTrustPanel extends StatelessWidget {
  const _ProfileTrustPanel({required this.profile});

  final TraderProfile profile;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final List<Widget> chips = <Widget>[
      _SignalChip(
        icon: Icons.circle,
        label: _onlineSignal(profile),
        color:
            profile.isOnline == true
                ? const Color(0xFF5FE3A1)
                : const Color(0xFFFFD66B),
      ),
      _SignalChip(
        icon: Icons.verified_user_outlined,
        label: _trustSignal(profile),
        color: const Color(0xFF79A7FF),
      ),
      _SignalChip(
        icon: Icons.star_rate_rounded,
        label: _ratingSignal(profile),
        color: const Color(0xFFFFD66B),
      ),
    ];
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: tokens.panel.withValues(alpha: 0.88),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tokens.stroke.withValues(alpha: 0.55)),
      ),
      child: LayoutBuilder(
        builder: (BuildContext context, BoxConstraints constraints) {
          final bool split = constraints.maxWidth >= 820;
          final Widget profileSummary = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Trader profile',
                style: Theme.of(
                  context,
                ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w900),
              ),
              const SizedBox(height: 6),
              Text(
                profile.tradingAlias,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 12),
              Wrap(spacing: 8, runSpacing: 8, children: chips),
            ],
          );
          final Widget disputes = _DisputeHistoryPanel(profile: profile);
          if (!split) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                profileSummary,
                const SizedBox(height: 14),
                disputes,
              ],
            );
          }
          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Expanded(child: profileSummary),
              const SizedBox(width: 16),
              Expanded(child: disputes),
            ],
          );
        },
      ),
    );
  }
}

class _DisputeHistoryPanel extends StatelessWidget {
  const _DisputeHistoryPanel({required this.profile});

  final TraderProfile profile;

  @override
  Widget build(BuildContext context) {
    final List<String> rows = _disputeRows(profile);
    return _BookPanel(title: 'Dispute history', rows: rows);
  }
}

class _BackendTruthPanel extends StatelessWidget {
  const _BackendTruthPanel({required this.overview, required this.market});

  final TraderOverview overview;
  final TraderMarket? market;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final List<_TruthGate> gates = _backendTruthGates(overview, market);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: tokens.panel.withValues(alpha: 0.88),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tokens.stroke.withValues(alpha: 0.55)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Backend truth gates',
            style: Theme.of(
              context,
            ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: gates
                .map(
                  (_TruthGate gate) => _SignalChip(
                    icon: gate.icon,
                    label: gate.label,
                    color: gate.color,
                  ),
                )
                .toList(growable: false),
          ),
        ],
      ),
    );
  }
}

class _TraderSurfaceCoveragePanel extends StatelessWidget {
  const _TraderSurfaceCoveragePanel({
    required this.profile,
    required this.market,
    required this.dashboard,
    required this.balanceState,
  });

  final TraderProfile profile;
  final TraderMarket? market;
  final TraderDashboard dashboard;
  final GtexSurfaceState<TraderBalanceSnapshot> balanceState;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final bool balanceReady = traderBalanceAllowsActions(balanceState);
    final bool profileReady =
        profile.id.trim().isNotEmpty && profile.tradingAlias.trim().isNotEmpty;
    final bool orderBookReady = market?.orderBook?.hasLiveDepth ?? false;
    final bool orderBookDegraded = market?.orderBook != null && !orderBookReady;
    final List<_TruthGate> surfaces = <_TruthGate>[
      _TruthGate(
        label: market == null ? 'Marketplace blocked' : 'Marketplace ready',
        icon: Icons.storefront_outlined,
        color: market == null ? GteShellTheme.warning : GteShellTheme.positive,
      ),
      _TruthGate(
        label: profileReady ? 'Profile ready' : 'Profile blocked',
        icon: Icons.badge_outlined,
        color: profileReady ? GteShellTheme.positive : GteShellTheme.warning,
      ),
      _TruthGate(
        label: balanceReady ? 'Dashboard ready' : 'Dashboard blocked',
        icon: Icons.dashboard_customize_outlined,
        color: balanceReady ? GteShellTheme.positive : GteShellTheme.warning,
      ),
      _capitalActionGate('Buy flow', false),
      _capitalActionGate('Sell flow', false),
      _TruthGate(
        label:
            orderBookReady
                ? 'Order book ready'
                : orderBookDegraded
                ? 'Order book degraded'
                : 'Order book blocked',
        icon: Icons.format_list_numbered_outlined,
        color: orderBookReady ? GteShellTheme.positive : GteShellTheme.warning,
      ),
      _TruthGate(
        label:
            dashboard.activeOrders == null ? 'Orders blocked' : 'Orders ready',
        icon: Icons.receipt_long_outlined,
        color:
            dashboard.activeOrders == null
                ? GteShellTheme.warning
                : GteShellTheme.positive,
      ),
      _disputeTruthGate(profile),
      _TruthGate(
        label:
            dashboard.pendingSettlements == null
                ? 'Settlements blocked'
                : 'Settlements ready',
        icon: Icons.task_alt_outlined,
        color:
            dashboard.pendingSettlements == null
                ? GteShellTheme.warning
                : GteShellTheme.positive,
      ),
      const _TruthGate(
        label: 'Deposit blocked',
        icon: Icons.add_card_outlined,
        color: GteShellTheme.warning,
      ),
      const _TruthGate(
        label: 'Withdrawal blocked',
        icon: Icons.payments_outlined,
        color: GteShellTheme.warning,
      ),
    ];
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: tokens.panel.withValues(alpha: 0.88),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tokens.stroke.withValues(alpha: 0.55)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Trader surfaces',
            style: Theme.of(
              context,
            ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: surfaces
                .map(
                  (_TruthGate surface) => _SignalChip(
                    icon: surface.icon,
                    label: surface.label,
                    color: surface.color,
                  ),
                )
                .toList(growable: false),
          ),
        ],
      ),
    );
  }
}

class _DepositWithdrawalPanel extends StatelessWidget {
  const _DepositWithdrawalPanel({required this.balanceState});

  final GtexSurfaceState<TraderBalanceSnapshot> balanceState;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final bool balanceReady = traderBalanceAllowsActions(balanceState);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: tokens.panel.withValues(alpha: 0.88),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tokens.stroke.withValues(alpha: 0.55)),
      ),
      child: LayoutBuilder(
        builder: (BuildContext context, BoxConstraints constraints) {
          final bool split = constraints.maxWidth >= 760;
          final Widget deposit = _FundingActionCard(
            title: 'Deposit',
            icon: Icons.add_card_outlined,
            status: 'Blocked until backend returns deposit state',
            rail: TraderPaymentRail.koraPay,
            enabled: false,
            disabledReason: _traderDepositEndpointBlockedReason,
          );
          final Widget withdrawal = _FundingActionCard(
            title: 'Withdrawal',
            icon: Icons.payments_outlined,
            status: 'Blocked until backend returns withdrawal state',
            rail: TraderPaymentRail.manualBankTransfer,
            enabled: false,
            disabledReason:
                balanceReady
                    ? _traderWithdrawalEndpointBlockedReason
                    : '$traderBalanceUnavailableReason $_traderWithdrawalEndpointBlockedReason',
          );
          if (!split) {
            return Column(
              children: <Widget>[
                deposit,
                const SizedBox(height: 12),
                withdrawal,
              ],
            );
          }
          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Expanded(child: deposit),
              const SizedBox(width: 12),
              Expanded(child: withdrawal),
            ],
          );
        },
      ),
    );
  }
}

class _FundingActionCard extends StatelessWidget {
  const _FundingActionCard({
    required this.title,
    required this.icon,
    required this.status,
    required this.rail,
    required this.enabled,
    required this.disabledReason,
    this.auditRef,
  });

  final String title;
  final IconData icon;
  final String status;
  final TraderPaymentRail rail;
  final bool enabled;
  final String? disabledReason;
  final String? auditRef;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        color: tokens.panelElevated.withValues(alpha: 0.74),
        border: Border.all(color: tokens.stroke.withValues(alpha: 0.5)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Row(
            children: <Widget>[
              Icon(icon),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  title,
                  style: Theme.of(
                    context,
                  ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w900),
                ),
              ),
              _SignalChip(
                icon: enabled ? Icons.check_circle_outline : Icons.lock_outline,
                label: enabled ? 'Ready' : 'Blocked',
                color: enabled ? GteShellTheme.positive : GteShellTheme.warning,
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(status, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 10),
          TraderPaymentRailSelector(selected: rail, onChanged: null),
          if (disabledReason != null) ...<Widget>[
            const SizedBox(height: 10),
            Text(
              disabledReason!,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: GteShellTheme.warning,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
          if (auditRef != null) ...<Widget>[
            const SizedBox(height: 10),
            TraderActionAuditReference(auditRef: auditRef),
          ],
        ],
      ),
    );
  }
}

class _SignalChip extends StatelessWidget {
  const _SignalChip({
    required this.icon,
    required this.label,
    required this.color,
  });

  final IconData icon;
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 34,
      padding: const EdgeInsets.symmetric(horizontal: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        color: color.withValues(alpha: 0.12),
        border: Border.all(color: color.withValues(alpha: 0.42)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(icon, size: 16, color: color),
          const SizedBox(width: 6),
          Text(
            label,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
              fontWeight: FontWeight.w800,
              color: color,
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
        overview.trending.isEmpty
            ? 'empty'
            : _signedPercent(_marketSignal(overview.trending)),
        _averageLiquidity(overview.trending),
      ),
      _MarketBucket(
        'Top Gainers',
        _symbols(overview.topGainers),
        overview.topGainers.isEmpty
            ? 'empty'
            : _signedPercent(_marketSignal(overview.topGainers)),
        _averageLiquidity(overview.topGainers),
      ),
      _MarketBucket(
        'Top Losers',
        _symbols(overview.topLosers),
        overview.topLosers.isEmpty
            ? 'empty'
            : _signedPercent(_marketSignal(overview.topLosers)),
        _averageLiquidity(overview.topLosers),
      ),
      _MarketBucket(
        'Most Traded Fan Coins',
        _volumeLeader(overview.mostTradedFanCoins),
        overview.mostTradedFanCoins.isEmpty ? 'empty' : 'live',
        _averageLiquidity(overview.mostTradedFanCoins),
      ),
      _MarketBucket(
        'Liquidity Activity',
        overview.liquidityActivity.isEmpty
            ? 'Liquidity feed empty'
            : '${overview.liquidityActivity.length} active markets',
        _liquiditySignal(overview.liquidityActivity),
        _averageLiquidity(overview.liquidityActivity),
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
      height: 164,
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
          const SizedBox(height: 8),
          _LiquidityBar(score: bucket.liquidityScore),
        ],
      ),
    );
  }
}

class _LiquidityBar extends StatelessWidget {
  const _LiquidityBar({required this.score});

  final int? score;

  @override
  Widget build(BuildContext context) {
    final int? clamped = score?.clamp(0, 100).toInt();
    return Row(
      children: <Widget>[
        Expanded(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              minHeight: 6,
              value: clamped == null ? 0 : clamped / 100,
              backgroundColor: Colors.white.withValues(alpha: 0.08),
              color:
                  clamped == null
                      ? const Color(0xFFFFD66B)
                      : const Color(0xFF5FE3A1),
            ),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          clamped == null ? 'blocked' : '$clamped',
          style: Theme.of(
            context,
          ).textTheme.labelSmall?.copyWith(fontWeight: FontWeight.w800),
        ),
      ],
    );
  }
}

class _LiquidityDepthPanel extends StatelessWidget {
  const _LiquidityDepthPanel({required this.markets});

  final List<TraderMarket> markets;

  @override
  Widget build(BuildContext context) {
    if (markets.isEmpty) {
      return const _CanonicalStateBox(
        title: 'Liquidity feed empty',
        message:
            'The backend returned no liquidity activity for trader markets.',
      );
    }
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: tokens.panel.withValues(alpha: 0.88),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tokens.stroke.withValues(alpha: 0.55)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Liquidity bars',
            style: Theme.of(
              context,
            ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 12),
          for (final TraderMarket market in markets.take(6))
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Row(
                children: <Widget>[
                  SizedBox(
                    width: 86,
                    child: Text(
                      market.symbol,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ),
                  Expanded(child: _LiquidityBar(score: market.liquidityScore)),
                  const SizedBox(width: 12),
                  SizedBox(
                    width: 150,
                    child: Text(
                      _spreadLabel(market),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      textAlign: TextAlign.end,
                    ),
                  ),
                ],
              ),
            ),
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
                  market == null
                      ? 'Market feed blocked'
                      : '${market!.symbol}/USD live market',
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
          _PriceChartPanel(market: market),
          const SizedBox(height: 14),
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final bool split = constraints.maxWidth >= 720;
              final Widget volume = _BookPanel(
                title: 'Market depth',
                rows: <String>[
                  '24h volume ${_metricCurrency(market?.volume24h)}',
                  'Market cap ${_metricCurrency(market?.marketCap)}',
                  'Liquidity ${_liquidityLabel(market?.liquidityScore)}',
                ],
              );
              final Widget orderBook = _OrderBookPanel(
                market: market,
                orderBook: market?.orderBook,
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
    required this.profile,
    required this.balanceState,
    required this.selectedTab,
    required this.onTabChanged,
  });

  final TraderMarket? market;
  final TraderProfile profile;
  final GtexSurfaceState<TraderBalanceSnapshot> balanceState;
  final String selectedTab;
  final ValueChanged<String> onTabChanged;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final bool isBuy = selectedTab == 'Buy';
    final bool isSell = selectedTab == 'Sell';
    final double? quotePrice =
        isBuy
            ? market?.liveBestAsk
            : isSell
            ? market?.liveBestBid
            : null;
    final TraderQuoteLockState quoteLock = _quoteLockForMarket(
      market,
      quotePrice,
    );
    final bool hasLiveDepth = market?.orderBook?.hasLiveDepth ?? false;
    final bool hasSettlementRail = market?.hasCanonicalSettlementRail ?? false;
    final bool hasVerifiedProfile =
        profile.status.trim().toUpperCase() == 'VERIFIED';
    final bool balanceReady = traderBalanceAllowsActions(balanceState);
    final bool canStart =
        market != null &&
        quoteLock.canConfirm &&
        balanceReady &&
        hasLiveDepth &&
        hasSettlementRail &&
        hasVerifiedProfile &&
        selectedTab != 'Convert';
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
            value: market?.displayName ?? 'Market syncing',
          ),
          const SizedBox(height: 10),
          _TradeField(
            label:
                isBuy
                    ? 'Buy quote'
                    : isSell
                    ? 'Sell quote'
                    : 'Quote',
            value:
                quotePrice == null
                    ? 'Blocked until backend quote syncs'
                    : '${_fixedPrice(quotePrice)} USD',
          ),
          const SizedBox(height: 10),
          _TradeField(label: 'Spread', value: _spreadLabel(market)),
          const SizedBox(height: 10),
          _TradeField(label: 'Settlement ETA', value: _settlementEta(market)),
          const SizedBox(height: 10),
          _TradeField(
            label: 'Settlement rail',
            value: _settlementRailLabel(market),
          ),
          const SizedBox(height: 14),
          QuoteLockCard(state: quoteLock, onRefresh: canStart ? null : () {}),
          const SizedBox(height: 14),
          TraderPaymentRailSelector(
            selected: TraderPaymentRail.koraPay,
            onChanged: null,
          ),
          const SizedBox(height: 14),
          ConfirmOrderBar(
            quoteLock: quoteLock,
            balanceAvailable: balanceReady,
            onConfirm: canStart ? () {} : null,
            actionLabel: '$selectedTab ${market?.symbol ?? 'market'}',
          ),
          const SizedBox(height: 14),
          _AuditFlowPanel(
            rows: <_AuditFlowRow>[
              _AuditFlowRow(
                'Backend quote lock',
                quoteLock.canConfirm ? 'ready' : 'blocked',
              ),
              _AuditFlowRow(
                'Backend balance',
                balanceReady ? 'ready' : 'blocked',
              ),
              _AuditFlowRow(
                'Live liquidity lock',
                hasLiveDepth ? 'ready' : 'blocked',
              ),
              _AuditFlowRow(
                'KoraPay/manual settlement',
                hasSettlementRail ? 'ready' : 'blocked',
              ),
              _AuditFlowRow(
                'KYC/TOTP guard',
                hasVerifiedProfile ? 'ready' : 'blocked',
              ),
              const _AuditFlowRow('Audit receipt', 'after order submit'),
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
      constraints: const BoxConstraints(minHeight: 58),
      padding: const EdgeInsets.symmetric(horizontal: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tokens.stroke.withValues(alpha: 0.55)),
      ),
      child: Row(
        children: <Widget>[
          Text(label, style: Theme.of(context).textTheme.labelMedium),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              value,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              textAlign: TextAlign.end,
              style: Theme.of(
                context,
              ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w900),
            ),
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

class _PriceChartPanel extends StatelessWidget {
  const _PriceChartPanel({required this.market});

  final TraderMarket? market;

  @override
  Widget build(BuildContext context) {
    final List<TraderPriceCandle> candles =
        market?.priceCandles ?? const <TraderPriceCandle>[];
    if (market == null) {
      return const _CanonicalStateBox(
        title: 'Chart blocked',
        message: 'No market was returned by the trader API.',
      );
    }
    if (candles.isEmpty) {
      return _CanonicalStateBox(
        title: 'Price candles syncing',
        message: 'No backend candle feed is attached for ${market!.symbol}.',
      );
    }
    return SizedBox(
      height: 260,
      child: CustomPaint(
        painter: _CandlestickPainter(candles: candles),
        child: const SizedBox.expand(),
      ),
    );
  }
}

class _OrderBookPanel extends StatelessWidget {
  const _OrderBookPanel({required this.market, required this.orderBook});

  final TraderMarket? market;
  final TraderOrderBook? orderBook;

  @override
  Widget build(BuildContext context) {
    if (market == null) {
      return const _CanonicalStateBox(
        title: 'Order book blocked',
        message: 'No market was returned by the trader API.',
      );
    }
    final TraderOrderBook? book = orderBook;
    if (book == null) {
      return _CanonicalStateBox(
        title: 'Order book blocked',
        message: 'No live depth was returned for ${market!.symbol}.',
      );
    }
    if (!book.hasLiveDepth) {
      return _CanonicalStateBox(
        title: 'Order book degraded',
        message: 'Live depth is missing one side for ${market!.symbol}.',
      );
    }
    final tokens = GteShellTheme.tokensOf(context);
    final double maxDepth = book.maxDepth;
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
            'Live order book',
            style: Theme.of(
              context,
            ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 4),
          Text(
            _spreadLabel(market),
            style: Theme.of(context).textTheme.labelMedium,
          ),
          const SizedBox(height: 10),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Expanded(
                child: _OrderBookSide(
                  title: 'Bids',
                  levels: book.bids,
                  maxDepth: maxDepth,
                  color: const Color(0xFF5FE3A1),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _OrderBookSide(
                  title: 'Asks',
                  levels: book.asks,
                  maxDepth: maxDepth,
                  color: const Color(0xFFFF6B7A),
                ),
              ),
            ],
          ),
          if (book.syncedAt != null) ...<Widget>[
            const SizedBox(height: 8),
            Text(
              'Synced ${_shortDateTime(book.syncedAt!)}',
              style: Theme.of(context).textTheme.labelSmall,
            ),
          ],
        ],
      ),
    );
  }
}

class _OrderBookSide extends StatelessWidget {
  const _OrderBookSide({
    required this.title,
    required this.levels,
    required this.maxDepth,
    required this.color,
  });

  final String title;
  final List<TraderOrderBookLevel> levels;
  final double maxDepth;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          title,
          style: Theme.of(
            context,
          ).textTheme.labelMedium?.copyWith(fontWeight: FontWeight.w900),
        ),
        const SizedBox(height: 6),
        for (final TraderOrderBookLevel level in levels.take(4))
          _OrderBookLevelRow(level: level, maxDepth: maxDepth, color: color),
      ],
    );
  }
}

class _OrderBookLevelRow extends StatelessWidget {
  const _OrderBookLevelRow({
    required this.level,
    required this.maxDepth,
    required this.color,
  });

  final TraderOrderBookLevel level;
  final double maxDepth;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final double fill = maxDepth <= 0 ? 0 : (level.quantity / maxDepth);
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(child: Text(_fixedPrice(level.price))),
              Text(_compactNumber(level.quantity)),
            ],
          ),
          const SizedBox(height: 3),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              minHeight: 4,
              value: fill.clamp(0, 1).toDouble(),
              color: color,
              backgroundColor: color.withValues(alpha: 0.12),
            ),
          ),
        ],
      ),
    );
  }
}

class _AuditFlowPanel extends StatelessWidget {
  const _AuditFlowPanel({required this.rows});

  final List<_AuditFlowRow> rows;

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
            'Auditable buy flow',
            style: Theme.of(
              context,
            ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 8),
          for (final _AuditFlowRow row in rows)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                children: <Widget>[
                  Icon(_auditIcon(row.state), size: 16),
                  const SizedBox(width: 8),
                  Expanded(child: Text(row.label)),
                  Text(
                    row.state,
                    style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _CanonicalStateBox extends StatelessWidget {
  const _CanonicalStateBox({required this.title, required this.message});

  final String title;
  final String message;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      constraints: const BoxConstraints(minHeight: 150),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        color: tokens.panelElevated.withValues(alpha: 0.74),
        border: Border.all(color: tokens.stroke.withValues(alpha: 0.5)),
      ),
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            const Icon(Icons.sync_problem_outlined, size: 28),
            const SizedBox(height: 8),
            Text(
              title,
              style: Theme.of(
                context,
              ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: 4),
            Text(
              message,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }
}

class _AuditFlowRow {
  const _AuditFlowRow(this.label, this.state);

  final String label;
  final String state;
}

class _CandlestickPainter extends CustomPainter {
  _CandlestickPainter({required this.candles});

  final List<TraderPriceCandle> candles;

  @override
  void paint(Canvas canvas, Size size) {
    if (candles.isEmpty) {
      return;
    }
    final Paint gridPaint =
        Paint()
          ..color = Colors.white.withValues(alpha: 0.08)
          ..strokeWidth = 1;
    for (int i = 1; i < 5; i++) {
      final double y = size.height * i / 5;
      canvas.drawLine(Offset(0, y), Offset(size.width, y), gridPaint);
    }

    final List<TraderPriceCandle> visible =
        candles.length > 64 ? candles.sublist(candles.length - 64) : candles;
    final double minLow = visible
        .map((TraderPriceCandle candle) => candle.low)
        .reduce(math.min);
    final double maxHigh = visible
        .map((TraderPriceCandle candle) => candle.high)
        .reduce(math.max);
    final double range = math.max(0.0001, maxHigh - minLow);
    final double plotHeight = math.max(1, size.height - 16);
    double yFor(double price) {
      final double normalized = (price - minLow) / range;
      return (size.height - 8) - (normalized * plotHeight);
    }

    final Paint upPaint = Paint()..color = const Color(0xFF5FE3A1);
    final Paint downPaint = Paint()..color = const Color(0xFFFF6B7A);
    final Paint wickPaint =
        Paint()
          ..color = Colors.white.withValues(alpha: 0.62)
          ..strokeWidth = 1.4;
    final double slot = size.width / visible.length;
    for (int i = 0; i < visible.length; i++) {
      final TraderPriceCandle candle = visible[i];
      final bool up = candle.close >= candle.open;
      final double high = yFor(candle.high);
      final double low = yFor(candle.low);
      final double open = yFor(candle.open);
      final double close = yFor(candle.close);
      final double x = (slot * i) + (slot * 0.5);
      canvas.drawLine(
        Offset(x, high.clamp(8, size.height - 8).toDouble()),
        Offset(x, low.clamp(8, size.height - 8).toDouble()),
        wickPaint,
      );
      final Rect body = Rect.fromCenter(
        center: Offset(
          x,
          ((open + close) / 2).clamp(8, size.height - 8).toDouble(),
        ),
        width: math.max(5, slot * 0.42),
        height: math.max(2, (open - close).abs()),
      );
      canvas.drawRRect(
        RRect.fromRectAndRadius(body, const Radius.circular(2)),
        up ? upPaint : downPaint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _CandlestickPainter oldDelegate) {
    return oldDelegate.candles != candles;
  }
}

class _Metric {
  const _Metric(this.label, this.value, this.detail);

  final String label;
  final String value;
  final String detail;
}

class _MarketBucket {
  const _MarketBucket(
    this.title,
    this.summary,
    this.signal,
    this.liquidityScore,
  );

  final String title;
  final String summary;
  final String signal;
  final int? liquidityScore;
}

class _TruthGate {
  const _TruthGate({
    required this.label,
    required this.icon,
    required this.color,
  });

  final String label;
  final IconData icon;
  final Color color;
}

_TruthGate _capitalActionGate(String title, bool ready) {
  return _TruthGate(
    label: ready ? '$title ready' : '$title blocked',
    icon: ready ? Icons.check_circle_outline : Icons.block_outlined,
    color: ready ? GteShellTheme.positive : GteShellTheme.warning,
  );
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

String _metricCompact(double? value) {
  return value == null ? 'Syncing' : _compactNumber(value);
}

String _metricCurrency(double? value) {
  return value == null ? 'Syncing' : _compactCurrency(value);
}

String _metricPrice(double? value, String currency) {
  return value == null ? 'Syncing' : '${_fixedPrice(value)} $currency';
}

String _metricTruth(double? value, String ready, String missing) {
  return value == null ? missing : ready;
}

String _fixedPrice(double value) => value.toStringAsFixed(value >= 10 ? 2 : 4);

String _signedAmount(double value) {
  final String sign = value >= 0 ? '+' : '-';
  return '$sign${_compactNumber(value.abs())}';
}

String _signedAmountOrSyncing(double? value) {
  return value == null ? 'Syncing' : _signedAmount(value);
}

String _signedPercent(double value) {
  final String sign = value >= 0 ? '+' : '';
  return '$sign${value.toStringAsFixed(1)}%';
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
  final List<double> changes = markets
      .map((TraderMarket market) => market.dailyChangePercent)
      .whereType<double>()
      .toList(growable: false);
  if (changes.isEmpty) {
    return 0;
  }
  final double total = markets.fold<double>(
    0,
    (double sum, TraderMarket market) => sum + (market.dailyChangePercent ?? 0),
  );
  return total / changes.length;
}

String _volumeLeader(List<TraderMarket> markets) {
  if (markets.isEmpty) {
    return 'No fan coin volume';
  }
  final List<TraderMarket> sorted = List<TraderMarket>.of(markets)..sort(
    (TraderMarket left, TraderMarket right) =>
        (right.volume24h ?? -1).compareTo(left.volume24h ?? -1),
  );
  final TraderMarket leader = sorted.first;
  if (leader.volume24h == null) {
    return '${leader.symbol} volume syncing';
  }
  return '${leader.symbol} volume ${_compactCurrency(leader.volume24h!)}';
}

String _liquiditySignal(List<TraderMarket> markets) {
  if (markets.isEmpty) {
    return 'empty';
  }
  final int? average = _averageLiquidity(markets);
  if (average == null) {
    return 'degraded';
  }
  if (average >= 80) {
    return 'Deep';
  }
  if (average >= 60) {
    return 'Stable';
  }
  return 'Thin';
}

int? _averageLiquidity(List<TraderMarket> markets) {
  final List<int> scores = markets
      .map((TraderMarket market) => market.liquidityScore)
      .whereType<int>()
      .toList(growable: false);
  if (scores.isEmpty) {
    return null;
  }
  final int total = scores.fold<int>(0, (int sum, int score) => sum + score);
  return (total / scores.length).round();
}

String _liquidityLabel(int? score) {
  return score == null ? 'blocked' : '${score.clamp(0, 100)}/100';
}

String _spreadLabel(TraderMarket? market) {
  if (market == null) {
    return 'Spread blocked';
  }
  final double? bid = market.liveBestBid;
  final double? ask = market.liveBestAsk;
  final double? spread = market.liveSpread;
  final double? spreadPercent = market.liveSpreadPercent;
  if (bid == null || ask == null || spread == null || spreadPercent == null) {
    return 'Spread syncing';
  }
  return 'Spread ${_fixedPrice(spread)} (${spreadPercent.toStringAsFixed(2)}%)';
}

String _settlementEta(TraderMarket? market) {
  if (market == null) {
    return 'ETA blocked';
  }
  if (market.settlementEtaLabel != null) {
    return market.settlementEtaLabel!;
  }
  final int? minutes = market.settlementEtaMinutes;
  if (minutes == null) {
    return 'ETA blocked';
  }
  if (minutes <= 0) {
    return 'Immediate after audit';
  }
  return '$minutes min';
}

String _settlementRailLabel(TraderMarket? market) {
  if (market == null) {
    return 'Settlement blocked';
  }
  if (market.settlementRails.isNotEmpty) {
    return market.settlementRails.join(' / ');
  }
  if (market.hasSettlementRails) {
    return 'Unsupported rail blocked';
  }
  return 'Settlement rail blocked';
}

String _onlineSignal(TraderProfile profile) {
  if (profile.isOnline == true) {
    return 'Online';
  }
  if (profile.isOnline == false && profile.lastSeenAt != null) {
    return 'Last seen ${_shortDateTime(profile.lastSeenAt!)}';
  }
  if (profile.isOnline == false) {
    return 'Offline';
  }
  return 'Presence syncing';
}

String _trustSignal(TraderProfile profile) {
  final String? tier = profile.trustTier;
  final int? score = profile.trustScore;
  if (tier == null && score == null) {
    return 'Trust degraded';
  }
  if (tier != null && score != null) {
    return '$tier trust $score/100';
  }
  if (score != null) {
    return 'Trust $score/100';
  }
  return '$tier trust';
}

String _ratingSignal(TraderProfile profile) {
  final double? rating = profile.ratingAverage;
  final int? count = profile.ratingCount;
  if (rating == null) {
    return 'Rating blocked';
  }
  if (count == null) {
    return '${rating.toStringAsFixed(1)} rating (count degraded)';
  }
  return '${rating.toStringAsFixed(1)} rating ($count)';
}

List<String> _disputeRows(TraderProfile profile) {
  if (!profile.hasDisputeHistory) {
    return const <String>['Dispute state blocked'];
  }
  if (profile.disputeHistory.isEmpty) {
    return const <String>['No disputes reported'];
  }
  return profile.disputeHistory
      .take(3)
      .map((TraderDisputeRecord record) => _disputeLabel(record))
      .toList(growable: false);
}

String _disputeLabel(TraderDisputeRecord record) {
  final String status = record.status ?? 'status blocked';
  final String? summary = record.summary;
  if (summary == null) {
    return status;
  }
  return '$status - $summary';
}

List<_TruthGate> _backendTruthGates(
  TraderOverview overview,
  TraderMarket? market,
) {
  return <_TruthGate>[
    _liquidityTruthGate(overview.liquidityActivity),
    _ratingTruthGate(overview.profile),
    _settlementTruthGate(market),
    _disputeTruthGate(overview.profile),
  ];
}

_TruthGate _liquidityTruthGate(List<TraderMarket> markets) {
  if (markets.isEmpty) {
    return const _TruthGate(
      label: 'Liquidity blocked',
      icon: Icons.waterfall_chart_outlined,
      color: GteShellTheme.warning,
    );
  }
  final bool hasMissingScore = markets.any(
    (TraderMarket market) => market.liquidityScore == null,
  );
  if (hasMissingScore) {
    return const _TruthGate(
      label: 'Liquidity degraded',
      icon: Icons.waterfall_chart_outlined,
      color: GteShellTheme.warning,
    );
  }
  return const _TruthGate(
    label: 'Liquidity ready',
    icon: Icons.waterfall_chart_outlined,
    color: GteShellTheme.positive,
  );
}

_TruthGate _ratingTruthGate(TraderProfile profile) {
  if (profile.ratingAverage == null) {
    return const _TruthGate(
      label: 'Rating blocked',
      icon: Icons.star_rate_rounded,
      color: GteShellTheme.warning,
    );
  }
  if (profile.ratingCount == null) {
    return const _TruthGate(
      label: 'Rating degraded',
      icon: Icons.star_rate_rounded,
      color: GteShellTheme.warning,
    );
  }
  return const _TruthGate(
    label: 'Rating ready',
    icon: Icons.star_rate_rounded,
    color: GteShellTheme.positive,
  );
}

_TruthGate _settlementTruthGate(TraderMarket? market) {
  if (market == null ||
      (market.settlementEtaLabel == null &&
          market.settlementEtaMinutes == null)) {
    return const _TruthGate(
      label: 'Settlement ETA blocked',
      icon: Icons.schedule_outlined,
      color: GteShellTheme.warning,
    );
  }
  return const _TruthGate(
    label: 'Settlement ETA ready',
    icon: Icons.schedule_outlined,
    color: GteShellTheme.positive,
  );
}

_TruthGate _disputeTruthGate(TraderProfile profile) {
  if (!profile.hasDisputeHistory) {
    return const _TruthGate(
      label: 'Disputes blocked',
      icon: Icons.gavel_outlined,
      color: GteShellTheme.warning,
    );
  }
  final bool hasMissingStatus = profile.disputeHistory.any(
    (TraderDisputeRecord record) => record.status == null,
  );
  if (hasMissingStatus) {
    return const _TruthGate(
      label: 'Disputes degraded',
      icon: Icons.gavel_outlined,
      color: GteShellTheme.warning,
    );
  }
  if (profile.disputeHistory.isEmpty) {
    return const _TruthGate(
      label: 'Disputes clear',
      icon: Icons.gavel_outlined,
      color: GteShellTheme.positive,
    );
  }
  return const _TruthGate(
    label: 'Disputes tracked',
    icon: Icons.gavel_outlined,
    color: GteShellTheme.positive,
  );
}

String _shortDateTime(DateTime value) {
  final DateTime local = value.toLocal();
  final String month = local.month.toString().padLeft(2, '0');
  final String day = local.day.toString().padLeft(2, '0');
  final String hour = local.hour.toString().padLeft(2, '0');
  final String minute = local.minute.toString().padLeft(2, '0');
  return '$month/$day $hour:$minute';
}

IconData _auditIcon(String state) {
  switch (state) {
    case 'ready':
      return Icons.check_circle_outline;
    case 'blocked':
      return Icons.block_outlined;
    case 'syncing':
      return Icons.sync_outlined;
    default:
      return Icons.radio_button_unchecked;
  }
}

TraderMarket? _primaryMarket(TraderOverview overview) {
  for (final List<TraderMarket> bucket in <List<TraderMarket>>[
    overview.trending,
    overview.liquidityActivity,
    overview.mostTradedFanCoins,
    overview.topGainers,
    overview.topLosers,
  ]) {
    if (bucket.isNotEmpty) {
      return bucket.first;
    }
  }
  return null;
}

TraderQuoteLockState _quoteLockForMarket(
  TraderMarket? market,
  double? quotePrice,
) {
  if (market == null || quotePrice == null) {
    return const TraderQuoteLockState.idle();
  }

  // The current Trader overview does not expose POST /trader/quote output yet.
  // Keep order confirmation disabled until a backend quote lock DTO is present.
  return const TraderQuoteLockState.idle();
}

IconData _iconForSection(String label) {
  switch (label) {
    case 'Marketplace':
      return Icons.show_chart;
    case 'Profile':
      return Icons.badge_outlined;
    case 'Dashboard':
      return Icons.dashboard_customize_outlined;
    case 'Buy/Sell':
      return Icons.swap_vertical_circle_outlined;
    case 'Order Book':
      return Icons.format_list_numbered_outlined;
    case 'Orders':
      return Icons.receipt_long_outlined;
    case 'Disputes':
      return Icons.gavel_outlined;
    case 'Settlements':
      return Icons.task_alt_outlined;
    case 'Deposit':
      return Icons.add_card_outlined;
    case 'Withdrawal':
      return Icons.payments_outlined;
    default:
      return Icons.candlestick_chart_outlined;
  }
}
