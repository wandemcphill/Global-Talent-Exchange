import 'package:flutter/foundation.dart';
import 'package:gte_frontend/models/platform/gtex_platform_experience.dart';

class GtexPlatformExperienceController extends ChangeNotifier {
  GtexPlatformExperienceController({
    GtexPlatformMode mode = GtexPlatformMode.mobile,
    List<GtexTvChannel> channels = const <GtexTvChannel>[],
    GtexPlatformSyncState syncState = const GtexPlatformSyncState(),
  }) : _mode = mode,
       _channels = List<GtexTvChannel>.unmodifiable(channels),
       _syncState = syncState,
       _selectedChannelId = _initialChannelId(channels);

  GtexPlatformMode _mode;
  List<GtexTvChannel> _channels;
  GtexPlatformSyncState _syncState;
  String? _selectedChannelId;
  String? _autoSwitchMessage;

  GtexPlatformMode get mode => _mode;

  List<GtexTvChannel> get channels => _channels;

  GtexPlatformSyncState get syncState => _syncState;

  String? get autoSwitchMessage => _autoSwitchMessage;

  GtexTvChannel? get currentChannel {
    if (_channels.isEmpty) {
      return null;
    }
    for (final GtexTvChannel channel in _channels) {
      if (channel.channelId == _selectedChannelId) {
        return channel;
      }
    }
    return _channels.first;
  }

  void switchMode(GtexPlatformMode nextMode) {
    if (_mode == nextMode) {
      return;
    }
    _mode = nextMode;
    notifyListeners();
  }

  void updateChannels(List<GtexTvChannel> nextChannels) {
    _channels = List<GtexTvChannel>.unmodifiable(nextChannels);
    if (_channels.every(
      (GtexTvChannel item) => item.channelId != _selectedChannelId,
    )) {
      _selectedChannelId = _initialChannelId(nextChannels);
    }
    notifyListeners();
  }

  void selectChannel(String channelId) {
    if (_selectedChannelId == channelId) {
      return;
    }
    _selectedChannelId = channelId;
    _autoSwitchMessage = null;
    notifyListeners();
  }

  void syncFromExternal({
    required String sourceDeviceId,
    required String sourceDeviceLabel,
    required String matchId,
    required String title,
    String? channelId,
    double resumePositionSeconds = 0,
    int commentaryCursor = 0,
  }) {
    final GtexPlatformHistoryEntry entry = GtexPlatformHistoryEntry(
      deviceId: sourceDeviceId,
      deviceLabel: sourceDeviceLabel,
      matchId: matchId,
      channelId: channelId,
      title: title,
      watchedAt: DateTime.now(),
      resumePositionSeconds: resumePositionSeconds,
      commentaryCursor: commentaryCursor,
    );
    _syncState = _syncState.copyWith(
      sourceDeviceId: sourceDeviceId,
      sourceDeviceLabel: sourceDeviceLabel,
      resumeMatchId: matchId,
      resumePositionSeconds: resumePositionSeconds,
      commentaryCursor: commentaryCursor,
      watchHistory: <GtexPlatformHistoryEntry>[
        entry,
        ..._syncState.watchHistory,
      ].take(8).toList(growable: false),
    );
    notifyListeners();
  }

  GtexTvChannel? handleMatchFinished() {
    if (_mode != GtexPlatformMode.tv || _channels.length < 2) {
      return null;
    }
    final GtexTvChannel? current = currentChannel;
    final int currentIndex =
        current == null
            ? -1
            : _channels.indexWhere(
              (GtexTvChannel item) => item.channelId == current.channelId,
            );
    final Iterable<GtexTvChannel> ordered = <GtexTvChannel>[
      ..._channels.skip(currentIndex + 1),
      ..._channels.take(currentIndex + 1),
    ];
    for (final GtexTvChannel candidate in ordered) {
      if (candidate.channelId == current?.channelId) {
        continue;
      }
      if (!candidate.autoSwitchEnabled) {
        continue;
      }
      _selectedChannelId = candidate.channelId;
      _autoSwitchMessage = 'Auto-switched to ${candidate.name}';
      notifyListeners();
      return candidate;
    }
    return null;
  }

  void clearAutoSwitchMessage() {
    if (_autoSwitchMessage == null) {
      return;
    }
    _autoSwitchMessage = null;
    notifyListeners();
  }

  static String? _initialChannelId(List<GtexTvChannel> channels) {
    for (final GtexTvChannel channel in channels) {
      if (channel.isLive) {
        return channel.channelId;
      }
    }
    return channels.isEmpty ? null : channels.first.channelId;
  }
}
