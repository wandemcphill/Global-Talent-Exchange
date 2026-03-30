import 'package:flutter/material.dart';

import '../../../models/match_event.dart';
import '../../../models/match_timeline_frame.dart';
import '../../../models/match_view_state.dart';
import '../../../models/real_match_engine_presentation.dart';
import 'broadcast_package_models.dart';

class RealMatchSceneDirector {
  const RealMatchSceneDirector._();

  static MatchEnginePresentationState resolve({
    required MatchViewState viewState,
    required MatchTimelineFrame frame,
    required MatchPresentationPackage package,
    MatchEvent? activeEvent,
    required double playbackSeconds,
  }) {
    final MatchSceneEventMapping eventMapping = _eventMapping(
      frame: frame,
      activeEvent: activeEvent,
    );
    final MatchEngineCameraPreset sceneState = _sceneState(
      frame: frame,
      activeEvent: activeEvent,
      eventMapping: eventMapping,
      playbackSeconds: playbackSeconds,
    );
    final MatchEnginePresentationMoment moment = _moment(
      sceneState: sceneState,
      eventMapping: eventMapping,
      activeEvent: activeEvent,
    );
    final MatchEngineEventContext? eventContext =
        activeEvent == null ? null : _eventContext(activeEvent);
    final MatchEngineTeamShape homeShape = _teamShape(
      viewState: viewState,
      frame: frame,
      side: MatchViewerSide.home,
    );
    final MatchEngineTeamShape awayShape = _teamShape(
      viewState: viewState,
      frame: frame,
      side: MatchViewerSide.away,
    );
    final MatchEngineBanner? banner = _banner(
      frame: frame,
      activeEvent: activeEvent,
      eventMapping: eventMapping,
    );
    final MatchEngineSummaryBoard? summaryBoard = _summaryBoard(
      frame: frame,
      activeEvent: activeEvent,
      package: package,
      viewState: viewState,
    );
    final List<MatchPresentationPlayer> ratingLeaders = package.ratingLeaders
        .where((MatchPresentationPlayer item) => item.rating != null)
        .take(6)
        .toList(growable: false);
    return MatchEnginePresentationState(
      sceneState: sceneState,
      cameraPreset: sceneState,
      eventMapping: eventMapping,
      moment: moment,
      phaseLabel: _phaseLabel(frame: frame, eventMapping: eventMapping),
      stateLabel: _stateLabel(frame: frame, eventMapping: eventMapping),
      sceneLabel: _sceneLabel(sceneState),
      cameraLabel: _cameraLabel(sceneState),
      clockLabel: activeEvent?.clockLabel ?? _clockLabel(frame.clockMinute),
      possessionSide: frame.possessionSide,
      possessionOwnerId: _possessionOwnerId(frame, activeEvent),
      homeShape: homeShape,
      awayShape: awayShape,
      activeEventContext: eventContext,
      ratingLeaders: ratingLeaders,
      lowerThirdHeadline: _headline(
        activeEvent: activeEvent,
        sceneState: sceneState,
        eventMapping: eventMapping,
      ),
      lowerThirdDetail: _detail(
        activeEvent: activeEvent,
        package: package,
        frame: frame,
        eventMapping: eventMapping,
      ),
      lowerThirdTrailing:
          activeEvent?.clockLabel ?? _clockLabel(frame.clockMinute),
      scorebugEventLabel: banner?.label ?? _scorebugEventLabel(activeEvent),
      banner: banner,
      summaryBoard: summaryBoard,
    );
  }

