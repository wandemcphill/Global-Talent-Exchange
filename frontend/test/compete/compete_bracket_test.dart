import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/compete/compete_bracket.dart';

void main() {
  test('legacy bracket import exposes canonical backend payload parser', () {
    final CompetitionBracketPayload payload =
        CompetitionBracketPayload.fromJson(_payload());

    expect(payload.competitionId, 'cup-1');
    expect(payload.lifecycle.stage, CompetitionLifecycleStage.inProgress);
    expect(payload.rounds.single.displayName, 'Semi-final');
    expect(payload.rounds.single.matches.single.homeScore, 2);
  });

  testWidgets('legacy bracket import renders canonical backend rounds only', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: CompetitionBracketSurface(
            payload: CompetitionBracketPayload.fromJson(_payload()),
          ),
        ),
      ),
    );

    expect(find.text('Semi-final'), findsOneWidget);
    expect(find.text('Lagos United'), findsOneWidget);
    expect(find.text('Accra City'), findsOneWidget);
    expect(find.text('2'), findsOneWidget);
  });

  testWidgets('legacy bracket import blocks missing backend bracket payload', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(body: CompetitionBracketSurface(payload: null)),
      ),
    );

    expect(find.text('Bracket blocked'), findsOneWidget);
  });
}

Map<String, Object?> _payload() {
  return <String, Object?>{
    'competition_id': 'cup-1',
    'lifecycle': <String, Object?>{
      'state': 'live',
      'label': 'Live bracket',
      'detail': 'Backend lifecycle state',
    },
    'bracket': <String, Object?>{
      'rounds': <Object?>[
        <String, Object?>{
          'name': 'Semi-final',
          'matches': <Object?>[
            <String, Object?>{
              'id': 'match-1',
              'home': <String, Object?>{'name': 'Lagos United'},
              'away': <String, Object?>{'name': 'Accra City'},
              'home_score': 2,
              'away_score': 1,
              'status': 'complete',
            },
          ],
        },
      ],
    },
  };
}
