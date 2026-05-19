import 'dart:collection';
import 'dart:async';

import 'package:flutter/foundation.dart';

import '../core/app_feedback.dart';
import '../domain/match/match_weights.dart';

import '../data/gte_api_repository.dart';
import '../data/gte_exchange_api_client.dart';
import '../data/gte_exchange_models.dart';
import '../data/gte_models.dart';

const int _marketPageSize = 500;

class GteExchangeController extends ChangeNotifier {
  GteExchangeController({required GteExchangeApiClient api}) : _api = api;

  final GteExchangeApiClient _api;
  GteExchangeApiClient get api => _api;
  final GteRequestGate _marketGate = GteRequestGate();
  final GteRequestGate _playerGate = GteRequestGate();
  final GteRequestGate _portfolioGate = GteRequestGate();
  final GteRequestGate _ordersGate = GteRequestGate();
  final GteRequestGate _authGate = GteRequestGate();
  final GteRequestGate _complianceGate = GteRequestGate();

  Future<void>? _bootstrapFuture;
  Future<void>? _portfolioFuture;
  Future<void>? _ordersFuture;
  Future<void>? _complianceFuture;
  DateTime? marketSyncedAt;
  DateTime? playerSyncedAt;
  DateTime? portfolioSyncedAt;
  DateTime? ordersSyncedAt;
  DateTime? complianceSyncedAt;

  bool isBootstrapping = false;
  bool isLoadingMarket = false;
  bool isLoadingMoreMarket = false;
  bool isLoadingPlayer = false;
  bool isSigningIn = false;
  bool isLoadingPortfolio = false;
  bool isLoadingOrders = false;
  bool isSubmittingOrder = false;
  bool isRefreshingOrder = false;
  bool isCancellingOrder = false;
  bool isLoadingCompliance = false;

  PlayerFilter marketFilter = const PlayerFilter();
  MatchWeights _weights = MatchWeights.defaultWeights();
  String selectedCandleInterval = '1h';

  String? marketError;
  String? playerError;
  String? playerProfileError;
  String? authError;
  String? portfolioError;
  String? ordersError;
  String? orderError;
  String? adminBuybackError;
  String? complianceError;

  GteAuthSession? session;
  GteMarketPlayerListView? marketPage;
  GtePlayerMarketSnapshot? selectedPlayer;
  PlayerProfile? selectedProfile;
  GteWalletSummary? walletSummary;
  GtePortfolioView? portfolio;
  GtePortfolioSummary? portfolioSummary;
  GteComplianceStatus? complianceStatus;
  List<GtePolicyRequirementSummary> policyRequirements =
      const <GtePolicyRequirementSummary>[];
  int recentOrderTotal = 0;
  int openOrderTotal = 0;

  final Map<String, GteOrderRecord> _ordersById = <String, GteOrderRecord>{};
  final Map<String, GteAdminBuybackPreview> _adminBuybackPreviewsByOrderId =
      <String, GteAdminBuybackPreview>{};
  final Set<String> _loadingAdminBuybackPreviewOrderIds = <String>{};
  final Set<String> _executingAdminBuybackOrderIds = <String>{};
  final List<String> _recentOrderIds = <String>[];
  final List<String> _openOrderIds = <String>[];
  final Map<String, _PlayerEngagementState> _playerEngagement =
      <String, _PlayerEngagementState>{};
  bool _hasLoadedOrdersOnce = false;

  List<GteMarketPlayerListItem> get players =>
      marketPage?.items ?? const <GteMarketPlayerListItem>[];

  String get marketSearch => marketFilter.search ?? '';
  String get marketClub => marketFilter.club ?? '';
  String get marketLeague => marketFilter.league ?? '';
  String get marketNationalTeam => marketFilter.nationalTeam ?? '';

  MatchWeights get weights => _weights;

  bool get hasActiveMarketFilters => marketFilter.hasActiveFilters;

  bool get isAuthenticated => session != null;

  bool get isAdmin => session?.user.role == 'admin';

  String? get accessToken => session?.accessToken;

  bool get hasMorePlayers {
    return marketPage?.hasMore ?? false;
  }

  List<GteOrderRecord> get recentOrders => _ordersForIds(_recentOrderIds);

  List<GteOrderRecord> get openOrders => _ordersForIds(_openOrderIds);

  GteAdminBuybackPreview? adminBuybackPreviewForOrder(String orderId) =>
      _adminBuybackPreviewsByOrderId[orderId];

