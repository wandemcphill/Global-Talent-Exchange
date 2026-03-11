import 'package:flutter/material.dart';

import '../providers/gte_app_controller.dart';
import '../providers/gte_mock_api.dart';
import '../widgets/gte_metric_chip.dart';
import '../widgets/gte_player_action_row.dart';
import '../widgets/gte_shell_theme.dart';
import '../widgets/gte_surface_panel.dart';
import '../widgets/gte_trend_strip.dart';

class GtePlayerDetailScreen extends StatefulWidget {
  const GtePlayerDetailScreen({
    super.key,
    required this.controller,
    required this.playerId,
  });

  final GteAppController controller;
  final String playerId;

  @override
  State<GtePlayerDetailScreen> createState() => _GtePlayerDetailScreenState();
}

class _GtePlayerDetailScreenState extends State<GtePlayerDetailScreen> {
  late Future<void> _loadFuture;

  @override
  void initState() {
    super.initState();
    _loadFuture = widget.controller.openPlayer(widget.playerId);
  }

  @override
  void didUpdateWidget(covariant GtePlayerDetailScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.playerId != widget.playerId) {
      _loadFuture = widget.controller.openPlayer(widget.playerId);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Theme(
      data: GteShellTheme.build(),
      child: Container(
        decoration: gteBackdropDecoration(),
        child: Scaffold(
          appBar: AppBar(
            title: const Text('Player profile'),
          ),
          body: FutureBuilder<void>(
            future: _loadFuture,
            builder: (BuildContext context, AsyncSnapshot<void> snapshot) {
              return AnimatedBuilder(
                animation: widget.controller,
                builder: (BuildContext context, Widget? child) {
                  final PlayerProfile? profile = widget.controller.selectedProfile;
                  final bool hasExpectedProfile =
                      profile != null && profile.snapshot.id == widget.playerId;

                  if (!hasExpectedProfile && snapshot.connectionState != ConnectionState.done) {
                    return const Center(child: CircularProgressIndicator());
                  }

                  if (!hasExpectedProfile) {
                    return Center(
                      child: Text(widget.controller.errorMessage ?? 'Player details unavailable.'),
                    );
                  }

                  return _DetailBody(
                    profile: profile!,
                    controller: widget.controller,
                  );
                },
              );
            },
          ),
        ),
      ),
    );
  }
}

class _DetailBody extends StatelessWidget {
  const _DetailBody({
    required this.profile,
    required this.controller,
  });

  final PlayerProfile profile;
  final GteAppController controller;

  @override
  Widget build(BuildContext context) {
    final PlayerSnapshot player = profile.snapshot;
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 48),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          GteSurfacePanel(
            emphasized: true,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(player.name, style: Theme.of(context).textTheme.displaySmall),
                const SizedBox(height: 8),
                Text(
                  '${player.club} - ${player.nation} - ${player.position} - ${player.age}',
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
                const SizedBox(height: 18),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: <Widget>[
                    GteMetricChip(label: 'Market value', value: '${player.marketCredits} cr'),
                    GteMetricChip(label: 'GSI', value: player.gsi.toString()),
                    GteMetricChip(label: 'Form', value: player.formRating.toStringAsFixed(1)),
                    GteMetricChip(
                      label: 'Weekly move',
                      value: '${player.valueDeltaPct > 0 ? '+' : ''}${player.valueDeltaPct.toStringAsFixed(1)}%',
                      positive: player.valueDeltaPct >= 0,
                    ),
                  ],
                ),
                const SizedBox(height: 18),
                GtePlayerActionRow(
                  player: player,
                  onFollow: () => controller.toggleFollow(player.id),
                  onWatchlist: () => controller.toggleWatchlist(player.id),
                  onShortlist: () => controller.toggleShortlist(player.id),
                  onTransferRoom: () => controller.toggleTransferRoom(player.id),
                  onIntensity: () => controller.cycleNotificationIntensity(player.id),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final bool isWide = constraints.maxWidth >= 920;
              final Widget trends = GteSurfacePanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text('Value trend', style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 12),
                    GteTrendStrip(points: player.valueTrend),
                    const SizedBox(height: 20),
                    Text('GSI trend', style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 12),
                    GteTrendStrip(points: profile.gsiTrend),
                  ],
                ),
              );
              final Widget intelligence = GteSurfacePanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text('Scouting report', style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 10),
                    Text(profile.scoutingReport, style: Theme.of(context).textTheme.bodyLarge),
                    const SizedBox(height: 18),
                    Text('Transfer signal', style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 10),
                    Text(profile.transferSignal, style: Theme.of(context).textTheme.bodyLarge),
                  ],
                ),
              );

              if (isWide) {
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Expanded(child: trends),
                    const SizedBox(width: 20),
                    Expanded(child: intelligence),
                  ],
                );
              }

              return Column(
                children: <Widget>[
                  trends,
                  const SizedBox(height: 20),
                  intelligence,
                ],
              );
            },
          ),
          const SizedBox(height: 20),
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final bool isWide = constraints.maxWidth >= 920;
              final Widget awards = GteSurfacePanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text('Awards timeline', style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 12),
                    ...profile.awards.map(
                      (String item) => Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Text('- $item', style: Theme.of(context).textTheme.bodyLarge),
                      ),
                    ),
                  ],
                ),
              );
              final Widget stats = GteSurfacePanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text('Performance highlights', style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 10,
                      runSpacing: 10,
                      children: profile.statBlocks
                          .map(
                            (String block) => Chip(label: Text(block)),
                          )
                          .toList(growable: false),
                    ),
                    const SizedBox(height: 16),
                    ...player.recentHighlights.map(
                      (String highlight) => Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Text('- $highlight', style: Theme.of(context).textTheme.bodyLarge),
                      ),
                    ),
                  ],
                ),
              );

              if (isWide) {
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Expanded(child: awards),
                    const SizedBox(width: 20),
                    Expanded(child: stats),
                  ],
                );
              }

              return Column(
                children: <Widget>[
                  awards,
                  const SizedBox(height: 20),
                  stats,
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}
