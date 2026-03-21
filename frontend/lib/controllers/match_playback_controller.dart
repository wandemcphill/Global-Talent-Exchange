import 'package:flutter/foundation.dart';
import 'package:flutter/scheduler.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';

class MatchPlaybackController extends ChangeNotifier {
  MatchPlaybackController({
    required TickerProvider vsync,
    required this.viewState,
    bool autoplay = true,
  }) {
    _ticker = vsync.createTicker(_tick);
    _speeds = <double>[1, 2, 4];
    _positionSeconds = 0;
    if (autoplay) {
      play();
    }
  }

  final MatchViewState viewState;
  late final Ticker _ticker;
  late final List<double> _speeds;
  Duration? _lastElapsed;
  double _positionSeconds = 0;
  int _speedIndex = 0;
  bool _isPlaying = false;

  bool get isPlaying => _isPlaying;

  double get speed => _speeds[_speedIndex];

  double get positionSeconds => _positionSeconds;

  double get progress => viewState.durationSeconds <= 0
      ? 0
      : _positionSeconds / viewState.durationSeconds;

  MatchTimelineFrame get leftFrame => _framePair.$1;

  MatchTimelineFrame get rightFrame => _framePair.$2;

  double get interpolationT => _framePair.$3;

  MatchTimelineFrame get displayFrame =>
      leftFrame.interpolate(rightFrame, interpolationT);

  MatchEvent? get activeEvent {
    final MatchEvent? exact = viewState.eventById(rightFrame.activeEventId);
    if (exact != null &&
        _positionSeconds >= exact.timeSeconds - 1.6 &&
        _positionSeconds <= exact.timeSeconds + 3.0) {
      return exact;
    }
    final MatchEvent? fallback = viewState.eventById(leftFrame.activeEventId);
    if (fallback != null &&
        _positionSeconds >= fallback.timeSeconds - 1.2 &&
        _positionSeconds <= fallback.timeSeconds + 2.5) {
      return fallback;
    }
    return null;
  }

  (MatchTimelineFrame, MatchTimelineFrame, double) get _framePair {
    final List<MatchTimelineFrame> frames = viewState.frames;
    if (frames.length == 1) {
      return (frames.first, frames.first, 0);
    }
    for (int index = 0; index < frames.length - 1; index += 1) {
      final MatchTimelineFrame left = frames[index];
      final MatchTimelineFrame right = frames[index + 1];
      if (_positionSeconds <= right.timeSeconds) {
        final double span = right.timeSeconds - left.timeSeconds;
        final double t =
            span <= 0 ? 0 : (_positionSeconds - left.timeSeconds) / span;
        return (left, right, t.clamp(0, 1));
      }
    }
    return (frames.last, frames.last, 0);
  }

  List<MatchEvent> get upcomingEvents {
    return viewState.events
        .where((MatchEvent event) => event.timeSeconds >= _positionSeconds - 2)
        .take(6)
        .toList(growable: false);
  }

  void play() {
    if (_isPlaying) {
      return;
    }
    _isPlaying = true;
    _lastElapsed = null;
    _ticker.start();
    notifyListeners();
  }

  void pause() {
    if (!_isPlaying) {
      return;
    }
    _isPlaying = false;
    _ticker.stop();
    _lastElapsed = null;
    notifyListeners();
  }

  void togglePlayPause() {
    if (_isPlaying) {
      pause();
    } else {
      play();
    }
  }

  void restart() {
    _positionSeconds = 0;
    _lastElapsed = null;
    notifyListeners();
  }

  void cycleSpeed() {
    _speedIndex = (_speedIndex + 1) % _speeds.length;
    notifyListeners();
  }

  void jumpToNextEvent() {
    for (final MatchEvent event in viewState.events) {
      if (event.timeSeconds > _positionSeconds + 0.2) {
        _positionSeconds = event.timeSeconds;
        _lastElapsed = null;
        notifyListeners();
        return;
      }
    }
    _positionSeconds = viewState.durationSeconds.toDouble();
    pause();
    notifyListeners();
  }

  @override
  void dispose() {
    _ticker.dispose();
    super.dispose();
  }

  void _tick(Duration elapsed) {
    if (!_isPlaying) {
      return;
    }
    final Duration previous = _lastElapsed ?? elapsed;
    _lastElapsed = elapsed;
    final double deltaSeconds =
        (elapsed - previous).inMicroseconds / Duration.microsecondsPerSecond;
    if (deltaSeconds <= 0) {
      return;
    }
    _positionSeconds += deltaSeconds * speed;
    if (_positionSeconds >= viewState.durationSeconds) {
      _positionSeconds = viewState.durationSeconds.toDouble();
      pause();
    } else {
      notifyListeners();
    }
  }
}
