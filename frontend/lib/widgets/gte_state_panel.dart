import 'package:flutter/material.dart';

import '../ui_gtex/components/gtex_button.dart';
import '../ui_gtex/theme/gtex_colors.dart';
import '../ui_gtex/theme/gtex_spacing.dart';
import 'gte_surface_panel.dart';

/// Below this content width the status badge stops sitting beside the copy
/// and stacks under it: narrower than this the two compete for the same line
/// and the message loses.
const double _stackHeaderWidth = 480;

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
      // This panel is the app's universal loading / empty / error / blocked
      // surface, so it renders at every width the product has: full-bleed
      // workspaces, a 330px browse rail, a 360px summary rail and modal
      // sheets. Deciding its header layout from the window meant a wide
      // window kept the side-by-side header inside a narrow rail, squeezing
      // the copy against the status badge. It measures the box it is handed
      // instead; MediaQuery only remains the fallback for an unbounded
      // parent, where there is no box to measure.
      child: LayoutBuilder(
        builder: (BuildContext context, BoxConstraints constraints) {
          final double availableWidth =
              constraints.hasBoundedWidth
                  ? constraints.maxWidth
                  : MediaQuery.sizeOf(context).width;
          final bool stackHeader = availableWidth < _stackHeaderWidth;
          return Column(
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
          );
        },
      ),
    );
  }
}
