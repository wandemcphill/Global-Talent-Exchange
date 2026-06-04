import 'package:flutter/material.dart';
import 'package:gte_frontend/features/app_routes/gte_navigation_helpers.dart';
import 'package:gte_frontend/features/app_routes/gte_route_data.dart';
import 'package:gte_frontend/features/compete/domain/competition_bracket_models.dart';
import 'package:gte_frontend/features/compete/domain/competition_hub_destination.dart';
import 'package:gte_frontend/features/compete/domain/competition_models.dart';
import 'package:gte_frontend/features/compete/presentation/screens/competition_create_screen.dart';
import 'package:gte_frontend/features/compete/presentation/screens/competition_detail_screen.dart';
import 'package:gte_frontend/features/compete/providers/competition_controller.dart';
import 'package:gte_frontend/features/compete/providers/competition_hub_curator.dart';
import 'package:gte_frontend/features/compete/widgets/competition_bracket_widgets.dart';
import 'package:gte_frontend/features/match_center/match_viewer_route_screen.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class GteCompeteBracketScreen extends StatefulWidget {
  const GteCompeteBracketScreen({
    super.key,
    required this.controller,
    required this.currentDestination,
    required this.onDestinationChanged,
    this.isAuthenticated = false,
    this.isCheckingCreatorAccess = false,
    this.canHostCompetitions = false,
    this.onOpenLogin,
    this.onOpenCreatorAccessRequest,
    this.navigationDependencies,
  });

  final CompetitionController controller;
  final CompetitionHubDestination currentDestination;
  final ValueChanged<CompetitionHubDestination> onDestinationChanged;
  final bool isAuthenticated;
  final bool isCheckingCreatorAccess;
  final bool canHostCompetitions;
  final VoidCallback? onOpenLogin;
  final VoidCallback? onOpenCreatorAccessRequest;
  final GteNavigationDependencies? navigationDependencies;

  @override
  State<GteCompeteBracketScreen> createState() =>
      _GteCompeteBracketScreenState();
}

class _GteCompeteBracketScreenState extends State<GteCompeteBracketScreen> {
  @override
  void initState() {
    super.initState();
    widget.controller.bootstrap();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.controller,
      builder: (BuildContext context, Widget? child) {
        final List<CompetitionSummary> competitions =
            widget.controller.competitions;
        final CompetitionHubDestination destination = widget.currentDestination;
        final List<CompetitionSummary> curated = _competitionsForDestination(
          destination,
          competitions,
        );
        final CompetitionSummary? focus = _focusCompetition(curated);

        return RefreshIndicator(
          onRefresh: widget.controller.loadDiscovery,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
            children: <Widget>[
              _CompeteBracketHero(
                destination: destination,
                competitionCount: competitions.length,
                visibleCount: curated.length,
                isRefreshing: widget.controller.isLoadingDiscovery,
                syncedAt: widget.controller.discoverySyncedAt,
                onRefresh: widget.controller.loadDiscovery,
                onCreate: _hostAction(),
                isAuthenticated: widget.isAuthenticated,
              ),
              const SizedBox(height: 18),
              _DestinationSelector(
                currentDestination: destination,
                competitions: competitions,
                onDestinationChanged: widget.onDestinationChanged,
              ),
              const SizedBox(height: 18),
              if (widget.controller.discoveryError != null &&
                  competitions.isEmpty)
                GteStatePanel(
                  title: 'Bracket surface unavailable',
                  message: widget.controller.discoveryError!,
                  actionLabel: 'Retry',
                  onAction: widget.controller.loadDiscovery,
                  icon: Icons.account_tree_outlined,
                )
              else if (widget.controller.isLoadingDiscovery &&
                  competitions.isEmpty)
                const GteStatePanel(
                  title: 'Loading competition brackets',
                  message: 'Waiting for backend competition discovery.',
                  icon: Icons.account_tree_outlined,
                  isLoading: true,
                )
              else if (focus == null)
                GteStatePanel(
                  title: destination.emptyTitle,
                  message: destination.emptyMessage,
                  icon: destination.icon,
                )
              else ...<Widget>[
                _BackendBracketFocus(
                  key: ValueKey<String>('bracket-focus-${focus.id}'),
                  controller: widget.controller,
                  competition: focus,
                  onOpenLiveMatch: _openMatchCenter,
                  onOpenCompetition: () => _openCompetition(focus.id),
                ),
                const SizedBox(height: 20),
                _CompetitionQueue(
                  competitions: curated,
                  activeCompetitionId: focus.id,
                  onOpenCompetition: _openCompetition,
                ),
              ],
            ],
          ),
        );
      },
    );
  }

  List<CompetitionSummary> _competitionsForDestination(
    CompetitionHubDestination destination,
    List<CompetitionSummary> competitions,
  ) {
    if (destination == CompetitionHubDestination.overview) {
      return competitions;
    }
    if (destination == CompetitionHubDestination.worldSuperCup) {
      return competitionHubWorldSuperCupWatchlist(competitions);
    }
    return competitionHubCompetitionsForDestination(destination, competitions);
  }

  CompetitionSummary? _focusCompetition(List<CompetitionSummary> competitions) {
    if (competitions.isEmpty) {
      return null;
    }
    for (final CompetitionStatus status in <CompetitionStatus>[
      CompetitionStatus.inProgress,
      CompetitionStatus.locked,
      CompetitionStatus.filled,
      CompetitionStatus.openForJoin,
      CompetitionStatus.published,
      CompetitionStatus.completed,
    ]) {
      for (final CompetitionSummary competition in competitions) {
        if (competition.status == status) {
          return competition;
        }
      }
    }
    return competitions.first;
  }

  Future<void> _openMatchCenter(String matchKey) async {
    final String resolved = matchKey.trim();
    if (resolved.isEmpty) {
      return;
    }
    final GteNavigationDependencies? dependencies =
        widget.navigationDependencies;
    if (dependencies != null) {
      await GteNavigationHelpers.pushRoute<void>(
        context,
        route: LiveMatchViewerRouteData(matchKey: resolved),
        dependencies: dependencies,
      );
      return;
    }
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (BuildContext context) =>
                MatchViewerRouteScreen(matchKey: resolved),
      ),
    );
  }

  Future<void> _openCompetition(String competitionId) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (BuildContext context) => CompetitionDetailScreen(
              controller: widget.controller,
              competitionId: competitionId,
              isAuthenticated: widget.isAuthenticated,
              onOpenLogin: widget.onOpenLogin,
              navigationDependencies: widget.navigationDependencies,
            ),
      ),
    );
  }

  Future<void> _openCreateCompetition() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (BuildContext context) => CompetitionCreateScreen(
              controller: widget.controller,
              isAuthenticated: widget.isAuthenticated,
              isCheckingHostEligibility: widget.isCheckingCreatorAccess,
              hostEligible:
                  widget.canHostCompetitions || widget.isAuthenticated,
              onOpenLogin: widget.onOpenLogin,
              onOpenCreatorAccessRequest: widget.onOpenCreatorAccessRequest,
            ),
      ),
    );
  }

  VoidCallback? _hostAction() {
    if (!widget.isAuthenticated) {
      return widget.onOpenLogin;
    }
    return _openCreateCompetition;
  }
}

