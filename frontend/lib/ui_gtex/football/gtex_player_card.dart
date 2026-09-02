import 'package:flutter/material.dart';

import '../components/gtex_action_button.dart';
import '../components/gtex_live_status_chip.dart';
import '../components/gtex_status_chip.dart';
import '../components/gtex_value_display.dart';
import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';
import 'gtex_player_portrait.dart';

enum GtexPlayerCardVariant {
  standard,
  nationalSeed,
  elite,
  legendary,
  holographic,
}

enum GtexPlayerCardScale { full, compact, thumbnail }

/// Below this width there is only room for a name, a rating and a price.
const double _microMaxWidth = 128;

/// The compact browse row's own height. Anything shorter cannot hold it.
const double _compactMinHeight = 76;

/// The full poster card stacks a portrait, an identity block, a stat grid,
/// a value row and a signal rail. It needs real space in both axes; asked
/// to render in a browse cell it would simply clip.
const double _fullCardMinHeight = 360;
const double _fullCardMinWidth = 280;

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
    this.availabilityLabel,
    this.interestLabel,
    this.isOwned = false,
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

  /// How the player can be acquired ("Transfer eligible", "Loan"...). Shown
  /// in the browse row's meta line once there is width for it.
  final String? availabilityLabel;

  /// Market attention, e.g. "Watched 41". Only ever passed when the backend
  /// actually reported an interest score.
  final String? interestLabel;

  /// True when the signed-in user already holds this player. The browse row
  /// marks it so an owned asset is never mistaken for a target.
  final bool isOwned;
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
        // Layout is chosen from what the card can actually draw in, and
        // width is the axis that decides how much of a footballer fits.
        // Height only rules out a layout it physically cannot contain: the
        // micro row needs 76px, the full poster card needs a portrait, a
        // stat grid and a footer.
        final bool microLayout =
            (constraints.hasBoundedWidth &&
                constraints.maxWidth < _microMaxWidth) ||
            (constraints.hasBoundedHeight &&
                constraints.maxHeight < _compactMinHeight);
        final bool tooShortForFullCard =
            constraints.hasBoundedHeight &&
            constraints.maxHeight < _fullCardMinHeight;
        final bool tooNarrowForFullCard =
            constraints.hasBoundedWidth &&
            constraints.maxWidth < _fullCardMinWidth;
        final bool compact =
            microLayout ||
            tooShortForFullCard ||
            tooNarrowForFullCard ||
            scale == GtexPlayerCardScale.compact;
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
            gsiLabel: gsiLabel,
            gsiTierLabel: gsiTierLabel,
            ageLabel: ageLabel,
            availabilityLabel: availabilityLabel,
            interestLabel: interestLabel,
            isOwned: isOwned,
            formResults: formResults,
            onAddToShortlist: onAddToShortlist,
            onBuyNow: onBuyNow,
            buyNowLabel: buyNowLabel,
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
    final TextStyle? labelStyle = Theme.of(
      context,
    ).textTheme.labelSmall?.copyWith(
      color: GtexColors.textTertiary,
      fontFamily: 'Barlow',
      fontWeight: FontWeight.w800,
      letterSpacing: 0.4,
    );
    final TextStyle? valueStyle = Theme.of(
      context,
    ).textTheme.labelSmall?.copyWith(
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
    this.gsiLabel,
    this.gsiTierLabel,
    this.ageLabel,
    this.availabilityLabel,
    this.interestLabel,
    this.isOwned = false,
    this.onAddToShortlist,
    this.onBuyNow,
    this.buyNowLabel = 'Buy now',
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
  final String? gsiLabel;
  final String? gsiTierLabel;
  final String? ageLabel;
  final String? availabilityLabel;
  final String? interestLabel;
  final bool isOwned;
  final GtexValueState valueState;
  final List<String> formResults;
  final VoidCallback? onAddToShortlist;
  final VoidCallback? onBuyNow;
  final String buyNowLabel;

  /// Row height of the browse card. Anything taller than this plus
  /// [_actionBarHeight] has room for the primary actions.
  static const double _rowHeight = 76;
  static const double _actionBarHeight = 48;

  /// Width at which the row can carry a meta line under the club without
  /// crowding the price column, and the widths at which each further piece
  /// of market intelligence earns its place.
  static const double _metaMinWidth = 340;
  static const double _gsiMinWidth = 440;
  static const double _signalsMinWidth = 560;

  /// The market facts this row can show, filtered to what the backend
  /// actually returned. Nothing here is synthesised: an absent value is
  /// simply not in the line.
  List<String> _metaFacts({required bool withGsi, required bool withSignals}) {
    return <String>[
      if (ageLabel != null && ageLabel!.trim().isNotEmpty) ageLabel!.trim(),
      if (withGsi && gsiLabel != null && gsiLabel!.trim().isNotEmpty)
        gsiLabel!.trim(),
      if (withSignals &&
          gsiTierLabel != null &&
          gsiTierLabel!.trim().isNotEmpty)
        gsiTierLabel!.trim(),
      if (availabilityLabel != null && availabilityLabel!.trim().isNotEmpty)
        availabilityLabel!.trim(),
      if (withSignals &&
          interestLabel != null &&
          interestLabel!.trim().isNotEmpty)
        interestLabel!.trim(),
    ];
  }

  @override
  Widget build(BuildContext context) {
    final bool hasActions = onBuyNow != null || onAddToShortlist != null;
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        // In a browse grid the cell is much taller than the row, so the
        // primary actions fit underneath. In a list the height is either
        // unbounded or row-sized, and the card stays a plain row.
        final bool showActionBar =
            hasActions &&
            constraints.hasBoundedHeight &&
            constraints.maxHeight >= _rowHeight + _actionBarHeight;
        final double width =
            constraints.hasBoundedWidth ? constraints.maxWidth : _metaMinWidth;
        return _buildCard(
          context,
          showActionBar,
          hasRoomForMeta: width >= _metaMinWidth,
          hasRoomForGsi: width >= _gsiMinWidth,
          hasRoomForSignals: width >= _signalsMinWidth,
        );
      },
    );
  }

  Widget _buildCard(
    BuildContext context,
    bool showActionBar, {
    required bool hasRoomForMeta,
    required bool hasRoomForGsi,
    required bool hasRoomForSignals,
  }) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
        onTap: onTap,
        child: AnimatedContainer(
          duration:
              reduceMotion ? Duration.zero : const Duration(milliseconds: 160),
          height: showActionBar ? null : _rowHeight,
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
          child:
              showActionBar
                  ? Column(
                    mainAxisSize: MainAxisSize.min,
                    mainAxisAlignment: MainAxisAlignment.start,
                    children: <Widget>[
                      ConstrainedBox(
                        constraints: const BoxConstraints(
                          minHeight: _rowHeight,
                        ),
                        child: _row(
                          context,
                          flushBottom: true,
                          hasRoomForMeta: hasRoomForMeta,
                          hasRoomForGsi: hasRoomForGsi,
                          hasRoomForSignals: hasRoomForSignals,
                        ),
                      ),
                      _CompactCardActionBar(
                        accent: positionAccent,
                        buyNowLabel: buyNowLabel,
                        playerName: name,
                        onAddToShortlist: onAddToShortlist,
                        onBuyNow: onBuyNow,
                      ),
                    ],
                  )
                  : _row(
                    context,
                    flushBottom: showActionBar,
                    hasRoomForMeta: hasRoomForMeta,
                    hasRoomForGsi: hasRoomForGsi,
                    hasRoomForSignals: hasRoomForSignals,
                  ),
        ),
      ),
    );
  }

  Widget _row(
    BuildContext context, {
    bool flushBottom = false,
    bool hasRoomForMeta = false,
    bool hasRoomForGsi = false,
    bool hasRoomForSignals = false,
  }) {
    final Color provenanceColor =
        isRegen ? GtexColors.accentViolet : GtexColors.accentBlue;
    final List<String> metaFacts =
        hasRoomForMeta
            ? _metaFacts(withGsi: hasRoomForGsi, withSignals: hasRoomForSignals)
            : const <String>[];
    return Row(
      children: <Widget>[
        Container(
          width: 4,
          decoration: BoxDecoration(
            color: positionAccent,
            borderRadius: BorderRadius.only(
              topLeft: const Radius.circular(GtexSpacing.radiusMd),
              bottomLeft:
                  flushBottom
                      ? Radius.zero
                      : const Radius.circular(GtexSpacing.radiusMd),
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
          compact: true,
        ),
        const SizedBox(width: GtexSpacing.sm),
        Expanded(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Flexible(
                    child: Text(
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
                  ),
                  if (isOwned) ...<Widget>[
                    const SizedBox(width: GtexSpacing.xs),
                    Text(
                      'OWNED',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: GtexColors.accentAmber,
                        fontFamily: 'Barlow',
                        fontWeight: FontWeight.w900,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ],
                ],
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
              if (metaFacts.isNotEmpty) ...<Widget>[
                const SizedBox(height: 2),
                Text(
                  metaFacts.join('  -  '),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: GtexColors.textTertiary,
                    fontFamily: 'DM Sans',
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
              if (formResults.isNotEmpty && hasRoomForMeta) ...<Widget>[
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
        ConstrainedBox(
          constraints: const BoxConstraints(minWidth: 84, maxWidth: 110),
          child: FittedBox(
            fit: BoxFit.scaleDown,
            alignment: Alignment.centerRight,
            child: GtexValueDisplay(
              valueLabel: priceLabel,
              deltaLabel: valueDeltaLabel,
              state: valueState,
              size: GtexValueDisplaySize.small,
              showStateIndicator: false,
            ),
          ),
        ),
        const SizedBox(width: GtexSpacing.xs),
      ],
    );
  }
}

/// Primary browse actions for [_CompactPlayerCard]. Only rendered when the
/// card has room for them, and only for the callbacks that were supplied —
/// an action that has no flow behind it is never drawn.
class _CompactCardActionBar extends StatelessWidget {
  const _CompactCardActionBar({
    required this.accent,
    required this.buyNowLabel,
    required this.playerName,
    this.onAddToShortlist,
    this.onBuyNow,
  });

  final Color accent;
  final String buyNowLabel;
  final String playerName;
  final VoidCallback? onAddToShortlist;
  final VoidCallback? onBuyNow;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: _CompactPlayerCard._actionBarHeight,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          GtexSpacing.sm,
          0,
          GtexSpacing.sm,
          GtexSpacing.sm,
        ),
        child: Row(
          children: <Widget>[
            if (onAddToShortlist != null)
              Expanded(
                child: Semantics(
                  button: true,
                  label: 'Add $playerName to shortlist',
                  child: OutlinedButton.icon(
                    onPressed: onAddToShortlist,
                    style: OutlinedButton.styleFrom(
                      minimumSize: const Size(0, 36),
                      tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      padding: const EdgeInsets.symmetric(
                        horizontal: GtexSpacing.xs,
                      ),
                      foregroundColor: GtexColors.textSecondary,
                      side: const BorderSide(color: GtexColors.surfaceBorder),
                    ),
                    icon: const Icon(Icons.bookmark_add_outlined, size: 16),
                    label: const Text(
                      'Shortlist',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ),
              ),
            if (onAddToShortlist != null && onBuyNow != null)
              const SizedBox(width: GtexSpacing.xs),
            if (onBuyNow != null)
              Expanded(
                child: Semantics(
                  button: true,
                  label: '$buyNowLabel: $playerName',
                  child: FilledButton(
                    onPressed: onBuyNow,
                    style: FilledButton.styleFrom(
                      minimumSize: const Size(0, 36),
                      tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      padding: const EdgeInsets.symmetric(
                        horizontal: GtexSpacing.xs,
                      ),
                      backgroundColor: accent,
                      foregroundColor: GtexColors.textInverse,
                    ),
                    child: Text(
                      buyNowLabel,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ),
              ),
          ],
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

/// A footballer's portrait on the card.
///
/// The fallback used to be `_FmSilhouettePainter`: a drawn head-and-
/// shoulders. GTEX shows a real face or no face - a generic silhouette
/// reads as a stand-in for a person who does not exist, which is exactly
/// the impression an ownership product cannot afford - so the shared
/// `GtexPlayerPortrait` plate stands in instead. It carries the same facts
/// the silhouette was overlaid with: the position and the country code.
class _PlayerImage extends StatelessWidget {
  const _PlayerImage({
    required this.imageUrl,
    required this.name,
    required this.position,
    required this.countryCode,
    required this.accent,
    this.portraitMissingReason,
    this.compact = false,
  });

  final String? imageUrl;
  final String name;
  final String position;
  final String countryCode;
  final Color accent;
  final String? portraitMissingReason;
  final bool compact;

  /// The country as a badge token. Callers pass either an ISO code or a
  /// full country name, so anything longer than a code is clipped the way
  /// the old overlay clipped it.
  String? get _shortCountryCode {
    final String code = countryCode.trim().toUpperCase();
    if (code.isEmpty) {
      return null;
    }
    return code.length > 3 ? code.substring(0, 3) : code;
  }

  @override
  Widget build(BuildContext context) {
    final String? trimmed = imageUrl?.trim();
    final bool hasPhotograph = trimmed != null && trimmed.isNotEmpty;
    final double size = compact ? 48 : 96;
    final Widget portrait = Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: GtexColors.surfaceOverlay,
        shape: BoxShape.circle,
        border: Border.all(color: accent.withValues(alpha: 0.5)),
      ),
      clipBehavior: Clip.antiAlias,
      child: GtexPlayerPortrait(
        name: name,
        imageUrl: trimmed,
        // A 48px circle has room for initials and nothing else, and the row
        // beside it already names the position and the club. Callers also
        // pass a full nationality here as often as a code, so it is clipped
        // to a badge-sized token rather than ellipsised mid-country.
        position: compact ? null : position,
        nationalityCode: compact ? null : _shortCountryCode,
        accent: accent,
        size: size,
        borderRadius: size / 2,
      ),
    );
    if (hasPhotograph) {
      return portrait;
    }
    return Tooltip(
      message:
          portraitMissingReason == null
              ? 'Portrait unavailable'
              : 'Portrait unavailable: $portraitMissingReason',
      child: portrait,
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
      constraints: const BoxConstraints(minWidth: 58),
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 8),
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
          FittedBox(
            fit: BoxFit.scaleDown,
            child: Text(
              value.isEmpty ? 'TBC' : value,
              maxLines: 1,
              style: const TextStyle(
                color: GtexColors.accentAmber,
                fontFamily: 'JetBrains Mono',
                fontSize: 18,
                fontWeight: FontWeight.w900,
                height: 1,
              ),
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
    final List<_StatItem> shown = stats.take(5).toList(growable: false);
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        // Fit as many columns as the available width allows (min 56px/cell)
        // so the grid never overflows a narrow detail panel.
        final int columns = (constraints.maxWidth / 66).floor().clamp(
          1,
          shown.length,
        );
        return Wrap(
          spacing: GtexSpacing.xs,
          runSpacing: GtexSpacing.xs,
          children: shown
              .map((_StatItem stat) {
                final double cellWidth =
                    (constraints.maxWidth - GtexSpacing.xs * (columns - 1)) /
                    columns;
                return Container(
                  width: cellWidth.clamp(56, double.infinity),
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
                    mainAxisSize: MainAxisSize.min,
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
      },
    );
  }
}

class _FormRail extends StatelessWidget {
  const _FormRail({required this.results, this.compact = false});

  final List<String> results;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final double chipWidth = (compact ? 18 : 24) + 4;
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        // Narrow cards cannot fit a full five-match rail. Drop the oldest
        // results rather than overflowing the row.
        final int fits =
            constraints.hasBoundedWidth
                ? (constraints.maxWidth / chipWidth).floor()
                : 5;
        return _buildRail(context, fits.clamp(0, 5));
      },
    );
  }

  Widget _buildRail(BuildContext context, int maxResults) {
    if (maxResults <= 0) {
      return const SizedBox.shrink();
    }
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: results
          .take(maxResults)
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

/// The card's rating box: which rating it is, and the figure.
///
/// It used to strip a leading `GSI ` and draw whatever remained in a fixed
/// 44px box with an ellipsis. Every other caller labels its rating
/// differently - the market sends `Form 7.4`, the regen world `OVR 82` - so
/// the box rendered `Form…` and the card's primary rating carried no number
/// at any width. The caption and the figure are now separate lines, and
/// neither is allowed to truncate.
class _RatingPill extends StatelessWidget {
  const _RatingPill({required this.label, required this.accent});

  final String label;
  final Color accent;

  /// A leading word naming the rating, e.g. `GSI 96`, `Form 7.4`, `OVR 82`.
  static final RegExp _captioned = RegExp(
    r'^([A-Za-z]{2,6})\s+(.+)$',
    caseSensitive: false,
  );

  @override
  Widget build(BuildContext context) {
    final String trimmed = label.trim();
    final RegExpMatch? match = _captioned.firstMatch(trimmed);
    final String? caption = match?.group(1)?.toUpperCase();
    // Only the leading figure belongs in a pill: `GSI 96 - Elite GSI` is a
    // tier label with a score in front of it, and the tier already has its
    // own place in the row's meta line.
    final String value = (match?.group(2) ?? trimmed).split(' - ').first.trim();
    return Container(
      constraints: const BoxConstraints(minWidth: 44),
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 5),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
        border: Border.all(color: accent.withValues(alpha: 0.38)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: <Widget>[
          if (caption != null)
            FittedBox(
              fit: BoxFit.scaleDown,
              child: Text(
                caption,
                maxLines: 1,
                style: TextStyle(
                  color: accent.withValues(alpha: 0.78),
                  fontFamily: 'Barlow',
                  fontWeight: FontWeight.w900,
                  fontSize: 8,
                  letterSpacing: 0.4,
                  height: 1.1,
                ),
              ),
            ),
          FittedBox(
            fit: BoxFit.scaleDown,
            child: Text(
              value.isEmpty ? '—' : value,
              maxLines: 1,
              style: TextStyle(
                color: accent,
                fontFamily: 'JetBrains Mono',
                fontWeight: FontWeight.w900,
                fontSize: 13,
                height: 1.15,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
