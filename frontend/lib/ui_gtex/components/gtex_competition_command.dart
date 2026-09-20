import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';
import '../theme/gtex_typography.dart';

/// A small, reusable family switcher for product surfaces that expose more
/// than one competition contract. It deliberately keeps the family labels
/// visible instead of flattening them into a generic "all competitions" feed.
class GtexCompetitionFamilySelector<T> extends StatelessWidget {
  const GtexCompetitionFamilySelector({
    super.key,
    required this.value,
    required this.items,
    required this.onChanged,
  });

  final T value;
  final List<GtexCompetitionFamilyItem<T>> items;
  final ValueChanged<T> onChanged;

  @override
  Widget build(BuildContext context) => SingleChildScrollView(
    scrollDirection: Axis.horizontal,
    child: Row(
      children: items
          .map(
            (GtexCompetitionFamilyItem<T> item) => Padding(
              padding: const EdgeInsets.only(right: GtexSpacing.xs),
              child: ChoiceChip(
                label: Text(item.label),
                selected: item.value == value,
                onSelected: (_) => onChanged(item.value),
                selectedColor: item.accent.withValues(alpha: 0.20),
                side: BorderSide(
                  color:
                      item.value == value
                          ? item.accent
                          : GtexColors.surfaceBorder,
                ),
                labelStyle: GtexText.labelSM.copyWith(
                  color:
                      item.value == value
                          ? item.accent
                          : GtexColors.textSecondary,
                ),
              ),
            ),
          )
          .toList(growable: false),
    ),
  );
}

class GtexCompetitionFamilyItem<T> {
  const GtexCompetitionFamilyItem({
    required this.value,
    required this.label,
    required this.accent,
  });

  final T value;
  final String label;
  final Color accent;
}

/// A fact-only fixture treatment. Callers supply text from their authoritative
/// match contract; absent timing or match links are intentionally omitted.
class GtexMatchdayFixtureTile extends StatelessWidget {
  const GtexMatchdayFixtureTile({
    super.key,
    required this.home,
    required this.away,
    required this.stateLabel,
    this.contextLabel,
    this.scoreLabel,
    this.onOpenMatch,
  });

  final String home;
  final String away;
  final String stateLabel;
  final String? contextLabel;
  final String? scoreLabel;
  final VoidCallback? onOpenMatch;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(GtexSpacing.md),
    decoration: BoxDecoration(
      color: GtexColors.surfaceRaised,
      border: Border.all(color: GtexColors.surfaceBorder),
      borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
    ),
    child: Row(
      children: <Widget>[
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                stateLabel.toUpperCase(),
                style: GtexText.labelSM.copyWith(color: GtexColors.accentBlue),
              ),
              const SizedBox(height: 4),
              Text(
                '$home  vs  $away',
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: GtexText.labelLG.copyWith(color: GtexColors.textPrimary),
              ),
              if (contextLabel != null) ...<Widget>[
                const SizedBox(height: 4),
                Text(
                  contextLabel!,
                  style: GtexText.bodySM.copyWith(
                    color: GtexColors.textSecondary,
                  ),
                ),
              ],
            ],
          ),
        ),
        if (scoreLabel != null)
          Text(
            scoreLabel!,
            style: GtexText.monoLG.copyWith(color: GtexColors.textPrimary),
          ),
        if (onOpenMatch != null) ...<Widget>[
          const SizedBox(width: GtexSpacing.sm),
          IconButton(
            tooltip: 'Open Match Viewer',
            onPressed: onOpenMatch,
            icon: const Icon(Icons.play_circle_outline_rounded),
            color: GtexColors.accentPrimary,
          ),
        ],
      ],
    ),
  );
}

class GtexCompetitionStandingRow extends StatelessWidget {
  const GtexCompetitionStandingRow({
    super.key,
    required this.position,
    required this.name,
    required this.points,
    this.played,
  });

  final String position;
  final String name;
  final String points;
  final String? played;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(
      horizontal: GtexSpacing.md,
      vertical: GtexSpacing.sm,
    ),
    decoration: const BoxDecoration(
      border: Border(bottom: BorderSide(color: GtexColors.surfaceBorder)),
    ),
    child: Row(
      children: <Widget>[
        SizedBox(width: 32, child: Text(position, style: GtexText.monoMD)),
        Expanded(
          child: Text(
            name,
            overflow: TextOverflow.ellipsis,
            style: GtexText.labelMD.copyWith(color: GtexColors.textPrimary),
          ),
        ),
        if (played != null)
          Text(
            'P $played',
            style: GtexText.bodySM.copyWith(color: GtexColors.textSecondary),
          ),
        const SizedBox(width: GtexSpacing.md),
        Text(
          '$points pts',
          style: GtexText.monoMD.copyWith(color: GtexColors.accentAmber),
        ),
      ],
    ),
  );
}
