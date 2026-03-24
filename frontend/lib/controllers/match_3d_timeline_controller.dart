import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:flutter/scheduler.dart';
import 'package:gte_frontend/models/ball_entity.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/models/player_entity.dart';

enum MatchPlaybackSpeedMode {
  slow,
  normal,
  fast,
}

class Match3dTimelineController extends ChangeNotifier {
  Match3dTimelineController({
    required TickerProvider vsync,
    required this.viewState,
    bool autoplay = true,
    MatchPlaybackSpeedMode initialSpeedMode = MatchPlaybackSpeedMode.normal,
  }) {
    _ticker = vsync.createTicker(_tick);
    _speeds = const <double>[0.5, 1.0, 2.0];
    _speedIndex = initialSpeedMode.index.clamp(0, _speeds.length - 1);
    _clockCompression = _ClockCompression.fromViewState(viewState);
    _segments = _buildSegments(viewState);
    if (autoplay) {
      play();
    }
  }

  static const double _maxSyntheticSegmentSeconds = 0.4;

  final MatchViewState viewState;
  late final Ticker _ticker;
  late List<double> _speeds;
  late final _ClockCompression _clockCompression;
  late final List<_TimelineSegment> _segments;

  Duration? _lastElapsed;
  double _positionSeconds = 0;
  int _speedIndex = 0;
  bool _isPlaying = false;
  bool _isAutoPaused = false;
  Duration? _autoPauseResumeAt;
  double? _autoPauseReleasePosition;
  double? _cachedPositionSeconds;
  _RuntimeSnapshot? _cachedSnapshot;
  _RuntimeSnapshot? _autoPausedSnapshot;

  bool get isPlaying => _isPlaying;

  bool get isAutoPaused => _isAutoPaused;

  double get speed => _speeds[_speedIndex];

  List<double> get speedOptions => List<double>.unmodifiable(_speeds);

  String get speedLabel {
    return speed == speed.roundToDouble()
        ? '${speed.toStringAsFixed(0)}x'
        : '${speed.toStringAsFixed(1)}x';
  }

  MatchPlaybackSpeedMode get speedMode => MatchPlaybackSpeedMode
      .values[_speedIndex.clamp(0, MatchPlaybackSpeedMode.values.length - 1)];

  double get effectivePlaybackRate =>
      isAutoPaused ? 0 : speed * displayFrame.playbackRate;

  double get positionSeconds => _positionSeconds;

  double get progress => viewState.durationSeconds <= 0
      ? 0
      : (_positionSeconds / viewState.durationSeconds).clamp(0, 1).toDouble();

  _RuntimeSnapshot get _activeSnapshot =>
      _autoPausedSnapshot ?? _runtimeSnapshot;

  MatchTimelineFrame get leftFrame => _activeSnapshot.segment.startFrame;

  MatchTimelineFrame get rightFrame => _activeSnapshot.segment.endFrame;

  double get interpolationT => _activeSnapshot.easedT;

  MatchTimelineFrame get currentFrame =>
      _activeSnapshot.easedT < _activeSnapshot.segment.changeoverT
          ? leftFrame
          : rightFrame;

  List<PlayerEntity> get playerEntities => _activeSnapshot.players;

  BallEntity get ballEntity => _activeSnapshot.ball;

  MatchTimelineFrame get displayFrame => _activeSnapshot.frame;

  double get clockMinute => displayFrame.clockMinute;

  List<MatchTimelineInjection> get activeInjections =>
      displayFrame.injectedEvents;

  String? get overlayText => displayFrame.overlayText;

  MatchEvent? get activeEvent {
    final MatchEvent? direct = viewState.eventById(displayFrame.activeEventId);
    if (direct != null) {
      return direct;
    }
    for (final MatchTimelineInjection injection in activeInjections) {
      final MatchEvent? event = viewState.eventById(injection.id);
      if (event != null) {
        return event;
      }
    }
    return _activeSnapshot.segment.event;
  }

  List<MatchEvent> get upcomingEvents {
    return viewState.events
        .where((MatchEvent event) => event.timeSeconds >= _positionSeconds - 2)
        .take(6)
        .toList(growable: false);
  }

  void play() {
    if (_isPlaying) {
      return;
    }
    _isPlaying = true;
    _lastElapsed = null;
    _ticker.start();
    if (displayFrame.pausePlayback) {
      _enterAutoPause(Duration.zero);
    }
    notifyListeners();
  }

  void pause() {
    if (!_isPlaying) {
      return;
    }
    _isPlaying = false;
    _ticker.stop();
    _clearAutoPause();
    _lastElapsed = null;
    notifyListeners();
  }

  void togglePlayPause() {
    if (_isPlaying) {
      pause();
    } else {
      play();
    }
  }

  void restart() {
    seekTo(0);
  }

  void seekTo(double seconds) {
    _clearAutoPause();
    _positionSeconds =
        seconds.clamp(0, viewState.durationSeconds.toDouble()).toDouble();
    _lastElapsed = null;
    _invalidateCache();
    if (_isPlaying && displayFrame.pausePlayback) {
      _enterAutoPause(Duration.zero);
    }
    notifyListeners();
  }

  void seekToSeconds(double seconds) {
    seekTo(seconds);
  }

  void seekToProgress(double progress) {
    seekTo(viewState.durationSeconds * progress.clamp(0, 1));
  }

