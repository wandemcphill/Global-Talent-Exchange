import 'package:flutter/material.dart';
import 'package:gte_frontend/widgets/gte_metric_chip.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

import '../data/reputation_models.dart';
import 'prestige_tier_badge.dart';
import 'reputation_progress_bar.dart';

class ReputationScoreCard extends StatelessWidget {
  const ReputationScoreCard({
    super.key,
    required this.profile,
    required this.clubDisplayName,
    this.globalRank,
    this.regionalRank,
  });

  final ReputationProfileDto profile;
  final String clubDisplayName;
  final PrestigeLeaderboardEntryDto? globalRank;
  final PrestigeLeaderboardEntryDto? regionalRank;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      emphasized: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Wrap(
            spacing: 12,
            runSpacing: 12,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: <Widget>[
              PrestigeTierBadge(tier: profile.currentPrestigeTier),
              Text(
                profile.regionLabel,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              if (profile.lastActiveSeason != null)
                Text(
                  'Last active: S${profile.lastActiveSeason}',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            clubDisplayName,
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 8),
          Text(
            'Reputation score',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 4),
          Text(
            '${profile.currentScore}',
            style: Theme.of(context).textTheme.displaySmall?.copyWith(
                  color: GteShellTheme.textPrimary,
                ),
          ),
          const SizedBox(height: 18),
          ReputationProgressBar(progress: profile.progress),
          const SizedBox(height: 18),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              GteMetricChip(
                label: 'Highest',
                value: '${profile.highestScore}',
              ),
              GteMetricChip(
                label: 'Global rank',
                value: globalRank == null ? '--' : '#${globalRank!.rank}',
              ),
              GteMetricChip(
                label: 'Region rank',
                value: regionalRank == null ? '--' : '#${regionalRank!.rank}',
              ),
            ],
          ),
        ],
      ),
    );
  }
}
