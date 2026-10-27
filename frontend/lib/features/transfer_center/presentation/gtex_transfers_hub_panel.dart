import 'package:flutter/material.dart';

import '../../../ui_gtex/ui_gtex.dart';
import '../live_transfer_center_provider.dart';

/// Canonical G10 Sporting Transfers Hub panel (Master Plan Document G10, Phase C3).
///
/// Provides the 5-segment sporting transfer surface:
/// `Listings · Offers · Negotiations · Window Bids · Shortlist`
/// with full offer lifecycle timeline, role/status-gated actions, and explicit
/// separation between Sporting Transfers and the Financial Player Share Market.
class GtexTransfersHubPanel extends StatefulWidget {
  const GtexTransfersHubPanel({
    super.key,
    this.initialSegment = GtexTransferHubSegment.listings,
    this.selectedSegment,
    this.onSelectSegment,
    this.activeClubId,
    this.listings = const <TransferCenterListingRecord>[],
    this.offers = const <TransferHubOfferRecord>[],
    this.negotiations = const <TransferNegotiationRecord>[],
    this.shortlist = const <TransferShortlistEntryRecord>[],
    this.windowBidsChild,
    this.onAcceptOffer,
    this.onRejectOffer,
    this.onCounterOffer,
    this.onCancelOffer,
    this.onMakeOfferForListing,
    this.onShortlistListing,
    this.onSubmitContractOffer,
    this.onOpenPlayer,
    this.onOpenFinancialMarket,
    this.confirmConsequentialActions = true,
  });

  final GtexTransferHubSegment initialSegment;
  final GtexTransferHubSegment? selectedSegment;
  final ValueChanged<GtexTransferHubSegment>? onSelectSegment;
  final String? activeClubId;
  final List<TransferCenterListingRecord> listings;
  final List<TransferHubOfferRecord> offers;
  final List<TransferNegotiationRecord> negotiations;
  final List<TransferShortlistEntryRecord> shortlist;
  final Widget? windowBidsChild;
  final Future<void> Function(TransferHubOfferRecord offer)? onAcceptOffer;
  final Future<void> Function(TransferHubOfferRecord offer)? onRejectOffer;
  final Future<void> Function(TransferHubOfferRecord offer)? onCounterOffer;
  final Future<void> Function(TransferHubOfferRecord offer)? onCancelOffer;
  final ValueChanged<TransferCenterListingRecord>? onMakeOfferForListing;
  final ValueChanged<TransferCenterListingRecord>? onShortlistListing;
  final ValueChanged<TransferNegotiationRecord>? onSubmitContractOffer;
  final ValueChanged<String>? onOpenPlayer;
  final VoidCallback? onOpenFinancialMarket;
  final bool confirmConsequentialActions;

  @override
  State<GtexTransfersHubPanel> createState() => _GtexTransfersHubPanelState();
}

class _GtexTransfersHubPanelState extends State<GtexTransfersHubPanel> {
  late GtexTransferHubSegment _internalSegment;

  GtexTransferHubSegment get _activeSegment =>
      widget.selectedSegment ?? _internalSegment;

  @override
  void initState() {
    super.initState();
    _internalSegment = widget.initialSegment;
  }

