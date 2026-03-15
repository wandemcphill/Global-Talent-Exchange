import 'package:flutter/material.dart';

import '../../models/creator_models.dart';
import '../gte_formatters.dart';
import '../gte_shell_theme.dart';
import '../gte_surface_panel.dart';

class CreatorFinanceSummaryCard extends StatelessWidget {
  const CreatorFinanceSummaryCard({
    super.key,
    required this.summary,
    this.accentColor = const Color(0xFF9C6BFF),
  });

  final CreatorFinanceSummary summary;
  final Color accentColor;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      accentColor: accentColor,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'CREATOR FINANCE SUMMARY',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              _FinanceMetric(
                label: 'Gift income',
                value: gteFormatFiat(
                  summary.totalGiftIncome,
                  currency: summary.currency,
                ),
              ),
              _FinanceMetric(
                label: 'Reward income',
                value: gteFormatFiat(
                  summary.totalRewardIncome,
                  currency: summary.currency,
                ),
              ),
              _FinanceMetric(
                label: 'Withdrawn net',
                value: gteFormatFiat(
                  summary.totalWithdrawnNet,
                  currency: summary.currency,
                ),
              ),
              _FinanceMetric(
                label: 'Fees',
                value: gteFormatFiat(
                  summary.totalWithdrawalFees,
                  currency: summary.currency,
                ),
              ),
              _FinanceMetric(
                label: 'Pending',
                value: gteFormatFiat(
                  summary.pendingWithdrawals,
                  currency: summary.currency,
                ),
              ),
              _FinanceMetric(
                label: 'Active comps',
                value: summary.activeCompetitions.toString(),
              ),
              _FinanceMetric(
                label: 'Attributed signups',
                value: summary.attributedSignups.toString(),
              ),
              _FinanceMetric(
                label: 'Qualified joins',
                value: summary.qualifiedJoins.toString(),
              ),
            ],
          ),
          if (summary.insights.isNotEmpty) ...<Widget>[
            const SizedBox(height: 12),
            Text(
              'Insights',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 6),
            for (final String insight in summary.insights)
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Text(
                  '• $insight',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ),
          ],
        ],
      ),
    );
  }
}

class _FinanceMetric extends StatelessWidget {
  const _FinanceMetric({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        color: Colors.white.withValues(alpha: 0.04),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: GteShellTheme.accent.withValues(alpha: 0.08),
            blurRadius: 16,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Text(label, style: Theme.of(context).textTheme.labelMedium),
          const SizedBox(height: 4),
          Text(value, style: Theme.of(context).textTheme.titleMedium),
        ],
      ),
    );
  }
}
