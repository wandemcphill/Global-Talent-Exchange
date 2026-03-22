import 'dart:convert';

import 'package:http/http.dart' as http;

import 'gte_models.dart';

enum GteBackendMode {
  live,
  fixture,
  liveThenFixture,
}

enum GteApiErrorType {
  network,
  unauthorized,
  notFound,
  validation,
  unavailable,
  parsing,
  unknown,
}

class GteApiException implements Exception {
  const GteApiException({
    required this.type,
    required this.message,
    this.statusCode,
    this.cause,
  });

  final GteApiErrorType type;
  final String message;
  final int? statusCode;
  final Object? cause;

  bool get supportsFixtureFallback =>
      type == GteApiErrorType.network ||
      type == GteApiErrorType.unavailable ||
      type == GteApiErrorType.parsing;

  @override
  String toString() => 'GteApiException($type, $statusCode): $message';
}

class GteRequestGate {
  int _requestId = 0;

  int begin() => ++_requestId;

  bool isActive(int requestId) => requestId == _requestId;
}

abstract class GteTokenStore {
  Future<String?> readToken();

  Future<void> writeToken(String? token);
}

class GteMemoryTokenStore implements GteTokenStore {
  String? _token;

  @override
  Future<String?> readToken() async => _token;

  @override
  Future<void> writeToken(String? token) async {
    _token = token;
  }
}

class GteTransportRequest {
  const GteTransportRequest({
    required this.method,
    required this.uri,
    this.headers = const <String, String>{},
    this.body,
  });

  final String method;
  final Uri uri;
  final Map<String, String> headers;
  final Object? body;
}

class GteTransportResponse {
  const GteTransportResponse({
    required this.statusCode,
    required this.body,
    this.headers = const <String, String>{},
  });

  final int statusCode;
  final Object? body;
  final Map<String, String> headers;
}

abstract class GteTransport {
  Future<GteTransportResponse> send(GteTransportRequest request);
}

class GteRepositoryConfig {
  const GteRepositoryConfig({
    required this.baseUrl,
    this.mode = GteBackendMode.liveThenFixture,
  });

  final String baseUrl;
  final GteBackendMode mode;

  Uri uriFor(String path,
      [Map<String, Object?> queryParameters = const <String, Object?>{}]) {
    final Uri baseUri =
        Uri.parse(baseUrl.endsWith('/') ? baseUrl : '$baseUrl/');
    final Uri resolved =
        baseUri.resolve(path.startsWith('/') ? path.substring(1) : path);
    final Map<String, List<String>> query = <String, List<String>>{};
    for (final MapEntry<String, Object?> entry in queryParameters.entries) {
      if (entry.value == null) {
        continue;
      }
      if (entry.value is Iterable<Object?> && entry.value is! String) {
        final List<String> values = (entry.value as Iterable<Object?>)
            .where((Object? value) => value != null)
            .map((Object? value) => value.toString())
            .toList(growable: false);
        if (values.isNotEmpty) {
          query[entry.key] = values;
        }
        continue;
      }
      query[entry.key] = <String>[entry.value.toString()];
    }
    if (query.isEmpty) {
      return resolved;
    }
    final String queryString = query.entries
        .expand(
          (MapEntry<String, List<String>> entry) => entry.value.map(
            (String value) =>
                '${Uri.encodeQueryComponent(entry.key)}=${Uri.encodeQueryComponent(value)}',
          ),
        )
        .join('&');
    return resolved.replace(query: queryString);
  }
}

abstract class GteApiRepository {
  Future<GteAuthSession> login(GteAuthLoginRequest request);

  Future<GteAuthSession> register(GteAuthRegisterRequest request);

  Future<GteCurrentUser> fetchCurrentUser();

  Future<void> logout();

  Future<List<GtePolicyDocumentSummary>> fetchPolicyDocuments({
    bool mandatoryOnly = false,
  });

  Future<GtePolicyDocumentDetail> fetchPolicyDocument(
    String documentKey, {
    String? versionLabel,
  });

  Future<GteComplianceStatus> fetchComplianceStatus();

  Future<List<GtePolicyRequirementSummary>> fetchPolicyRequirements();

  Future<List<GtePolicyAcceptanceSummary>> fetchMyPolicyAcceptances();

  Future<GtePolicyAcceptanceSummary> acceptPolicyDocument(
    String documentKey,
    String versionLabel,
  );

  Future<List<PlayerSnapshot>> fetchPlayers({int limit = 20});

  Future<PlayerProfile> fetchPlayerProfile(String playerId);

  Future<MarketPulse> fetchMarketPulse();

  Future<GteMarketTicker> fetchTicker(String playerId);

  Future<GteMarketCandles> fetchCandles(String playerId,
      {String interval = '1h', int limit = 30});

  Future<GteOrderBook> fetchOrderBook(String playerId);

  Future<GteOrderListView> listOrders({
    int limit = 20,
    int offset = 0,
    List<GteOrderStatus>? statuses,
  });

  Future<GteOrderRecord> fetchOrder(String orderId);

  Future<GteOrderRecord> placeOrder(GteOrderCreateRequest request);

  Future<GteOrderRecord> cancelOrder(String orderId);

  Future<GteWalletSummary> fetchWalletSummary();

  Future<GteWalletOverview> fetchWalletOverview();

  Future<GteWalletLedgerPage> fetchWalletLedger(
      {int page = 1, int pageSize = 20});

  Future<GteWithdrawalEligibility> fetchWithdrawalEligibility();

  Future<GteWithdrawalQuote> fetchWithdrawalQuote(
      GteWithdrawalQuoteRequest request);

  Future<GteWithdrawalReceipt> fetchWithdrawalReceipt(String withdrawalId);

  Future<GteDepositRequest> createDepositRequest(
      GteDepositCreateRequest request);

  Future<GteDepositRequest> submitDepositRequest(
      String depositId, GteDepositSubmitRequest request);

  Future<List<GteDepositRequest>> listDepositRequests();

  Future<GteTreasuryWithdrawalRequest> createWithdrawalRequest(
      GteWithdrawalCreateRequest request);

  Future<List<GteTreasuryWithdrawalRequest>> listWithdrawalRequests();

  Future<GteKycProfile> fetchKycProfile();

  Future<GteKycProfile> submitKycProfile(GteKycSubmitRequest request);

  Future<List<GteUserBankAccount>> listUserBankAccounts();

  Future<GteUserBankAccount> createUserBankAccount(
      GteUserBankAccountCreate request);

