import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_exchange_models.dart';
import 'package:gte_frontend/features/player_market_redesign/models/gtex_market_browse_models.dart';
import 'package:gte_frontend/features/player_market_redesign/widgets/gtex_market_player_grid.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

/// The market browse grid renders the compact player card at every
/// breakpoint. Two things had to hold at once: the compact variant must keep
/// its buy and shortlist callbacks, and it must stop discarding the market
/// intelligence the grid hands it. Before this pass `movementLabel` had zero
/// render sites anywhere in the product, even though the card's own value
/// display has always accepted a delta.
void main() {
  GtexMarketPlayerView playerView({
    String playerId = 'player-1',
    String name = 'Emmanuel Adebayo-Oluwaseun',
    double? movementPct,
    double? gsi = 88,
    int? age = 24,
    int? interest,
  }) {
    return GtexMarketPlayerView.fromListItem(
      GteMarketPlayerListItem.fromJson(<String, Object?>{
        'player_id': playerId,
        'player_name': name,
        'position': 'ST',
        'nationality': 'Nigeria',
        'current_club_name': 'Real Sporting Clube de Portugal B',
        'current_competition_name': 'Primeira Liga',
        'age': age,
        'current_value_credits': 1240000,
        if (movementPct != null) 'movement_pct': movementPct,
        if (interest != null) 'market_interest_score': interest,
        if (gsi != null) 'global_scouting_index': gsi,
        'average_rating': 8.4,
        'availability_label': 'Transfer eligible',
        'asking_type': 'transfer_eligible',
        'is_tradable': true,
      }),
    );
  }

  Widget grid(
    double width,
    List<GtexMarketPlayerView> players, {
    bool withActions = true,
    Set<String> owned = const <String>{},
  }) {
    return MaterialApp(
      theme: ThemeData.dark(),
      home: Scaffold(
        body: SizedBox(
          width: width,
          child: GtexMarketPlayerGrid(
            players: players,
            totalPlayers: players.length,
            selectedPlayerId: null,
            basketState: const GtexMarketBasketState(
              <String, GtexMarketPlayerView>{},
            ),
            isLoading: false,
            error: null,
            hasMore: false,
            ownedPlayerIds: owned,
            onRefresh: () {},
            onLoadMore: null,
            onSelectPlayer: (_) {},
            onToggleBasket: withActions ? (_) {} : (_) {},
            onBuyNow: (_) {},
          ),
        ),
      ),
    );
  }

  Future<List<String>> pumpCapturingErrors(
    WidgetTester tester,
    Widget widget,
    double width,
  ) async {
    tester.view.physicalSize = Size(width, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    final List<String> errors = <String>[];
    final FlutterExceptionHandler? previous = FlutterError.onError;
    FlutterError.onError =
        (FlutterErrorDetails details) =>
            errors.add(details.exceptionAsString());
    await tester.pumpWidget(widget);
    await tester.pump();
    FlutterError.onError = previous;
    return errors;
  }

  for (final double width in <double>[360, 414, 700, 900, 1200, 1440]) {
    testWidgets('browse grid exposes card actions at ${width}px', (
      WidgetTester tester,
    ) async {
      final List<String> errors = await pumpCapturingErrors(
        tester,
        grid(width, <GtexMarketPlayerView>[playerView(movementPct: 2.4)]),
        width,
      );

      expect(
        find.text('Open'),
        findsWidgets,
        reason: 'buy action must be reachable at ${width}px',
      );
      expect(
        find.text('Shortlist'),
        findsWidgets,
        reason: 'shortlist action must be reachable at ${width}px',
      );
      expect(
        errors.where((String e) => e.contains('overflow')),
        isEmpty,
        reason: 'browse card must not overflow at ${width}px',
      );
    });

    testWidgets('browse card renders signed movement at ${width}px', (
      WidgetTester tester,
    ) async {
      await pumpCapturingErrors(
        tester,
        grid(width, <GtexMarketPlayerView>[playerView(movementPct: 2.4)]),
        width,
      );

      // The movement is a *valuation* movement, so it travels with the
      // valuation rather than standing bare beside the share price.
      expect(
        find.text('Value GTEX 1.2M +2.4%'),
        findsWidgets,
        reason:
            'value movement is real backend data and must be visible on the '
            'browse card at ${width}px',
      );
    });
  }

  testWidgets('falling movement keeps its sign', (WidgetTester tester) async {
    await pumpCapturingErrors(
      tester,
      grid(900, <GtexMarketPlayerView>[playerView(movementPct: -3.7)]),
      900,
    );

    expect(find.text('Value GTEX 1.2M -3.7%'), findsWidgets);
    expect(find.text('Value GTEX 1.2M 3.7%'), findsNothing);
  });

  testWidgets('a player with no movement shows no delta, not 0.0%', (
    WidgetTester tester,
  ) async {
    await pumpCapturingErrors(
      tester,
      grid(900, <GtexMarketPlayerView>[playerView()]),
      900,
    );

    expect(
      find.textContaining('%'),
      findsNothing,
      reason: 'an absent movement must not be rendered as a flat one',
    );
  });

  testWidgets('the model itself refuses to invent a flat movement', (
    WidgetTester tester,
  ) async {
    expect(playerView().valueMovementLabel, isNull);
    expect(playerView(movementPct: 0).valueMovementLabel, '0.0%');
    expect(playerView(movementPct: 1.25).valueMovementLabel, '+1.3%');
  });

  testWidgets('GSI and its tier reach the browse card on a wide pane', (
    WidgetTester tester,
  ) async {
    await pumpCapturingErrors(
      tester,
      grid(700, <GtexMarketPlayerView>[playerView(gsi: 91, interest: 42)]),
      700,
    );

    // 700px of pane is one 668px column, past every meta threshold.
    expect(find.textContaining('GSI 91'), findsWidgets);
    expect(find.textContaining('Elite GSI'), findsWidgets);
    expect(find.textContaining('Watched 42'), findsWidgets);
    expect(find.textContaining('24 yrs'), findsWidgets);
  });

  testWidgets('a narrow card drops meta rather than clipping it', (
    WidgetTester tester,
  ) async {
    final List<String> errors = await pumpCapturingErrors(
      tester,
      grid(330, <GtexMarketPlayerView>[playerView(gsi: 91, interest: 42)]),
      330,
    );

    expect(errors.where((String e) => e.contains('overflow')), isEmpty);
    expect(find.textContaining('Watched 42'), findsNothing);
    // The player is still identifiable and still priced.
    expect(find.text('Emmanuel Adebayo-Oluwaseun'), findsOneWidget);
  });

  testWidgets('a held player is marked as owned', (WidgetTester tester) async {
    await pumpCapturingErrors(
      tester,
      grid(
        900,
        <GtexMarketPlayerView>[playerView(movementPct: 1.1)],
        owned: <String>{'player-1'},
      ),
      900,
    );

    expect(find.text('OWNED'), findsOneWidget);
  });

  testWidgets('ownership is never claimed without portfolio data', (
    WidgetTester tester,
  ) async {
    await pumpCapturingErrors(
      tester,
      grid(900, <GtexMarketPlayerView>[playerView(movementPct: 1.1)]),
      900,
    );

    expect(find.text('OWNED'), findsNothing);
  });

  testWidgets('discovery lanes filter the loaded listings', (
    WidgetTester tester,
  ) async {
    await pumpCapturingErrors(
      tester,
      grid(900, <GtexMarketPlayerView>[
        playerView(playerId: 'rising', name: 'Rising Striker', movementPct: 4),
        playerView(
          playerId: 'falling',
          name: 'Falling Winger',
          movementPct: -2,
        ),
      ]),
      900,
    );

    expect(find.text('Rising Striker'), findsOneWidget);
    expect(find.text('Falling Winger'), findsOneWidget);

    await tester.tap(
      find.byKey(const Key('gtex-market-lane-rising')),
      warnIfMissed: false,
    );
    await tester.pump();

    expect(find.text('Rising Striker'), findsOneWidget);
    expect(find.text('Falling Winger'), findsNothing);
  });

  testWidgets('the rating pill carries a figure, not a truncated caption', (
    WidgetTester tester,
  ) async {
    // The pill stripped only a leading `GSI ` and drew the remainder in a
    // fixed 44px box, so the market's `Form 8.4` rendered as `Form...` and
    // the card's primary rating showed no number at any width.
    for (final double width in <double>[340, 560, 900]) {
      await pumpCapturingErrors(
        tester,
        grid(width, <GtexMarketPlayerView>[playerView(movementPct: 1.2)]),
        width,
      );

      expect(
        find.text('8.4'),
        findsWidgets,
        reason: 'the rating figure must be legible at ${width}px',
      );
      expect(
        find.text('FORM'),
        findsWidgets,
        reason: 'the pill must still say which rating the figure is',
      );
      expect(
        find.textContaining('Form 8.4'),
        findsNothing,
        reason: 'the caption and the figure are separate lines now',
      );
    }
  });

  testWidgets('the rating pill keeps the score out of the tier label', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 560,
            height: 120,
            child: GtexPlayerCard(
              name: 'Scored Player',
              position: 'CB',
              clubName: 'Club',
              nationality: 'NG',
              priceLabel: '10 GTC',
              gsiLabel: 'GSI 96 - Elite GSI',
            ),
          ),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('96'), findsOneWidget);
    expect(find.text('GSI'), findsOneWidget);
  });

  testWidgets('most watched is ranked by interest, not merely filtered', (
    WidgetTester tester,
  ) async {
    // A lane named "Most watched" asserts an ordering. It has to keep it
    // from the backend's own interest score rather than leave the market's
    // arbitrary order under a ranking label.
    // A single column, so "leads the lane" is a vertical fact.
    await pumpCapturingErrors(
      tester,
      grid(420, <GtexMarketPlayerView>[
        playerView(playerId: 'low', name: 'Lightly Watched', interest: 4),
        playerView(playerId: 'none', name: 'Unwatched Player'),
        playerView(playerId: 'high', name: 'Heavily Watched', interest: 91),
      ]),
      420,
    );

    await tester.tap(
      find.byKey(const Key('gtex-market-lane-watched')),
      warnIfMissed: false,
    );
    await tester.pump();

    expect(find.text('Unwatched Player'), findsNothing);
    expect(
      tester.getTopLeft(find.text('Heavily Watched')).dy,
      lessThan(tester.getTopLeft(find.text('Lightly Watched')).dy),
      reason: 'the most watched listing must lead the most-watched lane',
    );
  });

  testWidgets('the market still uses exactly one player card type', (
    WidgetTester tester,
  ) async {
    await pumpCapturingErrors(
      tester,
      grid(900, <GtexMarketPlayerView>[
        playerView(playerId: 'a', movementPct: 1),
        playerView(playerId: 'b', name: 'Second Player', movementPct: -1),
      ]),
      900,
    );

    expect(find.byType(GtexPlayerCard), findsNWidgets(2));
  });

  testWidgets('list usage stays a plain row without an action bar', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(400, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ListView(
            children: <Widget>[
              GtexPlayerCard(
                name: 'Short Name',
                position: 'CM',
                clubName: 'Club',
                nationality: 'NG',
                priceLabel: '10 GTC',
                onAddToShortlist: () {},
                onBuyNow: () {},
              ),
            ],
          ),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('Buy now'), findsNothing);
    expect(find.text('Shortlist'), findsNothing);
  });
}
