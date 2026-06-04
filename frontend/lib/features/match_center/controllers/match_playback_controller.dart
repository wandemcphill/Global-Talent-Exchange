import 'package:flutter/foundation.dart';
import 'package:flutter/scheduler.dart';
import 'package:gte_frontend/features/match_center/models/match_event.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';
import 'package:gte_frontend/features/match_center/models/match_view_state.dart';

class MatchPlaybackController extends ChangeNotifier {
  static const int maxFrameGapMs = 2200;
  static const int minAnimationMs = 300;
  static const int defaultAnimationMs = 500;
  static const int maxAnimationMs = 800;
  static const String quarantineMessage =
      'The legacy local 2D match playback controller is quarantined for '
      'launch and must not be used in production.';

  MatchPlaybackController({
    required TickerProvider vsync,
    required this.viewState,
    bool autoplay = true,
  }) {
    throw UnsupportedError(quarantineMessage);
  }

  final MatchViewState viewState;

  bool get isPlaying => false;

  double get speed => 0;

  double get positionSeconds => 0;

  double get progress => 0;

  MatchTimelineFrame get leftFrame => throw UnsupportedError(quarantineMessage);

  MatchTimelineFrame get rightFrame =>
      throw UnsupportedError(quarantineMessage);

  double get interpolationT => throw UnsupportedError(quarantineMessage);

  MatchTimelineFrame get displayFrame =>
      throw UnsupportedError(quarantineMessage);

  MatchEvent? get activeEvent => null;

  List<MatchEvent> get upcomingEvents => const <MatchEvent>[];

  static int clampAnimationDurationMs(int? value) {
    return (value ?? defaultAnimationMs).clamp(minAnimationMs, maxAnimationMs);
  }

  void play() {
    throw UnsupportedError(quarantineMessage);
  }

  void pause() {
    throw UnsupportedError(quarantineMessage);
  }

  void togglePlayPause() {
    throw UnsupportedError(quarantineMessage);
  }

  void restart() {
    throw UnsupportedError(quarantineMessage);
  }

  void cycleSpeed() {
    throw UnsupportedError(quarantineMessage);
  }

  void jumpToNextEvent() {
    throw UnsupportedError(quarantineMessage);
  }
}
