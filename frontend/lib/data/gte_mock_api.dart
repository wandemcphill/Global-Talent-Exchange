import 'dart:async';

import '../features/capital/disputes/data/capital_dispute_fixture_store.dart';
import '../features/capital/payouts/data/capital_payout_fixture_store.dart';
import '../features/capital/settlement/data/capital_deposit_fixture_store.dart';
import '../features/capital/settlement/data/capital_policy_fixture_store.dart';
import '../features/capital/settlement/data/capital_treasury_dashboard_fixture_store.dart';
import '../features/capital/settlement/data/capital_treasury_fixture_store.dart';
import '../features/capital/trader/data/capital_buyback_fixture_store.dart';
import '../features/capital/trader/data/capital_portfolio_fixture_store.dart';
import '../features/capital/trader/data/capital_trader_fixture_store.dart';
import '../features/capital/wallet/data/capital_wallet_fixture_store.dart';
import 'gte_api_repository.dart';
import 'gte_models.dart';

class GteMockApi implements GteApiRepository {
  GteMockApi({
    this.latency = const Duration(milliseconds: 250),
    bool enableCapitalFixtures = false,
  }) : _capitalFixturesEnabled = enableCapitalFixtures,
       _catalog = _seedCatalog.map(_cloneSnapshot).toList(growable: false),
       _profiles = _seedProfiles.map(
         (String key, PlayerProfile value) =>
             MapEntry<String, PlayerProfile>(key, _cloneProfile(value)),
       ),
       _candles = _seedCandles.map(
         (String key, GteMarketCandles value) =>
             MapEntry<String, GteMarketCandles>(key, _cloneCandles(value)),
       ),
       _capitalWallet = CapitalWalletFixtureStore.seeded(),
       _capitalTreasury = CapitalTreasuryFixtureStore.seeded(),
       _capitalDisputes = CapitalDisputeFixtureStore.seeded(),
       _capitalPolicy = CapitalPolicyFixtureStore.seeded(),
       _notifications = List<GteNotification>.of(
         _seedNotifications,
         growable: true,
       ),
       _attachments = <GteAttachment>[],
       _analyticsEvents = List<GteAnalyticsEvent>.of(
         _seedAnalyticsEvents,
         growable: true,
       ) {
    _capitalDeposits = CapitalDepositFixtureStore.seeded(
      wallet: _capitalWallet,
      treasury: _capitalTreasury,
    );
    _capitalPayout = CapitalPayoutFixtureStore.seeded(
      wallet: _capitalWallet,
      treasury: _capitalTreasury,
    );
    _capitalDashboard = CapitalTreasuryDashboardFixtureStore(
      wallet: _capitalWallet,
      deposits: _capitalDeposits,
      payouts: _capitalPayout,
      disputes: _capitalDisputes,
    );
    _capitalPortfolio = CapitalPortfolioFixtureStore.seeded(
      wallet: _capitalWallet,
    );
    _capitalTrader = CapitalTraderFixtureStore.seeded(
      wallet: _capitalWallet,
      onWalletMutation: _capitalPortfolio.rebuildPortfolioSummary,
    );
    _capitalBuyback = CapitalBuybackFixtureStore(
      trader: _capitalTrader,
      portfolio: _capitalPortfolio,
      wallet: _capitalWallet,
    );
  }

  factory GteMockApi.capitalFixtures({
    Duration latency = const Duration(milliseconds: 250),
  }) {
    return GteMockApi(latency: latency, enableCapitalFixtures: true);
  }

  final Duration latency;
  final bool _capitalFixturesEnabled;
  final List<PlayerSnapshot> _catalog;
  final Map<String, PlayerProfile> _profiles;
  final Map<String, GteMarketCandles> _candles;

  final CapitalWalletFixtureStore _capitalWallet;
  final CapitalTreasuryFixtureStore _capitalTreasury;
  late final CapitalDepositFixtureStore _capitalDeposits;
  late final CapitalPayoutFixtureStore _capitalPayout;
  late final CapitalTreasuryDashboardFixtureStore _capitalDashboard;
  late final CapitalPortfolioFixtureStore _capitalPortfolio;
  late final CapitalTraderFixtureStore _capitalTrader;
  late final CapitalBuybackFixtureStore _capitalBuyback;
  final CapitalDisputeFixtureStore _capitalDisputes;
  final CapitalPolicyFixtureStore _capitalPolicy;
  final List<GteNotification> _notifications;
  final List<GteAttachment> _attachments;
  final List<GteAnalyticsEvent> _analyticsEvents;

  int _notificationSequence = _seedNotifications.length;
  int _attachmentSequence = 0;
  DateTime _clock = DateTime.utc(2026, 3, 11, 12, 0);

  @override
  Future<GteAuthSession> login(GteAuthLoginRequest request) async {
    await _delay();
    return _fixtureSession;
  }

  @override
  Future<GteAuthSession> signupPlayer(
    GtePlayerFrictionlessSignupRequest request,
  ) async {
    await _delay();
    return _signupSession(
      email: request.email,
      username: request.email.split('@').first,
      fullName: request.fullName,
      accountType: 'user',
      landingRoute: '/app/world',
    );
  }

  @override
  Future<GteAuthSession> signupOrganization(
    GteOrganizationFrictionlessSignupRequest request,
  ) async {
    await _delay();
    return _signupSession(
      email: request.email,
      username: request.email.split('@').first,
      fullName: request.contactName,
      accountType: 'user',
      landingRoute: '/app/world',
    );
  }

  @override
  Future<GteRecoveryChallenge> requestRecoveryChallenge(String email) async {
    await _delay();
    return GteRecoveryChallenge(
      email: email,
      questions: <GteRecoveryChallengeQuestion>[
        GteRecoveryChallengeQuestion(
          id: 'fixture-question-1',
          question: 'Custom recovery question 1',
        ),
        GteRecoveryChallengeQuestion(
          id: 'fixture-question-2',
          question: 'Custom recovery question 2',
        ),
      ],
    );
  }

  @override
  Future<void> resetPasswordWithRecoveryQuestions(
    GteRecoveryQuestionResetRequest request,
  ) async {
    await _delay();
  }

  @override
  Future<void> verifyPin(GtePinVerificationRequest request) async {
    await _delay();
  }

  GteAuthSession _signupSession({
    required String email,
    required String username,
    required String fullName,
    required String accountType,
    required String landingRoute,
  }) {
    final DateTime now = _nextTimestamp();
    return GteAuthSession(
      accessToken: 'fixture-$username-token',
      refreshToken: 'fixture-$username-refresh-token',
      sessionId: 'fixture-$username-session',
      tokenType: 'bearer',
      expiresIn: 3600,
      refreshExpiresIn: 2592000,
      user: GteCurrentUser(
        id: 'fixture-$username',
        email: email,
        username: username,
        fullName: fullName,
        phoneNumber: null,
        displayName: fullName,
        role: 'user',
        accountType: accountType,
        ageConfirmedAt: now,
      ),
      landingRoute: landingRoute,
    );
  }

  @override
  Future<GteCurrentUser> fetchCurrentUser() async {
    await _delay();
    return _fixtureSession.user;
  }

