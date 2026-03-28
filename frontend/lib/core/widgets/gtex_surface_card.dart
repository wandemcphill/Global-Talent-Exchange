import 'package:flutter/material.dart';

import '../constants/app_spacing.dart';
import '../theme/app_colors.dart';
import '../theme/app_motion.dart';
import 'app_press_scale.dart';

class GtexSurfaceCard extends StatelessWidget {
  const GtexSurfaceCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(spacingMD),
    this.onTap,
    this.glowColor,
    this.margin,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final VoidCallback? onTap;
  final Color? glowColor;
  final EdgeInsetsGeometry? margin;

  @override
  Widget build(BuildContext context) {
    final Widget content = RepaintBoundary(
      child: AnimatedContainer(
        duration: AppMotion.medium,
        curve: AppMotion.easeOut,
        margin: margin,
        padding: padding,
        decoration: BoxDecoration(
          color: AppColors.card.withValues(alpha: 0.96),
          borderRadius: BorderRadius.circular(cardRadius),
          border: Border.all(
            color: glowColor?.withValues(alpha: 0.35) ?? AppColors.divider,
          ),
          boxShadow: <BoxShadow>[
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.24),
              blurRadius: 24,
              offset: const Offset(0, 14),
            ),
            if (glowColor != null)
              BoxShadow(
                color: glowColor!.withValues(alpha: 0.12),
                blurRadius: 28,
                spreadRadius: 1,
              ),
          ],
        ),
        child: child,
      ),
    );

    if (onTap == null) {
      return content;
    }

    return AppPressScale(
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(cardRadius),
          onTap: onTap,
          child: content,
        ),
      ),
    );
  }
}
