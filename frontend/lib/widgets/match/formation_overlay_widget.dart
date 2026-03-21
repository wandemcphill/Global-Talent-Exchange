import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';

class FormationOverlayWidget extends StatelessWidget {
  const FormationOverlayWidget({
    super.key,
    required this.players,
  });

  final List<MatchViewerPlayerFrame> players;

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      painter: _FormationOverlayPainter(players: players),
      size: Size.infinite,
    );
  }
}

class _FormationOverlayPainter extends CustomPainter {
  const _FormationOverlayPainter({required this.players});

  final List<MatchViewerPlayerFrame> players;

  @override
  void paint(Canvas canvas, Size size) {
    final Paint homePaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2
      ..color = const Color(0x3317B26A);
    final Paint awayPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2
      ..color = const Color(0x33F97066);
    for (final MatchViewerPlayerFrame player in players) {
      if (!player.active) {
        continue;
      }
      final Offset center = Offset(
        (player.anchorPosition.x / 100) * size.width,
        (player.anchorPosition.y / 100) * size.height,
      );
      canvas.drawCircle(
        center,
        player.line == MatchPlayerLine.goalkeeper ? 7 : 5,
        player.side == MatchViewerSide.home ? homePaint : awayPaint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _FormationOverlayPainter oldDelegate) {
    return oldDelegate.players != players;
  }
}
