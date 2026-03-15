import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/features/competitions_hub/data/competition_hub_curator.dart';
import 'package:gte_frontend/features/competitions_hub/routing/competition_hub_destination.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/screens/competitions/competition_create_screen.dart';
import 'package:gte_frontend/screens/competitions/competition_detail_screen.dart';
import 'package:gte_frontend/widgets/competitions/competition_status_badge.dart';
import 'package:gte_frontend/widgets/competitions/competition_visibility_chip.dart';
import 'package:gte_frontend/widgets/gte_formatters.dart';
import 'package:gte_frontend/widgets/gte_metric_chip.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';
import 'package:gte_frontend/widgets/gte_sync_status_card.dart';
import 'package:gte_frontend/widgets/gtex_branding.dart';

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
              GtexHeroBanner(
                eyebrow: 'E-GAME ARENA',
                title: 'Fixtures, brackets, storylines, and adaptive simulations live here.',
                description: 'This surface is not the trading floor. It is the orchestration deck for leagues, cups, fast leagues, world super cups, and cinematic 3-5 minute match stories.',
                accent: Colors.deepPurpleAccent,
                chips: <Widget>[
                  GteMetricChip(
                    label: 'Visible',
                    value: destination == CompetitionHubDestination.worldSuperCup
                        ? worldSuperCupWatchlist.length.toString()
                        : curated.length.toString(),
                  ),
                  GteMetricChip(label: 'Open now', value: openCount.toString()),
                  GteMetricChip(
                    label: 'Status',
                    value: hasActiveSeason ? 'LIVE' : 'INACTIVE',
                    positive: hasActiveSeason,
                  ),
                ],
                actions: <Widget>[
                  if (!widget.isAuthenticated && widget.onOpenLogin != null)
                    FilledButton.tonalIcon(
                      onPressed: widget.onOpenLogin,
                      icon: const Icon(Icons.login),
                      label: const Text('Sign in for live join access'),
                    ),
                ],
                sidePanel: Container(
                  padding: const EdgeInsets.all(18),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(24),
                    color: Colors.white.withValues(alpha: 0.04),
                    border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Row(
                        children: <Widget>[
                          Icon(destination.icon, color: Colors.deepPurpleAccent.shade100),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(destination.routePath, style: Theme.of(context).textTheme.titleMedium),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Text(destination.hubDescription, style: Theme.of(context).textTheme.bodyMedium),
                      const SizedBox(height: 14),
                      Text('Arena promise', style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 8),
                      Text('Adaptive qualification, realistic match probabilities, key moments, injuries, and manager fingerprints should all show up here in one smooth flow.', style: Theme.of(context).textTheme.bodyMedium),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 20),
              GtexSignalStrip(
                title: 'Live match center',
                subtitle: 'Arena mode tracks which stories are live, which brackets are filling, and which formats are ready to burst into 3-5 minute highlight loops.',
                accent: Colors.deepPurpleAccent,
                tiles: <Widget>[
                  GtexSignalTile(
                    label: 'Featured fixture lane',
                    value: competitions.where((CompetitionSummary item) => item.status == CompetitionStatus.inProgress).isNotEmpty ? 'LIVE NOW' : 'QUEUE READY',
                    caption: competitions.where((CompetitionSummary item) => item.status == CompetitionStatus.inProgress).isNotEmpty
                        ? '${competitions.where((CompetitionSummary item) => item.status == CompetitionStatus.inProgress).length} contests are already in motion.'
                        : 'No active fixture stream yet. Published contests become the next live watchlist.',
                    icon: Icons.live_tv_rounded,
                    color: Colors.deepPurpleAccent,
                  ),
                  GtexSignalTile(
                    label: 'Join pressure',
                    value: openCount > 0 ? '$openCount OPEN' : 'SEALED',
                    caption: 'Open and published competitions stay separate from the market so match-night tension never feels like order entry.',
                    icon: Icons.groups_2_outlined,
                    color: const Color(0xFFFFA3E0),
                  ),
                  GtexSignalTile(
                    label: 'Format spread',
                    value: '${competitions.where((CompetitionSummary item) => item.isLeague).length}L / ${competitions.where((CompetitionSummary item) => item.isCup).length}C',
                    caption: 'Leagues, cups, fast leagues, and future world-stage routes stay visible in one arena stack.',
                    icon: Icons.emoji_events_outlined,
                    color: const Color(0xFF8ED8FF),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              GteSyncStatusCard(
                title: 'Arena systems',
                status: widget.controller.discoveryError == null
                    ? 'Live storylines, bracket states, and replay lanes are humming.'
                    : 'Arena sync degraded. Last good fixture board remains available.',
                syncedAt: widget.controller.discoverySyncedAt,
                accent: Colors.deepPurpleAccent,
                isRefreshing: widget.controller.isLoadingDiscovery,
                onRefresh: widget.controller.loadDiscovery,
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

    final List<CompetitionSummary> liveBoard = competitions
        .where((CompetitionSummary item) => item.status == CompetitionStatus.inProgress || item.status == CompetitionStatus.openForJoin || item.status == CompetitionStatus.published)
        .take(3)
        .toList(growable: false);
    final List<CompetitionSummary> recentlyFinal = competitions
        .where((CompetitionSummary item) => item.status == CompetitionStatus.completed)
        .take(3)
        .toList(growable: false);
    final List<CompetitionSummary> replayLane = featured
        .where((CompetitionSummary item) => item.status == CompetitionStatus.completed)
        .take(2)
        .toList(growable: false);
    final List<CompetitionSummary> gtexCompetitions = competitions
        .where(_isGtexCompetition)
        .take(4)
        .toList(growable: false);
    final List<CompetitionSummary> creatorCompetitions = competitions
        .where((CompetitionSummary item) => !_isGtexCompetition(item))
        .take(4)
        .toList(growable: false);

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
      GteSurfacePanel(
        accentColor: GteShellTheme.accentArena,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Host your own competition',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              'Create a creator competition, publish transparent rules, and share invite codes for private joins.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 14),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: <Widget>[
                FilledButton.icon(
                  onPressed: _openCreateCompetition,
                  icon: const Icon(Icons.add),
                  label: const Text('Host competition'),
                ),
                OutlinedButton.icon(
                  onPressed: () {
                    AppFeedback.showSuccess(
                      context,
                      'Invite codes are generated from the competition detail share screen.',
                    );
                  },
                  icon: const Icon(Icons.share_outlined),
                  label: const Text('Invite/join flow'),
                ),
              ],
            ),
          ],
        ),
      ),
      const SizedBox(height: 20),
      if (liveBoard.isNotEmpty) ...<Widget>[
        const _ArenaSectionHeader(
          eyebrow: 'MATCHDAY BOARD',
          title: 'Live fixture desk',
          description: 'A quick broadcast strip for the stories most likely to spill into highlights, results, and bracket movement.',
        ),
        const SizedBox(height: 12),
        ...liveBoard.map(
          (CompetitionSummary item) => Padding(
            padding: const EdgeInsets.only(bottom: 16),
            child: _LiveFixtureCard(competition: item, onOpen: () => _openCompetition(item.id)),
          ),
        ),
        const SizedBox(height: 4),
      ],
      if (recentlyFinal.isNotEmpty) ...<Widget>[
        const _ArenaSectionHeader(
          eyebrow: 'FINAL WHISTLE',
          title: 'Recently settled',
          description: 'Completed contests stay visible so users can jump from result to replay lane without losing the competition context.',
        ),
        const SizedBox(height: 12),
        ...recentlyFinal.map(
          (CompetitionSummary item) => Padding(
            padding: const EdgeInsets.only(bottom: 16),
            child: _LiveFixtureCard(competition: item, onOpen: () => _openCompetition(item.id)),
          ),
        ),
        const SizedBox(height: 4),
      ],
      if (featured.isEmpty)
        GteStatePanel(
          title: CompetitionHubDestination.overview.emptyTitle,
          message: CompetitionHubDestination.overview.emptyMessage,
          icon: Icons.emoji_events_outlined,
        )
      else
        ...<Widget>[
          if (gtexCompetitions.isNotEmpty) ...<Widget>[
            const _ArenaSectionHeader(
              eyebrow: 'GTEX COMPETITIONS',
              title: 'Platform-run fixtures and promo pools',
              description:
                  'GTEX competitions are funded by promotional pools and follow published rules.',
            ),
            const SizedBox(height: 12),
            ...gtexCompetitions.map(
              (CompetitionSummary item) => Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: _CompetitionCard(
                  competition: item,
                  contextLabel: 'GTEX competition',
                  onOpen: () => _openCompetition(item.id),
                ),
              ),
            ),
            const SizedBox(height: 4),
          ],
          if (creatorCompetitions.isNotEmpty) ...<Widget>[
            const _ArenaSectionHeader(
              eyebrow: 'CREATOR-HOSTED',
              title: 'User-hosted competitions',
              description:
                  'Creator competitions use published rules, transparent payouts, and invite-driven joins.',
            ),
            const SizedBox(height: 12),
            ...creatorCompetitions.map(
              (CompetitionSummary item) => Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: _CompetitionCard(
                  competition: item,
                  contextLabel: 'Creator-hosted',
                  onOpen: () => _openCompetition(item.id),
                ),
              ),
            ),
            const SizedBox(height: 4),
          ],
          if (replayLane.isNotEmpty) ...<Widget>[
            const _ArenaSectionHeader(
              eyebrow: 'REPLAY LANE',
              title: 'Highlight-ready competitions',
              description: 'These contests are the cleanest handoff into 3-5 minute stories, recap reels, and manager-fingerprint review.',
            ),
            const SizedBox(height: 12),
            ...replayLane.map(
              (CompetitionSummary item) => Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: _CompetitionCard(
                  competition: item,
                  contextLabel: 'Replay candidate',
                  onOpen: () => _openCompetition(item.id),
                ),
              ),
            ),
            const SizedBox(height: 4),
          ],
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

    final List<CompetitionSummary> liveNow = competitions
        .where((CompetitionSummary item) => item.status == CompetitionStatus.inProgress)
        .toList(growable: false);
    final List<CompetitionSummary> upNext = competitions
        .where((CompetitionSummary item) => item.status == CompetitionStatus.openForJoin || item.status == CompetitionStatus.published || item.status == CompetitionStatus.filled || item.status == CompetitionStatus.locked)
        .toList(growable: false);
    final List<CompetitionSummary> complete = competitions
        .where((CompetitionSummary item) => item.status == CompetitionStatus.completed)
        .toList(growable: false);

    return <Widget>[
      if (liveNow.isNotEmpty) ...<Widget>[
        _ArenaSectionHeader(
          eyebrow: destination.label.toUpperCase(),
          title: 'Live now',
          description: 'These contests are already in motion and should read like a match center first, not a lobby card.',
        ),
        const SizedBox(height: 12),
        ...liveNow.map(
          (CompetitionSummary item) => Padding(
            padding: const EdgeInsets.only(bottom: 16),
            child: _LiveFixtureCard(competition: item, onOpen: () => _openCompetition(item.id)),
          ),
        ),
        const SizedBox(height: 4),
      ],
      if (upNext.isNotEmpty) ...<Widget>[
        _ArenaSectionHeader(
          eyebrow: destination.label.toUpperCase(),
          title: 'Up next',
          description: 'Open, published, and locked competitions are grouped here so joinability is obvious in one scan.',
        ),
        const SizedBox(height: 12),
        ...upNext.map(
          (CompetitionSummary item) => Padding(
            padding: const EdgeInsets.only(bottom: 16),
            child: _CompetitionCard(
              competition: item,
              contextLabel: destination.label,
              onOpen: () => _openCompetition(item.id),
            ),
          ),
        ),
        const SizedBox(height: 4),
      ],
      if (complete.isNotEmpty) ...<Widget>[
        _ArenaSectionHeader(
          eyebrow: destination.label.toUpperCase(),
          title: 'Results and replays',
          description: 'Settled competitions remain visible for recap, bragging rights, and highlight routing.',
        ),
        const SizedBox(height: 12),
        ...complete.map(
          (CompetitionSummary item) => Padding(
            padding: const EdgeInsets.only(bottom: 16),
            child: _CompetitionCard(
              competition: item,
              contextLabel: 'Final result',
              onOpen: () => _openCompetition(item.id),
            ),
          ),
        ),
      ],
    ];
  }

  Future<void> _openCompetition(String competitionId) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => CompetitionDetailScreen(
          controller: widget.controller,
          competitionId: competitionId,
          isAuthenticated: widget.isAuthenticated,
          onOpenLogin: widget.onOpenLogin,
        ),
      ),
    );
  }

  bool _isGtexCompetition(CompetitionSummary item) {
    final String label = item.creatorLabel.toLowerCase();
    return label.contains('gtex') || label.contains('exchange');
  }

  Future<void> _openCreateCompetition() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => CompetitionCreateScreen(
          controller: widget.controller,
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
              _StatPill(
                label: 'Join state',
                value: _joinStateLabel(competition),
              ),
            ],
          ),
          const SizedBox(height: 16),
          ClipRRect(
            borderRadius: BorderRadius.circular(999),
            child: LinearProgressIndicator(
              value: competition.fillRate.clamp(0, 1),
              minHeight: 8,
              backgroundColor: Colors.white.withValues(alpha: 0.06),
              valueColor: const AlwaysStoppedAnimation<Color>(Colors.deepPurpleAccent),
            ),
          ),
          const SizedBox(height: 10),
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