  static MatchSceneEventMapping _eventMapping({
    required MatchTimelineFrame frame,
    required MatchEvent? activeEvent,
  }) {
    if (activeEvent != null) {
      switch (activeEvent.type) {
        case MatchViewerEventType.kickoff:
          return MatchSceneEventMapping.kickoff;
        case MatchViewerEventType.goal:
          return MatchSceneEventMapping.goal;
        case MatchViewerEventType.save:
          return MatchSceneEventMapping.save;
        case MatchViewerEventType.miss:
          return MatchSceneEventMapping.shot;
        case MatchViewerEventType.foul:
        case MatchViewerEventType.injury:
        case MatchViewerEventType.offside:
          return MatchSceneEventMapping.foul;
        case MatchViewerEventType.redCard:
        case MatchViewerEventType.yellowCard:
          return MatchSceneEventMapping.booking;
        case MatchViewerEventType.substitution:
          return MatchSceneEventMapping.substitution;
        case MatchViewerEventType.setPiece:
          return _setPieceMapping(activeEvent);
        case MatchViewerEventType.penalty:
          return MatchSceneEventMapping.penalty;
        case MatchViewerEventType.halftime:
          return MatchSceneEventMapping.halftime;
        case MatchViewerEventType.fulltime:
          return MatchSceneEventMapping.fulltime;
        case MatchViewerEventType.attack:
          return _isFinalThird(frame, frame.possessionSide)
              ? MatchSceneEventMapping.chance_creation
              : MatchSceneEventMapping.possession_phase;
        case MatchViewerEventType.neutral:
          break;
      }
    }
    if (frame.phase == MatchViewerPhase.halftime) {
      return MatchSceneEventMapping.halftime;
    }
    if (frame.phase == MatchViewerPhase.fulltime) {
      return MatchSceneEventMapping.fulltime;
    }
    if (frame.phase == MatchViewerPhase.kickoff) {
      return MatchSceneEventMapping.kickoff;
    }
    if (frame.phase == MatchViewerPhase.setPiece) {
      return _setPieceMapping(null, frame: frame);
    }
    if (_looksLikeShot(frame.ball.state)) {
      return MatchSceneEventMapping.shot;
    }
    if (_isFinalThird(frame, frame.possessionSide)) {
      return MatchSceneEventMapping.chance_creation;
    }
    return MatchSceneEventMapping.possession_phase;
  }

  static MatchEngineCameraPreset _sceneState({
    required MatchTimelineFrame frame,
    required MatchEvent? activeEvent,
    required MatchSceneEventMapping eventMapping,
    required double playbackSeconds,
  }) {
    switch (eventMapping) {
      case MatchSceneEventMapping.halftime:
        return MatchEngineCameraPreset.halftime_board;
      case MatchSceneEventMapping.fulltime:
        return MatchEngineCameraPreset.fulltime_board;
      case MatchSceneEventMapping.kickoff:
        final bool earlyKickoff =
            playbackSeconds <= 1.35 || frame.timeSeconds <= 1.35;
        return earlyKickoff
            ? MatchEngineCameraPreset.stadium_wide
            : MatchEngineCameraPreset.kickoff_center;
      case MatchSceneEventMapping.goal:
        if (_isReplayStage(frame)) {
          return MatchEngineCameraPreset.goal_replay;
        }
        return _attackingThirdScene(frame);
      case MatchSceneEventMapping.save:
      case MatchSceneEventMapping.shot:
        if (_isReplayStage(frame)) {
          return MatchEngineCameraPreset.goal_replay;
        }
        return _attackingThirdScene(frame);
      case MatchSceneEventMapping.corner:
      case MatchSceneEventMapping.free_kick:
      case MatchSceneEventMapping.penalty:
        if (_isReplayStage(frame)) {
          return MatchEngineCameraPreset.goal_replay;
        }
        return _setPieceScene(frame);
      case MatchSceneEventMapping.foul:
      case MatchSceneEventMapping.booking:
        return MatchEngineCameraPreset.defensive_block;
      case MatchSceneEventMapping.substitution:
        return MatchEngineCameraPreset.tactical_high;
      case MatchSceneEventMapping.chance_creation:
        return _attackingThirdScene(frame);
      case MatchSceneEventMapping.possession_phase:
        if (frame.possessionPhase == MatchPossessionPhase.recovery ||
            frame.possessionPhase == MatchPossessionPhase.stoppage ||
            frame.stage == MatchPlaybackStage.hold) {
          return MatchEngineCameraPreset.defensive_block;
        }
        return MatchEngineCameraPreset.tactical_high;
    }
  }

