import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/match_redesign/data/gtex_match_models.dart';
import 'package:gte_frontend/features/match_redesign/presentation/gtex_match_center_screen_v2.dart';

import 'match_test_fixtures.dart';

Future<void> _pump(WidgetTester tester, Widget child) async {
  tester.view.physicalSize = const Size(1280, 900);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(
    MaterialApp(home: Scaffold(body: child)),
  );
  await tester.pump();
}

void main() {
  testWidgets('the post-match economy panel directs viewers to Player Detail', (
    tester,
  ) async {
    final FakeMatchRepository repository = FakeMatchRepository(
      initial: buildMatchState(
        minute: 90,
        phase: GtexMatchPhase.fullTime,
      ),
    );

    await _pump(
      tester,
      GtexMatchCenterScreenV2(matchId: 'm-1', repository: repository),
    );
    await settle(tester);

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
