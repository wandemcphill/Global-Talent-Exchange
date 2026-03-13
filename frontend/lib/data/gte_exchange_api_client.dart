import 'gte_api_repository.dart';
import 'gte_exchange_models.dart';
import 'gte_http_transport.dart';
import 'gte_models.dart';
import 'package:gte_frontend/data/gte_mock_api.dart';

class GteExchangeApiClient {
  GteExchangeApiClient({
    required this.config,
    required this.transport,
    required this.repository,
  });

  final GteRepositoryConfig config;
  final GteTransport transport;
  final GteApiRepository repository;

  factory GteExchangeApiClient.standard({
    required String baseUrl,
    GteBackendMode mode = GteBackendMode.liveThenFixture,
  }) {
    final GteRepositoryConfig config =
        GteRepositoryConfig(baseUrl: baseUrl, mode: mode);
    final GteTransport transport = GteHttpTransport();
    final GteApiRepository fixtures = GteMockApi();
    return GteExchangeApiClient(
      config: config,
      transport: transport,
      repository: GteReliableApiRepository(
        config: config,
        transport: transport,
        fixtures: fixtures,
      ),
    );
  }

  factory GteExchangeApiClient.fixture({
    Duration latency = Duration.zero,
  }) {
    final GteRepositoryConfig config = const GteRepositoryConfig(
      baseUrl: 'http://127.0.0.1:8000',
      mode: GteBackendMode.fixture,
    );
    final GteTransport transport = _UnsupportedTransport();
    final GteApiRepository fixtures = GteMockApi(latency: latency);
    return GteExchangeApiClient(
      config: config,
      transport: transport,
      repository: GteReliableApiRepository(
        config: config,
        transport: transport,
        fixtures: fixtures,
      ),
    );
  }

  Future<GteAuthSession> login({
    required String email,
    required String password,
  }) {
    return repository.login(
      GteAuthLoginRequest(
        email: email,
        password: password,
      ),
    );
  }

  Future<void> logout() => repository.logout();

  Future<GteMarketPlayerListView> fetchPlayers({
    GteMarketPlayersQuery query = const GteMarketPlayersQuery(),
  }) async {
    if (config.mode == GteBackendMode.fixture) {
      return _fallbackPlayers(query);
    }

    try {
      return GteMarketPlayerListView.fromJson(
        await _sendPublicGet(
          '/api/market/players',
          query: query.toQueryParameters(),
        ),
      );
    } catch (error) {
      if (_shouldFallback(error)) {
        return _fallbackPlayers(query);
      }
      rethrow;
    }
  }

  Future<GteMarketPlayerDetailView> fetchPlayerDetail(String playerId) async {
    if (config.mode == GteBackendMode.fixture) {
      return _fallbackPlayerDetail(playerId);
    }

    try {
      return GteMarketPlayerDetailView.fromJson(
        await _sendPublicGet('/api/market/players/$playerId'),
      );
    } catch (error) {
      if (_shouldFallback(error)) {
        return _fallbackPlayerDetail(playerId);
      }
      rethrow;
    }
  }

  Future<GtePlayerMarketSnapshot> fetchPlayerMarket(
    String playerId, {
    String interval = '1h',
    int limit = 30,
  }) async {
    final List<dynamic> payload = await Future.wait<dynamic>(<Future<dynamic>>[
      fetchPlayerDetail(playerId),
      repository.fetchTicker(playerId),
      repository.fetchCandles(playerId, interval: interval, limit: limit),
      repository.fetchOrderBook(playerId),
      fetchPlayerLifecycleSnapshot(playerId),
    ]);
    return GtePlayerMarketSnapshot(
      detail: payload[0] as GteMarketPlayerDetailView,
      ticker: payload[1] as GteMarketTicker,
      candles: payload[2] as GteMarketCandles,
      orderBook: payload[3] as GteOrderBook,
      lifecycle: payload[4] as GtePlayerLifecycleSnapshot?,
    );
  }


