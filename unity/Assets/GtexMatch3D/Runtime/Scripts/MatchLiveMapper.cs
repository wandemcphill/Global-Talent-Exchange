using System;
using System.Collections.Generic;
using UnityEngine;

namespace Gtex.Match3D.Runtime
{
    public static class MatchLiveMapper
    {
        public static MatchSceneSyncPayload ToSceneSync(MatchResponse response)
        {
            if (response == null)
            {
                return null;
            }

            response.Normalize();
            Event activeEvent = response.ResolveActiveEvent();
            PlayerPosition ball = ResolveBallPosition(response);
            MatchSceneNodeDto[] entities = BuildEntities(response, ball, activeEvent);

            return new MatchSceneSyncPayload
            {
                type = "SCENE_SYNC",
                sessionId = "unity_match_3d:" + response.matchId,
                matchId = response.matchId,
                frameId = string.IsNullOrWhiteSpace(response.frameId)
                    ? "live:" + response.matchId + ":" + Mathf.RoundToInt(response.clockMinute * 100f)
                    : response.frameId,
                clockMinute = response.clockMinute,
                phase = response.phase,
                homeScore = response.homeScore,
                awayScore = response.awayScore,
                possessionSide = response.possessionSide,
                sequenceId = !string.IsNullOrWhiteSpace(response.activeEventId)
                    ? response.activeEventId
                    : response.frameId,
                rootNodeId = "scene-root",
                requestedCameraPreset = NormalizeProjectionPreset(response.cameraPreset),
                camera = BuildCameraRig(response, ball, activeEvent),
                action = BuildAction(activeEvent),
                entities = entities,
                matchEvent = BuildMatchEvent(activeEvent),
            };
        }

        private static MatchSceneNodeDto[] BuildEntities(
            MatchResponse response,
            PlayerPosition ball,
            Event activeEvent)
        {
            List<MatchSceneNodeDto> entities = new List<MatchSceneNodeDto>(response.players.Length + 2);
            entities.Add(BuildPitchNode(response));

            for (int index = 0; index < response.players.Length; index += 1)
            {
                PlayerPosition player = response.players[index];
                if (player == null || player.isBall)
                {
                    continue;
                }

                entities.Add(BuildPlayerNode(player, activeEvent));
            }

            if (ball != null)
            {
                entities.Add(BuildBallNode(ball, activeEvent));
            }

            return entities.ToArray();
        }

        private static MatchSceneNodeDto BuildPitchNode(MatchResponse response)
        {
            return new MatchSceneNodeDto
            {
                id = "pitch",
                type = "pitch",
                position = ToVector3Dto(Vector3.zero),
                rotation = ToQuaternionDto(Quaternion.identity),
                velocity = ToVector3Dto(Vector3.zero),
                payload = new MatchScenePayloadDto
                {
                    kind = "pitch",
                    label = "Pitch",
                    lengthMeters = response.pitchLengthMeters > 0f ? response.pitchLengthMeters : 105f,
                    widthMeters = response.pitchWidthMeters > 0f ? response.pitchWidthMeters : 68f,
                    active = true,
                },
            };
        }

        private static MatchSceneNodeDto BuildPlayerNode(PlayerPosition player, Event activeEvent)
        {
            Vector3 position = new Vector3(player.x, player.y, player.z);
            Vector3 velocity = new Vector3(player.velocityX, player.velocityY, player.velocityZ);

            return new MatchSceneNodeDto
            {
                id = ResolveEntityId(player),
                type = "player",
                parentId = "players",
                position = ToVector3Dto(position),
                rotation = ToQuaternionDto(ResolveRotation(player)),
                velocity = ToVector3Dto(velocity),
                payload = new MatchScenePayloadDto
                {
                    kind = "player",
                    label = player.label,
                    teamId = player.teamId,
                    side = player.teamSide,
                    role = player.role,
                    line = player.line,
                    active = player.active,
                    highlighted = player.highlighted,
                    hasPossession = player.hasPossession,
                    speedRatio = Mathf.Clamp01(player.speedRatio),
                    staminaPct = 100,
                    shirtNumber = Mathf.Max(0, player.shirtNumber),
                    animation = BuildAnimation(player, activeEvent),
                    state = player.state,
                },
            };
        }

