import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../../core/constants/app_breakpoints.dart';
import '../../../core/constants/app_spacing.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/utils/app_formatters.dart';
import '../../../core/widgets/app_hover_lift.dart';
import '../../../core/widgets/app_press_scale.dart';
import '../../../core/widgets/gtex_surface_card.dart';
import '../../../shared/providers/exchange_hub_provider.dart';
import '../../../shared/widgets/metric_pill.dart';

class ExchangeWalletDashboardCard extends StatelessWidget {
  const ExchangeWalletDashboardCard({
    super.key,
    required this.state,
    required this.onDeposit,
    required this.onWithdraw,
    required this.onConvert,
  });

  final ExchangeHubState state;
  final VoidCallback onDeposit;
  final VoidCallback onWithdraw;
  final VoidCallback onConvert;

  @override
  Widget build(BuildContext context) {
    return GtexSurfaceCard(
      glowColor: AppColors.primary,
      padding: EdgeInsets.zero,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(cardRadius),
        child: Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: <Color>[
                Color(0xFF062316),
                Color(0xFF0D3A24),
                Color(0xFF121826),
              ],
            ),
          ),
          child: Stack(
            children: <Widget>[
              const Positioned.fill(child: _JerseyBackdrop()),
              Padding(
                padding: const EdgeInsets.all(spacingLG),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Wrap(
                      spacing: spacingSM,
                      runSpacing: spacingSM,
                      children: const <Widget>[
                        _PillLabel(
                          label: 'Wallet Dashboard',
                          color: AppColors.primary,
                        ),
                        _PillLabel(
                          label: 'Closed-loop Fan Coin',
                          color: AppColors.gold,
                        ),
                      ],
                    ),
                    const SizedBox(height: spacingLG),
                    LayoutBuilder(
                      builder: (
                        BuildContext context,
                        BoxConstraints constraints,
                      ) {
                        final bool stacked =
                            constraints.maxWidth < AppBreakpoints.compact;
                        final Widget balances = _BalanceDeck(state: state);
                        final Widget actions = _WalletActions(
                          onDeposit: onDeposit,
                          onWithdraw: onWithdraw,
                          onConvert: onConvert,
                        );
                        if (stacked) {
                          return Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              balances,
                              const SizedBox(height: spacingLG),
                              actions,
                            ],
                          );
                        }
                        return Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Expanded(flex: 3, child: balances),
                            const SizedBox(width: spacingLG),
                            Expanded(flex: 2, child: actions),
                          ],
                        );
                      },
                    ),
                    const SizedBox(height: spacingLG),
                    Wrap(
                      spacing: spacingSM,
                      runSpacing: spacingSM,
                      children: <Widget>[
                        MetricPill(
                          label: 'This week spend',
                          value: AppFormatters.naira(state.weeklySpendNaira),
                          highlight: true,
                        ),
                        MetricPill(
                          label: 'Matches watched',
                          value: '${state.matchesWatched}',
                        ),
                        MetricPill(
                          label: 'Trades made',
                          value: '${state.tradesMade}',
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class ExchangeActivityPanel extends StatelessWidget {
  const ExchangeActivityPanel({super.key, required this.state});

  final ExchangeHubState state;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool stacked = constraints.maxWidth < AppBreakpoints.medium;
        final Widget transactions = GtexSurfaceCard(
          glowColor: AppColors.gold,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Recent Transactions',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: spacingXS),
              Text(
                'Deposits, conversions, trades, and payouts stay readable by lane.',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: spacingLG),
              for (
                int index = 0;
                index < state.recentActivity.length;
                index++
              ) ...<Widget>[
                _ActivityTile(entry: state.recentActivity[index]),
                if (index != state.recentActivity.length - 1) ...<Widget>[
                  const SizedBox(height: spacingMD),
                  Divider(color: AppColors.divider, height: 1),
                  const SizedBox(height: spacingMD),
                ],
              ],
            ],
          ),
        );
        final Widget treasury = GtexSurfaceCard(
          glowColor: AppColors.primary,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Treasury Snapshot',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: spacingXS),
              Text(
                'Withdrawals respect the current KYC tier before NGN payouts leave the platform.',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: spacingLG),
              _TreasuryLine(label: 'Tier', value: state.kycTier.label),
              _TreasuryLine(
                label: 'Daily limit',
                value: AppFormatters.naira(state.kycTier.dailyLimitNaira),
              ),
              _TreasuryLine(
                label: 'Remaining today',
                value: AppFormatters.naira(state.remainingWithdrawalLimitNaira),
              ),
              _TreasuryLine(
                label: 'Primary bank',
                value:
                    '${state.selectedBank?.bankName ?? 'Not set'} • ${state.selectedBank?.accountNumber ?? '--'}',
              ),
            ],
          ),
        );

        if (stacked) {
          return Column(
            children: <Widget>[
              transactions,
              const SizedBox(height: spacingLG),
              treasury,
            ],
          );
        }
        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Expanded(flex: 3, child: transactions),
            const SizedBox(width: spacingLG),
            Expanded(flex: 2, child: treasury),
          ],
        );
      },
    );
  }
}

class TradingDeskSection extends StatelessWidget {
  const TradingDeskSection({
    super.key,
    required this.state,
    required this.onSearchChanged,
    required this.onFilterChanged,
    required this.onOpenPlayer,
  });

  final ExchangeHubState state;
  final ValueChanged<String> onSearchChanged;
  final ValueChanged<TradingDeskFilter> onFilterChanged;
  final ValueChanged<String> onOpenPlayer;

