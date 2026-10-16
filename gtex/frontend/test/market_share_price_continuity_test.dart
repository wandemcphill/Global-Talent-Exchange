import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_exchange_models.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// One price, everywhere the user meets it.
///
/// Browse, detail and settlement all have to quote the same
/// `share_price_coin`. Two ways that broke: the browse list never carried the
/// price at all, and once it did, a settled trade moved the price on the
/// server while the cached list went on quoting the old one.
GteMarketPlayerListItem _item({
  required String playerId,
  double? sharePriceCoin,
}) {
  return GteMarketPlayerListItem(
    playerId: playerId,
    playerName: 'Player $playerId',
    position: 'CM',
    nationality: 'Testland',
    currentClubName: 'Test FC',
    currentValueCredits: 1000,
    sharePriceCoin: sharePriceCoin,
    movementPct: null,
    trendScore: null,
    marketInterestScore: null,
    averageRating: null,
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  SharedPreferences.setMockInitialValues(const <String, Object>{});

  group('GteMarketPlayerListView.withSharePrice', () {
    final GteMarketPlayerListView page = GteMarketPlayerListView(
      items: <GteMarketPlayerListItem>[
        _item(playerId: 'traded', sharePriceCoin: 5),
        _item(playerId: 'untouched', sharePriceCoin: 7),
      ],
      limit: 20,
      hasMore: false,
      offset: 0,
      total: 2,
    );

    test('writes the settled price onto the traded row only', () {
      final GteMarketPlayerListView next = page.withSharePrice('traded', 9);

      expect(next.items[0].sharePriceCoin, 9);
      expect(next.items[1].sharePriceCoin, 7);
      expect(next.total, 2);
      // Untouched rows keep their identity rather than being rebuilt.
      expect(identical(next.items[1], page.items[1]), isTrue);
    });

    test('leaves the page alone when nothing changed', () {
      expect(identical(page.withSharePrice('traded', 5), page), isTrue);
      expect(identical(page.withSharePrice('absent', 9), page), isTrue);
    });
  });

  test('the browse list quotes the price a trade settles at', () async {
    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );
    await controller.bootstrap();

    final GteMarketPlayerListItem row = controller.marketPage!.items.firstWhere(
      (GteMarketPlayerListItem item) => item.playerId == 'lamine-yamal',
    );

    expect(row.sharePriceCoin, isNotNull);
    expect(row.sharePriceCoin, greaterThan(0));
  });

  test('a settled trade updates the price the browse list quotes', () async {
    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );
    await controller.bootstrap();
    await controller.signIn(
      email: 'fixture.trader@gte.local',
      password: 'DemoPass123', // pragma: allowlist secret
    );

    // Put a stale price in the cached page, as a trade elsewhere would.
    controller.marketPage = controller.marketPage!.withSharePrice(
      'lamine-yamal',
      999,
    );

    final GtePlayerShareTradeResult? trade = await controller
        .tradePlayerShares(
          playerId: 'lamine-yamal',
          side: GteOrderSide.buy,
          shareCount: 1,
          idempotencyKey: 'browse-price-refresh-key',
        );

    expect(trade, isNotNull);
    final GteMarketPlayerListItem row = controller.marketPage!.items.firstWhere(
      (GteMarketPlayerListItem item) => item.playerId == 'lamine-yamal',
    );
    // The server's post-trade price, not the stale one and not a guess.
    expect(row.sharePriceCoin, trade!.market.sharePriceCoin);
    expect(row.sharePriceCoin, isNot(999));
  });
}
