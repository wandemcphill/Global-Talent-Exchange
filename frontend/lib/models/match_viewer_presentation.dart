import 'dart:math' as math;

import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';

enum MatchViewerPresentationMode {
  replay,
  broadcast,
}

enum BroadcastCameraPreset {
  broadcast,
  attackZoom,
  goalZoom,
  replayCamera,
}

class MatchPitchPresentation {
  const MatchPitchPresentation({
    required this.cameraPreset,
    required this.scale,
    required this.panX,
    required this.panY,
    required this.motionSeedKey,
    required this.enableMicroVariation,
    this.leftFrame,
    this.rightFrame,
    this.interpolationT = 0,
  });

  static const MatchPitchPresentation disabled = MatchPitchPresentation(
    cameraPreset: BroadcastCameraPreset.broadcast,
    scale: 1,
    panX: 0,
    panY: 0,
    motionSeedKey: 'replay',
    enableMicroVariation: false,
  );

  final BroadcastCameraPreset cameraPreset;
  final double scale;
  final double panX;
  final double panY;
  final String motionSeedKey;
  final bool enableMicroVariation;
  final MatchTimelineFrame? leftFrame;
  final MatchTimelineFrame? rightFrame;
  final double interpolationT;

  MatchViewerPoint resolvePlayerPosition(MatchViewerPlayerFrame player) {
    if (!enableMicroVariation || leftFrame == null || rightFrame == null) {
      return player.position;
    }
    final MatchViewerPlayerFrame? leftPlayer =
        _playerForFrame(leftFrame!, player.playerId);
    final MatchViewerPlayerFrame? rightPlayer =
        _playerForFrame(rightFrame!, player.playerId);
    if (leftPlayer == null || rightPlayer == null) {
      return player.position;
    }
    final double t = interpolationT.clamp(0, 1);
    final double deltaX = rightPlayer.position.x - leftPlayer.position.x;
    final double deltaY = rightPlayer.position.y - leftPlayer.position.y;
    final double distance = math.sqrt((deltaX * deltaX) + (deltaY * deltaY));
    if (distance < 0.18) {
      return player.position;
    }
    final double curvatureBase = math.min(1.5, math.max(0.18, distance * 0.18));
    final double fraction = _stableFraction(
      '$motionSeedKey|${player.playerId}|${leftFrame!.id}|${rightFrame!.id}',
    );
    final double sign = fraction >= 0.5 ? 1 : -1;
    final double curve = math.sin(math.pi * t) * curvatureBase * sign;
    final double perpendicularX = -deltaY / distance;
    final double perpendicularY = deltaX / distance;
    return MatchViewerPoint(
      x: (player.position.x + (perpendicularX * curve))
          .clamp(0, 100)
          .toDouble(),
      y: (player.position.y + (perpendicularY * curve))
          .clamp(0, 100)
          .toDouble(),
    );
  }

  static MatchViewerPlayerFrame? _playerForFrame(
    MatchTimelineFrame frame,
    String playerId,
  ) {
    for (final MatchViewerPlayerFrame player in frame.players) {
      if (player.playerId == playerId) {
        return player;
      }
    }
    return null;
  }

  static double _stableFraction(String seed) {
    int hash = 2166136261;
    for (final int codeUnit in seed.codeUnits) {
      hash ^= codeUnit;
      hash = (hash * 16777619) & 0x7fffffff;
    }
    return hash / 0x7fffffff;
  }
}

class MatchBroadcastPresentationState {
  const MatchBroadcastPresentationState({
    required this.clockLabel,
    required this.statusLabel,
    required this.stadiumFadeOpacity,
    required this.startingBannerOpacity,
    required this.lineupBoardOpacity,
    required this.visibleHomeScore,
    required this.visibleAwayScore,
    required this.scoreMasked,
    required this.isVarChecking,
    required this.pitchPresentation,
    this.focusEvent,
    this.commentaryHeadline,
    this.commentarySubtitle,
  });

  final String clockLabel;
  final String statusLabel;
  final double stadiumFadeOpacity;
  final double startingBannerOpacity;
  final double lineupBoardOpacity;
  final int? visibleHomeScore;
  final int? visibleAwayScore;
  final bool scoreMasked;
  final bool isVarChecking;
  final MatchPitchPresentation pitchPresentation;
  final MatchEvent? focusEvent;
  final String? commentaryHeadline;
  final String? commentarySubtitle;

  bool get showStartingBanner => startingBannerOpacity > 0.01;

  bool get showLineupBoard => lineupBoardOpacity > 0.01;

  bool get showCommentary =>
      commentaryHeadline != null && commentaryHeadline!.trim().isNotEmpty;
}
