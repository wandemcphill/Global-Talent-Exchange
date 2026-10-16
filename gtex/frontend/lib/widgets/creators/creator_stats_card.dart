import 'package:flutter/material.dart';

import '../../models/creator_models.dart';
import '../gte_shell_theme.dart';
import '../gte_surface_panel.dart';

class CreatorStatsCard extends StatelessWidget {
  const CreatorStatsCard({
    super.key,
    required this.stats,
    required this.growthSummary,
    required this.rewardSummary,
  });

  final CreatorStats stats;
  final CreatorGrowthSummary growthSummary;
  final CreatorRewardSummary rewardSummary;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Creator stats',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              _MetricTile(
                label: 'Invites sent',
                value: '${stats.communityInvites}',
              ),
              _MetricTile(
                label: 'Qualified referrals',
                value: '${stats.qualifiedReferrals}',
              ),
              _MetricTile(
                label: 'Creator competitions',
                value: '${stats.creatorCompetitions}',
              ),
              _MetricTile(
                label: 'Contest participants',
                value: '${stats.contestParticipants}',
              ),
            ],
          ),
          const SizedBox(height: 20),
          Text(
            growthSummary.growthHeadline,
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Text(
            growthSummary.growthDetail,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              _Pill(label: growthSummary.weeklyInviteLift),
              _Pill(label: growthSummary.topChannel),
              _Pill(label: growthSummary.inviteAttributionRate),
            ],
          ),
          const SizedBox(height: 20),
          Text(
            'Reward summary',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Text(
            rewardSummary.pendingCommunityRewards,
            style: Theme.of(context).textTheme.bodyLarge,
          ),
          const SizedBox(height: 6),
          Text(
            rewardSummary.lifetimeMilestoneRewards,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 6),
          Text(
            rewardSummary.competitionEntryCredits,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 10),
          Text(
            rewardSummary.ledgerStatus,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: GteShellTheme.accentWarm,
                ),
          ),
        ],
      ),
    );
  }
}

class _MetricTile extends StatelessWidget {
  const _MetricTile({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 152,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: GteShellTheme.stroke),
        color: GteShellTheme.panelStrong.withValues(alpha: 0.72),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            value,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontSize: 22,
                ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ],
      ),
    );
  }
}

class _Pill extends StatelessWidget {
  const _Pill({
    required this.label,
  });

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: GteShellTheme.accent.withValues(alpha: 0.12),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelLarge,
      ),
    );
  }
}
