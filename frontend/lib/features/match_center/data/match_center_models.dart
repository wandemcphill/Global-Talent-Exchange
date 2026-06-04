import 'package:flutter/foundation.dart';
import 'package:gte_frontend/features/match_center/data/live_match_fixtures.dart';

enum MatchCenterSurfaceState { confirmed, empty, blocked, degraded, syncing }

enum MatchCenterInspectorTab { timeline, stats }

extension MatchCenterSurfaceStateX on MatchCenterSurfaceState {
  String get label {
    switch (this) {
      case MatchCenterSurfaceState.confirmed:
        return 'CONFIRMED';
      case MatchCenterSurfaceState.empty:
        return 'EMPTY';
      case MatchCenterSurfaceState.blocked:
        return 'BLOCKED';
      case MatchCenterSurfaceState.degraded:
        return 'DEGRADED';
      case MatchCenterSurfaceState.syncing:
        return 'SYNCING';
    }
  }

  bool get isRenderable {
    switch (this) {
      case MatchCenterSurfaceState.confirmed:
      case MatchCenterSurfaceState.degraded:
        return true;
      case MatchCenterSurfaceState.empty:
      case MatchCenterSurfaceState.blocked:
      case MatchCenterSurfaceState.syncing:
        return false;
    }
  }

  bool get requiresAttention {
    switch (this) {
      case MatchCenterSurfaceState.blocked:
      case MatchCenterSurfaceState.degraded:
      case MatchCenterSurfaceState.syncing:
        return true;
      case MatchCenterSurfaceState.confirmed:
      case MatchCenterSurfaceState.empty:
        return false;
    }
  }
}

@immutable
class MatchCenterMetric {
  const MatchCenterMetric({
    required this.label,
    required this.value,
    this.positive = true,
  });

  final String label;
  final String value;
  final bool positive;
}

@immutable
class MatchCenterReadinessItem {
  const MatchCenterReadinessItem({
    required this.label,
    required this.state,
    required this.detail,
  });

  final String label;
  final MatchCenterSurfaceState state;
  final String detail;
}

@immutable
class MatchCenterReadiness {
  const MatchCenterReadiness({
    required this.scorebug,
    required this.pitch,
    required this.timeline,
    required this.stats,
    required this.liveIntelligence,
    required this.items,
  });

  final MatchCenterSurfaceState scorebug;
  final MatchCenterSurfaceState pitch;
  final MatchCenterSurfaceState timeline;
  final MatchCenterSurfaceState stats;
  final MatchCenterSurfaceState liveIntelligence;
  final List<MatchCenterReadinessItem> items;

  factory MatchCenterReadiness.fromSnapshot(
    LiveMatchSnapshot match, {
    bool feedDegraded = false,
    bool timelineDegraded = false,
    bool statsDegraded = false,
    bool intelligenceDegraded = false,
    bool scoreClockAuthoritative = true,
    bool timelineVerified = true,
    MatchCenterSurfaceState unverifiedRealtimeState =
        MatchCenterSurfaceState.syncing,
    String? scoreClockDetail,
    String? timelineDetail,
  }) {
    final bool hasMatchId = matchCenterHasText(match.matchId);
    final bool hasPitchData =
        match.homeLineup.isNotEmpty || match.awayLineup.isNotEmpty;
    final bool hasTimeline = match.commentary.isNotEmpty;
    final bool hasStats = match.stats != null;
    final MatchCenterSurfaceState scorebug =
        !scoreClockAuthoritative
            ? unverifiedRealtimeState
            : hasMatchId
            ? _confirmedOrDegraded(feedDegraded)
            : MatchCenterSurfaceState.blocked;
    final MatchCenterSurfaceState pitch =
        hasPitchData
            ? _confirmedOrDegraded(feedDegraded)
            : MatchCenterSurfaceState.empty;
    final MatchCenterSurfaceState timeline =
        !timelineVerified
            ? unverifiedRealtimeState
            : hasTimeline
            ? _confirmedOrDegraded(feedDegraded || timelineDegraded)
            : MatchCenterSurfaceState.empty;
    final MatchCenterSurfaceState stats =
        hasStats
            ? _confirmedOrDegraded(feedDegraded || statsDegraded)
            : MatchCenterSurfaceState.blocked;
    final MatchCenterSurfaceState intelligence = _intelligenceState(
      match.liveIntelligence,
      feedDegraded || intelligenceDegraded,
    );

    return MatchCenterReadiness(
      scorebug: scorebug,
      pitch: pitch,
      timeline: timeline,
      stats: stats,
      liveIntelligence: intelligence,
      items: <MatchCenterReadinessItem>[
        MatchCenterReadinessItem(
          label: 'Scorebug',
          state: scorebug,
          detail:
              !scoreClockAuthoritative
                  ? scoreClockDetail ??
                      'Backend score and clock snapshot not confirmed'
                  : hasMatchId
                  ? 'Match id resolved'
                  : 'Match id blocked',
        ),
        MatchCenterReadinessItem(
          label: '2D pitch',
          state: pitch,
          detail:
              hasPitchData
                  ? '${match.homeLineup.length + match.awayLineup.length} lineup records'
                  : 'Lineup data unavailable',
        ),
        MatchCenterReadinessItem(
          label: 'Timeline',
          state: timeline,
          detail:
              !timelineVerified
                  ? timelineDetail ??
                      'Timeline withheld until backend score-clock truth confirms match state'
                  : hasTimeline
                  ? '${match.commentary.length} verified events'
                  : 'No timeline events',
        ),
        MatchCenterReadinessItem(
          label: 'Stats',
          state: stats,
          detail: hasStats ? 'Stats payload loaded' : 'No stats payload',
        ),
        MatchCenterReadinessItem(
          label: 'Intelligence',
          state: intelligence,
          detail:
              match.liveIntelligence == null
                  ? 'No intelligence payload'
                  : match.liveIntelligence!.status,
        ),
      ],
    );
  }
}

