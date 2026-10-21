import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';
import '../theme/gtex_typography.dart';

/// Delegation policy mode (Master Plan Document F8 & G11).
enum GtexDelegationPolicyMode {
  ownerOnly,
  approvalRequired,
  automatic,
}

/// Canonical policy chip displaying staff/boardroom delegation mode
/// (`owner-only`, `approval-required`, `automatic <= cap`).
class GtexPolicyChip extends StatelessWidget {
  const GtexPolicyChip({
    super.key,
    required this.mode,
    this.capLabel,
    this.compact = false,
  });

  /// Resolve a [GtexPolicyChip] from a raw backend delegation string.
  factory GtexPolicyChip.fromBackendMode(
    String? rawMode, {
    Key? key,
    String? capLabel,
    bool compact = false,
  }) {
    final String normalized = (rawMode ?? '').trim().toLowerCase();
    final GtexDelegationPolicyMode resolvedMode = switch (normalized) {
      'automatic' || 'auto' || 'executive_led' =>
        GtexDelegationPolicyMode.automatic,
      'approval_required' || 'balanced' || 'recommend' =>
        GtexDelegationPolicyMode.approvalRequired,
      _ => GtexDelegationPolicyMode.ownerOnly,
    };
    return GtexPolicyChip(
      key: key,
      mode: resolvedMode,
      capLabel: capLabel,
      compact: compact,
    );
  }

  final GtexDelegationPolicyMode mode;
  final String? capLabel;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    final (String label, IconData icon, Color color) = switch (mode) {
      GtexDelegationPolicyMode.ownerOnly => (
        'Owner only',
        Icons.lock_outline_rounded,
        navy.gold500,
      ),
      GtexDelegationPolicyMode.approvalRequired => (
        'Approval required',
        Icons.how_to_reg_outlined,
        navy.warning,
      ),
      GtexDelegationPolicyMode.automatic => (
        (capLabel ?? '').trim().isNotEmpty
            ? 'Automatic <= ${capLabel!.trim()}'
            : 'Automatic',
        Icons.bolt_rounded,
        navy.info,
      ),
    };

    return Semantics(
      label: 'Delegation policy: $label',
      child: Container(
        padding: EdgeInsets.symmetric(
          horizontal: compact ? GtexSpacing.xs : GtexSpacing.sm,
          vertical: compact ? 4 : 6,
        ),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.14),
          borderRadius: BorderRadius.circular(GtexRadius.pill),
          border: Border.all(color: color.withValues(alpha: 0.48)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(icon, size: compact ? 13 : 15, color: color),
            const SizedBox(width: 5),
            Text(
              label,
              style: GtexTypography.numericS(color: color),
            ),
          ],
        ),
      ),
    );
  }
}
