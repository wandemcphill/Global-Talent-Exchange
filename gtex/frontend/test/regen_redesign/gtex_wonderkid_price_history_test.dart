import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/player_detail/gtex_player_navigator.dart';
import 'package:gte_frontend/features/regen_redesign/data/gtex_share_market_api.dart';
import 'package:gte_frontend/features/regen_redesign/presentation/gtex_regen_world_screen_v2.dart';
import 'package:gte_frontend/features/regen_redesign/widgets/gtex_share_price_history_panel.dart';
import 'package:gte_frontend/features/regen_redesign/widgets/gtex_wonderkid_board.dart';

class _FakeShareMarket implements GtexShareMarketReader {
  final List<String?> wonderkidNations = <String?>[];
  final List<String> ranges = <String>[];
  bool missingMarket = false;
  int tradeCount = 0;

  @override
  Future<List<GtexShareNation>> fetchRegenNations() async =>
      const <GtexShareNation>[
        GtexShareNation(name: 'Nigeria', count: 643, code: 'NG'),
        GtexShareNation(name: 'Ghana', count: 400, code: 'GH'),
      ];

  @override
  Future<List<GtexWonderkid>> fetchWonderkids({
    String? nation,
    int limit = 20,
  }) async {
    wonderkidNations.add(nation);
    return List<GtexWonderkid>.generate(
      6,
      (int i) => GtexWonderkid(
        playerId: 'wk-$i',
        name: nation == 'Ghana' ? 'Ghana Kid $i' : 'Kid $i',
        sharePriceCoin: 0.0268,
        nationality: nation ?? 'Nigeria',
        position: 'ST',
        age: 19,
        rating: 80,
        potential: 99 - i,
      ),
    );
  }

  @override
  Future<GtexSharePriceHistory> fetchPriceHistory(
    String playerId, {
    String range = '30d',
  }) async {
    ranges.add(range);
    if (missingMarket) {
      throw const GteApiException(
        type: GteApiErrorType.notFound,
        message: 'Player share market was not found.',
        statusCode: 404,
      );
    }
    return GtexSharePriceHistory.fromJson(<String, dynamic>{
      'player_id': playerId,
      'range': range,
      'points': <Map<String, Object?>>[
        <String, Object?>{
          'at': '2026-10-01T00:00:00Z',
          'price': '0.0200',
          'kind': 'listed',
        },
        <String, Object?>{
          'at': '2026-10-17T00:00:00Z',
          'price': '0.0250',
          'kind': 'current',
        },
      ],
      'open_price': '0.0200',
      'current_price': '0.0250',
      'high_price': '0.0250',
      'low_price': '0.0200',
      'change_pct': '25.00',
      'trade_count': tradeCount,
    });
  }
}

Widget _host(Widget child) => MaterialApp(home: Scaffold(body: child));

void main() {
  test('wonderkid and history models parse the backend payloads', () {
    final GtexWonderkid kid = GtexWonderkid.fromJson(<String, dynamic>{
      'player_id': 'p1',
      'player_name': 'Tunde Olawale',
      'share_price_coin': '0.0268',
      'nationality': 'Nigeria',
      'age': 19,
      'rating': 80,
      'potential': 99,
    });
    expect(kid.growthHeadroom, 19);
    expect(kid.sharePriceCoin, closeTo(0.0268, 1e-9));
  });

  testWidgets('wonderkid board ranks kids and refetches per nation', (
    WidgetTester tester,
  ) async {
    final _FakeShareMarket market = _FakeShareMarket();
    final List<String> opened = <String>[];
    await tester.pumpWidget(
      _host(
        GtexPlayerNavigator(
          openPlayer: (String id) async => opened.add(id),
          child: GtexWonderkidBoard(reader: market),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Wonderkid spotlight'), findsOneWidget);
    expect(find.text('#1'), findsOneWidget);
    expect(find.text('Kid 0'), findsOneWidget);
    expect(find.text('80 → 99'), findsOneWidget);
    expect(find.text('+19'), findsOneWidget);
    expect(market.wonderkidNations, <String?>[null]);

    await tester.tap(find.byKey(const Key('gtex-wonderkid-nation-picker')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Ghana (400)').last);
    await tester.pumpAndSettle();
    expect(market.wonderkidNations, <String?>[null, 'Ghana']);
    expect(find.text('Ghana Kid 0'), findsOneWidget);

    await tester.tap(find.byKey(const Key('gtex-wonderkid-row-wk-0')));
    await tester.pumpAndSettle();
    expect(opened, <String>['wk-0']);
  });

  testWidgets('price history panel shows change, chart and range refetch', (
    WidgetTester tester,
  ) async {
    final _FakeShareMarket market = _FakeShareMarket();
    await tester.pumpWidget(
      _host(
        SingleChildScrollView(
          child: GtexSharePriceHistoryPanel(reader: market, playerId: 'p1'),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Price history'), findsOneWidget);
    expect(find.text('+25.00%'), findsOneWidget);
    expect(find.byKey(const Key('gtex-price-history-chart')), findsOneWidget);
    expect(find.byKey(const Key('gtex-price-history-untraded')), findsOneWidget);

    await tester.tap(find.byKey(const Key('gtex-price-history-range-7d')));
    await tester.pumpAndSettle();
    expect(market.ranges, <String>['30d', '7d']);
  });

  testWidgets('price history panel states a missing share market', (
    WidgetTester tester,
  ) async {
    final _FakeShareMarket market = _FakeShareMarket()..missingMarket = true;
    await tester.pumpWidget(
      _host(GtexSharePriceHistoryPanel(reader: market, playerId: 'p1')),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('gtex-price-history-no-market')), findsOneWidget);
  });

  testWidgets('Regen World shows the Wonderkids lane only with a share market', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1600, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(_host(GtexRegenWorldScreenV2.fixture()));
    await tester.pumpAndSettle();
    expect(find.text('Wonderkids'), findsNothing);
    expect(find.byKey(const Key('gtex-price-history-panel')), findsNothing);

    await tester.pumpWidget(
      _host(GtexRegenWorldScreenV2.fixture(shareMarket: _FakeShareMarket())),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('gtex-price-history-panel')), findsOneWidget);
    await tester.tap(find.text('Wonderkids'));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('gtex-wonderkid-board')), findsOneWidget);
    expect(find.text('Kid 0'), findsOneWidget);
  });
}
