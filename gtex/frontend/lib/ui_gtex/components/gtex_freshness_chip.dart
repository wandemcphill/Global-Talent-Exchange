import 'package:flutter/material.dart';

import '../models/gtex_freshness.dart';
import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';
import 'green_pulse_dot.dart';

class GtexFreshnessChip extends StatelessWidget {
  const GtexFreshnessChip({
    super.key,
    required this.freshness,
    this.compact = false,
  });

  final GtexFreshnessInfo freshness;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    // Honest copy & badge policy:
    // When status or timestamp is UNKNOWN, do NOT render a decorative badge.
    if (freshness.status == GtexFreshnessStatus.unknown) {
      return const SizedBox.shrink();
    }

    final Color color = _statusColor(freshness.status);
    final String label = _statusLabel(freshness);

    final Widget dot = freshness.status == GtexFreshnessStatus.live
        ? GreenPulseDot(color: color, size: 8)
        : Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          );

    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: compact ? GtexSpacing.xs : GtexSpacing.sm,
        vertical: compact ? 3 : 5,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusPill),
        border: Border.all(color: color.withValues(alpha: 0.44)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          dot,
          const SizedBox(width: 6),
          Flexible(
            child: Text(
              label.toUpperCase(),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: color,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.4,
                  ),
            ),
          ),
        ],
      ),
    );
  }

  Color _statusColor(GtexFreshnessStatus status) {
    return switch (status) {
      GtexFreshnessStatus.live => GtexColors.statusLive,
      GtexFreshnessStatus.recent => GtexColors.accentPrimary,
      GtexFreshnessStatus.pendingRecalculation => GtexColors.statusLocked,
      GtexFreshnessStatus.stale => GtexColors.statusBlocked,
      GtexFreshnessStatus.unknown => GtexColors.textSecondary,
    };
  }

  String _statusLabel(GtexFreshnessInfo info) {
    if (info.label != null && info.label!.isNotEmpty) {
      return info.label!;
    }
    return switch (info.status) {
      GtexFreshnessStatus.live => 'LIVE',
      GtexFreshnessStatus.recent => 'RECENT',
      GtexFreshnessStatus.pendingRecalculation => 'PENDING RECALCULATION',
      GtexFreshnessStatus.stale => 'STALE',
      GtexFreshnessStatus.unknown => 'UNKNOWN',
    };
  }
}
