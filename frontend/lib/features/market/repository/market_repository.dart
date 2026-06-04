import '../data/market_api_service.dart';
import '../domain/market_models.dart';

abstract class MarketRepository {
  Future<MarketHubDTO> fetchHub();

  Future<MarketPage<MarketPlayerDTO>> searchPlayers(
    MarketFilters filters, {
    int page = 1,
    int pageSize = 24,
  });

  Future<MarketPlayerDetailDTO> getPlayerDetail(String playerId);
  Future<List<MarketBidDTO>> getActiveBids(MarketBidsRequest request);
  Future<MarketBidDTO> getBidDetail(MarketBidDetailRequest request);
  Future<MarketBidDTO> placeBid(PlaceBidRequest request);
  Future<MarketBidDTO> counterBid(CounterBidRequest request);
  Future<MarketBidDTO> acceptBid(AcceptBidRequest request);
  Future<MarketBidDTO> rejectBid(RejectBidRequest request);
  Future<MarketBidDTO> withdrawBid(WithdrawBidRequest request);
  Future<List<MarketBasketItemDTO>> getBasket();
  Future<MarketBasketItemDTO> addToBasket({
    required String playerId,
    required String clubId,
  });
  Future<void> removeFromBasket(String playerId);
  Future<MarketCheckoutDTO> getCheckout();
  Future<List<TransferActivityDTO>> getActivity({int limit = 50});
  Future<List<TransferActivityDTO>> getHistory({int limit = 50});
}

enum MarketBackendStateKind { blocked, syncing, error }

class MarketBackendDataException implements Exception {
  const MarketBackendDataException({
    required this.code,
    required this.message,
    this.kind = MarketBackendStateKind.error,
  });

  const MarketBackendDataException.blocked({
    required String code,
    required String message,
  }) : this(code: code, message: message, kind: MarketBackendStateKind.blocked);

  const MarketBackendDataException.syncing({
    required String code,
    required String message,
  }) : this(code: code, message: message, kind: MarketBackendStateKind.syncing);

  final String code;
  final String message;
  final MarketBackendStateKind kind;

  @override
  String toString() => '$code: $message';
}

class BackendMarketRepository implements MarketRepository {
  const BackendMarketRepository({required MarketApiService api}) : _api = api;

  final MarketApiService _api;

  @override
  Future<MarketHubDTO> fetchHub() async {
    final MarketPage<MarketPlayerDTO> players = await searchPlayers(
      MarketFilters.empty(),
    );
    List<MarketBidDTO>? activeBids;
    List<MarketBasketItemDTO>? basketItems;
    List<TransferActivityDTO>? activity;
    try {
      activeBids = await getActiveBids(const MarketBidsRequest());
    } catch (_) {
      activeBids = null;
    }
    try {
      basketItems = await getBasket();
    } catch (_) {
      basketItems = null;
    }
    if (activeBids != null) {
      activity = activeBids
          .map(TransferActivityDTO.fromBid)
          .toList(growable: false);
    }
    return MarketHubDTO(
      players: players,
      activeBids: activeBids,
      basketItems: basketItems,
      activity: activity,
      generatedAt: DateTime.now().toUtc(),
    );
  }

  @override
  Future<MarketPage<MarketPlayerDTO>> searchPlayers(
    MarketFilters filters, {
    int page = 1,
    int pageSize = 24,
  }) async {
    final JsonMap payload = await _api.searchMarketPlayers(
      filters: filters,
      page: page,
      pageSize: pageSize,
    );
    return MarketPage.fromJson<MarketPlayerDTO>(
      payload,
      MarketPlayerDTO.fromJson,
    );
  }

  @override
  Future<MarketPlayerDetailDTO> getPlayerDetail(String playerId) async {
    final JsonMap overview = await _api.fetchPlayerOverview(playerId);
    return MarketPlayerDetailDTO.fromJson(overview);
  }

  @override
  Future<List<MarketBidDTO>> getActiveBids(MarketBidsRequest request) async {
    final String? windowId = _blankToNull(request.windowId);
    final List<MarketBidDTO> bids =
        windowId == null
            ? (await _api.listMarketBids(
              clubId: _blankToNull(request.clubId),
            )).map(MarketBidDTO.fromJson).toList(growable: false)
            : await _listBids(windowId);
    final String? clubId = _blankToNull(request.clubId);
    final List<MarketBidDTO> filtered =
        clubId == null
            ? bids
            : bids
                .where(
                  (MarketBidDTO bid) =>
                      bid.fromClubId == clubId || bid.toClubId == clubId,
                )
                .toList(growable: false);
    for (final MarketBidDTO bid in filtered) {
      _assertReservationTruth(bid);
    }
    return filtered;
  }

  @override
  Future<MarketBidDTO> getBidDetail(MarketBidDetailRequest request) async {
    final String bidId = request.bidId.trim();
    if (_blankToNull(request.windowId) == null) {
      final MarketBidDTO bid = MarketBidDTO.fromJson(
        await _api.fetchMarketBid(bidId),
      );
      _assertReservationTruth(bid);
      return bid;
    }
    final List<MarketBidDTO> bids = await _listBids(request.windowId);
    for (final MarketBidDTO bid in bids) {
      if (bid.id == bidId) {
        _assertReservationTruth(bid);
        return bid;
      }
    }
    throw MarketBackendDataException(
      code: 'market.bid_not_found',
      message: 'Transfer bid $bidId was not returned by the backend.',
    );
  }

