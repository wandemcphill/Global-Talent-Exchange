import 'package:flutter/material.dart';

import '../../../ui_gtex/ui_gtex.dart';
import '../models/gtex_national_team_rental_models.dart';

class GtexRentalSummaryPanel extends StatelessWidget {
  const GtexRentalSummaryPanel({
    super.key,
    required this.selectedPlayer,
    required this.basketState,
    required this.isAuthenticated,
    required this.showPayment,
    required this.onOpenLogin,
    required this.onToggleBasket,
    required this.onRemoveFromBasket,
    required this.onReviewPayment,
    required this.onBackToBasket,
    required this.onConfirmPayment,
  });

  final GtexRentalPlayerView? selectedPlayer;
  final GtexRentalBasketState basketState;
  final bool isAuthenticated;
  final bool showPayment;
  final VoidCallback onOpenLogin;
  final ValueChanged<GtexRentalPlayerView> onToggleBasket;
  final ValueChanged<String> onRemoveFromBasket;
  final VoidCallback onReviewPayment;
  final VoidCallback onBackToBasket;
  final VoidCallback onConfirmPayment;

  @override
  Widget build(BuildContext context) {
    if (showPayment) {
      return _PaymentReview(
        basketState: basketState,
        isAuthenticated: isAuthenticated,
        onOpenLogin: onOpenLogin,
        onBack: onBackToBasket,
        onConfirm: onConfirmPayment,
      );
    }

    final List<GtexBasketLineItem> lineItems = basketState.items
        .map(
          (GtexRentalPlayerView player) => GtexBasketLineItem(
            id: player.playerId,
            title: player.name,
            subtitle:
                '${player.position} | ${player.nationality} | ${player.sourceLabel}',
            priceLabel: player.priceLabel,
            onRemove: () => onRemoveFromBasket(player.playerId),
          ),
        )
        .toList(growable: false);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        if (selectedPlayer != null)
          Padding(
            padding: const EdgeInsets.all(GtexSpacing.md),
            child: GtexPanel(
              title: selectedPlayer!.name,
              subtitle: 'Selected rental player',
              accent:
                  selectedPlayer!.isPreseededRegen
                      ? GtexColors.purple
                      : GtexColors.pitch,
              trailing: GtexStatusChip(
                label: selectedPlayer!.isPreseededRegen ? 'REGEN' : 'REAL',
                color:
                    selectedPlayer!.isPreseededRegen
                        ? GtexColors.purple
                        : GtexColors.pitch,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    '${selectedPlayer!.position} | ${selectedPlayer!.ageLabel} | ${selectedPlayer!.ratingLabel}',
                    style: const TextStyle(
                      color: GtexColors.text,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: GtexSpacing.xs),
                  Text(
                    selectedPlayer!.eligibilityNote ??
                        'Eligible for the selected national-team rental pool.',
                    style: const TextStyle(
                      color: GtexColors.textMuted,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: GtexSpacing.sm),
                  Row(
                    children: <Widget>[
                      Expanded(
                        child: Text(
                          selectedPlayer!.priceLabel,
                          style: Theme.of(
                            context,
                          ).textTheme.titleLarge?.copyWith(
                            color: GtexColors.gold,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ),
                      GtexActionButton(
                        label:
                            basketState.contains(selectedPlayer!.playerId)
                                ? 'Remove'
                                : 'Add rental',
                        icon:
                            basketState.contains(selectedPlayer!.playerId)
                                ? Icons.remove_circle_outline
                                : Icons.add_shopping_cart,
                        compact: true,
                        accent: GtexColors.gold,
                        onPressed: () => onToggleBasket(selectedPlayer!),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        Expanded(
          child: GtexShortlistBasket(
            title: 'Rental Basket',
            checkoutLabel: 'Review rental payment',
            emptyTitle: 'No rental players selected',
            emptyMessage:
                'Choose a country or national team, then add eligible players to build your temporary squad.',
            items: lineItems,
            totalLabel: basketState.totalLabel,
            onCheckout: basketState.items.isEmpty ? null : onReviewPayment,
          ),
        ),
      ],
    );
  }
}

class _PaymentReview extends StatelessWidget {
  const _PaymentReview({
    required this.basketState,
    required this.isAuthenticated,
    required this.onOpenLogin,
    required this.onBack,
    required this.onConfirm,
  });

  final GtexRentalBasketState basketState;
  final bool isAuthenticated;
  final VoidCallback onOpenLogin;
  final VoidCallback onBack;
  final VoidCallback onConfirm;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(GtexSpacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Row(
            children: <Widget>[
              IconButton(onPressed: onBack, icon: const Icon(Icons.arrow_back)),
              Expanded(
                child: Text(
                  'Rental Payment',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: GtexSpacing.md),
          GtexPanel(
            title: 'Squad rental summary',
            subtitle:
                'Review selected players before GTEX creates the rental entry and attaches rental contracts.',
            accent: GtexColors.gold,
            child: Column(
              children: <Widget>[
                _PaymentRow(
                  label: 'Players selected',
                  value: basketState.squadCount.toString(),
                ),
                _PaymentRow(
                  label: 'Rental subtotal',
                  value: basketState.totalLabel,
                ),
                const _PaymentRow(
                  label: 'Competition entry',
                  value: 'From selected tournament',
                ),
                const _PaymentRow(
                  label: 'Settlement',
                  value: 'Wallet / GTEX coin',
                ),
              ],
            ),
          ),
          const SizedBox(height: GtexSpacing.md),
          GtexPanel(
            accent: GtexColors.cyan,
            child: const Text(
              'GTEX will create or reuse a national-team entry, then attach each selected player through the live rental endpoint.',
              style: TextStyle(
                color: GtexColors.textMuted,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          const Spacer(),
          GtexActionButton(
            label:
                isAuthenticated
                    ? 'Pay and rent players'
                    : 'Sign in to continue',
            icon: isAuthenticated ? Icons.lock_open_outlined : Icons.login,
            accent: GtexColors.gold,
            onPressed: isAuthenticated ? onConfirm : onOpenLogin,
          ),
        ],
      ),
    );
  }
}

class _PaymentRow extends StatelessWidget {
  const _PaymentRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: GtexSpacing.xs),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Text(
              label,
              style: const TextStyle(
                color: GtexColors.textMuted,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          Text(
            value,
            style: const TextStyle(
              color: GtexColors.text,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }
}
