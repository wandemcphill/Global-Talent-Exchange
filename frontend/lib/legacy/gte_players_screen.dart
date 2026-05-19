import 'package:flutter/material.dart';

import '../core/widgets/player_card.dart';
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
                Text(
                  'Player hub',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
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
              child: _LegacyPlayerTile(
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

class _LegacyPlayerTile extends StatelessWidget {
  const _LegacyPlayerTile({
    required this.player,
    required this.controller,
    required this.onOpenPlayer,
  });

  final PlayerSnapshot player;
  final GteAppController controller;
  final ValueChanged<String> onOpenPlayer;

  @override
  Widget build(BuildContext context) {
    return PlayerCard(
      name: player.name,
      rating: player.gsi,
      image: '',
      position: player.position,
      subtitle: '${player.club} | ${player.nation} | Age ${player.age}',
      accentColor: GteShellTheme.accent,
      layout: PlayerCardLayout.horizontal,
      onTap: () => onOpenPlayer(player.id),
      badgeLabels: <String>[player.position, player.nation],
      metrics: <PlayerCardMetric>[
        PlayerCardMetric(label: 'GSI', value: player.gsi.toString()),
        PlayerCardMetric(
          label: 'Form',
          value: player.formRating.toStringAsFixed(1),
        ),
        PlayerCardMetric(
          label: 'Value move',
          value:
              '${player.valueDeltaPct > 0 ? '+' : ''}${player.valueDeltaPct.toStringAsFixed(1)}%',
        ),
        PlayerCardMetric(label: 'Market', value: '${player.marketCredits} cr'),
      ],
      footer: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Value trend', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          GteTrendStrip(points: player.valueTrend),
          const SizedBox(height: 18),
          Text('Recent signals', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          ...player.recentHighlights.map(
            (String highlight) => Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Text(
                '- $highlight',
                style: Theme.of(context).textTheme.bodyLarge,
              ),
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