  @override
  Future<void> logout() async {}

  @override
  Future<List<GtePolicyDocumentSummary>> fetchPolicyDocuments({
    bool mandatoryOnly = false,
  }) async {
    await _delay();
    return _capitalPolicy.fetchPolicyDocuments(mandatoryOnly: mandatoryOnly);
  }

  @override
  Future<GtePolicyDocumentDetail> fetchPolicyDocument(
    String documentKey, {
    String? versionLabel,
  }) async {
    await _delay();
    return _capitalPolicy.fetchPolicyDocument(
      documentKey,
      versionLabel: versionLabel,
    );
  }

  @override
  Future<GteComplianceStatus> fetchComplianceStatus() async {
    await _delay();
    return _capitalPolicy.fetchComplianceStatus(
      countryCode: _capitalWallet.countryCode,
    );
  }

  @override
  Future<List<GtePolicyRequirementSummary>> fetchPolicyRequirements() async {
    await _delay();
    return _capitalPolicy.currentMissingPolicyRequirements();
  }

  @override
  Future<List<GtePolicyAcceptanceSummary>> fetchMyPolicyAcceptances() async {
    await _delay();
    return _capitalPolicy.fetchMyPolicyAcceptances();
  }

  @override
  Future<GtePolicyAcceptanceSummary> acceptPolicyDocument(
    String documentKey,
    String versionLabel,
  ) async {
    await _delay();
    return _capitalPolicy.acceptPolicyDocument(
      documentKey: documentKey,
      versionLabel: versionLabel,
      acceptedAt: _nextTimestamp(),
    );
  }

  @override
  Future<List<PlayerSnapshot>> fetchPlayers({int limit = 20}) async {
    await _delay();
    return _catalog.take(limit).map(_cloneSnapshot).toList(growable: false);
  }

  @override
  Future<PlayerProfile> fetchPlayerProfile(String playerId) async {
    await _delay();
    final PlayerProfile? profile = _profiles[playerId];
    if (profile == null) {
      throw StateError('Unknown player id: $playerId');
    }
    return _cloneProfile(profile);
  }

  @override
  Future<MarketPulse> fetchMarketPulse() async {
    await _delay();
    return _marketPulse.copyWith(
      tickers: List<String>.from(_marketPulse.tickers),
      transferRoom: List<TransferRoomEntry>.from(_marketPulse.transferRoom),
    );
  }

  @override
  Future<GteMarketTicker> fetchTicker(String playerId) async {
    await _delay();
    return _capitalTrader.fetchTicker(playerId);
  }

  @override
  Future<GteMarketCandles> fetchCandles(
    String playerId, {
    String interval = '1h',
    int limit = 30,
  }) async {
    await _delay();
    final GteMarketCandles? candles = _candles[playerId];
    if (candles == null) {
      throw StateError('Unknown candle player id: $playerId');
    }
    final List<GteMarketCandle> trimmed = candles.candles
        .take(limit)
        .toList(growable: false);
    return GteMarketCandles(
      playerId: playerId,
      interval: interval,
      candles: trimmed,
    );
  }

  @override
  Future<GteOrderBook> fetchOrderBook(String playerId) async {
    await _delay();
    return _capitalTrader.fetchOrderBook(playerId, generatedAt: _clock);
  }

  @override
  Future<GteOrderListView> listOrders({
    int limit = 20,
    int offset = 0,
    List<GteOrderStatus>? statuses,
  }) async {
    await _delayCapitalFixture();
    return _capitalTrader.listOrders(
      limit: limit,
      offset: offset,
      statuses: statuses,
    );
  }

  @override
  Future<GteOrderRecord> fetchOrder(String orderId) async {
    await _delayCapitalFixture();
    return _capitalTrader.fetchOrder(orderId);
  }

  @override
  Future<GteOrderRecord> placeOrder(GteOrderCreateRequest request) async {
    await _delayCapitalFixture();
    return _capitalTrader.placeOrder(
      request: request,
      userId: _fixtureSession.user.id,
      timestamp: _nextTimestamp(),
    );
  }

  @override
  Future<GteOrderRecord> cancelOrder(String orderId) async {
    await _delayCapitalFixture();
    return _capitalTrader.cancelOrder(
      orderId: orderId,
      timestamp: _nextTimestamp(),
    );
  }

  @override
  Future<GteAdminBuybackPreview> fetchAdminBuybackPreview(
    String orderId,
  ) async {
    await _delayCapitalFixture();
    return _capitalBuyback.fetchAdminBuybackPreview(
      orderId: orderId,
      now: _clock,
    );
  }

  @override
  Future<GteAdminBuybackExecution> executeAdminBuyback(String orderId) async {
    await _delayCapitalFixture();
    return _capitalBuyback.executeAdminBuyback(
      orderId: orderId,
      now: _clock,
      executedAt: _nextTimestamp(),
    );
  }

  @override
  Future<GteWalletSummary> fetchWalletSummary({
    GteLedgerUnit currency = GteLedgerUnit.coin,
  }) async {
    await _delayCapitalFixture();
    return currency == GteLedgerUnit.credit
        ? _capitalWallet.fanSummary
        : _capitalWallet.coinSummary;
  }

  @override
  Future<GteUserWallet> fetchWallet() async {
    await _delayCapitalFixture();
    return GteUserWallet(
      id: 'wallet-fixture',
      userId: _fixtureSession.user.id,
      balance: _capitalWallet.coinSummary.availableBalance,
      currency: _capitalWallet.coinSummary.currency.name,
      complianceStatus: 'verified',
      createdAt: _clock,
    );
  }

  @override
  Future<GteWalletLedgerPage> fetchWalletLedger({
    int page = 1,
    int pageSize = 20,
  }) async {
    await _delayCapitalFixture();
    final int offset = (page - 1) * pageSize;
    final List<GteWalletLedgerEntry> items = _capitalWallet.ledger
        .skip(offset)
        .take(pageSize)
        .toList(growable: false);
    return GteWalletLedgerPage(
      page: page,
      pageSize: pageSize,
      total: _capitalWallet.ledger.length,
      items: items,
    );
  }

  @override
  Future<GteWalletOverview> fetchWalletOverview() async {
    await _delayCapitalFixture();
    return _buildWalletOverview();
  }

  @override
  Future<List<GteWalletTransactionRecord>> listWalletTransactions({
    int limit = 50,
  }) async {
    await _delayCapitalFixture();
    return _capitalWallet.transactions.take(limit).toList(growable: false);
  }

  @override
  Future<GteWalletTopUpSession> initiateWalletTopUp(
    GteWalletTopUpInitiateRequest request,
  ) async {
    await _delayCapitalFixture();
    final String reference = _capitalWallet.nextTransactionReference('WTX');
    final String provider = request.provider.trim().toLowerCase();
    if (provider != 'korapay') {
      throw const GteApiException(
        type: GteApiErrorType.validation,
        message: 'KoraPay is the only automatic wallet top-up provider.',
      );
    }
    final GteWalletTopUpSession session = GteWalletTopUpSession(
      reference: reference,
      paymentLink: 'https://mock.korapay.local/$reference',
      amount: request.amount,
      currency: request.unit.name,
      provider: provider,
      status: 'pending',
      mockMode: true,
    );
    _capitalWallet.putTopUpSession(
      reference,
      session,
      GteWalletTransactionRecord(
        id: 'wallet-txn-$reference',
        userId: _fixtureSession.user.id,
        type: 'credit',
        amount: request.amount,
        status: 'pending',
        reference: reference,
        createdAt: _nextTimestamp(),
      ),
    );
    return session;
  }

