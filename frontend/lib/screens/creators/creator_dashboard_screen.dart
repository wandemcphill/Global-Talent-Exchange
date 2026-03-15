import 'package:flutter/material.dart';

import '../../controllers/creator_controller.dart';
import '../../models/creator_models.dart';
import '../../widgets/creators/creator_finance_summary_card.dart';
import '../../widgets/creators/creator_header_card.dart';
import '../../widgets/creators/creator_stats_card.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';
import '../competitions/creator_competition_share_screen.dart';
import 'creator_profile_screen.dart';

class CreatorDashboardScreen extends StatefulWidget {
  const CreatorDashboardScreen({
    super.key,
    required this.controller,
  });

  final CreatorController controller;

  @override
  State<CreatorDashboardScreen> createState() => _CreatorDashboardScreenState();
}

class _CreatorDashboardScreenState extends State<CreatorDashboardScreen> {
  @override
  void initState() {
    super.initState();
    widget.controller.load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Creator command deck'),
        actions: <Widget>[
          TextButton(
            onPressed: () => _openProfile(context),
            child: const Text('Profile'),
          ),
        ],
      ),
      body: AnimatedBuilder(
        animation: widget.controller,
        builder: (BuildContext context, _) {
          if (widget.controller.isLoading && !widget.controller.hasData) {
            return const Padding(
              padding: EdgeInsets.all(20),
              child: GteStatePanel(
                eyebrow: 'CREATOR COMMAND DECK',
                title: 'Loading creator command deck',
                message:
                    'Gathering creator competitions, community invites, and reward summary.',
                icon: Icons.auto_graph_outlined,
              ),
            );
          }
          if (widget.controller.errorMessage != null &&
              !widget.controller.hasData) {
            return Padding(
              padding: const EdgeInsets.all(20),
              child: GteStatePanel(
                eyebrow: 'CREATOR SYSTEMS',
                title: 'Creator command deck unavailable',
                message: widget.controller.errorMessage!,
                icon: Icons.error_outline,
                actionLabel: 'Retry',
                onAction: widget.controller.load,
              ),
            );
          }

          final CreatorProfile profile = widget.controller.profile!;
          return SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                const GteStatePanel(
                  eyebrow: 'CREATOR MATCHDAY DESK',
                  title: 'Run community growth, invite momentum, and reward energy from one polished lane.',
                  message: 'This deck is tuned for hosts and promoters. Use it to track active competitions, share codes, and keep your creator economy moving without losing the premium GTEX rhythm.',
                  icon: Icons.campaign_outlined,
                  accentColor: Color(0xFF9C6BFF),
                ),
                const SizedBox(height: 16),
                CreatorHeaderCard(
                  profile: profile,
                  onShareCodeTap: () => _openCompetitionShare(context, null),
                ),
                const SizedBox(height: 16),
                CreatorStatsCard(
                  stats: profile.stats,
                  growthSummary: profile.growthSummary,
                  rewardSummary: profile.rewardSummary,
                ),
                const SizedBox(height: 16),
                CreatorFinanceSummaryCard(summary: profile.financeSummary),
                const SizedBox(height: 16),
                GteSurfacePanel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Row(
                        children: <Widget>[
                          Expanded(
                            child: Text(
                              'LIVE CREATOR COMPETITIONS',
                              style: Theme.of(context).textTheme.titleLarge,
                            ),
                          ),
                          FilledButton.tonalIcon(
                            onPressed: () => _openProfile(context),
                            icon: const Icon(Icons.person_outline),
                            label: const Text('Open profile'),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      if (profile.competitions.isEmpty)
                        const GteStatePanel(
                          eyebrow: 'COMMUNITY READY',
                          title: 'No creator competitions are live yet.',
                          message: 'Your creator profile is polished and ready. The next published competition will appear here with sharing tools and invite momentum intact.',
                          icon: Icons.celebration_outlined,
                          accentColor: Color(0xFF9C6BFF),
                        )
                      else
                        for (final CreatorCompetition competition
                            in profile.competitions) ...<Widget>[
                        _DashboardCompetitionTile(
                          competition: competition,
                          onOpenShare: () => _openCompetitionShare(
                            context,
                            competition.competitionId,
                          ),
                        ),
                        if (competition != profile.competitions.last)
                          const Divider(height: 28),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Future<void> _openCompetitionShare(
    BuildContext context,
    String? competitionId,
  ) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => CreatorCompetitionShareScreen(
          creatorController: widget.controller,
          competitionId: competitionId,
        ),
      ),
    );
  }

  Future<void> _openProfile(BuildContext context) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => CreatorProfileScreen(
          controller: widget.controller,
        ),
      ),
    );
  }
}

class _DashboardCompetitionTile extends StatelessWidget {
  const _DashboardCompetitionTile({
    required this.competition,
    required this.onOpenShare,
  });

  final CreatorCompetition competition;
  final VoidCallback onOpenShare;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    competition.title,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 6),
                  Text(
                    competition.seasonLabel,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
            FilledButton.icon(
              onPressed: onOpenShare,
              icon: const Icon(Icons.share_outlined),
              label: const Text('Share'),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          competition.inviteWindow,
          style: Theme.of(context).textTheme.bodyLarge,
        ),
        const SizedBox(height: 4),
        Text(
          competition.inviteAttributionLabel,
          style: Theme.of(context).textTheme.bodyMedium,
        ),
        const SizedBox(height: 4),
        Text(
          competition.rewardLabel,
          style: Theme.of(context).textTheme.bodyMedium,
        ),
      ],
    );
  }
}
