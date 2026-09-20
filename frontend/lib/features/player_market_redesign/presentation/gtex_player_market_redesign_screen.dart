import 'package:flutter/material.dart';

import '../../../data/gte_exchange_models.dart';
import '../../../domain/ownership/gtex_ownership_models.dart';
import '../../../providers/gte_exchange_controller.dart';
import '../../../ui_gtex/ui_gtex.dart';
import '../models/gtex_market_browse_models.dart';
import '../widgets/gtex_market_context_panel.dart';
import '../widgets/gtex_market_movers_rail.dart';
import '../widgets/gtex_market_player_grid.dart';
import '../widgets/gtex_market_selected_player_panel.dart';

/// Narrowest board pane that can carry the market-movers rail as a row of
/// lanes rather than three stacked full-width blocks. Matches the rail's own
/// internal row/stack threshold, so the rail is only admitted at a width
/// where it reads as a rail.
const double _moversRailMinPaneWidth = 640;

/// Shortest board pane that can carry the rail and still show a listing under
/// it. The rail is a header inside the board's scroll view, so it is paid for
/// out of the listing's vertical budget: measured at ~132px, plus room for a
/// player card beneath it.
const double _moversRailMinPaneHeight = 380;

class GtexPlayerMarketRedesignScreen extends StatefulWidget {
  const GtexPlayerMarketRedesignScreen({
    super.key,
    required this.controller,
    required this.onOpenPlayer,
    required this.onOpenLogin,
    this.onOpenTransferCalendar,
  });

  final GteExchangeController controller;
  final ValueChanged<String> onOpenPlayer;
  final VoidCallback onOpenLogin;
  final VoidCallback? onOpenTransferCalendar;

  @override
  State<GtexPlayerMarketRedesignScreen> createState() =>
      _GtexPlayerMarketRedesignScreenState();
}