  @override
  Future<GteWalletTopUpVerificationResult> verifyWalletTopUp(
    String reference,
  ) async {
    await _delayCapitalFixture();
    final GteWalletTopUpSession? pendingSession = _capitalWallet.topUpSession(
      reference,
    );
    if (pendingSession == null) {
      throw const GteApiException(
        type: GteApiErrorType.notFound,
        message: 'Top-up reference was not found.',
      );
    }
    final GteWalletTransactionRecord existing = _capitalWallet
        .transactionForReference(reference);
    final DateTime timestamp = _nextTimestamp();
    final GteWalletTransactionRecord updated = GteWalletTransactionRecord(
      id: existing.id,
      userId: existing.userId,
      type: existing.type,
      amount: existing.amount,
      status: 'verified',
      reference: existing.reference,
      createdAt: existing.createdAt ?? timestamp,
    );
    _capitalWallet.verifyTopUp(
      reference: reference,
      updated: updated,
      createdAt: timestamp,
    );
    _capitalPortfolio.rebuildPortfolioSummary();
    return GteWalletTopUpVerificationResult(
      wallet: await fetchWallet(),
      transaction: updated,
    );
  }

  @override
  Future<GteWalletConversionQuote> quoteWalletConversion(
    GteWalletConversionQuoteRequest request,
  ) async {
    await _delayCapitalFixture();
    return _buildWalletConversionQuote(request);
  }

  @override
  Future<GteWalletConversion> createWalletConversion(
    GteWalletConversionRequest request,
  ) async {
    await _delayCapitalFixture();
    final GteWalletConversionQuote quote = _buildWalletConversionQuote(request);
    if (_capitalWallet.coinSummary.availableBalance < quote.sourceAmount) {
      throw const GteApiException(
        type: GteApiErrorType.validation,
        message:
            'Available GTEX Coin balance is lower than the requested conversion amount.',
      );
    }
    final String reference = _capitalWallet.nextTransactionReference('WCV');
    final DateTime timestamp = _nextTimestamp();
    _capitalWallet.convertCoinToFan(
      sourceAmount: quote.sourceAmount,
      targetAmount: quote.targetAmount,
      reference: reference,
      userId: _fixtureSession.user.id,
      createdAt: timestamp,
    );
    _capitalPortfolio.rebuildPortfolioSummary();
    return GteWalletConversion(
      transactionId: 'txn-$reference',
      reference: reference,
      sourceUnit: quote.sourceUnit,
      sourceAmount: quote.sourceAmount,
      targetUnit: quote.targetUnit,
      targetAmount: quote.targetAmount,
      rate: quote.rate,
    );
  }

  @override
  Future<GteWithdrawalEligibility> fetchWithdrawalEligibility() async {
    await _delayCapitalFixture();
    return _capitalPayout.fetchWithdrawalEligibility(
      now: _clock,
      missingPolicies: _capitalPolicy.currentMissingPolicyRequirements(),
    );
  }

  @override
  Future<GteWithdrawalQuote> fetchWithdrawalQuote(
    GteWithdrawalQuoteRequest request,
  ) async {
    await _delayCapitalFixture();
    return _capitalPayout.fetchWithdrawalQuote(
      request: request,
      now: _clock,
      missingPolicies: _capitalPolicy.currentMissingPolicyRequirements(),
    );
  }

  @override
  Future<GteWithdrawalReceipt> fetchWithdrawalReceipt(
    String withdrawalId,
  ) async {
    await _delayCapitalFixture();
    return _capitalPayout.fetchWithdrawalReceipt(
      withdrawalId: withdrawalId,
      nextTimestamp: _nextTimestamp,
    );
  }

  @override
  Future<GteDepositRequest> createDepositRequest(
    GteDepositCreateRequest request,
  ) async {
    await _delayCapitalFixture();
    final DateTime createdAt = _nextTimestamp();
    final GteDepositRequest deposit = _capitalDeposits.createDepositRequest(
      request: request,
      createdAt: createdAt,
    );
    _pushNotification(
      topic: 'deposit_request_created',
      message:
          'Deposit ${deposit.reference} created. Awaiting payment confirmation.',
      resourceId: deposit.id,
    );
    return deposit;
  }

  @override
  Future<GteDepositRequest> submitDepositRequest(
    String depositId,
    GteDepositSubmitRequest request,
  ) async {
    await _delayCapitalFixture();
    final GteDepositRequest updated = _capitalDeposits.submitDepositRequest(
      depositId: depositId,
      request: request,
      submittedAt: _nextTimestamp(),
    );
    _pushNotification(
      topic: 'deposit_submitted',
      message:
          'Payment submitted for ${updated.reference}. The treasury team is reviewing it.',
      resourceId: updated.id,
    );
    return updated;
  }

  @override
  Future<List<GteDepositRequest>> listDepositRequests() async {
    await _delayCapitalFixture();
    return _capitalDeposits.listDepositRequests();
  }

  @override
  Future<GteTreasuryWithdrawalRequest> createWithdrawalRequest(
    GteWithdrawalCreateRequest request,
  ) async {
    await _delayCapitalFixture();
    final DateTime eligibilityNow = _clock;
    final DateTime createdAt = _nextTimestamp();
    final GteTreasuryWithdrawalRequest withdrawal = _capitalPayout
        .createWithdrawalRequest(
          request: request,
          eligibilityNow: eligibilityNow,
          createdAt: createdAt,
          missingPolicies: _capitalPolicy.currentMissingPolicyRequirements(),
        );
    _pushNotification(
      topic: 'withdrawal_requested',
      message:
          'Withdrawal ${withdrawal.reference} queued for review. Status: pending review.',
      resourceId: withdrawal.id,
    );
    return withdrawal;
  }

  @override
  Future<List<GteTreasuryWithdrawalRequest>> listWithdrawalRequests() async {
    await _delayCapitalFixture();
    return _capitalPayout.listWithdrawalRequests();
  }

  @override
  Future<GteKycProfile> fetchKycProfile() async {
    await _delayCapitalFixture();
    return _capitalWallet.kycProfile;
  }

  @override
  Future<GteKycProfile> submitKycProfile(GteKycSubmitRequest request) async {
    await _delayCapitalFixture();
    final DateTime now = _nextTimestamp();
    final GteKycProfile profile = _capitalWallet.submitKycProfile(
      request: request,
      submittedAt: now,
    );
    _pushNotification(
      topic: 'kyc_submitted',
      message: 'KYC submitted. Verification is now pending.',
      resourceId: profile.id,
    );
    return profile;
  }

  @override
  Future<List<GteUserBankAccount>> listUserBankAccounts() async {
    await _delayCapitalFixture();
    return _capitalWallet.listUserBankAccounts();
  }

