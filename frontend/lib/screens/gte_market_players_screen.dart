import 'package:flutter/material.dart';

import '../features/app_routes/gte_navigation_helpers.dart';
import '../features/app_routes/gte_route_data.dart';
import '../features/navigation_guards/gte_navigation_guards.dart';
import '../shared/widgets/gtex_premium_panels.dart';
import '../data/gte_exchange_models.dart';
import '../data/player_match_service.dart';
import '../providers/gte_exchange_controller.dart';
import '../services/avatar_mapper.dart';
import '../widgets/gte_formatters.dart';
import '../widgets/gte_metric_chip.dart';
import '../widgets/gte_shell_theme.dart';
import '../widgets/gte_sync_status_card.dart';
import '../widgets/gte_state_panel.dart';
import '../widgets/gte_surface_panel.dart';
import '../widgets/market/player_market_avatar.dart';
import '../widgets/gtex_branding.dart';

class GteMarketPlayersScreen extends StatefulWidget {
  const GteMarketPlayersScreen({
    super.key,
    required this.controller,
    required this.onOpenPlayer,
    required this.onOpenLogin,
    this.matchService,
    this.navigationDependencies,
  });

  final GteExchangeController controller;
  final ValueChanged<String> onOpenPlayer;
  final VoidCallback onOpenLogin;
  final GtePlayerMatchService? matchService;
  final GteNavigationDependencies? navigationDependencies;

  @override
  State<GteMarketPlayersScreen> createState() => _GteMarketPlayersScreenState();
}

enum _MarketLens { all, risers, fallers, highInterest }

class _GteMarketPlayersScreenState extends State<GteMarketPlayersScreen> {
  late final TextEditingController _searchController;
  late final TextEditingController _clubController;
  late final TextEditingController _leagueController;
  late final TextEditingController _nationalTeamController;
  _MarketLens _selectedLens = _MarketLens.all;

  @override
  void initState() {
    super.initState();
    _searchController = TextEditingController(
      text: widget.controller.marketSearch,
    );
    _clubController = TextEditingController(text: widget.controller.marketClub);
    _leagueController = TextEditingController(
      text: widget.controller.marketLeague,
    );
    _nationalTeamController = TextEditingController(
      text: widget.controller.marketNationalTeam,
    );
    _searchController.addListener(_handleSearchChanged);
    _clubController.addListener(_handleSearchChanged);
    _leagueController.addListener(_handleSearchChanged);
    _nationalTeamController.addListener(_handleSearchChanged);
  }

  @override
  void dispose() {
    _searchController.removeListener(_handleSearchChanged);
    _clubController.removeListener(_handleSearchChanged);
    _leagueController.removeListener(_handleSearchChanged);
    _nationalTeamController.removeListener(_handleSearchChanged);
    _searchController.dispose();
    _clubController.dispose();
    _leagueController.dispose();
    _nationalTeamController.dispose();
    super.dispose();
  }