  void setSpeedMode(MatchPlaybackSpeedMode mode) {
    final int nextIndex = mode.index.clamp(0, _speeds.length - 1);
    if (_speedIndex == nextIndex) {
      return;
    }
    _speedIndex = nextIndex;
    notifyListeners();
  }

  void cycleSpeed() {
    _speedIndex = (_speedIndex + 1) % _speeds.length;
    notifyListeners();
  }

  void setSpeed(double value) {
    final int nextIndex = _nearestSpeedIndex(value, _speeds);
    if (_speedIndex == nextIndex) {
      return;
    }
    _speedIndex = nextIndex;
    notifyListeners();
  }

  void updateSpeedOptions(List<double> speedOptions) {
    final List<double> normalized = speedOptions
        .where((double value) => value > 0)
        .map((double value) => value.toDouble())
        .toSet()
        .toList()
      ..sort();
    if (normalized.isEmpty || listEquals(normalized, _speeds)) {
      return;
    }
    final double currentSpeed = speed;
    _speeds = normalized;
    _speedIndex = _nearestSpeedIndex(currentSpeed, _speeds);
    notifyListeners();
  }

  void jumpToNextEvent() {
    for (final MatchEvent event in viewState.events) {
      if (event.timeSeconds > _positionSeconds + 0.1) {
        seekTo(event.timeSeconds);
        return;
      }
    }
    seekTo(viewState.durationSeconds.toDouble());
    pause();
  }

  MatchTimelineFrame frameAt(double seconds) {
    return _resolveRuntimeSnapshotAt(
      seconds.clamp(0, viewState.durationSeconds.toDouble()).toDouble(),
    ).frame;
  }

  @override
  void dispose() {
    _ticker.dispose();
    super.dispose();
  }

  static List<MatchViewerPoint> formationAnchorsFor({
    required String formation,
    required bool attacksRight,
  }) {
    final List<int> lines = switch (formation.trim()) {
      '4-2-3-1' => const <int>[4, 2, 3, 1],
      '4-4-2' => const <int>[4, 4, 2],
      '4-3-3' => const <int>[4, 3, 3],
      _ => const <int>[4, 3, 3],
    };
    final List<MatchViewerPoint> anchors = <MatchViewerPoint>[
      MatchViewerPoint(x: attacksRight ? 8 : 92, y: 50),
    ];
    final double denominator = math.max(1, lines.length - 1).toDouble();
    for (int lineIndex = 0; lineIndex < lines.length; lineIndex += 1) {
      final double rawX = 22 + ((60 / denominator) * lineIndex);
      final double x = attacksRight ? rawX : 100 - rawX;
      for (final double y in _lanePositions(lines[lineIndex])) {
        anchors.add(MatchViewerPoint(x: x, y: y));
      }
    }
    return anchors;
  }

  void _tick(Duration elapsed) {
    if (!_isPlaying) {
      return;
    }
    if (_isAutoPaused) {
      _lastElapsed = elapsed;
      final Duration? resumeAt = _autoPauseResumeAt;
      if (resumeAt != null && elapsed >= resumeAt) {
        _releaseAutoPause();
      }
      return;
    }
    final Duration previous = _lastElapsed ?? Duration.zero;
    _lastElapsed = elapsed;
    final double deltaSeconds =
        (elapsed - previous).inMicroseconds / Duration.microsecondsPerSecond;
    if (deltaSeconds <= 0) {
      return;
    }
    _positionSeconds += deltaSeconds * effectivePlaybackRate;
    if (_positionSeconds >= viewState.durationSeconds) {
      _positionSeconds = viewState.durationSeconds.toDouble();
      _invalidateCache();
      pause();
      return;
    }
    _invalidateCache();
    if (displayFrame.pausePlayback) {
      _enterAutoPause(elapsed);
      return;
    }
    notifyListeners();
  }

  void _invalidateCache() {
    _cachedPositionSeconds = null;
    _cachedSnapshot = null;
  }

  void _clearAutoPause() {
    _isAutoPaused = false;
    _autoPauseResumeAt = null;
    _autoPauseReleasePosition = null;
    _autoPausedSnapshot = null;
  }

  void _enterAutoPause(Duration elapsed) {
    if (_isAutoPaused) {
      return;
    }
    final _PauseCue? cue = _pauseCueAt(_positionSeconds);
    if (cue == null) {
      return;
    }
    _isAutoPaused = true;
    _autoPauseResumeAt = elapsed +
        Duration(
          microseconds:
              (cue.holdSeconds * Duration.microsecondsPerSecond).round(),
        );
    _autoPauseReleasePosition = cue.resumePosition;
    _autoPausedSnapshot = _runtimeSnapshot;
    notifyListeners();
  }

  void _releaseAutoPause() {
    final double releasePosition =
        (_autoPauseReleasePosition ?? (_positionSeconds + 0.05))
            .clamp(0, viewState.durationSeconds.toDouble())
            .toDouble();
    _clearAutoPause();
    _positionSeconds = releasePosition;
    _invalidateCache();
    notifyListeners();
  }

  _PauseCue? _pauseCueAt(double positionSeconds) {
    if (!displayFrame.pausePlayback) {
      return null;
    }
    MatchTimelineFrame? nextFrame;
    for (final MatchTimelineFrame frame in viewState.frames) {
      if (frame.timeSeconds > positionSeconds + 0.0001) {
        nextFrame = frame;
        break;
      }
    }
    final double holdSeconds = nextFrame == null
        ? 0.8
        : math.max(0.2, nextFrame.timeSeconds - positionSeconds).toDouble();
    final double resumePosition = nextFrame?.timeSeconds ??
        (positionSeconds + 0.05).clamp(0, viewState.durationSeconds.toDouble());
    return _PauseCue(
      holdSeconds: holdSeconds,
      resumePosition: resumePosition.toDouble(),
    );
  }

