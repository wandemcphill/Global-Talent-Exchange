import 'dart:math' as math;

import 'package:gte_frontend/models/ball_entity.dart' as runtime_ball;
import 'package:gte_frontend/models/match_3d_scene_graph.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/models/player_entity.dart' as runtime_player;
import 'package:gte_frontend/services/match_3d_monetization_service.dart';

class Match3dSceneManager {
  static const String rootNodeId = 'scene-root';
  static const String pitchNodeId = 'pitch';
  static const String ballNodeId = 'ball';
  static const String playersNodeId = 'players';
  static const String stadiumNodeId = 'stadium';
  static const String camerasNodeId = 'cameras';
  static const String lightsNodeId = 'lights';
  static const String cameraRigId = 'camera/main';
  static const double _pitchLengthMeters = 105;
  static const double _pitchWidthMeters = 68;

  final Map<String, Match3dSceneNode> entities = <String, Match3dSceneNode>{};

  Match3dSceneGraph buildScene({
    required MatchViewState viewState,
    required MatchTimelineFrame frame,
    MatchEvent? activeEvent,
    Match3dCameraPreset requestedCameraPreset = Match3dCameraPreset.broadcast,
    Iterable<runtime_player.PlayerEntity>? runtimePlayers,
    runtime_ball.BallEntity? runtimeBall,
  }) {
    entities.clear();
    _seedStaticNodes();

    final List<runtime_player.PlayerEntity> players =
        (runtimePlayers ?? _fallbackPlayers(frame)).toList(growable: false);
    final runtime_ball.BallEntity ball =
        runtimeBall ?? runtime_ball.BallEntity.fromFrame(frame.ball);
    final Set<String> highlightedEntityIds = _highlightedEntityIds(
      frame: frame,
      activeEvent: activeEvent,
      ball: ball,
    );
    final Match3dSceneAction action = _resolveAction(
      frame: frame,
      activeEvent: activeEvent,
      ball: ball,
      highlightedEntityIds: highlightedEntityIds,
    );

    final List<String> playerChildIds = <String>[];
    for (final runtime_player.PlayerEntity player in players) {
      final Match3dSceneNode node = _playerNode(
        player: player,
        activeEvent: activeEvent,
        highlightedEntityIds: highlightedEntityIds,
      );
      updateEntity(node.id, node);
      playerChildIds.add(node.id);
    }

    updateEntity(
      playersNodeId,
      Match3dSceneNode(
        id: playersNodeId,
        type: Match3dSceneNodeType.players,
        parentId: rootNodeId,
        childIds: playerChildIds,
        position: const Match3dVector3.zero(),
        rotation: const Match3dQuaternion.identity(),
        velocity: const Match3dVector3.zero(),
        payload: const Match3dGroupPayload(label: 'Players'),
      ),
    );

    updateEntity(ballNodeId, _ballNode(ball: ball));

    final Match3dCameraRig camera = _resolveCamera(
      frame: frame,
      ball: ball,
      requestedCameraPreset: requestedCameraPreset,
      action: action,
    );
    final Match3dExperienceLayer experience = _buildExperience(
      viewState: viewState,
      frame: frame,
      activeEvent: activeEvent,
      players: players,
      ball: ball,
    );
    updateEntity(
      camerasNodeId,
      Match3dSceneNode(
        id: camerasNodeId,
        type: Match3dSceneNodeType.cameras,
        parentId: rootNodeId,
        position: camera.position,
        rotation: Match3dQuaternion.lookRotation(
          camera.target - camera.position,
        ),
        velocity: const Match3dVector3.zero(),
        payload: const Match3dGroupPayload(label: 'Cameras'),
      ),
    );

    return Match3dSceneGraph(
      matchId: viewState.matchId,
      frameId: frame.id,
      clockMinute: frame.clockMinute,
      phase: frame.phase,
      homeScore: frame.homeScore,
      awayScore: frame.awayScore,
      possessionSide: frame.possessionSide,
      sequenceId: frame.sequenceId,
      requestedCameraPreset: requestedCameraPreset,
      camera: camera,
      action: action,
      experience: experience,
      entities: Map<String, Match3dSceneNode>.unmodifiable(
        Map<String, Match3dSceneNode>.of(entities),
      ),
    );
  }

