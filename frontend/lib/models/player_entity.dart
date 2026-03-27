import 'dart:math' as math;

import 'package:gte_frontend/models/match_timeline_frame.dart';

enum PlayerRunPattern {
  support,
  attack,
  defend,
}

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
      baseState: targetFrame.state == MatchViewerPlayerState.sentOff
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
      ),
      hasPossession: hasPossession,
      highlighted: highlighted,
      animationState: targetFrame.animationState,
      speedRatio: startFrame.speedRatio +
          ((targetFrame.speedRatio - startFrame.speedRatio) * progress),
      blendFactor: startFrame.blendFactor +
          ((targetFrame.blendFactor - startFrame.blendFactor) * progress),
      staminaPct: (startFrame.staminaPct +
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
    );
    final double inverse = 1 - t;
    return MatchViewerPoint(
      x: (inverse * inverse * start.x) +
          (2 * inverse * t * control.x) +
          (t * t * end.x),
      y: (inverse * inverse * start.y) +
          (2 * inverse * t * control.y) +
          (t * t * end.y),
    );
  }

  static MatchViewerPoint curvedMidpoint({
    required MatchViewerPoint start,
    required MatchViewerPoint end,
    required MatchViewerPoint anchor,
    required double ballSideY,
    required PlayerRunPattern runPattern,
  }) {
    final MatchViewerPoint midpoint = MatchViewerPoint(
      x: (start.x + end.x) / 2,
      y: (start.y + end.y) / 2,
    );
    final double runBiasX = switch (runPattern) {
      PlayerRunPattern.attack => 1.6,
      PlayerRunPattern.support => 0.9,
      PlayerRunPattern.defend => -0.8,
    };
    final double laneBiasY = (anchor.y - midpoint.y).clamp(-3.8, 3.8) * 0.55;
    final double ballBiasY = (ballSideY - midpoint.y).clamp(-4.2, 4.2) * 0.28;
    final double totalBiasY = (laneBiasY + ballBiasY).clamp(-4.8, 4.8);
    final double anchorBiasX = (anchor.x - midpoint.x).clamp(-3.0, 3.0) * 0.18;
    return MatchViewerPoint(
      x: midpoint.x + runBiasX + anchorBiasX,
      y: midpoint.y + totalBiasY,
    );
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

  PlayerEntity? nearestTo(
    MatchViewerPoint point, {
    MatchViewerSide? side,
  }) {
    PlayerEntity? nearest;
    double nearestDistance = double.infinity;
    for (final PlayerEntity player in this) {
      if (side != null && player.side != side) {
        continue;
      }
      final double deltaX = player.currentPosition.x - point.x;
      final double deltaY = player.currentPosition.y - point.y;
      final double distance = math.sqrt(
        (deltaX * deltaX) + (deltaY * deltaY),
      );
      if (distance < nearestDistance) {
        nearestDistance = distance;
        nearest = player;
      }
    }
    return nearest;
  }
}
