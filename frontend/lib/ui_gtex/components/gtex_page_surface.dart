import 'dart:ui';

import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';

class GtexPageSurface extends StatelessWidget {
  const GtexPageSurface({
    super.key,
    required this.child,
    this.padding = GtexSpacing.panelPadding,
    this.margin = EdgeInsets.zero,
    this.accent = GtexColors.pitch,
    this.isSelected = false,
    this.blurSigma = 12,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final EdgeInsetsGeometry margin;
  final Color accent;
  final bool isSelected;
  final double blurSigma;

  @override
  Widget build(BuildContext context) {
    final BorderRadius radius = BorderRadius.circular(GtexSpacing.radiusLg);
    final Color surfaceColor =
        isSelected
            ? Color.alphaBlend(
              accent.withValues(alpha: 0.09),
              GtexColors.panel.withValues(alpha: 0.76),
            )
            : GtexColors.panel.withValues(alpha: 0.72);

    return Padding(
      padding: margin,
      child: ClipRRect(
        borderRadius: radius,
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: blurSigma, sigmaY: blurSigma),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 180),
            curve: Curves.easeOutCubic,
            padding: padding,
            decoration: BoxDecoration(
              color: surfaceColor,
              borderRadius: radius,
              border: Border.all(
                color:
                    isSelected
                        ? accent.withValues(alpha: 0.78)
                        : GtexColors.line.withValues(alpha: 0.72),
              ),
              boxShadow: <BoxShadow>[
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.20),
                  blurRadius: 26,
                  spreadRadius: -18,
                  offset: const Offset(0, 18),
                ),
                if (isSelected) GtexColors.glow(accent, opacity: 0.18),
              ],
            ),
            child: Material(type: MaterialType.transparency, child: child),
          ),
        ),
      ),
    );
  }
}
