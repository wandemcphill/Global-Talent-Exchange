import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../app_routes/gte_navigation_helpers.dart';
import '../app_routes/gte_route_data.dart';
import '../navigation_guards/gte_navigation_guards.dart';
import '../../shared/widgets/gtex_premium_panels.dart';
import '../../widgets/gte_metric_chip.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';
import 'live_match_overview_provider.dart';

class GteLiveMatchHubRouteScreen extends ConsumerWidget {
  const GteLiveMatchHubRouteScreen({
    super.key,
    required this.dependencies,
    this.clubId,
    this.clubName,
  });

  final GteNavigationDependencies dependencies;
  final String? clubId;
  final String? clubName;

  String get _resolvedClubName {
    final String trimmed = (clubName ?? '').trim();
    return trimmed.isEmpty ? 'Your club' : trimmed;
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<LiveMatchOverview> overview = ref.watch(
      liveMatchOverviewProvider,
    );
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(title: const Text('Matchday desk')),
        body: overview.when(
          data: (LiveMatchOverview value) {
            final List<_MatchLaneEntry> entries = _resolvedEntries(value);
            return ListView(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
              children: <Widget>[
                GteSurfacePanel(
                  emphasized: true,
                  accentColor: GteShellTheme.accentArena,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Wrap(
                        spacing: 10,
                        runSpacing: 10,
                        children: <Widget>[
                          const GteMetricChip(label: 'Desk', value: 'MATCHDAY'),
                          GteMetricChip(
                            label: 'Club',
                            value: _resolvedClubName.toUpperCase(),
                          ),
                          GteMetricChip(
                            label: 'Live lanes',
                            value: entries.isEmpty ? 'SYNCING' : 'ACTIVE',
                            positive: entries.isNotEmpty,
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      Text(
                        entries.isEmpty
                            ? '$_resolvedClubName matchday is waiting for a backend-authored live lane.'
                            : '$_resolvedClubName matchday is now running through a real broadcast desk.',
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Open the tactical 2D viewer, jump into scouting, and move straight into transfer action without losing the live football mood.',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 16),
                      Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: <Widget>[
                          GteMetricChip(
                            label: 'Runtime',
                            value:
                                value.entries.isEmpty
                                    ? 'Awaiting live feed'
                                    : 'Live matchday',
                          ),
                          GteMetricChip(
                            label: 'Viewer lanes',
                            value: '2D Matchday',
                          ),
                          const GteMetricChip(
                            label: 'Wallet',
                            value: 'Transfer Balance',
                          ),
                          GteMetricChip(
                            label: 'Entries',
                            value: entries.length.toString(),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: <Widget>[
                          FilledButton.icon(
                            onPressed:
                                () => GteNavigationHelpers.pushRoute<void>(
                                  context,
                                  route: const PlayerCardsBrowseRouteData(),
                                  dependencies: dependencies,
                                ),
                            icon: const Icon(Icons.show_chart_outlined),
                            label: const Text('Open transfer market'),
                          ),
                          FilledButton.tonalIcon(
                            onPressed:
                                clubId == null || clubId!.trim().isEmpty
                                    ? null
                                    : () =>
                                        GteNavigationHelpers.pushRoute<void>(
                                          context,
                                          route: WorldClubContextRouteData(
                                            clubId: clubId!.trim(),
                                            clubName: _resolvedClubName,
                                          ),
                                          dependencies: dependencies,
                                        ),
                            icon: const Icon(Icons.auto_awesome_outlined),
                            label: const Text('Scout Prospects'),
                          ),
                          FilledButton.tonalIcon(
                            onPressed:
                                () => GteNavigationHelpers.pushRoute<void>(
                                  context,
                                  route:
                                      const FootballTransferCenterRouteData(),
                                  dependencies: dependencies,
                                ),
                            icon: const Icon(Icons.swap_horiz_outlined),
                            label: const Text('Transfer center'),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                GtexLiveTickerBar(
                  accentColor: GteShellTheme.accentArena,
                  items: <String>[
                    if (entries.isEmpty)
                      'Arena pulse is waiting for the backend to publish a live fixture stream',
                    if (entries.isNotEmpty)
                      '${entries.length} matchday lanes are primed for broadcast',
                    if (entries.any((_MatchLaneEntry entry) => entry.isLive))
                      'A live fixture is already pushing through the stadium control room',
                    if (entries.every((_MatchLaneEntry entry) => !entry.isLive))
                      'Floodlights are on and the next kickoff is loading into the desk',
                  ],
                ),
                const SizedBox(height: 18),
                if (entries.isEmpty)
                  const Padding(
                    padding: EdgeInsets.only(bottom: 16),
                    child: GteStatePanel(
                      eyebrow: 'MATCHDAY HUB',
                      title: 'Backend live lanes blocked',
                      message:
                          'No backend-authored match lanes are available yet. The 2D match viewer opens only when a real match key is present.',
                      icon: Icons.lock_clock_outlined,
                      accentColor: GteShellTheme.accentWarm,
                    ),
                  ),
                ...entries.map(
                  (_MatchLaneEntry entry) => Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: _MatchLaneCard(
                      entry: entry,
                      onOpenTwoD:
                          () => _openViewerRoute(context, entry.matchKey),
                    ),
                  ),
                ),
              ],
            );
          },
          loading:
              () => const Padding(
                padding: EdgeInsets.all(20),
                child: GteStatePanel(
                  eyebrow: 'MATCHDAY HUB',
                  title: 'Loading matchday lanes',
                  message:
                      'Checking live fixtures before opening the routed 2D matchday view.',
                  icon: Icons.stadium_outlined,
                  accentColor: GteShellTheme.accentArena,
                  isLoading: true,
                ),
              ),
          error:
              (Object _, StackTrace __) => ListView(
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
                children: <Widget>[
                  GteSurfacePanel(
                    emphasized: true,
                    accentColor: GteShellTheme.accentWarm,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'Live matchday feed degraded',
                          style: Theme.of(context).textTheme.headlineSmall,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'The broadcast-home feed is unavailable. The 2D match viewer stays blocked until a real match lane can be recovered.',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
        ),
      ),
    );
  }

  List<_MatchLaneEntry> _resolvedEntries(LiveMatchOverview overview) {
    final List<_MatchLaneEntry> entries = overview.entries
        .map(
          (LiveMatchOverviewEntry entry) => _MatchLaneEntry(
            matchKey: entry.matchKey,
            title: entry.title,
            subtitle: entry.subtitle,
            channelLabel: entry.channelLabel,
            isFeatured: entry.isFeatured,
            isLive: entry.isLive,
          ),
        )
        .toList(growable: false);
    return entries;
  }

  Future<void> _openViewerRoute(BuildContext context, String matchKey) {
    return GteNavigationHelpers.pushRoute<void>(
      context,
      route: LiveMatchViewerRouteData(matchKey: matchKey),
      dependencies: dependencies,
    );
  }
}

class _MatchLaneEntry {
  const _MatchLaneEntry({
    required this.matchKey,
    required this.title,
    required this.subtitle,
    required this.channelLabel,
    required this.isFeatured,
    required this.isLive,
  });

  final String matchKey;
  final String title;
  final String subtitle;
  final String channelLabel;
  final bool isFeatured;
  final bool isLive;
}

class _MatchLaneCard extends StatelessWidget {
  const _MatchLaneCard({required this.entry, required this.onOpenTwoD});

  final _MatchLaneEntry entry;
  final VoidCallback onOpenTwoD;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      accentColor:
          entry.isFeatured ? GteShellTheme.accentArena : GteShellTheme.accent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              _StatusPill(
                label: entry.isLive ? 'Live now' : 'Standby',
                accent:
                    entry.isLive
                        ? GteShellTheme.positive
                        : GteShellTheme.accentWarm,
              ),
              _StatusPill(
                label: entry.channelLabel,
                accent:
                    entry.isFeatured
                        ? GteShellTheme.accentArena
                        : GteShellTheme.accent,
              ),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      entry.title,
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      entry.subtitle,
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: List<Widget>.generate(
              4,
              (int index) => Expanded(
                child: Container(
                  height: 6,
                  margin: EdgeInsets.only(right: index == 3 ? 0 : 8),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(999),
                    color:
                        index < (entry.isLive ? 4 : 2)
                            ? (entry.isFeatured
                                    ? GteShellTheme.accentArena
                                    : GteShellTheme.accent)
                                .withValues(alpha: 0.92 - (index * 0.16))
                            : Colors.white.withValues(alpha: 0.08),
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton.icon(
                onPressed: onOpenTwoD,
                icon: const Icon(Icons.sports_soccer_outlined),
                label: const Text('Open live viewer'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _StatusPill extends StatelessWidget {
  const _StatusPill({required this.label, required this.accent});

  final String label;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: accent.withValues(alpha: 0.12),
        border: Border.all(color: accent.withValues(alpha: 0.28)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
          color: accent,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}
