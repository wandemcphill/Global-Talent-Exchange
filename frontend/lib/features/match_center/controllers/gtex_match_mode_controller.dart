import 'package:flutter/foundation.dart';
import 'package:gte_frontend/features/match_center/models/match/gtex_broadcast_event.dart';
import 'package:gte_frontend/features/match_center/models/match/gtex_match_render_mode.dart';
import 'package:gte_frontend/features/match_center/models/match_view_state.dart';

class GtexMatchModeController extends ChangeNotifier {
  GtexMatchModeController({
    required MatchViewState baseViewState,
    GtexMatchRenderMode initialMode = GtexMatchRenderMode.standard,
  }) : _baseViewState = baseViewState,
       _mode = initialMode {
    _rebuildProjection();
  }

  final MatchViewState _baseViewState;

  late GtexMatchRenderMode _mode;
  late int _targetDurationSeconds;
  static const List<GtexBroadcastEvent> _noViewerOnlyBeats =
      <GtexBroadcastEvent>[];

  MatchViewState get baseViewState => _baseViewState;

  GtexMatchRenderMode get mode => _mode;

  int get targetDurationSeconds => _targetDurationSeconds;

  List<GtexBroadcastEvent> get viewerOnlyBeats => _noViewerOnlyBeats;

  void setMode(GtexMatchRenderMode nextMode) {
    if (_mode == nextMode) {
      return;
    }
    _mode = nextMode;
    _rebuildProjection();
    notifyListeners();
  }

  double viewerSecondsForAuthoritative(double authoritativeSeconds) {
    return _clampToBackendTimeline(authoritativeSeconds);
  }

  double authoritativeSecondsForViewer(double viewerSeconds) {
    return _clampToBackendTimeline(viewerSeconds);
  }

  List<GtexBroadcastEvent> visibleViewerOnlyBeats(double viewerSeconds) {
    return _noViewerOnlyBeats;
  }

  void _rebuildProjection() {
    _targetDurationSeconds = _resolveTargetDuration();
  }

  int _resolveTargetDuration() {
    final int declaredDuration = _baseViewState.durationSeconds;
    final int lastFrameSecond =
        _baseViewState.frames.isEmpty
            ? 0
            : _baseViewState.lastFrame.timeSeconds.ceil();
    final int backendDuration =
        declaredDuration > lastFrameSecond ? declaredDuration : lastFrameSecond;
    return backendDuration < 0 ? 0 : backendDuration;
  }

  double _clampToBackendTimeline(double seconds) {
    if (seconds <= 0 || _targetDurationSeconds <= 0) {
      return 0;
    }
    final double endSeconds = _targetDurationSeconds.toDouble();
    return seconds > endSeconds ? endSeconds : seconds;
  }
}
