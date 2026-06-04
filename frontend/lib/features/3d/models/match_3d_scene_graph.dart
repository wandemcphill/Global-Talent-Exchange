import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';
import 'package:gte_frontend/features/match_center/models/real_match_engine_presentation.dart';

enum Match3dSceneNodeType {
  root,
  pitch,
  ball,
  players,
  player,
  stadium,
  cameras,
  lights,
}

enum Match3dAnimationState {
  idle,
  run,
  sprint,
  receive,
  pass,
  shoot,
  tackle,
  celebrate,
  intercept,
  recover,
}

enum Match3dCameraMode { followBall, tactical, cinematic }

enum Match3dSceneActionType {
  neutral,
  pass,
  shot,
  goal,
  save,
  miss,
  foul,
  booking,
  offside,
  kickoff,
  setPiece,
  substitution,
}

@immutable
class Match3dVector3 {
  const Match3dVector3({required this.x, required this.y, required this.z});

  const Match3dVector3.zero() : x = 0, y = 0, z = 0;

  final double x;
  final double y;
  final double z;

  double get magnitude => math.sqrt((x * x) + (y * y) + (z * z));

  Match3dVector3 get normalized {
    final double length = magnitude;
    if (length <= 0.000001) {
      return const Match3dVector3.zero();
    }
    return Match3dVector3(x: x / length, y: y / length, z: z / length);
  }

  Match3dVector3 operator +(Match3dVector3 other) {
    return Match3dVector3(x: x + other.x, y: y + other.y, z: z + other.z);
  }

  Match3dVector3 operator -(Match3dVector3 other) {
    return Match3dVector3(x: x - other.x, y: y - other.y, z: z - other.z);
  }

  Match3dVector3 scale(double factor) {
    return Match3dVector3(x: x * factor, y: y * factor, z: z * factor);
  }

  Map<String, double> toJson() {
    return <String, double>{'x': x, 'y': y, 'z': z};
  }
}

@immutable
class Match3dQuaternion {
  const Match3dQuaternion({
    required this.x,
    required this.y,
    required this.z,
    required this.w,
  });

  const Match3dQuaternion.identity() : x = 0, y = 0, z = 0, w = 1;

  final double x;
  final double y;
  final double z;
  final double w;

  factory Match3dQuaternion.lookRotation(Match3dVector3 direction) {
    final Match3dVector3 normalized = direction.normalized;
    if (normalized.magnitude <= 0.000001) {
      return const Match3dQuaternion.identity();
    }
    final double yaw = math.atan2(normalized.x, normalized.z);
    final double halfYaw = yaw / 2;
    return Match3dQuaternion(
      x: 0,
      y: math.sin(halfYaw),
      z: 0,
      w: math.cos(halfYaw),
    );
  }

  Map<String, double> toJson() {
    return <String, double>{'x': x, 'y': y, 'z': z, 'w': w};
  }
}

@immutable
class Match3dAnimationBlend {
  const Match3dAnimationBlend({
    required this.currentState,
    required this.targetState,
    required this.blendFactor,
    required this.durationMs,
  });

  final Match3dAnimationState currentState;
  final Match3dAnimationState targetState;
  final double blendFactor;
  final int durationMs;

  Map<String, Object> toJson() {
    return <String, Object>{
      'currentState': currentState.name,
      'targetState': targetState.name,
      'blendFactor': blendFactor,
      'durationMs': durationMs,
    };
  }
}

sealed class Match3dNodePayload {
  const Match3dNodePayload();

  Map<String, Object?> toJson();
}

class Match3dGroupPayload extends Match3dNodePayload {
  const Match3dGroupPayload({required this.label});

  final String label;

  @override
  Map<String, Object?> toJson() {
    return <String, Object?>{'kind': 'group', 'label': label};
  }
}

class Match3dPitchPayload extends Match3dNodePayload {
  const Match3dPitchPayload({this.lengthMeters = 105, this.widthMeters = 68});

  final double lengthMeters;
  final double widthMeters;

  @override
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'kind': 'pitch',
      'lengthMeters': lengthMeters,
      'widthMeters': widthMeters,
    };
  }
}

class Match3dPlayerPayload extends Match3dNodePayload {
  const Match3dPlayerPayload({
    required this.teamId,
    required this.side,
    required this.label,
    required this.role,
    required this.line,
    required this.active,
    required this.highlighted,
    required this.hasPossession,
    required this.speedRatio,
    required this.staminaPct,
    required this.animation,
    this.shirtNumber,
  });

  final String teamId;
  final MatchViewerSide side;
  final String label;
  final MatchViewerRole role;
  final MatchPlayerLine line;
  final bool active;
  final bool highlighted;
  final bool hasPossession;
  final double speedRatio;
  final int staminaPct;
  final Match3dAnimationBlend animation;
  final int? shirtNumber;

  @override
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'kind': 'player',
      'teamId': teamId,
      'side': side.name,
      'label': label,
      'role': role.name,
      'line': line.name,
      'active': active,
      'highlighted': highlighted,
      'hasPossession': hasPossession,
      'speedRatio': speedRatio,
      'staminaPct': staminaPct,
      'shirtNumber': shirtNumber,
      'animation': animation.toJson(),
    };
  }
}