  static MatchEnginePresentationMoment _moment({
    required MatchEngineCameraPreset sceneState,
    required MatchSceneEventMapping eventMapping,
    required MatchEvent? activeEvent,
  }) {
    switch (sceneState) {
      case MatchEngineCameraPreset.goal_replay:
        return switch (eventMapping) {
          MatchSceneEventMapping.goal ||
          MatchSceneEventMapping.save ||
          MatchSceneEventMapping.shot ||
          MatchSceneEventMapping.corner ||
          MatchSceneEventMapping.free_kick ||
          MatchSceneEventMapping
              .penalty => MatchEnginePresentationMoment.replay,
          _ =>
            activeEvent?.type == MatchViewerEventType.goal
                ? MatchEnginePresentationMoment.replay
                : MatchEnginePresentationMoment.recap,
        };
      case MatchEngineCameraPreset.halftime_board:
      case MatchEngineCameraPreset.fulltime_board:
        return MatchEnginePresentationMoment.recap;
      case MatchEngineCameraPreset.stadium_wide:
      case MatchEngineCameraPreset.kickoff_center:
      case MatchEngineCameraPreset.tactical_high:
      case MatchEngineCameraPreset.attacking_third_left:
      case MatchEngineCameraPreset.attacking_third_right:
      case MatchEngineCameraPreset.defensive_block:
      case MatchEngineCameraPreset.set_piece_left:
      case MatchEngineCameraPreset.set_piece_right:
        return MatchEnginePresentationMoment.live;
    }
  }

  static MatchEngineEventContext _eventContext(MatchEvent event) {
    return MatchEngineEventContext(
      eventId: event.id,
      teamId: event.teamId,
      teamName: event.teamName,
      primaryPlayerId: event.primaryPlayerId,
      primaryPlayerName: event.primaryPlayerName,
      secondaryPlayerId: event.secondaryPlayerId,
      secondaryPlayerName: event.secondaryPlayerName,
      bannerText: event.bannerText,
      commentary: event.commentary,
      reviewable: event.reviewable,
      reviewDecision: event.reviewDecision,
    );
  }

  static MatchEngineTeamShape _teamShape({
    required MatchViewState viewState,
    required MatchTimelineFrame frame,
    required MatchViewerSide side,
  }) {
    final List<MatchViewerPlayerFrame> players = frame.players
        .where((MatchViewerPlayerFrame player) => player.side == side)
        .where((MatchViewerPlayerFrame player) => player.active)
        .toList(growable: false);
    final List<MatchEngineShapeLane> lanes = <MatchEngineShapeLane>[
      _shapeLane(players, MatchEngineShapeLine.goalkeeper),
      _shapeLane(players, MatchEngineShapeLine.defense),
      _shapeLane(players, MatchEngineShapeLine.midfield),
      _shapeLane(players, MatchEngineShapeLine.attack),
    ];
    final List<MatchViewerPlayerFrame> outfield = players
        .where((MatchViewerPlayerFrame player) => !player.isGoalkeeper)
        .toList(growable: false);
    final double width =
        outfield.isEmpty
            ? 0
            : (outfield
                        .map((MatchViewerPlayerFrame item) => item.position.y)
                        .reduce(
                          (double left, double right) =>
                              left > right ? left : right,
                        ) -
                    outfield
                        .map((MatchViewerPlayerFrame item) => item.position.y)
                        .reduce(
                          (double left, double right) =>
                              left < right ? left : right,
                        ))
                .toDouble();
    final MatchEngineShapeLane defenseLane = lanes[1];
    final MatchEngineShapeLane attackLane = lanes[3];
    final double depth =
        (attackLane.averageX - defenseLane.averageX).abs().toDouble();
    final double compactness = (1 - (depth / 62)).clamp(0.16, 0.96).toDouble();
    return MatchEngineTeamShape(
      teamId: viewState.teamForSide(side).teamId,
      side: side,
      formation: viewState.teamForSide(side).formation,
      width: double.parse(width.toStringAsFixed(1)),
      depth: double.parse(depth.toStringAsFixed(1)),
      compactness: double.parse(compactness.toStringAsFixed(3)),
      inPossession: frame.possessionSide == side,
      lanes: lanes,
    );
  }

