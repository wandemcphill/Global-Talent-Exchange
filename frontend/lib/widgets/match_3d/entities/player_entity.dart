import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/widgets/match_3d/entities/pitch_entity.dart';

class PlayerEntity {
  const PlayerEntity({
    required this.playerId,
    required this.label,
    required this.base,
    required this.depth,
    required this.scale,
    required this.lean,
    required this.stride,
    required this.fillColor,
    required this.accentColor,
    required this.headColor,
    required this.highlighted,
    required this.isDimmed,
    required this.isGoalkeeper,
  });

  final String playerId;
  final String label;
  final Offset base;
  final double depth;
  final double scale;
  final double lean;
  final double stride;
  final Color fillColor;
  final Color accentColor;
  final Color headColor;
  final bool highlighted;
  final bool isDimmed;
  final bool isGoalkeeper;

  static List<PlayerEntity> buildAll({
    required MatchViewState viewState,
    required MatchTimelineFrame frame,
    required PitchProjection projection,
  }) {
    final List<PlayerEntity> players = <PlayerEntity>[];
    for (final MatchViewerPlayerFrame player in frame.players) {
      final MatchViewerTeam team = viewState.teamForSide(player.side);
      final PlayerEntity? entity = PlayerEntity.fromFrame(
        player: player,
        team: team,
        projection: projection,
      );
      if (entity != null) {
        players.add(entity);
      }
    }
    return players;
  }

  static PlayerEntity? fromFrame({
    required MatchViewerPlayerFrame player,
    required MatchViewerTeam team,
    required PitchProjection projection,
  }) {
    if (!player.active && player.state != MatchViewerPlayerState.sentOff) {
      return null;
    }

    final bool isRenderedActive =
        player.active && player.state != MatchViewerPlayerState.sentOff;
    final double depth = projection.depthForPercent(player.position.y);
    final double scale =
        projection.scaleForDepth(depth) * (player.isGoalkeeper ? 1.04 : 1);
    final Color baseColor = player.isGoalkeeper
        ? _parseColor(team.goalkeeperColorHex)
        : _parseColor(team.primaryColorHex);
    final Color accentColor = _parseColor(team.accentColorHex);
    final double lean = switch (player.state) {
      MatchViewerPlayerState.attacking => 0.15,
      MatchViewerPlayerState.defending => -0.12,
      MatchViewerPlayerState.moving || MatchViewerPlayerState.pressing => 0.08,
      _ => 0.0,
    };
    final double stride = switch (player.state) {
      MatchViewerPlayerState.attacking => 1.15,
      MatchViewerPlayerState.moving || MatchViewerPlayerState.pressing => 1.0,
      MatchViewerPlayerState.defending => 0.86,
      _ => 0.7,
    };

    return PlayerEntity(
      playerId: player.playerId,
      label: player.label,
      base: projection.projectPercent(player.position),
      depth: depth,
      scale:
          scale * (player.state == MatchViewerPlayerState.attacking ? 1.02 : 1),
      lean: lean,
      stride: stride,
      fillColor:
          isRenderedActive ? baseColor : baseColor.withValues(alpha: 0.28),
      accentColor:
          isRenderedActive ? accentColor : accentColor.withValues(alpha: 0.28),
      headColor: _parseColor(
        team.secondaryColorHex,
      ).withValues(alpha: isRenderedActive ? 0.94 : 0.4),
      highlighted: player.highlighted,
      isDimmed: !isRenderedActive,
      isGoalkeeper: player.isGoalkeeper,
    );
  }

