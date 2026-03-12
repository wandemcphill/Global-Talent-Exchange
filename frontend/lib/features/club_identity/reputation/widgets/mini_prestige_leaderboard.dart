import 'package:flutter/material.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

import '../data/reputation_models.dart';
import 'prestige_tier_badge.dart';

class MiniPrestigeLeaderboard extends StatelessWidget {
  const MiniPrestigeLeaderboard({
    super.key,
    required this.entries,
    required this.currentClubId,
    this.note,
  });

  final List<PrestigeLeaderboardEntryDto> entries;
  final String currentClubId;
  final String? note;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Prestige leaderboard',
              style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Text(
            'See who owns the loudest club identity right now.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          ...entries.map(
            (PrestigeLeaderboardEntryDto entry) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: _MiniLeaderboardRow(
                entry: entry,
                highlighted: entry.clubId == currentClubId,
              ),
            ),
          ),
          if (note != null) ...<Widget>[
            const SizedBox(height: 8),
            Text(
              note!,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: GteShellTheme.accentWarm,
                  ),
            ),
          ],
        ],
      ),
    );
  }
}

class _MiniLeaderboardRow extends StatelessWidget {
  const _MiniLeaderboardRow({
    required this.entry,
    required this.highlighted,
  });

  final PrestigeLeaderboardEntryDto entry;
  final bool highlighted;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        color: highlighted
            ? GteShellTheme.accent.withValues(alpha: 0.1)
            : GteShellTheme.panelStrong.withValues(alpha: 0.7),
        border: Border.all(
          color: highlighted
              ? GteShellTheme.accent.withValues(alpha: 0.4)
              : GteShellTheme.stroke,
        ),
      ),
      child: Row(
        children: <Widget>[
          SizedBox(
            width: 24,
            child: Text(
              '#${entry.rank}',
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  entry.clubName,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                Text(
                  entry.regionLabel,
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ],
            ),
          ),
          const SizedBox(width: 10),
          PrestigeTierBadge(tier: entry.currentPrestigeTier, compact: true),
          const SizedBox(width: 10),
          Text(
            '${entry.currentScore}',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: GteShellTheme.textPrimary,
                ),
          ),
        ],
      ),
    );
  }
}
