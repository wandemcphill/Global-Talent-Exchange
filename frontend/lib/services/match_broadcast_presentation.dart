import 'dart:math' as math;

import 'package:gte_frontend/controllers/match_3d_timeline_controller.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/models/match_viewer_presentation.dart';

class MatchBroadcastPresentationBuilder {
  MatchBroadcastPresentationBuilder._();

  static MatchBroadcastPresentationState build({
    required MatchViewState viewState,
    required Match3dTimelineController controller,
  }) {
    return fromPlayback(
      viewState: viewState,
      positionSeconds: controller.positionSeconds,
      displayFrame: controller.displayFrame,
      leftFrame: controller.leftFrame,
      rightFrame: controller.rightFrame,
      interpolationT: controller.interpolationT,
      activeEvent: controller.activeEvent,
    );
  }

  static MatchBroadcastPresentationState fromPlayback({
    required MatchViewState viewState,
    required double positionSeconds,
    required MatchTimelineFrame displayFrame,
    required MatchTimelineFrame leftFrame,
    required MatchTimelineFrame rightFrame,
    required double interpolationT,
    MatchEvent? activeEvent,
  }) {
    final double stadiumFadeOpacity =
        ((1.2 - positionSeconds) / 1.2).clamp(0, 1).toDouble();
    final double startingBannerOpacity = _windowOpacity(
      positionSeconds,
      start: 0.8,
      end: 4.0,
      fadeIn: 0.35,
      fadeOut: 0.65,
    );
    final double lineupBoardOpacity = _windowOpacity(
      positionSeconds,
      start: 1.4,
      end: 5.5,
      fadeIn: 0.45,
      fadeOut: 0.85,
    );
    final MatchEvent? focusEvent = _resolveFocusEvent(
      viewState: viewState,
      positionSeconds: positionSeconds,
      displayFrame: displayFrame,
      activeEvent: activeEvent,
    );
    final MatchEvent? lastGoal = _lastSettledGoal(
      viewState.events,
      positionSeconds,
    );
    final bool isFulltime = displayFrame.phase == MatchViewerPhase.fulltime ||
        positionSeconds >= (viewState.durationSeconds - 0.01);
    final bool revealScorelessDraw = isFulltime && lastGoal == null;
    final int? visibleHomeScore =
        lastGoal?.homeScore ?? (revealScorelessDraw ? 0 : null);
    final int? visibleAwayScore =
        lastGoal?.awayScore ?? (revealScorelessDraw ? 0 : null);
    final bool scoreMasked =
        visibleHomeScore == null || visibleAwayScore == null;
    final bool isVarChecking = _isVarWindow(
      focusEvent: focusEvent,
      positionSeconds: positionSeconds,
    );
    final ({String? headline, String? subtitle}) commentary =
        _commentaryForEvent(
      focusEvent: focusEvent,
      positionSeconds: positionSeconds,
      isVarChecking: isVarChecking,
    );
    final MatchPitchPresentation pitchPresentation = _pitchPresentation(
      viewState: viewState,
      positionSeconds: positionSeconds,
      displayFrame: displayFrame,
      leftFrame: leftFrame,
      rightFrame: rightFrame,
      interpolationT: interpolationT,
      focusEvent: focusEvent,
      introScaleBoost: stadiumFadeOpacity * 0.04,
    );
    return MatchBroadcastPresentationState(
      clockLabel: _clockLabel(positionSeconds),
      statusLabel: isFulltime ? 'FT' : 'LIVE',
      stadiumFadeOpacity: stadiumFadeOpacity,
      startingBannerOpacity: startingBannerOpacity,
      lineupBoardOpacity: lineupBoardOpacity,
      visibleHomeScore: visibleHomeScore,
      visibleAwayScore: visibleAwayScore,
      scoreMasked: scoreMasked,
      isVarChecking: isVarChecking,
      focusEvent: focusEvent,
      commentaryHeadline: commentary.headline,
      commentarySubtitle: commentary.subtitle,
      pitchPresentation: pitchPresentation,
    );
  }

  static MatchEvent? _lastSettledGoal(
    List<MatchEvent> events,
    double positionSeconds,
  ) {
    MatchEvent? goal;
    for (final MatchEvent event in events) {
      if (event.type != MatchViewerEventType.goal) {
        continue;
      }
      if (event.timeSeconds <= positionSeconds + 0.05) {
        goal = event;
      }
    }
    return goal;
  }