  _RuntimeSnapshot get _runtimeSnapshot {
    final double cachedPosition = _cachedPositionSeconds ?? double.nan;
    if (_cachedSnapshot != null &&
        (cachedPosition - _positionSeconds).abs() < 0.000001) {
      return _cachedSnapshot!;
    }
    final _RuntimeSnapshot snapshot =
        _resolveRuntimeSnapshotAt(_positionSeconds);
    _cachedPositionSeconds = _positionSeconds;
    _cachedSnapshot = snapshot;
    return snapshot;
  }

  _RuntimeSnapshot _resolveRuntimeSnapshotAt(double positionSeconds) {
    final _TimelineSegment segment = _segmentAt(positionSeconds);
    final double duration = segment.endTime - segment.startTime;
    final double linearT = duration <= 0
        ? 1
        : ((positionSeconds - segment.startTime) / duration)
            .clamp(0, 1)
            .toDouble();
    final double easedT = _applyEasing(segment.stage, linearT);
    final MatchTimelineFrame baseFrame = segment.startFrame.interpolate(
      segment.endFrame,
      easedT,
      maxGap: null,
      changeoverT: segment.changeoverT,
      ownershipSwitchT: segment.ownershipSwitchT,
    );
    final MatchTimelineFrame frame = _decorateDisplayFrame(
      frame: baseFrame,
      segment: segment,
      linearT: linearT,
      easedT: easedT,
    );
    return _snapshotFromFrame(
      frame: frame,
      segment: segment,
      easedT: easedT,
    );
  }

  _RuntimeSnapshot _snapshotFromFrame({
    required MatchTimelineFrame frame,
    required _TimelineSegment segment,
    required double easedT,
  }) {
    final MatchViewerSide possessionSide = frame.possessionSide;
    final List<PlayerEntity> players =
        frame.players.map((MatchViewerPlayerFrame player) {
      final MatchViewerPlayerFrame startPlayer =
          segment.startPlayers[player.playerId] ?? player;
      final MatchViewerPlayerFrame endPlayer =
          segment.endPlayers[player.playerId] ?? player;
      return PlayerEntity(
        playerId: player.playerId,
        teamId: player.teamId,
        side: player.side,
        role: player.role,
        line: player.line,
        label: player.label,
        shirtNumber: player.shirtNumber,
        active: player.active,
        baseState: player.state,
        runPattern: _runPatternForPlayer(
          player: player,
          possessionSide: possessionSide,
          ownerPlayerId: frame.ball.ownerPlayerId,
        ),
        anchor: player.anchorPosition,
        startPosition: startPlayer.position,
        targetPosition: endPlayer.position,
        currentPosition: player.position,
        hasPossession: frame.ball.ownerPlayerId == player.playerId,
        highlighted: player.highlighted ||
            segment.highlightedIds.contains(player.playerId),
      );
    }).toList(growable: false);
    return _RuntimeSnapshot(
      players: players,
      ball: BallEntity.fromFrame(frame.ball),
      frame: frame,
      segment: segment,
      easedT: easedT,
    );
  }

  MatchTimelineFrame _decorateDisplayFrame({
    required MatchTimelineFrame frame,
    required _TimelineSegment segment,
    required double linearT,
    required double easedT,
  }) {
    final List<MatchTimelineInjection> injections =
        _activeInjectionsAt(frame.timeSeconds);
    final MatchTimelineInjection? leadInjection =
        injections.isEmpty ? null : injections.first;
    final MatchEvent? leadEvent = viewState.eventById(leadInjection?.id);
    final String? ownerPlayerId = frame.ball.ownerPlayerId;
    return frame.copyWith(
      clockMinute: _clockCompression.resolve(
        rawClockMinute: frame.clockMinute,
        positionSeconds: frame.timeSeconds,
        phase: frame.phase,
      ),
      possessionSide: _playerSideForId(frame.players, ownerPlayerId) ??
          _sideForTeamId(leadEvent?.teamId) ??
          segment.possessionSide,
      activeEventId: leadEvent?.id ?? frame.activeEventId ?? segment.event?.id,
      eventBanner: leadInjection?.bannerText ??
          frame.eventBanner ??
          segment.event?.bannerText,
      overlayText: frame.overlayText ?? leadInjection?.bannerText,
      possessionPhase: _possessionPhaseForStage(segment.stage),
      sequenceId: segment.sequenceId,
      sequenceProgress: segment.sequenceEndTime <= segment.sequenceStartTime
          ? 1
          : ((frame.timeSeconds - segment.sequenceStartTime) /
                  (segment.sequenceEndTime - segment.sequenceStartTime))
              .clamp(0, 1)
              .toDouble(),
      isSynthetic: frame.isSynthetic || segment.synthetic,
      injectedEvents: injections,
      pausePlayback: frame.pausePlayback,
      playbackRate: frame.playbackRate,
      flagAnimation: frame.flagAnimation ||
          leadInjection?.type == MatchTimelineInjectionType.offside,
      celebrationTeamId: frame.celebrationTeamId ??
          (leadInjection?.type == MatchTimelineInjectionType.goal
              ? leadEvent?.teamId
              : null),
      stage: frame.stage,
      cameraPreset: frame.cameraPreset,
    );
  }