class _CompeteBracketHero extends StatelessWidget {
  const _CompeteBracketHero({
    required this.destination,
    required this.competitionCount,
    required this.visibleCount,
    required this.isRefreshing,
    required this.syncedAt,
    required this.onRefresh,
    required this.onCreate,
    required this.isAuthenticated,
  });

  final CompetitionHubDestination destination;
  final int competitionCount;
  final int visibleCount;
  final bool isRefreshing;
  final DateTime? syncedAt;
  final Future<void> Function() onRefresh;
  final VoidCallback? onCreate;
  final bool isAuthenticated;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      emphasized: true,
      accentColor: GteShellTheme.accentArena,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Icon(destination.icon, color: GteShellTheme.accentArena),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Compete bracket center',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Active competitions now lead with backend bracket truth, published lifecycle state, and canonical match-center handoffs.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              _MetricPill(label: 'All', value: competitionCount.toString()),
              _MetricPill(
                label: destination.label,
                value: visibleCount.toString(),
              ),
              _MetricPill(
                label: 'Sync',
                value: isRefreshing ? 'Loading' : 'Live',
              ),
              if (syncedAt != null)
                _MetricPill(label: 'Updated', value: _timeLabel(syncedAt!)),
            ],
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton.icon(
                onPressed: onCreate,
                icon: Icon(
                  isAuthenticated ? Icons.add_circle_outline : Icons.login,
                ),
                label: Text(isAuthenticated ? 'Create competition' : 'Sign in'),
              ),
              OutlinedButton.icon(
                onPressed: onRefresh,
                icon: const Icon(Icons.sync),
                label: const Text('Refresh brackets'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _timeLabel(DateTime value) {
    final Duration delta = DateTime.now().difference(value);
    if (delta.inMinutes < 1) {
      return 'now';
    }
    if (delta.inHours < 1) {
      return '${delta.inMinutes}m';
    }
    if (delta.inDays < 1) {
      return '${delta.inHours}h';
    }
    return '${delta.inDays}d';
  }
}

class _DestinationSelector extends StatelessWidget {
  const _DestinationSelector({
    required this.currentDestination,
    required this.competitions,
    required this.onDestinationChanged,
  });

  final CompetitionHubDestination currentDestination;
  final List<CompetitionSummary> competitions;
  final ValueChanged<CompetitionHubDestination> onDestinationChanged;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      padding: const EdgeInsets.all(12),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: CompetitionHubDestination.values
              .map((CompetitionHubDestination destination) {
                final int count =
                    destination == CompetitionHubDestination.overview
                        ? competitions.length
                        : destination == CompetitionHubDestination.worldSuperCup
                        ? competitionHubWorldSuperCupWatchlist(
                          competitions,
                        ).length
                        : competitionHubCompetitionsForDestination(
                          destination,
                          competitions,
                        ).length;
                return Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ChoiceChip(
                    selected: currentDestination == destination,
                    avatar: Icon(destination.icon, size: 18),
                    label: Text('${destination.label} ($count)'),
                    onSelected: (_) => onDestinationChanged(destination),
                  ),
                );
              })
              .toList(growable: false),
        ),
      ),
    );
  }
}

