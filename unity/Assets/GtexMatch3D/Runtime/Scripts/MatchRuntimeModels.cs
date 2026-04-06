using System;
using System.Collections.Generic;
using UnityEngine;

namespace Gtex.Match3D.Runtime
{
    [Serializable]
    public sealed class MatchSceneSyncPayload
    {
        public string type;
        public string sessionId;
        public string matchId;
        public string frameId;
        public float clockMinute;
        public string phase;
        public int homeScore;
        public int awayScore;
        public string possessionSide;
        public string sequenceId;
        public string rootNodeId;
        public string requestedCameraPreset;
        public MatchCameraRigDto camera;
        public MatchSceneActionDto action;
        public MatchSceneNodeDto[] entities;
        public MatchEventDto matchEvent;

        public bool IsSceneSync()
        {
            return string.Equals(type, "SCENE_SYNC", StringComparison.OrdinalIgnoreCase);
        }

        public MatchSceneNodeDto FindEntity(string entityId)
        {
            if (string.IsNullOrWhiteSpace(entityId) || entities == null)
            {
                return null;
            }

            for (int index = 0; index < entities.Length; index += 1)
            {
                MatchSceneNodeDto candidate = entities[index];
                if (candidate != null && string.Equals(candidate.id, entityId, StringComparison.Ordinal))
                {
                    return candidate;
                }
            }

            return null;
        }

        public MatchSceneNodeDto FindFirstEntityOfType(string entityType)
        {
            if (string.IsNullOrWhiteSpace(entityType) || entities == null)
            {
                return null;
            }

            for (int index = 0; index < entities.Length; index += 1)
            {
                MatchSceneNodeDto candidate = entities[index];
                if (candidate != null &&
                    string.Equals(candidate.type, entityType, StringComparison.OrdinalIgnoreCase))
                {
                    return candidate;
                }
            }

            return null;
        }
    }

    [Serializable]
    public sealed class MatchCameraRigDto
    {
        public string id;
        public string mode;
        public string projectionPreset;
        public SerializableVector3Dto position;
        public SerializableVector3Dto target;
    }

    [Serializable]
    public sealed class MatchSceneActionDto
    {
        public string type;
        public string cameraMode;
        public string[] highlightedEntityIds;
        public string label;
        public string primaryEntityId;
        public string secondaryEntityId;
    }

    [Serializable]
    public sealed class MatchSceneNodeDto
    {
        public string id;
        public string type;
        public string parentId;
        public string[] childIds;
        public SerializableVector3Dto position;
        public SerializableQuaternionDto rotation;
        public SerializableVector3Dto velocity;
        public MatchScenePayloadDto payload;
    }

    [Serializable]
    public sealed class MatchScenePayloadDto
    {
        public string kind;
        public string label;
        public float lengthMeters;
        public float widthMeters;
        public string teamId;
        public string side;
        public string role;
        public string line;
        public bool active;
        public bool highlighted;
        public bool hasPossession;
        public float speedRatio;
        public int staminaPct;
        public int shirtNumber;
        public MatchAnimationBlendDto animation;
        public string state;
        public string trajectoryType;
        public float elevation;
        public float spin;
        public string ownerPlayerId;
        public string targetPlayerId;
    }

    [Serializable]
    public sealed class MatchAnimationBlendDto
    {
        public string currentState;
        public string targetState;
        public float blendFactor;
        public int durationMs;
    }

    [Serializable]
    public sealed class MatchEventDto
    {
        public string id;
        public string type;
        public int sequence;
        public int minute;
        public int addedTime;
        public string clockLabel;
        public float timeSeconds;
        public string teamId;
        public string teamName;
        public string primaryPlayerId;
        public string primaryPlayerName;
        public string secondaryPlayerId;
        public string secondaryPlayerName;
        public int homeScore;
        public int awayScore;
        public string bannerText;
        public string commentary;
        public int emphasisLevel;
        public string[] highlightedPlayerIds;
        public string[] flags;
        public string playbackProfile;
        public string missVariant;
        public bool reviewable;
        public string reviewReason;
        public string reviewDecision;
        public string scoreCommit;
    }

    [Serializable]
    public sealed class MatchTeamIdentityDto
    {
        public string teamId;
        public string teamName;
    }

    [Serializable]
    public sealed class MatchNativeSessionDescriptorDto
    {
        public string sessionId;
        public string matchId;
        public string source;
        public MatchTeamIdentityDto homeTeam;
        public MatchTeamIdentityDto awayTeam;
        public string initialFrameId;
        public float initialClockMinute;
        public string initialPhase;
        public string initialCameraPreset;
        public int expectedPlayerCount;
        public float pitchLengthMeters = 105f;
        public float pitchWidthMeters = 68f;
        public int deterministicSeed;
    }

    [Serializable]
    public sealed class MatchNativeSessionCloseRequestDto
    {
        public string sessionId;
    }

    [Serializable]
    public sealed class MatchPlatformViewAttachmentDto
    {
        public bool attached;
    }

    [Serializable]
    public sealed class MatchNativeRuntimeInfoDto
    {
        public bool available = true;
        public string platform = "unity";
        public string runtime = "unity_match_3d";
        public string viewType = "match_3d/unity_view";
        public bool supportsSessions = true;
        public bool platformViewAttached;
        public string sessionStatus = "idle";
        public string sessionId;
        public string matchId;
        public int ackCount;
    }

    [Serializable]
    public sealed class MatchNativeSessionStateDto
    {
        public string sessionId;
        public string matchId;
        public string status = "idle";
        public string runtime = "unity_match_3d";
        public bool platformViewAttached;
        public int ackCount;
        public int entityCount;
        public int playerCount;
        public string lastFrameId;
        public string phase;
        public float clockMinute;
        public bool @implicit;

