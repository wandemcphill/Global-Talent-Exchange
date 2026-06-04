import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/compete/providers/competition_controller.dart';
import 'package:gte_frontend/data/competition_api.dart';
import 'package:gte_frontend/features/compete/compete.dart';
import 'package:gte_frontend/features/compete/presentation/screens/competition_detail_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('detail screen renders transparent financials and payout', (
    WidgetTester tester,
  ) async {
    final CompetitionController controller = CompetitionController(
      api: CompetitionApi.fixture(),
      currentUserId: 'fixture-user',
      currentUserName: 'Fixture Trader',
    );
    await controller.openCompetition('ugc-101');

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: CompetitionDetailScreen(
          controller: controller,
          competitionId: 'ugc-101',
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(find.text('Transparent financials'), 300);
    expect(find.text('Transparent financials'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('Transparent payout'), 300);
    expect(find.text('Transparent payout'), findsOneWidget);
    expect(find.textContaining('secure escrow'), findsWidgets);
    expect(find.textContaining('Platform service fee'), findsOneWidget);
    expect(find.textContaining('Host fee'), findsOneWidget);
    expect(find.textContaining('Prize pool'), findsOneWidget);
  });

  testWidgets('detail screen blocks bracket when backend payload is missing', (
    WidgetTester tester,
  ) async {
    final CompetitionController controller = CompetitionController(
      api: CompetitionApi.fixture(),
      currentUserId: 'fixture-user',
      currentUserName: 'Fixture Trader',
    );
    await controller.openCompetition('ugc-101');

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: CompetitionDetailScreen(
          controller: controller,
          competitionId: 'ugc-101',
        ),
      ),
    );
    await tester.pumpAndSettle();

    await _scrollUntilTextVisible(tester, 'TOURNAMENT LIFECYCLE');

    expect(find.text('TOURNAMENT LIFECYCLE'), findsOneWidget);
    expect(find.text('Progression: backend-owned'), findsOneWidget);
    expect(find.text('Bracket: backend payload missing'), findsOneWidget);
    expect(find.text('Bracket blocked'), findsOneWidget);
    expect(find.text('Backend bracket payload is missing.'), findsOneWidget);
    expect(find.text('Quarter Finals'), findsNothing);
  });

  testWidgets('detail screen renders backend bracket rounds and match nodes', (
    WidgetTester tester,
  ) async {
    final CompetitionController controller = CompetitionController(
      api: CompetitionApi.fixture(),
      currentUserId: 'fixture-user',
      currentUserName: 'Fixture Trader',
    );
    await controller.openCompetition('ugc-101');

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: CompetitionDetailScreen(
          controller: controller,
          competitionId: 'ugc-101',
          bracketPayload: _backendBracketPayload(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await _scrollUntilTextVisible(tester, 'GTEX Sunday Cup');

    expect(find.text('GTEX Sunday Cup'), findsOneWidget);
    expect(find.text('In progress'), findsOneWidget);
    expect(find.text('Bracket: 2 backend rounds'), findsOneWidget);
    expect(find.text('Semi Final'), findsOneWidget);
    expect(find.text('Final'), findsOneWidget);
    expect(find.text('Semi A'), findsOneWidget);
    expect(find.text('Final A'), findsOneWidget);
    expect(find.text('Lagos United'), findsWidgets);
    expect(find.text('Accra City'), findsOneWidget);
    expect(find.text('Winner of Semi B'), findsOneWidget);
    expect(find.text('Open match center'), findsOneWidget);
    expect(find.text('Live match live-final-1'), findsNothing);
    expect(find.text('Bracket blocked'), findsNothing);
  });

  testWidgets('detail screen loads bracket payload from backend loader', (
    WidgetTester tester,
  ) async {
    final CompetitionController controller = CompetitionController(
      api: CompetitionApi.fixture(),
      currentUserId: 'fixture-user',
      currentUserName: 'Fixture Trader',
    );
    await controller.openCompetition('ugc-101');

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: CompetitionDetailScreen(
          controller: controller,
          competitionId: 'ugc-101',
          bracketPayloadLoader: (_) async => _backendBracketPayload(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await _scrollUntilTextVisible(tester, 'GTEX Sunday Cup');

    expect(find.text('GTEX Sunday Cup'), findsOneWidget);
    expect(find.text('Bracket blocked'), findsNothing);
    expect(find.text('Bracket pending backend payload'), findsNothing);
  });
}

CompetitionBracketPayload _backendBracketPayload() {
  return CompetitionBracketPayload.fromJson(<String, Object?>{
    'competition_id': 'ugc-101',
    'title': 'GTEX Sunday Cup',
    'lifecycle': <String, Object?>{
      'stage': 'in_progress',
      'bracket_published': true,
    },
    'bracket': <String, Object?>{
      'id': 'bracket-ugc-101',
      'revision': 'rev-5',
      'rounds': <Object?>[
        <String, Object?>{
          'id': 'round-semi',
          'name': 'Semi Final',
          'order': 1,
          'status': 'completed',
          'matches': <Object?>[
            <String, Object?>{
              'id': 'match-semi-a',
              'label': 'Semi A',
              'status': 'completed',
              'home': <String, Object?>{
                'participant_id': 'lagos',
                'name': 'Lagos United',
                'seed': 1,
              },
              'away': <String, Object?>{
                'participant_id': 'accra',
                'name': 'Accra City',
                'seed': 4,
              },
              'score': <String, Object?>{'home': 2, 'away': 1},
              'winner_participant_id': 'lagos',
            },
          ],
        },
        <String, Object?>{
          'id': 'round-final',
          'name': 'Final',
          'order': 2,
          'status': 'scheduled',
          'matches': <Object?>[
            <String, Object?>{
              'id': 'match-final-a',
              'label': 'Final A',
              'status': 'scheduled',
              'home': <String, Object?>{
                'participant_id': 'lagos',
                'name': 'Lagos United',
                'seed': 1,
              },
              'away': <String, Object?>{
                'source_match_id': 'match-semi-b',
                'source_label': 'Winner of Semi B',
              },
              'live_match_id': 'live-final-1',
            },
          ],
        },
      ],
    },
  });
}

Future<void> _scrollUntilTextVisible(
  WidgetTester tester,
  String text, {
  int maxScrolls = 10,
}) async {
  final Finder scrollable = find.byType(Scrollable).first;
  for (int attempt = 0; attempt < maxScrolls; attempt += 1) {
    if (find.text(text).evaluate().isNotEmpty) {
      return;
    }
    await tester.drag(scrollable, const Offset(0, -460));
    await tester.pumpAndSettle();
  }
}
