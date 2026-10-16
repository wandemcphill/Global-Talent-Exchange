import 'package:flutter/material.dart';

import '../../../../widgets/gte_shell_theme.dart';
import '../../../../widgets/gte_surface_panel.dart';
import '../data/dynasty_profile_dto.dart';

class StreakIndicatorRow extends StatelessWidget {
  const StreakIndicatorRow({
    super.key,
    required this.streaks,
  });

  final DynastyStreaksDto streaks;

  @override
  Widget build(BuildContext context) {
    final List<_StreakCardData> items = <_StreakCardData>[
      _StreakCardData(
        label: 'Top-four run',
        value: streaks.topFour,
        icon: Icons.trending_up,
      ),
      _StreakCardData(
        label: 'Trophy seasons',
        value: streaks.trophySeasons,
        icon: Icons.emoji_events_outlined,
      ),
      _StreakCardData(
        label: 'World stage',
        value: streaks.worldSuperCupQualification,
        icon: Icons.public_outlined,
      ),
      _StreakCardData(
        label: 'Reputation rise',
        value: streaks.positiveReputation,
        icon: Icons.auto_graph_outlined,
      ),
    ];
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool stacked = constraints.maxWidth < 680;
        final double cardWidth =
            stacked ? constraints.maxWidth : (constraints.maxWidth - 12) / 2;
        return Wrap(
          spacing: 12,
          runSpacing: 12,
          children: items
              .map(
                (_StreakCardData item) => SizedBox(
                  width: cardWidth,
                  child: _StreakCard(data: item),
                ),
              )
              .toList(growable: false),
        );
      },
    );
  }
}

class _StreakCardData {
  const _StreakCardData({
    required this.label,
    required this.value,
    required this.icon,
  });

  final String label;
  final int value;
  final IconData icon;
}

class _StreakCard extends StatelessWidget {
  const _StreakCard({
    required this.data,
  });

  final _StreakCardData data;

  @override
  Widget build(BuildContext context) {
    final bool hot = data.value >= 3;
    return GteSurfacePanel(
      child: Row(
        children: <Widget>[
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: (hot ? GteShellTheme.accent : GteShellTheme.stroke)
                  .withValues(alpha: 0.14),
            ),
            child: Icon(
              data.icon,
              color: hot ? GteShellTheme.accent : GteShellTheme.textMuted,
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(data.label, style: Theme.of(context).textTheme.bodyMedium),
                const SizedBox(height: 4),
                Text(
                  '${data.value} season${data.value == 1 ? '' : 's'}',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