  List<String> _marketTickerItems() {
    final List<GteMarketPlayerListItem> players =
        _filteredPlayers.take(8).toList();
    if (players.isEmpty) {
      return const <String>[
        'Scanning global player pool',
        'Liquidity brokers are mapping fresh demand',
        'Scout reports are assembling into the live board',
      ];
    }
    return players
        .map((GteMarketPlayerListItem player) {
          final String trend =
              player.isRising
                  ? 'rising'
                  : (player.marketInterestScore ?? 0) > 72
                  ? 'heavy flow'
                  : 'watchlist';
          final double movement = player.movementPct ?? 0;
          return '${player.playerName} ${movement >= 0 ? '+' : ''}${movement.toStringAsFixed(1)}% · $trend';
        })
        .toList(growable: false);
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _refresh,
      child: SingleChildScrollView(
        key: const ValueKey<String>('trading-floor-scroll'),
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            GtexHeroBanner(
              eyebrow: 'PLAYER MARKET',
              title: 'Scout players and make your next squad move.',
              description:
                  'This is the live football trading floor. Form, club context, value, and movement stay sharp enough to scan quickly while still feeling like the sport is alive.',
              accent: GteShellTheme.accent,
              chips: <Widget>[
                const GteMetricChip(label: 'Board', value: 'REAL PLAYERS'),
                GteMetricChip(
                  label: 'Visible',
                  value:
                      _filteredPlayers.isEmpty
                          ? 'SCANNING'
                          : _filteredPlayers.length.toString(),
                ),
                GteMetricChip(
                  label: 'Pool size',
                  value:
                      (widget.controller.marketPage?.total ?? 0) == 0
                          ? 'WARMING'
                          : (widget.controller.marketPage?.total ?? 0)
                              .toString(),
                ),
                GteMetricChip(
                  label: 'Session',
                  value: widget.controller.isAuthenticated ? 'LIVE' : 'VISITOR',
                  positive: widget.controller.isAuthenticated,
                ),
                GteMetricChip(label: 'Focus', value: _lensLabel(_selectedLens)),
              ],
              actions: <Widget>[
                if (widget.navigationDependencies != null)
                  FilledButton.tonalIcon(
                    onPressed:
                        () => _openFeatureRoute(
                          const PlayerCardsBrowseRouteData(),
                        ),
                    icon: const Icon(Icons.style_outlined),
                    label: const Text('Player universe'),
                  ),
                if (!widget.controller.isAuthenticated)
                  FilledButton.icon(
                    onPressed: widget.onOpenLogin,
                    icon: const Icon(Icons.login),
                    label: const Text('Sign in to make moves'),
                  ),
              ],
              sidePanel: Column(
                children: <Widget>[
                  TextField(
                    controller: _searchController,
                    decoration: InputDecoration(
                      hintText:
                          'Search player, club, league, nationality, or team',
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
                            onPressed:
                                widget.controller.isLoadingMarket
                                    ? null
                                    : _refresh,
                            icon: const Icon(Icons.search),
                          ),
                        ],
                      ),
                    ),
                    onSubmitted: (_) => _refresh(),
                  ),
                  const SizedBox(height: 12),
                  LayoutBuilder(
                    builder: (
                      BuildContext context,
                      BoxConstraints constraints,
                    ) {
                      final bool stacked = constraints.maxWidth < 680;
                      final double fieldWidth =
                          stacked
                              ? constraints.maxWidth
                              : (constraints.maxWidth - 24) / 3;
                      return Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: <Widget>[
                          SizedBox(
                            width: fieldWidth,
                            child: TextField(
                              controller: _clubController,
                              textInputAction: TextInputAction.search,
                              decoration: InputDecoration(
                                labelText: 'Club',
                                hintText: 'Arsenal',
                                prefixIcon: const Icon(Icons.shield_outlined),
                                suffixIcon:
                                    _clubController.text.trim().isEmpty
                                        ? null
                                        : IconButton(
                                          onPressed:
                                              widget.controller.isLoadingMarket
                                                  ? null
                                                  : () =>
                                                      _clearFilterController(
                                                        _clubController,
                                                      ),
                                          icon: const Icon(Icons.close),
                                        ),
                              ),
                              onSubmitted: (_) => _refresh(),
                            ),
                          ),
                          SizedBox(
                            width: fieldWidth,
                            child: TextField(
                              controller: _nationalTeamController,
                              textInputAction: TextInputAction.search,
                              decoration: InputDecoration(
                                labelText: 'National team',
                                hintText: 'Nigeria or Nigeria U20',
                                prefixIcon: const Icon(Icons.flag_outlined),
                                suffixIcon:
                                    _nationalTeamController.text.trim().isEmpty
                                        ? null
                                        : IconButton(
                                          onPressed:
                                              widget.controller.isLoadingMarket
                                                  ? null
                                                  : () =>
                                                      _clearFilterController(
                                                        _nationalTeamController,
                                                      ),
                                          icon: const Icon(Icons.close),
                                        ),
                              ),
                              onSubmitted: (_) => _refresh(),
                            ),
                          ),
                          SizedBox(
                            width: fieldWidth,
                            child: TextField(
                              controller: _leagueController,
                              textInputAction: TextInputAction.search,
                              decoration: InputDecoration(
                                labelText: 'League',
                                hintText: 'Premier League',
                                prefixIcon: const Icon(Icons.public_outlined),
                                suffixIcon:
                                    _leagueController.text.trim().isEmpty
                                        ? null
                                        : IconButton(
                                          onPressed:
                                              widget.controller.isLoadingMarket
                                                  ? null
                                                  : () =>
                                                      _clearFilterController(
                                                        _leagueController,
                                                      ),
                                          icon: const Icon(Icons.close),
                                        ),
                              ),
                              onSubmitted: (_) => _refresh(),
                            ),
                          ),
                        ],
                      );
                    },
                  ),
                  if (_hasActiveStructuredFilters) ...<Widget>[
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: <Widget>[
                        if (_clubController.text.trim().isNotEmpty)
                          InputChip(
                            label: Text('Club: ${_clubController.text.trim()}'),
                            onDeleted:
                                widget.controller.isLoadingMarket
                                    ? null
                                    : () =>
                                        _clearFilterController(_clubController),
                          ),
                        if (_leagueController.text.trim().isNotEmpty)
                          InputChip(
                            label: Text(
                              'League: ${_leagueController.text.trim()}',
                            ),
                            onDeleted:
                                widget.controller.isLoadingMarket
                                    ? null
                                    : () => _clearFilterController(
                                      _leagueController,
                                    ),
                          ),
                        if (_nationalTeamController.text.trim().isNotEmpty)
                          InputChip(
                            label: Text(
                              'National team: ${_nationalTeamController.text.trim()}',
                            ),
                            onDeleted:
                                widget.controller.isLoadingMarket
                                    ? null
                                    : () => _clearFilterController(
                                      _nationalTeamController,
                                    ),
                          ),
                      ],
                    ),
                  ],
                  const SizedBox(height: 16),
                  Row(
                    children: <Widget>[
                      Expanded(
                        child: _MiniTerminalTile(
                          label: 'Access',
                          value:
                              widget.controller.isAuthenticated
                                  ? 'READY'
                                  : 'VISITOR',
                          accent: GteShellTheme.accent,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: _MiniTerminalTile(
                          label: 'Capital',
                          value:
                              widget.controller.walletSummary == null
                                  ? 'SYNCING'
                                  : 'READY',
                          accent: GteShellTheme.accentWarm,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
            GtexLiveTickerBar(
              accentColor: GteShellTheme.accent,
              items: _marketTickerItems(),
            ),
            const SizedBox(height: 20),
            GtexSignalStrip(
              title: 'Board pulse',
              subtitle:
                  'These signals tell you whether the board is rising, cooling, or simply waiting for more activity.',
              accent: GteShellTheme.accent,
              tiles: <Widget>[
                GtexSignalTile(
                  label: 'Form swing',
                  value: _deskBiasLabel(widget.controller.players),
                  caption:
                      'A quick read on whether more visible players are pushing upward or cooling off.',
                  icon: Icons.trending_up_rounded,
                  color: GteShellTheme.accent,
                ),
                GtexSignalTile(
                  label: 'Coverage',
                  value: '${widget.controller.players.length} TRACKED',
                  caption:
                      'The board stays scan-first. Thin activity still stays visible instead of being hidden.',
                  icon: Icons.view_kanban_outlined,
                  color: GteShellTheme.accentWarm,
                ),
                GtexSignalTile(
                  label: 'Move status',
                  value:
                      widget.controller.isAuthenticated
                          ? 'READY TO SIGN'
                          : 'VISITOR MODE',
                  caption:
                      'Sign-in unlocks move tickets, capital context, and account-aware confirmation flows.',
                  icon: Icons.bolt_outlined,
                  color: const Color(0xFF8DD9FF),
                ),
              ],
            ),
            const SizedBox(height: 20),
            GteSyncStatusCard(
              title: 'Player board health',
              status:
                  widget.controller.marketError == null
                      ? 'Player discovery, club context, and move hints are in sync.'
                      : 'Feed degraded. The last confirmed board remains visible for review.',
              syncedAt: widget.controller.marketSyncedAt,
              accent: GteShellTheme.accent,
              isRefreshing: widget.controller.isLoadingMarket,
              onRefresh: _refresh,
            ),
            if (widget.navigationDependencies != null) ...<Widget>[
              const SizedBox(height: 20),
              _MarketRoutePanel(
                onOpenPlayerCards:
                    () => _openFeatureRoute(const PlayerCardsBrowseRouteData()),
                onOpenWorld:
                    () => _openFeatureRoute(const WorldOverviewRouteData()),
                onOpenCreatorShareMarket: _openCreatorShareMarketRoute,
                onOpenClubSaleMarket:
                    () => _openFeatureRoute(
                      const ClubSaleMarketListingsRouteData(),
                    ),
              ),
            ],
            const SizedBox(height: 20),
            const GtexSectionHeader(
              eyebrow: 'FILTERS',
              title: 'Focus the board before you choose a player.',
              description:
                  'Use filters to narrow the board without burying the live story.',
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
              eyebrow: 'BOARD NOTES',
              title: 'A few signals before you commit to a move.',
              description:
                  'These notes keep the board honest about depth, access, and how much action is really there right now.',
              accent: GteShellTheme.accent,
            ),
            const SizedBox(height: 14),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: <Widget>[
                _DeskSignalCard(
                  title: 'Board mood',
                  body:
                      widget.controller.players.isEmpty
                          ? 'Waiting for fresh player activity.'
                          : 'The board is live and ready to scan.',
                ),
                _DeskSignalCard(
                  title: 'Depth note',
                  body:
                      'Thin activity stays visible instead of being disguised. You can see where movement is real.',
                ),
                _DeskSignalCard(
                  title: 'Access note',
                  body:
                      'Visitors can scout the board. Signed-in users get move tickets, capital context, and account sync.',
                ),
              ],
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
            GtexSectionHeader(
              eyebrow: 'PLAYER BOARD',
              title:
                  _filteredPlayers.isEmpty
                      ? 'The board needs another look.'
                      : 'Scan the tape and pick your next move.',
              description:
                  _filteredPlayers.isEmpty
                      ? 'When the board is thin, the app keeps it explicit. Widen the filter or clear the search while the next live wave assembles.'
                      : 'Cards stay compact, emotional, and deliberate so this page feels like football trading with stakes, not a spreadsheet in disguise.',
              accent: GteShellTheme.accent,
            ),
            const SizedBox(height: 14),
            if (widget.controller.isLoadingMarket &&
                widget.controller.players.isEmpty)
              const GteSurfacePanel(
                accentColor: GteShellTheme.accent,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    GtexSectionBadge(
                      label: 'LOADING BOARD',
                      color: GteShellTheme.accent,
                    ),
                    SizedBox(height: 14),
                    LinearProgressIndicator(),
                    SizedBox(height: 14),
                    Text(
                      'Refreshing player discovery, form cues, and the latest movement so the board opens with a clean snapshot.',
                    ),
                  ],
                ),
              )
            else if (widget.controller.marketError != null &&
                widget.controller.players.isEmpty)
              GteStatePanel(
                title: 'Player board unavailable',
                message:
                    'The app could not confirm a fresh player board. ${widget.controller.marketError!}',
                actionLabel: 'Retry board',
                onAction: _refresh,
                icon: Icons.warning_amber_rounded,
              )
            else if (_filteredPlayers.isEmpty)
              GteStatePanel(
                title: 'No players match this filter',
                message:
                    !_hasAnyBoardQuery
                        ? 'This filter lane is quiet right now. The market is still scanning for the next wave of opportunity.'
                        : 'No players matched ${_activeBoardQueryLabel()} in the ${_lensLabel(_selectedLens).toLowerCase()} view yet. Brokers are still sweeping the tape.',
                actionLabel:
                    _hasAnyBoardQuery ? 'Clear filters' : 'Reset filter',
                onAction: () {
                  _searchController.clear();
                  _clubController.clear();
                  _leagueController.clear();
                  _nationalTeamController.clear();
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
                    widget.controller.loadMarket(
                      search: _searchController.text,
                      reset: false,
                    );
                  },
                  child: const Text('Load more players'),
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
        return players
            .where(
              (GteMarketPlayerListItem player) => (player.movementPct ?? 0) > 0,
            )
            .toList(growable: false);
      case _MarketLens.fallers:
        return players
            .where(
              (GteMarketPlayerListItem player) => (player.movementPct ?? 0) < 0,
            )
            .toList(growable: false);
      case _MarketLens.highInterest:
        return players
            .where(
              (GteMarketPlayerListItem player) =>
                  (player.marketInterestScore ?? 0) >= 70,
            )
            .toList(growable: false);
      case _MarketLens.all:
        return players;
    }
  }

  String _lensLabel(_MarketLens lens) {
    switch (lens) {
      case _MarketLens.all:
        return 'FULL BOARD';
      case _MarketLens.risers:
        return 'RISERS';
      case _MarketLens.fallers:
        return 'DIPS';
      case _MarketLens.highInterest:
        return 'WATCHLIST';
    }
  }

  void _handleSearchChanged() {
    if (mounted) {
      setState(() {});
    }
  }

  bool get _hasActiveStructuredFilters {
    return _clubController.text.trim().isNotEmpty ||
        _nationalTeamController.text.trim().isNotEmpty ||
        _leagueController.text.trim().isNotEmpty;
  }

  bool get _hasAnyBoardQuery {
    return _searchController.text.trim().isNotEmpty ||
        _hasActiveStructuredFilters;
  }

  String _activeBoardQueryLabel() {
    final List<String> labels = <String>[
      if (_searchController.text.trim().isNotEmpty)
        'search "${_searchController.text.trim()}"',
      if (_clubController.text.trim().isNotEmpty)
        'club "${_clubController.text.trim()}"',
      if (_nationalTeamController.text.trim().isNotEmpty)
        'national team "${_nationalTeamController.text.trim()}"',
      if (_leagueController.text.trim().isNotEmpty)
        'league "${_leagueController.text.trim()}"',
    ];
    return labels.join(', ');
  }

  void _clearFilterController(TextEditingController controller) {
    controller.clear();
    _refresh();
  }

  Future<void> _refresh() {
    return widget.controller.loadMarket(
      search: _searchController.text,
      filter: widget.controller.marketFilter.copyWith(
        club: _clubController.text,
        nationalTeam: _nationalTeamController.text,
        league: _leagueController.text,
      ),
      reset: true,
    );
  }

  Future<void> _openCreatorShareMarketRoute() async {
    final String? clubId = widget.navigationDependencies?.currentClubId?.trim();
    if (clubId == null || clubId.isEmpty) {
      await _showRouteRequirementDialog(
        title: 'Club selection required',
        message:
            'Creator-share market routes are club-scoped and stay blocked until the session exposes a canonical current club id.',
      );
      return;
    }
    await _openFeatureRoute(
      CreatorShareMarketClubRouteData(
        clubId: clubId,
        clubName: widget.navigationDependencies?.currentClubName,
      ),
    );
  }

  Future<void> _showRouteRequirementDialog({
    required String title,
    required String message,
  }) {
    return showDialog<void>(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: Text(title),
          content: Text(message),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Close'),
            ),
          ],
        );
      },
    );
  }

  Future<void> _openFeatureRoute(GteAppRouteData route) {
    final GteNavigationDependencies? dependencies =
        widget.navigationDependencies;
    if (dependencies == null) {
      return Future<void>.value();
    }
    return GteNavigationHelpers.pushRoute<void>(
      context,
      route: route,
      dependencies: dependencies,
    );
  }
}