  @override
  Future<GteUserBankAccount> createUserBankAccount(
    GteUserBankAccountCreate request,
  ) async {
    await _delayCapitalFixture();
    final DateTime now = _nextTimestamp();
    final GteUserBankAccount account = _capitalWallet.createUserBankAccount(
      request: request,
      createdAt: now,
    );
    _pushNotification(
      topic: 'bank_details_created',
      message: 'Bank details saved for withdrawals.',
      resourceId: account.id,
    );
    return account;
  }

  @override
  Future<GteUserBankAccount> updateUserBankAccount(
    String bankAccountId,
    GteUserBankAccountUpdate request,
  ) async {
    await _delayCapitalFixture();
    final DateTime now = _nextTimestamp();
    final GteUserBankAccount updated = _capitalWallet.updateUserBankAccount(
      bankAccountId: bankAccountId,
      request: request,
      updatedAt: now,
    );
    _pushNotification(
      topic: 'bank_details_updated',
      message: 'Bank details updated.',
      resourceId: updated.id,
    );
    return updated;
  }

  @override
  Future<List<GteDispute>> listDisputes() async {
    await _delay();
    return _capitalDisputes.listDisputes();
  }

  @override
  Future<GteDispute> openDispute(GteDisputeCreateRequest request) async {
    await _delay();
    return _capitalDisputes.openDispute(
      request: request,
      user: _fixtureSession.user,
      createdAt: _nextTimestamp(),
      notify: _pushNotification,
    );
  }

  @override
  Future<GteDispute> fetchDispute(String disputeId) async {
    await _delay();
    return _capitalDisputes.fetchDispute(disputeId);
  }

  @override
  Future<GteDisputeMessage> sendDisputeMessage(
    String disputeId,
    GteDisputeMessageRequest request,
  ) async {
    await _delay();
    return _capitalDisputes.sendUserMessage(
      disputeId: disputeId,
      request: request,
      user: _fixtureSession.user,
      createdAt: _nextTimestamp(),
      notify: _pushNotification,
    );
  }

  @override
  Future<List<GteNotification>> listNotifications({int limit = 20}) async {
    await _delay();
    final List<GteNotification> sorted = List<GteNotification>.of(
      _notifications,
      growable: false,
    )..sort(
      (GteNotification a, GteNotification b) =>
          (b.createdAt ?? DateTime(0)).compareTo(a.createdAt ?? DateTime(0)),
    );
    return sorted.take(limit).toList(growable: false);
  }

  @override
  Future<void> markNotificationRead(String notificationId) async {
    await _delay();
    final int index = _notifications.indexWhere(
      (GteNotification notification) =>
          notification.notificationId == notificationId,
    );
    if (index == -1) {
      return;
    }
    final GteNotification existing = _notifications[index];
    if (existing.isRead) {
      return;
    }
    _notifications[index] = GteNotification(
      notificationId: existing.notificationId,
      userId: existing.userId,
      topic: existing.topic,
      templateKey: existing.templateKey,
      resourceId: existing.resourceId,
      fixtureId: existing.fixtureId,
      competitionId: existing.competitionId,
      message: existing.message,
      metadata: existing.metadata,
      createdAt: existing.createdAt,
      readAt: _nextTimestamp(),
      isRead: true,
    );
  }

  @override
  Future<void> markAllNotificationsRead() async {
    await _delay();
    for (int i = 0; i < _notifications.length; i++) {
      final GteNotification existing = _notifications[i];
      if (existing.isRead) {
        continue;
      }
      _notifications[i] = GteNotification(
        notificationId: existing.notificationId,
        userId: existing.userId,
        topic: existing.topic,
        templateKey: existing.templateKey,
        resourceId: existing.resourceId,
        fixtureId: existing.fixtureId,
        competitionId: existing.competitionId,
        message: existing.message,
        metadata: existing.metadata,
        createdAt: existing.createdAt,
        readAt: _nextTimestamp(),
        isRead: true,
      );
    }
  }

  @override
  Future<GteAttachment> uploadAttachment(
    String filename,
    List<int> bytes, {
    String? contentType,
  }) async {
    await _delay();
    final DateTime now = _nextTimestamp();
    final GteAttachment attachment = GteAttachment(
      id: 'attachment-${++_attachmentSequence}',
      filename: filename,
      contentType: contentType ?? 'application/octet-stream',
      sizeBytes: bytes.length,
      createdAt: now,
    );
    _attachments.add(attachment);
    return attachment;
  }

  @override
  Future<GteAnalyticsEvent> trackAnalyticsEvent(
    String name, {
    Map<String, Object?> metadata = const <String, Object?>{},
  }) async {
    await _delay();
    final DateTime now = _nextTimestamp();
    final GteAnalyticsEvent event = GteAnalyticsEvent(
      id: 'evt-${_analyticsEvents.length + 1}',
      name: name,
      userId: _fixtureSession.user.id,
      metadata: metadata,
      createdAt: now,
    );
    _analyticsEvents.add(event);
    return event;
  }

  @override
  Future<GteAnalyticsSummary> fetchAnalyticsSummary() async {
    await _delay();
    final Map<String, int> counts = <String, int>{};
    for (final GteAnalyticsEvent event in _analyticsEvents) {
      counts[event.name] = (counts[event.name] ?? 0) + 1;
    }
    final List<GteAnalyticsSummaryItem> totals = counts.entries
        .map(
          (MapEntry<String, int> entry) =>
              GteAnalyticsSummaryItem(name: entry.key, count: entry.value),
        )
        .toList(growable: false);
    return GteAnalyticsSummary(
      since:
          _analyticsEvents.isEmpty ? _clock : _analyticsEvents.first.createdAt,
      totals: totals,
    );
  }

  @override
  Future<GteAnalyticsFunnel> fetchAnalyticsFunnel() async {
    await _delay();
    return _seedAnalyticsFunnel;
  }

  @override
  Future<GteTreasuryDashboard> fetchTreasuryDashboard() async {
    await _delayCapitalFixture();
    return _capitalDashboard.fetchTreasuryDashboard();
  }

  @override
  Future<GteTreasurySettings> fetchTreasurySettings() async {
    await _delayCapitalFixture();
    return _capitalTreasury.settings;
  }

  @override
  Future<GteTreasurySettings> updateTreasurySettings(
    GteTreasurySettingsUpdate request,
  ) async {
    await _delayCapitalFixture();
    final GteTreasurySettings settings = _capitalTreasury.updateSettings(
      request: request,
      updatedAt: _nextTimestamp(),
    );
    _pushNotification(
      topic: 'treasury_settings_updated',
      message: 'Treasury settings updated.',
      resourceId: settings.id,
    );
    return settings;
  }

  @override
  Future<List<GteTreasuryBankAccount>> listTreasuryBankAccounts() async {
    await _delayCapitalFixture();
    return _capitalTreasury.listBankAccounts();
  }

  @override
  Future<GteTreasuryBankAccount> createTreasuryBankAccount(
    GteTreasuryBankAccountCreate request,
  ) async {
    await _delayCapitalFixture();
    final DateTime now = _nextTimestamp();
    return _capitalTreasury.createBankAccount(request: request, createdAt: now);
  }