  static MatchEvent? _resolveFocusEvent({
    required MatchViewState viewState,
    required double positionSeconds,
    required MatchTimelineFrame displayFrame,
    MatchEvent? activeEvent,
  }) {
    final MatchEvent? injectedFocus = _nearestInjectedFocusEvent(
      viewState: viewState,
      injections: displayFrame.injectedEvents,
      positionSeconds: positionSeconds,
    );
    if (injectedFocus != null) {
      return injectedFocus;
    }
    if (_isFocusEligible(activeEvent) &&
        positionSeconds >= activeEvent!.timeSeconds - 0.35) {
      return activeEvent;
    }
    MatchEvent? fallback;
    MatchEvent? upcoming;
    for (final MatchEvent event in viewState.events) {
      if (!_isFocusEligible(event)) {
        continue;
      }
      final double delta = positionSeconds - event.timeSeconds;
      if (delta >= 0 && delta <= 2.8) {
        fallback = event;
        continue;
      }
      if (upcoming == null && delta < 0 && delta >= -0.35) {
        upcoming = event;
      }
    }
    return fallback ?? upcoming;
  }

  static MatchEvent? _nearestInjectedFocusEvent({
    required MatchViewState viewState,
    required List<MatchTimelineInjection> injections,
    required double positionSeconds,
  }) {
    MatchEvent? nearest;
    double? nearestDelta;
    for (final MatchTimelineInjection injection in injections) {
      final MatchEvent? event = viewState.eventById(injection.id);
      if (!_isFocusEligible(event)) {
        continue;
      }
      final double delta = (positionSeconds - injection.peakSeconds).abs();
      if (nearest == null || delta < nearestDelta!) {
        nearest = event;
        nearestDelta = delta;
      }
    }
    return nearest;
  }

  static bool _isFocusEligible(MatchEvent? event) {
    if (event == null) {
      return false;
    }
    switch (event.type) {
      case MatchViewerEventType.kickoff:
      case MatchViewerEventType.halftime:
      case MatchViewerEventType.fulltime:
      case MatchViewerEventType.substitution:
        return false;
      default:
        return true;
    }
  }

  static bool _isVarWindow({
    required MatchEvent? focusEvent,
    required double positionSeconds,
  }) {
    if (focusEvent == null || !_isReviewable(focusEvent.type)) {
      return false;
    }
    final double delta = positionSeconds - focusEvent.timeSeconds;
    return delta >= -0.15 && delta < 0.9;
  }

  static bool _isReviewable(MatchViewerEventType type) {
    return type == MatchViewerEventType.goal ||
        type == MatchViewerEventType.offside ||
        type == MatchViewerEventType.redCard;
  }

  static ({String? headline, String? subtitle}) _commentaryForEvent({
    required MatchEvent? focusEvent,
    required double positionSeconds,
    required bool isVarChecking,
  }) {
    if (focusEvent == null) {
      return (headline: null, subtitle: null);
    }
    if (isVarChecking) {
      return (
        headline: 'VAR checking...',
        subtitle: focusEvent.commentary.isNotEmpty
            ? focusEvent.commentary
            : focusEvent.bannerText,
      );
    }
    return (
      headline: _headlineForEvent(focusEvent, positionSeconds),
      subtitle: focusEvent.commentary.isNotEmpty
          ? focusEvent.commentary
          : focusEvent.bannerText,
    );
  }

  static String _headlineForEvent(
    MatchEvent event,
    double positionSeconds,
  ) {
    switch (event.type) {
      case MatchViewerEventType.attack:
      case MatchViewerEventType.miss:
      case MatchViewerEventType.penalty:
      case MatchViewerEventType.setPiece:
        return 'Great chance!';
      case MatchViewerEventType.save:
        return 'What a save!';
      case MatchViewerEventType.offside:
        return 'Offside!';
      case MatchViewerEventType.goal:
        return positionSeconds < event.timeSeconds ? 'Great chance!' : 'Goal!';
      case MatchViewerEventType.redCard:
        return 'Big decision!';
      default:
        return event.bannerText;
    }
  }

