import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/models/match_3d_native_session.dart';
import 'package:gte_frontend/services/match_3d_bridge.dart';

void main() {
  test(
    'bridge exposes runtime info and session state when backend supports it',
    () async {
      final _FakeSessionBridgeBackend backend = _FakeSessionBridgeBackend();
      final Match3DBridge bridge = Match3DBridge(backend: backend);
      const Match3dNativeSessionDescriptor descriptor =
          Match3dNativeSessionDescriptor(
            sessionId: 'native_match_3d:test-match',
            matchId: 'test-match',
            source: 'fixture',
            homeTeamId: 'home',
            homeTeamName: 'Lagos Stars',
            awayTeamId: 'away',
            awayTeamName: 'Abuja City',
            initialFrameId: 'frame-1',
            initialClockMinute: 12,
            initialPhase: 'openPlay',
            initialCameraPreset: 'tactical_high',
            expectedPlayerCount: 22,
          );

      final Match3dNativeRuntimeInfo runtimeInfo =
          await bridge.getRuntimeInfo();
      final Match3dNativeSessionState opened = await bridge.openSession(
        descriptor,
      );
      final Match3dNativeSessionState state = (await bridge.getSessionState())!;
      final Match3dNativeSessionState closed = await bridge.closeSession(
        sessionId: descriptor.sessionId,
      );

      expect(runtimeInfo.available, isTrue);
      expect(runtimeInfo.supportsSessions, isTrue);
      expect(runtimeInfo.runtime, 'native_match_3d_canvas');
      expect(opened.isOpen, isTrue);
      expect(opened.sessionId, descriptor.sessionId);
      expect(state.matchId, descriptor.matchId);
      expect(state.lifecycle, Match3dNativeSessionLifecycle.open);
      expect(closed.lifecycle, Match3dNativeSessionLifecycle.closed);
      expect(backend.openRequests.single['matchId'], descriptor.matchId);
      expect(
        (backend.openRequests.single['homeTeam']
            as Map<String, Object?>)['teamName'],
        'Lagos Stars',
      );
    },
  );

  test(
    'bridge falls back cleanly when backend does not support sessions',
    () async {
      final _LegacyMatch3dBridgeBackend backend = _LegacyMatch3dBridgeBackend();
      final Match3DBridge bridge = Match3DBridge(backend: backend);
      const Match3dNativeSessionDescriptor descriptor =
          Match3dNativeSessionDescriptor(
            sessionId: 'native_match_3d:legacy-match',
            matchId: 'legacy-match',
            source: 'fixture',
            homeTeamId: 'home',
            homeTeamName: 'Lagos Stars',
            awayTeamId: 'away',
            awayTeamName: 'Abuja City',
            initialFrameId: 'frame-2',
            initialClockMinute: 9,
            initialPhase: 'openPlay',
            initialCameraPreset: 'tactical_high',
            expectedPlayerCount: 22,
          );

      final Match3dNativeRuntimeInfo runtimeInfo =
          await bridge.getRuntimeInfo();
      final Match3dNativeSessionState session = await bridge.openSession(
        descriptor,
      );

      expect(runtimeInfo.available, isTrue);
      expect(runtimeInfo.supportsSessions, isFalse);
      expect(session.lifecycle, Match3dNativeSessionLifecycle.unavailable);
      expect(session.sessionId, descriptor.sessionId);
    },
  );

  test('runtime event parsing preserves session and sync metadata', () {
    final Match3dNativeRuntimeEvent event =
        Match3dNativeRuntimeEvent.fromMap(<String, Object?>{
          'type': 'SCENE_SYNC_ACK',
          'available': true,
          'platform': 'android',
          'runtime': 'native_match_3d_canvas',
          'viewType': 'match_3d/native_view',
          'supportsSessions': true,
          'platformViewAttached': true,
          'sessionStatus': 'open',
          'sessionId': 'native_match_3d:test-match',
          'matchId': 'test-match',
          'status': 'open',
          'ackCount': 3,
          'entityCount': 25,
          'playerCount': 22,
          'frameId': 'frame-9',
          'phase': 'openPlay',
          'clockMinute': 18.5,
          'actionType': 'attack',
        });

    expect(event.type, Match3dNativeRuntimeEventType.sceneSyncAck);
    expect(event.runtimeInfo.available, isTrue);
    expect(
      event.runtimeInfo.sessionLifecycle,
      Match3dNativeSessionLifecycle.open,
    );
    expect(event.sessionState, isNotNull);
    expect(event.sessionState!.ackCount, 3);
    expect(event.frameId, 'frame-9');
    expect(event.actionType, 'attack');
  });
}

