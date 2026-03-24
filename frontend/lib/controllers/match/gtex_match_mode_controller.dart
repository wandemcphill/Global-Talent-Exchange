import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:gte_frontend/models/match/gtex_broadcast_event.dart';
import 'package:gte_frontend/models/match/gtex_match_render_mode.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_view_state.dart';

class GtexMatchModeController extends ChangeNotifier {
  GtexMatchModeController({
    required MatchViewState baseViewState,
    GtexMatchRenderMode initialMode = GtexMatchRenderMode.standard,
  })  : _baseViewState = baseViewState,
        _mode = initialMode {
    _rebuildProjection();
  }

  final MatchViewState _baseViewState;

  late GtexMatchRenderMode _mode;
  late int _targetDurationSeconds;
  List<GtexBroadcastEvent> _viewerOnlyBeats = const <GtexBroadcastEvent>[];

  MatchViewState get baseViewState => _baseViewState;

  GtexMatchRenderMode get mode => _mode;

  int get targetDurationSeconds => _targetDurationSeconds;

  List<GtexBroadcastEvent> get viewerOnlyBeats =>
      List<GtexBroadcastEvent>.unmodifiable(_viewerOnlyBeats);

  void setMode(GtexMatchRenderMode nextMode) {
    if (_mode == nextMode) {
      return;
    }
    _mode = nextMode;
    _rebuildProjection();
    notifyListeners();
  }

  double viewerSecondsForAuthoritative(double authoritativeSeconds) {
    if (_baseViewState.durationSeconds <= 0) {
      return 0;
    }
    final double progress =
        (authoritativeSeconds / _baseViewState.durationSeconds).clamp(0, 1);
    return progress * _targetDurationSeconds;
  }

  double authoritativeSecondsForViewer(double viewerSeconds) {
    if (_targetDurationSeconds <= 0) {
      return 0;
    }
    final double progress = (viewerSeconds / _targetDurationSeconds).clamp(0, 1);
    return progress * _baseViewState.durationSeconds;
  }

  List<GtexBroadcastEvent> visibleViewerOnlyBeats(double viewerSeconds) {
    return _viewerOnlyBeats
        .where((GtexBroadcastEvent beat) => beat.isVisibleAt(viewerSeconds))
        .toList(growable: false);
  }

  void _rebuildProjection() {
    _targetDurationSeconds = _resolveTargetDuration();
    _viewerOnlyBeats = _buildViewerOnlyBeats();
  }

  int _resolveTargetDuration() {
    final int eventCount = _baseViewState.events.length;
    final int reviewableCount = _baseViewState.events
        .where((MatchEvent event) => _isReviewable(event))
        .length;
    final int dramaticCount = _baseViewState.events
        .where((MatchEvent event) => _isDramatic(event))
        .length;
    final double richness = math.min(
      1,
      ((eventCount * 0.07) + (reviewableCount * 0.12) + (dramaticCount * 0.1)),
    );
    final int minimum = _mode.minimumDurationSeconds;
    final int maximum = _mode.maximumDurationSeconds;
    return minimum + ((maximum - minimum) * richness).round();
  }

  List<GtexBroadcastEvent> _buildViewerOnlyBeats() {
    if (_mode.viewerOnlyBeatDensity <= 0) {
      return const <GtexBroadcastEvent>[];
    }
    final List<GtexBroadcastEvent> beats = <GtexBroadcastEvent>[];
    for (final MatchEvent event in _baseViewState.events) {
      if (!_isBeatEligible(event)) {
        continue;
      }
      final double eventViewerSeconds =
          viewerSecondsForAuthoritative(event.timeSeconds);
      final String title = _viewerOnlyTitle(event);
      final String? subtitle = _viewerOnlySubtitle(event);
      if (title.isEmpty) {
        continue;
      }
      final double leadInSeconds =
          _mode == GtexMatchRenderMode.cinematic ? 1.25 : 0.7;
      beats.add(
        GtexBroadcastEvent(
          id: 'viewer-beat-${event.id}',
          type: GtexBroadcastEventType.commentaryBeat,
          title: title,
          subtitle: subtitle,
          teamId: event.teamId,
          startViewerSeconds: math.max(0, eventViewerSeconds - leadInSeconds),
          endViewerSeconds: math.max(0.9, eventViewerSeconds - 0.1),
          viewerOnly: true,
        ),
      );
    }
    return beats;
  }

  bool _isBeatEligible(MatchEvent event) {
    if (_mode == GtexMatchRenderMode.standard) {
      return _isReviewable(event) || event.type == MatchViewerEventType.attack;
    }
    return _isDramatic(event);
  }

  bool _isDramatic(MatchEvent event) {
    return <MatchViewerEventType>{
      MatchViewerEventType.attack,
      MatchViewerEventType.goal,
      MatchViewerEventType.save,
      MatchViewerEventType.miss,
      MatchViewerEventType.offside,
      MatchViewerEventType.redCard,
      MatchViewerEventType.setPiece,
      MatchViewerEventType.penalty,
    }.contains(event.type);
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

  String _viewerOnlyTitle(MatchEvent event) {
    switch (event.type) {
      case MatchViewerEventType.attack:
      case MatchViewerEventType.setPiece:
      case MatchViewerEventType.penalty:
        return 'Pressure building';
      case MatchViewerEventType.goal:
        return 'Crowd rising';
      case MatchViewerEventType.save:
      case MatchViewerEventType.miss:
        return 'Chance opening up';
      case MatchViewerEventType.offside:
        return 'Tight line here';
      case MatchViewerEventType.redCard:
        return 'Big decision coming';
      default:
        return '';
    }
  }

  String? _viewerOnlySubtitle(MatchEvent event) {
    if (event.commentary.trim().isNotEmpty) {
      return event.commentary;
    }
    return event.bannerText.trim().isEmpty ? null : event.bannerText;
  }
}
