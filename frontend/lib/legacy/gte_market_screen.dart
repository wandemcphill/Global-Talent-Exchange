import 'package:flutter/material.dart';

import '../data/gte_models.dart';
import 'gte_app_controller.dart';
import '../widgets/gte_metric_chip.dart';
import '../widgets/gte_surface_panel.dart';

class GteMarketScreen extends StatelessWidget {
  const GteMarketScreen({
    super.key,
    required this.controller,
    required this.onOpenPlayer,
    required this.onOpenTransferRoom,
  });

  final GteAppController controller;
  final ValueChanged<String> onOpenPlayer;
  final VoidCallback onOpenTransferRoom;

  @override
  Widget build(BuildContext context) {
    final MarketPulse? pulse = controller.marketPulse;

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
                Text('Market hub',
                    style: Theme.of(context).textTheme.headlineSmall),
                const SizedBox(height: 8),
                Text(
                  'Track momentum, follow the transfer room, and move from scouting to acquisition.',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 18),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: <Widget>[
                    GteMetricChip(
                      label: 'Daily volume',
                      value: pulse == null
                          ? '--'
                          : '${pulse.dailyVolumeCredits} cr',
                    ),
                    GteMetricChip(
                      label: 'Momentum',
                      value: pulse == null
                          ? '--'
                          : pulse.marketMomentum.toStringAsFixed(1),
                    ),
                    GteMetricChip(
                      label: 'Watchers',
                      value: pulse?.activeWatchers.toString() ?? '--',
                    ),
                    GteMetricChip(
                      label: 'Live deals',
                      value: pulse?.liveDeals.toString() ?? '--',
                    ),
                  ],
                ),
                const SizedBox(height: 18),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: <Widget>[
                    FilledButton.tonalIcon(
                      onPressed: controller.isRefreshingMarket
                          ? null
                          : () {
                              controller.refreshMarket();
                            },
                      icon: controller.isRefreshingMarket
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.refresh),
                      label: const Text('Refresh pulse'),
                    ),
                    FilledButton(
                      onPressed: onOpenTransferRoom,
                      child: const Text('Open transfer room'),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          if (pulse != null)
            GteSurfacePanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('Live ticker',
                      style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 14),
                  Wrap(
                    spacing: 10,
                    runSpacing: 10,
                    children: pulse.tickers
                        .map((String ticker) => Chip(label: Text(ticker)))
                        .toList(growable: false),
                  ),
                ],
              ),
            ),
          const SizedBox(height: 20),
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final bool isWide = constraints.maxWidth >= 960;
              final Widget trackedBoard = _TrackedBoard(
                title: 'Watchlist pressure',
                players: controller.watchlistPlayers,
                onOpenPlayer: onOpenPlayer,
              );
              final Widget transferPreview = _TransferPreview(
                pulse: pulse,
                onOpenTransferRoom: onOpenTransferRoom,
              );

              if (isWide) {
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Expanded(flex: 3, child: trackedBoard),
                    const SizedBox(width: 20),
                    Expanded(flex: 2, child: transferPreview),
                  ],
                );
              }

              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  trackedBoard,
                  const SizedBox(height: 20),
                  transferPreview,
                ],
              );
            },
          ),
          const SizedBox(height: 20),
          _TrackedBoard(
            title: 'Shortlist conversion',
            players: controller.shortlistPlayers,
            onOpenPlayer: onOpenPlayer,
          ),
        ],
      ),
    );
  }
}

class _TrackedBoard extends StatelessWidget {
  const _TrackedBoard({
    required this.title,
    required this.players,
    required this.onOpenPlayer,
  });

  final String title;
  final List<PlayerSnapshot> players;
  final ValueChanged<String> onOpenPlayer;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 16),
          if (players.isEmpty)
            Text(
              'No players tracked in this lane yet.',
              style: Theme.of(context).textTheme.bodyMedium,
            )
          else
            ...players.map(
              (PlayerSnapshot player) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text(player.name),
                  subtitle: Text(
                      '${player.club} - GSI ${player.gsi} - ${player.marketCredits} cr'),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => onOpenPlayer(player.id),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _TransferPreview extends StatelessWidget {
  const _TransferPreview({
    required this.pulse,
    required this.onOpenTransferRoom,
  });

  final MarketPulse? pulse;
  final VoidCallback onOpenTransferRoom;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Transfer room preview',
              style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 16),
          if (pulse == null)
            Text('Market feed unavailable.',
                style: Theme.of(context).textTheme.bodyMedium)
          else
            ...pulse!.transferRoom.take(3).map(
                  (TransferRoomEntry entry) => Padding(
                    padding: const EdgeInsets.only(bottom: 14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Chip(label: Text(entry.lane)),
                        const SizedBox(height: 8),
                        Text(entry.headline,
                            style: Theme.of(context).textTheme.titleLarge),
                        const SizedBox(height: 4),
                        Text(entry.activity,
                            style: Theme.of(context).textTheme.bodyMedium),
                      ],
                    ),
                  ),
                ),
          const SizedBox(height: 12),
          FilledButton.tonal(
            onPressed: onOpenTransferRoom,
            child: const Text('View full room'),
          ),
        ],
      ),
    );
  }
}
