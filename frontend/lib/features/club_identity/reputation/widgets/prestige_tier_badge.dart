import 'package:flutter/material.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

import '../data/reputation_models.dart';

class PrestigeTierBadge extends StatelessWidget {
  const PrestigeTierBadge({
    super.key,
    required this.tier,
    this.compact = false,
  });

  final PrestigeTier tier;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final _TierPalette palette = _paletteForTier(tier);
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: compact ? 10 : 14,
        vertical: compact ? 8 : 10,
      ),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        gradient: LinearGradient(
          colors: <Color>[
            palette.background,
            palette.background.withValues(alpha: 0.68),
          ],
        ),
        border: Border.all(color: palette.border),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(tier.icon, size: compact ? 14 : 18, color: palette.foreground),
          SizedBox(width: compact ? 6 : 8),
          Text(
            tier.label,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: palette.foreground,
                  fontWeight: FontWeight.w700,
                ),
          ),
        ],
      ),
    );
  }
}

class _TierPalette {
  const _TierPalette({
    required this.background,
    required this.border,
    required this.foreground,
  });

  final Color background;
  final Color border;
  final Color foreground;
}

_TierPalette _paletteForTier(PrestigeTier tier) {
  switch (tier) {
    case PrestigeTier.local:
      return const _TierPalette(
        background: Color(0xFF152033),
        border: GteShellTheme.stroke,
        foreground: GteShellTheme.textMuted,
      );
    case PrestigeTier.rising:
      return const _TierPalette(
        background: Color(0xFF16334A),
        border: Color(0xFF3F7EA2),
        foreground: GteShellTheme.accent,
      );
    case PrestigeTier.established:
      return const _TierPalette(
        background: Color(0xFF283320),
        border: Color(0xFF8DBB6B),
        foreground: Color(0xFFD5F3B1),
      );
    case PrestigeTier.elite:
      return const _TierPalette(
        background: Color(0xFF342819),
        border: Color(0xFFD6A861),
        foreground: GteShellTheme.accentWarm,
      );
    case PrestigeTier.legendary:
      return const _TierPalette(
        background: Color(0xFF2E1B2F),
        border: Color(0xFFE79CF1),
        foreground: Color(0xFFFFCCFF),
      );
    case PrestigeTier.dynasty:
      return const _TierPalette(
        background: Color(0xFF352514),
        border: Color(0xFFFFE08C),
        foreground: Color(0xFFFFF0BA),
      );
  }
}
