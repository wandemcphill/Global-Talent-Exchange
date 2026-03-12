import 'package:flutter/material.dart';

import '../../../../widgets/gte_shell_theme.dart';
import '../../../../widgets/gte_surface_panel.dart';
import '../data/dynasty_era_dto.dart';
import '../data/dynasty_types.dart';
import 'era_label_chip.dart';

class EraHistoryCard extends StatelessWidget {
  const EraHistoryCard({
    super.key,
    required this.detail,
  });

  final DynastyEraDetail detail;

  @override
  Widget build(BuildContext context) {
    final DynastyEraDto era = detail.era;
    return GteSurfacePanel(
      emphasized: era.active,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Wrap(
            spacing: 10,
            runSpacing: 10,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: <Widget>[
              EraLabelChip(era: era.eraLabel, active: era.active),
              if (era.active)
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(999),
                    color: GteShellTheme.accent.withValues(alpha: 0.12),
                  ),
                  child: Text(
                    'Current era',
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(
                          color: GteShellTheme.accent,
                        ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 14),
          Text(
            era.seasonSpanLabel,
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 6),
          Text(
            era.eraLabel.strapline,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              _StatPill(
                label: 'Peak score',
                value: '${era.peakScore}',
                tone: GteShellTheme.accentWarm,
              ),
              _StatPill(
                label: 'Trophies won',
                value: '${detail.trophiesWon}',
                tone: GteShellTheme.positive,
              ),
              _StatPill(
                label: 'Reputation',
                value: _signedValue(detail.reputationGrowth),
                tone: detail.reputationGrowth >= 0
                    ? GteShellTheme.accent
                    : GteShellTheme.negative,
              ),
            ],
          ),
          const SizedBox(height: 18),
          Text(
            'Defining achievements',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 10),
          if (detail.definingAchievements.isEmpty)
            Text(
              'This era has been labeled, but a fuller achievement feed has not been published yet.',
              style: Theme.of(context).textTheme.bodyMedium,
            )
          else
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: detail.definingAchievements
                  .take(4)
                  .map(
                    (String reason) => Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          const Padding(
                            padding: EdgeInsets.only(top: 4),
                            child: Icon(
                              Icons.chevron_right,
                              size: 18,
                              color: GteShellTheme.accentWarm,
                            ),
                          ),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              reason,
                              style: Theme.of(context).textTheme.bodyMedium,
                            ),
                          ),
                        ],
                      ),
                    ),
                  )
                  .toList(growable: false),
            ),
        ],
      ),
    );
  }

  String _signedValue(int value) {
    if (value > 0) {
      return '+$value';
    }
    return '$value';
  }
}

class _StatPill extends StatelessWidget {
  const _StatPill({
    required this.label,
    required this.value,
    required this.tone,
  });

  final String label;
  final String value;
  final Color tone;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: tone.withValues(alpha: 0.1),
        border: Border.all(color: tone.withValues(alpha: 0.28)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Text(label, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 4),
          Text(
            value,
            style:
                Theme.of(context).textTheme.titleMedium?.copyWith(color: tone),
          ),
        ],
      ),
    );
  }
}