  _TimelineSegment _segmentAt(double positionSeconds) {
    if (_segments.isEmpty) {
      return _TimelineSegment.stationary(viewState.firstFrame);
    }
    int low = 0;
    int high = _segments.length - 1;
    while (low <= high) {
      final int mid = (low + high) ~/ 2;
      final _TimelineSegment segment = _segments[mid];
      if (positionSeconds < segment.startTime) {
        high = mid - 1;
        continue;
      }
      if (positionSeconds > segment.endTime) {
        low = mid + 1;
        continue;
      }
      return segment;
    }
    return low >= _segments.length ? _segments.last : _segments.first;
  }

  List<MatchTimelineInjection> _activeInjectionsAt(double positionSeconds) {
    final List<MatchTimelineInjection> active = viewState.events
        .map(_buildInjectionForEvent)
        .where(
          (MatchTimelineInjection injection) =>
              injection.isActiveAt(positionSeconds),
        )
        .toList(growable: false);
    if (active.length < 2) {
      return active;
    }
    final List<MatchTimelineInjection> ordered =
        List<MatchTimelineInjection>.of(active)
          ..sort((MatchTimelineInjection left, MatchTimelineInjection right) {
            final int priority = _injectionPriority(right.type)
                .compareTo(_injectionPriority(left.type));
            if (priority != 0) {
              return priority;
            }
            final double leftDistance =
                (positionSeconds - left.peakSeconds).abs();
            final double rightDistance =
                (positionSeconds - right.peakSeconds).abs();
            return leftDistance.compareTo(rightDistance);
          });
    return ordered;
  }

  MatchTimelineInjection _buildInjectionForEvent(MatchEvent event) {
    final _InjectionWindow window = _windowForEvent(event.type);
    final double peakSeconds = event.timeSeconds
        .clamp(0, viewState.durationSeconds.toDouble())
        .toDouble();
    final double startSeconds =
        (peakSeconds - window.leadSeconds).clamp(0, peakSeconds).toDouble();
    final double endSeconds = (peakSeconds + window.trailSeconds)
        .clamp(startSeconds, viewState.durationSeconds.toDouble())
        .toDouble();
    return MatchTimelineInjection(
      id: event.id,
      type: _injectionTypeForEvent(event.type),
      teamId: event.teamId,
      bannerText: event.bannerText,
      startSeconds: startSeconds,
      peakSeconds: peakSeconds,
      endSeconds: endSeconds,
      highlightedPlayerIds: event.highlightedPlayerIds,
    );
  }

  List<_TimelineSegment> _buildSegments(MatchViewState viewState) {
    final List<MatchTimelineFrame> frames = List<MatchTimelineFrame>.of(
      viewState.frames,
    )..sort(
        (MatchTimelineFrame left, MatchTimelineFrame right) =>
            left.timeSeconds.compareTo(right.timeSeconds),
      );
    if (frames.isEmpty) {
      return const <_TimelineSegment>[];
    }
    if (frames.length == 1) {
      return <_TimelineSegment>[_TimelineSegment.stationary(frames.first)];
    }

    final List<MatchEvent> events = List<MatchEvent>.of(viewState.events)
      ..sort(
        (MatchEvent left, MatchEvent right) =>
            left.timeSeconds.compareTo(right.timeSeconds),
      );
    final List<_SegmentSeed> seeds = <_SegmentSeed>[];
    int sequenceCounter = 0;
    String? currentSequenceId;
    MatchViewerSide? lastPossessionSide;

    for (int index = 0; index < frames.length - 1; index += 1) {
      final MatchTimelineFrame pairStart = frames[index];
      final MatchTimelineFrame pairEnd = frames[index + 1];
      final double gapSeconds =
          math.max(0, pairEnd.timeSeconds - pairStart.timeSeconds).toDouble();
      final int splitCount = math.max(
        1,
        (gapSeconds / _maxSyntheticSegmentSeconds).ceil(),
      );
      for (int part = 0; part < splitCount; part += 1) {
        final double startRatio = part / splitCount;
        final double endRatio = (part + 1) / splitCount;
        final MatchTimelineFrame segmentStart = part == 0
            ? pairStart
            : _virtualFrame(pairStart, pairEnd, startRatio);
        final MatchTimelineFrame segmentEnd = part == splitCount - 1
            ? pairEnd
            : _virtualFrame(pairStart, pairEnd, endRatio);
        final MatchEvent? event = _eventForWindow(
          events: events,
          startTime: segmentStart.timeSeconds,
          endTime: segmentEnd.timeSeconds,
          startFrame: segmentStart,
          endFrame: segmentEnd,
        );
        final MatchViewerSide possessionSide = _possessionSideForSegment(
          startFrame: segmentStart,
          endFrame: segmentEnd,
          event: event,
        );
        final _SegmentStage stage = _classifyStage(
          startFrame: segmentStart,
          endFrame: segmentEnd,
          event: event,
          possessionSide: possessionSide,
        );
        final bool startsNewSequence = seeds.isEmpty ||
            event != null ||
            stage == _SegmentStage.reset ||
            stage == _SegmentStage.hold ||
            lastPossessionSide != possessionSide;
        if (startsNewSequence) {
          sequenceCounter += 1;
          currentSequenceId = event?.id ?? 'sequence-$sequenceCounter';
        }
        seeds.add(
          _SegmentSeed(
            startFrame: segmentStart,
            endFrame: segmentEnd,
            startTime: segmentStart.timeSeconds,
            endTime: segmentEnd.timeSeconds,
            event: event,
            stage: stage,
            possessionSide: possessionSide,
            synthetic: splitCount > 1 ||
                segmentStart.isSynthetic ||
                segmentEnd.isSynthetic,
            sequenceId: currentSequenceId ?? 'sequence-$sequenceCounter',
          ),
        );
        lastPossessionSide = possessionSide;
      }
    }

    final Map<String, _SequenceWindow> sequenceWindows =
        <String, _SequenceWindow>{};
    for (final _SegmentSeed seed in seeds) {
      final _SequenceWindow? existing = sequenceWindows[seed.sequenceId];
      if (existing == null) {
        sequenceWindows[seed.sequenceId] = _SequenceWindow(
          startTime: seed.startTime,
          endTime: seed.endTime,
        );
      } else {
        sequenceWindows[seed.sequenceId] = _SequenceWindow(
          startTime: existing.startTime,
          endTime: seed.endTime,
        );
      }
    }

    return seeds.map((_SegmentSeed seed) {
      final _SequenceWindow window = sequenceWindows[seed.sequenceId]!;
      return _TimelineSegment(
        startFrame: seed.startFrame,
        endFrame: seed.endFrame,
        startPlayers: <String, MatchViewerPlayerFrame>{
          for (final MatchViewerPlayerFrame player in seed.startFrame.players)
            player.playerId: player,
        },
        endPlayers: <String, MatchViewerPlayerFrame>{
          for (final MatchViewerPlayerFrame player in seed.endFrame.players)
            player.playerId: player,
        },
        startTime: seed.startTime,
        endTime: seed.endTime,
        event: seed.event,
        stage: seed.stage,
        possessionSide: seed.possessionSide,
        changeoverT: _changeoverForStage(seed.stage),
        ownershipSwitchT: _ownershipSwitchForStage(seed.stage),
        sequenceId: seed.sequenceId,
        sequenceStartTime: window.startTime,
        sequenceEndTime: window.endTime,
        synthetic: seed.synthetic,
        highlightedIds: <String>{
          ...?seed.event?.highlightedPlayerIds,
        },
      );
    }).toList(growable: false);
  }

