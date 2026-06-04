import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';
import 'package:gte_frontend/features/match_center/models/real_match_engine_presentation.dart';
import 'package:gte_frontend/features/3d/models/match_3d_scene_graph.dart';
import 'package:gte_frontend/features/match_center/models/match_view_state.dart';
import 'package:gte_frontend/features/3d/widgets/match_3d/gtex_3d_scene.dart';

import 'support/gtex_match_broadcast_fixture.dart';

void main() {
  test(
    'scene graph uses backend pressure telemetry for camera and experience',
    () {
      final MatchViewState viewState =
          buildBackendAuthored3dQuarantineViewState();
      expect(viewState.source, 'backend-authored-3d-quarantine');
      expect(
        viewState.frames.every(
          (MatchTimelineFrame frame) => !frame.isSynthetic,
        ),
        isTrue,
      );
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
          ownerPlayerId: 'home-9',
        ),
      );

      expect(frame.players, hasLength(22));
      expect(frame.isSynthetic, isFalse);

      final Match3dSceneGraph sceneGraph = Gtex3dScene.describeGraph(
        viewState: viewState,
        frame: frame,
        cameraPreset: MatchEngineCameraPreset.tactical_high,
      );

      final Match3dMotionPrediction homeNinePrediction = sceneGraph
          .experience
          .motionPredictions
          .firstWhere(
            (Match3dMotionPrediction item) => item.entityId == 'player:home-9',
          );

      expect(
        sceneGraph.camera.projectionPreset,
        MatchEngineCameraPreset.attacking_third_left,
      );
      expect(sceneGraph.experience.crowd.profile, 'explosive');
      expect(sceneGraph.experience.commentary.intensity, greaterThan(0.7));
      expect(sceneGraph.homeShape.compactness, closeTo(0.72, 0.001));
      expect(sceneGraph.awayShape.compactness, closeTo(0.39, 0.001));
      expect(homeNinePrediction.pressure, greaterThan(0.55));
      expect(homeNinePrediction.shootWeight, greaterThan(0.2));
    },
  );

  test('scene graph uses backend restart telemetry for set-piece framing', () {
    final MatchViewState viewState =
        buildBackendAuthored3dQuarantineViewState();
    expect(viewState.source, 'backend-authored-3d-quarantine');
    final MatchTimelineFrame frame = viewState.frames[1].copyWith(
      phase: MatchViewerPhase.setPiece,
      possessionPhase: MatchPossessionPhase.setPiece,
      transitionState: MatchTransitionState.homeReset,
      dangerZone: 'final_third',
      pressureIndex: 0.64,
      frameTags: const <String>['set_piece'],
      ball: viewState.frames[1].ball.copyWith(
        position: const MatchViewerPoint(x: 78, y: 58),
        ownerPlayerId: 'home-9',
        state: 'placed',
      ),
    );

    expect(frame.players, hasLength(22));
    expect(frame.isSynthetic, isFalse);

    final Match3dSceneGraph sceneGraph = Gtex3dScene.describeGraph(
      viewState: viewState,
      frame: frame,
      cameraPreset: MatchEngineCameraPreset.tactical_high,
    );

    expect(
      sceneGraph.camera.projectionPreset,
      MatchEngineCameraPreset.set_piece_right,
    );
    expect(sceneGraph.experience.commentary.tone, 'set_piece');
    expect(sceneGraph.experience.crowd.profile, 'charged');
  });
}
