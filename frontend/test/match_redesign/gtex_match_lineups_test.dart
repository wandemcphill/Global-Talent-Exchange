import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/match_redesign/data/gtex_match_models.dart';
import 'package:gte_frontend/features/match_redesign/widgets/gtex_match_lineups.dart';

void main() {
  testWidgets('match lineup exposes manager, form, fitness and bench context', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(900, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    const GtexLineupPlayer starter = GtexLineupPlayer(
      id: 'starter-9',
      name: 'Alex Forward',
      position: 'ST',
      shirtNumber: 9,
      rating: 84,
      formLabel: 'WWDWL',
      fitnessPct: 92,
    );
    const GtexLineupPlayer substitute = GtexLineupPlayer(
      id: 'bench-18',
      name: 'Reserve Striker',
      position: 'ST',
      shirtNumber: 18,
      rating: 77,
      formLabel: 'DWW',
      fitnessPct: 88,
    );
    const GtexMatchTeam home = GtexMatchTeam(
      id: 'home',
      name: 'Lagos Royals',
      shortName: 'LRO',
      score: 0,
      formation: '4-3-3',
      players: <GtexLineupPlayer>[starter],
      managerName: 'Coach Mira',
      recentFormPercent: 72,
      mentality: 'attacking',
      instructionSummary: <String>['High press'],
      bench: <GtexLineupPlayer>[substitute],
    );
    const GtexMatchTeam away = GtexMatchTeam(
      id: 'away',
      name: 'Abuja United',
      shortName: 'ABU',
      score: 0,
      formation: '4-2-3-1',
      players: <GtexLineupPlayer>[],
    );

    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: GtexMatchLineups(home: home, away: away),
        ),
      ),
    );

    expect(find.text('MANAGER · COACH MIRA'), findsOneWidget);
    expect(find.text('FORM · 72%'), findsOneWidget);
    expect(find.text('HIGH PRESS'), findsOneWidget);
    expect(find.text('WWDWL'), findsOneWidget);
    expect(find.text('FIT 92%'), findsOneWidget);
    expect(find.text('SUBSTITUTES'), findsOneWidget);
    expect(find.textContaining('Reserve Striker'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
