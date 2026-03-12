import 'package:flutter/material.dart';
import 'package:gte_frontend/models/academy_models.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class PlayerProgressCard extends StatelessWidget {
  const PlayerProgressCard({
    super.key,
    required this.player,
  });

  final AcademyPlayer player;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      emphasized: player.promotedToSenior,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(player.name, style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 8),
          Text(
            '${player.position} · ${player.age} · ${player.pathwayStage}',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          Text('Development progress', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(999),
            child: LinearProgressIndicator(
              value: (player.developmentProgressPercent / 100).clamp(0, 1),
              minHeight: 12,
              backgroundColor: GteShellTheme.panelStrong,
              valueColor: const AlwaysStoppedAnimation<Color>(GteShellTheme.accent),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            '${player.developmentProgressPercent.toStringAsFixed(0)}% complete · readiness ${player.readinessScore}',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 12),
          Text(player.nextMilestone, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              ...player.strengths.map((String item) => Chip(label: Text(item))),
              ...player.focusAreas
                  .map((String item) => Chip(label: Text('Focus: $item'))),
            ],
          ),
        ],
      ),
    );
  }
}