@immutable
class MatchCenterOverlayAvailability {
  const MatchCenterOverlayAvailability({
    required this.mode,
    required this.label,
    required this.state,
    required this.detail,
    required this.metrics,
  });

  final LiveMatchOverlayMode mode;
  final String label;
  final MatchCenterSurfaceState state;
  final String detail;
  final List<MatchCenterMetric> metrics;

  bool get isSupported => state.isRenderable;

  factory MatchCenterOverlayAvailability.fromSnapshot(
    LiveMatchSnapshot match,
    LiveMatchOverlayMode mode, {
    bool feedDegraded = false,
  }) {
    final LiveMatchStatsSnapshot? stats = match.stats;
    final bool hasPitchData =
        match.homeLineup.isNotEmpty || match.awayLineup.isNotEmpty;
    final String label = matchCenterOverlayLabel(mode);

    if (mode == LiveMatchOverlayMode.shape) {
      if (!hasPitchData) {
        return MatchCenterOverlayAvailability(
          mode: mode,
          label: label,
          state: MatchCenterSurfaceState.empty,
          detail: 'Lineup data is required before the shape shell can render.',
          metrics: const <MatchCenterMetric>[],
        );
      }
      return MatchCenterOverlayAvailability(
        mode: mode,
        label: label,
        state: _confirmedOrDegraded(feedDegraded),
        detail: 'Lineup shape is available from the current snapshot.',
        metrics: <MatchCenterMetric>[
          MatchCenterMetric(
            label: 'Home XI',
            value: match.homeLineup.length.toString(),
          ),
          MatchCenterMetric(
            label: 'Away XI',
            value: match.awayLineup.length.toString(),
          ),
        ],
      );
    }

    if (stats == null) {
      return MatchCenterOverlayAvailability(
        mode: mode,
        label: label,
        state: MatchCenterSurfaceState.blocked,
        detail: 'Stats payload is required before this overlay can render.',
        metrics: const <MatchCenterMetric>[],
      );
    }

    if (!stats.supportsOverlay(mode)) {
      return MatchCenterOverlayAvailability(
        mode: mode,
        label: label,
        state: MatchCenterSurfaceState.blocked,
        detail: _unsupportedOverlayDetail(mode),
        metrics: const <MatchCenterMetric>[],
      );
    }

    return MatchCenterOverlayAvailability(
      mode: mode,
      label: label,
      state: _confirmedOrDegraded(feedDegraded),
      detail: '$label overlay data is available from the current snapshot.',
      metrics: _overlayMetrics(match, mode),
    );
  }
}

List<MatchCenterOverlayAvailability> matchCenterOverlayStates(
  LiveMatchSnapshot match, {
  bool feedDegraded = false,
}) {
  return LiveMatchOverlayMode.values
      .map(
        (LiveMatchOverlayMode mode) =>
            MatchCenterOverlayAvailability.fromSnapshot(
              match,
              mode,
              feedDegraded: feedDegraded,
            ),
      )
      .toList(growable: false);
}

String matchCenterOverlayLabel(LiveMatchOverlayMode mode) {
  switch (mode) {
    case LiveMatchOverlayMode.shape:
      return 'Shape';
    case LiveMatchOverlayMode.pressure:
      return 'Pressure';
    case LiveMatchOverlayMode.shots:
      return 'Shots';
    case LiveMatchOverlayMode.xg:
      return 'xG';
    case LiveMatchOverlayMode.territory:
      return 'Territory';
    case LiveMatchOverlayMode.market:
      return 'Market';
  }
}

