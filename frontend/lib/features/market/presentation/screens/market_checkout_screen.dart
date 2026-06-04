import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gte_frontend/features/transfer_center/live_transfer_center_provider.dart';
import 'package:gte_frontend/shared/state/gtex_async_surface_state.dart';

import '../widgets/market_models.dart';
import '../widgets/market_widgets.dart';

class MarketCheckoutScreen extends ConsumerWidget {
  const MarketCheckoutScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final MarketAccessPolicy policy = marketAccessPolicyFromRef(ref);
    final GtexSurfaceState<List<MarketListingViewModel>> state =
        policy.isBlocked
            ? GtexBlocked<List<MarketListingViewModel>>(
              reason: policy.blockReason ?? 'Checkout blocked',
            )
            : marketListingSurfaceFromAsync(
              ref.watch(transferCenterListingsProvider),
            );

    return MarketScreenScaffold(
      title: 'Checkout Readiness',
      subtitle:
          'Owner approval, role gates, and backend listing state before a transfer checkout.',
      children: <Widget>[
        MarketRoleBanner(policy: policy),
        const SizedBox(height: 16),
        MarketAsyncSurface<List<MarketListingViewModel>>(
          state: state,
          dataBuilder:
              (List<MarketListingViewModel> listings) =>
                  CheckoutReadinessPanel(policy: policy, listings: listings),
        ),
      ],
    );
  }
}
