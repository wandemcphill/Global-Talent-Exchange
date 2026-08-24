import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_redesign/data/gtex_match_feed.dart';
import 'package:gte_frontend/features/match_redesign/data/gtex_match_models.dart';

import 'match_test_fixtures.dart';

void main() {
  group('GtexMatchRevision', () {
    test('orders by phase before minute', () {
      final GtexMatchRevision firstHalf = GtexMatchRevision.of(
        buildMatchState(minute: 44, phase: GtexMatchPhase.firstHalf),
      );
      final GtexMatchRevision secondHalf = GtexMatchRevision.of(
        buildMatchState(minute: 5, phase: GtexMatchPhase.secondHalf),
      );
      expect(secondHalf.compareTo(firstHalf), greaterThan(0));
    });

    test('orders by timeline length when phase and minute tie', () {
      final GtexMatchRevision fewer = GtexMatchRevision.of(
        buildMatchState(minute: 30, timelineEvents: 2),
      );
      final GtexMatchRevision more = GtexMatchRevision.of(
        buildMatchState(minute: 30, timelineEvents: 5),
      );
      expect(more.compareTo(fewer), greaterThan(0));
    });
  });

  group('GtexMatchFeedGuard', () {
    test('accepts the first snapshot', () {
      final GtexMatchFeedGuard guard = GtexMatchFeedGuard(matchId: 'm-1');
      final verdict = guard.offer(buildMatchState(minute: 10));

      expect(verdict, GtexMatchFeedVerdict.accepted);
      expect(guard.current, isNotNull);
      expect(guard.diagnostics.accepted, 1);
    });

    test('drops a byte-identical repeat as a duplicate', () {
      final GtexMatchFeedGuard guard = GtexMatchFeedGuard(matchId: 'm-1');
      guard.offer(buildMatchState(minute: 10));
      final verdict = guard.offer(buildMatchState(minute: 10));

      expect(verdict, GtexMatchFeedVerdict.duplicate);
      expect(guard.diagnostics.duplicates, 1);
      expect(guard.diagnostics.accepted, 1, reason: 'state must not advance');
    });

    test('drops an out-of-order frame as stale', () {
      final GtexMatchFeedGuard guard = GtexMatchFeedGuard(matchId: 'm-1');
      guard.offer(buildMatchState(minute: 40));
      final verdict = guard.offer(buildMatchState(minute: 12));

      expect(verdict, GtexMatchFeedVerdict.stale);
      expect(guard.diagnostics.stale, 1);
      expect(
        guard.current!.minute,
        40,
        reason: 'a late frame must never rewind the visible clock',
      );
    });

    test('never rewinds the scoreline from a stale frame', () {
      final GtexMatchFeedGuard guard = GtexMatchFeedGuard(matchId: 'm-1');
      guard.offer(buildMatchState(minute: 60, homeScore: 2, awayScore: 1));
      guard.offer(buildMatchState(minute: 55, homeScore: 1, awayScore: 1));

      expect(guard.current!.home.score, 2);
      expect(guard.current!.away.score, 1);
    });

    test('treats a null snapshot as malformed', () {
      final GtexMatchFeedGuard guard = GtexMatchFeedGuard(matchId: 'm-1');
      expect(guard.offer(null), GtexMatchFeedVerdict.malformed);
      expect(guard.diagnostics.malformed, 1);
      expect(guard.current, isNull);
    });

    test('rejects a snapshot belonging to a different match', () {
      final GtexMatchFeedGuard guard = GtexMatchFeedGuard(matchId: 'm-1');
      guard.offer(buildMatchState(minute: 10));
      final verdict = guard.offer(
        buildMatchState(matchId: 'other-match', minute: 90),
      );

      expect(verdict, GtexMatchFeedVerdict.malformed);
      expect(guard.current!.matchId, 'm-1');
    });

    test('advances on a genuinely newer frame', () {
      final GtexMatchFeedGuard guard = GtexMatchFeedGuard(matchId: 'm-1');
      guard.offer(buildMatchState(minute: 10));
      final verdict = guard.offer(buildMatchState(minute: 11));

      expect(verdict, GtexMatchFeedVerdict.accepted);
      expect(guard.current!.minute, 11);
      expect(guard.diagnostics.accepted, 2);
    });

    test('retains the selected player across an accepted refresh', () {
      final GtexMatchFeedGuard guard = GtexMatchFeedGuard(matchId: 'm-1');
      guard.offer(buildMatchState(minute: 10));
      guard.mutateLocally(
        guard.current!.copyWith(selectedPlayerId: 'player-7'),
      );

      guard.offer(buildMatchState(minute: 11));

      expect(guard.current!.selectedPlayerId, 'player-7');
      expect(guard.current!.minute, 11);
    });

    test('reports full time', () {
      final GtexMatchFeedGuard guard = GtexMatchFeedGuard(matchId: 'm-1');
      guard.offer(buildMatchState(minute: 90, phase: GtexMatchPhase.fullTime));
      expect(guard.isFinished, isTrue);
    });

    test('counts dropped frames in aggregate', () {
      final GtexMatchFeedGuard guard = GtexMatchFeedGuard(matchId: 'm-1');
      guard.offer(buildMatchState(minute: 30));
      guard.offer(buildMatchState(minute: 30)); // duplicate
      guard.offer(buildMatchState(minute: 4)); // stale
      guard.offer(null); // malformed

      expect(guard.diagnostics.droppedTotal, 3);
    });
  });

  group('GtexMatchReconnectPolicy', () {
    const GtexMatchReconnectPolicy policy = GtexMatchReconnectPolicy(
      initialDelay: Duration(seconds: 1),
      maxDelay: Duration(seconds: 8),
      maxAttempts: 4,
    );

    test('backs off exponentially', () {
      expect(policy.delayForAttempt(1), const Duration(seconds: 1));
      expect(policy.delayForAttempt(2), const Duration(seconds: 2));
      expect(policy.delayForAttempt(3), const Duration(seconds: 4));
    });

    test('clamps at the ceiling', () {
      expect(policy.delayForAttempt(9), const Duration(seconds: 8));
    });

    test('stops retrying past the attempt budget', () {
      expect(policy.shouldRetry(4), isTrue);
      expect(policy.shouldRetry(5), isFalse);
    });
  });
}
