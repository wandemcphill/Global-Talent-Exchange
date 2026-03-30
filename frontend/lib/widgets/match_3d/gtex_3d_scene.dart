import 'dart:async';

import 'package:flutter/material.dart';
import 'package:gte_frontend/models/ball_entity.dart' as runtime_ball;
import 'package:gte_frontend/models/match_3d_scene_graph.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/models/player_entity.dart' as runtime_player;
import 'package:gte_frontend/models/real_match_engine_presentation.dart';
import 'package:gte_frontend/services/match_3d_bridge.dart';
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
    this.cameraPreset = MatchEngineCameraPreset.tactical_high,
    this.bridge,
    this.runtimePlayers,
    this.runtimeBall,
  });

  static const Key aspectRatioKey = Key('gtex_3d_scene_aspect_ratio');
  static const Key paintKey = Key('gtex_3d_scene_paint');

  final MatchViewState viewState;
  final MatchTimelineFrame frame;
  final MatchEvent? activeEvent;
  final MatchEngineCameraPreset cameraPreset;
  final Match3DBridge? bridge;
  final Iterable<runtime_player.PlayerEntity>? runtimePlayers;
  final runtime_ball.BallEntity? runtimeBall;

  static Match3dSceneGraph describeGraph({
    required MatchViewState viewState,
    required MatchTimelineFrame frame,
    MatchEvent? activeEvent,
    MatchEngineCameraPreset cameraPreset =
        MatchEngineCameraPreset.tactical_high,
    Iterable<runtime_player.PlayerEntity>? runtimePlayers,
    runtime_ball.BallEntity? runtimeBall,
  }) {
    return Match3dSceneManager().buildScene(
      viewState: viewState,
      frame: frame,
      activeEvent: activeEvent,
      requestedCameraPreset: cameraPreset,
      runtimePlayers: runtimePlayers,
      runtimeBall: runtimeBall,
    );
  }

  static Gtex3dSceneSnapshot describeScene({
    required MatchViewState viewState,
    required MatchTimelineFrame frame,
    MatchEvent? activeEvent,
    MatchEngineCameraPreset cameraPreset =
        MatchEngineCameraPreset.tactical_high,
    Size size = const Size(1050, 680),
    Iterable<runtime_player.PlayerEntity>? runtimePlayers,
    runtime_ball.BallEntity? runtimeBall,
  }) {
    final Match3dSceneGraph sceneGraph = describeGraph(
      viewState: viewState,
      frame: frame,
      activeEvent: activeEvent,
      cameraPreset: cameraPreset,
      runtimePlayers: runtimePlayers,
      runtimeBall: runtimeBall,
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

class _Gtex3dSceneState extends State<Gtex3dScene>
    with SingleTickerProviderStateMixin {
  late final AnimationController _cameraTransitionController;
  MatchEngineCameraPreset? _previousCameraPreset;

  @override
  void initState() {
    super.initState();
    _cameraTransitionController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1),
      value: 1,
    );
    _syncBridge();
  }

  @override
  void didUpdateWidget(covariant Gtex3dScene oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.cameraPreset != widget.cameraPreset) {
      _previousCameraPreset = oldWidget.cameraPreset;
      _cameraTransitionController.duration = Duration(
        milliseconds: _transitionDurationMs(widget.cameraPreset),
      );
      _cameraTransitionController.forward(from: 0);
    }
    if (oldWidget.viewState != widget.viewState ||
        oldWidget.frame != widget.frame ||
        oldWidget.activeEvent != widget.activeEvent ||
        oldWidget.cameraPreset != widget.cameraPreset ||
        oldWidget.bridge != widget.bridge ||
        oldWidget.runtimeBall != widget.runtimeBall ||
        oldWidget.runtimePlayers != widget.runtimePlayers) {
      _syncBridge();
    }
  }

  @override
  void dispose() {
    _cameraTransitionController.dispose();
    super.dispose();
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
      runtimePlayers: widget.runtimePlayers,
      runtimeBall: widget.runtimeBall,
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
                repaint: _cameraTransitionController,
                viewState: widget.viewState,
                frame: widget.frame,
                activeEvent: widget.activeEvent,
                cameraPreset: widget.cameraPreset,
                previousCameraPreset:
                    _cameraTransitionController.isAnimating
                        ? _previousCameraPreset
                        : null,
                cameraTransition: _cameraTransitionController.value,
                runtimePlayers: widget.runtimePlayers,
                runtimeBall: widget.runtimeBall,
              ),
              child: const SizedBox.expand(),
            ),
          ),
        ),
      ),
    );
  }

  int _transitionDurationMs(MatchEngineCameraPreset preset) {
    return switch (preset) {
      MatchEngineCameraPreset.goal_replay => 420,
      MatchEngineCameraPreset.set_piece_left ||
      MatchEngineCameraPreset.set_piece_right => 360,
      MatchEngineCameraPreset.halftime_board ||
      MatchEngineCameraPreset.fulltime_board => 440,
      _ => 300,
    };
  }
}

class _Gtex3dScenePainter extends CustomPainter {
  const _Gtex3dScenePainter({
    Listenable? repaint,
    required this.viewState,
    required this.frame,
    required this.activeEvent,
    required this.cameraPreset,
    required this.previousCameraPreset,
    required this.cameraTransition,
    required this.runtimePlayers,
    required this.runtimeBall,
  }) : super(repaint: repaint);

  final MatchViewState viewState;
  final MatchTimelineFrame frame;
  final MatchEvent? activeEvent;
  final MatchEngineCameraPreset cameraPreset;
  final MatchEngineCameraPreset? previousCameraPreset;
  final double cameraTransition;
  final Iterable<runtime_player.PlayerEntity>? runtimePlayers;
  final runtime_ball.BallEntity? runtimeBall;

  @override
  void paint(Canvas canvas, Size size) {
    final Match3dSceneGraph sceneGraph = Gtex3dScene.describeGraph(
      viewState: viewState,
      frame: frame,
      activeEvent: activeEvent,
      cameraPreset: cameraPreset,
      runtimePlayers: runtimePlayers,
      runtimeBall: runtimeBall,
    );
    final MatchEngineCameraPreset currentPreset =
        sceneGraph.camera.projectionPreset;
    final PitchProjection projection =
        previousCameraPreset != null && cameraTransition < 1
            ? PitchProjection.lerp(
              PitchEntity.project(size, cameraPreset: previousCameraPreset!),
              PitchEntity.project(size, cameraPreset: currentPreset),
              Curves.easeInOutCubicEmphasized.transform(
                cameraTransition.clamp(0, 1).toDouble(),
              ),
            )
            : PitchEntity.project(size, cameraPreset: currentPreset);
    final PitchEntity pitch = PitchEntity(projection: projection);
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
    final BallEntity ball = BallEntity.fromNode(
      node: sceneGraph.ballNode,
      payload: ballPayload,
      projection: projection,
    );

    pitch.paint(canvas);

    final List<_DepthRenderable> renderables = <_DepthRenderable>[
      for (final PlayerEntity player in players)
        _DepthRenderable(depth: player.depth, order: 0, paint: player.paint),
      _DepthRenderable(depth: ball.depth, order: 1, paint: ball.paint),
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
        oldDelegate.cameraPreset != cameraPreset ||
        oldDelegate.previousCameraPreset != previousCameraPreset ||
        oldDelegate.runtimePlayers != runtimePlayers ||
        oldDelegate.runtimeBall != runtimeBall;
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
