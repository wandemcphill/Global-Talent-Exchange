import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/widgets/match/ball_widget.dart';
import 'package:gte_frontend/widgets/match/formation_overlay_widget.dart';
import 'package:gte_frontend/widgets/match/player_marker_widget.dart';

class Pitch2dWidget extends StatelessWidget {
  const Pitch2dWidget({
    super.key,
    required this.viewState,
    required this.frame,
    this.showFormationOverlay = true,
  });

  final MatchViewState viewState;
  final MatchTimelineFrame frame;
  final bool showFormationOverlay;

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
              final double shortestSide = constraints.biggest.shortestSide;
              final double markerSize =
                  (shortestSide * 0.06).clamp(18, 28).toDouble();
              final double ballSize =
                  (shortestSide * 0.027).clamp(8, 14).toDouble();
              return Stack(
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
                        child: FormationOverlayWidget(players: frame.players),
                      ),
                    ),
                  ...frame.players.map(
                    (MatchViewerPlayerFrame player) {
                      final MatchViewerTeam team =
                          viewState.teamForSide(player.side);
                      final Offset offset = _offsetForPoint(
                        player.position,
                        constraints.biggest,
                        markerSize,
                      );
                      if (!player.active &&
                          player.state != MatchViewerPlayerState.sentOff) {
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
                            frame.ball.position, constraints.biggest, ballSize)
                        .dx,
                    top: _offsetForPoint(
                            frame.ball.position, constraints.biggest, ballSize)
                        .dy,
                    child: BallWidget(ball: frame.ball, size: ballSize),
                  ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }
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
