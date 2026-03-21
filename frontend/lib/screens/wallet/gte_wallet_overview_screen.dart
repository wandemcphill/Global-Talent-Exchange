import 'package:flutter/material.dart';

import '../../data/gte_models.dart';
import '../../providers/gte_exchange_controller.dart';
import '../../widgets/gte_formatters.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';
import 'gte_policy_compliance_center_screen.dart';

class GteWalletOverviewScreen extends StatefulWidget {
  const GteWalletOverviewScreen({
    super.key,
    required this.controller,
  });

  final GteExchangeController controller;

  @override
  State<GteWalletOverviewScreen> createState() =>
      _GteWalletOverviewScreenState();
}

class _GteWalletOverviewScreenState extends State<GteWalletOverviewScreen> {
  late Future<GteWalletOverview> _overviewFuture;
  late Future<GteWithdrawalEligibility> _eligibilityFuture;
  late Future<GteWalletLedgerPage> _ledgerFuture;

  @override
  void initState() {
    super.initState();
    _overviewFuture = widget.controller.api.fetchWalletOverview();
    _eligibilityFuture = widget.controller.api.fetchWithdrawalEligibility();
    _ledgerFuture =
        widget.controller.api.fetchWalletLedger(page: 1, pageSize: 12);
  }

  Future<void> _refresh() async {
    setState(() {
      _overviewFuture = widget.controller.api.fetchWalletOverview();
      _eligibilityFuture = widget.controller.api.fetchWithdrawalEligibility();
      _ledgerFuture =
          widget.controller.api.fetchWalletLedger(page: 1, pageSize: 12);
    });
  }

