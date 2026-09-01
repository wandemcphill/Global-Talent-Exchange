import 'package:flutter/material.dart';

import '../../../ui_gtex/ui_gtex.dart';
import '../models/gtex_market_browse_models.dart';

class GtexMarketSelectedPlayerPanel extends StatelessWidget {
  const GtexMarketSelectedPlayerPanel({
    super.key,
    required this.selectedPlayer,
    required this.basketState,
    required this.isAuthenticated,
    required this.onOpenLogin,
    required this.onOpenPlayer,
    required this.onToggleBasket,
    required this.onRemoveFromBasket,
    required this.onCheckout,
  });

  final GtexMarketPlayerView? selectedPlayer;
  final GtexMarketBasketState basketState;
  final bool isAuthenticated;
  final VoidCallback onOpenLogin;
  final ValueChanged<GtexMarketPlayerView> onOpenPlayer;
  final ValueChanged<GtexMarketPlayerView> onToggleBasket;
  final ValueChanged<String> onRemoveFromBasket;
  final VoidCallback onCheckout;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: <Widget>[
        Expanded(
          flex: 7,
          child:
              selectedPlayer == null
                  ? const _NoSelectedPlayerPanel()
                  : _SelectedPlayerDetail(
                    player: selectedPlayer!,
                    inBasket: basketState.contains(selectedPlayer!.playerId),
                    isAuthenticated: isAuthenticated,
                    onOpenLogin: onOpenLogin,
                    onOpenPlayer: () => onOpenPlayer(selectedPlayer!),
                    onToggleBasket: () => onToggleBasket(selectedPlayer!),
                  ),
        ),
        const Divider(height: 1, color: GtexColors.line),
        Expanded(
          flex: 6,
          child: GtexShortlistBasket(
            title: 'Negotiation Shortlist',
            checkoutLabel:
                isAuthenticated
                    ? 'Review negotiation list'
                    : 'Sign in to negotiate',
            items: basketState.items
                .map(
                  (GtexMarketPlayerView player) => GtexBasketLineItem(
                    id: player.playerId,
                    title: player.name,
                    subtitle: '${player.clubName} - ${player.position}',
                    priceLabel: player.priceLabel,
                    onRemove: () => onRemoveFromBasket(player.playerId),
                  ),
                )
                .toList(growable: false),
            totalLabel: basketState.totalLabel,
            onCheckout:
                basketState.items.isEmpty
                    ? null
                    : (isAuthenticated ? onCheckout : onOpenLogin),
          ),
        ),
      ],
    );
  }
}

class _NoSelectedPlayerPanel extends StatelessWidget {
  const _NoSelectedPlayerPanel();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.all(GtexSpacing.md),
      child: GtexEmptyState(
        title: 'Select a player',
        message:
            'Pick a player for a quick read on value, movement and '
            'availability, then open the full profile for the football and '
            'the terms.',
        icon: Icons.person_search_outlined,
      ),
    );
  }
}

class _SelectedPlayerDetail extends StatelessWidget {
  const _SelectedPlayerDetail({
    required this.player,
    required this.inBasket,
    required this.isAuthenticated,
    required this.onOpenLogin,
    required this.onOpenPlayer,
    required this.onToggleBasket,
  });

  final GtexMarketPlayerView player;
  final bool inBasket;
  final bool isAuthenticated;
  final VoidCallback onOpenLogin;
  final VoidCallback onOpenPlayer;
  final VoidCallback onToggleBasket;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.md),
      children: <Widget>[
        GtexPlayerCard(
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
          badges: <Widget>[
            GtexStatusChip(
              label: player.availabilityTypeLabel,
              icon: Icons.sync_alt,
              color: GtexColors.gold,
              compact: true,
            ),
          ],
          isSelected: true,
          onAddToShortlist: onToggleBasket,
          buyNowLabel: player.hasOpenTransferListing ? 'Negotiate' : 'Open',
          onBuyNow: isAuthenticated ? onOpenPlayer : onOpenLogin,
        ),
        const SizedBox(height: GtexSpacing.md),
        Wrap(
          spacing: GtexSpacing.xs,
          runSpacing: GtexSpacing.xs,
          children: <Widget>[
            GtexStatusChip(
              label: player.availabilityTypeLabel,
              icon: player.isRising ? Icons.trending_up : Icons.trending_down,
              color: player.isRising ? GtexColors.pitch : GtexColors.red,
            ),
            if (player.loanTerms.isNotEmpty)
              GtexStatusChip(
                label: 'Loan terms',
                icon: Icons.schedule_outlined,
                color: GtexColors.gold,
              ),
            if (player.swapTerms.isNotEmpty)
              GtexStatusChip(
                label: 'Swap terms',
                icon: Icons.swap_horiz,
                color: GtexColors.cyan,
              ),
            if (!player.isTradable)
              const GtexStatusChip(
                label: 'Not tradable',
                icon: Icons.block_outlined,
                color: GtexColors.red,
              ),
            GtexStatusChip(
              label: player.leagueDetailLabel,
              icon: Icons.public_outlined,
              color: GtexColors.pitch,
            ),
          ],
        ),
        const SizedBox(height: GtexSpacing.md),
        // A preview, not a second player screen. The full terms - salary,
        // contract, clauses, swap and loan conditions - live on the
        // canonical player detail, so there is one place that holds the
        // whole story about a footballer.
        GtexPanel(
          title: 'At a glance',
          subtitle: 'Open the full profile for football, terms and depth',
          child: GtexTermsList(
            dense: true,
            rows: <GtexTermRow>[
              GtexTermRow('GSI', player.gsiDetailLabel),
              GtexTermRow.orUnknown('GSI movement', player.gsiTrendLabel),
              GtexTermRow('Market value', player.priceLabel),
              GtexTermRow.orUnknown('Value movement', player.movementLabel),
              GtexTermRow('Availability', player.availabilityTypeLabel),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Negotiation state',
          subtitle:
              inBasket
                  ? 'Shortlisted'
                  : player.hasOpenTransferListing
                  ? 'Open listing'
                  : 'No open listing',
          child: Text(
            inBasket
                ? 'This player is already in your shortlist for negotiation review.'
                : player.hasOpenTransferListing
                ? 'This player has an open Transfer Hub listing. Open the full card to continue the negotiation flow.'
                : 'This player is transfer eligible but has no open Transfer Hub listing published right now.',
            style: const TextStyle(
              color: GtexColors.textMuted,
              height: 1.35,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        Row(
          children: <Widget>[
            Expanded(
              child: GtexActionButton(
                key: const Key('gtex-market-open-full-profile'),
                label:
                    isAuthenticated
                        ? 'Open full profile'
                        : 'Sign in to open profile',
                icon: isAuthenticated ? Icons.open_in_new : Icons.login,
                onPressed: isAuthenticated ? onOpenPlayer : onOpenLogin,
              ),
            ),
          ],
        ),
        const SizedBox(height: GtexSpacing.sm),
        Row(
          children: <Widget>[
            Expanded(
              child: GtexActionButton(
                label: inBasket ? 'Remove shortlist' : 'Add shortlist',
                icon:
                    inBasket
                        ? Icons.remove_shopping_cart_outlined
                        : Icons.playlist_add,
                onPressed: onToggleBasket,
                accent: inBasket ? GtexColors.red : GtexColors.gold,
                secondary: true,
              ),
            ),
          ],
        ),
      ],
    );
  }
}
