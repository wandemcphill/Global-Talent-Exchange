import 'package:flutter/material.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';
import 'package:gte_frontend/features/match_center/widgets/pitch_2d_telemetry.dart';

@immutable
class FormationOverlayStyle {
  const FormationOverlayStyle({
    required this.pressureIndex,
    required this.homeCompactness,
    required this.awayCompactness,
    required this.possessionSide,
    required this.accentColor,
    required this.showTransitionGuide,
    required this.showSetPieceGuide,
  });

  factory FormationOverlayStyle.fromFrame(
    MatchTimelineFrame frame,
    Pitch2dTelemetryStyle telemetryStyle,
  ) {
    return FormationOverlayStyle(
      pressureIndex: telemetryStyle.pressureIndex,
      homeCompactness: telemetryStyle.homeCompactness,
      awayCompactness: telemetryStyle.awayCompactness,
      possessionSide: frame.possessionSide,
      accentColor: telemetryStyle.accentColor,
      showTransitionGuide: telemetryStyle.showTransitionLane,
      showSetPieceGuide: telemetryStyle.showSetPieceOverlay,
    );
  }

  final double pressureIndex;
  final double homeCompactness;
  final double awayCompactness;
  final MatchViewerSide possessionSide;
  final Color accentColor;
  final bool showTransitionGuide;
  final bool showSetPieceGuide;
}

class FormationOverlayWidget extends StatelessWidget {
  const FormationOverlayWidget({
    super.key,
    required this.frame,
    required this.players,
    required this.style,
  });

  final MatchTimelineFrame frame;
  final List<MatchViewerPlayerFrame> players;
  final FormationOverlayStyle style;

  static FormationOverlayStyle describeStyle(
    MatchTimelineFrame frame,
    Pitch2dTelemetryStyle telemetryStyle,
  ) {
    return FormationOverlayStyle.fromFrame(frame, telemetryStyle);
  }

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      painter: _FormationOverlayPainter(
        frame: frame,
        players: players,
        style: style,
      ),
      size: Size.infinite,
    );
  }
}

class _FormationOverlayPainter extends CustomPainter {
  const _FormationOverlayPainter({
    required this.frame,
    required this.players,
    required this.style,
  });

  final MatchTimelineFrame frame;
  final List<MatchViewerPlayerFrame> players;
  final FormationOverlayStyle style;

  @override
  void paint(Canvas canvas, Size size) {
    _drawShapeGuides(canvas, size, MatchViewerSide.home);
    _drawShapeGuides(canvas, size, MatchViewerSide.away);
    for (final MatchViewerPlayerFrame player in players) {
      if (!player.active) {
        continue;
      }
      final bool isBallOwner = frame.ball.ownerPlayerId == player.playerId;
      final double compactness =
          player.side == MatchViewerSide.home
              ? style.homeCompactness
              : style.awayCompactness;
      final bool isPossessionSide = player.side == style.possessionSide;
      final Color lineColor = _baseSideColor(player.side).withValues(
        alpha: 0.20 + (compactness * 0.10) + (isPossessionSide ? 0.06 : 0),
      );
      final Paint guidePaint =
          Paint()
            ..style = PaintingStyle.stroke
            ..strokeWidth = 1.1 + (style.pressureIndex * 0.8)
            ..color = lineColor;
      final Offset center = Offset(
        (player.anchorPosition.x / 100) * size.width,
        (player.anchorPosition.y / 100) * size.height,
      );
      canvas.drawCircle(
        center,
        player.line == MatchPlayerLine.goalkeeper ? 7.2 : 5.4,
        guidePaint,
      );
      if (player.highlighted || isBallOwner) {
        final Paint focusPaint =
            Paint()
              ..style = PaintingStyle.stroke
              ..strokeWidth = 1.4
              ..color = style.accentColor.withValues(
                alpha: isBallOwner ? 0.52 : 0.34,
              );
        canvas.drawCircle(
          center,
          player.line == MatchPlayerLine.goalkeeper ? 10 : 8,
          focusPaint,
        );
      }
    }
  }

  void _drawShapeGuides(Canvas canvas, Size size, MatchViewerSide side) {
    final double compactness =
        side == MatchViewerSide.home
            ? style.homeCompactness
            : style.awayCompactness;
    final bool isPossessionSide = side == style.possessionSide;
    for (final MatchPlayerLine line in MatchPlayerLine.values) {
      final List<MatchViewerPlayerFrame> linePlayers = players
          .where((MatchViewerPlayerFrame player) => player.side == side)
          .where((MatchViewerPlayerFrame player) => player.active)
          .where((MatchViewerPlayerFrame player) => player.line == line)
          .toList(growable: false);
      if (linePlayers.isEmpty) {
        continue;
      }
      double minX = double.infinity;
      double maxX = double.negativeInfinity;
      double minY = double.infinity;
      double maxY = double.negativeInfinity;
      for (final MatchViewerPlayerFrame player in linePlayers) {
        minX = minX < player.anchorPosition.x ? minX : player.anchorPosition.x;
        maxX = maxX > player.anchorPosition.x ? maxX : player.anchorPosition.x;
        minY = minY < player.anchorPosition.y ? minY : player.anchorPosition.y;
        maxY = maxY > player.anchorPosition.y ? maxY : player.anchorPosition.y;
      }
      final double marginX = 3.5 + ((1 - compactness) * 6);
      final double marginY = 3 + ((1 - compactness) * 5);
      final Rect bounds = Rect.fromLTRB(
        (((minX - marginX).clamp(2, 98)) / 100) * size.width,
        (((minY - marginY).clamp(2, 98)) / 100) * size.height,
        (((maxX + marginX).clamp(2, 98)) / 100) * size.width,
        (((maxY + marginY).clamp(2, 98)) / 100) * size.height,
      );
      final double baseAlpha = 0.04 + (compactness * 0.07);
      final Color bandColor = _baseSideColor(side).withValues(
        alpha:
            baseAlpha +
            (isPossessionSide ? 0.03 : 0) +
            (style.showTransitionGuide ? 0.02 : 0) +
            (style.showSetPieceGuide ? 0.02 : 0),
      );
      final Paint fillPaint = Paint()..color = bandColor;
      final Paint borderPaint =
          Paint()
            ..style = PaintingStyle.stroke
            ..strokeWidth = 1 + (style.pressureIndex * 0.7)
            ..color = _baseSideColor(side).withValues(
              alpha:
                  0.18 + (compactness * 0.12) + (isPossessionSide ? 0.06 : 0),
            );
      final RRect rrect = RRect.fromRectAndRadius(
        bounds,
        const Radius.circular(18),
      );
      canvas.drawRRect(rrect, fillPaint);
      canvas.drawRRect(rrect, borderPaint);
    }
  }

  Color _baseSideColor(MatchViewerSide side) {
    return side == MatchViewerSide.home
        ? const Color(0xFF17B26A)
        : const Color(0xFFF97066);
  }

  @override
  bool shouldRepaint(covariant _FormationOverlayPainter oldDelegate) {
    return oldDelegate.frame != frame ||
        oldDelegate.players != players ||
        oldDelegate.style != style;
  }
}