  Future<GteUserBankAccount> updateUserBankAccount(
      String bankAccountId, GteUserBankAccountUpdate request);

  Future<List<GteDispute>> listDisputes();

  Future<GteDispute> openDispute(GteDisputeCreateRequest request);

  Future<GteDispute> fetchDispute(String disputeId);

  Future<GteDisputeMessage> sendDisputeMessage(
      String disputeId, GteDisputeMessageRequest request);

  Future<List<GteNotification>> listNotifications({int limit = 20});

  Future<void> markNotificationRead(String notificationId);

  Future<void> markAllNotificationsRead();

  Future<GteAttachment> uploadAttachment(
    String filename,
    List<int> bytes, {
    String? contentType,
  });

  Future<GteAnalyticsEvent> trackAnalyticsEvent(
    String name, {
    Map<String, Object?> metadata = const <String, Object?>{},
  });

  Future<GteAnalyticsSummary> fetchAnalyticsSummary();

  Future<GteAnalyticsFunnel> fetchAnalyticsFunnel();

  Future<GteTreasuryDashboard> fetchTreasuryDashboard();

  Future<GteTreasurySettings> fetchTreasurySettings();

  Future<GteTreasurySettings> updateTreasurySettings(
      GteTreasurySettingsUpdate request);

  Future<List<GteTreasuryBankAccount>> listTreasuryBankAccounts();

  Future<GteTreasuryBankAccount> createTreasuryBankAccount(
      GteTreasuryBankAccountCreate request);

  Future<GteTreasuryBankAccount> updateTreasuryBankAccount(
      String accountId, GteTreasuryBankAccountUpdate request);

  Future<GteAdminQueuePage<GteAdminDeposit>> fetchAdminDeposits({
    int limit = 50,
    int offset = 0,
    String? status,
    String? query,
  });

  Future<GteDepositRequest> adminConfirmDeposit(String depositId,
      {String? adminNotes});

  Future<GteDepositRequest> adminRejectDeposit(String depositId,
      {String? adminNotes});

  Future<GteDepositRequest> adminReviewDeposit(String depositId,
      {String? adminNotes});

  Future<GteAdminQueuePage<GteAdminWithdrawal>> fetchAdminWithdrawals({
    int limit = 50,
    int offset = 0,
    String? status,
    String? query,
  });

  Future<GteTreasuryWithdrawalRequest> adminUpdateWithdrawalStatus(
    String withdrawalId, {
    required GteWithdrawalStatus status,
    String? adminNotes,
  });

  Future<GteAdminQueuePage<GteAdminKyc>> fetchAdminKyc({
    int limit = 50,
    int offset = 0,
    String? status,
    String? query,
  });

  Future<GteKycProfile> adminReviewKyc(
      String profileId, GteKycReviewRequest request);

  Future<GteAdminQueuePage<GteDispute>> fetchAdminDisputes({
    int limit = 50,
    int offset = 0,
    String? status,
    String? query,
  });

  Future<GteDispute> fetchAdminDispute(String disputeId);

  Future<GteDisputeMessage> adminSendDisputeMessage(
      String disputeId, GteDisputeMessageRequest request);

  Future<GtePortfolioView> fetchPortfolio();

  Future<GtePortfolioSummary> fetchPortfolioSummary();
}

class GteReliableApiRepository implements GteApiRepository {
  GteReliableApiRepository({
    required this.config,
    required this.transport,
    required this.fixtures,
    GteTokenStore? tokenStore,
  }) : tokenStore = tokenStore ?? GteMemoryTokenStore();

  final GteRepositoryConfig config;
  final GteTransport transport;
  final GteApiRepository fixtures;
  final GteTokenStore tokenStore;

  @override
  Future<GteAuthSession> login(GteAuthLoginRequest request) async {
    final GteAuthSession session = await _withFallback<GteAuthSession>(
      () async => GteAuthSession.fromJson(
        await _request('POST', '/auth/login', body: request.toJson()),
      ),
      () => fixtures.login(request),
      allowFixtureFallback: false,
    );
    await tokenStore.writeToken(session.accessToken);
    return session;
  }

  @override
  Future<GteAuthSession> register(GteAuthRegisterRequest request) async {
    final GteAuthSession session = await _withFallback<GteAuthSession>(
      () async => GteAuthSession.fromJson(
        await _request('POST', '/auth/register', body: request.toJson()),
      ),
      () => fixtures.register(request),
      allowFixtureFallback: false,
    );
    await tokenStore.writeToken(session.accessToken);
    return session;
  }

  @override
  Future<GteCurrentUser> fetchCurrentUser() {
    return _withFallback<GteCurrentUser>(
      () async => GteCurrentUser.fromJson(
          await _request('GET', '/api/auth/me', requiresAuth: true)),
      fixtures.fetchCurrentUser,
      allowFixtureFallback: false,
    );
  }

  @override
  Future<void> logout() => tokenStore.writeToken(null);

  @override
  Future<List<GtePolicyDocumentSummary>> fetchPolicyDocuments({
    bool mandatoryOnly = false,
  }) {
    return _withFallback<List<GtePolicyDocumentSummary>>(
      () async {
        final List<Object?> payload = GteJson.list(
          await _request(
            'GET',
            '/policies/documents',
            query: <String, Object?>{'mandatory_only': mandatoryOnly},
          ),
          label: 'policy documents',
        );
        return payload
            .map(GtePolicyDocumentSummary.fromJson)
            .toList(growable: false);
      },
      () => fixtures.fetchPolicyDocuments(mandatoryOnly: mandatoryOnly),
    );
  }

  @override
  Future<GtePolicyDocumentDetail> fetchPolicyDocument(
    String documentKey, {
    String? versionLabel,
  }) {
    return _withFallback<GtePolicyDocumentDetail>(
      () async => GtePolicyDocumentDetail.fromJson(
        await _request(
          'GET',
          '/policies/documents/$documentKey',
          query: <String, Object?>{
            if (versionLabel != null) 'version_label': versionLabel
          },
        ),
      ),
      () =>
          fixtures.fetchPolicyDocument(documentKey, versionLabel: versionLabel),
    );
  }

  @override
  Future<GteComplianceStatus> fetchComplianceStatus() {
    return _withFallback<GteComplianceStatus>(
      () async => GteComplianceStatus.fromJson(
        await _request('GET', '/policies/me/compliance', requiresAuth: true),
      ),
      fixtures.fetchComplianceStatus,
    );
  }

