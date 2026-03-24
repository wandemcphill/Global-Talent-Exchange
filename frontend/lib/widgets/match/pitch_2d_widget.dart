import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/models/match_viewer_presentation.dart';
import 'package:gte_frontend/widgets/match/ball_widget.dart';
import 'package:gte_frontend/widgets/match/formation_overlay_widget.dart';
import 'package:gte_frontend/widgets/match/player_marker_widget.dart';

class Pitch2dWidget extends StatelessWidget {
  const Pitch2dWidget({
    super.key,
    required this.viewState,
    required this.frame,
    this.showFormationOverlay = true,
    this.presentation,
  });

  final MatchViewState viewState;
  final MatchTimelineFrame frame;
  final bool showFormationOverlay;
  final MatchPitchPresentation? presentation;

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: 105 / 68,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(24),
        child: DecoratedBox(
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: <Color>[
                Color(0xFF0F5132),
                Color(0xFF19683D),
                Color(0xFF0D4A2D),
              ],
            ),
            border: Border.all(color: Colors.white.withValues(alpha: 0.14)),
          ),
          child: LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final MatchPitchPresentation activePresentation =
                  presentation ?? _fallbackPresentation(frame);
              final double shortestSide = constraints.biggest.shortestSide;
              final double markerSize =
                  (shortestSide * 0.06).clamp(18, 28).toDouble();
              final double ballSize =
                  (shortestSide * 0.027).clamp(8, 14).toDouble();
              return ClipRect(
                child: Transform(
                  alignment: Alignment.center,
                  transform: _perspectiveTransform(
                    constraints.biggest,
                    activePresentation,
                  ),
                  child: DecoratedBox(
                    decoration: const BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: <Color>[
                          Color(0xFF0F5132),
                          Color(0xFF19683D),
                          Color(0xFF0D4A2D),
                        ],
                      ),
                    ),
                    child: Stack(
                      fit: StackFit.expand,
                      children: <Widget>[
                        RepaintBoundary(
                          child: CustomPaint(
                            painter: _PitchPainter(),
                          ),
                        ),
                        if (showFormationOverlay)
                          IgnorePointer(
                            child: RepaintBoundary(
                              child: FormationOverlayWidget(
                                players: frame.players,
                              ),
                            ),
                          ),
                        ...frame.players.map(
                          (MatchViewerPlayerFrame player) {
                            final MatchViewerTeam team =
                                viewState.teamForSide(player.side);
                            final MatchViewerPoint position = activePresentation
                                .resolvePlayerPosition(player);
                            final Offset offset = _offsetForPoint(
                              position,
                              constraints.biggest,
                              markerSize,
                            );
                            if (!player.active &&
                                player.state !=
                                    MatchViewerPlayerState.sentOff) {
                              return const SizedBox.shrink();
                            }
                            return Positioned(
                              left: offset.dx,
                              top: offset.dy,
                              child: PlayerMarkerWidget(
                                player: player,
                                team: team,
                                size: markerSize,
                              ),
                            );
                          },
                        ),
                        Positioned(
                          left: _offsetForPoint(
                            frame.ball.position,
                            constraints.biggest,
                            ballSize,
                          ).dx,
                          top: _offsetForPoint(
                            frame.ball.position,
                            constraints.biggest,
                            ballSize,
                          ).dy,
                          child: BallWidget(ball: frame.ball, size: ballSize),
                        ),
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}

MatchPitchPresentation _fallbackPresentation(MatchTimelineFrame frame) {
  final double ballPanX =
      ((frame.ball.position.x - 50) / 100).clamp(-0.18, 0.18).toDouble();
  final double ballPanY =
      ((frame.ball.position.y - 50) / 160).clamp(-0.12, 0.12).toDouble();
  switch (frame.cameraPreset) {
    case MatchCameraPreset.attackPush:
      return MatchPitchPresentation(
        cameraPreset: BroadcastCameraPreset.attackZoom,
        scale: 1.12,
        panX: ballPanX,
        panY: -0.08 + ballPanY,
        motionSeedKey: frame.id,
        enableMicroVariation: true,
      );
    case MatchCameraPreset.boxZoom:
      return MatchPitchPresentation(
        cameraPreset: BroadcastCameraPreset.attackZoom,
        scale: 1.18,
        panX: ballPanX * 1.2,
        panY: -0.1 + ballPanY,
        motionSeedKey: frame.id,
        enableMicroVariation: true,
      );
    case MatchCameraPreset.goalCelebration:
      return MatchPitchPresentation(
        cameraPreset: BroadcastCameraPreset.goalZoom,
        scale: 1.24,
        panX: ballPanX * 1.35,
        panY: -0.12 + ballPanY,
        motionSeedKey: frame.id,
        enableMicroVariation: true,
      );
    case MatchCameraPreset.assistantFlag:
      return MatchPitchPresentation(
        cameraPreset: BroadcastCameraPreset.attackZoom,
        scale: 1.1,
        panX: ballPanX.sign * 0.15,
        panY: -0.06,
        motionSeedKey: frame.id,
        enableMicroVariation: false,
      );
    case MatchCameraPreset.varReplay:
      return MatchPitchPresentation(
        cameraPreset: BroadcastCameraPreset.replayCamera,
        scale: 1.28,
        panX: ballPanX * 1.4,
        panY: -0.12 + ballPanY,
        motionSeedKey: frame.id,
        enableMicroVariation: false,
      );
    case MatchCameraPreset.broadcast:
      return const MatchPitchPresentation(
        cameraPreset: BroadcastCameraPreset.broadcast,
        scale: 1.02,
        panX: 0,
        panY: -0.04,
        motionSeedKey: 'broadcast',
        enableMicroVariation: false,
      );
  }
}

Matrix4 _perspectiveTransform(
  Size size,
  MatchPitchPresentation presentation,
) {
  // ignore: deprecated_member_use
  return Matrix4.identity()
    ..translate(
      presentation.panX * size.width,
      presentation.panY * size.height,
    )
    ..setEntry(3, 2, 0.0012)
    ..rotateX(0.96)
    // ignore: deprecated_member_use
    ..scale(presentation.scale, presentation.scale);
}

Offset _offsetForPoint(
  MatchViewerPoint point,
  Size size,
  double objectSize,
) {
  return Offset(
    ((point.x / 100) * size.width) - (objectSize * 0.9),
    ((point.y / 100) * size.height) - (objectSize * 0.9),
  );
}

class _PitchPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final Paint stripePaint = Paint()..style = PaintingStyle.fill;
    for (int index = 0; index < 10; index += 1) {
      stripePaint.color =
          index.isEven ? const Color(0x11000000) : const Color(0x06FFFFFF);
      final double top = size.height * (index / 10);
      canvas.drawRect(
        Rect.fromLTWH(0, top, size.width, size.height / 10),
        stripePaint,
      );
    }

    final Paint linePaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2
      ..color = Colors.white.withValues(alpha: 0.88);
    final Paint spotPaint = Paint()
      ..style = PaintingStyle.fill
      ..color = Colors.white.withValues(alpha: 0.88);

    final Rect outer = Rect.fromLTWH(8, 8, size.width - 16, size.height - 16);
    canvas.drawRect(outer, linePaint);
    canvas.drawLine(
      Offset(size.width / 2, 8),
      Offset(size.width / 2, size.height - 8),
      linePaint,
    );
    canvas.drawCircle(
      Offset(size.width / 2, size.height / 2),
      size.height * 0.14,
      linePaint,
    );
    canvas.drawCircle(
      Offset(size.width / 2, size.height / 2),
      2.8,
      spotPaint,
    );

    final Rect leftBox = Rect.fromLTWH(
        8, size.height * 0.21, size.width * 0.16, size.height * 0.58);
    final Rect rightBox = Rect.fromLTWH(size.width - 8 - (size.width * 0.16),
        size.height * 0.21, size.width * 0.16, size.height * 0.58);
    final Rect leftSix = Rect.fromLTWH(
        8, size.height * 0.34, size.width * 0.07, size.height * 0.32);
    final Rect rightSix = Rect.fromLTWH(size.width - 8 - (size.width * 0.07),
        size.height * 0.34, size.width * 0.07, size.height * 0.32);
    canvas.drawRect(leftBox, linePaint);
    canvas.drawRect(rightBox, linePaint);
    canvas.drawRect(leftSix, linePaint);
    canvas.drawRect(rightSix, linePaint);
    canvas.drawCircle(
        Offset(size.width * 0.115, size.height / 2), 2.6, spotPaint);
    canvas.drawCircle(
        Offset(size.width * 0.885, size.height / 2), 2.6, spotPaint);

    final Rect leftGoal =
        Rect.fromLTWH(2, size.height * 0.42, 6, size.height * 0.16);
    final Rect rightGoal = Rect.fromLTWH(
        size.width - 8, size.height * 0.42, 6, size.height * 0.16);
    canvas.drawRect(leftGoal, linePaint);
    canvas.drawRect(rightGoal, linePaint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