class _BackendBracketFocus extends StatefulWidget {
  const _BackendBracketFocus({
    super.key,
    required this.controller,
    required this.competition,
    required this.onOpenLiveMatch,
    required this.onOpenCompetition,
  });

  final CompetitionController controller;
  final CompetitionSummary competition;
  final ValueChanged<String> onOpenLiveMatch;
  final VoidCallback onOpenCompetition;

  @override
  State<_BackendBracketFocus> createState() => _BackendBracketFocusState();
}

class _BackendBracketFocusState extends State<_BackendBracketFocus> {
  late Future<CompetitionBracketPayload?> _payloadFuture;

  @override
  void initState() {
    super.initState();
    _payloadFuture = widget.controller.loadBracketForCompetition(
      widget.competition,
    );
  }

  @override
  void didUpdateWidget(covariant _BackendBracketFocus oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.competition.id != widget.competition.id ||
        oldWidget.controller != widget.controller) {
      _payloadFuture = widget.controller.loadBracketForCompetition(
        widget.competition,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      accentColor: GteShellTheme.accentArena,
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
                      widget.competition.name,
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 6),
                    Text(
                      '${widget.competition.hostSummary} | ${widget.competition.participantCount}/${widget.competition.capacity} entrants',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              OutlinedButton.icon(
                onPressed: widget.onOpenCompetition,
                icon: const Icon(Icons.open_in_new),
                label: const Text('Details'),
              ),
            ],
          ),
          const SizedBox(height: 16),
          FutureBuilder<CompetitionBracketPayload?>(
            future: _payloadFuture,
            builder: (
              BuildContext context,
              AsyncSnapshot<CompetitionBracketPayload?> snapshot,
            ) {
              if (snapshot.connectionState == ConnectionState.waiting &&
                  !snapshot.hasData) {
                return const GteStatePanel(
                  title: 'Loading backend bracket',
                  message: 'Waiting for the published bracket payload.',
                  icon: Icons.account_tree_outlined,
                  isLoading: true,
                );
              }
              if (snapshot.hasError) {
                return GteStatePanel(
                  title: 'Bracket unavailable',
                  message:
                      'Backend bracket payload could not be loaded for this competition.',
                  icon: Icons.account_tree_outlined,
                  actionLabel: 'Retry',
                  onAction: () {
                    setState(() {
                      _payloadFuture = widget.controller
                          .loadBracketForCompetition(widget.competition);
                    });
                  },
                );
              }
              return CompetitionBracketSurface(
                payload: snapshot.data,
                padding: EdgeInsets.zero,
                roundWidth: 270,
                onOpenLiveMatch: widget.onOpenLiveMatch,
              );
            },
          ),
        ],
      ),
    );
  }
}

class _CompetitionQueue extends StatelessWidget {
  const _CompetitionQueue({
    required this.competitions,
    required this.activeCompetitionId,
    required this.onOpenCompetition,
  });

  final List<CompetitionSummary> competitions;
  final String activeCompetitionId;
  final ValueChanged<String> onOpenCompetition;

  @override
  Widget build(BuildContext context) {
    final List<CompetitionSummary> queue = competitions
        .where((CompetitionSummary item) => item.id != activeCompetitionId)
        .take(8)
        .toList(growable: false);
    if (queue.isEmpty) {
      return const SizedBox.shrink();
    }
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Bracket queue', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Text(
            'Open another competition to inspect its backend bracket payload.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 14),
          ...queue.map(
            (CompetitionSummary competition) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: _CompetitionQueueTile(
                competition: competition,
                onOpen: () => onOpenCompetition(competition.id),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _CompetitionQueueTile extends StatelessWidget {
  const _CompetitionQueueTile({
    required this.competition,
    required this.onOpen,
  });

  final CompetitionSummary competition;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        borderRadius: BorderRadius.circular(8),
      ),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        title: Text(competition.name),
        subtitle: Text(
          '${competition.safeFormatLabel} | ${competition.status.name} | ${competition.participantCount}/${competition.capacity}',
        ),
        trailing: TextButton.icon(
          onPressed: onOpen,
          icon: const Icon(Icons.account_tree_outlined),
          label: const Text('Bracket'),
        ),
      ),
    );
  }
}

class _MetricPill extends StatelessWidget {
  const _MetricPill({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Text(label, style: Theme.of(context).textTheme.labelMedium),
            const SizedBox(width: 8),
            Text(value, style: Theme.of(context).textTheme.labelLarge),
          ],
        ),
      ),
    );
  }
}
