import '../../../data/gte_api_contract.dart';
import '../../../data/gte_api_repository.dart';
import '../../../data/gte_authed_api.dart';
import '../domain/market_models.dart';

class MarketApiService {
  const MarketApiService({required GteAuthedApi client}) : _client = client;

  final GteAuthedApi _client;

  Future<List<JsonMap>> listTransferListings({MarketFilters? filters}) async {
    final Object? payload = await _requestDirect(
      'GET',
      '/api/transfer-market/players',
      query: _marketPlayerQuery(filters),
      auth: false,
    );
    return _extractMapList(payload, 'market players');
  }

  Future<JsonMap> searchMarketPlayers({
    required MarketFilters filters,
    int page = 1,
    int pageSize = 24,
  }) async {
    final Object? payload = await _requestDirect(
      'GET',
      '/api/transfer-market/players',
      query: _marketPlayerQuery(filters, page: page, pageSize: pageSize),
      auth: false,
    );
    if (payload is List) {
      return <String, Object?>{
        'items': payload,
        'page': page,
        'page_size': pageSize,
        'total': payload.length,
      };
    }
    return _map(payload, 'market player page');
  }

  Future<JsonMap> fetchTransferListing(String listingId) {
    return _client.getMap(
      '/api/transfer-market/listings/$listingId',
      auth: false,
    );
  }

  Future<JsonMap> postListingBid(PlaceBidRequest request) async {
    final String listingId = request.listingId?.trim() ?? '';
    if (listingId.isEmpty) {
      throw const MarketApiContractException(
        'listing_id_required',
        'Listing bid placement requires a listing id.',
      );
    }
    final Object? payload = await _client.post(
      '/api/transfer-market/listings/$listingId/bids',
      body: request.toListingJson(),
      auth: true,
    );
    return _map(payload, 'listing bid response');
  }

  Future<JsonMap> fetchPlayerOverview(String playerId) {
    return _getDirectMap('/api/transfer-market/players/$playerId', auth: false);
  }

  Future<JsonMap> fetchPlayerCard(String playerId) {
    return _client.getMap('/api/players/real-universe/$playerId', auth: false);
  }

  Future<List<JsonMap>> listTransferWindows() async {
    final List<dynamic> payload = await _client.getList(
      '/api/transfers/windows',
      auth: false,
    );
    return payload
        .map((dynamic item) => _map(item, 'transfer window'))
        .toList(growable: false);
  }

  Future<List<JsonMap>> listWindowBids(String windowId) async {
    final List<dynamic> payload = await _client.getList(
      '/api/transfers/windows/$windowId/bids',
      auth: false,
    );
    return payload
        .map((dynamic item) => _map(item, 'transfer bid'))
        .toList(growable: false);
  }

  Future<JsonMap> createWindowBid(
    String windowId,
    PlaceBidRequest request,
  ) async {
    final Object? payload = await _client.post(
      '/api/transfers/windows/$windowId/bids',
      body: request.toLifecycleJson(),
      auth: true,
    );
    return _map(payload, 'transfer bid');
  }

  Future<JsonMap> acceptWindowBid(AcceptBidRequest request) async {
    final Object? payload = await _client.post(
      '/api/transfers/windows/${request.windowId}/bids/${request.bidId}/accept',
      body: request.toJson(),
      auth: true,
    );
    return _map(payload, 'accepted transfer bid');
  }

  Future<JsonMap> rejectWindowBid(RejectBidRequest request) async {
    final Object? payload = await _client.post(
      '/api/transfers/windows/${request.windowId}/bids/${request.bidId}/reject',
      body: request.toJson(),
      auth: true,
    );
    return _map(payload, 'rejected transfer bid');
  }

  Future<JsonMap> counterWindowBid(CounterBidRequest request) async {
    final Object? payload = await _client.post(
      '/api/transfers/windows/${request.windowId}/bids/${request.bidId}/counter',
      body: request.toJson(),
      auth: true,
    );
    return _map(payload, 'counter transfer bid');
  }

