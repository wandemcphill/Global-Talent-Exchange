import 'package:flutter/material.dart';

import '../../../../widgets/gte_shell_theme.dart';
import '../data/dynasty_types.dart';

class EraLabelChip extends StatelessWidget {
  const EraLabelChip({
    super.key,
    required this.era,
    this.active = false,
  });

  final DynastyEraType era;
  final bool active;

  @override
  Widget build(BuildContext context) {
    final _EraTone tone = _toneForEra(era);
    final bool hasIcon = tone.icon != null;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: tone.fill.withValues(alpha: active ? 0.22 : 0.14),
        border: Border.all(color: tone.stroke),
        boxShadow: tone.glow,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          if (hasIcon) ...<Widget>[
            Icon(tone.icon, size: 16, color: tone.text),
            const SizedBox(width: 6),
          ],
          Text(
            era.label,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: tone.text,
                  fontWeight: tone.fontWeight,
                  letterSpacing:
                      tone.fontWeight == FontWeight.w700 ? 0.4 : null,
                ),
          ),
        ],
      ),
    );
  }
}

class _EraTone {
  const _EraTone({
    required this.fill,
    required this.stroke,
    required this.text,
    this.icon,
    this.glow,
    this.fontWeight,
  });

  final Color fill;
  final Color stroke;
  final Color text;
  final IconData? icon;
  final List<BoxShadow>? glow;
  final FontWeight? fontWeight;
}

_EraTone _toneForEra(DynastyEraType era) {
  switch (era) {
    case DynastyEraType.emergingPower:
      return const _EraTone(
        fill: GteShellTheme.accent,
        stroke: Color(0xAA7DE2D1),
        text: GteShellTheme.accent,
      );
    case DynastyEraType.dominantEra:
      return const _EraTone(
        fill: GteShellTheme.positive,
        stroke: Color(0xAA73F7AF),
        text: GteShellTheme.positive,
      );
    case DynastyEraType.continentalDynasty:
      return const _EraTone(
        fill: GteShellTheme.accentWarm,
        stroke: Color(0xAAFFC76B),
        text: GteShellTheme.accentWarm,
      );
    case DynastyEraType.globalDynasty:
      return const _EraTone(
        fill: Color(0xFFFFD978),
        stroke: Color(0xFFFFE7A9),
        text: Color(0xFFFFF1C8),
        icon: Icons.auto_awesome,
        glow: <BoxShadow>[
          BoxShadow(
            color: Color(0x66FFD978),
            blurRadius: 12,
            offset: Offset(0, 4),
          ),
        ],
        fontWeight: FontWeight.w700,
      );
    case DynastyEraType.fallenGiant:
      return const _EraTone(
        fill: Color(0xFFB4A48A),
        stroke: Color(0xFFD6C7AE),
        text: Color(0xFFF3E5CA),
      );
    case DynastyEraType.none:
      return const _EraTone(
        fill: GteShellTheme.stroke,
        stroke: GteShellTheme.stroke,
        text: GteShellTheme.textMuted,
      );
  }
}