  void updateEntity(String id, Match3dSceneNode entity) {
    entities[id] = entity;
  }

  void _seedStaticNodes() {
    updateEntity(
      rootNodeId,
      Match3dSceneNode(
        id: rootNodeId,
        type: Match3dSceneNodeType.root,
        childIds: const <String>[
          pitchNodeId,
          ballNodeId,
          playersNodeId,
          stadiumNodeId,
          camerasNodeId,
          lightsNodeId,
        ],
        position: const Match3dVector3.zero(),
        rotation: const Match3dQuaternion.identity(),
        velocity: const Match3dVector3.zero(),
        payload: const Match3dGroupPayload(label: 'SceneRoot'),
      ),
    );
    updateEntity(
      pitchNodeId,
      Match3dSceneNode(
        id: pitchNodeId,
        type: Match3dSceneNodeType.pitch,
        parentId: rootNodeId,
        position: const Match3dVector3.zero(),
        rotation: const Match3dQuaternion.identity(),
        velocity: const Match3dVector3.zero(),
        payload: const Match3dPitchPayload(
          lengthMeters: _pitchLengthMeters,
          widthMeters: _pitchWidthMeters,
        ),
      ),
    );
    updateEntity(
      stadiumNodeId,
      Match3dSceneNode(
        id: stadiumNodeId,
        type: Match3dSceneNodeType.stadium,
        parentId: rootNodeId,
        position: const Match3dVector3.zero(),
        rotation: const Match3dQuaternion.identity(),
        velocity: const Match3dVector3.zero(),
        payload: const Match3dGroupPayload(label: 'Stadium'),
      ),
    );
    updateEntity(
      lightsNodeId,
      Match3dSceneNode(
        id: lightsNodeId,
        type: Match3dSceneNodeType.lights,
        parentId: rootNodeId,
        position: const Match3dVector3(x: 0, y: 28, z: -12),
        rotation: const Match3dQuaternion.identity(),
        velocity: const Match3dVector3.zero(),
        payload: const Match3dGroupPayload(label: 'Lights'),
      ),
    );
  }

  List<runtime_player.PlayerEntity> _fallbackPlayers(MatchTimelineFrame frame) {
    return frame.players
        .map((MatchViewerPlayerFrame player) {
          return runtime_player.PlayerEntity.fromFrames(
            startFrame: player,
            targetFrame: player,
            anchor: player.anchorPosition,
            runPattern: _runPatternForPlayer(frame, player),
            progress: 1,
            ballSideY: frame.ball.position.y,
            hasPossession: frame.ball.ownerPlayerId == player.playerId,
            highlighted: player.highlighted,
          );
        })
        .toList(growable: false);
  }

  runtime_player.PlayerRunPattern _runPatternForPlayer(
    MatchTimelineFrame frame,
    MatchViewerPlayerFrame player,
  ) {
    if (frame.ball.ownerPlayerId == player.playerId) {
      return runtime_player.PlayerRunPattern.attack;
    }
    if (player.side == frame.possessionSide) {
      return player.state == MatchViewerPlayerState.attacking
          ? runtime_player.PlayerRunPattern.attack
          : runtime_player.PlayerRunPattern.support;
    }
    return runtime_player.PlayerRunPattern.defend;
  }

  Match3dSceneNode _playerNode({
    required runtime_player.PlayerEntity player,
    required MatchEvent? activeEvent,
    required Set<String> highlightedEntityIds,
  }) {
    final String entityId = _playerEntityId(player.playerId)!;
    final Match3dVector3 position = _worldPosition(player.currentPosition);
    final Match3dVector3 velocity =
        _worldPosition(player.targetPosition) -
        _worldPosition(player.startPosition);
    final Match3dVector3 facingVector =
        velocity.magnitude > 0.1
            ? velocity
            : (_worldPosition(player.anchor) - position);
    return Match3dSceneNode(
      id: entityId,
      type: Match3dSceneNodeType.player,
      parentId: playersNodeId,
      position: position,
      rotation: Match3dQuaternion.lookRotation(facingVector),
      velocity: velocity,
      payload: Match3dPlayerPayload(
        teamId: player.teamId,
        side: player.side,
        label: player.label,
        role: player.role,
        line: player.line,
        active: player.active,
        highlighted:
            highlightedEntityIds.contains(entityId) || player.highlighted,
        hasPossession: player.hasPossession,
        speedRatio: player.speedRatio,
        staminaPct: player.staminaPct,
        shirtNumber: player.shirtNumber,
        animation: _resolveAnimation(
          player: player,
          activeEvent: activeEvent,
          highlighted: highlightedEntityIds.contains(entityId),
        ),
      ),
    );
  }

