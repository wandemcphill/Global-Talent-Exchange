import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/match_redesign/data/gtex_match_models.dart';
import 'package:gte_frontend/features/match_redesign/widgets/gtex_post_match_panel.dart';

void main() {
  testWidgets('full-time report shows stats, management context and goal replay', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(700, 1200));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    int? replayMinute;
    final GtexLiveMatchState match = GtexLiveMatchState(
      matchId: 'full-time-review-test',
      home: const GtexMatchTeam(
        id: 'home',
        name: 'Lagos Royals',
        shortName: 'LRO',
        score: 2,
        formation: '4-3-3',
        players: <GtexLineupPlayer>[],
        managerName: 'Coach Mira',
        recentFormPercent: 76,
        primaryColorHex: '#1DBF73',
      ),
      away: const GtexMatchTeam(
        id: 'away',
        name: 'Abuja United',
        shortName: 'ABU',
        score: 1,
        formation: '4-2-3-1',
        players: <GtexLineupPlayer>[],
        managerName: 'Coach Ade',
        recentFormPercent: 61,
        primaryColorHex: '#D8A948',
      ),
      minute: 90,
      phase: GtexMatchPhase.fullTime,
      pitchPlayers: const <GtexPitchPlayer>[],
      timeline: const <GtexMatchTimelineEvent>[
        GtexMatchTimelineEvent(
          minute: 71,
          type: GtexPitchEventType.goal,
          title: 'Alex Striker scores',
          description: 'Finished from inside the box',
          teamId: 'home',
          playerName: 'Alex Striker',
        ),
        GtexMatchTimelineEvent(
          minute: 80,
          type: GtexPitchEventType.substitution,
          title: 'Fresh legs in midfield',
          description: 'Midfield substitution',
          teamId: 'away',
        ),
      ],
      stats: const GtexMatchStats(
        homePossession: 57,
        awayPossession: 43,
        homeShots: 13,
        awayShots: 8,
        homeShotsOnTarget: 6,
        awayShotsOnTarget: 3,
        homePassAccuracy: 86,
        awayPassAccuracy: 79,
        homeExpectedGoals: 1.72,
        awayExpectedGoals: 0.84,
      ),
      highlights: const <GtexMatchHighlight>[],
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: GtexPostMatchPanel(
              match: match,
              onReplayGoal: (int minute) => replayMinute = minute,
            ),
          ),
        ),
      ),
    );

    expect(find.text('FULL-TIME PERFORMANCE REVIEW'), findsOneWidget);
    expect(find.text('Coach Mira'), findsOneWidget);
    expect(find.text('57%'), findsOneWidget);
    expect(find.text('Expected goals'), findsOneWidget);
    expect(find.textContaining('Alex Striker'), findsOneWidget);
    expect(find.textContaining('Fresh legs in midfield'), findsOneWidget);
    expect(find.byKey(const Key('gtex-post-match-goal-replay-71')), findsOneWidget);

    await tester.tap(find.byKey(const Key('gtex-post-match-goal-replay-71')));
    expect(replayMinute, 71);
    expect(tester.takeException(), isNull);
  });
}
