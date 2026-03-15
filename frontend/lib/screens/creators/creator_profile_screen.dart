import 'package:flutter/material.dart';

import '../../controllers/creator_controller.dart';
import '../../models/creator_models.dart';
import '../../widgets/creators/creator_finance_summary_card.dart';
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
      appBar: AppBar(title: const Text('Creator profile deck')),
      body: AnimatedBuilder(
        animation: widget.controller,
        builder: (BuildContext context, _) {
          if (widget.controller.isLoading && !widget.controller.hasData) {
            return const Padding(
              padding: EdgeInsets.all(20),
              child: GteStatePanel(
                eyebrow: 'CREATOR PROFILE',
                title: 'Loading creator profile deck',
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
                eyebrow: 'CREATOR PROFILE',
                title: 'Creator profile deck unavailable',
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
                  eyebrow: 'PROFILE SIGNAL',
                  title: 'Shape a creator identity that feels trusted, promotable, and ready for matchday traffic.',
                  message: 'This profile deck keeps public links, creator momentum, and competition summaries in one presentation layer so the creator lane feels as premium as market and wallet.',
                  icon: Icons.person_pin_circle_outlined,
                  accentColor: Color(0xFF9C6BFF),
                ),
                const SizedBox(height: 16),
                CreatorHeaderCard(profile: profile),
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
                      Text(
                        'PUBLIC CREATOR LINK',
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
                        'CREATOR COMPETITION HISTORY',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 16),
                      if (profile.competitions.isEmpty)
                        const GteStatePanel(
                          eyebrow: 'MATCHDAY RECORD',
                          title: 'No published creator competitions yet.',
                          message: 'Once this creator starts hosting competitions, the archive will appear here with season labels, participation cues, and live-state context.',
                          icon: Icons.history_toggle_off_outlined,
                          accentColor: Color(0xFF9C6BFF),
                        )
                      else
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