  Future<JsonMap> withdrawWindowBid(WithdrawBidRequest request) async {
    final Object? payload = await _client.post(
      '/api/transfers/windows/${request.windowId}/bids/${request.bidId}/withdraw',
      body: request.toJson(),
      auth: true,
    );
    return _map(payload, 'withdrawn transfer bid');
  }

  Future<JsonMap> withdrawMarketBid(WithdrawBidRequest request) async {
    final String bidId = request.bidId.trim();
    if (bidId.isEmpty) {
      throw const MarketApiContractException(
        'bid_id_required',
        'Market bid withdrawal requires a bid id.',
      );
    }
    final Object? payload = await _requestDirect(
      'POST',
      '/api/v2/transfer-market/bid/$bidId/withdraw',
      body: request.toJson(),
      auth: true,
    );
    return _map(payload, 'withdrawn market bid');
  }

  Future<List<JsonMap>> listBasket() async {
    final Object? payload = await _requestDirect(
      'GET',
      '/api/transfer-market/basket',
      auth: true,
    );
    return _extractMapList(payload, 'market basket');
  }

  Future<JsonMap> addToBasket({
    required String playerId,
    required String clubId,
  }) async {
    final Object? payload = await _requestDirect(
      'POST',
      '/api/transfer-market/basket',
      query: <String, Object?>{'clubId': clubId},
      body: <String, Object?>{'player_id': playerId},
      auth: true,
    );
    final List<JsonMap> items = _extractMapList(payload, 'market basket');
    for (final JsonMap item in items) {
      if (item['player_id']?.toString() == playerId) {
        return item;
      }
    }
    throw FormatException('Expected added market basket player $playerId.');
  }

  Future<void> removeFromBasket({required String playerId}) async {
    await _requestDirect(
      'DELETE',
      '/api/transfer-market/basket/$playerId',
      auth: true,
    );
  }

  Future<JsonMap> fetchCheckoutReadiness() async {
    final Object? payload = await _requestDirect(
      'GET',
      '/api/transfer-market/checkout',
      auth: true,
    );
    return _map(payload, 'market checkout readiness');
  }

  Future<JsonMap> submitCheckout({
    String? idempotencyKey,
    String? notes,
  }) async {
    final Object? payload = await _requestDirect(
      'POST',
      '/api/transfer-market/checkout',
      body: _compact(<String, Object?>{
        'idempotency_key': idempotencyKey,
        'notes': notes,
      }),
      auth: true,
    );
    return _map(payload, 'market checkout submission');
  }

  Future<List<JsonMap>> listMarketActivity({int limit = 50}) async {
    final Object? payload = await _requestDirect(
      'GET',
      '/api/transfer-market/activity',
      query: <String, Object?>{'limit': limit},
      auth: false,
    );
    return _extractMapList(payload, 'market activity');
  }

  Future<List<JsonMap>> listMarketHistory({int limit = 50}) async {
    final Object? payload = await _requestDirect(
      'GET',
      '/api/transfer-market/history',
      query: <String, Object?>{'limit': limit},
      auth: false,
    );
    return _extractMapList(payload, 'market history');
  }

  Future<List<JsonMap>> listMarketBids({String? clubId, String? status}) async {
    final Object? payload = await _requestDirect(
      'GET',
      '/api/transfer-market/bids',
      query: _compact(<String, Object?>{'clubId': clubId, 'status': status}),
      auth: true,
    );
    return _extractMapList(payload, 'market bids');
  }

  Future<JsonMap> fetchMarketBid(String bidId) {
    return _getDirectMap('/api/transfer-market/bid/$bidId', auth: true);
  }

  Future<JsonMap> fetchWalletSummary() {
    return _client.getMap(
      '/api/wallets/summary',
      query: const <String, Object?>{'currency': 'coin'},
      auth: true,
    );
  }

  Future<JsonMap> _getDirectMap(
    String path, {
    Map<String, Object?> query = const <String, Object?>{},
    bool auth = true,
  }) async {
    final Object? payload = await _requestDirect(
      'GET',
      path,
      query: query,
      auth: auth,
    );
    return _map(payload, path);
  }

