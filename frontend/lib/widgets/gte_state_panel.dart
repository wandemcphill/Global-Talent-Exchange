import 'package:flutter/material.dart';

import '../ui_gtex/components/gtex_button.dart';
import '../ui_gtex/theme/gtex_colors.dart';
import '../ui_gtex/theme/gtex_spacing.dart';
import 'gte_surface_panel.dart';

class GteStatePanel extends StatelessWidget {
  const GteStatePanel({
    super.key,
    required this.title,
    required this.message,
    this.actionLabel,
    this.onAction,
    this.icon,
    this.eyebrow,
    this.accentColor,
    this.isLoading = false,
  });

  final String title;
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;
  final IconData? icon;
  final String? eyebrow;
  final Color? accentColor;
  final bool isLoading;

  @override
  Widget build(BuildContext context) {
    final Color accent = accentColor ?? GtexColors.pitch;
    final String resolvedEyebrow =
        eyebrow ?? (isLoading ? 'LIVE SYNC' : 'GTEX STATUS');
    final bool stackHeader = MediaQuery.sizeOf(context).width < 480;
    final bool showStatusVisual = icon != null || isLoading;
    final Widget eyebrowChip = Container(
      padding: const EdgeInsets.symmetric(
        horizontal: GtexSpacing.sm,
        vertical: 7,
      ),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusPill),
        border: Border.all(color: accent.withValues(alpha: 0.42)),
      ),
      child: Wrap(
        spacing: GtexSpacing.xs,
        runSpacing: 4,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: <Widget>[
          Container(
            width: 8,
            height: 8,
            margin: const EdgeInsets.symmetric(vertical: 4),
            decoration: BoxDecoration(shape: BoxShape.circle, color: accent),
          ),
          Text(
            resolvedEyebrow,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: accent,
              fontWeight: FontWeight.w900,
              letterSpacing: 0.6,
            ),
          ),
        ],
      ),
    );
    final Widget headerCopy = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        eyebrowChip,
        const SizedBox(height: GtexSpacing.sm),
        Text(
          title,
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
            color: GtexColors.text,
            fontWeight: FontWeight.w900,
          ),
        ),
        const SizedBox(height: GtexSpacing.xs),
        Text(
          message,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: GtexColors.textSecondary,
            height: 1.45,
          ),
        ),
      ],
    );
    final Widget? statusVisual =
        !showStatusVisual
            ? null
            : Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
                color: accent.withValues(alpha: 0.14),
                border: Border.all(color: accent.withValues(alpha: 0.36)),
                boxShadow: <BoxShadow>[
                  BoxShadow(
                    color: accent.withValues(alpha: 0.12),
                    blurRadius: 18,
                    spreadRadius: 1,
                  ),
                ],
              ),
              child:
                  isLoading
                      ? SizedBox(
                        width: 28,
                        height: 28,
                        child: CircularProgressIndicator(
                          strokeWidth: 2.6,
                          valueColor: AlwaysStoppedAnimation<Color>(accent),
                        ),
                      )
                      : Icon(icon, size: 28, color: accent),
            );

    return GteSurfacePanel(
      emphasized: true,
      accentColor: accent,
      padding: const EdgeInsets.all(GtexSpacing.lg),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          if (stackHeader)
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                headerCopy,
                if (statusVisual != null) ...<Widget>[
                  const SizedBox(height: GtexSpacing.md),
                  statusVisual,
                ],
              ],
            )
          else
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Expanded(child: headerCopy),
                if (statusVisual != null) ...<Widget>[
                  const SizedBox(width: GtexSpacing.md),
                  statusVisual,
                ],
              ],
            ),
          if (actionLabel != null && onAction != null) ...<Widget>[
            const SizedBox(height: GtexSpacing.md),
            GtexButton(
              label: actionLabel!,
              icon: isLoading ? Icons.refresh : Icons.arrow_forward,
              onPressed: onAction,
            ),
          ],
        ],
      ),
    );
  }
}
