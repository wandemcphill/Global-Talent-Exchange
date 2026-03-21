import 'package:flutter/material.dart';
import 'package:gte_frontend/data/gte_models.dart';

enum MatchViewerEventType {
  kickoff,
  goal,
  save,
  miss,
  offside,
  redCard,
  yellowCard,
  substitution,
  injury,
  halftime,
  fulltime,
  attack,
  setPiece,
  penalty,
  neutral,
}

MatchViewerEventType matchViewerEventTypeFromString(String value) {
  switch (value.trim().toLowerCase()) {
    case 'kickoff':
      return MatchViewerEventType.kickoff;
    case 'goal':
      return MatchViewerEventType.goal;
    case 'save':
      return MatchViewerEventType.save;
    case 'miss':
      return MatchViewerEventType.miss;
    case 'offside':
      return MatchViewerEventType.offside;
    case 'red_card':
      return MatchViewerEventType.redCard;
    case 'yellow_card':
      return MatchViewerEventType.yellowCard;
    case 'substitution':
      return MatchViewerEventType.substitution;
    case 'injury':
      return MatchViewerEventType.injury;
    case 'halftime':
      return MatchViewerEventType.halftime;
    case 'fulltime':
      return MatchViewerEventType.fulltime;
    case 'attack':
      return MatchViewerEventType.attack;
    case 'set_piece':
      return MatchViewerEventType.setPiece;
    case 'penalty':
      return MatchViewerEventType.penalty;
    default:
      return MatchViewerEventType.neutral;
  }
}

class MatchEvent {
  const MatchEvent({
    required this.id,
    required this.sequence,
    required this.type,
    required this.minute,
    required this.addedTime,
    required this.clockLabel,
    required this.timeSeconds,
    required this.homeScore,
    required this.awayScore,
    required this.bannerText,
    required this.commentary,
    required this.emphasisLevel,
    required this.highlightedPlayerIds,
    this.teamId,
    this.teamName,
    this.primaryPlayerId,
    this.primaryPlayerName,
    this.secondaryPlayerId,
    this.secondaryPlayerName,
  });

  final String id;
  final int sequence;
  final MatchViewerEventType type;
  final int minute;
  final int addedTime;
  final String clockLabel;
  final double timeSeconds;
  final String? teamId;
  final String? teamName;
  final String? primaryPlayerId;
  final String? primaryPlayerName;
  final String? secondaryPlayerId;
  final String? secondaryPlayerName;
  final int homeScore;
  final int awayScore;
  final String bannerText;
  final String commentary;
  final int emphasisLevel;
  final List<String> highlightedPlayerIds;

  bool get isMajor =>
      type == MatchViewerEventType.goal ||
      type == MatchViewerEventType.save ||
      type == MatchViewerEventType.miss ||
      type == MatchViewerEventType.redCard ||
      type == MatchViewerEventType.offside;

  IconData get icon {
    switch (type) {
      case MatchViewerEventType.goal:
        return Icons.sports_soccer;
      case MatchViewerEventType.save:
        return Icons.back_hand_outlined;
      case MatchViewerEventType.miss:
        return Icons.close_rounded;
      case MatchViewerEventType.offside:
        return Icons.flag_outlined;
      case MatchViewerEventType.redCard:
        return Icons.crop_portrait;
      case MatchViewerEventType.yellowCard:
        return Icons.rectangle_outlined;
      case MatchViewerEventType.substitution:
        return Icons.swap_horiz;
      case MatchViewerEventType.injury:
        return Icons.healing_outlined;
      case MatchViewerEventType.halftime:
        return Icons.pause_circle_outline;
      case MatchViewerEventType.fulltime:
        return Icons.stop_circle_outlined;
      case MatchViewerEventType.penalty:
        return Icons.adjust_outlined;
      case MatchViewerEventType.setPiece:
        return Icons.radio_button_checked_outlined;
      case MatchViewerEventType.kickoff:
        return Icons.play_arrow_outlined;
      case MatchViewerEventType.attack:
        return Icons.bolt_outlined;
      case MatchViewerEventType.neutral:
        return Icons.timeline_outlined;
    }
  }

  factory MatchEvent.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'match event');
    final List<Object?> rawHighlighted = GteJson.list(
      GteJson.value(json,
              <String>['highlighted_player_ids', 'highlightedPlayerIds']) ??
          const <Object?>[],
      label: 'highlighted player ids',
    );
    return MatchEvent(
      id: GteJson.string(json, <String>['event_id', 'eventId']),
      sequence: GteJson.integer(json, <String>['sequence']),
      type: matchViewerEventTypeFromString(
        GteJson.string(json, <String>['event_type', 'eventType']),
      ),
      minute: GteJson.integer(json, <String>['minute']),
      addedTime: GteJson.integer(
        json,
        <String>['added_time', 'addedTime'],
      ),
      clockLabel: GteJson.string(json, <String>['clock_label', 'clockLabel']),
      timeSeconds: GteJson.number(
        json,
        <String>['time_seconds', 'timeSeconds'],
      ),
      teamId: GteJson.stringOrNull(json, <String>['team_id', 'teamId']),
      teamName: GteJson.stringOrNull(json, <String>['team_name', 'teamName']),
      primaryPlayerId: GteJson.stringOrNull(
          json, <String>['primary_player_id', 'primaryPlayerId']),
      primaryPlayerName: GteJson.stringOrNull(
          json, <String>['primary_player_name', 'primaryPlayerName']),
      secondaryPlayerId: GteJson.stringOrNull(
          json, <String>['secondary_player_id', 'secondaryPlayerId']),
      secondaryPlayerName: GteJson.stringOrNull(
          json, <String>['secondary_player_name', 'secondaryPlayerName']),
      homeScore: GteJson.integer(json, <String>['home_score', 'homeScore']),
      awayScore: GteJson.integer(json, <String>['away_score', 'awayScore']),
      bannerText: GteJson.string(json, <String>['banner_text', 'bannerText']),
      commentary: GteJson.string(
        json,
        <String>['commentary'],
        fallback: '',
      ),
      emphasisLevel: GteJson.integer(
        json,
        <String>['emphasis_level', 'emphasisLevel'],
        fallback: 1,
      ),
      highlightedPlayerIds: rawHighlighted
          .map((Object? value) => value.toString())
          .where((String value) => value.trim().isNotEmpty)
          .toList(growable: false),
    );
  }
}
