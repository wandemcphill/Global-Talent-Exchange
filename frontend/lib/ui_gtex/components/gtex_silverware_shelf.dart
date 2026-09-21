import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';

/// Representation of a trophy or honor item in the shelf.
class SilverwareItem {
  const SilverwareItem({
    required this.name,
    required this.category,
    required this.count,
    this.latestSeason,
    this.accentColor = GtexColors.gold,
  });

  final String name;
  final String category;
  final int count;
  final String? latestSeason;
  final Color accentColor;
}

/// A compact ribbon/shelf displaying trophies and silverware won by a club or player.
class GtexSilverwareShelf extends StatelessWidget {
  const GtexSilverwareShelf({
    super.key,
    this.title = 'HONOURS & SILVERWARE',
    required this.trophies,
    this.totalTrophiesCount,
    this.onViewAll,
  });

  final String title;
  final List<SilverwareItem> trophies;
  final int? totalTrophiesCount;
  final VoidCallback? onViewAll;

  @override
  Widget build(BuildContext context) {
    final int count = totalTrophiesCount ??
        trophies.fold<int>(0, (int sum, SilverwareItem item) => sum + item.count);

    return Container(
      padding: const EdgeInsets.all(GtexSpacing.md),
      decoration: BoxDecoration(
        color: GtexColors.panelStrong,
        borderRadius: BorderRadius.circular(GtexSpacing.radiusLg),
        border: Border.all(color: GtexColors.gold.withValues(alpha: 0.35)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: GtexColors.gold.withValues(alpha: 0.05),
            blurRadius: 12,
            spreadRadius: -2,
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: <Widget>[
              Row(
                children: <Widget>[
                  const Icon(Icons.emoji_events, size: 20, color: GtexColors.gold),
                  const SizedBox(width: GtexSpacing.xs),
                  Text(
                    title.toUpperCase(),
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: GtexColors.text,
                          fontWeight: FontWeight.w900,
                          letterSpacing: 0.8,
                        ),
                  ),
                  const SizedBox(width: GtexSpacing.xs),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                    decoration: BoxDecoration(
                      color: GtexColors.gold.withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: GtexColors.gold.withValues(alpha: 0.5)),
                    ),
                    child: Text(
                      '$count',
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                            color: GtexColors.gold,
                            fontWeight: FontWeight.w900,
                          ),
                    ),
                  ),
                ],
              ),
              if (onViewAll != null)
                InkWell(
                  onTap: onViewAll,
                  child: Padding(
                    padding: const EdgeInsets.all(4.0),
                    child: Text(
                      'VIEW ALL',
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                            color: GtexColors.gold,
                            fontWeight: FontWeight.w800,
                          ),
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: GtexSpacing.sm),
          if (trophies.isEmpty) ...<Widget>[
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: GtexSpacing.md),
              decoration: BoxDecoration(
                color: GtexColors.surfaceBase.withValues(alpha: 0.5),
                borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
              ),
              child: Center(
                child: Text(
                  'No Silverware Won Yet',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: GtexColors.textMuted,
                        fontWeight: FontWeight.w600,
                      ),
                ),
              ),
            ),
          ] else ...<Widget>[
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: trophies.map((SilverwareItem trophy) {
                  return Container(
                    margin: const EdgeInsets.only(right: GtexSpacing.sm),
                    padding: const EdgeInsets.symmetric(
                      horizontal: GtexSpacing.sm,
                      vertical: GtexSpacing.xs + 2,
                    ),
                    decoration: BoxDecoration(
                      color: GtexColors.surfaceBase,
                      borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
                      border: Border.all(
                        color: trophy.accentColor.withValues(alpha: 0.4),
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: <Widget>[
                        Container(
                          width: 32,
                          height: 32,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: trophy.accentColor.withValues(alpha: 0.15),
                          ),
                          child: Icon(
                            Icons.emoji_events,
                            size: 18,
                            color: trophy.accentColor,
                          ),
                        ),
                        const SizedBox(width: GtexSpacing.xs),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisSize: MainAxisSize.min,
                          children: <Widget>[
                            Row(
                              mainAxisSize: MainAxisSize.min,
                              children: <Widget>[
                                Text(
                                  trophy.name,
                                  style: Theme.of(context).textTheme.labelMedium?.copyWith(
                                        color: GtexColors.text,
                                        fontWeight: FontWeight.w800,
                                      ),
                                ),
                                const SizedBox(width: 4),
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 4, vertical: 1),
                                  decoration: BoxDecoration(
                                    color: trophy.accentColor.withValues(alpha: 0.25),
                                    borderRadius: BorderRadius.circular(4),
                                  ),
                                  child: Text(
                                    'x${trophy.count}',
                                    style: Theme.of(context)
                                        .textTheme
                                        .labelSmall
                                        ?.copyWith(
                                          color: trophy.accentColor,
                                          fontWeight: FontWeight.w900,
                                          fontSize: 10,
                                        ),
                                  ),
                                ),
                              ],
                            ),
                            if (trophy.latestSeason != null)
                              Text(
                                trophy.latestSeason!,
                                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                                      color: GtexColors.textMuted,
                                      fontWeight: FontWeight.w600,
                                      fontSize: 10,
                                    ),
                              ),
                          ],
                        ),
                      ],
                    ),
                  );
                }).toList(),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
