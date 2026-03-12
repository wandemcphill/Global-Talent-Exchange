import 'package:flutter/material.dart';
import 'package:gte_frontend/models/club_finance_models.dart';
import 'package:gte_frontend/widgets/clubs/club_ops_formatters.dart';
import 'package:gte_frontend/widgets/clubs/club_ops_scaffold.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class FinanceSummaryCard extends StatelessWidget {
  const FinanceSummaryCard({
    super.key,
    required this.finance,
  });

  final ClubFinanceSnapshot finance;

  @override
  Widget build(BuildContext context) {
    final ClubBalanceSummary summary = finance.balanceSummary;
    final bool positiveNet = summary.netMonthlyMovement >= 0;
    return GteSurfacePanel(
      emphasized: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            finance.clubName,
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 8),
          Text(
            'Club finances are shown as operating cash, planned budget allocation, and transparent ledger movement.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 18),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              _HighlightMetric(
                label: 'Current balance',
                value: clubOpsFormatCurrency(summary.currentBalance),
                detail: 'Reserve target ${clubOpsFormatCurrency(summary.reserveTarget)}',
              ),
              _HighlightMetric(
                label: 'Operating budget',
                value: clubOpsFormatCurrency(summary.operatingBudget),
                detail: 'Runway ${summary.cashRunwayMonths.toStringAsFixed(1)} months',
              ),
              _HighlightMetric(
                label: 'Net monthly movement',
                value: clubOpsFormatSignedCurrency(summary.netMonthlyMovement),
                detail: '${clubOpsFormatPercent(summary.balanceDeltaPercent)} vs last month',
                positive: positiveNet,
              ),
            ],
          ),
          const SizedBox(height: 18),
          ClubOpsMetricRow(
            label: 'Monthly income',
            value: clubOpsFormatCurrency(summary.monthlyIncome),
            valueColor: GteShellTheme.positive,
          ),
          ClubOpsMetricRow(
            label: 'Monthly expenses',
            value: clubOpsFormatCurrency(summary.monthlyExpenses),
            valueColor: GteShellTheme.negative,
          ),
          ClubOpsMetricRow(
            label: 'Payroll commitment',
            value: clubOpsFormatCurrency(summary.payrollCommitment),
          ),
          ClubOpsMetricRow(
            label: 'Next payroll',
            value:
                '${clubOpsFormatCurrency(summary.nextPayrollAmount)} on ${clubOpsFormatDate(summary.nextPayrollDate)}',
          ),
        ],
      ),
    );
  }
}

class _HighlightMetric extends StatelessWidget {
  const _HighlightMetric({
    required this.label,
    required this.value,
    required this.detail,
    this.positive = true,
  });

  final String label;
  final String value;
  final String detail;
  final bool positive;

  @override
  Widget build(BuildContext context) {
    final Color accent =
        positive ? GteShellTheme.positive : GteShellTheme.accentWarm;
    return SizedBox(
      width: 220,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(22),
          border: Border.all(color: GteShellTheme.stroke),
          color: Colors.black.withValues(alpha: 0.14),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(label, style: Theme.of(context).textTheme.bodyMedium),
            const SizedBox(height: 8),
            Text(
              value,
              style: Theme.of(context)
                  .textTheme
                  .titleLarge
                  ?.copyWith(color: accent),
            ),
            const SizedBox(height: 6),
            Text(detail, style: Theme.of(context).textTheme.bodyMedium),
          ],
        ),
      ),
    );
  }
}
