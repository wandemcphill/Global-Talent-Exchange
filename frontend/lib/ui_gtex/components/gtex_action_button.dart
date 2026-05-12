import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';

class GtexActionButton extends StatelessWidget {
  const GtexActionButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.icon,
    this.accent = GtexColors.pitch,
    this.compact = false,
    this.secondary = false,
  });

  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;
  final Color accent;
  final bool compact;
  final bool secondary;

  @override
  Widget build(BuildContext context) {
    final ButtonStyle style =
        secondary
            ? OutlinedButton.styleFrom(
              foregroundColor: accent,
              side: BorderSide(color: accent.withValues(alpha: 0.55)),
              padding: EdgeInsets.symmetric(
                horizontal: compact ? GtexSpacing.sm : GtexSpacing.lg,
                vertical: compact ? GtexSpacing.xs : GtexSpacing.sm,
              ),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(GtexSpacing.radiusPill),
              ),
            )
            : FilledButton.styleFrom(
              backgroundColor: accent,
              foregroundColor: Colors.black,
              padding: EdgeInsets.symmetric(
                horizontal: compact ? GtexSpacing.sm : GtexSpacing.lg,
                vertical: compact ? GtexSpacing.xs : GtexSpacing.sm,
              ),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(GtexSpacing.radiusPill),
              ),
            );

    final Widget child = FittedBox(
      fit: BoxFit.scaleDown,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          if (icon != null) ...<Widget>[
            Icon(icon, size: compact ? 16 : 18),
            const SizedBox(width: GtexSpacing.xs),
          ],
          Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontWeight: FontWeight.w800),
          ),
        ],
      ),
    );

    if (secondary) {
      return OutlinedButton(onPressed: onPressed, style: style, child: child);
    }
    return FilledButton(onPressed: onPressed, style: style, child: child);
  }
}
