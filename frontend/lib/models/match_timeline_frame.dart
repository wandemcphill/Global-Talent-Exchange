import 'package:gte_frontend/data/gte_models.dart';

enum MatchViewerPhase {
  kickoff,
  openPlay,
  setPiece,
  halftime,
  fulltime,
}

enum MatchViewerSide {
  home,
  away,
}

enum MatchViewerPlayerState {
  idle,
  moving,
  pressing,
  attacking,
  defending,
  sentOff,
}

enum MatchPlayerLine {
  goalkeeper,
  defense,
  midfield,
  attack,
}

enum MatchViewerRole {
  goalkeeper,
  defender,
  midfielder,
  forward,
}

MatchViewerPhase matchViewerPhaseFromString(String value) {
  switch (value.trim().toLowerCase()) {
    case 'kickoff':
      return MatchViewerPhase.kickoff;
    case 'set_piece':
      return MatchViewerPhase.setPiece;
    case 'halftime':
      return MatchViewerPhase.halftime;
    case 'fulltime':
      return MatchViewerPhase.fulltime;
    default:
      return MatchViewerPhase.openPlay;
  }
}

MatchViewerSide matchViewerSideFromString(String value) {
  return value.trim().toLowerCase() == 'away'
      ? MatchViewerSide.away
      : MatchViewerSide.home;
}

MatchViewerPlayerState matchViewerPlayerStateFromString(String value) {
  switch (value.trim().toLowerCase()) {
    case 'moving':
      return MatchViewerPlayerState.moving;
    case 'pressing':
      return MatchViewerPlayerState.pressing;
    case 'attacking':
      return MatchViewerPlayerState.attacking;
    case 'defending':
      return MatchViewerPlayerState.defending;
    case 'sent_off':
      return MatchViewerPlayerState.sentOff;
    default:
      return MatchViewerPlayerState.idle;
  }
}

MatchPlayerLine matchPlayerLineFromString(String value) {
  switch (value.trim().toLowerCase()) {
    case 'goalkeeper':
      return MatchPlayerLine.goalkeeper;
    case 'defense':
      return MatchPlayerLine.defense;
    case 'attack':
      return MatchPlayerLine.attack;
    default:
      return MatchPlayerLine.midfield;
  }
}

MatchViewerRole matchViewerRoleFromString(String value) {
  switch (value.trim().toUpperCase()) {
    case 'GK':
      return MatchViewerRole.goalkeeper;
    case 'DF':
      return MatchViewerRole.defender;
    case 'FW':
      return MatchViewerRole.forward;
    default:
      return MatchViewerRole.midfielder;
  }
}

class MatchViewerPoint {
  const MatchViewerPoint({
    required this.x,
    required this.y,
  });

  final double x;
  final double y;

  factory MatchViewerPoint.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'pitch point');
    return MatchViewerPoint(
      x: GteJson.number(json, <String>['x']),
      y: GteJson.number(json, <String>['y']),
    );
  }

  static MatchViewerPoint lerp(
    MatchViewerPoint left,
    MatchViewerPoint right,
    double t,
  ) {
    return MatchViewerPoint(
      x: left.x + ((right.x - left.x) * t),
      y: left.y + ((right.y - left.y) * t),
    );
  }
}

class MatchViewerPlayerFrame {
  const MatchViewerPlayerFrame({
    required this.playerId,
    required this.teamId,
    required this.side,
    required this.label,
    required this.role,
    required this.line,
    required this.state,
    required this.active,
    required this.highlighted,
    required this.position,
    required this.anchorPosition,
    this.shirtNumber,
  });

  final String playerId;
  final String teamId;
  final MatchViewerSide side;
  final int? shirtNumber;
  final String label;
  final MatchViewerRole role;
  final MatchPlayerLine line;
  final MatchViewerPlayerState state;
  final bool active;
  final bool highlighted;
  final MatchViewerPoint position;
  final MatchViewerPoint anchorPosition;

  bool get isGoalkeeper => role == MatchViewerRole.goalkeeper;

  factory MatchViewerPlayerFrame.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'match viewer player frame');
    return MatchViewerPlayerFrame(
      playerId: GteJson.string(json, <String>['player_id', 'playerId']),
      teamId: GteJson.string(json, <String>['team_id', 'teamId']),
      side: matchViewerSideFromString(
        GteJson.string(json, <String>['side']),
      ),
      shirtNumber: GteJson.integerOrNull(
        json,
        <String>['shirt_number', 'shirtNumber'],
      ),
      label: GteJson.string(json, <String>['label'], fallback: '?'),
      role: matchViewerRoleFromString(
        GteJson.string(json, <String>['role']),
      ),
      line: matchPlayerLineFromString(
        GteJson.string(json, <String>['line'], fallback: 'midfield'),
      ),
      state: matchViewerPlayerStateFromString(
        GteJson.string(json, <String>['state'], fallback: 'idle'),
      ),
      active: GteJson.boolean(json, <String>['active'], fallback: true),
      highlighted: GteJson.boolean(
        json,
        <String>['highlighted'],
        fallback: false,
      ),
      position: MatchViewerPoint.fromJson(
        GteJson.value(json, <String>['position']),
      ),
      anchorPosition: MatchViewerPoint.fromJson(
        GteJson.value(json, <String>['anchor_position', 'anchorPosition']),
      ),
    );
  }

  MatchViewerPlayerFrame copyWith({
    MatchViewerPoint? position,
    MatchViewerPoint? anchorPosition,
  }) {
    return MatchViewerPlayerFrame(
      playerId: playerId,
      teamId: teamId,
      side: side,
      shirtNumber: shirtNumber,
      label: label,
      role: role,
      line: line,
      state: state,
      active: active,
      highlighted: highlighted,
      position: position ?? this.position,
      anchorPosition: anchorPosition ?? this.anchorPosition,
    );
  }
}

