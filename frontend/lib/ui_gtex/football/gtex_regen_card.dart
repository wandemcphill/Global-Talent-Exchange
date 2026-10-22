import 'package:flutter/material.dart';

import '../components/gtex_status_chip.dart';
import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';
import 'gtex_pitch_marks.dart';
import 'gtex_regen_portrait.dart';

class GtexRegenCard extends StatelessWidget {
  const GtexRegenCard({
    super.key,
    required this.name,
    required this.archetype,
    required this.nationality,
    required this.potentialLabel,
    this.ageLabel,
    this.storyLine,
    this.portraitUrl,
    this.portraitSeed,
    this.position = 'CM',
    this.countryCode,
    this.gsiLabel,
    this.gsiTierLabel,
    this.ratingLabel,
    this.valueLabel,
    this.generationLabel,
    this.traitLabels = const <String>[],
    this.lineageLabel,
    this.awardLabels = const <String>[],
    this.jerseyColor,
    this.onTap,
    this.isSelected = false,
  });

  final String name;
  final String archetype;
  final String nationality;
  final String potentialLabel;
  final String? ageLabel;
  final String? storyLine;
  final String? portraitUrl;
  final String? portraitSeed;
  final String position;
  final String? countryCode;
  final String? gsiLabel;
  final String? gsiTierLabel;
  final String? ratingLabel;
  final String? valueLabel;
  final String? generationLabel;
  final List<String> traitLabels;
  final String? lineageLabel;
  final List<String> awardLabels;
  final Color? jerseyColor;
  final VoidCallback? onTap;
  final bool isSelected;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final String seed =
        (portraitSeed ?? name).trim().isEmpty ? name : portraitSeed ?? name;
    final String resolvedCountryCode = _countryCodeFromLabel(
      countryCode ?? nationality,
    );
    final Color positionAccent = GtexColors.positionColor(position);
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          clipBehavior: Clip.antiAlias,
          padding: const EdgeInsets.all(GtexSpacing.md),
          decoration: BoxDecoration(
            color: GtexFloodlit.card,
            borderRadius: BorderRadius.circular(GtexSpacing.radiusLg),
            border: Border.all(
              color: isSelected ? GtexFloodlit.pitch : GtexFloodlit.line,
              width: isSelected ? 1.8 : 1,
            ),
            boxShadow: <BoxShadow>[
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.4),
                blurRadius: 24,
                spreadRadius: -12,
                offset: const Offset(0, 14),
              ),
              if (isSelected)
                BoxShadow(
                  color: GtexFloodlit.pitch.withValues(alpha: 0.3),
                  blurRadius: 32,
                  spreadRadius: -14,
                ),
            ],
          ),
          child: Stack(
            clipBehavior: Clip.none,
            children: <Widget>[
              const Positioned(
                left: -GtexSpacing.md,
                top: -GtexSpacing.md,
                right: -GtexSpacing.md,
                bottom: -GtexSpacing.md,
                child: IgnorePointer(
                  child: CustomPaint(
                    painter: GtexTurfStripesPainter(),
                    foregroundPainter: GtexChalkFramePainter(opacity: 0.22),
                  ),
                ),
              ),
              LayoutBuilder(
                builder: (BuildContext context, BoxConstraints constraints) {
                  // Density ladder. The card carries a lot - identity,
                  // chips, traits, lineage, awards and a storyline - and a
                  // grid cell is a fixed box, so each tier drops the least
                  // load-bearing block rather than overflowing it.
                  final double availableHeight =
                      constraints.maxHeight.isFinite
                          ? constraints.maxHeight
                          : double.infinity;
                  final bool tightHeight = availableHeight < 190;
                  final bool compact = constraints.maxWidth < 320;
                  final double portraitWidth =
                      tightHeight
                          ? 104
                          : compact
                          ? 118
                          : 132;
                  // The ladder used to key on height alone, but in the
                  // side-by-side layout it is the *details column* that runs
                  // out of room: the portrait takes a fixed slice, so a
                  // three-column grid on a wide screen leaves a narrower
                  // column than a two-column grid on a small one. A narrow
                  // column wraps its chips onto extra runs and overflows a
                  // fixed cell height. Treat it as medium density so the same
                  // least-load-bearing blocks are dropped instead.
                  // In the stacked layout the portrait sits above the details
                  // and the whole column is narrow, so both dimensions are
                  // short; treat it as narrow outright.
                  final double detailsWidth =
                      constraints.maxWidth - portraitWidth - GtexSpacing.sm;
                  final bool narrowDetails = compact || detailsWidth < 220;
                  final bool mediumHeight =
                      !tightHeight && (availableHeight < 300 || narrowDetails);
                  final Widget portrait = SizedBox(
                    width: portraitWidth,
                    child: GtexRegenPortrait(
                      portraitUrl: portraitUrl,
                      seed: seed,
                      position: position,
                      nationalityCode: resolvedCountryCode,
                      jerseyColor: jerseyColor,
                    ),
                  );
                  final Widget details = _RegenCardDetails(
                    name: name,
                    archetype: archetype,
                    nationality: nationality,
                    position: position,
                    gsiLabel: gsiLabel,
                    gsiTierLabel: gsiTierLabel,
                    ratingLabel: ratingLabel,
                    potentialLabel: potentialLabel,
                    ageLabel: ageLabel,
                    valueLabel: valueLabel,
                    generationLabel: generationLabel,
                    traitLabels: traitLabels,
                    lineageLabel: lineageLabel,
                    awardLabels: awardLabels,
                    storyLine: storyLine,
                    theme: theme,
                    isDense: tightHeight,
                    isMedium: mediumHeight,
                  );
                  if (compact) {
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        _PositionStripe(
                          color: positionAccent,
                          horizontal: true,
                        ),
                        const SizedBox(height: GtexSpacing.sm),
                        Center(child: portrait),
                        const SizedBox(height: GtexSpacing.sm),
                        details,
                      ],
                    );
                  }
                  return Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      _PositionStripe(color: positionAccent),
                      const SizedBox(width: GtexSpacing.sm),
                      portrait,
                      const SizedBox(width: GtexSpacing.sm),
                      Expanded(
                        child: SingleChildScrollView(
                          physics: const ClampingScrollPhysics(),
                          child: details,
                        ),
                      ),
                    ],
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _countryCodeFromLabel(String value) {
    final String normalized = value.trim().toUpperCase();
    if (normalized.isEmpty) return 'GTX';
    const Map<String, String> names = <String, String>{
      'NIGERIA': 'NGA',
      'ENGLAND': 'ENG',
      'BRAZIL': 'BRA',
      'FRANCE': 'FRA',
      'GERMANY': 'GER',
      'ARGENTINA': 'ARG',
      'SPAIN': 'ESP',
      'ITALY': 'ITA',
      'GHANA': 'GHA',
      'KOREA': 'KOR',
    };
    return names[normalized] ??
        (normalized.length > 3 ? normalized.substring(0, 3) : normalized);
  }
}

