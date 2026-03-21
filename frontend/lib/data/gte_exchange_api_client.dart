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

  Future<GteAuthSession> register({
    required String fullName,
    required String phoneNumber,
    required String email,
    required String password,
    required bool isOver18,
    String? username,
  }) {
    return repository.register(
      GteAuthRegisterRequest(
        email: email,
        fullName: fullName,
        phoneNumber: phoneNumber,
        isOver18: isOver18,
        username: username,
        password: password,
      ),
    );
  }

  Future<void> logout() => repository.logout();

  Future<List<GtePolicyDocumentSummary>> fetchPolicyDocuments({
    bool mandatoryOnly = false,
  }) {
    return repository.fetchPolicyDocuments(mandatoryOnly: mandatoryOnly);
  }

  Future<GtePolicyDocumentDetail> fetchPolicyDocument(
    String documentKey, {
    String? versionLabel,
  }) {
    return repository.fetchPolicyDocument(documentKey,
        versionLabel: versionLabel);
  }

  Future<GteComplianceStatus> fetchComplianceStatus() {
    return repository.fetchComplianceStatus();
  }

  Future<List<GtePolicyRequirementSummary>> fetchPolicyRequirements() {
    return repository.fetchPolicyRequirements();
  }

  Future<List<GtePolicyAcceptanceSummary>> fetchMyPolicyAcceptances() {
    return repository.fetchMyPolicyAcceptances();
  }

  Future<GtePolicyAcceptanceSummary> acceptPolicyDocument(
    String documentKey,
    String versionLabel,
  ) {
    return repository.acceptPolicyDocument(documentKey, versionLabel);
  }

  Future<GteWalletOverview> fetchWalletOverview() {
    return repository.fetchWalletOverview();
  }

  Future<GteWithdrawalEligibility> fetchWithdrawalEligibility() {
    return repository.fetchWithdrawalEligibility();
  }

  Future<GteWithdrawalQuote> fetchWithdrawalQuote(
    GteWithdrawalQuoteRequest request,
  ) {
    return repository.fetchWithdrawalQuote(request);
  }

  Future<GteWithdrawalReceipt> fetchWithdrawalReceipt(String withdrawalId) {
    return repository.fetchWithdrawalReceipt(withdrawalId);
  }

  Future<GteDepositRequest> createDepositRequest(
      GteDepositCreateRequest request) {
    return repository.createDepositRequest(request);
  }

  Future<GteDepositRequest> submitDepositRequest(
      String depositId, GteDepositSubmitRequest request) {
    return repository.submitDepositRequest(depositId, request);
  }

  Future<List<GteDepositRequest>> listDepositRequests() {
    return repository.listDepositRequests();
  }

  Future<GteTreasuryWithdrawalRequest> createWithdrawalRequest(
      GteWithdrawalCreateRequest request) {
    return repository.createWithdrawalRequest(request);
  }

  Future<List<GteTreasuryWithdrawalRequest>> listWithdrawalRequests() {
    return repository.listWithdrawalRequests();
  }

  Future<GteKycProfile> fetchKycProfile() {
    return repository.fetchKycProfile();
  }

  Future<GteKycProfile> submitKycProfile(GteKycSubmitRequest request) {
    return repository.submitKycProfile(request);
  }

  Future<List<GteUserBankAccount>> listUserBankAccounts() {
    return repository.listUserBankAccounts();
  }

  Future<GteUserBankAccount> createUserBankAccount(
      GteUserBankAccountCreate request) {
    return repository.createUserBankAccount(request);
  }

  Future<GteUserBankAccount> updateUserBankAccount(
      String bankAccountId, GteUserBankAccountUpdate request) {
    return repository.updateUserBankAccount(bankAccountId, request);
  }

  Future<List<GteDispute>> listDisputes() {
    return repository.listDisputes();
  }

  Future<GteDispute> openDispute(GteDisputeCreateRequest request) {
    return repository.openDispute(request);
  }

  Future<GteDispute> fetchDispute(String disputeId) {
    return repository.fetchDispute(disputeId);
  }

  Future<GteDisputeMessage> sendDisputeMessage(
      String disputeId, GteDisputeMessageRequest request) {
    return repository.sendDisputeMessage(disputeId, request);
  }

  Future<List<GteNotification>> listNotifications({int limit = 20}) {
    return repository.listNotifications(limit: limit);
  }

  Future<void> markNotificationRead(String notificationId) {
    return repository.markNotificationRead(notificationId);
  }

  Future<void> markAllNotificationsRead() {
    return repository.markAllNotificationsRead();
  }

  Future<GteAttachment> uploadAttachment(
    String filename,
    List<int> bytes, {
    String? contentType,
  }) {
    return repository.uploadAttachment(filename, bytes, contentType: contentType);
  }

  Future<GteAnalyticsEvent> trackAnalyticsEvent(
    String name, {
    Map<String, Object?> metadata = const <String, Object?>{},
  }) {
    return repository.trackAnalyticsEvent(name, metadata: metadata);
  }

  Future<GteAnalyticsSummary> fetchAnalyticsSummary() {
    return repository.fetchAnalyticsSummary();
  }

  Future<GteAnalyticsFunnel> fetchAnalyticsFunnel() {
    return repository.fetchAnalyticsFunnel();
  }

  Future<GteTreasuryDashboard> fetchTreasuryDashboard() {
    return repository.fetchTreasuryDashboard();
  }

  Future<GteTreasurySettings> fetchTreasurySettings() {
    return repository.fetchTreasurySettings();
  }

  Future<GteTreasurySettings> updateTreasurySettings(
      GteTreasurySettingsUpdate request) {
    return repository.updateTreasurySettings(request);
  }

  Future<List<GteTreasuryBankAccount>> listTreasuryBankAccounts() {
    return repository.listTreasuryBankAccounts();
  }

  Future<GteTreasuryBankAccount> createTreasuryBankAccount(
      GteTreasuryBankAccountCreate request) {
    return repository.createTreasuryBankAccount(request);
  }

  Future<GteTreasuryBankAccount> updateTreasuryBankAccount(
      String accountId, GteTreasuryBankAccountUpdate request) {
    return repository.updateTreasuryBankAccount(accountId, request);
  }

  Future<GteAdminQueuePage<GteAdminDeposit>> fetchAdminDeposits({
    int limit = 50,
    int offset = 0,
    String? status,
    String? query,
  }) {
    return repository.fetchAdminDeposits(
      limit: limit,
      offset: offset,
      status: status,
      query: query,
    );
  }

  Future<GteDepositRequest> adminConfirmDeposit(String depositId,
      {String? adminNotes}) {
    return repository.adminConfirmDeposit(depositId, adminNotes: adminNotes);
  }

  Future<GteDepositRequest> adminRejectDeposit(String depositId,
      {String? adminNotes}) {
    return repository.adminRejectDeposit(depositId, adminNotes: adminNotes);
  }

  Future<GteDepositRequest> adminReviewDeposit(String depositId,
      {String? adminNotes}) {
    return repository.adminReviewDeposit(depositId, adminNotes: adminNotes);
  }

  Future<GteAdminQueuePage<GteAdminWithdrawal>> fetchAdminWithdrawals({
    int limit = 50,
    int offset = 0,
    String? status,
    String? query,
  }) {
    return repository.fetchAdminWithdrawals(
      limit: limit,
      offset: offset,
      status: status,
      query: query,
    );
  }

  Future<GteTreasuryWithdrawalRequest> adminUpdateWithdrawalStatus(
    String withdrawalId, {
    required GteWithdrawalStatus status,
    String? adminNotes,
  }) {
    return repository.adminUpdateWithdrawalStatus(withdrawalId,
        status: status, adminNotes: adminNotes);
  }

  Future<GteAdminQueuePage<GteAdminKyc>> fetchAdminKyc({
    int limit = 50,
    int offset = 0,
    String? status,
    String? query,
  }) {
    return repository.fetchAdminKyc(
      limit: limit,
      offset: offset,
      status: status,
      query: query,
    );
  }

  Future<GteKycProfile> adminReviewKyc(
      String profileId, GteKycReviewRequest request) {
    return repository.adminReviewKyc(profileId, request);
  }

  Future<GteAdminQueuePage<GteDispute>> fetchAdminDisputes({
    int limit = 50,
    int offset = 0,
    String? status,
    String? query,
  }) {
    return repository.fetchAdminDisputes(
      limit: limit,
      offset: offset,
      status: status,
      query: query,
    );
  }

  Future<GteDispute> fetchAdminDispute(String disputeId) {
    return repository.fetchAdminDispute(disputeId);
  }

  Future<GteDisputeMessage> adminSendDisputeMessage(
      String disputeId, GteDisputeMessageRequest request) {
    return repository.adminSendDisputeMessage(disputeId, request);
  }

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

  Future<Map<String, Object?>> fetchMatchLiveFeed(String matchKey) async {
    return GteJson.map(
      await _sendPublicGet('/api/match-engine/live-feed/$matchKey'),
      label: 'match live feed',
    );
  }

  Future<Map<String, Object?>> fetchMatchHighlights(String matchKey) async {
    return GteJson.map(
      await _sendPublicGet('/api/match-engine/highlights/$matchKey'),
      label: 'match highlights',
    );
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

  Future<GteAdminBuybackPreview> fetchAdminBuybackPreview(String orderId) =>
      repository.fetchAdminBuybackPreview(orderId);

  Future<GteAdminBuybackExecution> executeAdminBuyback(String orderId) =>
      repository.executeAdminBuyback(orderId);

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

  Future<GteWalletLedgerPage> fetchWalletLedger({
    int page = 1,
    int pageSize = 20,
  }) {
    return repository.fetchWalletLedger(page: page, pageSize: pageSize);
  }

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
        scoutingSignalValueCredits: null,
        egameSignalValueCredits: null,
        confidenceScore: null,
        confidenceTier: null,
        trend7dPct: normalizedMovement,
        trend30dPct: null,
        trendDirection: normalizedMovement > 0
            ? 'up'
            : normalizedMovement < 0
                ? 'down'
                : 'flat',
        trendConfidence: null,
        movementTags: const <String>[],
      ),
      trend: GteMarketPlayerTrend(
        trendScore: profile.snapshot.gsi.toDouble(),
        marketInterestScore: profile.snapshot.recentHighlights.length * 10,
        averageRating: profile.snapshot.formRating,
        globalScoutingIndex: profile.snapshot.gsi.toDouble(),
        previousGlobalScoutingIndex: null,
        globalScoutingIndexMovementPct: null,
        drivers: List<String>.from(profile.snapshot.recentHighlights),
        trend7dPct: normalizedMovement,
        trend30dPct: null,
        trendDirection: normalizedMovement > 0
            ? 'up'
            : normalizedMovement < 0
                ? 'down'
                : 'flat',
        trendConfidence: null,
        confidenceTier: null,
        movementTags: const <String>[],
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
