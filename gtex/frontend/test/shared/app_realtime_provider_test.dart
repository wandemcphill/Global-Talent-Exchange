import 'dart:async';

import 'package:fake_async/fake_async.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/core/runtime/gtex_realtime_client.dart';
import 'package:gte_frontend/shared/providers/app_realtime_provider.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test(
    'app realtime sync invalidates market on wallet and market events',
    () async {
      int marketInvalidations = 0;
      int competitionInvalidations = 0;
      final _FakeGtexRealtimeClient fakeClient = _FakeGtexRealtimeClient();

      final controller = AppRealtimeSyncController(
        enabled: true,
        apiBaseUrl: 'https://api.example.test',
        includeWallet: true,
        invalidateMarket: () => marketInvalidations += 1,
        invalidateCompetitions: () => competitionInvalidations += 1,
        clientFactory: () => fakeClient,
      )..start();

      expect(fakeClient.subscribedChannels, <String>[
        'market',
        'competition',
        'wallet',
      ]);

      fakeClient.emitEvent('market', <String, Object?>{
        'type': 'market_price_update',
        'data': <String, Object?>{'player_id': 'player-1'},
      });
      fakeClient.emitEvent('wallet', <String, Object?>{
        'type': 'wallet_update',
        'data': <String, Object?>{'user_id': 'user-1'},
      });
      await Future<void>.delayed(Duration.zero);

      expect(marketInvalidations, 2);
      expect(competitionInvalidations, 0);

      await controller.dispose();
    },
  );

  test(
    'app realtime sync waits before enabling fallback polling during reconnect churn',
    () {
      fakeAsync((FakeAsync async) {
        int marketInvalidations = 0;
        int competitionInvalidations = 0;
        final _FakeGtexRealtimeClient fakeClient = _FakeGtexRealtimeClient();

        final controller = AppRealtimeSyncController(
          enabled: true,
          apiBaseUrl: 'https://api.example.test',
          includeWallet: false,
          invalidateMarket: () => marketInvalidations += 1,
          invalidateCompetitions: () => competitionInvalidations += 1,
          fallbackActivationDelay: const Duration(seconds: 10),
          clientFactory: () => fakeClient,
        )..start();

        fakeClient.emitState(GtexRealtimeConnectionState.reconnecting);
        async.flushMicrotasks();
        expect(marketInvalidations, 0);
        expect(competitionInvalidations, 0);

        async.elapse(const Duration(seconds: 9));
        expect(marketInvalidations, 0);
        expect(competitionInvalidations, 0);

        async.elapse(const Duration(seconds: 1));
        expect(marketInvalidations, 1);
        expect(competitionInvalidations, 1);

        fakeClient.emitState(GtexRealtimeConnectionState.connected);
        async.flushMicrotasks();
        async.elapse(const Duration(seconds: 10));
        expect(marketInvalidations, 1);
        expect(competitionInvalidations, 1);

        controller.dispose();
      });
    },
  );
}

class _FakeGtexRealtimeClient extends GtexRealtimeClient {
  _FakeGtexRealtimeClient()
    : super(
        apiBaseUrl: 'https://api.example.test',
        accessTokenProvider: () => null,
        socketFactory: (_) => throw UnimplementedError(),
      );

  final Map<String, StreamController<Map<String, Object?>>> _controllers =
      <String, StreamController<Map<String, Object?>>>{};
  final StreamController<GtexRealtimeConnectionState> _stateController =
      StreamController<GtexRealtimeConnectionState>.broadcast(sync: true);
  final List<String> subscribedChannels = <String>[];

  @override
  Stream<Map<String, Object?>> subscribe(String channel) {
    subscribedChannels.add(channel);
    return _controllerFor(channel).stream;
  }

  @override
  Stream<GtexRealtimeConnectionState> get connectionStates =>
      _stateController.stream;

  @override
  Future<void> dispose() async {
    for (final StreamController<Map<String, Object?>> controller
        in _controllers.values) {
      await controller.close();
    }
    await _stateController.close();
    await super.dispose();
  }

  void emitEvent(String channel, Map<String, Object?> event) {
    _controllerFor(channel).add(event);
  }

  void emitState(GtexRealtimeConnectionState state) {
    _stateController.add(state);
  }

  StreamController<Map<String, Object?>> _controllerFor(String channel) {
    return _controllers.putIfAbsent(
      channel,
      () => StreamController<Map<String, Object?>>.broadcast(sync: true),
    );
  }
}