class _RegenCardDetails extends StatelessWidget {
  const _RegenCardDetails({
    required this.name,
    required this.archetype,
    required this.nationality,
    required this.position,
    required this.potentialLabel,
    required this.theme,
    this.gsiLabel,
    this.gsiTierLabel,
    this.ratingLabel,
    this.ageLabel,
    this.valueLabel,
    this.generationLabel,
    this.traitLabels = const <String>[],
    this.lineageLabel,
    this.awardLabels = const <String>[],
    this.storyLine,
    this.isDense = false,
    this.isMedium = false,
  });

  final String name;
  final String archetype;
  final String nationality;
  final String position;
  final String potentialLabel;
  final ThemeData theme;
  final String? gsiLabel;
  final String? gsiTierLabel;
  final String? ratingLabel;
  final String? ageLabel;
  final String? valueLabel;
  final String? generationLabel;
  final List<String> traitLabels;
  final String? lineageLabel;
  final List<String> awardLabels;
  final String? storyLine;
  final bool isDense;

  /// Enough room for identity, chips, traits and lineage, but not for the
  /// awards rail and the storyline as well.
  final bool isMedium;

  @override
  Widget build(BuildContext context) {
    final String? resolvedGsiLabel = gsiLabel ?? ratingLabel;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            if (resolvedGsiLabel != null) ...<Widget>[
              _GsiPlate(label: resolvedGsiLabel, tierLabel: gsiTierLabel),
              const SizedBox(width: GtexSpacing.xs),
            ],
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    name.toUpperCase(),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: GtexFloodlit.chalk,
                      fontFamily: GtexFloodlit.display,
                      fontSize: 24,
                      fontWeight: FontWeight.w700,
                      height: 1,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '$nationality · $position · $archetype',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: GtexFloodlit.chalkMuted,
                      fontFamily: 'Inter',
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      height: 1.2,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        SizedBox(height: isDense ? GtexSpacing.xs : GtexSpacing.sm),
        if (!isDense && !isMedium) ...<Widget>[
          _RegenPotentialBar(
            currentRating: ratingLabel ?? gsiLabel,
            potentialLabel: potentialLabel,
          ),
          const SizedBox(height: 4),
        ],
        Wrap(
          spacing: 6,
          runSpacing: 6,
          children: <Widget>[
            const GtexStatusChip(
              label: 'REGEN DNA',
              color: GtexFloodlit.pitch,
              compact: true,
            ),
            if (!isDense &&
                generationLabel != null &&
                generationLabel!.trim().isNotEmpty)
              GtexStatusChip(
                label: generationLabel!,
                color: GtexColors.accentBlue,
                compact: true,
              ),
            GtexStatusChip(
              label: potentialLabel,
              color: GtexFloodlit.gold,
              compact: true,
            ),
            if (!isDense &&
                ratingLabel != null &&
                ratingLabel != resolvedGsiLabel)
              GtexStatusChip(
                label: ratingLabel!,
                color: GtexColors.cyan,
                compact: true,
              ),
            if (!isDense && gsiTierLabel != null)
              GtexStatusChip(
                label: gsiTierLabel!,
                color: GtexColors.accentViolet,
                compact: true,
              ),
            if (!isDense && ageLabel != null)
              GtexStatusChip(
                label: ageLabel!,
                color: GtexColors.cyan,
                compact: true,
              ),
            if (!isDense && valueLabel != null)
              GtexStatusChip(
                label: valueLabel!,
                color: GtexColors.coinGtex,
                compact: true,
              ),
          ],
        ),
        if (!isDense && traitLabels.isNotEmpty) ...<Widget>[
          const SizedBox(height: GtexSpacing.sm),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: traitLabels
                .where((String label) => label.trim().isNotEmpty)
                .take(3)
                .map(
                  (String label) => _TraitChip(
                    label: label.trim(),
                    color: _traitColor(label),
                  ),
                )
                .toList(growable: false),
          ),
        ],
        if (!isDense &&
            lineageLabel != null &&
            lineageLabel!.trim().isNotEmpty) ...<Widget>[
          const SizedBox(height: GtexSpacing.sm),
          _RegenSignalLine(
            icon: Icons.account_tree_rounded,
            label: lineageLabel!,
            color: GtexColors.accentViolet,
          ),
        ],
        if (!isDense && !isMedium && awardLabels.isNotEmpty) ...<Widget>[
          const SizedBox(height: GtexSpacing.sm),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: awardLabels
                .where((String label) => label.trim().isNotEmpty)
                // Bounded so a decorated regen cannot grow the card past
                // the cell it was given.
                .take(2)
                .map(
                  (String label) => _RegenSignalLine(
                    icon: Icons.emoji_events_rounded,
                    label: label.trim(),
                    color: GtexColors.accentAmber,
                  ),
                )
                .toList(growable: false),
          ),
        ],
        if (storyLine != null && !isMedium) ...<Widget>[
          SizedBox(height: isDense ? GtexSpacing.xs : GtexSpacing.sm),
          Text(
            storyLine!,
            maxLines: isDense ? 1 : 3,
            overflow: TextOverflow.ellipsis,
            style: theme.textTheme.bodySmall?.copyWith(
              color: GtexColors.textSecondary,
              height: 1.35,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ],
    );
  }
}

