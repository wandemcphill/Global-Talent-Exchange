import 'package:flutter/material.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/models/club_finance_models.dart';
import 'package:gte_frontend/widgets/clubs/club_ops_formatters.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';
import 'package:gte_frontend/widgets/gte_trend_strip.dart';

class CashflowTrendCard extends StatelessWidget {
  const CashflowTrendCard({
    super.key,
    required this.title,
    required this.cashflow,
    this.subtitle,
  });

  final String title;
  final String? subtitle;
  final List<CashflowPoint> cashflow;

  @override
  Widget build(BuildContext context) {
    final List<TrendPoint> points = cashflow
        .map((CashflowPoint point) => TrendPoint(label: point.label, value: point.net))
        .toList(growable: false);
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
          GteTrendStrip(points: points, height: 96),
          const SizedBox(height: 18),
          for (final CashflowPoint point in cashflow) ...<Widget>[
            Row(
              children: <Widget>[
                Expanded(child: Text(point.label)),
                Text(clubOpsFormatSignedCurrency(point.net)),
                const SizedBox(width: 12),
                Text(
                  'Close ${clubOpsFormatCurrency(point.closingBalance)}',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ],
            ),
            if (point != cashflow.last) const Divider(height: 20),
          ],
        ],
      ),
    );
  }
}
