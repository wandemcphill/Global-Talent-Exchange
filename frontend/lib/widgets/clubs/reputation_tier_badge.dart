import 'package:flutter/material.dart';
import 'package:gte_frontend/features/club_identity/reputation/data/reputation_models.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

class ReputationTierBadge extends StatelessWidget {
  const ReputationTierBadge({
    super.key,
    required this.tier,
  });

  final PrestigeTier tier;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: GteShellTheme.accent.withValues(alpha: 0.12),
        border:
            Border.all(color: GteShellTheme.accent.withValues(alpha: 0.28)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(tier.icon, size: 18, color: GteShellTheme.accent),
          const SizedBox(width: 8),
          Text(
            tier.label,
            style: Theme.of(context).textTheme.labelLarge,
          ),
        ],
      ),
    );
  }
}
