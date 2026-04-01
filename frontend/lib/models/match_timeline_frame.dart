import 'package:gte_frontend/data/gte_models.dart';

const Object _matchTimelineUnset = Object();

enum MatchViewerPhase { kickoff, openPlay, setPiece, halftime, fulltime }

enum MatchViewerSide { home, away }

enum MatchViewerPlayerState {
  idle,
  moving,
  pressing,
  attacking,
  defending,
  sentOff,
}

enum MatchPlayerAnimationState {
  idle,
  jog,
  run,
  sprint,
  control,
  pass,
  shoot,
  tackle,
  intercept,
  recover,
}

enum MatchPlayerLine { goalkeeper, defense, midfield, attack }

enum MatchViewerRole { goalkeeper, defender, midfielder, forward }

enum MatchPossessionPhase {
  restart,
  control,
  buildUp,
  attack,
  recovery,
  stoppage,
}

enum MatchTimelineInjectionType {
  goal,
  offside,
  foul,
  save,
  miss,
  card,
  substitution,
  halftime,
  fulltime,
  neutral,
}

enum MatchPlaybackStage { pre, event, hold, review, decision, post, reset }

enum MatchCameraPreset {
  broadcast,
  attackPush,
  boxZoom,
  goalCelebration,
  assistantFlag,
  varReplay,
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

MatchPlayerAnimationState matchPlayerAnimationStateFromString(String value) {
  switch (value.trim().toLowerCase()) {
    case 'jog':
      return MatchPlayerAnimationState.jog;
    case 'run':
      return MatchPlayerAnimationState.run;
    case 'sprint':
      return MatchPlayerAnimationState.sprint;
    case 'control':
      return MatchPlayerAnimationState.control;
    case 'pass':
      return MatchPlayerAnimationState.pass;
    case 'shoot':
      return MatchPlayerAnimationState.shoot;
    case 'tackle':
      return MatchPlayerAnimationState.tackle;
    case 'intercept':
      return MatchPlayerAnimationState.intercept;
    case 'recover':
      return MatchPlayerAnimationState.recover;
    default:
      return MatchPlayerAnimationState.idle;
  }
}

extension MatchPlayerAnimationStateX on MatchPlayerAnimationState {
  String get label => switch (this) {
    MatchPlayerAnimationState.idle => 'Idle',
    MatchPlayerAnimationState.jog => 'Jog',
    MatchPlayerAnimationState.run => 'Run',
    MatchPlayerAnimationState.sprint => 'Sprint',
    MatchPlayerAnimationState.control => 'Control',
    MatchPlayerAnimationState.pass => 'Pass',
    MatchPlayerAnimationState.shoot => 'Shoot',
    MatchPlayerAnimationState.tackle => 'Tackle',
    MatchPlayerAnimationState.intercept => 'Intercept',
    MatchPlayerAnimationState.recover => 'Recover',
  };
}

MatchPlayerLine matchPlayerLineFromString(String value) {
  switch (value.trim().toLowerCase()) {
    case 'goalkeeper':
      return MatchPlayerLine.goalkeeper;
    case 'defense':
    case 'defender':
      return MatchPlayerLine.defense;
    case 'attack':
      return MatchPlayerLine.attack;
    default:
      return MatchPlayerLine.midfield;
  }
}

MatchViewerRole matchViewerRoleFromString(String value) {
  switch (value.trim().toLowerCase()) {
    case 'gk':
    case 'goalkeeper':
      return MatchViewerRole.goalkeeper;
    case 'df':
    case 'defender':
      return MatchViewerRole.defender;
    case 'fw':
    case 'forward':
      return MatchViewerRole.forward;
    default:
      return MatchViewerRole.midfielder;
  }
}

MatchPossessionPhase matchPossessionPhaseFromString(String value) {
  switch (value.trim().toLowerCase()) {
    case 'restart':
      return MatchPossessionPhase.restart;
    case 'build_up':
    case 'build-up':
    case 'build up':
    case 'buildupp':
    case 'buildup':
      return MatchPossessionPhase.buildUp;
    case 'attack':
      return MatchPossessionPhase.attack;
    case 'recovery':
      return MatchPossessionPhase.recovery;
    case 'stoppage':
      return MatchPossessionPhase.stoppage;
    default:
      return MatchPossessionPhase.control;
  }
}

MatchTimelineInjectionType matchTimelineInjectionTypeFromString(String value) {
  switch (value.trim().toLowerCase()) {
    case 'goal':
      return MatchTimelineInjectionType.goal;
    case 'offside':
      return MatchTimelineInjectionType.offside;
    case 'foul':
    case 'tactical_foul':
      return MatchTimelineInjectionType.foul;
    case 'save':
      return MatchTimelineInjectionType.save;
    case 'miss':
      return MatchTimelineInjectionType.miss;
    case 'card':
    case 'red_card':
    case 'yellow_card':
      return MatchTimelineInjectionType.card;
    case 'substitution':
      return MatchTimelineInjectionType.substitution;
    case 'halftime':
      return MatchTimelineInjectionType.halftime;
    case 'fulltime':
      return MatchTimelineInjectionType.fulltime;
    default:
      return MatchTimelineInjectionType.neutral;
  }
}

MatchPlaybackStage matchPlaybackStageFromString(String value) {
  switch (value.trim().toLowerCase()) {
    case 'pre':
      return MatchPlaybackStage.pre;
    case 'hold':
      return MatchPlaybackStage.hold;
    case 'review':
      return MatchPlaybackStage.review;
    case 'decision':
      return MatchPlaybackStage.decision;
    case 'post':
      return MatchPlaybackStage.post;
    case 'reset':
      return MatchPlaybackStage.reset;
    default:
      return MatchPlaybackStage.event;
  }
}

MatchCameraPreset matchCameraPresetFromString(String value) {
  switch (value.trim().toLowerCase()) {
    case 'attack_push':
      return MatchCameraPreset.attackPush;
    case 'box_zoom':
      return MatchCameraPreset.boxZoom;
    case 'goal_celebration':
      return MatchCameraPreset.goalCelebration;
    case 'assistant_flag':
      return MatchCameraPreset.assistantFlag;
    case 'var_replay':
      return MatchCameraPreset.varReplay;
    default:
      return MatchCameraPreset.broadcast;
  }
}

class MatchViewerPoint {
  const MatchViewerPoint({required this.x, required this.y});

