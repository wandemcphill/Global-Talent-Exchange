import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/capital/trader/data/trader_api.dart';

void main() {
  test('trader api uses canonical trader routes', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'profile': _profileJson(),
            'portfolio_value': '24820.00',
            'gtex_coin_price': '1.42',
            'daily_pl': '312.40',
            'wallet_balance': '8410.50',
            'market_cap': '412800000',
            'trading_volume': '18200000',
            'trending': <Object?>[_marketJson('market-gtex', 'GTEX')],
            'top_gainers': <Object?>[_marketJson('market-lagfc', 'LAGFC')],
            'top_losers': <Object?>[_marketJson('market-lonfc', 'LONFC')],
            'most_traded_fan_coins': <Object?>[
              _marketJson('market-lagfc', 'LAGFC'),
            ],
            'liquidity_activity': <Object?>[_marketJson('market-gtex', 'GTEX')],
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <Object?>[_marketJson('market-gtex', 'GTEX')],
        ),
        GteTransportResponse(statusCode: 201, body: _orderJson()),
        GteTransportResponse(statusCode: 201, body: _p2pJson()),
        GteTransportResponse(
          statusCode: 200,
          body: <Object?>[
            <String, Object?>{
              'id': 'watch-1',
              'market': _marketJson('market-gtex', 'GTEX'),
            },
          ],
        ),
        GteTransportResponse(
          statusCode: 201,
          body: <String, Object?>{
            'id': 'watch-2',
            'market': _marketJson('market-lagfc', 'LAGFC'),
          },
        ),
        const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'secret': 'JBSWY3DPEHPK3PXP',
            'issuer': 'GTEX',
            'account_label': 'Atlas Desk',
          },
        ),
      ],
    );
    final TraderApi api = TraderApi.standard(
      baseUrl: 'https://example.test',
      accessToken: 'token-1',
      mode: GteBackendMode.live,
      transport: transport,
    );

    final TraderOverview overview = await api.overview();
    final List<TraderMarket> markets = await api.listMarkets();
    await api.placeOrder(
      const TraderOrderCreate(
        marketId: 'market-gtex',
        side: 'buy',
        quantity: 20,
        limitPrice: 1.4,
      ),
    );
    await api.createP2POffer(
      const TraderP2POfferCreate(
        marketId: 'market-gtex',
        side: 'sell',
        quantity: 10,
        unitPrice: 1.5,
        preferredCurrency: 'USD',
      ),
    );
    await api.listWatchlist();
    await api.addWatchlist('market-lagfc');
    await api.setupTotp();

    expect(overview.profile.tradingAlias, 'Atlas Desk');
    expect(overview.profile.isOnline, isTrue);
    expect(overview.profile.trustScore, 91);
    expect(overview.profile.ratingAverage, 4.8);
    expect(overview.profile.disputeHistory.single.status, 'resolved');
    expect(markets.single.symbol, 'GTEX');
    expect(markets.single.orderBook?.bestBid, 1.41);
    expect(markets.single.orderBook?.bestAsk, 1.43);
    expect(markets.single.liveSpread, closeTo(0.02, 0.0001));
    expect(markets.single.settlementEtaMinutes, 12);
    expect(markets.single.settlementRails, <String>['KoraPay', 'manual']);
    expect(
      transport.requests.map((GteTransportRequest request) => request.method),
      <String>['GET', 'GET', 'POST', 'POST', 'GET', 'POST', 'POST'],
    );
    expect(
      transport.requests.map((GteTransportRequest request) => request.uri.path),
      <String>[
        '/api/v2/trader/overview',
        '/api/v2/trader/markets',
        '/api/v2/trader/orders',
        '/api/v2/trader/p2p',
        '/api/v2/trader/watchlist',
        '/api/v2/trader/watchlist',
        '/api/v2/trader/security/totp/setup',
      ],
    );
    expect(
      transport.requests[2].body,
      containsPair('market_id', 'market-gtex'),
    );
    expect(
      transport.requests[5].body,
      containsPair('market_id', 'market-lagfc'),
    );
  });

  test('trader parser reads live depth and trust metadata', () {
    final TraderOverview overview = TraderOverview.fromJson(<String, Object?>{
      'profile': _profileJson(),
      'portfolio_value': '24820.00',
      'gtex_coin_price': '1.42',
      'daily_pl': '312.40',
      'wallet_balance': '8410.50',
      'market_cap': '412800000',
      'trading_volume': '18200000',
      'trending': <Object?>[_marketJson('market-gtex', 'GTEX')],
      'top_gainers': const <Object?>[],
      'top_losers': const <Object?>[],
      'most_traded_fan_coins': const <Object?>[],
      'liquidity_activity': const <Object?>[],
    });

    final TraderMarket market = overview.trending.single;
    expect(overview.profile.tradingAlias, 'Atlas Desk');
    expect(overview.profile.isOnline, isTrue);
    expect(overview.profile.trustScore, 91);
    expect(overview.profile.ratingAverage, 4.8);
    expect(overview.profile.disputeHistory.single.status, 'resolved');
    expect(market.orderBook?.bestBid, 1.41);
    expect(market.orderBook?.bestAsk, 1.43);
    expect(market.liveSpread, closeTo(0.02, 0.0001));
    expect(market.settlementEtaMinutes, 12);
    expect(market.settlementRails, <String>['KoraPay', 'manual']);
  });

  test('trader parser does not invent missing market truth', () {
    final TraderOverview overview = TraderOverview.fromJson(<String, Object?>{
      'profile': _profileJson(),
      'trending': <Object?>[
        <String, Object?>{
          'id': 'market-empty',
          'symbol': 'EMPTY',
          'display_name': 'Empty Feed',
          'asset_type': 'fan_coin',
          'updated_at': '2026-05-18T12:00:00Z',
        },
      ],
      'top_gainers': const <Object?>[],
      'top_losers': const <Object?>[],
      'most_traded_fan_coins': const <Object?>[],
      'liquidity_activity': const <Object?>[],
    });

    final TraderMarket market = overview.trending.single;
    expect(overview.walletBalance, isNull);
    expect(overview.tradingVolume, isNull);
    expect(market.price, isNull);
    expect(market.orderBook, isNull);
    expect(market.liveSpread, isNull);
    expect(market.settlementRails, isEmpty);
    expect(market.hasSettlementRails, isFalse);
  });
}