  Match3dSceneNode _ballNode({required runtime_ball.BallEntity ball}) {
    final Match3dVector3 position = _worldPosition(
      ball.currentPosition,
      elevation: ball.elevation,
    );
    final Match3dVector3 velocity =
        _worldPosition(ball.targetPosition) -
        _worldPosition(ball.startPosition);
    return Match3dSceneNode(
      id: ballNodeId,
      type: Match3dSceneNodeType.ball,
      parentId: rootNodeId,
      position: position,
      rotation: Match3dQuaternion.lookRotation(velocity),
      velocity: velocity,
      payload: Match3dBallPayload(
        state: ball.state,
        trajectoryType: ball.trajectoryType.name,
        ownerPlayerId: ball.ownerPlayerId,
        targetPlayerId: ball.targetPlayerId,
        elevation: ball.elevation,
        spin: _ballSpin(ball),
      ),
    );
  }

  Match3dAnimationBlend _resolveAnimation({
    required runtime_player.PlayerEntity player,
    required MatchEvent? activeEvent,
    required bool highlighted,
  }) {
    final Match3dAnimationState current = _mapAnimationState(
      player.animationState,
      speedRatio: player.speedRatio,
    );
    Match3dAnimationState target = current;
    if (player.hasPossession &&
        player.animationState == MatchPlayerAnimationState.control) {
      target = Match3dAnimationState.receive;
    }
    if (highlighted && activeEvent != null) {
      switch (activeEvent.type) {
        case MatchViewerEventType.goal:
          target = Match3dAnimationState.celebrate;
        case MatchViewerEventType.save:
          target = Match3dAnimationState.receive;
        case MatchViewerEventType.miss || MatchViewerEventType.penalty:
          target = Match3dAnimationState.shoot;
        case MatchViewerEventType.foul:
          target = Match3dAnimationState.tackle;
        case MatchViewerEventType.offside:
          target = Match3dAnimationState.recover;
        case MatchViewerEventType.attack ||
            MatchViewerEventType.setPiece ||
            MatchViewerEventType.kickoff ||
            MatchViewerEventType.redCard ||
            MatchViewerEventType.yellowCard ||
            MatchViewerEventType.substitution ||
            MatchViewerEventType.injury ||
            MatchViewerEventType.halftime ||
            MatchViewerEventType.fulltime ||
            MatchViewerEventType.neutral:
          break;
      }
    }
    return Match3dAnimationBlend(
      currentState: current,
      targetState: target,
      blendFactor: player.blendFactor.clamp(0, 1).toDouble(),
      durationMs: switch (target) {
        Match3dAnimationState.celebrate => 360,
        Match3dAnimationState.shoot => 240,
        Match3dAnimationState.pass => 200,
        Match3dAnimationState.tackle => 180,
        Match3dAnimationState.receive => 180,
        Match3dAnimationState.sprint => 160,
        Match3dAnimationState.run => 180,
        Match3dAnimationState.intercept => 180,
        Match3dAnimationState.recover => 220,
        Match3dAnimationState.idle => 160,
      },
    );
  }

