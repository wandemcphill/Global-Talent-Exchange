import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_3d_native_session.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_type.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/services/match_3d_bridge.dart';
import 'package:gte_frontend/services/match_3d_live_bootstrap_service.dart';
import 'package:gte_frontend/services/match_viewer_mapper.dart';
import 'package:gte_frontend/widgets/match_3d/gtex_3d_scene.dart';
import 'package:gte_frontend/widgets/match_3d/native_match_3d_surface.dart';

void main() {
  testWidgets(
    'native surface mounts AndroidView when the native bridge is available',
    (WidgetTester tester) async {
      final MatchViewState viewState = await _loadFallbackState(
        _buildCompetition(id: 'native-match-3d-available'),
      );
      final _FakeMatch3dBridgeBackend backend = _FakeMatch3dBridgeBackend(
        available: true,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: NativeMatch3dSurface(
              viewState: viewState,
              frame: viewState.firstFrame,
              activeEvent: viewState.events.first,
              bridge: Match3DBridge(backend: backend),
              androidLiveBootstrapProvisioner:
                  const _SuccessfulBootstrapProvisioner(),
            ),
          ),
        ),
      );
      await tester.pump();

      expect(find.byType(AndroidView), findsOneWidget);
      expect(find.byKey(NativeMatch3dSurface.runtimeBadgeKey), findsOneWidget);
      expect(find.text('Native 3D Live'), findsOneWidget);
      expect(backend.openedSessionIds, hasLength(1));
      expect(
        backend.openedSessionIds.single,
        'native_match_3d:${viewState.matchId}',
      );
      expect(backend.sentEvents, isNotEmpty);
      expect(backend.sentEvents.last['type'], 'SCENE_SYNC');
      expect(
        backend.sentEvents.last['sessionId'],
        'native_match_3d:${viewState.matchId}',
      );
    },
    variant: const TargetPlatformVariant(<TargetPlatform>{
      TargetPlatform.android,
    }),
  );

  testWidgets(
    'native surface falls back to Flutter 3D when the native bridge is unavailable',
    (WidgetTester tester) async {
      final MatchViewState viewState = await _loadFallbackState(
        _buildCompetition(id: 'native-match-3d-fallback'),
      );
      final _FakeMatch3dBridgeBackend backend = _FakeMatch3dBridgeBackend(
        available: false,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: NativeMatch3dSurface(
              viewState: viewState,
              frame: viewState.firstFrame,
              activeEvent: viewState.events.first,
              bridge: Match3DBridge(backend: backend),
              androidLiveBootstrapProvisioner:
                  const _SuccessfulBootstrapProvisioner(),
            ),
          ),
        ),
      );
      await tester.pump();

      expect(find.byType(Gtex3dScene), findsOneWidget);
      expect(find.byType(AndroidView), findsNothing);
      expect(backend.openedSessionIds, isEmpty);
    },
    variant: const TargetPlatformVariant(<TargetPlatform>{
      TargetPlatform.android,
    }),
  );

  testWidgets(
    'native surface shows the Unity activity shell when the runtime uses full-screen Unity',
    (WidgetTester tester) async {
      final MatchViewState viewState = await _loadFallbackState(
        _buildCompetition(id: 'native-match-3d-unity-activity'),
      );
      final _FakeMatch3dBridgeBackend backend = _FakeMatch3dBridgeBackend(
        available: true,
        platform: 'unity',
        runtime: 'unity_match_3d',
        viewType: 'match_3d/unity_activity',
        platformViewAttachedOnOpen: false,
        emitAckOnSceneSync: false,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: NativeMatch3dSurface(
              viewState: viewState,
              frame: viewState.firstFrame,
              activeEvent: viewState.events.first,
              bridge: Match3DBridge(backend: backend),
              androidLiveBootstrapProvisioner:
                  const _SuccessfulBootstrapProvisioner(),
            ),
          ),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 16));

      expect(find.byType(AndroidView), findsNothing);
      expect(find.byType(Gtex3dScene), findsNothing);
      expect(find.text('Opening Unity match engine'), findsOneWidget);
      expect(find.textContaining(viewState.matchId), findsOneWidget);
      expect(
        backend.openedSessionIds.single,
        'native_match_3d:${viewState.matchId}',
      );
    },
    variant: const TargetPlatformVariant(<TargetPlatform>{
      TargetPlatform.android,
    }),
  );

  testWidgets(
    'native surface mounts AndroidView when Unity reports the embedded native view type',
    (WidgetTester tester) async {
      final MatchViewState viewState = await _loadFallbackState(
        _buildCompetition(id: 'native-match-3d-unity-embedded'),
      );
      final _FakeMatch3dBridgeBackend backend = _FakeMatch3dBridgeBackend(
        available: true,
        platform: 'unity',
        runtime: 'unity_match_3d',
        viewType: 'match_3d/native_view',
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: NativeMatch3dSurface(
              viewState: viewState,
              frame: viewState.firstFrame,
              activeEvent: viewState.events.first,
              bridge: Match3DBridge(backend: backend),
              androidLiveBootstrapProvisioner:
                  const _SuccessfulBootstrapProvisioner(),
            ),
          ),
        ),
      );
      await tester.pump();

      expect(find.byType(AndroidView), findsOneWidget);
      expect(find.byType(Gtex3dScene), findsNothing);
      expect(find.text('Opening Unity match engine'), findsNothing);
      expect(
        backend.openedSessionIds.single,
        'native_match_3d:${viewState.matchId}',
      );
    },
    variant: const TargetPlatformVariant(<TargetPlatform>{
      TargetPlatform.android,
    }),
  );

  testWidgets(
    'native surface falls back to Flutter 3D when Unity bootstrap staging fails',
    (WidgetTester tester) async {
      final MatchViewState viewState = await _loadFallbackState(
        _buildCompetition(id: 'native-match-3d-bootstrap-failure'),
      );
      final _FakeMatch3dBridgeBackend backend = _FakeMatch3dBridgeBackend(
        available: true,
        platform: 'unity',
        runtime: 'unity_match_3d',
        viewType: 'match_3d/native_view',
      );
      String? reportedStatus;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: NativeMatch3dSurface(
              viewState: viewState,
              frame: viewState.firstFrame,
              activeEvent: viewState.events.first,
              bridge: Match3DBridge(backend: backend),
              androidLiveBootstrapProvisioner:
                  const _FailingBootstrapProvisioner(),
              onRuntimeStatusMessageChanged: (String? message) {
                reportedStatus = message;
              },
            ),
          ),
        ),
      );
      await tester.pump();

      expect(find.byType(Gtex3dScene), findsOneWidget);
      expect(find.byType(AndroidView), findsNothing);
      expect(
        reportedStatus,
        'Unity live bootstrap could not be staged on Android; Flutter 3D fallback active.',
      );
    },
    variant: const TargetPlatformVariant(<TargetPlatform>{
      TargetPlatform.android,
    }),
  );

  testWidgets(
    'native surface falls back and reports status when the native session closes unexpectedly',
    (WidgetTester tester) async {
      final MatchViewState viewState = await _loadFallbackState(
        _buildCompetition(id: 'native-match-3d-unexpected-close'),
      );
      final _FakeMatch3dBridgeBackend backend = _FakeMatch3dBridgeBackend(
        available: true,
      );
      String? reportedStatus;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: NativeMatch3dSurface(
              viewState: viewState,
              frame: viewState.firstFrame,
              activeEvent: viewState.events.first,
              bridge: Match3DBridge(backend: backend),
              onRuntimeStatusMessageChanged: (String? message) {
                reportedStatus = message;
              },
            ),
          ),
        ),
      );
      await tester.pump();

      backend.emitUnexpectedSessionClosed();
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 16));

      expect(find.byType(Gtex3dScene), findsOneWidget);
      expect(find.byType(AndroidView), findsNothing);
      expect(find.text('Flutter 3D Fallback'), findsOneWidget);
      expect(
        reportedStatus,
        'Native 3D session closed; Flutter 3D fallback active.',
      );
    },
    variant: const TargetPlatformVariant(<TargetPlatform>{
      TargetPlatform.android,
    }),
  );

  testWidgets(
    'native surface closes the active native session when unmounted',
    (WidgetTester tester) async {
      final MatchViewState viewState = await _loadFallbackState(
        _buildCompetition(id: 'native-match-3d-dispose'),
      );
      final _FakeMatch3dBridgeBackend backend = _FakeMatch3dBridgeBackend(
        available: true,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: NativeMatch3dSurface(
              viewState: viewState,
              frame: viewState.firstFrame,
              activeEvent: viewState.events.first,
              bridge: Match3DBridge(backend: backend),
            ),
          ),
        ),
      );
      await tester.pump();

      await tester.pumpWidget(const MaterialApp(home: SizedBox.shrink()));
      await tester.pump();

      expect(
        backend.closedSessionIds,
        contains('native_match_3d:${viewState.matchId}'),
      );
    },
    variant: const TargetPlatformVariant(<TargetPlatform>{
      TargetPlatform.android,
    }),
  );
}

