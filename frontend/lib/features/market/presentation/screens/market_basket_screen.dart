import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gte_frontend/features/transfer_center/live_transfer_center_provider.dart';
import 'package:gte_frontend/shared/state/gtex_async_surface_state.dart';
import 'package:gte_frontend/shared/widgets/gtex_async_state_view.dart';

import '../widgets/market_models.dart';
import '../widgets/market_widgets.dart';

class MarketBasketScreen extends ConsumerWidget {
  const MarketBasketScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final MarketAccessPolicy policy = marketAccessPolicyFromRef(ref);
    final GtexSurfaceState<List<MarketListingViewModel>> state =
        policy.isBlocked || !policy.canUseBasket
            ? GtexBlocked<List<MarketListingViewModel>>(
              reason:
                  policy.blockReason ??
                  policy.actionBlockReason ??
                  'Basket blocked',
            )
            : marketListingSurfaceFromAsync(
              ref.watch(transferCenterListingsProvider),
            );

    return MarketScreenScaffold(
      title: 'Transfer Basket',
      subtitle:
          'Checkout staging only renders records confirmed by the market backend.',
      children: <Widget>[
        MarketRoleBanner(policy: policy),
        const SizedBox(height: 16),
        MarketAsyncSurface<List<MarketListingViewModel>>(
          state: state,
          dataBuilder:
              (List<MarketListingViewModel> listings) => Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: <Widget>[
                  GtexAsyncStateView.empty(
                    title: 'No backend-confirmed basket is active',
                    message:
                        listings.isEmpty
                            ? 'The market provider returned no open listings and no basket DTO.'
                            : '${listings.length} open listing(s) are available, but the backend has not returned basket items for this session.',
                  ),
                  const SizedBox(height: 12),
                  const MarketNoticeBanner(
                    title: 'Basket data source',
                    message:
                        'This screen will render basket rows only when Agent A exposes backend basket DTOs through the market provider layer.',
                    icon: Icons.dataset_linked_rounded,
                  ),
                ],
              ),
        ),
      ],
    );
  }
}
