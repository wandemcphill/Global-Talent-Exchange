import 'dart:async';

import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match_3d_scene_graph.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/services/match_3d_bridge.dart';
import 'package:gte_frontend/services/match_3d_monetization_service.dart';
import 'package:gte_frontend/services/match_3d_scene_manager.dart';
import 'package:gte_frontend/widgets/match_3d/entities/ball_entity.dart';
import 'package:gte_frontend/widgets/match_3d/entities/pitch_entity.dart';
import 'package:gte_frontend/widgets/match_3d/entities/player_entity.dart';

class Gtex3dSceneSnapshot {
  const Gtex3dSceneSnapshot({
    required this.sceneGraph,
    required this.pitch,
    required this.players,
    required this.ball,
  });

  final Match3dSceneGraph sceneGraph;
  final PitchEntity pitch;
  final List<PlayerEntity> players;
  final BallEntity ball;
}

class Gtex3dScene extends StatefulWidget {
  const Gtex3dScene({
    super.key,
    required this.viewState,
    required this.frame,
    this.activeEvent,
    this.cameraPreset = Match3dCameraPreset.broadcast,
    this.bridge,
  });

  static const Key aspectRatioKey = Key('gtex_3d_scene_aspect_ratio');
  static const Key paintKey = Key('gtex_3d_scene_paint');

  final MatchViewState viewState;
  final MatchTimelineFrame frame;
  final MatchEvent? activeEvent;
  final Match3dCameraPreset cameraPreset;
  final Match3DBridge? bridge;

  static Match3dSceneGraph describeGraph({
    required MatchViewState viewState,
    required MatchTimelineFrame frame,
    MatchEvent? activeEvent,
    Match3dCameraPreset cameraPreset = Match3dCameraPreset.broadcast,
  }) {
    return Match3dSceneManager().buildScene(
      viewState: viewState,
      frame: frame,
      activeEvent: activeEvent,
      requestedCameraPreset: cameraPreset,
    );
  }

  static Gtex3dSceneSnapshot describeScene({
    required MatchViewState viewState,
    required MatchTimelineFrame frame,
    MatchEvent? activeEvent,
    Match3dCameraPreset cameraPreset = Match3dCameraPreset.broadcast,
    Size size = const Size(1050, 680),
  }) {
    final Match3dSceneGraph sceneGraph = describeGraph(
      viewState: viewState,
      frame: frame,
      activeEvent: activeEvent,
      cameraPreset: cameraPreset,
    );
    final PitchProjection projection = PitchEntity.project(
      size,
      cameraPreset: sceneGraph.camera.projectionPreset,
    );
    final List<PlayerEntity> players = PlayerEntity.buildAll(
      viewState: viewState,
      sceneGraph: sceneGraph,
      projection: projection,
    )..sort(
      (PlayerEntity left, PlayerEntity right) =>
          left.depth.compareTo(right.depth),
    );
    final Match3dBallPayload ballPayload =
        sceneGraph.ballNode.payload as Match3dBallPayload;
    return Gtex3dSceneSnapshot(
      sceneGraph: sceneGraph,
      pitch: PitchEntity(projection: projection),
      players: players,
      ball: BallEntity.fromNode(
        node: sceneGraph.ballNode,
        payload: ballPayload,
        projection: projection,
      ),
    );
  }

  @override
  State<Gtex3dScene> createState() => _Gtex3dSceneState();
}

class _Gtex3dSceneState extends State<Gtex3dScene> {
  @override
  void initState() {
    super.initState();
    _syncBridge();
  }

  @override
  void didUpdateWidget(covariant Gtex3dScene oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.viewState != widget.viewState ||
        oldWidget.frame != widget.frame ||
        oldWidget.activeEvent != widget.activeEvent ||
        oldWidget.cameraPreset != widget.cameraPreset ||
        oldWidget.bridge != widget.bridge) {
      _syncBridge();
    }
  }

  void _syncBridge() {
    final Match3DBridge? bridge = widget.bridge;
    if (bridge == null) {
      return;
    }
    final Match3dSceneGraph sceneGraph = Gtex3dScene.describeGraph(
      viewState: widget.viewState,
      frame: widget.frame,
      activeEvent: widget.activeEvent,
      cameraPreset: widget.cameraPreset,
    );
    unawaited(
      bridge.syncFrame(sceneGraph: sceneGraph, activeEvent: widget.activeEvent),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      key: Gtex3dScene.aspectRatioKey,
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
              key: Gtex3dScene.paintKey,
              isComplex: true,
              willChange: true,
              painter: _Gtex3dScenePainter(
                viewState: widget.viewState,
                frame: widget.frame,
                activeEvent: widget.activeEvent,
                cameraPreset: widget.cameraPreset,
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
    required this.activeEvent,
    required this.cameraPreset,
  });

  final MatchViewState viewState;
  final MatchTimelineFrame frame;
  final MatchEvent? activeEvent;
  final Match3dCameraPreset cameraPreset;

  @override
  void paint(Canvas canvas, Size size) {
    final Gtex3dSceneSnapshot scene = Gtex3dScene.describeScene(
      viewState: viewState,
      frame: frame,
      activeEvent: activeEvent,
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
        oldDelegate.activeEvent != activeEvent ||
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