  @override
  Future<List<GtePolicyRequirementSummary>> fetchPolicyRequirements() {
    return _withFallback<List<GtePolicyRequirementSummary>>(
      () async {
        final List<Object?> payload = GteJson.list(
          await _request('GET', '/policies/me/requirements',
              requiresAuth: true),
          label: 'policy requirements',
        );
        return payload
            .map(GtePolicyRequirementSummary.fromJson)
            .toList(growable: false);
      },
      fixtures.fetchPolicyRequirements,
    );
  }

  @override
  Future<List<GtePolicyAcceptanceSummary>> fetchMyPolicyAcceptances() {
    return _withFallback<List<GtePolicyAcceptanceSummary>>(
      () async {
        final List<Object?> payload = GteJson.list(
          await _request('GET', '/policies/me/acceptances', requiresAuth: true),
          label: 'policy acceptances',
        );
        return payload
            .map(GtePolicyAcceptanceSummary.fromJson)
            .toList(growable: false);
      },
      fixtures.fetchMyPolicyAcceptances,
    );
  }

  @override
  Future<GtePolicyAcceptanceSummary> acceptPolicyDocument(
    String documentKey,
    String versionLabel,
  ) {
    return _withFallback<GtePolicyAcceptanceSummary>(
      () async {
        final Map<String, Object?> payload = GteJson.map(
          await _request(
            'POST',
            '/policies/acceptances',
            body: <String, Object?>{
              'document_key': documentKey,
              'version_label': versionLabel,
            },
            requiresAuth: true,
          ),
          label: 'policy acceptance response',
        );
        return GtePolicyAcceptanceSummary(
          documentKey:
              GteJson.string(payload, <String>['document_key', 'documentKey']),
          title: documentKey,
          versionLabel: GteJson.string(
              payload, <String>['version_label', 'versionLabel']),
          acceptedAt: GteJson.dateTimeOrNull(
              payload, <String>['accepted_at', 'acceptedAt']),
        );
      },
      () => fixtures.acceptPolicyDocument(documentKey, versionLabel),
    );
  }

  @override
  Future<List<PlayerSnapshot>> fetchPlayers({int limit = 20}) {
    return _withFallback<List<PlayerSnapshot>>(
      () async {
        final Map<String, Object?> payload = GteJson.map(
          await _request('GET', '/api/market/players',
              query: <String, Object?>{'limit': limit}),
          label: 'market players',
        );
        final Map<String, PlayerSnapshot> fixtureById = {
          for (final PlayerSnapshot player
              in await fixtures.fetchPlayers(limit: limit))
            player.id: player,
        };
        return GteJson.typedList(payload, <String>['items'], (Object? value) {
          final Map<String, Object?> item =
              GteJson.map(value, label: 'market player item');
          final String playerId = GteJson.string(item, <String>['player_id']);
          return _mapPlayerSnapshot(item, fixtureById[playerId]);
        });
      },
      () => fixtures.fetchPlayers(limit: limit),
    );
  }

  @override
  Future<PlayerProfile> fetchPlayerProfile(String playerId) {
    return _withFallback<PlayerProfile>(
      () async {
        final PlayerProfile? fixtureProfile =
            await _safeFixture<PlayerProfile?>(
          () => fixtures.fetchPlayerProfile(playerId),
        );
        final Map<String, Object?> detail = GteJson.map(
          await _request('GET', '/api/market/players/$playerId'),
          label: 'market player detail',
        );
        final GteMarketTicker ticker = await fetchTicker(playerId);
        final GteMarketCandles candles = await fetchCandles(playerId, limit: 6);
        final GteOrderBook orderBook = await fetchOrderBook(playerId);
        return _mapPlayerProfile(
            detail, ticker, candles, orderBook, fixtureProfile);
      },
      () => fixtures.fetchPlayerProfile(playerId),
    );
  }

  @override
  Future<MarketPulse> fetchMarketPulse() {
    return _withFallback<MarketPulse>(
      () async {
        final MarketPulse fixturePulse = await fixtures.fetchMarketPulse();
        final List<PlayerSnapshot> players = await fetchPlayers(limit: 6);
        final double marketMomentum = players.isEmpty
            ? fixturePulse.marketMomentum
            : players.fold<double>(
                    0,
                    (double sum, PlayerSnapshot player) =>
                        sum + player.valueDeltaPct) /
                players.length;
        final int volume = players.fold<int>(
            0, (int sum, PlayerSnapshot player) => sum + player.marketCredits);
        final List<String> tickers =
            players.take(4).map((PlayerSnapshot player) {
          final String sign = player.valueDeltaPct >= 0 ? '+' : '';
          return '${player.name} $sign${player.valueDeltaPct.toStringAsFixed(1)}%';
        }).toList(growable: false);
        return MarketPulse(
          marketMomentum: marketMomentum,
          dailyVolumeCredits: volume,
          activeWatchers: players
                      .where((PlayerSnapshot player) => player.isWatchlisted)
                      .length *
                  73 +
              131,
          liveDeals: fixturePulse.transferRoom.length,
          hottestLeague: fixturePulse.hottestLeague,
          tickers: tickers.isEmpty ? fixturePulse.tickers : tickers,
          transferRoom: fixturePulse.transferRoom,
        );
      },
      fixtures.fetchMarketPulse,
    );
  }

  @override
  Future<GteMarketTicker> fetchTicker(String playerId) {
    return _withFallback<GteMarketTicker>(
      () async => GteMarketTicker.fromJson(
          await _request('GET', '/api/market/ticker/$playerId')),
      () => fixtures.fetchTicker(playerId),
    );
  }

  @override
  Future<GteMarketCandles> fetchCandles(String playerId,
      {String interval = '1h', int limit = 30}) {
    return _withFallback<GteMarketCandles>(
      () async => GteMarketCandles.fromJson(
        await _request(
          'GET',
          '/api/market/players/$playerId/candles',
          query: <String, Object?>{'interval': interval, 'limit': limit},
        ),
      ),
      () => fixtures.fetchCandles(playerId, interval: interval, limit: limit),
    );
  }

  @override
  Future<GteOrderBook> fetchOrderBook(String playerId) {
    return _withFallback<GteOrderBook>(
      () async => GteOrderBook.fromJson(
          await _request('GET', '/api/orders/book/$playerId')),
      () => fixtures.fetchOrderBook(playerId),
    );
  }

