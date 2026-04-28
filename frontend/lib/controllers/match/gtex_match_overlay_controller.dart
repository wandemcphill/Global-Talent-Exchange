import 'dart:math' as math;

import 'package:gte_frontend/models/match/gtex_broadcast_event.dart';
import 'package:gte_frontend/models/match/gtex_broadcast_hud_state.dart';
import 'package:gte_frontend/models/match/gtex_match_render_mode.dart';
import 'package:gte_frontend/models/match/gtex_match_view_type.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';

import 'gtex_match_mode_controller.dart';

class GtexMatchOverlayController {
  GtexMatchOverlayController({this.controlsAutoHideSeconds = 4});

  final double controlsAutoHideSeconds;

  double _controlsVisibleUntilSeconds = -1;

  void showControls(double viewerSeconds) {
    _controlsVisibleUntilSeconds = viewerSeconds + controlsAutoHideSeconds;
  }

  void hideControls() {
    _controlsVisibleUntilSeconds = 0;
  }

  GtexBroadcastHudState buildHudState({
    required MatchViewState viewState,
    required GtexMatchModeController modeController,
    required GtexMatchRenderMode mode,
    required GtexMatchViewType viewType,
    required MatchTimelineFrame frame,
    required double viewerSeconds,
    required bool isPaused,
    required String speedLabel,
    required bool scoreMasked,
    required int? homeScore,
    required int? awayScore,
    required bool spectatorMode,
    required bool pseudo3dEnabled,
    required bool isFullTime,
  }) {
    final GtexBroadcastEvent? varOverlay = _activeVarOverlay(
      viewState: viewState,
      modeController: modeController,
      viewerSeconds: viewerSeconds,
    );
    final GtexBroadcastEvent? eventOverlay =
        varOverlay == null
            ? _activeEventOverlay(
              viewState: viewState,
              modeController: modeController,
              viewerSeconds: viewerSeconds,
            )
            : null;
    final ({String? line, String? detail}) commentary = _commentaryState(
      viewState: viewState,
      modeController: modeController,
      viewerSeconds: viewerSeconds,
      eventOverlay: eventOverlay,
      varOverlay: varOverlay,
    );
    return GtexBroadcastHudState(
      clockLabel: _clockLabel(frame),
      statusLabel: _statusLabel(
        frame: frame,
        isPaused: isPaused,
        isFullTime: isFullTime,
      ),
      homeScore: homeScore,
      awayScore: awayScore,
      scoreMasked: scoreMasked,
      controlsVisible: _controlsVisible(
        viewerSeconds: viewerSeconds,
        isPaused: isPaused,
        frame: frame,
        isFullTime: isFullTime,
      ),
      isPaused: isPaused,
      speedLabel: speedLabel,
      mode: mode,
      viewType: viewType,
      eventOverlay: eventOverlay,
      commentary: commentary.line,
      commentaryDetail: commentary.detail,
      varOverlay: varOverlay,
      socialReactions:
          spectatorMode
              ? _socialReactions(
                eventOverlay: eventOverlay,
                varOverlay: varOverlay,
                pseudo3dEnabled: pseudo3dEnabled,
              )
              : const <String>[],
      showIntroOverlay: viewerSeconds <= 2.4 && !isFullTime,
      showFullTimeOverlay: isFullTime,
      showSocialRail: spectatorMode,
      canGift: false,
    );
  }

  bool _controlsVisible({
    required double viewerSeconds,
    required bool isPaused,
    required MatchTimelineFrame frame,
    required bool isFullTime,
  }) {
    if (isPaused || isFullTime || frame.phase == MatchViewerPhase.halftime) {
      return true;
    }
    return viewerSeconds < _controlsVisibleUntilSeconds;
  }

