using System;
using UnityEngine;

namespace FStudio.GTEX.Engine
{
    [DisallowMultipleComponent]
    public sealed class GTEXUnityBridge : MonoBehaviour
    {
        private const string RuntimeName = "unity_match_3d";
        private const string PlatformName = "unity";
        private const string ViewType = "match_3d/native_view";

        public const string BridgeGameObjectName = "GTEXUnityBridge";

        private static GTEXUnityBridge instance;

        private readonly BridgeSessionState sessionState = new BridgeSessionState();

        private bool runtimeReadySent;

        private void Awake()
        {
            if (instance != null && instance != this)
            {
                Destroy(gameObject);
                return;
            }

            instance = this;
            gameObject.name = BridgeGameObjectName;

            if (Application.isPlaying)
            {
                DontDestroyOnLoad(gameObject);
            }

            EmitRuntimeReady();
        }

        private void OnDestroy()
        {
            if (instance == this)
            {
                instance = null;
            }
        }

        public void OpenSession(string json)
        {
            var request = Deserialize<SessionRequest>(json);
            sessionState.SessionId = SelectValue(
                request != null ? request.sessionId : null,
                sessionState.SessionId);
            sessionState.MatchId = SelectValue(
                request != null ? request.matchId : null,
                sessionState.MatchId);
            sessionState.Status = "open";
            sessionState.Implicit = false;
            sessionState.LastFrameId = request != null ? request.initialFrameId : sessionState.LastFrameId;
            sessionState.Phase = request != null ? request.initialPhase : sessionState.Phase;
            sessionState.ClockMinute = request != null ? request.initialClockMinute : sessionState.ClockMinute;
            sessionState.PlayerCount = request != null ? Mathf.Max(0, request.expectedPlayerCount) : sessionState.PlayerCount;
            sessionState.EntityCount = Mathf.Max(sessionState.EntityCount, sessionState.PlayerCount);

            EmitRuntimeEvent("SESSION_OPENED");
        }

        public void CloseSession(string json)
        {
            var request = Deserialize<SessionLifecycleRequest>(json);
            sessionState.SessionId = SelectValue(
                request != null ? request.sessionId : null,
                sessionState.SessionId);
            sessionState.Status = "closed";
            sessionState.PlatformViewAttached = false;
            sessionState.Implicit = false;

            EmitRuntimeEvent("SESSION_CLOSED");
        }

        public void SetPlatformViewAttached(string json)
        {
            var request = Deserialize<PlatformAttachmentRequest>(json);
            var attached = request != null && request.attached;
            if (sessionState.PlatformViewAttached == attached && runtimeReadySent)
            {
                return;
            }

            sessionState.PlatformViewAttached = attached;
            EmitRuntimeEvent(attached ? "PLATFORM_VIEW_ATTACHED" : "PLATFORM_VIEW_DETACHED");
        }

        public void HandleSceneSyncWithAck(string json)
        {
            var request = Deserialize<SceneSyncRequest>(json);
            if (request != null)
            {
                sessionState.SessionId = SelectValue(request.sessionId, sessionState.SessionId);
                sessionState.MatchId = SelectValue(request.matchId, sessionState.MatchId);
                sessionState.Status = "open";
                sessionState.LastFrameId = request.frameId;
                sessionState.Phase = request.phase;
                sessionState.ClockMinute = request.clockMinute;
                sessionState.EntityCount = request.entities != null ? request.entities.Length : 0;
                sessionState.PlayerCount = CountPlayers(request.entities);
                sessionState.AckCount += 1;
            }

            EmitRuntimeEvent(
                "SCENE_SYNC_ACK",
                request != null ? request.frameId : sessionState.LastFrameId,
                request != null ? request.phase : sessionState.Phase,
                request != null ? request.clockMinute : sessionState.ClockMinute,
                request != null && request.action != null ? request.action.type : null);
        }

        private void EmitRuntimeReady()
        {
            if (runtimeReadySent)
            {
                return;
            }

            runtimeReadySent = true;
            EmitRuntimeEvent("RUNTIME_READY");
        }

