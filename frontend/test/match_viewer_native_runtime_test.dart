import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_3d_native_session.dart';
import 'package:gte_frontend/models/match_type.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/screens/match/gtex_match_viewer_screen.dart';
import 'package:gte_frontend/services/match_3d_bridge.dart';
import 'package:gte_frontend/services/match_3d_monetization_service.dart';
import 'package:gte_frontend/services/match_viewer_mapper.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets(
    'viewer keeps Android native 3D blocked and renders the 2D launch pitch',
    (WidgetTester tester) async {
      final CompetitionSummary competition = _buildCompetition(
        id: 'match-viewer-native-runtime-waiting',
      );
      final LiveMatchSnapshot snapshot = LiveMatchFixtures.buildSnapshot(
        competition,
      );
      final _ViewerNativeBridgeBackend backend = _ViewerNativeBridgeBackend(
        available: true,
        platformViewAttachedOnOpen: true,
        emitAckOnSceneSync: false,
      );

      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: GtexMatchViewerScreen(
            competition: competition,
            matchKey: competition.id,
            fallbackSnapshot: snapshot,
            preferFallback: true,
            renderMode: RenderMode.threeD,
            entitlement: const Match3dUserEntitlement.proManager(),
            engineBridge: Match3DBridge(backend: backend),
          ),
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 96));

      expect(
        find.byKey(const Key('match-pitch-2d-canvas'), skipOffstage: false),
        findsOneWidget,
      );
      expect(find.byType(AndroidView, skipOffstage: false), findsNothing);
      expect(
        find.textContaining('Native 3D session', skipOffstage: false),
        findsNothing,
      );
    },
    variant: const TargetPlatformVariant(<TargetPlatform>{
      TargetPlatform.android,
    }),
  );

  testWidgets(
    'viewer ignores unexpected native close and stays on the 2D launch pitch',
    (WidgetTester tester) async {
      final CompetitionSummary competition = _buildCompetition(
        id: 'match-viewer-native-runtime-close',
      );
      final LiveMatchSnapshot snapshot = LiveMatchFixtures.buildSnapshot(
        competition,
      );
      final _ViewerNativeBridgeBackend backend = _ViewerNativeBridgeBackend(
        available: true,
        platformViewAttachedOnOpen: true,
        emitAckOnSceneSync: true,
      );

      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: GtexMatchViewerScreen(
            competition: competition,
            matchKey: competition.id,
            fallbackSnapshot: snapshot,
            preferFallback: true,
            renderMode: RenderMode.threeD,
            entitlement: const Match3dUserEntitlement.proManager(),
            engineBridge: Match3DBridge(backend: backend),
          ),
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 96));

      backend.emitUnexpectedSessionClosed();
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 16));

      expect(
        find.byKey(const Key('match-pitch-2d-canvas'), skipOffstage: false),
        findsOneWidget,
      );
      expect(find.byType(AndroidView, skipOffstage: false), findsNothing);
      expect(
        find.textContaining('Flutter 3D fallback', skipOffstage: false),
        findsNothing,
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
    name: 'GTEX Native Runtime Viewer Test',
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
    rulesSummary: 'Native runtime viewer fixture',
    matchType: MatchType.gtexHosted,
    joinEligibility: const CompetitionJoinEligibility(eligible: true),
    beginnerFriendly: true,
    createdAt: DateTime.utc(2026, 1, 1),
    updatedAt: DateTime.utc(2026, 1, 2),
  );
}

class _ViewerNativeBridgeBackend
    implements Match3dBridgeBackend, Match3dBridgeSessionBackend {
  _ViewerNativeBridgeBackend({
    required this.available,
    required this.platformViewAttachedOnOpen,
    required this.emitAckOnSceneSync,
  });

  final bool available;
  final bool platformViewAttachedOnOpen;
  final bool emitAckOnSceneSync;
  final StreamController<dynamic> _controller =
      StreamController<dynamic>.broadcast();

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
      'platform': 'android',
      'runtime': 'native_match_3d_canvas',
      'viewType': 'match_3d/native_view',
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
    _sessionState = Match3dNativeSessionState(
      sessionId: request['sessionId'] as String? ?? '',
      matchId: request['matchId'] as String? ?? '',
      lifecycle: Match3dNativeSessionLifecycle.open,
      runtime: 'native_match_3d_canvas',
      platformViewAttached: platformViewAttachedOnOpen,
      ackCount: 0,
      entityCount: 0,
      playerCount: (request['expectedPlayerCount'] as num?)?.toInt() ?? 0,
      lastFrameId: request['initialFrameId'] as String?,
      phase: request['initialPhase'] as String?,
      clockMinute: (request['initialClockMinute'] as num?)?.toDouble(),
    );
    _controller.add(_runtimeEvent('SESSION_OPENED'));
    return _sessionState.toMap();
  }

  @override
  Future<Map<String, dynamic>> closeSession({String? sessionId}) async {
    _sessionState = Match3dNativeSessionState(
      sessionId: sessionId ?? _sessionState.sessionId,
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
    if (event['type'] != 'SCENE_SYNC' || !emitAckOnSceneSync) {
      return;
    }
    final List<dynamic> entities =
        event['entities'] as List<dynamic>? ?? const <dynamic>[];
    _sessionState = Match3dNativeSessionState(
      sessionId: event['sessionId'] as String? ?? _sessionState.sessionId,
      matchId: event['matchId'] as String? ?? _sessionState.matchId,
      lifecycle: Match3dNativeSessionLifecycle.open,
      runtime: _sessionState.runtime,
      platformViewAttached: platformViewAttachedOnOpen,
      ackCount: _sessionState.ackCount + 1,
      entityCount: entities.length,
      playerCount:
          entities
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
          'entityCount': _sessionState.entityCount,
          'playerCount': _sessionState.playerCount,
        },
      ),
    );
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
      'platform': 'android',
      'runtime': 'native_match_3d_canvas',
      'viewType': 'match_3d/native_view',
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