  static MatchEngineShapeLane _shapeLane(
    List<MatchViewerPlayerFrame> players,
    MatchEngineShapeLine line,
  ) {
    final List<MatchViewerPlayerFrame> matching = players
        .where((MatchViewerPlayerFrame player) => _matchesLine(player, line))
        .toList(growable: false);
    if (matching.isEmpty) {
      return MatchEngineShapeLane(
        line: line,
        averageX: 0,
        averageY: 0,
        width: 0,
        activeCount: 0,
      );
    }
    final double averageX =
        matching
            .map((MatchViewerPlayerFrame item) => item.position.x)
            .reduce((double left, double right) => left + right) /
        matching.length;
    final double averageY =
        matching
            .map((MatchViewerPlayerFrame item) => item.position.y)
            .reduce((double left, double right) => left + right) /
        matching.length;
    final double maxY = matching
        .map((MatchViewerPlayerFrame item) => item.position.y)
        .reduce((double left, double right) => left > right ? left : right);
    final double minY = matching
        .map((MatchViewerPlayerFrame item) => item.position.y)
        .reduce((double left, double right) => left < right ? left : right);
    return MatchEngineShapeLane(
      line: line,
      averageX: double.parse(averageX.toStringAsFixed(1)),
      averageY: double.parse(averageY.toStringAsFixed(1)),
      width: double.parse((maxY - minY).toStringAsFixed(1)),
      activeCount: matching.length,
    );
  }

  static bool _matchesLine(
    MatchViewerPlayerFrame player,
    MatchEngineShapeLine line,
  ) {
    return switch (line) {
      MatchEngineShapeLine.goalkeeper =>
        player.line == MatchPlayerLine.goalkeeper,
      MatchEngineShapeLine.defense => player.line == MatchPlayerLine.defense,
      MatchEngineShapeLine.midfield => player.line == MatchPlayerLine.midfield,
      MatchEngineShapeLine.attack => player.line == MatchPlayerLine.attack,
    };
  }

  static MatchEngineBanner? _banner({
    required MatchTimelineFrame frame,
    required MatchEvent? activeEvent,
    required MatchSceneEventMapping eventMapping,
  }) {
    switch (eventMapping) {
      case MatchSceneEventMapping.substitution:
        if (activeEvent == null) {
          return null;
        }
        final String detail =
            activeEvent.secondaryPlayerName != null &&
                    activeEvent.primaryPlayerName != null
                ? '${activeEvent.secondaryPlayerName} on for ${activeEvent.primaryPlayerName}'
                : activeEvent.commentary;
        return MatchEngineBanner(
          label: 'Substitution',
          detail: detail.trim().isEmpty ? activeEvent.bannerText : detail,
          accentColor: const Color(0xFF53B1FD),
          icon: Icons.swap_horiz,
        );
      case MatchSceneEventMapping.corner:
        return MatchEngineBanner(
          label: 'Corner',
          detail: _setPieceBannerDetail(
            frame: frame,
            activeEvent: activeEvent,
            fallback: 'Set-piece pressure building.',
            namedPlayerDetail:
                (String playerName) => '$playerName to deliver from the flag.',
          ),
          accentColor: const Color(0xFFFDB022),
          icon: Icons.turn_right,
        );
      case MatchSceneEventMapping.free_kick:
        return MatchEngineBanner(
          label: 'Free Kick',
          detail: _setPieceBannerDetail(
            frame: frame,
            activeEvent: activeEvent,
            fallback: 'Restart in a dangerous area.',
            namedPlayerDetail:
                (String playerName) => '$playerName stands over the restart.',
          ),
          accentColor: const Color(0xFFF79009),
          icon: Icons.adjust,
        );
      case MatchSceneEventMapping.penalty:
        return MatchEngineBanner(
          label: 'Penalty',
          detail: _setPieceBannerDetail(
            frame: frame,
            activeEvent: activeEvent,
            fallback: 'Spot kick about to be taken.',
            namedPlayerDetail:
                (String playerName) => '$playerName prepares from the spot.',
          ),
          accentColor: const Color(0xFFF04438),
          icon: Icons.radio_button_checked,
        );
      default:
        return null;
    }
  }

