import 'dart:math' as math;

import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';

enum PlayerRunPattern { support, attack, defend }

class PlayerEntity {
  const PlayerEntity({
    required this.playerId,
    required this.teamId,
    required this.side,
    required this.role,
    required this.line,
    required this.label,
    required this.shirtNumber,
    required this.active,
    required this.baseState,
    required this.runPattern,
    required this.anchor,
    required this.startPosition,
    required this.targetPosition,
    required this.currentPosition,
    required this.hasPossession,
    required this.highlighted,
    required this.animationState,
    required this.speedRatio,
    required this.blendFactor,
    required this.staminaPct,
  });

  final String playerId;
  final String teamId;
  final MatchViewerSide side;
  final MatchViewerRole role;
  final MatchPlayerLine line;
  final String label;
  final int? shirtNumber;
  final bool active;
  final MatchViewerPlayerState baseState;
  final PlayerRunPattern runPattern;
  final MatchViewerPoint anchor;
  final MatchViewerPoint startPosition;
  final MatchViewerPoint targetPosition;
  final MatchViewerPoint currentPosition;
  final bool hasPossession;
  final bool highlighted;
  final MatchPlayerAnimationState animationState;
  final double speedRatio;
  final double blendFactor;
  final int staminaPct;

  factory PlayerEntity.fromFrames({
    required MatchViewerPlayerFrame startFrame,
    required MatchViewerPlayerFrame targetFrame,
    required MatchViewerPoint anchor,
    required PlayerRunPattern runPattern,
    required double progress,
    required double ballSideY,
    required bool hasPossession,
    required bool highlighted,
    bool structuredPhase = false,
  }) {
    return PlayerEntity(
      playerId: startFrame.playerId,
      teamId: startFrame.teamId,
      side: startFrame.side,
      role: startFrame.role,
      line: startFrame.line,
      label: startFrame.label,
      shirtNumber: startFrame.shirtNumber,
      active: startFrame.active && targetFrame.active,
      baseState:
          targetFrame.state == MatchViewerPlayerState.sentOff
              ? targetFrame.state
              : startFrame.state,
      runPattern: runPattern,
      anchor: anchor,
      startPosition: startFrame.position,
      targetPosition: targetFrame.position,
      currentPosition: curvedPoint(
        start: startFrame.position,
        end: targetFrame.position,
        anchor: anchor,
        progress: progress,
        ballSideY: ballSideY,
        runPattern: runPattern,
        seedKey: startFrame.playerId,
        structuredPhase: structuredPhase,
        hasPossession: hasPossession,
      ),
      hasPossession: hasPossession,
      highlighted: highlighted,
      animationState: targetFrame.animationState,
      speedRatio:
          startFrame.speedRatio +
          ((targetFrame.speedRatio - startFrame.speedRatio) * progress),
      blendFactor:
          startFrame.blendFactor +
          ((targetFrame.blendFactor - startFrame.blendFactor) * progress),
      staminaPct:
          (startFrame.staminaPct +
                  ((targetFrame.staminaPct - startFrame.staminaPct) * progress))
              .round(),
    );
  }

  static MatchViewerPoint curvedPoint({
    required MatchViewerPoint start,
    required MatchViewerPoint end,
    required MatchViewerPoint anchor,
    required double progress,
    required double ballSideY,
    required PlayerRunPattern runPattern,
    required String seedKey,
    required bool structuredPhase,
    required bool hasPossession,
  }) {
    final double t = progress.clamp(0, 1);
    if (t <= 0) {
      return start;
    }
    if (t >= 1) {
      return end;
    }
    final MatchViewerPoint control = curvedMidpoint(
      start: start,
      end: end,
      anchor: anchor,
      ballSideY: ballSideY,
      runPattern: runPattern,
      seedKey: seedKey,
      structuredPhase: structuredPhase,
    );
    final double motionT = _motionCurve(
      t,
      runPattern: runPattern,
      structuredPhase: structuredPhase,
      hasPossession: hasPossession,
    );
    final double inverse = 1 - motionT;
    final MatchViewerPoint curved = MatchViewerPoint(
      x:
          (inverse * inverse * start.x) +
          (2 * inverse * motionT * control.x) +
          (motionT * motionT * end.x),
      y:
          (inverse * inverse * start.y) +
          (2 * inverse * motionT * control.y) +
          (motionT * motionT * end.y),
    );
    final double shapeTether =
        structuredPhase
            ? (1 - ((motionT - 0.5).abs() * 2)).clamp(0, 1).toDouble() * 0.14
            : 0;
    return MatchViewerPoint(
      x: curved.x + ((anchor.x - curved.x) * shapeTether),
      y: curved.y + ((anchor.y - curved.y) * shapeTether),
    );
  }