CompetitionSummary _buildCompetition({required String id}) {
  return CompetitionSummary(
    id: id,
    name: 'GTEX Native 3D Surface Test',
    format: CompetitionFormat.league,
    visibility: CompetitionVisibility.public,
    status: CompetitionStatus.completed,
    creatorId: 'creator-1',
    creatorName: 'GTEX',
    participantCount: 8,
    capacity: 8,
    currency: 'USD',
    entryFee: 0,
    platformFeePct: 0,
    hostFeePct: 0,
    platformFeeAmount: 0,
    hostFeeAmount: 0,
    prizePool: 0,
    payoutStructure: const <CompetitionPayoutBreakdown>[],
    rulesSummary: 'Native 3D surface fixture',
    matchType: MatchType.gtexHosted,
    joinEligibility: const CompetitionJoinEligibility(eligible: true),
    beginnerFriendly: true,
    createdAt: DateTime.utc(2026, 1, 1),
    updatedAt: DateTime.utc(2026, 1, 2),
  );
}

Future<MatchViewState> _loadFallbackState(CompetitionSummary competition) {
  final LiveMatchSnapshot snapshot = LiveMatchFixtures.buildSnapshot(
    competition,
  );
  return MatchViewerMapper.load(
    competition: competition,
    matchKey: competition.id,
    fallbackSnapshot: snapshot,
    preferFallback: true,
  );
}

