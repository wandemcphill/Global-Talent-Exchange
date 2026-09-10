import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_redesign/data/gtex_match_models.dart';
import 'package:gte_frontend/features/match_redesign/presentation/gtex_match_center_screen_v2.dart';

import 'match_test_fixtures.dart';

/// The match centre is where a reader is most likely to believe that a good
/// performance just made them money, so it is where the timing has to be exact.
///
/// This panel used to be headed "ECONOMY IMPACT" and, with nothing to show, read
/// "No live valuation movement returned for this match." No backend route emits
/// `economy_impacts`, so that sentence was what every user saw, and it told them
/// that per-match live valuation movement is a thing GTEX produces and had
/// merely failed to return this time. It is not: a performance is not persisted
/// until the fixture settles, it then has to earn a place in a rolling six-match
/// window, and the bounded overlay only reaches a published valuation on the
/// daily snapshot run.

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
  testWidgets('a live match never claims to have repriced anybody', (
    tester,
  ) async {
    final FakeMatchRepository repository = FakeMatchRepository(
      initial: buildMatchState(minute: 33),
    );

    await _pump(
      tester,
      GtexMatchCenterScreenV2(matchId: 'm-1', repository: repository),
    );
    await settle(tester);

    expect(
      find.textContaining(
        'does not reprice a footballer while it is being played',
      ),
      findsOneWidget,
    );
    // The old sentence implied a feed that does not exist.
    expect(
      find.textContaining('No live valuation movement returned'),
      findsNothing,
    );

    await teardown(tester, repository);
  });

  testWidgets('the empty state states the real cadence rather than a gap', (
    tester,
  ) async {
    final FakeMatchRepository repository = FakeMatchRepository(
      initial: buildMatchState(minute: 33),
    );

    await _pump(
      tester,
      GtexMatchCenterScreenV2(matchId: 'm-1', repository: repository),
    );
    await settle(tester);

    expect(find.textContaining('recorded at full time'), findsOneWidget);
    expect(find.textContaining('rolling'), findsOneWidget);
    expect(find.textContaining('next daily recalculation'), findsOneWidget);
    // And it points at where the real, data-backed consequence lives.
    expect(
      find.textContaining('Open a player from the lineups'),
      findsOneWidget,
    );

    await teardown(tester, repository);
  });

  testWidgets('the panel is no longer headed as an economy or price event', (
    tester,
  ) async {
    final FakeMatchRepository repository = FakeMatchRepository(
      initial: buildMatchState(minute: 33),
    );

    await _pump(
      tester,
      GtexMatchCenterScreenV2(matchId: 'm-1', repository: repository),
    );
    await settle(tester);

    expect(find.text('MATCHDAY → VALUATION'), findsOneWidget);
    expect(find.text('ECONOMY IMPACT'), findsNothing);

    await teardown(tester, repository);
  });

  testWidgets(
    'a backend-supplied movement is labelled valuation, never share price',
    (tester) async {
      // The parser for this payload exists, so the branch has to stay honest
      // even though nothing populates it today.
      final FakeMatchRepository repository = FakeMatchRepository(
        initial: buildMatchState(
          minute: 90,
          phase: GtexMatchPhase.fullTime,
          economyImpacts: const <GtexMatchEconomyImpact>[
            GtexMatchEconomyImpact(
              playerName: 'A. King',
              deltaPercent: 1.2,
              deltaLabel: '+1.2%',
            ),
          ],
        ),
      );

      await _pump(
        tester,
        GtexMatchCenterScreenV2(matchId: 'm-1', repository: repository),
      );
      await settle(tester);

      expect(find.textContaining('+1.2%'), findsWidgets);
      expect(
        find.textContaining('They are not share price movements'),
        findsOneWidget,
      );

      await teardown(tester, repository);
    },
  );
}