class _FakeSessionBridgeBackend
    implements Match3dBridgeBackend, Match3dBridgeSessionBackend {
  final StreamController<dynamic> _controller =
      StreamController<dynamic>.broadcast();
  final List<Map<String, Object?>> openRequests = <Map<String, Object?>>[];
  Match3dNativeSessionState _state = const Match3dNativeSessionState(
    sessionId: '',
    matchId: '',
    lifecycle: Match3dNativeSessionLifecycle.idle,
    runtime: 'native_match_3d_canvas',
    platformViewAttached: false,
    ackCount: 0,
    entityCount: 0,
    playerCount: 0,
  );

  @override
  Stream<dynamic> get events => _controller.stream;

  @override
  Future<bool> isAvailable() async => true;

  @override
  Future<void> handleEvent(Map<String, dynamic> event) async {
    _controller.add(event);
  }

  @override
  Future<Map<String, dynamic>> getRuntimeInfo() async {
    return <String, dynamic>{
      'available': true,
      'platform': 'android',
      'runtime': 'native_match_3d_canvas',
      'viewType': 'match_3d/native_view',
      'supportsSessions': true,
      'platformViewAttached': false,
      'sessionStatus': _state.lifecycle.name,
      'sessionId': _state.sessionId,
      'matchId': _state.matchId,
      'ackCount': _state.ackCount,
    };
  }

  @override
  Future<Map<String, dynamic>> openSession(Map<String, Object?> request) async {
    openRequests.add(request);
    _state = Match3dNativeSessionState(
      sessionId: request['sessionId'] as String,
      matchId: request['matchId'] as String,
      lifecycle: Match3dNativeSessionLifecycle.open,
      runtime: 'native_match_3d_canvas',
      platformViewAttached: true,
      ackCount: 0,
      entityCount: 0,
      playerCount: (request['expectedPlayerCount'] as num?)?.toInt() ?? 0,
      lastFrameId: request['initialFrameId'] as String?,
      phase: request['initialPhase'] as String?,
      clockMinute: (request['initialClockMinute'] as num?)?.toDouble(),
    );
    return _state.toMap();
  }

  @override
  Future<Map<String, dynamic>> closeSession({String? sessionId}) async {
    _state = Match3dNativeSessionState(
      sessionId: sessionId ?? '',
      matchId: _state.matchId,
      lifecycle: Match3dNativeSessionLifecycle.closed,
      runtime: _state.runtime,
      platformViewAttached: false,
      ackCount: _state.ackCount,
      entityCount: _state.entityCount,
      playerCount: _state.playerCount,
      lastFrameId: _state.lastFrameId,
      phase: _state.phase,
      clockMinute: _state.clockMinute,
    );
    return _state.toMap();
  }

  @override
  Future<Map<String, dynamic>> getSessionState() async => _state.toMap();
}

class _LegacyMatch3dBridgeBackend implements Match3dBridgeBackend {
  final StreamController<dynamic> _controller =
      StreamController<dynamic>.broadcast();

  @override
  Stream<dynamic> get events => _controller.stream;

  @override
  Future<bool> isAvailable() async => true;

  @override
  Future<void> handleEvent(Map<String, dynamic> event) async {
    _controller.add(event);
  }
}

extension on Match3dNativeSessionState {
  Map<String, dynamic> toMap() {
    return <String, dynamic>{
      'sessionId': sessionId,
      'matchId': matchId,
      'status': lifecycle.name,
      'runtime': runtime,
      'platformViewAttached': platformViewAttached,
      'ackCount': ackCount,
      'entityCount': entityCount,
      'playerCount': playerCount,
      'lastFrameId': lastFrameId,
      'phase': phase,
      'clockMinute': clockMinute,
      'implicit': implicit,
    };
  }
}