  Future<Object?> _requestDirect(
    String method,
    String path, {
    Map<String, Object?> query = const <String, Object?>{},
    Object? body,
    bool auth = true,
  }) async {
    final Map<String, String> headers = <String, String>{
      'Content-Type': 'application/json',
    };
    if (auth) {
      final String token =
          _client.authSession?.accessToken.trim().isNotEmpty == true
              ? _client.authSession!.accessToken
              : (_client.accessToken ?? '');
      if (token.trim().isEmpty) {
        throw const GteApiException(
          type: GteApiErrorType.unauthorized,
          message: 'Authentication required for this action.',
        );
      }
      headers['Authorization'] = 'Bearer ${token.trim()}';
    }
    final GteTransportResponse response = await _client.transport.send(
      GteTransportRequest(
        method: method,
        uri: _directUri(path, query),
        headers: gteVersionedApiHeaders(headers),
        body: body,
      ),
    );
    if (response.statusCode >= 400) {
      throw GteApiException(
        type: _errorType(response.statusCode),
        message: gteApiErrorMessage(
          response.body,
          fallback: 'Market request failed.',
        ),
        statusCode: response.statusCode,
      );
    }
    return gteApiSuccessPayload(response.body);
  }

  Uri _directUri(String path, Map<String, Object?> query) {
    final String normalizedPath =
        path.trim().startsWith('/') ? path.trim() : '/${path.trim()}';
    return _client.config.uriFor(normalizedPath, _compact(query));
  }
}

class MarketApiContractException implements Exception {
  const MarketApiContractException(this.code, this.message);

  final String code;
  final String message;

  @override
  String toString() => '$code: $message';
}

JsonMap _marketPlayerQuery(MarketFilters? filters, {int? page, int? pageSize}) {
  if (filters == null) {
    return _compact(<String, Object?>{
      'status': 'open',
      'page': page,
      'page_size': pageSize,
      'per_page': pageSize,
    });
  }
  final JsonMap query = filters.toQuery(
    page: page ?? 1,
    pageSize: pageSize ?? 24,
  );
  return _compact(<String, Object?>{
    ...query,
    'status': filters.status ?? 'open',
  });
}

List<JsonMap> _extractMapList(Object? payload, String label) {
  if (payload is List) {
    return payload
        .map((Object? item) => _map(item, label))
        .toList(growable: false);
  }
  final JsonMap json = _map(payload, label);
  final Object? items =
      json['items'] ??
      json['data'] ??
      json['results'] ??
      json['watchlist'] ??
      json['listings'] ??
      json['bids'];
  if (items == null) {
    throw FormatException('Expected $label list from backend.');
  }
  if (items is! List) {
    throw FormatException('Expected $label list from backend.');
  }
  return items.map((Object? item) => _map(item, label)).toList(growable: false);
}

JsonMap _map(Object? value, String label) {
  if (value is Map<String, Object?>) {
    return value;
  }
  if (value is Map) {
    return value.map(
      (Object? key, Object? item) => MapEntry(key.toString(), item),
    );
  }
  throw FormatException('Expected $label object from backend.');
}

JsonMap _compact(JsonMap value) {
  final JsonMap result = <String, Object?>{};
  for (final MapEntry<String, Object?> entry in value.entries) {
    final Object? item = entry.value;
    if (item == null) {
      continue;
    }
    if (item is String && item.trim().isEmpty) {
      continue;
    }
    result[entry.key] = item;
  }
  return result;
}

GteApiErrorType _errorType(int statusCode) {
  if (statusCode == 401 || statusCode == 403) {
    return GteApiErrorType.unauthorized;
  }
  if (statusCode == 404) {
    return GteApiErrorType.notFound;
  }
  if (statusCode == 422) {
    return GteApiErrorType.validation;
  }
  if (statusCode >= 500) {
    return GteApiErrorType.unavailable;
  }
  return GteApiErrorType.unknown;
}
