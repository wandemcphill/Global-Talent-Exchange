import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';

/// Tile rendering holding position, market value, contract length, and squad tier.
class GtexOwnershipIndicatorTile extends StatelessWidget {
  const GtexOwnershipIndicatorTile({
    super.key,
    required this.name,
    required this.quantity,
    this.sharePriceCoin = 0,
    this.contractDurationYears,
    this.squadTier,
    this.isTradable = true,
    this.onTap,
  });

  final String name;
  final int quantity;
  final int sharePriceCoin;
  final int? contractDurationYears;
  final String? squadTier;
  final bool isTradable;
  final VoidCallback? onTap;

  int get totalValuationCoin => quantity * sharePriceCoin;

  @override
  Widget build(BuildContext context) {
    final bool isOwned = quantity > 0;
    final Color accent = isOwned ? GtexColors.pitch : GtexColors.textMuted;

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
      child: Container(
        padding: const EdgeInsets.all(GtexSpacing.md),
        decoration: BoxDecoration(
          color: GtexColors.panelStrong,
          borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
          border: Border.all(
            color: isOwned
                ? accent.withValues(alpha: 0.5)
                : GtexColors.line.withValues(alpha: 0.6),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: <Widget>[
                Expanded(
                  child: Text(
                    name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          color: GtexColors.text,
                          fontWeight: FontWeight.w800,
                        ),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: accent.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(GtexSpacing.radiusSm),
                    border: Border.all(color: accent.withValues(alpha: 0.4)),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: <Widget>[
                      Icon(
                        isOwned ? Icons.pie_chart : Icons.store,
                        size: 13,
                        color: accent,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        isOwned ? '$quantity Shares Held' : 'No Shares Held',
                        style: Theme.of(context).textTheme.labelSmall?.copyWith(
                              color: accent,
                              fontWeight: FontWeight.w900,
                            ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: GtexSpacing.sm),
            Row(
              children: <Widget>[
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'POSITION VALUE',
                        style: Theme.of(context).textTheme.labelSmall?.copyWith(
                              color: GtexColors.textMuted,
                              fontWeight: FontWeight.w800,
                              fontSize: 10,
                            ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        isOwned ? '🪙 $totalValuationCoin' : '🪙 $sharePriceCoin / share',
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                              color: GtexColors.gold,
                              fontWeight: FontWeight.w900,
                            ),
                      ),
                    ],
                  ),
                ),
                if (contractDurationYears != null) ...<Widget>[
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'CONTRACT',
                          style: Theme.of(context).textTheme.labelSmall?.copyWith(
                                color: GtexColors.textMuted,
                                fontWeight: FontWeight.w800,
                                fontSize: 10,
                              ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          '$contractDurationYears Years',
                          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                                color: GtexColors.text,
                                fontWeight: FontWeight.w800,
                              ),
                        ),
                      ],
                    ),
                  ),
                ],
                if (squadTier != null && squadTier!.isNotEmpty) ...<Widget>[
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'SQUAD TIER',
                          style: Theme.of(context).textTheme.labelSmall?.copyWith(
                                color: GtexColors.textMuted,
                                fontWeight: FontWeight.w800,
                                fontSize: 10,
                              ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          squadTier!.replaceAll('_', ' ').toUpperCase(),
                          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                                color: GtexColors.pitch,
                                fontWeight: FontWeight.w800,
                              ),
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }
}
