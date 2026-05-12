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
          divisionName: 'Division 1',
          countryCode: 'ENG',
          clubId: 'arsenal',
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
      expect(player.priceLabel, isNot('GTX —'));
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
      expect(basket.contains('saka'), isTrue);
      expect(basket.removed('saka').contains('saka'), isFalse);
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
              priceLabel: 'GTX 100M',
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

GteMarketPlayerListItem _player({
  required String id,
  required String name,
  required String nationality,
  required String club,
  double price = 50000000,
  String? imageUrl,
  String? leagueName,
  String? divisionName,
  String? countryCode,
  String? clubId,
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
    currentDivisionName: divisionName,
    age: 24,
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
