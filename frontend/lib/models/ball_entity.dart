import 'package:gte_frontend/models/match_timeline_frame.dart';

enum BallTrajectoryType {
  carry,
  pass,
  shot,
  loose,
  reset,
}

class BallEntity {
  const BallEntity({
    required this.startPosition,
    required this.targetPosition,
    required this.currentPosition,
    required this.elevation,
    required this.ownerPlayerId,
    required this.targetPlayerId,
    required this.trajectoryType,
    required this.state,
  });

  final MatchViewerPoint startPosition;
  final MatchViewerPoint targetPosition;
  final MatchViewerPoint currentPosition;
  final double elevation;
  final String? ownerPlayerId;
  final String? targetPlayerId;
  final BallTrajectoryType trajectoryType;
  final String state;

  factory BallEntity.fromFrame(MatchViewerBallFrame frame) {
    return BallEntity(
      startPosition: frame.position,
      targetPosition: frame.position,
      currentPosition: frame.position,
      elevation: frame.elevation,
      ownerPlayerId: frame.ownerPlayerId,
      targetPlayerId: frame.ownerPlayerId,
      trajectoryType: switch (frame.state) {
        'placed' => BallTrajectoryType.reset,
        'shot' || 'saved' || 'missed' => BallTrajectoryType.shot,
        'stopped' => BallTrajectoryType.loose,
        _ => BallTrajectoryType.carry,
      },
      state: frame.state,
    );
  }

  static BallEntity carry({
    required MatchViewerPoint ownerPosition,
    required MatchViewerPoint targetPosition,
    required double progress,
    required double attackDirection,
    required String? ownerPlayerId,
    required String state,
  }) {
    final double t = progress.clamp(0, 1);
    final MatchViewerPoint leadStart = _leadPoint(
      ownerPosition,
      attackDirection: attackDirection,
    );
    final MatchViewerPoint leadEnd = _leadPoint(
      targetPosition,
      attackDirection: attackDirection,
    );
    return BallEntity(
      startPosition: leadStart,
      targetPosition: leadEnd,
      currentPosition: MatchViewerPoint.lerp(leadStart, leadEnd, t),
      elevation: 0.08,
      ownerPlayerId: ownerPlayerId,
      targetPlayerId: ownerPlayerId,
      trajectoryType: BallTrajectoryType.carry,
      state: state,
    );
  }

  static BallEntity interpolateTrajectory({
    required MatchViewerPoint startPosition,
    required MatchViewerPoint targetPosition,
    required double progress,
    required BallTrajectoryType trajectoryType,
    required String? ownerPlayerId,
    required String? targetPlayerId,
    required double attackDirection,
    required String state,
  }) {
    final double t = progress.clamp(0, 1);
    if (trajectoryType == BallTrajectoryType.carry ||
        trajectoryType == BallTrajectoryType.reset) {
      return BallEntity(
        startPosition: startPosition,
        targetPosition: targetPosition,
        currentPosition:
            MatchViewerPoint.lerp(startPosition, targetPosition, t),
        elevation: trajectoryType == BallTrajectoryType.reset ? 0 : 0.05,
        ownerPlayerId: ownerPlayerId,
        targetPlayerId: targetPlayerId,
        trajectoryType: trajectoryType,
        state: state,
      );
    }

    final MatchViewerPoint midpoint = MatchViewerPoint(
      x: (startPosition.x + targetPosition.x) / 2,
      y: (startPosition.y + targetPosition.y) / 2,
    );
    final double lateralBias =
        ((targetPosition.y - startPosition.y).clamp(-18, 18) / 18) * 3.4;
    final MatchViewerPoint control = MatchViewerPoint(
      x: midpoint.x + (attackDirection * 1.5),
      y: midpoint.y + lateralBias,
    );
    final double inverse = 1 - t;
    final MatchViewerPoint current = MatchViewerPoint(
      x: (inverse * inverse * startPosition.x) +
          (2 * inverse * t * control.x) +
          (t * t * targetPosition.x),
      y: (inverse * inverse * startPosition.y) +
          (2 * inverse * t * control.y) +
          (t * t * targetPosition.y),
    );
    final double peak = switch (trajectoryType) {
      BallTrajectoryType.pass => 1.4,
      BallTrajectoryType.shot => 2.6,
      BallTrajectoryType.loose => 0.7,
      BallTrajectoryType.carry || BallTrajectoryType.reset => 0,
    };
    final double resolvedElevation = peak * 4 * t * (1 - t);
    final String? resolvedOwner = switch (trajectoryType) {
      BallTrajectoryType.pass => t >= 1 ? targetPlayerId : ownerPlayerId,
      BallTrajectoryType.shot => t >= 1 ? targetPlayerId : ownerPlayerId,
      BallTrajectoryType.loose => t >= 1 ? targetPlayerId : null,
      BallTrajectoryType.carry || BallTrajectoryType.reset => ownerPlayerId,
    };
    return BallEntity(
      startPosition: startPosition,
      targetPosition: targetPosition,
      currentPosition: current,
      elevation: resolvedElevation,
      ownerPlayerId: resolvedOwner,
      targetPlayerId: targetPlayerId,
      trajectoryType: trajectoryType,
      state: state,
    );
  }

  MatchViewerBallFrame toFrame() {
    return MatchViewerBallFrame(
      position: currentPosition,
      ownerPlayerId: ownerPlayerId,
      state: state,
      elevation: elevation,
    );
  }

  static MatchViewerPoint _leadPoint(
    MatchViewerPoint ownerPosition, {
    required double attackDirection,
  }) {
    return MatchViewerPoint(
      x: (ownerPosition.x + (attackDirection * 1.1)).clamp(0, 100).toDouble(),
      y: (ownerPosition.y + 0.8).clamp(0, 100).toDouble(),
    );
  }
}
