import 'package:flutter/material.dart';

import 'gtex_page_surface.dart';
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
    final Widget content = GtexPageSurface(
      margin: margin,
      padding: padding,
      accent: accent,
      isSelected: isSelected,
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
