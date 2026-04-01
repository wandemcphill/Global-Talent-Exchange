import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';

class BallWidget extends StatelessWidget {
  const BallWidget({
    super.key,
    required this.ball,
    required this.size,
  });

  final MatchViewerBallFrame ball;
  final double size;

  @override
  Widget build(BuildContext context) {
    final Color fillColor = switch (ball.state) {
      'saved' => const Color(0xFFD1E9FF),
      'missed' => const Color(0xFFFEE4A8),
      'shot' => const Color(0xFFFFFFFF),
      'in_goal' => const Color(0xFFF2F4F7),
      _ => Colors.white,
    };
    return IgnorePointer(
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: fillColor,
          border: Border.all(color: const Color(0xFF0F172A), width: 1),
        ),
      ),
    );
  }
}
