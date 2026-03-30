import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/match/presentation/widgets/commentary_ribbon_widget.dart';
import 'package:gte_frontend/features/match/presentation/widgets/formation_board_widget.dart';
import 'package:gte_frontend/features/match/presentation/widgets/roster_card_widget.dart';
import 'package:gte_frontend/features/match/presentation/widgets/standings_context_widget.dart';
import 'package:gte_frontend/features/match/presentation/widgets/tactical_hud_widget.dart';

import 'support/gtex_match_broadcast_fixture.dart';

void main() {
  testWidgets('roster card renders starters and bench groups', (
    WidgetTester tester,
  ) async {
    final package = buildBroadcastTestPackage();

    await tester.pumpWidget(_wrap(RosterCardWidget(package: package)));

    expect(find.byKey(const Key('roster-card')), findsOneWidget);
    expect(find.text('Official Roster'), findsOneWidget);
    expect(find.text('Lagos Stars'), findsOneWidget);
    expect(find.text('Abuja City'), findsOneWidget);
    expect(find.text('SUBSTITUTES'), findsNWidgets(2));
  });

  testWidgets('formation board renders formation rail and bench data', (
    WidgetTester tester,
  ) async {
    final package = buildBroadcastTestPackage();

    await tester.pumpWidget(
      _wrap(
        FormationBoardWidget(
          team: package.home,
          title: '${package.home.teamName} Formation',
        ),
      ),
    );

    expect(find.byKey(const Key('formation-board-home')), findsOneWidget);
    expect(find.text('Lagos Stars Formation'), findsOneWidget);
    expect(find.text('COACH'), findsOneWidget);
    expect(find.text('Bench'), findsOneWidget);
    expect(find.textContaining('Salisu'), findsOneWidget);
  });

  testWidgets('standings context board renders table and storylines', (
    WidgetTester tester,
  ) async {
    final package = buildBroadcastTestPackage();

    await tester.pumpWidget(
      _wrap(StandingsContextWidget(contextBoard: package.context)),
    );

    expect(find.byKey(const Key('standings-context-board')), findsOneWidget);
    expect(find.text('Standings and Context'), findsOneWidget);
    expect(find.text('GTEX Premier League'), findsOneWidget);
    expect(find.textContaining('Top-four pressure'), findsOneWidget);
    expect(
      find.textContaining('Lagos can move into the top two'),
      findsOneWidget,
    );
  });

  testWidgets('commentary ribbon renders headline detail and trailing text', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _wrap(
        const CommentaryRibbonWidget(
          headline: 'Goal check',
          detail: 'The attacking move is under review from the far side.',
          trailing: "71'",
        ),
      ),
    );

    expect(find.text('Goal check'), findsOneWidget);
    expect(
      find.text('The attacking move is under review from the far side.'),
      findsOneWidget,
    );
    expect(find.text("71'"), findsOneWidget);
  });

  testWidgets('tactical HUD renders team instructions and rating strip', (
    WidgetTester tester,
  ) async {
    final package = buildBroadcastTestPackage();

    await tester.pumpWidget(_wrap(TacticalHudWidget(package: package)));

    expect(find.byKey(const Key('tactical-hud')), findsOneWidget);
    expect(find.text('Tactical HUD'), findsOneWidget);
    expect(find.text('Ratings strip'), findsOneWidget);
    expect(find.textContaining('High press 82'), findsOneWidget);
    expect(find.textContaining('Nnamdi'), findsWidgets);
  });
}

Widget _wrap(Widget child) {
  return MaterialApp(
    home: Scaffold(
      backgroundColor: const Color(0xFF060A10),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1100),
            child: child,
          ),
        ),
      ),
    ),
  );
}
