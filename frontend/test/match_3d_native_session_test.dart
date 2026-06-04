import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/3d/models/match_3d_native_session.dart';
import 'package:gte_frontend/features/3d/services/match_3d_bridge.dart';

void main() {
  test(
    'bridge remains unavailable and never opens backend sessions in quarantine',
    () async {
      final _FakeSessionBridgeBackend backend = _FakeSessionBridgeBackend();
      final Match3DBridge bridge = Match3DBridge(backend: backend);
      const Match3dNativeSessionDescriptor descriptor =
          Match3dNativeSessionDescriptor(
            sessionId: 'native_match_3d:backend-authored-match',
            matchId: 'backend-authored-match',
            source: 'backend-authored-3d-quarantine',
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

      final bool nativeAvailable = await bridge.isNativeAvailable();
      final Match3dNativeRuntimeInfo runtimeInfo =
          await bridge.getRuntimeInfo();
      final Match3dAndroidLiveBootstrapResult staged = await bridge
          .stageLiveBootstrap(<String, Object?>{
            'matchId': descriptor.matchId,
            'source': descriptor.source,
          });
      final Match3dNativeSessionState opened = await bridge.openSession(
        descriptor,
      );
      final Match3dNativeSessionState? state = await bridge.getSessionState();
      await bridge.sendEvent(<String, dynamic>{
        'type': 'SCENE_SYNC',
        'matchId': descriptor.matchId,
      });
      final Match3dNativeSessionState closed = await bridge.closeSession(
        sessionId: descriptor.sessionId,
      );

      expect(nativeAvailable, isFalse);
      expect(runtimeInfo.available, isFalse);
      expect(runtimeInfo.supportsSessions, isFalse);
      expect(
        runtimeInfo.sessionLifecycle,
        Match3dNativeSessionLifecycle.unavailable,
      );
      expect(staged.staged, isFalse);
      expect(staged.message, contains('quarantined'));
      expect(opened.lifecycle, Match3dNativeSessionLifecycle.unavailable);
      expect(opened.sessionId, descriptor.sessionId);
      expect(opened.matchId, descriptor.matchId);
      expect(state, isNull);
      expect(closed.lifecycle, Match3dNativeSessionLifecycle.unavailable);
      expect(closed.sessionId, descriptor.sessionId);
      expect(backend.runtimeInfoRequests, 0);
      expect(backend.stageRequests, isEmpty);
      expect(backend.openRequests, isEmpty);
      expect(backend.closeRequests, isEmpty);
      expect(backend.sessionStateRequests, 0);
      expect(backend.handledEvents, isEmpty);
    },
  );

  test('runtime event parsing preserves backend-authored sync metadata', () {
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
          'sessionId': 'native_match_3d:backend-authored-match',
          'matchId': 'backend-authored-match',
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
    expect(event.sessionState!.playerCount, 22);
    expect(event.frameId, 'frame-9');
    expect(event.actionType, 'attack');
  });
}

class _FakeSessionBridgeBackend
    implements Match3dBridgeBackend, Match3dBridgeSessionBackend {
  final StreamController<dynamic> _controller =
      StreamController<dynamic>.broadcast();
  final List<Map<String, Object?>> stageRequests = <Map<String, Object?>>[];
  final List<Map<String, Object?>> openRequests = <Map<String, Object?>>[];
  final List<String?> closeRequests = <String?>[];
  final List<Map<String, dynamic>> handledEvents = <Map<String, dynamic>>[];
  int runtimeInfoRequests = 0;
  int sessionStateRequests = 0;

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
    handledEvents.add(event);
    _controller.add(event);
  }

  @override
  Future<Map<String, dynamic>> getRuntimeInfo() async {
    runtimeInfoRequests += 1;
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
  Future<Map<String, dynamic>> stageLiveBootstrap(
    Map<String, Object?> request,
  ) async {
    stageRequests.add(request);
    return <String, dynamic>{
      'staged': true,
      'bootstrapPath': '/android/files/tmp/gtex-live-bootstrap.json',
      'matchId': request['matchId'] as String? ?? '',
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
    closeRequests.add(sessionId);
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
  Future<Map<String, dynamic>> getSessionState() async {
    sessionStateRequests += 1;
    return _state.toMap();
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