class Match3dBallPayload extends Match3dNodePayload {
  const Match3dBallPayload({
    required this.state,
    required this.trajectoryType,
    required this.elevation,
    required this.spin,
    this.ownerPlayerId,
    this.targetPlayerId,
  });

  final String state;
  final String trajectoryType;
  final double elevation;
  final double spin;
  final String? ownerPlayerId;
  final String? targetPlayerId;

  @override
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'kind': 'ball',
      'state': state,
      'trajectoryType': trajectoryType,
      'elevation': elevation,
      'spin': spin,
      'ownerPlayerId': ownerPlayerId,
      'targetPlayerId': targetPlayerId,
    };
  }
}

@immutable
class Match3dSceneNode {
  const Match3dSceneNode({
    required this.id,
    required this.type,
    required this.position,
    required this.rotation,
    required this.velocity,
    required this.payload,
    this.parentId,
    this.childIds = const <String>[],
  });

  final String id;
  final Match3dSceneNodeType type;
  final String? parentId;
  final List<String> childIds;
  final Match3dVector3 position;
  final Match3dQuaternion rotation;
  final Match3dVector3 velocity;
  final Match3dNodePayload payload;

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'id': id,
      'type': type.name,
      'parentId': parentId,
      'childIds': childIds,
      'position': position.toJson(),
      'rotation': rotation.toJson(),
      'velocity': velocity.toJson(),
      'payload': payload.toJson(),
    };
  }
}

@immutable
class Match3dCameraRig {
  const Match3dCameraRig({
    required this.id,
    required this.mode,
    required this.projectionPreset,
    required this.position,
    required this.target,
  });

  final String id;
  final Match3dCameraMode mode;
  final MatchEngineCameraPreset projectionPreset;
  final Match3dVector3 position;
  final Match3dVector3 target;

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'id': id,
      'mode': mode.name,
      'projectionPreset': projectionPreset.name,
      'position': position.toJson(),
      'target': target.toJson(),
    };
  }
}

@immutable
class Match3dSceneAction {
  const Match3dSceneAction({
    required this.type,
    required this.cameraMode,
    required this.highlightedEntityIds,
    this.label,
    this.primaryEntityId,
    this.secondaryEntityId,
  });

  const Match3dSceneAction.neutral()
    : type = Match3dSceneActionType.neutral,
      cameraMode = Match3dCameraMode.followBall,
      highlightedEntityIds = const <String>[],
      label = null,
      primaryEntityId = null,
      secondaryEntityId = null;

  final Match3dSceneActionType type;
  final Match3dCameraMode cameraMode;
  final List<String> highlightedEntityIds;
  final String? label;
  final String? primaryEntityId;
  final String? secondaryEntityId;

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'type': type.name,
      'cameraMode': cameraMode.name,
      'highlightedEntityIds': highlightedEntityIds,
      'label': label,
      'primaryEntityId': primaryEntityId,
      'secondaryEntityId': secondaryEntityId,
    };
  }
}

@immutable
class Match3dMotionPrediction {
  const Match3dMotionPrediction({
    required this.entityId,
    required this.runWeight,
    required this.sprintWeight,
    required this.shootWeight,
    required this.direction,
    required this.pressure,
    required this.ballDistance,
    required this.nearestDefenderDistance,
    required this.fatigueLoad,
    required this.roleEncoding,
  });

  final String entityId;
  final double runWeight;
  final double sprintWeight;
  final double shootWeight;
  final Match3dVector3 direction;
  final double pressure;
  final double ballDistance;
  final double nearestDefenderDistance;
  final double fatigueLoad;
  final String roleEncoding;

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'entityId': entityId,
      'runWeight': runWeight,
      'sprintWeight': sprintWeight,
      'shootWeight': shootWeight,
      'direction': direction.toJson(),
      'pressure': pressure,
      'ballDistance': ballDistance,
      'nearestDefenderDistance': nearestDefenderDistance,
      'fatigueLoad': fatigueLoad,
      'roleEncoding': roleEncoding,
    };
  }
}

@immutable
class Match3dCommentaryCue {
  const Match3dCommentaryCue({
    required this.line,
    required this.tone,
    required this.commentator,
    required this.language,
    required this.intensity,
    required this.ttsReady,
    required this.banterLayer,
    required this.audioChannel,
  });

  final String line;
  final String tone;
  final String commentator;
  final String language;
  final double intensity;
  final bool ttsReady;
  final bool banterLayer;
  final String audioChannel;

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'line': line,
      'tone': tone,
      'commentator': commentator,
      'language': language,
      'intensity': intensity,
      'ttsReady': ttsReady,
      'banterLayer': banterLayer,
      'audioChannel': audioChannel,
    };
  }
}

