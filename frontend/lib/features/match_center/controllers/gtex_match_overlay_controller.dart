import 'package:gte_frontend/features/match_center/models/match/gtex_broadcast_event.dart';
import 'package:gte_frontend/features/match_center/models/match/gtex_broadcast_hud_state.dart';
import 'package:gte_frontend/features/match_center/models/match/gtex_match_render_mode.dart';
import 'package:gte_frontend/features/match_center/models/match/gtex_match_view_type.dart';
import 'package:gte_frontend/features/match_center/models/match_event.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';
import 'package:gte_frontend/features/match_center/models/match_view_state.dart';

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
    required bool isFullTime,
  }) {
    final bool scoreClockMasked =
        scoreMasked || homeScore == null || awayScore == null;
    final MatchEvent? activeEvent =
        scoreClockMasked ? null : viewState.eventById(frame.activeEventId);
    final GtexBroadcastEvent? varOverlay = _frameVarOverlay(
      frame: frame,
      event: activeEvent,
    );
    final GtexBroadcastEvent? eventOverlay =
        varOverlay == null
            ? _frameEventOverlay(frame: frame, event: activeEvent)
            : null;
    final ({String? line, String? detail}) commentary =
        scoreClockMasked
            ? (line: null, detail: null)
            : _commentaryState(
              frame: frame,
              event: activeEvent,
              eventOverlay: eventOverlay,
              varOverlay: varOverlay,
            );
    return GtexBroadcastHudState(
      clockLabel: scoreClockMasked ? '--:--' : _clockLabel(frame),
      statusLabel: _statusLabel(
        frame: frame,
        isPaused: isPaused,
        isFullTime: isFullTime,
      ),
      homeScore: homeScore,
      awayScore: awayScore,
      scoreMasked: scoreClockMasked,
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
      socialReactions: const <String>[],
      showIntroOverlay: viewerSeconds <= 2.4 && !isFullTime,
      showFullTimeOverlay: isFullTime,
      showSocialRail: spectatorMode,
      canGift: spectatorMode && !isFullTime,
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

  GtexBroadcastEvent? _frameVarOverlay({
    required MatchTimelineFrame frame,
    required MatchEvent? event,
  }) {
    if (event == null || !_isReviewable(event)) {
      return null;
    }
    final bool decisionFrame =
        frame.stage == MatchPlaybackStage.decision ||
        frame.stage == MatchPlaybackStage.post ||
        event.isReviewConfirmed ||
        event.isReviewDisallowed;
    final bool disallowed =
        event.isReviewDisallowed ||
        event.flags.contains('disallowed') ||
        event.flags.contains('offside_disallowed');
    final GtexBroadcastEventType type =
        !decisionFrame
            ? GtexBroadcastEventType.varChecking
            : disallowed
            ? GtexBroadcastEventType.varDisallowed
            : GtexBroadcastEventType.varConfirmed;
    return GtexBroadcastEvent(
      id: 'frame-var-${frame.id}-${event.id}',
      type: type,
      title: switch (type) {
        GtexBroadcastEventType.varChecking => 'VAR checking',
        GtexBroadcastEventType.varDisallowed => 'Decision: disallowed',
        _ => 'Decision: confirmed',
      },
      subtitle: _backendSubtitle(frame: frame, event: event),
      teamId: event.teamId,
      startViewerSeconds: frame.timeSeconds,
      endViewerSeconds: frame.timeSeconds,
    );
  }

  GtexBroadcastEvent? _frameEventOverlay({
    required MatchTimelineFrame frame,
    required MatchEvent? event,
  }) {
    final String? frameTitle = _firstNonEmpty(<String?>[
      frame.eventBanner,
      frame.overlayText,
    ]);
    if (frameTitle == null) {
      return null;
    }
    final GtexBroadcastEventType? type =
        event == null
            ? GtexBroadcastEventType.commentaryBeat
            : _eventType(event) ?? GtexBroadcastEventType.commentaryBeat;
    if (type == null) {
      return null;
    }
    final String title = frameTitle;
    if (title.isEmpty) {
      return null;
    }
    return GtexBroadcastEvent(
      id: 'frame-event-${frame.id}-${event?.id ?? 'banner'}',
      type: type,
      title: title,
      subtitle: _backendSubtitle(frame: frame, event: event),
      teamId: event?.teamId,
      startViewerSeconds: frame.timeSeconds,
      endViewerSeconds: frame.timeSeconds,
    );
  }

  GtexBroadcastEventType? _eventType(MatchEvent event) {
    return switch (event.type) {
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
  }

  ({String? line, String? detail}) _commentaryState({
    required MatchTimelineFrame frame,
    required MatchEvent? event,
    required GtexBroadcastEvent? eventOverlay,
    required GtexBroadcastEvent? varOverlay,
  }) {
    if (varOverlay != null) {
      return (line: varOverlay.title, detail: varOverlay.subtitle);
    }
    if (eventOverlay != null) {
      return (line: eventOverlay.title, detail: eventOverlay.subtitle);
    }
    final String? frameLine = _firstNonEmpty(<String?>[
      frame.overlayText,
      frame.eventBanner,
    ]);
    if (frameLine != null) {
      return (line: _shortCommentary(frameLine), detail: null);
    }
    return (line: null, detail: null);
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

  String? _backendSubtitle({
    required MatchTimelineFrame frame,
    required MatchEvent? event,
  }) {
    final String? value = _firstNonEmpty(<String?>[
      frame.overlayText,
      event?.bannerText,
      event?.commentary,
      event?.reviewReason,
    ]);
    if (value == null) {
      return null;
    }
    return value;
  }

  String _shortCommentary(String value) {
    final String trimmed = value.trim();
    if (trimmed.length <= 58) {
      return trimmed;
    }
    return '${trimmed.substring(0, 55).trimRight()}...';
  }

  String? _firstNonEmpty(Iterable<String?> values) {
    for (final String? value in values) {
      final String trimmed = value?.trim() ?? '';
      if (trimmed.isNotEmpty) {
        return trimmed;
      }
    }
    return null;
  }
}