  Match3dAnimationState _mapAnimationState(
    MatchPlayerAnimationState state, {
    required double speedRatio,
  }) {
    switch (state) {
      case MatchPlayerAnimationState.run:
        return Match3dAnimationState.run;
      case MatchPlayerAnimationState.sprint:
        return Match3dAnimationState.sprint;
      case MatchPlayerAnimationState.control:
        return Match3dAnimationState.receive;
      case MatchPlayerAnimationState.pass:
        return Match3dAnimationState.pass;
      case MatchPlayerAnimationState.shoot:
        return Match3dAnimationState.shoot;
      case MatchPlayerAnimationState.tackle:
        return Match3dAnimationState.tackle;
      case MatchPlayerAnimationState.intercept:
        return Match3dAnimationState.intercept;
      case MatchPlayerAnimationState.recover:
        return Match3dAnimationState.recover;
      case MatchPlayerAnimationState.jog:
        return speedRatio >= 0.65
            ? Match3dAnimationState.run
            : Match3dAnimationState.idle;
      case MatchPlayerAnimationState.idle:
        if (speedRatio >= 0.8) {
          return Match3dAnimationState.sprint;
        }
        if (speedRatio >= 0.25) {
          return Match3dAnimationState.run;
        }
        return Match3dAnimationState.idle;
    }
  }

  Match3dSceneAction _resolveAction({
    required MatchTimelineFrame frame,
    required MatchEvent? activeEvent,
    required runtime_ball.BallEntity ball,
    required Set<String> highlightedEntityIds,
  }) {
    if (activeEvent != null) {
      switch (activeEvent.type) {
        case MatchViewerEventType.goal:
          return Match3dSceneAction(
            type: Match3dSceneActionType.goal,
            cameraMode: Match3dCameraMode.cinematic,
            label: activeEvent.bannerText,
            primaryEntityId:
                _playerEntityId(activeEvent.primaryPlayerId) ??
                _playerEntityId(ball.ownerPlayerId),
            secondaryEntityId: _playerEntityId(activeEvent.secondaryPlayerId),
            highlightedEntityIds: highlightedEntityIds.toList()..sort(),
          );
        case MatchViewerEventType.save:
          return Match3dSceneAction(
            type: Match3dSceneActionType.save,
            cameraMode: Match3dCameraMode.cinematic,
            label: activeEvent.bannerText,
            primaryEntityId:
                _playerEntityId(activeEvent.primaryPlayerId) ??
                _playerEntityId(ball.ownerPlayerId),
            secondaryEntityId: _playerEntityId(activeEvent.secondaryPlayerId),
            highlightedEntityIds: highlightedEntityIds.toList()..sort(),
          );
        case MatchViewerEventType.miss || MatchViewerEventType.penalty:
          return Match3dSceneAction(
            type: Match3dSceneActionType.miss,
            cameraMode: Match3dCameraMode.cinematic,
            label: activeEvent.bannerText,
            primaryEntityId:
                _playerEntityId(activeEvent.primaryPlayerId) ??
                _playerEntityId(ball.ownerPlayerId),
            secondaryEntityId: _playerEntityId(activeEvent.secondaryPlayerId),
            highlightedEntityIds: highlightedEntityIds.toList()..sort(),
          );
        case MatchViewerEventType.foul:
          return Match3dSceneAction(
            type: Match3dSceneActionType.foul,
            cameraMode: Match3dCameraMode.tactical,
            label: activeEvent.bannerText,
            primaryEntityId:
                _playerEntityId(activeEvent.primaryPlayerId) ??
                _playerEntityId(ball.ownerPlayerId),
            secondaryEntityId: _playerEntityId(activeEvent.secondaryPlayerId),
            highlightedEntityIds: highlightedEntityIds.toList()..sort(),
          );
        case MatchViewerEventType.offside:
          return Match3dSceneAction(
            type: Match3dSceneActionType.offside,
            cameraMode: Match3dCameraMode.tactical,
            label: activeEvent.bannerText,
            primaryEntityId: _playerEntityId(activeEvent.primaryPlayerId),
            secondaryEntityId: _playerEntityId(activeEvent.secondaryPlayerId),
            highlightedEntityIds: highlightedEntityIds.toList()..sort(),
          );
        case MatchViewerEventType.kickoff:
          return Match3dSceneAction(
            type: Match3dSceneActionType.kickoff,
            cameraMode: Match3dCameraMode.followBall,
            label: activeEvent.bannerText,
            primaryEntityId:
                _playerEntityId(activeEvent.primaryPlayerId) ??
                _playerEntityId(ball.ownerPlayerId),
            highlightedEntityIds: highlightedEntityIds.toList()..sort(),
          );
        case MatchViewerEventType.setPiece:
          return Match3dSceneAction(
            type: Match3dSceneActionType.setPiece,
            cameraMode: Match3dCameraMode.tactical,
            label: activeEvent.bannerText,
            primaryEntityId:
                _playerEntityId(activeEvent.primaryPlayerId) ??
                _playerEntityId(ball.ownerPlayerId),
            highlightedEntityIds: highlightedEntityIds.toList()..sort(),
          );
        case MatchViewerEventType.attack:
          break;
        case MatchViewerEventType.redCard ||
            MatchViewerEventType.yellowCard ||
            MatchViewerEventType.substitution ||
            MatchViewerEventType.injury ||
            MatchViewerEventType.halftime ||
            MatchViewerEventType.fulltime ||
            MatchViewerEventType.neutral:
          break;
      }
    }

    switch (ball.trajectoryType) {
      case runtime_ball.BallTrajectoryType.pass:
        return Match3dSceneAction(
          type: Match3dSceneActionType.pass,
          cameraMode: Match3dCameraMode.followBall,
          label: frame.eventBanner ?? 'Pass',
          primaryEntityId: _playerEntityId(ball.ownerPlayerId),
          secondaryEntityId: _playerEntityId(ball.targetPlayerId),
          highlightedEntityIds: highlightedEntityIds.toList()..sort(),
        );
      case runtime_ball.BallTrajectoryType.shot:
        return Match3dSceneAction(
          type: Match3dSceneActionType.shot,
          cameraMode: Match3dCameraMode.cinematic,
          label: frame.eventBanner ?? 'Shot',
          primaryEntityId: _playerEntityId(ball.ownerPlayerId),
          secondaryEntityId: _playerEntityId(ball.targetPlayerId),
          highlightedEntityIds: highlightedEntityIds.toList()..sort(),
        );
      case runtime_ball.BallTrajectoryType.reset:
        return Match3dSceneAction(
          type: Match3dSceneActionType.setPiece,
          cameraMode: Match3dCameraMode.tactical,
          label: frame.eventBanner ?? 'Restart',
          primaryEntityId: _playerEntityId(ball.ownerPlayerId),
          highlightedEntityIds: highlightedEntityIds.toList()..sort(),
        );
      case runtime_ball.BallTrajectoryType.carry ||
          runtime_ball.BallTrajectoryType.loose:
        return Match3dSceneAction(
          type: Match3dSceneActionType.neutral,
          cameraMode: Match3dCameraMode.followBall,
          label: frame.eventBanner,
          primaryEntityId: _playerEntityId(ball.ownerPlayerId),
          secondaryEntityId: _playerEntityId(ball.targetPlayerId),
          highlightedEntityIds: highlightedEntityIds.toList()..sort(),
        );
    }
  }