  @override
  Widget build(BuildContext context) {
    final List<PlayerShareListing> players = state.filteredPlayers;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        GtexSurfaceCard(
          glowColor: AppColors.primary,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Player Trading Market',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: spacingXS),
              Text(
                'Search players, price momentum, and buy/sell shares from the same desk.',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: spacingLG),
              TextField(
                key: const Key('trading-search'),
                onChanged: onSearchChanged,
                decoration: const InputDecoration(
                  hintText: 'Search player, club, or position',
                  prefixIcon: Icon(Icons.search_rounded),
                ),
              ),
              const SizedBox(height: spacingMD),
              TradingDeskFilterBar(
                activeFilter: state.activeFilter,
                onSelected: onFilterChanged,
              ),
            ],
          ),
        ),
        const SizedBox(height: spacingLG),
        LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            if (players.isEmpty) {
              return const GtexSurfaceCard(
                child: Text('No players match the active trading filters.'),
              );
            }

            final int crossAxisCount =
                constraints.maxWidth >= AppBreakpoints.expanded
                    ? 3
                    : constraints.maxWidth >= AppBreakpoints.compact
                    ? 2
                    : 1;

            return GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: players.length,
              gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: crossAxisCount,
                crossAxisSpacing: spacingMD,
                mainAxisSpacing: spacingMD,
                childAspectRatio:
                    constraints.maxWidth >= AppBreakpoints.compact
                        ? 0.72
                        : 0.82,
              ),
              itemBuilder: (BuildContext context, int index) {
                final PlayerShareListing player = players[index];
                return TradingPlayerCard(
                  player: player,
                  onTap: () => onOpenPlayer(player.id),
                );
              },
            );
          },
        ),
      ],
    );
  }
}

class ComplianceRail extends StatelessWidget {
  const ComplianceRail({super.key, required this.state});

  final ExchangeHubState state;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: <Widget>[
        GtexSurfaceCard(
          glowColor: AppColors.gold,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Legal + Compliance Layer',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: spacingXS),
              Text(
                'Nigeria stays the primary base, with GTex positioned as a closed-loop virtual currency for in-app use.',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: spacingLG),
              _BulletPoint(
                text: 'Do not present GTex as legal tender or cryptocurrency.',
              ),
              _BulletPoint(
                text:
                    'Once users can cash out, KYC tiers and withdrawal limits become non-negotiable.',
              ),
              _BulletPoint(
                text:
                    'Terms must state no guarantee of profit, volatile player values, and platform-managed pricing mechanics.',
              ),
              const SizedBox(height: spacingLG),
              Wrap(
                spacing: spacingSM,
                runSpacing: spacingSM,
                children: <Widget>[
                  _InfoBadge(
                    label: 'Basic',
                    value: AppFormatters.naira(50000),
                    caption: 'Daily payout limit',
                    color: AppColors.primary,
                  ),
                  _InfoBadge(
                    label: 'Verified',
                    value: AppFormatters.naira(500000),
                    caption: 'Daily payout limit',
                    color: AppColors.gold,
                  ),
                ],
              ),
              const SizedBox(height: spacingLG),
              Wrap(
                spacing: spacingSM,
                runSpacing: spacingSM,
                children: const <Widget>[
                  _MiniRequirement(label: 'Name'),
                  _MiniRequirement(label: 'Phone'),
                  _MiniRequirement(label: 'Bank verification'),
                  _MiniRequirement(label: 'BVN / NIN later'),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: spacingLG),
        GtexSurfaceCard(
          glowColor: AppColors.primary,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Expansion Watchlist',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: spacingLG),
              const _ExpansionTile(
                territory: 'Nigeria',
                note: 'Fintech + gaming + virtual asset framing stays central.',
              ),
              const SizedBox(height: spacingMD),
              const _ExpansionTile(
                territory: 'UK',
                note:
                    'FCA posture matters once wallet rails leave closed-loop use.',
              ),
              const SizedBox(height: spacingMD),
              const _ExpansionTile(
                territory: 'EU',
                note: 'PSD2 and AML obligations escalate quickly.',
              ),
              const SizedBox(height: spacingMD),
              const _ExpansionTile(
                territory: 'US',
                note: 'Avoid early entry while the model is still maturing.',
              ),
              const SizedBox(height: spacingLG),
              _TreasuryLine(label: 'Active tier', value: state.kycTier.label),
              _TreasuryLine(
                label: 'Current limit',
                value: AppFormatters.naira(state.kycTier.dailyLimitNaira),
              ),
            ],
          ),
        ),
        const SizedBox(height: spacingLG),
        GtexSurfaceCard(
          glowColor: AppColors.gold,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'AI Liquidity Desk',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: spacingXS),
              Text(
                'Autonomous agents seed liquidity, keep the market active, and stay inside volume caps.',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: spacingLG),
              for (
                int index = 0;
                index < state.agents.length;
                index++
              ) ...<Widget>[
                AgentDeskTile(
                  agent: state.agents[index],
                  player: state.playerById(state.agents[index].focusPlayerId),
                ),
                if (index != state.agents.length - 1)
                  const SizedBox(height: spacingMD),
              ],
            ],
          ),
        ),
      ],
    );
  }
}

class TradingDeskFilterBar extends StatelessWidget {
  const TradingDeskFilterBar({
    super.key,
    required this.activeFilter,
    required this.onSelected,
  });

  final TradingDeskFilter activeFilter;
  final ValueChanged<TradingDeskFilter> onSelected;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: TradingDeskFilter.values
            .map(
              (TradingDeskFilter filter) => Padding(
                padding: const EdgeInsets.only(right: spacingSM),
                child: ChoiceChip(
                  key: Key('trading-filter-${filter.name}'),
                  label: Text(filter.label),
                  selected: filter == activeFilter,
                  onSelected: (_) => onSelected(filter),
                ),
              ),
            )
            .toList(growable: false),
      ),
    );
  }
}

class TradingPlayerCard extends StatelessWidget {
  const TradingPlayerCard({
    super.key,
    required this.player,
    required this.onTap,
  });

