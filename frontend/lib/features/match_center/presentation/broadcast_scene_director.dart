import 'package:gte_frontend/features/match_center/models/match_event.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';

enum BroadcastPackageScene {
  titleBanner,
  rosterCard,
  homeFormation,
  awayFormation,
  contextBoard,
  storylinePanel,
  kickoffTransition,
  liveMatch,
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

  bool get isStudioScene =>
      scene != BroadcastPackageScene.liveMatch &&
      scene != BroadcastPackageScene.kickoffTransition;
}

class MatchSceneDirector {
  const MatchSceneDirector._();

  static const double preMatchSequenceSeconds = 17.4;

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
      scene: scene,
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
    if (frame.phase == MatchViewerPhase.fulltime ||
        activeEvent?.type == MatchViewerEventType.fulltime) {
      return BroadcastPackageScene.fulltimeBoard;
    }
    if (frame.phase == MatchViewerPhase.halftime ||
        activeEvent?.type == MatchViewerEventType.halftime) {
      return BroadcastPackageScene.halftimeBoard;
    }
    if (packageSeconds < 2.6) {
      return BroadcastPackageScene.titleBanner;
    }
    if (packageSeconds < 5.2) {
      return BroadcastPackageScene.rosterCard;
    }
    if (packageSeconds < 7.8) {
      return BroadcastPackageScene.homeFormation;
    }
    if (packageSeconds < 10.4) {
      return BroadcastPackageScene.awayFormation;
    }
    if (packageSeconds < 13.0) {
      return BroadcastPackageScene.contextBoard;
    }
    if (packageSeconds < 15.6) {
      return BroadcastPackageScene.storylinePanel;
    }
    if (packageSeconds < preMatchSequenceSeconds) {
      return BroadcastPackageScene.kickoffTransition;
    }
    return BroadcastPackageScene.liveMatch;
  }

  static MatchSimCameraState resolveCameraState({
    required MatchTimelineFrame frame,
    MatchEvent? activeEvent,
    BroadcastPackageScene? scene,
  }) {
    final BroadcastPackageScene resolvedScene =
        scene ??
        resolveBroadcastScene(
          frame: frame,
          activeEvent: activeEvent,
          packageSeconds: preMatchSequenceSeconds,
        );
    if (resolvedScene == BroadcastPackageScene.fulltimeBoard ||
        frame.phase == MatchViewerPhase.fulltime ||
        activeEvent?.type == MatchViewerEventType.fulltime) {
      return MatchSimCameraState.fulltimeBoard;
    }
    if (resolvedScene == BroadcastPackageScene.halftimeBoard ||
        frame.phase == MatchViewerPhase.halftime ||
        activeEvent?.type == MatchViewerEventType.halftime) {
      return MatchSimCameraState.halftimeBoard;
    }
    if (resolvedScene == BroadcastPackageScene.titleBanner ||
        frame.phase == MatchViewerPhase.kickoff) {
      return frame.timeSeconds <= 1.2
          ? MatchSimCameraState.tunnelOrWalkout
          : MatchSimCameraState.stadiumWide;
    }
    if (resolvedScene == BroadcastPackageScene.kickoffTransition ||
        activeEvent?.type == MatchViewerEventType.kickoff) {
      return MatchSimCameraState.kickoffCenter;
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
        return 'Pre-match title board';
      case BroadcastPackageScene.rosterCard:
        return 'Official roster card';
      case BroadcastPackageScene.homeFormation:
        return 'Home formation board';
      case BroadcastPackageScene.awayFormation:
        return 'Away formation board';
      case BroadcastPackageScene.contextBoard:
        return 'Standings and context board';
      case BroadcastPackageScene.storylinePanel:
        return 'Matchday storyline panel';
      case BroadcastPackageScene.kickoffTransition:
        return 'Kickoff transition';
      case BroadcastPackageScene.liveMatch:
        return 'Live broadcast lane';
      case BroadcastPackageScene.halftimeBoard:
        return 'Halftime package';
      case BroadcastPackageScene.fulltimeBoard:
        return 'Full-time package';
    }
  }
}
