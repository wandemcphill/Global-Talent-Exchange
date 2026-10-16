import 'dart:async';

import 'gtex_match_models.dart';
import 'gtex_match_repository.dart';

class GtexMatchDemoRepository implements GtexMatchRepository {
  const GtexMatchDemoRepository();

  @override
  Future<GtexLiveMatchState> fetchLiveMatch(String matchId) async {
    return _demoState(matchId, minute: 67);
  }

  @override
  Stream<GtexLiveMatchState> watchLiveMatch(String matchId) {
    return Stream<GtexLiveMatchState>.periodic(
      const Duration(milliseconds: 900),
      (int tick) => _demoState(matchId, minute: 67 + tick),
    ).take(25);
  }

  @override
  Future<void> sendTacticalInstruction(
    String matchId,
    GtexTacticalInstruction instruction,
  ) async {
    await Future<void>.delayed(const Duration(milliseconds: 250));
  }
}

GtexLiveMatchState _demoState(String matchId, {required int minute}) {
  final homePlayers = List.generate(11, (index) {
    final positions = [
      'GK',
      'RB',
      'CB',
      'CB',
      'LB',
      'DM',
      'CM',
      'AM',
      'RW',
      'ST',
      'LW',
    ];
    return GtexLineupPlayer(
      id: 'h$index',
      name:
          [
            'Ayo King',
            'D. Ramos',
            'S. Bello',
            'M. Cruz',
            'K. Stone',
            'J. Silva',
            'E. Mensah',
            'N. Rivers',
            'T. Malik',
            'Leo Vale',
            'I. Costa',
          ][index],
      position: positions[index],
      shirtNumber: index + 1,
      rating: 6.8 + (index % 4) * 0.3,
      isRegen: index == 9,
    );
  });
  final awayPlayers = List.generate(11, (index) {
    final positions = [
      'GK',
      'RB',
      'CB',
      'CB',
      'LB',
      'DM',
      'CM',
      'AM',
      'RW',
      'ST',
      'LW',
    ];
    return GtexLineupPlayer(
      id: 'a$index',
      name:
          [
            'P. Wade',
            'O. Grant',
            'L. Faye',
            'C. Dunn',
            'R. Okafor',
            'M. Nadir',
            'F. Diaz',
            'A. Chen',
            'B. Cole',
            'S. Imani',
            'R. Vega',
          ][index],
      position: positions[index],
      shirtNumber: index + 12,
      rating: 6.5 + (index % 5) * 0.25,
      isRegen: index == 7,
    );
  });

  return GtexLiveMatchState(
    matchId: matchId,
    minute: minute,
    phase: minute >= 90 ? GtexMatchPhase.fullTime : GtexMatchPhase.secondHalf,
    isWatchedByOwner: true,
    home: GtexMatchTeam(
      id: 'club-home',
      name: 'Lagos Crown FC',
      shortName: 'LCF',
      score: minute > 70 ? 2 : 1,
      formation: '4-2-3-1',
      players: homePlayers,
    ),
    away: GtexMatchTeam(
      id: 'club-away',
      name: 'Accra Voltage',
      shortName: 'AVG',
      score: 1,
      formation: '4-3-3',
      players: awayPlayers,
    ),
    pitchPlayers: _pitchPlayers(homePlayers, awayPlayers, minute),
    stats: GtexMatchStats(
      homePossession: 58,
      awayPossession: 42,
      homeShots: 12,
      awayShots: 7,
      homeShotsOnTarget: 6,
      awayShotsOnTarget: 3,
      homePassAccuracy: 86,
      awayPassAccuracy: 80,
      homeExpectedGoals: 1.9,
      awayExpectedGoals: 1.1,
    ),
    timeline: [
      const GtexMatchTimelineEvent(
        minute: 4,
        type: GtexPitchEventType.kickoff,
        title: 'Kick off',
        description: 'The game starts under GTEX broadcast lights.',
      ),
      const GtexMatchTimelineEvent(
        minute: 18,
        type: GtexPitchEventType.goal,
        title: 'Opening goal',
        description: 'Leo Vale finishes from the edge of the box.',
        playerName: 'Leo Vale',
      ),
      const GtexMatchTimelineEvent(
        minute: 42,
        type: GtexPitchEventType.save,
        title: 'Huge save',
        description: 'Ayo King keeps the lead alive.',
        playerName: 'Ayo King',
      ),
      const GtexMatchTimelineEvent(
        minute: 54,
        type: GtexPitchEventType.goal,
        title: 'Equaliser — Accra Voltage',
        description: 'S. Imani taps in after a fast transition.',
        playerName: 'S. Imani',
      ),
      if (minute > 70)
        const GtexMatchTimelineEvent(
          minute: 71,
          type: GtexPitchEventType.goal,
          title: 'Regen magic',
          description: 'Leo Vale scores again after a disguised pass.',
          playerName: 'Leo Vale',
        ),
      if (minute > 76)
        const GtexMatchTimelineEvent(
          minute: 77,
          type: GtexPitchEventType.tacticalChange,
          title: 'Tactical switch',
          description: 'Lagos Crown drops into a compact 4-4-1-1.',
        ),
    ],
    highlights: const [
      GtexMatchHighlight(
        minute: 18,
        title: 'Opening goal',
        summary: 'A clean strike from Leo Vale gives Lagos Crown control.',
        importance: 5,
      ),
      GtexMatchHighlight(
        minute: 42,
        title: 'Keeper moment',
        summary: 'Ayo King makes a reflex stop from close range.',
        importance: 4,
      ),
      GtexMatchHighlight(
        minute: 71,
        title: 'Regen spotlight',
        summary: 'The regen striker completes a decisive brace.',
        importance: 5,
      ),
    ],
  );
}

List<GtexPitchPlayer> _pitchPlayers(
  List<GtexLineupPlayer> home,
  List<GtexLineupPlayer> away,
  int minute,
) {
  const homeShape = <List<double>>[
    [0.08, 0.50],
    [0.25, 0.18],
    [0.22, 0.38],
    [0.22, 0.62],
    [0.25, 0.82],
    [0.42, 0.35],
    [0.42, 0.65],
    [0.58, 0.50],
    [0.68, 0.22],
    [0.74, 0.50],
    [0.68, 0.78],
  ];
  const awayShape = <List<double>>[
    [0.92, 0.50],
    [0.75, 0.82],
    [0.78, 0.62],
    [0.78, 0.38],
    [0.75, 0.18],
    [0.60, 0.35],
    [0.56, 0.55],
    [0.60, 0.72],
    [0.38, 0.78],
    [0.32, 0.50],
    [0.38, 0.22],
  ];
  return [
    for (var i = 0; i < home.length; i++)
      GtexPitchPlayer(
        playerId: home[i].id,
        teamId: 'club-home',
        name: home[i].name,
        shirtNumber: home[i].shirtNumber,
        x: homeShape[i][0],
        y: homeShape[i][1],
        isHome: true,
        hasBall: minute.isEven && i == 7,
      ),
    for (var i = 0; i < away.length; i++)
      GtexPitchPlayer(
        playerId: away[i].id,
        teamId: 'club-away',
        name: away[i].name,
        shirtNumber: away[i].shirtNumber,
        x: awayShape[i][0],
        y: awayShape[i][1],
        isHome: false,
        hasBall: minute.isOdd && i == 8,
      ),
  ];
}