class _GtexPlayerMarketRedesignScreenState
    extends State<GtexPlayerMarketRedesignScreen> {
  late final TextEditingController _searchController;
  late final TextEditingController _positionController;
  late final TextEditingController _minValueController;
  late final TextEditingController _maxValueController;
  late final TextEditingController _minAgeController;
  late final TextEditingController _maxAgeController;
  String? _selectedCountry;
  String? _selectedLeague;
  String? _selectedDivision;
  String? _selectedClub;
  String _selectedAvailability = 'all';
  String? _selectedPlayerId;
  GteMarketMovers? _movers;
  bool _isLoadingMovers = false;
  String? _moversError;
  GtexMarketBasketState _basketState = const GtexMarketBasketState(
    <String, GtexMarketPlayerView>{},
  );

  @override
  void initState() {
    super.initState();
    _searchController = TextEditingController(
      text: widget.controller.marketSearch,
    );
    _positionController = TextEditingController(
      text: widget.controller.marketFilter.position ?? '',
    );
    _minValueController = TextEditingController(
      text: _numberText(widget.controller.marketFilter.minValue),
    );
    _maxValueController = TextEditingController(
      text: _numberText(widget.controller.marketFilter.maxValue),
    );
    _minAgeController = TextEditingController(
      text: widget.controller.marketFilter.minAge?.toString() ?? '',
    );
    _maxAgeController = TextEditingController(
      text: widget.controller.marketFilter.maxAge?.toString() ?? '',
    );
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted &&
          widget.controller.marketBrowseCatalog == null &&
          !widget.controller.isLoadingMarketCatalog) {
        widget.controller.loadMarketBrowseCatalog();
      }
      if (mounted &&
          widget.controller.players.isEmpty &&
          !widget.controller.isLoadingMarket) {
        widget.controller.bootstrap();
      }
      _loadMovers();
    });
  }

  Future<void> _loadMovers() async {
    if (_isLoadingMovers) {
      return;
    }
    setState(() => _isLoadingMovers = true);
    try {
      final GteMarketMovers movers =
          await widget.controller.api.fetchMarketMovers();
      if (!mounted) {
        return;
      }
      setState(() {
        _movers = movers;
        _moversError = null;
        _isLoadingMovers = false;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _moversError = 'Value movers are unavailable right now.';
        _isLoadingMovers = false;
      });
    }
  }

  @override
  void dispose() {
    _searchController.dispose();
    _positionController.dispose();
    _minValueController.dispose();
    _maxValueController.dispose();
    _minAgeController.dispose();
    _maxAgeController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.controller,
      builder: (BuildContext context, Widget? child) {
        final List<GtexMarketPlayerView> players = widget.controller.players
            .map(GtexMarketPlayerView.fromListItem)
            .where(_matchesClientSidePath)
            .toList(growable: false);
        final GteMarketBrowseCatalog? catalog =
            widget.controller.marketBrowseCatalog;
        final GtexMarketBrowseSummary summary =
            catalog == null
                ? GtexMarketBrowseSummary.fromPlayers(
                  widget.controller.players
                      .map(GtexMarketPlayerView.fromListItem)
                      .toList(growable: false),
                )
                : GtexMarketBrowseSummary.fromCatalog(catalog);
        final GtexMarketPlayerView? selectedPlayer = _selectedPlayer(players);
        // Ownership comes from PHASE4-B's published contract (§4.3); before it
        // loads, or when signed out, the market simply does not claim
        // ownership.
        final Set<String> ownedPlayerIds = GtexOwnershipBook.fromPortfolio(
          widget.controller.portfolio,
        ).stakes.map((GtexOwnershipStake s) => s.playerId).toSet();

        return GtexMasterDetailScaffold(
          title: 'Transfer Hub',
          subtitle:
              'Browse listed football assets, shortlist targets, and open transfer, loan, swap, or loan-to-buy negotiations.',
          mobileLeftTitle: 'Browse hub',
          leftPanelWidth: 330,
          rightPanelWidth: 370,
          actions: <Widget>[
            IconButton.filledTonal(
              tooltip: 'Refresh market',
              onPressed: widget.controller.isLoadingMarket ? null : _refresh,
              icon: const Icon(Icons.sync),
            ),
            if (widget.onOpenTransferCalendar != null)
              GtexActionButton(
                label: 'Calendar',
                icon: Icons.event_note_outlined,
                compact: true,
                secondary: true,
                accent: GtexColors.cyan,
                onPressed: widget.onOpenTransferCalendar,
              ),
            if (!widget.controller.isAuthenticated)
              GtexActionButton(
                label: 'Sign in',
                icon: Icons.login,
                compact: true,
                onPressed: widget.onOpenLogin,
              ),
          ],
          leftPanel: GtexMarketContextPanel(
            searchController: _searchController,
            positionController: _positionController,
            minValueController: _minValueController,
            maxValueController: _maxValueController,
            minAgeController: _minAgeController,
            maxAgeController: _maxAgeController,
            summary: summary,
            selectedCountry: _selectedCountry,
            selectedLeague: _selectedLeague,
            selectedDivision: _selectedDivision,
            selectedClub: _selectedClub,
            selectedAvailability: _selectedAvailability,
            basketCount: _basketState.items.length,
            onSearchSubmitted: (_) => _applyServerFilters(resetSelection: true),
            onAdvancedSubmitted:
                () => _applyServerFilters(resetSelection: true),
            onClearFilters: _clearFilters,
            onCountrySelected: _setCountry,
            onLeagueSelected: _setLeague,
            onDivisionSelected: _setDivision,
            onClubSelected: _setClub,
            onAvailabilitySelected: _setAvailability,
          ),
          detail: LayoutBuilder(
            builder: (BuildContext context, BoxConstraints paneConstraints) {
              // The movers rail is secondary chrome and is decided from the
              // board's own pane, not the window: inside the shell the two
              // differ by the nav rail plus whichever master-detail panels
              // are inline, so a 1024px window hands this board about 544px
              // of width and a 1440px window about 574px. Reading the window
              // showed the rail in both, where it can only stack into three
              // full-width lanes. The rail is also a header inside the
              // board's scroll view, so it is paid for out of the listing's
              // vertical budget - at a 719px window the board pane is 247px
              // tall and a 132px rail left no room for a single player card.
              // It therefore appears only when the pane can lay it out as a
              // row *and* still show the listing beneath it. Below that, the
              // market's movement stays legible through the per-row deltas
              // and the discovery lanes.
              final Size viewport = MediaQuery.sizeOf(context);
              final double paneWidth =
                  paneConstraints.hasBoundedWidth
                      ? paneConstraints.maxWidth
                      : viewport.width;
              final double paneHeight =
                  paneConstraints.hasBoundedHeight
                      ? paneConstraints.maxHeight
                      : viewport.height;
              final bool showMoversRail =
                  paneWidth >= _moversRailMinPaneWidth &&
                  paneHeight >= _moversRailMinPaneHeight;
              return GtexMarketPlayerGrid(
                header: showMoversRail
                    ? GtexMarketMoversRail(
                      movers: _movers,
                      isLoading: _isLoadingMovers,
                      error: _moversError,
                      onOpenPlayer: widget.onOpenPlayer,
                    )
                    : null,
                players: players,
                ownedPlayerIds: ownedPlayerIds,
                totalPlayers: widget.controller.marketTotalPlayerCount,
                selectedPlayerId: _selectedPlayerId,
                basketState: _basketState,
                isLoading:
                    widget.controller.isLoadingMarket ||
                    widget.controller.isLoadingMoreMarket,
                error: widget.controller.marketError,
                hasMore: widget.controller.hasMorePlayers,
                onRefresh: _refresh,
                onLoadMore:
                    widget.controller.hasMorePlayers ? _loadMore : null,
                onSelectPlayer: _selectPlayer,
                onToggleBasket: _toggleBasket,
                onBuyNow:
                    (GtexMarketPlayerView player) =>
                        widget.onOpenPlayer(player.playerId),
              );
            },
          ),
          rightPanel: GtexMarketSelectedPlayerPanel(
            selectedPlayer: selectedPlayer,
            selectedPlayerOwned:
                selectedPlayer != null &&
                ownedPlayerIds.contains(selectedPlayer.playerId),
            basketState: _basketState,
            isAuthenticated: widget.controller.isAuthenticated,
            onOpenLogin: widget.onOpenLogin,
            onOpenPlayer:
                (GtexMarketPlayerView player) =>
                    widget.onOpenPlayer(player.playerId),
            onToggleBasket: _toggleBasket,
            onRemoveFromBasket: _removeFromBasket,
            onCheckout: _reviewBasket,
          ),
        );
      },
    );
  }

  bool _matchesClientSidePath(GtexMarketPlayerView _) {
    return true;
  }

  GtexMarketPlayerView? _selectedPlayer(List<GtexMarketPlayerView> players) {
    if (players.isEmpty) {
      return null;
    }
    if (_selectedPlayerId == null) {
      return players.first;
    }
    for (final GtexMarketPlayerView player in players) {
      if (player.playerId == _selectedPlayerId) {
        return player;
      }
    }
    return players.first;
  }

  void _selectPlayer(GtexMarketPlayerView player) {
    setState(() {
      _selectedPlayerId = player.playerId;
    });
  }

  void _toggleBasket(GtexMarketPlayerView player) {
    setState(() {
      _basketState = _basketState.toggled(player);
      _selectedPlayerId = player.playerId;
    });
  }

  void _removeFromBasket(String playerId) {
    setState(() {
      _basketState = _basketState.removed(playerId);
    });
  }

  void _setCountry(String? value) {
    setState(() {
      _selectedCountry = value;
      _selectedLeague = null;
      _selectedDivision = null;
      _selectedClub = null;
      _selectedPlayerId = null;
    });
    _applyServerFilters(resetSelection: false);
  }

  void _setLeague(String? value) {
    setState(() {
      _selectedLeague = value;
      _selectedDivision = null;
      _selectedClub = null;
      _selectedPlayerId = null;
    });
    _applyServerFilters(resetSelection: false);
  }

  void _setDivision(String? value) {
    setState(() {
      _selectedDivision = value;
      _selectedClub = null;
      _selectedPlayerId = null;
    });
    _applyServerFilters(resetSelection: false);
  }

  void _setClub(String? value) {
    setState(() {
      _selectedClub = value;
      _selectedPlayerId = null;
    });
    _applyServerFilters(resetSelection: false);
  }

  void _setAvailability(String value) {
    setState(() {
      _selectedAvailability = value;
      _selectedPlayerId = null;
    });
    _applyServerFilters(resetSelection: false);
  }

  void _clearFilters() {
    setState(() {
      _selectedCountry = null;
      _selectedLeague = null;
      _selectedDivision = null;
      _selectedClub = null;
      _selectedAvailability = 'all';
      _selectedPlayerId = null;
      _searchController.clear();
      _positionController.clear();
      _minValueController.clear();
      _maxValueController.clear();
      _minAgeController.clear();
      _maxAgeController.clear();
    });
    _applyServerFilters(resetSelection: true);
  }

  void _refresh() {
    _applyServerFilters(resetSelection: false);
    _loadMovers();
  }

  void _loadMore() {
    widget.controller.loadMarket(search: _searchController.text, reset: false);
  }

  void _applyServerFilters({required bool resetSelection}) {
    if (resetSelection) {
      setState(() {
        _selectedPlayerId = null;
      });
    }
    widget.controller.loadMarket(
      search: _searchController.text,
      filter: PlayerFilter(
        search: _searchController.text,
        position: _trimOrNull(_positionController.text),
        country: _selectedCountry,
        league: _selectedLeague,
        division: _selectedDivision,
        club: _selectedClub,
        minAge: _parseInt(_minAgeController.text),
        maxAge: _parseInt(_maxAgeController.text),
        minValue: _parseDouble(_minValueController.text),
        maxValue: _parseDouble(_maxValueController.text),
        availability: _serverAvailabilityFilter(_selectedAvailability),
      ),
      reset: true,
    );
  }

  static String _numberText(double? value) {
    if (value == null) {
      return '';
    }
    return value == value.roundToDouble()
        ? value.toStringAsFixed(0)
        : value.toString();
  }

  static String? _trimOrNull(String value) {
    final String trimmed = value.trim();
    return trimmed.isEmpty ? null : trimmed;
  }

  static int? _parseInt(String value) {
    final String normalized = value.trim().replaceAll(',', '');
    if (normalized.isEmpty) {
      return null;
    }
    final int? parsed = int.tryParse(normalized);
    if (parsed == null || parsed < 0) {
      return null;
    }
    return parsed;
  }

  static double? _parseDouble(String value) {
    final String normalized = value.trim().replaceAll(',', '');
    if (normalized.isEmpty) {
      return null;
    }
    final double? parsed = double.tryParse(normalized);
    if (parsed == null || parsed < 0) {
      return null;
    }
    return parsed;
  }

  String? _serverAvailabilityFilter(String value) {
    const Set<String> listingTypes = <String>{
      'transfer',
      'loan',
      'swap',
      'swap_plus_cash',
      'loan_to_buy',
      'temporary_rental',
      'open_offer',
      'private_negotiation',
    };
    return listingTypes.contains(value) ? value : null;
  }

  void _reviewBasket() {
    if (_basketState.items.isEmpty) {
      return;
    }
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: GtexColors.panel,
      barrierColor: Colors.black.withValues(alpha: 0.68),
      isScrollControlled: true,
      showDragHandle: true,
      builder:
          (BuildContext sheetContext) => _BasketReviewSheet(
            basketState: _basketState,
            onOpenPlayer: (GtexMarketPlayerView player) {
              Navigator.of(sheetContext).pop();
              widget.onOpenPlayer(player.playerId);
            },
          ),
    );
  }
}