  final PlayerShareListing player;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final Color accent =
        player.trendPercent >= 3
            ? AppColors.gold
            : player.userShares > 0
            ? AppColors.primary
            : AppColors.divider;

    return AppHoverLift(
      child: GtexSurfaceCard(
        key: Key('trading-card-${player.id}'),
        glowColor: accent,
        onTap: onTap,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                _InitialsAvatar(label: player.name, accent: accent),
                const SizedBox(width: spacingMD),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        player.name,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: spacingXS),
                      Text(
                        '${player.club} • ${player.position}',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: AppColors.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
                _TrendBadge(trendPercent: player.trendPercent),
              ],
            ),
            const SizedBox(height: spacingLG),
            Container(
              padding: const EdgeInsets.all(spacingMD),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(cardRadius),
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: <Color>[
                    accent.withValues(alpha: 0.12),
                    AppColors.surfaceMuted.withValues(alpha: 0.86),
                    AppColors.card,
                  ],
                ),
                border: Border.all(color: accent.withValues(alpha: 0.22)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('Price', style: Theme.of(context).textTheme.bodySmall),
                  const SizedBox(height: spacingXS),
                  Text(
                    AppFormatters.gtex(player.priceGtex),
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: spacingSM),
                  SizedBox(
                    height: 54,
                    child: MiniPriceChart(
                      points: player.chartPoints,
                      color:
                          accent == AppColors.divider
                              ? AppColors.primary
                              : accent,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: spacingMD),
            Wrap(
              spacing: spacingSM,
              runSpacing: spacingSM,
              children: <Widget>[
                MetricPill(
                  label: 'Volume',
                  value: AppFormatters.compact(player.volume),
                ),
                MetricPill(
                  label: 'Available',
                  value: '${player.sharesAvailable}',
                ),
                MetricPill(
                  label: 'Owned',
                  value: '${player.userShares}',
                  highlight: player.userShares > 0,
                ),
              ],
            ),
            const Spacer(),
            const SizedBox(height: spacingMD),
            Row(
              children: <Widget>[
                Expanded(
                  child: Text(
                    player.performanceLabel,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                ),
                const SizedBox(width: spacingSM),
                AppPressScale(
                  child: FilledButton.tonalIcon(
                    onPressed: onTap,
                    icon: const Icon(Icons.candlestick_chart_rounded),
                    label: const Text('Buy Shares'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class AgentDeskTile extends StatelessWidget {
  const AgentDeskTile({super.key, required this.agent, required this.player});

  final MarketAgentProfile agent;
  final PlayerShareListing? player;

  @override
  Widget build(BuildContext context) {
    final Color accent = switch (agent.type) {
      TradingAgentType.valueInvestor => AppColors.primary,
      TradingAgentType.momentumTrader => AppColors.gold,
      TradingAgentType.arbitrage => const Color(0xFF8FB3FF),
    };

    return Container(
      padding: const EdgeInsets.all(spacingMD),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(cardRadius),
        border: Border.all(color: accent.withValues(alpha: 0.24)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.18),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(switch (agent.type) {
                  TradingAgentType.valueInvestor => Icons.savings_rounded,
                  TradingAgentType.momentumTrader =>
                    Icons.local_fire_department_rounded,
                  TradingAgentType.arbitrage => Icons.hub_rounded,
                }, color: accent),
              ),
              const SizedBox(width: spacingMD),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      agent.type.label,
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    Text(
                      player?.name ?? 'Market focus',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              MetricPill(
                label: 'Live',
                value: '${agent.liveSharePercent}%',
                highlight: true,
              ),
            ],
          ),
          const SizedBox(height: spacingMD),
          Text(agent.lastMove, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: spacingSM),
          Text(
            agent.type.guardrail,
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(height: spacingMD),
          _MiniProgressLine(
            label: 'Market volume cap',
            progress: agent.liveSharePercent / agent.volumeCapPercent,
            accent: accent,
            valueLabel:
                '${agent.liveSharePercent}% / ${agent.volumeCapPercent}%',
          ),
        ],
      ),
    );
  }
}

class MiniPriceChart extends StatelessWidget {
  const MiniPriceChart({super.key, required this.points, required this.color});

  final List<double> points;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      painter: _MiniPriceChartPainter(points: points, color: color),
      size: Size.infinite,
    );
  }
}

class _BalanceDeck extends StatelessWidget {
  const _BalanceDeck({required this.state});

  final ExchangeHubState state;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          'Balance Card',
          style: Theme.of(context).textTheme.labelLarge?.copyWith(
            color: AppColors.textSecondary,
            letterSpacing: 1.1,
          ),
        ),
        const SizedBox(height: spacingSM),
        Text(
          key: const Key('wallet-balance-text'),
          AppFormatters.gtex(state.walletBalanceGtex),
          style: Theme.of(
            context,
          ).textTheme.displaySmall?.copyWith(fontWeight: FontWeight.w800),
        ),
        const SizedBox(height: spacingXS),
        Text(
          AppFormatters.naira(state.walletBalanceGtex * state.nairaPerGtex),
          style: Theme.of(
            context,
          ).textTheme.titleLarge?.copyWith(color: AppColors.gold),
        ),
        const SizedBox(height: spacingLG),
        Container(
          padding: const EdgeInsets.all(spacingMD),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.06),
            borderRadius: BorderRadius.circular(cardRadius),
            border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
          ),
          child: Row(
            children: <Widget>[
              Expanded(
                child: _BalanceStat(
                  label: 'GTex',
                  value: AppFormatters.gtex(state.walletBalanceGtex),
                  accent: AppColors.primary,
                ),
              ),
              const SizedBox(width: spacingMD),
              Expanded(
                child: _BalanceStat(
                  label: 'Fan Coin',
                  value: AppFormatters.fanCoin(state.fanCoinBalance),
                  accent: AppColors.gold,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _WalletActions extends StatelessWidget {
  const _WalletActions({
    required this.onDeposit,
    required this.onWithdraw,
    required this.onConvert,
  });

  final VoidCallback onDeposit;
  final VoidCallback onWithdraw;
  final VoidCallback onConvert;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          'Actions',
          style: Theme.of(context).textTheme.labelLarge?.copyWith(
            color: AppColors.textSecondary,
            letterSpacing: 1.1,
          ),
        ),
        const SizedBox(height: spacingSM),
        _ActionButton(
          buttonKey: const Key('wallet-action-deposit'),
          icon: Icons.arrow_downward_rounded,
          label: 'Deposit',
          caption: 'Paystack, KoraPay, or manual bank transfer.',
          accent: AppColors.primary,
          onTap: onDeposit,
        ),
        const SizedBox(height: spacingSM),
        _ActionButton(
          buttonKey: const Key('wallet-action-withdraw'),
          icon: Icons.arrow_upward_rounded,
          label: 'Withdraw',
          caption: 'Convert GTex back to NGN within KYC limits.',
          accent: AppColors.gold,
          onTap: onWithdraw,
        ),
        const SizedBox(height: spacingSM),
        _ActionButton(
          buttonKey: const Key('wallet-action-convert'),
          icon: Icons.sync_alt_rounded,
          label: 'Convert',
          caption: 'Move GTex into Fan Coin for closed-loop spend.',
          accent: const Color(0xFF8FB3FF),
          onTap: onConvert,
        ),
      ],
    );
  }
}

class DepositFlowSheet extends StatefulWidget {
  const DepositFlowSheet({
    super.key,
    required this.onSubmitInstant,
    required this.onSubmitManual,
  });

  final ValueChanged<DepositFlowRequest> onSubmitInstant;
  final ValueChanged<DepositFlowRequest> onSubmitManual;

  @override
  State<DepositFlowSheet> createState() => _DepositFlowSheetState();
}

class _DepositFlowSheetState extends State<DepositFlowSheet> {
  final TextEditingController _amountController = TextEditingController();
  PaymentMethod _selectedMethod = PaymentMethod.paystack;
  bool _receiptAttached = false;

  @override
  void dispose() {
    _amountController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return _SheetFrame(
      key: const Key('deposit-flow-sheet'),
      title: 'Deposit Flow',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          _SheetStepLabel(index: 1, title: 'Choose method'),
          const SizedBox(height: spacingMD),
          for (final PaymentMethod method in PaymentMethod.values) ...<Widget>[
            _MethodTile(
              method: method,
              selected: method == _selectedMethod,
              onTap: () => setState(() => _selectedMethod = method),
            ),
            if (method != PaymentMethod.values.last)
              const SizedBox(height: spacingSM),
          ],
          const SizedBox(height: spacingLG),
          const _SheetStepLabel(index: 2, title: 'Enter amount'),
          const SizedBox(height: spacingMD),
          TextField(
            controller: _amountController,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: const InputDecoration(
              labelText: 'Amount in NGN',
              prefixText: '₦',
            ),
          ),
          const SizedBox(height: spacingLG),
          _SheetStepLabel(
            index: 3,
            title:
                _selectedMethod.isInstant
                    ? 'Instant flow'
                    : 'Manual transfer flow',
          ),
          const SizedBox(height: spacingMD),
          if (_selectedMethod.isInstant)
            _InstantFlowCard(method: _selectedMethod)
          else
            _ManualFlowCard(
              receiptAttached: _receiptAttached,
              onUploadReceipt:
                  () => setState(() => _receiptAttached = !_receiptAttached),
            ),
          const SizedBox(height: spacingLG),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: () {
                final double? amount = double.tryParse(
                  _amountController.text.trim(),
                );
                if (amount == null) {
                  return;
                }
                final DepositFlowRequest request = DepositFlowRequest(
                  method: _selectedMethod,
                  amountNaira: amount,
                  receiptAttached: _receiptAttached,
                );
                if (_selectedMethod.isInstant) {
                  widget.onSubmitInstant(request);
                } else {
                  widget.onSubmitManual(request);
                }
              },
              icon: Icon(
                _selectedMethod.isInstant
                    ? Icons.bolt_rounded
                    : Icons.account_balance_outlined,
              ),
              label: Text(
                _selectedMethod.isInstant
                    ? 'Process deposit'
                    : 'Submit manual transfer',
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class WithdrawalFlowSheet extends StatefulWidget {
  const WithdrawalFlowSheet({
    super.key,
    required this.state,
    required this.onSelectBank,
    required this.onSubmit,
  });

  final ExchangeHubState state;
  final ValueChanged<String> onSelectBank;
  final ValueChanged<double> onSubmit;

  @override
  State<WithdrawalFlowSheet> createState() => _WithdrawalFlowSheetState();
}

class _WithdrawalFlowSheetState extends State<WithdrawalFlowSheet> {
  final TextEditingController _amountController = TextEditingController(
    text: '5',
  );

  @override
  void dispose() {
    _amountController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final double amountGtex =
        double.tryParse(_amountController.text.trim()) ?? 0;
    final int payoutNaira = (amountGtex * widget.state.nairaPerGtex).round();
    return _SheetFrame(
      title: 'Withdrawal',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          TextField(
            controller: _amountController,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: const InputDecoration(
              labelText: 'Input GTex amount',
              suffixText: 'GTex',
            ),
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: spacingMD),
          Container(
            padding: const EdgeInsets.all(spacingMD),
            decoration: BoxDecoration(
              color: AppColors.primary.withValues(alpha: 0.10),
              borderRadius: BorderRadius.circular(cardRadius),
              border: Border.all(
                color: AppColors.primary.withValues(alpha: 0.24),
              ),
            ),
            child: Text(
              'You will receive ${AppFormatters.naira(payoutNaira)}',
              style: Theme.of(context).textTheme.titleLarge,
            ),
          ),
          const SizedBox(height: spacingLG),
          DropdownButtonFormField<String>(
            initialValue: widget.state.selectedBankId,
            items: widget.state.bankAccounts
                .map(
                  (WalletBankAccount account) => DropdownMenuItem<String>(
                    value: account.id,
                    child: Text(
                      '${account.bankName} • ${account.accountNumber}',
                    ),
                  ),
                )
                .toList(growable: false),
            onChanged: (String? value) {
              if (value == null) {
                return;
              }
              widget.onSelectBank(value);
            },
            decoration: const InputDecoration(labelText: 'Select bank account'),
          ),
          const SizedBox(height: spacingLG),
          Wrap(
            spacing: spacingSM,
            runSpacing: spacingSM,
            children: <Widget>[
              MetricPill(
                label: 'Tier',
                value: widget.state.kycTier.label,
                highlight: true,
              ),
              MetricPill(
                label: 'Limit',
                value: AppFormatters.naira(
                  widget.state.kycTier.dailyLimitNaira,
                ),
              ),
              MetricPill(
                label: 'Remaining',
                value: AppFormatters.naira(
                  widget.state.remainingWithdrawalLimitNaira,
                ),
              ),
            ],
          ),
          const SizedBox(height: spacingLG),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: () => widget.onSubmit(amountGtex),
              icon: const Icon(Icons.payments_outlined),
              label: const Text('Submit withdrawal'),
            ),
          ),
        ],
      ),
    );
  }
}

class ConvertFlowSheet extends StatefulWidget {
  const ConvertFlowSheet({
    super.key,
    required this.availableBalance,
    required this.onSubmit,
  });

  final double availableBalance;
  final ValueChanged<double> onSubmit;

  @override
  State<ConvertFlowSheet> createState() => _ConvertFlowSheetState();
}

class _ConvertFlowSheetState extends State<ConvertFlowSheet> {
  double _amount = 2;

  @override
  Widget build(BuildContext context) {
    final double maxAmount = math.max(1, widget.availableBalance);
    final double safeValue = _amount.clamp(1, maxAmount).toDouble();
    final int fanCoin = (safeValue * 100).round();
    return _SheetFrame(
      title: 'Convert GTex',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Move GTex into closed-loop Fan Coin for matchday experiences, gifting, and cosmetics.',
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(height: spacingLG),
          Slider(
            min: 1,
            max: maxAmount,
            divisions: math.max(1, (maxAmount * 2).round()),
            value: safeValue,
            onChanged: (double value) {
              setState(() {
                _amount = value;
              });
            },
          ),
          const SizedBox(height: spacingSM),
          Text(
            '${AppFormatters.gtex(safeValue)} → $fanCoin Fan Coin',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: spacingLG),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: () => widget.onSubmit(safeValue),
              icon: const Icon(Icons.sync_alt_rounded),
              label: const Text('Convert now'),
            ),
          ),
        ],
      ),
    );
  }
}

