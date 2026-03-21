import 'dart:async';
import 'dart:math' as math;

import 'gte_api_repository.dart';
import 'gte_models.dart';

class GteMockApi implements GteApiRepository {
  GteMockApi({
    this.latency = const Duration(milliseconds: 250),
  })  : _catalog = _seedCatalog.map(_cloneSnapshot).toList(growable: false),
        _profiles = _seedProfiles.map(
          (String key, PlayerProfile value) => MapEntry<String, PlayerProfile>(
            key,
            _cloneProfile(value),
          ),
        ),
        _baseTickers = Map<String, GteMarketTicker>.from(_seedTickers),
        _candles = _seedCandles.map(
          (String key, GteMarketCandles value) =>
              MapEntry<String, GteMarketCandles>(
            key,
            _cloneCandles(value),
          ),
        ),
        _baseOrderBooks = _seedOrderBooks.map(
          (String key, GteOrderBook value) => MapEntry<String, GteOrderBook>(
            key,
            _cloneOrderBook(value),
          ),
        ),
        _walletSummary = _seedWalletSummary,
        _walletLedger =
            List<GteWalletLedgerEntry>.of(_seedWalletLedger, growable: true),
        _portfolio = GtePortfolioView(
          holdings: List<GtePortfolioHolding>.of(_seedPortfolioHoldings,
              growable: false),
        ),
        _orders = List<GteOrderRecord>.of(_seedOrders, growable: true),
        _portfolioSummary = _seedPortfolioSummary,
        _treasurySettings = _seedTreasurySettings,
        _treasuryBankAccounts = List<GteTreasuryBankAccount>.of(
            _seedTreasuryBankAccounts,
            growable: true),
        _depositRequests =
            List<GteDepositRequest>.of(_seedDeposits, growable: true),
        _withdrawalRequests = List<GteTreasuryWithdrawalRequest>.of(
            _seedWithdrawals,
            growable: true),
        _userBankAccounts =
            List<GteUserBankAccount>.of(_seedUserBankAccounts, growable: true),
        _kycProfile = _seedKycProfile,
        _disputes = List<GteDispute>.of(_seedDisputes, growable: true),
        _notifications =
            List<GteNotification>.of(_seedNotifications, growable: true),
        _attachments = <GteAttachment>[],
        _analyticsEvents =
            List<GteAnalyticsEvent>.of(_seedAnalyticsEvents, growable: true),
        _policyDocuments = List<GtePolicyDocumentDetail>.of(
            _seedPolicyDocuments,
            growable: true),
        _policyAcceptances = List<GtePolicyAcceptanceSummary>.of(
            _seedPolicyAcceptances,
            growable: true);

  final Duration latency;
  final List<PlayerSnapshot> _catalog;
  final Map<String, PlayerProfile> _profiles;
  final Map<String, GteMarketTicker> _baseTickers;
  final Map<String, GteMarketCandles> _candles;
  final Map<String, GteOrderBook> _baseOrderBooks;

  GteWalletSummary _walletSummary;
  final List<GteWalletLedgerEntry> _walletLedger;
  GtePortfolioView _portfolio;
  GtePortfolioSummary _portfolioSummary;
  final List<GteOrderRecord> _orders;
  final Set<String> _sessionOrderIds = <String>{};
  final List<GteDepositRequest> _depositRequests;
  final List<GteTreasuryWithdrawalRequest> _withdrawalRequests;
  final List<GteUserBankAccount> _userBankAccounts;
  GteKycProfile _kycProfile;
  final List<GteDispute> _disputes;
  final List<GteNotification> _notifications;
  final List<GteTreasuryBankAccount> _treasuryBankAccounts;
  GteTreasurySettings _treasurySettings;
  final List<GteAttachment> _attachments;
  final List<GteAnalyticsEvent> _analyticsEvents;
  final List<GtePolicyDocumentDetail> _policyDocuments;
  final List<GtePolicyAcceptanceSummary> _policyAcceptances;

  int _orderSequence = _seedOrders.length;
  int _ledgerSequence = _seedWalletLedger.length;
  int _depositSequence = _seedDeposits.length;
  int _withdrawalSequence = _seedWithdrawals.length;
  int _disputeSequence = _seedDisputes.length;
  int _notificationSequence = _seedNotifications.length;
  int _attachmentSequence = 0;
  int _userBankSequence = _seedUserBankAccounts.length;
  int _treasuryBankSequence = _seedTreasuryBankAccounts.length;
  DateTime _clock = DateTime.utc(2026, 3, 11, 12, 0);

  @override
  Future<GteAuthSession> login(GteAuthLoginRequest request) async {
    await _delay();
    return _fixtureSession;
  }