  Set<String> _highlightedEntityIds({
    required MatchTimelineFrame frame,
    required MatchEvent? activeEvent,
    required runtime_ball.BallEntity ball,
  }) {
    final Set<String> ids = <String>{};
    final String? ownerEntityId = _playerEntityId(ball.ownerPlayerId);
    final String? targetEntityId = _playerEntityId(ball.targetPlayerId);
    if (ownerEntityId != null) {
      ids.add(ownerEntityId);
    }
    if (targetEntityId != null &&
        ball.trajectoryType == runtime_ball.BallTrajectoryType.pass) {
      ids.add(targetEntityId);
    }
    if (activeEvent != null) {
      final String? primaryEntityId = _playerEntityId(
        activeEvent.primaryPlayerId,
      );
      final String? secondaryEntityId = _playerEntityId(
        activeEvent.secondaryPlayerId,
      );
      if (primaryEntityId != null) {
        ids.add(primaryEntityId);
      }
      if (secondaryEntityId != null) {
        ids.add(secondaryEntityId);
      }
      for (final String highlightedId in activeEvent.highlightedPlayerIds) {
        final String? entityId = _playerEntityId(highlightedId);
        if (entityId != null) {
          ids.add(entityId);
        }
      }
    }
    for (final MatchTimelineInjection injection in frame.injectedEvents) {
      for (final String highlightedId in injection.highlightedPlayerIds) {
        final String? entityId = _playerEntityId(highlightedId);
        if (entityId != null) {
          ids.add(entityId);
        }
      }
    }
    return ids;
  }

