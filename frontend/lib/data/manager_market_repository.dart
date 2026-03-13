import 'gte_api_repository.dart';
import 'gte_http_transport.dart';

class ManagerMarketRepository {
  ManagerMarketRepository({
    required this.config,
    required this.transport,
    required this.accessToken,
  });

  final GteRepositoryConfig config;
  final GteTransport transport;
  final String accessToken;

  factory ManagerMarketRepository.standard({
    required String baseUrl,
    required String accessToken,
    GteBackendMode mode = GteBackendMode.liveThenFixture,
  }) {
    return ManagerMarketRepository(
      config: GteRepositoryConfig(baseUrl: baseUrl, mode: mode),
      transport: GteHttpTransport(),
      accessToken: accessToken,
    );
  }

  Future<Map<String, dynamic>> fetchFilters() async => _getMap('/api/managers/filters', auth: false);

  Future<Map<String, dynamic>> fetchCatalog({String? search, String? tactic, String? trait, String? mentality, String? rarity, int limit = 500}) async {
    return _getMap('/api/managers/catalog', query: <String, Object?>{
      'limit': limit,
      if (search != null && search.trim().isNotEmpty) 'search': search.trim(),
      if (tactic != null && tactic.isNotEmpty) 'tactic': tactic,
      if (trait != null && trait.isNotEmpty) 'trait': trait,
      if (mentality != null && mentality.isNotEmpty) 'mentality': mentality,
      if (rarity != null && rarity.isNotEmpty) 'rarity': rarity,
    }, auth: false);
  }

  Future<Map<String, dynamic>> fetchTeam() async => _getMap('/api/managers/team');
  Future<List<Map<String, dynamic>>> fetchListings() async => _getList('/api/managers/trade-listings', auth: false);
  Future<List<Map<String, dynamic>>> fetchMyListings() async => _getList('/api/managers/my-trade-listings');
  Future<Map<String, dynamic>> fetchRecommendation() async => _getMap('/api/managers/recommendation');
  Future<List<Map<String, dynamic>>> fetchTradeHistory({String? managerId, int limit = 50}) async => _getList('/api/managers/history', query: <String, Object?>{'limit': limit, if (managerId != null && managerId.isNotEmpty) 'manager_id': managerId});
  Future<Map<String, dynamic>> compareManagers(String leftManagerId, String rightManagerId) async => _getMap('/api/managers/compare', query: <String, Object?>{'left_manager_id': leftManagerId, 'right_manager_id': rightManagerId}, auth: false);

  Future<void> recruit(String managerId, {String slot = 'bench'}) => _post('/api/managers/recruit', body: <String, Object?>{'manager_id': managerId, 'slot': slot});
  Future<void> assign(String assetId, String slot) => _post('/api/managers/assign', body: <String, Object?>{'asset_id': assetId, 'slot': slot});
  Future<void> release(String assetId) => _post('/api/managers/$assetId/release');
  Future<void> createListing(String assetId, String askingPriceCredits) => _post('/api/managers/trade-listings', body: <String, Object?>{'asset_id': assetId, 'asking_price_credits': askingPriceCredits});
  Future<void> buyListing(String listingId) => _post('/api/managers/trade-listings/$listingId/buy');
  Future<void> cancelListing(String listingId) => _post('/api/managers/trade-listings/$listingId/cancel');
  Future<void> swap(String proposerAssetId, String requestedAssetId, String cashAdjustmentCredits) => _post('/api/managers/swap', body: <String, Object?>{'proposer_asset_id': proposerAssetId, 'requested_asset_id': requestedAssetId, 'cash_adjustment_credits': cashAdjustmentCredits});

  Future<Map<String, dynamic>> _getMap(String path, {Map<String, Object?> query = const <String, Object?>{}, bool auth = true}) async {
    final Object? body = await _request('GET', path, query: query, auth: auth);
    if (body is Map<String, dynamic>) {
      return body;
    }
    throw const GteApiException(type: GteApiErrorType.parsing, message: 'Unexpected manager response shape.');
  }

  Future<List<Map<String, dynamic>>> _getList(String path, {Map<String, Object?> query = const <String, Object?>{}, bool auth = true}) async {
    final Object? body = await _request('GET', path, query: query, auth: auth);
    if (body is List) {
      return body.whereType<Map>().map((dynamic item) => Map<String, dynamic>.from(item as Map)).toList(growable: false);
    }
    throw const GteApiException(type: GteApiErrorType.parsing, message: 'Unexpected manager list response shape.');
  }

  Future<void> _post(String path, {Object? body}) async {
    await _request('POST', path, body: body);
  }

  Future<Object?> _request(String method, String path, {Map<String, Object?> query = const <String, Object?>{}, Object? body, bool auth = true}) async {
    final Map<String, String> headers = <String, String>{'Content-Type': 'application/json'};
    if (auth) {
      headers['Authorization'] = 'Bearer $accessToken';
    }
    final GteTransportResponse response = await transport.send(GteTransportRequest(method: method, uri: config.uriFor(path, query), headers: headers, body: body));
    if (response.statusCode >= 400) {
      throw _toException(response);
    }
    return response.body;
  }

  GteApiException _toException(GteTransportResponse response) {
    final Object? body = response.body;
    String message = 'Manager request failed.';
    if (body is Map<String, dynamic>) {
      message = (body['detail'] ?? body['message'] ?? message).toString();
    } else if (body is String && body.trim().isNotEmpty) {
      message = body;
    }
    return GteApiException(type: _errorType(response.statusCode), message: message, statusCode: response.statusCode);
  }

  GteApiErrorType _errorType(int statusCode) {
    if (statusCode == 401 || statusCode == 403) return GteApiErrorType.unauthorized;
    if (statusCode == 404) return GteApiErrorType.notFound;
    if (statusCode == 422) return GteApiErrorType.validation;
    if (statusCode >= 500) return GteApiErrorType.unavailable;
    return GteApiErrorType.unknown;
  }
}
