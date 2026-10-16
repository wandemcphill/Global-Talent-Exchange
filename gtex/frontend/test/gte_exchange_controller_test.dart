import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/domain/match/match_weight_presets.dart';
import 'package:gte_frontend/domain/match/match_weights.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:shared_preferences/shared_preferences.dart';

int _ownedShares(GteExchangeController controller, String playerId) {
  final GtePortfolioView? portfolio = controller.portfolio;
  if (portfolio == null) {
    return 0;
  }
  for (final GtePortfolioHolding holding in portfolio.holdings) {
    if (holding.playerId == playerId) {
      return holding.quantity.round();
    }
  }
  return 0;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  SharedPreferences.setMockInitialValues(const <String, Object>{});

  test('controller bootstrap loads the market directory', () async {
    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );

    await controller.bootstrap();

    expect(controller.players, isNotEmpty);
    expect(controller.marketPage?.total, greaterThan(0));
  });

  test('controller signs in and loads protected portfolio routes', () async {
    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );

    await controller.signIn(
      email: 'fixture.trader@gte.local',
      password: 'DemoPass123', // pragma: allowlist secret
    );

    expect(controller.isAuthenticated, isTrue);
    expect(controller.walletSummary?.availableBalance, greaterThan(0));
    expect(controller.portfolioSummary?.totalEquity, greaterThan(0));
    expect(controller.recentOrders, isNotEmpty);
    expect(controller.recentOrderTotal, greaterThan(0));
    expect(controller.openOrders, isNotEmpty);
    expect(controller.openOrderTotal, greaterThan(0));
  });

  test(
    'controller settles a player-share trade and syncs wallet and portfolio',
    () async {
      final GteExchangeController controller = GteExchangeController(
        api: GteExchangeApiClient.fixture(),
      );

      await controller.signIn(
        email: 'fixture.trader@gte.local',
        password: 'DemoPass123', // pragma: allowlist secret
      );
      await controller.openPlayer('lamine-yamal');
      final double startingAvailable =
          controller.walletSummary!.availableBalance;
      final int startingShares = _ownedShares(controller, 'lamine-yamal');

      final GtePlayerShareTradeResult? trade =
          await controller.tradePlayerShares(
        playerId: 'lamine-yamal',
        side: GteOrderSide.buy,
        shareCount: 2,
        idempotencyKey: 'controller-buy-key-1',
      );

      expect(trade, isNotNull);
      // System A settles immediately - ownership, not a pending order.
      expect(trade!.holding.shareCount, startingShares + 2);
      expect(trade.transactionId, isNotEmpty);
      expect(controller.orderError, isNull);
      expect(controller.isSubmittingOrder, isFalse);
      expect(
        controller.walletSummary!.availableBalance,
        lessThan(startingAvailable),
      );
      expect(_ownedShares(controller, 'lamine-yamal'), startingShares + 2);

      // Selling part of the position returns coin and reduces ownership.
      final GtePlayerShareTradeResult? sale =
          await controller.tradePlayerShares(
        playerId: 'lamine-yamal',
        side: GteOrderSide.sell,
        shareCount: 1,
        idempotencyKey: 'controller-sell-key-1',
      );

      expect(sale, isNotNull);
      expect(sale!.holding.shareCount, startingShares + 1);
    },
  );

  test(
    'controller reuses an idempotency key rather than trading twice',
    () async {
      final GteExchangeController controller = GteExchangeController(
        api: GteExchangeApiClient.fixture(),
      );

      await controller.signIn(
        email: 'fixture.trader@gte.local',
        password: 'DemoPass123', // pragma: allowlist secret
      );
      await controller.openPlayer('lamine-yamal');
      final double startingAvailable =
          controller.walletSummary!.availableBalance;
      final int startingShares = _ownedShares(controller, 'lamine-yamal');

      final GtePlayerShareTradeResult? first =
          await controller.tradePlayerShares(
        playerId: 'lamine-yamal',
        side: GteOrderSide.buy,
        shareCount: 2,
        idempotencyKey: 'controller-retry-key',
      );
      final GtePlayerShareTradeResult? retry =
          await controller.tradePlayerShares(
        playerId: 'lamine-yamal',
        side: GteOrderSide.buy,
        shareCount: 2,
        idempotencyKey: 'controller-retry-key',
      );

      expect(retry!.transactionId, first!.transactionId);
      expect(retry.holding.shareCount, startingShares + 2);
      expect(
        controller.walletSummary!.availableBalance,
        closeTo(startingAvailable - first.netAmountCoin, 0.001),
      );
    },
  );

  test('controller refuses to trade while signed out', () async {
    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );

    final GtePlayerShareTradeResult? trade =
        await controller.tradePlayerShares(
      playerId: 'lamine-yamal',
      side: GteOrderSide.buy,
      shareCount: 1,
      idempotencyKey: 'signed-out-key',
    );

    expect(trade, isNull);
    expect(controller.orderError, 'Sign in to trade shares.');
  });

  test(
    'fixture openPlayer resolves from market snapshot without loading compatibility profile',
    () async {
      final _FixtureSnapshotOnlyApiClient api = _FixtureSnapshotOnlyApiClient();
      final GteExchangeController controller = GteExchangeController(api: api);

      await controller.openPlayer('lamine-yamal');

      expect(api.fetchPlayerProfileCalls, 0);
      expect(controller.selectedPlayer?.detail.playerId, 'lamine-yamal');
      expect(controller.selectedProfile, isNull);
      expect(controller.playerProfileError, isNull);
      expect(controller.isPlayerShortlisted('lamine-yamal'), isFalse);

      controller.toggleShortlist('lamine-yamal');

      expect(controller.isPlayerShortlisted('lamine-yamal'), isTrue);
    },
  );

  test('controller stores normalized match weights and applies presets', () {
    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );

    controller.updateWeights(
      const MatchWeights(
        position: 2,
        age: 1,
        country: 1,
        height: 0,
        foot: 0,
        availability: 0,
      ),
    );

    expect(controller.weights.position, closeTo(0.5, 0.0001));
    expect(controller.weights.age, closeTo(0.25, 0.0001));
    expect(controller.weights.country, closeTo(0.25, 0.0001));

    controller.applyPreset(MatchWeightPresets.readyNow());

    expect(controller.weights.cacheKey, MatchWeightPresets.readyNow().cacheKey);
  });
}

class _FixtureSnapshotOnlyApiClient extends GteExchangeApiClient {
  _FixtureSnapshotOnlyApiClient._(GteExchangeApiClient delegate)
    : super(
        config: delegate.config,
        transport: delegate.transport,
        repository: delegate.repository,
      );

  factory _FixtureSnapshotOnlyApiClient() {
    final GteExchangeApiClient delegate = GteExchangeApiClient.fixture();
    return _FixtureSnapshotOnlyApiClient._(delegate);
  }

  int fetchPlayerProfileCalls = 0;

  @override
  Future<PlayerProfile> fetchPlayerProfile(String playerId) {
    fetchPlayerProfileCalls += 1;
    throw StateError(
      'Fixture player detail should not request compatibility data',
    );
  }
}
