import 'package:flutter/material.dart';

import '../providers/gte_app_controller.dart';
import '../providers/gte_mock_api.dart';
import '../widgets/gte_metric_chip.dart';
import '../widgets/gte_shell_theme.dart';
import '../widgets/gte_surface_panel.dart';
import '../widgets/gte_trend_strip.dart';

class GteDashboardScreen extends StatelessWidget {
  const GteDashboardScreen({
    super.key,
    required this.controller,
    required this.onOpenPlayer,
    required this.onOpenPlayersTab,
    required this.onOpenMarketTab,
  });

  final GteAppController controller;
  final ValueChanged<String> onOpenPlayer;
  final VoidCallback onOpenPlayersTab;
  final VoidCallback onOpenMarketTab;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
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
                Text(
                  'Global Talent Exchange',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: GteShellTheme.accent,
                    letterSpacing: 1.1,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  'Premium scouting, player value intelligence, and transfer-room discovery in one shell.',
                  style: theme.textTheme.displaySmall,
                ),
                const SizedBox(height: 20),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: <Widget>[
                    GteMetricChip(
                      label: 'Tracked players',
                      value: controller.players.length.toString(),
                    ),
                    GteMetricChip(
                      label: 'Watchlist',
                      value: controller.watchlistPlayers.length.toString(),
                    ),
                    GteMetricChip(
                      label: 'Market momentum',
                      value: pulse == null ? '--' : pulse.marketMomentum.toStringAsFixed(1),
                    ),
                    GteMetricChip(
                      label: 'Live deals',
                      value: pulse?.liveDeals.toString() ?? '--',
                    ),
                  ],
                ),
                const SizedBox(height: 24),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: <Widget>[
                    FilledButton(
                      onPressed: onOpenPlayersTab,
                      child: const Text('Open player hub'),
                    ),
                    FilledButton.tonal(
                      onPressed: onOpenMarketTab,
                      child: const Text('Open market hub'),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final bool isWide = constraints.maxWidth >= 960;
              final Widget featured = _FeaturedPlayersSection(
                players: controller.featuredPlayers,
                onOpenPlayer: onOpenPlayer,
              );
              final Widget market = _MarketPulseSection(
                pulse: pulse,
                onOpenMarketTab: onOpenMarketTab,
              );

              if (isWide) {
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Expanded(flex: 3, child: featured),
                    const SizedBox(width: 20),
                    Expanded(flex: 2, child: market),
                  ],
                );
              }

              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  featured,
                  const SizedBox(height: 20),
                  market,
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}

class _FeaturedPlayersSection extends StatelessWidget {
  const _FeaturedPlayersSection({
    required this.players,
    required this.onOpenPlayer,
  });

  final List<PlayerSnapshot> players;
  final ValueChanged<String> onOpenPlayer;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Featured prospects', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 6),
          Text(
            'High-intent scouting targets with live market movement and GSI trend visibility.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 18),
          ...players.take(3).map(
                (PlayerSnapshot player) => Padding(
                  padding: const EdgeInsets.only(bottom: 14),
                  child: GteSurfacePanel(
                    padding: const EdgeInsets.all(16),
                    onTap: () => onOpenPlayer(player.id),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Row(
                          children: <Widget>[
                            Expanded(
                              child: Text(
                                player.name,
                                style: Theme.of(context).textTheme.titleLarge,
                              ),
                            ),
                            Text(
                              '${player.marketCredits} cr',
                              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                    color: GteShellTheme.accent,
                                  ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Text(
                          '${player.club} - ${player.position} - GSI ${player.gsi}',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                        const SizedBox(height: 14),
                        GteTrendStrip(points: player.valueTrend, height: 56),
                      ],
                    ),
                  ),
                ),
              ),
        ],
      ),
    );
  }
}

class _MarketPulseSection extends StatelessWidget {
  const _MarketPulseSection({
    required this.pulse,
    required this.onOpenMarketTab,
  });

  final MarketPulse? pulse;
  final VoidCallback onOpenMarketTab;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Market pulse', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 14),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              GteMetricChip(
                label: 'Momentum',
                value: pulse == null ? '--' : pulse!.marketMomentum.toStringAsFixed(1),
              ),
              GteMetricChip(
                label: 'Daily volume',
                value: pulse == null ? '--' : '${pulse!.dailyVolumeCredits} cr',
              ),
              GteMetricChip(
                label: 'Hot league',
                value: pulse?.hottestLeague ?? '--',
              ),
            ],
          ),
          const SizedBox(height: 18),
          if (pulse != null)
            ...pulse!.tickers.map(
              (String ticker) => Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Text(ticker, style: Theme.of(context).textTheme.bodyLarge),
              ),
            ),
          const SizedBox(height: 12),
          Align(
            alignment: Alignment.centerLeft,
            child: FilledButton.tonal(
              onPressed: onOpenMarketTab,
              child: const Text('Open transfer room'),
            ),
          ),
        ],
      ),
    );
  }
}