  static MatchPitchPresentation _pitchPresentation({
    required MatchViewState viewState,
    required double positionSeconds,
    required MatchTimelineFrame displayFrame,
    required MatchTimelineFrame leftFrame,
    required MatchTimelineFrame rightFrame,
    required double interpolationT,
    required MatchEvent? focusEvent,
    required double introScaleBoost,
  }) {
    final BroadcastCameraPreset cameraPreset = _cameraPresetForEvent(
      focusEvent: focusEvent,
      positionSeconds: positionSeconds,
    );
    final bool attacksRight = _attacksRightForFocus(
      displayFrame: displayFrame,
      focusEvent: focusEvent,
    );
    final double baseScale = switch (cameraPreset) {
      BroadcastCameraPreset.broadcast => 1,
      BroadcastCameraPreset.attackZoom => 1.1,
      BroadcastCameraPreset.goalZoom => 1.16,
      BroadcastCameraPreset.replayCamera => 1.13,
    };
    final double basePanX = switch (cameraPreset) {
      BroadcastCameraPreset.broadcast => 0,
      BroadcastCameraPreset.attackZoom => attacksRight ? -0.07 : 0.07,
      BroadcastCameraPreset.goalZoom => attacksRight ? -0.11 : 0.11,
      BroadcastCameraPreset.replayCamera => attacksRight ? -0.09 : 0.09,
    };
    final double ballCenterDelta = (50 - displayFrame.ball.position.y) / 50;
    final double basePanY = switch (cameraPreset) {
      BroadcastCameraPreset.broadcast => ballCenterDelta * 0.015,
      BroadcastCameraPreset.attackZoom => ballCenterDelta * 0.035,
      BroadcastCameraPreset.goalZoom => ballCenterDelta * 0.045,
      BroadcastCameraPreset.replayCamera => ballCenterDelta * 0.04,
    };
    final String seedRoot = _seedRoot(
      viewState: viewState,
      focusEvent: focusEvent,
      leftFrame: leftFrame,
      rightFrame: rightFrame,
      cameraPreset: cameraPreset,
    );
    final double scaleNoise = _centeredFraction('$seedRoot|scale') * 0.02;
    final double panXNoise = _centeredFraction('$seedRoot|pan-x') * 0.02;
    final double panYNoise = _centeredFraction('$seedRoot|pan-y') * 0.018;
    return MatchPitchPresentation(
      cameraPreset: cameraPreset,
      scale:
          (baseScale + introScaleBoost + scaleNoise).clamp(1, 1.19).toDouble(),
      panX: (basePanX + panXNoise).clamp(-0.12, 0.12).toDouble(),
      panY: (basePanY + panYNoise).clamp(-0.08, 0.08).toDouble(),
      motionSeedKey: seedRoot,
      enableMicroVariation: true,
      leftFrame: leftFrame,
      rightFrame: rightFrame,
      interpolationT: interpolationT.clamp(0, 1),
    );
  }

  static BroadcastCameraPreset _cameraPresetForEvent({
    required MatchEvent? focusEvent,
    required double positionSeconds,
  }) {
    if (focusEvent == null) {
      return BroadcastCameraPreset.broadcast;
    }
    final double delta = positionSeconds - focusEvent.timeSeconds;
    if (focusEvent.type == MatchViewerEventType.goal) {
      if (delta >= 0.9 && delta < 1.7) {
        return BroadcastCameraPreset.replayCamera;
      }
      return BroadcastCameraPreset.goalZoom;
    }
    if (focusEvent.type == MatchViewerEventType.attack ||
        focusEvent.type == MatchViewerEventType.save ||
        focusEvent.type == MatchViewerEventType.miss ||
        focusEvent.type == MatchViewerEventType.offside ||
        focusEvent.type == MatchViewerEventType.penalty ||
        focusEvent.type == MatchViewerEventType.setPiece) {
      if (focusEvent.isMajor && delta >= 0.75 && delta < 1.5) {
        return BroadcastCameraPreset.replayCamera;
      }
      return BroadcastCameraPreset.attackZoom;
    }
    if (focusEvent.type == MatchViewerEventType.redCard &&
        delta >= 0.85 &&
        delta < 1.55) {
      return BroadcastCameraPreset.replayCamera;
    }
    return BroadcastCameraPreset.broadcast;
  }

  static bool _attacksRightForFocus({
    required MatchTimelineFrame displayFrame,
    required MatchEvent? focusEvent,
  }) {
    final MatchViewerSide side = focusEvent?.teamId == 'away'
        ? MatchViewerSide.away
        : MatchViewerSide.home;
    return side == MatchViewerSide.home
        ? displayFrame.homeAttacksRight
        : !displayFrame.homeAttacksRight;
  }

  static String _seedRoot({
    required MatchViewState viewState,
    required MatchEvent? focusEvent,
    required MatchTimelineFrame leftFrame,
    required MatchTimelineFrame rightFrame,
    required BroadcastCameraPreset cameraPreset,
  }) {
    final String root =
        (viewState.deterministicSeed ?? viewState.matchId.hashCode.abs())
            .toString();
    return '$root|${focusEvent?.id ?? 'ambient'}|${leftFrame.id}|${rightFrame.id}|${cameraPreset.name}';
  }

  static String _clockLabel(double positionSeconds) {
    final int totalSeconds = positionSeconds.floor().clamp(0, 5999);
    final int minutes = totalSeconds ~/ 60;
    final int seconds = totalSeconds % 60;
    return '$minutes:${seconds.toString().padLeft(2, '0')}';
  }

  static double _windowOpacity(
    double positionSeconds, {
    required double start,
    required double end,
    required double fadeIn,
    required double fadeOut,
  }) {
    if (positionSeconds < start || positionSeconds > end) {
      return 0;
    }
    final double fadeInEnd = math.min(end, start + fadeIn);
    if (positionSeconds <= fadeInEnd) {
      return ((positionSeconds - start) / fadeIn).clamp(0, 1).toDouble();
    }
    final double fadeOutStart = math.max(start, end - fadeOut);
    if (positionSeconds >= fadeOutStart) {
      return ((end - positionSeconds) / fadeOut).clamp(0, 1).toDouble();
    }
    return 1;
  }

  static double _centeredFraction(String seed) {
    return (_stableFraction(seed) * 2) - 1;
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
