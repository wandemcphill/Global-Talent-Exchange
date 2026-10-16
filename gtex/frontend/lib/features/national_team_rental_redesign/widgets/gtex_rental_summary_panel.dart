import 'package:flutter/material.dart';

import '../../../ui_gtex/ui_gtex.dart';
import '../models/gtex_national_team_rental_models.dart';

class GtexRentalSummaryPanel extends StatelessWidget {
  const GtexRentalSummaryPanel({
    super.key,
    required this.selectedPlayer,
    required this.selectedCompetition,
    required this.selectedTeam,
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
  final GtexRentalCompetitionView? selectedCompetition;
  final GtexRentalTeamView? selectedTeam;
  final GtexRentalBasketState basketState;
  final bool isAuthenticated;
  final bool showPayment;
  final VoidCallback? onOpenLogin;
  final ValueChanged<GtexRentalPlayerView> onToggleBasket;
  final ValueChanged<String> onRemoveFromBasket;
  final VoidCallback onReviewPayment;
  final VoidCallback onBackToBasket;
  final VoidCallback? onConfirmPayment;

  @override
  Widget build(BuildContext context) {
    final bool competitionOpen = selectedCompetition?.isOpen ?? false;
    if (showPayment && competitionOpen) {
      return _PaymentReview(
        basketState: basketState,
        selectedCompetition: selectedCompetition,
        selectedTeam: selectedTeam,
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
                label: selectedPlayer!.availabilityLabel,
                color:
                    selectedPlayer!.rentalEligible
                        ? GtexColors.pitch
                        : GtexColors.gold,
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
                        (selectedPlayer!.rentalEligible
                            ? 'Backend returned this player as eligible for the selected rental pool.'
                            : 'Backend did not return an eligibility message.'),
                    style: const TextStyle(
                      color: GtexColors.textMuted,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  if (!selectedPlayer!.rentalEligible) ...<Widget>[
                    const SizedBox(height: GtexSpacing.sm),
                    GtexBlockedState(
                      compact: true,
                      title: 'Rental action blocked',
                      reason: selectedPlayer!.ruleSourceLabel,
                      severity: GtexBlockedSeverity.locked,
                      resolution:
                          'Eligibility is controlled by the live national-team backend.',
                    ),
                  ],
                  const SizedBox(height: GtexSpacing.sm),
                  Wrap(
                    spacing: GtexSpacing.xs,
                    runSpacing: GtexSpacing.xs,
                    children: <Widget>[
                      GtexStatusChip(
                        label:
                            selectedPlayer!.isPreseededRegen
                                ? 'REGEN GEN-X'
                                : 'REAL PLAYER',
                        color:
                            selectedPlayer!.isPreseededRegen
                                ? GtexColors.purple
                                : GtexColors.pitch,
                        compact: true,
                      ),
                      GtexStatusChip(
                        label: selectedPlayer!.sourceLabel,
                        color: GtexColors.cyan,
                        compact: true,
                      ),
                    ],
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
                                : selectedPlayer!.rentalEligible
                                ? 'Add rental'
                                : 'Unavailable',
                        icon:
                            basketState.contains(selectedPlayer!.playerId)
                                ? Icons.remove_circle_outline
                                : selectedPlayer!.rentalEligible
                                ? Icons.add_shopping_cart
                                : Icons.block_outlined,
                        compact: true,
                        accent: GtexColors.gold,
                        onPressed:
                            selectedPlayer!.rentalEligible ||
                                    basketState.contains(
                                      selectedPlayer!.playerId,
                                    )
                                ? () => onToggleBasket(selectedPlayer!)
                                : null,
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        Expanded(
          child: Column(
            children: <Widget>[
              if (selectedCompetition == null)
                const Padding(
                  padding: EdgeInsets.fromLTRB(
                    GtexSpacing.md,
                    0,
                    GtexSpacing.md,
                    GtexSpacing.sm,
                  ),
                  child: GtexBlockedState(
                    compact: true,
                    title: 'Competition required',
                    reason:
                        'Select a live national competition before reviewing rental payment.',
                    severity: GtexBlockedSeverity.info,
                    resolution:
                        'Competition context controls backend eligibility and rental duration.',
                  ),
                ),
              if (selectedCompetition != null && !competitionOpen)
                Padding(
                  padding: const EdgeInsets.fromLTRB(
                    GtexSpacing.md,
                    0,
                    GtexSpacing.md,
                    GtexSpacing.sm,
                  ),
                  child: GtexBlockedState(
                    compact: true,
                    title: 'Competition closed',
                    reason:
                        '${selectedCompetition!.title} is ${selectedCompetition!.status}; rental payment is disabled until the backend opens a live competition.',
                    severity: GtexBlockedSeverity.locked,
                    resolution:
                        'Choose an open national competition returned by the live backend.',
                  ),
                ),
              Expanded(
                child: GtexShortlistBasket(
                  title: 'Rental Basket',
                  checkoutLabel: 'Review rental payment',
                  emptyTitle: 'No rental players selected',
                  emptyMessage:
                      'Choose a country or national team, then add backend-eligible players to build your temporary squad.',
                  items: lineItems,
                  totalLabel: basketState.totalLabel,
                  onCheckout:
                      basketState.items.isEmpty ||
                              !basketState.allEligible ||
                              !competitionOpen
                          ? null
                          : onReviewPayment,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _PaymentReview extends StatelessWidget {
  const _PaymentReview({
    required this.basketState,
    required this.selectedCompetition,
    required this.selectedTeam,
    required this.isAuthenticated,
    required this.onOpenLogin,
    required this.onBack,
    required this.onConfirm,
  });

  final GtexRentalBasketState basketState;
  final GtexRentalCompetitionView? selectedCompetition;
  final GtexRentalTeamView? selectedTeam;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;
  final VoidCallback onBack;
  final VoidCallback? onConfirm;

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
                _PaymentRow(
                  label: 'Competition entry',
                  value: selectedCompetition?.title ?? 'Select competition',
                ),
                _PaymentRow(
                  label: 'Roster rule',
                  value: selectedTeam?.squadRuleLabel ?? 'Backend rule pending',
                ),
                const _PaymentRow(
                  label: 'Settlement',
                  value: 'Wallet / GTEX Coin',
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
          if (!isAuthenticated && onOpenLogin == null)
            const Padding(
              padding: EdgeInsets.only(bottom: GtexSpacing.sm),
              child: GtexBlockedState(
                compact: true,
                title: 'Sign-in route unavailable',
                reason:
                    'The app did not provide a live sign-in action for national-team rentals.',
                severity: GtexBlockedSeverity.locked,
              ),
            ),
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
          Flexible(
            child: Text(
              value,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              textAlign: TextAlign.right,
              style: const TextStyle(
                color: GtexColors.text,
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
