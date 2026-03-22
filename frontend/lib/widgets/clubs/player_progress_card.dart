import 'package:flutter/material.dart';
import 'package:gte_frontend/models/academy_models.dart';
import 'package:gte_frontend/services/avatar_mapper.dart';
import 'package:gte_frontend/widgets/gte_formatters.dart';
import 'package:gte_frontend/widgets/gte_metric_chip.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';
import 'package:gte_frontend/widgets/squad/squad_avatar_badge.dart';

class PlayerProgressCard extends StatelessWidget {
  const PlayerProgressCard({
    super.key,
    required this.player,
  });

  final AcademyPlayer player;

  @override
  Widget build(BuildContext context) {
    final avatar = AvatarMapper.fromAcademyPlayer(player);
    final String summaryLine = <String>[
      player.position,
      'Age ${player.age}',
      player.pathwayStage,
      if (player.nationality != null) player.nationality!,
    ].join(' | ');

    return GteSurfacePanel(
      emphasized: player.promotedToSenior,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              SquadAvatarBadge(avatar: avatar, size: 56),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(player.name,
                        style: Theme.of(context).textTheme.headlineSmall),
                    const SizedBox(height: 8),
                    Text(
                      summaryLine,
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              GteMetricChip(
                label: 'Readiness',
                value: player.readinessScore.toString(),
              ),
              if (player.currentValueCredits != null)
                GteMetricChip(
                  label: 'Official GTEX',
                  value: gteFormatCredits(player.currentValueCredits!),
                ),
              if (player.dominantFoot != null)
                GteMetricChip(
                  label: 'Foot',
                  value: player.dominantFoot!,
                ),
              if (player.roleArchetype != null)
                GteMetricChip(
                  label: 'Role',
                  value: player.roleArchetype!,
                ),
              if (player.formationSlots.isNotEmpty)
                GteMetricChip(
                  label: 'Slots',
                  value: player.formationSlots.join('/'),
                ),
              if (player.squadEligible != null)
                GteMetricChip(
                  label: 'Squad',
                  value: player.squadEligible! ? 'Eligible' : 'Restricted',
                  positive: player.squadEligible!,
                ),
            ],
          ),
          const SizedBox(height: 16),
          Text('Development progress',
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(999),
            child: LinearProgressIndicator(
              value: (player.developmentProgressPercent / 100).clamp(0, 1),
              minHeight: 12,
              backgroundColor: GteShellTheme.panelStrong,
              valueColor:
                  const AlwaysStoppedAnimation<Color>(GteShellTheme.accent),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            '${player.developmentProgressPercent.toStringAsFixed(0)}% complete | readiness ${player.readinessScore}',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 12),
          Text(player.nextMilestone,
              style: Theme.of(context).textTheme.titleMedium),
          if (player.secondaryPositions.isNotEmpty) ...<Widget>[
            const SizedBox(height: 8),
            Text(
              'Secondary positions: ${player.secondaryPositions.join(', ')}',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
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
