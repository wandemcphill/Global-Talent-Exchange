import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/features/competitions_hub/data/competition_hub_curator.dart';
import 'package:gte_frontend/features/competitions_hub/routing/competition_hub_destination.dart';
import 'package:gte_frontend/features/navigation/routing/gte_navigation_route.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/widgets/gte_metric_chip.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class GteHomeScreen extends StatelessWidget {
  const GteHomeScreen({
    super.key,
    required this.controller,
    required this.competitionController,
    required this.onOpenPrimaryDestination,
    required this.onOpenCompetitionDestination,
  });

  final GteExchangeController controller;
  final CompetitionController competitionController;
  final ValueChanged<GtePrimaryDestination> onOpenPrimaryDestination;
  final ValueChanged<CompetitionHubDestination> onOpenCompetitionDestination;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: Listenable.merge(
        <Listenable>[controller, competitionController],
      ),
      builder: (BuildContext context, Widget? child) {
        final List<CompetitionSummary> competitions =
            competitionController.competitions;
        final List<CompetitionSummary> featured =
            competitionHubFeaturedCompetitions(competitions);
        final int openCompetitionCount = competitions
            .where(
              (CompetitionSummary item) =>
                  item.status == CompetitionStatus.openForJoin ||
                  item.status == CompetitionStatus.published,
            )
            .length;

        return RefreshIndicator(
          onRefresh: _refreshHome,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
            children: <Widget>[
              GteSurfacePanel(
                emphasized: true,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Home',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'One launch point for trading, competitions, club identity, and wallet awareness with direct routing into every top-level competition lane.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 18),
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: <Widget>[
                        GteMetricChip(
                          label: 'Market visible',
                          value: (controller.marketPage?.total ?? controller.players.length).toString(),
                        ),
                        GteMetricChip(
                          label: 'Competitions open',
                          value: openCompetitionCount.toString(),
                        ),
                        GteMetricChip(
                          label: 'Session',
                          value:
                              controller.isAuthenticated ? 'SIGNED IN' : 'GUEST',
                          positive: controller.isAuthenticated,
                        ),
                      ],
                    ),
                    const SizedBox(height: 18),
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: <Widget>[
                        FilledButton.tonalIcon(
                          onPressed: () => onOpenPrimaryDestination(
                            GtePrimaryDestination.market,
                          ),
                          icon: Icon(GtePrimaryDestination.market.icon),
                          label: const Text('Open market'),
                        ),
                        FilledButton.tonalIcon(
                          onPressed: () => onOpenPrimaryDestination(
                            GtePrimaryDestination.club,
                          ),
                          icon: Icon(GtePrimaryDestination.club.icon),
                          label: const Text('Open club'),
                        ),
                        FilledButton.tonalIcon(
                          onPressed: () => onOpenPrimaryDestination(
                            GtePrimaryDestination.wallet,
                          ),
                          icon: Icon(GtePrimaryDestination.wallet.icon),
                          label: const Text('Open wallet'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              Text(
                'Competition shortcuts',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 8),
              Text(
                'Home-level deep links target the same competition routes the hub tabs own.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 16),
              Wrap(
                spacing: 14,
                runSpacing: 14,
                children: CompetitionHubDestination.values
                    .map(
                      (CompetitionHubDestination destination) => SizedBox(
                        width: 250,
                        child: _HomeCompetitionShortcutCard(
                          destination: destination,
                          count: switch (destination) {
                            CompetitionHubDestination.overview =>
                              competitions.length,
                            CompetitionHubDestination.worldSuperCup => 0,
                            _ => competitionHubCompetitionsForDestination(
                                destination,
                                competitions,
                              ).length,
                          },
                          onTap: () => onOpenCompetitionDestination(destination),
                        ),
                      ),
                    )
                    .toList(growable: false),
              ),
              const SizedBox(height: 20),
              Text(
                'Featured now',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 12),
              if (competitionController.isLoadingDiscovery && competitions.isEmpty)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 40),
                  child: Center(child: CircularProgressIndicator()),
                )
              else if (competitionController.discoveryError != null &&
                  competitions.isEmpty)
                GteStatePanel(
                  title: 'Competition feed unavailable',
                  message: competitionController.discoveryError!,
                  actionLabel: 'Retry',
                  onAction: competitionController.loadDiscovery,
                  icon: Icons.emoji_events_outlined,
                )
              else if (featured.isEmpty)
                const GteStatePanel(
                  title: 'No featured competitions yet',
                  message:
                      'Once competition inventory is published, the home spotlight cards appear here.',
                  icon: Icons.emoji_events_outlined,
                )
              else
                ...featured.map(
                  (CompetitionSummary item) => Padding(
                    padding: const EdgeInsets.only(bottom: 14),
                    child: GteSurfacePanel(
                      onTap: () => onOpenCompetitionDestination(
                        item.isLeague
                            ? CompetitionHubDestination.leagues
                            : CompetitionHubDestination.gtexFastCup,
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            item.name,
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                          const SizedBox(height: 6),
                          Text(
                            '${item.creatorLabel} | ${item.safeFormatLabel}',
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                          const SizedBox(height: 12),
                          Text(
                            item.rulesSummary,
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                          const SizedBox(height: 14),
                          Material(
                            color: Colors.transparent,
                            child: Chip(
                              label: Text(
                                item.isLeague
                                    ? CompetitionHubDestination.leagues.routePath
                                    : CompetitionHubDestination
                                        .gtexFastCup.routePath,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
            ],
          ),
        );
      },
    );
  }

  Future<void> _refreshHome() async {
    await Future.wait<void>(<Future<void>>[
      controller.loadMarket(reset: true),
      competitionController.loadDiscovery(),
      if (controller.isAuthenticated) controller.refreshAccount(),
    ]);
  }
}

class _HomeCompetitionShortcutCard extends StatelessWidget {
  const _HomeCompetitionShortcutCard({
    required this.destination,
    required this.count,
    required this.onTap,
  });

  final CompetitionHubDestination destination;
  final int count;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final bool isInactive =
        destination == CompetitionHubDestination.worldSuperCup;
    return GteSurfacePanel(
      onTap: onTap,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(destination.icon),
          const SizedBox(height: 12),
          Text(
            destination.label,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 6),
          Text(
            destination.homeDescription,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 14),
          Material(
            color: Colors.transparent,
            child: Chip(
              label: Text(destination.routePath),
            ),
          ),
          const SizedBox(height: 12),
          Text(
            isInactive
                ? 'Persistent inactive tab'
                : count == 1
                    ? '1 visible competition'
                    : '$count visible competitions',
            style: Theme.of(context).textTheme.titleMedium,
          ),
        ],
      ),
    );
  }
}
