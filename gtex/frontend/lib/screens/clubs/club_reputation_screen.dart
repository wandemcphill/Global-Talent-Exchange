import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/features/club_identity/reputation/widgets/reputation_event_tile.dart';
import 'package:gte_frontend/models/club_reputation_models.dart';
import 'package:gte_frontend/widgets/clubs/reputation_progress_card.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class ClubReputationScreen extends StatelessWidget {
  const ClubReputationScreen({
    super.key,
    required this.controller,
  });

  final ClubController controller;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (BuildContext context, _) {
        final ClubReputationSummary? reputation = controller.reputation;
        return Container(
          decoration: gteBackdropDecoration(),
          child: Scaffold(
            backgroundColor: Colors.transparent,
            appBar: AppBar(
              title: const Text('Club reputation'),
            ),
            body: reputation == null
                ? Padding(
                    padding: const EdgeInsets.all(20),
                    child: GteStatePanel(
                      title: 'Club reputation unavailable',
                      message: controller.errorMessage ??
                          'Load the club profile before opening this screen.',
                      icon: Icons.stars_outlined,
                    ),
                  )
                : RefreshIndicator(
                    onRefresh: controller.refresh,
                    child: ListView(
                      physics: const AlwaysScrollableScrollPhysics(),
                      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
                      children: <Widget>[
                        ReputationProgressCard(reputation: reputation),
                        const SizedBox(height: 18),
                        GteSurfacePanel(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Text(
                                'Growth contributors',
                                style: Theme.of(context).textTheme.titleLarge,
                              ),
                              const SizedBox(height: 8),
                              Text(
                                'Earned prestige comes from achievements, trophies, and sustained club identity signals.',
                                style: Theme.of(context).textTheme.bodyMedium,
                              ),
                              const SizedBox(height: 16),
                              ...reputation.contributors.map(
                                (ReputationContribution contribution) =>
                                    Padding(
                                  padding: const EdgeInsets.only(bottom: 12),
                                  child: Row(
                                    children: <Widget>[
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment:
                                              CrossAxisAlignment.start,
                                          children: <Widget>[
                                            Text(
                                              contribution.title,
                                              style: Theme.of(context)
                                                  .textTheme
                                                  .titleMedium,
                                            ),
                                            const SizedBox(height: 4),
                                            Text(
                                              contribution.detail,
                                              style: Theme.of(context)
                                                  .textTheme
                                                  .bodyMedium,
                                            ),
                                          ],
                                        ),
                                      ),
                                      const SizedBox(width: 12),
                                      Text(
                                        '${contribution.delta >= 0 ? '+' : ''}${contribution.delta}',
                                        style: Theme.of(context)
                                            .textTheme
                                            .titleLarge
                                            ?.copyWith(
                                              color: contribution.delta >= 0
                                                  ? GteShellTheme.positive
                                                  : GteShellTheme.negative,
                                            ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 18),
                        Text(
                          'Recent reputation events',
                          style: Theme.of(context).textTheme.headlineSmall,
                        ),
                        const SizedBox(height: 12),
                        ...reputation.recentEvents.map(
                          (event) => Padding(
                            padding: const EdgeInsets.only(bottom: 12),
                            child: ReputationEventTile(event: event),
                          ),
                        ),
                      ],
                    ),
                  ),
          ),
        );
      },
    );
  }
}
