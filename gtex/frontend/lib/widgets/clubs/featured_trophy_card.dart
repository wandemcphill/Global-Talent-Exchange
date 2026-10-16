import 'package:flutter/material.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_item_dto.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class FeaturedTrophyCard extends StatelessWidget {
  const FeaturedTrophyCard({
    super.key,
    required this.trophy,
    this.onTap,
  });

  final TrophyItemDto trophy;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      emphasized: true,
      onTap: onTap,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(
            width: 64,
            height: 64,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: GteShellTheme.accentWarm.withValues(alpha: 0.14),
              border: Border.all(
                color: GteShellTheme.accentWarm.withValues(alpha: 0.4),
              ),
            ),
            child: const Icon(
              Icons.emoji_events,
              color: GteShellTheme.accentWarm,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  trophy.trophyName,
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 6),
                Text(
                  '${trophy.seasonLabel} • ${trophy.competitionRegion} • ${trophy.prestigeLabel}',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 10),
                Text(
                  trophy.finalResultSummary,
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
