import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../core/constants/app_spacing.dart';

enum MatchViewerCapability { twoD, pseudo3d, flutter3d, native3d, blocked }

extension MatchViewerCapabilityLabel on MatchViewerCapability {
  String get label {
    return switch (this) {
      MatchViewerCapability.twoD => '2D',
      MatchViewerCapability.pseudo3d => 'PSEUDO_3D',
      MatchViewerCapability.flutter3d => 'FLUTTER_3D',
      MatchViewerCapability.native3d => 'NATIVE_3D',
      MatchViewerCapability.blocked => 'BLOCKED',
    };
  }

  Color color(ColorScheme colors) {
    return switch (this) {
      MatchViewerCapability.twoD => colors.primary,
      MatchViewerCapability.pseudo3d => colors.secondary,
      MatchViewerCapability.flutter3d => colors.tertiary,
      MatchViewerCapability.native3d => colors.primaryContainer,
      MatchViewerCapability.blocked => colors.error,
    };
  }
}

class MatchViewerCapabilityBadge extends StatelessWidget {
  const MatchViewerCapabilityBadge({super.key, required this.capability});

  final MatchViewerCapability capability;

  @override
  Widget build(BuildContext context) {
    if (!kDebugMode) {
      return const SizedBox.shrink();
    }
    final ColorScheme colors = Theme.of(context).colorScheme;
    final Color color = capability.color(colors);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: spacingSM, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.35)),
      ),
      child: Text(
        capability.label,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
          color: color,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}