  Match3dCameraRig _resolveCamera({
    required MatchTimelineFrame frame,
    required runtime_ball.BallEntity ball,
    required Match3dCameraPreset requestedCameraPreset,
    required Match3dSceneAction action,
  }) {
    final Match3dVector3 target = _worldPosition(ball.currentPosition);
    final double attackDirection = _attackDirection(frame);
    final Match3dCameraMode mode = action.cameraMode;
    if (mode == Match3dCameraMode.tactical) {
      return Match3dCameraRig(
        id: cameraRigId,
        mode: mode,
        projectionPreset: Match3dCameraPreset.broadcast,
        position: Match3dVector3(x: target.x * 0.18, y: 42, z: target.z * 0.18),
        target: Match3dVector3(x: target.x, y: 0, z: target.z),
      );
    }
    if (mode == Match3dCameraMode.cinematic) {
      return Match3dCameraRig(
        id: cameraRigId,
        mode: mode,
        projectionPreset: Match3dCameraPreset.goalbox,
        position:
            target +
            Match3dVector3(
              x: -6 * attackDirection,
              y: 8,
              z: ball.currentPosition.y >= 50 ? -8 : 8,
            ),
        target: Match3dVector3(x: target.x, y: 0, z: target.z),
      );
    }
    final Match3dVector3 offset = switch (requestedCameraPreset) {
      Match3dCameraPreset.broadcast => Match3dVector3(
        x: -14 * attackDirection,
        y: 18,
        z: ball.currentPosition.y >= 50 ? -18 : 18,
      ),
      Match3dCameraPreset.sideline => Match3dVector3(
        x: -8 * attackDirection,
        y: 12,
        z: ball.currentPosition.y >= 50 ? -28 : 28,
      ),
      Match3dCameraPreset.goalbox => Match3dVector3(
        x: -8 * attackDirection,
        y: 9,
        z: ball.currentPosition.y >= 50 ? -12 : 12,
      ),
    };
    return Match3dCameraRig(
      id: cameraRigId,
      mode: mode,
      projectionPreset: requestedCameraPreset,
      position: target + offset,
      target: Match3dVector3(x: target.x, y: 0, z: target.z),
    );
  }

  Match3dVector3 _worldPosition(
    MatchViewerPoint point, {
    double elevation = 0,
  }) {
    return Match3dVector3(
      x: ((point.x / 100) * _pitchLengthMeters) - (_pitchLengthMeters / 2),
      y: elevation,
      z: ((point.y / 100) * _pitchWidthMeters) - (_pitchWidthMeters / 2),
    );
  }

  Match3dExperienceLayer _buildExperience({
    required MatchViewState viewState,
    required MatchTimelineFrame frame,
    required MatchEvent? activeEvent,
    required List<runtime_player.PlayerEntity> players,
    required runtime_ball.BallEntity ball,
  }) {
    final List<Match3dMotionPrediction> motionPredictions = players
        .map(
          (runtime_player.PlayerEntity player) => _motionPrediction(
            player: player,
            players: players,
            ball: ball,
            activeEvent: activeEvent,
          ),
        )
        .toList(growable: false);
    return Match3dExperienceLayer(
      motionPredictions: motionPredictions,
      commentary: _commentaryCue(frame: frame, activeEvent: activeEvent),
      crowd: _crowdState(
        viewState: viewState,
        frame: frame,
        activeEvent: activeEvent,
      ),
      spectatorSync: Match3dSpectatorSync(
        roomId: 'match_${viewState.matchId}',
        syncStrategy:
            viewState.deterministicSeed != null
                ? 'deterministic_playback'
                : 'presentation_sync',
        sharedClockSecond: frame.timeSeconds.floor(),
        tick: (frame.timeSeconds * 20).round(),
        maxLatencyMs: viewState.matchMode == MatchMode.cinematic ? 240 : 320,
        checkpointIntervalSeconds: 15,
        pauseReplayEnabled: true,
        reactionsEnabled: true,
      ),
    );
  }