  void _selectSegment(GtexTransferHubSegment segment) {
    if (widget.onSelectSegment != null) {
      widget.onSelectSegment!(segment);
    }
    if (mounted) {
      setState(() {
        _internalSegment = segment;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        _SportingTransfersBanner(
          onOpenFinancialMarket: widget.onOpenFinancialMarket,
        ),
        const SizedBox(height: GtexSpacing.md),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: GtexTransferHubSegment.values
                .map((GtexTransferHubSegment segment) {
                  final bool isSelected = segment == _activeSegment;
                  return Padding(
                    padding: const EdgeInsets.only(right: GtexSpacing.xs),
                    child: ChoiceChip(
                      key: Key('gtex-transfers-segment-${segment.slug}'),
                      label: Text(segment.label),
                      selected: isSelected,
                      onSelected: (_) => _selectSegment(segment),
                    ),
                  );
                })
                .toList(growable: false),
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        switch (_activeSegment) {
          GtexTransferHubSegment.listings => _ListingsSegmentView(
            listings: widget.listings,
            onMakeOffer: widget.onMakeOfferForListing,
            onShortlist: widget.onShortlistListing,
            onOpenPlayer: widget.onOpenPlayer,
          ),
          GtexTransferHubSegment.offers => _OffersSegmentView(
            offers: widget.offers,
            activeClubId: widget.activeClubId,
            onAcceptOffer: widget.onAcceptOffer,
            onRejectOffer: widget.onRejectOffer,
            onCounterOffer: widget.onCounterOffer,
            onCancelOffer: widget.onCancelOffer,
            onOpenPlayer: widget.onOpenPlayer,
            confirmConsequentialActions: widget.confirmConsequentialActions,
          ),
          GtexTransferHubSegment.negotiations => _NegotiationsSegmentView(
            negotiations: widget.negotiations,
            onSubmitContractOffer: widget.onSubmitContractOffer,
            onOpenPlayer: widget.onOpenPlayer,
          ),
          GtexTransferHubSegment.windowBids =>
            widget.windowBidsChild ??
                const GtexPanel(
                  title: 'Window Bids',
                  subtitle:
                      'Active transfer windows and deadline-window bids from the competition calendar.',
                  accent: GtexNavyColors.info,
                  child: Text(
                    'Select an active transfer window to inspect or place window bids.',
                    style: TextStyle(color: GtexColors.textMuted),
                  ),
                ),
          GtexTransferHubSegment.shortlist => _ShortlistSegmentView(
            shortlist: widget.shortlist,
            onOpenPlayer: widget.onOpenPlayer,
            onMoveToOffers: () => _selectSegment(GtexTransferHubSegment.offers),
          ),
        },
      ],
    );
  }
}

class _SportingTransfersBanner extends StatelessWidget {
  const _SportingTransfersBanner({this.onOpenFinancialMarket});

  final VoidCallback? onOpenFinancialMarket;

  @override
  Widget build(BuildContext context) {
    return Container(
      key: const Key('gtex-sporting-transfers-banner'),
      padding: const EdgeInsets.all(GtexSpacing.md),
      decoration: BoxDecoration(
        color: GtexNavyColors.bgRaised.withValues(alpha: 0.9),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: GtexColors.pitch.withValues(alpha: 0.35),
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Icon(
            Icons.swap_horiz_rounded,
            color: GtexColors.pitch,
            size: 20,
          ),
          const SizedBox(width: GtexSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Sporting Transfers — Club Roster & Registration',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 4),
                const Text(
                  'Sporting transfers move players between club squads and competition registrations. Financial player shares and cards live in the separate Market lane.',
                  style: TextStyle(color: GtexColors.textMuted, height: 1.35),
                ),
              ],
            ),
          ),
          if (onOpenFinancialMarket != null) ...<Widget>[
            const SizedBox(width: GtexSpacing.sm),
            GtexActionButton(
              label: 'Open Financial Market',
              icon: Icons.storefront_outlined,
              compact: true,
              secondary: true,
              onPressed: onOpenFinancialMarket,
            ),
          ],
        ],
      ),
    );
  }
}

class _ListingsSegmentView extends StatelessWidget {
  const _ListingsSegmentView({
    required this.listings,
    this.onMakeOffer,
    this.onShortlist,
    this.onOpenPlayer,
  });

  final List<TransferCenterListingRecord> listings;
  final ValueChanged<TransferCenterListingRecord>? onMakeOffer;
  final ValueChanged<TransferCenterListingRecord>? onShortlist;
  final ValueChanged<String>? onOpenPlayer;

