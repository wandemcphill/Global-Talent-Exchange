import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';
import 'gtex_status_presenter.dart';

enum GtexStatusTone { neutral, success, warning, danger, premium }

class GtexStatusChip extends StatelessWidget {
  const GtexStatusChip({
    super.key,
    required this.label,
    this.icon,
    this.color,
    this.tone,
    this.compact = false,
    this.outlined = false,
  });

  /// Build a canonical [GtexStatusChip] directly from a backend status string
  /// using [GtexStatusPresenter] (Document F10).
  factory GtexStatusChip.fromBackendStatus(
    String? rawStatus, {
    Key? key,
    GtexStatusContext context = GtexStatusContext.general,
    bool compact = false,
  }) {
    final GtexPresentedStatus presented = GtexStatusPresenter.present(
      rawStatus,
      context: context,
    );
    return GtexStatusChip(
      key: key,
      label: presented.label,
      icon: presented.icon,
      color: presented.color,
      compact: compact,
      outlined: presented.outlined,
    );
  }

  final String label;
  final IconData? icon;
  final Color? color;
  final GtexStatusTone? tone;
  final bool compact;
  final bool outlined;

  @override
  Widget build(BuildContext context) {
    final Color resolvedColor = color ?? _toneColor(tone);
    return Semantics(
      label: 'Status: $label',
      child: Container(
        padding: EdgeInsets.symmetric(
          horizontal: compact ? GtexSpacing.xs : GtexSpacing.sm,
          vertical: compact ? 5 : 7,
        ),
        decoration: BoxDecoration(
          color:
              outlined
                  ? Colors.transparent
                  : resolvedColor.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(GtexSpacing.radiusPill),
          border: Border.all(
            color: resolvedColor.withValues(alpha: outlined ? 0.8 : 0.48),
          ),
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
      ),
    );
  }

  Color _toneColor(GtexStatusTone? tone) {
    return switch (tone) {
      GtexStatusTone.success => GtexColors.accentPrimary,
      GtexStatusTone.warning => GtexColors.accentAmber,
      GtexStatusTone.danger => GtexColors.accentRed,
      GtexStatusTone.premium => GtexColors.coinGtex,
      GtexStatusTone.neutral || null => GtexColors.accentBlue,
    };
  }
}
