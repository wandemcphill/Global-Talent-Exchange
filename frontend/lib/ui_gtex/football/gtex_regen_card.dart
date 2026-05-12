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
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          padding: const EdgeInsets.all(GtexSpacing.sm),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: <Color>[
                GtexColors.gold.withValues(alpha: 0.14),
                GtexColors.panelStrong.withValues(alpha: 0.94),
                GtexColors.stadiumBlack.withValues(alpha: 0.98),
              ],
            ),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color:
                  isSelected
                      ? GtexColors.electricGreen.withValues(alpha: 0.92)
                      : GtexColors.gold.withValues(alpha: 0.44),
              width: isSelected ? 1.8 : 1,
            ),
            boxShadow: <BoxShadow>[
              if (isSelected) GtexColors.glow(GtexColors.electricGreen),
            ],
          ),
          child: LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final bool tightHeight =
                  constraints.maxHeight.isFinite && constraints.maxHeight < 190;
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
                storyLine: storyLine,
                theme: theme,
                isDense: tightHeight,
              );
              if (compact) {
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Center(child: portrait),
                    const SizedBox(height: GtexSpacing.sm),
                    details,
                  ],
                );
              }
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  portrait,
                  const SizedBox(width: GtexSpacing.sm),
                  Expanded(child: details),
                ],
              );
            },
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
    this.storyLine,
    this.isDense = false,
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
  final String? storyLine;
  final bool isDense;

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
            GtexStatusChip(
              label: potentialLabel,
              color: GtexColors.gold,
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
                color: GtexColors.gold,
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
                color: GtexColors.electricGreen,
                compact: true,
              ),
            const GtexStatusChip(
              label: 'NEWGEN',
              color: GtexColors.electricGreen,
              compact: true,
            ),
          ],
        ),
        if (storyLine != null) ...<Widget>[
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