class _RecordingTransport implements GteTransport {
  _RecordingTransport(this._responses);

  final List<GteTransportResponse> _responses;
  final List<GteTransportRequest> requests = <GteTransportRequest>[];

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    requests.add(request);
    return _responses.removeAt(0);
  }
}

Map<String, Object?> _profileJson() => <String, Object?>{
  'id': 'profile-1',
  'user_id': 'user-1',
  'trading_alias': 'Atlas Desk',
  'preferred_currency': 'USD',
  'trading_experience': 'professional',
  'interests_json': <Object?>['GTEX Coin', 'Fan Coins'],
  'wallet_label': 'Prime Wallet',
  'status': 'VERIFIED',
  'is_online': true,
  'trust_score': 91,
  'trust_tier': 'Prime',
  'rating_average': '4.8',
  'rating_count': 38,
  'dispute_history': <Object?>[
    <String, Object?>{
      'id': 'dispute-1',
      'status': 'resolved',
      'summary': 'Released after evidence review',
      'opened_at': '2026-05-16T12:00:00Z',
      'resolved_at': '2026-05-17T12:00:00Z',
    },
  ],
  'created_at': '2026-05-18T12:00:00Z',
  'updated_at': '2026-05-18T12:00:00Z',
};

Map<String, Object?> _marketJson(String id, String symbol) => <String, Object?>{
  'id': id,
  'symbol': symbol,
  'display_name': '$symbol Fan Coin',
  'asset_type': symbol == 'GTEX' ? 'platform_coin' : 'fan_coin',
  'price': '1.42',
  'daily_change_percent': symbol == 'LONFC' ? '-2.9' : '4.1',
  'market_cap': '412800000',
  'volume_24h': '18200000',
  'liquidity_score': 92,
  'buy_price': '1.43',
  'sell_price': '1.41',
  'settlement_eta_minutes': 12,
  'settlement_rails': <Object?>['KoraPay', 'manual'],
  'order_book': <String, Object?>{
    'synced_at': '2026-05-18T12:00:00Z',
    'bids': <Object?>[
      <String, Object?>{'price': '1.41', 'quantity': '240'},
      <String, Object?>{'price': '1.40', 'quantity': '180'},
    ],
    'asks': <Object?>[
      <String, Object?>{'price': '1.43', 'quantity': '210'},
      <String, Object?>{'price': '1.44', 'quantity': '160'},
    ],
  },
  'candles': <Object?>[
    <String, Object?>{
      'timestamp': '2026-05-18T11:45:00Z',
      'open': '1.39',
      'high': '1.44',
      'low': '1.38',
      'close': '1.42',
      'volume': '8000',
    },
  ],
  'updated_at': '2026-05-18T12:00:00Z',
};

Map<String, Object?> _orderJson() => <String, Object?>{
  'id': 'order-1',
  'market_id': 'market-gtex',
  'side': 'buy',
  'status': 'open',
  'quantity': '20',
  'limit_price': '1.4',
};

Map<String, Object?> _p2pJson() => <String, Object?>{
  'id': 'p2p-1',
  'market_id': 'market-gtex',
  'side': 'sell',
  'status': 'open',
  'quantity': '10',
  'unit_price': '1.5',
  'preferred_currency': 'USD',
};
