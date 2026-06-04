import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gte_frontend/features/transfer_center/live_transfer_center_provider.dart';
import 'package:gte_frontend/shared/state/gtex_async_surface_state.dart';

import '../widgets/market_models.dart';
import '../widgets/market_widgets.dart';

class MarketHubScreen extends ConsumerWidget {
  const MarketHubScreen({
    super.key,
    this.onOpenSearch,
    this.onOpenBasket,
    this.onOpenActivity,
    this.onOpenListing,
  });

  final VoidCallback? onOpenSearch;
  final VoidCallback? onOpenBasket;
  final VoidCallback? onOpenActivity;
  final ValueChanged<MarketListingViewModel>? onOpenListing;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final MarketAccessPolicy policy = marketAccessPolicyFromRef(ref);
    final GtexSurfaceState<List<MarketListingViewModel>> state;
    if (policy.isBlocked) {
      state = GtexBlocked<List<MarketListingViewModel>>(
        reason: policy.blockReason ?? 'Market blocked',
      );
    } else {
      state = marketListingSurfaceFromAsync(
        ref.watch(transferCenterListingsProvider),
        emptyReason: 'No players match your search',
      );
    }

    return MarketScreenScaffold(
      title: 'Market',
      subtitle:
          'Live transfer operations built from backend listing, bidder, and reservation DTOs.',
      actions: <Widget>[
        IconButton(
          tooltip: 'Search',
          onPressed: onOpenSearch,
          icon: const Icon(Icons.search_rounded),
        ),
        IconButton(
          tooltip: 'Basket',
          onPressed: policy.canUseBasket ? onOpenBasket : null,
          icon: const Icon(Icons.playlist_add_check_rounded),
        ),
      ],
      children: <Widget>[
        MarketRoleBanner(policy: policy),
        const SizedBox(height: 16),
        MarketAsyncSurface<List<MarketListingViewModel>>(
          state: state,
          loadingBuilder: () => const MarketPlayerCardSkeleton(),
          dataBuilder:
              (List<MarketListingViewModel> listings) => Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: <Widget>[
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: <Widget>[
                      MarketMetricPill(
                        label: 'Open listings',
                        value: '${listings.length}',
                      ),
                      MarketMetricPill(
                        label: 'Bid rows',
                        value:
                            '${listings.fold<int>(0, (int total, MarketListingViewModel item) => total + item.bidCount)}',
                      ),
                      MarketMetricPill(
                        label: 'Activity',
                        value: onOpenActivity == null ? 'Backend feed' : 'Open',
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  MarketListingGrid(
                    listings: listings,
                    policy: policy,
                    onOpenListing: onOpenListing,
                  ),
                ],
              ),
        ),
      ],
    );
  }
}
