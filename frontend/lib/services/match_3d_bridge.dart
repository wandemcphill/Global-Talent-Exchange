import 'package:flutter/services.dart';
import 'package:gte_frontend/models/match_3d_native_session.dart';
import 'package:gte_frontend/models/match_3d_scene_graph.dart';
import 'package:gte_frontend/models/match_event.dart';

abstract interface class Match3dBridgeBackend {
  const Match3dBridgeBackend();

  Stream<dynamic> get events;

  Future<bool> isAvailable();

  Future<void> handleEvent(Map<String, dynamic> event);
}

abstract interface class Match3dBridgeSessionBackend {
  const Match3dBridgeSessionBackend();

  Future<Map<String, dynamic>> getRuntimeInfo();

  Future<Map<String, dynamic>> stageLiveBootstrap(Map<String, Object?> request);

  Future<Map<String, dynamic>> openSession(Map<String, Object?> request);

  Future<Map<String, dynamic>> closeSession({String? sessionId});

  Future<Map<String, dynamic>> getSessionState();
}

class PlatformMatch3dBridgeBackend
    implements Match3dBridgeBackend, Match3dBridgeSessionBackend {
  const PlatformMatch3dBridgeBackend();

  static const MethodChannel _channel = MethodChannel('match_3d');
  static const EventChannel _events = EventChannel('match_3d/events');

  @override
  Stream<dynamic> get events => _events.receiveBroadcastStream();

  @override
  Future<bool> isAvailable() async {
    try {
      final Map<String, dynamic> payload = await getRuntimeInfo();
      return payload['available'] == true;
    } on MissingPluginException {
      return false;
    } on PlatformException {
      return false;
    }
  }

  @override
  Future<void> handleEvent(Map<String, dynamic> event) async {
    try {
      await _channel.invokeMethod<void>('handleEvent', event);
    } on MissingPluginException {
      // Native 3D engine integration is optional; Flutter fallback remains active.
    }
  }

  @override
  Future<Map<String, dynamic>> getRuntimeInfo() async {
    final Object? result = await _channel.invokeMethod<Object?>('runtimeInfo');
    return _normalizedMap(result);
  }

  @override
  Future<Map<String, dynamic>> stageLiveBootstrap(
    Map<String, Object?> request,
  ) async {
    final Object? result = await _channel.invokeMethod<Object?>(
      'stageLiveBootstrap',
      request,
    );
    return _normalizedMap(result);
  }

  @override
  Future<Map<String, dynamic>> openSession(Map<String, Object?> request) async {
    final Object? result = await _channel.invokeMethod<Object?>(
      'openSession',
      request,
    );
    return _normalizedMap(result);
  }

  @override
  Future<Map<String, dynamic>> closeSession({String? sessionId}) async {
    final Object? result = await _channel.invokeMethod<Object?>(
      'closeSession',
      <String, Object?>{'sessionId': sessionId},
    );
    return _normalizedMap(result);
  }

  @override
  Future<Map<String, dynamic>> getSessionState() async {
    final Object? result = await _channel.invokeMethod<Object?>(
      'getSessionState',
    );
    return _normalizedMap(result);
  }
}

class Match3DBridge {
  Match3DBridge({Match3dBridgeBackend? backend})
    : _backend = backend ?? const PlatformMatch3dBridgeBackend();

  final Match3dBridgeBackend _backend;

  Stream<dynamic> get events => _backend.events;

  Future<bool> isNativeAvailable() => _backend.isAvailable();

  Future<Match3dNativeRuntimeInfo> getRuntimeInfo() async {
    final Match3dBridgeSessionBackend? backend = _sessionBackendOrNull;
    if (backend == null) {
      return Match3dNativeRuntimeInfo(
        available: await isNativeAvailable(),
        platform: 'unknown',
        runtime: '',
        viewType: '',
        supportsSessions: false,
        platformViewAttached: false,
        sessionLifecycle: Match3dNativeSessionLifecycle.idle,
        ackCount: 0,
      );
    }
    try {
      return Match3dNativeRuntimeInfo.fromMap(await backend.getRuntimeInfo());
    } on MissingPluginException {
      return const Match3dNativeRuntimeInfo.unavailable();
    } on PlatformException {
      return const Match3dNativeRuntimeInfo.unavailable();
    }
  }

  Future<Match3dAndroidLiveBootstrapResult> stageLiveBootstrap(
    Map<String, Object?> request,
  ) async {
    final Match3dBridgeSessionBackend? backend = _sessionBackendOrNull;
    if (backend == null) {
      return const Match3dAndroidLiveBootstrapResult.unstaged(
        message:
            'Unity live bootstrap is unavailable in this runtime; Flutter 3D fallback active.',
      );
    }
    try {
      return Match3dAndroidLiveBootstrapResult.fromMap(
        await backend.stageLiveBootstrap(request),
      );
    } on MissingPluginException {
      return const Match3dAndroidLiveBootstrapResult.unstaged(
        message:
            'Unity live bootstrap is unavailable in this runtime; Flutter 3D fallback active.',
      );
    } on PlatformException {
      return const Match3dAndroidLiveBootstrapResult.unstaged(
        message:
            'Unity live bootstrap is unavailable in this runtime; Flutter 3D fallback active.',
      );
    }
  }