  @override
  Future<GteOrderListView> listOrders({
    int limit = 20,
    int offset = 0,
    List<GteOrderStatus>? statuses,
  }) {
    return _withFallback<GteOrderListView>(
      () async => GteOrderListView.fromJson(
        await _request(
          'GET',
          '/api/orders',
          query: <String, Object?>{
            'limit': limit,
            'offset': offset,
            if (statuses != null && statuses.isNotEmpty)
              'status':
                  statuses.map(_orderStatusQueryValue).toList(growable: false),
          },
          requiresAuth: true,
        ),
      ),
      () =>
          fixtures.listOrders(limit: limit, offset: offset, statuses: statuses),
    );
  }

  @override
  Future<GteOrderRecord> fetchOrder(String orderId) {
    return _withFallback<GteOrderRecord>(
      () async => GteOrderRecord.fromJson(
        await _request('GET', '/api/orders/$orderId', requiresAuth: true),
      ),
      () => fixtures.fetchOrder(orderId),
    );
  }

  @override
  Future<GteOrderRecord> placeOrder(GteOrderCreateRequest request) {
    return _withFallback<GteOrderRecord>(
      () async => GteOrderRecord.fromJson(
        await _request('POST', '/api/orders',
            body: request.toJson(), requiresAuth: true),
      ),
      () => fixtures.placeOrder(request),
    );
  }

  @override
  Future<GteOrderRecord> cancelOrder(String orderId) {
    return _withFallback<GteOrderRecord>(
      () async => GteOrderRecord.fromJson(
        await _request('POST', '/api/orders/$orderId/cancel',
            requiresAuth: true),
      ),
      () => fixtures.cancelOrder(orderId),
    );
  }

  @override
  Future<GteWalletSummary> fetchWalletSummary() {
    return _withFallback<GteWalletSummary>(
      () async => GteWalletSummary.fromJson(
        await _request('GET', '/api/wallets/summary', requiresAuth: true),
      ),
      fixtures.fetchWalletSummary,
    );
  }

  @override
  Future<GteWalletOverview> fetchWalletOverview() {
    return _withFallback<GteWalletOverview>(
      () async => GteWalletOverview.fromJson(
        await _request('GET', '/api/wallets/overview', requiresAuth: true),
      ),
      fixtures.fetchWalletOverview,
    );
  }

  @override
  Future<GteWalletLedgerPage> fetchWalletLedger(
      {int page = 1, int pageSize = 20}) {
    return _withFallback<GteWalletLedgerPage>(
      () async => GteWalletLedgerPage.fromJson(
        await _request(
          'GET',
          '/api/wallets/ledger',
          query: <String, Object?>{'page': page, 'page_size': pageSize},
          requiresAuth: true,
        ),
      ),
      () => fixtures.fetchWalletLedger(page: page, pageSize: pageSize),
    );
  }

  @override
  Future<GteWithdrawalEligibility> fetchWithdrawalEligibility() {
    return _withFallback<GteWithdrawalEligibility>(
      () async => GteWithdrawalEligibility.fromJson(
        await _request('GET', '/api/wallets/withdrawals/eligibility',
            requiresAuth: true),
      ),
      fixtures.fetchWithdrawalEligibility,
    );
  }

  @override
  Future<GteWithdrawalQuote> fetchWithdrawalQuote(
      GteWithdrawalQuoteRequest request) {
    return _withFallback<GteWithdrawalQuote>(
      () async => GteWithdrawalQuote.fromJson(
        await _request(
          'POST',
          '/api/wallets/withdrawals/quote',
          body: request.toJson(),
          requiresAuth: true,
        ),
      ),
      () => fixtures.fetchWithdrawalQuote(request),
    );
  }

  @override
  Future<GteWithdrawalReceipt> fetchWithdrawalReceipt(String withdrawalId) {
    return _withFallback<GteWithdrawalReceipt>(
      () async => GteWithdrawalReceipt.fromJson(
        await _request(
          'GET',
          '/api/wallets/withdrawals/$withdrawalId/receipt',
          requiresAuth: true,
        ),
      ),
      () => fixtures.fetchWithdrawalReceipt(withdrawalId),
    );
  }

  @override
  Future<GteDepositRequest> createDepositRequest(
      GteDepositCreateRequest request) {
    return _withFallback<GteDepositRequest>(
      () async => GteDepositRequest.fromJson(
        await _request('POST', '/api/wallets/deposits',
            body: request.toJson(), requiresAuth: true),
      ),
      () => fixtures.createDepositRequest(request),
    );
  }

  @override
  Future<GteDepositRequest> submitDepositRequest(
      String depositId, GteDepositSubmitRequest request) {
    return _withFallback<GteDepositRequest>(
      () async => GteDepositRequest.fromJson(
        await _request(
          'POST',
          '/api/wallets/deposits/$depositId/submit',
          body: request.toJson(),
          requiresAuth: true,
        ),
      ),
      () => fixtures.submitDepositRequest(depositId, request),
    );
  }

  @override
  Future<List<GteDepositRequest>> listDepositRequests() {
    return _withFallback<List<GteDepositRequest>>(
      () async {
        final List<Object?> payload = GteJson.list(
          await _request('GET', '/api/wallets/deposits', requiresAuth: true),
          label: 'deposit list',
        );
        return payload.map(GteDepositRequest.fromJson).toList(growable: false);
      },
      fixtures.listDepositRequests,
    );
  }

  @override
  Future<GteTreasuryWithdrawalRequest> createWithdrawalRequest(
      GteWithdrawalCreateRequest request) {
    return _withFallback<GteTreasuryWithdrawalRequest>(
      () async => GteTreasuryWithdrawalRequest.fromJson(
        await _request('POST', '/api/wallets/withdrawals',
            body: request.toJson(), requiresAuth: true),
      ),
      () => fixtures.createWithdrawalRequest(request),
    );
  }

  @override
  Future<List<GteTreasuryWithdrawalRequest>> listWithdrawalRequests() {
    return _withFallback<List<GteTreasuryWithdrawalRequest>>(
      () async {
        final List<Object?> payload = GteJson.list(
          await _request('GET', '/api/wallets/withdrawals', requiresAuth: true),
          label: 'withdrawal list',
        );
        return payload
            .map(GteTreasuryWithdrawalRequest.fromJson)
            .toList(growable: false);
      },
      fixtures.listWithdrawalRequests,
    );
  }

  @override
  Future<GteKycProfile> fetchKycProfile() {
    return _withFallback<GteKycProfile>(
      () async => GteKycProfile.fromJson(
        await _request('GET', '/api/kyc', requiresAuth: true),
      ),
      fixtures.fetchKycProfile,
    );
  }

