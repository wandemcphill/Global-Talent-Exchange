import 'package:flutter/material.dart';

import '../data/gte_exchange_models.dart';
import '../providers/gte_exchange_controller.dart';
import '../widgets/gte_formatters.dart';
import '../widgets/gte_metric_chip.dart';
import '../widgets/gte_shell_theme.dart';
import '../widgets/gte_sync_status_card.dart';
import '../widgets/gte_state_panel.dart';
import '../widgets/gte_surface_panel.dart';
import '../widgets/gtex_branding.dart';

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

enum _MarketLens { all, risers, fallers, highInterest }

class _GteMarketPlayersScreenState extends State<GteMarketPlayersScreen> {
  late final TextEditingController _searchController;
  _MarketLens _selectedLens = _MarketLens.all;

  @override
  void initState() {
    super.initState();
    _searchController = TextEditingController(text: widget.controller.marketSearch);
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
            GtexHeroBanner(
              eyebrow: 'TRADING FLOOR',
              title: 'A football asset terminal built for speed, conviction, and clean execution.',
              description: 'Trade mode stays dense and analytical. Quotes, movement, liquidity signals, and player profiles take center stage while the e-game arena lives on a different wavelength.',
              accent: GteShellTheme.accent,
              chips: <Widget>[
                GteMetricChip(label: 'Visible', value: _filteredPlayers.length.toString()),
                GteMetricChip(label: 'Tape size', value: (widget.controller.marketPage?.total ?? 0).toString()),
                GteMetricChip(
                  label: 'Session',
                  value: widget.controller.isAuthenticated ? 'LIVE' : 'PREVIEW',
                  positive: widget.controller.isAuthenticated,
                ),
                GteMetricChip(label: 'Lens', value: _lensLabel(_selectedLens)),
              ],
              actions: <Widget>[
                FilledButton.tonalIcon(
                  onPressed: widget.controller.isLoadingMarket ? null : _refresh,
                  icon: const Icon(Icons.refresh),
                  label: const Text('Refresh tape'),
                ),
                if (!widget.controller.isAuthenticated)
                  FilledButton.icon(
                    onPressed: widget.onOpenLogin,
                    icon: const Icon(Icons.login),
                    label: const Text('Sign in to trade'),
                  ),
              ],
              sidePanel: Column(
                children: <Widget>[
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
                            ),
                          IconButton(
                            onPressed: widget.controller.isLoadingMarket ? null : _refresh,
                            icon: const Icon(Icons.search),
                          ),
                        ],
                      ),
                    ),
                    onSubmitted: (_) => _refresh(),
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: <Widget>[
                      Expanded(
                        child: _MiniTerminalTile(
                          label: 'Execution',
                          value: widget.controller.isAuthenticated ? 'ARMED' : 'LOGIN',
                          accent: GteShellTheme.accent,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: _MiniTerminalTile(
                          label: 'Wallet link',
                          value: widget.controller.walletSummary == null ? 'PENDING' : 'SYNCED',
                          accent: GteShellTheme.accentWarm,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
            GtexSignalStrip(
              title: 'Desk pulse',
              subtitle: 'Trade mode keeps a tighter heartbeat than the arena. These signals tell you whether the tape is rising, cooling, or just waiting for better liquidity.',
              accent: GteShellTheme.accent,
              tiles: <Widget>[
                GtexSignalTile(
                  label: 'Momentum bias',
                  value: _deskBiasLabel(widget.controller.players),
                  caption: 'A quick read on whether more visible assets are being bid up or leaning into softer offers.',
                  icon: Icons.trending_up_rounded,
                  color: GteShellTheme.accent,
                ),
                GtexSignalTile(
                  label: 'Coverage',
                  value: '${widget.controller.players.length} TRACKED',
                  caption: 'What you see on this tape is scan-first. Thin books stay visible instead of being airbrushed away.',
                  icon: Icons.view_kanban_outlined,
                  color: GteShellTheme.accentWarm,
                ),
                GtexSignalTile(
                  label: 'Execution posture',
                  value: widget.controller.isAuthenticated ? 'ORDER ENTRY READY' : 'SCOUT MODE',
                  caption: 'Sign-in unlocks order tickets, wallet linkage, and portfolio-aware confirmation flows.',
                  icon: Icons.bolt_outlined,
                  color: const Color(0xFF8DD9FF),
                ),
              ],
            ),
            const SizedBox(height: 20),
            GteSyncStatusCard(
              title: 'Tape health',
              status: widget.controller.marketError == null
                  ? 'Price discovery, scouting context, and execution hints are in rhythm.'
                  : 'Feed degraded. Last confirmed tape remains visible for review.',
              syncedAt: widget.controller.marketSyncedAt,
              accent: GteShellTheme.accent,
              isRefreshing: widget.controller.isLoadingMarket,
              onRefresh: _refresh,
            ),
            const SizedBox(height: 20),
            const GtexSectionHeader(
              eyebrow: 'MARKET LENS',
              title: 'Focus the tape before you dive into individual assets.',
              description: 'The lens bar keeps the trading floor tight. Filter for risers, dips, or high-interest names without drifting into arena-style browsing.',
              accent: GteShellTheme.accent,
            ),
            const SizedBox(height: 14),
            _MarketLensBar(
              selectedLens: _selectedLens,
              counts: _MarketLensCounts.fromPlayers(widget.controller.players),
              onSelected: (_MarketLens lens) {
                setState(() {
                  _selectedLens = lens;
                });
              },
            ),
            const SizedBox(height: 20),
            const GtexSectionHeader(
              eyebrow: 'DESK CONTEXT',
              title: 'Read the tape before you place conviction behind a click.',
              description: 'These notes keep the trading floor honest about liquidity, execution posture, and how much of the price is truly tradable right now.',
              accent: GteShellTheme.accent,
            ),
            const SizedBox(height: 14),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: <Widget>[
                _DeskSignalCard(
                  title: 'Tape mood',
                  body: widget.controller.players.isEmpty ? 'Waiting for price feed.' : 'Quotes are flowing and the desk is scan-ready.',
                ),
                _DeskSignalCard(
                  title: 'Liquidity note',
                  body: 'Thin books stay visible instead of being disguised. You can see where conviction is real.',
                ),
                _DeskSignalCard(
                  title: 'Execution policy',
                  body: 'Guests can scout the tape. Signed-in users get order entry, wallet context, and portfolio sync.',
                ),
              ],
            ),
            if (widget.controller.marketError != null && widget.controller.players.isNotEmpty) ...<Widget>[
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
            GtexSectionHeader(
              eyebrow: 'PRICE BOARD',
              title: _filteredPlayers.isEmpty ? 'The board needs another look.' : 'Scan the board and pick your next entry.',
              description: _filteredPlayers.isEmpty
                  ? 'When the market is thin, the app keeps the state explicit instead of pretending the tape is full. Refresh, widen the lens, or clear the search to keep moving.'
                  : 'Trading cards stay compact, signal-rich, and execution-aware so the floor feels different from the live match center.',
              accent: GteShellTheme.accent,
            ),
            const SizedBox(height: 14),
            if (widget.controller.isLoadingMarket && widget.controller.players.isEmpty)
              const GteSurfacePanel(
                accentColor: GteShellTheme.accent,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    GtexSectionBadge(label: 'LOADING TAPE', color: GteShellTheme.accent),
                    SizedBox(height: 14),
                    LinearProgressIndicator(),
                    SizedBox(height: 14),
                    Text('Refreshing player discovery, liquidity hints, and the latest visible movement so the board opens with a clean snapshot.'),
                  ],
                ),
              )
            else if (widget.controller.marketError != null && widget.controller.players.isEmpty)
              GteStatePanel(
                title: 'Market unavailable',
                message: 'The trading floor could not confirm a fresh board. ${widget.controller.marketError!}',
                actionLabel: 'Retry board',
                onAction: _refresh,
                icon: Icons.warning_amber_rounded,
              )
            else if (_filteredPlayers.isEmpty)
              GteStatePanel(
                title: 'No players match this tape view',
                message: _searchController.text.trim().isEmpty
                    ? 'This lens is currently quiet. Switch the market lens or pull to refresh the board.'
                    : 'No players matched "${_searchController.text.trim()}" in the ${_lensLabel(_selectedLens).toLowerCase()} view.',
                actionLabel: _searchController.text.trim().isEmpty ? 'Reset lens' : 'Clear search',
                onAction: () {
                  if (_searchController.text.trim().isNotEmpty) {
                    _searchController.clear();
                  }
                  setState(() {
                    _selectedLens = _MarketLens.all;
                  });
                  _refresh();
                },
                icon: Icons.search_off,
              )
            else
              ..._filteredPlayers.map(
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
                    widget.controller.loadMarket(search: _searchController.text, reset: false);
                  },
                  child: const Text('Load more from tape'),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }


  List<GteMarketPlayerListItem> get _filteredPlayers {
    final List<GteMarketPlayerListItem> players = widget.controller.players;
    switch (_selectedLens) {
      case _MarketLens.risers:
        return players.where((GteMarketPlayerListItem player) => player.movementPct > 0).toList(growable: false);
      case _MarketLens.fallers:
        return players.where((GteMarketPlayerListItem player) => player.movementPct < 0).toList(growable: false);
      case _MarketLens.highInterest:
        return players.where((GteMarketPlayerListItem player) => player.marketInterestScore >= 70).toList(growable: false);
      case _MarketLens.all:
        return players;
    }
  }

  String _lensLabel(_MarketLens lens) {
    switch (lens) {
      case _MarketLens.all:
        return 'FULL TAPE';
      case _MarketLens.risers:
        return 'RISERS';
      case _MarketLens.fallers:
        return 'DIPS';
      case _MarketLens.highInterest:
        return 'HEAT';
    }
  }

  void _handleSearchChanged() {
    if (mounted) {
      setState(() {});
    }
  }

  Future<void> _refresh() {
    return widget.controller.loadMarket(search: _searchController.text, reset: true);
  }
}

String _deskBiasLabel(List<GteMarketPlayerListItem> players) {
  if (players.isEmpty) {
    return 'WAITING';
  }
  final int risers = players.where((GteMarketPlayerListItem player) => player.isRising).length;
  final int fallers = players.length - risers;
  if (risers == fallers) {
    return 'BALANCED';
  }
  return risers > fallers ? 'RISK ON' : 'COOLING';
}


class _MarketLensBar extends StatelessWidget {
  const _MarketLensBar({
    required this.selectedLens,
    required this.counts,
    required this.onSelected,
  });

