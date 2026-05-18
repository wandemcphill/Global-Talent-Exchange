import 'package:flutter/material.dart';

import '../components/gtex_action_button.dart';
import '../components/gtex_status_chip.dart';
import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';

enum GtexPlayerCardVariant {
  standard,
  nationalSeed,
  elite,
  legendary,
  holographic,
}

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
    this.countryCode,
    this.rarityLabel,
    this.marketHeatLabel,
    this.demandLabel,
    this.chemistryLinks = const <String>[],
    this.cardVariant = GtexPlayerCardVariant.standard,
    this.portraitStatus,
    this.portraitMissingReason,
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
  final String? countryCode;
  final String? rarityLabel;
  final String? marketHeatLabel;
  final String? demandLabel;
  final List<String> chemistryLinks;
  final GtexPlayerCardVariant cardVariant;
  final String? portraitStatus;
  final String? portraitMissingReason;
  final List<Widget> badges;
  final bool isSelected;
  final VoidCallback? onTap;
  final VoidCallback? onAddToShortlist;
  final VoidCallback? onBuyNow;
  final String buyNowLabel;

  @override
  Widget build(BuildContext context) {
    final Color accent = _variantAccent(cardVariant);
    final bool reduceMotion =
        MediaQuery.maybeOf(context)?.disableAnimations ?? false;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(GtexSpacing.radiusLg),
        onTap: onTap,
        child: AnimatedContainer(
          duration:
              reduceMotion ? Duration.zero : const Duration(milliseconds: 180),
          padding: const EdgeInsets.all(GtexSpacing.md),
          decoration: BoxDecoration(
            gradient: _cardGradient(accent),
            borderRadius: BorderRadius.circular(GtexSpacing.radiusLg),
            border: Border.all(
              color:
                  isSelected
                      ? GtexColors.pitch.withValues(alpha: 0.75)
                      : accent.withValues(
                        alpha: _variantBorderOpacity(cardVariant),
                      ),
            ),
            boxShadow: <BoxShadow>[
              if (!reduceMotion && isSelected)
                GtexColors.glow(GtexColors.pitch, opacity: 0.18),
              if (!reduceMotion &&
                  cardVariant != GtexPlayerCardVariant.standard)
                GtexColors.glow(accent, opacity: 0.12),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  _PlayerImage(
                    imageUrl: imageUrl,
                    name: name,
                    position: position,
                    countryCode: countryCode ?? nationality,
                    accent: accent,
                    portraitMissingReason: portraitMissingReason,
                  ),
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
                            if (rarityLabel != null)
                              GtexStatusChip(
                                label: rarityLabel!,
                                color: accent,
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
                            if (marketHeatLabel != null)
                              GtexStatusChip(
                                label: marketHeatLabel!,
                                color: GtexColors.gold,
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
              if (chemistryLinks.isNotEmpty || demandLabel != null) ...<Widget>[
                _PlayerCardSignalRail(
                  accent: accent,
                  demandLabel: demandLabel,
                  links: chemistryLinks,
                ),
                const SizedBox(height: GtexSpacing.sm),
              ],
              Row(
                children: <Widget>[
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          demandLabel == null ? 'MARKET VALUE' : 'LIVE VALUE',
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

Color _variantAccent(GtexPlayerCardVariant variant) {
  switch (variant) {
    case GtexPlayerCardVariant.nationalSeed:
      return GtexColors.mint;
    case GtexPlayerCardVariant.elite:
      return GtexColors.gold;
    case GtexPlayerCardVariant.legendary:
      return GtexColors.gold;
    case GtexPlayerCardVariant.holographic:
      return GtexColors.cyan;
    case GtexPlayerCardVariant.standard:
      return GtexColors.pitch;
  }
}

double _variantBorderOpacity(GtexPlayerCardVariant variant) {
  switch (variant) {
    case GtexPlayerCardVariant.standard:
      return 0.42;
    case GtexPlayerCardVariant.nationalSeed:
      return 0.62;
    case GtexPlayerCardVariant.elite:
    case GtexPlayerCardVariant.legendary:
    case GtexPlayerCardVariant.holographic:
      return 0.72;
  }
}

LinearGradient _cardGradient(Color accent) {
  return LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: <Color>[
      accent.withValues(alpha: 0.16),
      GtexColors.panelStrong.withValues(alpha: 0.96),
      GtexColors.stadiumBlack.withValues(alpha: 0.98),
    ],
  );
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

class _PlayerCardSignalRail extends StatelessWidget {
  const _PlayerCardSignalRail({
    required this.accent,
    required this.links,
    this.demandLabel,
  });

  final Color accent;
  final List<String> links;
  final String? demandLabel;

  @override
  Widget build(BuildContext context) {
    final List<String> signals = <String>[
      if (demandLabel != null && demandLabel!.trim().isNotEmpty) demandLabel!,
      ...links.where((String item) => item.trim().isNotEmpty).take(3),
    ];
    if (signals.isEmpty) {
      return const SizedBox.shrink();
    }
    return Wrap(
      spacing: 6,
      runSpacing: 6,
      children: signals
          .map(
            (String signal) => Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
              decoration: BoxDecoration(
                color: accent.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(GtexSpacing.radiusPill),
                border: Border.all(color: accent.withValues(alpha: 0.26)),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  Icon(Icons.hub_outlined, size: 12, color: accent),
                  const SizedBox(width: 4),
                  Text(
                    signal,
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: GtexColors.textSecondary,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ],
              ),
            ),
          )
          .toList(growable: false),
    );
  }
}

class _PlayerImage extends StatelessWidget {
  const _PlayerImage({
    required this.imageUrl,
    required this.name,
    required this.position,
    required this.countryCode,
    required this.accent,
    this.portraitMissingReason,
  });

  final String? imageUrl;
  final String name;
  final String position;
  final String countryCode;
  final Color accent;
  final String? portraitMissingReason;

  @override
  Widget build(BuildContext context) {
    final String? trimmed = imageUrl?.trim();
    return Container(
      width: 68,
      height: 82,
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
        border: Border.all(color: accent.withValues(alpha: 0.38)),
      ),
      clipBehavior: Clip.antiAlias,
      child:
          trimmed == null || trimmed.isEmpty
              ? _FootballSilhouette(
                name: name,
                position: position,
                countryCode: countryCode,
                accent: accent,
                reason: portraitMissingReason,
              )
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
                errorBuilder:
                    (_, __, ___) => _FootballSilhouette(
                      name: name,
                      position: position,
                      countryCode: countryCode,
                      accent: accent,
                      reason: portraitMissingReason,
                    ),
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

class _FootballSilhouette extends StatelessWidget {
  const _FootballSilhouette({
    required this.name,
    required this.position,
    required this.countryCode,
    required this.accent,
    this.reason,
  });

  final String name;
  final String position;
  final String countryCode;
  final Color accent;
  final String? reason;

  @override
  Widget build(BuildContext context) {
    final String initials =
        name
            .split(RegExp(r'\s+'))
            .where((String part) => part.isNotEmpty)
            .take(2)
            .map((String part) => part.characters.first.toUpperCase())
            .join();
    final String code =
        countryCode.trim().isEmpty ? 'GTEX' : countryCode.toUpperCase();
    return Tooltip(
      message:
          reason == null ? 'Portrait pending' : 'Portrait pending: $reason',
      child: DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: <Color>[
              accent.withValues(alpha: 0.22),
              GtexColors.panelStrong,
              GtexColors.stadiumBlack,
            ],
          ),
        ),
        child: Stack(
          fit: StackFit.expand,
          children: <Widget>[
            Positioned(
              left: 8,
              right: 8,
              bottom: 8,
              child: SizedBox(
                height: 36,
                child: CustomPaint(painter: _FootballCardPitchPainter(accent)),
              ),
            ),
            Center(
              child: Icon(
                Icons.person_rounded,
                size: 44,
                color: GtexColors.text.withValues(alpha: 0.88),
              ),
            ),
            Positioned(
              left: 6,
              top: 6,
              child: Text(
                position,
                style: const TextStyle(
                  color: GtexColors.text,
                  fontSize: 10,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
            Positioned(
              right: 6,
              top: 6,
              child: Text(
                code.length > 4 ? code.substring(0, 4) : code,
                style: TextStyle(
                  color: accent,
                  fontSize: 9,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
            Positioned(
              left: 0,
              right: 0,
              bottom: 8,
              child: Text(
                initials.isEmpty ? 'GT' : initials,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: GtexColors.text,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _FootballCardPitchPainter extends CustomPainter {
  const _FootballCardPitchPainter(this.accent);

  final Color accent;

  @override
  void paint(Canvas canvas, Size size) {
    final Paint line =
        Paint()
          ..color = accent.withValues(alpha: 0.25)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1;
    final Rect pitch = Offset.zero & size;
    canvas.drawRRect(
      RRect.fromRectAndRadius(pitch.deflate(1), const Radius.circular(4)),
      line,
    );
    canvas.drawLine(
      Offset(size.width / 2, 1),
      Offset(size.width / 2, size.height - 1),
      line,
    );
    canvas.drawCircle(
      Offset(size.width / 2, size.height / 2),
      size.height * 0.18,
      line,
    );
    canvas.drawArc(
      Rect.fromCenter(
        center: Offset(1, size.height / 2),
        width: size.height * 0.8,
        height: size.height * 0.8,
      ),
      -1.2,
      2.4,
      false,
      line,
    );
    canvas.drawArc(
      Rect.fromCenter(
        center: Offset(size.width - 1, size.height / 2),
        width: size.height * 0.8,
        height: size.height * 0.8,
      ),
      2.0,
      2.4,
      false,
      line,
    );
  }

  @override
  bool shouldRepaint(covariant _FootballCardPitchPainter oldDelegate) =>
      oldDelegate.accent != accent;
}
