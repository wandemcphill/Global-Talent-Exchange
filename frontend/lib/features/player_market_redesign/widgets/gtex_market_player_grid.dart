import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';

import '../../../ui_gtex/ui_gtex.dart';
import '../models/gtex_market_browse_models.dart';

/// Height of a browse card: the identity row - which now carries a meta
/// line of market intelligence under the club - plus its action bar.
const double _browseCardHeight = 168;

/// Narrowest a browse card may be before a second column stops being worth
/// it. Below this the row cannot carry its meta line, so an extra column
/// would buy density by throwing the market data away again.
const double _minBrowseCardWidth = 420;

/// Discovery lanes over the loaded listings. Each one is a filter on data
/// the backend already returned - there is no client-side ranking engine
/// here, and no lane exists for a signal the API does not provide.
enum GtexMarketDiscoveryLane {
  all,
  opportunities,
  rising,
  falling,
  watched,
}

extension GtexMarketDiscoveryLaneLabel on GtexMarketDiscoveryLane {
  String get label => switch (this) {
    GtexMarketDiscoveryLane.all => 'All listings',
    GtexMarketDiscoveryLane.opportunities => 'Opportunities',
    // Both lanes read the valuation movement, so both say so.
    GtexMarketDiscoveryLane.rising => 'Value rising',
    GtexMarketDiscoveryLane.falling => 'Value falling',
    GtexMarketDiscoveryLane.watched => 'Most watched',
  };

  IconData get icon => switch (this) {
    GtexMarketDiscoveryLane.all => Icons.grid_view_outlined,
    GtexMarketDiscoveryLane.opportunities => Icons.auto_awesome_outlined,
    GtexMarketDiscoveryLane.rising => Icons.trending_up,
    GtexMarketDiscoveryLane.falling => Icons.trending_down,
    GtexMarketDiscoveryLane.watched => Icons.visibility_outlined,
  };

  Color get accent => switch (this) {
    GtexMarketDiscoveryLane.all => GtexColors.pitch,
    GtexMarketDiscoveryLane.opportunities => GtexColors.cyan,
    GtexMarketDiscoveryLane.rising => GtexColors.accentPrimary,
    GtexMarketDiscoveryLane.falling => GtexColors.accentRed,
    GtexMarketDiscoveryLane.watched => GtexColors.gold,
  };

  bool matches(GtexMarketPlayerView player) => switch (this) {
    GtexMarketDiscoveryLane.all => true,
    GtexMarketDiscoveryLane.opportunities => player.isOpportunity,
    GtexMarketDiscoveryLane.rising => player.isRising,
    GtexMarketDiscoveryLane.falling => player.isFalling,
    GtexMarketDiscoveryLane.watched => player.interestLabel != null,
  };

  /// The lane's listings, in the order the lane's name promises.
  ///
  /// `Most watched` claims a ranking, so it has to actually be one: the
  /// matches are ordered by the backend's own interest score, highest
  /// first. Filtering alone would have made the label an assertion the
  /// screen was not keeping. The other lanes make no ordering claim and
  /// keep the market's own order.
  List<GtexMarketPlayerView> applyTo(List<GtexMarketPlayerView> players) {
    if (this == GtexMarketDiscoveryLane.all) {
      return players;
    }
    final List<GtexMarketPlayerView> matched = players
        .where(matches)
        .toList(growable: false);
    if (this == GtexMarketDiscoveryLane.watched) {
      final List<GtexMarketPlayerView> ranked = List<GtexMarketPlayerView>.of(
        matched,
      )..sort(
        (GtexMarketPlayerView a, GtexMarketPlayerView b) =>
            (b.interestScore ?? 0).compareTo(a.interestScore ?? 0),
      );
      return List<GtexMarketPlayerView>.unmodifiable(ranked);
    }
    if (this == GtexMarketDiscoveryLane.opportunities) {
      // Opportunities lead with the strongest combined move; both keys are
      // non-null here by construction of [isOpportunity].
      final List<GtexMarketPlayerView> ranked = List<GtexMarketPlayerView>.of(
        matched,
      )..sort(
        (GtexMarketPlayerView a, GtexMarketPlayerView b) {
          final int byValue = (b.movementPct ?? 0).compareTo(a.movementPct ?? 0);
          if (byValue != 0) return byValue;
          return (b.globalScoutingIndexMovementPct ?? 0).compareTo(
            a.globalScoutingIndexMovementPct ?? 0,
          );
        },
      );
      return List<GtexMarketPlayerView>.unmodifiable(ranked);
    }
    return matched;
  }
}

