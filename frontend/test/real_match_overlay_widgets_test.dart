import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/match/presentation/real_match_scene_director.dart';
import 'package:gte_frontend/features/match/presentation/widgets/commentary_ribbon_widget.dart';
import 'package:gte_frontend/features/match/presentation/widgets/match_moment_banner_widget.dart';
import 'package:gte_frontend/features/match/presentation/widgets/match_recap_board_widget.dart';
import 'package:gte_frontend/features/match/presentation/widgets/player_ratings_strip_widget.dart';
import 'package:gte_frontend/features/match/presentation/widgets/real_match_scorebug_widget.dart';
import 'package:gte_frontend/features/match/presentation/widgets/real_match_tactical_hud_widget.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/real_match_engine_presentation.dart';

import 'support/gtex_match_broadcast_fixture.dart';

void main() {
  testWidgets('real match scorebug renders phase, state, and event ribbon', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _wrap(
        const RealMatchScorebugWidget(
          homeName: 'LAG',
          awayName: 'ABJ',
          homeScore: 2,
          awayScore: 1,
          clockLabel: "72'",
          phaseLabel: 'Goal moment',
          stateLabel: 'Highlight replay',
          cameraLabel: 'REPLAY',
          eventLabel: 'Lagos score',
        ),
      ),
    );

    expect(find.byKey(const Key('real-match-scorebug')), findsOneWidget);
    expect(find.text('Goal moment'), findsOneWidget);
    expect(find.text('HIGHLIGHT REPLAY'), findsOneWidget);
    expect(find.text('REPLAY'), findsOneWidget);
    expect(find.text('Lagos score'), findsOneWidget);
  });

  testWidgets('real tactical HUD and ratings strip render team shape data', (
    WidgetTester tester,
  ) async {
    final viewState = buildBroadcastTestViewState();
    final package = buildBroadcastTestPackage();
    final MatchEvent goal = viewState.events.firstWhere(
      (MatchEvent event) => event.type == MatchViewerEventType.goal,
    );
    final MatchEnginePresentationState presentation =
        RealMatchSceneDirector.resolve(
          viewState: viewState,
          frame: viewState.frames[2],
          package: package,
          activeEvent: goal.copyWith(
            primaryPlayerName: 'Nnamdi',
            secondaryPlayerName: 'Okoro',
          ),
          playbackSeconds: 14,
        );

    await tester.pumpWidget(
      _wrap(
        Column(
          children: <Widget>[
            RealMatchTacticalHudWidget(
              package: package,
              presentation: presentation,
            ),
            const SizedBox(height: 12),
            PlayerRatingsStripWidget(players: presentation.ratingLeaders),
          ],
        ),
      ),
    );

    expect(find.byKey(const Key('real-match-tactical-hud')), findsOneWidget);
    expect(find.text('Tactical HUD'), findsOneWidget);
    expect(find.text('LAG'), findsOneWidget);
    expect(find.text('ABJ'), findsOneWidget);
    expect(find.textContaining('Possession focus: Nnamdi'), findsOneWidget);
    expect(find.byKey(const Key('player-ratings-strip')), findsOneWidget);
    expect(find.textContaining('Nnamdi 8.1'), findsOneWidget);
  });

  testWidgets('moment banner and commentary ribbon render event context', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _wrap(
        const Column(
          children: <Widget>[
            MatchMomentBannerWidget(
              banner: MatchEngineBanner(
                label: 'Substitution',
                detail: 'Emeka on for Bassey',
                accentColor: Color(0xFF53B1FD),
                icon: Icons.swap_horiz,
              ),
            ),
            SizedBox(height: 12),
            CommentaryRibbonWidget(
              headline: 'Lagos change',
              detail: 'Fresh legs arrive as the midfield shape is reset.',
              trailing: "64'",
            ),
          ],
        ),
      ),
    );

    expect(find.byKey(const Key('match-moment-banner')), findsOneWidget);
    expect(find.text('Substitution'), findsOneWidget);
    expect(find.text('Emeka on for Bassey'), findsOneWidget);
    expect(find.byKey(const Key('commentary-ribbon')), findsOneWidget);
    expect(find.text('Lagos change'), findsOneWidget);
  });

  testWidgets('recap board renders halftime or full-time summary bullets', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _wrap(
        const MatchRecapBoardWidget(
          summaryBoard: MatchEngineSummaryBoard(
            title: 'Halftime recap',
            subtitle: 'LAG 1 - 0 ABJ',
            bullets: <String>[
              'Lagos control the right flank in the opening spell.',
              'Abuja are threatening on quick transitions.',
            ],
          ),
        ),
      ),
    );

    expect(find.byKey(const Key('match-recap-board')), findsOneWidget);
    expect(find.text('HALFTIME RECAP'), findsOneWidget);
    expect(find.text('LAG 1 - 0 ABJ'), findsOneWidget);
    expect(
      find.textContaining('Lagos control the right flank'),
      findsOneWidget,
    );
  });
}

Widget _wrap(Widget child) {
  return MaterialApp(
    home: Scaffold(
      backgroundColor: const Color(0xFF060A10),
      body: Padding(
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