  @override
  Widget build(BuildContext context) {
    if (listings.isEmpty) {
      return const GtexPanel(
        title: 'Sporting Transfer Listings',
        subtitle: 'Players listed for permanent transfer, loan, or swap.',
        accent: GtexColors.pitch,
        child: Text(
          'No active transfer listings match the current club filter.',
          style: TextStyle(color: GtexColors.textMuted),
        ),
      );
    }

    return Column(
      children: listings
          .map(
            (TransferCenterListingRecord listing) => Padding(
              padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
              child: GtexPanel(
                key: Key('gtex-transfer-listing-${listing.id}'),
                title: listing.playerName,
                subtitle:
                    '${listing.currentClubName ?? listing.sellingClubId} · ${listing.marketSignal}',
                accent: GtexColors.pitch,
                trailing: GtexStatusChip.fromBackendStatus(
                  listing.status,
                  context: GtexStatusContext.transfer,
                  compact: true,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Wrap(
                      spacing: GtexSpacing.md,
                      runSpacing: GtexSpacing.xs,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: <Widget>[
                        Row(
                          mainAxisSize: MainAxisSize.min,
                          children: <Widget>[
                            const Text(
                              'Asking: ',
                              style: TextStyle(color: GtexColors.textMuted),
                            ),
                            GtexMoney(
                              amount: listing.basePrice,
                              size: GtexMoneySize.small,
                            ),
                          ],
                        ),
                        Row(
                          mainAxisSize: MainAxisSize.min,
                          children: <Widget>[
                            const Text(
                              'Highest bid: ',
                              style: TextStyle(color: GtexColors.textMuted),
                            ),
                            GtexMoney(
                              amount: listing.currentHighestBid,
                              size: GtexMoneySize.small,
                            ),
                          ],
                        ),
                        _MetaTagPill(
                          label: '${listing.bidCount} bids',
                          icon: Icons.gavel_outlined,
                          color: GtexNavyColors.info,
                        ),
                        _MetaTagPill(
                          label: '${listing.watchlistCount} watching',
                          icon: Icons.visibility_outlined,
                          color: GtexNavyColors.textSecondary,
                        ),
                      ],
                    ),
                    const SizedBox(height: GtexSpacing.sm),
                    Wrap(
                      spacing: GtexSpacing.xs,
                      runSpacing: GtexSpacing.xs,
                      children: <Widget>[
                        FilledButton.tonalIcon(
                          key: Key('gtex-listing-make-offer-${listing.id}'),
                          onPressed:
                              listing.isTerminal || onMakeOffer == null
                                  ? null
                                  : () => onMakeOffer!(listing),
                          icon: const Icon(Icons.local_offer_outlined, size: 16),
                          label: const Text('Make offer'),
                        ),
                        OutlinedButton.icon(
                          key: Key('gtex-listing-shortlist-${listing.id}'),
                          onPressed:
                              listing.isTerminal || onShortlist == null
                                  ? null
                                  : () => onShortlist!(listing),
                          icon: const Icon(
                            Icons.bookmark_add_outlined,
                            size: 16,
                          ),
                          label: const Text('Shortlist'),
                        ),
                        if (onOpenPlayer != null && listing.playerId.isNotEmpty)
                          TextButton.icon(
                            key: Key('gtex-listing-open-player-${listing.id}'),
                            onPressed: () => onOpenPlayer!(listing.playerId),
                            icon: const Icon(Icons.person_outline, size: 16),
                            label: const Text('Open player profile'),
                          ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          )
          .toList(growable: false),
    );
  }
}

class _OffersSegmentView extends StatelessWidget {
  const _OffersSegmentView({
    required this.offers,
    this.activeClubId,
    this.onAcceptOffer,
    this.onRejectOffer,
    this.onCounterOffer,
    this.onCancelOffer,
    this.onOpenPlayer,
    this.confirmConsequentialActions = true,
  });

  final List<TransferHubOfferRecord> offers;
  final String? activeClubId;
  final Future<void> Function(TransferHubOfferRecord offer)? onAcceptOffer;
  final Future<void> Function(TransferHubOfferRecord offer)? onRejectOffer;
  final Future<void> Function(TransferHubOfferRecord offer)? onCounterOffer;
  final Future<void> Function(TransferHubOfferRecord offer)? onCancelOffer;
  final ValueChanged<String>? onOpenPlayer;
  final bool confirmConsequentialActions;

  Future<void> _confirmAndRun(
    BuildContext context, {
    required String title,
    required String summary,
    required String confirmLabel,
    required GtexConfirmVariant variant,
    required Future<void> Function() action,
  }) async {
    if (!confirmConsequentialActions) {
      await action();
      return;
    }
    await GtexConfirmSheet.show(
      context,
      title: title,
      summary: summary,
      confirmLabel: confirmLabel,
      variant: variant,
      onConfirm: (_) async {
        await action();
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    if (offers.isEmpty) {
      return const GtexPanel(
        title: 'Transfer Offers Lifecycle',
        subtitle:
            'Track incoming and outgoing club offers from draft to final settlement.',
        accent: GtexColors.gold,
        child: Text(
          'No active or historical transfer offers recorded for this club.',
          style: TextStyle(color: GtexColors.textMuted),
        ),
      );
    }

    return Column(
      children: offers
          .map((TransferHubOfferRecord offer) {
            final bool canAccept =
                offer.canAccept(activeClubId: activeClubId) &&
                onAcceptOffer != null;
            final bool canReject =
                offer.canReject(activeClubId: activeClubId) &&
                onRejectOffer != null;
            final bool canCounter =
                offer.canCounter(activeClubId: activeClubId) &&
                onCounterOffer != null;
            final bool canCancel =
                offer.canCancel(activeClubId: activeClubId) &&
                onCancelOffer != null;
            final String titleLabel =
                offer.playerName.isNotEmpty
                    ? '${offer.playerName} (${offer.offerType.toUpperCase()})'
                    : 'Offer #${offer.id} (${offer.offerType.toUpperCase()})';

            return Padding(
              padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
              child: GtexPanel(
                key: Key('gtex-transfer-offer-${offer.id}'),
                title: titleLabel,
                subtitle:
                    'Seller: ${offer.sellerClubId} ↔ Bidder: ${offer.bidderClubId} · ${offer.expiryCountdownLabel}',
                accent: GtexColors.gold,
                trailing: GtexStatusChip.fromBackendStatus(
                  offer.status,
                  context: GtexStatusContext.offer,
                  compact: true,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    _OfferLifecycleTimelineStrip(
                      offerId: offer.id,
                      stages: offer.lifecycleTimeline,
                    ),
                    const SizedBox(height: GtexSpacing.sm),
                    Wrap(
                      spacing: GtexSpacing.md,
                      runSpacing: GtexSpacing.xs,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: <Widget>[
                        Row(
                          mainAxisSize: MainAxisSize.min,
                          children: <Widget>[
                            const Text(
                              'Fee: ',
                              style: TextStyle(color: GtexColors.textMuted),
                            ),
                            GtexMoney(
                              amount: offer.cashAmount,
                              isPending: offer.statusView.isPendingLike,
                              size: GtexMoneySize.small,
                            ),
                          ],
                        ),
                        if (offer.sellOnPercentage != null)
                          _MetaTagPill(
                            label:
                                'Sell-on ${offer.sellOnPercentage!.toStringAsFixed(0)}%',
                            icon: Icons.percent_rounded,
                            color: GtexNavyColors.info,
                          ),
                        if (offer.offeredPlayerIds.isNotEmpty)
                          _MetaTagPill(
                            label:
                                '+${offer.offeredPlayerIds.length} swap player(s)',
                            icon: Icons.swap_calls_rounded,
                            color: GtexNavyColors.warning,
                          ),
                      ],
                    ),
                    if ((offer.message ?? '').trim().isNotEmpty) ...<Widget>[
                      const SizedBox(height: GtexSpacing.xs),
                      Text(
                        offer.message!.trim(),
                        style: const TextStyle(color: GtexColors.textMuted),
                      ),
                    ],
                    const SizedBox(height: GtexSpacing.sm),
                    Wrap(
                      spacing: GtexSpacing.xs,
                      runSpacing: GtexSpacing.xs,
                      children: <Widget>[
                        FilledButton.tonal(
                          key: Key('gtex-offer-accept-${offer.id}'),
                          onPressed:
                              canAccept
                                  ? () => _confirmAndRun(
                                    context,
                                    title: 'Accept transfer offer?',
                                    summary:
                                        'Accepting offer #${offer.id} between ${offer.sellerClubId} and ${offer.bidderClubId} commits this transfer agreement.',
                                    confirmLabel: 'Accept offer',
                                    variant: GtexConfirmVariant.financial,
                                    action: () => onAcceptOffer!(offer),
                                  )
                                  : null,
                          child: const Text('Accept'),
                        ),
                        FilledButton.tonal(
                          key: Key('gtex-offer-counter-${offer.id}'),
                          onPressed:
                              canCounter ? () => onCounterOffer!(offer) : null,
                          child: const Text('Counter'),
                        ),
                        OutlinedButton(
                          key: Key('gtex-offer-reject-${offer.id}'),
                          onPressed:
                              canReject
                                  ? () => _confirmAndRun(
                                    context,
                                    title: 'Reject transfer offer?',
                                    summary:
                                        'Rejecting offer #${offer.id} closes this offer path.',
                                    confirmLabel: 'Reject offer',
                                    variant: GtexConfirmVariant.destructive,
                                    action: () => onRejectOffer!(offer),
                                  )
                                  : null,
                          child: const Text('Reject'),
                        ),
                        OutlinedButton(
                          key: Key('gtex-offer-cancel-${offer.id}'),
                          onPressed:
                              canCancel
                                  ? () => _confirmAndRun(
                                    context,
                                    title: 'Cancel transfer offer?',
                                    summary:
                                        'Cancelling offer #${offer.id} withdraws your club bid.',
                                    confirmLabel: 'Cancel offer',
                                    variant: GtexConfirmVariant.destructive,
                                    action: () => onCancelOffer!(offer),
                                  )
                                  : null,
                          child: const Text('Cancel'),
                        ),
                        if (offer.isCompletedTransfer &&
                            offer.playerId.isNotEmpty &&
                            onOpenPlayer != null)
                          TextButton.icon(
                            key: Key('gtex-offer-open-player-${offer.id}'),
                            onPressed: () => onOpenPlayer!(offer.playerId),
                            icon: const Icon(Icons.person_outline, size: 16),
                            label: const Text('Open player profile'),
                          ),
                      ],
                    ),
                  ],
                ),
              ),
            );
          })
          .toList(growable: false),
    );
  }
}

class _OfferLifecycleTimelineStrip extends StatelessWidget {
  const _OfferLifecycleTimelineStrip({
    required this.offerId,
    required this.stages,
  });

  final String offerId;
  final List<GtexTransferOfferLifecycleStage> stages;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      key: Key('gtex-offer-timeline-$offerId'),
      spacing: GtexSpacing.xs,
      runSpacing: GtexSpacing.xs,
      children: stages
          .map((GtexTransferOfferLifecycleStage stage) {
            final (Color color, IconData icon) = switch (stage.state) {
              GtexTransferOfferLifecycleStageState.completed => (
                GtexNavyColors.success,
                Icons.check_circle_outline_rounded,
              ),
              GtexTransferOfferLifecycleStageState.active => (
                GtexNavyColors.warning,
                Icons.radio_button_checked_rounded,
              ),
              GtexTransferOfferLifecycleStageState.upcoming => (
                GtexNavyColors.textSecondary,
                Icons.radio_button_unchecked_rounded,
              ),
              GtexTransferOfferLifecycleStageState.terminalFailure => (
                GtexNavyColors.danger,
                Icons.cancel_outlined,
              ),
            };

            return Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.14),
                borderRadius: BorderRadius.circular(999),
                border: Border.all(color: color.withValues(alpha: 0.42)),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  Icon(icon, size: 14, color: color),
                  const SizedBox(width: 5),
                  Text(
                    stage.label,
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: GtexColors.text,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
            );
          })
          .toList(growable: false),
    );
  }
}

class _NegotiationsSegmentView extends StatelessWidget {
  const _NegotiationsSegmentView({
    required this.negotiations,
    this.onSubmitContractOffer,
    this.onOpenPlayer,
  });

  final List<TransferNegotiationRecord> negotiations;
  final ValueChanged<TransferNegotiationRecord>? onSubmitContractOffer;
  final ValueChanged<String>? onOpenPlayer;

  @override
  Widget build(BuildContext context) {
    if (negotiations.isEmpty) {
      return const GtexPanel(
        title: 'Player & Agent Negotiations',
        subtitle:
            'Contract terms, coach tactical opinion, and agent clause alignment.',
        accent: GtexNavyColors.info,
        child: Text(
          'No active contract negotiations require your input right now.',
          style: TextStyle(color: GtexColors.textMuted),
        ),
      );
    }

    return Column(
      children: negotiations
          .map(
            (TransferNegotiationRecord negotiation) => Padding(
              padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
              child: GtexPanel(
                key: Key('gtex-transfer-negotiation-${negotiation.id}'),
                title:
                    negotiation.playerName.isNotEmpty
                        ? negotiation.playerName
                        : 'Negotiation #${negotiation.id}',
                subtitle:
                    '${negotiation.sellingClubId} → ${negotiation.bidderClubId} · ${negotiation.contractYears} yr contract${negotiation.expectedRole == null ? '' : ' · Role: ${negotiation.expectedRole}'}',
                accent: GtexNavyColors.info,
                trailing: GtexStatusChip.fromBackendStatus(
                  negotiation.status,
                  context: GtexStatusContext.offer,
                  compact: true,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Wrap(
                      spacing: GtexSpacing.sm,
                      runSpacing: GtexSpacing.xs,
                      children: <Widget>[
                        if (negotiation.wageOfferAmount != null)
                          Row(
                            mainAxisSize: MainAxisSize.min,
                            children: <Widget>[
                              const Text(
                                'Wage offer: ',
                                style: TextStyle(color: GtexColors.textMuted),
                              ),
                              GtexMoney(
                                amount: negotiation.wageOfferAmount!,
                                size: GtexMoneySize.small,
                              ),
                            ],
                          ),
                        if (negotiation.playerInterestLevel != null)
                          _MetaTagPill(
                            label:
                                'Player interest: ${negotiation.playerInterestLevel}',
                            icon: Icons.person_pin_circle_outlined,
                            color: GtexNavyColors.info,
                          ),
                        if (negotiation.coachStance != null)
                          _MetaTagPill(
                            label: 'Coach: ${negotiation.coachStance}',
                            icon: Icons.sports_outlined,
                            color:
                                negotiation.coachStance == 'approve'
                                    ? GtexNavyColors.success
                                    : negotiation.coachStance == 'reject'
                                    ? GtexNavyColors.danger
                                    : GtexNavyColors.warning,
                          ),
                        if (negotiation.agentAction != null)
                          _MetaTagPill(
                            label: 'Agent: ${negotiation.agentAction}',
                            icon: Icons.handshake_outlined,
                            color: GtexNavyColors.textSecondary,
                          ),
                      ],
                    ),
                    if ((negotiation.coachReason ?? '').isNotEmpty) ...<Widget>[
                      const SizedBox(height: GtexSpacing.xs),
                      Text(
                        'Coach note: ${negotiation.coachReason}',
                        style: const TextStyle(color: GtexColors.textMuted),
                      ),
                    ],
                    if (negotiation.concerns.isNotEmpty) ...<Widget>[
                      const SizedBox(height: GtexSpacing.xs),
                      Text(
                        'Concerns: ${negotiation.concerns.join(', ')}',
                        style: const TextStyle(color: GtexNavyColors.warning),
                      ),
                    ],
                    const SizedBox(height: GtexSpacing.sm),
                    Wrap(
                      spacing: GtexSpacing.xs,
                      runSpacing: GtexSpacing.xs,
                      children: <Widget>[
                        FilledButton.tonalIcon(
                          key: Key(
                            'gtex-negotiation-submit-contract-${negotiation.id}',
                          ),
                          onPressed:
                              negotiation.isTerminal ||
                                      onSubmitContractOffer == null
                                  ? null
                                  : () => onSubmitContractOffer!(negotiation),
                          icon: const Icon(Icons.description_outlined, size: 16),
                          label: const Text('Submit contract offer'),
                        ),
                        if (onOpenPlayer != null &&
                            negotiation.playerId.isNotEmpty)
                          TextButton.icon(
                            onPressed: () => onOpenPlayer!(negotiation.playerId),
                            icon: const Icon(Icons.person_outline, size: 16),
                            label: const Text('Open player profile'),
                          ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          )
          .toList(growable: false),
    );
  }
}

class _ShortlistSegmentView extends StatelessWidget {
  const _ShortlistSegmentView({
    required this.shortlist,
    this.onOpenPlayer,
    this.onMoveToOffers,
  });

  final List<TransferShortlistEntryRecord> shortlist;
  final ValueChanged<String>? onOpenPlayer;
  final VoidCallback? onMoveToOffers;

  @override
  Widget build(BuildContext context) {
    final double totalEstimatedCredits = shortlist.fold<double>(
      0,
      (double sum, TransferShortlistEntryRecord item) =>
          sum + item.estimatedFeeCredits,
    );

    return GtexPanel(
      title: 'Recruitment Shortlist & Transfer Basket',
      subtitle:
          'Tracked targets bridged from Scouting & Recruitment into active transfer offers.',
      accent: GtexColors.pitch,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              const Text(
                'Estimated basket total: ',
                style: TextStyle(color: GtexColors.textMuted),
              ),
              GtexMoney(
                amount: totalEstimatedCredits,
                size: GtexMoneySize.small,
              ),
              const Spacer(),
              if (onMoveToOffers != null)
                GtexActionButton(
                  label: 'Review Offers',
                  icon: Icons.swap_horiz_rounded,
                  compact: true,
                  secondary: true,
                  onPressed: onMoveToOffers,
                ),
            ],
          ),
          const SizedBox(height: GtexSpacing.sm),
          if (shortlist.isEmpty)
            const Text(
              'No shortlisted targets yet. Add players from Listings or Recruitment to build your transfer basket.',
              style: TextStyle(color: GtexColors.textMuted),
            )
          else
            Column(
              children: shortlist
                  .map(
                    (TransferShortlistEntryRecord item) => Padding(
                      padding: const EdgeInsets.only(bottom: GtexSpacing.xs),
                      child: ListTile(
                        key: Key('gtex-transfer-shortlist-${item.id}'),
                        contentPadding: EdgeInsets.zero,
                        title: Text(
                          item.playerName,
                          style: const TextStyle(
                            color: GtexColors.text,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        subtitle: Text(
                          'Source: ${item.source} · Discovery score ${item.discoveryScore.toStringAsFixed(0)}',
                          style: const TextStyle(color: GtexColors.textMuted),
                        ),
                        trailing:
                            onOpenPlayer == null
                                ? null
                                : TextButton(
                                  onPressed: () => onOpenPlayer!(item.playerId),
                                  child: const Text('Profile'),
                                ),
                      ),
                    ),
                  )
                  .toList(growable: false),
            ),
        ],
      ),
    );
  }
}

class _MetaTagPill extends StatelessWidget {
  const _MetaTagPill({
    required this.label,
    required this.icon,
    required this.color,
  });

  final String label;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.35)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(icon, size: 13, color: color),
          const SizedBox(width: 4),
          Text(
            label,
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: GtexColors.text,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}
