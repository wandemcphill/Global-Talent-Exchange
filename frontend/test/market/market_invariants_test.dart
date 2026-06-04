import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/market/market.dart';

void main() {
  test('market access roles match owner manager scout invariants', () {
    final MarketAccessPolicy owner = MarketAccessPolicy.resolve(
      role: 'club.owner',
      authenticated: true,
      hasClubContext: true,
    );
    final MarketAccessPolicy manager = MarketAccessPolicy.resolve(
      role: 'club.manager',
      authenticated: true,
      hasClubContext: true,
    );
    final MarketAccessPolicy scout = MarketAccessPolicy.resolve(
      role: 'club.scout',
      authenticated: true,
      hasClubContext: true,
    );

    expect(owner.canCheckout, isTrue);
    expect(manager.canBid, isTrue);
    expect(manager.canCheckout, isFalse);
    expect(manager.checkoutBlockReason, 'Owner approval required');
    expect(scout.canView, isTrue);
    expect(scout.canBid, isFalse);
    expect(scout.canCheckout, isFalse);
  });

  test('bid lifecycle canonicalizes pending counter terminal states', () {
    expect(
      marketBidLifecycleStatusFrom('pending'),
      MarketBidLifecycleStatus.pending,
    );
    expect(
      marketBidLifecycleStatusFrom('counter_offer'),
      MarketBidLifecycleStatus.counter,
    );
    expect(
      marketBidLifecycleStatusFrom('completed'),
      MarketBidLifecycleStatus.accepted,
    );
    expect(
      marketBidLifecycleStatusFrom('coach_blocked'),
      MarketBidLifecycleStatus.rejected,
    );
    expect(
      marketBidLifecycleStatusFrom('withdrawn'),
      MarketBidLifecycleStatus.withdrawn,
    );
  });

  test(
    'bid view model preserves wallet reservation truth from backend only',
    () {
      final MarketBidViewModel bid =
          MarketBidViewModel.fromJson(<String, Object?>{
            'bid_id': 'bid-1',
            'club_id': 'club-1',
            'club_name': 'Club One',
            'amount': 1400,
            'status': 'pending',
            'is_highest': true,
            'wallet_reservation_status': 'reserved',
            'wallet_reserved_amount': 1400,
            'wallet_reservation_reference': 'wallet-lock-1',
          });
      final MarketBidViewModel missingWallet = MarketBidViewModel.fromJson(
        <String, Object?>{
          'bid_id': 'bid-2',
          'club_id': 'club-2',
          'amount': 900,
        },
      );

      expect(bid.walletReservationStatus, 'reserved');
      expect(bid.walletReservedAmount, 1400);
      expect(bid.walletReservationReference, 'wallet-lock-1');
      expect(missingWallet.walletReservationStatus, isNull);
      expect(missingWallet.walletReservedAmount, isNull);
      expect(missingWallet.walletReservationReference, isNull);
    },
  );
}