  Match3dMotionPrediction _motionPrediction({
    required runtime_player.PlayerEntity player,
    required List<runtime_player.PlayerEntity> players,
    required runtime_ball.BallEntity ball,
    required MatchEvent? activeEvent,
  }) {
    final MatchViewerSide opponentSide =
        player.side == MatchViewerSide.home
            ? MatchViewerSide.away
            : MatchViewerSide.home;
    final runtime_player.PlayerEntity? nearestDefender = players.nearestTo(
      player.currentPosition,
      side: opponentSide,
    );
    final double nearestDefenderDistance =
        nearestDefender == null
            ? 32
            : _distance(
              player.currentPosition,
              nearestDefender.currentPosition,
            );
    final double ballDistance = _distance(
      player.currentPosition,
      ball.currentPosition,
    );
    final double pressure =
        (1 - (nearestDefenderDistance / 30).clamp(0, 1)).toDouble();
    double shootScore =
        player.hasPossession &&
                activeEvent != null &&
                (activeEvent.type == MatchViewerEventType.goal ||
                    activeEvent.type == MatchViewerEventType.miss ||
                    activeEvent.type == MatchViewerEventType.penalty)
            ? 0.72
            : player.hasPossession
            ? 0.18
            : 0.04;
    double sprintScore =
        (player.speedRatio.clamp(0, 1) * 0.58) +
        (ballDistance < 12 ? 0.14 : 0) +
        (pressure * 0.22);
    double runScore =
        0.30 + (((1 - player.speedRatio).clamp(0, 1)) * 0.24) + 0.08;
    if (!player.active) {
      shootScore = 0;
      sprintScore = 0;
      runScore = 1;
    }
    final double total = runScore + sprintScore + shootScore;
    final Match3dVector3 direction =
        (_worldPosition(player.targetPosition) -
                _worldPosition(player.currentPosition))
            .normalized;
    return Match3dMotionPrediction(
      entityId: _playerEntityId(player.playerId)!,
      runWeight: double.parse((runScore / total).toStringAsFixed(3)),
      sprintWeight: double.parse((sprintScore / total).toStringAsFixed(3)),
      shootWeight: double.parse((shootScore / total).toStringAsFixed(3)),
      direction: Match3dVector3(x: direction.x, y: 0, z: direction.z),
      pressure: double.parse(pressure.toStringAsFixed(3)),
      ballDistance: double.parse(ballDistance.toStringAsFixed(2)),
      nearestDefenderDistance: double.parse(
        nearestDefenderDistance.toStringAsFixed(2),
      ),
      fatigueLoad: double.parse(
        (1 - (player.staminaPct / 100)).clamp(0, 1).toStringAsFixed(3),
      ),
      roleEncoding: player.role.name,
    );
  }

  Match3dCommentaryCue _commentaryCue({
    required MatchTimelineFrame frame,
    required MatchEvent? activeEvent,
  }) {
    final MatchEvent? event = activeEvent;
    final String line =
        event?.commentary.trim().isNotEmpty == true
            ? event!.commentary
            : (frame.eventBanner ?? 'Match flow continues.');
    final bool headline =
        event != null &&
        (event.type == MatchViewerEventType.goal ||
            event.type == MatchViewerEventType.save ||
            event.type == MatchViewerEventType.miss ||
            event.type == MatchViewerEventType.redCard);
    final double intensity = _clampDouble(
      ((event?.emphasisLevel ?? 1) / 3) + (headline ? 0.2 : 0),
      0.2,
      1,
    );
    return Match3dCommentaryCue(
      line: line,
      tone: event?.playbackProfile ?? 'tactical',
      commentator: headline ? 'lead' : 'analyst',
      language: 'en',
      intensity: double.parse(intensity.toStringAsFixed(3)),
      ttsReady: line.trim().isNotEmpty,
      banterLayer: event?.secondaryPlayerId != null && headline,
      audioChannel: headline ? 'headline' : 'match_bed',
    );
  }