  static MatchViewerPoint curvedMidpoint({
    required MatchViewerPoint start,
    required MatchViewerPoint end,
    required MatchViewerPoint anchor,
    required double ballSideY,
    required PlayerRunPattern runPattern,
    required String seedKey,
    required bool structuredPhase,
  }) {
    final MatchViewerPoint midpoint = MatchViewerPoint(
      x: (start.x + end.x) / 2,
      y: (start.y + end.y) / 2,
    );
    final double spreadBias =
        ((_stableFraction(seedKey) * 2) - 1) * (structuredPhase ? 0.92 : 1.55);
    final double runBiasX = switch (runPattern) {
      PlayerRunPattern.attack => structuredPhase ? 1.1 : 1.9,
      PlayerRunPattern.support => structuredPhase ? 0.8 : 1.1,
      PlayerRunPattern.defend => structuredPhase ? -0.5 : -1.0,
    };
    final double laneBiasY =
        (anchor.y - midpoint.y).clamp(-4.4, 4.4) *
        (structuredPhase ? 0.86 : 0.68);
    final double ballBiasY =
        (ballSideY - midpoint.y).clamp(-3.2, 3.2) *
        (structuredPhase ? 0.08 : 0.14);
    final double totalBiasY = (laneBiasY + ballBiasY + spreadBias).clamp(
      -5.6,
      5.6,
    );
    final double anchorBiasX =
        (anchor.x - midpoint.x).clamp(-4.0, 4.0) *
        (structuredPhase ? 0.48 : 0.22);
    return MatchViewerPoint(
      x: midpoint.x + runBiasX + anchorBiasX,
      y: midpoint.y + totalBiasY,
    );
  }

  static double _motionCurve(
    double progress, {
    required PlayerRunPattern runPattern,
    required bool structuredPhase,
    required bool hasPossession,
  }) {
    final double t = progress.clamp(0, 1).toDouble();
    if (structuredPhase) {
      return _easeInOut(t);
    }
    switch (runPattern) {
      case PlayerRunPattern.attack:
        return _easeOutPower(t, hasPossession ? 1.9 : 1.65);
      case PlayerRunPattern.support:
        return _easeInOut(t);
      case PlayerRunPattern.defend:
        return (0.12 + (t * 0.88)).clamp(0, 1).toDouble();
    }
  }

  static double _stableFraction(String seed) {
    int hash = 2166136261;
    for (final int codeUnit in seed.codeUnits) {
      hash ^= codeUnit;
      hash = (hash * 16777619) & 0x7fffffff;
    }
    return hash / 0x7fffffff;
  }

  static double _easeInOut(double t) {
    if (t < 0.5) {
      return 2 * t * t;
    }
    final double value = (-2 * t) + 2;
    return 1 - ((value * value) / 2);
  }

  static double _easeOutPower(double t, double power) {
    return 1 - math.pow(1 - t, power).toDouble();
  }

  MatchViewerPlayerFrame toFrame() {
    return MatchViewerPlayerFrame(
      playerId: playerId,
      teamId: teamId,
      side: side,
      shirtNumber: shirtNumber,
      label: label,
      role: role,
      line: line,
      state: _viewerState,
      active: active,
      highlighted: highlighted,
      position: currentPosition,
      anchorPosition: anchor,
      animationState: animationState,
      speedRatio: speedRatio,
      blendFactor: blendFactor,
      staminaPct: staminaPct,
    );
  }

  MatchViewerPlayerState get _viewerState {
    if (baseState == MatchViewerPlayerState.sentOff || !active) {
      return MatchViewerPlayerState.sentOff;
    }
    switch (runPattern) {
      case PlayerRunPattern.attack:
        return hasPossession
            ? MatchViewerPlayerState.attacking
            : MatchViewerPlayerState.moving;
      case PlayerRunPattern.support:
        return MatchViewerPlayerState.moving;
      case PlayerRunPattern.defend:
        return MatchViewerPlayerState.defending;
    }
  }
}

extension PlayerEntityListX on Iterable<PlayerEntity> {
  PlayerEntity? byId(String? playerId) {
    if (playerId == null) {
      return null;
    }
    for (final PlayerEntity player in this) {
      if (player.playerId == playerId) {
        return player;
      }
    }
    return null;
  }

  PlayerEntity? nearestTo(MatchViewerPoint point, {MatchViewerSide? side}) {
    PlayerEntity? nearest;
    double nearestDistance = double.infinity;
    for (final PlayerEntity player in this) {
      if (side != null && player.side != side) {
        continue;
      }
      final double deltaX = player.currentPosition.x - point.x;
      final double deltaY = player.currentPosition.y - point.y;
      final double distance = math.sqrt((deltaX * deltaX) + (deltaY * deltaY));
      if (distance < nearestDistance) {
        nearestDistance = distance;
        nearest = player;
      }
    }
    return nearest;
  }
}