class MatchViewerBallFrame {
  const MatchViewerBallFrame({
    required this.position,
    required this.state,
    this.ownerPlayerId,
  });

  final MatchViewerPoint position;
  final String? ownerPlayerId;
  final String state;

  factory MatchViewerBallFrame.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'match viewer ball frame');
    return MatchViewerBallFrame(
      position: MatchViewerPoint.fromJson(
        GteJson.value(json, <String>['position']),
      ),
      ownerPlayerId: GteJson.stringOrNull(
          json, <String>['owner_player_id', 'ownerPlayerId']),
      state: GteJson.string(json, <String>['state'], fallback: 'rolling'),
    );
  }
}

class MatchTimelineFrame {
  const MatchTimelineFrame({
    required this.id,
    required this.timeSeconds,
    required this.clockMinute,
    required this.phase,
    required this.homeScore,
    required this.awayScore,
    required this.homeAttacksRight,
    required this.players,
    required this.ball,
    this.activeEventId,
    this.eventBanner,
  });

  final String id;
  final double timeSeconds;
  final double clockMinute;
  final MatchViewerPhase phase;
  final int homeScore;
  final int awayScore;
  final bool homeAttacksRight;
  final String? activeEventId;
  final String? eventBanner;
  final List<MatchViewerPlayerFrame> players;
  final MatchViewerBallFrame ball;

  factory MatchTimelineFrame.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'match timeline frame');
    final List<Object?> rawPlayers = GteJson.list(
      GteJson.value(json, <String>['players']) ?? const <Object?>[],
      label: 'match frame players',
    );
    return MatchTimelineFrame(
      id: GteJson.string(json, <String>['frame_id', 'frameId']),
      timeSeconds:
          GteJson.number(json, <String>['time_seconds', 'timeSeconds']),
      clockMinute:
          GteJson.number(json, <String>['clock_minute', 'clockMinute']),
      phase: matchViewerPhaseFromString(
        GteJson.string(json, <String>['phase'], fallback: 'open_play'),
      ),
      homeScore: GteJson.integer(json, <String>['home_score', 'homeScore']),
      awayScore: GteJson.integer(json, <String>['away_score', 'awayScore']),
      homeAttacksRight: GteJson.boolean(
        json,
        <String>['home_attacks_right', 'homeAttacksRight'],
        fallback: true,
      ),
      activeEventId: GteJson.stringOrNull(
          json, <String>['active_event_id', 'activeEventId']),
      eventBanner:
          GteJson.stringOrNull(json, <String>['event_banner', 'eventBanner']),
      players: rawPlayers
          .map(MatchViewerPlayerFrame.fromJson)
          .toList(growable: false),
      ball: MatchViewerBallFrame.fromJson(
        GteJson.value(json, <String>['ball']),
      ),
    );
  }

  MatchTimelineFrame interpolate(
    MatchTimelineFrame next,
    double t,
  ) {
    if (players.length != next.players.length) {
      return this;
    }
    final List<MatchViewerPlayerFrame> interpolatedPlayers =
        <MatchViewerPlayerFrame>[];
    for (int index = 0; index < players.length; index += 1) {
      final MatchViewerPlayerFrame current = players[index];
      final MatchViewerPlayerFrame target = next.players[index];
      if (current.playerId != target.playerId) {
        return this;
      }
      interpolatedPlayers.add(
        current.copyWith(
          position: MatchViewerPoint.lerp(current.position, target.position, t),
          anchorPosition: MatchViewerPoint.lerp(
            current.anchorPosition,
            target.anchorPosition,
            t,
          ),
        ),
      );
    }
    return MatchTimelineFrame(
      id: id,
      timeSeconds: timeSeconds + ((next.timeSeconds - timeSeconds) * t),
      clockMinute: clockMinute + ((next.clockMinute - clockMinute) * t),
      phase: phase,
      homeScore: homeScore,
      awayScore: awayScore,
      homeAttacksRight: homeAttacksRight,
      activeEventId: activeEventId,
      eventBanner: eventBanner,
      players: interpolatedPlayers,
      ball: MatchViewerBallFrame(
        position: MatchViewerPoint.lerp(ball.position, next.ball.position, t),
        ownerPlayerId: t < 0.5 ? ball.ownerPlayerId : next.ball.ownerPlayerId,
        state: t < 0.5 ? ball.state : next.ball.state,
      ),
    );
  }
}