String _deskBiasLabel(List<GteMarketPlayerListItem> players) {
  if (players.isEmpty) {
    return 'WAITING';
  }
  final int risers =
      players.where((GteMarketPlayerListItem player) => player.isRising).length;
  final int fallers = players.length - risers;
  if (risers == fallers) {
    return 'BALANCED';
  }
  return risers > fallers ? 'RISING' : 'COOLING';
}

class _MarketRoutePanel extends StatelessWidget {
  const _MarketRoutePanel({
    required this.onOpenPlayerCards,
    required this.onOpenWorld,
    required this.onOpenCreatorShareMarket,
    required this.onOpenClubSaleMarket,
  });

  final VoidCallback onOpenPlayerCards;
  final VoidCallback onOpenWorld;
  final VoidCallback onOpenCreatorShareMarket;
  final VoidCallback onOpenClubSaleMarket;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      accentColor: GteShellTheme.accent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Go deeper than the tape',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(
            'This board is for fast player reads. Drop into the broader player-card universe, regen world, creator economy, or club ownership lanes when you want to go from scouting to empire-building.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton.tonalIcon(
                onPressed: onOpenPlayerCards,
                icon: const Icon(Icons.style_outlined),
                label: const Text('Player universe'),
              ),
              FilledButton.tonalIcon(
                onPressed: onOpenWorld,
                icon: const Icon(Icons.public_outlined),
                label: const Text('Regen world'),
              ),
              FilledButton.tonalIcon(
                onPressed: onOpenCreatorShareMarket,
                icon: const Icon(Icons.candlestick_chart_outlined),
                label: const Text('Creator shares'),
              ),
              FilledButton.tonalIcon(
                onPressed: onOpenClubSaleMarket,
                icon: const Icon(Icons.storefront_outlined),
                label: const Text('Club sale market'),
              ),
            ],
          ),
        ],
      ),
    );
  }
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
    final List<({String label, _MarketLens lens, String value})> options =
        <({String label, _MarketLens lens, String value})>[
          (
            label: 'All players',
            lens: _MarketLens.all,
            value: counts.total.toString(),
          ),
          (
            label: 'Risers',
            lens: _MarketLens.risers,
            value: counts.risers.toString(),
          ),
          (
            label: 'Dips',
            lens: _MarketLens.fallers,
            value: counts.fallers.toString(),
          ),
          (
            label: 'Watchlist',
            lens: _MarketLens.highInterest,
            value: counts.highInterest.toString(),
          ),
        ];
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool stacked = constraints.maxWidth < 720;
        final double tileWidth =
            stacked ? constraints.maxWidth : (constraints.maxWidth - 30) / 4;
        return Wrap(
          spacing: 10,
          runSpacing: 10,
          children: options
              .map(
                (({String label, _MarketLens lens, String value}) option) =>
                    SizedBox(
                      width: tileWidth,
                      child: _MarketLensTile(
                        label: option.label,
                        value: option.value,
                        selected: selectedLens == option.lens,
                        onTap: () => onSelected(option.lens),
                      ),
                    ),
              )
              .toList(growable: false),
        );
      },
    );
  }
}

