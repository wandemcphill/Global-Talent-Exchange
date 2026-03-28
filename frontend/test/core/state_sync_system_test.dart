import 'dart:async';

import 'package:fake_async/fake_async.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/core/state_sync_system.dart';

void main() {
  test('attach starts periodic sync and detach stops it', () {
    fakeAsync((FakeAsync async) {
      int syncCount = 0;
      final StateSyncSystem system = StateSyncSystem(
        interval: const Duration(seconds: 5),
        onSync: () async {
          syncCount += 1;
        },
      );

      system.attach();
      async.elapse(const Duration(seconds: 5));
      async.flushMicrotasks();
      expect(syncCount, 1);

      system.detach();
      async.elapse(const Duration(seconds: 5));
      async.flushMicrotasks();
      expect(syncCount, 1);
    });
  });

  test(
    'critical action requests a follow-up sync when one is already running',
    () async {
      final List<Completer<void>> completers = <Completer<void>>[
        Completer<void>(),
        Completer<void>(),
      ];
      int syncCount = 0;
      final StateSyncSystem system = StateSyncSystem(
        interval: const Duration(minutes: 1),
        onSync: () {
          final int index = syncCount;
          syncCount += 1;
          return completers[index].future;
        },
      );

      final Future<void> syncFuture = system.sync();
      expect(syncCount, 1);

      final Future<void> queuedFuture = system.syncAfterCriticalAction();
      completers[0].complete();
      await Future<void>.delayed(Duration.zero);

      expect(syncCount, 2);

      completers[1].complete();
      await Future.wait(<Future<void>>[syncFuture, queuedFuture]);

      expect(system.lastSyncedAt, isNotNull);
      expect(system.isSyncing, isFalse);
    },
  );
}