  final _MarketLens selectedLens;
  final _MarketLensCounts counts;
  final ValueChanged<_MarketLens> onSelected;

  @override
  Widget build(BuildContext context) {
    final List<({String label, _MarketLens lens, String value})> options = <({String label, _MarketLens lens, String value})>[
      (label: 'All tape', lens: _MarketLens.all, value: counts.total.toString()),
      (label: 'Risers', lens: _MarketLens.risers, value: counts.risers.toString()),
      (label: 'Dips', lens: _MarketLens.fallers, value: counts.fallers.toString()),
      (label: 'Heat', lens: _MarketLens.highInterest, value: counts.highInterest.toString()),
    ];
    return GteSurfacePanel(
      padding: const EdgeInsets.all(14),
      child: Wrap(
        spacing: 10,
        runSpacing: 10,
        children: options
            .map(
              (({String label, _MarketLens lens, String value}) option) => ChoiceChip(
                label: Text('${option.label} ${option.value}'),
                selected: selectedLens == option.lens,
                onSelected: (_) => onSelected(option.lens),
              ),
            )
            .toList(growable: false),
      ),
    );
  }
}

class _MarketLensCounts {
  const _MarketLensCounts({
    required this.total,
    required this.risers,
    required this.fallers,
    required this.highInterest,
  });

