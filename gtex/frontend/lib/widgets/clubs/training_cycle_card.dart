import 'package:flutter/material.dart';
import 'package:gte_frontend/models/academy_models.dart';
import 'package:gte_frontend/widgets/clubs/club_ops_formatters.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class TrainingCycleCard extends StatelessWidget {
  const TrainingCycleCard({
    super.key,
    required this.cycle,
  });

  final TrainingCycle cycle;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(cycle.title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 6),
          Text(
            '${cycle.phaseLabel} · ${cycle.cohortLabel}',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 10),
          Text(cycle.focus, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 6),
          Text(cycle.objective, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 12),
          Text(
            '${clubOpsFormatDate(cycle.startDate)} to ${clubOpsFormatDate(cycle.endDate)}',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          Text(
            'Attendance ${cycle.attendancePercent.toStringAsFixed(0)}% · ${cycle.intensityLabel} load',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ],
      ),
    );
  }
}