        private static MatchSceneNodeDto BuildBallNode(PlayerPosition ball, Event activeEvent)
        {
            Vector3 position = new Vector3(ball.x, ball.y, ball.z);
            Vector3 velocity = new Vector3(ball.velocityX, ball.velocityY, ball.velocityZ);
            string trajectoryType = !string.IsNullOrWhiteSpace(ball.trajectoryType)
                ? ball.trajectoryType
                : ResolveBallTrajectoryType(activeEvent);

            return new MatchSceneNodeDto
            {
                id = "ball",
                type = "ball",
                position = ToVector3Dto(position),
                rotation = ToQuaternionDto(velocity.sqrMagnitude > 0.001f
                    ? Quaternion.LookRotation(velocity.normalized, Vector3.up)
                    : Quaternion.identity),
                velocity = ToVector3Dto(velocity),
                payload = new MatchScenePayloadDto
                {
                    kind = "ball",
                    label = "Ball",
                    active = true,
                    hasPossession = ball.hasPossession,
                    state = string.IsNullOrWhiteSpace(ball.state) ? "rolling" : ball.state,
                    trajectoryType = trajectoryType,
                    ownerPlayerId = ball.playerId,
                    spin = ball.spin,
                },
            };
        }

        private static MatchCameraRigDto BuildCameraRig(
            MatchResponse response,
            PlayerPosition ball,
            Event activeEvent)
        {
            Vector3 target = ResolveCameraTarget(response, ball, activeEvent);
            Vector3 offset = ResolveCameraOffset(response.cameraPreset, activeEvent);
            return new MatchCameraRigDto
            {
                id = "live-camera",
                mode = ResolveCameraMode(activeEvent),
                projectionPreset = NormalizeProjectionPreset(response.cameraPreset),
                position = ToVector3Dto(target + offset),
                target = ToVector3Dto(target),
            };
        }

        private static MatchSceneActionDto BuildAction(Event activeEvent)
        {
            if (activeEvent == null)
            {
                return null;
            }

            string actionType = NormalizeActionType(activeEvent.type);
            if (string.IsNullOrWhiteSpace(actionType))
            {
                return null;
            }

            return new MatchSceneActionDto
            {
                type = actionType,
                cameraMode = ResolveCameraMode(activeEvent),
                label = activeEvent.bannerText,
                primaryEntityId = ResolvePlayerEntityId(activeEvent.primaryPlayerId),
                secondaryEntityId = ResolvePlayerEntityId(activeEvent.secondaryPlayerId),
                highlightedEntityIds = ResolveHighlightedEntityIds(activeEvent),
            };
        }

        private static MatchEventDto BuildMatchEvent(Event activeEvent)
        {
            if (activeEvent == null)
            {
                return null;
            }

            return new MatchEventDto
            {
                id = activeEvent.id,
                type = activeEvent.type,
                sequence = activeEvent.sequence,
                minute = activeEvent.minute,
                addedTime = activeEvent.addedTime,
                clockLabel = activeEvent.clockLabel,
                timeSeconds = activeEvent.timeSeconds,
                teamId = activeEvent.teamId,
                teamName = activeEvent.teamName,
                primaryPlayerId = activeEvent.primaryPlayerId,
                primaryPlayerName = activeEvent.primaryPlayerName,
                secondaryPlayerId = activeEvent.secondaryPlayerId,
                secondaryPlayerName = activeEvent.secondaryPlayerName,
                homeScore = activeEvent.homeScore,
                awayScore = activeEvent.awayScore,
                bannerText = activeEvent.bannerText,
                commentary = activeEvent.commentary,
                emphasisLevel = activeEvent.emphasisLevel,
                highlightedPlayerIds = activeEvent.highlightedPlayerIds ?? Array.Empty<string>(),
                flags = activeEvent.flags ?? Array.Empty<string>(),
                playbackProfile = activeEvent.playbackProfile,
                missVariant = activeEvent.missVariant,
                reviewable = activeEvent.reviewable,
                reviewReason = activeEvent.reviewReason,
                reviewDecision = activeEvent.reviewDecision,
                scoreCommit = activeEvent.scoreCommit,
            };
        }

        private static MatchAnimationBlendDto BuildAnimation(PlayerPosition player, Event activeEvent)
        {
            string currentState = ResolveAnimationState(player.animationState, player.speedRatio);
            string targetState = ResolveTargetAnimation(player, activeEvent, currentState);
            return new MatchAnimationBlendDto
            {
                currentState = currentState,
                targetState = targetState,
                blendFactor = Mathf.Clamp01(player.speedRatio),
                durationMs = ResolveAnimationDurationMs(targetState),
            };
        }

        private static PlayerPosition ResolveBallPosition(MatchResponse response)
        {
            if (response.ballPosition != null)
            {
                return response.ballPosition;
            }

            for (int index = 0; index < response.players.Length; index += 1)
            {
                PlayerPosition candidate = response.players[index];
                if (candidate != null && candidate.hasPossession)
                {
                    return new PlayerPosition
                    {
                        entityId = "ball",
                        playerId = candidate.playerId,
                        x = candidate.x,
                        y = Mathf.Max(0.12f, candidate.y + 0.18f),
                        z = candidate.z,
                        isBall = true,
                        hasPossession = true,
                        state = "controlled",
                        trajectoryType = "controlled",
                    };
                }
            }

            return null;
        }