class _FakeMatch3dBridgeBackend
    implements Match3dBridgeBackend, Match3dBridgeSessionBackend {
  _FakeMatch3dBridgeBackend({
    required this.available,
    this.platform = 'android',
    this.runtime = 'native_match_3d_canvas',
    this.viewType = 'match_3d/native_view',
    this.platformViewAttachedOnOpen = true,
    this.emitAckOnSceneSync = true,
  });

  final bool available;
  final String platform;
  final String runtime;
  final String viewType;
  final bool platformViewAttachedOnOpen;
  final bool emitAckOnSceneSync;
  final StreamController<dynamic> _controller =
      StreamController<dynamic>.broadcast();
  final List<Map<String, dynamic>> sentEvents = <Map<String, dynamic>>[];
  final List<String> openedSessionIds = <String>[];
  final List<String> closedSessionIds = <String>[];
  Match3dNativeSessionState _sessionState = const Match3dNativeSessionState(
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
  Future<bool> isAvailable() async => available;

  @override
  Future<Map<String, dynamic>> getRuntimeInfo() async {
    return <String, dynamic>{
      'available': available,
      'platform': platform,
      'runtime': runtime,
      'viewType': viewType,
      'supportsSessions': true,
      'platformViewAttached': _sessionState.platformViewAttached,
      'sessionStatus': _sessionState.lifecycle.name,
      'sessionId': _sessionState.sessionId,
      'matchId': _sessionState.matchId,
      'ackCount': _sessionState.ackCount,
    };
  }

  @override
  Future<Map<String, dynamic>> stageLiveBootstrap(
    Map<String, Object?> request,
  ) async {
    return <String, dynamic>{
      'staged': true,
      'bootstrapPath': '/android/files/tmp/gtex-live-bootstrap.json',
      'matchId': request['matchId'] as String? ?? '',
    };
  }

  @override
  Future<Map<String, dynamic>> openSession(Map<String, Object?> request) async {
    final String sessionId = request['sessionId'] as String? ?? '';
    openedSessionIds.add(sessionId);
    _sessionState = Match3dNativeSessionState(
      sessionId: sessionId,
      matchId: request['matchId'] as String? ?? '',
      lifecycle: Match3dNativeSessionLifecycle.open,
      runtime: runtime,
      platformViewAttached: platformViewAttachedOnOpen,
      ackCount: 0,
      entityCount: 0,
      playerCount: (request['expectedPlayerCount'] as num?)?.toInt() ?? 0,
      lastFrameId: request['initialFrameId'] as String?,
      phase: request['initialPhase'] as String?,
      clockMinute: (request['initialClockMinute'] as num?)?.toDouble(),
    );
    if (platformViewAttachedOnOpen) {
      _controller.add(_runtimeEvent('PLATFORM_VIEW_ATTACHED'));
    }
    _controller.add(_runtimeEvent('SESSION_OPENED'));
    return _sessionState.toMap();
  }

  @override
  Future<Map<String, dynamic>> closeSession({String? sessionId}) async {
    final String resolvedSessionId = sessionId ?? _sessionState.sessionId;
    if (resolvedSessionId.isNotEmpty) {
      closedSessionIds.add(resolvedSessionId);
    }
    _sessionState = Match3dNativeSessionState(
      sessionId: resolvedSessionId,
      matchId: _sessionState.matchId,
      lifecycle: Match3dNativeSessionLifecycle.closed,
      runtime: _sessionState.runtime,
      platformViewAttached: false,
      ackCount: _sessionState.ackCount,
      entityCount: _sessionState.entityCount,
      playerCount: _sessionState.playerCount,
      lastFrameId: _sessionState.lastFrameId,
      phase: _sessionState.phase,
      clockMinute: _sessionState.clockMinute,
    );
    _controller.add(_runtimeEvent('SESSION_CLOSED'));
    return _sessionState.toMap();
  }

  @override
  Future<Map<String, dynamic>> getSessionState() async => _sessionState.toMap();

  @override
  Future<void> handleEvent(Map<String, dynamic> event) async {
    sentEvents.add(event);
    if (event['type'] == 'SCENE_SYNC' && emitAckOnSceneSync) {
      _sessionState = Match3dNativeSessionState(
        sessionId: event['sessionId'] as String? ?? _sessionState.sessionId,
        matchId: event['matchId'] as String? ?? _sessionState.matchId,
        lifecycle: Match3dNativeSessionLifecycle.open,
        runtime: _sessionState.runtime,
        platformViewAttached: true,
        ackCount: _sessionState.ackCount + 1,
        entityCount:
            (event['entities'] as List<dynamic>? ?? const <dynamic>[]).length,
        playerCount:
            (event['entities'] as List<dynamic>? ?? const <dynamic>[])
                .whereType<Map<String, dynamic>>()
                .where(
                  (Map<String, dynamic> entity) => entity['type'] == 'player',
                )
                .length,
        lastFrameId: event['frameId'] as String?,
        phase: event['phase'] as String?,
        clockMinute: (event['clockMinute'] as num?)?.toDouble(),
      );
      _controller.add(
        _runtimeEvent(
          'SCENE_SYNC_ACK',
          extra: <String, Object?>{
            'frameId': event['frameId'] as String?,
            'phase': event['phase'] as String?,
            'clockMinute': event['clockMinute'] as num?,
            'actionType':
                (event['action'] as Map<String, dynamic>?)?['type'] as String?,
            'entityCount': _sessionState.entityCount,
            'playerCount': _sessionState.playerCount,
          },
        ),
      );
      return;
    }
    _controller.add(event);
  }

  void emitUnexpectedSessionClosed() {
    _sessionState = Match3dNativeSessionState(
      sessionId: _sessionState.sessionId,
      matchId: _sessionState.matchId,
      lifecycle: Match3dNativeSessionLifecycle.closed,
      runtime: _sessionState.runtime,
      platformViewAttached: false,
      ackCount: _sessionState.ackCount,
      entityCount: _sessionState.entityCount,
      playerCount: _sessionState.playerCount,
      lastFrameId: _sessionState.lastFrameId,
      phase: _sessionState.phase,
      clockMinute: _sessionState.clockMinute,
    );
    _controller.add(_runtimeEvent('SESSION_CLOSED'));
  }

  Map<String, dynamic> _runtimeEvent(
    String type, {
    Map<String, Object?> extra = const <String, Object?>{},
  }) {
    return <String, dynamic>{
      'type': type,
      'available': available,
      'platform': platform,
      'runtime': runtime,
      'viewType': viewType,
      'supportsSessions': true,
      'platformViewAttached': _sessionState.platformViewAttached,
      'sessionStatus': _sessionState.lifecycle.name,
      'sessionId': _sessionState.sessionId,
      'matchId': _sessionState.matchId,
      'status': _sessionState.lifecycle.name,
      'ackCount': _sessionState.ackCount,
      'entityCount': _sessionState.entityCount,
      'playerCount': _sessionState.playerCount,
      'lastFrameId': _sessionState.lastFrameId,
      'phase': _sessionState.phase,
      'clockMinute': _sessionState.clockMinute,
      ...extra,
    };
  }
}

class _FailingBootstrapProvisioner
    implements Match3dAndroidLiveBootstrapProvisioner {
  const _FailingBootstrapProvisioner();

  @override
  Future<Match3dAndroidLiveBootstrapResult> provision({
    required String matchId,
  }) async {
    return const Match3dAndroidLiveBootstrapResult.unstaged(
      message:
          'Unity live bootstrap could not be staged on Android; Flutter 3D fallback active.',
    );
  }
}

class _SuccessfulBootstrapProvisioner
    implements Match3dAndroidLiveBootstrapProvisioner {
  const _SuccessfulBootstrapProvisioner();

  @override
  Future<Match3dAndroidLiveBootstrapResult> provision({
    required String matchId,
  }) async {
    return Match3dAndroidLiveBootstrapResult(
      staged: true,
      bootstrapPath: '/android/files/tmp/gtex-live-bootstrap.json',
      matchId: matchId,
    );
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
