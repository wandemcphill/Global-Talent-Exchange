import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../shared/models/auth_session.dart';
import '../../../shared/providers/auth_provider.dart';
import '../../../shared/state/gtex_async_surface_state.dart';
import '../data/market_api_service.dart';
import '../domain/market_models.dart';
import '../repository/market_repository.dart';

enum MarketSurface {
  hub,
  search,
  playerDetail,
  basket,
  checkout,
  activity,
  history,
  activeBids,
  bidDetail,
}

class MarketRoleAccess {
  const MarketRoleAccess({
    required this.role,
    required this.authenticated,
    this.clubId,
  });

  final String role;
  final bool authenticated;
  final String? clubId;

  String? blockedReasonFor(MarketSurface surface) {
    if (_isSuspended) {
      return 'Account suspended - contact support';
    }
    if (!authenticated || _isGuest) {
      return 'Sign in to access the market';
    }
    if (!_isKnownMarketRole) {
      return 'Market role not recognised';
    }
    if (_requiresClub(surface) && (clubId == null || clubId!.trim().isEmpty)) {
      return 'Club context required';
    }
    if (_isScout &&
        (surface == MarketSurface.basket ||
            surface == MarketSurface.checkout ||
            surface == MarketSurface.activeBids ||
            surface == MarketSurface.bidDetail)) {
      return 'Scout read-only access';
    }
    if (_isManager && surface == MarketSurface.checkout) {
      return 'Owner approval required';
    }
    return null;
  }

  bool get _isGuest {
    final String normalized = _normalizedRole;
    return normalized == 'guest' || normalized == 'unauthenticated';
  }

  bool get _isSuspended => _normalizedRole == 'suspended';
  bool get _isOwner =>
      <String>{'club.owner', 'club_owner', 'owner'}.contains(_normalizedRole);
  bool get _isManager => <String>{
    'club.manager',
    'club_manager',
    'manager',
  }.contains(_normalizedRole);
  bool get _isScout =>
      <String>{'club.scout', 'club_scout', 'scout'}.contains(_normalizedRole);
  bool get _isKnownMarketRole => _isOwner || _isManager || _isScout;

  String get _normalizedRole => role.trim().toLowerCase();

  bool _requiresClub(MarketSurface surface) {
    return surface == MarketSurface.basket ||
        surface == MarketSurface.checkout ||
        surface == MarketSurface.activeBids ||
        surface == MarketSurface.bidDetail;
  }
}

class MarketFiltersController extends Notifier<MarketFilters> {
  @override
  MarketFilters build() => MarketFilters.empty();

  void setFilters(MarketFilters filters) {
    state = filters;
  }

  void setQuery(String query) {
    state = state.copyWith(query: query);
  }

  void reset() {
    state = MarketFilters.empty();
  }
}

final Provider<MarketApiService> marketApiServiceProvider =
    Provider<MarketApiService>((Ref ref) {
      return MarketApiService(client: ref.watch(authedApiProvider));
    });

final Provider<MarketRepository> marketRepositoryProvider =
    Provider<MarketRepository>((Ref ref) {
      return BackendMarketRepository(api: ref.watch(marketApiServiceProvider));
    });

final Provider<MarketRoleAccess> marketRoleAccessProvider =
    Provider<MarketRoleAccess>((Ref ref) {
      final AuthSession? session = ref.watch(authProvider);
      final String? clubId = ref.watch(clubContextProvider)?.id;
      return MarketRoleAccess(
        role: ref.watch(currentUserRoleProvider),
        authenticated: session?.isAuthenticated ?? false,
        clubId: clubId,
      );
    });

final NotifierProvider<MarketFiltersController, MarketFilters>
marketFiltersProvider =
    NotifierProvider<MarketFiltersController, MarketFilters>(
      MarketFiltersController.new,
    );

final marketHubProvider =
    FutureProvider.autoDispose<GtexSurfaceState<MarketHubDTO>>((Ref ref) {
      return _guarded<MarketHubDTO>(
        ref,
        MarketSurface.hub,
        (MarketRepository repository) => repository.fetchHub(),
        empty: (MarketHubDTO data) => data.players.isEmpty,
        partial:
            (MarketHubDTO data) =>
                data.hasPartialBackendData
                    ? GtexSyncing<MarketHubDTO>(current: data)
                    : null,
        emptyReason: 'No players match your search',
      );
    });

final marketSearchProvider = FutureProvider.autoDispose
    .family<GtexSurfaceState<MarketPage<MarketPlayerDTO>>, MarketFilters>((
      Ref ref,
      MarketFilters filters,
    ) {
      return _guarded<MarketPage<MarketPlayerDTO>>(
        ref,
        MarketSurface.search,
        (MarketRepository repository) => repository.searchPlayers(filters),
        empty: (MarketPage<MarketPlayerDTO> page) => page.isEmpty,
        emptyReason: 'No players match your search',
      );
    });

final marketPlayerProvider = FutureProvider.autoDispose
    .family<GtexSurfaceState<MarketPlayerDetailDTO>, String>((
      Ref ref,
      String playerId,
    ) {
      return _guarded<MarketPlayerDetailDTO>(
        ref,
        MarketSurface.playerDetail,
        (MarketRepository repository) => repository.getPlayerDetail(playerId),
        partial:
            (MarketPlayerDetailDTO data) =>
                !data.hasBackendDetailTruth
                    ? GtexSyncing<MarketPlayerDetailDTO>(current: data)
                    : null,
      );
    });

