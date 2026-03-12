import 'package:flutter/material.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

import '../data/reputation_repository.dart';
import '../widgets/milestone_chip.dart';
import '../widgets/mini_prestige_leaderboard.dart';
import '../widgets/reputation_loading_skeleton.dart';
import '../widgets/reputation_score_card.dart';
import '../widgets/reputation_timeline_list.dart';
import 'prestige_leaderboard_screen.dart';
import 'reputation_controller.dart';
import 'reputation_history_screen.dart';

class ClubReputationOverviewScreen extends StatefulWidget {
  const ClubReputationOverviewScreen({
    super.key,
    required this.clubId,
    this.clubName,
    this.baseUrl = 'http://127.0.0.1:8000',
    this.mode = GteBackendMode.liveThenFixture,
    this.repository,
    this.controller,
  });

  final String clubId;
  final String? clubName;
  final String baseUrl;
  final GteBackendMode mode;
  final ReputationRepository? repository;
  final ReputationController? controller;

  @override
  State<ClubReputationOverviewScreen> createState() =>
      _ClubReputationOverviewScreenState();
}

class _ClubReputationOverviewScreenState
    extends State<ClubReputationOverviewScreen> {
  late final ReputationController _controller;
  late final bool _ownsController;

  @override
  void initState() {
    super.initState();
    _ownsController = widget.controller == null;
    _controller = widget.controller ??
        ReputationController(
          repository: widget.repository ??
              ReputationApiRepository.standard(
                baseUrl: widget.baseUrl,
                mode: widget.mode,
              ),
          clubId: widget.clubId,
          clubName: widget.clubName,
        );
    _controller.load();
  }

  @override
  void dispose() {
    if (_ownsController) {
      _controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: const Text('Club reputation'),
        ),
        body: AnimatedBuilder(
          animation: _controller,
          builder: (BuildContext context, Widget? child) {
            if (_controller.isLoading && !_controller.hasData) {
              return const _OverviewLoadingView();
            }
            if (_controller.errorMessage != null && !_controller.hasData) {
              return Padding(
                padding: const EdgeInsets.all(20),
                child: GteStatePanel(
                  title: 'Unable to load club prestige',
                  message: _controller.errorMessage!,
                  actionLabel: 'Retry',
                  onAction: _controller.load,
                  icon: Icons.shield_outlined,
                ),
              );
            }

            final bool wide = MediaQuery.of(context).size.width >= 980;
            return RefreshIndicator(
              onRefresh: _controller.refresh,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
                children: <Widget>[
                  if (_controller.overview != null)
                    ReputationScoreCard(
                      profile: _controller.overview!,
                      clubDisplayName: _controller.displayClubName,
                      globalRank: _controller.globalRankEntry,
                      regionalRank: _controller.regionalRankEntry,
                    ),
                  const SizedBox(height: 18),
                  if (wide)
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Expanded(
                          flex: 6,
                          child: _RecentChangesPanel(controller: _controller),
                        ),
                        const SizedBox(width: 18),
                        Expanded(
                          flex: 5,
                          child: Column(
                            children: <Widget>[
                              _MilestonePanel(controller: _controller),
                              const SizedBox(height: 18),
                              _LeaderboardPreviewPanel(controller: _controller),
                            ],
                          ),
                        ),
                      ],
                    )
                  else ...<Widget>[
                    _RecentChangesPanel(controller: _controller),
                    const SizedBox(height: 18),
                    _MilestonePanel(controller: _controller),
                    const SizedBox(height: 18),
                    _LeaderboardPreviewPanel(controller: _controller),
                  ],
                ],
              ),
            );
          },
        ),
      ),
    );
  }
}

class _RecentChangesPanel extends StatelessWidget {
  const _RecentChangesPanel({
    required this.controller,
  });

  final ReputationController controller;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text('Recent reputation changes',
                        style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 6),
                    Text(
                      'See the stories driving how your club is perceived season after season.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              FilledButton.tonal(
                onPressed: () {
                  Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (BuildContext context) =>
                          ReputationHistoryScreen(
                        controller: controller,
                      ),
                    ),
                  );
                },
                child: const Text('View full history'),
              ),
            ],
          ),
          const SizedBox(height: 18),
          ReputationTimelineList(
            events: controller.recentEvents,
            emptyTitle: 'No reputation history yet',
            emptyMessage:
                'The timeline will populate once the club starts stacking seasons, trophies, and milestones.',
          ),
        ],
      ),
    );
  }
}

class _MilestonePanel extends StatelessWidget {
  const _MilestonePanel({
    required this.controller,
  });

  final ReputationController controller;

  @override
  Widget build(BuildContext context) {
    final List<Widget> milestoneChips = controller.overview?.biggestMilestones
            .map((milestone) => MilestoneChip(milestone: milestone))
            .toList(growable: false) ??
        const <Widget>[];
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Key milestones', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Text(
            'Historic moments and badges that shaped the club aura.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          if (milestoneChips.isEmpty)
            const Text('No milestones unlocked yet.')
          else
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: milestoneChips,
            ),
        ],
      ),
    );
  }
}

class _LeaderboardPreviewPanel extends StatelessWidget {
  const _LeaderboardPreviewPanel({
    required this.controller,
  });

  final ReputationController controller;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: <Widget>[
        MiniPrestigeLeaderboard(
          entries: controller.miniLeaderboardPreview,
          currentClubId: controller.clubId,
          note: controller.activeLeaderboard?.note,
        ),
        const SizedBox(height: 12),
        Align(
          alignment: Alignment.centerRight,
          child: FilledButton.tonalIcon(
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (BuildContext context) => PrestigeLeaderboardScreen(
                    controller: controller,
                  ),
                ),
              );
            },
            icon: const Icon(Icons.leaderboard),
            label: const Text('Open leaderboard'),
          ),
        ),
      ],
    );
  }
}

class _OverviewLoadingView extends StatelessWidget {
  const _OverviewLoadingView();

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: const <Widget>[
        ReputationLoadingSkeleton(emphasized: true, lines: 5),
        SizedBox(height: 18),
        ReputationLoadingSkeleton(lines: 5),
        SizedBox(height: 18),
        ReputationLoadingSkeleton(lines: 4),
      ],
    );
  }
}
