import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../app_routes/gte_navigation_helpers.dart';
import '../app_routes/gte_route_data.dart';
import '../navigation_guards/gte_navigation_guards.dart';
import '../../widgets/gte_metric_chip.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';
import 'live_match_overview_provider.dart';
import 'match_3d_route_screen.dart';
import 'match_broadcast_screen.dart';
import 'match_viewer_route_screen.dart';

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
        appBar: AppBar(title: const Text('Matchday hub')),
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
                      Text(
                        '$_resolvedClubName matchday is now routed into the live product lanes.',
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Open the tactical 2D viewer, the broadcast package, or the Flutter 3D lane from one honest hub. Player trading, regen discovery, and transfer planning stay one tap away from the same surface.',
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
                                    ? 'Fallback signal'
                                    : 'Live matchday',
                          ),
                          GteMetricChip(
                            label: 'Viewer lanes',
                            value: '2D + Broadcast + 3D',
                          ),
                          const GteMetricChip(
                            label: 'Wallet rail',
                            value: 'GTEX Coin',
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
                            label: const Text('Player market'),
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
                            label: const Text('Regen universe'),
                          ),
                          FilledButton.tonalIcon(
                            onPressed:
                                () => GteNavigationHelpers.pushRoute<void>(
                                  context,
                                  route: const FootballTransferCenterRouteData(),
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
                ...entries.map(
                  (_MatchLaneEntry entry) => Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: _MatchLaneCard(
                      entry: entry,
                      onOpenTwoD:
                          () => _openRouteScreen(
                            context,
                            MatchViewerRouteScreen(matchKey: entry.matchKey),
                          ),
                      onOpenBroadcast:
                          () => _openRouteScreen(
                            context,
                            MatchBroadcastScreen(matchKey: entry.matchKey),
                          ),
                      onOpenThreeD:
                          () => _openRouteScreen(
                            context,
                            Match3dRouteScreen(matchKey: entry.matchKey),
                          ),
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
                      'Checking the live broadcast desk before opening the routed 2D, broadcast, and Flutter 3D lanes.',
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
                          'The shell stays usable by falling back to the routed match lanes directly. You can still enter 2D and Flutter 3D while the broadcast desk catches up.',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                  _MatchLaneCard(
                    entry: _fallbackEntries(_resolvedClubName).first,
                    onOpenTwoD:
                        () => _openRouteScreen(
                          context,
                          const MatchViewerRouteScreen(
                            matchKey: 'fallback-matchday-lane',
                          ),
                        ),
                    onOpenBroadcast:
                        () => _openRouteScreen(
                          context,
                          const MatchBroadcastScreen(
                            matchKey: 'fallback-matchday-lane',
                          ),
                        ),
                    onOpenThreeD:
                        () => _openRouteScreen(
                          context,
                          const Match3dRouteScreen(
                            matchKey: 'fallback-matchday-lane',
                          ),
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
    if (entries.isNotEmpty) {
      return entries;
    }
    return _fallbackEntries(_resolvedClubName);
  }

  List<_MatchLaneEntry> _fallbackEntries(String resolvedClubName) {
    return <_MatchLaneEntry>[
      _MatchLaneEntry(
        matchKey: 'fallback-matchday-lane',
        title: '$resolvedClubName live matchday lane',
        subtitle:
            'Fallback route that still opens the truthful 2D and Flutter 3D viewers while the live desk is syncing.',
        channelLabel: 'Fallback signal',
        isFeatured: true,
        isLive: false,
      ),
    ];
  }

  Future<void> _openRouteScreen(BuildContext context, Widget screen) {
    return Navigator.of(context).push<void>(
      MaterialPageRoute<void>(builder: (BuildContext context) => screen),
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
  const _MatchLaneCard({
    required this.entry,
    required this.onOpenTwoD,
    required this.onOpenBroadcast,
    required this.onOpenThreeD,
  });

  final _MatchLaneEntry entry;
  final VoidCallback onOpenTwoD;
  final VoidCallback onOpenBroadcast;
  final VoidCallback onOpenThreeD;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      accentColor:
          entry.isFeatured
              ? GteShellTheme.accentArena
              : GteShellTheme.accent,
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
              const SizedBox(width: 12),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: <Widget>[
                  _StatusPill(
                    label: entry.isLive ? 'Live' : 'Fallback',
                    accent:
                        entry.isLive
                            ? GteShellTheme.positive
                            : GteShellTheme.accentWarm,
                  ),
                  const SizedBox(height: 8),
                  _StatusPill(
                    label: entry.channelLabel,
                    accent:
                        entry.isFeatured
                            ? GteShellTheme.accentArena
                            : GteShellTheme.accent,
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton.icon(
                onPressed: onOpenTwoD,
                icon: const Icon(Icons.sports_soccer_outlined),
                label: const Text('Open 2D'),
              ),
              FilledButton.tonalIcon(
                onPressed: onOpenBroadcast,
                icon: const Icon(Icons.live_tv_outlined),
                label: const Text('Broadcast'),
              ),
              FilledButton.tonalIcon(
                onPressed: onOpenThreeD,
                icon: const Icon(Icons.view_in_ar_outlined),
                label: const Text('Open 3D'),
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
