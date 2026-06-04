import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/match_center/presentation/broadcast_package_models.dart';
import 'package:gte_frontend/features/match_center/presentation/widgets/commentary_ribbon_widget.dart';
import 'package:gte_frontend/features/match_center/presentation/widgets/formation_board_widget.dart';
import 'package:gte_frontend/features/match_center/presentation/widgets/roster_card_widget.dart';
import 'package:gte_frontend/features/match_center/presentation/widgets/scorebug_widget.dart';
import 'package:gte_frontend/features/match_center/presentation/widgets/standings_context_widget.dart';
import 'package:gte_frontend/features/match_center/presentation/widgets/storyline_panel_widget.dart';
import 'package:gte_frontend/features/match_center/presentation/widgets/tactical_hud_widget.dart';
import 'package:gte_frontend/features/match_center/presentation/broadcast_scene_director.dart';

import 'support/gtex_match_broadcast_fixture.dart';

void main() {
  testWidgets('roster card renders starters and bench groups', (
    WidgetTester tester,
  ) async {
    final package = buildBroadcastTestPackage();

    await tester.pumpWidget(_wrap(RosterCardWidget(package: package)));

    expect(find.byKey(const Key('roster-card')), findsOneWidget);
    expect(find.text('Official Roster Card'), findsOneWidget);
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
      _wrap(
        StandingsContextWidget(
          contextBoard: package.context,
          homeTeam: package.home,
          awayTeam: package.away,
        ),
      ),
    );

    expect(find.byKey(const Key('standings-context-board')), findsOneWidget);
    expect(find.text('Standings and Context'), findsOneWidget);
    expect(find.text('GTEX Premier League'), findsOneWidget);
    expect(find.textContaining('3rd versus 5th'), findsOneWidget);
    expect(
      find.textContaining('Lagos can move into the top two'),
      findsNothing,
    );
  });

  testWidgets('storyline panel renders only populated buckets', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _wrap(
        StorylinePanelWidget(
          panel: const BroadcastStorylinePanelData(
            staffNotes: <String>['Balogun keeps the press aggressive.'],
            pressRoundup: <String>['Press focus: title-race pressure.'],
            talkingPoints: <String>['Lagos can move into the top two.'],
          ),
        ),
      ),
    );

    expect(find.byKey(const Key('storyline-panel')), findsOneWidget);
    expect(find.text('Storyline Panel'), findsOneWidget);
    expect(find.text('STAFF NOTES'), findsOneWidget);
    expect(find.text('PRESS ROUNDUP'), findsOneWidget);
    expect(find.text('TALKING POINTS'), findsOneWidget);
    expect(find.text('SOCIAL ROUNDUP'), findsNothing);
  });

  testWidgets('scorebug renders abbreviations, score, clock, and phase', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _wrap(
        const MatchScorebarWidget(
          homeName: 'LAG',
          awayName: 'ABJ',
          homeScore: 1,
          awayScore: 0,
          clockLabel: "71'",
          statusLabel: 'Open Play',
          cameraState: MatchSimCameraState.attackingThird,
          eventLabel: 'Lagos score',
        ),
      ),
    );

    expect(find.byKey(const Key('broadcast-scorebug')), findsOneWidget);
    expect(find.text('LAG'), findsOneWidget);
    expect(find.text('ABJ'), findsOneWidget);
    expect(find.text("71'"), findsOneWidget);
    expect(find.text('Open Play | ATTACK'), findsOneWidget);
    expect(find.text('Lagos score'), findsOneWidget);
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

    expect(find.byKey(const Key('commentary-ribbon')), findsOneWidget);
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