  static MatchEngineSummaryBoard? _summaryBoard({
    required MatchTimelineFrame frame,
    required MatchEvent? activeEvent,
    required MatchPresentationPackage package,
    required MatchViewState viewState,
  }) {
    if (frame.phase == MatchViewerPhase.halftime ||
        activeEvent?.type == MatchViewerEventType.halftime) {
      final List<String> bullets = _summaryLines(<String>[
        ...package.commentaryHighlights.take(2),
        ...package.momentumNotes.take(2),
      ]);
      return MatchEngineSummaryBoard(
        title: 'Halftime recap',
        subtitle:
            '${viewState.homeTeam.shortName} ${frame.homeScore} - ${frame.awayScore} ${viewState.awayTeam.shortName}',
        bullets: bullets,
      );
    }
    if (frame.phase == MatchViewerPhase.fulltime ||
        activeEvent?.type == MatchViewerEventType.fulltime) {
      final List<String> bullets = _summaryLines(<String>[
        ...package.momentumNotes.take(2),
        ...package.coachNotes.take(2),
        ...package.ratingLeaders
            .where((MatchPresentationPlayer item) => item.rating != null)
            .take(2)
            .map(
              (MatchPresentationPlayer item) =>
                  '${item.playerName} rated ${item.rating!.toStringAsFixed(1)}',
            ),
      ]);
      return MatchEngineSummaryBoard(
        title: 'Full-time recap',
        subtitle:
            '${viewState.homeTeam.shortName} ${frame.homeScore} - ${frame.awayScore} ${viewState.awayTeam.shortName}',
        bullets: bullets,
      );
    }
    return null;
  }

  static List<String> _summaryLines(List<String> values) {
    final List<String> output = <String>[];
    final Set<String> seen = <String>{};
    for (final String value in values) {
      final String trimmed = value.trim();
      if (trimmed.isEmpty || !seen.add(trimmed)) {
        continue;
      }
      output.add(trimmed);
    }
    return output.take(4).toList(growable: false);
  }

  static MatchSceneEventMapping _setPieceMapping(
    MatchEvent? activeEvent, {
    MatchTimelineFrame? frame,
  }) {
    final String sample =
        '${activeEvent?.bannerText ?? ''} ${activeEvent?.commentary ?? ''} ${frame?.eventBanner ?? ''}'
            .toLowerCase();
    if (sample.contains('corner')) {
      return MatchSceneEventMapping.corner;
    }
    if (sample.contains('penalty') || sample.contains('spot kick')) {
      return MatchSceneEventMapping.penalty;
    }
    return MatchSceneEventMapping.free_kick;
  }

  static MatchEngineCameraPreset _attackingThirdScene(
    MatchTimelineFrame frame,
  ) {
    return _attacksRight(frame, frame.possessionSide)
        ? MatchEngineCameraPreset.attacking_third_right
        : MatchEngineCameraPreset.attacking_third_left;
  }

  static MatchEngineCameraPreset _setPieceScene(MatchTimelineFrame frame) {
    return _attacksRight(frame, frame.possessionSide)
        ? MatchEngineCameraPreset.set_piece_right
        : MatchEngineCameraPreset.set_piece_left;
  }

  static bool _attacksRight(MatchTimelineFrame frame, MatchViewerSide side) {
    return side == MatchViewerSide.home
        ? frame.homeAttacksRight
        : !frame.homeAttacksRight;
  }

