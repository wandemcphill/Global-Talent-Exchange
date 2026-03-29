import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_type.dart';
import 'package:gte_frontend/models/match_3d_scene_graph.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/services/match_3d_bridge.dart';
import 'package:gte_frontend/services/match_viewer_mapper.dart';
import 'package:gte_frontend/widgets/match_3d/gtex_3d_scene.dart';

void main() {
  test(
    'scene graph builds stage hierarchy and cinematic goal action',
    () async {
      final CompetitionSummary competition = _buildCompetition(
        id: 'match-3d-bridge-scene-goal',
      );
      final MatchViewState viewState = await _loadFallbackState(competition);
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
      expect(sceneGraph.camera.projectionPreset.name, 'goalbox');
      expect(sceneGraph.action.label, goalEvent.bannerText);
      expect(sceneGraph.experience.motionPredictions, hasLength(22));
      expect(sceneGraph.experience.commentary.line, isNotEmpty);
      expect(sceneGraph.experience.crowd.profile, isNotEmpty);
      expect(
        sceneGraph.experience.spectatorSync.roomId,
        viewState.matchId.prependMatchPrefix,
      );
    },
  );

  test('bridge sync serializes scene graph and active event payload', () async {
    final CompetitionSummary competition = _buildCompetition(
      id: 'match-3d-bridge-sync',
    );
    final MatchViewState viewState = await _loadFallbackState(competition);
    final MatchEvent activeEvent = viewState.events.first;
    final Match3dSceneGraph sceneGraph = Gtex3dScene.describeGraph(
      viewState: viewState,
      frame: viewState.firstFrame,
      activeEvent: activeEvent,
    );
    final _FakeMatch3dBridgeBackend backend = _FakeMatch3dBridgeBackend();
    final Match3DBridge bridge = Match3DBridge(backend: backend);

    await bridge.syncFrame(sceneGraph: sceneGraph, activeEvent: activeEvent);

    expect(backend.sentEvents, hasLength(1));
    final Map<String, dynamic> payload = backend.sentEvents.single;
    expect(payload['type'], 'SCENE_SYNC');
    expect(payload['matchEvent'], isA<Map<String, dynamic>>());
    expect((payload['camera'] as Map<String, dynamic>)['mode'], isNotEmpty);
    expect(payload['experience'], isA<Map<String, dynamic>>());
    expect(
      ((payload['experience'] as Map<String, dynamic>)['motionPredictions']
              as List<dynamic>)
          .length,
      22,
    );
    expect((payload['entities'] as List<dynamic>).length, greaterThan(25));

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