        public bool IsOpen()
        {
            return string.Equals(status, "open", StringComparison.OrdinalIgnoreCase) ||
                   string.Equals(status, "implicit", StringComparison.OrdinalIgnoreCase);
        }
    }

    [Serializable]
    public sealed class MatchNativeRuntimeEventDto
    {
        public string type;
        public bool available = true;
        public string platform = "unity";
        public string runtime = "unity_match_3d";
        public string viewType = "match_3d/unity_view";
        public bool supportsSessions = true;
        public bool platformViewAttached;
        public string sessionStatus = "idle";
        public string sessionId;
        public string matchId;
        public string status = "idle";
        public int ackCount;
        public int entityCount;
        public int playerCount;
        public string lastFrameId;
        public string phase;
        public float clockMinute;
        public string actionType;
        public bool @implicit;
    }

    [Serializable]
    public sealed class SerializableVector3Dto
    {
        public float x;
        public float y;
        public float z;

        public Vector3 ToVector3()
        {
            return new Vector3(x, y, z);
        }
    }

    [Serializable]
    public sealed class SerializableQuaternionDto
    {
        public float x;
        public float y;
        public float z;
        public float w = 1f;

        public Quaternion ToQuaternion()
        {
            return new Quaternion(x, y, z, w);
        }
    }

    [Serializable]
    public sealed class ReplayClip
    {
        public string label;
        public int framesPerSecond = 30;
        public List<ReplayFrameData> frames = new List<ReplayFrameData>();
    }

    [Serializable]
    public sealed class ReplayFrameData
    {
        public int tick;
        public string frameId;
        public float clockMinute;
        public int homeScore;
        public int awayScore;
        public string actionType;
        public string actionLabel;
        public List<ReplayPlayerFrameData> players = new List<ReplayPlayerFrameData>();
        public ReplayBallFrameData ball = new ReplayBallFrameData();
        public ReplayCameraFrameData camera = new ReplayCameraFrameData();
    }

    [Serializable]
    public sealed class ReplayPlayerFrameData
    {
        public string id;
        public Vector3 position;
        public Quaternion rotation = Quaternion.identity;
        public Vector3 velocity;
        public string animationState;
        public bool highlighted;
        public bool hasPossession;
    }

    [Serializable]
    public sealed class ReplayBallFrameData
    {
        public Vector3 position;
        public Quaternion rotation = Quaternion.identity;
        public Vector3 velocity;
        public float spin;
        public string state;
        public string trajectoryType;
    }

    [Serializable]
    public sealed class ReplayCameraFrameData
    {
        public Vector3 position;
        public Vector3 target;
        public string mode;
        public string projectionPreset;
    }

    public static class MatchRuntimeJson
    {
        public static MatchSceneSyncPayload DeserializeSceneSync(string json)
        {
            if (string.IsNullOrWhiteSpace(json))
            {
                return null;
            }

            try
            {
                return JsonUtility.FromJson<MatchSceneSyncPayload>(json);
            }
            catch (Exception exception)
            {
                Debug.LogError("Failed to parse scene sync payload.\n" + exception);
                return null;
            }
        }

        public static MatchEventDto DeserializeMatchEvent(string json)
        {
            if (string.IsNullOrWhiteSpace(json))
            {
                return null;
            }

            try
            {
                return JsonUtility.FromJson<MatchEventDto>(json);
            }
            catch (Exception exception)
            {
                Debug.LogError("Failed to parse match event payload.\n" + exception);
                return null;
            }
        }

        public static MatchNativeSessionDescriptorDto DeserializeSessionDescriptor(string json)
        {
            if (string.IsNullOrWhiteSpace(json))
            {
                return null;
            }

            try
            {
                return JsonUtility.FromJson<MatchNativeSessionDescriptorDto>(json);
            }
            catch (Exception exception)
            {
                Debug.LogError("Failed to parse native session descriptor.\n" + exception);
                return null;
            }
        }

        public static MatchNativeSessionCloseRequestDto DeserializeSessionCloseRequest(string json)
        {
            if (string.IsNullOrWhiteSpace(json))
            {
                return null;
            }

            try
            {
                return JsonUtility.FromJson<MatchNativeSessionCloseRequestDto>(json);
            }
            catch (Exception exception)
            {
                Debug.LogError("Failed to parse native session close request.\n" + exception);
                return null;
            }
        }

        public static MatchPlatformViewAttachmentDto DeserializePlatformViewAttachment(string json)
        {
            if (string.IsNullOrWhiteSpace(json))
            {
                return null;
            }

            try
            {
                return JsonUtility.FromJson<MatchPlatformViewAttachmentDto>(json);
            }
            catch (Exception exception)
            {
                Debug.LogError("Failed to parse platform view attachment payload.\n" + exception);
                return null;
            }
        }

        public static string SerializeRuntimeInfo(MatchNativeRuntimeInfoDto payload)
        {
            return Serialize(payload);
        }

        public static string SerializeSessionState(MatchNativeSessionStateDto payload)
        {
            return Serialize(payload);
        }

        public static string SerializeRuntimeEvent(MatchNativeRuntimeEventDto payload)
        {
            return Serialize(payload);
        }

        private static string Serialize<T>(T payload) where T : class
        {
            if (payload == null)
            {
                return "{}";
            }

            try
            {
                return JsonUtility.ToJson(payload);
            }
            catch (Exception exception)
            {
                Debug.LogError("Failed to serialize runtime payload.\n" + exception);
                return "{}";
            }
        }
    }
}