  static bool _isFinalThird(MatchTimelineFrame frame, MatchViewerSide side) {
    final double x = frame.ball.position.x;
    return _attacksRight(frame, side) ? x >= 63 : x <= 37;
  }

  static bool _isReplayStage(MatchTimelineFrame frame) {
    return frame.stage == MatchPlaybackStage.post ||
        frame.stage == MatchPlaybackStage.review ||
        frame.stage == MatchPlaybackStage.decision;
  }

  static bool _looksLikeShot(String state) {
    final String normalized = state.trim().toLowerCase();
    return normalized == 'shot' ||
        normalized == 'saved' ||
        normalized == 'missed' ||
        normalized == 'in_goal';
  }

  static String? _possessionOwnerId(
    MatchTimelineFrame frame,
    MatchEvent? activeEvent,
  ) {
    return frame.ball.ownerPlayerId ??
        activeEvent?.primaryPlayerId ??
        activeEvent?.secondaryPlayerId;
  }

  static String _clockLabel(double minute) {
    return "${minute.clamp(0, 120).round()}'";
  }

  static String _phaseLabel({
    required MatchTimelineFrame frame,
    required MatchSceneEventMapping eventMapping,
  }) {
    return switch (eventMapping) {
      MatchSceneEventMapping.kickoff => 'Kickoff',
      MatchSceneEventMapping.possession_phase => 'Possession',
      MatchSceneEventMapping.chance_creation => 'Chance creation',
      MatchSceneEventMapping.shot => 'Shot phase',
      MatchSceneEventMapping.save => 'Save phase',
      MatchSceneEventMapping.goal => 'Goal moment',
      MatchSceneEventMapping.foul => 'Foul stop',
      MatchSceneEventMapping.booking => 'Booking',
      MatchSceneEventMapping.substitution => 'Substitution',
      MatchSceneEventMapping.corner => 'Corner',
      MatchSceneEventMapping.free_kick => 'Free kick',
      MatchSceneEventMapping.penalty => 'Penalty',
      MatchSceneEventMapping.halftime => 'Halftime',
      MatchSceneEventMapping.fulltime => 'Full-time',
    };
  }

  static String _stateLabel({
    required MatchTimelineFrame frame,
    required MatchSceneEventMapping eventMapping,
  }) {
    if (frame.possessionPhase == MatchPossessionPhase.recovery) {
      return 'Transition';
    }
    if (frame.possessionPhase == MatchPossessionPhase.buildUp) {
      return 'Build-up';
    }
    if (frame.possessionPhase == MatchPossessionPhase.attack) {
      return 'Attacking phase';
    }
    return switch (eventMapping) {
      MatchSceneEventMapping.kickoff => 'Restart',
      MatchSceneEventMapping.possession_phase => 'Settled possession',
      MatchSceneEventMapping.chance_creation => 'Final-third pressure',
      MatchSceneEventMapping.shot => 'Shot release',
      MatchSceneEventMapping.save => 'Goalmouth action',
      MatchSceneEventMapping.goal => 'Highlight replay',
      MatchSceneEventMapping.foul => 'Defensive phase',
      MatchSceneEventMapping.booking => 'Official intervention',
      MatchSceneEventMapping.substitution => 'Bench rotation',
      MatchSceneEventMapping.corner => 'Set-piece scene',
      MatchSceneEventMapping.free_kick => 'Set-piece scene',
      MatchSceneEventMapping.penalty => 'Set-piece scene',
      MatchSceneEventMapping.halftime => 'Recap board',
      MatchSceneEventMapping.fulltime => 'Recap board',
    };
  }

  static String _sceneLabel(MatchEngineCameraPreset sceneState) {
    return switch (sceneState) {
      MatchEngineCameraPreset.stadium_wide => 'Stadium-wide presentation',
      MatchEngineCameraPreset.kickoff_center => 'Kickoff-center framing',
      MatchEngineCameraPreset.tactical_high => 'Tactical high camera',
      MatchEngineCameraPreset.attacking_third_left =>
        'Attacking-third left framing',
      MatchEngineCameraPreset.attacking_third_right =>
        'Attacking-third right framing',
      MatchEngineCameraPreset.defensive_block => 'Defensive block view',
      MatchEngineCameraPreset.set_piece_left => 'Set-piece left framing',
      MatchEngineCameraPreset.set_piece_right => 'Set-piece right framing',
      MatchEngineCameraPreset.goal_replay => 'Replay angle',
      MatchEngineCameraPreset.halftime_board => 'Halftime board',
      MatchEngineCameraPreset.fulltime_board => 'Full-time board',
    };
  }

