import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/match_redesign/data/gtex_match_models.dart';
import 'package:gte_frontend/features/match_redesign/widgets/gtex_2d_pitch.dart';

GtexLiveMatchState _match({required double playerX}) {
  return GtexLiveMatchState(
    matchId: 'motion-test-match',
    home: const GtexMatchTeam(
      id: 'home',
      name: 'Lagos Royals',
      shortName: 'LRO',
      score: 0,
      formation: '4-3-3',
      players: <GtexLineupPlayer>[],
    ),
    away: const GtexMatchTeam(
      id: 'away',
      name: 'Abuja United',
      shortName: 'ABU',
      score: 0,
      formation: '4-2-3-1',
      players: <GtexLineupPlayer>[],
    ),
    minute: 18,
    phase: GtexMatchPhase.firstHalf,
    pitchPlayers: <GtexPitchPlayer>[
      GtexPitchPlayer(
        playerId: 'player-9',
        teamId: 'home',
        name: 'Alex Striker',
        shirtNumber: 9,
        x: playerX,
        y: 0.45,
        isHome: true,
        hasBall: true,
      ),
      const GtexPitchPlayer(
        playerId: 'player-4',
        teamId: 'away',
        name: 'Morgan Defender',
        shirtNumber: 4,
        x: 0.76,
        y: 0.58,
        isHome: false,
      ),
    ],
    timeline: const <GtexMatchTimelineEvent>[],
    stats: const GtexMatchStats(
      homePossession: 55,
      awayPossession: 45,
      homeShots: 2,
      awayShots: 1,
      homeShotsOnTarget: 1,
      awayShotsOnTarget: 0,
      homePassAccuracy: 83,
      awayPassAccuracy: 78,
      homeExpectedGoals: 0.6,
      awayExpectedGoals: 0.2,
    ),
    highlights: const <GtexMatchHighlight>[],
  );
}

void main() {
  testWidgets('2D pitch animates keyed player tokens and names the ball carrier', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Center(
            child: SizedBox(
              width: 390,
              child: Gtex2dPitch(
                match: _match(playerX: 0.25),
                onPlayerSelected: (_) {},
              ),
            ),
          ),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('ALEX STRIKER'), findsOneWidget);
    expect(find.byType(AnimatedPositioned), findsNWidgets(2));
    final double startX = tester.getTopLeft(
      find.descendant(
        of: find.byKey(const ValueKey<String>('player-9')),
        matching: find.byType(GestureDetector),
      ),
    ).dx;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Center(
            child: SizedBox(
              width: 390,
              child: Gtex2dPitch(
                match: _match(playerX: 0.72),
                onPlayerSelected: (_) {},
              ),
            ),
          ),
        ),
      ),
    );
    await tester.pump(const Duration(milliseconds: 210));

    final double movedX = tester.getTopLeft(
      find.descendant(
        of: find.byKey(const ValueKey<String>('player-9')),
        matching: find.byType(GestureDetector),
      ),
    ).dx;
    expect(movedX, greaterThan(startX));
    expect(movedX, lessThan(300));
    expect(tester.takeException(), isNull);
  });
}
