import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match_3d_scene_graph.dart';
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
    required Match3dSceneGraph sceneGraph,
    required PitchProjection projection,
  }) {
    final List<PlayerEntity> players = <PlayerEntity>[];
    for (final Match3dSceneNode node in sceneGraph.playerNodes) {
      final Match3dPlayerPayload payload = node.payload as Match3dPlayerPayload;
      final MatchViewerTeam team = viewState.teamForSide(payload.side);
      final PlayerEntity? entity = PlayerEntity.fromNode(
        node: node,
        payload: payload,
        team: team,
        projection: projection,
      );
      if (entity != null) {
        players.add(entity);
      }
    }
    return players;
  }

  static PlayerEntity? fromNode({
    required Match3dSceneNode node,
    required Match3dPlayerPayload payload,
    required MatchViewerTeam team,
    required PitchProjection projection,
  }) {
    if (!payload.active &&
        payload.animation.targetState != Match3dAnimationState.recover) {
      return null;
    }

    final bool isRenderedActive =
        payload.active &&
        payload.animation.targetState != Match3dAnimationState.recover;
    final MatchViewerPoint position = _percentFromWorld(node.position);
    final double depth = projection.depthForPercent(position.y);
    final double scale =
        projection.scaleForDepth(depth) *
        (payload.role == MatchViewerRole.goalkeeper ? 1.04 : 1);
    final Color baseColor =
        payload.role == MatchViewerRole.goalkeeper
            ? _parseColor(team.goalkeeperColorHex)
            : _parseColor(team.primaryColorHex);
    final Color accentColor = _parseColor(team.accentColorHex);
    final double lean = _blendScalar(
      _leanForState(payload.animation.currentState, payload.speedRatio),
      _leanForState(payload.animation.targetState, payload.speedRatio),
      payload.animation.blendFactor,
    );
    final double stride = _blendScalar(
      _strideForState(payload.animation.currentState, payload.speedRatio),
      _strideForState(payload.animation.targetState, payload.speedRatio),
      payload.animation.blendFactor,
    );

    return PlayerEntity(
      playerId: node.id,
      label: payload.label,
      base: projection.projectPercent(position),
      depth: depth,
      scale:
          scale *
          (payload.animation.targetState == Match3dAnimationState.sprint
              ? 1.03
              : 1),
      lean: lean,
      stride: stride,
      fillColor:
          isRenderedActive ? baseColor : baseColor.withValues(alpha: 0.28),
      accentColor:
          isRenderedActive ? accentColor : accentColor.withValues(alpha: 0.28),
      headColor: _parseColor(
        team.secondaryColorHex,
      ).withValues(alpha: isRenderedActive ? 0.94 : 0.4),
      highlighted: payload.highlighted,
      isDimmed: !isRenderedActive,
      isGoalkeeper: payload.role == MatchViewerRole.goalkeeper,
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

    final Paint shadowPaint =
        Paint()..color = Colors.black.withValues(alpha: isDimmed ? 0.08 : 0.18);
    canvas.drawOval(
      Rect.fromCenter(
        center: Offset(base.dx, baseY - (scale * 0.8)),
        width: shadowWidth,
        height: shadowHeight,
      ),
      shadowPaint,
    );

    if (highlighted) {
      final Paint haloPaint =
          Paint()
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

    final Path bodyPath =
        Path()
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
    final Paint outlinePaint =
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.15 * scale
          ..color = accentColor.withValues(alpha: isDimmed ? 0.42 : 0.92);
    canvas.drawPath(bodyPath, bodyPaint);
    canvas.drawPath(bodyPath, outlinePaint);

    final Paint trimPaint =
        Paint()..color = accentColor.withValues(alpha: isDimmed ? 0.36 : 0.8);
    canvas.drawRect(
      Rect.fromCenter(
        center: Offset(
          base.dx + (leanOffsetX * 0.18),
          baseY - (bodyHeight * 0.24),
        ),
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

    final Paint legPaint =
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.5 * scale
          ..strokeCap = StrokeCap.round
          ..color = fillColor.withValues(alpha: isDimmed ? 0.45 : 0.88);
    canvas.drawLine(
      Offset(base.dx - (bodyWidth * 0.14), baseY - (bodyHeight * 0.04)),
      Offset(
        base.dx - (bodyWidth * 0.2) - (stride * 0.35),
        baseY + (scale * 0.4),
      ),
      legPaint,
    );
    canvas.drawLine(
      Offset(base.dx + (bodyWidth * 0.14), baseY - (bodyHeight * 0.04)),
      Offset(
        base.dx + (bodyWidth * 0.2) + (stride * 0.35),
        baseY + (scale * 0.4),
      ),
      legPaint,
    );
  }
}

Color _parseColor(String value) {
  final String normalized = value.replaceAll('#', '').trim();
  final String hex = normalized.length == 6 ? 'FF$normalized' : normalized;
  return Color(int.tryParse(hex, radix: 16) ?? 0xFFFFFFFF);
}

MatchViewerPoint _percentFromWorld(Match3dVector3 position) {
  return MatchViewerPoint(
    x:
        (((position.x + (PitchEntity.lengthMeters / 2)) /
                    PitchEntity.lengthMeters) *
                100)
            .clamp(0, 100)
            .toDouble(),
    y:
        (((position.z + (PitchEntity.widthMeters / 2)) /
                    PitchEntity.widthMeters) *
                100)
            .clamp(0, 100)
            .toDouble(),
  );
}

double _blendScalar(double from, double to, double t) {
  final double resolvedT = t.clamp(0, 1).toDouble();
  return from + ((to - from) * resolvedT);
}

double _leanForState(Match3dAnimationState state, double speedRatio) {
  return switch (state) {
    Match3dAnimationState.sprint => 0.2,
    Match3dAnimationState.run => 0.1,
    Match3dAnimationState.pass => 0.14,
    Match3dAnimationState.shoot => 0.2,
    Match3dAnimationState.tackle => -0.18,
    Match3dAnimationState.intercept => -0.08,
    Match3dAnimationState.celebrate => 0.05,
    Match3dAnimationState.receive => 0.03,
    Match3dAnimationState.recover => -0.04,
    Match3dAnimationState.idle => speedRatio >= 0.3 ? 0.05 : 0,
  };
}

double _strideForState(Match3dAnimationState state, double speedRatio) {
  final double speedBoost = speedRatio.clamp(0, 1).toDouble() * 0.18;
  return switch (state) {
    Match3dAnimationState.sprint => 1.3 + speedBoost,
    Match3dAnimationState.run => 1.04 + speedBoost,
    Match3dAnimationState.pass => 0.94,
    Match3dAnimationState.shoot => 0.9,
    Match3dAnimationState.tackle => 0.82,
    Match3dAnimationState.intercept => 0.9,
    Match3dAnimationState.celebrate => 1.12,
    Match3dAnimationState.receive => 0.82,
    Match3dAnimationState.recover => 0.76,
    Match3dAnimationState.idle => 0.68,
  };
}