  GtexBroadcastEvent? _activeVarOverlay({
    required MatchViewState viewState,
    required GtexMatchModeController modeController,
    required double viewerSeconds,
  }) {
    for (final MatchEvent event in viewState.events.reversed) {
      if (!_isReviewable(event)) {
        continue;
      }
      final double eventViewerSeconds = modeController
          .viewerSecondsForAuthoritative(event.timeSeconds);
      final double delta = viewerSeconds - eventViewerSeconds;
      if (delta >= -0.18 && delta < 0.72) {
        return GtexBroadcastEvent(
          id: 'var-checking-${event.id}',
          type: GtexBroadcastEventType.varChecking,
          title: 'VAR checking',
          subtitle: _varSubtitle(event),
          teamId: event.teamId,
          startViewerSeconds: eventViewerSeconds - 0.18,
          endViewerSeconds: eventViewerSeconds + 0.72,
        );
      }
      if (delta >= 0.72 && delta < 1.55) {
        return GtexBroadcastEvent(
          id: 'var-decision-${event.id}',
          type:
              event.isReviewDisallowed
                  ? GtexBroadcastEventType.varDisallowed
                  : GtexBroadcastEventType.varConfirmed,
          title:
              event.isReviewDisallowed
                  ? 'Decision: disallowed'
                  : 'Decision: confirmed',
          subtitle: _varDecisionSubtitle(event),
          teamId: event.teamId,
          startViewerSeconds: eventViewerSeconds + 0.72,
          endViewerSeconds: eventViewerSeconds + 1.55,
        );
      }
    }
    return null;
  }

  GtexBroadcastEvent? _activeEventOverlay({
    required MatchViewState viewState,
    required GtexMatchModeController modeController,
    required double viewerSeconds,
  }) {
    for (final MatchEvent event in viewState.events.reversed) {
      final GtexBroadcastEvent? mapped = _mapMatchEvent(
        event: event,
        modeController: modeController,
      );
      if (mapped != null && mapped.isVisibleAt(viewerSeconds)) {
        return mapped;
      }
    }
    final List<GtexBroadcastEvent> viewerOnlyBeats = modeController
        .visibleViewerOnlyBeats(viewerSeconds);
    if (viewerOnlyBeats.isNotEmpty) {
      return viewerOnlyBeats.last;
    }
    return null;
  }

  GtexBroadcastEvent? _mapMatchEvent({
    required MatchEvent event,
    required GtexMatchModeController modeController,
  }) {
    final GtexBroadcastEventType? type = switch (event.type) {
      MatchViewerEventType.goal => GtexBroadcastEventType.goal,
      MatchViewerEventType.save ||
      MatchViewerEventType.miss ||
      MatchViewerEventType.attack ||
      MatchViewerEventType.pass ||
      MatchViewerEventType.setPiece ||
      MatchViewerEventType.penalty => GtexBroadcastEventType.missedChance,
      MatchViewerEventType.yellowCard => GtexBroadcastEventType.yellowCard,
      MatchViewerEventType.redCard => GtexBroadcastEventType.redCard,
      MatchViewerEventType.offside => GtexBroadcastEventType.offside,
      MatchViewerEventType.fulltime => GtexBroadcastEventType.fullTime,
      _ => null,
    };
    if (type == null) {
      return null;
    }
    final double startViewerSeconds =
        modeController.viewerSecondsForAuthoritative(event.timeSeconds) - 0.18;
    final double holdSeconds =
        event.type == MatchViewerEventType.goal ? 1.8 : 1.25;
    final String title = _eventTitle(event);
    if (title.isEmpty) {
      return null;
    }
    return GtexBroadcastEvent(
      id: 'event-${event.id}',
      type: type,
      title: title,
      subtitle:
          event.bannerText.trim().isEmpty ? event.commentary : event.bannerText,
      teamId: event.teamId,
      startViewerSeconds: math.max(0, startViewerSeconds),
      endViewerSeconds: math.max(
        startViewerSeconds + 0.8,
        startViewerSeconds + holdSeconds,
      ),
    );
  }

  ({String? line, String? detail}) _commentaryState({
    required MatchViewState viewState,
    required GtexMatchModeController modeController,
    required double viewerSeconds,
    required GtexBroadcastEvent? eventOverlay,
    required GtexBroadcastEvent? varOverlay,
  }) {
    if (varOverlay != null) {
      return (line: varOverlay.title, detail: varOverlay.subtitle);
    }
    if (eventOverlay != null) {
      return (line: eventOverlay.title, detail: eventOverlay.subtitle);
    }
    for (final MatchEvent event in viewState.events.reversed) {
      final double eventViewerSeconds = modeController
          .viewerSecondsForAuthoritative(event.timeSeconds);
      if ((viewerSeconds - eventViewerSeconds).abs() <= 1.2 &&
          event.commentary.trim().isNotEmpty) {
        return (
          line: _shortCommentary(event.commentary),
          detail: event.bannerText.trim().isEmpty ? null : event.bannerText,
        );
      }
    }
    return (line: null, detail: null);
  }

