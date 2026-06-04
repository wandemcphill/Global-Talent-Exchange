import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_models.dart';

import 'capital_wallet_availability.dart';
import 'capital_wallet_display_snapshot.dart';

CapitalWalletApi capitalWalletApiForClient(GteAuthedApi client) {
  return CapitalWalletApi(client: client);
}

CapitalWalletApi capitalWalletApiForRepository(GteApiRepository repository) {
  return CapitalWalletApi(repository: repository);
}

class CapitalWalletApi {
  const CapitalWalletApi({this.client, this.repository})
    : assert(
        client != null || repository != null,
        'CapitalWalletApi requires a live client or repository.',
      );

  final GteAuthedApi? client;
  final GteApiRepository? repository;

  Future<GteWalletSummary> fetchSummary({
    GteLedgerUnit currency = GteLedgerUnit.coin,
  }) async {
    final GteApiRepository? repository = this.repository;
    if (repository != null) {
      return repository.fetchWalletSummary(currency: currency);
    }
    final Map<String, dynamic> payload = await _client.getMap(
      '/wallets/summary',
      query: <String, Object?>{'currency': currency.name},
      auth: true,
    );
    return GteWalletSummary.fromJson(payload);
  }

  Future<CapitalWalletDisplaySnapshot> fetchDisplaySnapshot({
    GteLedgerUnit currency = GteLedgerUnit.coin,
  }) async {
    return CapitalWalletDisplaySnapshot.fromSummary(
      await fetchSummary(currency: currency),
    );
  }

  Future<GteWalletOverview> fetchOverview({
    GteLedgerUnit currency = GteLedgerUnit.coin,
  }) async {
    final GteApiRepository? repository = this.repository;
    if (repository != null) {
      return repository.fetchWalletOverview();
    }
    final Map<String, dynamic> payload = await _client.getMap(
      '/wallets/overview',
      query: <String, Object?>{'currency': currency.name},
      auth: true,
    );
    return GteWalletOverview.fromJson(payload);
  }

  Future<CapitalWalletAvailability> fetchAvailability({
    GteLedgerUnit currency = GteLedgerUnit.coin,
  }) async {
    final GteWalletOverview overview = await fetchOverview(currency: currency);
    return CapitalWalletAvailability.fromWalletOverview(overview);
  }

  Future<List<GteWalletTransactionRecord>> listWalletTransactions({
    int limit = 50,
  }) async {
    final GteApiRepository? repository = this.repository;
    if (repository != null) {
      return repository.listWalletTransactions(limit: limit);
    }
    final List<dynamic> payload = await _client.getList(
      '/api/wallets/transactions',
      query: <String, Object?>{'limit': limit},
      auth: true,
    );
    return payload
        .map(GteWalletTransactionRecord.fromJson)
        .toList(growable: false);
  }

  Future<GteWalletLedgerPage> fetchLedger({
    int page = 1,
    int pageSize = 20,
  }) async {
    final GteApiRepository? repository = this.repository;
    if (repository != null) {
      return repository.fetchWalletLedger(page: page, pageSize: pageSize);
    }
    return GteWalletLedgerPage.fromJson(
      await _client.request(
        'GET',
        '/api/wallets/ledger',
        query: <String, Object?>{'page': page, 'page_size': pageSize},
        auth: true,
      ),
    );
  }

  Future<GteWalletTopUpSession> initiateTopUp(
    GteWalletTopUpInitiateRequest request,
  ) async {
    final GteApiRepository? repository = this.repository;
    if (repository != null) {
      return repository.initiateWalletTopUp(request);
    }
    return GteWalletTopUpSession.fromJson(
      await _client.request(
        'POST',
        '/api/wallets/top-up/initiate',
        body: request.toJson(),
        auth: true,
      ),
    );
  }

  Future<GteWalletTopUpVerificationResult> verifyTopUp(String reference) async {
    final GteApiRepository? repository = this.repository;
    if (repository != null) {
      return repository.verifyWalletTopUp(reference);
    }
    return GteWalletTopUpVerificationResult.fromJson(
      await _client.request(
        'POST',
        '/api/wallets/top-up/verify',
        body: <String, Object?>{'reference': reference},
        auth: true,
      ),
    );
  }

  Future<GteWalletConversionQuote> quoteConversion(
    GteWalletConversionQuoteRequest request,
  ) async {
    final GteApiRepository? repository = this.repository;
    if (repository != null) {
      return repository.quoteWalletConversion(request);
    }
    return GteWalletConversionQuote.fromJson(
      await _client.request(
        'POST',
        '/api/wallets/conversions/quote',
        body: request.toJson(),
        auth: true,
      ),
    );
  }

