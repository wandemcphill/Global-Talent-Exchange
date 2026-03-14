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

  @override
  void initState() {
    super.initState();
    _overviewFuture = widget.controller.api.fetchWalletOverview();
    _eligibilityFuture = widget.controller.api.fetchWithdrawalEligibility();
  }

  Future<void> _refresh() async {
    setState(() {
      _overviewFuture = widget.controller.api.fetchWalletOverview();
      _eligibilityFuture = widget.controller.api.fetchWithdrawalEligibility();
    });
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
        builder: (BuildContext context, AsyncSnapshot<GteWalletOverview> snapshot) {
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
          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: <Widget>[
                GteSurfacePanel(
                  accentColor: GteShellTheme.accentCapital,
                  emphasized: true,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text('Available balance',
                          style: Theme.of(context).textTheme.titleLarge),
                      const SizedBox(height: 8),
                      Text(
                        gteFormatCredits(overview.availableBalance),
                        style: Theme.of(context)
                            .textTheme
                            .displaySmall
                            ?.copyWith(fontSize: 30),
                      ),
                      const SizedBox(height: 16),
                      Row(
                        children: <Widget>[
                          _MetricTile(
                            label: 'Pending deposits',
                            value: gteFormatCredits(overview.pendingDeposits),
                          ),
                          const SizedBox(width: 12),
                          _MetricTile(
                            label: 'Pending withdrawals',
                            value: gteFormatCredits(overview.pendingWithdrawals),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
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
                              style: Theme.of(context).textTheme.titleMedium),
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
                                  builder: (_) => GtePolicyComplianceCenterScreen(
                                    controller: widget.controller,
                                  ),
                                ),
                              );
                              await _refresh();
                            },
                            icon: const Icon(Icons.gavel_outlined),
                            label: Text(
                              'Review ${overview.requiredPolicyAcceptancesMissing} pending item(s)',
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
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
                                  if (eligibility.missingRequiredPolicies.isNotEmpty) ...<Widget>[
                                    const SizedBox(height: 8),
                                    Text(
                                      'Pending: ${eligibility.missingRequiredPolicies.join(', ')}',
                                      style: Theme.of(context).textTheme.bodySmall,
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
