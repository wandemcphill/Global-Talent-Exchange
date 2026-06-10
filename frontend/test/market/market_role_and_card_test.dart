import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/market/presentation/screens/market_hub_screen.dart';
import 'package:gte_frontend/features/market/presentation/widgets/market_models.dart';
import 'package:gte_frontend/features/market/presentation/widgets/market_widgets.dart';
import 'package:gte_frontend/features/transfer_center/live_transfer_center_provider.dart';
import 'package:gte_frontend/features/transfer_center/transfer_center_models.dart';
import 'package:gte_frontend/shared/models/auth_session.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets(
    'hub renders backend listings while scout actions stay read-only',
    (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authProvider.overrideWith(
              (Ref ref) => _session(role: 'club.scout'),
            ),
            transferCenterListingsProvider.overrideWith(
              (Ref ref) async => <TransferCenterListingRecord>[_record()],
            ),
          ],
          child: MaterialApp(
            theme: GteShellTheme.build(),
            home: const MarketHubScreen(),
          ),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.text('Ada Striker'), findsOneWidget);
      expect(find.text('Scout read-only access'), findsWidgets);
      expect(find.widgetWithText(FilledButton, 'Bid'), findsNothing);
    },
  );

  testWidgets('manager checkout is blocked by owner approval', (
    WidgetTester tester,
  ) async {
    final MarketAccessPolicy policy = MarketAccessPolicy.resolve(
      role: 'club.manager',
      authenticated: true,
      hasClubContext: true,
    );
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: Scaffold(
          body: CheckoutReadinessPanel(
            policy: policy,
            listings: <MarketListingViewModel>[_listing()],
          ),
        ),
      ),
    );

    expect(find.text('Owner approval required'), findsOneWidget);
    expect(find.text('Checkout ready for owner review'), findsNothing);
  });
}

AuthSession _session({required String role}) {
  return AuthSession(
    userId: 'user-1',
    accessToken: 'token-1',
    refreshToken: 'refresh-1',
    sessionId: 'session-1',
    role: role,
    clubId: 'club-1',
    clubName: 'Lagos United',
  );
}

TransferCenterListingRecord _record() {
  return const TransferCenterListingRecord(
    id: 'listing-1',
    playerId: 'player-1',
    playerName: 'Ada Striker',
    sellingClubId: 'club-seller',
    currentClubName: 'Lagos United',
    basePrice: 70,
    currentHighestBid: 84,
    highestBidderId: 'club-buyer',
    status: 'open',
    watchlistCount: 4,
    bidCount: 1,
    marketSignal: 'Backend signal',
    channel: 'auction',
    timeRemaining: 3600,
    negotiationId: null,
    bidders: <Map<String, Object?>>[
      <String, Object?>{
        'bid_id': 'bid-1',
        'club_id': 'club-buyer',
        'club_name': 'Accra City',
        'amount': 84,
        'is_highest': true,
        'wallet_reservation_status': 'reserved',
      },
    ],
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
