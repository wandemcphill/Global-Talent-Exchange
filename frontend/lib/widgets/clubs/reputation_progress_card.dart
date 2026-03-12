import 'package:flutter/material.dart';
import 'package:gte_frontend/features/club_identity/reputation/data/reputation_models.dart';
import 'package:gte_frontend/models/club_reputation_models.dart';
import 'package:gte_frontend/widgets/clubs/reputation_tier_badge.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class ReputationProgressCard extends StatelessWidget {
  const ReputationProgressCard({
    super.key,
    required this.reputation,
  });

  final ClubReputationSummary reputation;

  @override
  Widget build(BuildContext context) {
    final progress = reputation.profile.progress;
    final String nextTierLabel = progress.nextTier == null
        ? 'Dynasty summit reached'
        : _tierLabel(progress.nextTier!);
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              ReputationTierBadge(tier: reputation.profile.currentPrestigeTier),
              const Spacer(),
              Text(
                '#${reputation.globalRank?.rank ?? '--'} global',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            '${reputation.profile.currentScore}',
            style: Theme.of(context).textTheme.displaySmall,
          ),
          const SizedBox(height: 6),
          Text(
            'Earned prestige toward $nextTierLabel',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          ClipRRect(
            borderRadius: BorderRadius.circular(999),
            child: LinearProgressIndicator(
              value: progress.normalizedProgress,
              minHeight: 10,
              backgroundColor: GteShellTheme.panelStrong,
            ),
          ),
          const SizedBox(height: 12),
          Text(
            progress.pointsToNextTier == null
                ? 'This club is already at the highest visible reputation tier.'
                : '${progress.pointsToNextTier} reputation needed to reach ${_tierLabel(progress.nextTier!)}.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ],
      ),
    );
  }
}

String _tierLabel(PrestigeTier tier) {
  switch (tier) {
    case PrestigeTier.local:
      return 'Local';
    case PrestigeTier.rising:
      return 'Rising';
    case PrestigeTier.established:
      return 'Established';
    case PrestigeTier.elite:
      return 'Elite';
    case PrestigeTier.legendary:
      return 'Legendary';
    case PrestigeTier.dynasty:
      return 'Dynasty';
  }
}
