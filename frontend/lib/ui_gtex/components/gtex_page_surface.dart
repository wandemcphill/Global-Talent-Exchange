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
    this.blurSigma = 14,
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

    return Padding(
      padding: margin,
      child: ClipRRect(
        borderRadius: radius,
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: blurSigma, sigmaY: blurSigma),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            curve: Curves.easeOutCubic,
            decoration: BoxDecoration(
              borderRadius: radius,
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: <Color>[
                  isSelected
                      ? Color.alphaBlend(
                          accent.withValues(alpha: 0.14),
                          const Color(0xFF111B30),
                        )
                      : const Color(0xFF111B30).withValues(alpha: 0.88),
                  const Color(0xFF090F1C).withValues(alpha: 0.94),
                  const Color(0xFF060A14).withValues(alpha: 0.98),
                ],
              ),
              border: Border.all(
                color: isSelected
                    ? accent.withValues(alpha: 0.82)
                    : Colors.white.withValues(alpha: 0.13),
                width: isSelected ? 1.5 : 1.0,
              ),
              boxShadow: <BoxShadow>[
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.58),
                  blurRadius: 34,
                  spreadRadius: -10,
                  offset: const Offset(0, 16),
                ),
                if (isSelected) GtexColors.glow(accent, opacity: 0.22),
              ],
            ),
            child: Material(
              color: Colors.transparent,
              borderRadius: radius,
              clipBehavior: Clip.antiAlias,
              child: Padding(padding: padding, child: child),
            ),
          ),
        ),
      ),
    );
  }
}
