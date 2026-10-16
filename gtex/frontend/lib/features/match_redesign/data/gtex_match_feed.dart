import 'package:flutter/foundation.dart';

import 'gtex_match_models.dart';

/// Connection lifecycle for the live match feed.
///
/// The match centre renders a different affordance for every state, so the
/// surface never shows a blank panel while the socket is re-establishing.
enum GtexMatchConnectionStatus {
  /// No feed has been requested yet.
  idle,

  /// First snapshot is in flight.
  connecting,

  /// Feed is attached and delivering fresh snapshots.
  live,

  /// Feed dropped mid-match and a retry is scheduled.
  reconnecting,

  /// Feed gave up after exhausting retries; the last snapshot is still shown.
  offline,

  /// The match reached full time; no further updates are expected.
  finished,
}

extension GtexMatchConnectionStatusX on GtexMatchConnectionStatus {
  String get label {
    switch (this) {
      case GtexMatchConnectionStatus.idle:
        return 'Idle';
      case GtexMatchConnectionStatus.connecting:
        return 'Connecting';
      case GtexMatchConnectionStatus.live:
        return 'Live';
      case GtexMatchConnectionStatus.reconnecting:
        return 'Reconnecting';
      case GtexMatchConnectionStatus.offline:
        return 'Offline';
      case GtexMatchConnectionStatus.finished:
        return 'Full time';
    }
  }

  /// Whether the feed is currently expected to deliver more snapshots.
  bool get isStreaming =>
      this == GtexMatchConnectionStatus.live ||
      this == GtexMatchConnectionStatus.reconnecting;

  /// Whether the surface should warn the user that data may be behind.
  bool get isDegraded =>
      this == GtexMatchConnectionStatus.reconnecting ||
      this == GtexMatchConnectionStatus.offline;
}

/// Monotonic position of a snapshot within a match.
///
/// The live feed re-fetches whole snapshots rather than applying deltas, so
/// ordering has to be derived from the payload itself. Comparing on
/// (phase, minute, events, goals) is enough to reject a snapshot that a slow
/// or duplicated socket frame dragged back in time.
@immutable
class GtexMatchRevision implements Comparable<GtexMatchRevision> {
  const GtexMatchRevision({
    required this.phaseRank,
    required this.minute,
    required this.timelineLength,
    required this.goals,
  });

  factory GtexMatchRevision.of(GtexLiveMatchState state) {
    return GtexMatchRevision(
      phaseRank: state.phase.index,
      minute: state.minute,
      timelineLength: state.timeline.length,
      goals: state.home.score + state.away.score,
    );
  }

  final int phaseRank;
  final int minute;
  final int timelineLength;
  final int goals;

  @override
  int compareTo(GtexMatchRevision other) {
    final int byPhase = phaseRank.compareTo(other.phaseRank);
    if (byPhase != 0) {
      return byPhase;
    }
    final int byMinute = minute.compareTo(other.minute);
    if (byMinute != 0) {
      return byMinute;
    }
    final int byTimeline = timelineLength.compareTo(other.timelineLength);
    if (byTimeline != 0) {
      return byTimeline;
    }
    return goals.compareTo(other.goals);
  }

  @override
  bool operator ==(Object other) {
    return other is GtexMatchRevision &&
        other.phaseRank == phaseRank &&
        other.minute == minute &&
        other.timelineLength == timelineLength &&
        other.goals == goals;
  }

  @override
  int get hashCode => Object.hash(phaseRank, minute, timelineLength, goals);

  @override
  String toString() =>
      'GtexMatchRevision(phase: $phaseRank, minute: $minute, '
      'events: $timelineLength, goals: $goals)';
}

/// Why the guard rejected (or accepted) an inbound snapshot.
enum GtexMatchFeedVerdict {
  /// Snapshot advanced the match and was applied.
  accepted,

  /// Snapshot was byte-for-byte at the same revision as the current one.
  duplicate,

  /// Snapshot described an earlier point in the match than what is shown.
  stale,

  /// Snapshot could not be understood and was discarded.
  malformed,
}

/// Rolling counters describing live-feed health.
///
/// Surfaced in debug builds and used by tests to assert that the guard is
/// actually dropping the frames it claims to drop.
@immutable
class GtexMatchFeedDiagnostics {
  const GtexMatchFeedDiagnostics({
    this.accepted = 0,
    this.duplicates = 0,
    this.stale = 0,
    this.malformed = 0,
    this.reconnects = 0,
  });

  final int accepted;
  final int duplicates;
  final int stale;
  final int malformed;
  final int reconnects;

  int get droppedTotal => duplicates + stale + malformed;

  GtexMatchFeedDiagnostics copyWith({
    int? accepted,
    int? duplicates,
    int? stale,
    int? malformed,
    int? reconnects,
  }) {
    return GtexMatchFeedDiagnostics(
      accepted: accepted ?? this.accepted,
      duplicates: duplicates ?? this.duplicates,
      stale: stale ?? this.stale,
      malformed: malformed ?? this.malformed,
      reconnects: reconnects ?? this.reconnects,
    );
  }