  Match3dCrowdState _crowdState({
    required MatchViewState viewState,
    required MatchTimelineFrame frame,
    required MatchEvent? activeEvent,
  }) {
    final bool homeSpike = activeEvent?.teamId == viewState.homeTeam.teamId;
    final bool awaySpike = activeEvent?.teamId == viewState.awayTeam.teamId;
    final bool explosiveMoment =
        activeEvent != null &&
        (activeEvent.type == MatchViewerEventType.goal ||
            activeEvent.type == MatchViewerEventType.miss ||
            activeEvent.type == MatchViewerEventType.redCard);
    final int scoreDelta = frame.homeScore - frame.awayScore;
    double homeIntensity =
        0.52 +
        (frame.possessionSide == MatchViewerSide.home ? 0.05 : 0) +
        (scoreDelta > 0 ? math.min(scoreDelta * 0.05, 0.12) : 0) +
        (homeSpike && explosiveMoment ? 0.12 : 0);
    double awayIntensity =
        0.46 +
        (frame.possessionSide == MatchViewerSide.away ? 0.05 : 0) +
        (scoreDelta < 0 ? math.min(scoreDelta.abs() * 0.05, 0.12) : 0) +
        (awaySpike && explosiveMoment ? 0.12 : 0);
    if (homeSpike && explosiveMoment) {
      awayIntensity -= 0.06;
    }
    if (awaySpike && explosiveMoment) {
      homeIntensity -= 0.06;
    }
    homeIntensity = _clampDouble(homeIntensity, 0.2, 1);
    awayIntensity = _clampDouble(awayIntensity, 0.2, 1);
    final MatchViewerSide dominantSide =
        homeIntensity >= awayIntensity
            ? MatchViewerSide.home
            : MatchViewerSide.away;
    return Match3dCrowdState(
      profile:
          explosiveMoment
              ? 'explosive'
              : viewState.matchMode == MatchMode.cinematic
              ? 'charged'
              : 'standard',
      homeIntensity: double.parse(homeIntensity.toStringAsFixed(3)),
      awayIntensity: double.parse(awayIntensity.toStringAsFixed(3)),
      dominantSide: dominantSide,
      chantLevel: double.parse(
        math.max(homeIntensity, awayIntensity).toStringAsFixed(3),
      ),
      hostility: double.parse(
        _clampDouble(
          (homeIntensity - awayIntensity).abs() + (explosiveMoment ? 0.1 : 0),
          0,
          1,
        ).toStringAsFixed(3),
      ),
      spike: explosiveMoment,
    );
  }

  double _ballSpin(runtime_ball.BallEntity ball) {
    final double lateralTravel = ball.targetPosition.y - ball.startPosition.y;
    final double direction = lateralTravel == 0 ? 1 : lateralTravel.sign;
    final double base = switch (ball.trajectoryType) {
      runtime_ball.BallTrajectoryType.shot => 0.9,
      runtime_ball.BallTrajectoryType.pass => 0.45,
      runtime_ball.BallTrajectoryType.loose => 0.2,
      runtime_ball.BallTrajectoryType.carry => 0.08,
      runtime_ball.BallTrajectoryType.reset => 0,
    };
    return base * direction;
  }

  double _attackDirection(MatchTimelineFrame frame) {
    final bool attacksRight =
        frame.possessionSide == MatchViewerSide.home
            ? frame.homeAttacksRight
            : !frame.homeAttacksRight;
    return attacksRight ? 1 : -1;
  }

  String? _playerEntityId(String? playerId) {
    if (playerId == null || playerId.trim().isEmpty) {
      return null;
    }
    return 'player:$playerId';
  }

  double _distance(MatchViewerPoint left, MatchViewerPoint right) {
    final double deltaX = left.x - right.x;
    final double deltaY = left.y - right.y;
    return math.sqrt((deltaX * deltaX) + (deltaY * deltaY));
  }

  double _clampDouble(double value, double min, double max) {
    return value.clamp(min, max).toDouble();
  }
}
