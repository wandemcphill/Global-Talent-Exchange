import 'package:flutter/material.dart';
import 'package:gte_frontend/features/match/presentation/broadcast_package_models.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';

enum MatchEngineCameraPreset {
  stadium_wide,
  kickoff_center,
  tactical_high,
  attacking_third_left,
  attacking_third_right,
  defensive_block,
  set_piece_left,
  set_piece_right,
  goal_replay,
  halftime_board,
  fulltime_board,
}

enum MatchSceneEventMapping {
  kickoff,
  possession_phase,
  chance_creation,
  shot,
  save,
  goal,
  foul,
  booking,
  substitution,
  corner,
  free_kick,
  penalty,
  halftime,
  fulltime,
}

enum MatchEnginePresentationMoment { live, replay, recap }

enum MatchEngineShapeLine { goalkeeper, defense, midfield, attack }

class MatchEngineShapeLane {
  const MatchEngineShapeLane({
    required this.line,
    required this.averageX,
    required this.averageY,
    required this.width,
    required this.activeCount,
  });

  final MatchEngineShapeLine line;
  final double averageX;
  final double averageY;
  final double width;
  final int activeCount;

  Map<String, Object> toJson() {
    return <String, Object>{
      'line': line.name,
      'averageX': averageX,
      'averageY': averageY,
      'width': width,
      'activeCount': activeCount,
    };
  }
}

class MatchEngineTeamShape {
  const MatchEngineTeamShape({
    required this.teamId,
    required this.side,
    required this.formation,
    required this.width,
    required this.depth,
    required this.compactness,
    required this.inPossession,
    required this.lanes,
  });

  final String teamId;
  final MatchViewerSide side;
  final String formation;
  final double width;
  final double depth;
  final double compactness;
  final bool inPossession;
  final List<MatchEngineShapeLane> lanes;

  String get compactnessLabel {
    if (compactness >= 0.72) {
      return 'Compact';
    }
    if (compactness >= 0.46) {
      return 'Balanced';
    }
    return 'Stretched';
  }

  String get widthLabel {
    if (width >= 44) {
      return 'Very wide';
    }
    if (width >= 34) {
      return 'Wide';
    }
    if (width >= 24) {
      return 'Narrow';
    }
    return 'Very narrow';
  }

  Map<String, Object> toJson() {
    return <String, Object>{
      'teamId': teamId,
      'side': side.name,
      'formation': formation,
      'width': width,
      'depth': depth,
      'compactness': compactness,
      'compactnessLabel': compactnessLabel,
      'widthLabel': widthLabel,
      'inPossession': inPossession,
      'lanes': lanes
          .map((MatchEngineShapeLane item) => item.toJson())
          .toList(growable: false),
    };
  }
}

class MatchEngineEventContext {
  const MatchEngineEventContext({
    this.eventId,
    this.teamId,
    this.teamName,
    this.primaryPlayerId,
    this.primaryPlayerName,
    this.secondaryPlayerId,
    this.secondaryPlayerName,
    this.bannerText,
    this.commentary,
    this.reviewable = false,
    this.reviewDecision,
  });

  final String? eventId;
  final String? teamId;
  final String? teamName;
  final String? primaryPlayerId;
  final String? primaryPlayerName;
  final String? secondaryPlayerId;
  final String? secondaryPlayerName;
  final String? bannerText;
  final String? commentary;
  final bool reviewable;
  final String? reviewDecision;

  bool get hasPrimaryPlayer =>
      primaryPlayerName != null && primaryPlayerName!.trim().isNotEmpty;

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'eventId': eventId,
      'teamId': teamId,
      'teamName': teamName,
      'primaryPlayerId': primaryPlayerId,
      'primaryPlayerName': primaryPlayerName,
      'secondaryPlayerId': secondaryPlayerId,
      'secondaryPlayerName': secondaryPlayerName,
      'bannerText': bannerText,
      'commentary': commentary,
      'reviewable': reviewable,
      'reviewDecision': reviewDecision,
    };
  }
}

class MatchEngineBanner {
  const MatchEngineBanner({
    required this.label,
    required this.detail,
    required this.accentColor,
    required this.icon,
  });

