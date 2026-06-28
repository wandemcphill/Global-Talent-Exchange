import 'package:flutter/material.dart';

import '../components/gtex_action_button.dart';
import '../components/gtex_live_status_chip.dart';
import '../components/gtex_status_chip.dart';
import '../components/gtex_value_display.dart';
import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';

enum GtexPlayerCardVariant {
  standard,
  nationalSeed,
  elite,
  legendary,
  holographic,
}

enum GtexPlayerCardScale { full, compact, thumbnail }

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
    this.scale = GtexPlayerCardScale.full,
    this.portraitStatus,
    this.portraitMissingReason,
    this.badges = const <Widget>[],
    this.formResults = const <String>[],
    this.valueDeltaLabel,
    this.valueState = GtexValueState.recent,
    this.ownerLabel,
    this.contractLabel,
    this.potentialLabel,
    this.heightLabel,
    this.footLabel,
    this.secondaryPositions = const <String>[],
    this.salaryLabel,
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
  final String? heightLabel;
  final String? footLabel;
  final List<String> secondaryPositions;
  final String? salaryLabel;
  final String? countryCode;
  final String? rarityLabel;
  final String? marketHeatLabel;
  final String? demandLabel;
  final List<String> chemistryLinks;
  final GtexPlayerCardVariant cardVariant;
  final GtexPlayerCardScale scale;
  final String? portraitStatus;
  final String? portraitMissingReason;
  final List<Widget> badges;
  final List<String> formResults;
  final String? valueDeltaLabel;
  final GtexValueState valueState;
  final String? ownerLabel;
  final String? contractLabel;
  final String? potentialLabel;
  final bool isSelected;
  final VoidCallback? onTap;
  final VoidCallback? onAddToShortlist;
  final VoidCallback? onBuyNow;
  final String buyNowLabel;

  bool get _isRegen => cardVariant != GtexPlayerCardVariant.standard;

  @override
  Widget build(BuildContext context) {
    final Color positionAccent = GtexColors.positionColor(position);
    final bool reduceMotion =
        MediaQuery.maybeOf(context)?.disableAnimations ?? false;
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool microLayout =
            (constraints.hasBoundedWidth && constraints.maxWidth < 128) ||
            (constraints.hasBoundedHeight && constraints.maxHeight < 92);
        final bool shortLayout =
            constraints.hasBoundedHeight && constraints.maxHeight < 360;
        final bool compact =
            microLayout || shortLayout || scale == GtexPlayerCardScale.compact;
        if (microLayout) {
          return _MicroPlayerCard(
            name: name,
            position: position,
            clubName: clubName,
            priceLabel: priceLabel,
            nationality: nationality,
            isRegen: _isRegen,
            positionAccent: positionAccent,
            isSelected: isSelected,
            reduceMotion: reduceMotion,
            valueState: valueState,
            imageUrl: imageUrl,
            onTap: onTap,
            valueDeltaLabel: valueDeltaLabel,
            ratingLabel: ratingLabel ?? gsiLabel,
          );
        }
        if (compact) {
          return _CompactPlayerCard(
            name: name,
            position: position,
            clubName: clubName,
            priceLabel: priceLabel,
            imageUrl: imageUrl,
            nationality: nationality,
            isRegen: _isRegen,
            positionAccent: positionAccent,
            isSelected: isSelected,
            reduceMotion: reduceMotion,
            onTap: onTap,
            valueDeltaLabel: valueDeltaLabel,
            valueState: valueState,
            ratingLabel: ratingLabel ?? gsiLabel,
            formResults: formResults,
          );
        }

        return _FullPlayerCard(
          name: name,
          position: position,
          clubName: clubName,
          nationality: nationality,
          priceLabel: priceLabel,
          imageUrl: imageUrl,
          gsiLabel: gsiLabel,
          gsiTierLabel: gsiTierLabel,
          gsiTrendLabel: gsiTrendLabel,
          ratingLabel: ratingLabel,
          ageLabel: ageLabel,
          countryCode: countryCode,
          rarityLabel: rarityLabel,
          marketHeatLabel: marketHeatLabel,
          demandLabel: demandLabel,
          chemistryLinks: chemistryLinks,
          cardVariant: cardVariant,
          portraitMissingReason: portraitMissingReason,
          badges: badges,
          formResults: formResults,
          valueDeltaLabel: valueDeltaLabel,
          valueState: valueState,
          ownerLabel: ownerLabel,
          contractLabel: contractLabel,
          potentialLabel: potentialLabel,
          heightLabel: heightLabel,
          footLabel: footLabel,
          secondaryPositions: secondaryPositions,
          salaryLabel: salaryLabel,
          isSelected: isSelected,
          onTap: onTap,
          onAddToShortlist: onAddToShortlist,
          onBuyNow: onBuyNow,
          buyNowLabel: buyNowLabel,
          positionAccent: positionAccent,
          isRegen: _isRegen,
          reduceMotion: reduceMotion,
        );
      },
    );
  }
}

