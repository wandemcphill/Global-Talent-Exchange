import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_redesign/data/gtex_match_feed.dart';
import 'package:gte_frontend/features/match_redesign/data/gtex_match_models.dart';
import 'package:gte_frontend/features/match_redesign/presentation/gtex_match_center_controller.dart';

import 'match_test_fixtures.dart';

/// Tight policy so reconnect behaviour is observable without long waits.
const GtexMatchReconnectPolicy _fastPolicy = GtexMatchReconnectPolicy(
  initialDelay: Duration(milliseconds: 10),
  maxDelay: Duration(milliseconds: 20),
  maxAttempts: 3,
);

void main() {
  group('load', () {
    test('moves idle → live and exposes the first snapshot', () async {
      final FakeMatchRepository repository = FakeMatchRepository(
        initial: buildMatchState(minute: 12),
      );
      final GtexMatchCenterController controller = GtexMatchCenterController(
        matchId: 'm-1',
        repository: repository,
        reconnectPolicy: _fastPolicy,
      );
      expect(controller.connection, GtexMatchConnectionStatus.idle);

      await controller.load();

      expect(controller.connection, GtexMatchConnectionStatus.live);
      expect(controller.state!.minute, 12);
      expect(controller.error, isNull);
      expect(controller.isLoading, isFalse);

      controller.dispose();
      await repository.disposeControllers();
    });

    test('surfaces a hard error when nothing can be shown', () async {
      final FakeMatchRepository repository = FakeMatchRepository(
        fetchError: StateError('backend down'),
      );
      final GtexMatchCenterController controller = GtexMatchCenterController(
        matchId: 'm-1',
        repository: repository,
        reconnectPolicy: _fastPolicy,
      );

      await controller.load();

      expect(controller.error, isNotNull);
      expect(controller.state, isNull);
      expect(controller.connection, GtexMatchConnectionStatus.offline);

      controller.dispose();
    });

    test('goes straight to finished for a completed match', () async {
      final FakeMatchRepository repository = FakeMatchRepository(
        initial: buildMatchState(minute: 90, phase: GtexMatchPhase.fullTime),
      );
      final GtexMatchCenterController controller = GtexMatchCenterController(
        matchId: 'm-1',
        repository: repository,
        reconnectPolicy: _fastPolicy,
      );

      await controller.load();

      expect(controller.connection, GtexMatchConnectionStatus.finished);
      expect(
        repository.watchCount,
        0,
        reason: 'a finished match must not open a live subscription',
      );

      controller.dispose();
    });

    test('retry recovers after a transient failure', () async {
      final FakeMatchRepository repository = FakeMatchRepository(
        fetchError: StateError('boom'),
      );
      final GtexMatchCenterController controller = GtexMatchCenterController(
        matchId: 'm-1',
        repository: repository,
        reconnectPolicy: _fastPolicy,
      );

      await controller.load();
      expect(controller.error, isNotNull);

      repository.fetchError = null;
      await controller.retry();

      expect(controller.error, isNull);
      expect(controller.state, isNotNull);
      expect(controller.connection, GtexMatchConnectionStatus.live);

      controller.dispose();
      await repository.disposeControllers();
    });
  });

  group('streaming', () {
    test('applies a newer frame and notifies once', () async {
      final FakeMatchRepository repository = FakeMatchRepository(
        initial: buildMatchState(minute: 10),
      );
      final GtexMatchCenterController controller = GtexMatchCenterController(
        matchId: 'm-1',
        repository: repository,
        reconnectPolicy: _fastPolicy,
      );
      await controller.load();

      int notifications = 0;
      controller.addListener(() => notifications += 1);

      repository.currentController.add(buildMatchState(minute: 11));
      await Future<void>.delayed(Duration.zero);

      expect(controller.state!.minute, 11);
      expect(notifications, 1);

      controller.dispose();
      await repository.disposeControllers();
    });

    test('duplicate frames do not rebuild the surface', () async {
      final FakeMatchRepository repository = FakeMatchRepository(
        initial: buildMatchState(minute: 10),
      );
      final GtexMatchCenterController controller = GtexMatchCenterController(
        matchId: 'm-1',
        repository: repository,
        reconnectPolicy: _fastPolicy,
      );
      await controller.load();

      int notifications = 0;
      controller.addListener(() => notifications += 1);

      repository.currentController.add(buildMatchState(minute: 10));
      repository.currentController.add(buildMatchState(minute: 10));
      await Future<void>.delayed(Duration.zero);

      expect(
        notifications,
        0,
        reason: 'redundant frames must not notify listeners',
      );
      expect(controller.diagnostics.duplicates, 2);

      controller.dispose();
      await repository.disposeControllers();
    });

    test('stale frames never rewind the visible state', () async {
      final FakeMatchRepository repository = FakeMatchRepository(
        initial: buildMatchState(minute: 40, homeScore: 2),
      );
      final GtexMatchCenterController controller = GtexMatchCenterController(
        matchId: 'm-1',
        repository: repository,
        reconnectPolicy: _fastPolicy,
      );
      await controller.load();

      repository.currentController.add(
        buildMatchState(minute: 20, homeScore: 1),
      );
      await Future<void>.delayed(Duration.zero);

      expect(controller.state!.minute, 40);
      expect(controller.state!.home.score, 2);
      expect(controller.diagnostics.stale, 1);

      controller.dispose();
      await repository.disposeControllers();
    });

    test('a malformed frame does not tear the feed down', () async {
      final FakeMatchRepository repository = FakeMatchRepository(
        initial: buildMatchState(minute: 10),
      );
      final GtexMatchCenterController controller = GtexMatchCenterController(
        matchId: 'm-1',
        repository: repository,
        reconnectPolicy: _fastPolicy,
      );
      await controller.load();

      repository.currentController.addError(
        const FormatException('bad frame'),
      );
      await Future<void>.delayed(Duration.zero);

      // Last good snapshot survives and the controller is recovering.
      expect(controller.state!.minute, 10);
      expect(controller.connection, GtexMatchConnectionStatus.reconnecting);
      expect(controller.isShowingStaleData, isTrue);

      controller.dispose();
      await repository.disposeControllers();
    });

    test('reconnects after a drop and returns to live', () async {
      final FakeMatchRepository repository = FakeMatchRepository(
        initial: buildMatchState(minute: 10),
      );
      final GtexMatchCenterController controller = GtexMatchCenterController(
        matchId: 'm-1',
        repository: repository,
        reconnectPolicy: _fastPolicy,
      );
      await controller.load();
      expect(repository.watchCount, 1);

      await repository.currentController.close();
      await Future<void>.delayed(const Duration(milliseconds: 60));

      expect(
        repository.watchCount,
        greaterThan(1),
        reason: 'the controller must re-subscribe after a drop',
      );
      expect(controller.diagnostics.reconnects, greaterThan(0));

      repository.currentController.add(buildMatchState(minute: 15));
      await Future<void>.delayed(Duration.zero);

      expect(controller.connection, GtexMatchConnectionStatus.live);
      expect(controller.state!.minute, 15);

      controller.dispose();
      await repository.disposeControllers();
    });

    test('gives up as offline once the retry budget is spent', () async {
      final FakeMatchRepository repository = FakeMatchRepository(
        initial: buildMatchState(minute: 10),
      );
      final GtexMatchCenterController controller = GtexMatchCenterController(
        matchId: 'm-1',
        repository: repository,
        reconnectPolicy: const GtexMatchReconnectPolicy(
          initialDelay: Duration(milliseconds: 5),
          maxDelay: Duration(milliseconds: 5),
          maxAttempts: 2,
        ),
      );
      await controller.load();

      // Close each new subscription as soon as it is opened.
      for (int attempt = 0; attempt < 5; attempt += 1) {
        await repository.currentController.close();
        await Future<void>.delayed(const Duration(milliseconds: 20));
      }

      expect(controller.connection, GtexMatchConnectionStatus.offline);
      expect(
        controller.state,
        isNotNull,
        reason: 'the last good snapshot must stay on screen when offline',
      );

      controller.dispose();
      await repository.disposeControllers();
    });

    test('full time closes the subscription', () async {
      final FakeMatchRepository repository = FakeMatchRepository(
        initial: buildMatchState(minute: 88),
      );
      final GtexMatchCenterController controller = GtexMatchCenterController(
        matchId: 'm-1',
        repository: repository,
        reconnectPolicy: _fastPolicy,
      );
      await controller.load();

      repository.currentController.add(
        buildMatchState(minute: 90, phase: GtexMatchPhase.fullTime),
      );
      await Future<void>.delayed(const Duration(milliseconds: 40));

      expect(controller.connection, GtexMatchConnectionStatus.finished);
      expect(
        repository.watchCount,
        1,
        reason: 'full time must not trigger a reconnect',
      );

      controller.dispose();
      await repository.disposeControllers();
    });
  });

  group('interaction', () {
    test('selectTab ignores a repeat selection', () async {
      final FakeMatchRepository repository = FakeMatchRepository();
      final GtexMatchCenterController controller = GtexMatchCenterController(
        matchId: 'm-1',
        repository: repository,
        reconnectPolicy: _fastPolicy,
      );
      await controller.load();

      int notifications = 0;
      controller.addListener(() => notifications += 1);

      controller.selectTab(2);
      controller.selectTab(2);

      expect(controller.selectedTab, 2);
      expect(notifications, 1);

      controller.dispose();
      await repository.disposeControllers();
    });

    test('sendInstruction is not re-entrant', () async {
      final FakeMatchRepository repository = FakeMatchRepository();
      final GtexMatchCenterController controller = GtexMatchCenterController(
        matchId: 'm-1',
        repository: repository,
        reconnectPolicy: _fastPolicy,
      );
      await controller.load();

      const GtexTacticalInstruction instruction = GtexTacticalInstruction(
        pressIntensity: 60,
        defensiveLine: 55,
        tempo: 70,
        riskLevel: 40,
      );

      await Future.wait<void>(<Future<void>>[
        controller.sendInstruction(instruction),
        controller.sendInstruction(instruction),
      ]);

      expect(repository.sentInstructions.length, 1);
      expect(controller.isSendingInstruction, isFalse);

      controller.dispose();
      await repository.disposeControllers();
    });

    test('does not notify after dispose', () async {
      final FakeMatchRepository repository = FakeMatchRepository();
      final GtexMatchCenterController controller = GtexMatchCenterController(
        matchId: 'm-1',
        repository: repository,
        reconnectPolicy: _fastPolicy,
      );
      await controller.load();
      final controllerStream = repository.currentController;

      controller.dispose();

      // Pushing a frame at a disposed controller must be inert, not a crash.
      controllerStream.add(buildMatchState(minute: 77));
      await Future<void>.delayed(Duration.zero);

      await repository.disposeControllers();
    });
  });
}