class _MarketLensTile extends StatelessWidget {
  const _MarketLensTile({
    required this.label,
    required this.value,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final String value;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final Color accent =
        selected ? GteShellTheme.accent : GteShellTheme.textMuted;
    return GteSurfacePanel(
      onTap: onTap,
      emphasized: selected,
      accentColor: GteShellTheme.accent,
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text(
                  label.toUpperCase(),
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: accent,
                    letterSpacing: 0.9,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              if (selected)
                const Icon(
                  Icons.radio_button_checked_rounded,
                  size: 16,
                  color: GteShellTheme.accent,
                ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            value,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              color: selected ? GteShellTheme.textPrimary : accent,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
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
      risers:
          players
              .where(
                (GteMarketPlayerListItem player) =>
                    (player.movementPct ?? 0) > 0,
              )
              .length,
      fallers:
          players
              .where(
                (GteMarketPlayerListItem player) =>
                    (player.movementPct ?? 0) < 0,
              )
              .length,
      highInterest:
          players
              .where(
                (GteMarketPlayerListItem player) =>
                    (player.marketInterestScore ?? 0) >= 70,
              )
              .length,
    );
  }
}

class _PlayerCard extends StatelessWidget {
  const _PlayerCard({required this.player, required this.onTap});

  final GteMarketPlayerListItem player;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final double currentValueCredits = player.currentValueCredits ?? 0;
    final double movementPct = player.movementPct ?? 0;
    final double trendScore = player.trendScore ?? 0;
    final int marketInterestScore = player.marketInterestScore ?? 0;
    final Color movementColor =
        player.isRising ? GteShellTheme.positive : GteShellTheme.negative;
    final avatar = AvatarMapper.fromMarketListItem(player);
    final String demandLabel =
        marketInterestScore >= 80
            ? 'HEAVY FLOW'
            : marketInterestScore >= 55
            ? 'ACTIVE FLOW'
            : 'THIN FLOW';
    final bool looksIlliquid = marketInterestScore < 35 && trendScore < 4;
    final String momentumLabel =
        trendScore >= 7
            ? 'Breakout'
            : trendScore >= 4
            ? 'Building'
            : 'Quiet';
    return GteSurfacePanel(
      onTap: onTap,
      accentColor: movementColor,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              _MarketTickerPill(
                label: player.isRising ? 'Rising' : 'Cooling',
                color: movementColor,
              ),
              _MarketTickerPill(
                label: demandLabel,
                color:
                    looksIlliquid
                        ? GteShellTheme.accentWarm
                        : GteShellTheme.accent,
              ),
              _MarketTickerPill(
                label: momentumLabel,
                color: GteShellTheme.accentCapital,
              ),
            ],
          ),
          const SizedBox(height: 14),
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final Widget identityBlock = Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    player.playerName,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 6),
                  Text(
                    <String>[
                      if (player.currentClubName != null)
                        player.currentClubName!,
                      if (player.nationality != null) player.nationality!,
                      if (player.position != null) player.position!,
                      'Age ${player.age}',
                    ].join(' - '),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              );
              final Widget quoteBlock = Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.end,
                children: <Widget>[
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 8,
                    ),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(999),
                      color:
                          looksIlliquid
                              ? GteShellTheme.accentWarm.withValues(alpha: 0.12)
                              : movementColor.withValues(alpha: 0.1),
                    ),
                    child: Text(
                      looksIlliquid ? 'THIN BOOK' : demandLabel,
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(
                        color:
                            looksIlliquid
                                ? GteShellTheme.accentWarm
                                : movementColor,
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 12,
                    ),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(18),
                      color: Colors.white.withValues(alpha: 0.04),
                      border: Border.all(
                        color: movementColor.withValues(alpha: 0.18),
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: <Widget>[
                        Text(
                          'LIVE QUOTE',
                          style: Theme.of(
                            context,
                          ).textTheme.bodySmall?.copyWith(
                            color: GteShellTheme.textMuted,
                            letterSpacing: 0.8,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          gteFormatCredits(currentValueCredits),
                          textAlign: TextAlign.end,
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 6),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 6,
                    ),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(999),
                      color: movementColor.withValues(alpha: 0.12),
                    ),
                    child: Text(
                      gteFormatMovement(movementPct),
                      style: Theme.of(
                        context,
                      ).textTheme.labelLarge?.copyWith(color: movementColor),
                    ),
                  ),
                ],
              );
              if (constraints.maxWidth < 360) {
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        PlayerMarketAvatar(avatar: avatar),
                        const SizedBox(width: 16),
                        Expanded(child: identityBlock),
                      ],
                    ),
                    const SizedBox(height: 14),
                    Align(alignment: Alignment.centerRight, child: quoteBlock),
                  ],
                );
              }
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  PlayerMarketAvatar(avatar: avatar),
                  const SizedBox(width: 16),
                  Expanded(child: identityBlock),
                  const SizedBox(width: 16),
                  Flexible(
                    fit: FlexFit.loose,
                    child: Align(
                      alignment: Alignment.topRight,
                      child: quoteBlock,
                    ),
                  ),
                ],
              );
            },
          ),
          const SizedBox(height: 16),
          Row(
            children: <Widget>[
              Expanded(
                child: _MicroBookStat(
                  label: 'Trend pressure',
                  value: momentumLabel.toUpperCase(),
                  color: movementColor,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _MicroBookStat(
                  label: 'Scout demand',
                  value:
                      marketInterestScore >= 70
                          ? 'HEAVY'
                          : marketInterestScore >= 40
                          ? 'ACTIVE'
                          : 'LIGHT',
                  color: GteShellTheme.accentWarm,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: List<Widget>.generate(
              5,
              (int index) => Expanded(
                child: Container(
                  height: 6,
                  margin: EdgeInsets.only(right: index == 4 ? 0 : 8),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(999),
                    color:
                        index < ((marketInterestScore / 20).clamp(1, 5).toInt())
                            ? movementColor.withValues(
                              alpha: 0.9 - (index * 0.1),
                            )
                            : Colors.white.withValues(alpha: 0.08),
                  ),
                ),
              ),
            ),
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
                GteMetricChip(
                  label: 'Trend score',
                  value: trendScore.toStringAsFixed(1),
                ),
                GteMetricChip(
                  label: 'Interest',
                  value: marketInterestScore.toString(),
                ),
                GteMetricChip(label: 'Flow', value: demandLabel),
                GteMetricChip(
                  label: 'Rating',
                  value: player.averageRating?.toStringAsFixed(1) ?? '--',
                ),
                GteMetricChip(
                  label: 'Market state',
                  value: player.isRising ? 'BID UP' : 'CHECK OFFER',
                  positive: player.isRising,
                ),
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
              Row(
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  Text(
                    'Open dossier',
                    style: Theme.of(
                      context,
                    ).textTheme.labelLarge?.copyWith(color: movementColor),
                  ),
                  const SizedBox(width: 8),
                  Icon(Icons.arrow_forward, size: 18, color: movementColor),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _MarketTickerPill extends StatelessWidget {
  const _MarketTickerPill({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: color.withValues(alpha: 0.14),
        border: Border.all(color: color.withValues(alpha: 0.28)),
      ),
      child: Text(
        label.toUpperCase(),
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
          color: color,
          letterSpacing: 0.9,
          fontWeight: FontWeight.w800,
        ),
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
  const _MicroBookStat({
    required this.label,
    required this.value,
    required this.color,
  });

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
          Text(
            value,
            style: Theme.of(
              context,
            ).textTheme.titleMedium?.copyWith(color: color),
          ),
        ],
      ),
    );
  }
}

class _MiniTerminalTile extends StatelessWidget {
  const _MiniTerminalTile({
    required this.label,
    required this.value,
    required this.accent,
  });

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
          Text(
            value,
            style: Theme.of(
              context,
            ).textTheme.titleMedium?.copyWith(color: accent),
          ),
        ],
      ),
    );
  }
}
