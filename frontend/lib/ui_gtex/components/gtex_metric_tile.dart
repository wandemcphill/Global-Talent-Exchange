import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';

class GtexMetricTile extends StatelessWidget {
  const GtexMetricTile({
    super.key,
    required this.label,
    required this.value,
    this.delta,
    this.helper,
    this.icon,
    this.accent = GtexColors.pitch,
  });

  final String label;
  final String value;
  final String? delta;
  final String? helper;
  final IconData? icon;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(GtexSpacing.md),
      decoration: BoxDecoration(
        color: GtexColors.panelStrong.withValues(alpha: 0.78),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
        border: Border.all(color: GtexColors.line.withValues(alpha: 0.72)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          if (icon != null) ...<Widget>[
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                color: accent.withValues(alpha: 0.12),
                shape: BoxShape.circle,
              ),
              child: Icon(icon, color: accent, size: 20),
            ),
            const SizedBox(height: GtexSpacing.xs),
          ],
          Text(
            label.toUpperCase(),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: GtexColors.textMuted,
              fontWeight: FontWeight.w900,
              letterSpacing: 0.8,
            ),
          ),
          const SizedBox(height: 3),
          Text(
            value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
              color: GtexColors.text,
              fontWeight: FontWeight.w900,
            ),
          ),
          if (helper != null && helper!.trim().isNotEmpty) ...<Widget>[
            const SizedBox(height: 3),
            Text(
              helper!,
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: GtexColors.textMuted,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
          if (delta != null) ...<Widget>[
            const SizedBox(height: 3),
            Text(
              delta!,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                color: accent,
                fontWeight: FontWeight.w900,
              ),
            ),
          ],
        ],
      ),
    );
  }
}
