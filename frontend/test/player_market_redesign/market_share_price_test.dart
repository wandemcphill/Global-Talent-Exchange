import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_exchange_models.dart';
import 'package:gte_frontend/features/player_market_redesign/player_market_redesign.dart';

/// The Market's economic vocabulary.
///
/// PRICE is `PlayerShareMarket.share_price_coin` - the coin amount a trade
/// settles at. VALUE is the valuation overlay (`market_value_eur`, or the
/// value engine's credits). They are different numbers from different
/// domains, and the Market has to say which is which. This file pins that
/// separation at the layer where it was lost: the browse view-model.
void main() {
  GteMarketPlayerListItem raw({
    double? sharePriceCoin,
    double? marketValueEur = 120000000,
    double? currentValueCredits = 50000000,
    double? movementPct,
  }) {
    return GteMarketPlayerListItem(
      playerId: 'saka',
      playerName: 'Bukayo Saka',
      position: 'RW',
      nationality: 'England',
      currentClubName: 'Arsenal',
      age: 23,
      marketValueEur: marketValueEur,
      currentValueCredits: currentValueCredits,
      sharePriceCoin: sharePriceCoin,
      movementPct: movementPct,
      trendScore: null,
      marketInterestScore: null,
      averageRating: 7.4,
    );
  }

  group('market list transport', () {
    test('parses the tradable share price the backend already sends', () {
      final GteMarketPlayerListItem item =
          GteMarketPlayerListItem.fromJson(<String, Object?>{
            'player_id': 'saka',
            'player_name': 'Bukayo Saka',
            'position': 'RW',
            'nationality': 'England',
            'current_club_name': 'Arsenal',
            'market_value_eur': 120000000,
            'current_value_credits': 50000000,
            'share_price_coin': '12.40',
            'movement_pct': 3.2,
            'trend_score': null,
            'market_interest_score': null,
            'average_rating': 7.4,
            'is_tradable': true,
          });

      expect(item.sharePriceCoin, 12.40);
    });

    test('a player with no issued share market is unpriced, not free', () {
      final GteMarketPlayerListItem item =
          GteMarketPlayerListItem.fromJson(<String, Object?>{
            'player_id': 'unissued',
            'player_name': 'Unissued Player',
            'position': 'CM',
            'nationality': 'England',
            'current_club_name': 'Arsenal',
            'market_value_eur': 4000000,
            'current_value_credits': 900,
            'movement_pct': null,
            'trend_score': null,
            'market_interest_score': null,
            'average_rating': null,
            'is_tradable': true,
          });

      expect(item.sharePriceCoin, isNull);
    });
  });

  group('GtexMarketPlayerView', () {
    test('the price it quotes is the share price, never the valuation', () {
      final GtexMarketPlayerView player = GtexMarketPlayerView.fromListItem(
        raw(sharePriceCoin: 12.40),
      );

      expect(player.sharePriceCoin, 12.40);
      expect(player.sharePriceLabel, 'GTEX 12.40');
      // The valuation must not leak into the price under any label.
      expect(player.sharePriceLabel, isNot(contains('120')));
      expect(player.sharePriceLabel, isNot(contains('EUR')));
    });

    test('an unissued market says so rather than quoting a valuation', () {
      final GtexMarketPlayerView player = GtexMarketPlayerView.fromListItem(
        raw(sharePriceCoin: null),
      );

      expect(player.sharePriceCoin, isNull);
      expect(player.sharePriceLabel, 'No share market');
      // Not zero, not the valuation, not a blank.
      expect(player.sharePriceLabel, isNot(contains('0')));
      expect(player.estimatedValueLabel, 'EUR 120.0M');
    });

    test('valuation is carried separately and named as a valuation', () {
      final GtexMarketPlayerView player = GtexMarketPlayerView.fromListItem(
        raw(sharePriceCoin: 12.40, movementPct: 3.2),
      );

      expect(player.estimatedValueLabel, 'EUR 120.0M');
      // The movement the backend sends is a *valuation* movement. Whatever
      // the Market prints beside it has to say so.
      expect(player.valueMovementLabel, '+3.2%');
      expect(player.valueBadgeLabel, 'Value EUR 120.0M +3.2%');
    });

    test('valuation falls back to credits, still labelled as value', () {
      final GtexMarketPlayerView player = GtexMarketPlayerView.fromListItem(
        raw(sharePriceCoin: 12.40, marketValueEur: null),
      );

      expect(player.estimatedValueLabel, 'GTEX 50.0M');
      expect(player.valueBadgeLabel, 'Value GTEX 50.0M');
    });

    test('missing valuation is unknown, not zero', () {
      final GtexMarketPlayerView player = GtexMarketPlayerView.fromListItem(
        raw(
          sharePriceCoin: 12.40,
          marketValueEur: null,
          currentValueCredits: null,
        ),
      );

      expect(player.estimatedValueLabel, isNull);
      expect(player.valueBadgeLabel, isNull);
    });
  });

  group('sorting says which number it ordered by', () {
    test('value sorts are named for the valuation they read', () {
      expect(
        GtexMarketSort.valueHighToLow.label,
        'Estimated value: high to low',
      );
      expect(
        GtexMarketSort.valueLowToHigh.label,
        'Estimated value: low to high',
      );
      expect(
        GtexMarketSort.sharePriceHighToLow.label,
        'Share price: high to low',
      );
    });

    test('share-price sort orders by the tradable price', () {
      final List<GtexMarketPlayerView> players = <GtexMarketPlayerView>[
        GtexMarketPlayerView.fromListItem(
          raw(sharePriceCoin: 5, currentValueCredits: 900),
        ),
        GtexMarketPlayerView.fromListItem(
          raw(sharePriceCoin: 50, currentValueCredits: 10),
        ),
        // Unpriced players sort last rather than as zero.
        GtexMarketPlayerView.fromListItem(
          raw(sharePriceCoin: null, currentValueCredits: 5000),
        ),
      ];

      final List<GtexMarketPlayerView> sorted =
          GtexMarketSort.sharePriceHighToLow.applyTo(players);

      expect(sorted[0].sharePriceCoin, 50);
      expect(sorted[1].sharePriceCoin, 5);
      expect(sorted[2].sharePriceCoin, isNull);
    });
  });

  group('market grid', () {
    Widget host(List<GtexMarketPlayerView> players) {
      return MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 1200,
            height: 900,
            child: GtexMarketPlayerGrid(
              players: players,
              totalPlayers: players.length,
              selectedPlayerId: null,
              basketState: const GtexMarketBasketState(
                <String, GtexMarketPlayerView>{},
              ),
              isLoading: false,
              error: null,
              onRefresh: () {},
              onLoadMore: null,
              hasMore: false,
              onSelectPlayer: (_) {},
              onToggleBasket: (_) {},
              onBuyNow: (_) {},
            ),
          ),
        ),
      );
    }

    testWidgets(
      'quotes the share price and names the valuation apart from it',
      (WidgetTester tester) async {
        await tester.pumpWidget(
          host(<GtexMarketPlayerView>[
            GtexMarketPlayerView.fromListItem(
              raw(sharePriceCoin: 12.40, movementPct: 3.2),
            ),
          ]),
        );
        await tester.pumpAndSettle();

        expect(find.text('GTEX 12.40'), findsOneWidget);
        expect(find.text('Value EUR 120.0M +3.2%'), findsOneWidget);
        // The bare valuation must never stand where a price belongs.
        expect(find.text('EUR 120.0M'), findsNothing);
      },
    );
  });
}