@immutable
class Match3dCrowdState {
  const Match3dCrowdState({
    required this.profile,
    required this.homeIntensity,
    required this.awayIntensity,
    required this.dominantSide,
    required this.chantLevel,
    required this.hostility,
    required this.spike,
  });

  final String profile;
  final double homeIntensity;
  final double awayIntensity;
  final MatchViewerSide dominantSide;
  final double chantLevel;
  final double hostility;
  final bool spike;

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'profile': profile,
      'homeIntensity': homeIntensity,
      'awayIntensity': awayIntensity,
      'dominantSide': dominantSide.name,
      'chantLevel': chantLevel,
      'hostility': hostility,
      'spike': spike,
    };
  }
}

@immutable
class Match3dSpectatorSync {
  const Match3dSpectatorSync({
    required this.roomId,
    required this.syncStrategy,
    required this.sharedClockSecond,
    required this.tick,
    required this.maxLatencyMs,
    required this.checkpointIntervalSeconds,
    required this.pauseReplayEnabled,
    required this.reactionsEnabled,
  });

  final String roomId;
  final String syncStrategy;
  final int sharedClockSecond;
  final int tick;
  final int maxLatencyMs;
  final int checkpointIntervalSeconds;
  final bool pauseReplayEnabled;
  final bool reactionsEnabled;

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'roomId': roomId,
      'syncStrategy': syncStrategy,
      'sharedClockSecond': sharedClockSecond,
      'tick': tick,
      'maxLatencyMs': maxLatencyMs,
      'checkpointIntervalSeconds': checkpointIntervalSeconds,
      'pauseReplayEnabled': pauseReplayEnabled,
      'reactionsEnabled': reactionsEnabled,
    };
  }
}

@immutable
class Match3dExperienceLayer {
  const Match3dExperienceLayer({
    required this.motionPredictions,
    required this.commentary,
    required this.crowd,
    required this.spectatorSync,
  });

  final List<Match3dMotionPrediction> motionPredictions;
  final Match3dCommentaryCue commentary;
  final Match3dCrowdState crowd;
  final Match3dSpectatorSync spectatorSync;

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'motionPredictions': motionPredictions
          .map((Match3dMotionPrediction item) => item.toJson())
          .toList(growable: false),
      'commentary': commentary.toJson(),
      'crowd': crowd.toJson(),
      'spectatorSync': spectatorSync.toJson(),
    };
  }
}

@immutable
class Match3dSceneGraph {
  const Match3dSceneGraph({
    required this.matchId,
    required this.frameId,
    required this.clockMinute,
    required this.phase,
    required this.homeScore,
    required this.awayScore,
    required this.possessionSide,
    required this.possessionOwnerId,
    required this.requestedCameraPreset,
    required this.camera,
    required this.action,
    required this.experience,
    required this.homeShape,
    required this.awayShape,
    required this.activeEventContext,
    required this.entities,
    this.sequenceId,
    this.rootNodeId = 'scene-root',
  });

  final String matchId;
  final String frameId;
  final double clockMinute;
  final MatchViewerPhase phase;
  final int homeScore;
  final int awayScore;
  final MatchViewerSide possessionSide;
  final String? possessionOwnerId;
  final String? sequenceId;
  final String rootNodeId;
  final MatchEngineCameraPreset requestedCameraPreset;
  final Match3dCameraRig camera;
  final Match3dSceneAction action;
  final Match3dExperienceLayer experience;
  final MatchEngineTeamShape homeShape;
  final MatchEngineTeamShape awayShape;
  final MatchEngineEventContext? activeEventContext;
  final Map<String, Match3dSceneNode> entities;

  Match3dSceneNode get root => entities[rootNodeId]!;

  Iterable<Match3dSceneNode> get playerNodes sync* {
    for (final Match3dSceneNode node in entities.values) {
      if (node.type == Match3dSceneNodeType.player) {
        yield node;
      }
    }
  }

  Match3dSceneNode get ballNode => entities['ball']!;

  Match3dSceneNode? entity(String id) => entities[id];

  Map<String, Object?> toBridgePayload() {
    final List<Match3dSceneNode> orderedEntities =
        entities.values.toList()
          ..sort((Match3dSceneNode left, Match3dSceneNode right) {
            return left.id.compareTo(right.id);
          });
    return <String, Object?>{
      'type': 'SCENE_SYNC',
      'matchId': matchId,
      'frameId': frameId,
      'clockMinute': clockMinute,
      'phase': phase.name,
      'homeScore': homeScore,
      'awayScore': awayScore,
      'possessionSide': possessionSide.name,
      'possessionOwnerId': possessionOwnerId,
      'sequenceId': sequenceId,
      'rootNodeId': rootNodeId,
      'requestedCameraPreset': requestedCameraPreset.name,
      'camera': camera.toJson(),
      'action': action.toJson(),
      'experience': experience.toJson(),
      'homeShape': homeShape.toJson(),
      'awayShape': awayShape.toJson(),
      'activeEventContext': activeEventContext?.toJson(),
      'entities': orderedEntities
          .map((Match3dSceneNode node) => node.toJson())
          .toList(growable: false),
    };
  }
}