  MatchTimelineFrame _virtualFrame(
    MatchTimelineFrame start,
    MatchTimelineFrame end,
    double ratio,
  ) {
    final MatchTimelineFrame interpolated = start.interpolate(
      end,
      ratio,
      maxGap: null,
    );
    return interpolated.copyWith(
      id: '${start.id}~${end.id}@${(ratio * 1000).round()}',
      isSynthetic: true,
    );
  }

  MatchEvent? _eventForWindow({
    required List<MatchEvent> events,
    required double startTime,
    required double endTime,
    required MatchTimelineFrame startFrame,
    required MatchTimelineFrame endFrame,
  }) {
    for (final MatchEvent event in events) {
      if (event.timeSeconds < startTime - 0.0001) {
        continue;
      }
      if (event.timeSeconds > endTime + 0.0001) {
        break;
      }
      return event;
    }
    return viewState.eventById(endFrame.activeEventId) ??
        viewState.eventById(startFrame.activeEventId);
  }

  static _SegmentStage _classifyStage({
    required MatchTimelineFrame startFrame,
    required MatchTimelineFrame endFrame,
    required MatchEvent? event,
    required MatchViewerSide possessionSide,
  }) {
    if (endFrame.phase == MatchViewerPhase.halftime ||
        endFrame.phase == MatchViewerPhase.fulltime ||
        event?.type == MatchViewerEventType.halftime ||
        event?.type == MatchViewerEventType.fulltime) {
      return _SegmentStage.hold;
    }
    if (endFrame.phase == MatchViewerPhase.kickoff ||
        startFrame.phase == MatchViewerPhase.kickoff ||
        event?.type == MatchViewerEventType.kickoff) {
      return _SegmentStage.reset;
    }
    if (event != null) {
      switch (event.type) {
        case MatchViewerEventType.attack:
        case MatchViewerEventType.setPiece:
        case MatchViewerEventType.penalty:
          return _SegmentStage.buildUp;
        case MatchViewerEventType.goal:
        case MatchViewerEventType.save:
        case MatchViewerEventType.miss:
        case MatchViewerEventType.offside:
        case MatchViewerEventType.foul:
        case MatchViewerEventType.redCard:
        case MatchViewerEventType.yellowCard:
        case MatchViewerEventType.substitution:
        case MatchViewerEventType.injury:
          return _SegmentStage.event;
        case MatchViewerEventType.kickoff:
        case MatchViewerEventType.halftime:
        case MatchViewerEventType.fulltime:
        case MatchViewerEventType.neutral:
          break;
      }
    }
    if (startFrame.activeEventId != null &&
        startFrame.activeEventId == endFrame.activeEventId) {
      return _SegmentStage.postEvent;
    }
    final double attackDirection = possessionSide == MatchViewerSide.home
        ? (endFrame.homeAttacksRight ? 1 : -1)
        : (endFrame.homeAttacksRight ? -1 : 1);
    final double forwardProgress =
        (endFrame.ball.position.x - startFrame.ball.position.x) *
            attackDirection;
    if (forwardProgress >= 6) {
      return _SegmentStage.event;
    }
    if (forwardProgress >= 2) {
      return _SegmentStage.buildUp;
    }
    return _SegmentStage.openPlay;
  }