class PlayerTradeSheet extends StatefulWidget {
  const PlayerTradeSheet({
    super.key,
    required this.state,
    required this.player,
    required this.onBuy,
    required this.onSell,
  });

  final ExchangeHubState state;
  final PlayerShareListing player;
  final ValueChanged<int> onBuy;
  final ValueChanged<int> onSell;

  @override
  State<PlayerTradeSheet> createState() => _PlayerTradeSheetState();
}

class _PlayerTradeSheetState extends State<PlayerTradeSheet> {
  bool _selling = false;
  double _shares = 1;

  @override
  Widget build(BuildContext context) {
    final PlayerShareListing player = widget.player;
    final int maxBuy = math.min(
      player.sharesAvailable,
      widget.state.walletBalanceGtex ~/ player.priceGtex,
    );
    final int maxSell = player.userShares;
    final int maxShares = math.max(1, _selling ? maxSell : maxBuy);
    final int selectedShares = _shares.clamp(1, maxShares).round();
    final double orderValue = player.priceGtex * selectedShares;
    final bool canTrade = _selling ? maxSell > 0 : maxBuy > 0;

    return _SheetFrame(
      key: const Key('player-trade-sheet'),
      title: 'Player Detail',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              _InitialsAvatar(
                label: player.name,
                accent: AppColors.primary,
                size: 72,
              ),
              const SizedBox(width: spacingMD),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      player.name,
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: spacingXS),
                    Text(
                      '${player.club} • ${player.position} • ${player.country}',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: spacingSM),
                    Wrap(
                      spacing: spacingSM,
                      runSpacing: spacingSM,
                      children: <Widget>[
                        MetricPill(
                          label: 'Price',
                          value: AppFormatters.gtex(player.priceGtex),
                          highlight: true,
                        ),
                        MetricPill(
                          label: 'Trend',
                          value: AppFormatters.percent(player.trendPercent),
                        ),
                        MetricPill(
                          label: 'Owned',
                          value: '${player.userShares}',
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: spacingLG),
          SizedBox(
            height: 160,
            child: MiniPriceChart(
              points: player.chartPoints,
              color:
                  player.trendPercent >= 0 ? AppColors.primary : AppColors.gold,
            ),
          ),
          const SizedBox(height: spacingLG),
          Wrap(
            spacing: spacingSM,
            runSpacing: spacingSM,
            children: <Widget>[
              _InfoBadge(
                label: 'Shares available',
                value: '${player.sharesAvailable}',
                caption: 'Live float',
                color: AppColors.primary,
              ),
              _InfoBadge(
                label: 'Performance',
                value: player.performanceLabel,
                caption: 'Current form',
                color: AppColors.gold,
              ),
              _InfoBadge(
                label: 'Volume',
                value: AppFormatters.compact(player.volume),
                caption: '24h market depth',
                color: const Color(0xFF8FB3FF),
              ),
            ],
          ),
          const SizedBox(height: spacingLG),
          Text(
            'Performance stats',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: spacingMD),
          _MiniProgressLine(
            label: 'Price chart confidence',
            progress: player.confidenceScore,
            accent: AppColors.primary,
            valueLabel: '${(player.confidenceScore * 100).round()}',
          ),
          const SizedBox(height: spacingSM),
          _MiniProgressLine(
            label: 'Liquidity',
            progress: player.liquidityScore,
            accent: AppColors.gold,
            valueLabel: '${(player.liquidityScore * 100).round()}',
          ),
          const SizedBox(height: spacingSM),
          _MiniProgressLine(
            label: 'Recent performance',
            progress: player.performanceScore,
            accent: const Color(0xFF8FB3FF),
            valueLabel: '${(player.performanceScore * 100).round()}',
          ),
          const SizedBox(height: spacingLG),
          Wrap(
            spacing: spacingSM,
            runSpacing: spacingSM,
            children: <Widget>[
              ChoiceChip(
                label: const Text('Buy Shares'),
                selected: !_selling,
                onSelected: (_) => setState(() => _selling = false),
              ),
              ChoiceChip(
                label: const Text('Sell Shares'),
                selected: _selling,
                onSelected: (_) => setState(() => _selling = true),
              ),
            ],
          ),
          const SizedBox(height: spacingLG),
          Text(
            _selling ? 'Sell shares' : 'Buy shares',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: spacingSM),
          Slider(
            min: 1,
            max: maxShares.toDouble(),
            divisions: math.max(1, maxShares - 1),
            value: selectedShares.toDouble(),
            onChanged:
                canTrade
                    ? (double value) => setState(() => _shares = value)
                    : null,
          ),
          Text(
            '$selectedShares share${selectedShares == 1 ? '' : 's'} • ${AppFormatters.gtex(orderValue)}',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: spacingLG),
          if (!canTrade)
            Text(
              _selling
                  ? 'You do not own shares in this player yet.'
                  : 'Deposit more GTex before buying this player.',
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary),
            ),
          if (!canTrade) const SizedBox(height: spacingLG),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              key: Key(_selling ? 'trade-submit-sell' : 'trade-submit-buy'),
              onPressed:
                  canTrade
                      ? () {
                        if (_selling) {
                          widget.onSell(selectedShares);
                        } else {
                          widget.onBuy(selectedShares);
                        }
                      }
                      : null,
              icon: Icon(
                _selling
                    ? Icons.trending_down_rounded
                    : Icons.trending_up_rounded,
              ),
              label: Text(
                _selling
                    ? 'Sell $selectedShares share${selectedShares == 1 ? '' : 's'}'
                    : 'Buy $selectedShares share${selectedShares == 1 ? '' : 's'}',
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class DepositFlowRequest {
  const DepositFlowRequest({
    required this.method,
    required this.amountNaira,
    required this.receiptAttached,
  });

  final PaymentMethod method;
  final double amountNaira;
  final bool receiptAttached;
}

class _SheetFrame extends StatelessWidget {
  const _SheetFrame({super.key, required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
        border: Border.all(color: AppColors.divider),
      ),
      child: SafeArea(
        top: false,
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(
            spacingLG,
            spacingMD,
            spacingLG,
            spacingLG,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Center(
                child: Container(
                  width: 56,
                  height: 5,
                  decoration: BoxDecoration(
                    color: AppColors.divider,
                    borderRadius: BorderRadius.circular(999),
                  ),
                ),
              ),
              const SizedBox(height: spacingLG),
              Row(
                children: <Widget>[
                  Expanded(
                    child: Text(
                      title,
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                  ),
                  IconButton(
                    key: const Key('sheet-close'),
                    onPressed: () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.close_rounded),
                  ),
                ],
              ),
              const SizedBox(height: spacingLG),
              child,
            ],
          ),
        ),
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  const _ActionButton({
    required Key buttonKey,
    required this.icon,
    required this.label,
    required this.caption,
    required this.accent,
    required this.onTap,
  }) : _buttonKey = buttonKey;

  final Key _buttonKey;
  final IconData icon;
  final String label;
  final String caption;
  final Color accent;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return AppPressScale(
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          key: _buttonKey,
          onTap: onTap,
          borderRadius: BorderRadius.circular(cardRadius),
          child: Container(
            padding: const EdgeInsets.all(spacingMD),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.06),
              borderRadius: BorderRadius.circular(cardRadius),
              border: Border.all(color: accent.withValues(alpha: 0.26)),
            ),
            child: Row(
              children: <Widget>[
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: accent.withValues(alpha: 0.16),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Icon(icon, color: accent),
                ),
                const SizedBox(width: spacingMD),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        label,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: spacingXS),
                      Text(
                        caption,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: AppColors.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _ActivityTile extends StatelessWidget {
  const _ActivityTile({required this.entry});

  final WalletActivityEntry entry;

  @override
  Widget build(BuildContext context) {
    final Color accent = switch (entry.tone) {
      WalletActivityTone.positive => AppColors.primary,
      WalletActivityTone.negative => AppColors.gold,
      WalletActivityTone.neutral => const Color(0xFF8FB3FF),
      WalletActivityTone.pending => AppColors.textSecondary,
    };

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Container(
          width: 44,
          height: 44,
          decoration: BoxDecoration(
            color: accent.withValues(alpha: 0.14),
            borderRadius: BorderRadius.circular(14),
          ),
          child: Icon(switch (entry.tone) {
            WalletActivityTone.positive => Icons.arrow_downward_rounded,
            WalletActivityTone.negative => Icons.arrow_upward_rounded,
            WalletActivityTone.neutral => Icons.sync_alt_rounded,
            WalletActivityTone.pending => Icons.hourglass_bottom_rounded,
          }, color: accent),
        ),
        const SizedBox(width: spacingMD),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Expanded(
                    child: Text(
                      entry.title,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                  ),
                  Text(
                    entry.amountLabel,
                    style: Theme.of(
                      context,
                    ).textTheme.titleMedium?.copyWith(color: accent),
                  ),
                ],
              ),
              const SizedBox(height: spacingXS),
              Text(
                entry.subtitle,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: spacingSM),
              Wrap(
                spacing: spacingSM,
                runSpacing: spacingSM,
                children: <Widget>[
                  _PillLabel(label: entry.statusLabel, color: accent),
                  Text(
                    entry.timeLabel,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _InfoBadge extends StatelessWidget {
  const _InfoBadge({
    required this.label,
    required this.value,
    required this.caption,
    required this.color,
  });

  final String label;
  final String value;
  final String caption;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(spacingMD),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(cardRadius),
        border: Border.all(color: color.withValues(alpha: 0.24)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Text(
            label,
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(height: spacingXS),
          Text(value, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: spacingXS),
          Text(
            caption,
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
          ),
        ],
      ),
    );
  }
}

class _MiniRequirement extends StatelessWidget {
  const _MiniRequirement({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: spacingMD,
        vertical: spacingSM,
      ),
      decoration: BoxDecoration(
        color: AppColors.surfaceMuted,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: AppColors.divider),
      ),
      child: Text(label, style: Theme.of(context).textTheme.bodySmall),
    );
  }
}

class _BulletPoint extends StatelessWidget {
  const _BulletPoint({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: spacingSM),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(
            width: 8,
            height: 8,
            margin: const EdgeInsets.only(top: 6),
            decoration: const BoxDecoration(
              color: AppColors.gold,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: spacingSM),
          Expanded(
            child: Text(text, style: Theme.of(context).textTheme.bodyMedium),
          ),
        ],
      ),
    );
  }
}

class _ExpansionTile extends StatelessWidget {
  const _ExpansionTile({required this.territory, required this.note});

  final String territory;
  final String note;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(spacingMD),
      decoration: BoxDecoration(
        color: AppColors.surfaceMuted,
        borderRadius: BorderRadius.circular(cardRadius),
        border: Border.all(color: AppColors.divider),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          SizedBox(
            width: 54,
            child: Text(
              territory,
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ),
          const SizedBox(width: spacingMD),
          Expanded(
            child: Text(
              note,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary),
            ),
          ),
        ],
      ),
    );
  }
}

class _MiniProgressLine extends StatelessWidget {
  const _MiniProgressLine({
    required this.label,
    required this.progress,
    required this.accent,
    required this.valueLabel,
  });

