import 'package:gte_frontend/data/gte_models.dart';

class LiveMatchSpeedMode {
  const LiveMatchSpeedMode({
    required this.key,
    required this.label,
    required this.targetDurationSeconds,
  });

  final String key;
  final String label;
  final int targetDurationSeconds;

  factory LiveMatchSpeedMode.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'live speed mode',
    );
    return LiveMatchSpeedMode(
      key: GteJson.string(json, <String>['key']),
      label: GteJson.string(json, <String>['label']),
      targetDurationSeconds: GteJson.integer(json, <String>[
        'target_duration_seconds',
        'targetDurationSeconds',
      ], fallback: 90),
    );
  }
}

class LiveMatchSpectateSession {
  const LiveMatchSpectateSession({
    required this.id,
    required this.matchId,
    required this.channel,
    required this.websocketPath,
    this.commentaryWebsocketPath,
    this.audioStemWebsocketPath,
    this.presenceChannel,
    this.presenceWebsocketPath,
    this.ttsWebsocketPath,
    this.replayRoute,
    this.speedModes = const <LiveMatchSpeedMode>[],
  });

  final String id;
  final String matchId;
  final String channel;
  final String websocketPath;
  final String? commentaryWebsocketPath;
  final String? audioStemWebsocketPath;
  final String? presenceChannel;
  final String? presenceWebsocketPath;
  final String? ttsWebsocketPath;
  final String? replayRoute;
  final List<LiveMatchSpeedMode> speedModes;

  factory LiveMatchSpectateSession.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'live spectate session',
    );
    return LiveMatchSpectateSession(
      id: GteJson.string(json, <String>['id']),
      matchId: GteJson.string(json, <String>['match_id', 'matchId']),
      channel: GteJson.string(json, <String>['channel']),
      websocketPath: GteJson.string(json, <String>[
        'websocket_path',
        'websocketPath',
      ]),
      commentaryWebsocketPath: GteJson.stringOrNull(json, <String>[
        'commentary_websocket_path',
        'commentaryWebsocketPath',
      ]),
      audioStemWebsocketPath: GteJson.stringOrNull(json, <String>[
        'audio_stem_websocket_path',
        'audioStemWebsocketPath',
      ]),
      presenceChannel: GteJson.stringOrNull(json, <String>[
        'presence_channel',
        'presenceChannel',
      ]),
      presenceWebsocketPath: GteJson.stringOrNull(json, <String>[
        'presence_websocket_path',
        'presenceWebsocketPath',
      ]),
      ttsWebsocketPath: GteJson.stringOrNull(json, <String>[
        'tts_websocket_path',
        'ttsWebsocketPath',
      ]),
      replayRoute: GteJson.stringOrNull(json, <String>[
        'replay_route',
        'replayRoute',
      ]),
      speedModes: GteJson.typedList(json, <String>[
        'speed_modes',
        'speedModes',
      ], LiveMatchSpeedMode.fromJson),
    );
  }
}
