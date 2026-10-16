import 'package:flutter/material.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

import '../data/reputation_models.dart';

class ReputationEventTile extends StatelessWidget {
  const ReputationEventTile({
    super.key,
    required this.event,
  });

  final ReputationEventDto event;

  @override
  Widget build(BuildContext context) {
    final Color tone =
        event.isPositive ? GteShellTheme.positive : GteShellTheme.negative;
    final int year = event.occurredAt.year;
    final bool hasYear = year > 1970;
    final String metaLine = hasYear
        ? '${event.seasonLabel} - ${event.category.label} - $year'
        : '${event.seasonLabel} - ${event.category.label}';
    final List<String> highlightTags = <String>[
      ...event.milestones,
      ...event.badges.map(prettifyBadgeCode),
    ].where((String value) => value.trim().isNotEmpty).toList(growable: false);
    return GteSurfacePanel(
      padding: const EdgeInsets.all(18),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: tone.withValues(alpha: 0.12),
            ),
            child: Icon(event.category.icon, color: tone),
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
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            event.title,
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                          const SizedBox(height: 4),
                          Text(
                            metaLine,
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 12),
                    _DeltaPill(delta: event.delta),
                  ],
                ),
                const SizedBox(height: 10),
                Text(
                  event.description,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color:
                            GteShellTheme.textPrimary.withValues(alpha: 0.84),
                      ),
                ),
                if (highlightTags.isNotEmpty) ...<Widget>[
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: highlightTags
                        .take(3)
                        .map(
                          (String tag) => Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 10,
                              vertical: 6,
                            ),
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(999),
                              color:
                                  GteShellTheme.panelStrong.withValues(alpha: 0.9),
                              border: Border.all(
                                color: GteShellTheme.stroke,
                              ),
                            ),
                            child: Text(
                              tag,
                              style: Theme.of(context).textTheme.labelMedium,
                            ),
                          ),
                        )
                        .toList(growable: false),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _DeltaPill extends StatelessWidget {
  const _DeltaPill({
    required this.delta,
  });

  final int delta;

  @override
  Widget build(BuildContext context) {
    final bool positive = delta >= 0;
    final Color tone =
        positive ? GteShellTheme.positive : GteShellTheme.negative;
    final String label = positive ? '+$delta' : '$delta';
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: tone.withValues(alpha: 0.12),
        border: Border.all(color: tone.withValues(alpha: 0.28)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelLarge?.copyWith(color: tone),
      ),
    );
  }
}
