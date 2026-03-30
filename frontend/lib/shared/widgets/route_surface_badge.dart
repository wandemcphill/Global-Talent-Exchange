import 'package:flutter/material.dart';

import '../../core/constants/app_spacing.dart';
import '../../widgets/gte_shell_theme.dart';
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
    final theme = GteShellTheme.definitionOf(context);
    final tokens = GteShellTheme.tokensOf(context);
    final Color color = switch (state) {
      AppRouteSurfaceState.live => theme.primaryColor,
      AppRouteSurfaceState.partiallyWired => theme.secondaryColor,
      AppRouteSurfaceState.placeholder => theme.accentColor,
      AppRouteSurfaceState.hidden => tokens.stroke,
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: spacingSM, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(tokens.radiusPill),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
          color: color,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}
