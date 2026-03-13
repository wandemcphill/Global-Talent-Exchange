import 'package:flutter/material.dart';

import '../data/gte_models.dart';
import 'gte_formatters.dart';
import 'gte_metric_chip.dart';
import 'gte_shell_theme.dart';
import 'gte_surface_panel.dart';

class GteWalletSummaryCard extends StatelessWidget {
  const GteWalletSummaryCard({
    super.key,
    required this.summary,
  });

  final GteWalletSummary summary;

  @override
  Widget build(BuildContext context) {
    final double utilization = summary.totalBalance <= 0
        ? 0
        : (summary.reservedBalance / summary.totalBalance).clamp(0, 1);
    final double freeRatio = summary.totalBalance <= 0
        ? 0
        : (summary.availableBalance / summary.totalBalance).clamp(0, 1);

    return GteSurfacePanel(
      emphasized: true,
      accentColor: GteShellTheme.accentCapital,
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
                    Text('Wallet summary', style: Theme.of(context).textTheme.headlineSmall),
                    const SizedBox(height: 8),
                    Text(
                      'Capital state for funding, reserves, and execution readiness.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(16),
                  color: GteShellTheme.accentCapital.withValues(alpha: 0.12),
                  border: Border.all(color: GteShellTheme.accentCapital.withValues(alpha: 0.2)),
                ),
                child: Text(
                  summary.currency.name.toUpperCase(),
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(color: GteShellTheme.accentCapital),
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(24),
              gradient: LinearGradient(
                colors: <Color>[
                  GteShellTheme.accentCapital.withValues(alpha: 0.18),
                  Colors.white.withValues(alpha: 0.03),
                ],
              ),
              border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('Available to deploy', style: Theme.of(context).textTheme.bodyMedium),
                const SizedBox(height: 6),
                Text(
                  gteFormatCredits(summary.availableBalance),
                  style: Theme.of(context).textTheme.displaySmall?.copyWith(fontSize: 30),
                ),
                const SizedBox(height: 14),
                ClipRRect(
                  borderRadius: BorderRadius.circular(999),
                  child: LinearProgressIndicator(
                    value: freeRatio,
                    minHeight: 10,
                    backgroundColor: Colors.white.withValues(alpha: 0.06),
                    valueColor: AlwaysStoppedAnimation<Color>(GteShellTheme.accentCapital),
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  utilization <= 0
                      ? 'No cash is currently reserved by open orders.'
                      : '${(utilization * 100).toStringAsFixed(0)}% of total funds are reserved by working orders.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              GteMetricChip(
                label: 'Reserved',
                value: gteFormatCredits(summary.reservedBalance),
                positive: summary.reservedBalance <= summary.totalBalance,
              ),
              GteMetricChip(
                label: 'Total balance',
                value: gteFormatCredits(summary.totalBalance),
              ),
              GteMetricChip(
                label: 'Funding state',
                value: summary.availableBalance > 0 ? 'READY' : 'LOW CASH',
                positive: summary.availableBalance > 0,
              ),
            ],
          ),
        ],
      ),
    );
  }
}
