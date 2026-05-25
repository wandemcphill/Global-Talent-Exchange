import 'package:flutter/material.dart';

import '../../../data/match_gift_api.dart';
import '../../../ui_gtex/ui_gtex.dart';

typedef MatchGiftSelectionHandler =
    Future<void> Function(MatchGiftCatalogItem gift);

class GtexGiftingSheet extends StatelessWidget {
  const GtexGiftingSheet({
    super.key,
    required this.onSelected,
    this.unitLabel = 'Fan Coin',
  });

  final MatchGiftSelectionHandler onSelected;
  final String unitLabel;

  static Future<void> show(
    BuildContext context, {
    required MatchGiftSelectionHandler onSelected,
    String unitLabel = 'Fan Coin',
  }) {
    return showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (BuildContext context) {
        return GtexGiftingSheet(onSelected: onSelected, unitLabel: unitLabel);
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Container(
        margin: const EdgeInsets.all(12),
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
        decoration: BoxDecoration(
          gradient: GtexColors.panelGlow(accent: GtexColors.coinFan),
          borderRadius: BorderRadius.circular(GtexSpacing.radiusXl),
          border: Border.all(color: GtexColors.coinFan.withValues(alpha: 0.32)),
          boxShadow: <BoxShadow>[
            GtexColors.glow(GtexColors.coinFan, opacity: 0.18),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Send a live gift',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                color: GtexColors.text,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Match support settles through the live gift engine. Pick a real catalog item and send it to the verified match host.',
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: GtexColors.textSecondary),
            ),
            const SizedBox(height: 18),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: kMatchGiftCatalog
                  .map(
                    (MatchGiftCatalogItem option) => _GiftCatalogTile(
                      option: option,
                      unitLabel: unitLabel,
                      onTap: () async {
                        Navigator.of(context).pop();
                        await onSelected(option);
                      },
                    ),
                  )
                  .toList(growable: false),
            ),
          ],
        ),
      ),
    );
  }
}

class _GiftCatalogTile extends StatelessWidget {
  const _GiftCatalogTile({
    required this.option,
    required this.unitLabel,
    required this.onTap,
  });

  final MatchGiftCatalogItem option;
  final String unitLabel;
  final Future<void> Function() onTap;

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      tween: Tween<double>(begin: 0.96, end: 1),
      duration: const Duration(milliseconds: 240),
      curve: Curves.easeOutCubic,
      builder: (BuildContext context, double scale, Widget? child) {
        return Transform.scale(scale: scale, child: child);
      },
      child: InkWell(
        borderRadius: BorderRadius.circular(GtexSpacing.radiusLg),
        onTap: onTap,
        child: Container(
          width: 180,
          padding: const EdgeInsets.all(GtexSpacing.md),
          decoration: BoxDecoration(
            color: GtexColors.panelStrong.withValues(alpha: 0.82),
            borderRadius: BorderRadius.circular(GtexSpacing.radiusLg),
            border: Border.all(
              color: GtexColors.coinFan.withValues(alpha: 0.22),
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Icon(_giftIconFor(option.key), color: GtexColors.coinFan),
                  const SizedBox(width: GtexSpacing.xs),
                  Expanded(
                    child: Text(
                      option.label,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(
                        color: GtexColors.text,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: GtexSpacing.xs),
              Text(
                option.description,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: GtexColors.textMuted),
              ),
              const SizedBox(height: GtexSpacing.sm),
              FanCoinChip(
                amount: option.fanCoinAmount.toStringAsFixed(0),
                semanticLabel:
                    '${option.fanCoinAmount.toStringAsFixed(0)} $unitLabel gift',
              ),
            ],
          ),
        ),
      ),
    );
  }
}

IconData _giftIconFor(String key) {
  switch (key) {
    case 'fire':
      return Icons.campaign_outlined;
    case 'applause':
      return Icons.stadium_outlined;
    case 'crown':
      return Icons.workspace_premium_outlined;
  }
  return Icons.sports_soccer_outlined;
}
