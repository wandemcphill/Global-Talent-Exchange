import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:gte_frontend/controllers/match/gtex_match_mode_controller.dart';
import 'package:gte_frontend/controllers/match/gtex_match_overlay_controller.dart';
import 'package:gte_frontend/models/match/gtex_broadcast_hud_state.dart';
import 'package:gte_frontend/models/match/gtex_match_render_mode.dart';
import 'package:gte_frontend/models/match/gtex_match_view_type.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/services/match_3d_monetization_service.dart';

class GtexMatchBroadcastController extends ChangeNotifier {
  GtexMatchBroadcastController({
    required MatchViewState viewState,
    required GtexMatchRenderMode initialMode,
    required GtexMatchViewType initialViewType,
    required bool isPremiumUser,
    required bool spectatorMode,
    required bool auto3DEnabled,
    this.competitionId,
    Match3dUserEntitlement? entitlement,
    GtexMatchOverlayController? overlayController,
  })  : _viewState = viewState,
        _spectatorMode = spectatorMode,
        _auto3DEnabled = auto3DEnabled,
        _entitlement = entitlement,
        _modeController = GtexMatchModeController(
          baseViewState: viewState,
          initialMode: initialMode,
        ),
        _overlayController = overlayController ?? GtexMatchOverlayController(),
        _isPremiumUser = isPremiumUser {
    _viewType = _resolveInitialViewType(initialViewType);
    _rebuildHudState();
  }

  final MatchViewState _viewState;
  final bool _spectatorMode;
  final bool _auto3DEnabled;
  final String? competitionId;
  final Match3dUserEntitlement? _entitlement;
  final GtexMatchModeController _modeController;
  final GtexMatchOverlayController _overlayController;
  final bool _isPremiumUser;

  static const List<double> _speedOptions = <double>[1, 2, 4];

  late GtexMatchViewType _viewType;
  double _viewerPositionSeconds = 0;
  int _speedIndex = 0;
  bool _isPaused = false;
  late GtexBroadcastHudState _hudState;

  MatchViewState get viewState => _viewState;

  GtexMatchModeController get modeController => _modeController;

  GtexMatchOverlayController get overlayController => _overlayController;

  GtexMatchRenderMode get mode => _modeController.mode;

  GtexMatchViewType get viewType => _viewType;

  double get viewerPositionSeconds => _viewerPositionSeconds;

  double get playbackSpeed => _speedOptions[_speedIndex];

  String get speedLabel => '${playbackSpeed.toStringAsFixed(0)}x';

  bool get isPaused => _isPaused;

  bool get canUsePseudo3D {
    final Match3dUserEntitlement entitlement = _entitlement ??
        Match3dUserEntitlement(
          isPremiumUser: _isPremiumUser,
        );
    return entitlement.isPremiumUser ||
        entitlement.hasUnlockedMatch(_viewState.matchId) ||
        (competitionId != null &&
            entitlement.hasTournamentBoost(competitionId!));
  }

  bool get isFullTime {
    return authoritativePositionSeconds >= _viewState.durationSeconds - 0.05 ||
        currentFrame.phase == MatchViewerPhase.fulltime;
  }

  double get authoritativePositionSeconds =>
      _modeController.authoritativeSecondsForViewer(_viewerPositionSeconds);

  MatchTimelineFrame get currentFrame => frameAtAuthoritativeSeconds(
        authoritativePositionSeconds,
      );

  GtexBroadcastHudState get hudState => _hudState;

  int get finalHomeScore =>
      _viewState.frames.isEmpty ? 0 : _viewState.lastFrame.homeScore;

  int get finalAwayScore =>
      _viewState.frames.isEmpty ? 0 : _viewState.lastFrame.awayScore;

  void advanceBy(Duration delta) {
    if (_isPaused || isFullTime) {
      _rebuildHudState();
      return;
    }
    final double deltaSeconds =
        delta.inMicroseconds / Duration.microsecondsPerSecond;
    if (deltaSeconds <= 0) {
      return;
    }
    _viewerPositionSeconds += deltaSeconds * playbackSpeed;
    _viewerPositionSeconds = _viewerPositionSeconds.clamp(
      0,
      _modeController.targetDurationSeconds.toDouble(),
    );
    if (isFullTime) {
      _isPaused = true;
    }
    _rebuildHudState();
    notifyListeners();
  }

  void togglePause() {
    _isPaused = !_isPaused;
    if (_isPaused) {
      _overlayController.showControls(_viewerPositionSeconds);
    }
    _rebuildHudState();
    notifyListeners();
  }

  void cycleSpeed() {
    _speedIndex = (_speedIndex + 1) % _speedOptions.length;
    _overlayController.showControls(_viewerPositionSeconds);
    _rebuildHudState();
    notifyListeners();
  }

  void replay() {
    final MatchEvent? anchor = _lastReplayableEvent();
    if (anchor != null) {
      final double anchorViewerSeconds =
          _modeController.viewerSecondsForAuthoritative(anchor.timeSeconds);
      _viewerPositionSeconds = math.max(0, anchorViewerSeconds - 2.4);
    } else {
      _viewerPositionSeconds = math.max(0, _viewerPositionSeconds - 6);
    }
    _overlayController.showControls(_viewerPositionSeconds);
    _rebuildHudState();
    notifyListeners();
  }