  static MatchViewerSide _possessionSideForSegment({
    required MatchTimelineFrame startFrame,
    required MatchTimelineFrame endFrame,
    required MatchEvent? event,
  }) {
    if (event?.teamId != null) {
      return event!.teamId == startFrame.players.first.teamId
          ? startFrame.players.first.side
          : endFrame.possessionSide;
    }
    return _playerSideForId(endFrame.players, endFrame.ball.ownerPlayerId) ??
        endFrame.possessionSide;
  }

  static MatchPossessionPhase _possessionPhaseForStage(_SegmentStage stage) {
    return switch (stage) {
      _SegmentStage.reset => MatchPossessionPhase.restart,
      _SegmentStage.buildUp => MatchPossessionPhase.buildUp,
      _SegmentStage.event => MatchPossessionPhase.attack,
      _SegmentStage.postEvent => MatchPossessionPhase.recovery,
      _SegmentStage.openPlay => MatchPossessionPhase.control,
      _SegmentStage.hold => MatchPossessionPhase.stoppage,
    };
  }

  static MatchPlaybackStage _playbackStageForSegment(_SegmentStage stage) {
    return switch (stage) {
      _SegmentStage.reset => MatchPlaybackStage.reset,
      _SegmentStage.buildUp => MatchPlaybackStage.pre,
      _SegmentStage.event => MatchPlaybackStage.event,
      _SegmentStage.postEvent => MatchPlaybackStage.post,
      _SegmentStage.openPlay => MatchPlaybackStage.event,
      _SegmentStage.hold => MatchPlaybackStage.hold,
    };
  }

  static MatchCameraPreset _cameraPresetForSegment(_TimelineSegment segment) {
    if (segment.event == null) {
      return MatchCameraPreset.broadcast;
    }
    return switch (segment.event!.type) {
      MatchViewerEventType.goal => MatchCameraPreset.goalCelebration,
      MatchViewerEventType.offside => MatchCameraPreset.assistantFlag,
      MatchViewerEventType.save ||
      MatchViewerEventType.miss ||
      MatchViewerEventType.attack ||
      MatchViewerEventType.penalty ||
      MatchViewerEventType.setPiece =>
        MatchCameraPreset.attackPush,
      _ => MatchCameraPreset.broadcast,
    };
  }

  static double _playbackRateForStage(_SegmentStage stage) {
    return switch (stage) {
      _SegmentStage.reset => 0.9,
      _SegmentStage.buildUp => 1.0,
      _SegmentStage.event => 1.05,
      _SegmentStage.postEvent => 0.95,
      _SegmentStage.openPlay => 1.0,
      _SegmentStage.hold => 0.85,
    };
  }

  static double _applyEasing(_SegmentStage stage, double t) {
    final double clamped = t.clamp(0, 1).toDouble();
    return switch (stage) {
      _SegmentStage.reset => _easeOut(clamped),
      _SegmentStage.buildUp => _easeIn(clamped),
      _SegmentStage.event => _easeInOut(clamped),
      _SegmentStage.postEvent => _easeOut(clamped),
      _SegmentStage.openPlay => clamped,
      _SegmentStage.hold => _easeOut(clamped),
    };
  }

  static double _changeoverForStage(_SegmentStage stage) {
    return switch (stage) {
      _SegmentStage.reset => 0.35,
      _SegmentStage.buildUp => 0.5,
      _SegmentStage.event => 0.45,
      _SegmentStage.postEvent => 0.55,
      _SegmentStage.openPlay => 0.5,
      _SegmentStage.hold => 0.2,
    };
  }

  static double _ownershipSwitchForStage(_SegmentStage stage) {
    return switch (stage) {
      _SegmentStage.reset => 0.35,
      _SegmentStage.buildUp => 0.5,
      _SegmentStage.event => 0.45,
      _SegmentStage.postEvent => 0.55,
      _SegmentStage.openPlay => 0.5,
      _SegmentStage.hold => 0.2,
    };
  }

  static MatchTimelineInjectionType _injectionTypeForEvent(
    MatchViewerEventType type,
  ) {
    return switch (type) {
      MatchViewerEventType.goal => MatchTimelineInjectionType.goal,
      MatchViewerEventType.offside => MatchTimelineInjectionType.offside,
      MatchViewerEventType.foul => MatchTimelineInjectionType.foul,
      MatchViewerEventType.save => MatchTimelineInjectionType.save,
      MatchViewerEventType.miss => MatchTimelineInjectionType.miss,
      MatchViewerEventType.redCard ||
      MatchViewerEventType.yellowCard =>
        MatchTimelineInjectionType.card,
      MatchViewerEventType.substitution =>
        MatchTimelineInjectionType.substitution,
      MatchViewerEventType.halftime => MatchTimelineInjectionType.halftime,
      MatchViewerEventType.fulltime => MatchTimelineInjectionType.fulltime,
      _ => MatchTimelineInjectionType.neutral,
    };
  }

