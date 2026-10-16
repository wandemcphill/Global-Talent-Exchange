import 'package:flutter/material.dart';
import 'package:gte_frontend/models/sponsorship_models.dart';
import 'package:gte_frontend/widgets/clubs/club_ops_formatters.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class SponsorshipRevenueSummaryCard extends StatelessWidget {
  const SponsorshipRevenueSummaryCard({
    super.key,
    required this.analytics,
  });

  final SponsorshipAnalyticsSnapshot analytics;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Sponsorship revenue', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 10),
          Text(
            clubOpsFormatCurrency(analytics.totalRevenue),
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 6),
          Text(
            '${analytics.renewalRatePercent.toStringAsFixed(0)}% renewals · ${analytics.assetUtilizationPercent.toStringAsFixed(0)}% asset utilization',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ],
      ),
    );
  }
}