  final String label;
  final double progress;
  final Color accent;
  final String valueLabel;

  @override
  Widget build(BuildContext context) {
    final double safeProgress = progress.clamp(0, 1).toDouble();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            Expanded(
              child: Text(label, style: Theme.of(context).textTheme.bodySmall),
            ),
            Text(
              valueLabel,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
            ),
          ],
        ),
        const SizedBox(height: spacingXS),
        ClipRRect(
          borderRadius: BorderRadius.circular(999),
          child: LinearProgressIndicator(
            value: safeProgress,
            minHeight: 9,
            backgroundColor: AppColors.surfaceMuted,
            valueColor: AlwaysStoppedAnimation<Color>(accent),
          ),
        ),
      ],
    );
  }
}

class _TrendBadge extends StatelessWidget {
  const _TrendBadge({required this.trendPercent});

  final double trendPercent;

  @override
  Widget build(BuildContext context) {
    final bool positive = trendPercent >= 0;
    final Color accent = positive ? AppColors.primary : AppColors.gold;
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: spacingSM,
        vertical: spacingXS,
      ),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: accent.withValues(alpha: 0.28)),
      ),
      child: Text(
        '${positive ? '↑' : '↓'} ${AppFormatters.percent(trendPercent)}',
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
          color: accent,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _TreasuryLine extends StatelessWidget {
  const _TreasuryLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: spacingSM),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          SizedBox(
            width: 110,
            child: Text(
              label,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
            ),
          ),
          Expanded(
            child: Text(value, style: Theme.of(context).textTheme.bodyMedium),
          ),
        ],
      ),
    );
  }
}

