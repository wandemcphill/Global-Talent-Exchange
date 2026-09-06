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
    this.selectedPlayerOwned = false,
  });

  /// True when the signed-in user already holds the selected player.
  final bool selectedPlayerOwned;
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
                    isOwned: selectedPlayerOwned,
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
                    // The shortlist totals valuations under "Shortlist
                    // value", so each line carries the same figure - not a
                    // price the user would be charged.
                    priceLabel: player.estimatedValueLabel ?? 'Value unknown',
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
    required this.isOwned,
    required this.isAuthenticated,
    required this.onOpenLogin,
    required this.onOpenPlayer,
    required this.onToggleBasket,
  });

  final GtexMarketPlayerView player;
  final bool inBasket;
  final bool isOwned;
  final bool isAuthenticated;
  final VoidCallback onOpenLogin;
  final VoidCallback onOpenPlayer;
  final VoidCallback onToggleBasket;

  /// The pane is short: the preview sits above the shortlist basket, so it
  /// gets roughly a third of the workspace height. Below the height the
  /// poster card needs, the card renders in its own compact layout instead
  /// of filling the whole pane with a clipped portrait.
  static const double _posterCardMinHeight = 380;

  /// A short market read for the selected player. When the user owns the
  /// player it frames the value movement as their position moving; otherwise
  /// it flags an opportunity when the market and the scouting index agree.
  /// Every figure shown is a value the backend returned - nothing is
  /// synthesised, and the panel is absent when there is no real signal.
  Widget? get _marketSignal {
    final String? movement = player.valueMovementLabel;
    if (isOwned) {
      final String direction = player.isRising
          ? 'up'
          : player.isFalling
          ? 'down'
          : 'flat';
      return GtexPanel(
        title: 'Your position',
        subtitle: 'You already hold this player',
        accent: GtexColors.gold,
        child: GtexTermsList(
          dense: true,
          rows: <GtexTermRow>[
            GtexTermRow('Share price', player.sharePriceLabel),
            GtexTermRow.orUnknown('Estimated value', player.estimatedValueLabel),
            GtexTermRow.orUnknown('Value movement', movement),
            GtexTermRow('Position trend', 'Trading $direction'),
            GtexTermRow.orUnknown('Scouting index', player.gsiTrendLabel),
          ],
        ),
      );
    }
    if (player.isOpportunity) {
      return GtexPanel(
        title: 'Opportunity signal',
        subtitle: 'Market value and scouting index are both rising',
        accent: GtexColors.cyan,
        child: GtexTermsList(
          dense: true,
          rows: <GtexTermRow>[
            GtexTermRow.orUnknown('Value movement', movement),
            GtexTermRow.orUnknown('Scouting index', player.gsiTrendLabel),
            GtexTermRow.orUnknown('Market interest', player.interestLabel),
          ],
        ),
      );
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool posterFits =
            !constraints.hasBoundedHeight ||
            constraints.maxHeight >= _posterCardMinHeight;
        return Column(
          children: <Widget>[
            Expanded(child: _scrollingRead(context, posterFits: posterFits)),
            // "Open full profile" is the preview's whole purpose - it is the
            // way into the canonical player detail - so it is pinned rather
            // than left at the bottom of a list taller than its pane. At
            // 1440x900 it used to sit so far below the fold that the list
            // never even built it.
            Padding(
              padding: const EdgeInsets.fromLTRB(
                GtexSpacing.md,
                0,
                GtexSpacing.md,
                GtexSpacing.md,
              ),
              child: _actions(context),
            ),
          ],
        );
      },
    );
  }

  Widget _actions(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
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

  Widget _scrollingRead(BuildContext context, {required bool posterFits}) {
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.md),
      children: <Widget>[
        GtexPlayerCard(
          scale:
              posterFits
                  ? GtexPlayerCardScale.full
                  : GtexPlayerCardScale.compact,
          name: player.name,
          position: player.position,
          clubName: player.clubName,
          nationality: player.nationality,
          priceLabel: player.sharePriceLabel,
          valuationLabel: player.valueBadgeLabel,
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
              GtexTermRow('Share price', player.sharePriceLabel),
              GtexTermRow.orUnknown(
                'Estimated value',
                player.estimatedValueLabel,
              ),
              GtexTermRow.orUnknown(
                'Value movement',
                player.valueMovementLabel,
              ),
              GtexTermRow('Availability', player.availabilityTypeLabel),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.xs),
        Align(
          alignment: Alignment.centerLeft,
          child: GtexActionButton(
            key: const Key('gtex-market-why-price'),
            label: 'Why this price?',
            icon: Icons.insights_outlined,
            compact: true,
            secondary: true,
            accent: GtexColors.cyan,
            onPressed: isAuthenticated ? onOpenPlayer : onOpenLogin,
          ),
        ),
        if (_marketSignal != null) ...<Widget>[
          const SizedBox(height: GtexSpacing.md),
          _marketSignal!,
        ],
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
      ],
    );
  }
}
