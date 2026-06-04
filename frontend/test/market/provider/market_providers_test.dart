import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/market/domain/market_models.dart';
import 'package:gte_frontend/features/market/providers/market_providers.dart';
import 'package:gte_frontend/features/market/repository/market_repository.dart';
import 'package:gte_frontend/shared/models/auth_session.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';
import 'package:gte_frontend/shared/state/gtex_async_surface_state.dart';

void main() {
  test('scout role is blocked from basket state', () async {
    final _FakeMarketRepository repository = _FakeMarketRepository();
    final ProviderContainer container = _container(
      role: 'club.scout',
      repository: repository,
    );
    addTearDown(container.dispose);

    final GtexSurfaceState<List<MarketBasketItemDTO>> state = await container
        .read(marketBasketProvider.future);

    expect(state, isA<GtexBlocked<List<MarketBasketItemDTO>>>());
    expect(
      (state as GtexBlocked<List<MarketBasketItemDTO>>).reason,
      'Scout read-only access',
    );
    expect(repository.basketCalls, 0);
  });

  test(
    'manager role is blocked from checkout with owner approval copy',
    () async {
      final ProviderContainer container = _container(
        role: 'club.manager',
        repository: _FakeMarketRepository(),
      );
      addTearDown(container.dispose);

      final GtexSurfaceState<MarketCheckoutDTO> state = await container.read(
        marketCheckoutProvider.future,
      );

      expect(state, isA<GtexBlocked<MarketCheckoutDTO>>());
      expect(
        (state as GtexBlocked<MarketCheckoutDTO>).reason,
        'Owner approval required',
      );
    },
  );

  test('unrecognised role resolves to blocked, not error', () async {
    final ProviderContainer container = _container(
      role: 'mystery-role',
      repository: _FakeMarketRepository(),
    );
    addTearDown(container.dispose);

    final GtexSurfaceState<MarketPage<MarketPlayerDTO>> state = await container
        .read(marketSearchProvider(MarketFilters.empty()).future);

    expect(state, isA<GtexBlocked<MarketPage<MarketPlayerDTO>>>());
    expect(
      (state as GtexBlocked<MarketPage<MarketPlayerDTO>>).reason,
      'Market role not recognised',
    );
  });

  test('backend-null checkout truth surfaces blocked state', () async {
    final _FakeMarketRepository repository = _FakeMarketRepository(
      checkoutError: const MarketBackendDataException.blocked(
        code: 'market.wallet_truth_missing',
        message: 'Wallet availability is missing from the backend.',
      ),
    );
    final ProviderContainer container = _container(
      role: 'club.owner',
      repository: repository,
    );
    addTearDown(container.dispose);

    final GtexSurfaceState<MarketCheckoutDTO> state = await container.read(
      marketCheckoutProvider.future,
    );

    expect(state, isA<GtexBlocked<MarketCheckoutDTO>>());
    expect(
      (state as GtexBlocked<MarketCheckoutDTO>).reason,
      'Wallet availability is missing from the backend.',
    );
  });

  test(
    'incomplete player detail surfaces syncing with backend data visible',
    () async {
      final _FakeMarketRepository repository = _FakeMarketRepository(
        playerDetail: const MarketPlayerDetailDTO(
          player: MarketPlayerDTO(id: 'player-1', name: 'Syncing Forward'),
        ),
      );
      final ProviderContainer container = _container(
        role: 'club.owner',
        repository: repository,
      );
      addTearDown(container.dispose);

      final GtexSurfaceState<MarketPlayerDetailDTO> state = await container
          .read(marketPlayerProvider('player-1').future);

      expect(state, isA<GtexSyncing<MarketPlayerDetailDTO>>());
      expect(
        (state as GtexSyncing<MarketPlayerDetailDTO>).current.player.name,
        'Syncing Forward',
      );
    },
  );
}

ProviderContainer _container({
  required String role,
  required MarketRepository repository,
  String? clubId = 'club-1',
}) {
  return ProviderContainer(
    overrides: [
      initialAuthSessionProvider.overrideWithValue(
        AuthSession(
          userId: 'user-1',
          accessToken: 'token-1',
          refreshToken: 'refresh-1',
          sessionId: 'session-1',
          role: role,
          clubId: clubId,
        ),
      ),
      marketRepositoryProvider.overrideWithValue(repository),
    ],
  );
}

class _FakeMarketRepository implements MarketRepository {
  _FakeMarketRepository({this.checkoutError, this.playerDetail});

  final MarketBackendDataException? checkoutError;
  final MarketPlayerDetailDTO? playerDetail;
  int basketCalls = 0;

  @override
  Future<MarketHubDTO> fetchHub() async {
    return MarketHubDTO(
      players: MarketPage<MarketPlayerDTO>(
        items: const <MarketPlayerDTO>[],
        page: 1,
        pageSize: 24,
        total: 0,
      ),
    );
  }

  @override
  Future<MarketPage<MarketPlayerDTO>> searchPlayers(
    MarketFilters filters, {
    int page = 1,
    int pageSize = 24,
  }) async {
    return MarketPage<MarketPlayerDTO>(
      items: const <MarketPlayerDTO>[],
      page: page,
      pageSize: pageSize,
      total: 0,
    );
  }

  @override
  Future<MarketPlayerDetailDTO> getPlayerDetail(String playerId) async {
    return playerDetail ??
        MarketPlayerDetailDTO(
          player: MarketPlayerDTO(id: playerId, name: 'Player $playerId'),
          availability: const <String, Object?>{'status': 'available'},
        );
  }

  @override
  Future<List<MarketBasketItemDTO>> getBasket() async {
    basketCalls += 1;
    return const <MarketBasketItemDTO>[];
  }

  @override
  Future<MarketCheckoutDTO> getCheckout() async {
    final MarketBackendDataException? error = checkoutError;
    if (error != null) {
      throw error;
    }
    return const MarketCheckoutDTO(
      items: <MarketBasketItemDTO>[],
      walletCurrency: 'coin',
      walletAvailableBalance: 25,
      walletReservedBalance: 0,
    );
  }

  @override
  Future<List<MarketBidDTO>> getActiveBids(MarketBidsRequest request) async {
    return const <MarketBidDTO>[];
  }

  @override
  Future<MarketBidDTO> getBidDetail(MarketBidDetailRequest request) {
    throw UnimplementedError();
  }

  @override
  Future<MarketBidDTO> placeBid(PlaceBidRequest request) {
    throw UnimplementedError();
  }

  @override
  Future<MarketBidDTO> counterBid(CounterBidRequest request) {
    throw UnimplementedError();
  }

  @override
  Future<MarketBidDTO> acceptBid(AcceptBidRequest request) {
    throw UnimplementedError();
  }

  @override
  Future<MarketBidDTO> rejectBid(RejectBidRequest request) {
    throw UnimplementedError();
  }

  @override
  Future<MarketBidDTO> withdrawBid(WithdrawBidRequest request) {
    throw UnimplementedError();
  }

  @override
  Future<MarketBasketItemDTO> addToBasket({
    required String playerId,
    required String clubId,
  }) {
    throw UnimplementedError();
  }

  @override
  Future<void> removeFromBasket(String playerId) {
    throw UnimplementedError();
  }

  @override
  Future<List<TransferActivityDTO>> getActivity({int limit = 50}) async {
    return const <TransferActivityDTO>[];
  }

  @override
  Future<List<TransferActivityDTO>> getHistory({int limit = 50}) async {
    return const <TransferActivityDTO>[];
  }
}