  @override
  Future<GteTreasuryBankAccount> updateTreasuryBankAccount(
    String accountId,
    GteTreasuryBankAccountUpdate request,
  ) async {
    await _delayCapitalFixture();
    final DateTime now = _nextTimestamp();
    return _capitalTreasury.updateBankAccount(
      accountId: accountId,
      request: request,
      updatedAt: now,
    );
  }

  @override
  Future<GteAdminQueuePage<GteAdminDeposit>> fetchAdminDeposits({
    int limit = 50,
    int offset = 0,
    String? status,
    String? query,
  }) async {
    await _delayCapitalFixture();
    return _capitalDeposits.fetchAdminDeposits(
      limit: limit,
      offset: offset,
      status: status,
      query: query,
      user: _fixtureSession.user,
    );
  }

  @override
  Future<GteDepositRequest> adminConfirmDeposit(
    String depositId, {
    String? adminNotes,
  }) async {
    await _delayCapitalFixture();
    final DateTime now = _nextTimestamp();
    final GteDepositRequest updated = _capitalDeposits.adminConfirmDeposit(
      depositId: depositId,
      adminNotes: adminNotes,
      confirmedAt: now,
    );
    _pushNotification(
      topic: 'deposit_confirmed',
      message: 'Deposit ${updated.reference} confirmed.',
      resourceId: updated.id,
    );
    return updated;
  }

  @override
  Future<GteDepositRequest> adminRejectDeposit(
    String depositId, {
    String? adminNotes,
  }) async {
    await _delayCapitalFixture();
    final DateTime now = _nextTimestamp();
    final GteDepositRequest updated = _capitalDeposits.adminRejectDeposit(
      depositId: depositId,
      adminNotes: adminNotes,
      rejectedAt: now,
    );
    _pushNotification(
      topic: 'deposit_rejected',
      message: 'Deposit ${updated.reference} rejected.',
      resourceId: updated.id,
    );
    return updated;
  }

  @override
  Future<GteDepositRequest> adminReviewDeposit(
    String depositId, {
    String? adminNotes,
  }) async {
    await _delayCapitalFixture();
    final DateTime now = _nextTimestamp();
    return _capitalDeposits.adminReviewDeposit(
      depositId: depositId,
      adminNotes: adminNotes,
      reviewedAt: now,
    );
  }

  @override
  Future<GteAdminQueuePage<GteAdminWithdrawal>> fetchAdminWithdrawals({
    int limit = 50,
    int offset = 0,
    String? status,
    String? query,
  }) async {
    await _delayCapitalFixture();
    return _capitalPayout.fetchAdminWithdrawals(
      limit: limit,
      offset: offset,
      status: status,
      query: query,
      user: _fixtureSession.user,
    );
  }

  @override
  Future<GteTreasuryWithdrawalRequest> adminUpdateWithdrawalStatus(
    String withdrawalId, {
    required GteWithdrawalStatus status,
    String? adminNotes,
  }) async {
    await _delayCapitalFixture();
    final DateTime now = _nextTimestamp();
    final GteTreasuryWithdrawalRequest updated = _capitalPayout
        .adminUpdateWithdrawalStatus(
          withdrawalId: withdrawalId,
          status: status,
          adminNotes: adminNotes,
          updatedAt: now,
        );
    if (status == GteWithdrawalStatus.paid) {
      _pushNotification(
        topic: 'withdrawal_paid',
        message: 'Withdrawal ${updated.reference} marked as paid.',
        resourceId: updated.id,
      );
    } else if (status == GteWithdrawalStatus.rejected ||
        status == GteWithdrawalStatus.cancelled) {
      _pushNotification(
        topic: 'withdrawal_rejected',
        message: 'Withdrawal ${updated.reference} was rejected.',
        resourceId: updated.id,
      );
    }
    return updated;
  }

  @override
  Future<GteAdminQueuePage<GteAdminKyc>> fetchAdminKyc({
    int limit = 50,
    int offset = 0,
    String? status,
    String? query,
  }) async {
    await _delayCapitalFixture();
    return _capitalWallet.fetchAdminKyc(
      limit: limit,
      offset: offset,
      status: status,
      query: query,
      user: _fixtureSession.user,
    );
  }

  @override
  Future<GteKycProfile> adminReviewKyc(
    String profileId,
    GteKycReviewRequest request,
  ) async {
    await _delayCapitalFixture();
    final DateTime now = _nextTimestamp();
    final GteKycProfile profile = _capitalWallet.reviewKyc(
      profileId: profileId,
      request: request,
      reviewedAt: now,
    );
    _pushNotification(
      topic:
          request.status == GteKycStatus.rejected
              ? 'kyc_rejected'
              : 'kyc_approved',
      message:
          request.status == GteKycStatus.rejected
              ? 'KYC rejected. Please review the notes.'
              : 'KYC verified.',
      resourceId: profile.id,
    );
    return profile;
  }

  @override
  Future<GteAdminQueuePage<GteDispute>> fetchAdminDisputes({
    int limit = 50,
    int offset = 0,
    String? status,
    String? query,
  }) async {
    await _delay();
    return _capitalDisputes.fetchAdminDisputes(
      limit: limit,
      offset: offset,
      status: status,
      query: query,
    );
  }

  @override
  Future<GteDispute> fetchAdminDispute(String disputeId) async {
    await _delay();
    return _capitalDisputes.fetchDispute(disputeId);
  }

  @override
  Future<GteDisputeMessage> adminSendDisputeMessage(
    String disputeId,
    GteDisputeMessageRequest request,
  ) async {
    await _delay();
    return _capitalDisputes.sendAdminMessage(
      disputeId: disputeId,
      request: request,
      createdAt: _nextTimestamp(),
      notify: _pushNotification,
    );
  }

  @override
  Future<GtePortfolioView> fetchPortfolio() async {
    await _delayCapitalFixture();
    return _capitalPortfolio.fetchPortfolio();
  }

  @override
  Future<GtePortfolioSummary> fetchPortfolioSummary() async {
    await _delayCapitalFixture();
    return _capitalPortfolio.fetchPortfolioSummary();
  }

  Future<void> _delay() async {
    await Future<void>.delayed(latency);
  }

  Future<void> _delayCapitalFixture() async {
    await _delay();
    if (_capitalFixturesEnabled) {
      return;
    }
    throw const GteApiException(
      type: GteApiErrorType.unavailable,
      message:
          'Capital wallet, order, deposit, withdrawal, and admin finance fixtures are disabled unless GteMockApi.capitalFixtures is used explicitly.',
    );
  }

  DateTime _nextTimestamp() {
    _clock = _clock.add(const Duration(seconds: 1));
    return _clock;
  }