class _BalanceStat extends StatelessWidget {
  const _BalanceStat({
    required this.label,
    required this.value,
    required this.accent,
  });

  final String label;
  final String value;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          label.toUpperCase(),
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: AppColors.textSecondary,
            fontWeight: FontWeight.w700,
            letterSpacing: 1.0,
          ),
        ),
        const SizedBox(height: spacingXS),
        Text(
          value,
          style: Theme.of(
            context,
          ).textTheme.titleLarge?.copyWith(color: accent),
        ),
      ],
    );
  }
}

class _PillLabel extends StatelessWidget {
  const _PillLabel({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: spacingSM,
        vertical: spacingXS,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.16),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.32)),
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

class _InitialsAvatar extends StatelessWidget {
  const _InitialsAvatar({
    required this.label,
    required this.accent,
    this.size = 56,
  });

  final String label;
  final Color accent;
  final double size;

  @override
  Widget build(BuildContext context) {
    final String initials =
        label
            .split(' ')
            .where((String part) => part.isNotEmpty)
            .take(2)
            .map((String part) => part[0].toUpperCase())
            .join();
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            accent.withValues(alpha: 0.24),
            AppColors.surfaceMuted,
          ],
        ),
        border: Border.all(color: accent.withValues(alpha: 0.32)),
      ),
      alignment: Alignment.center,
      child: Text(
        initials,
        style: Theme.of(
          context,
        ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
      ),
    );
  }
}

