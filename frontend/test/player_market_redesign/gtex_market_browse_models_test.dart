import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_exchange_models.dart';
import 'package:gte_frontend/features/player_market_redesign/player_market_redesign.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

void main() {
  group('GtexMarketBrowseSummary', () {
    test('groups loaded market players by nationality and club', () {
      final List<GtexMarketPlayerView> players = <GtexMarketPlayerView>[
        GtexMarketPlayerView.fromListItem(
          _player(id: '1', name: 'A', nationality: 'England', club: 'Arsenal'),
        ),
        GtexMarketPlayerView.fromListItem(
          _player(id: '2', name: 'B', nationality: 'England', club: 'Arsenal'),
        ),
        GtexMarketPlayerView.fromListItem(
          _player(id: '3', name: 'C', nationality: 'Nigeria', club: 'Chelsea'),
        ),
      ];

      final GtexMarketBrowseSummary summary =
          GtexMarketBrowseSummary.fromPlayers(players);

      expect(summary.countries.first.label, 'England');
      expect(summary.countries.first.count, 2);
      expect(summary.clubs.first.label, 'Arsenal');
      expect(summary.clubs.first.count, 2);
    });

    test('uses catalog counts when live market catalog is available', () {
      final GtexMarketBrowseSummary summary =
          GtexMarketBrowseSummary.fromCatalog(
            const GteMarketBrowseCatalog(
              total: 17000,
              countries: <GteMarketBrowseOption>[
                GteMarketBrowseOption(id: 'ENG', label: 'England', count: 5200),
              ],
              leagues: <GteMarketBrowseOption>[
                GteMarketBrowseOption(
                  id: 'premier-league',
                  label: 'Premier League',
                  count: 620,
                  parentId: 'ENG',
                  countryId: 'ENG',
                  leagueId: 'premier-league',
                ),
              ],
              divisions: <GteMarketBrowseOption>[
                GteMarketBrowseOption(
                  id: 'division-1',
                  label: 'Division 1',
                  count: 620,
                  parentId: 'premier-league',
                  countryId: 'ENG',
                  leagueId: 'premier-league',
                  divisionId: 'division-1',
                ),
              ],
              clubs: <GteMarketBrowseOption>[
                GteMarketBrowseOption(
                  id: 'arsenal',
                  label: 'Arsenal',
                  count: 34,
                  parentId: 'division-1',
                  countryId: 'ENG',
                  leagueId: 'premier-league',
                  divisionId: 'division-1',
                ),
              ],
            ),
          );

      expect(summary.countries.single.count, 5200);
      expect(summary.leagues.single.label, 'Premier League');
      expect(summary.leagues.single.countryId, 'ENG');
      expect(summary.divisions.single.id, 'division-1');
      expect(summary.divisions.single.leagueId, 'premier-league');
      expect(summary.clubs.single.label, 'Arsenal');
      expect(summary.clubs.single.divisionId, 'division-1');
    });

    test('maps image and hierarchy fields from live market list item', () {
      final GtexMarketPlayerView player = GtexMarketPlayerView.fromListItem(
        _player(
          id: 'saka',
          name: 'Bukayo Saka',
          nationality: 'England',
          club: 'Arsenal',
          imageUrl: 'https://cdn.gtex.test/saka.png',
          leagueName: 'Premier League',
          leagueCountryName: 'England',
          divisionName: 'Division 1',
          countryCode: 'ENG',
          clubId: 'arsenal',
          marketValueEur: 120000000,
          transferListingId: 'listing-saka',
          transferListingStatus: 'open',
          sellingClubId: 'club-arsenal',
          availabilityLabel: 'Loan To Buy',
          askingType: 'loan_to_buy',
          globalScoutingIndex: 88,
          globalScoutingIndexMovementPct: 3.4,
        ),
      );

      expect(player.imageUrl, 'https://cdn.gtex.test/saka.png');
      expect(player.leagueName, 'Premier League');
      expect(player.leagueDetailLabel, 'Premier League (England)');
      expect(player.divisionName, 'Division 1');
      expect(player.countryCode, 'ENG');
      expect(player.clubId, 'arsenal');
      expect(player.transferListingId, 'listing-saka');
      expect(player.transferListingStatus, 'open');
      expect(player.sellingClubId, 'club-arsenal');
      expect(player.hasOpenTransferListing, isTrue);
      expect(player.availabilityTypeLabel, 'Loan To Buy');
      expect(player.gsiLabel, 'GSI 88');
      expect(player.gsiTierLabel, 'High-grade GSI');
      expect(player.gsiTrendLabel, 'GSI +3.4%');
      expect(player.gsiDetailLabel, 'GSI 88 - High-grade GSI');
      expect(player.priceLabel, 'EUR 120.0M');
      expect(player.internalPriceLabel, 'GTEX 50.0M');
    });

    test('does not coerce missing real-player age to zero', () {
      final GteMarketPlayerListItem raw =
          GteMarketPlayerListItem.fromJson(<String, Object?>{
            'player_id': 'sparse-real',
            'player_name': 'Sparse Real Player',
            'position': 'FW',
            'nationality': 'England',
            'current_club_name': 'Summary FC',
            'current_value_credits': 125,
            'movement_pct': 0,
            'trend_score': null,
            'market_interest_score': null,
            'average_rating': null,
            'is_tradable': true,
          });
      final GtexMarketPlayerView player = GtexMarketPlayerView.fromListItem(
        raw,
      );

      expect(raw.age, isNull);
      expect(player.age, isNull);
      expect(player.ageLabel, 'Age TBC');
      expect(player.clubName, 'Summary FC');
      expect(player.priceLabel, 'GTEX 125');
    });
  });

  group('GtexMarketBasketState', () {
    test('toggles players and calculates total basket cost', () {
      final GtexMarketPlayerView saka = GtexMarketPlayerView.fromListItem(
        _player(
          id: 'saka',
          name: 'Bukayo Saka',
          nationality: 'England',
          club: 'Arsenal',
          price: 100000000,
        ),
      );
      final GtexMarketPlayerView oshimen = GtexMarketPlayerView.fromListItem(
        _player(
          id: 'osimhen',
          name: 'Victor Osimhen',
          nationality: 'Nigeria',
          club: 'Galatasaray',
          price: 75000000,
        ),
      );

      final GtexMarketBasketState basket = const GtexMarketBasketState(
        <String, GtexMarketPlayerView>{},
      ).toggled(saka).toggled(oshimen);

      expect(basket.items.length, 2);
      expect(basket.totalCredits, 175000000);
      expect(basket.totalLabel, 'GTEX 175.0M');
      expect(basket.contains('saka'), isTrue);
      expect(basket.removed('saka').contains('saka'), isFalse);
    });
  });

  group('GtexMarketPlayerView opportunity classification', () {
    test('is an opportunity only when value and GSI both rise', () {
      final GtexMarketPlayerView both = GtexMarketPlayerView.fromListItem(
        _rawPlayer(movementPct: 2.5, gsiMovementPct: 3.1),
      );
      expect(both.isOpportunity, isTrue);

      final GtexMarketPlayerView valueOnly = GtexMarketPlayerView.fromListItem(
        _rawPlayer(movementPct: 3.0, gsiMovementPct: null),
      );
      expect(valueOnly.isOpportunity, isFalse);

      final GtexMarketPlayerView gsiOnly = GtexMarketPlayerView.fromListItem(
        _rawPlayer(movementPct: -1.0, gsiMovementPct: 4.0),
      );
      expect(gsiOnly.isOpportunity, isFalse);

      final GtexMarketPlayerView nullMovement =
          GtexMarketPlayerView.fromListItem(
        _rawPlayer(movementPct: null, gsiMovementPct: 4.0),
      );
      expect(nullMovement.hasMovement, isFalse);
      expect(nullMovement.isOpportunity, isFalse);
    });
  });

  group('GtexMarketSort', () {
    List<String> ids(List<GtexMarketPlayerView> players) =>
        players.map((GtexMarketPlayerView p) => p.playerId).toList();

    final List<GtexMarketPlayerView> sample = <GtexMarketPlayerView>[
      GtexMarketPlayerView.fromListItem(
        _rawPlayer(id: 'cheap', price: 10, movementPct: 1, rating: 6.0),
      ),
      GtexMarketPlayerView.fromListItem(
        _rawPlayer(id: 'rich', price: 900, movementPct: -5, rating: 8.5),
      ),
      GtexMarketPlayerView.fromListItem(
        _rawPlayer(id: 'mid', price: 100, movementPct: 9, rating: null),
      ),
    ];

    test('relevance keeps input order', () {
      expect(ids(GtexMarketSort.relevance.applyTo(sample)),
          <String>['cheap', 'rich', 'mid']);
    });

    test('price sorts ascend and descend', () {
      expect(ids(GtexMarketSort.priceLowToHigh.applyTo(sample)),
          <String>['cheap', 'mid', 'rich']);
      expect(ids(GtexMarketSort.priceHighToLow.applyTo(sample)),
          <String>['rich', 'mid', 'cheap']);
    });

    test('risers and fallers order by movement', () {
      expect(ids(GtexMarketSort.biggestRisers.applyTo(sample)).first, 'mid');
      expect(ids(GtexMarketSort.biggestFallers.applyTo(sample)).first, 'rich');
    });

    test('top rated pushes missing ratings last', () {
      expect(ids(GtexMarketSort.topRated.applyTo(sample)),
          <String>['rich', 'cheap', 'mid']);
    });

    test('does not mutate the source list', () {
      final List<GtexMarketPlayerView> copy = List<GtexMarketPlayerView>.of(
        sample,
      );
      GtexMarketSort.priceHighToLow.applyTo(sample);
      expect(ids(sample), ids(copy));
    });
  });

  group('GtexPlayerCard', () {
    testWidgets('renders real image_url instead of fallback initials', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: GtexPlayerCard(
              name: 'Bukayo Saka',
              position: 'RW',
              clubName: 'Arsenal',
              nationality: 'England',
              priceLabel: 'EUR 100.0M',
              gsiLabel: 'GSI 88',
              imageUrl: 'https://cdn.gtex.test/saka.png',
            ),
          ),
        ),
      );

      expect(find.byType(Image), findsOneWidget);
      expect(find.text('BS'), findsNothing);
      expect(find.text('88'), findsOneWidget);
      expect(find.text('GSI'), findsOneWidget);
    });
  });
}

