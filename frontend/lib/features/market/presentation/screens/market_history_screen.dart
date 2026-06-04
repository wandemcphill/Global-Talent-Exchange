import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gte_frontend/shared/state/gtex_async_surface_state.dart';

import '../widgets/market_models.dart';
import '../widgets/market_widgets.dart';

class MarketHistoryScreen extends ConsumerWidget {
  const MarketHistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final MarketAccessPolicy policy = marketAccessPolicyFromRef(ref);
    final GtexSurfaceState<List<MarketListingViewModel>> state =
        policy.isBlocked
            ? GtexBlocked<List<MarketListingViewModel>>(
              reason: policy.blockReason ?? 'Market history blocked',
            )
            : const GtexEmpty<List<MarketListingViewModel>>(
              reason:
                  'Market history endpoint not returned by backend provider.',
            );

    return MarketScreenScaffold(
      title: 'Market History',
      subtitle:
          'Completed and withdrawn transfers require backend history DTOs before rendering.',
      children: <Widget>[
        MarketRoleBanner(policy: policy),
        const SizedBox(height: 16),
        MarketAsyncSurface<List<MarketListingViewModel>>(
          state: state,
          emptyTitle: 'No backend history records',
          emptyMessage:
              'History is intentionally empty until the backend exposes market history records.',
          dataBuilder:
              (List<MarketListingViewModel> listings) =>
                  MarketListingGrid(listings: listings, policy: policy),
        ),
      ],
    );
  }
}
