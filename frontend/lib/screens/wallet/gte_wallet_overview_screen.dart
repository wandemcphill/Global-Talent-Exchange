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
        title: const Text('Wallet overview'),
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
                              Text('Wallet hub',
                                  style:
                                      Theme.of(context).textTheme.titleLarge),
                              const SizedBox(height: 8),
                              Text(
                                'FanCoin rewards and Coin/Market Balance stay separated for clarity.',
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
                                        'Promo pool rewards and gifting credits.',
                                    accent: GteShellTheme.accentCommunity,
                                  ),
                                  const SizedBox(width: 12),
                                  _BalanceTile(
                                    label: 'Coin / Market Balance',
                                    value: gteFormatCredits(
                                        overview.availableBalance),
                                    caption:
                                        'Tradeable balance for market and competitions.',
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
                          'Source-tagged history',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 8),
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
                      Text('Wallet flow totals',
                          style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 12),
                      Row(
                        children: <Widget>[
                          _MetricTile(
                            label: 'Total inflow',
                            value: gteFormatCredits(overview.totalInflow),
                          ),
                          const SizedBox(width: 12),
                          _MetricTile(
                            label: 'Total outflow',
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
          color: Colors.white.withValues(alpha: 0.03),
          border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(label, style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: 6),
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
            Text(label, style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: 6),
            Text(value, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 6),
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
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: GteSurfacePanel(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Icon(icon),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(label, style: Theme.of(context).textTheme.titleSmall),
                  if (entry.description?.trim().isNotEmpty == true) ...<Widget>[
                    const SizedBox(height: 4),
                    Text(
                      entry.description!,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                  const SizedBox(height: 4),
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
