import 'package:flutter/material.dart';
import 'package:gte_frontend/models/academy_models.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class AcademyProgramCard extends StatelessWidget {
  const AcademyProgramCard({
    super.key,
    required this.program,
  });

  final AcademyProgram program;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(program.name, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 6),
          Text(
            '${program.ageBand} · ${program.focusArea}',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 10),
          Text(program.description, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 12),
          Text('Lead: ${program.staffLead}',
              style: Theme.of(context).textTheme.bodyMedium),
          Text(
            '${program.weeklyHours} hrs/week · ${program.enrolledPlayers} players',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 8),
          Text(program.outcomeLabel, style: Theme.of(context).textTheme.titleMedium),
        ],
      ),
    );
  }
}
