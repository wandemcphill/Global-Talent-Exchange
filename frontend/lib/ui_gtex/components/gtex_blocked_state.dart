import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';

enum GtexBlockedSeverity { warning, error, info, locked }

class GtexBlockedState extends StatelessWidget {
  const GtexBlockedState({
    super.key,
    required this.reason,
    this.title,
    this.severity = GtexBlockedSeverity.warning,
    this.resolution,
    this.ctaLabel,
    this.ctaAction,
    this.icon,
    this.compact = false,
  });

  final String reason;
  final String? title;
  final GtexBlockedSeverity severity;
  final String? resolution;
  final String? ctaLabel;
  final VoidCallback? ctaAction;
  final IconData? icon;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens colors = GtexColors.of(context);
    final Color accent = _severityColor(severity);
    final IconData resolvedIcon = icon ?? _severityIcon(severity);
    return Container(
      padding: EdgeInsets.all(compact ? GtexSpacing.sm : GtexSpacing.md),
      decoration: BoxDecoration(
        color:
            severity == GtexBlockedSeverity.locked
                ? colors.bgSurface
                : accent.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusLg),
        border: Border.all(
          color:
              severity == GtexBlockedSeverity.locked
                  ? colors.bgBorder
                  : accent.withValues(alpha: 0.5),
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(
            width: compact ? 32 : 40,
            height: compact ? 32 : 40,
            decoration: BoxDecoration(
              color: accent.withValues(alpha: 0.14),
              borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
              border: Border.all(color: accent.withValues(alpha: 0.32)),
            ),
            child: Icon(resolvedIcon, color: accent, size: compact ? 18 : 22),
          ),
          const SizedBox(width: GtexSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                Text(
                  title ?? _severityTitle(severity),
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    color: colors.textPrimary,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: GtexSpacing.xxs),
                Text(
                  reason,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: colors.textSecondary,
                    height: 1.35,
                  ),
                ),
                if (resolution != null &&
                    resolution!.trim().isNotEmpty) ...<Widget>[
                  const SizedBox(height: GtexSpacing.xs),
                  Text(
                    resolution!,
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: accent,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
                if (ctaLabel != null && ctaAction != null) ...<Widget>[
                  const SizedBox(height: GtexSpacing.sm),
                  OutlinedButton(
                    onPressed: ctaAction,
                    style: OutlinedButton.styleFrom(
                      foregroundColor: accent,
                      side: BorderSide(color: accent.withValues(alpha: 0.5)),
                    ),
                    child: Text(ctaLabel!),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Color _severityColor(GtexBlockedSeverity severity) {
    return switch (severity) {
      GtexBlockedSeverity.warning => GtexColors.accentAmber,
      GtexBlockedSeverity.error => GtexColors.accentRed,
      GtexBlockedSeverity.info => GtexColors.accentBlue,
      GtexBlockedSeverity.locked => GtexColors.textTertiary,
    };
  }

  IconData _severityIcon(GtexBlockedSeverity severity) {
    return switch (severity) {
      GtexBlockedSeverity.warning => Icons.warning_amber_rounded,
      GtexBlockedSeverity.error => Icons.error_outline_rounded,
      GtexBlockedSeverity.info => Icons.info_outline_rounded,
      GtexBlockedSeverity.locked => Icons.lock_outline_rounded,
    };
  }

  String _severityTitle(GtexBlockedSeverity severity) {
    return switch (severity) {
      GtexBlockedSeverity.warning => 'Action blocked',
      GtexBlockedSeverity.error => 'Live data unavailable',
      GtexBlockedSeverity.info => 'Information required',
      GtexBlockedSeverity.locked => 'Access boundary',
    };
  }
}
