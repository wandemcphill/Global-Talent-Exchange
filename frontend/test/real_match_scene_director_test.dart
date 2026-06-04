import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/match_center/presentation/broadcast_package_models.dart';
import 'package:gte_frontend/features/match_center/presentation/real_match_scene_director.dart';
import 'package:gte_frontend/features/match_center/models/match_event.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';
import 'package:gte_frontend/features/match_center/models/match_view_state.dart';
import 'package:gte_frontend/features/match_center/models/real_match_engine_presentation.dart';

import 'support/gtex_match_broadcast_fixture.dart';

void main() {
  test(
    'scene director sequences kickoff from stadium wide into center view',
    () {
      final MatchViewState viewState = buildBroadcastTestViewState();
      final MatchPresentationPackage package = buildBroadcastTestPackage();
      final MatchEvent kickoff = viewState.events.first;
      final MatchTimelineFrame frame = viewState.firstFrame.copyWith(
        possessionPhase: MatchPossessionPhase.restart,
      );

      final MatchEnginePresentationState early = _resolve(
        viewState: viewState,
        package: package,
        frame: frame,
        activeEvent: kickoff,
        playbackSeconds: 0.8,
      );
      final MatchEnginePresentationState settled = _resolve(
        viewState: viewState,
        package: package,
        frame: frame.copyWith(timeSeconds: 2.0),
        activeEvent: kickoff,
        playbackSeconds: 2.0,
      );

      expect(early.sceneState, MatchEngineCameraPreset.stadium_wide);
      expect(settled.sceneState, MatchEngineCameraPreset.kickoff_center);
      expect(early.eventMapping, MatchSceneEventMapping.kickoff);
      expect(early.phaseLabel, 'Kickoff');
    },
  );

  test('event-to-scene mapping covers required live and recap moments', () {
    final MatchViewState viewState = buildBroadcastTestViewState();
    final MatchPresentationPackage package = buildBroadcastTestPackage();
    final MatchEvent kickoff = viewState.events.first;
    final MatchEvent goal = viewState.events.firstWhere(
      (MatchEvent event) => event.type == MatchViewerEventType.goal,
    );
    final MatchEvent miss = viewState.events.firstWhere(
      (MatchEvent event) => event.type == MatchViewerEventType.miss,
    );
    final MatchTimelineFrame baseFrame = viewState.frames[1];
    final MatchTimelineFrame attackingFrame = baseFrame.copyWith(
      possessionPhase: MatchPossessionPhase.attack,
      ball: baseFrame.ball.copyWith(
        position: baseFrame.ball.position.copyWith(x: 74),
      ),
    );
    final MatchTimelineFrame possessionFrame = baseFrame.copyWith(
      possessionPhase: MatchPossessionPhase.control,
      ball: baseFrame.ball.copyWith(
        position: baseFrame.ball.position.copyWith(x: 54),
      ),
    );
    final MatchTimelineFrame setPieceFrame = baseFrame.copyWith(
      phase: MatchViewerPhase.setPiece,
      eventBanner: 'Corner for Lagos',
      ball: baseFrame.ball.copyWith(
        position: baseFrame.ball.position.copyWith(x: 81, y: 18),
      ),
    );
    final List<_MappingCase> cases = <_MappingCase>[
      _MappingCase(
        name: 'kickoff',
        frame: viewState.firstFrame,
        activeEvent: kickoff,
        expectedMapping: MatchSceneEventMapping.kickoff,
      ),
      _MappingCase(
        name: 'possession phase',
        frame: possessionFrame,
        expectedMapping: MatchSceneEventMapping.possession_phase,
      ),
      _MappingCase(
        name: 'chance creation',
        frame: attackingFrame,
        activeEvent: kickoff.copyWith(
          type: MatchViewerEventType.attack,
          bannerText: 'Lagos push into the box',
          commentary: 'The attack reaches the final third.',
        ),
        expectedMapping: MatchSceneEventMapping.chance_creation,
      ),
      _MappingCase(
        name: 'shot',
        frame: baseFrame.copyWith(ball: baseFrame.ball.copyWith(state: 'shot')),
        activeEvent: miss,
        expectedMapping: MatchSceneEventMapping.shot,
      ),
      _MappingCase(
        name: 'save',
        frame: baseFrame,
        activeEvent: goal.copyWith(
          type: MatchViewerEventType.save,
          bannerText: 'Big save',
          commentary: 'The keeper turns it around the post.',
        ),
        expectedMapping: MatchSceneEventMapping.save,
      ),
      _MappingCase(
        name: 'goal',
        frame: viewState.frames[2],
        activeEvent: goal,
        expectedMapping: MatchSceneEventMapping.goal,
      ),
      _MappingCase(
        name: 'foul',
        frame: baseFrame.copyWith(
          possessionPhase: MatchPossessionPhase.recovery,
        ),
        activeEvent: goal.copyWith(
          type: MatchViewerEventType.foul,
          bannerText: 'Foul on the edge',
          commentary: 'The attack is stopped illegally.',
        ),
        expectedMapping: MatchSceneEventMapping.foul,
      ),
      _MappingCase(
        name: 'booking',
        frame: baseFrame,
        activeEvent: goal.copyWith(
          type: MatchViewerEventType.yellowCard,
          bannerText: 'Yellow card',
          commentary: 'The referee goes to the pocket.',
        ),
        expectedMapping: MatchSceneEventMapping.booking,
      ),
      _MappingCase(
        name: 'substitution',
        frame: baseFrame,
        activeEvent: goal.copyWith(
          type: MatchViewerEventType.substitution,
          bannerText: 'Lagos change',
          commentary: 'Fresh legs arrive in midfield.',
          primaryPlayerName: 'Bassey',
          secondaryPlayerName: 'Emeka',
        ),
        expectedMapping: MatchSceneEventMapping.substitution,
      ),
      _MappingCase(
        name: 'corner',
        frame: setPieceFrame,
        activeEvent: goal.copyWith(
          type: MatchViewerEventType.setPiece,
          bannerText: 'Corner for Lagos',
          commentary: 'Corner on the right-hand side.',
        ),
        expectedMapping: MatchSceneEventMapping.corner,
      ),
      _MappingCase(
        name: 'free kick',
        frame: setPieceFrame.copyWith(eventBanner: 'Free kick Lagos'),
        activeEvent: goal.copyWith(
          type: MatchViewerEventType.setPiece,
          bannerText: 'Free kick Lagos',
          commentary: 'A direct free kick from 24 yards.',
        ),
        expectedMapping: MatchSceneEventMapping.free_kick,
      ),
      _MappingCase(
        name: 'penalty',
        frame: setPieceFrame.copyWith(eventBanner: 'Penalty to Lagos'),
        activeEvent: goal.copyWith(
          type: MatchViewerEventType.penalty,
          bannerText: 'Penalty to Lagos',
          commentary: 'Spot kick awarded after review.',
        ),
        expectedMapping: MatchSceneEventMapping.penalty,
      ),
      _MappingCase(
        name: 'halftime',
        frame: baseFrame.copyWith(phase: MatchViewerPhase.halftime),
        activeEvent: goal.copyWith(
          type: MatchViewerEventType.halftime,
          bannerText: 'Halftime',
          commentary: 'The players head in.',
        ),
        expectedMapping: MatchSceneEventMapping.halftime,
      ),
      _MappingCase(
        name: 'fulltime',
        frame: viewState.lastFrame,
        activeEvent: viewState.events.last,
        expectedMapping: MatchSceneEventMapping.fulltime,
      ),
    ];

    for (final _MappingCase item in cases) {
      final MatchEnginePresentationState presentation = _resolve(
        viewState: viewState,
        package: package,
        frame: item.frame,
        activeEvent: item.activeEvent,
        playbackSeconds: item.frame.timeSeconds,
      );
      expect(
        presentation.eventMapping,
        item.expectedMapping,
        reason: item.name,
      );
    }
  });

  test('scene director drives set-piece, substitution, and replay cameras', () {
    final MatchViewState viewState = buildBroadcastTestViewState();
    final MatchPresentationPackage package = buildBroadcastTestPackage();
    final MatchEvent goal = viewState.events.firstWhere(
      (MatchEvent event) => event.type == MatchViewerEventType.goal,
    );
    final MatchEnginePresentationState corner = _resolve(
      viewState: viewState,
      package: package,
      frame: viewState.frames[2].copyWith(
        phase: MatchViewerPhase.setPiece,
        eventBanner: 'Corner for Lagos',
        ball: viewState.frames[2].ball.copyWith(
          position: viewState.frames[2].ball.position.copyWith(x: 84, y: 14),
        ),
      ),
      activeEvent: goal.copyWith(
        type: MatchViewerEventType.setPiece,
        bannerText: 'Corner for Lagos',
        commentary: 'Corner from the right.',
        primaryPlayerName: 'Nnamdi',
      ),
      playbackSeconds: 12,
    );
    final MatchEnginePresentationState substitution = _resolve(
      viewState: viewState,
      package: package,
      frame: viewState.frames[1],
      activeEvent: goal.copyWith(
        type: MatchViewerEventType.substitution,
        bannerText: 'Lagos change',
        commentary: 'Fresh legs enter midfield.',
        primaryPlayerName: 'Bassey',
        secondaryPlayerName: 'Emeka',
      ),
      playbackSeconds: 24,
    );
    final MatchEnginePresentationState replay = _resolve(
      viewState: viewState,
      package: package,
      frame: viewState.frames[3].copyWith(stage: MatchPlaybackStage.post),
      activeEvent: goal,
      playbackSeconds: 17,
    );
    final MatchEnginePresentationState cornerReplay = _resolve(
      viewState: viewState,
      package: package,
      frame: viewState.frames[3].copyWith(
        phase: MatchViewerPhase.setPiece,
        stage: MatchPlaybackStage.review,
        eventBanner: 'Corner for Lagos',
      ),
      activeEvent: goal.copyWith(
        type: MatchViewerEventType.setPiece,
        bannerText: 'Corner for Lagos',
        primaryPlayerName: 'Nnamdi',
        commentary: '',
      ),
      playbackSeconds: 18,
    );

    expect(corner.sceneState, MatchEngineCameraPreset.set_piece_right);
    expect(corner.banner?.label, 'Corner');
    expect(corner.banner?.detail, 'Nnamdi to deliver from the flag.');
    expect(substitution.sceneState, MatchEngineCameraPreset.tactical_high);
    expect(substitution.banner?.label, 'Substitution');
    expect(substitution.banner?.detail, contains('Emeka on for Bassey'));
    expect(replay.sceneState, MatchEngineCameraPreset.goal_replay);
    expect(replay.isReplayMoment, isTrue);
    expect(cornerReplay.sceneState, MatchEngineCameraPreset.goal_replay);
    expect(cornerReplay.isReplayMoment, isTrue);
    expect(cornerReplay.lowerThirdDetail, contains('Replay'));
  });

  test('scene director produces halftime and full-time recap boards', () {
    final MatchViewState viewState = buildBroadcastTestViewState();
    final MatchPresentationPackage package = buildBroadcastTestPackage();
    final MatchEvent goal = viewState.events.firstWhere(
      (MatchEvent event) => event.type == MatchViewerEventType.goal,
    );
    final MatchEnginePresentationState halftime = _resolve(
      viewState: viewState,
      package: package,
      frame: viewState.frames[2].copyWith(
        phase: MatchViewerPhase.halftime,
        clockMinute: 45,
      ),
      activeEvent: goal.copyWith(
        type: MatchViewerEventType.halftime,
        bannerText: 'Halftime',
        commentary: 'The players head in.',
      ),
      playbackSeconds: 45,
    );
    final MatchEnginePresentationState fulltime = _resolve(
      viewState: viewState,
      package: package,
      frame: viewState.lastFrame,
      activeEvent: viewState.events.last,
      playbackSeconds: 90,
    );

    expect(halftime.sceneState, MatchEngineCameraPreset.halftime_board);
    expect(halftime.summaryBoard?.title, 'Halftime recap');
    expect(halftime.isRecapMoment, isTrue);
    expect(fulltime.sceneState, MatchEngineCameraPreset.fulltime_board);
    expect(fulltime.summaryBoard?.title, 'Full-time recap');
    expect(fulltime.showSummaryBoard, isTrue);
  });

  test('scene director uses backend telemetry for live pressure framing', () {
    final MatchViewState viewState = buildBroadcastTestViewState();
    final MatchPresentationPackage package = buildBroadcastTestPackage();
    final MatchTimelineFrame frame = viewState.frames[1].copyWith(
      possessionPhase: MatchPossessionPhase.boxAttack,
      transitionState: MatchTransitionState.homeBreak,
      dangerZone: 'box',
      pressureIndex: 0.88,
      compactnessHome: 0.72,
      compactnessAway: 0.39,
      frameTags: const <String>['counter', 'box_entry'],
      ball: viewState.frames[1].ball.copyWith(
        position: const MatchViewerPoint(x: 82, y: 44),
      ),
    );

    final MatchEnginePresentationState presentation = _resolve(
      viewState: viewState,
      package: package,
      frame: frame,
      playbackSeconds: frame.timeSeconds,
    );

    expect(presentation.eventMapping, MatchSceneEventMapping.chance_creation);
    expect(
      presentation.sceneState,
      MatchEngineCameraPreset.attacking_third_right,
    );
    expect(presentation.phaseLabel, 'Box attack');
    expect(presentation.stateLabel, 'Counter break');
    expect(presentation.pressureLabel, 'Red Zone');
    expect(presentation.transitionLabel, 'Home Break');
    expect(presentation.dangerLabel, 'Box Threat');
    expect(presentation.scorebugEventLabel, 'Box threat');
    expect(presentation.lowerThirdHeadline, 'Box attack');
    expect(presentation.lowerThirdDetail, contains('reached the box'));
    expect(presentation.homeShape.compactness, closeTo(0.72, 0.001));
    expect(presentation.awayShape.compactness, closeTo(0.39, 0.001));
  });
}

MatchEnginePresentationState _resolve({
  required MatchViewState viewState,
  required MatchPresentationPackage package,
  required MatchTimelineFrame frame,
  MatchEvent? activeEvent,
  required double playbackSeconds,
}) {
  return RealMatchSceneDirector.resolve(
    viewState: viewState,
    frame: frame,
    package: package,
    activeEvent: activeEvent,
    playbackSeconds: playbackSeconds,
  );
}

class _MappingCase {
  const _MappingCase({
    required this.name,
    required this.frame,
    required this.expectedMapping,
    this.activeEvent,
  });

  final String name;
  final MatchTimelineFrame frame;
  final MatchEvent? activeEvent;
  final MatchSceneEventMapping expectedMapping;
}
