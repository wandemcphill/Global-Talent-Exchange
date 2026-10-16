import 'package:flutter/material.dart';
import 'package:gte_frontend/models/club_models.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class DynastyMilestoneCard extends StatelessWidget {
  const DynastyMilestoneCard({
    super.key,
    required this.milestone,
  });

  final ClubLegacyMilestone milestone;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Icon(
                milestone.unlocked
                    ? Icons.verified_outlined
                    : Icons.lock_outline,
                color: milestone.unlocked
                    ? GteShellTheme.positive
                    : GteShellTheme.textMuted,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  milestone.title,
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            milestone.subtitle,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(999),
              color: GteShellTheme.panelStrong.withValues(alpha: 0.94),
              border: Border.all(color: GteShellTheme.stroke),
            ),
            child: Text(
              milestone.tagLabel,
              style: Theme.of(context).textTheme.labelLarge,
            ),
          ),
        ],
      ),
    );
  }
}
