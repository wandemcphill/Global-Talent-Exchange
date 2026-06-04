import 'package:flutter/material.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';

enum MatchViewerEventType {
  kickoff,
  goal,
  save,
  miss,
  foul,
  offside,
  redCard,
  yellowCard,
  substitution,
  injury,
  halftime,
  fulltime,
  attack,
  pass,
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
    case 'foul':
    case 'tactical_foul':
      return MatchViewerEventType.foul;
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
    case 'pass':
      return MatchViewerEventType.pass;
    case 'set_piece':
      return MatchViewerEventType.setPiece;
    case 'penalty':
      return MatchViewerEventType.penalty;
    default:
      return MatchViewerEventType.neutral;
  }
}

class MatchEventPlayerPosition {
  const MatchEventPlayerPosition({
    required this.playerId,
    required this.position,
    this.playerName,
    this.teamId,
    this.side,
    this.shirtNumber,
    this.role,
    this.line,
  });

  final String playerId;
  final String? playerName;
  final String? teamId;
  final MatchViewerSide? side;
  final int? shirtNumber;
  final String? role;
  final String? line;
  final MatchViewerPoint position;

  factory MatchEventPlayerPosition.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'match event player position',
    );
    final Object? positionPayload = GteJson.value(json, <String>['position']);
    final MatchViewerPoint point =
        positionPayload == null
            ? MatchViewerPoint(
              x: GteJson.number(json, <String>['x']),
              y: GteJson.number(json, <String>['y']),
            )
            : MatchViewerPoint.fromJson(positionPayload);
    final String? side = GteJson.stringOrNull(json, <String>['side']);
    return MatchEventPlayerPosition(
      playerId: GteJson.string(json, <String>['player_id', 'playerId', 'id']),
      playerName: GteJson.stringOrNull(json, <String>[
        'player_name',
        'playerName',
        'name',
        'label',
      ]),
      teamId: GteJson.stringOrNull(json, <String>['team_id', 'teamId']),
      side: side == null ? null : matchViewerSideFromString(side),
      shirtNumber: GteJson.integerOrNull(json, <String>[
        'shirt_number',
        'shirtNumber',
        'number',
      ]),
      role: GteJson.stringOrNull(json, <String>['role']),
      line: GteJson.stringOrNull(json, <String>['line']),
      position: point,
    );
  }
}

class MatchEventBallTarget {
  const MatchEventBallTarget({
    required this.position,
    this.ownerPlayerId,
    this.state = 'rolling',
    this.elevation = 0,
  });

  final MatchViewerPoint position;
  final String? ownerPlayerId;
  final String state;
  final double elevation;