  bool isLoadingAdminBuybackPreview(String orderId) =>
      _loadingAdminBuybackPreviewOrderIds.contains(orderId);

  bool isExecutingAdminBuyback(String orderId) =>
      _executingAdminBuybackOrderIds.contains(orderId);

  void syncSession(GteAuthSession? nextSession) {
    if (_sessionsEquivalent(session, nextSession)) {
      return;
    }
    session = nextSession;
    notifyListeners();
  }

  bool get hasLoadedOrders =>
      isLoadingOrders ||
      _hasLoadedOrdersOnce ||
      recentOrderTotal > 0 ||
      openOrderTotal > 0 ||
      ordersError != null;

  GteOrderRecord? orderForPlayer(String playerId) {
    for (final GteOrderRecord order in recentOrders) {
      if (order.playerId == playerId) {
        return order;
      }
    }
    for (final GteOrderRecord order in openOrders) {
      if (order.playerId == playerId) {
        return order;
      }
    }
    final List<GteOrderRecord> fallback = _ordersById.values.toList(
      growable: false,
    )..sort((GteOrderRecord left, GteOrderRecord right) {
      final DateTime leftStamp =
          left.updatedAt ??
          left.createdAt ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true);
      final DateTime rightStamp =
          right.updatedAt ??
          right.createdAt ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true);
      return rightStamp.compareTo(leftStamp);
    });
    for (final GteOrderRecord order in fallback) {
      if (order.playerId == playerId) {
        return order;
      }
    }
    return null;
  }

  Future<void> bootstrap() {
    if (_bootstrapFuture != null) {
      return _bootstrapFuture!;
    }
    isBootstrapping = true;
    notifyListeners();
    final Future<void> task = loadMarket(reset: true).whenComplete(() {
      isBootstrapping = false;
      _bootstrapFuture = null;
      notifyListeners();
    });
    _bootstrapFuture = task;
    return task;
  }

  bool _sessionsEquivalent(GteAuthSession? left, GteAuthSession? right) {
    if (identical(left, right)) {
      return true;
    }
    if (left == null || right == null) {
      return left == right;
    }
    if (left.accessToken != right.accessToken ||
        left.refreshToken != right.refreshToken ||
        left.sessionId != right.sessionId ||
        left.user.id != right.user.id ||
        left.user.role != right.user.role) {
      return false;
    }
    if (left.permissions.length != right.permissions.length) {
      return false;
    }
    for (int index = 0; index < left.permissions.length; index += 1) {
      if (left.permissions[index] != right.permissions[index]) {
        return false;
      }
    }
    return true;
  }

  Future<void> loadMarket({
    String? search,
    PlayerFilter? filter,
    bool reset = false,
  }) async {
    final PlayerFilter nextFilter =
        ((filter ?? marketFilter).copyWith(
          search:
              search ?? (filter == null ? marketFilter.search : filter.search),
        )).normalized();
    final bool shouldReset =
        reset || marketPage == null || nextFilter != marketFilter;
    if ((isLoadingMarket || isLoadingMoreMarket) && !shouldReset) {
      return;
    }
    if (!shouldReset && !hasMorePlayers) {
      return;
    }
    final int requestId = _marketGate.begin();
    marketError = null;
    marketFilter = nextFilter;
    if (shouldReset) {
      isLoadingMarket = true;
      marketPage = null;
    } else {
      isLoadingMoreMarket = true;
    }
    notifyListeners();

    try {
      final String? cursor = shouldReset ? null : _nextMarketCursor();
      final int offset = shouldReset ? 0 : _nextMarketOffset();
      final GteMarketPlayerListView response = await _api.fetchPlayers(
        query: GteMarketPlayersQuery(
          limit: _marketPageSize,
          cursor: cursor,
          offset: offset,
          search: nextFilter.search,
          position: nextFilter.position,
          country: nextFilter.country,
          nationalTeam: nextFilter.nationalTeam,
          club: nextFilter.club,
          league: nextFilter.league,
          minAge: nextFilter.minAge,
          maxAge: nextFilter.maxAge,
          availability: nextFilter.availability,
        ),
      );
      if (!_marketGate.isActive(requestId)) {
        return;
      }
      marketSyncedAt = DateTime.now().toUtc();
      if (shouldReset || marketPage == null) {
        marketPage = response;
      } else {
        marketPage = _mergeMarketPage(marketPage!, response);
      }
    } catch (error) {
      if (_marketGate.isActive(requestId)) {
        marketError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_marketGate.isActive(requestId)) {
        isLoadingMarket = false;
        isLoadingMoreMarket = false;
        notifyListeners();
      }
    }
  }

  String? _nextMarketCursor() {
    final String? cursor = marketPage?.nextCursor?.trim();
    if (cursor == null || cursor.isEmpty) {
      return null;
    }
    return cursor;
  }

  int _nextMarketOffset() {
    return marketPage?.items.length ?? 0;
  }

  GteMarketPlayerListView _mergeMarketPage(
    GteMarketPlayerListView current,
    GteMarketPlayerListView next,
  ) {
    final LinkedHashMap<String, GteMarketPlayerListItem> uniquePlayers =
        LinkedHashMap<String, GteMarketPlayerListItem>();
    for (final GteMarketPlayerListItem player in current.items) {
      uniquePlayers[player.playerId] = player;
    }
    for (final GteMarketPlayerListItem player in next.items) {
      uniquePlayers[player.playerId] = player;
    }
    return GteMarketPlayerListView(
      items: uniquePlayers.values.toList(growable: false),
      limit: next.limit,
      hasMore: next.hasMore,
      nextCursor: next.nextCursor,
      offset: 0,
      total:
          next.total > uniquePlayers.length ? next.total : uniquePlayers.length,
    );
  }

  Future<void> openPlayer(String playerId, {String interval = '1h'}) async {
    final int requestId = _playerGate.begin();
    selectedCandleInterval = interval;
    playerError = null;
    playerProfileError = null;
    selectedProfile = null;
    isLoadingPlayer = true;
    notifyListeners();

    try {
      final GtePlayerMarketSnapshot snapshot = await _api.fetchPlayerMarket(
        playerId,
        interval: interval,
        limit: 30,
      );
      if (!_playerGate.isActive(requestId)) {
        return;
      }
      selectedPlayer = snapshot;
      playerSyncedAt = DateTime.now().toUtc();
    } catch (error) {
      if (_playerGate.isActive(requestId)) {
        playerError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_playerGate.isActive(requestId)) {
        isLoadingPlayer = false;
        notifyListeners();
      }
    }
  }

  Future<void> changeCandleInterval(String interval) async {
    final GtePlayerMarketSnapshot? current = selectedPlayer;
    if (current == null || interval == selectedCandleInterval) {
      return;
    }
    final int requestId = _playerGate.begin();
    selectedCandleInterval = interval;
    isLoadingPlayer = true;
    playerError = null;
    notifyListeners();

    try {
      final GteMarketCandles candles = await _api.fetchCandles(
        current.detail.playerId,
        interval: interval,
        limit: 30,
      );
      if (!_playerGate.isActive(requestId)) {
        return;
      }
      selectedPlayer = current.copyWith(candles: candles);
      playerSyncedAt = DateTime.now().toUtc();
    } catch (error) {
      if (_playerGate.isActive(requestId)) {
        playerError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_playerGate.isActive(requestId)) {
        isLoadingPlayer = false;
        notifyListeners();
      }
    }
  }

  Future<void> signIn({required String email, required String password}) async {
    final int requestId = _authGate.begin();
    authError = null;
    isSigningIn = true;
    notifyListeners();

    try {
      final GteAuthSession nextSession = await _api.login(
        email: email,
        password: password,
      );
      if (!_authGate.isActive(requestId)) {
        return;
      }
      session = nextSession;
      await Future.wait<void>(<Future<void>>[
        _refreshTradingState(
          playerId: selectedPlayer?.detail.playerId,
          refreshPlayer: selectedPlayer != null,
        ),
      ]);
      unawaited(refreshCompliance());
    } catch (error) {
      if (_authGate.isActive(requestId)) {
        authError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_authGate.isActive(requestId)) {
        isSigningIn = false;
        notifyListeners();
      }
    }
  }

  Future<void> register({
    required String fullName,
    required String phoneNumber,
    required String email,
    required String password,
    required bool isOver18,
    required String regionCode,
    String? username,
  }) async {
    final int requestId = _authGate.begin();
    authError = null;
    isSigningIn = true;
    notifyListeners();

    try {
      final GteAuthSession nextSession = await _api.register(
        fullName: fullName,
        phoneNumber: phoneNumber,
        email: email,
        password: password,
        isOver18: isOver18,
        regionCode: regionCode,
        username: username,
      );
      if (!_authGate.isActive(requestId)) {
        return;
      }
      session = nextSession;
      authError = null;
      await refreshAccount();
    } catch (error) {
      if (_authGate.isActive(requestId)) {
        authError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_authGate.isActive(requestId)) {
        isSigningIn = false;
        notifyListeners();
      }
    }
  }

  Future<void> signOut() async {
    await _api.logout();
    session = null;
    walletSummary = null;
    portfolio = null;
    portfolioSummary = null;
    complianceStatus = null;
    policyRequirements = const <GtePolicyRequirementSummary>[];
    authError = null;
    playerProfileError = null;
    portfolioError = null;
    ordersError = null;
    orderError = null;
    adminBuybackError = null;
    complianceError = null;
    selectedProfile = null;
    recentOrderTotal = 0;
    openOrderTotal = 0;
    _recentOrderIds.clear();
    _openOrderIds.clear();
    _hasLoadedOrdersOnce = false;
    _ordersById.clear();
    _adminBuybackPreviewsByOrderId.clear();
    _loadingAdminBuybackPreviewOrderIds.clear();
    _executingAdminBuybackOrderIds.clear();
    _playerEngagement.clear();
    _bootstrapFuture = null;
    _portfolioFuture = null;
    _ordersFuture = null;
    marketFilter = const PlayerFilter();
    _weights = MatchWeights.defaultWeights();
    marketSyncedAt = null;
    playerSyncedAt = null;
    portfolioSyncedAt = null;
    ordersSyncedAt = null;
    complianceSyncedAt = null;
    notifyListeners();
  }

  void bindCurrentClub({
    required String clubId,
    required String clubName,
    String? clubSlug,
  }) {
    final GteAuthSession? currentSession = session;
    if (currentSession == null) {
      return;
    }
    final String resolvedClubId = clubId.trim();
    final String resolvedClubName = clubName.trim();
    final String? resolvedClubSlug =
        clubSlug == null || clubSlug.trim().isEmpty ? null : clubSlug.trim();
    if (resolvedClubId.isEmpty || resolvedClubName.isEmpty) {
      return;
    }

    final Map<String, Object?> clubObject = <String, Object?>{
      'id': resolvedClubId,
      'club_id': resolvedClubId,
      'name': resolvedClubName,
      'club_name': resolvedClubName,
      if (resolvedClubSlug != null) 'slug': resolvedClubSlug,
      if (resolvedClubSlug != null) 'club_slug': resolvedClubSlug,
    };
    final Map<String, Object?> membership = <String, Object?>{
      'club_id': resolvedClubId,
      'club_name': resolvedClubName,
      if (resolvedClubSlug != null) 'club_slug': resolvedClubSlug,
      'organization_type': 'club',
      'is_current': true,
      'is_primary': true,
    };

    final Map<String, Object?> sessionJson = Map<String, Object?>.from(
      currentSession.rawJson,
    );
    final Map<String, Object?> userJson = Map<String, Object?>.from(
      currentSession.user.rawJson,
    );

    for (final Map<String, Object?> target in <Map<String, Object?>>[
      sessionJson,
      userJson,
    ]) {
      target['active_organization_type'] = 'club';
      target['active_organization_id'] = resolvedClubId;
      target['active_organization_name'] = resolvedClubName;
      target['current_club_id'] = resolvedClubId;
      target['current_club_name'] = resolvedClubName;
      target['club_id'] = resolvedClubId;
      target['club_name'] = resolvedClubName;
      if (resolvedClubSlug != null) {
        target['active_organization_slug'] = resolvedClubSlug;
        target['current_club_slug'] = resolvedClubSlug;
        target['club_slug'] = resolvedClubSlug;
      }
      target['club'] = clubObject;
      target['current_club'] = clubObject;
      target['memberships'] = _mergeClubMemberships(
        target['memberships'],
        membership,
      );
      target['owned_clubs'] = _mergeClubMemberships(
        target['owned_clubs'],
        membership,
      );
      target['managed_clubs'] = _mergeClubMemberships(
        target['managed_clubs'],
        membership,
      );
    }

    sessionJson['user'] = userJson;
    session = GteAuthSession.fromJson(sessionJson);
    notifyListeners();
  }

  void updateWeights(MatchWeights newWeights) {
    _weights = newWeights.normalize();
    notifyListeners();
  }

  void applyPreset(MatchWeights preset) {
    updateWeights(preset);
  }

  Future<void> refreshAccount() async {
    if (!isAuthenticated) {
      return;
    }
    await Future.wait<void>(<Future<void>>[
      _refreshTradingState(),
      refreshCompliance(),
    ]);
  }

  Future<void> refreshCompliance() {
    if (!isAuthenticated) {
      return Future<void>.value();
    }
    if (_complianceFuture != null) {
      return _complianceFuture!;
    }
    final int requestId = _complianceGate.begin();
    complianceError = null;
    isLoadingCompliance = true;
    notifyListeners();

    final Future<void> task = () async {
      try {
        final List<dynamic> payload = await Future.wait<dynamic>(
          <Future<dynamic>>[
            _api.fetchComplianceStatus(),
            _api.fetchPolicyRequirements(),
          ],
        );
        if (!_complianceGate.isActive(requestId)) {
          return;
        }
        complianceStatus = payload[0] as GteComplianceStatus;
        policyRequirements = payload[1] as List<GtePolicyRequirementSummary>;
        complianceSyncedAt = DateTime.now().toUtc();
      } catch (error) {
        if (_complianceGate.isActive(requestId)) {
          complianceError = AppFeedback.messageFor(error);
        }
      } finally {
        if (_complianceGate.isActive(requestId)) {
          isLoadingCompliance = false;
          notifyListeners();
        }
        _complianceFuture = null;
      }
    }();

    _complianceFuture = task;
    return task;
  }

  Future<void> loadPortfolio() {
    if (!isAuthenticated) {
      return Future<void>.value();
    }
    if (_portfolioFuture != null) {
      return _portfolioFuture!;
    }
    final int requestId = _portfolioGate.begin();
    portfolioError = null;
    isLoadingPortfolio = true;
    notifyListeners();

    final Future<void> task = () async {
      try {
        final List<dynamic> payload =
            await Future.wait<dynamic>(<Future<dynamic>>[
              _api.fetchWalletSummary(currency: GteLedgerUnit.coin),
              _api.fetchPortfolio(),
              _api.fetchPortfolioSummary(),
            ]);
        if (!_portfolioGate.isActive(requestId)) {
          return;
        }
        walletSummary = payload[0] as GteWalletSummary;
        portfolio = payload[1] as GtePortfolioView;
        portfolioSummary = payload[2] as GtePortfolioSummary;
        portfolioSyncedAt = DateTime.now().toUtc();
      } catch (error) {
        if (_portfolioGate.isActive(requestId)) {
          portfolioError = AppFeedback.messageFor(error);
        }
      } finally {
        if (_portfolioGate.isActive(requestId)) {
          isLoadingPortfolio = false;
          notifyListeners();
        }
        _portfolioFuture = null;
      }
    }();

    _portfolioFuture = task;
    return task;
  }

  Future<void> loadOrders({int limit = 20}) {
    if (!isAuthenticated) {
      return Future<void>.value();
    }
    if (_ordersFuture != null) {
      return _ordersFuture!;
    }
    final int requestId = _ordersGate.begin();
    ordersError = null;
    isLoadingOrders = true;
    notifyListeners();

    final Future<void> task = () async {
      try {
        final List<dynamic> payload = await Future.wait<dynamic>(
          <Future<dynamic>>[
            _api.listOrders(limit: limit),
            _api.listOrders(
              limit: limit,
              statuses: const <GteOrderStatus>[
                GteOrderStatus.open,
                GteOrderStatus.partiallyFilled,
              ],
            ),
          ],
        );
        if (!_ordersGate.isActive(requestId)) {
          return;
        }
        final GteOrderListView recentResponse = payload[0] as GteOrderListView;
        final GteOrderListView openResponse = payload[1] as GteOrderListView;
        recentOrderTotal = recentResponse.total;
        openOrderTotal = openResponse.total;
        _hasLoadedOrdersOnce = true;
        _applyOrderList(_recentOrderIds, recentResponse.items);
        _applyOrderList(_openOrderIds, openResponse.items);
        ordersSyncedAt = DateTime.now().toUtc();
      } catch (error) {
        if (_ordersGate.isActive(requestId)) {
          ordersError = AppFeedback.messageFor(error);
        }
      } finally {
        if (_ordersGate.isActive(requestId)) {
          isLoadingOrders = false;
          notifyListeners();
        }
        _ordersFuture = null;
      }
    }();

    _ordersFuture = task;
    return task;
  }

  Future<GteOrderRecord?> placeOrder({
    required String playerId,
    required GteOrderSide side,
    required double quantity,
    double? maxPrice,
  }) async {
    if (!isAuthenticated || isSubmittingOrder) {
      orderError = isAuthenticated ? orderError : 'Sign in to place orders.';
      notifyListeners();
      return null;
    }
    isSubmittingOrder = true;
    orderError = null;
    notifyListeners();
    try {
      final GteOrderRecord order = await _api.placeOrder(
        playerId: playerId,
        side: side,
        quantity: quantity,
        maxPrice: maxPrice,
      );
      _mergeOrder(order);
      await _refreshTradingState(playerId: playerId, refreshPlayer: true);
      return _ordersById[order.id] ?? order;
    } catch (error) {
      orderError = AppFeedback.messageFor(error);
      notifyListeners();
      return null;
    } finally {
      isSubmittingOrder = false;
      notifyListeners();
    }
  }

  Future<GteOrderRecord?> refreshOrder(String orderId) async {
    if (isRefreshingOrder) {
      return null;
    }
    isRefreshingOrder = true;
    orderError = null;
    notifyListeners();
    try {
      final GteOrderRecord order = await _api.fetchOrder(orderId);
      _mergeOrder(order);
      await _refreshTradingState(
        playerId: order.playerId,
        refreshPlayer: selectedPlayer?.detail.playerId == order.playerId,
      );
      return _ordersById[order.id] ?? order;
    } catch (error) {
      orderError = AppFeedback.messageFor(error);
      notifyListeners();
      return null;
    } finally {
      isRefreshingOrder = false;
      notifyListeners();
    }
  }

  Future<GteOrderRecord?> cancelOrder(String orderId) async {
    if (isCancellingOrder) {
      return null;
    }
    isCancellingOrder = true;
    orderError = null;
    notifyListeners();
    try {
      final GteOrderRecord order = await _api.cancelOrder(orderId);
      _mergeOrder(order);
      await _refreshTradingState(
        playerId: order.playerId,
        refreshPlayer: selectedPlayer?.detail.playerId == order.playerId,
      );
      return _ordersById[order.id] ?? order;
    } catch (error) {
      orderError = AppFeedback.messageFor(error);
      notifyListeners();
      return null;
    } finally {
      isCancellingOrder = false;
      notifyListeners();
    }
  }

  Future<GteAdminBuybackPreview?> loadAdminBuybackPreview(
    String orderId,
  ) async {
    if (!isAuthenticated ||
        _loadingAdminBuybackPreviewOrderIds.contains(orderId)) {
      return _adminBuybackPreviewsByOrderId[orderId];
    }
    _loadingAdminBuybackPreviewOrderIds.add(orderId);
    adminBuybackError = null;
    notifyListeners();
    try {
      final GteAdminBuybackPreview preview = await _api
          .fetchAdminBuybackPreview(orderId);
      _adminBuybackPreviewsByOrderId[orderId] = preview;
      return preview;
    } catch (error) {
      adminBuybackError = AppFeedback.messageFor(error);
      return null;
    } finally {
      _loadingAdminBuybackPreviewOrderIds.remove(orderId);
      notifyListeners();
    }
  }

  Future<GteAdminBuybackExecution?> executeAdminBuyback(String orderId) async {
    if (!isAuthenticated || _executingAdminBuybackOrderIds.contains(orderId)) {
      return null;
    }
    _executingAdminBuybackOrderIds.add(orderId);
    adminBuybackError = null;
    notifyListeners();
    try {
      final GteAdminBuybackExecution execution = await _api.executeAdminBuyback(
        orderId,
      );
      _adminBuybackPreviewsByOrderId[orderId] = execution.preview;
      _mergeOrder(execution.order);
      await _refreshTradingState(
        playerId: execution.order.playerId,
        refreshPlayer:
            selectedPlayer?.detail.playerId == execution.order.playerId,
      );
      return execution;
    } catch (error) {
      adminBuybackError = AppFeedback.messageFor(error);
      notifyListeners();
      return null;
    } finally {
      _executingAdminBuybackOrderIds.remove(orderId);
      notifyListeners();
    }
  }

  String playerLabel(String playerId) {
    for (final GteMarketPlayerListItem player in players) {
      if (player.playerId == playerId) {
        return player.playerName;
      }
    }
    if (selectedPlayer?.detail.playerId == playerId) {
      return selectedPlayer!.detail.identity.playerName;
    }
    return playerId;
  }

  bool isPlayerScouted(String playerId) {
    return _engagementStateFor(playerId).isScouted;
  }

  bool isPlayerShortlisted(String playerId) {
    return _engagementStateFor(playerId).isShortlisted;
  }

  void toggleScouted(String playerId) {
    final _PlayerEngagementState current = _engagementStateFor(playerId);
    _playerEngagement[playerId] = current.copyWith(
      isScouted: !current.isScouted,
    );
    notifyListeners();
  }

  void toggleShortlist(String playerId) {
    final _PlayerEngagementState current = _engagementStateFor(playerId);
    _playerEngagement[playerId] = current.copyWith(
      isShortlisted: !current.isShortlisted,
    );
    notifyListeners();
  }

  Future<void> _refreshTradingState({
    String? playerId,
    bool refreshPlayer = false,
  }) async {
    final List<Future<void>> tasks = <Future<void>>[];
    if (isAuthenticated) {
      tasks.add(loadPortfolio());
      tasks.add(loadOrders());
    }
    if (refreshPlayer && playerId != null) {
      tasks.add(openPlayer(playerId, interval: selectedCandleInterval));
    }
    if (tasks.isEmpty) {
      return;
    }
    await Future.wait<void>(tasks);
  }

  List<GteOrderRecord> _ordersForIds(List<String> orderIds) {
    return orderIds
        .map((String orderId) => _ordersById[orderId])
        .whereType<GteOrderRecord>()
        .toList(growable: false);
  }

  void _applyOrderList(List<String> target, List<GteOrderRecord> orders) {
    target
      ..clear()
      ..addAll(orders.map((GteOrderRecord order) => order.id));
    for (final GteOrderRecord order in orders) {
      _ordersById[order.id] = order;
    }
  }

  void _mergeOrder(GteOrderRecord order) {
    _ordersById[order.id] = order;
    if (order.side != GteOrderSide.sell || !order.canCancel) {
      _adminBuybackPreviewsByOrderId.remove(order.id);
    }
    _recentOrderIds
      ..remove(order.id)
      ..insert(0, order.id);
    if (order.canCancel) {
      _openOrderIds
        ..remove(order.id)
        ..insert(0, order.id);
    } else {
      _openOrderIds.remove(order.id);
    }
    if (recentOrderTotal < _recentOrderIds.length) {
      recentOrderTotal = _recentOrderIds.length;
    }
    if (openOrderTotal < _openOrderIds.length) {
      openOrderTotal = _openOrderIds.length;
    }
  }

  _PlayerEngagementState _engagementStateFor(String playerId) {
    final _PlayerEngagementState? existing = _playerEngagement[playerId];
    if (existing != null) {
      return existing;
    }
    return const _PlayerEngagementState(isScouted: false, isShortlisted: false);
  }
}