  @override
  Future<GteKycProfile> submitKycProfile(GteKycSubmitRequest request) {
    return _withFallback<GteKycProfile>(
      () async => GteKycProfile.fromJson(
        await _request('POST', '/api/kyc',
            body: request.toJson(), requiresAuth: true),
      ),
      () => fixtures.submitKycProfile(request),
    );
  }

  @override
  Future<List<GteUserBankAccount>> listUserBankAccounts() {
    return _withFallback<List<GteUserBankAccount>>(
      () async {
        final List<Object?> payload = GteJson.list(
          await _request('GET', '/api/bank-accounts', requiresAuth: true),
          label: 'bank accounts',
        );
        return payload.map(GteUserBankAccount.fromJson).toList(growable: false);
      },
      fixtures.listUserBankAccounts,
    );
  }

  @override
  Future<GteUserBankAccount> createUserBankAccount(
      GteUserBankAccountCreate request) {
    return _withFallback<GteUserBankAccount>(
      () async => GteUserBankAccount.fromJson(
        await _request('POST', '/api/bank-accounts',
            body: request.toJson(), requiresAuth: true),
      ),
      () => fixtures.createUserBankAccount(request),
    );
  }

  @override
  Future<GteUserBankAccount> updateUserBankAccount(
      String bankAccountId, GteUserBankAccountUpdate request) {
    return _withFallback<GteUserBankAccount>(
      () async => GteUserBankAccount.fromJson(
        await _request('PUT', '/api/bank-accounts/$bankAccountId',
            body: request.toJson(), requiresAuth: true),
      ),
      () => fixtures.updateUserBankAccount(bankAccountId, request),
    );
  }

  @override
  Future<List<GteDispute>> listDisputes() {
    return _withFallback<List<GteDispute>>(
      () async {
        final List<Object?> payload = GteJson.list(
          await _request('GET', '/api/disputes', requiresAuth: true),
          label: 'disputes',
        );
        return payload.map(GteDispute.fromJson).toList(growable: false);
      },
      fixtures.listDisputes,
    );
  }

  @override
  Future<GteDispute> openDispute(GteDisputeCreateRequest request) {
    return _withFallback<GteDispute>(
      () async => GteDispute.fromJson(
        await _request('POST', '/api/disputes',
            body: request.toJson(), requiresAuth: true),
      ),
      () => fixtures.openDispute(request),
    );
  }

  @override
  Future<GteDispute> fetchDispute(String disputeId) {
    return _withFallback<GteDispute>(
      () async => GteDispute.fromJson(
        await _request('GET', '/api/disputes/$disputeId', requiresAuth: true),
      ),
      () => fixtures.fetchDispute(disputeId),
    );
  }

  @override
  Future<GteDisputeMessage> sendDisputeMessage(
      String disputeId, GteDisputeMessageRequest request) {
    return _withFallback<GteDisputeMessage>(
      () async => GteDisputeMessage.fromJson(
        await _request(
          'POST',
          '/api/disputes/$disputeId/messages',
          body: request.toJson(),
          requiresAuth: true,
        ),
      ),
      () => fixtures.sendDisputeMessage(disputeId, request),
    );
  }

  @override
  Future<List<GteNotification>> listNotifications({int limit = 20}) {
    return _withFallback<List<GteNotification>>(
      () async {
        final List<Object?> payload = GteJson.list(
          await _request('GET', '/notifications/me',
              query: <String, Object?>{'limit': limit}, requiresAuth: true),
          label: 'notifications',
        );
        return payload.map(GteNotification.fromJson).toList(growable: false);
      },
      () => fixtures.listNotifications(limit: limit),
    );
  }

  @override
  Future<void> markNotificationRead(String notificationId) {
    return _withFallback<void>(
      () async {
        await _request('POST', '/notifications/$notificationId/read',
            requiresAuth: true);
      },
      () => fixtures.markNotificationRead(notificationId),
    );
  }

  @override
  Future<void> markAllNotificationsRead() {
    return _withFallback<void>(
      () async {
        await _request('POST', '/notifications/read-all', requiresAuth: true);
      },
      fixtures.markAllNotificationsRead,
    );
  }

  @override
  Future<GteAttachment> uploadAttachment(
    String filename,
    List<int> bytes, {
    String? contentType,
  }) {
    return _withFallback<GteAttachment>(
      () async => _uploadAttachmentLive(
        filename,
        bytes,
        contentType: contentType,
      ),
      () =>
          fixtures.uploadAttachment(filename, bytes, contentType: contentType),
    );
  }

  @override
  Future<GteAnalyticsEvent> trackAnalyticsEvent(
    String name, {
    Map<String, Object?> metadata = const <String, Object?>{},
  }) {
    return _withFallback<GteAnalyticsEvent>(
      () async => GteAnalyticsEvent.fromJson(
        await _request(
          'POST',
          '/api/analytics/events',
          body: <String, Object?>{'name': name, 'metadata': metadata},
          requiresAuth: true,
        ),
      ),
      () => fixtures.trackAnalyticsEvent(name, metadata: metadata),
    );
  }

  @override
  Future<GteAnalyticsSummary> fetchAnalyticsSummary() {
    return _withFallback<GteAnalyticsSummary>(
      () async => GteAnalyticsSummary.fromJson(
        await _request('GET', '/api/admin/analytics/summary',
            requiresAuth: true),
      ),
      fixtures.fetchAnalyticsSummary,
    );
  }

  @override
  Future<GteAnalyticsFunnel> fetchAnalyticsFunnel() {
    return _withFallback<GteAnalyticsFunnel>(
      () async => GteAnalyticsFunnel.fromJson(
        await _request('GET', '/api/admin/analytics/funnels',
            requiresAuth: true),
      ),
      fixtures.fetchAnalyticsFunnel,
    );
  }

  @override
  Future<GtePortfolioView> fetchPortfolio() {
    return _withFallback<GtePortfolioView>(
      () async => GtePortfolioView.fromJson(
        await _request('GET', '/api/portfolio', requiresAuth: true),
      ),
      fixtures.fetchPortfolio,
    );
  }

  @override
  Future<GtePortfolioSummary> fetchPortfolioSummary() {
    return _withFallback<GtePortfolioSummary>(
      () async => GtePortfolioSummary.fromJson(
        await _request('GET', '/api/portfolio/summary', requiresAuth: true),
      ),
      fixtures.fetchPortfolioSummary,
    );
  }

  @override
  Future<GteTreasuryDashboard> fetchTreasuryDashboard() {
    return _withFallback<GteTreasuryDashboard>(
      () async => GteTreasuryDashboard.fromJson(
        await _request('GET', '/api/admin/treasury/dashboard',
            requiresAuth: true),
      ),
      fixtures.fetchTreasuryDashboard,
    );
  }

