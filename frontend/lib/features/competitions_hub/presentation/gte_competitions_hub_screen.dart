import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/features/competitions_hub/data/competition_hub_curator.dart';
import 'package:gte_frontend/features/competitions_hub/routing/competition_hub_destination.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/screens/competitions/competition_detail_screen.dart';
import 'package:gte_frontend/widgets/competitions/competition_status_badge.dart';
import 'package:gte_frontend/widgets/competitions/competition_visibility_chip.dart';
import 'package:gte_frontend/widgets/gte_formatters.dart';
import 'package:gte_frontend/widgets/gte_metric_chip.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class GteCompetitionsHubScreen extends StatefulWidget {
  const GteCompetitionsHubScreen({
    super.key,
    required this.controller,
    required this.currentDestination,
    required this.onDestinationChanged,
    this.isAuthenticated = false,
    this.onOpenLogin,
  });

  final CompetitionController controller;
  final CompetitionHubDestination currentDestination;
  final ValueChanged<CompetitionHubDestination> onDestinationChanged;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;

  @override
  State<GteCompetitionsHubScreen> createState() =>
      _GteCompetitionsHubScreenState();
}

class _GteCompetitionsHubScreenState extends State<GteCompetitionsHubScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(
      length: CompetitionHubDestination.values.length,
      vsync: this,
      initialIndex: CompetitionHubDestination.values.indexOf(
        widget.currentDestination,
      ),
    );
    widget.controller.bootstrap();
  }

  @override
  void didUpdateWidget(covariant GteCompetitionsHubScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    final int nextIndex = CompetitionHubDestination.values.indexOf(
      widget.currentDestination,
    );
    if (_tabController.index != nextIndex) {
      _tabController.animateTo(nextIndex);
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.controller,
      builder: (BuildContext context, Widget? child) {
        final List<CompetitionSummary> competitions =
            widget.controller.competitions;
        final CompetitionHubDestination destination = widget.currentDestination;
        final List<CompetitionSummary> curated =
            competitionHubCompetitionsForDestination(destination, competitions);
        final List<CompetitionSummary> worldSuperCupWatchlist =
            competitionHubWorldSuperCupWatchlist(competitions);
        final int openCount = competitions
            .where(
              (CompetitionSummary item) =>
                  item.status == CompetitionStatus.openForJoin ||
                  item.status == CompetitionStatus.published,
            )
            .length;
        final bool hasActiveSeason =
            competitionHubHasActiveSeason(destination, competitions);

        return RefreshIndicator(
          onRefresh: widget.controller.loadDiscovery,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
            children: <Widget>[
              GteSurfacePanel(
                emphasized: true,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: <Widget>[
                        Text(
                          'Competitions',
                          style: Theme.of(context).textTheme.headlineSmall,
                        ),
                        Material(
                          color: Colors.transparent,
                          child: Chip(
                            avatar: Icon(destination.icon, size: 18),
                            label: Text(destination.routePath),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Text(
                      destination.hubDescription,
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 18),
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: <Widget>[
                        GteMetricChip(
                          label: 'Visible',
                          value: destination ==
                                  CompetitionHubDestination.worldSuperCup
                              ? worldSuperCupWatchlist.length.toString()
                              : curated.length.toString(),
                        ),
                        GteMetricChip(
                          label: 'Open now',
                          value: openCount.toString(),
                        ),
                        GteMetricChip(
                          label: 'Status',
                          value: hasActiveSeason ? 'LIVE' : 'INACTIVE',
                          positive: hasActiveSeason,
                        ),
                      ],
                    ),
                    if (!widget.isAuthenticated && widget.onOpenLogin != null)
                      Padding(
                        padding: const EdgeInsets.only(top: 18),
                        child: FilledButton.tonalIcon(
                          onPressed: widget.onOpenLogin,
                          icon: const Icon(Icons.login),
                          label: const Text('Sign in for live join access'),
                        ),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              GteSurfacePanel(
                padding: const EdgeInsets.symmetric(vertical: 10),
                child: TabBar(
                  controller: _tabController,
                  isScrollable: true,
                  dividerColor: Colors.transparent,
                  onTap: (int index) {
                    widget.onDestinationChanged(
                      CompetitionHubDestination.values[index],
                    );
                  },
                  tabs: CompetitionHubDestination.values
                      .map(
                        (CompetitionHubDestination value) => Tab(
                          text: value.label,
                          icon: Icon(value.icon, size: 18),
                        ),
                      )
                      .toList(growable: false),
                ),
              ),
              const SizedBox(height: 20),
              if (widget.controller.discoveryError != null &&
                  competitions.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(bottom: 20),
                  child: GteSurfacePanel(
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        const Icon(Icons.info_outline),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            'Showing the last successful competition snapshot. ${widget.controller.discoveryError!}',
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ..._buildDestinationContent(
                context,
                destination: destination,
                curated: curated,
                allCompetitions: competitions,
                worldSuperCupWatchlist: worldSuperCupWatchlist,
              ),
            ],
          ),
        );
      },
    );
  }

  List<Widget> _buildDestinationContent(
    BuildContext context, {
    required CompetitionHubDestination destination,
    required List<CompetitionSummary> curated,
    required List<CompetitionSummary> allCompetitions,
    required List<CompetitionSummary> worldSuperCupWatchlist,
  }) {
    if (widget.controller.isLoadingDiscovery && allCompetitions.isEmpty) {
      return const <Widget>[
        Padding(
          padding: EdgeInsets.symmetric(vertical: 64),
          child: Center(child: CircularProgressIndicator()),
        ),
      ];
    }

    if (widget.controller.discoveryError != null && allCompetitions.isEmpty) {
      return <Widget>[
        GteStatePanel(
          title: 'Competitions hub unavailable',
          message: widget.controller.discoveryError!,
          actionLabel: 'Retry',
          onAction: widget.controller.loadDiscovery,
          icon: Icons.emoji_events_outlined,
        ),
      ];
    }

    switch (destination) {
      case CompetitionHubDestination.overview:
        return _buildOverview(context, allCompetitions);
      case CompetitionHubDestination.worldSuperCup:
        return _buildWorldSuperCup(context, worldSuperCupWatchlist);
      default:
        return _buildCompetitionCollection(
          context,
          destination: destination,
          competitions: curated,
        );
    }
  }

  List<Widget> _buildOverview(
    BuildContext context,
    List<CompetitionSummary> competitions,
  ) {
    final List<CompetitionSummary> featured =
        competitionHubFeaturedCompetitions(competitions);

    return <Widget>[
      GteSurfacePanel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Competition routes',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              'Every destination resolves to a stable route so home shortcuts and future router wiring can target the same hub paths.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 18),
            Wrap(
              spacing: 14,
              runSpacing: 14,
              children: CompetitionHubDestination.values
                  .where(
                    (CompetitionHubDestination value) =>
                        value != CompetitionHubDestination.overview,
                  )
                  .map(
                    (CompetitionHubDestination value) => SizedBox(
                      width: 250,
                      child: _DestinationRouteCard(
                        destination: value,
                        count: value == CompetitionHubDestination.worldSuperCup
                            ? 0
                            : competitionHubCompetitionsForDestination(
                                value,
                                competitions,
                              ).length,
                        isActive: competitionHubHasActiveSeason(
                          value,
                          competitions,
                        ),
                        onTap: () => widget.onDestinationChanged(value),
                      ),
                    ),
                  )
                  .toList(growable: false),
            ),
          ],
        ),
      ),
      const SizedBox(height: 20),
      if (featured.isEmpty)
        GteStatePanel(
          title: CompetitionHubDestination.overview.emptyTitle,
          message: CompetitionHubDestination.overview.emptyMessage,
          icon: Icons.emoji_events_outlined,
        )
      else
        ...<Widget>[
          Text(
            'Featured now',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 12),
          ...featured.map(
            (CompetitionSummary item) => Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: _CompetitionCard(
                competition: item,
                contextLabel: 'Featured competition',
                onOpen: () => _openCompetition(item.id),
              ),
            ),
          ),
        ],
    ];
  }

  List<Widget> _buildWorldSuperCup(
    BuildContext context,
    List<CompetitionSummary> worldSuperCupWatchlist,
  ) {
    return <Widget>[
      GteSurfacePanel(
        emphasized: true,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'World Super Cup',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(
              'The tab stays persistent even while the competition is inactive so future world-stage identity never disappears from the app shell.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 18),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: <Widget>[
                GteMetricChip(
                  label: 'Season',
                  value: 'OFFLINE',
                  positive: false,
                ),
                GteMetricChip(
                  label: 'Route',
                  value: 'PERSISTENT',
                ),
                GteMetricChip(
                  label: 'Watchlist',
                  value: worldSuperCupWatchlist.length.toString(),
                ),
              ],
            ),
            const SizedBox(height: 18),
            FilledButton.tonalIcon(
              onPressed: () {
                widget.onDestinationChanged(
                  CompetitionHubDestination.championsLeague,
                );
              },
              icon: const Icon(Icons.workspace_premium_outlined),
              label: const Text('Open qualifying routes'),
            ),
          ],
        ),
      ),
      const SizedBox(height: 20),
      if (worldSuperCupWatchlist.isEmpty)
        GteStatePanel(
          title: CompetitionHubDestination.worldSuperCup.emptyTitle,
          message: CompetitionHubDestination.worldSuperCup.emptyMessage,
          icon: Icons.public_outlined,
        )
      else
        ...<Widget>[
          Text(
            'Qualifying watchlist',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 12),
          ...worldSuperCupWatchlist.map(
            (CompetitionSummary item) => Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: _CompetitionCard(
                competition: item,
                contextLabel: 'World-stage watchlist',
                onOpen: () => _openCompetition(item.id),
              ),
            ),
          ),
        ],
    ];
  }

  List<Widget> _buildCompetitionCollection(
    BuildContext context, {
    required CompetitionHubDestination destination,
    required List<CompetitionSummary> competitions,
  }) {
    if (competitions.isEmpty) {
      return <Widget>[
        GteStatePanel(
          title: destination.emptyTitle,
          message: destination.emptyMessage,
          icon: destination.icon,
        ),
      ];
    }

    return <Widget>[
      ...competitions.map(
        (CompetitionSummary item) => Padding(
          padding: const EdgeInsets.only(bottom: 16),
          child: _CompetitionCard(
            competition: item,
            contextLabel: destination.label,
            onOpen: () => _openCompetition(item.id),
          ),
        ),
      ),
    ];
  }

  Future<void> _openCompetition(String competitionId) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => CompetitionDetailScreen(
          controller: widget.controller,
          competitionId: competitionId,
        ),
      ),
    );
  }
}