class _ArenaSectionHeader extends StatelessWidget {
  const _ArenaSectionHeader({required this.eyebrow, required this.title, required this.description});

  final String eyebrow;
  final String title;
  final String description;

  @override
  Widget build(BuildContext context) {
    return GtexSectionHeader(
      eyebrow: eyebrow,
      title: title,
      description: description,
      accent: Colors.deepPurpleAccent,
    );
  }
}

class _LiveFixtureCard extends StatelessWidget {
  const _LiveFixtureCard({required this.competition, required this.onOpen});

  final CompetitionSummary competition;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final bool isLive = competition.status == CompetitionStatus.inProgress;
    final bool isFinal = competition.status == CompetitionStatus.completed;
    final double fillPct = competition.fillRate.clamp(0, 1);
    final Color accent = isFinal
        ? const Color(0xFFFFC86A)
        : isLive
            ? const Color(0xFFFF8CF2)
            : Colors.deepPurpleAccent;
    return GteSurfacePanel(
      onTap: onOpen,
      accentColor: accent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(competition.name, style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 6),
                    Text('${competition.creatorLabel} • ${competition.safeFormatLabel}', style: Theme.of(context).textTheme.bodyMedium),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(999),
                  color: accent.withValues(alpha: 0.14),
                ),
                child: Text(isFinal ? 'FINAL RESULT' : isLive ? 'LIVE MATCH CENTER' : 'UP NEXT', style: Theme.of(context).textTheme.labelLarge?.copyWith(color: accent)),
              ),
            ],
          ),
          const SizedBox(height: 14),
          ClipRRect(
            borderRadius: BorderRadius.circular(999),
            child: LinearProgressIndicator(
              value: fillPct,
              minHeight: 9,
              backgroundColor: Colors.white.withValues(alpha: 0.06),
              valueColor: AlwaysStoppedAnimation<Color>(accent),
            ),
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              _StatPill(label: 'Bracket fill', value: '${(fillPct * 100).round()}%'),
              _StatPill(label: 'Phase', value: isFinal ? 'Replay ready' : isLive ? 'Story active' : 'Join window'),
              _StatPill(label: 'Entry', value: gteFormatCredits(competition.entryFee)),
              _StatPill(label: 'Prize', value: gteFormatCredits(competition.prizePool)),
            ],
          ),
          const SizedBox(height: 14),
          Text(
            isFinal
                ? 'The matchday story is settled. Route users into recap, final standings, and short-form replay context from here.'
                : isLive
                    ? 'Manager fingerprints, probability swings, injuries, and key moments should flow into a compact story reel from here.'
                    : 'This contest is sitting on the launchpad. As soon as it tips into play, it should feel like a separate broadcast product, not a market card.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }
}