class _BasketReviewSheet extends StatelessWidget {
  const _BasketReviewSheet({
    required this.basketState,
    required this.onOpenPlayer,
  });

  final GtexMarketBasketState basketState;
  final ValueChanged<GtexMarketPlayerView> onOpenPlayer;

  @override
  Widget build(BuildContext context) {
    final List<GtexMarketPlayerView> items = basketState.items;
    return SafeArea(
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.sizeOf(context).height * 0.82,
        ),
        child: ListView(
          padding: const EdgeInsets.fromLTRB(
            GtexSpacing.lg,
            0,
            GtexSpacing.lg,
            GtexSpacing.lg,
          ),
          shrinkWrap: true,
          children: <Widget>[
            Text(
              'Review Negotiation Shortlist',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                color: GtexColors.text,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: GtexSpacing.xs),
            Text(
              'Open one full player card at a time to continue listing review, negotiation, or shortlist follow-up.',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: GtexColors.textMuted,
                height: 1.35,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: GtexSpacing.md),
            GtexPanel(
              title: 'Shortlist value',
              subtitle: '${items.length} player${items.length == 1 ? '' : 's'}',
              accent: GtexColors.gold,
              child: Text(
                basketState.totalLabel,
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                  color: GtexColors.gold,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
            const SizedBox(height: GtexSpacing.md),
            ...items.map(
              (GtexMarketPlayerView player) => Padding(
                padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
                child: GtexPanel(
                  title: player.name,
                  subtitle:
                      '${player.clubName} - ${player.position} - '
                      '${player.sharePriceLabel}',
                  child: Row(
                    children: <Widget>[
                      Expanded(
                        child: Wrap(
                          spacing: GtexSpacing.xs,
                          runSpacing: GtexSpacing.xs,
                          children: <Widget>[
                            GtexStatusChip(
                              label: player.ratingLabel,
                              color: GtexColors.gold,
                              compact: true,
                            ),
                            GtexStatusChip(
                              label: player.ageLabel,
                              color: GtexColors.cyan,
                              compact: true,
                            ),
                          ],
                        ),
                      ),
                      GtexActionButton(
                        label:
                            player.hasOpenTransferListing
                                ? 'Open negotiation'
                                : 'Open player',
                        icon: Icons.open_in_new,
                        compact: true,
                        onPressed: () => onOpenPlayer(player),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