  GteWalletOverview _buildWalletOverview() {
    final double pendingDeposits = _capitalDeposits.pendingDepositAmount;
    final double pendingWithdrawals = _capitalPayout.activeWithdrawalAmount;
    final double totalInflow = _capitalWallet.ledger
        .where((GteWalletLedgerEntry entry) => entry.amount > 0)
        .fold<double>(0, (double sum, GteWalletLedgerEntry entry) {
          return sum + entry.amount;
        });
    final double totalOutflow = _capitalWallet.ledger
        .where((GteWalletLedgerEntry entry) => entry.amount < 0)
        .fold<double>(0, (double sum, GteWalletLedgerEntry entry) {
          return sum + entry.amount.abs();
        });
    final List<GtePolicyRequirementSummary> missing =
        _capitalPolicy.currentMissingPolicyRequirements();
    final GteWithdrawalEligibility eligibility = _capitalPayout
        .fetchWithdrawalEligibility(now: _clock, missingPolicies: missing);
    final GteTreasurySettings settings = _capitalTreasury.settings;
    final String depositMode =
        settings.depositMode == GtePaymentMode.automatic
            ? 'gateway'
            : 'bank_transfer';
    final String withdrawalMode =
        settings.withdrawalMode == GtePaymentMode.automatic
            ? 'gateway'
            : 'bank_transfer';
    final Map<String, String> paymentProviderStatus =
        depositMode == 'gateway'
            ? const <String, String>{
              'bank_transfer_manual': 'blocked',
              'korapay': 'non_live',
            }
            : const <String, String>{
              'bank_transfer_manual': 'ready',
              'korapay': 'blocked',
            };
    final double lockedBalance =
        _capitalWallet.coinSummary.lockedBalance > 0
            ? _capitalWallet.coinSummary.lockedBalance
            : _capitalWallet.coinSummary.reservedBalance;
    return GteWalletOverview(
      availableBalance: _capitalWallet.coinSummary.availableBalance,
      reservedBalance: _capitalWallet.coinSummary.reservedBalance,
      lockedBalance: lockedBalance,
      lockReasons:
          lockedBalance > 0
              ? const <String>[
                'Active orders, withdrawals, or settlement commitments are reserving GTEX Coin.',
              ]
              : const <String>[],
      pendingDeposits: pendingDeposits,
      pendingWithdrawals: pendingWithdrawals,
      totalInflow: totalInflow,
      totalOutflow: totalOutflow,
      withdrawableNow: eligibility.withdrawableNow,
      currency: _capitalWallet.coinSummary.currency,
      countryCode: _capitalWallet.countryCode,
      requiredPolicyAcceptancesMissing: missing.length,
      policyBlocked: missing.isNotEmpty,
      policyBlockReason:
          missing.isEmpty
              ? null
              : 'Accept the latest required policy documents to unlock full wallet access.',
      depositMode: depositMode,
      withdrawalMode: withdrawalMode,
      paymentProviderStatus: paymentProviderStatus,
    );
  }

  void _pushNotification({
    required String topic,
    required String message,
    String? resourceId,
  }) {
    final DateTime now = _nextTimestamp();
    final GteNotification notification = GteNotification(
      notificationId: 'note-${++_notificationSequence}',
      userId: _fixtureSession.user.id,
      topic: topic,
      templateKey: null,
      resourceId: resourceId,
      fixtureId: null,
      competitionId: null,
      message: message,
      metadata: const <String, Object?>{},
      createdAt: now,
      readAt: null,
      isRead: false,
    );
    _notifications.insert(0, notification);
  }

  GteWalletConversionQuote _buildWalletConversionQuote(
    GteWalletConversionQuoteRequest request,
  ) {
    if (request.amount <= 0) {
      throw const GteApiException(
        type: GteApiErrorType.validation,
        message: 'Conversion amount must be positive.',
      );
    }
    if (request.sourceUnit != GteLedgerUnit.coin) {
      throw const GteApiException(
        type: GteApiErrorType.validation,
        message: 'Only GTEX Coin can be converted into Fan Coin.',
      );
    }
    const double rate = 100;
    return GteWalletConversionQuote(
      sourceUnit: GteLedgerUnit.coin,
      sourceAmount: request.amount,
      targetUnit: GteLedgerUnit.credit,
      targetAmount: request.amount * rate,
      rate: rate,
    );
  }
}

PlayerSnapshot _cloneSnapshot(PlayerSnapshot player) {
  return player.copyWith(
    valueTrend: List<TrendPoint>.from(player.valueTrend),
    recentHighlights: List<String>.from(player.recentHighlights),
  );
}

PlayerProfile _cloneProfile(PlayerProfile profile) {
  return profile.copyWith(
    snapshot: _cloneSnapshot(profile.snapshot),
    gsiTrend: List<TrendPoint>.from(profile.gsiTrend),
    awards: List<String>.from(profile.awards),
    statBlocks: List<String>.from(profile.statBlocks),
  );
}

GteMarketCandles _cloneCandles(GteMarketCandles candles) {
  return GteMarketCandles(
    playerId: candles.playerId,
    interval: candles.interval,
    candles: List<GteMarketCandle>.from(candles.candles),
  );
}

final GteAuthSession _fixtureSession = GteAuthSession(
  accessToken: 'fixture-session-token',
  refreshToken: 'fixture-session-refresh-token',
  sessionId: 'fixture-session-id',
  tokenType: 'bearer',
  expiresIn: 3600,
  refreshExpiresIn: 2592000,
  user: GteCurrentUser(
    id: 'fixture-user',
    email: 'fixture.trader@gte.local',
    username: 'fixture_trader',
    fullName: 'Fixture Trader',
    phoneNumber: '+2347000000000',
    displayName: 'Fixture Trader',
    role: 'user',
    kycStatus: 'partial_verified_no_id',
    isActive: true,
    ageConfirmedAt: DateTime.utc(2026, 3, 10, 8),
    rawJson: const <String, Object?>{
      'id': 'fixture-user',
      'email': 'fixture.trader@gte.local',
      'username': 'fixture_trader',
      'full_name': 'Fixture Trader',
      'phone_number': '+2347000000000',
      'display_name': 'Fixture Trader',
      'role': 'user',
      'kyc_status': 'partial_verified_no_id',
      'is_active': true,
      'age_confirmed_at': '2026-03-10T08:00:00Z',
      'session_id': 'fixture-session-id',
      'current_club_id': 'royal-lagos-fc',
      'current_club_name': 'Royal Lagos FC',
      'memberships': <Map<String, Object?>>[
        <String, Object?>{
          'club_id': 'royal-lagos-fc',
          'club_name': 'Royal Lagos FC',
          'is_current': true,
        },
      ],
    },
  ),
  rawJson: const <String, Object?>{
    'access_token': 'fixture-session-token',
    'token_type': 'bearer',
    'expires_in': 3600,
    'current_club_id': 'royal-lagos-fc',
    'current_club_name': 'Royal Lagos FC',
    'user': <String, Object?>{
      'id': 'fixture-user',
      'email': 'fixture.trader@gte.local',
      'username': 'fixture_trader',
      'full_name': 'Fixture Trader',
      'phone_number': '+2347000000000',
      'display_name': 'Fixture Trader',
      'role': 'user',
      'kyc_status': 'partial_verified_no_id',
      'is_active': true,
      'age_confirmed_at': '2026-03-10T08:00:00Z',
      'current_club_id': 'royal-lagos-fc',
      'current_club_name': 'Royal Lagos FC',
      'memberships': <Map<String, Object?>>[
        <String, Object?>{
          'club_id': 'royal-lagos-fc',
          'club_name': 'Royal Lagos FC',
          'is_current': true,
        },
      ],
    },
  },
);