  final double x;
  final double y;

  factory MatchViewerPoint.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'pitch point');
    return MatchViewerPoint(
      x: GteJson.number(json, <String>['x']),
      y: GteJson.number(json, <String>['y']),
    );
  }

  MatchViewerPoint copyWith({double? x, double? y}) {
    return MatchViewerPoint(x: x ?? this.x, y: y ?? this.y);
  }

  static MatchViewerPoint lerp(
    MatchViewerPoint left,
    MatchViewerPoint right,
    double t,
  ) {
    final double resolvedT = _clampUnit(t);
    return MatchViewerPoint(
      x: left.x + ((right.x - left.x) * resolvedT),
      y: left.y + ((right.y - left.y) * resolvedT),
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
    this.animationState = MatchPlayerAnimationState.idle,
    this.speedRatio = 0,
    this.blendFactor = 0.2,
    this.staminaPct = 100,
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
  final MatchPlayerAnimationState animationState;
  final double speedRatio;
  final double blendFactor;
  final int staminaPct;

  bool get isGoalkeeper => role == MatchViewerRole.goalkeeper;

  factory MatchViewerPlayerFrame.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'match viewer player frame',
    );
    return MatchViewerPlayerFrame(
      playerId: GteJson.string(json, <String>['player_id', 'playerId']),
      teamId: GteJson.string(json, <String>['team_id', 'teamId']),
      side: matchViewerSideFromString(GteJson.string(json, <String>['side'])),
      shirtNumber: GteJson.integerOrNull(json, <String>[
        'shirt_number',
        'shirtNumber',
      ]),
      label: GteJson.string(json, <String>['label'], fallback: '?'),
      role: matchViewerRoleFromString(GteJson.string(json, <String>['role'])),
      line: matchPlayerLineFromString(
        GteJson.string(json, <String>['line'], fallback: 'midfield'),
      ),
      state: matchViewerPlayerStateFromString(
        GteJson.string(json, <String>['state'], fallback: 'idle'),
      ),
      active: GteJson.boolean(json, <String>['active'], fallback: true),
      highlighted: GteJson.boolean(json, <String>[
        'highlighted',
      ], fallback: false),
      position: MatchViewerPoint.fromJson(
        GteJson.value(json, <String>['position']),
      ),
      anchorPosition: MatchViewerPoint.fromJson(
        GteJson.value(json, <String>['anchor_position', 'anchorPosition']),
      ),
      animationState: matchPlayerAnimationStateFromString(
        GteJson.string(json, <String>[
          'animation_state',
          'animationState',
        ], fallback: 'idle'),
      ),
      speedRatio:
          GteJson.number(json, <String>[
            'speed_ratio',
            'speedRatio',
          ], fallback: 0).toDouble(),
      blendFactor:
          GteJson.number(json, <String>[
            'blend_factor',
            'blendFactor',
          ], fallback: 0.2).toDouble(),
      staminaPct: GteJson.integer(json, <String>[
        'stamina_pct',
        'staminaPct',
      ], fallback: 100),
    );
  }

  MatchViewerPlayerFrame copyWith({
    MatchViewerSide? side,
    int? shirtNumber,
    String? label,
    MatchViewerRole? role,
    MatchPlayerLine? line,
    MatchViewerPlayerState? state,
    bool? active,
    bool? highlighted,
    MatchViewerPoint? position,
    MatchViewerPoint? anchorPosition,
    MatchPlayerAnimationState? animationState,
    double? speedRatio,
    double? blendFactor,
    int? staminaPct,
  }) {
    return MatchViewerPlayerFrame(
      playerId: playerId,
      teamId: teamId,
      side: side ?? this.side,
      shirtNumber: shirtNumber ?? this.shirtNumber,
      label: label ?? this.label,
      role: role ?? this.role,
      line: line ?? this.line,
      state: state ?? this.state,
      active: active ?? this.active,
      highlighted: highlighted ?? this.highlighted,
      position: position ?? this.position,
      anchorPosition: anchorPosition ?? this.anchorPosition,
      animationState: animationState ?? this.animationState,
      speedRatio: speedRatio ?? this.speedRatio,
      blendFactor: blendFactor ?? this.blendFactor,
      staminaPct: staminaPct ?? this.staminaPct,
    );
  }
}

