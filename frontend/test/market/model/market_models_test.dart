import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/market/domain/market_models.dart';

void main() {
  group('Market DTOs', () {
    test('parse transfer listing player without inventing missing fields', () {
      final MarketPlayerDTO player = MarketPlayerDTO.fromJson(
        const <String, Object?>{
          'id': 'listing-1',
          'player_id': 'player-1',
          'selling_club_id': 'seller-club',
          'base_price': '1700000.0000',
          'status': 'open',
          'player': <String, Object?>{
            'id': 'player-1',
            'full_name': 'Reserved Funds Forward',
            'normalized_position': 'forward',
            'current_club_name': 'Seller FC',
          },
        },
      );

      expect(player.id, 'player-1');
      expect(player.name, 'Reserved Funds Forward');
      expect(player.position, 'forward');
      expect(player.askingPrice, 1700000);
      expect(player.listingId, 'listing-1');
      expect(player.age, isNull);
      expect(player.contractEnd, isNull);
    });

    test('normalizes backend bid statuses into the market lifecycle', () {
      expect(
        MarketBidStatus.pending.canTransitionTo(MarketBidStatus.counter),
        isTrue,
      );
      expect(
        MarketBidStatus.counter.canTransitionTo(MarketBidStatus.accepted),
        isTrue,
      );
      expect(
        MarketBidStatus.accepted.canTransitionTo(MarketBidStatus.withdrawn),
        isFalse,
      );

      final Map<String, MarketBidStatus> statuses = <String, MarketBidStatus>{
        'pending': MarketBidStatus.pending,
        'submitted': MarketBidStatus.pending,
        'counter': MarketBidStatus.counter,
        'counter_offer': MarketBidStatus.counter,
        'accepted': MarketBidStatus.accepted,
        'completed': MarketBidStatus.accepted,
        'rejected': MarketBidStatus.rejected,
        'withdrawn': MarketBidStatus.withdrawn,
      };

      for (final MapEntry<String, MarketBidStatus> entry in statuses.entries) {
        expect(MarketBidStatus.fromBackend(entry.key), entry.value);
      }
    });

    test('active bid keeps wallet reservation truth nullable', () {
      final MarketBidDTO missingReservation =
          MarketBidDTO.fromJson(const <String, Object?>{
            'id': 'bid-1',
            'window_id': 'window-1',
            'player_id': 'player-1',
            'buying_club_id': 'buyer-club',
            'selling_club_id': 'seller-club',
            'bid_amount': '300.0000',
            'status': 'pending',
          });

      expect(missingReservation.walletReservation, isNull);
      expect(missingReservation.hasBackendReservationTruth, isFalse);

      final MarketBidDTO reserved =
          MarketBidDTO.fromJson(const <String, Object?>{
            'id': 'bid-2',
            'window_id': 'window-1',
            'player_id': 'player-1',
            'buying_club_id': 'buyer-club',
            'selling_club_id': 'seller-club',
            'bid_amount': '300.0000',
            'status': 'submitted',
            'wallet_reservation_status': 'reserved',
            'wallet_reserved_amount': '300.0000',
            'wallet_reservation_reference': 'transfer-bid:bid-2:reserve',
          });

      expect(reserved.status, MarketBidStatus.pending);
      expect(reserved.walletReservation?.status, 'reserved');
      expect(reserved.walletReservation?.reservedAmount, 300);
      expect(reserved.hasBackendReservationTruth, isTrue);
      expect(reserved.toJson()['status'], 'pending');
    });
  });
}