  @override
  Future<GteTreasurySettings> fetchTreasurySettings() {
    return _withFallback<GteTreasurySettings>(
      () async => GteTreasurySettings.fromJson(
        await _request('GET', '/api/admin/treasury/settings',
            requiresAuth: true),
      ),
      fixtures.fetchTreasurySettings,
    );
  }

  @override
  Future<GteTreasurySettings> updateTreasurySettings(
      GteTreasurySettingsUpdate request) {
    return _withFallback<GteTreasurySettings>(
      () async => GteTreasurySettings.fromJson(
        await _request('PUT', '/api/admin/treasury/settings',
            body: request.toJson(), requiresAuth: true),
      ),
      () => fixtures.updateTreasurySettings(request),
    );
  }

  @override
  Future<List<GteTreasuryBankAccount>> listTreasuryBankAccounts() {
    return _withFallback<List<GteTreasuryBankAccount>>(
      () async {
        final List<Object?> payload = GteJson.list(
          await _request('GET', '/api/admin/treasury/bank-accounts',
              requiresAuth: true),
          label: 'treasury bank accounts',
        );
        return payload
            .map(GteTreasuryBankAccount.fromJson)
            .toList(growable: false);
      },
      fixtures.listTreasuryBankAccounts,
    );
  }

  @override
  Future<GteTreasuryBankAccount> createTreasuryBankAccount(
      GteTreasuryBankAccountCreate request) {
    return _withFallback<GteTreasuryBankAccount>(
      () async => GteTreasuryBankAccount.fromJson(
        await _request('POST', '/api/admin/treasury/bank-accounts',
            body: request.toJson(), requiresAuth: true),
      ),
      () => fixtures.createTreasuryBankAccount(request),
    );
  }

  @override
  Future<GteTreasuryBankAccount> updateTreasuryBankAccount(
      String accountId, GteTreasuryBankAccountUpdate request) {
    return _withFallback<GteTreasuryBankAccount>(
      () async => GteTreasuryBankAccount.fromJson(
        await _request('PUT', '/api/admin/treasury/bank-accounts/$accountId',
            body: request.toJson(), requiresAuth: true),
      ),
      () => fixtures.updateTreasuryBankAccount(accountId, request),
    );
  }

  @override
  Future<GteAdminQueuePage<GteAdminDeposit>> fetchAdminDeposits({
    int limit = 50,
    int offset = 0,
    String? status,
    String? query,
  }) {
    return _withFallback<GteAdminQueuePage<GteAdminDeposit>>(
      () async => GteAdminQueuePage<GteAdminDeposit>.fromJson(
        await _request(
          'GET',
          '/api/admin/treasury/deposits',
          query: <String, Object?>{
            'limit': limit,
            'offset': offset,
            if (status != null) 'status': status,
            if (query != null && query.isNotEmpty) 'q': query,
          },
          requiresAuth: true,
        ),
        GteAdminDeposit.fromJson,
      ),
      () => fixtures.fetchAdminDeposits(
        limit: limit,
        offset: offset,
        status: status,
        query: query,
      ),
    );
  }

  @override
  Future<GteDepositRequest> adminConfirmDeposit(String depositId,
      {String? adminNotes}) {
    return _withFallback<GteDepositRequest>(
      () async => GteDepositRequest.fromJson(
        await _request(
          'POST',
          '/api/admin/treasury/deposits/$depositId/confirm',
          body: adminNotes == null
              ? null
              : <String, Object?>{'admin_notes': adminNotes},
          requiresAuth: true,
        ),
      ),
      () => fixtures.adminConfirmDeposit(depositId, adminNotes: adminNotes),
    );
  }

  @override
  Future<GteDepositRequest> adminRejectDeposit(String depositId,
      {String? adminNotes}) {
    return _withFallback<GteDepositRequest>(
      () async => GteDepositRequest.fromJson(
        await _request(
          'POST',
          '/api/admin/treasury/deposits/$depositId/reject',
          body: adminNotes == null
              ? null
              : <String, Object?>{'admin_notes': adminNotes},
          requiresAuth: true,
        ),
      ),
      () => fixtures.adminRejectDeposit(depositId, adminNotes: adminNotes),
    );
  }

  @override
  Future<GteDepositRequest> adminReviewDeposit(String depositId,
      {String? adminNotes}) {
    return _withFallback<GteDepositRequest>(
      () async => GteDepositRequest.fromJson(
        await _request(
          'POST',
          '/api/admin/treasury/deposits/$depositId/review',
          body: adminNotes == null
              ? null
              : <String, Object?>{'admin_notes': adminNotes},
          requiresAuth: true,
        ),
      ),
      () => fixtures.adminReviewDeposit(depositId, adminNotes: adminNotes),
    );
  }

  @override
  Future<GteAdminQueuePage<GteAdminWithdrawal>> fetchAdminWithdrawals({
    int limit = 50,
    int offset = 0,
    String? status,
    String? query,
  }) {
    return _withFallback<GteAdminQueuePage<GteAdminWithdrawal>>(
      () async => GteAdminQueuePage<GteAdminWithdrawal>.fromJson(
        await _request(
          'GET',
          '/api/admin/treasury/withdrawals',
          query: <String, Object?>{
            'limit': limit,
            'offset': offset,
            if (status != null) 'status': status,
            if (query != null && query.isNotEmpty) 'q': query,
          },
          requiresAuth: true,
        ),
        GteAdminWithdrawal.fromJson,
      ),
      () => fixtures.fetchAdminWithdrawals(
        limit: limit,
        offset: offset,
        status: status,
        query: query,
      ),
    );
  }

  @override
  Future<GteTreasuryWithdrawalRequest> adminUpdateWithdrawalStatus(
    String withdrawalId, {
    required GteWithdrawalStatus status,
    String? adminNotes,
  }) {
    return _withFallback<GteTreasuryWithdrawalRequest>(
      () async => GteTreasuryWithdrawalRequest.fromJson(
        await _request(
          'POST',
          '/api/admin/treasury/withdrawals/$withdrawalId/status',
          body: <String, Object?>{
            'status': _serializeWithdrawalStatus(status),
            if (adminNotes != null) 'admin_notes': adminNotes,
          },
          requiresAuth: true,
        ),
      ),
      () => fixtures.adminUpdateWithdrawalStatus(withdrawalId,
          status: status, adminNotes: adminNotes),
    );
  }

