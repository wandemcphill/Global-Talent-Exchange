import 'package:flutter/material.dart';

import 'green_pulse_dot.dart';
import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';

enum GtexLiveStatus {
  live,
  loading,
  blocked,
  error,
  cooldown,
  pending,
  recent,
  locked,
}

class GtexLiveStatusChip extends StatelessWidget {
  const GtexLiveStatusChip({
    super.key,
    required this.status,
    this.label,
    this.countdown,
    this.pulse = false,
    this.compact = false,
  });

  final GtexLiveStatus status;
  final String? label;
  final Duration? countdown;
  final bool pulse;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final Color color = _statusColor(status);
    final String resolvedLabel = label ?? _statusLabel(status, countdown);
    final Widget dot =
        status == GtexLiveStatus.live && pulse
            ? GreenPulseDot(color: color, size: 8)
            : _StatusDot(color: color);
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: compact ? GtexSpacing.xs : GtexSpacing.sm,
        vertical: compact ? 4 : 6,
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
              resolvedLabel.toUpperCase(),
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

  Color _statusColor(GtexLiveStatus status) {
    return switch (status) {
      GtexLiveStatus.live => GtexColors.statusLive,
      GtexLiveStatus.loading => GtexColors.statusLoading,
      GtexLiveStatus.blocked ||
      GtexLiveStatus.error => GtexColors.statusBlocked,
      GtexLiveStatus.cooldown ||
      GtexLiveStatus.pending ||
      GtexLiveStatus.locked => GtexColors.statusLocked,
      GtexLiveStatus.recent => GtexColors.textSecondary,
    };
  }

  String _statusLabel(GtexLiveStatus status, Duration? countdown) {
    return switch (status) {
      GtexLiveStatus.live => 'Live',
      GtexLiveStatus.loading => 'Loading',
      GtexLiveStatus.blocked => 'Blocked',
      GtexLiveStatus.error => 'Error',
      GtexLiveStatus.cooldown =>
        countdown == null
            ? 'Cooldown'
            : 'Cooldown ${_durationLabel(countdown)}',
      GtexLiveStatus.pending => 'Pending',
      GtexLiveStatus.recent => 'Recent',
      GtexLiveStatus.locked => 'Locked',
    };
  }

  String _durationLabel(Duration duration) {
    if (duration.inDays > 0) {
      return '${duration.inDays}d ${duration.inHours.remainder(24)}h';
    }
    if (duration.inHours > 0) {
      return '${duration.inHours}h ${duration.inMinutes.remainder(60)}m';
    }
    return '${duration.inMinutes}m';
  }
}

class _StatusDot extends StatelessWidget {
  const _StatusDot({required this.color});

  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 8,
      height: 8,
      decoration: BoxDecoration(color: color, shape: BoxShape.circle),
    );
  }
}
