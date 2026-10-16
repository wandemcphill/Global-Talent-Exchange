import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/national_team_rental_redesign/models/gtex_national_team_rental_models.dart';

void main() {
  group('GtexRentalBasketState', () {
    test('adds, removes, and totals rental players', () {
      const GtexRentalPlayerView player = GtexRentalPlayerView(
        playerId: 'p1',
        name: 'Live Test Player',
        position: 'ST',
        age: 19,
        rating: 77.2,
        nationality: 'Nigeria',
        countryCode: 'NG',
        clubName: 'Backend Seed',
        rentalCostCredits: 150000,
        sourceBucket: 'national_seed',
      );

      const GtexRentalBasketState empty = GtexRentalBasketState(
        <String, GtexRentalPlayerView>{},
      );
      final GtexRentalBasketState added = empty.toggled(player);
      expect(added.contains('p1'), isTrue);
      expect(added.squadCount, 1);
      expect(added.totalCredits, 150000);
      expect(added.totalLabel, 'GTEX 150.0K');

      final GtexRentalBasketState removed = added.toggled(player);
      expect(removed.contains('p1'), isFalse);
      expect(removed.squadCount, 0);
    });

    test('does not add backend-locked players to the rental basket', () {
      const GtexRentalPlayerView locked = GtexRentalPlayerView(
        playerId: 'locked-p1',
        name: 'Locked Test Player',
        position: 'CB',
        age: 21,
        rating: 70,
        nationality: 'Nigeria',
        countryCode: 'NG',
        clubName: 'Backend Pool',
        rentalCostCredits: 100000,
        sourceBucket: 'real_player',
        rentalEligible: false,
        eligibilityReasons: <String>['cooldown_active'],
      );

      const GtexRentalBasketState empty = GtexRentalBasketState(
        <String, GtexRentalPlayerView>{},
      );
      final GtexRentalBasketState next = empty.toggled(locked);

      expect(next.contains('locked-p1'), isFalse);
      expect(locked.availabilityLabel, 'LOCKED - COOLDOWN_ACTIVE');
    });
  });
}
