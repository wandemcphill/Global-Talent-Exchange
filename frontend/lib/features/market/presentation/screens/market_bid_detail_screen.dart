import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gte_frontend/features/transfer_center/live_transfer_center_provider.dart';
import 'package:gte_frontend/features/transfer_center/transfer_center_models.dart';
import 'package:gte_frontend/shared/state/gtex_async_surface_state.dart';

import '../widgets/market_models.dart';
import '../widgets/market_widgets.dart';

class MarketBidDetailScreen extends ConsumerWidget {
  const MarketBidDetailScreen({super.key, required this.bidId});

  final String bidId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final MarketAccessPolicy policy = marketAccessPolicyFromRef(ref);
    final GtexSurfaceState<MarketBidDetailViewModel> state;
    if (policy.isBlocked) {
      state = GtexBlocked<MarketBidDetailViewModel>(
        reason: policy.blockReason ?? 'Bid detail blocked',
      );
    } else {
      state = _bidDetailSurfaceFromAsync(
        ref.watch(transferCenterListingsProvider),
        bidId,
      );
    }

    return MarketScreenScaffold(
      title: 'Bid Detail',
      subtitle:
          'Bid lifecycle and wallet reservation truth from backend bidder rows.',
      children: <Widget>[
        MarketRoleBanner(policy: policy),
        const SizedBox(height: 16),
        MarketAsyncSurface<MarketBidDetailViewModel>(
          state: state,
          emptyTitle: 'Bid detail unavailable',
          emptyMessage:
              'The backend did not return a bidder row for this bid id.',
          dataBuilder: (MarketBidDetailViewModel detail) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                MarketPlayerCard(listing: detail.listing, policy: policy),
                const SizedBox(height: 16),
                BidEventTimeline(bids: <MarketBidViewModel>[detail.bid]),
                const SizedBox(height: 16),
                MarketReservationPanel(bid: detail.bid),
              ],
            );
          },
        ),
      ],
    );
  }
}

GtexSurfaceState<MarketBidDetailViewModel> _bidDetailSurfaceFromAsync(
  AsyncValue<List<TransferCenterListingRecord>> value,
  String bidId,
) {
  final GtexSurfaceState<List<MarketListingViewModel>> listingState =
      marketListingSurfaceFromAsync(value);
  MarketBidDetailViewModel? find(List<MarketListingViewModel> listings) {
    for (final MarketListingViewModel listing in listings) {
      final MarketBidViewModel? bid = listing.bidById(bidId);
      if (bid != null) {
        return MarketBidDetailViewModel(
          listing: listing,
          bid: bid,
          negotiation: null,
        );
      }
    }
    return null;
  }

  if (listingState is GtexData<List<MarketListingViewModel>>) {
    final MarketBidDetailViewModel? detail = find(listingState.data);
    return detail == null
        ? const GtexEmpty<MarketBidDetailViewModel>(
          reason: 'Bid detail backend row not returned.',
        )
        : GtexData<MarketBidDetailViewModel>(data: detail);
  }
  if (listingState is GtexSyncing<List<MarketListingViewModel>>) {
    final MarketBidDetailViewModel? detail = find(listingState.current);
    return detail == null
        ? const GtexEmpty<MarketBidDetailViewModel>(
          reason: 'Bid detail backend row not returned.',
        )
        : GtexSyncing<MarketBidDetailViewModel>(current: detail);
  }
  if (listingState is GtexError<List<MarketListingViewModel>>) {
    return GtexError<MarketBidDetailViewModel>(
      code: listingState.code,
      message: listingState.message,
    );
  }
  if (listingState is GtexBlocked<List<MarketListingViewModel>>) {
    return GtexBlocked<MarketBidDetailViewModel>(
      reason: listingState.reason,
      ctaRoute: listingState.ctaRoute,
    );
  }
  if (listingState is GtexLoading<List<MarketListingViewModel>>) {
    return const GtexLoading<MarketBidDetailViewModel>();
  }
  return const GtexEmpty<MarketBidDetailViewModel>(
    reason: 'Bid detail backend row not returned.',
  );
}
