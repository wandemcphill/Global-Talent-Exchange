import 'package:flutter/material.dart';

import 'gtex_panel.dart';
import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';

class GtexCard extends StatelessWidget {
  const GtexCard({
    super.key,
    required this.child,
    this.padding = GtexSpacing.panelPadding,
    this.borderColor,
    this.accent,
    this.onTap,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final Color? borderColor;
  final Color? accent;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      padding: padding,
      accent: borderColor ?? accent ?? GtexColors.pitch,
      isSelected: borderColor != null,
      onTap: onTap,
      child: child,
    );
  }
}
