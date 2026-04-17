import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_exchange_models.dart';

void main() {
  test(
    'player filter normalization keeps club, league, and national team filters',
    () {
      const PlayerFilter raw = PlayerFilter(
        search: ' Saka ',
        club: ' Arsenal ',
        nationalTeam: ' Nigeria U20 ',
        league: ' Premier League ',
      );

      final PlayerFilter normalized = raw.normalized();

      expect(normalized.search, 'Saka');
      expect(normalized.club, 'Arsenal');
      expect(normalized.nationalTeam, 'Nigeria U20');
      expect(normalized.league, 'Premier League');
      expect(normalized.hasActiveFilters, isTrue);
    },
  );

  test(
    'market player query serializes club, league, and national team parameters',
    () {
      const GteMarketPlayersQuery query = GteMarketPlayersQuery(
        search: 'saka',
        club: 'Arsenal',
        nationalTeam: 'Nigeria U20',
        league: 'Premier League',
      );

      expect(query.toQueryParameters(), <String, Object?>{
        'limit': 20,
        'offset': 0,
        'search': 'saka',
        'club': 'Arsenal',
        'national_team': 'Nigeria U20',
        'league': 'Premier League',
      });
    },
  );
}
