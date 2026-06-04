import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gte_frontend/features/transfer_center/live_transfer_center_provider.dart';
import 'package:gte_frontend/shared/state/gtex_async_surface_state.dart';

import '../widgets/market_models.dart';
import '../widgets/market_widgets.dart';

class MarketActivityScreen extends ConsumerWidget {
  const MarketActivityScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final MarketAccessPolicy policy = marketAccessPolicyFromRef(ref);
    final GtexSurfaceState<List<MarketBidViewModel>> state =
        policy.isBlocked
            ? GtexBlocked<List<MarketBidViewModel>>(
              reason: policy.blockReason ?? 'Market activity blocked',
            )
            : _activitySurfaceFromListings(
              marketListingSurfaceFromAsync(
                ref.watch(transferCenterListingsProvider),
              ),
            );

    return MarketScreenScaffold(
      title: 'Market Activity',
      subtitle:
          'Realtime-adjacent activity rendered only from backend bid rows already returned by the market feed.',
      children: <Widget>[
        MarketRoleBanner(policy: policy),
        const SizedBox(height: 16),
        MarketAsyncSurface<List<MarketBidViewModel>>(
          state: state,
          emptyTitle: 'No backend activity events',
          emptyMessage:
              'The market activity endpoint has not returned events for this session.',
          dataBuilder:
              (List<MarketBidViewModel> bids) => BidEventTimeline(bids: bids),
        ),
      ],
    );
  }
}

GtexSurfaceState<List<MarketBidViewModel>> _activitySurfaceFromListings(
  GtexSurfaceState<List<MarketListingViewModel>> source,
) {
  List<MarketBidViewModel> bids(List<MarketListingViewModel> listings) {
    return listings
        .expand((MarketListingViewModel listing) => listing.bids)
        .toList(growable: false);
  }

  if (source is GtexData<List<MarketListingViewModel>>) {
    final List<MarketBidViewModel> rows = bids(source.data);
    return rows.isEmpty
        ? const GtexEmpty<List<MarketBidViewModel>>(
          reason: 'No backend activity events',
        )
        : GtexData<List<MarketBidViewModel>>(data: rows);
  }
  if (source is GtexSyncing<List<MarketListingViewModel>>) {
    return GtexSyncing<List<MarketBidViewModel>>(current: bids(source.current));
  }
  if (source is GtexError<List<MarketListingViewModel>>) {
    return GtexError<List<MarketBidViewModel>>(
      code: source.code,
      message: source.message,
    );
  }
  if (source is GtexBlocked<List<MarketListingViewModel>>) {
    return GtexBlocked<List<MarketBidViewModel>>(
      reason: source.reason,
      ctaRoute: source.ctaRoute,
    );
  }
  if (source is GtexLoading<List<MarketListingViewModel>>) {
    return const GtexLoading<List<MarketBidViewModel>>();
  }
  return const GtexEmpty<List<MarketBidViewModel>>(
    reason: 'No backend activity events',
  );
}