  static _InjectionWindow _windowForEvent(MatchViewerEventType type) {
    return switch (type) {
      MatchViewerEventType.goal =>
        const _InjectionWindow(leadSeconds: 1.2, trailSeconds: 2.6),
      MatchViewerEventType.offside ||
      MatchViewerEventType.foul ||
      MatchViewerEventType.redCard ||
      MatchViewerEventType.yellowCard =>
        const _InjectionWindow(leadSeconds: 0.9, trailSeconds: 1.8),
      MatchViewerEventType.save ||
      MatchViewerEventType.miss =>
        const _InjectionWindow(leadSeconds: 0.6, trailSeconds: 1.4),
      MatchViewerEventType.halftime ||
      MatchViewerEventType.fulltime =>
        const _InjectionWindow(leadSeconds: 0.3, trailSeconds: 2.0),
      MatchViewerEventType.substitution =>
        const _InjectionWindow(leadSeconds: 0.4, trailSeconds: 1.0),
      _ => const _InjectionWindow(leadSeconds: 0.35, trailSeconds: 0.85),
    };
  }

  static int _injectionPriority(MatchTimelineInjectionType type) {
    return switch (type) {
      MatchTimelineInjectionType.goal => 100,
      MatchTimelineInjectionType.fulltime => 95,
      MatchTimelineInjectionType.halftime => 90,
      MatchTimelineInjectionType.card => 85,
      MatchTimelineInjectionType.offside => 80,
      MatchTimelineInjectionType.foul => 75,
      MatchTimelineInjectionType.save => 70,
      MatchTimelineInjectionType.miss => 65,
      MatchTimelineInjectionType.substitution => 60,
      MatchTimelineInjectionType.neutral => 10,
    };
  }

  static MatchViewerSide? _playerSideForId(
    List<MatchViewerPlayerFrame> players,
    String? playerId,
  ) {
    if (playerId == null) {
      return null;
    }
    for (final MatchViewerPlayerFrame player in players) {
      if (player.playerId == playerId) {
        return player.side;
      }
    }
    return null;
  }

  MatchViewerSide? _sideForTeamId(String? teamId) {
    if (teamId == null) {
      return null;
    }
    if (teamId == viewState.homeTeam.teamId) {
      return MatchViewerSide.home;
    }
    if (teamId == viewState.awayTeam.teamId) {
      return MatchViewerSide.away;
    }
    return null;
  }

  static PlayerRunPattern _runPatternForPlayer({
    required MatchViewerPlayerFrame player,
    required MatchViewerSide possessionSide,
    required String? ownerPlayerId,
  }) {
    if (player.side != possessionSide) {
      return PlayerRunPattern.defend;
    }
    if (player.playerId == ownerPlayerId ||
        player.line == MatchPlayerLine.attack) {
      return PlayerRunPattern.attack;
    }
    return PlayerRunPattern.support;
  }

  static List<double> _lanePositions(int count) {
    if (count <= 1) {
      return const <double>[50];
    }
    return List<double>.generate(
      count,
      (int index) => 18 + ((64 / (count - 1)) * index),
      growable: false,
    );
  }

  static double _easeIn(double t) => t * t;

  static double _easeOut(double t) => 1 - ((1 - t) * (1 - t));

  static double _easeInOut(double t) {
    if (t < 0.5) {
      return 2 * t * t;
    }
    final double value = (-2 * t) + 2;
    return 1 - ((value * value) / 2);
  }

  static int _nearestSpeedIndex(double speed, List<double> values) {
    int nearestIndex = 0;
    double nearestDistance = double.infinity;
    for (int index = 0; index < values.length; index += 1) {
      final double distance = (values[index] - speed).abs();
      if (distance < nearestDistance) {
        nearestDistance = distance;
        nearestIndex = index;
      }
    }
    return nearestIndex;
  }
}

class _ClockCompression {
  const _ClockCompression({
    required this.halftimeSeconds,
    required this.fulltimeSeconds,
    required this.firstHalfMaxClock,
    required this.secondHalfMaxClock,
  });

  factory _ClockCompression.fromViewState(MatchViewState viewState) {
    double? halftimeSeconds;
    double? fulltimeSeconds;
    double firstHalfMaxClock = 45;
    double secondHalfMaxClock = 90;
    bool secondHalf = false;
    final List<MatchTimelineFrame> frames = List<MatchTimelineFrame>.of(
      viewState.frames,
    )..sort(
        (MatchTimelineFrame left, MatchTimelineFrame right) =>
            left.timeSeconds.compareTo(right.timeSeconds),
      );
    for (final MatchTimelineFrame frame in frames) {
      if (frame.phase == MatchViewerPhase.halftime) {
        halftimeSeconds ??= frame.timeSeconds;
        firstHalfMaxClock = math.max(firstHalfMaxClock, frame.clockMinute);
      } else if (frame.phase == MatchViewerPhase.fulltime) {
        fulltimeSeconds ??= frame.timeSeconds;
        secondHalfMaxClock = math.max(secondHalfMaxClock, frame.clockMinute);
      } else if (!secondHalf) {
        firstHalfMaxClock = math.max(firstHalfMaxClock, frame.clockMinute);
      } else {
        secondHalfMaxClock = math.max(secondHalfMaxClock, frame.clockMinute);
      }
      if (halftimeSeconds != null && frame.timeSeconds >= halftimeSeconds) {
        secondHalf = true;
      }
    }
    for (final MatchEvent event in viewState.events) {
      if (event.type == MatchViewerEventType.halftime) {
        halftimeSeconds ??= event.timeSeconds;
      }
      if (event.type == MatchViewerEventType.fulltime) {
        fulltimeSeconds ??= event.timeSeconds;
      }
      final double resolvedClock = event.minute + (event.addedTime / 10);
      if (event.minute <= 45) {
        firstHalfMaxClock = math.max(firstHalfMaxClock, resolvedClock);
      } else {
        secondHalfMaxClock = math.max(secondHalfMaxClock, resolvedClock);
      }
    }
    return _ClockCompression(
      halftimeSeconds: halftimeSeconds,
      fulltimeSeconds: fulltimeSeconds,
      firstHalfMaxClock: firstHalfMaxClock,
      secondHalfMaxClock: secondHalfMaxClock,
    );
  }