  final int total;
  final int risers;
  final int fallers;
  final int highInterest;

  factory _MarketLensCounts.fromPlayers(List<GteMarketPlayerListItem> players) {
    return _MarketLensCounts(
      total: players.length,
      risers: players.where((GteMarketPlayerListItem player) => player.movementPct > 0).length,
      fallers: players.where((GteMarketPlayerListItem player) => player.movementPct < 0).length,
      highInterest: players.where((GteMarketPlayerListItem player) => player.marketInterestScore >= 70).length,
    );
  }
}

class _PlayerCard extends StatelessWidget {
  const _PlayerCard({required this.player, required this.onTap});

  final GteMarketPlayerListItem player;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final Color movementColor = player.isRising ? GteShellTheme.positive : GteShellTheme.negative;
    final String demandLabel = player.marketInterestScore >= 80
        ? 'HEAVY FLOW'
        : player.marketInterestScore >= 55
            ? 'ACTIVE FLOW'
            : 'THIN FLOW';
    final bool looksIlliquid = player.marketInterestScore < 35 && player.trendScore < 4;
    return GteSurfacePanel(
      onTap: onTap,
      accentColor: movementColor,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(player.playerName, style: Theme.of(context).textTheme.headlineSmall),
                    const SizedBox(height: 6),
                    Text(
                      <String>[
                        if (player.currentClubName != null) player.currentClubName!,
                        if (player.nationality != null) player.nationality!,
                        if (player.position != null) player.position!,
                        'Age ${player.age}',
                      ].join(' • '),
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 16),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: <Widget>[
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(999),
                      color: looksIlliquid
                          ? GteShellTheme.accentWarm.withValues(alpha: 0.12)
                          : movementColor.withValues(alpha: 0.1),
                    ),
                    child: Text(
                      looksIlliquid ? 'THIN BOOK' : demandLabel,
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(
                            color: looksIlliquid ? GteShellTheme.accentWarm : movementColor,
                          ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(gteFormatCredits(player.currentValueCredits), style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 6),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(999),
                      color: movementColor.withValues(alpha: 0.12),
                    ),
                    child: Text(
                      gteFormatMovement(player.movementPct),
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(color: movementColor),
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: <Widget>[
              Expanded(
                child: _MicroBookStat(
                  label: 'Trend pressure',
                  value: player.trendScore >= 7 ? 'ACCELERATING' : player.trendScore >= 4 ? 'BUILDING' : 'QUIET',
                  color: movementColor,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _MicroBookStat(
                  label: 'Scout demand',
                  value: player.marketInterestScore >= 70 ? 'HEAVY' : player.marketInterestScore >= 40 ? 'ACTIVE' : 'LIGHT',
                  color: GteShellTheme.accentWarm,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(22),
              color: Colors.white.withValues(alpha: 0.03),
              border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
            ),
            child: Wrap(
              spacing: 12,
              runSpacing: 12,
              children: <Widget>[
                GteMetricChip(label: 'Trend score', value: player.trendScore.toStringAsFixed(1)),
                GteMetricChip(label: 'Interest', value: player.marketInterestScore.toString()),
                GteMetricChip(label: 'Flow', value: demandLabel),
                GteMetricChip(label: 'Rating', value: player.averageRating?.toStringAsFixed(1) ?? '--'),
                GteMetricChip(label: 'Market state', value: player.isRising ? 'BID UP' : 'CHECK OFFER', positive: player.isRising),
              ],
            ),
          ),
          const SizedBox(height: 14),
          Row(
            children: <Widget>[
              Expanded(
                child: Text(
                  looksIlliquid
                      ? 'Liquidity looks light. Open the detail view to inspect quote quality, spreads, and timing before you commit.'
                      : player.isRising
                          ? 'Momentum is tilting upward. Open the detail view for quote depth and order entry.'
                          : 'Price is cooling. Open the detail view to inspect quote quality and timing.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
              const SizedBox(width: 12),
              const Icon(Icons.arrow_forward, size: 18),
            ],
          ),
        ],
      ),
    );
  }
}

class _DeskSignalCard extends StatelessWidget {
  const _DeskSignalCard({required this.title, required this.body});

  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 280,
      child: GteSurfacePanel(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(title, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Text(body, style: Theme.of(context).textTheme.bodySmall),
          ],
        ),
      ),
    );
  }
}

class _MicroBookStat extends StatelessWidget {
  const _MicroBookStat({required this.label, required this.value, required this.color});

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        color: color.withValues(alpha: 0.08),
        border: Border.all(color: color.withValues(alpha: 0.18)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(label, style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 6),
          Text(value, style: Theme.of(context).textTheme.titleMedium?.copyWith(color: color)),
        ],
      ),
    );
  }
}

class _MiniTerminalTile extends StatelessWidget {
  const _MiniTerminalTile({required this.label, required this.value, required this.accent});

  final String label;
  final String value;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        color: Colors.white.withValues(alpha: 0.04),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(label, style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 6),
          Text(value, style: Theme.of(context).textTheme.titleMedium?.copyWith(color: accent)),
        ],
      ),
    );
  }
}
