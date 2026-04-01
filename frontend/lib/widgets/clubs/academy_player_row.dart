import 'package:flutter/material.dart';
import 'package:gte_frontend/models/academy_models.dart';
import 'package:gte_frontend/services/avatar_mapper.dart';
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
                  '${player.age} · ${player.pathwayStage}',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: <Widget>[
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