const List<PlayerSnapshot> _seedCatalog = <PlayerSnapshot>[
  PlayerSnapshot(
    id: 'lamine-yamal',
    name: 'Lamine Yamal',
    club: 'Barcelona',
    nation: 'Spain',
    position: 'RW',
    age: 18,
    marketCredits: 1180,
    gsi: 96,
    formRating: 9.2,
    valueDeltaPct: 7.8,
    valueTrend: <TrendPoint>[
      TrendPoint(label: 'W1', value: 67),
      TrendPoint(label: 'W2', value: 71),
      TrendPoint(label: 'W3', value: 76),
      TrendPoint(label: 'W4', value: 82),
      TrendPoint(label: 'W5', value: 88),
    ],
    recentHighlights: <String>[
      '2 goals in the last 3 matches',
      'Final-third chance creation up 18%',
      'Transfer room activity accelerated this week',
    ],
    isFollowed: true,
    isWatchlisted: true,
  ),
  PlayerSnapshot(
    id: 'jude-bellingham',
    name: 'Jude Bellingham',
    club: 'Real Madrid',
    nation: 'England',
    position: 'CM',
    age: 22,
    marketCredits: 1260,
    gsi: 94,
    formRating: 8.9,
    valueDeltaPct: 4.6,
    valueTrend: <TrendPoint>[
      TrendPoint(label: 'W1', value: 70),
      TrendPoint(label: 'W2', value: 73),
      TrendPoint(label: 'W3', value: 79),
      TrendPoint(label: 'W4', value: 84),
      TrendPoint(label: 'W5', value: 87),
    ],
    recentHighlights: <String>[
      'Tournament influence tier: elite',
      'Shortlist demand remains stable',
      'Midfield duel win rate above 64%',
    ],
    isShortlisted: true,
  ),
  PlayerSnapshot(
    id: 'jamal-musiala',
    name: 'Jamal Musiala',
    club: 'Bayern Munich',
    nation: 'Germany',
    position: 'AM',
    age: 23,
    marketCredits: 1095,
    gsi: 91,
    formRating: 8.7,
    valueDeltaPct: 3.9,
    valueTrend: <TrendPoint>[
      TrendPoint(label: 'W1', value: 61),
      TrendPoint(label: 'W2', value: 65),
      TrendPoint(label: 'W3', value: 69),
      TrendPoint(label: 'W4', value: 74),
      TrendPoint(label: 'W5', value: 79),
    ],
    recentHighlights: <String>[
      'Line-breaking carries trending upward',
      'Scout Mode alerts active across 14 clubs',
      'Ball progression profile improved',
    ],
    isFollowed: true,
    notificationIntensity: NotificationIntensity.scoutMode,
  ),
  PlayerSnapshot(
    id: 'victor-osimhen',
    name: 'Victor Osimhen',
    club: 'Galatasaray',
    nation: 'Nigeria',
    position: 'ST',
    age: 27,
    marketCredits: 920,
    gsi: 88,
    formRating: 8.4,
    valueDeltaPct: 6.1,
    valueTrend: <TrendPoint>[
      TrendPoint(label: 'W1', value: 55),
      TrendPoint(label: 'W2', value: 58),
      TrendPoint(label: 'W3', value: 62),
      TrendPoint(label: 'W4', value: 69),
      TrendPoint(label: 'W5', value: 75),
    ],
    recentHighlights: <String>[
      'Transfer signal upgraded to active',
      'Shot volume back above 4.2 per 90',
      'Platform market demand rose after last matchday',
    ],
    inTransferRoom: true,
  ),
];

final Map<String, PlayerProfile> _seedProfiles = <String, PlayerProfile>{
  'lamine-yamal': PlayerProfile(
    snapshot: _seedCatalog[0],
    gsiTrend: const <TrendPoint>[
      TrendPoint(label: 'M1', value: 72),
      TrendPoint(label: 'M2', value: 77),
      TrendPoint(label: 'M3', value: 83),
      TrendPoint(label: 'M4', value: 89),
      TrendPoint(label: 'M5', value: 96),
    ],
    awards: const <String>[
      'Golden Boy shortlist',
      'Matchday MVP x3',
      'Continental semifinal decisive contribution',
    ],
    statBlocks: const <String>[
      'xA 0.42',
      'Dribbles won 5.7',
      'Progressive carries 7.3',
      'Final-third receptions 13.8',
    ],
    scoutingReport:
        'Explosive right-sided creator with elite manipulation of space and accelerating end product. Breakout profile still carries upside headroom.',
    transferSignal:
        'Untouchable unless a record-setting move materializes. Watchlist and shortlist activity remains the strongest in the catalog.',
  ),
  'jude-bellingham': PlayerProfile(
    snapshot: _seedCatalog[1],
    gsiTrend: const <TrendPoint>[
      TrendPoint(label: 'M1', value: 70),
      TrendPoint(label: 'M2', value: 75),
      TrendPoint(label: 'M3', value: 81),
      TrendPoint(label: 'M4', value: 87),
      TrendPoint(label: 'M5', value: 94),
    ],
    awards: const <String>[
      'Player of the season finalist',
      'Continental final-winning moment',
      'Best XI selection',
    ],
    statBlocks: const <String>[
      'Press resistance 95th pct',
      'Box arrivals 6.1',
      'Shot-creating actions 5.0',
      'Duel win rate 63%',
    ],
    scoutingReport:
        'Complete midfield controller with premium ball-carrying, duel dominance, and high-leverage scoring output. Low-risk elite asset.',
    transferSignal:
        'Market remains premium and supply-constrained. Acquisition scenario is improbable, but his card drives benchmark pricing.',
  ),
  'jamal-musiala': PlayerProfile(
    snapshot: _seedCatalog[2],
    gsiTrend: const <TrendPoint>[
      TrendPoint(label: 'M1', value: 66),
      TrendPoint(label: 'M2', value: 71),
      TrendPoint(label: 'M3', value: 76),
      TrendPoint(label: 'M4', value: 84),
      TrendPoint(label: 'M5', value: 91),
    ],
    awards: const <String>[
      'Young player of the month',
      'Tournament breakout watch',
      'Domestic title race accelerator',
    ],
    statBlocks: const <String>[
      'Carries into box 3.8',
      'Touches in zone 14: 11.2',
      'Turn resistance 92nd pct',
      'Progressive passes received 14.6',
    ],
    scoutingReport:
        'Hybrid creator-finisher with elite change of direction and close-control gravity. Best deployed with freedom between lines.',
    transferSignal:
        'Scout Mode traffic is heavy. Price is climbing steadily without the volatility seen in pure hype-driven movers.',
  ),
  'victor-osimhen': PlayerProfile(
    snapshot: _seedCatalog[3],
    gsiTrend: const <TrendPoint>[
      TrendPoint(label: 'M1', value: 61),
      TrendPoint(label: 'M2', value: 66),
      TrendPoint(label: 'M3', value: 69),
      TrendPoint(label: 'M4', value: 82),
      TrendPoint(label: 'M5', value: 88),
    ],
    awards: const <String>[
      'League golden boot race contender',
      'Transfer room headline striker',
      'Match-winning brace spotlight',
    ],
    statBlocks: const <String>[
      'Shots 4.4',
      'Aerial wins 3.2',
      'Penalty-box touches 8.9',
      'Goals per shot 0.23',
    ],
    scoutingReport:
        'Vertical striker with premium penalty-box occupation, elite separation bursts, and immediate transfer-market gravity.',
    transferSignal:
        'Transfer room remains live. Featured on both platform deal boards and user market chatter after the latest valuation jump.',
  ),
};

