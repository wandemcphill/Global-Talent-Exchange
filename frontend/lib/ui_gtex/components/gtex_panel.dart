import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';

class GtexPanel extends StatelessWidget {
  const GtexPanel({
    super.key,
    required this.child,
    this.padding = GtexSpacing.panelPadding,
    this.accent = GtexColors.pitch,
    this.title,
    this.subtitle,
    this.helper,
    this.trailing,
    this.margin = EdgeInsets.zero,
    this.onTap,
    this.isSelected = false,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final Color accent;
  final String? title;
  final String? subtitle;
  final String? helper;
  final Widget? trailing;
  final EdgeInsetsGeometry margin;
  final VoidCallback? onTap;
  final bool isSelected;

  @override
  Widget build(BuildContext context) {
    final BorderRadius radius = BorderRadius.circular(GtexSpacing.radiusLg);
    final String? supportText = subtitle ?? helper;
    final Widget content = AnimatedContainer(
      duration: const Duration(milliseconds: 180),
      curve: Curves.easeOutCubic,
      margin: margin,
      padding: padding,
      decoration: BoxDecoration(
        color:
            isSelected
                ? Color.alphaBlend(
                  accent.withValues(alpha: 0.08),
                  GtexColors.panel,
                )
                : GtexColors.panel.withValues(alpha: 0.88),
        borderRadius: radius,
        border: Border.all(
          color:
              isSelected
                  ? accent.withValues(alpha: 0.78)
                  : GtexColors.line.withValues(alpha: 0.78),
        ),
        boxShadow: <BoxShadow>[
          if (isSelected) GtexColors.glow(accent, opacity: 0.2),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          if (title != null || trailing != null) ...<Widget>[
            Row(
              children: <Widget>[
                if (title != null)
                  Expanded(
                    child: Text(
                      title!,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: GtexColors.text,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                if (trailing != null) trailing!,
              ],
            ),
            if (supportText != null) ...<Widget>[
              const SizedBox(height: GtexSpacing.xxs),
              Text(
                supportText,
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: GtexColors.textMuted),
              ),
            ],
            const SizedBox(height: GtexSpacing.md),
          ],
          child,
        ],
      ),
    );

    if (onTap == null) {
      return content;
    }
    return Material(
      color: Colors.transparent,
      child: InkWell(borderRadius: radius, onTap: onTap, child: content),
    );
  }
}