  static String _cameraLabel(MatchEngineCameraPreset sceneState) {
    return switch (sceneState) {
      MatchEngineCameraPreset.stadium_wide => 'WIDE',
      MatchEngineCameraPreset.kickoff_center => 'KICKOFF',
      MatchEngineCameraPreset.tactical_high => 'TACTICAL',
      MatchEngineCameraPreset.attacking_third_left => 'ATTACK L',
      MatchEngineCameraPreset.attacking_third_right => 'ATTACK R',
      MatchEngineCameraPreset.defensive_block => 'BLOCK',
      MatchEngineCameraPreset.set_piece_left => 'SET L',
      MatchEngineCameraPreset.set_piece_right => 'SET R',
      MatchEngineCameraPreset.goal_replay => 'REPLAY',
      MatchEngineCameraPreset.halftime_board => 'HALF',
      MatchEngineCameraPreset.fulltime_board => 'FULL',
    };
  }

  static String _headline({
    required MatchEvent? activeEvent,
    required MatchEngineCameraPreset sceneState,
    required MatchSceneEventMapping eventMapping,
  }) {
    if (activeEvent != null && activeEvent.bannerText.trim().isNotEmpty) {
      return activeEvent.bannerText;
    }
    return switch (eventMapping) {
      MatchSceneEventMapping.possession_phase => 'Match control',
      MatchSceneEventMapping.chance_creation => 'Chance building',
      MatchSceneEventMapping.shot => 'Shot released',
      MatchSceneEventMapping.save => 'Save sequence',
      MatchSceneEventMapping.goal => 'Goal replay',
      MatchSceneEventMapping.foul => 'Play stopped',
      MatchSceneEventMapping.booking => 'Card shown',
      MatchSceneEventMapping.substitution => 'Substitution window',
      MatchSceneEventMapping.corner => 'Corner routine',
      MatchSceneEventMapping.free_kick => 'Free-kick setup',
      MatchSceneEventMapping.penalty => 'Penalty setup',
      MatchSceneEventMapping.kickoff => 'Kickoff',
      MatchSceneEventMapping.halftime => 'Halftime recap',
      MatchSceneEventMapping.fulltime => 'Full-time recap',
    };
  }

  static String _detail({
    required MatchEvent? activeEvent,
    required MatchPresentationPackage package,
    required MatchTimelineFrame frame,
    required MatchSceneEventMapping eventMapping,
  }) {
    if (activeEvent != null && activeEvent.commentary.trim().isNotEmpty) {
      return activeEvent.commentary;
    }
    final String eventFallback = _eventFallbackDetail(
      activeEvent: activeEvent,
      frame: frame,
      eventMapping: eventMapping,
    );
    if (eventFallback.isNotEmpty) {
      return eventFallback;
    }
    if (package.commentaryHighlights.isNotEmpty) {
      return package.commentaryHighlights.first;
    }
    if (package.context.matchSignificance != null &&
        package.context.matchSignificance!.trim().isNotEmpty) {
      return package.context.matchSignificance!;
    }
    return switch (frame.phase) {
      MatchViewerPhase.kickoff =>
        'The match opens with the tactical structure visible from the first restart.',
      MatchViewerPhase.setPiece =>
        'Set-piece modules stay hidden when the payload does not expose more detail.',
      MatchViewerPhase.halftime =>
        'Halftime analysis is limited on this payload.',
      MatchViewerPhase.fulltime =>
        'Full-time analysis is limited on this payload.',
      MatchViewerPhase.openPlay =>
        'Live tactical detail is shown only when the current payload exposes it.',
    };
  }

