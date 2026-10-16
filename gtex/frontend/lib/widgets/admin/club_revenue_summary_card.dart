import 'package:flutter/material.dart';
import 'package:gte_frontend/models/club_models.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class ClubRevenueSummaryCard extends StatelessWidget {
  const ClubRevenueSummaryCard({
    super.key,
    required this.summary,
  });

  final ClubRevenueSummary summary;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 220,
      child: GteSurfacePanel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              summary.valueLabel,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              summary.label,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            const SizedBox(height: 6),
            Text(
              summary.caption,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }
}