        private static string ResolveEntityId(PlayerPosition player)
        {
            if (!string.IsNullOrWhiteSpace(player.entityId))
            {
                return player.entityId;
            }

            return ResolvePlayerEntityId(player.playerId) ?? "player:unknown";
        }

        private static string ResolvePlayerEntityId(string playerId)
        {
            if (string.IsNullOrWhiteSpace(playerId))
            {
                return null;
            }

            return playerId.StartsWith("player:", StringComparison.Ordinal)
                ? playerId
                : "player:" + playerId;
        }

        private static string[] ResolveHighlightedEntityIds(Event activeEvent)
        {
            if (activeEvent == null)
            {
                return Array.Empty<string>();
            }

            List<string> ids = new List<string>();
            if (activeEvent.highlightedPlayerIds != null)
            {
                for (int index = 0; index < activeEvent.highlightedPlayerIds.Length; index += 1)
                {
                    string playerId = activeEvent.highlightedPlayerIds[index];
                    string entityId = ResolvePlayerEntityId(playerId);
                    if (!string.IsNullOrWhiteSpace(entityId))
                    {
                        ids.Add(entityId);
                    }
                }
            }

            if (ids.Count == 0)
            {
                string primary = ResolvePlayerEntityId(activeEvent.primaryPlayerId);
                string secondary = ResolvePlayerEntityId(activeEvent.secondaryPlayerId);
                if (!string.IsNullOrWhiteSpace(primary))
                {
                    ids.Add(primary);
                }

                if (!string.IsNullOrWhiteSpace(secondary))
                {
                    ids.Add(secondary);
                }
            }

            return ids.ToArray();
        }

        private static Vector3 ResolveCameraTarget(
            MatchResponse response,
            PlayerPosition ball,
            Event activeEvent)
        {
            if (activeEvent != null && !string.IsNullOrWhiteSpace(activeEvent.primaryPlayerId))
            {
                PlayerPosition focusPlayer = FindPlayer(response, activeEvent.primaryPlayerId);
                if (focusPlayer != null)
                {
                    return new Vector3(focusPlayer.x, focusPlayer.y, focusPlayer.z);
                }
            }

            if (ball != null)
            {
                return new Vector3(ball.x, ball.y, ball.z);
            }

            return Vector3.zero;
        }

        private static Vector3 ResolveCameraOffset(string cameraPreset, Event activeEvent)
        {
            string normalizedPreset = NormalizeProjectionPreset(cameraPreset);
            string mode = ResolveCameraMode(activeEvent);

            if (string.Equals(mode, "cinematic", StringComparison.OrdinalIgnoreCase))
            {
                return new Vector3(-8f, 9f, -7f);
            }

            if (string.Equals(mode, "tactical", StringComparison.OrdinalIgnoreCase))
            {
                return new Vector3(-10f, 22f, -8f);
            }

            if (string.Equals(normalizedPreset, "sideline", StringComparison.OrdinalIgnoreCase))
            {
                return new Vector3(-4f, 11f, -20f);
            }

            if (string.Equals(normalizedPreset, "goalbox", StringComparison.OrdinalIgnoreCase))
            {
                return new Vector3(-6f, 8f, -6f);
            }

            return new Vector3(-14f, 18f, -18f);
        }

