import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_exchange_models.dart';
import 'package:gte_frontend/features/player_market_redesign/player_market_redesign.dart';
import 'package:gte_frontend/ui_gtex/football/gtex_player_card.dart';

void main() {
  GtexMarketPlayerView view({
    required String id,
    double? movementPct,
    double? gsiMovementPct,
    int? interestScore,
  }) {
    return GtexMarketPlayerView.fromListItem(
      GteMarketPlayerListItem(
        playerId: id,
        playerName: 'Player $id',
        position: 'CM',
        nationality: 'Testland',
        currentClubName: 'Test FC',
        age: 24,
        currentValueCredits: 1000,
        movementPct: movementPct,
        trendScore: null,
        marketInterestScore: interestScore,
        averageRating: 7,
        globalScoutingIndex: 80,
        globalScoutingIndexMovementPct: gsiMovementPct,
      ),
    );
  }

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

  testWidgets('opportunity lane counts only value+GSI risers', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      host(<GtexMarketPlayerView>[
        view(id: 'opp', movementPct: 3, gsiMovementPct: 2),
        view(id: 'value-only', movementPct: 4, gsiMovementPct: null),
        view(id: 'flat', movementPct: null, gsiMovementPct: null),
      ]),
    );
    await tester.pumpAndSettle();

    expect(find.text('Opportunities 1'), findsOneWidget);
  });

  testWidgets('sort menu is present and switchable', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      host(<GtexMarketPlayerView>[
        view(id: 'a', movementPct: 1),
        view(id: 'b', movementPct: 9),
      ]),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('gtex-market-sort')), findsOneWidget);
    await tester.tap(find.byKey(const Key('gtex-market-sort')));
    await tester.pumpAndSettle();
    expect(
      find.byKey(const Key('gtex-market-sort-biggestRisers')),
      findsOneWidget,
    );
    await tester.tap(find.byKey(const Key('gtex-market-sort-biggestRisers')));
    await tester.pumpAndSettle();
    expect(find.textContaining('Biggest risers'), findsWidgets);
  });

  testWidgets('every market row renders through the canonical GtexPlayerCard', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      host(<GtexMarketPlayerView>[
        view(id: 'a', movementPct: 1),
        view(id: 'b', movementPct: -2),
      ]),
    );
    await tester.pumpAndSettle();

    expect(find.byType(GtexPlayerCard), findsNWidgets(2));
  });

  test('no second player-card widget lives in the market feature', () {
    final Directory dir = Directory('lib/features/player_market_redesign');
    final RegExp cardClass = RegExp(
      r'class\s+\w*(PlayerCard|MarketCard)\w*\s+extends\s+(StatelessWidget|StatefulWidget)',
    );
    for (final FileSystemEntity entity in dir.listSync(recursive: true)) {
      if (entity is! File || !entity.path.endsWith('.dart')) {
        continue;
      }
      expect(
        cardClass.hasMatch(entity.readAsStringSync()),
        isFalse,
        reason: '${entity.path} defines its own player card - use GtexPlayerCard',
      );
    }
  });
}
