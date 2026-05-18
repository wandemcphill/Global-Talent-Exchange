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

String _salaryLabel(GtexMarketPlayerView player) {
  final double? amount = player.salaryAmount;
  if (amount == null || amount <= 0) {
    return 'Not disclosed';
  }
  return '${GtexMarketFormatters.credits(amount)} / wk';
}

String _contractLabel(GtexMarketPlayerView player) {
  final double? years = player.contractYearsRemaining;
  if (years == null || years <= 0) {
    return 'Not disclosed';
  }
  final String value =
      years == years.roundToDouble()
          ? years.toStringAsFixed(0)
          : years.toStringAsFixed(1);
  return '$value year${value == '1' ? '' : 's'} remaining';
}

String _buyClauseLabel(GtexMarketPlayerView player) {
  final double? amount = player.buyClauseAmount;
  if (amount == null || amount <= 0) {
    return 'Not disclosed';
  }
  return GtexMarketFormatters.credits(amount);
}

String _swapLabel(GtexMarketPlayerView player) {
  return _termsLabel(player.swapTerms, fallback: 'No published swap terms');
}

String _loanLabel(GtexMarketPlayerView player) {
  return _termsLabel(player.loanTerms, fallback: 'No published loan terms');
}

String _termsLabel(Map<String, Object?> terms, {required String fallback}) {
  if (terms.isEmpty) {
    return fallback;
  }
  return terms.entries
      .where((MapEntry<String, Object?> entry) => entry.value != null)
      .take(2)
      .map((MapEntry<String, Object?> entry) {
        final String label = GtexMarketFormatters.labelFromToken(entry.key);
        return '$label: ${entry.value}';
      })
      .join(', ');
}

class _TermRow extends StatelessWidget {
  const _TermRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Text(
              label,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: GtexColors.textMuted,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.end,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
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

class _NoSelectedPlayerPanel extends StatelessWidget {
  const _NoSelectedPlayerPanel();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.all(GtexSpacing.md),
      child: GtexEmptyState(
        title: 'Select a player',
        message:
            'Pick a player to inspect transfer, loan, swap, salary, contract, and buy-clause terms.',
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
        GtexPanel(
          title: 'Transfer terms',
          subtitle: 'Club, wage, contract, and clauses',
          child: Column(
            children: <Widget>[
              _TermRow(label: 'GSI', value: player.gsiDetailLabel),
              _TermRow(
                label: 'GSI movement',
                value: player.gsiTrendLabel ?? 'No movement signal',
              ),
              _TermRow(label: 'Market value', value: player.priceLabel),
              _TermRow(label: 'Salary range', value: _salaryLabel(player)),
              _TermRow(label: 'Contract', value: _contractLabel(player)),
              _TermRow(label: 'Buy clause', value: _buyClauseLabel(player)),
              _TermRow(label: 'Swap condition', value: _swapLabel(player)),
              _TermRow(label: 'Loan-to-buy', value: _loanLabel(player)),
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
                label: inBasket ? 'Remove shortlist' : 'Add shortlist',
                icon:
                    inBasket
                        ? Icons.remove_shopping_cart_outlined
                        : Icons.playlist_add,
                onPressed: onToggleBasket,
                accent: inBasket ? GtexColors.red : GtexColors.gold,
              ),
            ),
          ],
        ),
        const SizedBox(height: GtexSpacing.sm),
        Row(
          children: <Widget>[
            Expanded(
              child: GtexActionButton(
                label:
                    isAuthenticated
                        ? player.hasOpenTransferListing
                            ? 'Negotiate'
                            : 'Open player card'
                        : 'Sign in to negotiate',
                icon:
                    isAuthenticated
                        ? player.hasOpenTransferListing
                            ? Icons.handshake_outlined
                            : Icons.open_in_new
                        : Icons.login,
                onPressed: isAuthenticated ? onOpenPlayer : onOpenLogin,
                secondary: true,
              ),
            ),
          ],
        ),
      ],
    );
  }
}
