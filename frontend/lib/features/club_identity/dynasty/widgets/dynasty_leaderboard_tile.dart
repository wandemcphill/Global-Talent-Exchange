import 'package:flutter/material.dart';

import '../../../../widgets/gte_shell_theme.dart';
import '../../../../widgets/gte_surface_panel.dart';
import '../data/dynasty_leaderboard_entry_dto.dart';
import 'era_label_chip.dart';

class DynastyLeaderboardTile extends StatelessWidget {
  const DynastyLeaderboardTile({
    super.key,
    required this.entry,
    required this.rank,
    this.onTap,
  });

  final DynastyLeaderboardEntryDto entry;
  final int rank;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      onTap: onTap,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(
            width: 46,
            height: 46,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: _rankColor(rank).withValues(alpha: 0.16),
            ),
            alignment: Alignment.center,
            child: Text(
              '$rank',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: _rankColor(rank),
                  ),
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Expanded(
                      child: Text(
                        entry.clubName,
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Text(
                      '${entry.dynastyScore}',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            color: GteShellTheme.accentWarm,
                          ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                EraLabelChip(
                  era: entry.currentEraLabel,
                  active: entry.activeDynastyFlag,
                ),
                if (entry.reasons.isNotEmpty) ...<Widget>[
                  const SizedBox(height: 12),
                  Text(
                    entry.reasons.first,
                    style: Theme.of(context).textTheme.bodyMedium,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Color _rankColor(int rank) {
    if (rank == 1) {
      return const Color(0xFFFFE08C);
    }
    if (rank == 2) {
      return const Color(0xFFC7D3E4);
    }
    if (rank == 3) {
      return const Color(0xFFD8AE82);
    }
    return GteShellTheme.accent;
  }
}
