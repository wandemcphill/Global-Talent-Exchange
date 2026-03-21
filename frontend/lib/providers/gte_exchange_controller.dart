import 'package:flutter/foundation.dart';
import '../core/app_feedback.dart';

import '../data/gte_api_repository.dart';
import '../data/gte_exchange_api_client.dart';
import '../data/gte_exchange_models.dart';
import '../data/gte_models.dart';

const int _marketPageSize = 100;

class GteExchangeController extends ChangeNotifier {
  GteExchangeController({
    required GteExchangeApiClient api,
  }) : _api = api;

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

  String marketSearch = '';
  String selectedCandleInterval = '1h';

  String? marketError;
  String? playerError;
  String? authError;
  String? portfolioError;
  String? ordersError;
  String? orderError;
  String? adminBuybackError;
  String? complianceError;

  GteAuthSession? session;
  GteMarketPlayerListView? marketPage;
  GtePlayerMarketSnapshot? selectedPlayer;
  GteWalletSummary? walletSummary;
  GtePortfolioView? portfolio;
  GtePortfolioSummary? portfolioSummary;
  GteComplianceStatus? complianceStatus;
  List<GtePolicyRequirementSummary> policyRequirements = const <GtePolicyRequirementSummary>[];
  int recentOrderTotal = 0;
  int openOrderTotal = 0;

  final Map<String, GteOrderRecord> _ordersById = <String, GteOrderRecord>{};
  final Map<String, GteAdminBuybackPreview> _adminBuybackPreviewsByOrderId =
      <String, GteAdminBuybackPreview>{};
  final Set<String> _loadingAdminBuybackPreviewOrderIds = <String>{};
  final Set<String> _executingAdminBuybackOrderIds = <String>{};
  final List<String> _recentOrderIds = <String>[];
  final List<String> _openOrderIds = <String>[];
  bool _hasLoadedOrdersOnce = false;

  List<GteMarketPlayerListItem> get players =>
      marketPage?.items ?? const <GteMarketPlayerListItem>[];

  bool get isAuthenticated => session != null;

  bool get isAdmin => session?.user.role == 'admin';

  String? get accessToken => session?.accessToken;

  bool get hasMorePlayers {
    if (marketPage == null) {
      return false;
    }
    return marketPage!.items.length + marketPage!.offset < marketPage!.total;
  }

  List<GteOrderRecord> get recentOrders => _ordersForIds(_recentOrderIds);

  List<GteOrderRecord> get openOrders => _ordersForIds(_openOrderIds);

  GteAdminBuybackPreview? adminBuybackPreviewForOrder(String orderId) =>
      _adminBuybackPreviewsByOrderId[orderId];

  bool isLoadingAdminBuybackPreview(String orderId) =>
      _loadingAdminBuybackPreviewOrderIds.contains(orderId);

