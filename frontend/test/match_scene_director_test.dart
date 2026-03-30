import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/match/presentation/match_scene_director.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';

import 'support/gtex_match_broadcast_fixture.dart';

void main() {
  test('scene director sequences the pre-match broadcast package', () {
    final viewState = buildBroadcastTestViewState();
    final MatchTimelineFrame frame = viewState.frames.first;
    final MatchEvent kickoff = viewState.events.first;

    expect(
      MatchSceneDirector.resolveBroadcastScene(
        frame: frame,
        activeEvent: kickoff,
        packageSeconds: 1.0,
      ),
      BroadcastPackageScene.titleBanner,
    );
    expect(
      MatchSceneDirector.resolveBroadcastScene(
        frame: frame,
        activeEvent: kickoff,
        packageSeconds: 4.0,
      ),
      BroadcastPackageScene.rosterCard,
    );
    expect(
      MatchSceneDirector.resolveBroadcastScene(
        frame: frame,
        activeEvent: kickoff,
        packageSeconds: 7.0,
      ),
      BroadcastPackageScene.homeFormation,
    );
    expect(
      MatchSceneDirector.resolveBroadcastScene(
        frame: frame,
        activeEvent: kickoff,
        packageSeconds: 9.0,
      ),
      BroadcastPackageScene.awayFormation,
    );
    expect(
      MatchSceneDirector.resolveBroadcastScene(
        frame: frame,
        activeEvent: kickoff,
        packageSeconds: 12.0,
      ),
      BroadcastPackageScene.contextBoard,
    );
    expect(
      MatchSceneDirector.resolveBroadcastScene(
        frame: frame,
        activeEvent: kickoff,
        packageSeconds: 15.0,
      ),
      BroadcastPackageScene.reactions,
    );
    expect(
      MatchSceneDirector.resolveBroadcastScene(
        frame: frame,
        activeEvent: kickoff,
        packageSeconds: 20.0,
      ),
      BroadcastPackageScene.kickoffLive,
    );
  });

  test(
    'scene director switches to halftime and fulltime boards from phase',
    () {
      final viewState = buildBroadcastTestViewState();
      final MatchTimelineFrame halftimeFrame = viewState.frames.first.copyWith(
        phase: MatchViewerPhase.halftime,
      );
      final MatchTimelineFrame fulltimeFrame = viewState.frames.last;

      expect(
        MatchSceneDirector.resolveBroadcastScene(
          frame: halftimeFrame,
          packageSeconds: 20.0,
        ),
        BroadcastPackageScene.halftimeBoard,
      );
      expect(
        MatchSceneDirector.resolveBroadcastScene(
          frame: fulltimeFrame,
          packageSeconds: 20.0,
        ),
        BroadcastPackageScene.fulltimeBoard,
      );
    },
  );

  test('scene director resolves event-driven camera states', () {
    final viewState = buildBroadcastTestViewState();
    final MatchEvent goalEvent = viewState.events.firstWhere(
      (MatchEvent item) => item.type == MatchViewerEventType.goal,
    );
    final MatchTimelineFrame replayFrame = viewState.frames[3].copyWith(
      stage: MatchPlaybackStage.post,
    );
    final MatchEvent setPieceEvent = goalEvent.copyWith(
      type: MatchViewerEventType.setPiece,
      teamId: 'home',
    );
    final MatchTimelineFrame setPieceFrame = viewState.frames[2].copyWith(
      phase: MatchViewerPhase.setPiece,
    );

    expect(
      MatchSceneDirector.resolveCameraState(
        frame: replayFrame,
        activeEvent: goalEvent,
      ),
      MatchSimCameraState.goalReplayAngle,
    );
    expect(
      MatchSceneDirector.resolveCameraState(
        frame: setPieceFrame,
        activeEvent: setPieceEvent,
      ),
      MatchSimCameraState.setPieceRight,
    );
  });
}