String matchCenterPhaseLabel(LiveMatchSnapshot match) {
  if (match.isFinal) {
    return 'FINAL';
  }
  if (match.isHalftime) {
    return 'HALFTIME';
  }
  if (match.isLive) {
    return 'LIVE';
  }
  return 'PRE-MATCH';
}

String matchCenterClockLabel(LiveMatchSnapshot match) {
  if (match.isFinal) {
    return 'FT';
  }
  if (match.isHalftime) {
    return 'HT';
  }
  if (match.isLive) {
    return '${match.minute}\'';
  }
  return '00\'';
}

bool matchCenterHasText(String? value) {
  return value?.trim().isNotEmpty == true;
}

MatchCenterSurfaceState _confirmedOrDegraded(bool degraded) {
  return degraded
      ? MatchCenterSurfaceState.degraded
      : MatchCenterSurfaceState.confirmed;
}

MatchCenterSurfaceState _intelligenceState(
  LiveMatchLiveIntelligence? intelligence,
  bool degraded,
) {
  if (intelligence == null) {
    return MatchCenterSurfaceState.empty;
  }
  final String status = intelligence.status.trim().toLowerCase();
  final bool statusDegraded =
      status.contains('degraded') ||
      status.contains('partial') ||
      status.contains('stale') ||
      status.contains('delayed') ||
      status.contains('error');
  if (degraded || statusDegraded) {
    return MatchCenterSurfaceState.degraded;
  }
  if (!intelligence.hasSignals) {
    return MatchCenterSurfaceState.empty;
  }
  return MatchCenterSurfaceState.confirmed;
}

String _unsupportedOverlayDetail(LiveMatchOverlayMode mode) {
  switch (mode) {
    case LiveMatchOverlayMode.shape:
      return 'Lineup data is required before the shape shell can render.';
    case LiveMatchOverlayMode.pressure:
      return 'Pressure metrics are missing from the stats payload.';
    case LiveMatchOverlayMode.shots:
      return 'Shot markers are missing from the stats payload.';
    case LiveMatchOverlayMode.xg:
      return 'Expected-goals metrics or xG shot markers are missing.';
    case LiveMatchOverlayMode.territory:
      return 'Territory metrics are missing from the stats payload.';
    case LiveMatchOverlayMode.market:
      return 'Market context is missing from the stats payload.';
  }
}

List<MatchCenterMetric> _overlayMetrics(
  LiveMatchSnapshot match,
  LiveMatchOverlayMode mode,
) {
  final LiveMatchStatsSnapshot? stats = match.stats;
  if (stats == null) {
    return const <MatchCenterMetric>[];
  }
  switch (mode) {
    case LiveMatchOverlayMode.shape:
      return <MatchCenterMetric>[
        MatchCenterMetric(
          label: 'Home XI',
          value: match.homeLineup.length.toString(),
        ),
        MatchCenterMetric(
          label: 'Away XI',
          value: match.awayLineup.length.toString(),
        ),
      ];
    case LiveMatchOverlayMode.pressure:
      return _pairMetrics(match, stats.pressure, decimals: 0);
    case LiveMatchOverlayMode.shots:
      return <MatchCenterMetric>[
        MatchCenterMetric(label: 'Shot map', value: '${stats.shotMap.length}'),
        if (stats.shots != null)
          MatchCenterMetric(
            label: 'Shots',
            value: '${stats.shots!.homeLabel()} / ${stats.shots!.awayLabel()}',
          ),
      ];
    case LiveMatchOverlayMode.xg:
      return <MatchCenterMetric>[
        if (stats.expectedGoals != null)
          MatchCenterMetric(
            label: 'xG',
            value:
                '${stats.expectedGoals!.homeLabel(decimals: 2)} / '
                '${stats.expectedGoals!.awayLabel(decimals: 2)}',
          ),
        MatchCenterMetric(label: 'xG shots', value: '${stats.shotMap.length}'),
      ];
    case LiveMatchOverlayMode.territory:
      return _pairMetrics(match, stats.territory, decimals: 0);
    case LiveMatchOverlayMode.market:
      return <MatchCenterMetric>[
        if (matchCenterHasText(stats.marketSignal))
          MatchCenterMetric(label: 'Signal', value: stats.marketSignal!),
        if (matchCenterHasText(stats.marketDetail))
          MatchCenterMetric(label: 'Context', value: stats.marketDetail!),
      ];
  }
}

List<MatchCenterMetric> _pairMetrics(
  LiveMatchSnapshot match,
  LiveMatchStatPair? pair, {
  required int decimals,
}) {
  if (pair == null) {
    return const <MatchCenterMetric>[];
  }
  return <MatchCenterMetric>[
    MatchCenterMetric(
      label: match.homeTeam,
      value: pair.homeLabel(decimals: decimals),
    ),
    MatchCenterMetric(
      label: match.awayTeam,
      value: pair.awayLabel(decimals: decimals),
      positive: false,
    ),
  ];
}