  bool isExecutingAdminBuyback(String orderId) =>
      _executingAdminBuybackOrderIds.contains(orderId);

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
    final List<GteOrderRecord> fallback =
        _ordersById.values.toList(growable: false)
          ..sort((GteOrderRecord left, GteOrderRecord right) {
            final DateTime leftStamp = left.updatedAt ??
                left.createdAt ??
                DateTime.fromMillisecondsSinceEpoch(0, isUtc: true);
            final DateTime rightStamp = right.updatedAt ??
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

  Future<void> loadMarket({
    String? search,
    bool reset = false,
  }) async {
    final int requestId = _marketGate.begin();
    final String nextSearch = (search ?? marketSearch).trim();
    marketError = null;
    if (reset || marketPage == null) {
      isLoadingMarket = true;
    } else {
      isLoadingMoreMarket = true;
    }
    notifyListeners();

    try {
      final int offset = reset || marketPage == null
          ? 0
          : marketPage!.offset + marketPage!.items.length;
      final GteMarketPlayerListView response = await _api.fetchPlayers(
        query: GteMarketPlayersQuery(
          limit: _marketPageSize,
          offset: offset,
          search: nextSearch.isEmpty ? null : nextSearch,
        ),
      );
      if (!_marketGate.isActive(requestId)) {
        return;
      }
      marketSearch = nextSearch;
      marketSyncedAt = DateTime.now().toUtc();
      if (reset || marketPage == null) {
        marketPage = response;
      } else {
        marketPage = GteMarketPlayerListView(
          items: <GteMarketPlayerListItem>[
            ...marketPage!.items,
            ...response.items,
          ],
          limit: response.limit,
          offset: 0,
          total: response.total,
        );
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

  Future<void> openPlayer(
    String playerId, {
    String interval = '1h',
  }) async {
    final int requestId = _playerGate.begin();
    selectedCandleInterval = interval;
    playerError = null;
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

  Future<void> signIn({
    required String email,
    required String password,
  }) async {
    final int requestId = _authGate.begin();
    authError = null;
    isSigningIn = true;
    notifyListeners();

    try {
      final GteAuthSession nextSession =
          await _api.login(email: email, password: password);
      if (!_authGate.isActive(requestId)) {
        return;
      }
      session = nextSession;
      await Future.wait<void>(<Future<void>>[
        _refreshTradingState(
          playerId: selectedPlayer?.detail.playerId,
          refreshPlayer: selectedPlayer != null,
        ),
        refreshCompliance(),
      ]);
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
    portfolioError = null;
    ordersError = null;
    orderError = null;
    adminBuybackError = null;
    complianceError = null;
    recentOrderTotal = 0;
    openOrderTotal = 0;
    _recentOrderIds.clear();
    _openOrderIds.clear();
    _hasLoadedOrdersOnce = false;
    _ordersById.clear();
    _adminBuybackPreviewsByOrderId.clear();
    _loadingAdminBuybackPreviewOrderIds.clear();
    _executingAdminBuybackOrderIds.clear();
    _bootstrapFuture = null;
    _portfolioFuture = null;
    _ordersFuture = null;
    marketSyncedAt = null;
    playerSyncedAt = null;
    portfolioSyncedAt = null;
    ordersSyncedAt = null;
    complianceSyncedAt = null;
    notifyListeners();
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
        final List<dynamic> payload =
            await Future.wait<dynamic>(<Future<dynamic>>[
          _api.fetchComplianceStatus(),
          _api.fetchPolicyRequirements(),
        ]);
        if (!_complianceGate.isActive(requestId)) {
          return;
        }
        complianceStatus = payload[0] as GteComplianceStatus;
        policyRequirements =
            payload[1] as List<GtePolicyRequirementSummary>;
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
        final List<dynamic> payload = await Future.wait<dynamic>(<Future<dynamic>>[
          _api.fetchWalletSummary(),
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

  Future<void> loadOrders({
    int limit = 20,
  }) {
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
        final List<dynamic> payload = await Future.wait<dynamic>(<Future<dynamic>>[
          _api.listOrders(limit: limit),
          _api.listOrders(
            limit: limit,
            statuses: const <GteOrderStatus>[
              GteOrderStatus.open,
              GteOrderStatus.partiallyFilled,
            ],
          ),
        ]);
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
      await _refreshTradingState(
        playerId: playerId,
        refreshPlayer: true,
      );
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

  Future<GteAdminBuybackPreview?> loadAdminBuybackPreview(String orderId) async {
    if (!isAuthenticated ||
        _loadingAdminBuybackPreviewOrderIds.contains(orderId)) {
      return _adminBuybackPreviewsByOrderId[orderId];
    }
    _loadingAdminBuybackPreviewOrderIds.add(orderId);
    adminBuybackError = null;
    notifyListeners();
    try {
      final GteAdminBuybackPreview preview =
          await _api.fetchAdminBuybackPreview(orderId);
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
      final GteAdminBuybackExecution execution =
          await _api.executeAdminBuyback(orderId);
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
      tasks.add(
        openPlayer(
          playerId,
          interval: selectedCandleInterval,
        ),
      );
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
}
