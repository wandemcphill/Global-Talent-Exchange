import 'package:flutter/material.dart';
import 'package:gte_frontend/models/academy_models.dart';
import 'package:gte_frontend/services/avatar_mapper.dart';
import 'package:gte_frontend/widgets/gte_formatters.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';
import 'package:gte_frontend/widgets/squad/squad_avatar_badge.dart';

class AcademyPlayerRow extends StatelessWidget {
  const AcademyPlayerRow({
    super.key,
    required this.player,
    this.onTap,
  });

  final AcademyPlayer player;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final avatar = AvatarMapper.fromAcademyPlayer(player);
    final String metadataLine = <String>[
      player.position,
      'Age ${player.age}',
      player.pathwayStage,
      if (player.nationalityCode != null) player.nationalityCode!,
    ].join(' | ');
    final String extraLine = <String>[
      if (player.secondaryPositions.isNotEmpty)
        'Alt ${player.secondaryPositions.join('/')}',
      if (player.currentValueCredits != null)
        'GTEX ${gteFormatCredits(player.currentValueCredits!)}',
    ].join(' | ');

    return GteSurfacePanel(
      onTap: onTap,
      padding: const EdgeInsets.all(16),
      child: Row(
        children: <Widget>[
          SquadAvatarBadge(avatar: avatar),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(player.name,
                    style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 4),
                Text(
                  metadataLine,
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                if (extraLine.isNotEmpty) ...<Widget>[
                  const SizedBox(height: 4),
                  Text(
                    extraLine,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: <Widget>[
              if (player.currentValueCredits != null) ...<Widget>[
                Text(
                  gteFormatCredits(player.currentValueCredits!),
                  style: Theme.of(context).textTheme.titleMedium,
                  textAlign: TextAlign.right,
                ),
                const SizedBox(height: 4),
                Text(
                  'Official GTEX',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 8),
              ],
              Text('${player.readinessScore}',
                  style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 4),
              Text('Readiness', style: Theme.of(context).textTheme.bodyMedium),
            ],
          ),
        ],
      ),
    );
  }
}
