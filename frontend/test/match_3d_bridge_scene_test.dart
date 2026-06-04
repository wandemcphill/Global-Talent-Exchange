import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_type.dart';
import 'package:gte_frontend/features/3d/models/match_3d_scene_graph.dart';
import 'package:gte_frontend/features/match_center/models/match_event.dart';
import 'package:gte_frontend/features/match_center/models/match_view_state.dart';
import 'package:gte_frontend/features/3d/services/match_3d_bridge.dart';
import 'package:gte_frontend/features/3d/widgets/match_3d/gtex_3d_scene.dart';

import 'support/gtex_match_broadcast_fixture.dart';

void main() {
  test(
    'scene graph builds stage hierarchy and cinematic goal action',
    () async {
      final CompetitionSummary competition = _buildCompetition(
        id: 'match-3d-bridge-scene-goal',
      );
      final MatchViewState viewState =
          await _loadBackendAuthoredQuarantineState(competition);
      final MatchEvent goalEvent = viewState.events.firstWhere(
        (MatchEvent event) => event.type == MatchViewerEventType.goal,
      );
      final Match3dSceneGraph sceneGraph = Gtex3dScene.describeGraph(
        viewState: viewState,
        frame: viewState.frames.firstWhere(
          (frame) => frame.timeSeconds >= goalEvent.timeSeconds,
        ),
        activeEvent: goalEvent,
      );

      expect(sceneGraph.root.childIds, const <String>[
        'pitch',
        'ball',
        'players',
        'stadium',
        'cameras',
        'lights',
      ]);
      expect(sceneGraph.playerNodes.length, 22);
      expect(sceneGraph.action.type, Match3dSceneActionType.goal);
      expect(sceneGraph.camera.mode, Match3dCameraMode.cinematic);
      expect(sceneGraph.camera.projectionPreset.name, 'goal_replay');
      expect(sceneGraph.action.label, goalEvent.bannerText);
      expect(sceneGraph.experience.motionPredictions, hasLength(22));
      expect(sceneGraph.experience.commentary.line, isNotEmpty);
      expect(sceneGraph.experience.crowd.profile, isNotEmpty);
      expect(sceneGraph.homeShape.formation, isNotEmpty);
      expect(sceneGraph.awayShape.formation, isNotEmpty);
      expect(sceneGraph.activeEventContext?.bannerText, goalEvent.bannerText);
      expect(
        sceneGraph.experience.spectatorSync.roomId,
        viewState.matchId.prependMatchPrefix,
      );
    },
  );

  test('bridge sync is a no-op while legacy runtime is quarantined', () async {
    final CompetitionSummary competition = _buildCompetition(
      id: 'match-3d-bridge-sync',
    );
    final MatchViewState viewState = await _loadBackendAuthoredQuarantineState(
      competition,
    );
    final MatchEvent activeEvent = viewState.events.first;
    final Match3dSceneGraph sceneGraph = Gtex3dScene.describeGraph(
      viewState: viewState,
      frame: viewState.firstFrame,
      activeEvent: activeEvent,
    );
    final _FakeMatch3dBridgeBackend backend = _FakeMatch3dBridgeBackend();
    final Match3DBridge bridge = Match3DBridge(backend: backend);

    await bridge.syncFrame(sceneGraph: sceneGraph, activeEvent: activeEvent);

    expect(backend.sentEvents, isEmpty);

    await backend.dispose();
  });
}

extension on String {
  String get prependMatchPrefix => 'match_$this';
}

CompetitionSummary _buildCompetition({required String id}) {
  return CompetitionSummary(
    id: id,
    name: 'GTEX 3D Bridge Test',
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
    rulesSummary: '3D bridge validation fixture',
    matchType: MatchType.gtexHosted,
    joinEligibility: const CompetitionJoinEligibility(eligible: true),
    beginnerFriendly: true,
    createdAt: DateTime.utc(2026, 1, 1),
    updatedAt: DateTime.utc(2026, 1, 2),
  );
}

Future<MatchViewState> _loadBackendAuthoredQuarantineState(
  CompetitionSummary competition,
) async {
  return buildBackendAuthored3dQuarantineViewState();
}

class _FakeMatch3dBridgeBackend implements Match3dBridgeBackend {
  _FakeMatch3dBridgeBackend();

  final StreamController<dynamic> _controller =
      StreamController<dynamic>.broadcast();
  final List<Map<String, dynamic>> sentEvents = <Map<String, dynamic>>[];

  @override
  Stream<dynamic> get events => _controller.stream;

  @override
  Future<bool> isAvailable() async => true;

  @override
  Future<void> handleEvent(Map<String, dynamic> event) async {
    sentEvents.add(event);
    _controller.add(event);
  }

  Future<void> dispose() async {
    await _controller.close();
  }
}