List<Object?> _mergeClubMemberships(
  Object? rawMemberships,
  Map<String, Object?> membership,
) {
  final List<Object?> merged = <Object?>[];
  bool replaced = false;
  if (rawMemberships is List) {
    for (final Object? item in rawMemberships) {
      if (item is Map) {
        final Map<String, Object?> existing = item.map(
          (Object? key, Object? value) =>
              MapEntry<String, Object?>(key.toString(), value),
        );
        final String existingClubId =
            existing['club_id']?.toString().trim() ??
            existing['organization_id']?.toString().trim() ??
            '';
        if (existingClubId == membership['club_id']) {
          merged.add(<String, Object?>{...existing, ...membership});
          replaced = true;
          continue;
        }
      }
      merged.add(item);
    }
  }
  if (!replaced) {
    merged.insert(0, membership);
  }
  return merged;
}

class _PlayerEngagementState {
  const _PlayerEngagementState({
    required this.isScouted,
    required this.isShortlisted,
  });

  final bool isScouted;
  final bool isShortlisted;

  _PlayerEngagementState copyWith({bool? isScouted, bool? isShortlisted}) {
    return _PlayerEngagementState(
      isScouted: isScouted ?? this.isScouted,
      isShortlisted: isShortlisted ?? this.isShortlisted,
    );
  }
}