final marketBasketProvider = FutureProvider.autoDispose<
  GtexSurfaceState<List<MarketBasketItemDTO>>
>((Ref ref) {
  return _guarded<List<MarketBasketItemDTO>>(
    ref,
    MarketSurface.basket,
    (MarketRepository repository) => repository.getBasket(),
    empty: (List<MarketBasketItemDTO> items) => items.isEmpty,
    partial:
        (List<MarketBasketItemDTO> items) =>
            items.any(
                  (MarketBasketItemDTO item) => item.checkoutEligible == null,
                )
                ? GtexSyncing<List<MarketBasketItemDTO>>(current: items)
                : null,
    emptyReason: 'No players in your transfer basket',
  );
});

final marketCheckoutProvider =
    FutureProvider.autoDispose<GtexSurfaceState<MarketCheckoutDTO>>((Ref ref) {
      return _guarded<MarketCheckoutDTO>(
        ref,
        MarketSurface.checkout,
        (MarketRepository repository) => repository.getCheckout(),
        partial:
            (MarketCheckoutDTO checkout) =>
                checkout.ready
                    ? null
                    : GtexBlocked<MarketCheckoutDTO>(
                      reason:
                          checkout.blockedReason ??
                          (checkout.blockedReasons.isEmpty
                              ? null
                              : checkout.blockedReasons.first) ??
                          'Checkout readiness is blocked by the backend.',
                    ),
        empty: (MarketCheckoutDTO checkout) => checkout.items.isEmpty,
        emptyReason: 'Your transfer basket is empty',
      );
    });

final transferActivityProvider = FutureProvider.autoDispose
    .family<GtexSurfaceState<List<TransferActivityDTO>>, int>((
      Ref ref,
      int limit,
    ) {
      return _guarded<List<TransferActivityDTO>>(
        ref,
        MarketSurface.activity,
        (MarketRepository repository) => repository.getActivity(limit: limit),
        empty: (List<TransferActivityDTO> items) => items.isEmpty,
        emptyReason: 'No transfer activity yet',
      );
    });

final marketHistoryProvider = FutureProvider.autoDispose
    .family<GtexSurfaceState<List<TransferActivityDTO>>, int>((
      Ref ref,
      int limit,
    ) {
      return _guarded<List<TransferActivityDTO>>(
        ref,
        MarketSurface.history,
        (MarketRepository repository) => repository.getHistory(limit: limit),
        empty: (List<TransferActivityDTO> items) => items.isEmpty,
        emptyReason: 'No completed transfers returned by the backend',
      );
    });

final activeBidsProvider = FutureProvider.autoDispose.family<
  GtexSurfaceState<List<MarketBidDTO>>,
  MarketBidsRequest
>((Ref ref, MarketBidsRequest request) {
  final String? clubId = request.clubId ?? ref.watch(clubContextProvider)?.id;
  return _guarded<List<MarketBidDTO>>(
    ref,
    MarketSurface.activeBids,
    (MarketRepository repository) => repository.getActiveBids(
      MarketBidsRequest(windowId: request.windowId, clubId: clubId),
    ),
    empty: (List<MarketBidDTO> bids) => bids.isEmpty,
    emptyReason: 'No active transfer bids returned by the backend',
  );
});

final marketBidDetailProvider = FutureProvider.autoDispose
    .family<GtexSurfaceState<MarketBidDTO>, MarketBidDetailRequest>((
      Ref ref,
      MarketBidDetailRequest request,
    ) {
      return _guarded<MarketBidDTO>(
        ref,
        MarketSurface.bidDetail,
        (MarketRepository repository) => repository.getBidDetail(request),
      );
    });

Future<GtexSurfaceState<T>> _guarded<T>(
  Ref ref,
  MarketSurface surface,
  Future<T> Function(MarketRepository repository) load, {
  bool Function(T data)? empty,
  GtexSurfaceState<T>? Function(T data)? partial,
  String emptyReason = 'No market data returned by the backend',
}) async {
  final MarketRoleAccess access = ref.watch(marketRoleAccessProvider);
  final String? blockedReason = access.blockedReasonFor(surface);
  if (blockedReason != null) {
    return GtexBlocked<T>(reason: blockedReason);
  }
  try {
    final T data = await load(ref.watch(marketRepositoryProvider));
    final GtexSurfaceState<T>? partialState = partial?.call(data);
    if (partialState != null) {
      return partialState;
    }
    if (empty != null && empty(data)) {
      return GtexEmpty<T>(reason: emptyReason);
    }
    return GtexData<T>(data: data);
  } on MarketBackendDataException catch (error) {
    return switch (error.kind) {
      MarketBackendStateKind.blocked => GtexBlocked<T>(reason: error.message),
      MarketBackendStateKind.syncing => GtexError<T>(
        code: error.code,
        message: error.message,
      ),
      MarketBackendStateKind.error => GtexError<T>(
        code: error.code,
        message: error.message,
      ),
    };
  } on FormatException catch (error) {
    return GtexError<T>(
      code: 'market.backend_payload_invalid',
      message: error.message,
    );
  } catch (error) {
    return GtexError<T>(
      code: 'market.backend_error',
      message: error.toString(),
    );
  }
}
