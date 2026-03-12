import 'package:flutter/material.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

import '../data/reputation_models.dart';
import '../widgets/prestige_tier_badge.dart';
import '../widgets/reputation_loading_skeleton.dart';
import 'reputation_controller.dart';

class PrestigeLeaderboardScreen extends StatelessWidget {
  const PrestigeLeaderboardScreen({
    super.key,
    required this.controller,
  });

  final ReputationController controller;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: const Text('Prestige leaderboard'),
        ),
        body: AnimatedBuilder(
          animation: controller,
          builder: (BuildContext context, Widget? child) {
            final PrestigeLeaderboardDto? leaderboard =
                controller.activeLeaderboard;
            if (controller.isLoading && leaderboard == null) {
              return ListView(
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
                children: const <Widget>[
                  ReputationLoadingSkeleton(lines: 4, emphasized: true),
                  SizedBox(height: 18),
                  ReputationLoadingSkeleton(lines: 6),
                ],
              );
            }
            if (controller.errorMessage != null && leaderboard == null) {
              return Padding(
                padding: const EdgeInsets.all(20),
                child: GteStatePanel(
                  title: 'Leaderboard unavailable',
                  message: controller.errorMessage!,
                  actionLabel: 'Retry',
                  onAction: controller.load,
                  icon: Icons.leaderboard,
                ),
              );
            }

            final List<PrestigeLeaderboardEntryDto> entries =
                leaderboard?.entries ?? const <PrestigeLeaderboardEntryDto>[];
            final PrestigeLeaderboardEntryDto? pinned =
                controller.pinnedLeaderboardEntry;

            return RefreshIndicator(
              onRefresh: controller.refresh,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
                children: <Widget>[
                  GteSurfacePanel(
                    emphasized: true,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'Where your club stands',
                          style: Theme.of(context).textTheme.headlineSmall,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Track the clubs setting the prestige pace across every competition cycle.',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                        const SizedBox(height: 18),
                        Wrap(
                          spacing: 10,
                          runSpacing: 10,
                          children: PrestigeLeaderboardScope.values
                              .map(
                                (PrestigeLeaderboardScope scope) => ChoiceChip(
                                  label: Text(scope.label),
                                  selected:
                                      controller.leaderboardScope == scope,
                                  onSelected: (_) =>
                                      controller.setLeaderboardScope(scope),
                                ),
                              )
                              .toList(growable: false),
                        ),
                        if (leaderboard?.note != null) ...<Widget>[
                          const SizedBox(height: 12),
                          Text(
                            leaderboard!.note!,
                            style: Theme.of(context)
                                .textTheme
                                .bodyMedium
                                ?.copyWith(
                                  color: GteShellTheme.accentWarm,
                                ),
                          ),
                        ],
                      ],
                    ),
                  ),
                  if (pinned != null) ...<Widget>[
                    const SizedBox(height: 18),
                    _LeaderboardRow(
                      entry: pinned,
                      highlighted: true,
                      pinned: true,
                    ),
                  ],
                  const SizedBox(height: 18),
                  if (entries.isEmpty)
                    const GteStatePanel(
                      title: 'No leaderboard data',
                      message: 'This scope does not have any clubs yet.',
                      icon: Icons.public_off,
                    )
                  else
                    ...entries
                        .take(ReputationController.leaderboardVisibleLimit)
                        .map(
                          (PrestigeLeaderboardEntryDto entry) => Padding(
                            padding: const EdgeInsets.only(bottom: 14),
                            child: _LeaderboardRow(
                              entry: entry,
                              highlighted: entry.clubId == controller.clubId,
                            ),
                          ),
                        ),
                ],
              ),
            );
          },
        ),
      ),
    );
  }
}

class _LeaderboardRow extends StatelessWidget {
  const _LeaderboardRow({
    required this.entry,
    required this.highlighted,
    this.pinned = false,
  });

  final PrestigeLeaderboardEntryDto entry;
  final bool highlighted;
  final bool pinned;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      emphasized: highlighted,
      child: Row(
        children: <Widget>[
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: highlighted
                  ? GteShellTheme.accent.withValues(alpha: 0.12)
                  : GteShellTheme.panelStrong,
            ),
            child: Center(
              child: Text(
                '#${entry.rank}',
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  children: <Widget>[
                    Expanded(
                      child: Text(
                        entry.clubName,
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                    ),
                    if (pinned)
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(999),
                          color:
                              GteShellTheme.accentWarm.withValues(alpha: 0.12),
                          border: Border.all(
                            color:
                                GteShellTheme.accentWarm.withValues(alpha: 0.3),
                          ),
                        ),
                        child: Text(
                          'Pinned',
                          style:
                              Theme.of(context).textTheme.labelLarge?.copyWith(
                                    color: GteShellTheme.accentWarm,
                                  ),
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  '${entry.regionLabel} - Peak ${entry.highestScore} - ${entry.totalSeasons} seasons',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 12),
                Row(
                  children: <Widget>[
                    PrestigeTierBadge(
                        tier: entry.currentPrestigeTier, compact: true),
                    const Spacer(),
                    Text(
                      '${entry.currentScore}',
                      style: Theme.of(context)
                          .textTheme
                          .headlineSmall
                          ?.copyWith(fontSize: 22),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