  @override
  bool operator ==(Object other) {
    return other is GtexMatchFeedDiagnostics &&
        other.accepted == accepted &&
        other.duplicates == duplicates &&
        other.stale == stale &&
        other.malformed == malformed &&
        other.reconnects == reconnects;
  }

  @override
  int get hashCode =>
      Object.hash(accepted, duplicates, stale, malformed, reconnects);

  @override
  String toString() =>
      'GtexMatchFeedDiagnostics(accepted: $accepted, duplicates: $duplicates, '
      'stale: $stale, malformed: $malformed, reconnects: $reconnects)';
}

/// Pure gatekeeper between the transport and the rendered match state.
///
/// Kept free of timers and futures so the duplicate/stale/malformed rules can
/// be unit tested without pumping a widget tree.
class GtexMatchFeedGuard {
  GtexMatchFeedGuard({this.matchId});

  /// When set, snapshots carrying a different match id are treated as
  /// malformed. Guards against a socket that was not torn down when the user
  /// navigated between fixtures.
  final String? matchId;

  GtexLiveMatchState? _current;
  GtexMatchRevision? _revision;
  GtexMatchFeedDiagnostics _diagnostics = const GtexMatchFeedDiagnostics();

  GtexLiveMatchState? get current => _current;
  GtexMatchRevision? get revision => _revision;
  GtexMatchFeedDiagnostics get diagnostics => _diagnostics;

  /// Whether the accepted snapshot says the match is over.
  bool get isFinished => _current?.phase == GtexMatchPhase.fullTime;

  /// Offers a snapshot to the guard, returning what happened to it.
  ///
  /// Only [GtexMatchFeedVerdict.accepted] mutates [current], which is what
  /// keeps the match centre from rebuilding on every redundant frame.
  GtexMatchFeedVerdict offer(GtexLiveMatchState? snapshot) {
    if (snapshot == null) {
      _diagnostics = _diagnostics.copyWith(
        malformed: _diagnostics.malformed + 1,
      );
      return GtexMatchFeedVerdict.malformed;
    }
    final String? expectedId = matchId;
    if (expectedId != null &&
        expectedId.isNotEmpty &&
        snapshot.matchId.isNotEmpty &&
        snapshot.matchId != expectedId) {
      _diagnostics = _diagnostics.copyWith(
        malformed: _diagnostics.malformed + 1,
      );
      return GtexMatchFeedVerdict.malformed;
    }

    final GtexMatchRevision incoming = GtexMatchRevision.of(snapshot);
    final GtexMatchRevision? known = _revision;
    if (known != null) {
      final int ordering = incoming.compareTo(known);
      if (ordering == 0) {
        _diagnostics = _diagnostics.copyWith(
          duplicates: _diagnostics.duplicates + 1,
        );
        return GtexMatchFeedVerdict.duplicate;
      }
      if (ordering < 0) {
        _diagnostics = _diagnostics.copyWith(stale: _diagnostics.stale + 1);
        return GtexMatchFeedVerdict.stale;
      }
    }

    // Preserve the locally selected player across refreshes so a snapshot
    // arriving mid-inspection does not collapse the player detail panel.
    final String? retainedSelection = _current?.selectedPlayerId;
    _current =
        retainedSelection == null || snapshot.selectedPlayerId != null
            ? snapshot
            : snapshot.copyWith(selectedPlayerId: retainedSelection);
    _revision = incoming;
    _diagnostics = _diagnostics.copyWith(accepted: _diagnostics.accepted + 1);
    return GtexMatchFeedVerdict.accepted;
  }

  /// Records a transport-level failure that did not carry a snapshot.
  void recordMalformed() {
    _diagnostics = _diagnostics.copyWith(malformed: _diagnostics.malformed + 1);
  }

  /// Records that the controller is re-establishing the feed.
  void recordReconnect() {
    _diagnostics = _diagnostics.copyWith(reconnects: _diagnostics.reconnects + 1);
  }

  /// Applies a purely local mutation (player selection) without disturbing the
  /// revision watermark.
  void mutateLocally(GtexLiveMatchState next) {
    _current = next;
  }
}

/// Exponential backoff schedule for live feed reconnects.
///
/// Bounded so a match left open on a dead network settles into a slow poll
/// rather than hammering the API.
@immutable
class GtexMatchReconnectPolicy {
  const GtexMatchReconnectPolicy({
    this.initialDelay = const Duration(seconds: 1),
    this.maxDelay = const Duration(seconds: 30),
    this.maxAttempts = 6,
  });

  final Duration initialDelay;
  final Duration maxDelay;
  final int maxAttempts;

  /// Delay before retry number [attempt] (1-based).
  Duration delayForAttempt(int attempt) {
    if (attempt <= 1) {
      return initialDelay;
    }
    final int multiplier = 1 << (attempt - 1).clamp(0, 16);
    final int millis = initialDelay.inMilliseconds * multiplier;
    if (millis >= maxDelay.inMilliseconds) {
      return maxDelay;
    }
    return Duration(milliseconds: millis);
  }

  bool shouldRetry(int attempt) => attempt <= maxAttempts;
}