class MatchViewerBallFrame {
  const MatchViewerBallFrame({
    required this.position,
    required this.state,
    this.ownerPlayerId,
    this.elevation = 0,
  });

  final MatchViewerPoint position;
  final String? ownerPlayerId;
  final String state;
  final double elevation;

  factory MatchViewerBallFrame.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'match viewer ball frame',
    );
    return MatchViewerBallFrame(
      position: MatchViewerPoint.fromJson(
        GteJson.value(json, <String>['position']),
      ),
      ownerPlayerId: GteJson.stringOrNull(json, <String>[
        'owner_player_id',
        'ownerPlayerId',
      ]),
      state: GteJson.string(json, <String>['state'], fallback: 'rolling'),
      elevation:
          GteJson.number(json, <String>['elevation'], fallback: 0).toDouble(),
    );
  }

  MatchViewerBallFrame copyWith({
    MatchViewerPoint? position,
    Object? ownerPlayerId = _matchTimelineUnset,
    String? state,
    double? elevation,
  }) {
    return MatchViewerBallFrame(
      position: position ?? this.position,
      ownerPlayerId:
          identical(ownerPlayerId, _matchTimelineUnset)
              ? this.ownerPlayerId
              : ownerPlayerId as String?,
      state: state ?? this.state,
      elevation: elevation ?? this.elevation,
    );
  }
}

