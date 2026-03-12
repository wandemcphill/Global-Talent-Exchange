import 'package:flutter/material.dart';
import 'package:gte_frontend/models/academy_models.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class AcademyConversionCard extends StatelessWidget {
  const AcademyConversionCard({
    super.key,
    required this.analytics,
  });

  final AcademyAnalyticsSnapshot analytics;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Academy pathway', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 10),
          Text(
            '${analytics.conversionRatePercent.toStringAsFixed(1)}% conversion',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 6),
          Text(
            '${analytics.retentionRatePercent.toStringAsFixed(0)}% retention · readiness ${analytics.averageReadinessScore}',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 10),
          Text(analytics.pathwayHealthLabel,
              style: Theme.of(context).textTheme.bodyMedium),
        ],
      ),
    );
  }
}