  factory MatchEventBallTarget.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'match event ball target',
    );
    final Object? positionPayload = GteJson.value(json, <String>['position']);
    final MatchViewerPoint point =
        positionPayload == null
            ? MatchViewerPoint(
              x: GteJson.number(json, <String>['x']),
              y: GteJson.number(json, <String>['y']),
            )
            : MatchViewerPoint.fromJson(positionPayload);
    return MatchEventBallTarget(
      position: point,
      ownerPlayerId: GteJson.stringOrNull(json, <String>[
        'owner_player_id',
        'ownerPlayerId',
      ]),
      state: GteJson.string(json, <String>['state'], fallback: 'rolling'),
      elevation:
          GteJson.number(json, <String>[
            'elevation',
            'height',
          ], fallback: 0).toDouble(),
    );
  }

  MatchViewerBallFrame toFrame() {
    return MatchViewerBallFrame(
      position: position,
      ownerPlayerId: ownerPlayerId,
      state: state,
      elevation: elevation,
    );
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
    required this.flags,
    this.playbackProfile = 'neutral',
    this.missVariant,
    this.reviewable = false,
    this.reviewReason,
    this.reviewDecision,
    this.scoreCommit = 'immediate',
    this.durationMs = 500,
    this.positions = const <MatchEventPlayerPosition>[],
    this.ball,
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
  final List<String> flags;
  final String playbackProfile;
  final String? missVariant;
  final bool reviewable;
  final String? reviewReason;
  final String? reviewDecision;
  final String scoreCommit;
  final int durationMs;
  final List<MatchEventPlayerPosition> positions;
  final MatchEventBallTarget? ball;

  bool get isMajor =>
      type == MatchViewerEventType.goal ||
      type == MatchViewerEventType.save ||
      type == MatchViewerEventType.miss ||
      type == MatchViewerEventType.foul ||
      type == MatchViewerEventType.redCard ||
      type == MatchViewerEventType.offside;

  bool get isDataUnavailable => flags.contains('data_unavailable');

  bool get isPresentationOnly => flags.contains('presentation_only');

  bool get isReviewConfirmed => reviewDecision == 'confirmed';

  bool get isReviewDisallowed => reviewDecision == 'disallowed';

  bool get commitsScoreAfterReview => scoreCommit == 'after_review';

  IconData get icon {
    switch (type) {
      case MatchViewerEventType.goal:
        return Icons.sports_soccer;
      case MatchViewerEventType.save:
        return Icons.back_hand_outlined;
      case MatchViewerEventType.miss:
        return Icons.close_rounded;
      case MatchViewerEventType.foul:
        return Icons.warning_amber_outlined;
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
      case MatchViewerEventType.pass:
        return Icons.swap_horiz_rounded;
      case MatchViewerEventType.neutral:
        return Icons.timeline_outlined;
    }
  }

  factory MatchEvent.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'match event');
    final List<Object?> rawHighlighted = GteJson.list(
      GteJson.value(json, <String>[
            'highlighted_player_ids',
            'highlightedPlayerIds',
          ]) ??
          const <Object?>[],
      label: 'highlighted player ids',
    );
    final List<Object?> rawFlags = GteJson.list(
      GteJson.value(json, <String>['flags']) ?? const <Object?>[],
      label: 'match event flags',
    );
    final List<Object?> rawPositions = GteJson.list(
      GteJson.value(json, <String>['positions']) ?? const <Object?>[],
      label: 'match event positions',
    );
    final Object? rawBall = GteJson.value(json, <String>['ball']);
    return MatchEvent(
      id: GteJson.string(json, <String>['event_id', 'eventId']),
      sequence: GteJson.integer(json, <String>['sequence']),
      type: matchViewerEventTypeFromString(
        GteJson.string(json, <String>['event_type', 'eventType']),
      ),
      minute: GteJson.integer(json, <String>['minute']),
      addedTime: GteJson.integer(json, <String>['added_time', 'addedTime']),
      clockLabel: GteJson.string(json, <String>['clock_label', 'clockLabel']),
      timeSeconds: GteJson.number(json, <String>[
        'time_seconds',
        'timeSeconds',
      ]),
      teamId: GteJson.stringOrNull(json, <String>['team_id', 'teamId']),
      teamName: GteJson.stringOrNull(json, <String>['team_name', 'teamName']),
      primaryPlayerId: GteJson.stringOrNull(json, <String>[
        'primary_player_id',
        'primaryPlayerId',
      ]),
      primaryPlayerName: GteJson.stringOrNull(json, <String>[
        'primary_player_name',
        'primaryPlayerName',
      ]),
      secondaryPlayerId: GteJson.stringOrNull(json, <String>[
        'secondary_player_id',
        'secondaryPlayerId',
      ]),
      secondaryPlayerName: GteJson.stringOrNull(json, <String>[
        'secondary_player_name',
        'secondaryPlayerName',
      ]),
      homeScore: GteJson.integer(json, <String>['home_score', 'homeScore']),
      awayScore: GteJson.integer(json, <String>['away_score', 'awayScore']),
      bannerText: GteJson.string(json, <String>['banner_text', 'bannerText']),
      commentary: GteJson.string(json, <String>['commentary'], fallback: ''),
      emphasisLevel: GteJson.integer(json, <String>[
        'emphasis_level',
        'emphasisLevel',
      ], fallback: 1),
      playbackProfile: GteJson.string(json, <String>[
        'playback_profile',
        'playbackProfile',
      ], fallback: 'neutral'),
      missVariant: GteJson.stringOrNull(json, <String>[
        'miss_variant',
        'missVariant',
      ]),
      reviewable: GteJson.boolean(json, <String>[
        'reviewable',
      ], fallback: false),
      reviewReason: GteJson.stringOrNull(json, <String>[
        'review_reason',
        'reviewReason',
      ]),
      reviewDecision: GteJson.stringOrNull(json, <String>[
        'review_decision',
        'reviewDecision',
      ]),
      scoreCommit: GteJson.string(json, <String>[
        'score_commit',
        'scoreCommit',
      ], fallback: 'immediate'),
      durationMs: _clampAnimationDurationMs(
        GteJson.integer(json, <String>[
          'duration_ms',
          'durationMs',
        ], fallback: 500),
      ),
      positions: rawPositions
          .map(MatchEventPlayerPosition.fromJson)
          .toList(growable: false),
      ball: rawBall == null ? null : MatchEventBallTarget.fromJson(rawBall),
      highlightedPlayerIds: rawHighlighted
          .map((Object? value) => value.toString())
          .where((String value) => value.trim().isNotEmpty)
          .toList(growable: false),
      flags: rawFlags
          .map((Object? value) => value.toString())
          .where((String value) => value.trim().isNotEmpty)
          .toList(growable: false),
    );
  }

  MatchEvent copyWith({
    int? sequence,
    MatchViewerEventType? type,
    int? minute,
    int? addedTime,
    String? clockLabel,
    double? timeSeconds,
    Object? teamId = _matchEventUnset,
    Object? teamName = _matchEventUnset,
    Object? primaryPlayerId = _matchEventUnset,
    Object? primaryPlayerName = _matchEventUnset,
    Object? secondaryPlayerId = _matchEventUnset,
    Object? secondaryPlayerName = _matchEventUnset,
    int? homeScore,
    int? awayScore,
    String? bannerText,
    String? commentary,
    int? emphasisLevel,
    List<String>? highlightedPlayerIds,
    List<String>? flags,
    String? playbackProfile,
    Object? missVariant = _matchEventUnset,
    bool? reviewable,
    Object? reviewReason = _matchEventUnset,
    Object? reviewDecision = _matchEventUnset,
    String? scoreCommit,
    int? durationMs,
    List<MatchEventPlayerPosition>? positions,
    Object? ball = _matchEventUnset,
  }) {
    return MatchEvent(
      id: id,
      sequence: sequence ?? this.sequence,
      type: type ?? this.type,
      minute: minute ?? this.minute,
      addedTime: addedTime ?? this.addedTime,
      clockLabel: clockLabel ?? this.clockLabel,
      timeSeconds: timeSeconds ?? this.timeSeconds,
      teamId:
          identical(teamId, _matchEventUnset) ? this.teamId : teamId as String?,
      teamName:
          identical(teamName, _matchEventUnset)
              ? this.teamName
              : teamName as String?,
      primaryPlayerId:
          identical(primaryPlayerId, _matchEventUnset)
              ? this.primaryPlayerId
              : primaryPlayerId as String?,
      primaryPlayerName:
          identical(primaryPlayerName, _matchEventUnset)
              ? this.primaryPlayerName
              : primaryPlayerName as String?,
      secondaryPlayerId:
          identical(secondaryPlayerId, _matchEventUnset)
              ? this.secondaryPlayerId
              : secondaryPlayerId as String?,
      secondaryPlayerName:
          identical(secondaryPlayerName, _matchEventUnset)
              ? this.secondaryPlayerName
              : secondaryPlayerName as String?,
      homeScore: homeScore ?? this.homeScore,
      awayScore: awayScore ?? this.awayScore,
      bannerText: bannerText ?? this.bannerText,
      commentary: commentary ?? this.commentary,
      emphasisLevel: emphasisLevel ?? this.emphasisLevel,
      highlightedPlayerIds: highlightedPlayerIds ?? this.highlightedPlayerIds,
      flags: flags ?? this.flags,
      playbackProfile: playbackProfile ?? this.playbackProfile,
      missVariant:
          identical(missVariant, _matchEventUnset)
              ? this.missVariant
              : missVariant as String?,
      reviewable: reviewable ?? this.reviewable,
      reviewReason:
          identical(reviewReason, _matchEventUnset)
              ? this.reviewReason
              : reviewReason as String?,
      reviewDecision:
          identical(reviewDecision, _matchEventUnset)
              ? this.reviewDecision
              : reviewDecision as String?,
      scoreCommit: scoreCommit ?? this.scoreCommit,
      durationMs: durationMs ?? this.durationMs,
      positions: positions ?? this.positions,
      ball:
          identical(ball, _matchEventUnset)
              ? this.ball
              : ball as MatchEventBallTarget?,
    );
  }
}

const Object _matchEventUnset = Object();

int _clampAnimationDurationMs(int value) {
  return value.clamp(300, 800);
}