class GtexMarketPlayerGrid extends StatefulWidget {
  const GtexMarketPlayerGrid({
    super.key,
    required this.players,
    required this.totalPlayers,
    required this.selectedPlayerId,
    required this.basketState,
    required this.isLoading,
    required this.error,
    required this.onRefresh,
    required this.onLoadMore,
    required this.hasMore,
    required this.onSelectPlayer,
    required this.onToggleBasket,
    required this.onBuyNow,
    this.ownedPlayerIds = const <String>{},
    this.header,
  });

  /// Optional content rendered above the listing board - the market movers
  /// rail lives here.
  final Widget? header;

  final List<GtexMarketPlayerView> players;
  final int totalPlayers;
  final String? selectedPlayerId;
  final GtexMarketBasketState basketState;
  final bool isLoading;
  final String? error;
  final VoidCallback onRefresh;
  final VoidCallback? onLoadMore;
  final bool hasMore;
  final ValueChanged<GtexMarketPlayerView> onSelectPlayer;
  final ValueChanged<GtexMarketPlayerView> onToggleBasket;
  final ValueChanged<GtexMarketPlayerView> onBuyNow;

  /// Players the signed-in user already holds. Empty when signed out or
  /// before the portfolio has loaded - never guessed.
  final Set<String> ownedPlayerIds;

  @override
  State<GtexMarketPlayerGrid> createState() => _GtexMarketPlayerGridState();
}

class _GtexMarketPlayerGridState extends State<GtexMarketPlayerGrid> {
  GtexMarketDiscoveryLane _lane = GtexMarketDiscoveryLane.all;
  GtexMarketSort _sort = GtexMarketSort.relevance;

