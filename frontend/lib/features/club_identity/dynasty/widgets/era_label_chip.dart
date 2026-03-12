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
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: tone.fill.withValues(alpha: active ? 0.22 : 0.14),
        border: Border.all(color: tone.stroke),
      ),
      child: Text(
        era.label,
        style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: tone.text,
            ),
      ),
    );
  }
}

class _EraTone {
  const _EraTone({
    required this.fill,
    required this.stroke,
    required this.text,
  });

  final Color fill;
  final Color stroke;
  final Color text;
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
        text: Color(0xFFFFE7A9),
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
