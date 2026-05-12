import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/national_team_rental_redesign/models/gtex_national_team_rental_models.dart';

void main() {
  group('GtexRentalBasketState', () {
    test('adds, removes, and totals rental players', () {
      const GtexRentalPlayerView player = GtexRentalPlayerView(
        playerId: 'p1',
        name: 'Demo Player',
        position: 'ST',
        age: 19,
        rating: 77.2,
        nationality: 'Nigeria',
        countryCode: 'NG',
        clubName: 'GTEX Seed',
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
      expect(added.totalLabel, 'GTC 150.0K');

      final GtexRentalBasketState removed = added.toggled(player);
      expect(removed.contains('p1'), isFalse);
      expect(removed.squadCount, 0);
    });
  });

  group('GtexNationalTeamRentalDemoData', () {
    test('contains competitions, countries, teams, and players', () {
      expect(GtexNationalTeamRentalDemoData.competitions, isNotEmpty);
      expect(GtexNationalTeamRentalDemoData.countries, isNotEmpty);
      expect(GtexNationalTeamRentalDemoData.teams, isNotEmpty);
      expect(GtexNationalTeamRentalDemoData.players, isNotEmpty);
    });
  });
}