  static String? _scorebugEventLabel(MatchEvent? activeEvent) {
    if (activeEvent == null || activeEvent.bannerText.trim().isEmpty) {
      return null;
    }
    return activeEvent.bannerText;
  }

  static String _setPieceBannerDetail({
    required MatchTimelineFrame frame,
    required MatchEvent? activeEvent,
    required String fallback,
    required String Function(String playerName) namedPlayerDetail,
  }) {
    final String? primaryPlayerName = activeEvent?.primaryPlayerName?.trim();
    if (primaryPlayerName != null && primaryPlayerName.isNotEmpty) {
      return namedPlayerDetail(primaryPlayerName);
    }
    final String bannerText =
        activeEvent?.bannerText.trim() ?? frame.eventBanner?.trim() ?? '';
    if (bannerText.isNotEmpty) {
      return bannerText;
    }
    return fallback;
  }

  static String _eventFallbackDetail({
    required MatchEvent? activeEvent,
    required MatchTimelineFrame frame,
    required MatchSceneEventMapping eventMapping,
  }) {
    final String? primaryPlayerName = activeEvent?.primaryPlayerName?.trim();
    final String? secondaryPlayerName =
        activeEvent?.secondaryPlayerName?.trim();
    return switch (eventMapping) {
      MatchSceneEventMapping.kickoff =>
        'The match opens with the tactical structure visible from the first restart.',
      MatchSceneEventMapping.goal =>
        _isReplayStage(frame)
            ? 'Replay angle isolates the finish and the recovery runs around the box.'
            : 'The attacking shape breaks the final line and turns the move into a finish.',
      MatchSceneEventMapping.save || MatchSceneEventMapping.shot =>
        _isReplayStage(frame)
            ? 'Replay angle tracks the strike, flight, and goalkeeper line.'
            : 'The move compresses around the area as the shot lane opens.',
      MatchSceneEventMapping.substitution =>
        secondaryPlayerName != null &&
                secondaryPlayerName.isNotEmpty &&
                primaryPlayerName != null &&
                primaryPlayerName.isNotEmpty
            ? '$secondaryPlayerName replaces $primaryPlayerName.'
            : 'Fresh legs arrive and the team shape resets around the change.',
      MatchSceneEventMapping.corner =>
        _isReplayStage(frame)
            ? 'Replay angle tracks the delivery arc and the runners attacking the six-yard lane.'
            : primaryPlayerName != null && primaryPlayerName.isNotEmpty
            ? '$primaryPlayerName shapes the delivery for the near-post routine.'
            : 'Attackers and markers stack across the six-yard lane for the delivery.',
      MatchSceneEventMapping.free_kick =>
        _isReplayStage(frame)
            ? 'Replay framing holds on the strike lane, the wall, and the goalkeeper set.'
            : primaryPlayerName != null && primaryPlayerName.isNotEmpty
            ? '$primaryPlayerName waits over the ball as the line holds the edge.'
            : 'The restart unit settles into position while the line guards the box edge.',
      MatchSceneEventMapping.penalty =>
        _isReplayStage(frame)
            ? 'Replay framing holds on the spot-kick outcome and goalkeeper reaction.'
            : primaryPlayerName != null && primaryPlayerName.isNotEmpty
            ? '$primaryPlayerName stands over the penalty with the box cleared.'
            : 'The spot-kick setup clears the area and isolates the taker.',
      MatchSceneEventMapping.halftime =>
        'Halftime analysis is limited on this payload.',
      MatchSceneEventMapping.fulltime =>
        'Full-time analysis is limited on this payload.',
      MatchSceneEventMapping.possession_phase => '',
      MatchSceneEventMapping.chance_creation => '',
      MatchSceneEventMapping.foul =>
        'Play pauses while the defensive block regains shape around the restart.',
      MatchSceneEventMapping.booking =>
        'The referee intervention slows the tempo while players reset their positions.',
    };
  }
}
