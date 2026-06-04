import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/compete/compete.dart';

void main() {
  group('CompetitionBracketSurface', () {
    testWidgets('shows blocked state when backend payload is missing', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(
        _host(const CompetitionBracketSurface(payload: null)),
      );

      expect(find.text('Bracket blocked'), findsOneWidget);
      expect(find.text('Backend bracket payload is missing.'), findsOneWidget);
    });

    testWidgets('shows degraded empty state instead of generating a bracket', (
      WidgetTester tester,
    ) async {
      final CompetitionBracketPayload payload =
          CompetitionBracketPayload.fromJson(<String, Object?>{
            'competition_id': 'comp-empty',
            'title': 'Locked Cup',
            'status': 'locked',
            'participant_count': 8,
            'capacity': 8,
            'backend_warnings': <String>['bracket_worker_pending'],
          });

      await tester.pumpWidget(
        _host(CompetitionBracketSurface(payload: payload)),
      );

      expect(find.text('Bracket pending backend payload'), findsOneWidget);
      expect(
        find.text(
          'No backend rounds were supplied, so this surface is not generating a placeholder bracket.',
        ),
        findsOneWidget,
      );
      expect(find.textContaining('bracket_worker_pending'), findsOneWidget);
      expect(find.text('Round 1'), findsNothing);
    });

    testWidgets('renders only matches supplied by backend payload', (
      WidgetTester tester,
    ) async {
      final CompetitionBracketPayload payload = _backendPayload();

      await tester.pumpWidget(
        _host(CompetitionBracketSurface(payload: payload)),
      );

      expect(find.text('GTEX Sunday Cup'), findsOneWidget);
      expect(find.text('Semi Final'), findsOneWidget);
      expect(find.text('Match A'), findsOneWidget);
      expect(find.text('Alpha FC'), findsOneWidget);
      expect(find.text('Beta FC'), findsOneWidget);
      expect(find.text('#1'), findsOneWidget);
      expect(find.text('#4'), findsOneWidget);
      expect(find.text('3'), findsOneWidget);
      expect(find.text('1'), findsOneWidget);
      expect(find.text('Live match live-semi-1'), findsOneWidget);
      expect(find.text('Bracket pending backend payload'), findsNothing);
    });

    testWidgets('marks backend rounds without matches as degraded', (
      WidgetTester tester,
    ) async {
      final CompetitionBracketPayload payload =
          CompetitionBracketPayload.fromJson(<String, Object?>{
            'competition_id': 'comp-round-only',
            'title': 'Round Only Cup',
            'lifecycle': <String, Object?>{'status': 'published'},
            'rounds': <Object?>[
              <String, Object?>{
                'id': 'round-1',
                'name': 'Opening Round',
                'status': 'scheduled',
              },
            ],
          });

      await tester.pumpWidget(
        _host(CompetitionBracketSurface(payload: payload)),
      );

      expect(find.text('Opening Round'), findsOneWidget);
      expect(
        find.text('Backend has not supplied matches for this round.'),
        findsOneWidget,
      );
    });
  });
}

Widget _host(Widget child) {
  return MaterialApp(home: Scaffold(body: SingleChildScrollView(child: child)));
}

CompetitionBracketPayload _backendPayload() {
  return CompetitionBracketPayload.fromJson(<String, Object?>{
    'competition_id': 'comp-42',
    'title': 'GTEX Sunday Cup',
    'lifecycle': <String, Object?>{
      'stage': 'in_progress',
      'bracket_published': true,
    },
    'bracket': <String, Object?>{
      'id': 'bracket-42',
      'revision': 'rev-7',
      'rounds': <Object?>[
        <String, Object?>{
          'id': 'round-semi',
          'name': 'Semi Final',
          'order': 1,
          'status': 'live',
          'matches': <Object?>[
            <String, Object?>{
              'id': 'match-semi-1',
              'label': 'Match A',
              'status': 'live',
              'home': <String, Object?>{
                'participant_id': 'alpha',
                'name': 'Alpha FC',
                'seed': 1,
              },
              'away': <String, Object?>{
                'participant_id': 'beta',
                'name': 'Beta FC',
                'seed': 4,
              },
              'score': <String, Object?>{'home': 3, 'away': 1},
              'winner_participant_id': 'alpha',
              'live_match_id': 'live-semi-1',
            },
          ],
        },
      ],
    },
  });
}
