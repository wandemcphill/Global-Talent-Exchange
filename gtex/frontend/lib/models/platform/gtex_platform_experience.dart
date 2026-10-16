import 'package:flutter/foundation.dart';

enum GtexPlatformMode { mobile, web, tv }

extension GtexPlatformModeX on GtexPlatformMode {
  String get label {
    switch (this) {
      case GtexPlatformMode.mobile:
        return 'Mobile';
      case GtexPlatformMode.web:
        return 'Web';
      case GtexPlatformMode.tv:
        return 'TV';
    }
  }
}

@immutable
class GtexTvChannel {
  const GtexTvChannel({
    required this.channelId,
    required this.name,
    required this.headline,
    required this.subheadline,
    this.matchId,
    this.viewerCount = 0,
    this.isLive = true,
    this.autoSwitchEnabled = true,
    this.highlightLabel,
  });

  final String channelId;
  final String name;
  final String headline;
  final String subheadline;
  final String? matchId;
  final int viewerCount;
  final bool isLive;
  final bool autoSwitchEnabled;
  final String? highlightLabel;
}

@immutable
class GtexPlatformHistoryEntry {
  const GtexPlatformHistoryEntry({
    required this.deviceId,
    required this.deviceLabel,
    required this.matchId,
    required this.title,
    required this.watchedAt,
    this.channelId,
    this.resumePositionSeconds = 0,
    this.commentaryCursor = 0,
  });

  final String deviceId;
  final String deviceLabel;
  final String matchId;
  final String title;
  final DateTime watchedAt;
  final String? channelId;
  final double resumePositionSeconds;
  final int commentaryCursor;
}

@immutable
class GtexPlatformSyncState {
  const GtexPlatformSyncState({
    this.sourceDeviceId,
    this.sourceDeviceLabel,
    this.resumeMatchId,
    this.resumePositionSeconds = 0,
    this.commentaryCursor = 0,
    this.watchHistory = const <GtexPlatformHistoryEntry>[],
  });

  final String? sourceDeviceId;
  final String? sourceDeviceLabel;
  final String? resumeMatchId;
  final double resumePositionSeconds;
  final int commentaryCursor;
  final List<GtexPlatformHistoryEntry> watchHistory;

  GtexPlatformSyncState copyWith({
    String? sourceDeviceId,
    String? sourceDeviceLabel,
    String? resumeMatchId,
    double? resumePositionSeconds,
    int? commentaryCursor,
    List<GtexPlatformHistoryEntry>? watchHistory,
  }) {
    return GtexPlatformSyncState(
      sourceDeviceId: sourceDeviceId ?? this.sourceDeviceId,
      sourceDeviceLabel: sourceDeviceLabel ?? this.sourceDeviceLabel,
      resumeMatchId: resumeMatchId ?? this.resumeMatchId,
      resumePositionSeconds:
          resumePositionSeconds ?? this.resumePositionSeconds,
      commentaryCursor: commentaryCursor ?? this.commentaryCursor,
      watchHistory: watchHistory ?? this.watchHistory,
    );
  }
}