  @override
  Future<GteAdminQueuePage<GteAdminKyc>> fetchAdminKyc({
    int limit = 50,
    int offset = 0,
    String? status,
    String? query,
  }) {
    return _withFallback<GteAdminQueuePage<GteAdminKyc>>(
      () async => GteAdminQueuePage<GteAdminKyc>.fromJson(
        await _request(
          'GET',
          '/api/admin/treasury/kyc',
          query: <String, Object?>{
            'limit': limit,
            'offset': offset,
            if (status != null) 'status': status,
            if (query != null && query.isNotEmpty) 'q': query,
          },
          requiresAuth: true,
        ),
        GteAdminKyc.fromJson,
      ),
      () => fixtures.fetchAdminKyc(
        limit: limit,
        offset: offset,
        status: status,
        query: query,
      ),
    );
  }

  @override
  Future<GteKycProfile> adminReviewKyc(
      String profileId, GteKycReviewRequest request) {
    return _withFallback<GteKycProfile>(
      () async => GteKycProfile.fromJson(
        await _request(
          'POST',
          '/api/admin/treasury/kyc/$profileId/review',
          body: request.toJson(),
          requiresAuth: true,
        ),
      ),
      () => fixtures.adminReviewKyc(profileId, request),
    );
  }

  @override
  Future<GteAdminQueuePage<GteDispute>> fetchAdminDisputes({
    int limit = 50,
    int offset = 0,
    String? status,
    String? query,
  }) {
    return _withFallback<GteAdminQueuePage<GteDispute>>(
      () async => GteAdminQueuePage<GteDispute>.fromJson(
        await _request(
          'GET',
          '/api/admin/treasury/disputes',
          query: <String, Object?>{
            'limit': limit,
            'offset': offset,
            if (status != null) 'status': status,
            if (query != null && query.isNotEmpty) 'q': query,
          },
          requiresAuth: true,
        ),
        GteDispute.fromJson,
      ),
      () => fixtures.fetchAdminDisputes(
        limit: limit,
        offset: offset,
        status: status,
        query: query,
      ),
    );
  }

  @override
  Future<GteDispute> fetchAdminDispute(String disputeId) {
    return _withFallback<GteDispute>(
      () async => GteDispute.fromJson(
        await _request('GET', '/api/admin/treasury/disputes/$disputeId',
            requiresAuth: true),
      ),
      () => fixtures.fetchAdminDispute(disputeId),
    );
  }

  @override
  Future<GteDisputeMessage> adminSendDisputeMessage(
      String disputeId, GteDisputeMessageRequest request) {
    return _withFallback<GteDisputeMessage>(
      () async => GteDisputeMessage.fromJson(
        await _request(
          'POST',
          '/api/admin/treasury/disputes/$disputeId/messages',
          body: request.toJson(),
          requiresAuth: true,
        ),
      ),
      () => fixtures.adminSendDisputeMessage(disputeId, request),
    );
  }

  Future<GteAttachment> _uploadAttachmentLive(
    String filename,
    List<int> bytes, {
    String? contentType,
  }) async {
    final Uri uri = config.uriFor('/api/attachments');
    final http.Client client = http.Client();
    try {
      final http.MultipartRequest request = http.MultipartRequest('POST', uri)
        ..headers['Accept'] = 'application/json';
      final String? token = await tokenStore.readToken();
      if (token != null && token.isNotEmpty) {
        request.headers['Authorization'] = 'Bearer $token';
      }
      request.files.add(
        http.MultipartFile.fromBytes(
          'file',
          bytes,
          filename: filename,
        ),
      );
      final http.StreamedResponse response = await client.send(request);
      final String text = await response.stream.bytesToString();
      final Object? decoded = text.trim().isEmpty ? null : jsonDecode(text);
      if (response.statusCode >= 400) {
        throw GteApiException(
          type: _errorTypeFromStatusCode(response.statusCode),
          message: _errorMessage(decoded),
          statusCode: response.statusCode,
          cause: decoded,
        );
      }
      return GteAttachment.fromJson(decoded);
    } on FormatException catch (error) {
      throw GteApiException(
        type: GteApiErrorType.parsing,
        message: error.message,
        cause: error,
      );
    } on GteApiException {
      rethrow;
    } catch (error) {
      throw GteApiException(
        type: GteApiErrorType.network,
        message: 'Unable to reach the backend.',
        cause: error,
      );
    } finally {
      client.close();
    }
  }

  Future<T> _withFallback<T>(
    Future<T> Function() liveCall,
    Future<T> Function() fixtureCall, {
    bool allowFixtureFallback = true,
  }) async {
    if (config.mode == GteBackendMode.fixture) {
      return fixtureCall();
    }
    try {
      return await liveCall();
    } on GteApiException catch (error) {
      if (allowFixtureFallback &&
          config.mode == GteBackendMode.liveThenFixture &&
          error.supportsFixtureFallback) {
        return fixtureCall();
      }
      rethrow;
    }
  }

  Future<T?> _safeFixture<T>(Future<T> Function() callback) async {
    try {
      return await callback();
    } catch (_) {
      return null;
    }
  }