  List<String> _socialReactions({
    required GtexBroadcastEvent? eventOverlay,
    required GtexBroadcastEvent? varOverlay,
    required bool pseudo3dEnabled,
  }) {
    final GtexBroadcastEvent? active = varOverlay ?? eventOverlay;
    if (active == null) {
      return pseudo3dEnabled
          ? const <String>['LIVE', 'FIRE 2 FC', 'CAM+']
          : const <String>['LIVE', 'FIRE 2 FC', 'CHAT'];
    }
    switch (active.type) {
      case GtexBroadcastEventType.goal:
        return const <String>['FIRE 2 FC', 'APPLAUSE 5 FC', 'CROWN 20 FC'];
      case GtexBroadcastEventType.offside:
        return const <String>['OOH', 'APPLAUSE 5 FC', 'CHAT'];
      case GtexBroadcastEventType.varChecking:
      case GtexBroadcastEventType.varConfirmed:
      case GtexBroadcastEventType.varDisallowed:
        return const <String>['FIRE 2 FC', 'WAIT', 'CHAT'];
      case GtexBroadcastEventType.redCard:
        return const <String>['DRAMA', 'CROWN 20 FC', 'CHAT'];
      case GtexBroadcastEventType.missedChance:
        return const <String>['OOH', 'FIRE 2 FC', 'CHAT'];
      default:
        return const <String>['LIVE', 'FIRE 2 FC', 'CHAT'];
    }
  }

  bool _isReviewable(MatchEvent event) {
    return event.reviewable ||
        event.flags.contains('reviewable') ||
        <MatchViewerEventType>{
          MatchViewerEventType.goal,
          MatchViewerEventType.offside,
          MatchViewerEventType.redCard,
        }.contains(event.type);
  }

  String _clockLabel(MatchTimelineFrame frame) {
    final int totalSeconds = (frame.clockMinute * 60).round();
    final int minutes = totalSeconds ~/ 60;
    final int seconds = totalSeconds % 60;
    final String paddedSeconds = seconds.toString().padLeft(2, '0');
    return '$minutes:$paddedSeconds';
  }

  String _statusLabel({
    required MatchTimelineFrame frame,
    required bool isPaused,
    required bool isFullTime,
  }) {
    if (isFullTime || frame.phase == MatchViewerPhase.fulltime) {
      return 'FT';
    }
    if (frame.phase == MatchViewerPhase.halftime) {
      return 'HT';
    }
    if (isPaused) {
      return 'PAUSED';
    }
    return 'LIVE';
  }

  String _eventTitle(MatchEvent event) {
    switch (event.type) {
      case MatchViewerEventType.goal:
        return 'Goal';
      case MatchViewerEventType.save:
        return 'Huge save';
      case MatchViewerEventType.miss:
      case MatchViewerEventType.attack:
      case MatchViewerEventType.pass:
      case MatchViewerEventType.setPiece:
      case MatchViewerEventType.penalty:
        return 'Chance';
      case MatchViewerEventType.yellowCard:
        return 'Yellow card';
      case MatchViewerEventType.redCard:
        return 'Red card';
      case MatchViewerEventType.offside:
        return 'Offside';
      case MatchViewerEventType.fulltime:
        return 'Full time';
      default:
        return '';
    }
  }

  String _varSubtitle(MatchEvent event) {
    if (event.reviewReason?.trim().isNotEmpty == true) {
      return event.reviewReason!.trim();
    }
    if (event.commentary.trim().isNotEmpty) {
      return event.commentary;
    }
    return 'Major moment under review';
  }

  String _varDecisionSubtitle(MatchEvent event) {
    if (event.bannerText.trim().isNotEmpty) {
      return event.bannerText;
    }
    return event.isReviewDisallowed
        ? 'No score change applied'
        : 'Score stands';
  }

  String _shortCommentary(String value) {
    final String trimmed = value.trim();
    if (trimmed.length <= 58) {
      return trimmed;
    }
    return '${trimmed.substring(0, 55).trimRight()}...';
  }
}