  final double? halftimeSeconds;
  final double? fulltimeSeconds;
  final double firstHalfMaxClock;
  final double secondHalfMaxClock;

  double resolve({
    required double rawClockMinute,
    required double positionSeconds,
    required MatchViewerPhase phase,
  }) {
    if (phase == MatchViewerPhase.halftime) {
      return 45.0;
    }
    if (phase == MatchViewerPhase.fulltime ||
        (fulltimeSeconds != null && positionSeconds >= fulltimeSeconds!)) {
      return 90.0;
    }
    final bool secondHalf =
        halftimeSeconds != null && positionSeconds > halftimeSeconds!;
    if (!secondHalf) {
      if (rawClockMinute <= 45) {
        return rawClockMinute.clamp(0, 45).toDouble();
      }
      if (firstHalfMaxClock <= 45.0001) {
        return 45.0;
      }
      final double compressed =
          44.25 + (((rawClockMinute - 45) / (firstHalfMaxClock - 45)) * 0.75);
      return compressed.clamp(44.25, 45.0).toDouble();
    }
    if (rawClockMinute <= 90) {
      return rawClockMinute.clamp(45, 90).toDouble();
    }
    if (secondHalfMaxClock <= 90.0001) {
      return 90.0;
    }
    final double compressed =
        89.25 + (((rawClockMinute - 90) / (secondHalfMaxClock - 90)) * 0.75);
    return compressed.clamp(89.25, 90.0).toDouble();
  }
}

enum _SegmentStage {
  reset,
  buildUp,
  event,
  postEvent,
  openPlay,
  hold,
}

class _SegmentSeed {
  const _SegmentSeed({
    required this.startFrame,
    required this.endFrame,
    required this.startTime,
    required this.endTime,
    required this.event,
    required this.stage,
    required this.possessionSide,
    required this.synthetic,
    required this.sequenceId,
  });

  final MatchTimelineFrame startFrame;
  final MatchTimelineFrame endFrame;
  final double startTime;
  final double endTime;
  final MatchEvent? event;
  final _SegmentStage stage;
  final MatchViewerSide possessionSide;
  final bool synthetic;
  final String sequenceId;
}

class _SequenceWindow {
  const _SequenceWindow({
    required this.startTime,
    required this.endTime,
  });

  final double startTime;
  final double endTime;
}

class _TimelineSegment {
  const _TimelineSegment({
    required this.startFrame,
    required this.endFrame,
    required this.startPlayers,
    required this.endPlayers,
    required this.startTime,
    required this.endTime,
    required this.event,
    required this.stage,
    required this.possessionSide,
    required this.changeoverT,
    required this.ownershipSwitchT,
    required this.sequenceId,
    required this.sequenceStartTime,
    required this.sequenceEndTime,
    required this.synthetic,
    required this.highlightedIds,
  });

  factory _TimelineSegment.stationary(MatchTimelineFrame frame) {
    return _TimelineSegment(
      startFrame: frame,
      endFrame: frame,
      startPlayers: <String, MatchViewerPlayerFrame>{
        for (final MatchViewerPlayerFrame player in frame.players)
          player.playerId: player,
      },
      endPlayers: <String, MatchViewerPlayerFrame>{
        for (final MatchViewerPlayerFrame player in frame.players)
          player.playerId: player,
      },
      startTime: frame.timeSeconds,
      endTime: frame.timeSeconds,
      event: null,
      stage: _SegmentStage.hold,
      possessionSide: frame.possessionSide,
      changeoverT: 0.5,
      ownershipSwitchT: 0.5,
      sequenceId: 'sequence-1',
      sequenceStartTime: frame.timeSeconds,
      sequenceEndTime: frame.timeSeconds,
      synthetic: false,
      highlightedIds: const <String>{},
    );
  }

  final MatchTimelineFrame startFrame;
  final MatchTimelineFrame endFrame;
  final Map<String, MatchViewerPlayerFrame> startPlayers;
  final Map<String, MatchViewerPlayerFrame> endPlayers;
  final double startTime;
  final double endTime;
  final MatchEvent? event;
  final _SegmentStage stage;
  final MatchViewerSide possessionSide;
  final double changeoverT;
  final double ownershipSwitchT;
  final String sequenceId;
  final double sequenceStartTime;
  final double sequenceEndTime;
  final bool synthetic;
  final Set<String> highlightedIds;
}

class _InjectionWindow {
  const _InjectionWindow({
    required this.leadSeconds,
    required this.trailSeconds,
  });

  final double leadSeconds;
  final double trailSeconds;
}

class _PauseCue {
  const _PauseCue({
    required this.holdSeconds,
    required this.resumePosition,
  });

  final double holdSeconds;
  final double resumePosition;
}

class _RuntimeSnapshot {
  const _RuntimeSnapshot({
    required this.players,
    required this.ball,
    required this.frame,
    required this.segment,
    required this.easedT,
  });

  final List<PlayerEntity> players;
  final BallEntity ball;
  final MatchTimelineFrame frame;
  final _TimelineSegment segment;
  final double easedT;
}
