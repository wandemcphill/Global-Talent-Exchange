import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gte_frontend/features/transfer_center/live_transfer_center_provider.dart';
import 'package:gte_frontend/shared/state/gtex_async_surface_state.dart';

import '../widgets/market_models.dart';
import '../widgets/market_widgets.dart';

class MarketPlayerDetailScreen extends ConsumerWidget {
  const MarketPlayerDetailScreen({
    super.key,
    required this.listingId,
    this.onOpenBid,
  });

  final String listingId;
  final ValueChanged<MarketBidViewModel>? onOpenBid;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final MarketAccessPolicy policy = marketAccessPolicyFromRef(ref);
    final GtexSurfaceState<MarketDetailViewModel> state;
    if (policy.isBlocked) {
      state = GtexBlocked<MarketDetailViewModel>(
        reason: policy.blockReason ?? 'Market detail blocked',
      );
    } else {
      final AsyncValue<TransferCenterDetailData> detailValue =
          ref.watch(transferCenterDetailProvider(listingId))
              as AsyncValue<TransferCenterDetailData>;
      state = _detailSurfaceFromAsync(detailValue);
    }

    return MarketScreenScaffold(
      title: 'Player Detail',
      subtitle:
          'Player valuation, bids, and wallet reservation truth from backend listing detail.',
      children: <Widget>[
        MarketRoleBanner(policy: policy),
        const SizedBox(height: 16),
        MarketAsyncSurface<MarketDetailViewModel>(
          state: state,
          emptyTitle: 'Player listing unavailable',
          emptyMessage: 'The backend did not return this listing.',
          dataBuilder: (MarketDetailViewModel detail) {
            final MarketListingViewModel listing = detail.listing;
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                MarketPlayerCard(listing: listing, policy: policy),
                const SizedBox(height: 16),
                MarketActionBar(policy: policy),
                const SizedBox(height: 16),
                BidEventTimeline(bids: listing.bids),
                if (detail.negotiation == null) ...<Widget>[
                  const SizedBox(height: 16),
                  const MarketNoticeBanner(
                    title: 'Negotiation pending',
                    message:
                        'The backend did not return a negotiation DTO for this listing.',
                    icon: Icons.pending_actions_rounded,
                  ),
                ],
              ],
            );
          },
        ),
      ],
    );
  }
}

GtexSurfaceState<MarketDetailViewModel> _detailSurfaceFromAsync(
  AsyncValue<TransferCenterDetailData> value,
) {
  if (value.hasValue) {
    final MarketDetailViewModel detail =
        MarketDetailViewModel.fromTransferCenter(value.requireValue);
    if (value.isRefreshing || value.isReloading) {
      return GtexSyncing<MarketDetailViewModel>(current: detail);
    }
    return GtexData<MarketDetailViewModel>(data: detail);
  }
  if (value.isLoading) {
    return const GtexLoading<MarketDetailViewModel>();
  }
  if (value.hasError) {
    return GtexError<MarketDetailViewModel>(
      code: 'market.detail',
      message: value.error?.toString() ?? 'Market detail request failed.',
    );
  }
  return const GtexLoading<MarketDetailViewModel>();
}