  Future<GteWalletConversion> createConversion(
    GteWalletConversionRequest request,
  ) async {
    final GteApiRepository? repository = this.repository;
    if (repository != null) {
      return repository.createWalletConversion(request);
    }
    return GteWalletConversion.fromJson(
      await _client.request(
        'POST',
        '/api/wallets/conversions',
        body: request.toJson(),
        auth: true,
      ),
    );
  }

  Future<GteDepositRequest> createDepositRequest(
    GteDepositCreateRequest request,
  ) async {
    final GteApiRepository? repository = this.repository;
    if (repository != null) {
      return repository.createDepositRequest(request);
    }
    return GteDepositRequest.fromJson(
      await _client.request(
        'POST',
        '/api/wallets/deposits',
        body: request.toJson(),
        auth: true,
      ),
    );
  }

  Future<GteDepositRequest> submitDepositRequest(
    String depositId,
    GteDepositSubmitRequest request,
  ) async {
    final GteApiRepository? repository = this.repository;
    if (repository != null) {
      return repository.submitDepositRequest(depositId, request);
    }
    return GteDepositRequest.fromJson(
      await _client.request(
        'POST',
        '/api/wallets/deposits/$depositId/submit',
        body: request.toJson(),
        auth: true,
      ),
    );
  }

  Future<List<GteDepositRequest>> listDepositRequests() async {
    final GteApiRepository? repository = this.repository;
    if (repository != null) {
      return repository.listDepositRequests();
    }
    final List<dynamic> payload = await _client.getList(
      '/api/wallets/deposits',
      auth: true,
    );
    return payload.map(GteDepositRequest.fromJson).toList(growable: false);
  }

  Future<GteWithdrawalEligibility> fetchWithdrawalEligibility() async {
    final GteApiRepository? repository = this.repository;
    if (repository != null) {
      return repository.fetchWithdrawalEligibility();
    }
    return GteWithdrawalEligibility.fromJson(
      await _client.request(
        'GET',
        '/api/wallets/withdrawals/eligibility',
        auth: true,
      ),
    );
  }

  Future<GteWithdrawalQuote> fetchWithdrawalQuote(
    GteWithdrawalQuoteRequest request,
  ) async {
    final GteApiRepository? repository = this.repository;
    if (repository != null) {
      return repository.fetchWithdrawalQuote(request);
    }
    return GteWithdrawalQuote.fromJson(
      await _client.request(
        'POST',
        '/api/wallets/withdrawals/quote',
        body: request.toJson(),
        auth: true,
      ),
    );
  }

  Future<GteTreasuryWithdrawalRequest> createWithdrawalRequest(
    GteWithdrawalCreateRequest request,
  ) async {
    final GteApiRepository? repository = this.repository;
    if (repository != null) {
      return repository.createWithdrawalRequest(request);
    }
    return GteTreasuryWithdrawalRequest.fromJson(
      await _client.request(
        'POST',
        '/api/wallets/withdrawals',
        body: request.toJson(),
        auth: true,
      ),
    );
  }

  Future<GteWithdrawalReceipt> fetchWithdrawalReceipt(
    String withdrawalId,
  ) async {
    final GteApiRepository? repository = this.repository;
    if (repository != null) {
      return repository.fetchWithdrawalReceipt(withdrawalId);
    }
    return GteWithdrawalReceipt.fromJson(
      await _client.request(
        'GET',
        '/api/wallets/withdrawals/$withdrawalId/receipt',
        auth: true,
      ),
    );
  }

  Future<List<GteTreasuryWithdrawalRequest>> listWithdrawalRequests() async {
    final GteApiRepository? repository = this.repository;
    if (repository != null) {
      return repository.listWithdrawalRequests();
    }
    final List<dynamic> payload = await _client.getList(
      '/api/wallets/withdrawals',
      auth: true,
    );
    return payload
        .map(GteTreasuryWithdrawalRequest.fromJson)
        .toList(growable: false);
  }

