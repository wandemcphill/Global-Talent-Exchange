import 'package:flutter/material.dart';

import '../../core/constants/app_spacing.dart';
import '../../navigation/app_destinations.dart';

class RouteSurfaceBadge extends StatelessWidget {
  const RouteSurfaceBadge({super.key, required this.state});

  final AppRouteSurfaceState state;

  @override
  Widget build(BuildContext context) {
    final String? label = state.disclosureLabel;
    if (label == null) {
      return const SizedBox.shrink();
    }
    final ColorScheme colors = Theme.of(context).colorScheme;
    final Color color = switch (state) {
      AppRouteSurfaceState.live => colors.primary,
      AppRouteSurfaceState.partiallyWired => colors.secondary,
      AppRouteSurfaceState.placeholder => colors.tertiary,
      AppRouteSurfaceState.hidden => colors.outline,
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: spacingSM, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.35)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
          color: color,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}
