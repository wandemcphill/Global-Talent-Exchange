import 'package:flutter/material.dart';

import '../data/gte_exchange_models.dart';
import '../providers/gte_exchange_controller.dart';
import '../widgets/gte_formatters.dart';
import '../widgets/gte_metric_chip.dart';
import '../widgets/gte_state_panel.dart';
import '../widgets/gte_surface_panel.dart';

class GteMarketPlayersScreen extends StatefulWidget {
  const GteMarketPlayersScreen({
    super.key,
    required this.controller,
    required this.onOpenPlayer,
    required this.onOpenLogin,
  });

  final GteExchangeController controller;
  final ValueChanged<String> onOpenPlayer;
  final VoidCallback onOpenLogin;

  @override
  State<GteMarketPlayersScreen> createState() => _GteMarketPlayersScreenState();
}

class _GteMarketPlayersScreenState extends State<GteMarketPlayersScreen> {
  late final TextEditingController _searchController;

  @override
  void initState() {
    super.initState();
    _searchController =
        TextEditingController(text: widget.controller.marketSearch);
    _searchController.addListener(_handleSearchChanged);
  }

  @override
  void dispose() {
    _searchController.removeListener(_handleSearchChanged);
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _refresh,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            GteSurfacePanel(
              emphasized: true,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('Market players',
                      style: Theme.of(context).textTheme.headlineSmall),
                  const SizedBox(height: 8),
                  Text(
                    'Browse tradable players, then drill into quotes, candles, and the order ticket from one flow.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 18),
                  TextField(
                    controller: _searchController,
                    decoration: InputDecoration(
                      hintText: 'Search player, club, nationality, or position',
                      suffixIconConstraints: const BoxConstraints(minWidth: 96),
                      suffixIcon: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: <Widget>[
                          if (_searchController.text.isNotEmpty)
                            IconButton(
                              onPressed: () {
                                _searchController.clear();
                                _refresh();
                              },
                              icon: const Icon(Icons.close),
                              tooltip: 'Clear search',
                            ),
                          IconButton(
                            onPressed: widget.controller.isLoadingMarket
                                ? null
                                : _refresh,
                            icon: const Icon(Icons.search),
                            tooltip: 'Search',
                          ),
                        ],
                      ),
                    ),
                    onSubmitted: (_) => _refresh(),
                  ),
                  const SizedBox(height: 18),
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: <Widget>[
                      GteMetricChip(
                        label: 'Visible',
                        value: widget.controller.players.length.toString(),
                      ),
                      GteMetricChip(
                        label: 'Total',
                        value: (widget.controller.marketPage?.total ?? 0)
                            .toString(),
                      ),
                      GteMetricChip(
                        label: 'Session',
                        value: widget.controller.isAuthenticated
                            ? 'TRADING'
                            : 'GUEST',
                        positive: widget.controller.isAuthenticated,
                      ),
                    ],
                  ),
                  const SizedBox(height: 18),
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: <Widget>[
                      FilledButton.tonalIcon(
                        onPressed:
                            widget.controller.isLoadingMarket ? null : _refresh,
                        icon: const Icon(Icons.refresh),
                        label: const Text('Refresh'),
                      ),
                      if (!widget.controller.isAuthenticated)
                        FilledButton(
                          onPressed: widget.onOpenLogin,
                          child: const Text('Sign in to trade'),
                        )
                      else
                        Text(
                          'Signed in. Wallet, portfolio, and order routes are ready.',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                    ],
                  ),
                ],
              ),
            ),
            if (widget.controller.marketError != null &&
                widget.controller.players.isNotEmpty) ...<Widget>[
              const SizedBox(height: 20),
              GteSurfacePanel(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    const Padding(
                      padding: EdgeInsets.only(top: 2),
                      child: Icon(Icons.warning_amber_rounded),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Showing the last successful market snapshot. ${widget.controller.marketError!}',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ),
                  ],
                ),
              ),
            ],
            const SizedBox(height: 20),
            if (widget.controller.isLoadingMarket &&
                widget.controller.players.isEmpty)
              const Center(
                child: Padding(
                  padding: EdgeInsets.symmetric(vertical: 48),
                  child: CircularProgressIndicator(),
                ),
              )
            else if (widget.controller.marketError != null &&
                widget.controller.players.isEmpty)
              GteStatePanel(
                title: 'Market unavailable',
                message: widget.controller.marketError!,
                actionLabel: 'Retry',
                onAction: _refresh,
                icon: Icons.warning_amber_rounded,
              )
            else if (widget.controller.players.isEmpty)
              GteStatePanel(
                title: 'No players found',
                message: _searchController.text.trim().isEmpty
                    ? 'No players are available right now. Pull to refresh and try again.'
                    : 'No players matched "${_searchController.text.trim()}".',
                actionLabel: _searchController.text.trim().isEmpty
                    ? null
                    : 'Clear search',
                onAction: _searchController.text.trim().isEmpty
                    ? null
                    : () {
                        _searchController.clear();
                        _refresh();
                      },
                icon: Icons.search_off,
              )
            else
              ...widget.controller.players.map(
                (GteMarketPlayerListItem player) => Padding(
                  padding: const EdgeInsets.only(bottom: 16),
                  child: _PlayerCard(
                    player: player,
                    onTap: () => widget.onOpenPlayer(player.playerId),
                  ),
                ),
              ),
            if (widget.controller.isLoadingMoreMarket) ...<Widget>[
              const SizedBox(height: 12),
              const Center(child: CircularProgressIndicator()),
            ] else if (widget.controller.hasMorePlayers) ...<Widget>[
              const SizedBox(height: 4),
              Center(
                child: FilledButton.tonal(
                  onPressed: () {
                    widget.controller.loadMarket(
                      search: _searchController.text,
                      reset: false,
                    );
                  },
                  child: const Text('Load more'),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  void _handleSearchChanged() {
    if (mounted) {
      setState(() {});
    }
  }

  Future<void> _refresh() {
    return widget.controller.loadMarket(
      search: _searchController.text,
      reset: true,
    );
  }
}

class _PlayerCard extends StatelessWidget {
  const _PlayerCard({
    required this.player,
    required this.onTap,
  });

  final GteMarketPlayerListItem player;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      onTap: onTap,
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
                    Text(player.playerName,
                        style: Theme.of(context).textTheme.headlineSmall),
                    const SizedBox(height: 6),
                    Text(
                      <String>[
                        if (player.currentClubName != null)
                          player.currentClubName!,
                        if (player.nationality != null) player.nationality!,
                        if (player.position != null) player.position!,
                        'Age ${player.age}',
                      ].join(' | '),
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 16),
              Text(
                gteFormatCredits(player.currentValueCredits),
                style: Theme.of(context).textTheme.titleLarge,
              ),
            ],
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              GteMetricChip(
                label: 'Move',
                value: gteFormatMovement(player.movementPct),
                positive: player.isRising,
              ),
              GteMetricChip(
                label: 'Trend score',
                value: player.trendScore.toStringAsFixed(1),
              ),
              GteMetricChip(
                label: 'Interest',
                value: player.marketInterestScore.toString(),
              ),
              GteMetricChip(
                label: 'Rating',
                value: player.averageRating?.toStringAsFixed(1) ?? '--',
              ),
            ],
          ),
        ],
      ),
    );
  }
}