  Future<List<GtePolicyDocumentSummary>> fetchPolicyDocuments({
    bool mandatoryOnly = false,
  }) async {
    final GteApiRepository? repository = this.repository;
    if (repository != null) {
      return repository.fetchPolicyDocuments(mandatoryOnly: mandatoryOnly);
    }
    final List<dynamic> payload = await _client.getList(
      '/policies/documents',
      query: <String, Object?>{'mandatory_only': mandatoryOnly},
      auth: true,
    );
    return payload
        .map(GtePolicyDocumentSummary.fromJson)
        .toList(growable: false);
  }

  Future<GtePolicyDocumentDetail> fetchPolicyDocument(
    String documentKey, {
    String? versionLabel,
  }) async {
    final GteApiRepository? repository = this.repository;
    if (repository != null) {
      return repository.fetchPolicyDocument(
        documentKey,
        versionLabel: versionLabel,
      );
    }
    final Map<String, dynamic> payload = await _client.getMap(
      '/policies/documents/$documentKey',
      query: <String, Object?>{
        if (versionLabel != null) 'version_label': versionLabel,
      },
      auth: true,
    );
    return GtePolicyDocumentDetail.fromJson(payload);
  }

  Future<List<GtePolicyAcceptanceSummary>> fetchMyPolicyAcceptances() async {
    final GteApiRepository? repository = this.repository;
    if (repository != null) {
      return repository.fetchMyPolicyAcceptances();
    }
    final List<dynamic> payload = await _client.getList(
      '/policies/me/acceptances',
      auth: true,
    );
    return payload
        .map(GtePolicyAcceptanceSummary.fromJson)
        .toList(growable: false);
  }

  Future<GtePolicyAcceptanceSummary> acceptPolicyDocument(
    String documentKey,
    String versionLabel,
  ) async {
    final GteApiRepository? repository = this.repository;
    if (repository != null) {
      return repository.acceptPolicyDocument(documentKey, versionLabel);
    }
    final Map<String, Object?> payload = GteJson.map(
      await _client.request(
        'POST',
        '/policies/acceptances',
        body: <String, Object?>{
          'document_key': documentKey,
          'version_label': versionLabel,
        },
        auth: true,
      ),
      label: 'policy acceptance response',
    );
    return GtePolicyAcceptanceSummary(
      documentKey: GteJson.string(payload, <String>[
        'document_key',
        'documentKey',
      ]),
      title: documentKey,
      versionLabel: GteJson.string(payload, <String>[
        'version_label',
        'versionLabel',
      ]),
      acceptedAt: GteJson.dateTimeOrNull(payload, <String>[
        'accepted_at',
        'acceptedAt',
      ]),
    );
  }

  Future<GteComplianceStatus> fetchComplianceStatus() async {
    final GteApiRepository? repository = this.repository;
    if (repository != null) {
      return repository.fetchComplianceStatus();
    }
    final Map<String, dynamic> payload = await _client.getMap(
      '/policies/me/compliance',
      auth: true,
    );
    return GteComplianceStatus.fromJson(payload);
  }

  Future<List<GtePolicyRequirementSummary>> fetchPolicyRequirements() async {
    final GteApiRepository? repository = this.repository;
    if (repository != null) {
      return repository.fetchPolicyRequirements();
    }
    final List<dynamic> payload = await _client.getList(
      '/policies/me/requirements',
      auth: true,
    );
    return payload
        .map(GtePolicyRequirementSummary.fromJson)
        .toList(growable: false);
  }

  Future<CapitalWalletMarketSnapshot> fetchMarketSnapshot() async {
    final List<dynamic> payload = await Future.wait<dynamic>(<Future<dynamic>>[
      fetchDisplaySnapshot(currency: GteLedgerUnit.coin),
      fetchDisplaySnapshot(currency: GteLedgerUnit.credit),
      fetchOverview(),
      fetchComplianceStatus(),
    ], eagerError: true);
    return CapitalWalletMarketSnapshot.fromBackend(
      coinSnapshot: payload[0] as CapitalWalletDisplaySnapshot,
      creditSnapshot: payload[1] as CapitalWalletDisplaySnapshot,
      overview: payload[2] as GteWalletOverview,
      compliance: payload[3] as GteComplianceStatus,
    );
  }

  Future<GteKycProfile> fetchKycProfile() async {
    final GteApiRepository? repository = this.repository;
    if (repository != null) {
      return repository.fetchKycProfile();
    }
    return GteKycProfile.fromJson(
      await _client.request('GET', '/api/kyc', auth: true),
    );
  }