class _MethodTile extends StatelessWidget {
  const _MethodTile({
    required this.method,
    required this.selected,
    required this.onTap,
  });

  final PaymentMethod method;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(cardRadius),
      child: Container(
        padding: const EdgeInsets.all(spacingMD),
        decoration: BoxDecoration(
          color:
              selected
                  ? AppColors.primary.withValues(alpha: 0.10)
                  : AppColors.surfaceMuted,
          borderRadius: BorderRadius.circular(cardRadius),
          border: Border.all(
            color: selected ? AppColors.primary : AppColors.divider,
          ),
        ),
        child: Row(
          children: <Widget>[
            Icon(
              method.isInstant
                  ? Icons.flash_on_rounded
                  : Icons.account_balance_outlined,
              color: selected ? AppColors.primary : AppColors.textSecondary,
            ),
            const SizedBox(width: spacingMD),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    method.label,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: spacingXS),
                  Text(
                    method.subtitle,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _InstantFlowCard extends StatelessWidget {
  const _InstantFlowCard({required this.method});

  final PaymentMethod method;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(spacingMD),
      decoration: BoxDecoration(
        color: AppColors.primary.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(cardRadius),
        border: Border.all(color: AppColors.primary.withValues(alpha: 0.24)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Redirect to ${method.label}',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: spacingSM),
          Text(
            'Show “Processing…” while the gateway confirms settlement and pushes GTex back into the wallet.',
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary),
          ),
        ],
      ),
    );
  }
}

class _ManualFlowCard extends StatelessWidget {
  const _ManualFlowCard({
    required this.receiptAttached,
    required this.onUploadReceipt,
  });