        private static string ResolveCameraMode(Event activeEvent)
        {
            string actionType = NormalizeActionType(activeEvent != null ? activeEvent.type : null);
            if (string.Equals(actionType, "goal", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(actionType, "save", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(actionType, "miss", StringComparison.OrdinalIgnoreCase))
            {
                return "cinematic";
            }

            if (string.Equals(actionType, "foul", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(actionType, "offside", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(actionType, "kickoff", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(actionType, "setPiece", StringComparison.OrdinalIgnoreCase))
            {
                return "tactical";
            }

            return "followBall";
        }

        private static Quaternion ResolveRotation(PlayerPosition player)
        {
            Vector3 direction = new Vector3(player.facingX, 0f, player.facingZ);
            if (direction.sqrMagnitude <= 0.001f)
            {
                direction = new Vector3(player.velocityX, 0f, player.velocityZ);
            }

            if (direction.sqrMagnitude <= 0.001f)
            {
                direction = string.Equals(player.teamSide, "away", StringComparison.OrdinalIgnoreCase)
                    ? Vector3.left
                    : Vector3.right;
            }

            return Quaternion.LookRotation(direction.normalized, Vector3.up);
        }

        private static string ResolveAnimationState(string rawState, float speedRatio)
        {
            string normalized = (rawState ?? string.Empty).Trim().ToLowerInvariant();
            switch (normalized)
            {
                case "run":
                    return "run";
                case "sprint":
                    return "sprint";
                case "control":
                case "receive":
                    return "receive";
                case "pass":
                    return "pass";
                case "shoot":
                case "shot":
                    return "shoot";
                case "press":
                    return "tackle";
                case "save":
                    return "intercept";
                case "celebrate":
                    return "celebrate";
                case "recover":
                    return "recover";
                case "idle":
                    return "idle";
                default:
                    if (speedRatio >= 0.7f)
                    {
                        return "sprint";
                    }

                    if (speedRatio >= 0.25f)
                    {
                        return "run";
                    }

                    return "idle";
            }
        }

        private static string ResolveTargetAnimation(PlayerPosition player, Event activeEvent, string currentState)
        {
            if (activeEvent == null || !IsHighlightedByEvent(player, activeEvent))
            {
                return currentState;
            }

            string eventType = (activeEvent.type ?? string.Empty).Trim().ToLowerInvariant();
            switch (eventType)
            {
                case "goal":
                    return "celebrate";
                case "save":
                    return "receive";
                case "miss":
                case "penalty":
                    return "shoot";
                case "foul":
                    return "tackle";
                case "offside":
                    return "recover";
                default:
                    return currentState;
            }
        }

        private static int ResolveAnimationDurationMs(string state)
        {
            switch ((state ?? string.Empty).Trim().ToLowerInvariant())
            {
                case "celebrate":
                    return 360;
                case "shoot":
                    return 240;
                case "pass":
                    return 200;
                case "tackle":
                case "intercept":
                case "receive":
                    return 180;
                case "recover":
                    return 220;
                case "sprint":
                    return 160;
                case "run":
                case "idle":
                default:
                    return 160;
            }
        }

        private static bool IsHighlightedByEvent(PlayerPosition player, Event activeEvent)
        {
            if (player == null || activeEvent == null)
            {
                return false;
            }

            if (player.highlighted)
            {
                return true;
            }

            if (activeEvent.highlightedPlayerIds != null)
            {
                for (int index = 0; index < activeEvent.highlightedPlayerIds.Length; index += 1)
                {
                    if (string.Equals(activeEvent.highlightedPlayerIds[index], player.playerId, StringComparison.Ordinal))
                    {
                        return true;
                    }
                }
            }

            return string.Equals(activeEvent.primaryPlayerId, player.playerId, StringComparison.Ordinal) ||
                   string.Equals(activeEvent.secondaryPlayerId, player.playerId, StringComparison.Ordinal);
        }

        private static string NormalizeActionType(string value)
        {
            string normalized = (value ?? string.Empty).Trim().ToLowerInvariant();
            switch (normalized)
            {
                case "goal":
                    return "goal";
                case "save":
                    return "save";
                case "miss":
                    return "miss";
                case "foul":
                    return "foul";
                case "offside":
                    return "offside";
                case "kickoff":
                    return "kickoff";
                case "set_piece":
                case "setpiece":
                    return "setPiece";
                case "penalty":
                    return "shot";
                default:
                    return null;
            }
        }

        private static string NormalizeProjectionPreset(string value)
        {
            string normalized = (value ?? string.Empty).Trim().ToLowerInvariant();
            switch (normalized)
            {
                case "assistant_flag":
                case "sideline":
                    return "sideline";
                case "goal_celebration":
                case "goalbox":
                    return "goalbox";
                default:
                    return "broadcast";
            }
        }

        private static string ResolveBallTrajectoryType(Event activeEvent)
        {
            string eventType = (activeEvent != null ? activeEvent.type : string.Empty) ?? string.Empty;
            switch (eventType.Trim().ToLowerInvariant())
            {
                case "goal":
                case "save":
                case "miss":
                case "penalty":
                    return "shot";
                case "kickoff":
                case "set_piece":
                    return "pass";
                default:
                    return "controlled";
            }
        }

        private static PlayerPosition FindPlayer(MatchResponse response, string playerId)
        {
            if (response == null || response.players == null || string.IsNullOrWhiteSpace(playerId))
            {
                return null;
            }

            for (int index = 0; index < response.players.Length; index += 1)
            {
                PlayerPosition candidate = response.players[index];
                if (candidate != null &&
                    string.Equals(candidate.playerId, playerId, StringComparison.Ordinal))
                {
                    return candidate;
                }
            }

            return null;
        }

        private static SerializableVector3Dto ToVector3Dto(Vector3 vector)
        {
            return new SerializableVector3Dto
            {
                x = vector.x,
                y = vector.y,
                z = vector.z,
            };
        }

        private static SerializableQuaternionDto ToQuaternionDto(Quaternion quaternion)
        {
            return new SerializableQuaternionDto
            {
                x = quaternion.x,
                y = quaternion.y,
                z = quaternion.z,
                w = quaternion.w,
            };
        }
    }
}
