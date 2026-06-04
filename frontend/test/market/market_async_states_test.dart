import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/market/presentation/widgets/market_models.dart';
import 'package:gte_frontend/features/market/presentation/widgets/market_widgets.dart';
import 'package:gte_frontend/shared/state/gtex_async_surface_state.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('MarketAsyncSurface renders every surface state', (
    WidgetTester tester,
  ) async {
    final List<MarketListingViewModel> data = <MarketListingViewModel>[
      _listing(),
    ];
    final List<_Case> cases = <_Case>[
      _Case(
        const GtexLoading<List<MarketListingViewModel>>(),
        'Loading market data',
      ),
      _Case(
        const GtexEmpty<List<MarketListingViewModel>>(
          reason: 'No players match your search',
        ),
        'No players match your search',
      ),
      _Case(
        const GtexBlocked<List<MarketListingViewModel>>(
          reason: 'Scout read-only access',
        ),
        'Scout read-only access',
      ),
      _Case(
        GtexPending<List<MarketListingViewModel>>(stale: data),
        'Bid update pending',
      ),
      _Case(
        GtexSyncing<List<MarketListingViewModel>>(current: data),
        'Syncing latest market data',
      ),
      _Case(
        GtexReconnecting<List<MarketListingViewModel>>(
          lastKnown: data,
          attempt: 2,
        ),
        'Reconnecting market feed',
      ),
      _Case(
        GtexDegraded<List<MarketListingViewModel>>(
          current: data,
          warning: 'Market data may be delayed by the live feed.',
        ),
        'Market data may be delayed',
      ),
      _Case(
        GtexConfirmed<List<MarketListingViewModel>>(
          data: data,
          auditRef: 'audit-123',
        ),
        'audit-123',
      ),
      _Case(
        const GtexError<List<MarketListingViewModel>>(
          code: 'backend',
          message: 'Backend unavailable',
        ),
        'Market error backend',
      ),
      _Case(GtexData<List<MarketListingViewModel>>(data: data), 'Ada Striker'),
    ];

    for (final _Case item in cases) {
      await tester.pumpWidget(_wrap(item.state));
      await tester.pump();
      expect(find.textContaining(item.expectedText), findsWidgets);
    }
  });
}

Widget _wrap(GtexSurfaceState<List<MarketListingViewModel>> state) {
  return MaterialApp(
    theme: GteShellTheme.build(),
    home: Scaffold(
      body: SingleChildScrollView(
        child: MarketAsyncSurface<List<MarketListingViewModel>>(
          state: state,
          dataBuilder:
              (List<MarketListingViewModel> data) =>
                  Text(data.first.playerName),
        ),
      ),
    ),
  );
}

MarketListingViewModel _listing() {
  return const MarketListingViewModel(
    id: 'listing-1',
    playerId: 'player-1',
    playerName: 'Ada Striker',
    position: 'ST',
    currentClubName: 'Lagos United',
    basePrice: 70,
    currentHighestBid: 84,
    status: 'open',
    watchlistCount: 4,
    bidCount: 1,
    marketSignal: 'Backend signal',
    channel: 'auction',
    timeRemaining: 3600,
    negotiationId: null,
    expiresAt: null,
    bids: <MarketBidViewModel>[],
    raw: <String, Object?>{},
  );
}

class _Case {
  const _Case(this.state, this.expectedText);

  final GtexSurfaceState<List<MarketListingViewModel>> state;
  final String expectedText;
}