class _FullPlayerCard extends StatelessWidget {
  const _FullPlayerCard({
    required this.name,
    required this.position,
    required this.clubName,
    required this.nationality,
    required this.priceLabel,
    required this.cardVariant,
    required this.formResults,
    required this.valueState,
    required this.badges,
    required this.positionAccent,
    required this.isRegen,
    required this.isSelected,
    required this.reduceMotion,
    required this.buyNowLabel,
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
    this.portraitMissingReason,
    this.valueDeltaLabel,
    this.ownerLabel,
    this.contractLabel,
    this.potentialLabel,
    this.heightLabel,
    this.footLabel,
    this.secondaryPositions = const <String>[],
    this.salaryLabel,
    this.onTap,
    this.onAddToShortlist,
    this.onBuyNow,
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
  final String? heightLabel;
  final String? footLabel;
  final List<String> secondaryPositions;
  final String? salaryLabel;
  final String? countryCode;
  final String? rarityLabel;
  final String? marketHeatLabel;
  final String? demandLabel;
  final List<String> chemistryLinks;
  final GtexPlayerCardVariant cardVariant;
  final String? portraitMissingReason;
  final List<Widget> badges;
  final List<String> formResults;
  final String? valueDeltaLabel;
  final GtexValueState valueState;
  final String? ownerLabel;
  final String? contractLabel;
  final String? potentialLabel;
  final Color positionAccent;
  final bool isRegen;
  final bool isSelected;
  final bool reduceMotion;
  final VoidCallback? onTap;
  final VoidCallback? onAddToShortlist;
  final VoidCallback? onBuyNow;
  final String buyNowLabel;

  @override
  Widget build(BuildContext context) {
    final Color provenanceColor =
        isRegen ? GtexColors.accentViolet : GtexColors.accentBlue;
    final String identityLabel = isRegen ? 'REGEN DNA' : 'REAL PLAYER';
    final String identitySupport =
        isRegen ? 'lineage profile' : 'scouting profile';
    final String? rarityChip =
        rarityLabel == null || rarityLabel!.trim().isEmpty
            ? null
            : rarityLabel!.trim();
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(GtexSpacing.radiusLg),
        onTap: onTap,
        child: AnimatedContainer(
          duration:
              reduceMotion ? Duration.zero : const Duration(milliseconds: 160),
          clipBehavior: Clip.antiAlias,
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: <Color>[
                GtexColors.surfaceRaised,
                GtexColors.surfaceBase,
                provenanceColor.withValues(alpha: isRegen ? 0.1 : 0.07),
              ],
            ),
            borderRadius: BorderRadius.circular(GtexSpacing.radiusLg),
            border: Border.all(
              color:
                  isSelected
                      ? GtexColors.accentPrimary
                      : GtexColors.surfaceBorder,
            ),
            boxShadow: <BoxShadow>[GtexColors.glow(Colors.black, opacity: 0.3)],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Container(height: 4, color: positionAccent),
              _IdentityBanner(
                label: identityLabel,
                support: identitySupport,
                icon: isRegen ? Icons.hub_rounded : Icons.badge_rounded,
                color: provenanceColor,
              ),
              Padding(
                padding: const EdgeInsets.all(GtexSpacing.md),
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
                          accent: provenanceColor,
                          isRegen: isRegen,
                          portraitMissingReason: portraitMissingReason,
                        ),
                        const SizedBox(width: GtexSpacing.sm),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Wrap(
                                spacing: 6,
                                runSpacing: 6,
                                children: <Widget>[
                                  GtexStatusChip(
                                    label: identityLabel,
                                    color: provenanceColor,
                                    compact: true,
                                  ),
                                  if (rarityChip != null)
                                    GtexStatusChip(
                                      label: rarityChip,
                                      color: provenanceColor,
                                      compact: true,
                                    ),
                                  if (marketHeatLabel != null)
                                    GtexStatusChip(
                                      label: marketHeatLabel!,
                                      color: GtexColors.accentAmber,
                                      compact: true,
                                    ),
                                  if (demandLabel != null)
                                    GtexLiveStatusChip(
                                      status: GtexLiveStatus.live,
                                      label: demandLabel!,
                                      compact: true,
                                    ),
                                  ...badges,
                                ],
                              ),
                              const SizedBox(height: GtexSpacing.sm),
                              _PositionRail(
                                primary: position,
                                secondary: secondaryPositions,
                                accent: positionAccent,
                              ),
                              Text(
                                name,
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                                style: Theme.of(
                                  context,
                                ).textTheme.titleLarge?.copyWith(
                                  color: GtexColors.textPrimary,
                                  fontFamily: 'DM Sans',
                                  fontWeight: FontWeight.w800,
                                  height: 1.1,
                                ),
                              ),
                              const SizedBox(height: GtexSpacing.xxs),
                              Text(
                                '$clubName / $nationality',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: Theme.of(
                                  context,
                                ).textTheme.bodySmall?.copyWith(
                                  color: GtexColors.textSecondary,
                                  fontFamily: 'DM Sans',
                                ),
                              ),
                              const SizedBox(height: GtexSpacing.xxs),
                              _BioRail(
                                heightLabel: heightLabel,
                                footLabel: footLabel,
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: GtexSpacing.md),
                    Row(
                      children: <Widget>[
                        if (gsiLabel != null) ...<Widget>[
                          _GsiPlate(label: gsiLabel!),
                          const SizedBox(width: GtexSpacing.xs),
                        ],
                        Expanded(
                          child: _StatGrid(
                            stats: <_StatItem>[
                              if (ratingLabel != null)
                                _StatItem('OVR', ratingLabel!),
                              if (potentialLabel != null)
                                _StatItem('POT', potentialLabel!),
                              if (ageLabel != null) _StatItem('AGE', ageLabel!),
                              if (gsiTierLabel != null)
                                _StatItem('TIER', gsiTierLabel!),
                              if (gsiTrendLabel != null)
                                _StatItem('TREND', gsiTrendLabel!),
                            ],
                          ),
                        ),
                      ],
                    ),
                    if (formResults.isNotEmpty) ...<Widget>[
                      const SizedBox(height: GtexSpacing.sm),
                      _FormRail(results: formResults),
                    ],
                    const SizedBox(height: GtexSpacing.md),
                    Divider(color: GtexColors.surfaceBorder, height: 1),
                    const SizedBox(height: GtexSpacing.md),
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: <Widget>[
                        Expanded(
                          child: GtexValueDisplay(
                            valueLabel: priceLabel,
                            deltaLabel: valueDeltaLabel,
                            state: valueState,
                            size: GtexValueDisplaySize.standard,
                            updatedLabel:
                                valueState == GtexValueState.live
                                    ? 'Updated live'
                                    : null,
                          ),
                        ),
                        if (onAddToShortlist != null)
                          IconButton.outlined(
                            tooltip: 'Add to watchlist',
                            onPressed: onAddToShortlist,
                            icon: const Icon(Icons.star_border_rounded),
                          ),
                        if (onBuyNow != null) ...<Widget>[
                          const SizedBox(width: GtexSpacing.xs),
                          GtexActionButton(
                            label: buyNowLabel,
                            onPressed: onBuyNow,
                            compact: true,
                            accent: GtexColors.accentPrimary,
                          ),
                        ],
                      ],
                    ),
                    if (_footerSignals.isNotEmpty) ...<Widget>[
                      const SizedBox(height: GtexSpacing.sm),
                      _SignalRail(
                        signals: _footerSignals,
                        accent: provenanceColor,
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  List<String> get _footerSignals {
    return <String>[
      if (salaryLabel != null && salaryLabel!.trim().isNotEmpty) salaryLabel!,
      if (ownerLabel != null && ownerLabel!.trim().isNotEmpty) ownerLabel!,
      if (contractLabel != null && contractLabel!.trim().isNotEmpty)
        contractLabel!,
      ...chemistryLinks.where((String item) => item.trim().isNotEmpty).take(2),
    ];
  }
}

class _PositionRail extends StatelessWidget {
  const _PositionRail({
    required this.primary,
    required this.secondary,
    required this.accent,
  });

  final String primary;
  final List<String> secondary;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final List<String> extras = secondary
        .where((String item) => item.trim().isNotEmpty)
        .take(3)
        .toList(growable: false);
    return Wrap(
      spacing: 4,
      runSpacing: 4,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: <Widget>[
        Text(
          primary.toUpperCase(),
          style: Theme.of(context).textTheme.labelLarge?.copyWith(
            color: accent,
            fontFamily: 'Barlow',
            fontWeight: FontWeight.w900,
            letterSpacing: 0.6,
          ),
        ),
        ...extras.map(
          (String pos) => Container(
            padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(GtexSpacing.radiusSm),
              border: Border.all(color: GtexColors.surfaceBorder),
            ),
            child: Text(
              pos.toUpperCase(),
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: GtexColors.textSecondary,
                fontFamily: 'Barlow',
                fontWeight: FontWeight.w800,
                letterSpacing: 0.4,
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _BioRail extends StatelessWidget {
  const _BioRail({this.heightLabel, this.footLabel});

  final String? heightLabel;
  final String? footLabel;

  @override
  Widget build(BuildContext context) {
    final String height =
        (heightLabel == null || heightLabel!.trim().isEmpty)
            ? '—'
            : heightLabel!.trim();
    final String foot =
        (footLabel == null || footLabel!.trim().isEmpty)
            ? '—'
            : footLabel!.trim();
    final TextStyle? labelStyle = Theme.of(context).textTheme.labelSmall
        ?.copyWith(
          color: GtexColors.textTertiary,
          fontFamily: 'Barlow',
          fontWeight: FontWeight.w800,
          letterSpacing: 0.4,
        );
    final TextStyle? valueStyle = Theme.of(context).textTheme.labelSmall
        ?.copyWith(
          color: GtexColors.textSecondary,
          fontFamily: 'DM Sans',
          fontWeight: FontWeight.w700,
        );
    return Row(
      children: <Widget>[
        Text('HEIGHT ', style: labelStyle),
        Text(height, style: valueStyle),
        const SizedBox(width: GtexSpacing.sm),
        Text('FOOT ', style: labelStyle),
        Flexible(
          child: Text(
            foot,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: valueStyle,
          ),
        ),
      ],
    );
  }
}

class _IdentityBanner extends StatelessWidget {
  const _IdentityBanner({
    required this.label,
    required this.support,
    required this.icon,
    required this.color,
  });

  final String label;
  final String support;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: GtexSpacing.md,
        vertical: GtexSpacing.xs,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        border: Border(
          bottom: BorderSide(color: color.withValues(alpha: 0.18)),
        ),
      ),
      child: Row(
        children: <Widget>[
          Icon(icon, size: 15, color: color),
          const SizedBox(width: GtexSpacing.xs),
          Text(
            label,
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: color,
              fontFamily: 'Barlow',
              fontWeight: FontWeight.w900,
              letterSpacing: 0.6,
            ),
          ),
          const SizedBox(width: GtexSpacing.xs),
          Expanded(
            child: Text(
              support.toUpperCase(),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: GtexColors.textSecondary,
                fontFamily: 'DM Sans',
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _CompactPlayerCard extends StatelessWidget {
  const _CompactPlayerCard({
    required this.name,
    required this.position,
    required this.clubName,
    required this.priceLabel,
    required this.nationality,
    required this.isRegen,
    required this.positionAccent,
    required this.isSelected,
    required this.reduceMotion,
    required this.valueState,
    required this.formResults,
    this.imageUrl,
    this.onTap,
    this.valueDeltaLabel,
    this.ratingLabel,
  });

  final String name;
  final String position;
  final String clubName;
  final String priceLabel;
  final String nationality;
  final bool isRegen;
  final Color positionAccent;
  final bool isSelected;
  final bool reduceMotion;
  final String? imageUrl;
  final VoidCallback? onTap;
  final String? valueDeltaLabel;
  final String? ratingLabel;
  final GtexValueState valueState;
  final List<String> formResults;

  @override
  Widget build(BuildContext context) {
    final Color provenanceColor =
        isRegen ? GtexColors.accentViolet : GtexColors.accentBlue;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
        onTap: onTap,
        child: AnimatedContainer(
          duration:
              reduceMotion ? Duration.zero : const Duration(milliseconds: 160),
          height: 76,
          decoration: BoxDecoration(
            color: GtexColors.surfaceRaised,
            borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
            border: Border.all(
              color:
                  isSelected
                      ? GtexColors.accentPrimary
                      : GtexColors.surfaceBorder,
            ),
          ),
          child: Row(
            children: <Widget>[
              Container(
                width: 4,
                decoration: BoxDecoration(
                  color: positionAccent,
                  borderRadius: const BorderRadius.only(
                    topLeft: Radius.circular(GtexSpacing.radiusMd),
                    bottomLeft: Radius.circular(GtexSpacing.radiusMd),
                  ),
                ),
              ),
              const SizedBox(width: GtexSpacing.xs),
              _PlayerImage(
                imageUrl: imageUrl,
                name: name,
                position: position,
                countryCode: nationality,
                accent: provenanceColor,
                isRegen: isRegen,
                compact: true,
              ),
              const SizedBox(width: GtexSpacing.sm),
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      isRegen ? 'REGEN DNA' : 'REAL PLAYER',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: provenanceColor,
                        fontFamily: 'Barlow',
                        fontWeight: FontWeight.w900,
                        letterSpacing: 0.5,
                      ),
                    ),
                    const SizedBox(height: 1),
                    Text(
                      name,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        color: GtexColors.textPrimary,
                        fontFamily: 'DM Sans',
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      '$position / $clubName',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: GtexColors.textSecondary,
                        fontFamily: 'DM Sans',
                      ),
                    ),
                    if (formResults.isNotEmpty) ...<Widget>[
                      const SizedBox(height: 4),
                      _FormRail(results: formResults, compact: true),
                    ],
                  ],
                ),
              ),
              if (ratingLabel != null) ...<Widget>[
                const SizedBox(width: GtexSpacing.xs),
                _RatingPill(label: ratingLabel!, accent: positionAccent),
              ],
              const SizedBox(width: GtexSpacing.xs),
              SizedBox(
                width: 92,
                child: GtexValueDisplay(
                  valueLabel: priceLabel,
                  deltaLabel: valueDeltaLabel,
                  state: valueState,
                  size: GtexValueDisplaySize.small,
                  showStateIndicator: false,
                ),
              ),
              const SizedBox(width: GtexSpacing.xs),
            ],
          ),
        ),
      ),
    );
  }
}

class _MicroPlayerCard extends StatelessWidget {
  const _MicroPlayerCard({
    required this.name,
    required this.position,
    required this.clubName,
    required this.priceLabel,
    required this.nationality,
    required this.isRegen,
    required this.positionAccent,
    required this.isSelected,
    required this.reduceMotion,
    required this.valueState,
    this.imageUrl,
    this.onTap,
    this.valueDeltaLabel,
    this.ratingLabel,
  });

  final String name;
  final String position;
  final String clubName;
  final String priceLabel;
  final String nationality;
  final bool isRegen;
  final Color positionAccent;
  final bool isSelected;
  final bool reduceMotion;
  final GtexValueState valueState;
  final String? imageUrl;
  final VoidCallback? onTap;
  final String? valueDeltaLabel;
  final String? ratingLabel;

  @override
  Widget build(BuildContext context) {
    final Color provenanceColor =
        isRegen ? GtexColors.accentViolet : GtexColors.accentBlue;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
        onTap: onTap,
        child: LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            final double width =
                constraints.hasBoundedWidth && constraints.maxWidth.isFinite
                    ? constraints.maxWidth
                    : 180;
            final double height =
                constraints.hasBoundedHeight && constraints.maxHeight.isFinite
                    ? constraints.maxHeight
                    : 58;

            return ClipRRect(
              borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
              child: AnimatedContainer(
                duration:
                    reduceMotion
                        ? Duration.zero
                        : const Duration(milliseconds: 160),
                width: width,
                height: height,
                decoration: BoxDecoration(
                  color: GtexColors.surfaceRaised,
                  border: Border.all(
                    color:
                        isSelected
                            ? GtexColors.accentPrimary
                            : GtexColors.surfaceBorder,
                  ),
                ),
                child: FittedBox(
                  fit: BoxFit.scaleDown,
                  alignment: Alignment.centerLeft,
                  child: SizedBox(
                    width: 190,
                    height: 58,
                    child: Row(
                      children: <Widget>[
                        Container(width: 4, color: positionAccent),
                        const SizedBox(width: GtexSpacing.xs),
                        _PlayerImage(
                          imageUrl: imageUrl,
                          name: name,
                          position: position,
                          countryCode: nationality,
                          accent: provenanceColor,
                          isRegen: isRegen,
                          compact: true,
                        ),
                        const SizedBox(width: GtexSpacing.sm),
                        Expanded(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Text(
                                name,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: Theme.of(
                                  context,
                                ).textTheme.labelLarge?.copyWith(
                                  color: GtexColors.textPrimary,
                                  fontFamily: 'DM Sans',
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                '$position / $clubName',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: Theme.of(
                                  context,
                                ).textTheme.labelSmall?.copyWith(
                                  color: GtexColors.textSecondary,
                                  fontFamily: 'DM Sans',
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: GtexSpacing.xs),
                        SizedBox(
                          width: 64,
                          child: GtexValueDisplay(
                            valueLabel: ratingLabel ?? priceLabel,
                            deltaLabel: valueDeltaLabel,
                            state: valueState,
                            size: GtexValueDisplaySize.small,
                            showStateIndicator: false,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            );
          },
        ),
      ),
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
    required this.isRegen,
    this.portraitMissingReason,
    this.compact = false,
  });

  final String? imageUrl;
  final String name;
  final String position;
  final String countryCode;
  final Color accent;
  final bool isRegen;
  final String? portraitMissingReason;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final String? trimmed = imageUrl?.trim();
    final double size = compact ? 48 : 96;
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: GtexColors.surfaceOverlay,
        shape: BoxShape.circle,
        border: Border.all(color: accent.withValues(alpha: 0.5)),
      ),
      clipBehavior: Clip.antiAlias,
      child:
          trimmed == null || trimmed.isEmpty
              ? _PlayerAvatarFallback(
                name: name,
                position: position,
                countryCode: countryCode,
                accent: accent,
                isRegen: isRegen,
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
                    (_, __, ___) => _PlayerAvatarFallback(
                      name: name,
                      position: position,
                      countryCode: countryCode,
                      accent: accent,
                      isRegen: isRegen,
                      reason: portraitMissingReason,
                    ),
              ),
    );
  }
}

class _PlayerAvatarFallback extends StatelessWidget {
  const _PlayerAvatarFallback({
    required this.name,
    required this.position,
    required this.countryCode,
    required this.accent,
    required this.isRegen,
    this.reason,
  });

  final String name;
  final String position;
  final String countryCode;
  final Color accent;
  final bool isRegen;
  final String? reason;

  @override
  Widget build(BuildContext context) {
    final String code =
        countryCode.trim().isEmpty ? 'GTEX' : countryCode.toUpperCase();
    return Tooltip(
      message:
          reason == null
              ? 'Portrait unavailable'
              : 'Portrait unavailable: $reason',
      child: Stack(
        fit: StackFit.expand,
        children: <Widget>[
          CustomPaint(
            painter: _FmSilhouettePainter(accent: accent, regenTint: isRegen),
          ),
          Positioned(
            left: 8,
            top: 8,
            child: Text(
              position.toUpperCase(),
              style: TextStyle(
                color: accent,
                fontFamily: 'Barlow',
                fontSize: 10,
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
          Positioned(
            right: 8,
            top: 8,
            child: Text(
              code.length > 4 ? code.substring(0, 4) : code,
              style: const TextStyle(
                color: GtexColors.textSecondary,
                fontSize: 9,
                fontWeight: FontWeight.w800,
              ),
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
    return const DecoratedBox(
      decoration: BoxDecoration(color: GtexColors.surfaceHover),
      child: Center(
        child: SizedBox(
          width: 18,
          height: 18,
          child: CircularProgressIndicator(strokeWidth: 2),
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
      width: 58,
      padding: const EdgeInsets.symmetric(vertical: 8),
      decoration: BoxDecoration(
        color: GtexColors.surfaceOverlay,
        borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
        border: Border.all(
          color: GtexColors.accentAmber.withValues(alpha: 0.55),
        ),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Text(
            value.isEmpty ? 'TBC' : value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: GtexColors.accentAmber,
              fontFamily: 'JetBrains Mono',
              fontSize: 18,
              fontWeight: FontWeight.w900,
              height: 1,
            ),
          ),
          const SizedBox(height: 3),
          const Text(
            'GSI',
            style: TextStyle(
              color: GtexColors.textSecondary,
              fontFamily: 'Barlow',
              fontSize: 9,
              fontWeight: FontWeight.w900,
              height: 1,
              letterSpacing: 0.4,
            ),
          ),
        ],
      ),
    );
  }
}

class _StatItem {
  const _StatItem(this.label, this.value);

  final String label;
  final String value;
}

class _StatGrid extends StatelessWidget {
  const _StatGrid({required this.stats});

  final List<_StatItem> stats;

  @override
  Widget build(BuildContext context) {
    if (stats.isEmpty) {
      return const SizedBox.shrink();
    }
    return Wrap(
      spacing: GtexSpacing.xs,
      runSpacing: GtexSpacing.xs,
      children: stats
          .take(5)
          .map((_StatItem stat) {
            return Container(
              width: 66,
              padding: const EdgeInsets.symmetric(
                horizontal: GtexSpacing.xs,
                vertical: GtexSpacing.xs,
              ),
              decoration: BoxDecoration(
                color: GtexColors.surfaceOverlay,
                borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
                border: Border.all(color: GtexColors.surfaceBorder),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    stat.label.toUpperCase(),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: GtexColors.textSecondary,
                      fontFamily: 'Barlow',
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0.4,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    stat.value,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      color: GtexColors.textPrimary,
                      fontFamily: 'JetBrains Mono',
                      fontWeight: FontWeight.w900,
                      height: 1,
                    ),
                  ),
                ],
              ),
            );
          })
          .toList(growable: false),
    );
  }
}

class _FormRail extends StatelessWidget {
  const _FormRail({required this.results, this.compact = false});

  final List<String> results;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: results
          .take(5)
          .map((String result) {
            final String label =
                result.trim().isEmpty
                    ? '-'
                    : result.trim().substring(0, 1).toUpperCase();
            return Container(
              width: compact ? 18 : 24,
              height: compact ? 18 : 22,
              margin: const EdgeInsets.only(right: 4),
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: _formColor(label).withValues(alpha: 0.14),
                borderRadius: BorderRadius.circular(GtexSpacing.radiusSm),
                border: Border.all(
                  color: _formColor(label).withValues(alpha: 0.48),
                ),
              ),
              child: Text(
                label,
                style: TextStyle(
                  color: _formColor(label),
                  fontSize: compact ? 10 : 11,
                  fontFamily: 'JetBrains Mono',
                  fontWeight: FontWeight.w900,
                ),
              ),
            );
          })
          .toList(growable: false),
    );
  }

  Color _formColor(String label) {
    return switch (label) {
      'W' => GtexColors.accentPrimary,
      'D' => GtexColors.accentAmber,
      'L' => GtexColors.accentRed,
      _ => GtexColors.textTertiary,
    };
  }
}

class _SignalRail extends StatelessWidget {
  const _SignalRail({required this.signals, required this.accent});

  final List<String> signals;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 6,
      runSpacing: 6,
      children: signals
          .map((String signal) {
            return Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
              decoration: BoxDecoration(
                color: accent.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(GtexSpacing.radiusSm),
                border: Border.all(color: accent.withValues(alpha: 0.22)),
              ),
              child: Text(
                signal,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: GtexColors.textSecondary,
                  fontFamily: 'DM Sans',
                  fontWeight: FontWeight.w700,
                ),
              ),
            );
          })
          .toList(growable: false),
    );
  }
}

class _RatingPill extends StatelessWidget {
  const _RatingPill({required this.label, required this.accent});

  final String label;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 44,
      padding: const EdgeInsets.symmetric(vertical: 6),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
        border: Border.all(color: accent.withValues(alpha: 0.38)),
      ),
      alignment: Alignment.center,
      child: Text(
        label.replaceFirst(RegExp(r'^GSI\s*', caseSensitive: false), ''),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: TextStyle(
          color: accent,
          fontFamily: 'JetBrains Mono',
          fontWeight: FontWeight.w900,
          fontSize: 13,
        ),
      ),
    );
  }
}

class _FmSilhouettePainter extends CustomPainter {
  const _FmSilhouettePainter({required this.accent, required this.regenTint});

  final Color accent;
  final bool regenTint;

  @override
  void paint(Canvas canvas, Size size) {
    final double w = size.width;
    final double h = size.height;
    canvas.drawRect(
      Offset.zero & size,
      Paint()..color = GtexColors.surfaceOverlay,
    );

    const Color base = Color(0xFF8A95A1);
    final Color silhouette =
        regenTint ? (Color.lerp(base, accent, 0.35) ?? base) : base;
    final Paint fill = Paint()
      ..color = silhouette
      ..isAntiAlias = true;

    final Path body =
        Path()
          ..moveTo(w * 0.10, h)
          ..cubicTo(w * 0.12, h * 0.70, w * 0.30, h * 0.62, w * 0.50, h * 0.62)
          ..cubicTo(w * 0.70, h * 0.62, w * 0.88, h * 0.70, w * 0.90, h)
          ..close();
    canvas.drawPath(body, fill);
    canvas.drawCircle(Offset(w * 0.5, h * 0.36), w * 0.19, fill);
  }

  @override
  bool shouldRepaint(covariant _FmSilhouettePainter oldDelegate) =>
      oldDelegate.accent != accent || oldDelegate.regenTint != regenTint;
}
