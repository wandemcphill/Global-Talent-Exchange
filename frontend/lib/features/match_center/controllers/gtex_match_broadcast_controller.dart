import 'package:flutter/foundation.dart';
import 'package:gte_frontend/features/match_center/controllers/gtex_match_mode_controller.dart';
import 'package:gte_frontend/features/match_center/controllers/gtex_match_overlay_controller.dart';
import 'package:gte_frontend/features/match_center/models/match/gtex_broadcast_hud_state.dart';
import 'package:gte_frontend/features/match_center/models/match/gtex_match_render_mode.dart';
import 'package:gte_frontend/features/match_center/models/match/gtex_match_view_type.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';
import 'package:gte_frontend/features/match_center/models/match_view_state.dart';

class GtexMatchBroadcastController extends ChangeNotifier {
  GtexMatchBroadcastController({
    required MatchViewState viewState,
    required GtexMatchRenderMode initialMode,
    required GtexMatchViewType initialViewType,
    required bool isPremiumUser,
    required bool spectatorMode,
    this.competitionId,
    GtexMatchOverlayController? overlayController,
  }) : _viewState = viewState,
       _spectatorMode = spectatorMode,
       _legacyRuntimeInputQuarantined = initialViewType.isLegacyQuarantined,
       _legacyRuntimeEntitlementSignal =
           isPremiumUser || (competitionId?.trim().isNotEmpty ?? false),
       _modeController = GtexMatchModeController(
         baseViewState: viewState,
         initialMode: initialMode,
       ),
       _overlayController = overlayController ?? GtexMatchOverlayController() {
    _viewerPositionSeconds = _initialBackendDisplaySeconds(viewState);
    _viewType = _resolveInitialViewType(initialViewType);
    _rebuildHudState();
  }

  final MatchViewState _viewState;
  final bool _spectatorMode;
  final String? competitionId;
  final bool _legacyRuntimeInputQuarantined;
  final bool _legacyRuntimeEntitlementSignal;
  final GtexMatchModeController _modeController;
  final GtexMatchOverlayController _overlayController;

  late GtexMatchViewType _viewType;
  double _viewerPositionSeconds = 0;
  late GtexBroadcastHudState _hudState;

  MatchViewState get viewState => _viewState;

  GtexMatchModeController get modeController => _modeController;

  GtexMatchOverlayController get overlayController => _overlayController;

  GtexMatchRenderMode get mode => _modeController.mode;

  GtexMatchViewType get viewType => _viewType;

  double get viewerPositionSeconds => _viewerPositionSeconds;

  String get speedLabel => 'Live';

  bool get isPaused => false;

  bool get legacyRuntimeInputQuarantined => _legacyRuntimeInputQuarantined;

  bool get legacyRuntimeEntitlementSignal => _legacyRuntimeEntitlementSignal;

  bool get isFullTime {
    return currentFrame.phase == MatchViewerPhase.fulltime ||
        authoritativePositionSeconds >= _backendTimelineEndSeconds - 0.05;
  }

  double get authoritativePositionSeconds =>
      _clampToBackendTimeline(_viewerPositionSeconds);

  MatchTimelineFrame get currentFrame =>
      frameAtAuthoritativeSeconds(authoritativePositionSeconds);

  GtexBroadcastHudState get hudState => _hudState;

  int get finalHomeScore =>
      _viewState.frames.isEmpty ? 0 : _viewState.lastFrame.homeScore;

  int get finalAwayScore =>
      _viewState.frames.isEmpty ? 0 : _viewState.lastFrame.awayScore;

  void setMode(GtexMatchRenderMode nextMode) {
    _modeController.setMode(nextMode);
    _viewerPositionSeconds = _clampToBackendTimeline(_viewerPositionSeconds);
    _overlayController.showControls(_viewerPositionSeconds);
    _rebuildHudState();
    notifyListeners();
  }

  void setViewType(GtexMatchViewType nextType) {
    final GtexMatchViewType canonicalNextType = nextType.canonical;
    if (_viewType == canonicalNextType) {
      return;
    }
    _viewType = canonicalNextType;
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
    MatchTimelineFrame selected = _viewState.firstFrame;
    for (final MatchTimelineFrame frame in _viewState.frames) {
      if (frame.timeSeconds > seconds) {
        break;
      }
      selected = frame;
    }
    return selected;
  }

  void _rebuildHudState() {
    final MatchTimelineFrame frame = currentFrame;
    _hudState = _overlayController.buildHudState(
      viewState: _viewState,
      mode: mode,
      viewType: _viewType,
      frame: frame,
      viewerSeconds: _viewerPositionSeconds,
      isPaused: false,
      speedLabel: speedLabel,
      scoreMasked: _viewState.scoreRevealLocked,
      homeScore: _viewState.scoreRevealLocked ? null : frame.homeScore,
      awayScore: _viewState.scoreRevealLocked ? null : frame.awayScore,
      spectatorMode: _spectatorMode,
      isFullTime: isFullTime,
    );
  }

  double get _backendTimelineEndSeconds {
    final double lastFrameSeconds =
        _viewState.frames.isEmpty ? 0 : _viewState.lastFrame.timeSeconds;
    final double declaredDuration = _viewState.durationSeconds.toDouble();
    return declaredDuration > lastFrameSeconds
        ? declaredDuration
        : lastFrameSeconds;
  }

  double _clampToBackendTimeline(double seconds) {
    if (seconds <= 0 || _backendTimelineEndSeconds <= 0) {
      return 0;
    }
    return seconds > _backendTimelineEndSeconds
        ? _backendTimelineEndSeconds
        : seconds;
  }

  GtexMatchViewType _resolveInitialViewType(GtexMatchViewType initialViewType) {
    return initialViewType.canonical;
  }

  static double _initialBackendDisplaySeconds(MatchViewState viewState) {
    if (viewState.frames.isEmpty) {
      return 0;
    }
    final double lastFrameSeconds = viewState.lastFrame.timeSeconds;
    if (viewState.segmentEndSeconds > 0) {
      final double segmentEnd = viewState.segmentEndSeconds.toDouble();
      return segmentEnd > lastFrameSeconds ? lastFrameSeconds : segmentEnd;
    }
    return viewState.firstFrame.timeSeconds;
  }
}