class _DestinationRouteCard extends StatelessWidget {
  const _DestinationRouteCard({
    required this.destination,
    required this.count,
    required this.isActive,
    required this.onTap,
  });

  final CompetitionHubDestination destination;
  final int count;
  final bool isActive;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final String summary = destination == CompetitionHubDestination.worldSuperCup
        ? 'Season inactive'
        : count == 1
            ? '1 competition'
            : '$count competitions';
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
            summary,
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 6),
          Text(
            isActive ? 'Active route' : 'Reserved route',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ],
      ),
    );
  }
}

class _CompetitionCard extends StatelessWidget {
  const _CompetitionCard({
    required this.competition,
    required this.contextLabel,
    required this.onOpen,
  });

  final CompetitionSummary competition;
  final String contextLabel;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      onTap: onOpen,
      child: Column(
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
                      competition.name,
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 6),
                    Text(
                      '$contextLabel | ${competition.creatorLabel}',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 16),
              CompetitionStatusBadge(status: competition.status),
            ],
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              CompetitionVisibilityChip(visibility: competition.visibility),
              Material(
                color: Colors.transparent,
                child: Chip(
                  label: Text(competition.safeFormatLabel),
                ),
              ),
              if (competition.beginnerFriendly == true)
                const Material(
                  color: Colors.transparent,
                  child: Chip(label: Text('Beginner friendly')),
                ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            competition.rulesSummary,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              _StatPill(
                label: 'Entry',
                value: gteFormatCredits(competition.entryFee),
              ),
              _StatPill(
                label: 'Prize pool',
                value: gteFormatCredits(competition.prizePool),
              ),
              _StatPill(
                label: 'Fill',
                value:
                    '${competition.participantCount}/${competition.capacity}',
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: <Widget>[
              FilledButton.tonalIcon(
                onPressed: onOpen,
                icon: const Icon(Icons.open_in_new),
                label: const Text('View'),
              ),
              const Spacer(),
              Text(
                _joinStateLabel(competition),
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _joinStateLabel(CompetitionSummary competition) {
    if (competition.joinEligibility.eligible) {
      return 'Ready to join';
    }
    if (competition.joinEligibility.requiresInvite) {
      return 'Invite required';
    }
    return 'Track details';
  }
}

class _StatPill extends StatelessWidget {
  const _StatPill({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFF2A3A56)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(label, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 4),
          Text(value, style: Theme.of(context).textTheme.titleMedium),
        ],
      ),
    );
  }
}