  @override
  Widget build(BuildContext context) {
    final List<GtexMarketPlayerView> players = widget.players;
    final int totalPlayers = widget.totalPlayers;
    final String? selectedPlayerId = widget.selectedPlayerId;
    final GtexMarketBasketState basketState = widget.basketState;
    final bool isLoading = widget.isLoading;
    final String? error = widget.error;
    final VoidCallback onRefresh = widget.onRefresh;
    final VoidCallback? onLoadMore = widget.onLoadMore;
    final bool hasMore = widget.hasMore;
    if (isLoading && players.isEmpty) {
      return const _LoadingBoard();
    }
    if (error != null && players.isEmpty) {
      return Padding(
        padding: const EdgeInsets.all(GtexSpacing.lg),
        child: GtexEmptyState(
          title: 'Player market unavailable',
          message: error,
          icon: Icons.warning_amber_rounded,
          actionLabel: 'Retry market',
          onAction: onRefresh,
        ),
      );
    }
    final List<GtexMarketPlayerView> laneMatches = _sort.applyTo(
      _lane.applyTo(players),
    );

    if (players.isEmpty) {
      return Padding(
        padding: const EdgeInsets.all(GtexSpacing.lg),
        child: GtexEmptyState(
          title: 'No players match this lane',
          message:
              'Clear filters or choose another country, league, division, or club.',
          icon: Icons.search_off_outlined,
          actionLabel: 'Refresh market',
          onAction: onRefresh,
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () async => onRefresh(),
      child: CustomScrollView(
        slivers: <Widget>[
          if (widget.header != null)
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(
                GtexSpacing.md,
                GtexSpacing.md,
                GtexSpacing.md,
                0,
              ),
              sliver: SliverToBoxAdapter(child: widget.header),
            ),
          SliverPadding(
            padding: const EdgeInsets.all(GtexSpacing.md),
            sliver: SliverToBoxAdapter(
              child: Wrap(
                spacing: GtexSpacing.sm,
                runSpacing: GtexSpacing.xs,
                children: <Widget>[
                  GtexStatusChip(
                    label: _loadedCountLabel(players.length, totalPlayers),
                    icon: Icons.groups_outlined,
                  ),
                  if (totalPlayers > players.length)
                    GtexStatusChip(
                      label: '${_formatCount(totalPlayers)} matching listings',
                      icon: Icons.public_outlined,
                      color: GtexColors.pitch,
                    ),
                  if (basketState.items.isNotEmpty)
                    GtexStatusChip(
                      label: '${basketState.items.length} shortlisted',
                      icon: Icons.shopping_basket_outlined,
                      color: GtexColors.gold,
                    ),
                  for (final GtexMarketDiscoveryLane lane
                      in GtexMarketDiscoveryLane.values)
                    _DiscoveryLaneChip(
                      lane: lane,
                      count:
                          lane == GtexMarketDiscoveryLane.all
                              ? players.length
                              : players
                                  .where(
                                    (GtexMarketPlayerView player) =>
                                        lane.matches(player),
                                  )
                                  .length,
                      isSelected: _lane == lane,
                      onSelected: () => setState(() => _lane = lane),
                    ),
                  _SortMenu(
                    sort: _sort,
                    onSelected: (GtexMarketSort value) =>
                        setState(() => _sort = value),
                  ),
                  if (error != null)
                    GtexStatusChip(
                      label: 'Last good snapshot',
                      icon: Icons.sync_problem_outlined,
                      color: GtexColors.red,
                    ),
                ],
              ),
            ),
          ),
          if (laneMatches.isEmpty)
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.all(GtexSpacing.lg),
                child: GtexEmptyState(
                  title:
                      'No ${_lane.label.toLowerCase()} in the loaded listings',
                  message:
                      'This lane filters the listings already loaded. Load '
                      'more players or switch back to all listings.',
                  icon: _lane.icon,
                  actionLabel: 'Show all listings',
                  onAction:
                      () => setState(() => _lane = GtexMarketDiscoveryLane.all),
                ),
              ),
            ),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(
              GtexSpacing.md,
              0,
              GtexSpacing.md,
              GtexSpacing.md,
            ),
            sliver: SliverLayoutBuilder(
              builder: (BuildContext context, SliverConstraints constraints) {
                final double width = constraints.crossAxisExtent;
                // Columns follow the width a card needs to stay readable
                // rather than fixed viewport breakpoints, so a second column
                // only appears when both columns are still worth reading.
                final int crossAxisCount = ((width + GtexSpacing.sm) ~/
                        (_minBrowseCardWidth + GtexSpacing.sm))
                    .clamp(1, 3);
                return SliverGrid(
                  gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: crossAxisCount,
                    crossAxisSpacing: GtexSpacing.sm,
                    mainAxisSpacing: GtexSpacing.sm,
                    // A ratio makes the cell height follow the column width,
                    // which left most of each browse card empty on wide
                    // screens. Pin the height to what the card actually needs.
                    mainAxisExtent: _browseCardHeight,
                  ),
                  delegate: SliverChildBuilderDelegate((
                    BuildContext context,
                    int index,
                  ) {
                    final GtexMarketPlayerView player = laneMatches[index];
                    return GtexPlayerCard(
                      name: player.name,
                      position: player.position,
                      clubName: player.clubName,
                      nationality: player.nationality,
                      // The card's headline figure is the tradable share
                      // price and nothing else. It used to be the ingested
                      // EUR valuation, so the number the user browsed on was
                      // never the number they were charged.
                      priceLabel: player.sharePriceLabel,
                      imageUrl: player.imageUrl,
                      gsiLabel: player.gsiLabel,
                      gsiTierLabel: player.gsiTierLabel,
                      gsiTrendLabel: player.gsiTrendLabel,
                      ratingLabel: player.ratingLabel,
                      ageLabel: player.ageValueLabel,
                      heightLabel: player.heightLabel,
                      footLabel: player.footLabel,
                      secondaryPositions: player.secondaryPositions,
                      // The backend's movement is a movement of the
                      // *valuation*. It cannot sit unlabelled beside a share
                      // price, so it travels with the valuation instead, in
                      // the value chip below.
                      valueDeltaLabel: null,
                      valuationLabel: player.valueBadgeLabel,
                      availabilityLabel: player.availabilityTypeLabel,
                      interestLabel: player.interestLabel,
                      isOwned: widget.ownedPlayerIds.contains(player.playerId),
                      badges: <Widget>[
                        if (player.isOpportunity)
                          const GtexStatusChip(
                            label: 'Opportunity',
                            icon: Icons.auto_awesome_outlined,
                            color: GtexColors.cyan,
                            compact: true,
                          ),
                        GtexStatusChip(
                          label: player.availabilityTypeLabel,
                          icon: _availabilityIcon(player.askingType),
                          color: GtexColors.gold,
                          compact: true,
                        ),
                        GtexStatusChip(
                          label: player.leagueDetailLabel,
                          icon: Icons.public_outlined,
                          color: GtexColors.pitch,
                          compact: true,
                        ),
                        if (player.loanTerms.isNotEmpty)
                          const GtexStatusChip(
                            label: 'Loan',
                            icon: Icons.schedule_outlined,
                            color: GtexColors.pitch,
                            compact: true,
                          ),
                        if (player.swapTerms.isNotEmpty)
                          const GtexStatusChip(
                            label: 'Swap',
                            icon: Icons.swap_horiz,
                            color: GtexColors.cyan,
                            compact: true,
                          ),
                      ],
                      isSelected: selectedPlayerId == player.playerId,
                      onTap: () => widget.onSelectPlayer(player),
                      onAddToShortlist: () => widget.onToggleBasket(player),
                      buyNowLabel:
                          player.hasOpenTransferListing ? 'Negotiate' : 'Open',
                      onBuyNow: () => widget.onBuyNow(player),
                    );
                  }, childCount: laneMatches.length),
                );
              },
            ),
          ),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(
                GtexSpacing.md,
                0,
                GtexSpacing.md,
                GtexSpacing.lg,
              ),
              child: Column(
                children: <Widget>[
                  if (isLoading) const LinearProgressIndicator(),
                  if (!isLoading && hasMore)
                    GtexActionButton(
                      label: 'Load more players',
                      icon: Icons.expand_more,
                      onPressed: onLoadMore,
                      secondary: true,
                    ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  IconData _availabilityIcon(String askingType) {
    switch (askingType) {
      case 'loan':
      case 'loan_to_buy':
      case 'temporary_rental':
        return Icons.schedule_outlined;
      case 'swap':
      case 'swap_plus_cash':
        return Icons.swap_horiz;
      case 'private_negotiation':
        return Icons.lock_open_outlined;
      case 'open_offer':
        return Icons.local_offer_outlined;
      case 'transfer_eligible':
        return Icons.fact_check_outlined;
      default:
        return Icons.sync_alt;
    }
  }

  String _loadedCountLabel(int loaded, int total) {
    if (total > loaded) {
      return '${_formatCount(loaded)} of ${_formatCount(total)} loaded';
    }
    return '${_formatCount(loaded)} visible';
  }

  String _formatCount(int value) {
    final String raw = value.toString();
    final StringBuffer buffer = StringBuffer();
    for (int index = 0; index < raw.length; index += 1) {
      final int remaining = raw.length - index;
      buffer.write(raw[index]);
      if (remaining > 1 && remaining % 3 == 1) {
        buffer.write(',');
      }
    }
    return buffer.toString();
  }
}

class _LoadingBoard extends StatelessWidget {
  const _LoadingBoard();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(GtexSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const GtexStatusChip(label: 'LOADING MARKET', icon: Icons.sync),
          const SizedBox(height: GtexSpacing.md),
          Text(
            'Building the transfer board...',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              color: GtexColors.text,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: GtexSpacing.sm),
          const LinearProgressIndicator(),
        ],
      ),
    );
  }
}

/// A discovery lane selector. Counts are over the listings currently
/// loaded, which is what the lane filters, so the number always matches
/// what selecting it will show.
class _DiscoveryLaneChip extends StatelessWidget {
  const _DiscoveryLaneChip({
    required this.lane,
    required this.count,
    required this.isSelected,
    required this.onSelected,
  });