  @override
  Future<MarketBidDTO> placeBid(PlaceBidRequest request) async {
    final MarketBidDTO bid;
    if (_blankToNull(request.listingId) != null) {
      final JsonMap listing = await _api.postListingBid(request);
      final JsonMap currentBid = _requiredMap(
        listing['current_bid'],
        'listing current bid',
      );
      bid = MarketBidDTO.fromListingBid(currentBid, listing);
    } else {
      final String windowId = _requiredText(
        request.windowId,
        'window id for lifecycle bid',
      );
      bid = MarketBidDTO.fromJson(
        await _api.createWindowBid(windowId, request),
      );
    }
    _assertReservationTruth(bid);
    return bid;
  }

  @override
  Future<MarketBidDTO> counterBid(CounterBidRequest request) async {
    final MarketBidDTO bid = MarketBidDTO.fromJson(
      await _api.counterWindowBid(request),
    );
    _assertReservationTruth(bid);
    return bid;
  }

  @override
  Future<MarketBidDTO> acceptBid(AcceptBidRequest request) async {
    final MarketBidDTO bid = MarketBidDTO.fromJson(
      await _api.acceptWindowBid(request),
    );
    _assertReservationTruth(bid);
    return bid;
  }

  @override
  Future<MarketBidDTO> rejectBid(RejectBidRequest request) async {
    final MarketBidDTO bid = MarketBidDTO.fromJson(
      await _api.rejectWindowBid(request),
    );
    _assertTransitionResult(bid, MarketBidStatus.rejected);
    return bid;
  }

  @override
  Future<MarketBidDTO> withdrawBid(WithdrawBidRequest request) async {
    final String? windowId = _blankToNull(request.windowId);
    final MarketBidDTO bid = MarketBidDTO.fromJson(
      windowId == null
          ? await _api.withdrawMarketBid(request)
          : await _api.withdrawWindowBid(request),
    );
    _assertTransitionResult(bid, MarketBidStatus.withdrawn);
    return bid;
  }

  @override
  Future<List<MarketBasketItemDTO>> getBasket() async {
    final List<JsonMap> items = await _api.listBasket();
    return items.map(MarketBasketItemDTO.fromJson).toList(growable: false);
  }

  @override
  Future<MarketBasketItemDTO> addToBasket({
    required String playerId,
    required String clubId,
  }) async {
    return MarketBasketItemDTO.fromJson(
      await _api.addToBasket(playerId: playerId, clubId: clubId),
    );
  }

  @override
  Future<void> removeFromBasket(String playerId) {
    return _api.removeFromBasket(playerId: playerId);
  }

  @override
  Future<MarketCheckoutDTO> getCheckout() async {
    return MarketCheckoutDTO.fromBackend(
      readinessPayload: await _api.fetchCheckoutReadiness(),
    );
  }

  @override
  Future<List<TransferActivityDTO>> getActivity({int limit = 50}) async {
    return (await _api.listMarketActivity(
      limit: limit,
    )).map(TransferActivityDTO.fromJson).toList(growable: false);
  }

  @override
  Future<List<TransferActivityDTO>> getHistory({int limit = 50}) async {
    return (await _api.listMarketHistory(
      limit: limit,
    )).map(TransferActivityDTO.fromJson).toList(growable: false);
  }

  Future<List<MarketBidDTO>> _listBids(String? windowId) async {
    final String? resolvedWindowId = _blankToNull(windowId);
    if (resolvedWindowId != null) {
      return (await _api.listWindowBids(
        resolvedWindowId,
      )).map(MarketBidDTO.fromJson).toList(growable: false);
    }
    final List<JsonMap> windows = await _api.listTransferWindows();
    if (windows.isEmpty) {
      return const <MarketBidDTO>[];
    }
    final List<String> windowIds = windows
        .map((JsonMap item) => _blankToNull(item['id']?.toString()))
        .whereType<String>()
        .toList(growable: false);
    final List<MarketBidDTO> bids = <MarketBidDTO>[];
    for (final String id in windowIds) {
      bids.addAll(
        (await _api.listWindowBids(
          id,
        )).map(MarketBidDTO.fromJson).toList(growable: false),
      );
    }
    return bids;
  }
}

void _assertReservationTruth(MarketBidDTO bid) {
  if (bid.hasBackendReservationTruth) {
    return;
  }
  throw MarketBackendDataException.blocked(
    code: 'market.wallet_reservation_truth_missing',
    message:
        'Transfer bid ${bid.id} is ${bid.status.backendValue} but the backend did not return wallet reservation truth.',
  );
}

void _assertTransitionResult(MarketBidDTO bid, MarketBidStatus expected) {
  if (bid.status == expected) {
    return;
  }
  throw MarketBackendDataException(
    code: 'market.bid_transition_unexpected',
    message:
        'Expected bid ${bid.id} to be ${expected.backendValue}, got ${bid.rawStatus}.',
  );
}

JsonMap _requiredMap(Object? value, String label) {
  if (value is Map<String, Object?>) {
    return value;
  }
  if (value is Map) {
    return value.map(
      (Object? key, Object? item) => MapEntry(key.toString(), item),
    );
  }
  throw FormatException('Expected $label object from backend.');
}

String _requiredText(String? value, String label) {
  final String? resolved = _blankToNull(value);
  if (resolved == null) {
    throw MarketBackendDataException.blocked(
      code: 'market.${label.replaceAll(' ', '_')}_missing',
      message: 'Missing $label for backend market request.',
    );
  }
  return resolved;
}

String? _blankToNull(String? value) {
  final String resolved = value?.trim() ?? '';
  return resolved.isEmpty ? null : resolved;
}