GteMarketPlayerListItem _rawPlayer({
  String id = 'raw',
  double? price = 50000000,
  double? movementPct,
  double? gsiMovementPct,
  double? rating,
  int? interestScore,
}) {
  return GteMarketPlayerListItem(
    playerId: id,
    playerName: 'Raw $id',
    position: 'CM',
    nationality: 'Testland',
    currentClubName: 'Test FC',
    age: 25,
    currentValueCredits: price,
    movementPct: movementPct,
    trendScore: null,
    marketInterestScore: interestScore,
    averageRating: rating,
    globalScoutingIndex: 80,
    globalScoutingIndexMovementPct: gsiMovementPct,
  );
}

GteMarketPlayerListItem _player({
  required String id,
  required String name,
  required String nationality,
  required String club,
  double price = 50000000,
  String? imageUrl,
  String? leagueName,
  String? leagueCountryName,
  String? divisionName,
  String? countryCode,
  String? clubId,
  double? marketValueEur,
  String? transferListingId,
  String? transferListingStatus,
  String? sellingClubId,
  String availabilityLabel = 'Transfer eligible',
  String askingType = 'transfer_eligible',
  double? globalScoutingIndex = 85,
  double? globalScoutingIndexMovementPct,
}) {
  return GteMarketPlayerListItem(
    playerId: id,
    playerName: name,
    position: 'RW',
    nationality: nationality,
    nationalityCode: countryCode,
    currentClubId: clubId,
    currentClubName: club,
    currentCompetitionName: leagueName,
    currentCompetitionCountryName: leagueCountryName,
    currentDivisionName: divisionName,
    age: 24,
    marketValueEur: marketValueEur,
    currentValueCredits: price,
    movementPct: 2.5,
    trendScore: 85,
    marketInterestScore: 92,
    averageRating: 7.8,
    globalScoutingIndex: globalScoutingIndex,
    globalScoutingIndexMovementPct: globalScoutingIndexMovementPct,
    transferListingId: transferListingId,
    transferListingStatus: transferListingStatus,
    sellingClubId: sellingClubId,
    availabilityLabel: availabilityLabel,
    askingType: askingType,
    imageUrl: imageUrl,
  );
}
