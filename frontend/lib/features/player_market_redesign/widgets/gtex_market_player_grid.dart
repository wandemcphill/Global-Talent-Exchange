import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';

import '../../../ui_gtex/ui_gtex.dart';
import '../models/gtex_market_browse_models.dart';

/// Height of a browse card: the identity row plus its action bar.
const double _browseCardHeight = 132;

class GtexMarketPlayerGrid extends StatelessWidget {
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
  });

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

  @override
  Widget build(BuildContext context) {
    if (isLoading && players.isEmpty) {
      return const _LoadingBoard();
    }
    if (error != null && players.isEmpty) {
      return Padding(
        padding: const EdgeInsets.all(GtexSpacing.lg),
        child: GtexEmptyState(
          title: 'Player market unavailable',
          message: error!,
          icon: Icons.warning_amber_rounded,
          actionLabel: 'Retry market',
          onAction: onRefresh,
        ),
      );
    }
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
                final int crossAxisCount =
                    width >= 1100
                        ? 3
                        : width >= 680
                        ? 2
                        : 1;
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
                    final GtexMarketPlayerView player = players[index];
                    return GtexPlayerCard(
                      name: player.name,
                      position: player.position,
                      clubName: player.clubName,
                      nationality: player.nationality,
                      priceLabel: player.priceLabel,
                      imageUrl: player.imageUrl,
                      gsiLabel: player.gsiLabel,
                      gsiTierLabel: player.gsiTierLabel,
                      gsiTrendLabel: player.gsiTrendLabel,
                      ratingLabel: player.ratingLabel,
                      ageLabel: player.ageLabel,
                      heightLabel: player.heightLabel,
                      footLabel: player.footLabel,
                      secondaryPositions: player.secondaryPositions,
                      badges: <Widget>[
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
                      onTap: () => onSelectPlayer(player),
                      onAddToShortlist: () => onToggleBasket(player),
                      buyNowLabel:
                          player.hasOpenTransferListing ? 'Negotiate' : 'Open',
                      onBuyNow: () => onBuyNow(player),
                    );
                  }, childCount: players.length),
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
