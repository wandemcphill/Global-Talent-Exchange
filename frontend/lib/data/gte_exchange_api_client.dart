import 'dart:convert';

import 'package:gte_frontend/app/test_runtime_detector.dart';
import 'package:gte_frontend/data/gte_mock_api.dart';
import 'package:gte_frontend/models/match_view_state.dart';

import '../shared/auth/auth_identity_store.dart';
import 'gte_api_repository.dart';
import 'gte_exchange_models.dart';
import 'gte_http_transport.dart';
import 'gte_models.dart';
import '../domain/value/gtex_value_models.dart';

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
    GteBackendMode mode = GteBackendMode.live,
    AuthSessionStore? authSessionStore,
  }) {
    final GteRepositoryConfig config = GteRepositoryConfig(
      baseUrl: baseUrl,
      mode: mode,
    );
    final GteTransport transport = GteHttpTransport();
    return GteExchangeApiClient(
      config: config,
      transport: transport,
      repository: GteModeAwareApiRepository(
        config: config,
        transport: transport,
        fixtures: const GteFixtureRepositoryUnavailable(),
        authSessionStore: authSessionStore ?? SecureAuthSessionStore(),
      ),
    );
  }

  factory GteExchangeApiClient.fixture({Duration latency = Duration.zero}) {
    assertFixtureFactoryAllowed('GteExchangeApiClient.fixture');
    final GteRepositoryConfig config = const GteRepositoryConfig(
      baseUrl: 'http://127.0.0.1:8000',
      mode: GteBackendMode.fixture,
    );
    final GteTransport transport = _UnsupportedTransport();
    final GteApiRepository fixtures = GteMockApi(latency: latency);
    return GteExchangeApiClient(
      config: config,
      transport: transport,
      repository: GteModeAwareApiRepository(
        config: config,
        transport: transport,
        fixtures: fixtures,
        authSessionStore: MemoryAuthSessionStore(),
      ),
    );
  }

  Future<GteAuthSession> login({
    required String email,
    required String password,
  }) {
    return repository.login(
      GteAuthLoginRequest(email: email, password: password),
    );
  }

  Future<GteAuthSession> register({
    required String fullName,
    required String phoneNumber,
    required String email,
    required String password,
    required bool isOver18,
    required String regionCode,
    String? username,
  }) {
    return repository.register(
      GteAuthRegisterRequest(
        email: email,
        fullName: fullName,
        phoneNumber: phoneNumber,
        isOver18: isOver18,
        regionCode: regionCode,
        username: username,
        password: password,
      ),
    );
  }

  Future<GteAuthSession> signupUser(GteUserSignupRequest request) {
    return repository.signupUser(request);
  }

  Future<GteAuthSession> signupCreator(GteCreatorSignupRequest request) {
    return repository.signupCreator(request);
  }

  Future<GteAuthSession> signupTrader(GteTraderSignupRequest request) {
    return repository.signupTrader(request);
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
    return repository.fetchPolicyDocument(
      documentKey,
      versionLabel: versionLabel,
    );
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
    GteDepositCreateRequest request,
  ) {
    return repository.createDepositRequest(request);
  }

  Future<GteDepositRequest> submitDepositRequest(
    String depositId,
    GteDepositSubmitRequest request,
  ) {
    return repository.submitDepositRequest(depositId, request);
  }

  Future<List<GteDepositRequest>> listDepositRequests() {
    return repository.listDepositRequests();
  }

  Future<GteTreasuryWithdrawalRequest> createWithdrawalRequest(
    GteWithdrawalCreateRequest request,
  ) {
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

  Future<GteKycProfile> submitKycDocuments(
    GteKycDocumentSubmission submission,
  ) {
    return repository.submitKycDocuments(submission);
  }

  Future<List<GteUserBankAccount>> listUserBankAccounts() {
    return repository.listUserBankAccounts();
  }

  Future<GteUserBankAccount> createUserBankAccount(
    GteUserBankAccountCreate request,
  ) {
    return repository.createUserBankAccount(request);
  }

  Future<GteUserBankAccount> updateUserBankAccount(
    String bankAccountId,
    GteUserBankAccountUpdate request,
  ) {
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
    String disputeId,
    GteDisputeMessageRequest request,
  ) {
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
    return repository.uploadAttachment(
      filename,
      bytes,
      contentType: contentType,
    );
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
    GteTreasurySettingsUpdate request,
  ) {
    return repository.updateTreasurySettings(request);
  }

  Future<List<GteTreasuryBankAccount>> listTreasuryBankAccounts() {
    return repository.listTreasuryBankAccounts();
  }

  Future<GteTreasuryBankAccount> createTreasuryBankAccount(
    GteTreasuryBankAccountCreate request,
  ) {
    return repository.createTreasuryBankAccount(request);
  }

  Future<GteTreasuryBankAccount> updateTreasuryBankAccount(
    String accountId,
    GteTreasuryBankAccountUpdate request,
  ) {
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

  Future<GteDepositRequest> adminConfirmDeposit(
    String depositId, {
    String? adminNotes,
  }) {
    return repository.adminConfirmDeposit(depositId, adminNotes: adminNotes);
  }

  Future<GteDepositRequest> adminRejectDeposit(
    String depositId, {
    String? adminNotes,
  }) {
    return repository.adminRejectDeposit(depositId, adminNotes: adminNotes);
  }

  Future<GteDepositRequest> adminReviewDeposit(
    String depositId, {
    String? adminNotes,
  }) {
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
    return repository.adminUpdateWithdrawalStatus(
      withdrawalId,
      status: status,
      adminNotes: adminNotes,
    );
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
    String profileId,
    GteKycReviewRequest request,
  ) {
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
    String disputeId,
    GteDisputeMessageRequest request,
  ) {
    return repository.adminSendDisputeMessage(disputeId, request);
  }

  Future<GteMarketPlayerListView> fetchPlayers({
    GteMarketPlayersQuery query = const GteMarketPlayersQuery(),
  }) async {
    return _loadPublicWithFallback<GteMarketPlayerListView>(
      liveCall:
          () async => GteMarketPlayerListView.fromJson(
            await _sendPublicGet(
              '/api/market/players',
              query: query.toQueryParameters(),
            ),
          ),
      fallbackCall: () => _fallbackPlayers(query),
    );
  }

  Future<GteMarketBrowseCatalog> fetchMarketBrowseCatalog() async {
    return _loadPublicWithFallback<GteMarketBrowseCatalog>(
      liveCall:
          () async => GteMarketBrowseCatalog.fromJson(
            await _sendPublicGet('/api/market/browse/catalog'),
          ),
      fallbackCall: _fallbackMarketBrowseCatalog,
    );
  }

  Future<List<GteMarketLeagueBrowseItem>> fetchMarketLeagues() async {
    return _loadPublicWithFallback<List<GteMarketLeagueBrowseItem>>(
      liveCall:
          () async => GteJson.list(
            await _sendPublicGet('/api/market/leagues'),
            label: 'market leagues',
          ).map(GteMarketLeagueBrowseItem.fromJson).toList(growable: false),
      fallbackCall: _fallbackMarketLeagues,
    );
  }

  Future<List<GteMarketClubBrowseItem>> fetchMarketLeagueClubs(
    String leagueId,
  ) async {
    return _loadPublicWithFallback<List<GteMarketClubBrowseItem>>(
      liveCall:
          () async => GteJson.list(
            await _sendPublicGet('/api/market/leagues/$leagueId/clubs'),
            label: 'market league clubs',
          ).map(GteMarketClubBrowseItem.fromJson).toList(growable: false),
      fallbackCall: () => _fallbackMarketClubs(leagueId),
    );
  }

  Future<GteMarketPlayerListView> fetchMarketClubPlayers(
    String clubId, {
    int limit = 100,
  }) async {
    return _loadPublicWithFallback<GteMarketPlayerListView>(
      liveCall:
          () async => GteMarketPlayerListView.fromJson(
            await _sendPublicGet(
              '/api/market/clubs/$clubId/players',
              query: <String, Object?>{'limit': limit},
            ),
          ),
      fallbackCall:
          () => _fallbackPlayers(
            GteMarketPlayersQuery(limit: limit, club: clubId),
          ),
    );
  }

  Future<List<GteMarketNationalityBrowseItem>>
  fetchMarketNationalities() async {
    return _loadPublicWithFallback<List<GteMarketNationalityBrowseItem>>(
      liveCall:
          () async => GteJson.list(
                await _sendPublicGet('/api/market/nationalities'),
                label: 'market nationalities',
              )
              .map(GteMarketNationalityBrowseItem.fromJson)
              .toList(growable: false),
      fallbackCall: _fallbackMarketNationalities,
    );
  }

  Future<GteMarketPlayerListView> fetchMarketNationalityPlayers(
    String countryCode, {
    int limit = 100,
  }) async {
    return _loadPublicWithFallback<GteMarketPlayerListView>(
      liveCall:
          () async => GteMarketPlayerListView.fromJson(
            await _sendPublicGet(
              '/api/market/nationalities/$countryCode/players',
              query: <String, Object?>{'limit': limit},
            ),
          ),
      fallbackCall:
          () => _fallbackPlayers(
            GteMarketPlayersQuery(limit: limit, country: countryCode),
          ),
    );
  }

  Future<List<GteMarketNationalityBrowseItem>>
  fetchMarketNationalTeams() async {
    return _loadPublicWithFallback<List<GteMarketNationalityBrowseItem>>(
      liveCall:
          () async => GteJson.list(
                await _sendPublicGet('/api/market/national-teams'),
                label: 'market national teams',
              )
              .map(GteMarketNationalityBrowseItem.fromJson)
              .toList(growable: false),
      fallbackCall: _fallbackMarketNationalities,
    );
  }

  Future<GteMarketPlayerListView> fetchMarketNationalTeamEligiblePlayers(
    String teamId, {
    int limit = 100,
  }) async {
    return _loadPublicWithFallback<GteMarketPlayerListView>(
      liveCall:
          () async => GteMarketPlayerListView.fromJson(
            await _sendPublicGet(
              '/api/market/national-teams/$teamId/eligible-players',
              query: <String, Object?>{'limit': limit},
            ),
          ),
      fallbackCall:
          () => _fallbackPlayers(
            GteMarketPlayersQuery(limit: limit, nationalTeam: teamId),
          ),
    );
  }

  Future<GteMarketPlayerDetailView> fetchPlayerDetail(String playerId) async {
    return _loadPublicWithFallback<GteMarketPlayerDetailView>(
      liveCall:
          () async => GteMarketPlayerDetailView.fromJson(
            await _sendPublicGet('/api/market/players/$playerId'),
          ),
      fallbackCall: () => _fallbackPlayerDetail(playerId),
    );
  }

  /// A footballer's recent GTEX competition form and its bounded valuation effect.
  ///
  /// In fixture mode this yields the honest empty form. In live mode a transport
  /// or contract failure *propagates* — `_loadPublicWithFallback` only substitutes
  /// the fallback for fixtures — and the caller is responsible for degrading
  /// gracefully. `GtexFmPlayerProfileScreen._loadForm` does exactly that, showing
  /// "no GTEX competition football yet" rather than inventing flat form.
  ///
  /// The payload is copied rather than cast. A hard `as Map<String, dynamic>`
  /// works only because `jsonDecode` happens to produce that exact type; any
  /// other well-formed map (a stub transport, a cached decode, a future change of
  /// transport) would throw a `CastError` that surfaces as a bogus "network"
  /// failure.
  Future<GtexPlayerForm> fetchPlayerForm(String playerId) async {
    return _loadPublicWithFallback<GtexPlayerForm>(
      liveCall: () async {
        final Object? payload = await _sendPublicGet(
          '/api/players/$playerId/form',
        );
        if (payload is! Map) {
          return GtexPlayerForm.unknown(playerId);
        }
        return GtexPlayerForm.fromJson(Map<String, dynamic>.from(payload));
      },
      fallbackCall: () async => GtexPlayerForm.unknown(playerId),
    );
  }

  Future<GtePlayerOverview> fetchPlayerOverview(String playerId) async {
    return _loadPublicWithFallback<GtePlayerOverview>(
      liveCall:
          () async => GtePlayerOverview.fromJson(
            await _sendPublicGet('/api/players/$playerId/overview'),
          ),
      fallbackCall: () => _fallbackPlayerOverview(playerId),
    );
  }

  Future<List<GteCareerEntry>> fetchPlayerCareer(String playerId) async {
    return _loadPublicWithFallback<List<GteCareerEntry>>(
      liveCall: () async {
        final Object? raw = await _sendPublicGet(
          '/api/players/$playerId/career',
        );
        return GteJson.list(
          raw,
          label: 'player career',
        ).map(GteCareerEntry.fromJson).toList(growable: false);
      },
      fallbackCall: () => _fallbackPlayerCareer(playerId),
    );
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
      fetchPlayerOverview(playerId),
      fetchPlayerCareer(playerId),
    ]);
    final GtePlayerOverview overview = payload[4] as GtePlayerOverview;
    return GtePlayerMarketSnapshot(
      detail: payload[0] as GteMarketPlayerDetailView,
      ticker: payload[1] as GteMarketTicker,
      candles: payload[2] as GteMarketCandles,
      orderBook: payload[3] as GteOrderBook,
      overview: overview,
      careerEntries: payload[5] as List<GteCareerEntry>,
      lifecycle: GtePlayerLifecycleSnapshot.fromOverview(overview),
    );
  }

  Future<GtePlayerLifecycleSnapshot?> fetchPlayerLifecycleSnapshot(
    String playerId,
  ) async {
    return _loadPublicWithFallback<GtePlayerLifecycleSnapshot?>(
      liveCall:
          () async => GtePlayerLifecycleSnapshot.fromJson(
            await _sendPublicGet('/api/players/$playerId/lifecycle-snapshot'),
          ),
      fallbackCall: () async {
        final GtePlayerOverview overview = await _fallbackPlayerOverview(
          playerId,
        );
        return GtePlayerLifecycleSnapshot.fromOverview(overview);
      },
    );
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

  Future<Map<String, Object?>> fetchMatchAnalytics(String matchKey) async {
    return GteJson.map(
      await _sendPublicGet('/api/match-engine/analytics/$matchKey'),
      label: 'match analytics',
    );
  }

  Future<Map<String, Object?>> fetchMatchViewer(
    String matchKey, {
    MatchMode mode = MatchMode.standard,
  }) async {
    return GteJson.map(
      await _sendPublicGet(
        '/api/match-viewer/$matchKey',
        query: <String, Object?>{'mode': mode.apiValue},
      ),
      label: 'match viewer',
    );
  }

  Future<Map<String, Object?>> fetchMatchViewerSession(
    String matchKey, {
    MatchMode mode = MatchMode.standard,
    String? continuationToken,
  }) async {
    return GteJson.map(
      await _sendPublicGet(
        '/api/match-viewer/$matchKey/session',
        query: <String, Object?>{
          'mode': mode.apiValue,
          if (continuationToken != null && continuationToken.isNotEmpty)
            'token': continuationToken,
        },
      ),
      label: 'match viewer session',
    );
  }

  Future<Map<String, Object?>> joinMatchSpectateSession(
    String matchKey, {
    bool payToView = false,
  }) async {
    if (config.mode == GteBackendMode.fixture) {
      return _fixtureSpectateSession(matchKey);
    }
    final GteApiRepository resolvedRepository = repository;
    if (resolvedRepository is! GteModeAwareApiRepository) {
      throw const GteApiException(
        type: GteApiErrorType.unavailable,
        message:
            'Live match spectate sessions require the backend-connected repository.',
      );
    }
    return resolvedRepository.requestJson(
      'POST',
      '/api/matches/$matchKey/spectate',
      query: <String, Object?>{'pay_to_view': payToView},
      requiresAuth: true,
    );
  }

  Future<Map<String, Object?>> fetchMatchReplay(String matchKey) async {
    return GteJson.map(
      await _sendPublicGet('/api/matches/$matchKey/replay'),
      label: 'match replay',
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

  Future<GteWalletSummary> fetchWalletSummary({
    GteLedgerUnit currency = GteLedgerUnit.coin,
  }) => repository.fetchWalletSummary(currency: currency);

  Future<GteUserWallet> fetchWallet() => repository.fetchWallet();

  Future<GteWalletLedgerPage> fetchWalletLedger({
    int page = 1,
    int pageSize = 20,
  }) {
    return repository.fetchWalletLedger(page: page, pageSize: pageSize);
  }

  Future<List<GteWalletTransactionRecord>> listWalletTransactions({
    int limit = 50,
  }) {
    return repository.listWalletTransactions(limit: limit);
  }

  Future<GteWalletTopUpSession> initiateWalletTopUp(
    GteWalletTopUpInitiateRequest request,
  ) {
    return repository.initiateWalletTopUp(request);
  }

  Future<GteWalletTopUpVerificationResult> verifyWalletTopUp(String reference) {
    return repository.verifyWalletTopUp(reference);
  }

  Future<GteWalletConversionQuote> quoteWalletConversion(
    GteWalletConversionQuoteRequest request,
  ) {
    return repository.quoteWalletConversion(request);
  }

  Future<GteWalletConversion> createWalletConversion(
    GteWalletConversionRequest request,
  ) {
    return repository.createWalletConversion(request);
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
      return gteApiSuccessPayload(response.body);
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

  Future<T> _loadPublicWithFallback<T>({
    required Future<T> Function() liveCall,
    required Future<T> Function() fallbackCall,
  }) async {
    if (config.mode == GteBackendMode.fixture) {
      return fallbackCall();
    }
    return liveCall();
  }

  Map<String, Object?> _fixtureSpectateSession(String matchKey) {
    return <String, Object?>{
      'id': 'fixture-spectator-$matchKey',
      'match_id': matchKey,
      'user_id': 'fixture-user',
      'joined_at': DateTime.now().toUtc().toIso8601String(),
      'read_only': true,
      'channel': 'match:$matchKey:events',
      'websocket_path':
          '/api/matches/$matchKey/stream?session_id=fixture-spectator-$matchKey',
      'commentary_websocket_path':
          '/api/matches/$matchKey/commentary/stream?session_id=fixture-spectator-$matchKey',
      'presence_channel': 'match:$matchKey:events',
      'presence_websocket_path': '/ws/spectate/$matchKey',
      'tts_websocket_path': '/tts/live?voice=default',
      'replay_route': '/api/matches/$matchKey/replay',
      'speed_modes': const <Map<String, Object?>>[
        <String, Object?>{
          'key': 'normal',
          'label': 'Normal',
          'target_duration_seconds': 90,
        },
        <String, Object?>{
          'key': 'fast',
          'label': 'Fast',
          'target_duration_seconds': 30,
        },
        <String, Object?>{
          'key': 'turbo',
          'label': 'Turbo',
          'target_duration_seconds': 10,
        },
      ],
      'sync_strategy': 'deterministic_playback',
      'watch_party_enabled': true,
      'reactions_enabled': true,
      'premium_features': const <String, Object?>{},
      'sponsored_overlays': const <Object?>[],
      'stadium_ads': const <Object?>[],
    };
  }

  Future<GteMarketPlayerListView> _fallbackPlayers(
    GteMarketPlayersQuery query,
  ) async {
    final int startOffset = _fallbackCursorOffset(query);
    final int minimumWindow = startOffset + query.limit;
    final List<PlayerSnapshot> base = await repository.fetchPlayers(
      limit: minimumWindow > 20 ? minimumWindow : 20,
    );
    final String searchTerm = query.search?.trim().toLowerCase() ?? '';
    final String? position = query.position?.trim().toLowerCase();
    final String? country = query.country?.trim().toLowerCase();
    final String? nationalTeam = query.nationalTeam?.trim().toLowerCase();
    final String? club = query.club?.trim().toLowerCase();
    final String? availability = query.availability?.trim().toLowerCase();
    final List<PlayerSnapshot> filtered = base
        .where((PlayerSnapshot player) {
          if (searchTerm.isNotEmpty) {
            final String haystack =
                <String>[
                  player.name,
                  player.club,
                  player.nation,
                  player.position,
                ].join(' ').toLowerCase();
            if (!haystack.contains(searchTerm)) {
              return false;
            }
          }
          if (position != null &&
              !player.position.toLowerCase().contains(position)) {
            return false;
          }
          if (country != null &&
              !player.nation.toLowerCase().contains(country)) {
            return false;
          }
          if (nationalTeam != null &&
              !player.nation.toLowerCase().contains(nationalTeam)) {
            return false;
          }
          if (club != null && !player.club.toLowerCase().contains(club)) {
            return false;
          }
          if (query.minAge != null && player.age < query.minAge!) {
            return false;
          }
          if (query.maxAge != null && player.age > query.maxAge!) {
            return false;
          }
          if (availability == 'free_agent' &&
              player.club.trim().toLowerCase() != 'free agent') {
            return false;
          }
          return true;
        })
        .toList(growable: false);
    final List<PlayerSnapshot> page = filtered
        .skip(startOffset)
        .take(query.limit)
        .toList(growable: false);
    final bool hasMore = startOffset + page.length < filtered.length;
    return GteMarketPlayerListView(
      items: page.map(_mapSnapshotToListItem).toList(growable: false),
      limit: query.limit,
      hasMore: hasMore,
      nextCursor:
          hasMore ? _encodeFallbackCursor(startOffset + page.length) : null,
      offset: startOffset,
      total: filtered.length,
    );
  }

  Future<GteMarketPlayerDetailView> _fallbackPlayerDetail(
    String playerId,
  ) async {
    final PlayerProfile profile = await repository.fetchPlayerProfile(playerId);
    final double normalizedMovement = _normalizeMovement(
      profile.snapshot.valueDeltaPct,
    );
    final double previousValue =
        normalizedMovement.abs() < 0.0001
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
        trendDirection:
            normalizedMovement > 0
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
        trendDirection:
            normalizedMovement > 0
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

  Future<List<GteMarketLeagueBrowseItem>> _fallbackMarketLeagues() async {
    final GteMarketPlayerListView players = await _fallbackPlayers(
      const GteMarketPlayersQuery(limit: 100),
    );
    final Map<String, ({String name, Set<String> clubs, int players})> grouped =
        <String, ({String name, Set<String> clubs, int players})>{};
    for (final GteMarketPlayerListItem player in players.items) {
      const String leagueId = 'fixture-global-league';
      final String club = player.currentClubName?.trim() ?? 'Independent';
      final current = grouped[leagueId];
      if (current == null) {
        grouped[leagueId] = (
          name: 'Global Exchange League',
          clubs: <String>{club},
          players: 1,
        );
      } else {
        grouped[leagueId] = (
          name: current.name,
          clubs: <String>{...current.clubs, club},
          players: current.players + 1,
        );
      }
    }
    return grouped.entries
        .map(
          (entry) => GteMarketLeagueBrowseItem(
            leagueId: entry.key,
            slug: entry.key,
            displayName: entry.value.name,
            playerCount: entry.value.players,
            clubCount: entry.value.clubs.length,
          ),
        )
        .toList(growable: false);
  }

  Future<GteMarketBrowseCatalog> _fallbackMarketBrowseCatalog() async {
    final GteMarketPlayerListView players = await _fallbackPlayers(
      const GteMarketPlayersQuery(limit: 500),
    );
    return GteMarketBrowseCatalog(
      total: players.total,
      countries: _fallbackBrowseOptions(
        players.items.map(
          (GteMarketPlayerListItem player) =>
              _BrowseSeed(player.nationality ?? 'Global', player.nationality),
        ),
      ),
      leagues: _fallbackBrowseOptions(
        players.items.map(
          (GteMarketPlayerListItem player) => _BrowseSeed(
            player.currentCompetitionName ?? 'Global Exchange League',
            player.currentCompetitionName,
          ),
        ),
      ),
      divisions: _fallbackBrowseOptions(
        players.items.map(
          (GteMarketPlayerListItem player) => _BrowseSeed(
            player.currentDivisionName ?? 'Division 1',
            player.currentDivisionName,
          ),
        ),
      ),
      clubs: _fallbackBrowseOptions(
        players.items.map(
          (GteMarketPlayerListItem player) => _BrowseSeed(
            player.currentClubName ?? 'Independent',
            player.currentClubName,
          ),
        ),
      ),
    );
  }

  List<GteMarketBrowseOption> _fallbackBrowseOptions(
    Iterable<_BrowseSeed> seeds,
  ) {
    final Map<String, int> counts = <String, int>{};
    final Map<String, String> labels = <String, String>{};
    for (final _BrowseSeed seed in seeds) {
      final String label = seed.label.trim();
      if (label.isEmpty) {
        continue;
      }
      final String id =
          seed.id?.trim().isNotEmpty == true ? seed.id!.trim() : label;
      labels[id] = label;
      counts[id] = (counts[id] ?? 0) + 1;
    }
    final List<MapEntry<String, int>> entries =
        counts.entries.toList()
          ..sort((MapEntry<String, int> left, MapEntry<String, int> right) {
            final int byCount = right.value.compareTo(left.value);
            if (byCount != 0) {
              return byCount;
            }
            return (labels[left.key] ?? left.key).compareTo(
              labels[right.key] ?? right.key,
            );
          });
    return entries
        .map(
          (MapEntry<String, int> entry) => GteMarketBrowseOption(
            id: entry.key,
            label: labels[entry.key] ?? entry.key,
            count: entry.value,
          ),
        )
        .toList(growable: false);
  }

  Future<List<GteMarketClubBrowseItem>> _fallbackMarketClubs(
    String leagueId,
  ) async {
    final GteMarketPlayerListView players = await _fallbackPlayers(
      const GteMarketPlayersQuery(limit: 100),
    );
    final Map<String, int> counts = <String, int>{};
    for (final GteMarketPlayerListItem player in players.items) {
      final String name = player.currentClubName?.trim() ?? 'Independent';
      counts[name] = (counts[name] ?? 0) + 1;
    }
    return counts.entries
        .map(
          (entry) => GteMarketClubBrowseItem(
            clubId: entry.key,
            slug: _fixtureSlug(entry.key),
            displayName: entry.key,
            playerCount: entry.value,
          ),
        )
        .toList(growable: false);
  }

  Future<List<GteMarketNationalityBrowseItem>>
  _fallbackMarketNationalities() async {
    final GteMarketPlayerListView players = await _fallbackPlayers(
      const GteMarketPlayersQuery(limit: 100),
    );
    final Map<String, int> counts = <String, int>{};
    for (final GteMarketPlayerListItem player in players.items) {
      final String name = player.nationality?.trim() ?? 'Global';
      counts[name] = (counts[name] ?? 0) + 1;
    }
    return counts.entries
        .map(
          (entry) => GteMarketNationalityBrowseItem(
            countryCode: entry.key,
            slug: _fixtureSlug(entry.key),
            displayName: entry.key,
            eligiblePlayerCount: entry.value,
          ),
        )
        .toList(growable: false);
  }

  String _fixtureSlug(String value) {
    final String normalized = value.trim().toLowerCase();
    if (normalized.isEmpty) {
      return 'fixture';
    }
    return normalized.replaceAll(RegExp(r'[^a-z0-9]+'), '-');
  }

  Future<GtePlayerOverview> _fallbackPlayerOverview(String playerId) async {
    final PlayerProfile profile = await repository.fetchPlayerProfile(playerId);
    final PlayerSnapshot snapshot = profile.snapshot;
    final DateTime now = DateTime.now().toUtc();
    final DateTime generatedOn = DateTime.utc(now.year, now.month, now.day);
    final GteCareerTotals totals = _fallbackCareerTotals(snapshot);
    final List<GteSeasonProgression> seasonalProgression =
        _fallbackSeasonalProgression(snapshot, totals);
    final bool freeAgent = snapshot.club.trim().toLowerCase() == 'free agent';
    final String transferSignal = _fixtureTransferSignal(snapshot);
    final List<GteLifecycleEventItem> events = snapshot.recentHighlights
        .take(3)
        .toList(growable: false)
        .asMap()
        .entries
        .map((MapEntry<int, String> entry) {
          return GteLifecycleEventItem(
            eventType: 'market_signal',
            summary: entry.value,
            occurredOn: generatedOn.subtract(Duration(days: entry.key)),
          );
        })
        .toList(growable: false);

    return GtePlayerOverview(
      playerId: snapshot.id,
      playerName: snapshot.name,
      position: snapshot.position,
      marketValueEur: null,
      overviewGeneratedOn: generatedOn,
      careerSummary: GtePlayerCareerSummary(
        playerId: snapshot.id,
        playerName: snapshot.name,
        currentClubId: null,
        currentClubName: freeAgent ? null : snapshot.club,
        currentCompetitionId: null,
        currentCompetitionName: null,
        totals: totals,
        seasonalProgression: seasonalProgression,
      ),
      availabilityBadge: const GteLifecycleBadgeView(
        status: 'available',
        label: 'Available',
        available: true,
      ),
      contractBadge: GteContractBadgeView(
        status: freeAgent ? 'free_agent' : 'active',
        label: freeAgent ? 'Free agent' : 'Under contract',
        clubName: freeAgent ? null : snapshot.club,
        endsOn: freeAgent ? null : DateTime.utc(now.year + 1, 6, 30),
      ),
      transferStatus: GteTransferStatusView(
        windowOpen: true,
        eligible: true,
        reason: transferSignal.isEmpty ? null : transferSignal,
        windowLabel: 'Open market',
        lastBidStatus: snapshot.inTransferRoom ? 'active' : null,
      ),
      agencySummary: null,
      recentEvents: events,
    );
  }

  Future<List<GteCareerEntry>> _fallbackPlayerCareer(String playerId) async {
    final PlayerProfile profile = await repository.fetchPlayerProfile(playerId);
    final PlayerSnapshot snapshot = profile.snapshot;
    final GteCareerTotals totals = _fallbackCareerTotals(snapshot);
    final List<GteSeasonProgression> progression = _fallbackSeasonalProgression(
      snapshot,
      totals,
    );
    final DateTime now = DateTime.now().toUtc();
    final List<GteCareerEntry> entries = progression.reversed
        .toList(growable: false)
        .asMap()
        .entries
        .map((MapEntry<int, GteSeasonProgression> entry) {
          final GteSeasonProgression season = entry.value;
          final String clubName =
              season.clubName ??
              (snapshot.club.trim().isEmpty ? 'Independent' : snapshot.club);
          return GteCareerEntry(
            id: '${snapshot.id}-${season.seasonLabel}',
            playerId: snapshot.id,
            clubId: season.clubId,
            clubName: clubName,
            seasonLabel: season.seasonLabel,
            squadRole: entry.key == 0 ? 'Breakthrough' : 'First team',
            appearances: season.appearances,
            goals: season.goals,
            assists: season.assists,
            averageRating: season.averageRating?.round(),
            notes:
                snapshot.recentHighlights.isEmpty
                    ? null
                    : snapshot.recentHighlights[entry.key %
                        snapshot.recentHighlights.length],
            startOn: DateTime.utc(now.year - (2 - entry.key), 7, 1),
            endOn: DateTime.utc(now.year - (1 - entry.key), 6, 30),
            updatedAt: now,
          );
        })
        .toList(growable: false);
    entries.sort(
      (GteCareerEntry left, GteCareerEntry right) =>
          right.timelineAnchor.compareTo(left.timelineAnchor),
    );
    return entries;
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
      globalScoutingIndex: player.gsi.toDouble(),
      isAvailable: true,
      availabilityLabel: 'Available now',
      askingType: player.inTransferRoom ? 'transfer' : 'trial',
      agentUserId: 'fixture-agent-${player.id}',
      agentName: '${player.club} representation',
      marketplaceNote:
          player.recentHighlights.isEmpty
              ? null
              : player.recentHighlights.first,
    );
  }

  String _fixtureTransferSignal(PlayerSnapshot snapshot) {
    if (snapshot.club.trim().toLowerCase() == 'free agent') {
      return 'Available immediately as a free agent in fixture mode.';
    }
    if (snapshot.inTransferRoom) {
      return 'Transfer room interest is active in fixture mode.';
    }
    return 'Fixture market snapshot generated from seeded player data.';
  }

  GteCareerTotals _fallbackCareerTotals(PlayerSnapshot snapshot) {
    final String position = snapshot.position.trim().toUpperCase();
    final int appearances =
        (24 + (snapshot.gsi / 5).round() + (snapshot.age % 6))
            .clamp(18, 48)
            .toInt();
    final int starts =
        (appearances * (0.72 + (snapshot.formRating / 25)))
            .round()
            .clamp(12, appearances)
            .toInt();
    final int minutes =
        (starts * (position == 'GK' ? 90 : 79)).clamp(1200, 4320).toInt();
    if (_isGoalkeeper(position)) {
      return GteCareerTotals(
        appearances: appearances,
        starts: starts,
        goals: 0,
        assists: 0,
        cleanSheets: (starts * 0.38).round(),
        saves: starts * 3,
        minutes: minutes,
      );
    }
    if (_isDefender(position)) {
      return GteCareerTotals(
        appearances: appearances,
        starts: starts,
        goals: (snapshot.formRating / 2.2).round().clamp(1, 7).toInt(),
        assists: (snapshot.formRating / 1.8).round().clamp(2, 9).toInt(),
        cleanSheets: (starts * 0.34).round(),
        saves: 0,
        minutes: minutes,
      );
    }
    if (_isMidfielder(position)) {
      return GteCareerTotals(
        appearances: appearances,
        starts: starts,
        goals: (snapshot.formRating * 1.6).round().clamp(4, 18).toInt(),
        assists: (snapshot.formRating * 1.4).round().clamp(4, 16).toInt(),
        cleanSheets: 0,
        saves: 0,
        minutes: minutes,
      );
    }
    return GteCareerTotals(
      appearances: appearances,
      starts: starts,
      goals: (snapshot.formRating * 2.2).round().clamp(8, 28).toInt(),
      assists: (snapshot.formRating * 1.1).round().clamp(3, 14).toInt(),
      cleanSheets: 0,
      saves: 0,
      minutes: minutes,
    );
  }

  List<GteSeasonProgression> _fallbackSeasonalProgression(
    PlayerSnapshot snapshot,
    GteCareerTotals totals,
  ) {
    final DateTime now = DateTime.now().toUtc();
    const List<double> weights = <double>[0.24, 0.33, 0.43];
    final List<int> appearances = _distributeTotal(totals.appearances, weights);
    final List<int> starts = _distributeTotal(totals.starts, weights);
    final List<int> goals = _distributeTotal(totals.goals, weights);
    final List<int> assists = _distributeTotal(totals.assists, weights);
    final List<int> cleanSheets = _distributeTotal(totals.cleanSheets, weights);
    final List<int> saves = _distributeTotal(totals.saves, weights);
    final List<int> minutes = _distributeTotal(totals.minutes, weights);
    return List<GteSeasonProgression>.generate(3, (int index) {
      final int startYear = now.year - (2 - index);
      return GteSeasonProgression(
        seasonLabel: '$startYear/${(startYear + 1).toString().substring(2)}',
        competitionId: null,
        competitionName: null,
        clubId: null,
        clubName: snapshot.club.trim().isEmpty ? 'Independent' : snapshot.club,
        appearances: appearances[index],
        starts: starts[index],
        goals: goals[index],
        assists: assists[index],
        cleanSheets: cleanSheets[index],
        saves: saves[index],
        minutes: minutes[index],
        averageRating:
            (snapshot.formRating - (0.4 - (index * 0.2)))
                .clamp(6.4, 9.2)
                .toDouble(),
      );
    }).reversed.toList(growable: false);
  }

  List<int> _distributeTotal(int total, List<double> weights) {
    if (total <= 0) {
      return List<int>.filled(weights.length, 0, growable: false);
    }
    final List<int> values =
        weights.map((double weight) => (total * weight).floor()).toList();
    int assigned = values.fold<int>(0, (int sum, int value) => sum + value);
    int cursor = values.length - 1;
    while (assigned < total) {
      values[cursor] += 1;
      assigned += 1;
      cursor = cursor == 0 ? values.length - 1 : cursor - 1;
    }
    return values;
  }

  int _fallbackCursorOffset(GteMarketPlayersQuery query) {
    final String? rawCursor = query.cursor?.trim();
    if (rawCursor == null || rawCursor.isEmpty) {
      return query.offset < 0 ? 0 : query.offset;
    }
    try {
      final Map<String, dynamic> payload =
          jsonDecode(
                utf8.decode(base64Url.decode(base64Url.normalize(rawCursor))),
              )
              as Map<String, dynamic>;
      final Object? offset = payload['offset'];
      if (offset is int && offset >= 0) {
        return offset;
      }
      if (offset is num && offset >= 0) {
        return offset.toInt();
      }
    } catch (_) {
      return query.offset < 0 ? 0 : query.offset;
    }
    return query.offset < 0 ? 0 : query.offset;
  }

  String _encodeFallbackCursor(int offset) {
    return base64Url.encode(
      utf8.encode(jsonEncode(<String, int>{'offset': offset})),
    );
  }

  bool _isGoalkeeper(String position) => position == 'GK';

  bool _isDefender(String position) {
    return position == 'CB' ||
        position == 'LB' ||
        position == 'RB' ||
        position == 'LWB' ||
        position == 'RWB';
  }

  bool _isMidfielder(String position) {
    return position == 'DM' ||
        position == 'CM' ||
        position == 'AM' ||
        position == 'LM' ||
        position == 'RM';
  }
}

class _BrowseSeed {
  const _BrowseSeed(this.label, this.id);

  final String label;
  final String? id;
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
  return gteApiErrorMessage(
    payload,
    fallback: 'The backend returned an unexpected response.',
  );
}
