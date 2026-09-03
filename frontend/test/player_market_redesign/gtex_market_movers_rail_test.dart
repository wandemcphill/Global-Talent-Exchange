import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_exchange_models.dart';
import 'package:gte_frontend/features/player_market_redesign/player_market_redesign.dart';

void main() {
  group('GteMarketMovers.fromJson', () {
    test('parses the pricing-engine movers payload', () {
      final GteMarketMovers movers = GteMarketMovers.fromJson(<String, Object?>{
        'top_gainers': <Object?>[
          <String, Object?>{
            'player_id': 'p1',
            'player_name': 'Riser One',
            'day_change_percent': 4.35,
            'volume_24h': 3.0,
          },
        ],
        'top_losers': <Object?>[
          <String, Object?>{
            'player_id': 'p2',
            'player_name': 'Faller Two',
            'day_change_percent': -2.1,
          },
        ],
        'most_traded': <Object?>[],
        'trending': <Object?>[],
      });

      expect(movers.isEmpty, isFalse);
      expect(movers.topGainers.single.playerId, 'p1');
      expect(movers.topGainers.single.isUp, isTrue);
      expect(movers.topLosers.single.isDown, isTrue);
    });

    test('an all-empty payload is empty', () {
      expect(
        GteMarketMovers.fromJson(<String, Object?>{
          'top_gainers': <Object?>[],
          'top_losers': <Object?>[],
        }).isEmpty,
        isTrue,
      );
      expect(GteMarketMovers.empty.isEmpty, isTrue);
    });
  });

  group('GtexMarketMoversRail', () {
    Widget host(Widget child) => MaterialApp(home: Scaffold(body: child));

    testWidgets('states the absence instead of showing a zero', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(
        host(
          GtexMarketMoversRail(
            movers: GteMarketMovers.empty,
            isLoading: false,
            error: null,
            onOpenPlayer: (_) {},
          ),
        ),
      );

      expect(find.textContaining('once prices move'), findsOneWidget);
      expect(find.textContaining('%'), findsNothing);
      expect(find.textContaining('0.0'), findsNothing);
    });

    testWidgets('renders real movers and opens the player on tap', (
      WidgetTester tester,
    ) async {
      String? opened;
      await tester.pumpWidget(
        host(
          GtexMarketMoversRail(
            isLoading: false,
            error: null,
            onOpenPlayer: (String id) => opened = id,
            movers: const GteMarketMovers(
              topGainers: <GteMarketMoverItem>[
                GteMarketMoverItem(
                  playerId: 'riser-1',
                  playerName: 'Ada Riser',
                  dayChange: 5,
                  dayChangePercent: 4.3,
                  volume24h: 3,
                ),
              ],
              topLosers: <GteMarketMoverItem>[
                GteMarketMoverItem(
                  playerId: 'faller-1',
                  playerName: 'Ben Faller',
                  dayChange: -3,
                  dayChangePercent: -2.6,
                  volume24h: 1,
                ),
              ],
            ),
          ),
        ),
      );

      expect(find.text('Ada Riser'), findsOneWidget);
      expect(find.text('+4.3%'), findsOneWidget);
      expect(find.text('-2.6%'), findsOneWidget);

      await tester.tap(find.byKey(const Key('gtex-mover-riser-1')));
      expect(opened, 'riser-1');
    });
  });
}
