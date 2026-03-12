import 'package:flutter/material.dart';
import 'package:gte_frontend/models/scouting_models.dart';
import 'package:gte_frontend/widgets/clubs/club_ops_formatters.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class ScoutAssignmentCard extends StatelessWidget {
  const ScoutAssignmentCard({
    super.key,
    required this.assignment,
  });

  final ScoutAssignment assignment;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(assignment.focusArea, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 6),
          Text(
            '${assignment.region} · ${assignment.competition}',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 10),
          Text(assignment.objective, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 12),
          Text('Scout: ${assignment.scoutName}',
              style: Theme.of(context).textTheme.bodyMedium),
          Text(
            '${assignment.activeProspects} active prospects · due ${clubOpsFormatDate(assignment.dueDate)}',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 8),
          Text(
            '${assignment.priorityLabel} · ${assignment.statusLabel}',
            style: Theme.of(context).textTheme.titleMedium,
          ),
        ],
      ),
    );
  }
}
