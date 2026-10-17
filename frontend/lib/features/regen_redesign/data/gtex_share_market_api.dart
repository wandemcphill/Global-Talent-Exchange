import 'package:gte_frontend/data/gte_authed_api.dart';

double _toDouble(Object? value) =>
    value is num ? value.toDouble() : double.tryParse('${value ?? ''}') ?? 0;

int? _toInt(Object? value) =>
    value is num ? value.toInt() : int.tryParse('${value ?? ''}');

String? _toText(Object? value) {
  final String text = '${value ?? ''}'.trim();
  return text.isEmpty ? null : text;
}

/// A regen aged 21 or under, ranked by `sort=wonderkid` on the share market.
class GtexWonderkid {
  const GtexWonderkid({
    required this.playerId,
    required this.name,
    required this.sharePriceCoin,
    this.nationality,
    this.position,
    this.age,
    this.rating,
    this.potential,
    this.imageUrl,
    this.priceChange7dPct,
  });

  factory GtexWonderkid.fromJson(Map<String, dynamic> json) => GtexWonderkid(
    playerId: '${json['player_id']}',
    name: _toText(json['player_name']) ?? 'Unnamed regen',
    sharePriceCoin: _toDouble(json['share_price_coin']),
    nationality: _toText(json['nationality']),
    position: _toText(json['position']),
    age: _toInt(json['age']),
    rating: _toInt(json['rating']),
    potential: _toInt(json['potential']),
    imageUrl: _toText(json['image_url']),
    priceChange7dPct:
        json['price_change_7d_pct'] == null
            ? null
            : _toDouble(json['price_change_7d_pct']),
  );

  final String playerId;
  final String name;
  final double sharePriceCoin;
  final String? nationality;
  final String? position;
  final int? age;
  final int? rating;
  final int? potential;
  final String? imageUrl;

  /// Share price change versus 7 days ago (or since listing when younger).
  final double? priceChange7dPct;

  int? get growthHeadroom =>
      rating == null || potential == null ? null : potential! - rating!;
}

class GtexShareNation {
  const GtexShareNation({required this.name, required this.count, this.code});

  factory GtexShareNation.fromJson(Map<String, dynamic> json) =>
      GtexShareNation(
        name: '${json['name']}',
        count: _toInt(json['count']) ?? 0,
        code: _toText(json['code']),
      );

  final String name;
  final int count;
  final String? code;
}

class GtexSharePricePoint {
  const GtexSharePricePoint({
    required this.at,
    required this.price,
    required this.kind,
  });

  factory GtexSharePricePoint.fromJson(Map<String, dynamic> json) =>
      GtexSharePricePoint(
        at: DateTime.parse('${json['at']}'),
        price: _toDouble(json['price']),
        kind: '${json['kind']}',
      );

  final DateTime at;
  final double price;
  final String kind;
}

class GtexSharePriceHistory {
  const GtexSharePriceHistory({
    required this.playerId,
    required this.range,
    required this.points,
    required this.openPrice,
    required this.currentPrice,
    required this.highPrice,
    required this.lowPrice,
    required this.changePct,
    required this.tradeCount,
  });

  factory GtexSharePriceHistory.fromJson(Map<String, dynamic> json) =>
      GtexSharePriceHistory(
        playerId: '${json['player_id']}',
        range: '${json['range']}',
        points: ((json['points'] as List<dynamic>?) ?? <dynamic>[])
            .whereType<Map<dynamic, dynamic>>()
            .map(
              (Map<dynamic, dynamic> p) =>
                  GtexSharePricePoint.fromJson(Map<String, dynamic>.from(p)),
            )
            .toList(growable: false),
        openPrice: _toDouble(json['open_price']),
        currentPrice: _toDouble(json['current_price']),
        highPrice: _toDouble(json['high_price']),
        lowPrice: _toDouble(json['low_price']),
        changePct: _toDouble(json['change_pct']),
        tradeCount: _toInt(json['trade_count']) ?? 0,
      );

  final String playerId;
  final String range;
  final List<GtexSharePricePoint> points;
  final double openPrice;
  final double currentPrice;
  final double highPrice;
  final double lowPrice;
  final double changePct;
  final int tradeCount;
}

/// Read side of the player share market used by the wonderkid board and the
/// price history panel. An interface so widgets can be tested without HTTP.
abstract class GtexShareMarketReader {
  Future<List<GtexShareNation>> fetchRegenNations();

  Future<List<GtexWonderkid>> fetchWonderkids({String? nation, int limit = 20});

  Future<GtexSharePriceHistory> fetchPriceHistory(
    String playerId, {
    String range = '30d',
  });
}

class GtexShareMarketApi implements GtexShareMarketReader {
  const GtexShareMarketApi({required this.client});

  final GteAuthedApi client;

  @override
  Future<List<GtexShareNation>> fetchRegenNations() async {
    final List<dynamic> rows = await client.getList(
      '/players/markets/nations',
      query: <String, Object?>{'source': 'regen'},
      auth: false,
    );
    return rows
        .whereType<Map<dynamic, dynamic>>()
        .map(
          (Map<dynamic, dynamic> row) =>
              GtexShareNation.fromJson(Map<String, dynamic>.from(row)),
        )
        .toList(growable: false);
  }

  @override
  Future<List<GtexWonderkid>> fetchWonderkids({
    String? nation,
    int limit = 20,
  }) async {
    final Map<String, dynamic> page = await client.getMap(
      '/players/markets',
      query: <String, Object?>{
        'sort': 'wonderkid',
        'page': 1,
        'per_page': limit,
        if (nation != null && nation.isNotEmpty) 'nation': nation,
      },
      auth: false,
    );
    return ((page['items'] as List<dynamic>?) ?? <dynamic>[])
        .whereType<Map<dynamic, dynamic>>()
        .map(
          (Map<dynamic, dynamic> row) =>
              GtexWonderkid.fromJson(Map<String, dynamic>.from(row)),
        )
        .toList(growable: false);
  }

  @override
  Future<GtexSharePriceHistory> fetchPriceHistory(
    String playerId, {
    String range = '30d',
  }) async {
    return GtexSharePriceHistory.fromJson(
      await client.getMap(
        '/players/${playerId.trim()}/shares/price-history',
        query: <String, Object?>{'range': range},
        auth: false,
      ),
    );
  }
}