  Future<GtePlayerLifecycleSnapshot?> fetchPlayerLifecycleSnapshot(String playerId) async {
    if (config.mode == GteBackendMode.fixture) {
      return null;
    }

    try {
      return GtePlayerLifecycleSnapshot.fromJson(
        await _sendPublicGet('/api/players/$playerId/lifecycle-snapshot'),
      );
    } catch (error) {
      if (_shouldFallback(error)) {
        return null;
      }
      rethrow;
    }
  }

  Future<GteMarketCandles> fetchCandles(
    String playerId, {
    String interval = '1h',
    int limit = 30,
  }) {
    return repository.fetchCandles(playerId, interval: interval, limit: limit);
  }

  Future<GteOrderRecord> placeOrder({
    required String playerId,
    required GteOrderSide side,
    required double quantity,
    double? maxPrice,
  }) {
    return repository.placeOrder(
      GteOrderCreateRequest(
        playerId: playerId,
        side: side,
        quantity: quantity,
        maxPrice: maxPrice,
      ),
    );
  }

  Future<GteOrderRecord> fetchOrder(String orderId) =>
      repository.fetchOrder(orderId);

  Future<GteOrderRecord> cancelOrder(String orderId) =>
      repository.cancelOrder(orderId);

  Future<GteOrderListView> listOrders({
    int limit = 20,
    int offset = 0,
    List<GteOrderStatus>? statuses,
  }) {
    return repository.listOrders(
      limit: limit,
      offset: offset,
      statuses: statuses,
    );
  }

  Future<GteWalletSummary> fetchWalletSummary() =>
      repository.fetchWalletSummary();

  Future<GtePortfolioView> fetchPortfolio() => repository.fetchPortfolio();

  Future<GtePortfolioSummary> fetchPortfolioSummary() =>
      repository.fetchPortfolioSummary();

  Future<Object?> _sendPublicGet(
    String path, {
    Map<String, Object?> query = const <String, Object?>{},
  }) async {
    try {
      final GteTransportResponse response = await transport.send(
        GteTransportRequest(
          method: 'GET',
          uri: config.uriFor(path, query),
          headers: const <String, String>{'Accept': 'application/json'},
        ),
      );
      if (response.statusCode >= 400) {
        throw GteApiException(
          type: _errorTypeFromStatus(response.statusCode),
          message: _errorMessage(response.body),
          statusCode: response.statusCode,
          cause: response.body,
        );
      }
      return response.body;
    } on GteApiException {
      rethrow;
    } catch (error) {
      throw GteApiException(
        type: GteApiErrorType.network,
        message: 'Unable to reach the backend.',
        cause: error,
      );
    }
  }

  bool _shouldFallback(Object error) {
    if (config.mode != GteBackendMode.liveThenFixture) {
      return false;
    }
    return (error is GteApiException && error.supportsFixtureFallback) ||
        error is GteParsingException;
  }

  Future<GteMarketPlayerListView> _fallbackPlayers(
      GteMarketPlayersQuery query) async {
    final int minimumWindow = query.offset + query.limit;
    final List<PlayerSnapshot> base = await repository.fetchPlayers(
      limit: minimumWindow > 20 ? minimumWindow : 20,
    );
    final String searchTerm = query.search?.trim().toLowerCase() ?? '';
    final List<PlayerSnapshot> filtered = searchTerm.isEmpty
        ? base
        : base.where((PlayerSnapshot player) {
            final String haystack = <String>[
              player.name,
              player.club,
              player.nation,
              player.position,
            ].join(' ').toLowerCase();
            return haystack.contains(searchTerm);
          }).toList(growable: false);
    final List<PlayerSnapshot> page =
        filtered.skip(query.offset).take(query.limit).toList(
              growable: false,
            );
    return GteMarketPlayerListView(
      items: page.map(_mapSnapshotToListItem).toList(growable: false),
      limit: query.limit,
      offset: query.offset,
      total: filtered.length,
    );
  }