class MatchTimelineInjection {
  const MatchTimelineInjection({
    required this.id,
    required this.type,
    required this.bannerText,
    required this.startSeconds,
    required this.peakSeconds,
    required this.endSeconds,
    this.teamId,
    this.highlightedPlayerIds = const <String>[],
  });

  final String id;
  final MatchTimelineInjectionType type;
  final String? teamId;
  final String bannerText;
  final double startSeconds;
  final double peakSeconds;
  final double endSeconds;
  final List<String> highlightedPlayerIds;

  factory MatchTimelineInjection.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'match timeline injection',
    );
    final List<Object?> rawHighlighted = GteJson.list(
      GteJson.value(json, <String>[
            'highlighted_player_ids',
            'highlightedPlayerIds',
          ]) ??
          const <Object?>[],
      label: 'timeline injection highlighted players',
    );
    return MatchTimelineInjection(
      id: GteJson.string(json, <String>['id']),
      type: matchTimelineInjectionTypeFromString(
        GteJson.string(json, <String>['type']),
      ),
      teamId: GteJson.stringOrNull(json, <String>['team_id', 'teamId']),
      bannerText: GteJson.string(json, <String>['banner_text', 'bannerText']),
      startSeconds: GteJson.number(json, <String>[
        'start_seconds',
        'startSeconds',
      ]),
      peakSeconds: GteJson.number(json, <String>[
        'peak_seconds',
        'peakSeconds',
      ]),
      endSeconds: GteJson.number(json, <String>['end_seconds', 'endSeconds']),
      highlightedPlayerIds: rawHighlighted
          .map((Object? item) => item?.toString() ?? '')
          .where((String item) => item.trim().isNotEmpty)
          .toList(growable: false),
    );
  }

  bool isActiveAt(double seconds) {
    return seconds >= startSeconds && seconds <= endSeconds;
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
    required this.possessionSide,
    required this.players,
    required this.ball,
    this.activeEventId,
    this.eventBanner,
    this.stage = MatchPlaybackStage.event,
    this.cameraPreset = MatchCameraPreset.broadcast,
    this.overlayText,
    this.pausePlayback = false,
    this.playbackRate = 1,
    this.flagAnimation = false,
    this.celebrationTeamId,
    this.possessionPhase,
    this.sequenceId,
    this.sequenceProgress,
    this.isSynthetic = false,
    this.injectedEvents = const <MatchTimelineInjection>[],
  });

  final String id;
  final double timeSeconds;
  final double clockMinute;
  final MatchViewerPhase phase;
  final int homeScore;
  final int awayScore;
  final bool homeAttacksRight;
  final MatchViewerSide possessionSide;
  final String? activeEventId;
  final String? eventBanner;
  final MatchPlaybackStage stage;
  final MatchCameraPreset cameraPreset;
  final String? overlayText;
  final bool pausePlayback;
  final double playbackRate;
  final bool flagAnimation;
  final String? celebrationTeamId;
  final MatchPossessionPhase? possessionPhase;
  final String? sequenceId;
  final double? sequenceProgress;
  final bool isSynthetic;
  final List<MatchTimelineInjection> injectedEvents;
  final List<MatchViewerPlayerFrame> players;
  final MatchViewerBallFrame ball;

  factory MatchTimelineFrame.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'match timeline frame',
    );
    final List<Object?> rawPlayers = GteJson.list(
      GteJson.value(json, <String>['players']) ?? const <Object?>[],
      label: 'match frame players',
    );
    final List<Object?> rawInjectedEvents = GteJson.list(
      GteJson.value(json, <String>['injected_events', 'injectedEvents']) ??
          const <Object?>[],
      label: 'match frame injected events',
    );
    final String? possessionPhaseValue = _stringOrNull(
      GteJson.value(json, <String>['possession_phase', 'possessionPhase']),
    );
    return MatchTimelineFrame(
      id: GteJson.string(json, <String>['frame_id', 'frameId']),
      timeSeconds: GteJson.number(json, <String>[
        'time_seconds',
        'timeSeconds',
      ]),
      clockMinute: GteJson.number(json, <String>[
        'clock_minute',
        'clockMinute',
      ]),
      phase: matchViewerPhaseFromString(
        GteJson.string(json, <String>['phase'], fallback: 'open_play'),
      ),
      homeScore: GteJson.integer(json, <String>['home_score', 'homeScore']),
      awayScore: GteJson.integer(json, <String>['away_score', 'awayScore']),
      homeAttacksRight: GteJson.boolean(json, <String>[
        'home_attacks_right',
        'homeAttacksRight',
      ], fallback: true),
      possessionSide: matchViewerSideFromString(
        GteJson.string(json, <String>[
          'possession_side',
          'possessionSide',
        ], fallback: 'home'),
      ),
      activeEventId: GteJson.stringOrNull(json, <String>[
        'active_event_id',
        'activeEventId',
      ]),
      eventBanner: GteJson.stringOrNull(json, <String>[
        'event_banner',
        'eventBanner',
      ]),
      stage: matchPlaybackStageFromString(
        GteJson.string(json, <String>['stage'], fallback: 'event'),
      ),
      cameraPreset: matchCameraPresetFromString(
        GteJson.string(json, <String>[
          'camera_preset',
          'cameraPreset',
        ], fallback: 'broadcast'),
      ),
      overlayText: GteJson.stringOrNull(json, <String>[
        'overlay_text',
        'overlayText',
      ]),
      pausePlayback: GteJson.boolean(json, <String>[
        'pause_playback',
        'pausePlayback',
      ], fallback: false),
      playbackRate: GteJson.number(json, <String>[
        'playback_rate',
        'playbackRate',
      ], fallback: 1),
      flagAnimation: GteJson.boolean(json, <String>[
        'flag_animation',
        'flagAnimation',
      ], fallback: false),
      celebrationTeamId: GteJson.stringOrNull(json, <String>[
        'celebration_team_id',
        'celebrationTeamId',
      ]),
      possessionPhase:
          possessionPhaseValue == null
              ? null
              : matchPossessionPhaseFromString(possessionPhaseValue),
      sequenceId: GteJson.stringOrNull(json, <String>[
        'sequence_id',
        'sequenceId',
      ]),
      sequenceProgress: _numberOrNull(
        GteJson.value(json, <String>['sequence_progress', 'sequenceProgress']),
      ),
      isSynthetic: GteJson.boolean(json, <String>[
        'is_synthetic',
        'isSynthetic',
      ], fallback: false),
      injectedEvents: rawInjectedEvents
          .map(MatchTimelineInjection.fromJson)
          .toList(growable: false),
      players: rawPlayers
          .map(MatchViewerPlayerFrame.fromJson)
          .toList(growable: false),
      ball: MatchViewerBallFrame.fromJson(
        GteJson.value(json, <String>['ball']),
      ),
    );
  }

  MatchTimelineFrame copyWith({
    String? id,
    double? timeSeconds,
    double? clockMinute,
    MatchViewerPhase? phase,
    int? homeScore,
    int? awayScore,
    bool? homeAttacksRight,
    MatchViewerSide? possessionSide,
    Object? activeEventId = _matchTimelineUnset,
    Object? eventBanner = _matchTimelineUnset,
    MatchPlaybackStage? stage,
    MatchCameraPreset? cameraPreset,
    Object? overlayText = _matchTimelineUnset,
    bool? pausePlayback,
    double? playbackRate,
    bool? flagAnimation,
    Object? celebrationTeamId = _matchTimelineUnset,
    Object? possessionPhase = _matchTimelineUnset,
    Object? sequenceId = _matchTimelineUnset,
    Object? sequenceProgress = _matchTimelineUnset,
    bool? isSynthetic,
    Object? injectedEvents = _matchTimelineUnset,
    List<MatchViewerPlayerFrame>? players,
    MatchViewerBallFrame? ball,
  }) {
    return MatchTimelineFrame(
      id: id ?? this.id,
      timeSeconds: timeSeconds ?? this.timeSeconds,
      clockMinute: clockMinute ?? this.clockMinute,
      phase: phase ?? this.phase,
      homeScore: homeScore ?? this.homeScore,
      awayScore: awayScore ?? this.awayScore,
      homeAttacksRight: homeAttacksRight ?? this.homeAttacksRight,
      possessionSide: possessionSide ?? this.possessionSide,
      activeEventId:
          identical(activeEventId, _matchTimelineUnset)
              ? this.activeEventId
              : activeEventId as String?,
      eventBanner:
          identical(eventBanner, _matchTimelineUnset)
              ? this.eventBanner
              : eventBanner as String?,
      stage: stage ?? this.stage,
      cameraPreset: cameraPreset ?? this.cameraPreset,
      overlayText:
          identical(overlayText, _matchTimelineUnset)
              ? this.overlayText
              : overlayText as String?,
      pausePlayback: pausePlayback ?? this.pausePlayback,
      playbackRate: playbackRate ?? this.playbackRate,
      flagAnimation: flagAnimation ?? this.flagAnimation,
      celebrationTeamId:
          identical(celebrationTeamId, _matchTimelineUnset)
              ? this.celebrationTeamId
              : celebrationTeamId as String?,
      possessionPhase:
          identical(possessionPhase, _matchTimelineUnset)
              ? this.possessionPhase
              : possessionPhase as MatchPossessionPhase?,
      sequenceId:
          identical(sequenceId, _matchTimelineUnset)
              ? this.sequenceId
              : sequenceId as String?,
      sequenceProgress:
          identical(sequenceProgress, _matchTimelineUnset)
              ? this.sequenceProgress
              : sequenceProgress as double?,
      isSynthetic: isSynthetic ?? this.isSynthetic,
      injectedEvents:
          identical(injectedEvents, _matchTimelineUnset)
              ? this.injectedEvents
              : injectedEvents as List<MatchTimelineInjection>,
      players: players ?? this.players,
      ball: ball ?? this.ball,
    );
  }

  MatchTimelineFrame interpolate(
    MatchTimelineFrame next,
    double t, {
    Duration? maxGap = const Duration(milliseconds: 2200),
    double changeoverT = 0.5,
    double ownershipSwitchT = 0.5,
  }) {
    final double resolvedT = _clampUnit(t);
    final double gapSeconds = next.timeSeconds - timeSeconds;
    final double resolvedChangeover = _clampUnit(changeoverT);
    final double resolvedOwnershipSwitch = _clampUnit(ownershipSwitchT);
    if (gapSeconds <= 0) {
      return resolvedT < resolvedChangeover ? this : next;
    }
    if (maxGap != null && gapSeconds > (maxGap.inMilliseconds / 1000.0)) {
      return resolvedT < resolvedChangeover ? this : next;
    }

    return MatchTimelineFrame(
      id: resolvedT < resolvedChangeover ? id : next.id,
      timeSeconds: timeSeconds + ((next.timeSeconds - timeSeconds) * resolvedT),
      clockMinute: clockMinute + ((next.clockMinute - clockMinute) * resolvedT),
      phase: resolvedT < resolvedChangeover ? phase : next.phase,
      homeScore: resolvedT < resolvedChangeover ? homeScore : next.homeScore,
      awayScore: resolvedT < resolvedChangeover ? awayScore : next.awayScore,
      homeAttacksRight:
          resolvedT < resolvedChangeover
              ? homeAttacksRight
              : next.homeAttacksRight,
      possessionSide:
          resolvedT < resolvedChangeover ? possessionSide : next.possessionSide,
      activeEventId:
          resolvedT < resolvedChangeover ? activeEventId : next.activeEventId,
      eventBanner:
          resolvedT < resolvedChangeover ? eventBanner : next.eventBanner,
      stage: resolvedT < resolvedChangeover ? stage : next.stage,
      cameraPreset:
          resolvedT < resolvedChangeover ? cameraPreset : next.cameraPreset,
      overlayText:
          resolvedT < resolvedChangeover ? overlayText : next.overlayText,
      pausePlayback:
          resolvedT < resolvedChangeover ? pausePlayback : next.pausePlayback,
      playbackRate:
          resolvedT < resolvedChangeover ? playbackRate : next.playbackRate,
      flagAnimation:
          resolvedT < resolvedChangeover ? flagAnimation : next.flagAnimation,
      celebrationTeamId:
          resolvedT < resolvedChangeover
              ? celebrationTeamId
              : next.celebrationTeamId,
      possessionPhase: _interpolatedPossessionPhase(
        next,
        resolvedT,
        resolvedChangeover,
      ),
      sequenceId: resolvedT < resolvedChangeover ? sequenceId : next.sequenceId,
      sequenceProgress: _interpolatedSequenceProgress(next, resolvedT),
      isSynthetic:
          isSynthetic || next.isSynthetic || (resolvedT > 0 && resolvedT < 1),
      injectedEvents: _mergedInjections(next, resolvedT, resolvedChangeover),
      players: _interpolatedPlayers(next, resolvedT, resolvedChangeover),
      ball: MatchViewerBallFrame(
        position: MatchViewerPoint.lerp(
          ball.position,
          next.ball.position,
          resolvedT,
        ),
        ownerPlayerId:
            resolvedT < resolvedOwnershipSwitch
                ? ball.ownerPlayerId
                : next.ball.ownerPlayerId,
        state:
            resolvedT < resolvedOwnershipSwitch ? ball.state : next.ball.state,
        elevation:
            ball.elevation +
            ((next.ball.elevation - ball.elevation) * resolvedT),
      ),
    );
  }

  MatchPossessionPhase? _interpolatedPossessionPhase(
    MatchTimelineFrame next,
    double t,
    double changeoverT,
  ) {
    if (possessionPhase == next.possessionPhase) {
      return possessionPhase;
    }
    return t < changeoverT ? possessionPhase : next.possessionPhase;
  }

  double? _interpolatedSequenceProgress(MatchTimelineFrame next, double t) {
    final double? start = sequenceProgress;
    final double? end = next.sequenceProgress;
    if (start != null && end != null) {
      return start + ((end - start) * t);
    }
    return t < 0.5 ? start : end;
  }

  List<MatchViewerPlayerFrame> _interpolatedPlayers(
    MatchTimelineFrame next,
    double t,
    double changeoverT,
  ) {
    final Map<String, MatchViewerPlayerFrame> leftById =
        <String, MatchViewerPlayerFrame>{
          for (final MatchViewerPlayerFrame player in players)
            player.playerId: player,
        };
    final Map<String, MatchViewerPlayerFrame> rightById =
        <String, MatchViewerPlayerFrame>{
          for (final MatchViewerPlayerFrame player in next.players)
            player.playerId: player,
        };
    final bool showRightOnlyPlayers = t >= changeoverT;
    final List<String> orderedIds = _orderedPlayerIds(players, next.players);
    return orderedIds
        .map((String playerId) {
          final MatchViewerPlayerFrame? left = leftById[playerId];
          final MatchViewerPlayerFrame? right = rightById[playerId];
          if (left != null && right != null) {
            return MatchViewerPlayerFrame(
              playerId: left.playerId,
              teamId: left.teamId,
              side: t < changeoverT ? left.side : right.side,
              shirtNumber:
                  t < changeoverT ? left.shirtNumber : right.shirtNumber,
              label: t < changeoverT ? left.label : right.label,
              role: t < changeoverT ? left.role : right.role,
              line: t < changeoverT ? left.line : right.line,
              state: t < changeoverT ? left.state : right.state,
              active: t < changeoverT ? left.active : right.active,
              highlighted:
                  t < changeoverT ? left.highlighted : right.highlighted,
              position: MatchViewerPoint.lerp(left.position, right.position, t),
              anchorPosition: MatchViewerPoint.lerp(
                left.anchorPosition,
                right.anchorPosition,
                t,
              ),
              animationState:
                  t < changeoverT ? left.animationState : right.animationState,
              speedRatio:
                  left.speedRatio + ((right.speedRatio - left.speedRatio) * t),
              blendFactor:
                  left.blendFactor +
                  ((right.blendFactor - left.blendFactor) * t),
              staminaPct:
                  (left.staminaPct + ((right.staminaPct - left.staminaPct) * t))
                      .round(),
            );
          }
          if (left != null) {
            return showRightOnlyPlayers
                ? left.copyWith(
                  active: false,
                  highlighted: false,
                  state:
                      left.state == MatchViewerPlayerState.sentOff
                          ? MatchViewerPlayerState.sentOff
                          : MatchViewerPlayerState.idle,
                )
                : left;
          }
          final MatchViewerPlayerFrame incoming = right!;
          return showRightOnlyPlayers
              ? incoming
              : incoming.copyWith(active: false, highlighted: false);
        })
        .toList(growable: false);
  }

  List<MatchTimelineInjection> _mergedInjections(
    MatchTimelineFrame next,
    double t,
    double changeoverT,
  ) {
    if (injectedEvents.isEmpty) {
      return next.injectedEvents;
    }
    if (next.injectedEvents.isEmpty) {
      return injectedEvents;
    }
    final List<MatchTimelineInjection> preferred =
        t < changeoverT ? injectedEvents : next.injectedEvents;
    final List<MatchTimelineInjection> alternate =
        t < changeoverT ? next.injectedEvents : injectedEvents;
    return _dedupeInjections(<MatchTimelineInjection>[
      ...preferred,
      ...alternate,
    ]);
  }
}

