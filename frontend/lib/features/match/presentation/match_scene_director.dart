import '../../../models/match_event.dart';
import '../../../models/match_timeline_frame.dart';

enum BroadcastPackageScene {
  titleBanner,
  rosterCard,
  homeFormation,
  awayFormation,
  contextBoard,
  reactions,
  kickoffLive,
  halftimeBoard,
  fulltimeBoard,
}

enum MatchSimCameraState {
  stadiumWide,
  tunnelOrWalkout,
  kickoffCenter,
  tacticalTop,
  attackingThird,
  setPieceLeft,
  setPieceRight,
  goalReplayAngle,
  halftimeBoard,
  fulltimeBoard,
}

class BroadcastSceneSnapshot {
  const BroadcastSceneSnapshot({
    required this.scene,
    required this.cameraState,
    required this.label,
  });

  final BroadcastPackageScene scene;
  final MatchSimCameraState cameraState;
  final String label;
}

class MatchSceneDirector {
  const MatchSceneDirector._();

  static BroadcastSceneSnapshot resolve({
    required MatchTimelineFrame frame,
    MatchEvent? activeEvent,
    required double packageSeconds,
  }) {
    final BroadcastPackageScene scene = resolveBroadcastScene(
      frame: frame,
      activeEvent: activeEvent,
      packageSeconds: packageSeconds,
    );
    final MatchSimCameraState cameraState = resolveCameraState(
      frame: frame,
      activeEvent: activeEvent,
    );
    return BroadcastSceneSnapshot(
      scene: scene,
      cameraState: cameraState,
      label: _sceneLabel(scene),
    );
  }

  static BroadcastPackageScene resolveBroadcastScene({
    required MatchTimelineFrame frame,
    MatchEvent? activeEvent,
    required double packageSeconds,
  }) {
    if (frame.phase == MatchViewerPhase.fulltime) {
      return BroadcastPackageScene.fulltimeBoard;
    }
    if (frame.phase == MatchViewerPhase.halftime) {
      return BroadcastPackageScene.halftimeBoard;
    }
    if (packageSeconds < 2.8) {
      return BroadcastPackageScene.titleBanner;
    }
    if (packageSeconds < 5.4) {
      return BroadcastPackageScene.rosterCard;
    }
    if (packageSeconds < 8.0) {
      return BroadcastPackageScene.homeFormation;
    }
    if (packageSeconds < 10.6) {
      return BroadcastPackageScene.awayFormation;
    }
    if (packageSeconds < 13.2) {
      return BroadcastPackageScene.contextBoard;
    }
    if (packageSeconds < 15.8) {
      return BroadcastPackageScene.reactions;
    }
    if (activeEvent?.type == MatchViewerEventType.halftime) {
      return BroadcastPackageScene.halftimeBoard;
    }
    if (activeEvent?.type == MatchViewerEventType.fulltime) {
      return BroadcastPackageScene.fulltimeBoard;
    }
    return BroadcastPackageScene.kickoffLive;
  }

  static MatchSimCameraState resolveCameraState({
    required MatchTimelineFrame frame,
    MatchEvent? activeEvent,
  }) {
    if (frame.phase == MatchViewerPhase.fulltime ||
        activeEvent?.type == MatchViewerEventType.fulltime) {
      return MatchSimCameraState.fulltimeBoard;
    }
    if (frame.phase == MatchViewerPhase.halftime ||
        activeEvent?.type == MatchViewerEventType.halftime) {
      return MatchSimCameraState.halftimeBoard;
    }
    if (activeEvent?.type == MatchViewerEventType.kickoff ||
        frame.phase == MatchViewerPhase.kickoff) {
      return frame.timeSeconds <= 1.2
          ? MatchSimCameraState.tunnelOrWalkout
          : MatchSimCameraState.kickoffCenter;
    }
    if (activeEvent?.type == MatchViewerEventType.goal &&
        (frame.stage == MatchPlaybackStage.post ||
            frame.stage == MatchPlaybackStage.decision)) {
      return MatchSimCameraState.goalReplayAngle;
    }
    if (activeEvent?.type == MatchViewerEventType.setPiece ||
        activeEvent?.type == MatchViewerEventType.penalty ||
        frame.phase == MatchViewerPhase.setPiece) {
      final bool leftSide =
          (activeEvent?.teamId == null || activeEvent!.teamId == 'home')
              ? frame.homeAttacksRight
              : !frame.homeAttacksRight;
      return leftSide
          ? MatchSimCameraState.setPieceRight
          : MatchSimCameraState.setPieceLeft;
    }
    if (activeEvent?.type == MatchViewerEventType.attack ||
        activeEvent?.type == MatchViewerEventType.save ||
        activeEvent?.type == MatchViewerEventType.miss ||
        activeEvent?.type == MatchViewerEventType.offside ||
        activeEvent?.type == MatchViewerEventType.goal) {
      return MatchSimCameraState.attackingThird;
    }
    if (frame.cameraPreset == MatchCameraPreset.broadcast &&
        frame.timeSeconds < 2.0) {
      return MatchSimCameraState.stadiumWide;
    }
    return MatchSimCameraState.tacticalTop;
  }

  static String _sceneLabel(BroadcastPackageScene scene) {
    switch (scene) {
      case BroadcastPackageScene.titleBanner:
        return 'Match title';
      case BroadcastPackageScene.rosterCard:
        return 'Official roster';
      case BroadcastPackageScene.homeFormation:
        return 'Home formation';
      case BroadcastPackageScene.awayFormation:
        return 'Away formation';
      case BroadcastPackageScene.contextBoard:
        return 'Standings and context';
      case BroadcastPackageScene.reactions:
        return 'Matchday desk';
      case BroadcastPackageScene.kickoffLive:
        return 'Kickoff and live';
      case BroadcastPackageScene.halftimeBoard:
        return 'Halftime package';
      case BroadcastPackageScene.fulltimeBoard:
        return 'Fulltime package';
    }
  }
}
