import 'package:flutter/material.dart';

import '../../controllers/creator_controller.dart';
import '../../models/creator_models.dart';
import '../../widgets/creators/creator_header_card.dart';
import '../../widgets/creators/creator_stats_card.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';

class CreatorProfileScreen extends StatefulWidget {
  const CreatorProfileScreen({
    super.key,
    required this.controller,
  });

  final CreatorController controller;

  @override
  State<CreatorProfileScreen> createState() => _CreatorProfileScreenState();
}

class _CreatorProfileScreenState extends State<CreatorProfileScreen> {
  @override
  void initState() {
    super.initState();
    widget.controller.load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Creator profile')),
      body: AnimatedBuilder(
        animation: widget.controller,
        builder: (BuildContext context, _) {
          if (widget.controller.isLoading && !widget.controller.hasData) {
            return const Padding(
              padding: EdgeInsets.all(20),
              child: GteStatePanel(
                title: 'Loading creator profile',
                message:
                    'Pulling creator competitions and community growth summary.',
                icon: Icons.person_search_outlined,
              ),
            );
          }
          if (widget.controller.errorMessage != null &&
              !widget.controller.hasData) {
            return Padding(
              padding: const EdgeInsets.all(20),
              child: GteStatePanel(
                title: 'Creator profile unavailable',
                message: widget.controller.errorMessage!,
                icon: Icons.error_outline,
              ),
            );
          }

          final CreatorProfile profile = widget.controller.profile!;
          return SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                CreatorHeaderCard(profile: profile),
                const SizedBox(height: 16),
                CreatorStatsCard(
                  stats: profile.stats,
                  growthSummary: profile.growthSummary,
                  rewardSummary: profile.rewardSummary,
                ),
                const SizedBox(height: 16),
                GteSurfacePanel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Creator profile link',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 8),
                      SelectableText(
                        profile.profileLink,
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                GteSurfacePanel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Creator competitions',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 16),
                      for (final CreatorCompetition competition
                          in profile.competitions) ...<Widget>[
                        _CompetitionSummaryTile(competition: competition),
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
}

class _CompetitionSummaryTile extends StatelessWidget {
  const _CompetitionSummaryTile({
    required this.competition,
  });

  final CreatorCompetition competition;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            Expanded(
              child: Text(
                competition.title,
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ),
            Chip(
              label: Text(competition.isLive ? 'Live now' : 'Upcoming'),
            ),
          ],
        ),
        const SizedBox(height: 6),
        Text(
          competition.seasonLabel,
          style: Theme.of(context).textTheme.bodyMedium,
        ),
        const SizedBox(height: 6),
        Text(
          competition.inviteAttributionLabel,
          style: Theme.of(context).textTheme.bodyLarge,
        ),
        const SizedBox(height: 4),
        Text(
          competition.participationLabel,
          style: Theme.of(context).textTheme.bodyMedium,
        ),
      ],
    );
  }
}