class _TraitChip extends StatelessWidget {
  const _TraitChip({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: label,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.14),
          borderRadius: BorderRadius.circular(GtexSpacing.radiusSm),
          border: Border.all(color: color.withValues(alpha: 0.42)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(Icons.auto_graph_rounded, size: 13, color: color),
            const SizedBox(width: 4),
            Flexible(
              child: Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: GtexColors.textPrimary,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _RegenSignalLine extends StatelessWidget {
  const _RegenSignalLine({
    required this.icon,
    required this.label,
    required this.color,
  });

  final IconData icon;
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusSm),
        border: Border.all(color: color.withValues(alpha: 0.24)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(icon, size: 14, color: color),
          const SizedBox(width: 5),
          Flexible(
            child: Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: GtexColors.textSecondary,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

Color _traitColor(String label) {
  final String normalized = label.toLowerCase();
  if (normalized.contains('elite') ||
      normalized.contains('dna') ||
      normalized.contains('inherited')) {
    return GtexColors.accentAmber;
  }
  if (normalized.contains('rare') ||
      normalized.contains('finisher') ||
      normalized.contains('leader')) {
    return GtexColors.accentBlue;
  }
  if (normalized.contains('press') ||
      normalized.contains('pace') ||
      normalized.contains('stamina')) {
    return GtexColors.accentPrimary;
  }
  return GtexColors.textSecondary;
}

class _PositionStripe extends StatelessWidget {
  const _PositionStripe({required this.color, this.horizontal = false});

  final Color color;
  final bool horizontal;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: horizontal ? double.infinity : 4,
      height: horizontal ? 4 : 118,
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(GtexSpacing.radiusSm),
      ),
    );
  }
}

class _GsiPlate extends StatelessWidget {
  const _GsiPlate({required this.label, this.tierLabel});

  final String label;
  final String? tierLabel;

  @override
  Widget build(BuildContext context) {
    final String value =
        label.replaceFirst(RegExp(r'^GSI\s*', caseSensitive: false), '').trim();
    return Container(
      width: 60,
      padding: const EdgeInsets.symmetric(vertical: 8),
      decoration: BoxDecoration(
        color: GtexFloodlit.night.withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: GtexFloodlit.gold.withValues(alpha: 0.55)),
      ),
      child: Column(
        children: <Widget>[
          Text(
            value.isEmpty ? 'TBC' : value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: GtexFloodlit.gold,
              fontFamily: GtexFloodlit.display,
              fontSize: 24,
              fontWeight: FontWeight.w700,
              height: 1,
            ),
          ),
          const Text(
            'GSI',
            style: TextStyle(
              color: GtexFloodlit.chalkMuted,
              fontFamily: 'Inter',
              fontSize: 9,
              fontWeight: FontWeight.w600,
              letterSpacing: 1.2,
              height: 1.3,
            ),
          ),
          if (tierLabel != null)
            Text(
              tierLabel!,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: GtexColors.textMuted,
                fontSize: 8,
                fontWeight: FontWeight.w800,
                height: 1.1,
              ),
            ),
        ],
      ),
    );
  }
}

