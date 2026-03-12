import 'package:flutter/material.dart';

import '../data/gte_models.dart';
import '../widgets/gte_metric_chip.dart';
import '../widgets/gte_shell_theme.dart';
import '../widgets/gte_surface_panel.dart';
import '../widgets/gte_trend_strip.dart';
import 'gte_app_controller.dart';
import 'gte_player_action_row.dart';

class GtePlayersScreen extends StatelessWidget {
  const GtePlayersScreen({
    super.key,
    required this.controller,
    required this.onOpenPlayer,
  });

  final GteAppController controller;
  final ValueChanged<String> onOpenPlayer;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          GteSurfacePanel(
            emphasized: true,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('Player hub',
                    style: Theme.of(context).textTheme.headlineSmall),
                const SizedBox(height: 8),
                Text(
                  'Scout, track, shortlist, and move premium profiles into the transfer room.',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 18),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: <Widget>[
                    GteMetricChip(
                      label: 'Catalog',
                      value: controller.players.length.toString(),
                    ),
                    GteMetricChip(
                      label: 'Watchlist',
                      value: controller.watchlistPlayers.length.toString(),
                    ),
                    GteMetricChip(
                      label: 'Shortlist',
                      value: controller.shortlistPlayers.length.toString(),
                    ),
                    GteMetricChip(
                      label: 'Transfer room',
                      value: controller.transferRoomPlayers.length.toString(),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          ...controller.players.map(
            (PlayerSnapshot player) => Padding(
              padding: const EdgeInsets.only(bottom: 18),
              child: _PlayerCard(
                player: player,
                controller: controller,
                onOpenPlayer: onOpenPlayer,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _PlayerCard extends StatelessWidget {
  const _PlayerCard({
    required this.player,
    required this.controller,
    required this.onOpenPlayer,
  });

  final PlayerSnapshot player;
  final GteAppController controller;
  final ValueChanged<String> onOpenPlayer;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      onTap: () => onOpenPlayer(player.id),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final bool isWide = constraints.maxWidth >= 720;
              final Widget summary = Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Row(
                    children: <Widget>[
                      Expanded(
                        child: Text(player.name,
                            style: Theme.of(context).textTheme.headlineSmall),
                      ),
                      Text(
                        '${player.marketCredits} cr',
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                              color: GteShellTheme.accent,
                            ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                    '${player.club} - ${player.nation} - ${player.position} - ${player.age}',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 16),
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: <Widget>[
                      GteMetricChip(label: 'GSI', value: player.gsi.toString()),
                      GteMetricChip(
                          label: 'Form',
                          value: player.formRating.toStringAsFixed(1)),
                      GteMetricChip(
                        label: 'Value move',
                        value:
                            '${player.valueDeltaPct > 0 ? '+' : ''}${player.valueDeltaPct.toStringAsFixed(1)}%',
                        positive: player.valueDeltaPct >= 0,
                      ),
                    ],
                  ),
                ],
              );

              final Widget trend = Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('Value trend',
                      style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 12),
                  GteTrendStrip(points: player.valueTrend),
                ],
              );

              if (isWide) {
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Expanded(flex: 3, child: summary),
                    const SizedBox(width: 18),
                    Expanded(flex: 2, child: trend),
                  ],
                );
              }

              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  summary,
                  const SizedBox(height: 18),
                  trend,
                ],
              );
            },
          ),
          const SizedBox(height: 18),
          Text('Recent signals', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          ...player.recentHighlights.map(
            (String highlight) => Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Text('- $highlight',
                  style: Theme.of(context).textTheme.bodyLarge),
            ),
          ),
          const SizedBox(height: 16),
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
    );
  }
}
