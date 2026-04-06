enum Match3dNativeSessionLifecycle { idle, open, closed, implicit, unavailable }

enum Match3dNativeRuntimeEventType {
  runtimeReady,
  sessionOpened,
  sessionClosed,
  sessionImplicit,
  platformViewAttached,
  platformViewDetached,
  sceneSyncAck,
  unknown,
}

Match3dNativeRuntimeEventType match3dNativeRuntimeEventTypeFromString(
  String? value,
) {
  switch (value?.trim().toUpperCase()) {
    case 'RUNTIME_READY':
      return Match3dNativeRuntimeEventType.runtimeReady;
    case 'SESSION_OPENED':
      return Match3dNativeRuntimeEventType.sessionOpened;
    case 'SESSION_CLOSED':
      return Match3dNativeRuntimeEventType.sessionClosed;
    case 'SESSION_IMPLICIT':
      return Match3dNativeRuntimeEventType.sessionImplicit;
    case 'PLATFORM_VIEW_ATTACHED':
      return Match3dNativeRuntimeEventType.platformViewAttached;
    case 'PLATFORM_VIEW_DETACHED':
      return Match3dNativeRuntimeEventType.platformViewDetached;
    case 'SCENE_SYNC_ACK':
      return Match3dNativeRuntimeEventType.sceneSyncAck;
    default:
      return Match3dNativeRuntimeEventType.unknown;
  }
}

Match3dNativeSessionLifecycle match3dNativeSessionLifecycleFromString(
  String? value,
) {
  switch (value?.trim().toLowerCase()) {
    case 'open':
      return Match3dNativeSessionLifecycle.open;
    case 'closed':
      return Match3dNativeSessionLifecycle.closed;
    case 'implicit':
      return Match3dNativeSessionLifecycle.implicit;
    case 'unavailable':
      return Match3dNativeSessionLifecycle.unavailable;
    default:
      return Match3dNativeSessionLifecycle.idle;
  }
}

class Match3dNativeRuntimeInfo {
  const Match3dNativeRuntimeInfo({
    required this.available,
    required this.platform,
    required this.runtime,
    required this.viewType,
    required this.supportsSessions,
    required this.platformViewAttached,
    required this.sessionLifecycle,
    required this.ackCount,
    this.activeSessionId,
    this.activeMatchId,
  });

  factory Match3dNativeRuntimeInfo.fromMap(Object? value) {
    final Map<String, dynamic> payload = _stringKeyedMap(value);
    return Match3dNativeRuntimeInfo(
      available: _booleanValue(payload['available']),
      platform: _stringValue(payload['platform'], fallback: 'unknown'),
      runtime: _stringValue(payload['runtime']),
      viewType: _stringValue(payload['viewType']),
      supportsSessions: _booleanValue(payload['supportsSessions']),
      platformViewAttached: _booleanValue(payload['platformViewAttached']),
      sessionLifecycle: match3dNativeSessionLifecycleFromString(
        _nullableString(payload['sessionStatus']),
      ),
      ackCount: _intValue(payload['ackCount']),
      activeSessionId: _nullableString(payload['sessionId']),
      activeMatchId: _nullableString(payload['matchId']),
    );
  }

  const Match3dNativeRuntimeInfo.unavailable()
    : available = false,
      platform = 'unknown',
      runtime = '',
      viewType = '',
      supportsSessions = false,
      platformViewAttached = false,
      sessionLifecycle = Match3dNativeSessionLifecycle.unavailable,
      ackCount = 0,
      activeSessionId = null,
      activeMatchId = null;

  final bool available;
  final String platform;
  final String runtime;
  final String viewType;
  final bool supportsSessions;
  final bool platformViewAttached;
  final Match3dNativeSessionLifecycle sessionLifecycle;
  final int ackCount;
  final String? activeSessionId;
  final String? activeMatchId;
}

class Match3dNativeRuntimeEvent {
  const Match3dNativeRuntimeEvent({
    required this.type,
    required this.runtimeInfo,
    this.sessionState,
    this.frameId,
    this.phase,
    this.clockMinute,
    this.actionType,
    this.entityCount,
    this.playerCount,
  });

  factory Match3dNativeRuntimeEvent.fromMap(Object? value) {
    final Map<String, dynamic> payload = _stringKeyedMap(value);
    final Match3dNativeSessionState? sessionState =
        _containsSessionState(payload)
            ? Match3dNativeSessionState.fromMap(payload)
            : null;
    return Match3dNativeRuntimeEvent(
      type: match3dNativeRuntimeEventTypeFromString(
        _nullableString(payload['type']),
      ),
      runtimeInfo: Match3dNativeRuntimeInfo.fromMap(payload),
      sessionState: sessionState,
      frameId: _nullableString(payload['frameId']),
      phase: _nullableString(payload['phase']),
      clockMinute: _doubleValue(payload['clockMinute']),
      actionType: _nullableString(payload['actionType']),
      entityCount:
          payload.containsKey('entityCount')
              ? _intValue(payload['entityCount'])
              : null,
      playerCount:
          payload.containsKey('playerCount')
              ? _intValue(payload['playerCount'])
              : null,
    );
  }

  final Match3dNativeRuntimeEventType type;
  final Match3dNativeRuntimeInfo runtimeInfo;
  final Match3dNativeSessionState? sessionState;
  final String? frameId;
  final String? phase;
  final double? clockMinute;
  final String? actionType;
  final int? entityCount;
  final int? playerCount;
}