  final GtexMarketDiscoveryLane lane;
  final int count;
  final bool isSelected;
  final VoidCallback onSelected;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      selected: isSelected,
      label: '${lane.label}, $count listings',
      child: InkWell(
        key: Key('gtex-market-lane-${lane.name}'),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusPill),
        onTap:
            count == 0 && lane != GtexMarketDiscoveryLane.all
                ? null
                : onSelected,
        child: Opacity(
          opacity: count == 0 && lane != GtexMarketDiscoveryLane.all ? 0.45 : 1,
          child: GtexStatusChip(
            label: '${lane.label} $count',
            icon: lane.icon,
            color: lane.accent,
            compact: !isSelected,
          ),
        ),
      ),
    );
  }
}

/// Sort selector for the loaded listings. Ordering is applied client-side over
/// the players already loaded, matching how the discovery lanes filter.
class _SortMenu extends StatelessWidget {
  const _SortMenu({required this.sort, required this.onSelected});

  final GtexMarketSort sort;
  final ValueChanged<GtexMarketSort> onSelected;

  @override
  Widget build(BuildContext context) {
    return PopupMenuButton<GtexMarketSort>(
      key: const Key('gtex-market-sort'),
      tooltip: 'Sort listings',
      initialValue: sort,
      onSelected: onSelected,
      itemBuilder: (BuildContext context) => <PopupMenuEntry<GtexMarketSort>>[
        for (final GtexMarketSort option in GtexMarketSort.values)
          CheckedPopupMenuItem<GtexMarketSort>(
            key: Key('gtex-market-sort-${option.name}'),
            value: option,
            checked: option == sort,
            child: Text(option.label),
          ),
      ],
      child: GtexStatusChip(
        label: 'Sort: ${sort.label}',
        icon: Icons.swap_vert,
        color: GtexColors.cyan,
      ),
    );
  }
}