  Future<Object?> _request(
    String method,
    String path, {
    Map<String, Object?> query = const <String, Object?>{},
    Object? body,
    bool requiresAuth = false,
  }) async {
    final Map<String, String> headers = <String, String>{
      'Accept': 'application/json'
    };
    if (requiresAuth) {
      final String? token = await tokenStore.readToken();
      if (token != null && token.isNotEmpty) {
        headers['Authorization'] = 'Bearer $token';
      }
    }
    if (body != null) {
      headers['Content-Type'] = 'application/json';
    }

    try {
      final GteTransportResponse response = await transport.send(
        GteTransportRequest(
          method: method,
          uri: config.uriFor(path, query),
          headers: headers,
          body: body,
        ),
      );
      if (response.statusCode >= 400) {
        throw GteApiException(
          type: _errorTypeFromStatusCode(response.statusCode),
          message: _errorMessage(response.body),
          statusCode: response.statusCode,
          cause: response.body,
        );
      }
      return response.body;
    } on GteParsingException catch (error) {
      throw GteApiException(
        type: GteApiErrorType.parsing,
        message: error.message,
        cause: error,
      );
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

  PlayerSnapshot _mapPlayerSnapshot(
      Map<String, Object?> json, PlayerSnapshot? fixture) {
    final String playerId = GteJson.string(json, <String>['player_id']);
    final String playerName = GteJson.string(json, <String>['player_name']);
    final double movement = GteJson.number(json, <String>['movement_pct']);
    return (fixture ?? _generatedPlayerSnapshot(playerId, playerName)).copyWith(
      id: playerId,
      name: playerName,
      club: GteJson.stringOrNull(json, <String>['current_club_name']) ??
          fixture?.club ??
          'Unknown club',
      nation: GteJson.stringOrNull(json, <String>['nationality']) ??
          fixture?.nation ??
          'Unknown nation',
      position: GteJson.stringOrNull(json, <String>['position']) ??
          fixture?.position ??
          'N/A',
      age: GteJson.integer(json, <String>['age'], fallback: fixture?.age ?? 0),
      marketCredits:
          GteJson.number(json, <String>['current_value_credits']).round(),
      gsi: GteJson.number(json, <String>['trend_score']).round(),
      formRating: GteJson.number(json, <String>['average_rating'],
          fallback: fixture?.formRating ?? 0.0),
      valueDeltaPct: movement,
    );
  }

  PlayerProfile _mapPlayerProfile(
    Map<String, Object?> json,
    GteMarketTicker ticker,
    GteMarketCandles candles,
    GteOrderBook orderBook,
    PlayerProfile? fixture,
  ) {
    final Map<String, Object?> identity = GteJson.map(
      GteJson.value(json, <String>['identity']) ?? const <String, Object?>{},
      label: 'player identity',
    );
    final Map<String, Object?> value = GteJson.map(
      GteJson.value(json, <String>['value']) ?? const <String, Object?>{},
      label: 'player value',
    );
    final Map<String, Object?> trend = GteJson.map(
      GteJson.value(json, <String>['trend']) ?? const <String, Object?>{},
      label: 'player trend',
    );
    final PlayerSnapshot snapshot = _mapPlayerSnapshot(
      <String, Object?>{
        'player_id': GteJson.string(json, <String>['player_id']),
        'player_name': GteJson.string(identity, <String>['player_name'],
            fallback: fixture?.snapshot.name ?? 'Unknown player'),
        'current_club_name':
            GteJson.stringOrNull(identity, <String>['current_club_name']),
        'nationality': GteJson.stringOrNull(identity, <String>['nationality']),
        'position': GteJson.stringOrNull(identity, <String>['position']),
        'age': GteJson.integer(identity, <String>['age'],
            fallback: fixture?.snapshot.age ?? 0),
        'current_value_credits': GteJson.number(
            value, <String>['current_value_credits'],
            fallback: fixture?.snapshot.marketCredits.toDouble() ?? 0.0),
        'movement_pct': GteJson.number(value, <String>['movement_pct'],
            fallback: fixture?.snapshot.valueDeltaPct ?? 0.0),
        'trend_score': GteJson.number(trend, <String>['global_scouting_index'],
            fallback: fixture?.snapshot.gsi.toDouble() ?? 0.0),
        'average_rating': GteJson.number(trend, <String>['average_rating'],
            fallback: fixture?.snapshot.formRating ?? 0.0),
      },
      fixture?.snapshot,
    ).copyWith(
      valueTrend: candles.candles
          .map((GteMarketCandle candle) => TrendPoint(
              label: candle.timestamp.hour.toString().padLeft(2, '0'),
              value: candle.close))
          .toList(growable: false),
      recentHighlights: fixture?.snapshot.recentHighlights ??
          <String>[
            'Last price ${ticker.lastPrice?.toStringAsFixed(1) ?? 'n/a'} credits',
            '24h volume ${ticker.volume24h.toStringAsFixed(1)}',
            'Spread ${ticker.spread?.toStringAsFixed(1) ?? 'n/a'}',
          ],
    );
    return (fixture ??
            PlayerProfile(
              snapshot: snapshot,
              gsiTrend: snapshot.valueTrend,
              awards: const <String>[],
              statBlocks: const <String>[],
              scoutingReport: 'Live market-backed profile.',
              transferSignal: 'Market detail sourced from the backend.',
            ))
        .copyWith(
      snapshot: snapshot,
      gsiTrend: snapshot.valueTrend,
      ticker: ticker,
      orderBook: orderBook,
      candles: candles,
    );
  }

  PlayerSnapshot _generatedPlayerSnapshot(String playerId, String playerName) {
    return PlayerSnapshot(
      id: playerId,
      name: playerName,
      club: 'Unknown club',
      nation: 'Unknown nation',
      position: 'N/A',
      age: 0,
      marketCredits: 0,
      gsi: 0,
      formRating: 0.0,
      valueDeltaPct: 0.0,
      valueTrend: const <TrendPoint>[],
      recentHighlights: const <String>[],
    );
  }

  GteApiErrorType _errorTypeFromStatusCode(int statusCode) {
    if (statusCode == 401) {
      return GteApiErrorType.unauthorized;
    }
    if (statusCode == 404) {
      return GteApiErrorType.notFound;
    }
    if (statusCode >= 400 && statusCode < 500) {
      return GteApiErrorType.validation;
    }
    if (statusCode >= 500) {
      return GteApiErrorType.unavailable;
    }
    return GteApiErrorType.unknown;
  }

  String _errorMessage(Object? body) {
    if (body is Map) {
      final Map<String, Object?> json = GteJson.map(body);
      final String? detail =
          GteJson.stringOrNull(json, <String>['detail', 'message', 'error']);
      if (detail != null) {
        return detail;
      }
    }
    return 'Backend request failed.';
  }
}

String _orderStatusQueryValue(GteOrderStatus status) {
  switch (status) {
    case GteOrderStatus.open:
      return 'open';
    case GteOrderStatus.partiallyFilled:
      return 'partially_filled';
    case GteOrderStatus.filled:
      return 'filled';
    case GteOrderStatus.cancelled:
      return 'cancelled';
    case GteOrderStatus.rejected:
      return 'rejected';
    case GteOrderStatus.unknown:
      return 'unknown';
  }
}

String _serializeWithdrawalStatus(GteWithdrawalStatus status) {
  switch (status) {
    case GteWithdrawalStatus.draft:
      return 'draft';
    case GteWithdrawalStatus.pendingKyc:
      return 'pending_kyc';
    case GteWithdrawalStatus.pendingReview:
      return 'pending_review';
    case GteWithdrawalStatus.approved:
      return 'approved';
    case GteWithdrawalStatus.rejected:
      return 'rejected';
    case GteWithdrawalStatus.processing:
      return 'processing';
    case GteWithdrawalStatus.paid:
      return 'paid';
    case GteWithdrawalStatus.disputed:
      return 'disputed';
    case GteWithdrawalStatus.cancelled:
      return 'cancelled';
  }
}