  double _fanCoinBalance(List<GteWalletLedgerEntry> entries) {
    double total = 0;
    for (final GteWalletLedgerEntry entry in entries) {
      final String reason = entry.reason.toLowerCase();
      if (reason.contains('reward') ||
          reason.contains('promo') ||
          reason.contains('gift') ||
          reason.contains('fan')) {
        total += entry.amount;
      }
    }
    return total;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Club Wallet'),
        actions: <Widget>[
          IconButton(onPressed: _refresh, icon: const Icon(Icons.refresh)),
        ],
      ),
      body: FutureBuilder<GteWalletOverview>(
        future: _overviewFuture,
        builder:
            (BuildContext context, AsyncSnapshot<GteWalletOverview> snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (!snapshot.hasData) {
            return const Center(
              child: GteStatePanel(
                title: 'Wallet unavailable',
                message: 'Unable to load the wallet overview right now.',
                icon: Icons.account_balance_wallet_outlined,
              ),
            );
          }
          final GteWalletOverview overview = snapshot.data!;
          final int pendingPolicyItems =
              overview.requiredPolicyAcceptancesMissing;
          final String complianceActionLabel = pendingPolicyItems > 0
              ? 'Review $pendingPolicyItems pending item(s)'
              : 'Open compliance center';
          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: <Widget>[
                FutureBuilder<GteWalletLedgerPage>(
                  future: _ledgerFuture,
                  builder: (BuildContext context,
                      AsyncSnapshot<GteWalletLedgerPage> ledgerSnapshot) {
                    final double? fanCoinBalance = ledgerSnapshot.hasData
                        ? _fanCoinBalance(ledgerSnapshot.data!.items)
                        : null;
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: <Widget>[
                        GteSurfacePanel(
                          accentColor: GteShellTheme.accentCapital,
                          emphasized: true,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Wrap(
                                spacing: 10,
                                runSpacing: 10,
                                children: const <Widget>[
                                  _WalletTag(
                                    label: 'Club wallet',
                                    color: GteShellTheme.accentCapital,
                                  ),
                                  _WalletTag(
                                    label: 'Rewards lane',
                                    color: GteShellTheme.accentCommunity,
                                  ),
                                ],
                              ),
                              const SizedBox(height: 14),
                               Text('Club wallet',
                                   style: Theme.of(context)
                                       .textTheme
                                       .headlineSmall),
                              const SizedBox(height: 8),
                               Text(
                                 'FanCoin rewards stay separate from your tradable balance.',
                                 style: Theme.of(context).textTheme.bodyMedium,
                               ),
                              const SizedBox(height: 14),
                              Row(
                                children: <Widget>[
                                  _BalanceTile(
                                    label: 'FanCoin',
                                    value: fanCoinBalance == null
                                        ? 'Syncing...'
                                        : gteFormatCredits(fanCoinBalance),
                                    caption:
                                        'Rewards, boosts, and gifting credits.',
                                    accent: GteShellTheme.accentCommunity,
                                  ),
                                  const SizedBox(width: 12),
                                  _BalanceTile(
                                    label: 'Coin / Market Balance',
                                    value: gteFormatCredits(
                                        overview.availableBalance),
                                    caption:
                                        'Balance ready for market and competitions.',
                                    accent: GteShellTheme.accentCapital,
                                  ),
                                ],
                              ),
                              const SizedBox(height: 16),
                              Row(
                                children: <Widget>[
                                  _MetricTile(
                                    label: 'Pending deposits',
                                    value: gteFormatCredits(
                                        overview.pendingDeposits),
                                  ),
                                  const SizedBox(width: 12),
                                  _MetricTile(
                                    label: 'Pending withdrawals',
                                    value: gteFormatCredits(
                                        overview.pendingWithdrawals),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 16),
                        if (overview.policyBlocked ||
                            overview.requiredPolicyAcceptancesMissing > 0)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 18),
                            child: GteSurfacePanel(
                              accentColor: Colors.orange,
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: <Widget>[
                                  Text('Compliance action needed',
                                      style: Theme.of(context)
                                          .textTheme
                                          .titleMedium),
                                  const SizedBox(height: 8),
                                  Text(
                                    overview.policyBlockReason ??
                                        'Complete required policy acceptances to unlock all wallet actions.',
                                  ),
                                  const SizedBox(height: 12),
                                  FilledButton.icon(
                                    onPressed: () async {
                                      await Navigator.of(context).push(
                                        MaterialPageRoute<void>(
                                          builder: (_) =>
                                              GtePolicyComplianceCenterScreen(
                                            controller: widget.controller,
                                          ),
                                        ),
                                      );
                                      await _refresh();
                                    },
                                    icon: const Icon(Icons.gavel_outlined),
                                    label: Text(complianceActionLabel),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        Text(
                          'Money moves',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Every wallet event stays readable by source so rewards, top-ups, and transfers do not blur together.',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                        const SizedBox(height: 12),
                        if (ledgerSnapshot.connectionState ==
                                ConnectionState.waiting &&
                            !ledgerSnapshot.hasData)
                          const GteSurfacePanel(
                            child: Text('Loading wallet history...'),
                          )
                        else if (!ledgerSnapshot.hasData)
                          const GteStatePanel(
                            title: 'Wallet history unavailable',
                            message:
                                'Unable to load source-tagged history right now.',
                            icon: Icons.receipt_long_outlined,
                          )
                        else
                          ...ledgerSnapshot.data!.items
                              .map((GteWalletLedgerEntry entry) {
                            return _LedgerEntryTile(entry: entry);
                          }),
                      ],
                    );
                  },
                ),
                const SizedBox(height: 18),
                GteSurfacePanel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text('Money in / out',
                          style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 12),
                      Row(
                        children: <Widget>[
                          _MetricTile(
                            label: 'Money in',
                            value: gteFormatCredits(overview.totalInflow),
                          ),
                          const SizedBox(width: 12),
                          _MetricTile(
                            label: 'Money out',
                            value: gteFormatCredits(overview.totalOutflow),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                FutureBuilder<GteWithdrawalEligibility>(
                  future: _eligibilityFuture,
                  builder: (BuildContext context,
                      AsyncSnapshot<GteWithdrawalEligibility> eligibilitySnap) {
                    if (!eligibilitySnap.hasData) {
                      return const GteSurfacePanel(
                        child: Text('Loading withdrawal eligibility...'),
                      );
                    }
                    final GteWithdrawalEligibility eligibility =
                        eligibilitySnap.data!;
                    final bool rewardsRestricted = eligibility.policyBlocked ||
                        !eligibility.countryWithdrawalsEnabled ||
                        eligibility.requiresKyc ||
                        eligibility.requiresBankAccount;
                    return GteSurfacePanel(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text('Withdrawal eligibility',
                              style: Theme.of(context).textTheme.titleMedium),
                          const SizedBox(height: 12),
                          Row(
                            children: <Widget>[
                              _MetricTile(
                                label: 'Withdrawable now',
                                value: gteFormatCredits(
                                    eligibility.withdrawableNow),
                              ),
                              const SizedBox(width: 12),
                              _MetricTile(
                                label: 'Remaining allowance',
                                value: gteFormatCredits(
                                    eligibility.remainingAllowance),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          Text(
                            eligibility.nextEligibleAt == null
                                ? 'No throttling window in effect.'
                                : 'Next eligibility: ${gteFormatDateTime(eligibility.nextEligibleAt)}',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                          if (rewardsRestricted) ...<Widget>[
                            const SizedBox(height: 12),
                            Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(14),
                                color: Colors.orange.withValues(alpha: 0.08),
                                border: Border.all(
                                  color: Colors.orange.withValues(alpha: 0.2),
                                ),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: <Widget>[
                                  Text('Restricted rewards',
                                      style: Theme.of(context)
                                          .textTheme
                                          .titleSmall),
                                  const SizedBox(height: 6),
                                  Text(
                                    eligibility.policyBlockReason ??
                                        'Rewards and withdrawals can be restricted by policy, KYC, or regional controls.',
                                    style:
                                        Theme.of(context).textTheme.bodySmall,
                                  ),
                                  if (!eligibility
                                      .countryWithdrawalsEnabled) ...<Widget>[
                                    const SizedBox(height: 6),
                                    Text(
                                      'Region status: withdrawals are disabled for this country.',
                                      style:
                                          Theme.of(context).textTheme.bodySmall,
                                    ),
                                  ],
                                  if (eligibility.requiresKyc) ...<Widget>[
                                    const SizedBox(height: 6),
                                    Text(
                                      'KYC is required before withdrawals unlock.',
                                      style:
                                          Theme.of(context).textTheme.bodySmall,
                                    ),
                                  ],
                                  if (eligibility
                                      .requiresBankAccount) ...<Widget>[
                                    const SizedBox(height: 6),
                                    Text(
                                      'Verified bank details are required.',
                                      style:
                                          Theme.of(context).textTheme.bodySmall,
                                    ),
                                  ],
                                ],
                              ),
                            ),
                          ],
                          if (eligibility.policyBlocked) ...<Widget>[
                            const SizedBox(height: 12),
                            Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(14),
                                color: Colors.orange.withValues(alpha: 0.08),
                                border: Border.all(
                                  color: Colors.orange.withValues(alpha: 0.2),
                                ),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: <Widget>[
                                  Text(
                                    eligibility.policyBlockReason ??
                                        'Withdrawal is currently blocked by policy requirements.',
                                  ),
                                  if (eligibility.missingRequiredPolicies
                                      .isNotEmpty) ...<Widget>[
                                    const SizedBox(height: 8),
                                    Text(
                                      'Pending: ${eligibility.missingRequiredPolicies.join(', ')}',
                                      style:
                                          Theme.of(context).textTheme.bodySmall,
                                    ),
                                  ],
                                ],
                              ),
                            ),
                          ],
                        ],
                      ),
                    );
                  },
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _WalletTag extends StatelessWidget {
  const _WalletTag({
    required this.label,
    required this.color,
  });

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: color.withValues(alpha: 0.14),
        border: Border.all(color: color.withValues(alpha: 0.24)),
      ),
      child: Text(
        label.toUpperCase(),
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: color,
              fontWeight: FontWeight.w800,
              letterSpacing: 1,
            ),
      ),
    );
  }
}

class _MetricTile extends StatelessWidget {
  const _MetricTile({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          color: GteShellTheme.panelStrong.withValues(alpha: 0.6),
          border: Border.all(
              color: GteShellTheme.accentCapital.withValues(alpha: 0.12)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              label.toUpperCase(),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    letterSpacing: 0.9,
                    fontWeight: FontWeight.w700,
                  ),
            ),
            const SizedBox(height: 8),
            Text(value, style: Theme.of(context).textTheme.titleMedium),
          ],
        ),
      ),
    );
  }
}

class _BalanceTile extends StatelessWidget {
  const _BalanceTile({
    required this.label,
    required this.value,
    required this.caption,
    required this.accent,
  });

  final String label;
  final String value;
  final String caption;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          color: accent.withValues(alpha: 0.08),
          border: Border.all(color: accent.withValues(alpha: 0.2)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              label.toUpperCase(),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    letterSpacing: 0.9,
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: 8),
            Text(
              value,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              caption,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }
}

class _LedgerEntryTile extends StatelessWidget {
  const _LedgerEntryTile({required this.entry});

  final GteWalletLedgerEntry entry;

  @override
  Widget build(BuildContext context) {
    final String label = _sourceLabel(entry.reason);
    final IconData icon = _sourceIcon(entry.reason);
    final bool isPositive = entry.amount >= 0;
    final Color accent =
        isPositive ? GteShellTheme.positive : GteShellTheme.accentWarm;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: GteSurfacePanel(
        accentColor: accent,
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(14),
                color: accent.withValues(alpha: 0.14),
              ),
              child: Icon(icon, color: accent),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 6,
                    ),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(999),
                      color: accent.withValues(alpha: 0.14),
                    ),
                    child: Text(
                      label.toUpperCase(),
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: accent,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 1,
                          ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  if (entry.description?.trim().isNotEmpty == true) ...<Widget>[
                    Text(
                      entry.description!,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                    const SizedBox(height: 4),
                  ],
                  Text(
                    'Source: ${entry.reason}',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            Text(
              gteFormatCredits(entry.amount),
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    color: isPositive
                        ? GteShellTheme.positive
                        : GteShellTheme.negative,
                  ),
            ),
          ],
        ),
      ),
    );
  }

  String _sourceLabel(String reason) {
    final String value = reason.toLowerCase();
    if (value.contains('trade')) {
      return 'Market trade';
    }
    if (value.contains('withdrawal')) {
      return 'Withdrawal activity';
    }
    if (value.contains('deposit')) {
      return 'Deposit activity';
    }
    if (value.contains('reward') || value.contains('promo')) {
      return 'Promo reward';
    }
    if (value.contains('gift')) {
      return 'Fan support';
    }
    if (value.contains('adjust')) {
      return 'Adjustment';
    }
    return 'Wallet event';
  }

  IconData _sourceIcon(String reason) {
    final String value = reason.toLowerCase();
    if (value.contains('trade')) {
      return Icons.candlestick_chart_outlined;
    }
    if (value.contains('withdrawal')) {
      return Icons.south_west_outlined;
    }
    if (value.contains('deposit')) {
      return Icons.north_east_outlined;
    }
    if (value.contains('reward') || value.contains('promo')) {
      return Icons.emoji_events_outlined;
    }
    if (value.contains('gift')) {
      return Icons.card_giftcard_outlined;
    }
    return Icons.receipt_long_outlined;
  }
}