String? _stringOrNull(Object? value) {
  if (value == null) {
    return null;
  }
  final String text = value.toString().trim();
  return text.isEmpty ? null : text;
}

double? _numberOrNull(Object? value) {
  if (value == null) {
    return null;
  }
  if (value is num) {
    return value.toDouble();
  }
  return double.tryParse(value.toString());
}

double _clampUnit(double value) {
  return value.clamp(0.0, 1.0).toDouble();
}

List<String> _orderedPlayerIds(
  List<MatchViewerPlayerFrame> leftPlayers,
  List<MatchViewerPlayerFrame> rightPlayers,
) {
  final List<String> ordered = <String>[];
  final Set<String> seen = <String>{};
  for (final MatchViewerPlayerFrame player in leftPlayers) {
    if (seen.add(player.playerId)) {
      ordered.add(player.playerId);
    }
  }
  for (final MatchViewerPlayerFrame player in rightPlayers) {
    if (seen.add(player.playerId)) {
      ordered.add(player.playerId);
    }
  }
  return ordered;
}

List<MatchTimelineInjection> _dedupeInjections(
  List<MatchTimelineInjection> injections,
) {
  final Map<String, MatchTimelineInjection> unique =
      <String, MatchTimelineInjection>{};
  for (final MatchTimelineInjection injection in injections) {
    unique[injection.id] = injection;
  }
  return unique.values.toList(growable: false);
}
