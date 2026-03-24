import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/services/match_3d_monetization_service.dart';
import 'package:gte_frontend/widgets/match_3d/entities/ball_entity.dart';
import 'package:gte_frontend/widgets/match_3d/entities/pitch_entity.dart';
import 'package:gte_frontend/widgets/match_3d/entities/player_entity.dart';

class Gtex3dSceneSnapshot {
  const Gtex3dSceneSnapshot({
    required this.pitch,
    required this.players,
    required this.ball,
  });

  final PitchEntity pitch;
  final List<PlayerEntity> players;
  final BallEntity ball;
}

class Gtex3dScene extends StatelessWidget {
  const Gtex3dScene({
    super.key,
    required this.viewState,
    required this.frame,
    this.cameraPreset = Match3dCameraPreset.broadcast,
  });

  static const Key aspectRatioKey = Key('gtex_3d_scene_aspect_ratio');
  static const Key paintKey = Key('gtex_3d_scene_paint');

  final MatchViewState viewState;
  final MatchTimelineFrame frame;
  final Match3dCameraPreset cameraPreset;

  static Gtex3dSceneSnapshot describeScene({
    required MatchViewState viewState,
    required MatchTimelineFrame frame,
    Match3dCameraPreset cameraPreset = Match3dCameraPreset.broadcast,
    Size size = const Size(1050, 680),
  }) {
    final PitchProjection projection = PitchEntity.project(
      size,
      cameraPreset: cameraPreset,
    );
    final List<PlayerEntity> players =
        PlayerEntity.buildAll(
          viewState: viewState,
          frame: frame,
          projection: projection,
        )..sort(
          (PlayerEntity left, PlayerEntity right) =>
              left.depth.compareTo(right.depth),
        );
    return Gtex3dSceneSnapshot(
      pitch: PitchEntity(projection: projection),
      players: players,
      ball: BallEntity.fromFrame(ball: frame.ball, projection: projection),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      key: aspectRatioKey,
      aspectRatio: PitchEntity.aspectRatio,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(24),
        child: DecoratedBox(
          decoration: BoxDecoration(
            border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
            gradient: const LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: <Color>[Color(0xFF0D1A22), Color(0xFF09131B)],
            ),
          ),
          child: RepaintBoundary(
            child: CustomPaint(
              key: paintKey,
              isComplex: true,
              willChange: true,
              painter: _Gtex3dScenePainter(
                viewState: viewState,
                frame: frame,
                cameraPreset: cameraPreset,
              ),
              child: const SizedBox.expand(),
            ),
          ),
        ),
      ),
    );
  }
}

class _Gtex3dScenePainter extends CustomPainter {
  const _Gtex3dScenePainter({
    required this.viewState,
    required this.frame,
    required this.cameraPreset,
  });

  final MatchViewState viewState;
  final MatchTimelineFrame frame;
  final Match3dCameraPreset cameraPreset;

  @override
  void paint(Canvas canvas, Size size) {
    final Gtex3dSceneSnapshot scene = Gtex3dScene.describeScene(
      viewState: viewState,
      frame: frame,
      cameraPreset: cameraPreset,
      size: size,
    );

    scene.pitch.paint(canvas);

    final List<_DepthRenderable> renderables = <_DepthRenderable>[
      for (final PlayerEntity player in scene.players)
        _DepthRenderable(depth: player.depth, order: 0, paint: player.paint),
      _DepthRenderable(
        depth: scene.ball.depth,
        order: 1,
        paint: scene.ball.paint,
      ),
    ]..sort(_compareRenderables);

    for (final _DepthRenderable renderable in renderables) {
      renderable.paint(canvas);
    }
  }

  @override
  bool shouldRepaint(covariant _Gtex3dScenePainter oldDelegate) {
    return oldDelegate.viewState != viewState ||
        oldDelegate.frame != frame ||
        oldDelegate.cameraPreset != cameraPreset;
  }
}

class _DepthRenderable {
  const _DepthRenderable({
    required this.depth,
    required this.order,
    required this.paint,
  });

  final double depth;
  final int order;
  final void Function(Canvas canvas) paint;
}

int _compareRenderables(_DepthRenderable left, _DepthRenderable right) {
  final int depthCompare = left.depth.compareTo(right.depth);
  if (depthCompare != 0) {
    return depthCompare;
  }
  return left.order.compareTo(right.order);
}
