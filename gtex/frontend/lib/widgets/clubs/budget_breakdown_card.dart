import 'package:flutter/material.dart';
import 'package:gte_frontend/models/club_finance_models.dart';
import 'package:gte_frontend/widgets/clubs/club_ops_formatters.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class BudgetBreakdownCard extends StatelessWidget {
  const BudgetBreakdownCard({
    super.key,
    required this.title,
    required this.items,
    this.subtitle,
  });

  final String title;
  final String? subtitle;
  final List<FinanceCategoryBreakdown> items;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          if (subtitle != null) ...<Widget>[
            const SizedBox(height: 8),
            Text(subtitle!, style: Theme.of(context).textTheme.bodyMedium),
          ],
          const SizedBox(height: 18),
          for (final FinanceCategoryBreakdown item in items) ...<Widget>[
            _BudgetRow(item: item),
            if (item != items.last) const SizedBox(height: 14),
          ],
        ],
      ),
    );
  }
}

class _BudgetRow extends StatelessWidget {
  const _BudgetRow({
    required this.item,
  });

  final FinanceCategoryBreakdown item;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            Expanded(
              child: Text(
                item.label,
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ),
            const SizedBox(width: 12),
            Text(
              clubOpsFormatCurrency(item.amount),
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ],
        ),
        const SizedBox(height: 6),
        ClipRRect(
          borderRadius: BorderRadius.circular(999),
          child: LinearProgressIndicator(
            value: (item.sharePercent / 100).clamp(0, 1),
            minHeight: 10,
            backgroundColor: GteShellTheme.panelStrong,
            valueColor:
                const AlwaysStoppedAnimation<Color>(GteShellTheme.accentWarm),
          ),
        ),
        const SizedBox(height: 6),
        Text(
          '${item.sharePercent.toStringAsFixed(1)}% of planned spend${item.detail == null ? '' : ' · ${item.detail}'}',
          style: Theme.of(context).textTheme.bodyMedium,
        ),
      ],
    );
  }
}
