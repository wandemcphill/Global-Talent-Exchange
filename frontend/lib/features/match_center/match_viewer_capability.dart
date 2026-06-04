import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../core/constants/app_spacing.dart';
import '../../widgets/gte_shell_theme.dart';

enum MatchViewerCapability { twoD, legacyRuntime, blocked }

extension MatchViewerCapabilityLabel on MatchViewerCapability {
  String get label {
    return switch (this) {
      MatchViewerCapability.twoD => '2D',
      MatchViewerCapability.legacyRuntime => 'QUARANTINED',
      MatchViewerCapability.blocked => 'BLOCKED',
    };
  }

  Color color(BuildContext context) {
    final theme = GteShellTheme.definitionOf(context);
    final tokens = GteShellTheme.tokensOf(context);
    return switch (this) {
      MatchViewerCapability.twoD => theme.primaryColor,
      MatchViewerCapability.legacyRuntime => tokens.negative,
      MatchViewerCapability.blocked => tokens.negative,
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
    final Color color = capability.color(context);
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: spacingSM, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(tokens.radiusPill),
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
