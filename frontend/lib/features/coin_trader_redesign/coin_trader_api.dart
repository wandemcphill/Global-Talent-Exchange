import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';

import 'coin_trader_models.dart';

class GtexCoinTraderApi {
  GtexCoinTraderApi({required this.client});

  final GteAuthedApi client;

  factory GtexCoinTraderApi.standard({
    required String baseUrl,
    required String? accessToken,
    GteBackendMode mode = GteBackendMode.live,
  }) {
    final GteBackendMode resolvedMode = gteProductionBackendMode(mode);
    return GtexCoinTraderApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: resolvedMode),
        transport: GteHttpTransport(),
        accessToken: accessToken,
        mode: resolvedMode,
      ),
    );
  }

  factory GtexCoinTraderApi.fixture() {
    return GtexCoinTraderApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: GteHttpTransport(),
        accessToken: 'fixture-token',
        mode: GteBackendMode.fixture,
      ),
    );
  }

  Future<List<GtexCoinTraderProfile>> listTraders({
    String? countryCode,
    String? coinUnit,
  }) {
    return client.withFallback<List<GtexCoinTraderProfile>>(() async {
      final List<dynamic> payload = await client.getList(
        _path('/api/coin-traders'),
        auth: false,
        query: <String, Object?>{
          if (_notBlank(countryCode)) 'country_code': countryCode,
          if (_notBlank(coinUnit)) 'coin_unit': _ledgerUnit(coinUnit!),
        },
      );
      return payload
          .map(GtexCoinTraderProfile.fromJson)
          .toList(growable: false);
    }, () async => const <GtexCoinTraderProfile>[]);
  }

  Future<GtexCoinTraderProfile> fetchTrader(String profileId) {
    return client.withFallback<GtexCoinTraderProfile>(
      () async {
        final Map<String, dynamic> payload = await client.getMap(
          _path('/api/coin-traders/$profileId'),
          auth: false,
        );
        return GtexCoinTraderProfile.fromJson(payload);
      },
      () async {
        throw _fixtureMissingProfile();
      },
    );
  }

  Future<GtexCoinTraderProfile> fetchMyProfile() {
    return client.withFallback<GtexCoinTraderProfile>(
      () async {
        final Map<String, dynamic> payload = await client.getMap(
          _path('/api/coin-traders/me'),
        );
        return GtexCoinTraderProfile.fromJson(payload);
      },
      () async {
        throw _fixtureMissingProfile();
      },
    );
  }

  Future<GtexCoinTraderProfile> applyTraderProfile({
    required String displayName,
    String? countryCode,
    Map<String, Object?> terms = const <String, Object?>{},
    List<Map<String, Object?>> paymentMethods = const <Map<String, Object?>>[],
    List<Map<String, Object?>> bankAccounts = const <Map<String, Object?>>[],
    Map<String, Object?> metadata = const <String, Object?>{},
  }) async {
    final Object? payload = await client.post(
      _path('/api/coin-traders/apply'),
      body: <String, Object?>{
        'display_name': displayName,
        if (_notBlank(countryCode)) 'country_code': countryCode,
        'terms': terms,
        'payment_methods': paymentMethods,
        'bank_accounts': bankAccounts,
        'metadata_json': metadata,
      },
    );
    return GtexCoinTraderProfile.fromJson(payload);
  }

  Future<GtexCoinTraderRate> upsertRate({
    required String coinUnit,
    required String fiatCurrency,
    required double buyRateFiat,
    required double sellRateFiat,
    required double minCoinAmount,
    required double maxCoinAmount,
    required double availableLiquidity,
    bool isActive = true,
  }) async {
    final Object? payload = await client.request(
      'PUT',
      _path('/api/coin-traders/me/rates'),
      body: <String, Object?>{
        'coin_unit': _ledgerUnit(coinUnit),
        'fiat_currency': fiatCurrency,
        'buy_rate_fiat': buyRateFiat,
        'sell_rate_fiat': sellRateFiat,
        'min_coin_amount': minCoinAmount,
        'max_coin_amount': maxCoinAmount,
        'available_liquidity': availableLiquidity,
        'is_active': isActive,
        'metadata_json': const <String, Object?>{},
      },
    );
    return GtexCoinTraderRate.fromJson(payload);
  }

  Future<GtexCoinTradeOrder> createOrder({
    required String traderProfileId,
    required String direction,
    required String coinUnit,
    required double coinAmount,
    required String fiatCurrency,
    String? paymentMethod,
  }) async {
    final Object? payload = await client.post(
      _path('/api/coin-traders/orders'),
      body: <String, Object?>{
        'trader_profile_id': traderProfileId,
        'direction': direction,
        'coin_unit': _ledgerUnit(coinUnit),
        'coin_amount': coinAmount,
        'fiat_currency': fiatCurrency,
        if (_notBlank(paymentMethod)) 'payment_method': paymentMethod,
        'idempotency_key':
            'web-${DateTime.now().microsecondsSinceEpoch}-$traderProfileId',
      },
    );
    return GtexCoinTradeOrder.fromJson(payload);
  }

  Future<List<GtexCoinTradeOrder>> listMyOrders({bool asTrader = false}) {
    return client.withFallback<List<GtexCoinTradeOrder>>(() async {
      final List<dynamic> payload = await client.getList(
        _path('/api/coin-traders/orders'),
        query: <String, Object?>{'as_trader': asTrader},
      );
      return payload.map(GtexCoinTradeOrder.fromJson).toList(growable: false);
    }, () async => const <GtexCoinTradeOrder>[]);
  }

  Future<GtexCoinTradeOrder> acceptOrder(String orderId) async {
    final Object? payload = await client.post(
      _path('/api/coin-traders/orders/$orderId/accept'),
    );
    return GtexCoinTradeOrder.fromJson(payload);
  }

  Future<GtexCoinTradeOrder> submitProof({
    required String orderId,
    String? proofReference,
    String? proofUrl,
    String? note,
  }) async {
    final Object? payload = await client.post(
      _path('/api/coin-traders/orders/$orderId/proof'),
      body: <String, Object?>{
        if (_notBlank(proofReference)) 'proof_reference': proofReference,
        if (_notBlank(proofUrl)) 'proof_url': proofUrl,
        if (_notBlank(note)) 'note': note,
      },
    );
    return GtexCoinTradeOrder.fromJson(payload);
  }

  Future<GtexCoinTradeOrder> confirmOrder(String orderId) async {
    final Object? payload = await client.post(
      _path('/api/coin-traders/orders/$orderId/confirm'),
    );
    return GtexCoinTradeOrder.fromJson(payload);
  }

  Future<GtexCoinTradeOrder> cancelOrder(String orderId) async {
    final Object? payload = await client.post(
      _path('/api/coin-traders/orders/$orderId/cancel'),
    );
    return GtexCoinTradeOrder.fromJson(payload);
  }

  Future<GtexCoinTradeOrder> disputeOrder({
    required String orderId,
    required String reason,
    Map<String, Object?> evidence = const <String, Object?>{},
  }) async {
    final Object? payload = await client.post(
      _path('/api/coin-traders/orders/$orderId/dispute'),
      body: <String, Object?>{'reason': reason, 'evidence': evidence},
    );
    return GtexCoinTradeOrder.fromJson(payload);
  }

  Future<List<GtexCoinTraderProfile>> adminListTraders() {
    return client.withFallback<List<GtexCoinTraderProfile>>(() async {
      final List<dynamic> payload = await client.getList(
        _path('/api/admin/coin-traders'),
      );
      return payload
          .map(GtexCoinTraderProfile.fromJson)
          .toList(growable: false);
    }, () async => const <GtexCoinTraderProfile>[]);
  }

  Future<List<GtexCoinTradeOrder>> adminListOrders() {
    return client.withFallback<List<GtexCoinTradeOrder>>(() async {
      final List<dynamic> payload = await client.getList(
        _path('/api/admin/coin-traders/orders'),
      );
      return payload.map(GtexCoinTradeOrder.fromJson).toList(growable: false);
    }, () async => const <GtexCoinTradeOrder>[]);
  }

  Future<GtexCoinTraderProfile> adminApproveTrader(
    String profileId, {
    String tier = 'bronze',
    String? note,
  }) async {
    final Object? payload = await client.post(
      _path('/api/admin/coin-traders/$profileId/approve'),
      body: <String, Object?>{'tier': tier, if (_notBlank(note)) 'note': note},
    );
    return GtexCoinTraderProfile.fromJson(payload);
  }

  Future<GtexCoinTraderProfile> adminRejectTrader(
    String profileId, {
    String? note,
  }) async {
    final Object? payload = await client.post(
      _path('/api/admin/coin-traders/$profileId/reject'),
      body: <String, Object?>{if (_notBlank(note)) 'note': note},
    );
    return GtexCoinTraderProfile.fromJson(payload);
  }

  Future<GtexCoinTraderProfile> adminFreezeTrader(
    String profileId, {
    String? note,
  }) async {
    final Object? payload = await client.post(
      _path('/api/admin/coin-traders/$profileId/freeze'),
      body: <String, Object?>{if (_notBlank(note)) 'note': note},
    );
    return GtexCoinTraderProfile.fromJson(payload);
  }

  Future<GtexCoinTradeOrder> adminResolveOrder(
    String orderId, {
    required String resolution,
    String? note,
  }) async {
    final Object? payload = await client.post(
      _path('/api/admin/coin-traders/orders/$orderId/resolve'),
      body: <String, Object?>{
        'resolution': resolution,
        if (_notBlank(note)) 'note': note,
      },
    );
    return GtexCoinTradeOrder.fromJson(payload);
  }

  String _path(String path) {
    final Uri base = Uri.parse(
      client.config.baseUrl.endsWith('/')
          ? client.config.baseUrl
          : '${client.config.baseUrl}/',
    );
    return base
        .resolve(path.startsWith('/') ? path.substring(1) : path)
        .toString();
  }
}

bool _notBlank(String? value) => value != null && value.trim().isNotEmpty;

String _ledgerUnit(String value) {
  final String normalized = value.trim().toLowerCase();
  return normalized == 'credit' ? 'credit' : 'coin';
}

GteApiException _fixtureMissingProfile() {
  return const GteApiException(
    type: GteApiErrorType.notFound,
    message: 'No coin trader profile exists for this fixture session.',
    statusCode: 404,
  );
}
