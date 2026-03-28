import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/data/admin_finance_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/models/admin_finance_models.dart';
import 'package:gte_frontend/widgets/gte_formatters.dart';
import 'package:gte_frontend/widgets/gte_metric_chip.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';
import 'package:gte_frontend/widgets/gtex_branding.dart';

class AdminFinancialDashboardScreen extends StatefulWidget {
  const AdminFinancialDashboardScreen({
    super.key,
    required this.baseUrl,
    required this.accessToken,
    required this.backendMode,
  });

  final String baseUrl;
  final String accessToken;
  final GteBackendMode backendMode;

  @override
  State<AdminFinancialDashboardScreen> createState() =>
      _AdminFinancialDashboardScreenState();
}

class _AdminFinancialDashboardScreenState
    extends State<AdminFinancialDashboardScreen> {
  late final AdminFinanceApi _api;
  late Future<AdminFinanceControlTower> _controlTowerFuture;
  late Future<AdminEconomySimulationResult> _simulationFuture;

  final TextEditingController _dailyActiveUsers = TextEditingController();
  final TextEditingController _matchesPerUser = TextEditingController();
  final TextEditingController _fanSpendPerMatch = TextEditingController();
  final TextEditingController _fanMintPerMatch = TextEditingController();
  final TextEditingController _purchaseRate = TextEditingController();
  final TextEditingController _purchaseAmount = TextEditingController();
  final TextEditingController _tournamentEntry = TextEditingController();
  final TextEditingController _participationRate = TextEditingController();
  final TextEditingController _rewardPayout = TextEditingController();

  bool _runningSimulation = false;

  @override
  void initState() {
    super.initState();
    _api = AdminFinanceApi.standard(
      baseUrl: widget.baseUrl,
      accessToken: widget.accessToken,
      mode: widget.backendMode,
    );
    _seedSimulationInputs();
    _controlTowerFuture = _api.fetchControlTower();
    _simulationFuture = _api.simulate();
  }

  @override
  void dispose() {
    _dailyActiveUsers.dispose();
    _matchesPerUser.dispose();
    _fanSpendPerMatch.dispose();
    _fanMintPerMatch.dispose();
    _purchaseRate.dispose();
    _purchaseAmount.dispose();
    _tournamentEntry.dispose();
    _participationRate.dispose();
    _rewardPayout.dispose();
    super.dispose();
  }

  void _seedSimulationInputs() {
    const AdminEconomySimulationConfig defaults =
        AdminEconomySimulationConfig.defaults();
    _dailyActiveUsers.text = defaults.dailyActiveUsers.toString();
    _matchesPerUser.text = defaults.avgMatchesPerUser.toStringAsFixed(1);
    _fanSpendPerMatch.text = defaults.fanSpendPerMatch.toStringAsFixed(1);
    _fanMintPerMatch.text = defaults.fanMintPerMatch.toStringAsFixed(1);
    _purchaseRate.text = defaults.gtexPurchaseRate.toStringAsFixed(2);
    _purchaseAmount.text = defaults.gtexPurchaseAmount.toStringAsFixed(1);
    _tournamentEntry.text = defaults.tournamentEntryGtex.toStringAsFixed(1);
    _participationRate.text = defaults.tournamentParticipationRate
        .toStringAsFixed(2);
    _rewardPayout.text = defaults.gtexRewardPayoutPerMatch.toStringAsFixed(1);
  }

  Future<void> _refresh() async {
    setState(() {
      _controlTowerFuture = _api.fetchControlTower();
      _simulationFuture = _api.simulate(config: _currentConfig());
    });
    await Future.wait<Object?>(<Future<Object?>>[
      _controlTowerFuture,
      _simulationFuture,
    ]);
  }

  Future<void> _runSimulation() async {
    setState(() {
      _runningSimulation = true;
      _simulationFuture = _api.simulate(config: _currentConfig());
    });
    try {
      await _simulationFuture;
      if (!mounted) {
        return;
      }
      AppFeedback.showSuccess(context, '30-day economy projection refreshed.');
    } catch (error) {
      if (!mounted) {
        return;
      }
      AppFeedback.showError(context, 'Unable to refresh economy projection.');
    } finally {
      if (mounted) {
        setState(() => _runningSimulation = false);
      }
    }
  }

  AdminEconomySimulationConfig _currentConfig() {
    const AdminEconomySimulationConfig defaults =
        AdminEconomySimulationConfig.defaults();
    return AdminEconomySimulationConfig(
      dailyActiveUsers:
          int.tryParse(_dailyActiveUsers.text.trim()) ??
          defaults.dailyActiveUsers,
      avgMatchesPerUser: _parseDouble(
        _matchesPerUser.text,
        defaults.avgMatchesPerUser,
      ),
      fanSpendPerMatch: _parseDouble(
        _fanSpendPerMatch.text,
        defaults.fanSpendPerMatch,
      ),
      fanMintPerMatch: _parseDouble(
        _fanMintPerMatch.text,
        defaults.fanMintPerMatch,
      ),
      gtexPurchaseRate: _parseDouble(
        _purchaseRate.text,
        defaults.gtexPurchaseRate,
      ),
      gtexPurchaseAmount: _parseDouble(
        _purchaseAmount.text,
        defaults.gtexPurchaseAmount,
      ),
      tournamentEntryGtex: _parseDouble(
        _tournamentEntry.text,
        defaults.tournamentEntryGtex,
      ),
      tournamentParticipationRate: _parseDouble(
        _participationRate.text,
        defaults.tournamentParticipationRate,
      ),
      gtexRewardPayoutPerMatch: _parseDouble(
        _rewardPayout.text,
        defaults.gtexRewardPayoutPerMatch,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: const Text('Financial control tower'),
          actions: <Widget>[
            IconButton(onPressed: _refresh, icon: const Icon(Icons.refresh)),
          ],
        ),
        body: FutureBuilder<AdminFinanceControlTower>(
          future: _controlTowerFuture,
          builder: (
            BuildContext context,
            AsyncSnapshot<AdminFinanceControlTower> snapshot,
          ) {
            if (snapshot.connectionState == ConnectionState.waiting &&
                !snapshot.hasData) {
              return const Center(child: CircularProgressIndicator());
            }
            if (!snapshot.hasData) {
              return Center(
                child: GteStatePanel(
                  title: 'Financial dashboard unavailable',
                  message: 'Unable to load admin economy metrics right now.',
                  icon: Icons.monitor_heart_outlined,
                  actionLabel: 'Retry',
                  onAction: _refresh,
                  accentColor: GteShellTheme.accentAdmin,
                ),
              );
            }
            final AdminFinanceControlTower tower = snapshot.data!;
            final List<AdminFinanceDailyStat> trailingHistory =
                tower.history.length > 10
                    ? tower.history.sublist(tower.history.length - 10)
                    : tower.history;

            return RefreshIndicator(
              onRefresh: _refresh,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(20, 14, 20, 120),
                children: <Widget>[
                  _HeroPanel(
                    tower: tower,
                    onRunSimulation: _runSimulation,
                    runningSimulation: _runningSimulation,
                  ),
                  const SizedBox(height: 18),
                  const GtexSectionHeader(
                    eyebrow: 'LIVE ECONOMY',
                    title: 'Revenue, supply, and burn pressure at a glance.',
                    description:
                        'Track daily inflow, token balance, and match spend before imbalance becomes visible to users.',
                    accent: GteShellTheme.accentAdmin,
                  ),
                  const SizedBox(height: 12),
                  _MetricChartPanel(
                    title: 'Revenue pulse',
                    subtitle:
                        'Daily NGN inflow from GTex purchases and treasury confirmations.',
                    accent: GteShellTheme.accentAdmin,
                    valueLabel: gteFormatFiat(
                      tower.dailyRevenueNaira,
                      currency: 'NGN',
                    ),
                    chart: _MiniBarChart(
                      values: trailingHistory
                          .map(
                            (AdminFinanceDailyStat stat) => stat.revenueNaira,
                          )
                          .toList(growable: false),
                      labels: trailingHistory
                          .map(
                            (AdminFinanceDailyStat stat) =>
                                '${stat.date.month}/${stat.date.day}',
                          )
                          .toList(growable: false),
                      color: GteShellTheme.accentAdmin,
                    ),
                  ),
                  const SizedBox(height: 12),
                  _MetricChartPanel(
                    title: 'GTex supply curve',
                    subtitle:
                        'Watch how mint, fees, and tournament sinks shape your circulating GTex position.',
                    accent: GteShellTheme.accentCapital,
                    valueLabel: gteFormatGtex(tower.gtexSupply),
                    chart: _MiniBarChart(
                      values: trailingHistory
                          .map((AdminFinanceDailyStat stat) => stat.gtexSupply)
                          .toList(growable: false),
                      labels: trailingHistory
                          .map(
                            (AdminFinanceDailyStat stat) =>
                                '${stat.date.month}/${stat.date.day}',
                          )
                          .toList(growable: false),
                      color: GteShellTheme.accentCapital,
                    ),
                  ),
                  const SizedBox(height: 12),
                  GteSurfacePanel(
                    accentColor: GteShellTheme.accentWarm,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'Fan Coin burn heatmap',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: 6),
                        Text(
                          'Daily burn intensity across engagement events. Darker tiles mean faster burn.',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                        const SizedBox(height: 14),
                        _BurnHeatStrip(
                          stats: tower.history,
                          color: GteShellTheme.accentWarm,
                        ),
                        const SizedBox(height: 12),
                        Wrap(
                          spacing: 10,
                          runSpacing: 10,
                          children: <Widget>[
                            GteMetricChip(
                              label: 'Fan burn today',
                              value: gteFormatFanCoin(tower.fanBurnedToday),
                            ),
                            GteMetricChip(
                              label: 'Fan mint today',
                              value: gteFormatFanCoin(tower.fanMintedToday),
                              positive: false,
                            ),
                            GteMetricChip(
                              label: 'Fan burn/mint',
                              value: _formatRatio(tower.fanBurnMintRatio),
                              positive: (tower.fanBurnMintRatio ?? 0) >= 1,
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 18),
                  const GtexSectionHeader(
                    eyebrow: 'HEALTH PANEL',
                    title: 'Economy alerts, liquidity, and rails status.',
                    description:
                        'This is the admin lane for inflation signals, payout pressure, and gateway posture.',
                    accent: GteShellTheme.accentCapital,
                  ),
                  const SizedBox(height: 12),
                  GteSurfacePanel(
                    accentColor: _riskColor(context, tower.inflationRisk),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'Economy health',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: 12),
                        Wrap(
                          spacing: 10,
                          runSpacing: 10,
                          children: <Widget>[
                            GteMetricChip(
                              label: 'Inflation risk',
                              value: tower.inflationRisk,
                              positive: tower.inflationRisk == 'LOW',
                            ),
                            GteMetricChip(
                              label: 'Liquidity',
                              value: tower.liquidityStatus,
                              positive: tower.liquidityStatus == 'HEALTHY',
                            ),
                            GteMetricChip(
                              label: 'User spend trend',
                              value: tower.userSpendTrend,
                              positive:
                                  tower.userSpendTrend.toUpperCase() == 'UP',
                            ),
                            GteMetricChip(
                              label: 'GTex burn/mint',
                              value: _formatRatio(tower.gtexBurnMintRatio),
                              positive: (tower.gtexBurnMintRatio ?? 0) >= 1,
                            ),
                          ],
                        ),
                        const SizedBox(height: 16),
                        if (tower.alerts.isEmpty)
                          const GteStatePanel(
                            title: 'No active alerts',
                            message:
                                'Economy rails are quiet and no high-priority balance issues are currently active.',
                            icon: Icons.verified_outlined,
                            accentColor: GteShellTheme.accentCommunity,
                          )
                        else
                          ...tower.alerts.map(
                            (AdminFinanceAlert alert) => Padding(
                              padding: const EdgeInsets.only(bottom: 10),
                              child: _AlertTile(alert: alert),
                            ),
                          ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 12),
                  GteSurfacePanel(
                    accentColor: GteShellTheme.accentCapital,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'Cash rails',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: 6),
                        Text(
                          'Monitor payment gateways, withdrawal posture, and queue load without leaving the command tower.',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                        const SizedBox(height: 14),
                        Wrap(
                          spacing: 10,
                          runSpacing: 10,
                          children: <Widget>[
                            GteMetricChip(
                              label: 'Deposit mode',
                              value: _labelize(tower.cashRails.depositMode),
                              positive:
                                  tower.cashRails.automaticDepositsEnabled,
                            ),
                            GteMetricChip(
                              label: 'Withdrawal mode',
                              value: _labelize(tower.cashRails.withdrawalMode),
                              positive:
                                  tower.cashRails.automaticWithdrawalsEnabled,
                            ),
                            GteMetricChip(
                              label: 'Pending orders',
                              value: tower.pendingPurchaseOrders.toString(),
                              positive: tower.pendingPurchaseOrders < 20,
                            ),
                            GteMetricChip(
                              label: 'Pending withdrawals',
                              value: tower.pendingWithdrawals.toString(),
                              positive: tower.pendingWithdrawals < 10,
                            ),
                            GteMetricChip(
                              label: 'Pending KYC',
                              value: tower.pendingKyc.toString(),
                              positive: tower.pendingKyc < 25,
                            ),
                            GteMetricChip(
                              label: 'Withdrawal range',
                              value:
                                  '${gteFormatFiat(tower.cashRails.minWithdrawal, currency: tower.cashRails.currencyCode)} - ${gteFormatFiat(tower.cashRails.maxWithdrawal, currency: tower.cashRails.currencyCode)}',
                            ),
                          ],
                        ),
                        const SizedBox(height: 14),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: tower.cashRails.paymentMethods
                              .map(
                                (String method) => _LabelBadge(
                                  label: method,
                                  color: GteShellTheme.accentCapital,
                                ),
                              )
                              .toList(growable: false),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 18),
                  const GtexSectionHeader(
                    eyebrow: 'TRANSACTION WATCH',
                    title:
                        'Large transfers, pool pressure, and price movement.',
                    description:
                        'Use these feeds to spot suspicious spikes or demand shocks before they distort the live economy.',
                    accent: GteShellTheme.accentCommunity,
                  ),
                  const SizedBox(height: 12),
                  GteSurfacePanel(
                    accentColor: GteShellTheme.accentCommunity,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'Top transactions',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: 12),
                        if (tower.topTransactions.isEmpty)
                          const Text('No large transactions available.')
                        else
                          ...tower.topTransactions.map(
                            (AdminFinanceLargeTransaction transaction) =>
                                Padding(
                                  padding: const EdgeInsets.only(bottom: 10),
                                  child: _TransactionTile(
                                    transaction: transaction,
                                  ),
                                ),
                          ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 12),
                  GteSurfacePanel(
                    accentColor: GteShellTheme.accentClub,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'Gameplay economy',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: 12),
                        Wrap(
                          spacing: 10,
                          runSpacing: 10,
                          children: <Widget>[
                            GteMetricChip(
                              label: 'Avg spend per match',
                              value: gteFormatGtex(tower.avgSpendPerMatch),
                            ),
                            GteMetricChip(
                              label: 'Marketplace fees',
                              value: gteFormatGtex(tower.marketplaceFeeAmount),
                            ),
                          ],
                        ),
                        const SizedBox(height: 14),
                        Text(
                          'Player price trends',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 8),
                        ...tower.playerPriceTrends.map(
                          (AdminFinancePlayerTrend trend) => Padding(
                            padding: const EdgeInsets.only(bottom: 8),
                            child: _TrendTile(trend: trend),
                          ),
                        ),
                        const SizedBox(height: 14),
                        Text(
                          'Tournament pools',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 8),
                        ...tower.tournamentPoolSizes.map(
                          (AdminFinanceTournamentPool pool) => Padding(
                            padding: const EdgeInsets.only(bottom: 8),
                            child: _PoolTile(pool: pool),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 18),
                  const GtexSectionHeader(
                    eyebrow: 'PREDICTION ENGINE',
                    title:
                        'Run the 30-day simulator before you touch the levers.',
                    description:
                        'Model user demand, match spend, and tournament sink pressure to catch inflation or supply freezes early.',
                    accent: GteShellTheme.accentArena,
                  ),
                  const SizedBox(height: 12),
                  GteSurfacePanel(
                    accentColor: GteShellTheme.accentArena,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'Simulation controls',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: 12),
                        Wrap(
                          spacing: 12,
                          runSpacing: 12,
                          children: <Widget>[
                            _NumberField(
                              controller: _dailyActiveUsers,
                              label: 'Daily active users',
                            ),
                            _NumberField(
                              controller: _matchesPerUser,
                              label: 'Matches per user',
                            ),
                            _NumberField(
                              controller: _fanSpendPerMatch,
                              label: 'Fan spend per match',
                            ),
                            _NumberField(
                              controller: _fanMintPerMatch,
                              label: 'Fan mint per match',
                            ),
                            _NumberField(
                              controller: _purchaseRate,
                              label: 'GTex purchase rate',
                            ),
                            _NumberField(
                              controller: _purchaseAmount,
                              label: 'GTex purchase amount',
                            ),
                            _NumberField(
                              controller: _tournamentEntry,
                              label: 'Tournament entry GTex',
                            ),
                            _NumberField(
                              controller: _participationRate,
                              label: 'Tournament participation',
                            ),
                            _NumberField(
                              controller: _rewardPayout,
                              label: 'Reward payout per match',
                            ),
                          ],
                        ),
                        const SizedBox(height: 14),
                        FilledButton.icon(
                          onPressed: _runningSimulation ? null : _runSimulation,
                          icon:
                              _runningSimulation
                                  ? const SizedBox(
                                    width: 16,
                                    height: 16,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                    ),
                                  )
                                  : const Icon(Icons.timeline_outlined),
                          label: const Text('Run 30-day projection'),
                        ),
                        const SizedBox(height: 16),
                        FutureBuilder<AdminEconomySimulationResult>(
                          future: _simulationFuture,
                          builder: (
                            BuildContext context,
                            AsyncSnapshot<AdminEconomySimulationResult>
                            simulationSnapshot,
                          ) {
                            if (simulationSnapshot.connectionState ==
                                    ConnectionState.waiting &&
                                !simulationSnapshot.hasData) {
                              return const Padding(
                                padding: EdgeInsets.symmetric(vertical: 16),
                                child: Center(
                                  child: CircularProgressIndicator(),
                                ),
                              );
                            }
                            if (!simulationSnapshot.hasData) {
                              return const Text(
                                'Projection unavailable right now.',
                              );
                            }
                            final AdminEconomySimulationResult result =
                                simulationSnapshot.data!;
                            final List<AdminEconomySimulationPoint>
                            trailingProjections =
                                result.projections.length > 10
                                    ? result.projections.sublist(
                                      result.projections.length - 10,
                                    )
                                    : result.projections;

                            return Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                Wrap(
                                  spacing: 10,
                                  runSpacing: 10,
                                  children: <Widget>[
                                    GteMetricChip(
                                      label: 'Day 30 GTex',
                                      value: gteFormatGtex(
                                        result.summary.endingGtexSupply,
                                      ),
                                      positive:
                                          result.summary.inflationRisk == 'LOW',
                                    ),
                                    GteMetricChip(
                                      label: 'Day 30 Fan Coin',
                                      value: gteFormatFanCoin(
                                        result.summary.endingFanSupply,
                                      ),
                                    ),
                                    GteMetricChip(
                                      label: 'Inflation risk',
                                      value: result.summary.inflationRisk,
                                      positive:
                                          result.summary.inflationRisk == 'LOW',
                                    ),
                                    GteMetricChip(
                                      label: 'GTex burn/mint',
                                      value: _formatRatio(
                                        result.summary.gtexBurnMintRatio,
                                      ),
                                      positive:
                                          (result.summary.gtexBurnMintRatio ??
                                              0) >=
                                          1,
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 14),
                                _MetricChartPanel(
                                  title: 'Projection curve',
                                  subtitle:
                                      'Trailing 10 points from the 30-day GTex supply projection.',
                                  accent: GteShellTheme.accentArena,
                                  valueLabel:
                                      'Days ${trailingProjections.first.day}-${trailingProjections.last.day}',
                                  chart: _MiniBarChart(
                                    values: trailingProjections
                                        .map(
                                          (AdminEconomySimulationPoint point) =>
                                              point.gtexSupply,
                                        )
                                        .toList(growable: false),
                                    labels: trailingProjections
                                        .map(
                                          (AdminEconomySimulationPoint point) =>
                                              'D${point.day}',
                                        )
                                        .toList(growable: false),
                                    color: GteShellTheme.accentArena,
                                  ),
                                ),
                                const SizedBox(height: 14),
                                Text(
                                  'Recommendations',
                                  style:
                                      Theme.of(context).textTheme.titleMedium,
                                ),
                                const SizedBox(height: 8),
                                ...result.summary.recommendations.map(
                                  (String item) => Padding(
                                    padding: const EdgeInsets.only(bottom: 8),
                                    child: Row(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: <Widget>[
                                        const Padding(
                                          padding: EdgeInsets.only(top: 6),
                                          child: Icon(
                                            Icons.adjust,
                                            size: 14,
                                            color: GteShellTheme.accentArena,
                                          ),
                                        ),
                                        const SizedBox(width: 8),
                                        Expanded(
                                          child: Text(
                                            item,
                                            style:
                                                Theme.of(
                                                  context,
                                                ).textTheme.bodySmall,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                              ],
                            );
                          },
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            );
          },
        ),
      ),
    );
  }
}

class _HeroPanel extends StatelessWidget {
  const _HeroPanel({
    required this.tower,
    required this.onRunSimulation,
    required this.runningSimulation,
  });

  final AdminFinanceControlTower tower;
  final VoidCallback onRunSimulation;
  final bool runningSimulation;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      emphasized: true,
      accentColor: GteShellTheme.accentAdmin,
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
                      'Mission control for GTEX economy risk.',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Last sync ${gteFormatRelativeTime(tower.generatedAt)}. If demand, liquidity, or token balance drifts, this board should show it first.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              FilledButton.tonalIcon(
                onPressed: runningSimulation ? null : onRunSimulation,
                icon:
                    runningSimulation
                        ? const SizedBox(
                          width: 14,
                          height: 14,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                        : const Icon(Icons.auto_graph_outlined),
                label: const Text('Run sim'),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              GteMetricChip(
                label: 'Revenue today',
                value: gteFormatFiat(tower.dailyRevenueNaira, currency: 'NGN'),
              ),
              GteMetricChip(
                label: 'GTex supply',
                value: gteFormatGtex(tower.gtexSupply),
                positive: tower.inflationRisk == 'LOW',
              ),
              GteMetricChip(
                label: 'Fan supply',
                value: gteFormatFanCoin(tower.fanSupply),
              ),
              GteMetricChip(
                label: 'Inflation risk',
                value: tower.inflationRisk,
                positive: tower.inflationRisk == 'LOW',
              ),
              GteMetricChip(
                label: 'Liquidity',
                value: tower.liquidityStatus,
                positive: tower.liquidityStatus == 'HEALTHY',
              ),
              GteMetricChip(
                label: 'Avg spend/match',
                value: gteFormatGtex(tower.avgSpendPerMatch),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _MetricChartPanel extends StatelessWidget {
  const _MetricChartPanel({
    required this.title,
    required this.subtitle,
    required this.accent,
    required this.valueLabel,
    required this.chart,
  });

  final String title;
  final String subtitle;
  final Color accent;
  final String valueLabel;
  final Widget chart;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      accentColor: accent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(title, style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 6),
                    Text(
                      subtitle,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              _LabelBadge(label: valueLabel, color: accent),
            ],
          ),
          const SizedBox(height: 14),
          chart,
        ],
      ),
    );
  }
}

class _MiniBarChart extends StatelessWidget {
  const _MiniBarChart({
    required this.values,
    required this.labels,
    required this.color,
  });

  final List<double> values;
  final List<String> labels;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final List<double> safeValues = values.isEmpty ? <double>[0] : values;
    final List<String> safeLabels = labels.isEmpty ? <String>['-'] : labels;
    final double maxValue = safeValues.reduce(math.max);
    final Color muted = GteShellTheme.tokensOf(context).textMuted;

    return SizedBox(
      height: 152,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: List<Widget>.generate(safeValues.length, (int index) {
          final double ratio =
              maxValue == 0 ? 0.12 : (safeValues[index] / maxValue).clamp(0, 1);
          return Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 3),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.end,
                children: <Widget>[
                  Expanded(
                    child: Align(
                      alignment: Alignment.bottomCenter,
                      child: Container(
                        height: math.max(10, ratio * 96),
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(10),
                          gradient: LinearGradient(
                            begin: Alignment.topCenter,
                            end: Alignment.bottomCenter,
                            colors: <Color>[
                              color.withValues(alpha: 0.88),
                              color.withValues(alpha: 0.28),
                            ],
                          ),
                          border: Border.all(
                            color: color.withValues(alpha: 0.26),
                          ),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    safeLabels[index],
                    style: Theme.of(
                      context,
                    ).textTheme.bodySmall?.copyWith(color: muted, fontSize: 10),
                  ),
                ],
              ),
            ),
          );
        }),
      ),
    );
  }
}

class _BurnHeatStrip extends StatelessWidget {
  const _BurnHeatStrip({required this.stats, required this.color});

  final List<AdminFinanceDailyStat> stats;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final List<AdminFinanceDailyStat> safeStats =
        stats.isEmpty ? const <AdminFinanceDailyStat>[] : stats;
    final double maxBurn =
        safeStats.isEmpty
            ? 1
            : safeStats
                .map((AdminFinanceDailyStat stat) => stat.fanBurned)
                .reduce(math.max);

    return Wrap(
      spacing: 6,
      runSpacing: 6,
      children: safeStats
          .map((AdminFinanceDailyStat stat) {
            final double ratio =
                maxBurn == 0 ? 0 : (stat.fanBurned / maxBurn).clamp(0, 1);
            return Tooltip(
              message:
                  '${stat.date.year}-${stat.date.month.toString().padLeft(2, '0')}-${stat.date.day.toString().padLeft(2, '0')}: ${gteFormatFanCoin(stat.fanBurned)}',
              child: Container(
                width: 18,
                height: 18,
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.16 + (ratio * 0.72)),
                  borderRadius: BorderRadius.circular(5),
                  border: Border.all(
                    color: color.withValues(alpha: 0.18 + (ratio * 0.28)),
                  ),
                ),
              ),
            );
          })
          .toList(growable: false),
    );
  }
}

class _AlertTile extends StatelessWidget {
  const _AlertTile({required this.alert});

  final AdminFinanceAlert alert;

  @override
  Widget build(BuildContext context) {
    final Color color = _alertColor(alert.level);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: color.withValues(alpha: 0.22)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(Icons.warning_amber_rounded, color: color),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  children: <Widget>[
                    Expanded(
                      child: Text(
                        alert.title,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                    ),
                    _LabelBadge(label: alert.level.toUpperCase(), color: color),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  alert.message,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: 6),
                Text(
                  '${alert.metricKey} • ${gteFormatRelativeTime(alert.createdAt)}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _TransactionTile extends StatelessWidget {
  const _TransactionTile({required this.transaction});

  final AdminFinanceLargeTransaction transaction;

  @override
  Widget build(BuildContext context) {
    final bool positive = transaction.amount >= 0;
    final Color color =
        positive ? GteShellTheme.positive : GteShellTheme.negative;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: color.withValues(alpha: 0.18)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(
            positive ? Icons.south_west_outlined : Icons.north_east_outlined,
            color: color,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  children: <Widget>[
                    Expanded(
                      child: Text(
                        transaction.reference ?? transaction.transactionId,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                    ),
                    Text(
                      _formatUnitAmount(transaction.amount, transaction.unit),
                      style: Theme.of(
                        context,
                      ).textTheme.titleMedium?.copyWith(color: color),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  '${transaction.reason} • ${transaction.sourceTag}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: 4),
                Text(
                  '${transaction.accountCode} • ${gteFormatDateTime(transaction.createdAt)}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _TrendTile extends StatelessWidget {
  const _TrendTile({required this.trend});

  final AdminFinancePlayerTrend trend;

  @override
  Widget build(BuildContext context) {
    final bool positive = trend.trendDirection.toLowerCase() != 'down';
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: (positive ? GteShellTheme.positive : GteShellTheme.negative)
              .withValues(alpha: 0.22),
        ),
      ),
      child: Row(
        children: <Widget>[
          Icon(
            positive ? Icons.trending_up : Icons.trending_down,
            color: positive ? GteShellTheme.positive : GteShellTheme.negative,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              trend.playerId,
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ),
          Text(
            '${trend.momentum7dPct.toStringAsFixed(1)}% / ${trend.momentum30dPct.toStringAsFixed(1)}%',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(width: 10),
          Text(
            trend.lastTradePriceCredits == null
                ? '--'
                : gteFormatCredits(trend.lastTradePriceCredits!),
            style: Theme.of(context).textTheme.titleMedium,
          ),
        ],
      ),
    );
  }
}

class _PoolTile extends StatelessWidget {
  const _PoolTile({required this.pool});

  final AdminFinanceTournamentPool pool;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: GteShellTheme.accentClub.withValues(alpha: 0.2),
        ),
      ),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  pool.competitionId,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 4),
                Text(
                  '${pool.poolType} • ${pool.status}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Text(
            gteFormatCompetitionAmount(pool.amount, pool.currency),
            style: Theme.of(context).textTheme.titleMedium,
          ),
        ],
      ),
    );
  }
}

class _NumberField extends StatelessWidget {
  const _NumberField({required this.controller, required this.label});

  final TextEditingController controller;
  final String label;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 220,
      child: TextField(
        controller: controller,
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        decoration: InputDecoration(labelText: label),
      ),
    );
  }
}

class _LabelBadge extends StatelessWidget {
  const _LabelBadge({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.24)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
          color: color,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

Color _alertColor(String level) {
  switch (level.toLowerCase()) {
    case 'high':
      return GteShellTheme.negative;
    case 'medium':
      return GteShellTheme.warning;
    default:
      return GteShellTheme.positive;
  }
}

Color _riskColor(BuildContext context, String risk) {
  switch (risk.toUpperCase()) {
    case 'HIGH':
      return GteShellTheme.negative;
    case 'MEDIUM':
      return GteShellTheme.warning;
    default:
      return GteShellTheme.tokensOf(context).positive;
  }
}

String _formatUnitAmount(double amount, String unit) {
  if (unit.toLowerCase() == 'credit') {
    return gteFormatFanCoin(amount.abs());
  }
  return gteFormatGtex(amount.abs());
}

String _formatRatio(double? ratio) {
  if (ratio == null) {
    return '--';
  }
  return '${ratio.toStringAsFixed(2)}x';
}

String _labelize(String raw) {
  return raw.replaceAll('_', ' ').toUpperCase();
}

double _parseDouble(String raw, double fallback) {
  return double.tryParse(raw.trim()) ?? fallback;
}
