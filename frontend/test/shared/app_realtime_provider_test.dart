import 'dart:async';

import 'package:fake_async/fake_async.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/services/reliability/reliable_websocket_manager.dart';
import 'package:gte_frontend/shared/providers/app_realtime_provider.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test(
    'app realtime sync invalidates market on wallet and market events',
    () async {
      int marketInvalidations = 0;
      int competitionInvalidations = 0;
      late _FakeReliableWebSocketManager fakeManager;

      final controller = AppRealtimeSyncController(
        enabled: true,
        socketUri: Uri.parse('ws://example.test/realtime/stream'),
        invalidateMarket: () => marketInvalidations += 1,
        invalidateCompetitions: () => competitionInvalidations += 1,
        managerFactory: (Uri _) {
          fakeManager = _FakeReliableWebSocketManager();
          return fakeManager;
        },
      )..start();

      fakeManager.emitMessage(
        '{"type":"market_price_update","data":{"player_id":"player-1"}}',
      );
      fakeManager.emitMessage(
        '{"type":"wallet_update","data":{"user_id":"user-1"}}',
      );
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
        late _FakeReliableWebSocketManager fakeManager;

        final controller = AppRealtimeSyncController(
          enabled: true,
          socketUri: Uri.parse('ws://example.test/realtime/stream'),
          invalidateMarket: () => marketInvalidations += 1,
          invalidateCompetitions: () => competitionInvalidations += 1,
          fallbackActivationDelay: const Duration(seconds: 10),
          managerFactory: (Uri _) {
            fakeManager = _FakeReliableWebSocketManager();
            return fakeManager;
          },
        )..start();

        fakeManager.emitState(ReliableWebSocketState.reconnecting);
        async.flushMicrotasks();
        expect(marketInvalidations, 0);
        expect(competitionInvalidations, 0);

        async.elapse(const Duration(seconds: 9));
        expect(marketInvalidations, 0);
        expect(competitionInvalidations, 0);

        async.elapse(const Duration(seconds: 1));
        expect(marketInvalidations, 1);
        expect(competitionInvalidations, 1);

        fakeManager.emitState(ReliableWebSocketState.connected);
        async.flushMicrotasks();
        async.elapse(const Duration(seconds: 10));
        expect(marketInvalidations, 1);
        expect(competitionInvalidations, 1);

        controller.dispose();
      });
    },
  );
}

class _FakeReliableWebSocketManager extends ReliableWebSocketManager {
  _FakeReliableWebSocketManager()
    : _messageController = StreamController<dynamic>.broadcast(),
      _stateController = StreamController<ReliableWebSocketState>.broadcast(
        sync: true,
      ),
      super(socketUri: Uri.parse('ws://example.test/realtime/stream'));

  final StreamController<dynamic> _messageController;
  final StreamController<ReliableWebSocketState> _stateController;

  @override
  Stream<dynamic> get messages => _messageController.stream;

  @override
  Stream<ReliableWebSocketState> get connectionStates =>
      _stateController.stream;

  @override
  void connect() {}

  @override
  Future<void> dispose() async {
    await _messageController.close();
    await _stateController.close();
  }

  void emitMessage(dynamic message) {
    _messageController.add(message);
  }

  void emitState(ReliableWebSocketState state) {
    _stateController.add(state);
  }
}