  Future<GteKycProfile> submitKycProfile(GteKycSubmitRequest request) async {
    final GteApiRepository? repository = this.repository;
    if (repository != null) {
      return repository.submitKycProfile(request);
    }
    return GteKycProfile.fromJson(
      await _client.request(
        'POST',
        '/api/kyc',
        body: request.toJson(),
        auth: true,
      ),
    );
  }

  Future<GteAttachment> uploadAttachment(
    String filename,
    List<int> bytes, {
    String? contentType,
  }) async {
    final GteApiRepository? repository = this.repository;
    if (repository == null) {
      throw const CapitalWalletUnavailableException(
        'Capital wallet attachment upload requires repository transport.',
      );
    }
    return repository.uploadAttachment(
      filename,
      bytes,
      contentType: contentType,
    );
  }

  Future<List<GteUserBankAccount>> listUserBankAccounts() async {
    final GteApiRepository? repository = this.repository;
    if (repository != null) {
      return repository.listUserBankAccounts();
    }
    final List<dynamic> payload = await _client.getList(
      '/api/bank-accounts',
      auth: true,
    );
    return payload.map(GteUserBankAccount.fromJson).toList(growable: false);
  }

  Future<GteUserBankAccount> createUserBankAccount(
    GteUserBankAccountCreate request,
  ) async {
    final GteApiRepository? repository = this.repository;
    if (repository != null) {
      return repository.createUserBankAccount(request);
    }
    return GteUserBankAccount.fromJson(
      await _client.request(
        'POST',
        '/api/bank-accounts',
        body: request.toJson(),
        auth: true,
      ),
    );
  }

  Future<GteUserBankAccount> updateUserBankAccount(
    String bankAccountId,
    GteUserBankAccountUpdate request,
  ) async {
    final GteApiRepository? repository = this.repository;
    if (repository != null) {
      return repository.updateUserBankAccount(bankAccountId, request);
    }
    return GteUserBankAccount.fromJson(
      await _client.request(
        'PUT',
        '/api/bank-accounts/$bankAccountId',
        body: request.toJson(),
        auth: true,
      ),
    );
  }

  GteAuthedApi get _client {
    final GteAuthedApi? client = this.client;
    if (client == null) {
      throw const CapitalWalletUnavailableException(
        'Capital wallet client is unavailable.',
      );
    }
    return client;
  }
}

class CapitalWalletUnavailableException extends GteApiException {
  const CapitalWalletUnavailableException(String message)
    : super(type: GteApiErrorType.unavailable, message: message);
}

class CapitalWalletMarketSnapshot {
  const CapitalWalletMarketSnapshot({
    required this.coinAvailableBalance,
    required this.creditAvailableBalance,
    required this.totalCoinBalance,
    required this.reservedCoinBalance,
    required this.lockedCoinBalance,
    required this.pendingWithdrawalCoinBalance,
    required this.lockReasons,
    required this.canTradeMarket,
    required this.canDeposit,
    required this.canWithdraw,
    required this.complianceMessage,
  });

  final double coinAvailableBalance;
  final double creditAvailableBalance;
  final double totalCoinBalance;
  final double reservedCoinBalance;
  final double lockedCoinBalance;
  final double pendingWithdrawalCoinBalance;
  final List<String> lockReasons;
  final bool canTradeMarket;
  final bool canDeposit;
  final bool canWithdraw;
  final String complianceMessage;

  factory CapitalWalletMarketSnapshot.fromBackend({
    required CapitalWalletDisplaySnapshot coinSnapshot,
    required CapitalWalletDisplaySnapshot creditSnapshot,
    required GteWalletOverview overview,
    required GteComplianceStatus compliance,
  }) {
    return CapitalWalletMarketSnapshot(
      coinAvailableBalance: overview.availableBalance,
      creditAvailableBalance: creditSnapshot.availableBalance,
      totalCoinBalance: coinSnapshot.totalBalance,
      reservedCoinBalance: overview.reservedBalance,
      lockedCoinBalance: overview.lockedBalance,
      pendingWithdrawalCoinBalance: overview.pendingWithdrawals,
      lockReasons: overview.lockReasons,
      canTradeMarket: compliance.canTradeMarket,
      canDeposit: compliance.canDeposit,
      canWithdraw: compliance.canWithdrawPlatformRewards,
      complianceMessage:
          overview.policyBlocked
              ? overview.policyBlockReason ??
                  'Policy restrictions are blocking wallet actions.'
              : compliance.hasMissingRequiredPolicies
              ? 'Compliance action required before full trading is enabled.'
              : 'Wallet and compliance state loaded from live backend.',
    );
  }
}