        private void EmitRuntimeEvent(
            string type,
            string frameId = null,
            string phase = null,
            float clockMinute = float.NaN,
            string actionType = null)
        {
            var payload = new RuntimeEventPayload
            {
                type = type,
                available = true,
                platform = PlatformName,
                runtime = RuntimeName,
                viewType = ViewType,
                supportsSessions = true,
                sessionId = sessionState.SessionId,
                matchId = sessionState.MatchId,
                status = sessionState.Status,
                sessionStatus = sessionState.Status,
                platformViewAttached = sessionState.PlatformViewAttached,
                ackCount = sessionState.AckCount,
                entityCount = sessionState.EntityCount,
                playerCount = sessionState.PlayerCount,
                frameId = SelectValue(frameId, sessionState.LastFrameId),
                lastFrameId = SelectValue(frameId, sessionState.LastFrameId),
                phase = SelectValue(phase, sessionState.Phase),
                clockMinute = float.IsNaN(clockMinute) ? sessionState.ClockMinute : clockMinute,
                actionType = actionType,
                implicitSession = sessionState.Implicit,
                @implicit = sessionState.Implicit
            };

            var json = JsonUtility.ToJson(payload);
            ForwardRuntimeEvent(json);
            Debug.Log("[GTEXUnityBridge] " + type + " -> " + json);
        }

        private static T Deserialize<T>(string json) where T : class
        {
            if (string.IsNullOrWhiteSpace(json))
            {
                return null;
            }

            try
            {
                return JsonUtility.FromJson<T>(json);
            }
            catch (Exception exception)
            {
                Debug.LogWarning("[GTEXUnityBridge] Failed to parse payload.\n" + exception);
                return null;
            }
        }

        private static void ForwardRuntimeEvent(string json)
        {
#if UNITY_ANDROID && !UNITY_EDITOR
            try
            {
                var callback = new AndroidJavaClass("com.gtex.exchange.match3d.UnityBridgeCallback");
                callback.CallStatic("onRuntimeEvent", json);
            }
            catch (Exception exception)
            {
                Debug.LogWarning("[GTEXUnityBridge] Failed to forward runtime event to Android bridge.\n" + exception);
            }
#endif
        }

        private static int CountPlayers(SceneEntity[] entities)
        {
            if (entities == null || entities.Length == 0)
            {
                return 0;
            }

            var count = 0;
            for (var index = 0; index < entities.Length; index += 1)
            {
                var entity = entities[index];
                if (entity == null)
                {
                    continue;
                }

                var entityType = entity.type ?? string.Empty;
                var payloadKind = entity.payload != null ? entity.payload.kind ?? string.Empty : string.Empty;
                if (string.Equals(entityType, "player", StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(payloadKind, "player", StringComparison.OrdinalIgnoreCase))
                {
                    count += 1;
                }
            }

            return count;
        }

        private static string SelectValue(string candidate, string fallback)
        {
            return string.IsNullOrWhiteSpace(candidate) ? fallback ?? string.Empty : candidate;
        }

        [Serializable]
        private sealed class SessionRequest
        {
            public string sessionId;
            public string matchId;
            public string initialFrameId;
            public float initialClockMinute;
            public string initialPhase;
            public int expectedPlayerCount;
        }

        [Serializable]
        private sealed class SessionLifecycleRequest
        {
            public string sessionId;
        }

        [Serializable]
        private sealed class PlatformAttachmentRequest
        {
            public bool attached;
        }

        [Serializable]
        private sealed class SceneSyncRequest
        {
            public string sessionId;
            public string matchId;
            public string frameId;
            public float clockMinute;
            public string phase;
            public SceneAction action;
            public SceneEntity[] entities = Array.Empty<SceneEntity>();
        }

        [Serializable]
        private sealed class SceneAction
        {
            public string type;
        }

        [Serializable]
        private sealed class SceneEntity
        {
            public string id;
            public string type;
            public SceneEntityPayload payload;
        }

        [Serializable]
        private sealed class SceneEntityPayload
        {
            public string kind;
        }

        [Serializable]
        private sealed class RuntimeEventPayload
        {
            public string type;
            public bool available;
            public string platform;
            public string runtime;
            public string viewType;
            public bool supportsSessions;
            public string sessionId;
            public string matchId;
            public string status;
            public string sessionStatus;
            public bool platformViewAttached;
            public int ackCount;
            public int entityCount;
            public int playerCount;
            public string frameId;
            public string lastFrameId;
            public string phase;
            public float clockMinute;
            public string actionType;
            public bool implicitSession;
            public bool @implicit;
        }

        private sealed class BridgeSessionState
        {
            public string SessionId = string.Empty;
            public string MatchId = string.Empty;
            public string Status = "idle";
            public bool PlatformViewAttached;
            public int AckCount;
            public int EntityCount;
            public int PlayerCount;
            public string LastFrameId = string.Empty;
            public string Phase = string.Empty;
            public float ClockMinute;
            public bool Implicit;
        }
    }
}