  void setMode(GtexMatchRenderMode nextMode) {
    final double authoritativeSeconds = authoritativePositionSeconds;
    _modeController.setMode(nextMode);
    _viewerPositionSeconds = _modeController.viewerSecondsForAuthoritative(
      authoritativeSeconds,
    );
    _overlayController.showControls(_viewerPositionSeconds);
    _rebuildHudState();
    notifyListeners();
  }

  void setViewType(GtexMatchViewType nextType) {
    if (nextType == GtexMatchViewType.pseudo3D && !canUsePseudo3D) {
      return;
    }
    if (_viewType == nextType) {
      return;
    }
    _viewType = nextType;
    _rebuildHudState();
    notifyListeners();
  }

  void showControls() {
    _overlayController.showControls(_viewerPositionSeconds);
    _rebuildHudState();
    notifyListeners();
  }

  MatchTimelineFrame frameAtAuthoritativeSeconds(double seconds) {
    if (_viewState.frames.isEmpty) {
      throw StateError('Broadcast controller requires timeline frames.');
    }
    if (seconds <= _viewState.firstFrame.timeSeconds) {
      return _viewState.firstFrame;
    }
    if (seconds >= _viewState.lastFrame.timeSeconds) {
      return _viewState.lastFrame;
    }
    for (int index = 0; index < _viewState.frames.length - 1; index += 1) {
      final MatchTimelineFrame left = _viewState.frames[index];
      final MatchTimelineFrame right = _viewState.frames[index + 1];
      if (seconds >= left.timeSeconds && seconds <= right.timeSeconds) {
        final double span = right.timeSeconds - left.timeSeconds;
        final double t = span <= 0 ? 0 : (seconds - left.timeSeconds) / span;
        return left.interpolate(right, t);
      }
    }
    return _viewState.lastFrame;
  }

  void _rebuildHudState() {
    final ({int? home, int? away, bool masked}) scoreState = _scoreboardState();
    _hudState = _overlayController.buildHudState(
      viewState: _viewState,
      modeController: _modeController,
      mode: mode,
      viewType: _viewType,
      frame: currentFrame,
      viewerSeconds: _viewerPositionSeconds,
      isPaused: _isPaused,
      speedLabel: speedLabel,
      scoreMasked: scoreState.masked,
      homeScore: scoreState.home,
      awayScore: scoreState.away,
      spectatorMode: _spectatorMode,
      pseudo3dEnabled: _viewType == GtexMatchViewType.pseudo3D,
      isFullTime: isFullTime,
    );
  }

  ({int? home, int? away, bool masked}) _scoreboardState() {
    MatchEvent? lastConfirmedGoal;
    for (final MatchEvent event in _viewState.events) {
      if (event.type != MatchViewerEventType.goal) {
        continue;
      }
      if (_viewerPositionSeconds < _goalRevealViewerSeconds(event)) {
        continue;
      }
      if (_goalIsDisallowed(event)) {
        continue;
      }
      lastConfirmedGoal = event;
    }
    if (lastConfirmedGoal != null) {
      return (
        home: lastConfirmedGoal.homeScore,
        away: lastConfirmedGoal.awayScore,
        masked: false,
      );
    }
    if (isFullTime) {
      return (
        home: finalHomeScore,
        away: finalAwayScore,
        masked: false,
      );
    }
    return (home: null, away: null, masked: true);
  }

  double _goalRevealViewerSeconds(MatchEvent event) {
    final double viewerSeconds =
        _modeController.viewerSecondsForAuthoritative(event.timeSeconds);
    if (event.commitsScoreAfterReview || event.reviewable) {
      return viewerSeconds + 1.15;
    }
    return viewerSeconds;
  }

  bool _goalIsDisallowed(MatchEvent event) {
    return event.isReviewDisallowed ||
        event.flags.contains('disallowed') ||
        event.flags.contains('offside_disallowed');
  }

  MatchEvent? _lastReplayableEvent() {
    MatchEvent? result;
    final double authoritativeSeconds = authoritativePositionSeconds;
    for (final MatchEvent event in _viewState.events) {
      if (event.timeSeconds > authoritativeSeconds) {
        break;
      }
      if (<MatchViewerEventType>{
        MatchViewerEventType.goal,
        MatchViewerEventType.miss,
        MatchViewerEventType.save,
        MatchViewerEventType.offside,
        MatchViewerEventType.redCard,
      }.contains(event.type)) {
        result = event;
      }
    }
    return result;
  }

  GtexMatchViewType _resolveInitialViewType(GtexMatchViewType initialViewType) {
    if ((initialViewType == GtexMatchViewType.pseudo3D || _auto3DEnabled) &&
        canUsePseudo3D) {
      return GtexMatchViewType.pseudo3D;
    }
    return GtexMatchViewType.twoD;
  }
}
