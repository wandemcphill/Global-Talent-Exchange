import 'package:gte_frontend/features/match_center/data/live_match_fixtures.dart';

enum LiveMatchRealtimeStatus {
  idle,
  connecting,
  syncing,
  live,
  confirmed,
  reconnecting,
  degraded,
  blocked,
  closed,
  error,
}

enum LiveMatchRealtimeSource {
  seed,
  snapshotWebSocket,
  commentaryWebSocket,
  transport,
}

class LiveMatchRealtimeIssue {
  const LiveMatchRealtimeIssue({
    required this.code,
    required this.message,
    required this.source,
  });

  final String code;
  final String message;
  final LiveMatchRealtimeSource source;
}

class LiveMatchCommentaryGroup {
  const LiveMatchCommentaryGroup({required this.minute, required this.events});

  final int minute;
  final List<LiveMatchEvent> events;

  bool get hasKeyMoment =>
      events.any((LiveMatchEvent event) => event.isKeyMoment);
}

class LiveMatchRealtimeFrame {
  const LiveMatchRealtimeFrame({
    required this.snapshot,
    required this.commentaryGroups,
    required this.status,
    required this.source,
    required this.hasBackendSnapshotTruth,
    this.issue,
  });

  factory LiveMatchRealtimeFrame.fromSnapshot({
    required LiveMatchSnapshot snapshot,
    required LiveMatchRealtimeStatus status,
    required LiveMatchRealtimeSource source,
    bool hasBackendSnapshotTruth = true,
    LiveMatchRealtimeIssue? issue,
  }) {
    return LiveMatchRealtimeFrame(
      snapshot: snapshot,
      commentaryGroups: groupLiveMatchCommentary(snapshot.commentary),
      status: status,
      source: source,
      hasBackendSnapshotTruth: hasBackendSnapshotTruth,
      issue: issue,
    );
  }

  final LiveMatchSnapshot snapshot;
  final List<LiveMatchCommentaryGroup> commentaryGroups;
  final LiveMatchRealtimeStatus status;
  final LiveMatchRealtimeSource source;
  final bool hasBackendSnapshotTruth;
  final LiveMatchRealtimeIssue? issue;

  bool get isUsable =>
      hasBackendSnapshotTruth &&
      (status == LiveMatchRealtimeStatus.live ||
          status == LiveMatchRealtimeStatus.confirmed);
}

class LiveMatchRealtimeRequest {
  const LiveMatchRealtimeRequest({
    required this.seed,
    required this.snapshotWebSocketUri,
    this.commentaryWebSocketUri,
  });

  final LiveMatchSnapshot seed;
  final Uri? snapshotWebSocketUri;
  final Uri? commentaryWebSocketUri;

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is LiveMatchRealtimeRequest &&
            other.seed == seed &&
            other.snapshotWebSocketUri == snapshotWebSocketUri &&
            other.commentaryWebSocketUri == commentaryWebSocketUri;
  }

  @override
  int get hashCode =>
      Object.hash(seed, snapshotWebSocketUri, commentaryWebSocketUri);
}

List<LiveMatchCommentaryGroup> groupLiveMatchCommentary(
  Iterable<LiveMatchEvent> events,
) {
  final List<LiveMatchEvent> sorted = events.toList(growable: false);
  sorted.sort((LiveMatchEvent left, LiveMatchEvent right) {
    final int minuteCompare = left.minute.compareTo(right.minute);
    if (minuteCompare != 0) {
      return minuteCompare;
    }
    final int titleCompare = left.title.compareTo(right.title);
    if (titleCompare != 0) {
      return titleCompare;
    }
    return left.detail.compareTo(right.detail);
  });

  final List<LiveMatchCommentaryGroup> groups = <LiveMatchCommentaryGroup>[];
  var bucket = <LiveMatchEvent>[];
  int? activeMinute;
  for (final LiveMatchEvent event in sorted) {
    if (activeMinute != event.minute) {
      if (activeMinute != null) {
        groups.add(
          LiveMatchCommentaryGroup(
            minute: activeMinute,
            events: List<LiveMatchEvent>.unmodifiable(bucket),
          ),
        );
      }
      activeMinute = event.minute;
      bucket = <LiveMatchEvent>[];
    }
    bucket.add(event);
  }
  if (activeMinute != null) {
    groups.add(
      LiveMatchCommentaryGroup(
        minute: activeMinute,
        events: List<LiveMatchEvent>.unmodifiable(bucket),
      ),
    );
  }
  return List<LiveMatchCommentaryGroup>.unmodifiable(groups);
}