class Match3dNativeSessionDescriptor {
  const Match3dNativeSessionDescriptor({
    required this.sessionId,
    required this.matchId,
    required this.source,
    required this.homeTeamId,
    required this.homeTeamName,
    required this.awayTeamId,
    required this.awayTeamName,
    required this.initialFrameId,
    required this.initialClockMinute,
    required this.initialPhase,
    required this.initialCameraPreset,
    required this.expectedPlayerCount,
    this.pitchLengthMeters = 105,
    this.pitchWidthMeters = 68,
    this.deterministicSeed,
  });

  final String sessionId;
  final String matchId;
  final String source;
  final String homeTeamId;
  final String homeTeamName;
  final String awayTeamId;
  final String awayTeamName;
  final String initialFrameId;
  final double initialClockMinute;
  final String initialPhase;
  final String initialCameraPreset;
  final int expectedPlayerCount;
  final double pitchLengthMeters;
  final double pitchWidthMeters;
  final int? deterministicSeed;

  Map<String, Object?> toPayload() {
    return <String, Object?>{
      'sessionId': sessionId,
      'matchId': matchId,
      'source': source,
      'homeTeam': <String, Object?>{
        'teamId': homeTeamId,
        'teamName': homeTeamName,
      },
      'awayTeam': <String, Object?>{
        'teamId': awayTeamId,
        'teamName': awayTeamName,
      },
      'initialFrameId': initialFrameId,
      'initialClockMinute': initialClockMinute,
      'initialPhase': initialPhase,
      'initialCameraPreset': initialCameraPreset,
      'expectedPlayerCount': expectedPlayerCount,
      'pitchLengthMeters': pitchLengthMeters,
      'pitchWidthMeters': pitchWidthMeters,
      'deterministicSeed': deterministicSeed,
    };
  }
}

class Match3dNativeSessionState {
  const Match3dNativeSessionState({
    required this.sessionId,
    required this.matchId,
    required this.lifecycle,
    required this.runtime,
    required this.platformViewAttached,
    required this.ackCount,
    required this.entityCount,
    required this.playerCount,
    this.lastFrameId,
    this.phase,
    this.clockMinute,
    this.implicit = false,
  });

  factory Match3dNativeSessionState.fromMap(Object? value) {
    final Map<String, dynamic> payload = _stringKeyedMap(value);
    return Match3dNativeSessionState(
      sessionId: _stringValue(payload['sessionId']),
      matchId: _stringValue(payload['matchId']),
      lifecycle: match3dNativeSessionLifecycleFromString(
        _nullableString(payload['status']),
      ),
      runtime: _stringValue(payload['runtime']),
      platformViewAttached: _booleanValue(payload['platformViewAttached']),
      ackCount: _intValue(payload['ackCount']),
      entityCount: _intValue(payload['entityCount']),
      playerCount: _intValue(payload['playerCount']),
      lastFrameId: _nullableString(payload['lastFrameId']),
      phase: _nullableString(payload['phase']),
      clockMinute: _doubleValue(payload['clockMinute']),
      implicit: _booleanValue(payload['implicit']),
    );
  }

  factory Match3dNativeSessionState.unsupported(
    Match3dNativeSessionDescriptor descriptor,
  ) {
    return Match3dNativeSessionState(
      sessionId: descriptor.sessionId,
      matchId: descriptor.matchId,
      lifecycle: Match3dNativeSessionLifecycle.unavailable,
      runtime: '',
      platformViewAttached: false,
      ackCount: 0,
      entityCount: 0,
      playerCount: 0,
    );
  }

  final String sessionId;
  final String matchId;
  final Match3dNativeSessionLifecycle lifecycle;
  final String runtime;
  final bool platformViewAttached;
  final int ackCount;
  final int entityCount;
  final int playerCount;
  final String? lastFrameId;
  final String? phase;
  final double? clockMinute;
  final bool implicit;

  bool get isOpen =>
      lifecycle == Match3dNativeSessionLifecycle.open ||
      lifecycle == Match3dNativeSessionLifecycle.implicit;
}

bool _containsSessionState(Map<String, dynamic> payload) {
  return payload.containsKey('status') ||
      payload.containsKey('sessionId') ||
      payload.containsKey('implicit');
}

Map<String, dynamic> _stringKeyedMap(Object? value) {
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

bool _booleanValue(Object? value, {bool fallback = false}) {
  return switch (value) {
    bool() => value,
    num() => value != 0,
    String() => value.trim().toLowerCase() == 'true',
    _ => fallback,
  };
}

int _intValue(Object? value, {int fallback = 0}) {
  return switch (value) {
    int() => value,
    num() => value.toInt(),
    String() => int.tryParse(value) ?? fallback,
    _ => fallback,
  };
}

double? _doubleValue(Object? value) {
  return switch (value) {
    double() => value,
    num() => value.toDouble(),
    String() => double.tryParse(value),
    _ => null,
  };
}

String _stringValue(Object? value, {String fallback = ''}) {
  return switch (value) {
    null => fallback,
    _ => value.toString(),
  };
}

String? _nullableString(Object? value) {
  final String resolved = _stringValue(value);
  return resolved.isEmpty ? null : resolved;
}
