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
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              _ClubAvatar(name: clubDisplayName),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      clubDisplayName,
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: <Widget>[
                        _MetaPill(label: profile.regionLabel),
                        if (profile.lastActiveSeason != null)
                          _MetaPill(
                            label: 'Last active: S${profile.lastActiveSeason}',
                          ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: <Widget>[
                  Text(
                    'Prestige tier',
                    style: Theme.of(context).textTheme.labelMedium,
                  ),
                  const SizedBox(height: 6),
                  PrestigeTierBadge(tier: profile.currentPrestigeTier),
                ],
              ),
            ],
          ),
          const SizedBox(height: 18),
          Text(
            'Reputation score',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 6),
          Text(
            '${profile.currentScore}',
            style: Theme.of(context).textTheme.displayMedium?.copyWith(
                  color: GteShellTheme.textPrimary,
                  fontWeight: FontWeight.w700,
                  fontSize: 42,
                ),
          ),
          const SizedBox(height: 16),
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

class _ClubAvatar extends StatelessWidget {
  const _ClubAvatar({
    required this.name,
  });

  final String name;

  @override
  Widget build(BuildContext context) {
    final String initials = _clubInitials(name);
    return Container(
      width: 52,
      height: 52,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: LinearGradient(
          colors: <Color>[
            GteShellTheme.accent.withValues(alpha: 0.9),
            GteShellTheme.accentWarm.withValues(alpha: 0.9),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        border: Border.all(
          color: GteShellTheme.accentWarm.withValues(alpha: 0.6),
          width: 1.4,
        ),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: GteShellTheme.accentWarm.withValues(alpha: 0.25),
            blurRadius: 10,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Center(
        child: Text(
          initials,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                color: GteShellTheme.textPrimary,
                fontWeight: FontWeight.w700,
              ),
        ),
      ),
    );
  }
}

class _MetaPill extends StatelessWidget {
  const _MetaPill({
    required this.label,
  });

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: GteShellTheme.panelStrong.withValues(alpha: 0.8),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: GteShellTheme.stroke),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelMedium,
      ),
    );
  }
}

String _clubInitials(String value) {
  final List<String> parts = value
      .split(RegExp(r'\s+'))
      .where((String part) => part.trim().isNotEmpty)
      .toList(growable: false);
  if (parts.isEmpty) {
    return 'CL';
  }
  if (parts.length == 1) {
    final String word = parts.first;
    return word.length >= 2
        ? word.substring(0, 2).toUpperCase()
        : word.substring(0, 1).toUpperCase();
  }
  return '${parts[0][0]}${parts[1][0]}'.toUpperCase();
}