  final bool receiptAttached;
  final VoidCallback onUploadReceipt;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(spacingMD),
      decoration: BoxDecoration(
        color: AppColors.gold.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(cardRadius),
        border: Border.all(color: AppColors.gold.withValues(alpha: 0.22)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Bank details', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: spacingSM),
          const _TreasuryLine(label: 'Account name', value: 'GTEX LTD'),
          const _TreasuryLine(label: 'Account number', value: '0123456789'),
          const _TreasuryLine(label: 'Status', value: 'Manual treasury review'),
          const SizedBox(height: spacingMD),
          OutlinedButton.icon(
            onPressed: onUploadReceipt,
            icon: const Icon(Icons.upload_file_rounded),
            label: Text(
              receiptAttached ? 'Receipt attached' : 'Upload receipt',
            ),
          ),
        ],
      ),
    );
  }
}

class _SheetStepLabel extends StatelessWidget {
  const _SheetStepLabel({required this.index, required this.title});

  final int index;
  final String title;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: <Widget>[
        CircleAvatar(
          radius: 14,
          backgroundColor: AppColors.primary.withValues(alpha: 0.16),
          child: Text(
            '$index',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: AppColors.primary,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        const SizedBox(width: spacingSM),
        Text(title, style: Theme.of(context).textTheme.titleMedium),
      ],
    );
  }
}

class _JerseyBackdrop extends StatelessWidget {
  const _JerseyBackdrop();

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: <Widget>[
        Positioned(
          left: -30,
          top: -10,
          child: Transform.rotate(
            angle: -0.35,
            child: Container(
              width: 110,
              height: 420,
              color: Colors.white.withValues(alpha: 0.05),
            ),
          ),
        ),
        Positioned(
          left: 120,
          top: -20,
          child: Transform.rotate(
            angle: -0.35,
            child: Container(
              width: 54,
              height: 420,
              color: Colors.white.withValues(alpha: 0.04),
            ),
          ),
        ),
        Positioned.fill(child: CustomPaint(painter: _PitchOverlayPainter())),
      ],
    );
  }
}

class _MiniPriceChartPainter extends CustomPainter {
  _MiniPriceChartPainter({required this.points, required this.color});

  final List<double> points;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    if (points.length < 2) {
      return;
    }

    final double minPoint = points.reduce(math.min);
    final double maxPoint = points.reduce(math.max);
    final double spread = math.max(0.1, maxPoint - minPoint);
    final Path path = Path();

    for (int index = 0; index < points.length; index++) {
      final double dx = size.width * (index / (points.length - 1));
      final double normalized = (points[index] - minPoint) / spread;
      final double dy = size.height - (normalized * size.height);
      if (index == 0) {
        path.moveTo(dx, dy);
      } else {
        path.lineTo(dx, dy);
      }
    }

    final Path fillPath =
        Path.from(path)
          ..lineTo(size.width, size.height)
          ..lineTo(0, size.height)
          ..close();

    canvas.drawPath(
      fillPath,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: <Color>[
            color.withValues(alpha: 0.20),
            color.withValues(alpha: 0.02),
          ],
        ).createShader(Offset.zero & size),
    );
    canvas.drawPath(
      path,
      Paint()
        ..color = color
        ..style = PaintingStyle.stroke
        ..strokeWidth = 3
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round,
    );
  }

  @override
  bool shouldRepaint(covariant _MiniPriceChartPainter oldDelegate) {
    return oldDelegate.points != points || oldDelegate.color != color;
  }
}

class _PitchOverlayPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final Paint paint =
        Paint()
          ..color = Colors.white.withValues(alpha: 0.06)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.5;

    canvas.drawRect(
      Rect.fromLTWH(24, 20, size.width - 48, size.height - 40),
      paint,
    );
    canvas.drawLine(
      Offset(size.width / 2, 20),
      Offset(size.width / 2, size.height - 20),
      paint,
    );
    canvas.drawCircle(Offset(size.width / 2, size.height / 2), 44, paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) {
    return false;
  }
}
