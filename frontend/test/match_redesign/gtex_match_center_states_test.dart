import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_redesign/data/gtex_match_models.dart';
import 'package:gte_frontend/features/match_redesign/presentation/gtex_match_center_screen_v2.dart';

import 'match_test_fixtures.dart';

Future<void> _pump(
  WidgetTester tester,
  Widget child, {
  Size size = const Size(1400, 1000),
}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(MaterialApp(home: child));
}

void main() {
  testWidgets('shows a loading state before the first snapshot lands', (
    tester,
  ) async {
    final Completer<GtexLiveMatchState> gate =
        Completer<GtexLiveMatchState>();
    final _GatedRepository repository = _GatedRepository(gate: gate);

    await _pump(
      tester,
      GtexMatchCenterScreenV2(matchId: 'm-1', repository: repository),
    );
    await tester.pump();

    expect(find.text('Loading live match authority'), findsOneWidget);

    gate.complete(buildMatchState(minute: 5));
    await settle(tester);
    expect(find.text('Loading live match authority'), findsNothing);

    await teardown(tester, repository);
  });

  testWidgets('shows an error state with a working retry', (tester) async {
    final FakeMatchRepository repository = FakeMatchRepository(
      fetchError: StateError('match authority unreachable'),
    );

    await _pump(
      tester,
      GtexMatchCenterScreenV2(matchId: 'm-1', repository: repository),
    );
    await settle(tester);

    expect(find.text('Live match unavailable'), findsOneWidget);
    expect(find.text('Retry live feed'), findsOneWidget);

    repository.fetchError = null;
    await tester.tap(find.text('Retry live feed'));
    await settle(tester);

    expect(find.text('Live match unavailable'), findsNothing);
    expect(find.textContaining('Lagos Crown'), findsWidgets);

    await teardown(tester, repository);
  });

  testWidgets('error state offers a way out when onExit is wired', (
    tester,
  ) async {
    int exits = 0;
    final FakeMatchRepository repository = FakeMatchRepository(
      fetchError: StateError('down'),
    );

    await _pump(
      tester,
      GtexMatchCenterScreenV2(
        matchId: 'm-1',
        repository: repository,
        onExit: () => exits += 1,
      ),
    );
    await settle(tester);

    await tester.tap(find.text('Back'));
    await tester.pump();
    expect(exits, 1);
  });

  testWidgets('error state hides the exit button when there is nowhere to go', (
    tester,
  ) async {
    final FakeMatchRepository repository = FakeMatchRepository(
      fetchError: StateError('down'),
    );

    await _pump(
      tester,
      GtexMatchCenterScreenV2(matchId: 'm-1', repository: repository),
    );
    await settle(tester);

    expect(
      find.text('Back'),
      findsNothing,
      reason: 'no dead-end buttons without a destination',
    );
  });

  testWidgets('reconnecting banner appears when the feed drops', (
    tester,
  ) async {
    final FakeMatchRepository repository = FakeMatchRepository(
      initial: buildMatchState(minute: 20),
    );

    await _pump(
      tester,
      GtexMatchCenterScreenV2(matchId: 'm-1', repository: repository),
    );
    await settle(tester);
    expect(find.text('RECONNECTING'), findsNothing);

    repository.currentController.addError(const FormatException('bad'));
    await tester.pump();
    await tester.pump();

    expect(find.text('RECONNECTING'), findsOneWidget);
    // The last good snapshot is still on screen behind the banner.
    expect(find.textContaining('Lagos Crown'), findsWidgets);

    // Unmount first so the controller cancels its reconnect timer, then close
    // the transport. Reversing the order leaves a pending timer at teardown.
    await teardown(tester, repository);
  });

  testWidgets('full time shows the replay entry when a destination exists', (
    tester,
  ) async {
    final List<String> opened = <String>[];
    final FakeMatchRepository repository = FakeMatchRepository(
      initial: buildMatchState(
        minute: 90,
        phase: GtexMatchPhase.fullTime,
        homeScore: 2,
        awayScore: 1,
      ),
    );

    await _pump(
      tester,
      GtexMatchCenterScreenV2(
        matchId: 'm-1',
        repository: repository,
        onOpenReplay: opened.add,
      ),
    );
    await settle(tester);

    expect(find.text('FEED CLOSED'), findsOneWidget);
    expect(find.text('Watch replay'), findsOneWidget);

    await tester.tap(find.text('Watch replay'));
    await tester.pump();
    expect(opened, <String>['m-1']);
  });

  testWidgets('full time hides the replay entry without a destination', (
    tester,
  ) async {
    final FakeMatchRepository repository = FakeMatchRepository(
      initial: buildMatchState(minute: 90, phase: GtexMatchPhase.fullTime),
    );

    await _pump(
      tester,
      GtexMatchCenterScreenV2(matchId: 'm-1', repository: repository),
    );
    await settle(tester);

    expect(find.text('Watch replay'), findsNothing);
  });

  testWidgets('renders on a narrow viewport without overflow', (tester) async {
    final FakeMatchRepository repository = FakeMatchRepository(
      initial: buildMatchState(minute: 33),
    );

    await _pump(
      tester,
      GtexMatchCenterScreenV2(matchId: 'm-1', repository: repository),
      size: const Size(400, 900),
    );
    await settle(tester);

    expect(find.text('MATCH CENTER'), findsWidgets);
    expect(tester.takeException(), isNull);

    await teardown(tester, repository);
  });

  testWidgets('timeline empty state is explicit, never blank', (tester) async {
    final FakeMatchRepository repository = FakeMatchRepository(
      initial: buildMatchState(minute: 3),
    );

    await _pump(
      tester,
      GtexMatchCenterScreenV2(matchId: 'm-1', repository: repository),
    );
    await settle(tester);

    // GtexMatchEmptyFeed renders its title upper-cased.
    expect(find.text('TIMELINE UNAVAILABLE'), findsOneWidget);
    expect(
      tester.takeException(),
      isNull,
      reason: 'the empty state itself must not overflow its panel',
    );

    await teardown(tester, repository);
  });
}

/// Repository whose first fetch completes only when the test says so.
class _GatedRepository extends FakeMatchRepository {
  _GatedRepository({required this.gate});

  final Completer<GtexLiveMatchState> gate;

  @override
  Future<GtexLiveMatchState> fetchLiveMatch(String matchId) => gate.future;
}