  final String label;
  final String detail;
  final Color accentColor;
  final IconData icon;
}

class MatchEngineSummaryBoard {
  const MatchEngineSummaryBoard({
    required this.title,
    required this.subtitle,
    required this.bullets,
  });

  final String title;
  final String subtitle;
  final List<String> bullets;
}

class MatchEnginePresentationState {
  const MatchEnginePresentationState({
    required this.sceneState,
    required this.cameraPreset,
    required this.eventMapping,
    required this.moment,
    required this.phaseLabel,
    required this.stateLabel,
    required this.sceneLabel,
    required this.cameraLabel,
    required this.clockLabel,
    required this.possessionSide,
    required this.possessionOwnerId,
    required this.homeShape,
    required this.awayShape,
    required this.activeEventContext,
    required this.ratingLeaders,
    required this.lowerThirdHeadline,
    required this.lowerThirdDetail,
    required this.lowerThirdTrailing,
    required this.scorebugEventLabel,
    required this.pressureIndex,
    required this.dangerZone,
    required this.transitionState,
    required this.frameTags,
    this.banner,
    this.summaryBoard,
  });

  final MatchEngineCameraPreset sceneState;
  final MatchEngineCameraPreset cameraPreset;
  final MatchSceneEventMapping eventMapping;
  final MatchEnginePresentationMoment moment;
  final String phaseLabel;
  final String stateLabel;
  final String sceneLabel;
  final String cameraLabel;
  final String clockLabel;
  final MatchViewerSide possessionSide;
  final String? possessionOwnerId;
  final MatchEngineTeamShape homeShape;
  final MatchEngineTeamShape awayShape;
  final MatchEngineEventContext? activeEventContext;
  final List<MatchPresentationPlayer> ratingLeaders;
  final String lowerThirdHeadline;
  final String lowerThirdDetail;
  final String lowerThirdTrailing;
  final String? scorebugEventLabel;
  final double? pressureIndex;
  final String? dangerZone;
  final MatchTransitionState? transitionState;
  final List<String> frameTags;
  final MatchEngineBanner? banner;
  final MatchEngineSummaryBoard? summaryBoard;

  bool get showRatingsStrip => ratingLeaders.isNotEmpty;

  bool get showBanner => banner != null;

  bool get showSummaryBoard => summaryBoard != null;

  bool get isReplayMoment => moment == MatchEnginePresentationMoment.replay;

  bool get isRecapMoment => moment == MatchEnginePresentationMoment.recap;

  bool get isDangerMoment =>
      dangerZone == 'box' ||
      dangerZone == 'final_third' ||
      frameTags.contains('box_entry') ||
      pressureIndex != null && pressureIndex! >= 0.72;

  bool get isSetPieceMoment =>
      frameTags.contains('set_piece') ||
      transitionState?.isReset == true ||
      dangerZone == 'set_piece';

  String get pressureLabel {
    final double value = pressureIndex ?? 0;
    if (value >= 0.84) {
      return 'Red Zone';
    }
    if (value >= 0.68) {
      return 'High Pressure';
    }
    if (value >= 0.46) {
      return 'Building';
    }
    return 'Settled';
  }

  String get dangerLabel {
    return switch (dangerZone) {
      'box' => 'Box Threat',
      'final_third' => 'Final Third',
      'middle_third' => 'Transition Lane',
      'set_piece' => 'Set Piece',
      'stopped' => 'Stoppage',
      _ =>
        isSetPieceMoment
            ? 'Set Piece'
            : transitionState?.isBreak == true
            ? 'Breakaway'
            : 'Open Play',
    };
  }

  String get transitionLabel {
    return switch (transitionState) {
      MatchTransitionState.homeBreak => 'Home Break',
      MatchTransitionState.awayBreak => 'Away Break',
      MatchTransitionState.homeReset => 'Home Reset',
      MatchTransitionState.awayReset => 'Away Reset',
      MatchTransitionState.stopped => 'Stopped',
      MatchTransitionState.stable || null =>
        pressureIndex != null && pressureIndex! >= 0.68
            ? 'Pressure Build'
            : 'Stable',
    };
  }

  String get telemetryLabel => '$dangerLabel · $pressureLabel';
}