class _RegenPotentialBar extends StatelessWidget {
  const _RegenPotentialBar({
    required this.currentRating,
    required this.potentialLabel,
  });

  final String? currentRating;
  final String potentialLabel;

  @override
  Widget build(BuildContext context) {
    int cur = 70;
    if (currentRating != null) {
      final Match? m = RegExp(r'\d+').firstMatch(currentRating!);
      if (m != null) cur = int.tryParse(m.group(0)!) ?? 70;
    }
    final List<int> pots = RegExp(r'\d+')
        .allMatches(potentialLabel)
        .map((m) => int.tryParse(m.group(0)!) ?? 0)
        .where((n) => n > 50)
        .toList();
    final int minPot = pots.isNotEmpty ? pots.first : cur + 10;
    final int maxPot = pots.length > 1 ? pots.last : minPot;

    final double curPct = (cur / 99.0).clamp(0.0, 1.0);
    final double potMaxPct = (maxPot / 99.0).clamp(0.0, 1.0);

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 2),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: const Color(0xFF071220),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: const Color(0xFF1E3557)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: <Widget>[
              const Flexible(
                child: Text(
                  'PROJECTED CEILING',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: Color(0xFF64748B),
                    fontSize: 9,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.5,
                  ),
                ),
              ),
              const SizedBox(width: 4),
              Text(
                '$cur -> $minPot${maxPot > minPot ? '-$maxPot' : ''}',
                style: const TextStyle(
                  color: Color(0xFFFBBF24),
                  fontSize: 10,
                  fontWeight: FontWeight.w800,
                  fontFamily: 'DMMono',
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          SizedBox(
            height: 5,
            child: LayoutBuilder(
              builder: (context, constraints) {
                final double w = constraints.maxWidth;
                return Stack(
                  children: <Widget>[
                    Container(
                      width: w,
                      decoration: BoxDecoration(
                        color: const Color(0xFF0F172A),
                        borderRadius: BorderRadius.circular(3),
                      ),
                    ),
                    Positioned(
                      left: w * curPct,
                      width: (w * (potMaxPct - curPct)).clamp(0.0, w),
                      top: 0,
                      bottom: 0,
                      child: Container(
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: <Color>[Color(0xFFD97706), Color(0xFFF59E0B)],
                          ),
                          borderRadius: BorderRadius.circular(3),
                        ),
                      ),
                    ),
                    Container(
                      width: (w * curPct).clamp(0.0, w),
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: <Color>[Color(0xFF0284C7), Color(0xFF38BDF8)],
                        ),
                        borderRadius: BorderRadius.circular(3),
                      ),
                    ),
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