  Future<GteMarketPlayerDetailView> _fallbackPlayerDetail(
      String playerId) async {
    final PlayerProfile profile = await repository.fetchPlayerProfile(playerId);
    final double normalizedMovement =
        _normalizeMovement(profile.snapshot.valueDeltaPct);
    final double previousValue = normalizedMovement.abs() < 0.0001
        ? profile.snapshot.marketCredits.toDouble()
        : profile.snapshot.marketCredits / (1 + normalizedMovement);
    return GteMarketPlayerDetailView(
      playerId: profile.snapshot.id,
      identity: GteMarketPlayerIdentity(
        playerName: profile.snapshot.name,
        firstName: _splitName(profile.snapshot.name, 0),
        lastName: _splitName(profile.snapshot.name, 1),
        shortName: null,
        position: profile.snapshot.position,
        normalizedPosition: profile.snapshot.position.toLowerCase(),
        nationality: profile.snapshot.nation,
        nationalityCode: null,
        age: profile.snapshot.age,
        dateOfBirth: null,
        preferredFoot: null,
        shirtNumber: null,
        heightCm: null,
        weightKg: null,
        currentClubId: null,
        currentClubName: profile.snapshot.club,
        currentCompetitionId: null,
        currentCompetitionName: null,
        imageUrl: null,
      ),
      marketProfile: const GteMarketPlayerMarketProfile(
        isTradable: true,
        marketValueEur: null,
        supplyTier: null,
        liquidityBand: null,
        holderCount: null,
        topHolderSharePct: null,
        top3HolderSharePct: null,
        snapshotMarketPriceCredits: null,
        quotedMarketPriceCredits: null,
        trustedTradePriceCredits: null,
        tradeTrustScore: null,
      ),
      value: GteMarketPlayerValue(
        lastSnapshotId: null,
        lastSnapshotAt: null,
        currentValueCredits: profile.snapshot.marketCredits.toDouble(),
        previousValueCredits: previousValue,
        movementPct: normalizedMovement,
        footballTruthValueCredits: profile.snapshot.marketCredits.toDouble(),
        marketSignalValueCredits: profile.snapshot.marketCredits.toDouble(),
        publishedCardValueCredits: profile.snapshot.marketCredits.toDouble(),
      ),
      trend: GteMarketPlayerTrend(
        trendScore: profile.snapshot.gsi.toDouble(),
        marketInterestScore: profile.snapshot.recentHighlights.length * 10,
        averageRating: profile.snapshot.formRating,
        globalScoutingIndex: profile.snapshot.gsi.toDouble(),
        previousGlobalScoutingIndex: null,
        globalScoutingIndexMovementPct: null,
        drivers: List<String>.from(profile.snapshot.recentHighlights),
      ),
    );
  }

  GteMarketPlayerListItem _mapSnapshotToListItem(PlayerSnapshot player) {
    return GteMarketPlayerListItem(
      playerId: player.id,
      playerName: player.name,
      position: player.position,
      nationality: player.nation,
      currentClubName: player.club,
      age: player.age,
      currentValueCredits: player.marketCredits.toDouble(),
      movementPct: _normalizeMovement(player.valueDeltaPct),
      trendScore: player.gsi.toDouble(),
      marketInterestScore: player.recentHighlights.length * 10,
      averageRating: player.formRating,
    );
  }
}

class _UnsupportedTransport implements GteTransport {
  @override
  Future<GteTransportResponse> send(GteTransportRequest request) {
    throw const GteApiException(
      type: GteApiErrorType.unavailable,
      message: 'Transport is disabled in fixture mode.',
    );
  }
}

String _splitName(String fullName, int index) {
  final List<String> parts = fullName.trim().split(RegExp(r'\s+'));
  if (parts.isEmpty) {
    return '';
  }
  if (index == 0) {
    return parts.first;
  }
  if (parts.length == 1) {
    return parts.first;
  }
  return parts.skip(1).join(' ');
}

double _normalizeMovement(double value) {
  return value.abs() > 1 ? value / 100 : value;
}

GteApiErrorType _errorTypeFromStatus(int statusCode) {
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

String _errorMessage(Object? payload) {
  if (payload is String && payload.trim().isNotEmpty) {
    return payload;
  }
  if (payload is Map) {
    final Object? detail = payload['detail'] ?? payload['message'];
    if (detail is String && detail.trim().isNotEmpty) {
      return detail;
    }
  }
  return 'The backend returned an unexpected response.';
}
