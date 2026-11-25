import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_redesign/data/gtex_match_models.dart';
import 'package:gte_frontend/features/match_redesign/widgets/gtex_2d_pitch.dart';
import 'package:gte_frontend/features/match_redesign/widgets/gtex_commentary_match.dart';

GtexLiveMatchState _match() {
  return GtexLiveMatchState(
    matchId: 'commentary-match',
    minute: 37,
    phase: GtexMatchPhase.firstHalf,
    home: const GtexMatchTeam(
      id: 'home',
      name: 'Ekiti FC',
      shortName: 'EKI',
      score: 1,
      formation: '5-3-2',
      mentality: 'defensive',
      instructionSummary: <String>['low block', 'narrow'],
      players: <GtexLineupPlayer>[
        GtexLineupPlayer(
          id: 'eki-9',
          name: 'A. Adeyemi',
          position: 'ST',
          shirtNumber: 9,
          rating: 7.2,
          fitnessPct: 81,
        ),
      ],
    ),
    away: const GtexMatchTeam(
      id: 'away',
      name: 'Lagos Titans',
      shortName: 'LAG',
      score: 0,
      formation: '4-4-2',
      mentality: 'attacking',
      players: <GtexLineupPlayer>[],
    ),
    pitchPlayers: const <GtexPitchPlayer>[
      GtexPitchPlayer(
        playerId: 'eki-9',
        teamId: 'home',
        name: 'A. Adeyemi',
        shirtNumber: 9,
        x: 0.7,
        y: 0.4,
        isHome: true,
      ),
    ],
    timeline: const <GtexMatchTimelineEvent>[
      GtexMatchTimelineEvent(
        minute: 12,
        type: GtexPitchEventType.pass,
        title: 'Circulation',
        description: 'Ekiti play it out from the back. Adeyemi finds the pivot.',
        teamId: 'home',
      ),
      GtexMatchTimelineEvent(
        minute: 37,
        type: GtexPitchEventType.shot,
        title: 'Shot',
        description: 'A. Adeyemi shoots from the edge of the box.',
        teamId: 'home',
        playerName: 'A. Adeyemi',
      ),
    ],
    stats: const GtexMatchStats(
      homePossession: 58,
      awayPossession: 42,
      homeShots: 7,
      awayShots: 3,
      homeShotsOnTarget: 3,
      awayShotsOnTarget: 1,
      homePassAccuracy: 84,
      awayPassAccuracy: 77,
      homeExpectedGoals: 1.1,
      awayExpectedGoals: 0.4,
    ),
    highlights: const <GtexMatchHighlight>[],
  );
}

void main() {
  testWidgets('commentary mode shows the lineup, tactic, stamina and stats without a pitch', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1200, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 1100,
            height: 700,
            child: GtexLiveMatchStage(
              match: _match().copyWith(timeline: <GtexMatchTimelineEvent>[_match().timeline.first]),
              onPlayerSelected: (_) {},
            ),
          ),
        ),
      ),
    );
    await tester.pump();

    expect(find.byType(Gtex2dPitch), findsNothing);
    expect(find.byKey(const Key('commentary-only')), findsOneWidget);
    expect(find.textContaining('5-3-2'), findsWidgets);
    expect(find.textContaining('Mentality  defensive'), findsOneWidget);
    expect(find.textContaining('A. Adeyemi'), findsWidgets);
    expect(find.textContaining('81% STA'), findsOneWidget);
    expect(find.text('Shots'), findsOneWidget);
    expect(find.textContaining('play it out from the back'), findsOneWidget);
    expect(find.textContaining('is about to act'), findsNothing);
    expect(find.byKey(const Key('commentary-hold')), findsNothing);
  });

  testWidgets('the classic pitch keeps the previous picture until the chance lands', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1200, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SizedBox(width: 1100, height: 700, child: _PitchHost()),
        ),
      ),
    );
    await tester.pump();

    expect(find.byType(Gtex2dPitch), findsNothing);
    expect(find.byKey(const Key('commentary-only')), findsOneWidget);

    tester.state<_PitchHostState>(find.byType(_PitchHost)).arrive();
    await tester.pump();
    expect(find.byType(Gtex2dPitch), findsOneWidget);
    expect(tester.widget<Gtex2dPitch>(find.byType(Gtex2dPitch)).match.pitchPlayers.single.x, 0.2);
    expect(find.textContaining('is about to act'), findsOneWidget);
    expect(find.textContaining('shoots from the edge'), findsNothing);

    await tester.pump(kCommentaryActionHold);
    await tester.pump();
    expect(find.byType(Gtex2dPitch), findsOneWidget);
    expect(tester.widget<Gtex2dPitch>(find.byType(Gtex2dPitch)).match.pitchPlayers.single.x, 0.8);
    expect(find.textContaining('shoots from the edge'), findsOneWidget);

    await tester.pump(kHighlightPicture);
    await tester.pump();
    expect(find.byType(Gtex2dPitch), findsNothing);
    expect(find.byKey(const Key('commentary-only')), findsOneWidget);
    expect(find.textContaining('shoots from the edge'), findsOneWidget);
  });

  test('a shot holds and a pass does not', () {
    expect(commentaryHoldsForRead(GtexPitchEventType.shot), isTrue);
    expect(commentaryHoldsForRead(GtexPitchEventType.pass), isFalse);
  });
}

class _PitchHost extends StatefulWidget {
  const _PitchHost();

  @override
  State<_PitchHost> createState() => _PitchHostState();
}

class _PitchHostState extends State<_PitchHost> {
  late GtexLiveMatchState _matchState = _match().copyWith(
    timeline: <GtexMatchTimelineEvent>[_match().timeline.first],
    pitchPlayers: <GtexPitchPlayer>[
      const GtexPitchPlayer(
        playerId: 'eki-9',
        teamId: 'home',
        name: 'A. Adeyemi',
        shirtNumber: 9,
        x: 0.2,
        y: 0.4,
        isHome: true,
      ),
    ],
  );

  void arrive() {
    setState(() {
      _matchState = _match().copyWith(
        pitchPlayers: <GtexPitchPlayer>[
          const GtexPitchPlayer(
            playerId: 'eki-9',
            teamId: 'home',
            name: 'A. Adeyemi',
            shirtNumber: 9,
            x: 0.8,
            y: 0.4,
            isHome: true,
          ),
        ],
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return GtexLiveMatchStage(match: _matchState, onPlayerSelected: (_) {});
  }
}
