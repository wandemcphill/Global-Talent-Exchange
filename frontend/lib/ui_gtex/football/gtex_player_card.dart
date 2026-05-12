import 'package:flutter/material.dart';

import '../components/gtex_action_button.dart';
import '../components/gtex_status_chip.dart';
import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';

class GtexPlayerCard extends StatelessWidget {
  const GtexPlayerCard({
    super.key,
    required this.name,
    required this.position,
    required this.clubName,
    required this.nationality,
    required this.priceLabel,
    this.imageUrl,
    this.gsiLabel,
    this.gsiTierLabel,
    this.gsiTrendLabel,
    this.ratingLabel,
    this.ageLabel,
    this.badges = const <Widget>[],
    this.isSelected = false,
    this.onTap,
    this.onAddToShortlist,
    this.onBuyNow,
    this.buyNowLabel = 'Buy',
  });

  final String name;
  final String position;
  final String clubName;
  final String nationality;
  final String priceLabel;
  final String? imageUrl;
  final String? gsiLabel;
  final String? gsiTierLabel;
  final String? gsiTrendLabel;
  final String? ratingLabel;
  final String? ageLabel;
  final List<Widget> badges;
  final bool isSelected;
  final VoidCallback? onTap;
  final VoidCallback? onAddToShortlist;
  final VoidCallback? onBuyNow;
  final String buyNowLabel;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(GtexSpacing.radiusLg),
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          padding: const EdgeInsets.all(GtexSpacing.md),
          decoration: BoxDecoration(
            gradient: GtexColors.panelGlow(
              accent: isSelected ? GtexColors.pitch : GtexColors.cyan,
            ),
            borderRadius: BorderRadius.circular(GtexSpacing.radiusLg),
            border: Border.all(
              color:
                  isSelected
                      ? GtexColors.pitch.withValues(alpha: 0.75)
                      : GtexColors.line.withValues(alpha: 0.72),
            ),
            boxShadow: <BoxShadow>[
              if (isSelected) GtexColors.glow(GtexColors.pitch, opacity: 0.18),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  _PlayerImage(imageUrl: imageUrl, name: name),
                  const SizedBox(width: GtexSpacing.sm),
                  if (gsiLabel != null) ...<Widget>[
                    _GsiPlate(label: gsiLabel!),
                    const SizedBox(width: GtexSpacing.sm),
                  ],
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          name,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(
                            context,
                          ).textTheme.titleMedium?.copyWith(
                            color: GtexColors.text,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                        const SizedBox(height: 3),
                        Text(
                          '$clubName - $nationality',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(
                            context,
                          ).textTheme.bodySmall?.copyWith(
                            color: GtexColors.textMuted,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: GtexSpacing.xs),
                        _PlayerCardChipRail(
                          chips: <Widget>[
                            GtexStatusChip(
                              label: position,
                              color: GtexColors.pitch,
                              compact: true,
                            ),
                            if (ratingLabel != null)
                              GtexStatusChip(
                                label: ratingLabel!,
                                color: GtexColors.gold,
                                compact: true,
                              ),
                            if (gsiTierLabel != null)
                              GtexStatusChip(
                                label: gsiTierLabel!,
                                color: GtexColors.cyan,
                                compact: true,
                              ),
                            if (gsiTrendLabel != null)
                              GtexStatusChip(
                                label: gsiTrendLabel!,
                                color: GtexColors.mint,
                                compact: true,
                              ),
                            if (ageLabel != null)
                              GtexStatusChip(
                                label: ageLabel!,
                                color: GtexColors.cyan,
                                compact: true,
                              ),
                            ...badges,
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: GtexSpacing.md),
              Row(
                children: <Widget>[
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'MARKET VALUE',
                          style: Theme.of(
                            context,
                          ).textTheme.labelSmall?.copyWith(
                            color: GtexColors.textMuted,
                            fontWeight: FontWeight.w900,
                            letterSpacing: 0.9,
                          ),
                        ),
                        Text(
                          priceLabel,
                          style: Theme.of(
                            context,
                          ).textTheme.titleMedium?.copyWith(
                            color: GtexColors.gold,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ],
                    ),
                  ),
                  if (onAddToShortlist != null)
                    IconButton.filledTonal(
                      tooltip: 'Add to shortlist',
                      onPressed: onAddToShortlist,
                      icon: const Icon(Icons.playlist_add),
                    ),
                  if (onBuyNow != null) ...<Widget>[
                    const SizedBox(width: GtexSpacing.xs),
                    GtexActionButton(
                      label: buyNowLabel,
                      onPressed: onBuyNow,
                      compact: true,
                      accent: GtexColors.gold,
                    ),
                  ],
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _PlayerCardChipRail extends StatelessWidget {
  const _PlayerCardChipRail({required this.chips});

  final List<Widget> chips;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 28,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemBuilder: (BuildContext context, int index) => chips[index],
        separatorBuilder:
            (BuildContext context, int index) => const SizedBox(width: 6),
        itemCount: chips.length,
      ),
    );
  }
}

class _PlayerImage extends StatelessWidget {
  const _PlayerImage({required this.imageUrl, required this.name});

  final String? imageUrl;
  final String name;

  @override
  Widget build(BuildContext context) {
    final String? trimmed = imageUrl?.trim();
    return Container(
      width: 68,
      height: 82,
      decoration: BoxDecoration(
        color: GtexColors.panelElevated,
        borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
        border: Border.all(color: GtexColors.line.withValues(alpha: 0.72)),
      ),
      clipBehavior: Clip.antiAlias,
      child:
          trimmed == null || trimmed.isEmpty
              ? _FallbackInitials(name: name)
              : Image.network(
                trimmed,
                fit: BoxFit.cover,
                gaplessPlayback: true,
                filterQuality: FilterQuality.medium,
                loadingBuilder: (
                  BuildContext context,
                  Widget child,
                  ImageChunkEvent? loadingProgress,
                ) {
                  if (loadingProgress == null) {
                    return child;
                  }
                  return const _PortraitLoadingPlate();
                },
                errorBuilder: (_, __, ___) => _FallbackInitials(name: name),
              ),
    );
  }
}

class _GsiPlate extends StatelessWidget {
  const _GsiPlate({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final String value =
        label.replaceFirst(RegExp(r'^GSI\s*', caseSensitive: false), '').trim();
    return Container(
      width: 54,
      padding: const EdgeInsets.symmetric(vertical: 8),
      decoration: BoxDecoration(
        color: GtexColors.gold.withValues(alpha: 0.16),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusSm),
        border: Border.all(color: GtexColors.gold.withValues(alpha: 0.62)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Text(
            value.isEmpty ? 'TBC' : value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: GtexColors.gold,
              fontSize: 18,
              fontWeight: FontWeight.w900,
              height: 1,
            ),
          ),
          const SizedBox(height: 3),
          const Text(
            'GSI',
            style: TextStyle(
              color: GtexColors.textMuted,
              fontSize: 9,
              fontWeight: FontWeight.w900,
              height: 1,
            ),
          ),
        ],
      ),
    );
  }
}

class _PortraitLoadingPlate extends StatelessWidget {
  const _PortraitLoadingPlate();

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            GtexColors.pitch.withValues(alpha: 0.16),
            GtexColors.panelStrong,
            GtexColors.cyan.withValues(alpha: 0.12),
          ],
        ),
      ),
      child: const Center(
        child: SizedBox(
          width: 18,
          height: 18,
          child: CircularProgressIndicator(strokeWidth: 2),
        ),
      ),
    );
  }
}

class _FallbackInitials extends StatelessWidget {
  const _FallbackInitials({required this.name});

  final String name;

  @override
  Widget build(BuildContext context) {
    final String initials =
        name
            .split(RegExp(r'\s+'))
            .where((String part) => part.isNotEmpty)
            .take(2)
            .map((String part) => part.characters.first.toUpperCase())
            .join();
    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            GtexColors.pitch.withValues(alpha: 0.2),
            GtexColors.cyan.withValues(alpha: 0.12),
          ],
        ),
      ),
      child: Center(
        child: Text(
          initials.isEmpty ? 'GT' : initials,
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
            color: GtexColors.text,
            fontWeight: FontWeight.w900,
          ),
        ),
      ),
    );
  }
}