  void paint(Canvas canvas) {
    final double shadowWidth = 17 * scale;
    final double shadowHeight = 5 * scale;
    final double bodyWidth = (isGoalkeeper ? 11.8 : 10.6) * scale;
    final double bodyHeight = (isGoalkeeper ? 24 : 22) * scale;
    final double shoulderWidth = bodyWidth * 1.18;
    final double headRadius = 3.7 * scale;
    final double baseY = base.dy;
    final double torsoTop = baseY - bodyHeight;
    final double leanOffsetX = shoulderWidth * lean;
    final double headCenterY = torsoTop - (headRadius * 0.15) - (stride * 0.18);

    final Paint shadowPaint = Paint()
      ..color = Colors.black.withValues(alpha: isDimmed ? 0.08 : 0.18);
    canvas.drawOval(
      Rect.fromCenter(
        center: Offset(base.dx, baseY - (scale * 0.8)),
        width: shadowWidth,
        height: shadowHeight,
      ),
      shadowPaint,
    );

    if (highlighted) {
      final Paint haloPaint = Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.6 * scale
        ..color = accentColor.withValues(alpha: 0.68);
      canvas.drawOval(
        Rect.fromCenter(
          center: Offset(base.dx, torsoTop + (bodyHeight * 0.42)),
          width: shoulderWidth * 1.55,
          height: bodyHeight * 1.5,
        ),
        haloPaint,
      );
    }

    final Path bodyPath = Path()
      ..moveTo(
        base.dx - (shoulderWidth * 0.5),
        torsoTop + (bodyHeight * 0.28),
      )
      ..quadraticBezierTo(
        base.dx + (leanOffsetX * 0.32),
        torsoTop - (bodyHeight * 0.02) - (stride * 0.12),
        base.dx + (shoulderWidth * 0.5) + (leanOffsetX * 0.12),
        torsoTop + (bodyHeight * 0.28),
      )
      ..lineTo(
        base.dx + (bodyWidth * 0.42) + (leanOffsetX * 0.24),
        baseY - (bodyHeight * 0.08),
      )
      ..quadraticBezierTo(
        base.dx + (leanOffsetX * 0.2),
        baseY + (bodyHeight * 0.04),
        base.dx - (bodyWidth * 0.42) + (leanOffsetX * 0.12),
        baseY - (bodyHeight * 0.08),
      )
      ..close();

    final Paint bodyPaint = Paint()..color = fillColor;
    final Paint outlinePaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.15 * scale
      ..color = accentColor.withValues(alpha: isDimmed ? 0.42 : 0.92);
    canvas.drawPath(bodyPath, bodyPaint);
    canvas.drawPath(bodyPath, outlinePaint);

    final Paint trimPaint = Paint()
      ..color = accentColor.withValues(alpha: isDimmed ? 0.36 : 0.8);
    canvas.drawRect(
      Rect.fromCenter(
        center:
            Offset(base.dx + (leanOffsetX * 0.18), baseY - (bodyHeight * 0.24)),
        width: bodyWidth * 0.96,
        height: 2.1 * scale,
      ),
      trimPaint,
    );

    final Paint headPaint = Paint()..color = headColor;
    canvas.drawCircle(
      Offset(base.dx + (leanOffsetX * 0.28), headCenterY),
      headRadius,
      headPaint,
    );

    final Paint legPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5 * scale
      ..strokeCap = StrokeCap.round
      ..color = fillColor.withValues(alpha: isDimmed ? 0.45 : 0.88);
    canvas.drawLine(
      Offset(base.dx - (bodyWidth * 0.14), baseY - (bodyHeight * 0.04)),
      Offset(
          base.dx - (bodyWidth * 0.2) - (stride * 0.35), baseY + (scale * 0.4)),
      legPaint,
    );
    canvas.drawLine(
      Offset(base.dx + (bodyWidth * 0.14), baseY - (bodyHeight * 0.04)),
      Offset(
          base.dx + (bodyWidth * 0.2) + (stride * 0.35), baseY + (scale * 0.4)),
      legPaint,
    );
  }
}

Color _parseColor(String value) {
  final String normalized = value.replaceAll('#', '').trim();
  final String hex = normalized.length == 6 ? 'FF$normalized' : normalized;
  return Color(int.tryParse(hex, radix: 16) ?? 0xFFFFFFFF);
}