  Future<Match3dNativeSessionState> openSession(
    Match3dNativeSessionDescriptor descriptor,
  ) async {
    final Match3dBridgeSessionBackend? backend = _sessionBackendOrNull;
    if (backend == null) {
      return Match3dNativeSessionState.unsupported(descriptor);
    }
    try {
      return Match3dNativeSessionState.fromMap(
        await backend.openSession(descriptor.toPayload()),
      );
    } on MissingPluginException {
      return Match3dNativeSessionState.unsupported(descriptor);
    } on PlatformException {
      return Match3dNativeSessionState.unsupported(descriptor);
    }
  }

  Future<Match3dNativeSessionState> closeSession({String? sessionId}) async {
    final Match3dBridgeSessionBackend? backend = _sessionBackendOrNull;
    if (backend == null) {
      return Match3dNativeSessionState(
        sessionId: sessionId ?? '',
        matchId: '',
        lifecycle: Match3dNativeSessionLifecycle.unavailable,
        runtime: '',
        platformViewAttached: false,
        ackCount: 0,
        entityCount: 0,
        playerCount: 0,
      );
    }
    try {
      return Match3dNativeSessionState.fromMap(
        await backend.closeSession(sessionId: sessionId),
      );
    } on MissingPluginException {
      return Match3dNativeSessionState(
        sessionId: sessionId ?? '',
        matchId: '',
        lifecycle: Match3dNativeSessionLifecycle.unavailable,
        runtime: '',
        platformViewAttached: false,
        ackCount: 0,
        entityCount: 0,
        playerCount: 0,
      );
    } on PlatformException {
      return Match3dNativeSessionState(
        sessionId: sessionId ?? '',
        matchId: '',
        lifecycle: Match3dNativeSessionLifecycle.unavailable,
        runtime: '',
        platformViewAttached: false,
        ackCount: 0,
        entityCount: 0,
        playerCount: 0,
      );
    }
  }

  Future<Match3dNativeSessionState?> getSessionState() async {
    final Match3dBridgeSessionBackend? backend = _sessionBackendOrNull;
    if (backend == null) {
      return null;
    }
    try {
      return Match3dNativeSessionState.fromMap(await backend.getSessionState());
    } on MissingPluginException {
      return null;
    } on PlatformException {
      return null;
    }
  }

  Future<void> sendEvent(Map<String, dynamic> event) async {
    await _backend.handleEvent(event);
  }

  Future<void> syncFrame({
    required Match3dSceneGraph sceneGraph,
    MatchEvent? activeEvent,
    String? sessionId,
  }) async {
    final Map<String, dynamic> payload = Map<String, dynamic>.from(
      sceneGraph.toBridgePayload(),
    );
    if (sessionId != null && sessionId.isNotEmpty) {
      payload['sessionId'] = sessionId;
    }
    if (activeEvent != null) {
      payload['matchEvent'] = _eventPayload(activeEvent);
    }
    await sendEvent(payload);
  }

  Match3dBridgeSessionBackend? get _sessionBackendOrNull {
    final Match3dBridgeBackend backend = _backend;
    return backend is Match3dBridgeSessionBackend
        ? backend as Match3dBridgeSessionBackend
        : null;
  }

  Map<String, dynamic> _eventPayload(MatchEvent event) {
    return <String, dynamic>{
      'id': event.id,
      'type': event.type.name,
      'sequence': event.sequence,
      'minute': event.minute,
      'addedTime': event.addedTime,
      'clockLabel': event.clockLabel,
      'timeSeconds': event.timeSeconds,
      'teamId': event.teamId,
      'teamName': event.teamName,
      'primaryPlayerId': event.primaryPlayerId,
      'primaryPlayerName': event.primaryPlayerName,
      'secondaryPlayerId': event.secondaryPlayerId,
      'secondaryPlayerName': event.secondaryPlayerName,
      'homeScore': event.homeScore,
      'awayScore': event.awayScore,
      'bannerText': event.bannerText,
      'commentary': event.commentary,
      'emphasisLevel': event.emphasisLevel,
      'highlightedPlayerIds': event.highlightedPlayerIds,
      'flags': event.flags,
      'playbackProfile': event.playbackProfile,
      'missVariant': event.missVariant,
      'reviewable': event.reviewable,
      'reviewReason': event.reviewReason,
      'reviewDecision': event.reviewDecision,
      'scoreCommit': event.scoreCommit,
    };
  }
}

Map<String, dynamic> _normalizedMap(Object? value) {
  if (value is Map<String, dynamic>) {
    return value;
  }
  if (value is Map<Object?, Object?>) {
    final Map<String, dynamic> normalized = <String, dynamic>{};
    value.forEach((Object? key, Object? nestedValue) {
      if (key is String) {
        normalized[key] = nestedValue;
      }
    });
    return normalized;
  }
  return const <String, dynamic>{};
}