final MarketPulse _marketPulse = MarketPulse(
  marketMomentum: 8.4,
  dailyVolumeCredits: 18340,
  activeWatchers: 642,
  liveDeals: 21,
  hottestLeague: 'UEFA Club Championship',
  tickers: const <String>[
    'Yamal +7.8%',
    'Osimhen +6.1%',
    'Musiala Scout Mode spike',
    'Transfer room volume +14%',
  ],
  transferRoom: <TransferRoomEntry>[
    TransferRoomEntry(
      id: 'tr-1',
      headline: 'Platform Deal: Victor Osimhen demand surge',
      lane: 'Platform Deals',
      marketCredits: 920,
      activity: '22 shortlist moves in 24h',
      timestamp: DateTime.utc(2026, 3, 11, 10, 30),
    ),
    TransferRoomEntry(
      id: 'tr-2',
      headline: 'User Market Deal: Musiala premium listing filled',
      lane: 'User Market Deals',
      marketCredits: 1110,
      activity: 'Cleared in 6 minutes',
      timestamp: DateTime.utc(2026, 3, 11, 9, 50),
    ),
    TransferRoomEntry(
      id: 'tr-3',
      headline: 'Announcement: Jude benchmark pricing reset',
      lane: 'Announcements',
      marketCredits: 1260,
      activity: 'Market cap ceiling updated',
      timestamp: DateTime.utc(2026, 3, 11, 8, 45),
    ),
  ],
);

final Map<String, GteMarketCandles> _seedCandles = <String, GteMarketCandles>{
  'lamine-yamal': GteMarketCandles(
    playerId: 'lamine-yamal',
    interval: '1h',
    candles: <GteMarketCandle>[
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 8),
        open: 1148,
        high: 1159,
        low: 1141,
        close: 1152,
        volume: 3,
      ),
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 9),
        open: 1152,
        high: 1168,
        low: 1149,
        close: 1161,
        volume: 4,
      ),
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 10),
        open: 1161,
        high: 1175,
        low: 1158,
        close: 1168,
        volume: 5,
      ),
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 11),
        open: 1168,
        high: 1182,
        low: 1164,
        close: 1176,
        volume: 6,
      ),
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 12),
        open: 1176,
        high: 1193,
        low: 1170,
        close: 1180,
        volume: 7,
      ),
    ],
  ),
  'jude-bellingham': GteMarketCandles(
    playerId: 'jude-bellingham',
    interval: '1h',
    candles: <GteMarketCandle>[
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 8),
        open: 1210,
        high: 1222,
        low: 1204,
        close: 1216,
        volume: 3,
      ),
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 9),
        open: 1216,
        high: 1230,
        low: 1213,
        close: 1224,
        volume: 4,
      ),
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 10),
        open: 1224,
        high: 1241,
        low: 1218,
        close: 1233,
        volume: 5,
      ),
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 11),
        open: 1233,
        high: 1254,
        low: 1228,
        close: 1246,
        volume: 6,
      ),
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 12),
        open: 1246,
        high: 1268,
        low: 1240,
        close: 1260,
        volume: 7,
      ),
    ],
  ),
  'jamal-musiala': GteMarketCandles(
    playerId: 'jamal-musiala',
    interval: '1h',
    candles: <GteMarketCandle>[
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 8),
        open: 1061,
        high: 1074,
        low: 1055,
        close: 1068,
        volume: 3,
      ),
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 9),
        open: 1068,
        high: 1082,
        low: 1061,
        close: 1075,
        volume: 4,
      ),
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 10),
        open: 1075,
        high: 1089,
        low: 1069,
        close: 1081,
        volume: 5,
      ),
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 11),
        open: 1081,
        high: 1100,
        low: 1078,
        close: 1090,
        volume: 6,
      ),
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 12),
        open: 1090,
        high: 1107,
        low: 1084,
        close: 1095,
        volume: 7,
      ),
    ],
  ),
  'victor-osimhen': GteMarketCandles(
    playerId: 'victor-osimhen',
    interval: '1h',
    candles: <GteMarketCandle>[
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 12),
        open: 920,
        high: 924,
        low: 915,
        close: 920,
        volume: 1,
      ),
    ],
  ),
};

final List<GteNotification> _seedNotifications = <GteNotification>[
  GteNotification(
    notificationId: 'note-1',
    userId: 'fixture-user',
    topic: 'deposit_submitted',
    templateKey: null,
    resourceId: 'deposit-1',
    fixtureId: null,
    competitionId: null,
    message: 'Deposit DEP-1001 submitted. Pending review.',
    metadata: const <String, Object?>{},
    createdAt: DateTime.utc(2026, 3, 11, 8, 6),
    readAt: null,
    isRead: false,
  ),
  GteNotification(
    notificationId: 'note-0',
    userId: 'fixture-user',
    topic: 'wallet_credit',
    templateKey: null,
    resourceId: 'deposit-2',
    fixtureId: null,
    competitionId: null,
    message: 'Deposit DEP-1000 confirmed. Wallet credited.',
    metadata: const <String, Object?>{},
    createdAt: DateTime.utc(2026, 3, 10, 9, 12),
    readAt: DateTime.utc(2026, 3, 10, 9, 20),
    isRead: true,
  ),
];

final List<GteAnalyticsEvent> _seedAnalyticsEvents = <GteAnalyticsEvent>[
  GteAnalyticsEvent(
    id: 'evt-1',
    name: 'signup_completed',
    userId: 'fixture-user',
    metadata: const <String, Object?>{},
    createdAt: DateTime.utc(2026, 3, 10, 8),
  ),
  GteAnalyticsEvent(
    id: 'evt-2',
    name: 'deposit_submitted',
    userId: 'fixture-user',
    metadata: const <String, Object?>{},
    createdAt: DateTime.utc(2026, 3, 11, 8, 6),
  ),
];

final GteAnalyticsFunnel _seedAnalyticsFunnel = GteAnalyticsFunnel(
  since: DateTime.utc(2026, 3, 1),
  steps: const <GteAnalyticsFunnelStep>[
    GteAnalyticsFunnelStep(name: 'signup_completed', users: 1200),
    GteAnalyticsFunnelStep(name: 'deposit_submitted', users: 540),
    GteAnalyticsFunnelStep(name: 'kyc_submitted', users: 210),
    GteAnalyticsFunnelStep(name: 'withdrawal_requested', users: 78),
  ],
);