  @override
  Future<GteAuthSession> register(GteAuthRegisterRequest request) async {
    await _delay();
    if (!request.isOver18) {
      throw const GteApiException(
        type: GteApiErrorType.validation,
        message: 'You must be 18 or older to create an account.',
      );
    }
    final String fallbackUsername =
        request.username ?? request.email.split('@').first;
    final DateTime now = _nextTimestamp();
    return GteAuthSession(
      accessToken: 'fixture-$fallbackUsername-token',
      tokenType: 'bearer',
      expiresIn: 3600,
      user: GteCurrentUser(
        id: 'fixture-$fallbackUsername',
        email: request.email,
        username: fallbackUsername,
        fullName: request.fullName,
        phoneNumber: request.phoneNumber,
        displayName: request.fullName,
        role: 'user',
        ageConfirmedAt: now,
      ),
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
    final Iterable<GtePolicyDocumentDetail> docs = mandatoryOnly
        ? _policyDocuments
            .where((GtePolicyDocumentDetail doc) => doc.isMandatory)
        : _policyDocuments;
    return docs
        .map(
          (GtePolicyDocumentDetail doc) => GtePolicyDocumentSummary(
            id: doc.id,
            documentKey: doc.documentKey,
            title: doc.title,
            isMandatory: doc.isMandatory,
            active: doc.active,
            latestVersion: doc.latestVersion,
          ),
        )
        .toList(growable: false);
  }

  @override
  Future<GtePolicyDocumentDetail> fetchPolicyDocument(
    String documentKey, {
    String? versionLabel,
  }) async {
    await _delay();
    return _policyDocuments.firstWhere(
      (GtePolicyDocumentDetail doc) => doc.documentKey == documentKey,
      orElse: () => throw StateError('Unknown policy document: $documentKey'),
    );
  }

  @override
  Future<GteComplianceStatus> fetchComplianceStatus() async {
    await _delay();
    final List<GtePolicyRequirementSummary> missing =
        await fetchPolicyRequirements();
    final bool canDeposit = missing.isEmpty;
    return GteComplianceStatus(
      countryCode: _kycProfile.country?.toUpperCase() ?? 'NG',
      countryPolicyBucket: 'regulated_market_disabled',
      depositsEnabled: true,
      marketTradingEnabled: canDeposit,
      platformRewardWithdrawalsEnabled: canDeposit,
      requiredPolicyAcceptancesMissing: missing.length,
      missingPolicyAcceptances: missing,
      canDeposit: true,
      canWithdrawPlatformRewards: canDeposit,
      canTradeMarket: canDeposit,
    );
  }

  @override
  Future<List<GtePolicyRequirementSummary>> fetchPolicyRequirements() async {
    await _delay();
    return _currentMissingPolicyRequirements();
  }

  @override
  Future<List<GtePolicyAcceptanceSummary>> fetchMyPolicyAcceptances() async {
    await _delay();
    return List<GtePolicyAcceptanceSummary>.of(_policyAcceptances,
        growable: false);
  }

  @override
  Future<GtePolicyAcceptanceSummary> acceptPolicyDocument(
    String documentKey,
    String versionLabel,
  ) async {
    await _delay();
    final GtePolicyDocumentDetail document =
        await fetchPolicyDocument(documentKey);
    final int existingIndex = _policyAcceptances.indexWhere(
      (GtePolicyAcceptanceSummary item) => item.documentKey == documentKey,
    );
    final GtePolicyAcceptanceSummary acceptance = GtePolicyAcceptanceSummary(
      documentKey: documentKey,
      title: document.title,
      versionLabel: versionLabel,
      acceptedAt: _nextTimestamp(),
    );
    if (existingIndex >= 0) {
      _policyAcceptances[existingIndex] = acceptance;
    } else {
      _policyAcceptances.add(acceptance);
    }
    return acceptance;
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
    final GteMarketTicker? ticker = _baseTickers[playerId];
    if (ticker == null) {
      throw StateError('Unknown ticker player id: $playerId');
    }
    final Iterable<GteOrderRecord> openOrders = _orders.where(
      (GteOrderRecord order) =>
          order.playerId == playerId &&
          order.canCancel &&
          _sessionOrderIds.contains(order.id),
    );
    double? bestBid = ticker.bestBid;
    double? bestAsk = ticker.bestAsk;
    for (final GteOrderRecord order in openOrders) {
      final double? price = _priceForOrder(order);
      if (price == null || price <= 0) {
        continue;
      }
      if (order.side == GteOrderSide.buy) {
        bestBid = bestBid == null ? price : math.max(bestBid, price);
      } else {
        bestAsk = bestAsk == null ? price : math.min(bestAsk, price);
      }
    }

    final double? spread =
        bestBid != null && bestAsk != null ? bestAsk - bestBid : ticker.spread;
    final double? midPrice = bestBid != null && bestAsk != null
        ? (bestBid + bestAsk) / 2
        : ticker.midPrice;
    return GteMarketTicker(
      playerId: ticker.playerId,
      symbol: ticker.symbol,
      lastPrice: ticker.lastPrice,
      bestBid: bestBid,
      bestAsk: bestAsk,
      spread: spread,
      midPrice: midPrice,
      referencePrice: ticker.referencePrice,
      dayChange: ticker.dayChange,
      dayChangePercent: ticker.dayChangePercent,
      volume24h: ticker.volume24h,
    );
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
    final List<GteMarketCandle> trimmed =
        candles.candles.take(limit).toList(growable: false);
    return GteMarketCandles(
      playerId: playerId,
      interval: interval,
      candles: trimmed,
    );
  }

  @override
  Future<GteOrderBook> fetchOrderBook(String playerId) async {
    await _delay();
    final GteOrderBook? base = _baseOrderBooks[playerId];
    if (base == null) {
      throw StateError('Unknown order book player id: $playerId');
    }

    final Iterable<GteOrderRecord> openOrders = _orders.where(
      (GteOrderRecord order) =>
          order.playerId == playerId &&
          order.canCancel &&
          _sessionOrderIds.contains(order.id),
    );
    final List<GteOrderBookLevel> bids = _mergeOrderBookSide(
      base.bids,
      openOrders
          .where((GteOrderRecord order) => order.side == GteOrderSide.buy),
      descending: true,
    );
    final List<GteOrderBookLevel> asks = _mergeOrderBookSide(
      base.asks,
      openOrders
          .where((GteOrderRecord order) => order.side == GteOrderSide.sell),
      descending: false,
    );
    return GteOrderBook(
      playerId: playerId,
      bids: bids,
      asks: asks,
      generatedAt: _clock,
    );
  }

  @override
  Future<GteOrderListView> listOrders({
    int limit = 20,
    int offset = 0,
    List<GteOrderStatus>? statuses,
  }) async {
    await _delay();
    Iterable<GteOrderRecord> filtered = _orders;
    if (statuses != null && statuses.isNotEmpty) {
      final Set<GteOrderStatus> allowed = statuses.toSet();
      filtered = filtered
          .where((GteOrderRecord order) => allowed.contains(order.status));
    }
    final List<GteOrderRecord> ordered = filtered.toList(growable: false);
    final List<GteOrderRecord> items =
        ordered.skip(offset).take(limit).toList(growable: false);
    return GteOrderListView(
      items: items,
      limit: limit,
      offset: offset,
      total: ordered.length,
    );
  }

  @override
  Future<GteOrderRecord> fetchOrder(String orderId) async {
    await _delay();
    return _orders.firstWhere(
      (GteOrderRecord order) => order.id == orderId,
      orElse: () => throw StateError('Unknown order id: $orderId'),
    );
  }

  @override
  Future<GteOrderRecord> placeOrder(GteOrderCreateRequest request) async {
    await _delay();
    final double? referencePrice =
        _referencePriceFor(request.playerId, request.side);
    final double requestedReserve =
        request.side == GteOrderSide.buy && request.maxPrice != null
            ? request.quantity * request.maxPrice!
            : 0.0;
    final double reservedAmount =
        math.min(requestedReserve, _walletSummary.availableBalance);
    final DateTime timestamp = _nextTimestamp();

    final GteOrderRecord order = GteOrderRecord(
      id: 'ord-${++_orderSequence}',
      userId: _fixtureSession.user.id,
      playerId: request.playerId,
      side: request.side,
      status: GteOrderStatus.open,
      quantity: request.quantity,
      filledQuantity: 0.0,
      remainingQuantity: request.quantity,
      maxPrice: request.maxPrice ?? referencePrice,
      reservedAmount: reservedAmount,
      currency: GteLedgerUnit.credit,
      holdTransactionId: request.side == GteOrderSide.buy && reservedAmount > 0
          ? 'ledger-${_ledgerSequence + 1}'
          : null,
      createdAt: timestamp,
      updatedAt: timestamp,
      executionSummary: const GteOrderExecutionSummary(
        executionCount: 0,
        totalNotional: 0.0,
        averagePrice: null,
      ),
    );
    _orders.insert(0, order);
    _sessionOrderIds.add(order.id);

    if (request.side == GteOrderSide.buy && reservedAmount > 0) {
      _walletSummary = GteWalletSummary(
        availableBalance: _walletSummary.availableBalance - reservedAmount,
        reservedBalance: _walletSummary.reservedBalance + reservedAmount,
        totalBalance: _walletSummary.totalBalance,
        currency: _walletSummary.currency,
      );
      _walletLedger.insert(
        0,
        GteWalletLedgerEntry(
          id: 'ledger-${++_ledgerSequence}',
          amount: -reservedAmount,
          reason: 'order_funds_reserved',
          description: 'Reserved credits for ${request.playerId} buy order',
          createdAt: timestamp,
        ),
      );
      _rebuildPortfolioSummary();
    }

    return order;
  }

  @override
  Future<GteOrderRecord> cancelOrder(String orderId) async {
    await _delay();
    final int index =
        _orders.indexWhere((GteOrderRecord order) => order.id == orderId);
    if (index == -1) {
      throw StateError('Unknown order id: $orderId');
    }
    final GteOrderRecord existing = _orders[index];
    if (!existing.canCancel) {
      return existing;
    }

    final DateTime timestamp = _nextTimestamp();
    final GteOrderRecord cancelled = GteOrderRecord(
      id: existing.id,
      userId: existing.userId,
      playerId: existing.playerId,
      side: existing.side,
      status: GteOrderStatus.cancelled,
      quantity: existing.quantity,
      filledQuantity: existing.filledQuantity,
      remainingQuantity: existing.remainingQuantity,
      maxPrice: existing.maxPrice,
      reservedAmount: 0.0,
      currency: existing.currency,
      holdTransactionId: existing.holdTransactionId,
      createdAt: existing.createdAt,
      updatedAt: timestamp,
      executionSummary: existing.executionSummary,
    );
    _orders[index] = cancelled;

    if (existing.side == GteOrderSide.buy && existing.reservedAmount > 0) {
      _walletSummary = GteWalletSummary(
        availableBalance:
            _walletSummary.availableBalance + existing.reservedAmount,
        reservedBalance: math.max(
          0.0,
          _walletSummary.reservedBalance - existing.reservedAmount,
        ),
        totalBalance: _walletSummary.totalBalance,
        currency: _walletSummary.currency,
      );
      _walletLedger.insert(
        0,
        GteWalletLedgerEntry(
          id: 'ledger-${++_ledgerSequence}',
          amount: existing.reservedAmount,
          reason: 'order_cancel_release',
          description: 'Released credits from cancelled order ${existing.id}',
          createdAt: timestamp,
        ),
      );
      _rebuildPortfolioSummary();
    }

    return cancelled;
  }

  @override
  Future<GteAdminBuybackPreview> fetchAdminBuybackPreview(String orderId) async {
    await _delay();
    final GteOrderRecord order = await fetchOrder(orderId);
    final double fairValue =
        order.maxPrice ?? _referencePriceFor(order.playerId, GteOrderSide.sell) ?? 0;
    final double remainingQuantity =
        order.remainingQuantity < 0 ? 0 : order.remainingQuantity;
    final double estimatedP2pTotal = remainingQuantity * fairValue;
    final double payoutRatio = _adminBuybackPayoutRatio(fairValue);
    final double adminUnitPrice = fairValue * payoutRatio;
    final double adminTotal = remainingQuantity * adminUnitPrice;
    final DateTime? windowEndsAt = order.createdAt?.add(const Duration(hours: 48));
    final bool windowElapsed = windowEndsAt == null || !_clock.isBefore(windowEndsAt);
    final List<String> reasons = <String>[
      if (order.side != GteOrderSide.sell)
        'Admin quick exit is only available for sell orders.',
      if (!order.canCancel)
        'Only open sell orders can use admin quick exit.',
      if (!windowElapsed)
        'P2P remains the default path until ${windowEndsAt?.toIso8601String() ?? 'the priority window ends'}.',
    ];
    return GteAdminBuybackPreview(
      orderId: order.id,
      playerId: order.playerId,
      eligible: reasons.isEmpty,
      reasons: reasons,
      message:
          'P2P listings usually pay more. Admin quick exit is a lower fallback after the priority window ends.',
      country: 'Nigeria',
      fairValue: fairValue,
      estimatedP2pUnitPrice: fairValue,
      estimatedP2pTotal: estimatedP2pTotal,
      adminUnitPrice: adminUnitPrice,
      adminTotal: adminTotal,
      payoutRatio: payoutRatio,
      liquidityBand: _liquidityBandForPrice(fairValue),
      payoutBand: _payoutBandForPrice(fairValue),
      p2pPriorityWindowHours: 48,
      p2pPriorityWindowEndsAt: windowEndsAt,
      minimumHoldDays: 7,
      minimumHoldExpiresAt:
          order.createdAt?.subtract(const Duration(days: 1)),
      holdDaysRemaining: 0,
    );
  }

  @override
  Future<GteAdminBuybackExecution> executeAdminBuyback(String orderId) async {
    await _delay();
    final GteAdminBuybackPreview preview =
        await fetchAdminBuybackPreview(orderId);
    if (!preview.eligible) {
      throw GteApiException(
        type: GteApiErrorType.validation,
        message: preview.reasons.isEmpty
            ? 'Admin buyback is unavailable.'
            : preview.reasons.first,
      );
    }
    final int index =
        _orders.indexWhere((GteOrderRecord order) => order.id == orderId);
    if (index == -1) {
      throw StateError('Unknown order id: $orderId');
    }
    final GteOrderRecord existing = _orders[index];
    final DateTime executedAt = _nextTimestamp();
    final GteOrderRecord updated = GteOrderRecord(
      id: existing.id,
      userId: existing.userId,
      playerId: existing.playerId,
      side: existing.side,
      status: GteOrderStatus.filled,
      quantity: existing.quantity,
      filledQuantity: existing.quantity,
      remainingQuantity: 0,
      maxPrice: existing.maxPrice,
      reservedAmount: 0,
      currency: existing.currency,
      holdTransactionId: existing.holdTransactionId,
      createdAt: existing.createdAt,
      updatedAt: executedAt,
      executionSummary: existing.executionSummary,
    );
    _orders[index] = updated;
    _walletSummary = GteWalletSummary(
      availableBalance: _walletSummary.availableBalance + preview.adminTotal,
      reservedBalance: _walletSummary.reservedBalance,
      totalBalance: _walletSummary.totalBalance + preview.adminTotal,
      currency: _walletSummary.currency,
    );
    _walletLedger.insert(
      0,
      GteWalletLedgerEntry(
        id: 'ledger-${++_ledgerSequence}',
        amount: preview.adminTotal,
        reason: 'admin_buyback_settlement',
        description: 'Admin quick exit credited for ${existing.playerId}',
        createdAt: executedAt,
      ),
    );
    _adjustHoldingQuantity(
      existing.playerId,
      -existing.remainingQuantity,
      currentPrice: preview.fairValue,
    );
    _rebuildPortfolioSummary();
    return GteAdminBuybackExecution(
      preview: preview,
      order: updated,
      quantity: existing.remainingQuantity,
      unitPrice: preview.adminUnitPrice,
      total: preview.adminTotal,
      executedAt: executedAt,
    );
  }

  @override
  Future<GteWalletSummary> fetchWalletSummary() async {
    await _delay();
    return _walletSummary;
  }

  @override
  Future<GteWalletLedgerPage> fetchWalletLedger(
      {int page = 1, int pageSize = 20}) async {
    await _delay();
    final int offset = (page - 1) * pageSize;
    final List<GteWalletLedgerEntry> items =
        _walletLedger.skip(offset).take(pageSize).toList(growable: false);
    return GteWalletLedgerPage(
      page: page,
      pageSize: pageSize,
      total: _walletLedger.length,
      items: items,
    );
  }

  @override
  Future<GteWalletOverview> fetchWalletOverview() async {
    await _delay();
    return _buildWalletOverview();
  }

  @override
  Future<GteWithdrawalEligibility> fetchWithdrawalEligibility() async {
    await _delay();
    return _computeWithdrawalEligibility();
  }

  @override
  Future<GteWithdrawalQuote> fetchWithdrawalQuote(
      GteWithdrawalQuoteRequest request) async {
    await _delay();
    final GteWithdrawalEligibility eligibility =
        _computeWithdrawalEligibility();
    final int feeBps = 1000;
    final double minimumFee = 5;
    final double feeAmount =
        math.max(request.amountCoin * feeBps.toDouble() / 10000, minimumFee);
    final double totalDebit = request.amountCoin + feeAmount;
    final double rateValue = _treasurySettings.withdrawalRateValue;
    final double estimatedFiat = _treasurySettings.withdrawalRateDirection ==
            GteRateDirection.fiatPerCoin
        ? request.amountCoin * rateValue
        : request.amountCoin / math.max(rateValue, 0.0001);
    String? blockedReason;
    if (eligibility.policyBlocked) {
      blockedReason = eligibility.policyBlockReason ??
          'Policy acceptance required before withdrawal is enabled.';
    } else if (eligibility.requiresKyc) {
      blockedReason = 'KYC required before withdrawals are enabled.';
    } else if (eligibility.requiresBankAccount) {
      blockedReason = 'Bank account required before withdrawals are enabled.';
    } else if (request.amountCoin > eligibility.withdrawableNow) {
      blockedReason = 'Withdrawal exceeds available balance.';
    }
    return GteWithdrawalQuote(
      grossAmount: request.amountCoin,
      feeAmount: feeAmount,
      netAmount: request.amountCoin,
      totalDebit: totalDebit,
      sourceScope: request.sourceScope,
      currencyCode: _treasurySettings.currencyCode,
      rateValue: rateValue,
      rateDirection: _treasurySettings.withdrawalRateDirection,
      estimatedFiatPayout: estimatedFiat,
      processorMode: _treasurySettings.withdrawalMode == GtePaymentMode.manual
          ? 'manual_bank_transfer'
          : 'automatic_gateway',
      payoutChannel: 'bank_transfer',
      feeBps: feeBps,
      minimumFee: minimumFee,
      eligibility: eligibility,
      blockedReason: blockedReason,
    );
  }

  @override
  Future<GteWithdrawalReceipt> fetchWithdrawalReceipt(
      String withdrawalId) async {
    await _delay();
    final GteTreasuryWithdrawalRequest withdrawal =
        _withdrawalRequests.firstWhere(
      (GteTreasuryWithdrawalRequest item) => item.id == withdrawalId,
      orElse: () => _withdrawalRequests.isNotEmpty
          ? _withdrawalRequests.first
          : _buildWithdrawalFixture(withdrawalId),
    );
    return GteWithdrawalReceipt(
      withdrawal: withdrawal,
      grossAmount: withdrawal.amountCoin,
      feeAmount: withdrawal.feeAmount,
      netAmount: withdrawal.amountCoin,
      totalDebit: withdrawal.totalDebit,
      sourceScope: 'trade',
      processorMode: _treasurySettings.withdrawalMode == GtePaymentMode.manual
          ? 'manual_bank_transfer'
          : 'automatic_gateway',
      payoutChannel: 'bank_transfer',
    );
  }

  @override
  Future<GteDepositRequest> createDepositRequest(
      GteDepositCreateRequest request) async {
    await _delay();
    final GteTreasuryBankAccount bank =
        _treasurySettings.activeBankAccount ?? _treasuryBankAccounts.first;
    final DateTime createdAt = _nextTimestamp();
    final double rateValue = _treasurySettings.depositRateValue;
    final bool fiatPerCoin =
        _treasurySettings.depositRateDirection == GteRateDirection.fiatPerCoin;
    double amountFiat = 0;
    double amountCoin = 0;
    if (request.inputUnit == 'coin') {
      amountCoin = request.amount;
      amountFiat = fiatPerCoin
          ? request.amount * rateValue
          : request.amount / math.max(rateValue, 0.0001);
    } else {
      amountFiat = request.amount;
      amountCoin = fiatPerCoin
          ? request.amount / math.max(rateValue, 0.0001)
          : request.amount * rateValue;
    }
    final String reference = 'DEP-${++_depositSequence}';
    final GteDepositRequest deposit = GteDepositRequest(
      id: 'deposit-${_depositSequence}',
      reference: reference,
      status: GteDepositStatus.awaitingPayment,
      amountFiat: amountFiat,
      amountCoin: amountCoin,
      currencyCode: _treasurySettings.currencyCode,
      rateValue: rateValue,
      rateDirection: _treasurySettings.depositRateDirection,
      bankName: bank.bankName,
      bankAccountNumber: bank.accountNumber,
      bankAccountName: bank.accountName,
      bankCode: bank.bankCode,
      payerName: null,
      senderBank: null,
      transferReference: null,
      proofAttachmentId: null,
      adminNotes: null,
      createdAt: createdAt,
      submittedAt: null,
      reviewedAt: null,
      confirmedAt: null,
      rejectedAt: null,
      expiresAt: null,
    );
    _depositRequests.insert(0, deposit);
    _pushNotification(
      topic: 'deposit_request_created',
      message: 'Deposit $reference created. Awaiting payment confirmation.',
      resourceId: deposit.id,
    );
    return deposit;
  }

  @override
  Future<GteDepositRequest> submitDepositRequest(
      String depositId, GteDepositSubmitRequest request) async {
    await _delay();
    final int index = _depositRequests
        .indexWhere((GteDepositRequest item) => item.id == depositId);
    if (index == -1) {
      throw StateError('Deposit not found');
    }
    final GteDepositRequest existing = _depositRequests[index];
    final GteDepositRequest updated = GteDepositRequest(
      id: existing.id,
      reference: existing.reference,
      status: GteDepositStatus.paymentSubmitted,
      amountFiat: existing.amountFiat,
      amountCoin: existing.amountCoin,
      currencyCode: existing.currencyCode,
      rateValue: existing.rateValue,
      rateDirection: existing.rateDirection,
      bankName: existing.bankName,
      bankAccountNumber: existing.bankAccountNumber,
      bankAccountName: existing.bankAccountName,
      bankCode: existing.bankCode,
      payerName: request.payerName ?? existing.payerName,
      senderBank: request.senderBank ?? existing.senderBank,
      transferReference:
          request.transferReference ?? existing.transferReference,
      proofAttachmentId:
          request.proofAttachmentId ?? existing.proofAttachmentId,
      adminNotes: existing.adminNotes,
      createdAt: existing.createdAt,
      submittedAt: _nextTimestamp(),
      reviewedAt: existing.reviewedAt,
      confirmedAt: existing.confirmedAt,
      rejectedAt: existing.rejectedAt,
      expiresAt: existing.expiresAt,
    );
    _depositRequests[index] = updated;
    _pushNotification(
      topic: 'deposit_submitted',
      message:
          'Payment submitted for ${existing.reference}. The treasury team is reviewing it.',
      resourceId: existing.id,
    );
    return updated;
  }

  @override
  Future<List<GteDepositRequest>> listDepositRequests() async {
    await _delay();
    return List<GteDepositRequest>.of(_depositRequests, growable: false);
  }

  @override
  Future<GteTreasuryWithdrawalRequest> createWithdrawalRequest(
      GteWithdrawalCreateRequest request) async {
    await _delay();
    final GteWithdrawalEligibility eligibility =
        _computeWithdrawalEligibility();
    if (eligibility.requiresKyc || eligibility.requiresBankAccount) {
      throw const GteApiException(
        type: GteApiErrorType.validation,
        message: 'KYC and bank details are required before withdrawing.',
      );
    }
    if (request.amountCoin > eligibility.withdrawableNow) {
      throw const GteApiException(
        type: GteApiErrorType.validation,
        message: 'Insufficient withdrawable balance.',
      );
    }
    final GteUserBankAccount bank = _resolveBankAccount(request.bankAccountId);
    final double rateValue = _treasurySettings.withdrawalRateValue;
    final bool fiatPerCoin = _treasurySettings.withdrawalRateDirection ==
        GteRateDirection.fiatPerCoin;
    final double amountFiat = fiatPerCoin
        ? request.amountCoin * rateValue
        : request.amountCoin / math.max(rateValue, 0.0001);
    final DateTime createdAt = _nextTimestamp();
    final String reference = 'WDR-${++_withdrawalSequence}';
    final GteTreasuryWithdrawalRequest withdrawal =
        GteTreasuryWithdrawalRequest(
      id: 'withdrawal-${_withdrawalSequence}',
      payoutRequestId: 'payout-${_withdrawalSequence}',
      reference: reference,
      status: GteWithdrawalStatus.pendingReview,
      unit: GteLedgerUnit.coin,
      amountCoin: request.amountCoin,
      amountFiat: amountFiat,
      currencyCode: _treasurySettings.currencyCode,
      rateValue: rateValue,
      rateDirection: _treasurySettings.withdrawalRateDirection,
      bankName: bank.bankName,
      bankAccountNumber: bank.accountNumber,
      bankAccountName: bank.accountName,
      bankCode: bank.bankCode,
      kycStatusSnapshot: _kycStatusToString(_kycProfile.status),
      kycTierSnapshot: _kycStatusToString(_kycProfile.status),
      feeAmount: 0,
      totalDebit: request.amountCoin,
      notes: request.notes,
      createdAt: createdAt,
      reviewedAt: null,
      approvedAt: null,
      processedAt: null,
      paidAt: null,
      rejectedAt: null,
      cancelledAt: null,
    );
    _withdrawalRequests.insert(0, withdrawal);
    _walletSummary = GteWalletSummary(
      availableBalance: _walletSummary.availableBalance - request.amountCoin,
      reservedBalance: _walletSummary.reservedBalance + request.amountCoin,
      totalBalance: _walletSummary.totalBalance,
      currency: _walletSummary.currency,
    );
    _walletLedger.insert(
      0,
      GteWalletLedgerEntry(
        id: 'ledger-${++_ledgerSequence}',
        amount: -request.amountCoin,
        reason: 'withdrawal_hold',
        description: 'Withdrawal hold for $reference',
        createdAt: createdAt,
      ),
    );
    _pushNotification(
      topic: 'withdrawal_requested',
      message:
          'Withdrawal $reference queued for review. Status: pending review.',
      resourceId: withdrawal.id,
    );
    return withdrawal;
  }

  @override
  Future<List<GteTreasuryWithdrawalRequest>> listWithdrawalRequests() async {
    await _delay();
    return List<GteTreasuryWithdrawalRequest>.of(_withdrawalRequests,
        growable: false);
  }

  @override
  Future<GteKycProfile> fetchKycProfile() async {
    await _delay();
    return _kycProfile;
  }

  @override
  Future<GteKycProfile> submitKycProfile(GteKycSubmitRequest request) async {
    await _delay();
    final DateTime now = _nextTimestamp();
    _kycProfile = GteKycProfile(
      id: _kycProfile.id,
      status: GteKycStatus.pending,
      nin: request.nin ?? _kycProfile.nin,
      bvn: request.bvn ?? _kycProfile.bvn,
      addressLine1: request.addressLine1,
      addressLine2: request.addressLine2,
      city: request.city,
      state: request.state,
      country: request.country,
      idDocumentAttachmentId: request.idDocumentAttachmentId,
      submittedAt: now,
      reviewedAt: null,
      rejectionReason: null,
      createdAt: _kycProfile.createdAt,
      updatedAt: now,
    );
    _pushNotification(
      topic: 'kyc_submitted',
      message: 'KYC submitted. Verification is now pending.',
      resourceId: _kycProfile.id,
    );
    return _kycProfile;
  }

  @override
  Future<List<GteUserBankAccount>> listUserBankAccounts() async {
    await _delay();
    return List<GteUserBankAccount>.of(_userBankAccounts, growable: false);
  }

  @override
  Future<GteUserBankAccount> createUserBankAccount(
      GteUserBankAccountCreate request) async {
    await _delay();
    if (request.setActive) {
      for (int i = 0; i < _userBankAccounts.length; i++) {
        final GteUserBankAccount account = _userBankAccounts[i];
        _userBankAccounts[i] = GteUserBankAccount(
          id: account.id,
          currencyCode: account.currencyCode,
          bankName: account.bankName,
          accountNumber: account.accountNumber,
          accountName: account.accountName,
          bankCode: account.bankCode,
          isActive: false,
          createdAt: account.createdAt,
          updatedAt: account.updatedAt,
        );
      }
    }
    final DateTime now = _nextTimestamp();
    final GteUserBankAccount account = GteUserBankAccount(
      id: 'user-bank-${++_userBankSequence}',
      currencyCode: request.currencyCode,
      bankName: request.bankName,
      accountNumber: request.accountNumber,
      accountName: request.accountName,
      bankCode: request.bankCode,
      isActive: request.setActive,
      createdAt: now,
      updatedAt: now,
    );
    _userBankAccounts.insert(0, account);
    _pushNotification(
      topic: 'bank_details_created',
      message: 'Bank details saved for withdrawals.',
      resourceId: account.id,
    );
    return account;
  }

  @override
  Future<GteUserBankAccount> updateUserBankAccount(
      String bankAccountId, GteUserBankAccountUpdate request) async {
    await _delay();
    final int index = _userBankAccounts.indexWhere(
        (GteUserBankAccount account) => account.id == bankAccountId);
    if (index == -1) {
      throw StateError('Bank account not found');
    }
    if (request.isActive == true) {
      for (int i = 0; i < _userBankAccounts.length; i++) {
        final GteUserBankAccount account = _userBankAccounts[i];
        _userBankAccounts[i] = GteUserBankAccount(
          id: account.id,
          currencyCode: account.currencyCode,
          bankName: account.bankName,
          accountNumber: account.accountNumber,
          accountName: account.accountName,
          bankCode: account.bankCode,
          isActive: account.id == bankAccountId,
          createdAt: account.createdAt,
          updatedAt: account.updatedAt,
        );
      }
    }
    final GteUserBankAccount existing = _userBankAccounts[index];
    final DateTime now = _nextTimestamp();
    final GteUserBankAccount updated = GteUserBankAccount(
      id: existing.id,
      currencyCode: request.currencyCode ?? existing.currencyCode,
      bankName: request.bankName ?? existing.bankName,
      accountNumber: request.accountNumber ?? existing.accountNumber,
      accountName: request.accountName ?? existing.accountName,
      bankCode: request.bankCode ?? existing.bankCode,
      isActive: request.isActive ?? existing.isActive,
      createdAt: existing.createdAt,
      updatedAt: now,
    );
    _userBankAccounts[index] = updated;
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
    return List<GteDispute>.of(_disputes, growable: false);
  }

  @override
  Future<GteDispute> openDispute(GteDisputeCreateRequest request) async {
    await _delay();
    final DateTime now = _nextTimestamp();
    final String disputeId = 'dispute-${++_disputeSequence}';
    final GteDisputeMessage message = GteDisputeMessage(
      id: 'dispute-msg-${_disputeSequence}-1',
      senderUserId: _fixtureSession.user.id,
      senderRole: 'user',
      message: request.message,
      attachmentId: request.attachmentId,
      createdAt: now,
    );
    final GteDispute dispute = GteDispute(
      id: disputeId,
      status: GteDisputeStatus.open,
      reference: request.reference,
      resourceType: request.resourceType,
      resourceId: request.resourceId,
      subject: request.subject,
      createdAt: now,
      updatedAt: now,
      lastMessageAt: now,
      userId: _fixtureSession.user.id,
      userEmail: _fixtureSession.user.email,
      userFullName: _fixtureSession.user.fullName,
      userPhoneNumber: _fixtureSession.user.phoneNumber,
      messages: <GteDisputeMessage>[message],
    );
    _disputes.insert(0, dispute);
    _pushNotification(
      topic: 'dispute_opened',
      message: 'Support dispute opened for ${request.reference}.',
      resourceId: dispute.id,
    );
    return dispute;
  }

  @override
  Future<GteDispute> fetchDispute(String disputeId) async {
    await _delay();
    return _disputes
        .firstWhere((GteDispute dispute) => dispute.id == disputeId);
  }

  @override
  Future<GteDisputeMessage> sendDisputeMessage(
      String disputeId, GteDisputeMessageRequest request) async {
    await _delay();
    final int index =
        _disputes.indexWhere((GteDispute dispute) => dispute.id == disputeId);
    if (index == -1) {
      throw StateError('Dispute not found');
    }
    final DateTime now = _nextTimestamp();
    final GteDisputeMessage message = GteDisputeMessage(
      id: 'dispute-msg-${disputeId}-${now.millisecondsSinceEpoch}',
      senderUserId: _fixtureSession.user.id,
      senderRole: 'user',
      message: request.message,
      attachmentId: request.attachmentId,
      createdAt: now,
    );
    final GteDispute existing = _disputes[index];
    final GteDispute updated = GteDispute(
      id: existing.id,
      status: GteDisputeStatus.awaitingAdmin,
      reference: existing.reference,
      resourceType: existing.resourceType,
      resourceId: existing.resourceId,
      subject: existing.subject,
      createdAt: existing.createdAt,
      updatedAt: now,
      lastMessageAt: now,
      userId: existing.userId,
      userEmail: existing.userEmail,
      userFullName: existing.userFullName,
      userPhoneNumber: existing.userPhoneNumber,
      messages: <GteDisputeMessage>[...existing.messages, message],
    );
    _disputes[index] = updated;
    _pushNotification(
      topic: 'dispute_opened',
      message: 'Your message was sent to support.',
      resourceId: updated.id,
    );
    return message;
  }

  @override
  Future<List<GteNotification>> listNotifications({int limit = 20}) async {
    await _delay();
    final List<GteNotification> sorted = List<GteNotification>.of(
        _notifications,
        growable: false)
      ..sort((GteNotification a, GteNotification b) =>
          (b.createdAt ?? DateTime(0)).compareTo(a.createdAt ?? DateTime(0)));
    return sorted.take(limit).toList(growable: false);
  }

  @override
  Future<void> markNotificationRead(String notificationId) async {
    await _delay();
    final int index = _notifications.indexWhere(
        (GteNotification notification) =>
            notification.notificationId == notificationId);
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
        .map((MapEntry<String, int> entry) => GteAnalyticsSummaryItem(
              name: entry.key,
              count: entry.value,
            ))
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
    await _delay();
    final int pendingDeposits = _depositRequests
        .where((GteDepositRequest deposit) =>
            deposit.status == GteDepositStatus.awaitingPayment ||
            deposit.status == GteDepositStatus.paymentSubmitted ||
            deposit.status == GteDepositStatus.underReview)
        .length;
    final int pendingWithdrawals = _withdrawalRequests
        .where((GteTreasuryWithdrawalRequest withdrawal) =>
            withdrawal.status == GteWithdrawalStatus.pendingReview ||
            withdrawal.status == GteWithdrawalStatus.processing ||
            withdrawal.status == GteWithdrawalStatus.approved)
        .length;
    final int pendingKyc = _kycProfile.status == GteKycStatus.pending ? 1 : 0;
    final int openDisputes = _disputes
        .where(
            (GteDispute dispute) => dispute.status != GteDisputeStatus.closed)
        .length;
    return GteTreasuryDashboard(
      totalUsers: 12840,
      activeUsers: 3210,
      pendingDeposits: pendingDeposits,
      pendingWithdrawals: pendingWithdrawals,
      pendingKyc: pendingKyc,
      openDisputes: openDisputes,
      depositsConfirmedToday: 18,
      withdrawalsPaidToday: 7,
      walletLiability: _walletSummary.totalBalance,
      pendingTreasuryExposure: pendingDeposits.toDouble(),
    );
  }

  @override
  Future<GteTreasurySettings> fetchTreasurySettings() async {
    await _delay();
    return _treasurySettings;
  }

  @override
  Future<GteTreasurySettings> updateTreasurySettings(
      GteTreasurySettingsUpdate request) async {
    await _delay();
    _treasurySettings = GteTreasurySettings(
      id: _treasurySettings.id,
      settingsKey: _treasurySettings.settingsKey,
      currencyCode: request.currencyCode ?? _treasurySettings.currencyCode,
      depositRateValue:
          request.depositRateValue ?? _treasurySettings.depositRateValue,
      depositRateDirection: request.depositRateDirection ??
          _treasurySettings.depositRateDirection,
      withdrawalRateValue:
          request.withdrawalRateValue ?? _treasurySettings.withdrawalRateValue,
      withdrawalRateDirection: request.withdrawalRateDirection ??
          _treasurySettings.withdrawalRateDirection,
      minDeposit: request.minDeposit ?? _treasurySettings.minDeposit,
      maxDeposit: request.maxDeposit ?? _treasurySettings.maxDeposit,
      minWithdrawal: request.minWithdrawal ?? _treasurySettings.minWithdrawal,
      maxWithdrawal: request.maxWithdrawal ?? _treasurySettings.maxWithdrawal,
      depositMode: request.depositMode ?? _treasurySettings.depositMode,
      withdrawalMode:
          request.withdrawalMode ?? _treasurySettings.withdrawalMode,
      maintenanceMessage:
          request.maintenanceMessage ?? _treasurySettings.maintenanceMessage,
      whatsappNumber:
          request.whatsappNumber ?? _treasurySettings.whatsappNumber,
      activeBankAccount: request.activeBankAccountId == null
          ? _treasurySettings.activeBankAccount
          : _treasuryBankAccounts.firstWhere(
              (GteTreasuryBankAccount account) =>
                  account.id == request.activeBankAccountId,
              orElse: () => _treasuryBankAccounts.first,
            ),
      createdAt: _treasurySettings.createdAt,
      updatedAt: _nextTimestamp(),
    );
    _pushNotification(
      topic: 'treasury_settings_updated',
      message: 'Treasury settings updated.',
      resourceId: _treasurySettings.id,
    );
    return _treasurySettings;
  }

  @override
  Future<List<GteTreasuryBankAccount>> listTreasuryBankAccounts() async {
    await _delay();
    return List<GteTreasuryBankAccount>.of(_treasuryBankAccounts,
        growable: false);
  }

  @override
  Future<GteTreasuryBankAccount> createTreasuryBankAccount(
      GteTreasuryBankAccountCreate request) async {
    await _delay();
    final DateTime now = _nextTimestamp();
    final GteTreasuryBankAccount account = GteTreasuryBankAccount(
      id: 'treasury-bank-${++_treasuryBankSequence}',
      currencyCode: request.currencyCode,
      bankName: request.bankName,
      accountNumber: request.accountNumber,
      accountName: request.accountName,
      bankCode: request.bankCode,
      isActive: request.isActive,
      createdAt: now,
      updatedAt: now,
    );
    if (request.isActive) {
      for (int i = 0; i < _treasuryBankAccounts.length; i++) {
        final GteTreasuryBankAccount existing = _treasuryBankAccounts[i];
        _treasuryBankAccounts[i] = GteTreasuryBankAccount(
          id: existing.id,
          currencyCode: existing.currencyCode,
          bankName: existing.bankName,
          accountNumber: existing.accountNumber,
          accountName: existing.accountName,
          bankCode: existing.bankCode,
          isActive: false,
          createdAt: existing.createdAt,
          updatedAt: existing.updatedAt,
        );
      }
    }
    _treasuryBankAccounts.insert(0, account);
    return account;
  }

  @override
  Future<GteTreasuryBankAccount> updateTreasuryBankAccount(
      String accountId, GteTreasuryBankAccountUpdate request) async {
    await _delay();
    final int index = _treasuryBankAccounts.indexWhere(
        (GteTreasuryBankAccount account) => account.id == accountId);
    if (index == -1) {
      throw StateError('Treasury bank account not found');
    }
    if (request.isActive == true) {
      for (int i = 0; i < _treasuryBankAccounts.length; i++) {
        final GteTreasuryBankAccount existing = _treasuryBankAccounts[i];
        _treasuryBankAccounts[i] = GteTreasuryBankAccount(
          id: existing.id,
          currencyCode: existing.currencyCode,
          bankName: existing.bankName,
          accountNumber: existing.accountNumber,
          accountName: existing.accountName,
          bankCode: existing.bankCode,
          isActive: existing.id == accountId,
          createdAt: existing.createdAt,
          updatedAt: existing.updatedAt,
        );
      }
    }
    final GteTreasuryBankAccount existing = _treasuryBankAccounts[index];
    final DateTime now = _nextTimestamp();
    final GteTreasuryBankAccount updated = GteTreasuryBankAccount(
      id: existing.id,
      currencyCode: request.currencyCode ?? existing.currencyCode,
      bankName: request.bankName ?? existing.bankName,
      accountNumber: request.accountNumber ?? existing.accountNumber,
      accountName: request.accountName ?? existing.accountName,
      bankCode: request.bankCode ?? existing.bankCode,
      isActive: request.isActive ?? existing.isActive,
      createdAt: existing.createdAt,
      updatedAt: now,
    );
    _treasuryBankAccounts[index] = updated;
    return updated;
  }

  @override
  Future<GteAdminQueuePage<GteAdminDeposit>> fetchAdminDeposits({
    int limit = 50,
    int offset = 0,
    String? status,
    String? query,
  }) async {
    await _delay();
    Iterable<GteDepositRequest> items = _depositRequests;
    if (status != null) {
      final GteDepositStatus parsed = _depositStatusFromString(status);
      items =
          items.where((GteDepositRequest deposit) => deposit.status == parsed);
    }
    if (query != null && query.isNotEmpty) {
      final String needle = query.toLowerCase();
      items = items.where((GteDepositRequest deposit) =>
          deposit.reference.toLowerCase().contains(needle) ||
          (deposit.payerName ?? '').toLowerCase().contains(needle) ||
          (deposit.senderBank ?? '').toLowerCase().contains(needle));
    }
    final List<GteAdminDeposit> mapped = items
        .skip(offset)
        .take(limit)
        .map((GteDepositRequest deposit) => GteAdminDeposit(
              id: deposit.id,
              reference: deposit.reference,
              status: deposit.status,
              amountFiat: deposit.amountFiat,
              amountCoin: deposit.amountCoin,
              currencyCode: deposit.currencyCode,
              payerName: deposit.payerName,
              senderBank: deposit.senderBank,
              transferReference: deposit.transferReference,
              createdAt: deposit.createdAt,
              submittedAt: deposit.submittedAt,
              reviewedAt: deposit.reviewedAt,
              confirmedAt: deposit.confirmedAt,
              rejectedAt: deposit.rejectedAt,
              adminNotes: deposit.adminNotes,
              userId: _fixtureSession.user.id,
              userEmail: _fixtureSession.user.email,
              userFullName: _fixtureSession.user.fullName,
              userPhoneNumber: _fixtureSession.user.phoneNumber,
            ))
        .toList(growable: false);
    return GteAdminQueuePage<GteAdminDeposit>(
      items: mapped,
      total: items.length,
      limit: limit,
      offset: offset,
    );
  }

  @override
  Future<GteDepositRequest> adminConfirmDeposit(String depositId,
      {String? adminNotes}) async {
    await _delay();
    final int index = _depositRequests
        .indexWhere((GteDepositRequest deposit) => deposit.id == depositId);
    if (index == -1) {
      throw StateError('Deposit not found');
    }
    final GteDepositRequest existing = _depositRequests[index];
    final DateTime now = _nextTimestamp();
    final GteDepositRequest updated = GteDepositRequest(
      id: existing.id,
      reference: existing.reference,
      status: GteDepositStatus.confirmed,
      amountFiat: existing.amountFiat,
      amountCoin: existing.amountCoin,
      currencyCode: existing.currencyCode,
      rateValue: existing.rateValue,
      rateDirection: existing.rateDirection,
      bankName: existing.bankName,
      bankAccountNumber: existing.bankAccountNumber,
      bankAccountName: existing.bankAccountName,
      bankCode: existing.bankCode,
      payerName: existing.payerName,
      senderBank: existing.senderBank,
      transferReference: existing.transferReference,
      proofAttachmentId: existing.proofAttachmentId,
      adminNotes: adminNotes ?? existing.adminNotes,
      createdAt: existing.createdAt,
      submittedAt: existing.submittedAt,
      reviewedAt: now,
      confirmedAt: now,
      rejectedAt: null,
      expiresAt: existing.expiresAt,
    );
    _depositRequests[index] = updated;
    _walletSummary = GteWalletSummary(
      availableBalance: _walletSummary.availableBalance + existing.amountCoin,
      reservedBalance: _walletSummary.reservedBalance,
      totalBalance: _walletSummary.totalBalance + existing.amountCoin,
      currency: _walletSummary.currency,
    );
    _walletLedger.insert(
      0,
      GteWalletLedgerEntry(
        id: 'ledger-${++_ledgerSequence}',
        amount: existing.amountCoin,
        reason: 'deposit_confirmed',
        description: 'Deposit confirmed ${existing.reference}',
        createdAt: now,
      ),
    );
    _pushNotification(
      topic: 'deposit_confirmed',
      message: 'Deposit ${existing.reference} confirmed.',
      resourceId: existing.id,
    );
    return updated;
  }

  @override
  Future<GteDepositRequest> adminRejectDeposit(String depositId,
      {String? adminNotes}) async {
    await _delay();
    final int index = _depositRequests
        .indexWhere((GteDepositRequest deposit) => deposit.id == depositId);
    if (index == -1) {
      throw StateError('Deposit not found');
    }
    final GteDepositRequest existing = _depositRequests[index];
    final DateTime now = _nextTimestamp();
    final GteDepositRequest updated = GteDepositRequest(
      id: existing.id,
      reference: existing.reference,
      status: GteDepositStatus.rejected,
      amountFiat: existing.amountFiat,
      amountCoin: existing.amountCoin,
      currencyCode: existing.currencyCode,
      rateValue: existing.rateValue,
      rateDirection: existing.rateDirection,
      bankName: existing.bankName,
      bankAccountNumber: existing.bankAccountNumber,
      bankAccountName: existing.bankAccountName,
      bankCode: existing.bankCode,
      payerName: existing.payerName,
      senderBank: existing.senderBank,
      transferReference: existing.transferReference,
      proofAttachmentId: existing.proofAttachmentId,
      adminNotes: adminNotes ?? existing.adminNotes,
      createdAt: existing.createdAt,
      submittedAt: existing.submittedAt,
      reviewedAt: now,
      confirmedAt: null,
      rejectedAt: now,
      expiresAt: existing.expiresAt,
    );
    _depositRequests[index] = updated;
    _pushNotification(
      topic: 'deposit_rejected',
      message: 'Deposit ${existing.reference} rejected.',
      resourceId: existing.id,
    );
    return updated;
  }

  @override
  Future<GteDepositRequest> adminReviewDeposit(String depositId,
      {String? adminNotes}) async {
    await _delay();
    final int index = _depositRequests
        .indexWhere((GteDepositRequest deposit) => deposit.id == depositId);
    if (index == -1) {
      throw StateError('Deposit not found');
    }
    final GteDepositRequest existing = _depositRequests[index];
    final DateTime now = _nextTimestamp();
    final GteDepositRequest updated = GteDepositRequest(
      id: existing.id,
      reference: existing.reference,
      status: GteDepositStatus.underReview,
      amountFiat: existing.amountFiat,
      amountCoin: existing.amountCoin,
      currencyCode: existing.currencyCode,
      rateValue: existing.rateValue,
      rateDirection: existing.rateDirection,
      bankName: existing.bankName,
      bankAccountNumber: existing.bankAccountNumber,
      bankAccountName: existing.bankAccountName,
      bankCode: existing.bankCode,
      payerName: existing.payerName,
      senderBank: existing.senderBank,
      transferReference: existing.transferReference,
      proofAttachmentId: existing.proofAttachmentId,
      adminNotes: adminNotes ?? existing.adminNotes,
      createdAt: existing.createdAt,
      submittedAt: existing.submittedAt,
      reviewedAt: now,
      confirmedAt: existing.confirmedAt,
      rejectedAt: existing.rejectedAt,
      expiresAt: existing.expiresAt,
    );
    _depositRequests[index] = updated;
    return updated;
  }

  @override
  Future<GteAdminQueuePage<GteAdminWithdrawal>> fetchAdminWithdrawals({
    int limit = 50,
    int offset = 0,
    String? status,
    String? query,
  }) async {
    await _delay();
    Iterable<GteTreasuryWithdrawalRequest> items = _withdrawalRequests;
    if (status != null) {
      final GteWithdrawalStatus parsed = _withdrawalStatusFromString(status);
      items = items.where((GteTreasuryWithdrawalRequest withdrawal) =>
          withdrawal.status == parsed);
    }
    if (query != null && query.isNotEmpty) {
      final String needle = query.toLowerCase();
      items = items.where((GteTreasuryWithdrawalRequest withdrawal) =>
          withdrawal.reference.toLowerCase().contains(needle) ||
          withdrawal.bankAccountName.toLowerCase().contains(needle) ||
          withdrawal.bankAccountNumber.contains(needle));
    }
    final List<GteAdminWithdrawal> mapped = items
        .skip(offset)
        .take(limit)
        .map((GteTreasuryWithdrawalRequest withdrawal) => GteAdminWithdrawal(
              id: withdrawal.id,
              reference: withdrawal.reference,
              status: withdrawal.status,
              amountCoin: withdrawal.amountCoin,
              amountFiat: withdrawal.amountFiat,
              currencyCode: withdrawal.currencyCode,
              bankName: withdrawal.bankName,
              bankAccountNumber: withdrawal.bankAccountNumber,
              bankAccountName: withdrawal.bankAccountName,
              createdAt: withdrawal.createdAt,
              reviewedAt: withdrawal.reviewedAt,
              approvedAt: withdrawal.approvedAt,
              processedAt: withdrawal.processedAt,
              paidAt: withdrawal.paidAt,
              rejectedAt: withdrawal.rejectedAt,
              cancelledAt: withdrawal.cancelledAt,
              userId: _fixtureSession.user.id,
              userEmail: _fixtureSession.user.email,
              userFullName: _fixtureSession.user.fullName,
              userPhoneNumber: _fixtureSession.user.phoneNumber,
            ))
        .toList(growable: false);
    return GteAdminQueuePage<GteAdminWithdrawal>(
      items: mapped,
      total: items.length,
      limit: limit,
      offset: offset,
    );
  }

  @override
  Future<GteTreasuryWithdrawalRequest> adminUpdateWithdrawalStatus(
    String withdrawalId, {
    required GteWithdrawalStatus status,
    String? adminNotes,
  }) async {
    await _delay();
    final int index = _withdrawalRequests.indexWhere(
        (GteTreasuryWithdrawalRequest withdrawal) =>
            withdrawal.id == withdrawalId);
    if (index == -1) {
      throw StateError('Withdrawal not found');
    }
    final GteTreasuryWithdrawalRequest existing = _withdrawalRequests[index];
    final DateTime now = _nextTimestamp();
    final GteTreasuryWithdrawalRequest updated = GteTreasuryWithdrawalRequest(
      id: existing.id,
      payoutRequestId: existing.payoutRequestId,
      reference: existing.reference,
      status: status,
      unit: existing.unit,
      amountCoin: existing.amountCoin,
      amountFiat: existing.amountFiat,
      currencyCode: existing.currencyCode,
      rateValue: existing.rateValue,
      rateDirection: existing.rateDirection,
      bankName: existing.bankName,
      bankAccountNumber: existing.bankAccountNumber,
      bankAccountName: existing.bankAccountName,
      bankCode: existing.bankCode,
      kycStatusSnapshot: existing.kycStatusSnapshot,
      kycTierSnapshot: existing.kycTierSnapshot,
      feeAmount: existing.feeAmount,
      totalDebit: existing.totalDebit,
      notes: existing.notes,
      createdAt: existing.createdAt,
      reviewedAt: status == GteWithdrawalStatus.pendingReview ||
              status == GteWithdrawalStatus.approved
          ? now
          : existing.reviewedAt,
      approvedAt:
          status == GteWithdrawalStatus.approved ? now : existing.approvedAt,
      processedAt:
          status == GteWithdrawalStatus.processing ? now : existing.processedAt,
      paidAt: status == GteWithdrawalStatus.paid ? now : existing.paidAt,
      rejectedAt:
          status == GteWithdrawalStatus.rejected ? now : existing.rejectedAt,
      cancelledAt:
          status == GteWithdrawalStatus.cancelled ? now : existing.cancelledAt,
    );
    _withdrawalRequests[index] = updated;
    if (status == GteWithdrawalStatus.paid) {
      _walletSummary = GteWalletSummary(
        availableBalance: _walletSummary.availableBalance,
        reservedBalance:
            math.max(0, _walletSummary.reservedBalance - existing.amountCoin),
        totalBalance: _walletSummary.totalBalance - existing.amountCoin,
        currency: _walletSummary.currency,
      );
      _pushNotification(
        topic: 'withdrawal_paid',
        message: 'Withdrawal ${existing.reference} marked as paid.',
        resourceId: existing.id,
      );
    } else if (status == GteWithdrawalStatus.rejected ||
        status == GteWithdrawalStatus.cancelled) {
      _walletSummary = GteWalletSummary(
        availableBalance: _walletSummary.availableBalance + existing.amountCoin,
        reservedBalance:
            math.max(0, _walletSummary.reservedBalance - existing.amountCoin),
        totalBalance: _walletSummary.totalBalance,
        currency: _walletSummary.currency,
      );
      _pushNotification(
        topic: 'withdrawal_rejected',
        message: 'Withdrawal ${existing.reference} was rejected.',
        resourceId: existing.id,
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
    await _delay();
    final List<GteAdminKyc> items = <GteAdminKyc>[
      GteAdminKyc(
        id: _kycProfile.id,
        userId: _fixtureSession.user.id,
        status: _kycProfile.status,
        nin: _kycProfile.nin,
        bvn: _kycProfile.bvn,
        addressLine1: _kycProfile.addressLine1,
        city: _kycProfile.city,
        state: _kycProfile.state,
        country: _kycProfile.country,
        submittedAt: _kycProfile.submittedAt,
        reviewedAt: _kycProfile.reviewedAt,
        rejectionReason: _kycProfile.rejectionReason,
        userEmail: _fixtureSession.user.email,
        userFullName: _fixtureSession.user.fullName,
        userPhoneNumber: _fixtureSession.user.phoneNumber,
      ),
    ];
    return GteAdminQueuePage<GteAdminKyc>(
      items: items,
      total: items.length,
      limit: limit,
      offset: offset,
    );
  }

  @override
  Future<GteKycProfile> adminReviewKyc(
      String profileId, GteKycReviewRequest request) async {
    await _delay();
    if (profileId != _kycProfile.id) {
      throw StateError('KYC profile not found');
    }
    final DateTime now = _nextTimestamp();
    _kycProfile = GteKycProfile(
      id: _kycProfile.id,
      status: request.status,
      nin: _kycProfile.nin,
      bvn: _kycProfile.bvn,
      addressLine1: _kycProfile.addressLine1,
      addressLine2: _kycProfile.addressLine2,
      city: _kycProfile.city,
      state: _kycProfile.state,
      country: _kycProfile.country,
      idDocumentAttachmentId: _kycProfile.idDocumentAttachmentId,
      submittedAt: _kycProfile.submittedAt,
      reviewedAt: now,
      rejectionReason: request.rejectionReason,
      createdAt: _kycProfile.createdAt,
      updatedAt: now,
    );
    _pushNotification(
      topic: request.status == GteKycStatus.rejected
          ? 'kyc_rejected'
          : 'kyc_approved',
      message: request.status == GteKycStatus.rejected
          ? 'KYC rejected. Please review the notes.'
          : 'KYC verified.',
      resourceId: _kycProfile.id,
    );
    return _kycProfile;
  }

  @override
  Future<GteAdminQueuePage<GteDispute>> fetchAdminDisputes({
    int limit = 50,
    int offset = 0,
    String? status,
    String? query,
  }) async {
    await _delay();
    Iterable<GteDispute> items = _disputes;
    if (status != null) {
      final GteDisputeStatus parsed = _disputeStatusFromString(status);
      items = items.where((GteDispute dispute) => dispute.status == parsed);
    }
    if (query != null && query.isNotEmpty) {
      final String needle = query.toLowerCase();
      items = items.where((GteDispute dispute) =>
          dispute.reference.toLowerCase().contains(needle));
    }
    final List<GteDispute> paged =
        items.skip(offset).take(limit).toList(growable: false);
    return GteAdminQueuePage<GteDispute>(
      items: paged,
      total: items.length,
      limit: limit,
      offset: offset,
    );
  }

  @override
  Future<GteDispute> fetchAdminDispute(String disputeId) async {
    await _delay();
    return _disputes
        .firstWhere((GteDispute dispute) => dispute.id == disputeId);
  }

  @override
  Future<GteDisputeMessage> adminSendDisputeMessage(
      String disputeId, GteDisputeMessageRequest request) async {
    await _delay();
    final int index =
        _disputes.indexWhere((GteDispute dispute) => dispute.id == disputeId);
    if (index == -1) {
      throw StateError('Dispute not found');
    }
    final DateTime now = _nextTimestamp();
    final GteDisputeMessage message = GteDisputeMessage(
      id: 'dispute-admin-msg-${disputeId}-${now.millisecondsSinceEpoch}',
      senderUserId: 'admin-1',
      senderRole: 'admin',
      message: request.message,
      attachmentId: request.attachmentId,
      createdAt: now,
    );
    final GteDispute existing = _disputes[index];
    final GteDispute updated = GteDispute(
      id: existing.id,
      status: GteDisputeStatus.awaitingUser,
      reference: existing.reference,
      resourceType: existing.resourceType,
      resourceId: existing.resourceId,
      subject: existing.subject,
      createdAt: existing.createdAt,
      updatedAt: now,
      lastMessageAt: now,
      userId: existing.userId,
      userEmail: existing.userEmail,
      userFullName: existing.userFullName,
      userPhoneNumber: existing.userPhoneNumber,
      messages: <GteDisputeMessage>[...existing.messages, message],
    );
    _disputes[index] = updated;
    _pushNotification(
      topic: 'dispute_reply',
      message: 'Support replied to dispute ${existing.reference}.',
      resourceId: existing.id,
    );
    return message;
  }

  @override
  Future<GtePortfolioView> fetchPortfolio() async {
    await _delay();
    return GtePortfolioView(
      holdings:
          List<GtePortfolioHolding>.of(_portfolio.holdings, growable: false),
    );
  }

  @override
  Future<GtePortfolioSummary> fetchPortfolioSummary() async {
    await _delay();
    return _portfolioSummary;
  }

  Future<void> _delay() async {
    await Future<void>.delayed(latency);
  }

  DateTime _nextTimestamp() {
    _clock = _clock.add(const Duration(seconds: 1));
    return _clock;
  }

  GteTreasuryWithdrawalRequest _buildWithdrawalFixture(String withdrawalId) {
    final DateTime createdAt = _nextTimestamp();
    final GteUserBankAccount? bank =
        _userBankAccounts.isNotEmpty ? _userBankAccounts.first : null;
    return GteTreasuryWithdrawalRequest(
      id: withdrawalId,
      payoutRequestId: 'payout-$withdrawalId',
      reference: 'WDR-FIXTURE',
      status: GteWithdrawalStatus.pendingReview,
      unit: GteLedgerUnit.coin,
      amountCoin: 0,
      amountFiat: 0,
      currencyCode: _treasurySettings.currencyCode,
      rateValue: _treasurySettings.withdrawalRateValue,
      rateDirection: _treasurySettings.withdrawalRateDirection,
      bankName: bank?.bankName ?? 'Unknown bank',
      bankAccountNumber: bank?.accountNumber ?? '0000000000',
      bankAccountName: bank?.accountName ?? 'Unknown account',
      bankCode: bank?.bankCode,
      kycStatusSnapshot: _kycProfile.status.name,
      kycTierSnapshot: _kycProfile.status.name,
      feeAmount: 0,
      totalDebit: 0,
      notes: 'Generated fallback withdrawal fixture.',
      createdAt: createdAt,
      reviewedAt: null,
      approvedAt: null,
      processedAt: null,
      paidAt: null,
      rejectedAt: null,
      cancelledAt: null,
    );
  }

  GteWalletOverview _buildWalletOverview() {
    final double pendingDeposits = _depositRequests
        .where((GteDepositRequest deposit) =>
            deposit.status == GteDepositStatus.awaitingPayment ||
            deposit.status == GteDepositStatus.paymentSubmitted ||
            deposit.status == GteDepositStatus.underReview)
        .fold<double>(0, (double sum, GteDepositRequest deposit) {
      return sum + deposit.amountCoin;
    });
    final double pendingWithdrawals = _withdrawalRequests
        .where((GteTreasuryWithdrawalRequest withdrawal) =>
            withdrawal.status == GteWithdrawalStatus.pendingReview ||
            withdrawal.status == GteWithdrawalStatus.processing ||
            withdrawal.status == GteWithdrawalStatus.approved)
        .fold<double>(0, (double sum, GteTreasuryWithdrawalRequest withdrawal) {
      return sum + withdrawal.amountCoin;
    });
    final double totalInflow = _walletLedger
        .where((GteWalletLedgerEntry entry) => entry.amount > 0)
        .fold<double>(0, (double sum, GteWalletLedgerEntry entry) {
      return sum + entry.amount;
    });
    final double totalOutflow = _walletLedger
        .where((GteWalletLedgerEntry entry) => entry.amount < 0)
        .fold<double>(0, (double sum, GteWalletLedgerEntry entry) {
      return sum + entry.amount.abs();
    });
    final GteWithdrawalEligibility eligibility =
        _computeWithdrawalEligibility();
    final List<GtePolicyRequirementSummary> missing =
        _currentMissingPolicyRequirements();
    return GteWalletOverview(
      availableBalance: _walletSummary.availableBalance,
      pendingDeposits: pendingDeposits,
      pendingWithdrawals: pendingWithdrawals,
      totalInflow: totalInflow,
      totalOutflow: totalOutflow,
      withdrawableNow: eligibility.withdrawableNow,
      currency: _walletSummary.currency,
      countryCode: _kycProfile.country?.toUpperCase() ?? 'NG',
      requiredPolicyAcceptancesMissing: missing.length,
      policyBlocked: missing.isNotEmpty,
      policyBlockReason: missing.isEmpty
          ? null
          : 'Accept the latest required policy documents to unlock full wallet access.',
    );
  }

  List<GtePolicyRequirementSummary> _currentMissingPolicyRequirements() {
    final Set<String> acceptedKeys = _policyAcceptances
        .map((GtePolicyAcceptanceSummary item) => item.documentKey)
        .toSet();
    return _policyDocuments
        .where((GtePolicyDocumentDetail doc) =>
            doc.isMandatory && !acceptedKeys.contains(doc.documentKey))
        .map(
          (GtePolicyDocumentDetail doc) => GtePolicyRequirementSummary(
            documentKey: doc.documentKey,
            title: doc.title,
            versionLabel: doc.latestVersion?.versionLabel ?? 'v1.0',
            isMandatory: doc.isMandatory,
            effectiveAt: doc.latestVersion?.effectiveAt,
          ),
        )
        .toList(growable: false);
  }

  GteWithdrawalEligibility _computeWithdrawalEligibility() {
    final GteKycStatus status = _kycProfile.status;
    final bool requiresKyc = status == GteKycStatus.unverified ||
        status == GteKycStatus.pending ||
        status == GteKycStatus.rejected;
    final bool requiresBankAccount = !_userBankAccounts
        .any((GteUserBankAccount account) => account.isActive);
    final double available = _walletSummary.availableBalance;
    double withdrawable = available;
    double remainingAllowance = available;
    DateTime? nextEligibleAt;
    final DateTime now = _clock;
    if (requiresKyc || requiresBankAccount) {
      withdrawable = 0;
      remainingAllowance = 0;
    } else if (status == GteKycStatus.partialVerifiedNoId) {
      final DateTime windowStart = now.subtract(const Duration(hours: 24));
      final List<GteTreasuryWithdrawalRequest> recent = _withdrawalRequests
          .where((GteTreasuryWithdrawalRequest withdrawal) =>
              (withdrawal.createdAt ?? now).isAfter(windowStart) &&
              (withdrawal.status == GteWithdrawalStatus.pendingReview ||
                  withdrawal.status == GteWithdrawalStatus.processing ||
                  withdrawal.status == GteWithdrawalStatus.approved ||
                  withdrawal.status == GteWithdrawalStatus.paid))
          .toList(growable: false);
      final double recentTotal = recent.fold<double>(
          0,
          (double sum, GteTreasuryWithdrawalRequest withdrawal) =>
              sum + withdrawal.amountCoin);
      final double limit = available * 0.3;
      remainingAllowance = math.max(0, limit - recentTotal);
      withdrawable = math.min(available, remainingAllowance);
      if (remainingAllowance <= 0 && recent.isNotEmpty) {
        final DateTime earliest = recent
            .map((GteTreasuryWithdrawalRequest withdrawal) =>
                withdrawal.createdAt ?? now)
            .reduce((DateTime left, DateTime right) =>
                left.isBefore(right) ? left : right);
        nextEligibleAt = earliest.add(const Duration(hours: 24));
      }
    }
    final double pendingWithdrawals = _withdrawalRequests
        .where((GteTreasuryWithdrawalRequest withdrawal) =>
            withdrawal.status == GteWithdrawalStatus.pendingReview ||
            withdrawal.status == GteWithdrawalStatus.processing ||
            withdrawal.status == GteWithdrawalStatus.approved)
        .fold<double>(0, (double sum, GteTreasuryWithdrawalRequest withdrawal) {
      return sum + withdrawal.amountCoin;
    });
    final List<GtePolicyRequirementSummary> missing =
        _currentMissingPolicyRequirements();
    if (missing.isNotEmpty) {
      withdrawable = 0;
      remainingAllowance = 0;
    }
    return GteWithdrawalEligibility(
      availableBalance: available,
      withdrawableNow: withdrawable,
      remainingAllowance: remainingAllowance,
      nextEligibleAt: nextEligibleAt,
      kycStatus: status,
      requiresKyc: requiresKyc,
      requiresBankAccount: requiresBankAccount,
      pendingWithdrawals: pendingWithdrawals,
      countryCode: _kycProfile.country?.toUpperCase() ?? 'NG',
      countryWithdrawalsEnabled: true,
      missingRequiredPolicies: missing
          .map((GtePolicyRequirementSummary item) => item.documentKey)
          .toList(growable: false),
      policyBlocked: missing.isNotEmpty,
      policyBlockReason: missing.isEmpty
          ? null
          : 'Policy acceptance required before withdrawal is enabled.',
    );
  }

  GteUserBankAccount _resolveBankAccount(String? bankAccountId) {
    if (bankAccountId != null) {
      return _userBankAccounts.firstWhere(
          (GteUserBankAccount account) => account.id == bankAccountId);
    }
    final Iterable<GteUserBankAccount> active = _userBankAccounts
        .where((GteUserBankAccount account) => account.isActive);
    if (active.isNotEmpty) {
      return active.first;
    }
    if (_userBankAccounts.isEmpty) {
      throw const GteApiException(
        type: GteApiErrorType.validation,
        message: 'No bank account on file.',
      );
    }
    return _userBankAccounts.first;
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

  double? _referencePriceFor(String playerId, GteOrderSide side) {
    final GteMarketTicker? ticker = _baseTickers[playerId];
    if (ticker == null) {
      return null;
    }
    return side == GteOrderSide.buy
        ? ticker.bestAsk ?? ticker.referencePrice ?? ticker.lastPrice
        : ticker.bestBid ?? ticker.referencePrice ?? ticker.lastPrice;
  }

  double? _priceForOrder(GteOrderRecord order) {
    return order.maxPrice ?? _referencePriceFor(order.playerId, order.side);
  }

  List<GteOrderBookLevel> _mergeOrderBookSide(
    List<GteOrderBookLevel> seeded,
    Iterable<GteOrderRecord> liveOrders, {
    required bool descending,
  }) {
    final Map<String, _MutableBookLevel> byPrice =
        <String, _MutableBookLevel>{};

    void mergeLevel({
      required double price,
      required double quantity,
      required int orderCount,
    }) {
      if (price <= 0 || quantity <= 0 || orderCount <= 0) {
        return;
      }
      final String key = price.toStringAsFixed(4);
      final _MutableBookLevel existing = byPrice[key] ??
          _MutableBookLevel(
            price: price,
            quantity: 0.0,
            orderCount: 0,
          );
      existing.quantity += quantity;
      existing.orderCount += orderCount;
      byPrice[key] = existing;
    }

    for (final GteOrderBookLevel level in seeded) {
      mergeLevel(
        price: level.price,
        quantity: level.quantity,
        orderCount: level.orderCount,
      );
    }
    for (final GteOrderRecord order in liveOrders) {
      final double? price = _priceForOrder(order);
      if (price == null) {
        continue;
      }
      mergeLevel(
        price: price,
        quantity: order.remainingQuantity,
        orderCount: 1,
      );
    }

    final List<_MutableBookLevel> merged =
        byPrice.values.toList(growable: false)
          ..sort((_MutableBookLevel left, _MutableBookLevel right) {
            return descending
                ? right.price.compareTo(left.price)
                : left.price.compareTo(right.price);
          });
    return merged
        .map(
          (_MutableBookLevel level) => GteOrderBookLevel(
            price: level.price,
            quantity: level.quantity,
            orderCount: level.orderCount,
          ),
        )
        .toList(growable: false);
  }

  void _rebuildPortfolioSummary() {
    final double totalMarketValue = _portfolio.holdings.fold<double>(
      0.0,
      (double sum, GtePortfolioHolding holding) => sum + holding.marketValue,
    );
    final double unrealizedPlTotal = _portfolio.holdings.fold<double>(
      0.0,
      (double sum, GtePortfolioHolding holding) => sum + holding.unrealizedPl,
    );
    _portfolioSummary = GtePortfolioSummary(
      totalMarketValue: totalMarketValue,
      cashBalance: _walletSummary.availableBalance,
      totalEquity: totalMarketValue + _walletSummary.availableBalance,
      unrealizedPlTotal: unrealizedPlTotal,
      realizedPlTotal: _seedPortfolioSummary.realizedPlTotal,
    );
  }
}

class _MutableBookLevel {
  _MutableBookLevel({
    required this.price,
    required this.quantity,
    required this.orderCount,
  });

  final double price;
  double quantity;
  int orderCount;
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

GteOrderBook _cloneOrderBook(GteOrderBook orderBook) {
  return GteOrderBook(
    playerId: orderBook.playerId,
    bids: List<GteOrderBookLevel>.from(orderBook.bids),
    asks: List<GteOrderBookLevel>.from(orderBook.asks),
    generatedAt: orderBook.generatedAt,
  );
}

GteDepositStatus _depositStatusFromString(String value) {
  switch (value.toLowerCase()) {
    case 'payment_submitted':
      return GteDepositStatus.paymentSubmitted;
    case 'under_review':
      return GteDepositStatus.underReview;
    case 'confirmed':
      return GteDepositStatus.confirmed;
    case 'rejected':
      return GteDepositStatus.rejected;
    case 'expired':
      return GteDepositStatus.expired;
    case 'disputed':
      return GteDepositStatus.disputed;
    case 'awaiting_payment':
    default:
      return GteDepositStatus.awaitingPayment;
  }
}

GteWithdrawalStatus _withdrawalStatusFromString(String value) {
  switch (value.toLowerCase()) {
    case 'draft':
      return GteWithdrawalStatus.draft;
    case 'pending_kyc':
      return GteWithdrawalStatus.pendingKyc;
    case 'approved':
      return GteWithdrawalStatus.approved;
    case 'rejected':
      return GteWithdrawalStatus.rejected;
    case 'processing':
      return GteWithdrawalStatus.processing;
    case 'paid':
      return GteWithdrawalStatus.paid;
    case 'disputed':
      return GteWithdrawalStatus.disputed;
    case 'cancelled':
      return GteWithdrawalStatus.cancelled;
    case 'pending_review':
    default:
      return GteWithdrawalStatus.pendingReview;
  }
}

GteDisputeStatus _disputeStatusFromString(String value) {
  switch (value.toLowerCase()) {
    case 'awaiting_user':
      return GteDisputeStatus.awaitingUser;
    case 'awaiting_admin':
      return GteDisputeStatus.awaitingAdmin;
    case 'resolved':
      return GteDisputeStatus.resolved;
    case 'closed':
      return GteDisputeStatus.closed;
    case 'open':
    default:
      return GteDisputeStatus.open;
  }
}

String _kycStatusToString(GteKycStatus status) {
  switch (status) {
    case GteKycStatus.unverified:
      return 'unverified';
    case GteKycStatus.pending:
      return 'pending';
    case GteKycStatus.partialVerifiedNoId:
      return 'partial_verified_no_id';
    case GteKycStatus.fullyVerified:
      return 'fully_verified';
    case GteKycStatus.rejected:
      return 'rejected';
  }
}

final List<GtePolicyDocumentDetail> _seedPolicyDocuments =
    <GtePolicyDocumentDetail>[
  GtePolicyDocumentDetail(
    id: 'policy-terms',
    documentKey: 'terms_and_conditions',
    title: 'Terms & Conditions',
    isMandatory: true,
    active: true,
    latestVersion: GtePolicyDocumentVersionSummary(
      id: 'policy-terms-v1',
      versionLabel: 'v1.0',
      effectiveAt: DateTime.utc(2026, 3, 1),
      publishedAt: DateTime.utc(2026, 3, 1),
      changelog: 'Initial public release.',
    ),
    bodyMarkdown: '''# Terms & Conditions

GTEX is a rules-driven football competition and exchange platform. Use of wallet, competition, and reward surfaces is subject to market rules, integrity controls, and local availability.''',
  ),
  GtePolicyDocumentDetail(
    id: 'policy-privacy',
    documentKey: 'privacy_policy',
    title: 'Privacy Policy',
    isMandatory: true,
    active: true,
    latestVersion: GtePolicyDocumentVersionSummary(
      id: 'policy-privacy-v1',
      versionLabel: 'v1.0',
      effectiveAt: DateTime.utc(2026, 3, 1),
      publishedAt: DateTime.utc(2026, 3, 1),
      changelog: 'Initial public release.',
    ),
    bodyMarkdown: '''# Privacy Policy

We collect account, KYC, payment proof, and gameplay telemetry needed to operate GTEX, detect abuse, and satisfy moderation, anti-fraud, and regional controls.''',
  ),
  GtePolicyDocumentDetail(
    id: 'policy-withdrawal',
    documentKey: 'withdrawal_policy',
    title: 'Withdrawal Policy',
    isMandatory: true,
    active: true,
    latestVersion: GtePolicyDocumentVersionSummary(
      id: 'policy-withdrawal-v1',
      versionLabel: 'v1.0',
      effectiveAt: DateTime.utc(2026, 3, 1),
      publishedAt: DateTime.utc(2026, 3, 1),
      changelog: 'Clarifies KYC, bank account, and regional restrictions.',
    ),
    bodyMarkdown: '''# Withdrawal Policy

Withdrawals depend on KYC state, verified bank details, active policy acceptance, treasury review, and regional feature flags.''',
  ),
];

final List<GtePolicyAcceptanceSummary> _seedPolicyAcceptances =
    <GtePolicyAcceptanceSummary>[
  GtePolicyAcceptanceSummary(
    documentKey: 'terms_and_conditions',
    title: 'Terms & Conditions',
    versionLabel: 'v1.0',
    acceptedAt: DateTime.utc(2026, 3, 2, 10),
  ),
];

final GteAuthSession _fixtureSession = GteAuthSession(
  accessToken: 'fixture-session-token',
  tokenType: 'bearer',
  expiresIn: 3600,
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

final Map<String, GteMarketTicker> _seedTickers = <String, GteMarketTicker>{
  'lamine-yamal': const GteMarketTicker(
    playerId: 'lamine-yamal',
    symbol: 'L. Yamal',
    lastPrice: 1180,
    bestBid: 1172,
    bestAsk: 1188,
    spread: 16,
    midPrice: 1180,
    referencePrice: 1095,
    dayChange: 85,
    dayChangePercent: 7.8,
    volume24h: 34,
  ),
  'jude-bellingham': const GteMarketTicker(
    playerId: 'jude-bellingham',
    symbol: 'J. Bellingham',
    lastPrice: 1260,
    bestBid: 1254,
    bestAsk: 1266,
    spread: 12,
    midPrice: 1260,
    referencePrice: 1205,
    dayChange: 55,
    dayChangePercent: 4.6,
    volume24h: 28,
  ),
  'jamal-musiala': const GteMarketTicker(
    playerId: 'jamal-musiala',
    symbol: 'J. Musiala',
    lastPrice: 1095,
    bestBid: 1087,
    bestAsk: 1104,
    spread: 17,
    midPrice: 1095.5,
    referencePrice: 1054,
    dayChange: 41,
    dayChangePercent: 3.9,
    volume24h: 19,
  ),
  'victor-osimhen': const GteMarketTicker(
    playerId: 'victor-osimhen',
    symbol: 'V. Osimhen',
    lastPrice: 920,
    bestBid: 914,
    bestAsk: 929,
    spread: 15,
    midPrice: 921.5,
    referencePrice: 867,
    dayChange: 53,
    dayChangePercent: 6.1,
    volume24h: 24,
  ),
};

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

final Map<String, GteOrderBook> _seedOrderBooks = <String, GteOrderBook>{
  'lamine-yamal': GteOrderBook(
    playerId: 'lamine-yamal',
    generatedAt: DateTime.utc(2026, 3, 11, 12),
    bids: const <GteOrderBookLevel>[
      GteOrderBookLevel(price: 1172, quantity: 3, orderCount: 2),
      GteOrderBookLevel(price: 1166, quantity: 6, orderCount: 3),
    ],
    asks: const <GteOrderBookLevel>[
      GteOrderBookLevel(price: 1188, quantity: 2, orderCount: 1),
      GteOrderBookLevel(price: 1196, quantity: 5, orderCount: 2),
    ],
  ),
  'jude-bellingham': GteOrderBook(
    playerId: 'jude-bellingham',
    generatedAt: DateTime.utc(2026, 3, 11, 12),
    bids: const <GteOrderBookLevel>[
      GteOrderBookLevel(price: 1254, quantity: 2, orderCount: 1),
      GteOrderBookLevel(price: 1248, quantity: 5, orderCount: 3),
    ],
    asks: const <GteOrderBookLevel>[
      GteOrderBookLevel(price: 1266, quantity: 2, orderCount: 1),
      GteOrderBookLevel(price: 1274, quantity: 4, orderCount: 2),
    ],
  ),
  'jamal-musiala': GteOrderBook(
    playerId: 'jamal-musiala',
    generatedAt: DateTime.utc(2026, 3, 11, 12),
    bids: const <GteOrderBookLevel>[
      GteOrderBookLevel(price: 1087, quantity: 1.5, orderCount: 1),
      GteOrderBookLevel(price: 1081, quantity: 4.0, orderCount: 2),
    ],
    asks: const <GteOrderBookLevel>[
      GteOrderBookLevel(price: 1104, quantity: 1.0, orderCount: 1),
      GteOrderBookLevel(price: 1112, quantity: 3.0, orderCount: 2),
    ],
  ),
  'victor-osimhen': GteOrderBook(
    playerId: 'victor-osimhen',
    generatedAt: DateTime.utc(2026, 3, 11, 12),
    bids: const <GteOrderBookLevel>[],
    asks: const <GteOrderBookLevel>[
      GteOrderBookLevel(price: 929, quantity: 1.0, orderCount: 1),
    ],
  ),
};

const GteWalletSummary _seedWalletSummary = GteWalletSummary(
  availableBalance: 1200,
  reservedBalance: 62.5,
  totalBalance: 1262.5,
  currency: GteLedgerUnit.credit,
);

const List<GtePortfolioHolding> _seedPortfolioHoldings = <GtePortfolioHolding>[
  GtePortfolioHolding(
    playerId: 'lamine-yamal',
    quantity: 1,
    averageCost: 1095,
    currentPrice: 1180,
    marketValue: 1180,
    unrealizedPl: 85,
    unrealizedPlPercent: 7.8,
  ),
  GtePortfolioHolding(
    playerId: 'victor-osimhen',
    quantity: 1.2,
    averageCost: 850,
    currentPrice: 920,
    marketValue: 1104,
    unrealizedPl: 84,
    unrealizedPlPercent: 8.2,
  ),
];

const GtePortfolioSummary _seedPortfolioSummary = GtePortfolioSummary(
  totalMarketValue: 2284,
  cashBalance: 1200,
  totalEquity: 3484,
  unrealizedPlTotal: 169,
  realizedPlTotal: 42,
);

final List<GteWalletLedgerEntry> _seedWalletLedger = <GteWalletLedgerEntry>[
  GteWalletLedgerEntry(
    id: 'ledger-1',
    amount: -62.5,
    reason: 'withdrawal_hold',
    description: 'Reserved credits for resting buy order',
    createdAt: DateTime.utc(2026, 3, 11, 11, 30),
  ),
  GteWalletLedgerEntry(
    id: 'ledger-2',
    amount: 1200,
    reason: 'adjustment',
    description: 'Demo wallet seed',
    createdAt: DateTime.utc(2026, 3, 11, 8),
  ),
  GteWalletLedgerEntry(
    id: 'ledger-3',
    amount: -1095,
    reason: 'trade_execution',
    description: 'Portfolio acquisition cash leg',
    createdAt: DateTime.utc(2026, 3, 10, 18, 15),
  ),
];

final List<GteOrderRecord> _seedOrders = <GteOrderRecord>[
  GteOrderRecord(
    id: 'ord-1',
    userId: 'fixture-user',
    playerId: 'lamine-yamal',
    side: GteOrderSide.buy,
    status: GteOrderStatus.open,
    quantity: 0.5,
    filledQuantity: 0,
    remainingQuantity: 0.5,
    maxPrice: 125,
    reservedAmount: 62.5,
    currency: GteLedgerUnit.credit,
    holdTransactionId: 'ledger-1',
    createdAt: DateTime.utc(2026, 3, 11, 11, 30),
    updatedAt: DateTime.utc(2026, 3, 11, 11, 30),
    executionSummary: GteOrderExecutionSummary(
      executionCount: 0,
      totalNotional: 0.0,
      averagePrice: null,
    ),
  ),
  GteOrderRecord(
    id: 'ord-2',
    userId: 'fixture-user',
    playerId: 'victor-osimhen',
    side: GteOrderSide.buy,
    status: GteOrderStatus.filled,
    quantity: 1,
    filledQuantity: 1,
    remainingQuantity: 0.0,
    maxPrice: 920,
    reservedAmount: 0.0,
    currency: GteLedgerUnit.credit,
    holdTransactionId: 'ledger-3',
    createdAt: DateTime.utc(2026, 3, 10, 18, 15),
    updatedAt: DateTime.utc(2026, 3, 10, 18, 16),
    executionSummary: GteOrderExecutionSummary(
      executionCount: 1,
      totalNotional: 920,
      averagePrice: 920,
      lastExecutedAt: DateTime.utc(2026, 3, 10, 18, 16),
      executions: <GteOrderExecution>[
        GteOrderExecution(
          payload: <String, Object?>{
            'price': 920,
            'quantity': 1,
          },
        ),
      ],
    ),
  ),
];

final GteTreasuryBankAccount _seedTreasuryBankAccount = GteTreasuryBankAccount(
  id: 'treasury-bank-1',
  currencyCode: 'NGN',
  bankName: 'GTEX Treasury',
  accountNumber: '0001234567',
  accountName: 'GTEX Treasury Desk',
  bankCode: 'GTB',
  isActive: true,
  createdAt: DateTime.utc(2026, 3, 10, 9),
  updatedAt: DateTime.utc(2026, 3, 10, 9),
);

final List<GteTreasuryBankAccount> _seedTreasuryBankAccounts =
    <GteTreasuryBankAccount>[
  _seedTreasuryBankAccount,
];

final GteTreasurySettings _seedTreasurySettings = GteTreasurySettings(
  id: 'treasury-settings-1',
  settingsKey: 'default',
  currencyCode: 'NGN',
  depositRateValue: 900,
  depositRateDirection: GteRateDirection.fiatPerCoin,
  withdrawalRateValue: 880,
  withdrawalRateDirection: GteRateDirection.fiatPerCoin,
  minDeposit: 1000,
  maxDeposit: 500000,
  minWithdrawal: 2000,
  maxWithdrawal: 500000,
  depositMode: GtePaymentMode.manual,
  withdrawalMode: GtePaymentMode.manual,
  maintenanceMessage: null,
  whatsappNumber: '+2347000000000',
  activeBankAccount: _seedTreasuryBankAccount,
  createdAt: DateTime.utc(2026, 3, 10, 9),
  updatedAt: DateTime.utc(2026, 3, 10, 9),
);

final List<GteUserBankAccount> _seedUserBankAccounts = <GteUserBankAccount>[
  GteUserBankAccount(
    id: 'user-bank-1',
    currencyCode: 'NGN',
    bankName: 'Zenith Bank',
    accountNumber: '0123456789',
    accountName: 'Ayo Martins',
    bankCode: 'ZENITH',
    isActive: true,
    createdAt: DateTime.utc(2026, 3, 10, 11),
    updatedAt: DateTime.utc(2026, 3, 10, 11),
  ),
];

final GteKycProfile _seedKycProfile = GteKycProfile(
  id: 'kyc-1',
  status: GteKycStatus.partialVerifiedNoId,
  nin: 'NIN-4392901',
  bvn: null,
  addressLine1: '12 Adeola Odeku St',
  addressLine2: null,
  city: 'Lagos',
  state: 'Lagos',
  country: 'Nigeria',
  idDocumentAttachmentId: null,
  submittedAt: DateTime.utc(2026, 3, 10, 12),
  reviewedAt: DateTime.utc(2026, 3, 10, 14),
  rejectionReason: null,
  createdAt: DateTime.utc(2026, 3, 10, 12),
  updatedAt: DateTime.utc(2026, 3, 10, 14),
);

final List<GteDepositRequest> _seedDeposits = <GteDepositRequest>[
  GteDepositRequest(
    id: 'deposit-1',
    reference: 'DEP-1001',
    status: GteDepositStatus.paymentSubmitted,
    amountFiat: 250000,
    amountCoin: 277.78,
    currencyCode: 'NGN',
    rateValue: 900,
    rateDirection: GteRateDirection.fiatPerCoin,
    bankName: 'GTEX Treasury',
    bankAccountNumber: '0001234567',
    bankAccountName: 'GTEX Treasury Desk',
    bankCode: 'GTB',
    payerName: 'Ayo Martins',
    senderBank: 'GTBank',
    transferReference: 'TRX-8493',
    proofAttachmentId: null,
    adminNotes: null,
    createdAt: DateTime.utc(2026, 3, 11, 8),
    submittedAt: DateTime.utc(2026, 3, 11, 8, 5),
    reviewedAt: null,
    confirmedAt: null,
    rejectedAt: null,
    expiresAt: null,
  ),
  GteDepositRequest(
    id: 'deposit-2',
    reference: 'DEP-1000',
    status: GteDepositStatus.confirmed,
    amountFiat: 50000,
    amountCoin: 55.56,
    currencyCode: 'NGN',
    rateValue: 900,
    rateDirection: GteRateDirection.fiatPerCoin,
    bankName: 'GTEX Treasury',
    bankAccountNumber: '0001234567',
    bankAccountName: 'GTEX Treasury Desk',
    bankCode: 'GTB',
    payerName: 'Ayo Martins',
    senderBank: 'Access Bank',
    transferReference: 'TRX-8390',
    proofAttachmentId: null,
    adminNotes: 'Matched transfer reference.',
    createdAt: DateTime.utc(2026, 3, 10, 9),
    submittedAt: DateTime.utc(2026, 3, 10, 9, 3),
    reviewedAt: DateTime.utc(2026, 3, 10, 9, 10),
    confirmedAt: DateTime.utc(2026, 3, 10, 9, 11),
    rejectedAt: null,
    expiresAt: null,
  ),
];

final List<GteTreasuryWithdrawalRequest> _seedWithdrawals =
    <GteTreasuryWithdrawalRequest>[
  GteTreasuryWithdrawalRequest(
    id: 'withdrawal-1',
    payoutRequestId: 'payout-1',
    reference: 'WDR-2001',
    status: GteWithdrawalStatus.processing,
    unit: GteLedgerUnit.coin,
    amountCoin: 120,
    amountFiat: 105600,
    currencyCode: 'NGN',
    rateValue: 880,
    rateDirection: GteRateDirection.fiatPerCoin,
    bankName: 'Zenith Bank',
    bankAccountNumber: '0123456789',
    bankAccountName: 'Ayo Martins',
    bankCode: 'ZENITH',
    kycStatusSnapshot: 'partial_verified_no_id',
    kycTierSnapshot: 'partial_verified_no_id',
    feeAmount: 0,
    totalDebit: 120,
    notes: 'Weekly payout',
    createdAt: DateTime.utc(2026, 3, 11, 7),
    reviewedAt: DateTime.utc(2026, 3, 11, 7, 10),
    approvedAt: DateTime.utc(2026, 3, 11, 7, 12),
    processedAt: DateTime.utc(2026, 3, 11, 7, 30),
    paidAt: null,
    rejectedAt: null,
    cancelledAt: null,
  ),
];

final List<GteDispute> _seedDisputes = <GteDispute>[
  GteDispute(
    id: 'dispute-1',
    status: GteDisputeStatus.awaitingAdmin,
    reference: 'DEP-1001',
    resourceType: 'deposit',
    resourceId: 'deposit-1',
    subject: 'Deposit still pending',
    createdAt: DateTime.utc(2026, 3, 11, 9),
    updatedAt: DateTime.utc(2026, 3, 11, 9, 5),
    lastMessageAt: DateTime.utc(2026, 3, 11, 9, 5),
    userId: 'fixture-user',
    userEmail: 'fixture.trader@gte.local',
    userFullName: 'Fixture Trader',
    userPhoneNumber: '+2347000000000',
    messages: <GteDisputeMessage>[
      GteDisputeMessage(
        id: 'dispute-msg-1',
        senderUserId: 'fixture-user',
        senderRole: 'user',
        message: 'I paid 30 minutes ago, please confirm.',
        attachmentId: null,
        createdAt: DateTime.utc(2026, 3, 11, 9, 5),
      ),
    ],
  ),
];

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
