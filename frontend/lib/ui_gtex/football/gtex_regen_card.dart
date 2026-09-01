import 'package:flutter/material.dart';

import '../components/gtex_status_chip.dart';
import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';
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
          padding: const EdgeInsets.all(GtexSpacing.sm),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: <Color>[
                GtexColors.surfaceRaised,
                GtexColors.surfaceBase,
                GtexColors.accentViolet.withValues(alpha: 0.07),
              ],
            ),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color:
                  isSelected
                      ? GtexColors.accentViolet.withValues(alpha: 0.92)
                      : GtexColors.surfaceBorderStrong,
              width: isSelected ? 1.8 : 1,
            ),
            boxShadow: <BoxShadow>[
              if (isSelected) GtexColors.glow(GtexColors.accentViolet),
            ],
          ),
          child: Stack(
            children: <Widget>[
              Positioned.fill(
                child: IgnorePointer(
                  child: CustomPaint(
                    painter: _RegenDnaWatermarkPainter(GtexColors.accentViolet),
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
                  final bool mediumHeight =
                      !tightHeight && availableHeight < 300;
                  final bool compact = constraints.maxWidth < 320;
                  final Widget portrait = SizedBox(
                    width:
                        tightHeight
                            ? 104
                            : compact
                            ? 118
                            : 132,
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
                      Expanded(child: details),
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
                    style: theme.textTheme.titleMedium?.copyWith(
                      color: GtexColors.text,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 0,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    '$nationality | $position | $archetype',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: GtexColors.textMuted,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        SizedBox(height: isDense ? GtexSpacing.xs : GtexSpacing.sm),
        Wrap(
          spacing: 6,
          runSpacing: 6,
          children: <Widget>[
            const GtexStatusChip(
              label: 'REGEN DNA',
              color: GtexColors.accentViolet,
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
              color: GtexColors.accentViolet,
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
            Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: GtexColors.textPrimary,
                fontWeight: FontWeight.w800,
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

class _RegenDnaWatermarkPainter extends CustomPainter {
  const _RegenDnaWatermarkPainter(this.color);

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final Paint paint =
        Paint()
          ..color = color.withValues(alpha: 0.055)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.2;
    final Path left = Path();
    final Path right = Path();
    for (double y = -20; y <= size.height + 20; y += 12) {
      final double progress = y / size.height;
      final double wave = 18 * (0.5 + 0.5 * progress);
      final double centerX = size.width - 44;
      final double offset = 16 * (1 + progress);
      final double x1 = centerX + (wave * 0.35);
      final double x2 = centerX - offset;
      if (y == -20) {
        left.moveTo(x1, y);
        right.moveTo(x2, y);
      } else {
        left.lineTo(x1, y);
        right.lineTo(x2, y);
      }
      if (((y / 24).round()).isEven) {
        canvas.drawLine(Offset(x1, y), Offset(x2, y + 6), paint);
      }
    }
    canvas.drawPath(left, paint);
    canvas.drawPath(right, paint);
  }

  @override
  bool shouldRepaint(covariant _RegenDnaWatermarkPainter oldDelegate) =>
      oldDelegate.color != color;
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
      width: 54,
      padding: const EdgeInsets.symmetric(vertical: 7),
      decoration: BoxDecoration(
        color: GtexColors.gold.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: GtexColors.gold.withValues(alpha: 0.6)),
      ),
      child: Column(
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
          const Text(
            'GSI',
            style: TextStyle(
              color: GtexColors.textMuted,
              fontSize: 9,
              fontWeight: FontWeight.w900,
              height: 1.2,
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
