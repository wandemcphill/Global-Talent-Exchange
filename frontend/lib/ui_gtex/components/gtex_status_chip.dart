import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';

enum GtexStatusTone { neutral, success, warning, danger, premium }

class GtexStatusChip extends StatelessWidget {
  const GtexStatusChip({
    super.key,
    required this.label,
    this.icon,
    this.color,
    this.tone,
    this.compact = false,
  });

  final String label;
  final IconData? icon;
  final Color? color;
  final GtexStatusTone? tone;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final Color resolvedColor = color ?? _toneColor(tone);
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: compact ? GtexSpacing.xs : GtexSpacing.sm,
        vertical: compact ? 5 : 7,
      ),
      decoration: BoxDecoration(
        color: resolvedColor.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusPill),
        border: Border.all(color: resolvedColor.withValues(alpha: 0.48)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          if (icon != null) ...<Widget>[
            Icon(icon, size: compact ? 13 : 15, color: resolvedColor),
            const SizedBox(width: 5),
          ],
          Flexible(
            child: Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: resolvedColor,
                fontWeight: FontWeight.w900,
                letterSpacing: 0.3,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Color _toneColor(GtexStatusTone? tone) {
    return switch (tone) {
      GtexStatusTone.success => GtexColors.pitch,
      GtexStatusTone.warning => GtexColors.orange,
      GtexStatusTone.danger => GtexColors.red,
      GtexStatusTone.premium => GtexColors.gold,
      GtexStatusTone.neutral || null => GtexColors.cyan,
    };
  }
}
