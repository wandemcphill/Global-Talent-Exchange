using UnityEngine;

namespace Gtex.Match3D.Runtime
{
    public sealed class FlutterUnityBridge : MonoBehaviour
    {
        [SerializeField] private MatchController matchController;
        [SerializeField] private string runtimeId = "unity_match_3d";
        [SerializeField] private string viewType = "match_3d/unity_view";
        [SerializeField] private bool clearSceneOnSessionClose = true;
        [SerializeField] private bool createImplicitSessionFromSceneSync = true;
        [SerializeField] private bool platformViewAttached = false;

        private MatchNativeSessionStateDto _sessionState;
        private string _lastRuntimeEventJson = "{}";

        private void Awake()
        {
            if (matchController == null)
            {
                matchController = GetComponent<MatchController>();
            }

            EnsureSessionState();
            RecordRuntimeEvent("RUNTIME_READY");
        }

        public void SetController(MatchController controller)
        {
            matchController = controller;
        }

        public string GetRuntimeInfoJson()
        {
            EnsureSessionState();
            return MatchRuntimeJson.SerializeRuntimeInfo(BuildRuntimeInfo());
        }

        public string GetSessionStateJson()
        {
            EnsureSessionState();
            return MatchRuntimeJson.SerializeSessionState(_sessionState);
        }

        public string GetLastRuntimeEventJson()
        {
            return _lastRuntimeEventJson;
        }

        public string OpenSession(string json)
        {
            EnsureSessionState();
            MatchNativeSessionDescriptorDto descriptor =
                MatchRuntimeJson.DeserializeSessionDescriptor(json);
            if (descriptor == null)
            {
                return MatchRuntimeJson.SerializeSessionState(_sessionState);
            }

            if (clearSceneOnSessionClose && matchController != null)
            {
                matchController.ClearScene();
            }

            _sessionState = new MatchNativeSessionStateDto
            {
                sessionId = ResolveSessionId(descriptor.sessionId, descriptor.matchId),
                matchId = descriptor.matchId,
                status = "open",
                runtime = runtimeId,
                platformViewAttached = platformViewAttached,
                ackCount = 0,
                entityCount = 0,
                playerCount = descriptor.expectedPlayerCount,
                lastFrameId = descriptor.initialFrameId,
                phase = descriptor.initialPhase,
                clockMinute = descriptor.initialClockMinute,
                @implicit = false,
            };

            RecordRuntimeEvent("SESSION_OPENED");
            return MatchRuntimeJson.SerializeSessionState(_sessionState);
        }

        public string CloseSession(string json)
        {
            EnsureSessionState();
            MatchNativeSessionCloseRequestDto request =
                MatchRuntimeJson.DeserializeSessionCloseRequest(json);
            string requestedSessionId = request != null ? request.sessionId : null;
            if (!string.IsNullOrWhiteSpace(requestedSessionId) &&
                !string.Equals(_sessionState.sessionId, requestedSessionId, System.StringComparison.Ordinal))
            {
                return MatchRuntimeJson.SerializeSessionState(_sessionState);
            }

            _sessionState.status = "closed";
            _sessionState.platformViewAttached = false;
            _sessionState.@implicit = false;
            platformViewAttached = false;

            if (clearSceneOnSessionClose && matchController != null)
            {
                matchController.ClearScene();
            }

            RecordRuntimeEvent("SESSION_CLOSED");
            return MatchRuntimeJson.SerializeSessionState(_sessionState);
        }

        public string SetPlatformViewAttached(string json)
        {
            EnsureSessionState();
            MatchPlatformViewAttachmentDto payload =
                MatchRuntimeJson.DeserializePlatformViewAttachment(json);
            platformViewAttached = payload != null && payload.attached;
            _sessionState.platformViewAttached = platformViewAttached;

            return RecordRuntimeEvent(
                platformViewAttached ? "PLATFORM_VIEW_ATTACHED" : "PLATFORM_VIEW_DETACHED");
        }

        public void HandleMessage(string json)
        {
            HandleSceneSync(json);
        }

        public void HandleSceneSync(string json)
        {
            HandleSceneSyncWithAck(json);
        }

        public string HandleSceneSyncWithAck(string json)
        {
            MatchSceneSyncPayload payload = MatchRuntimeJson.DeserializeSceneSync(json);
            if (payload == null || matchController == null)
            {
                return _lastRuntimeEventJson;
            }

            EnsureSceneSession(payload);
            matchController.ApplySceneSync(payload);
            UpdateSessionFromPayload(payload);
            return RecordRuntimeEvent(
                "SCENE_SYNC_ACK",
                payload.action != null ? payload.action.type : null);
        }

        public void HandleMatchEvent(string json)
        {
            MatchEventDto matchEvent = MatchRuntimeJson.DeserializeMatchEvent(json);
            if (matchEvent == null || matchController == null)
            {
                return;
            }

            matchController.HandleEvent(matchEvent);
        }

        private void EnsureSessionState()
        {
            if (_sessionState != null)
            {
                return;
            }

            _sessionState = new MatchNativeSessionStateDto
            {
                sessionId = string.Empty,
                matchId = string.Empty,
                status = "idle",
                runtime = runtimeId,
                platformViewAttached = platformViewAttached,
                ackCount = 0,
                entityCount = 0,
                playerCount = 0,
                lastFrameId = null,
                phase = null,
                clockMinute = 0f,
                @implicit = false,
            };
        }

        private void EnsureSceneSession(MatchSceneSyncPayload payload)
        {
            EnsureSessionState();
            if (_sessionState.IsOpen() &&
                (string.IsNullOrWhiteSpace(payload.sessionId) ||
                 string.Equals(_sessionState.sessionId, payload.sessionId, System.StringComparison.Ordinal)))
            {
                return;
            }

            if (!createImplicitSessionFromSceneSync)
            {
                return;
            }

            _sessionState.sessionId = ResolveSessionId(payload.sessionId, payload.matchId);
            _sessionState.matchId = payload.matchId;
            _sessionState.status = "implicit";
            _sessionState.runtime = runtimeId;
            _sessionState.platformViewAttached = platformViewAttached;
            _sessionState.ackCount = 0;
            _sessionState.entityCount = 0;
            _sessionState.playerCount = 0;
            _sessionState.lastFrameId = payload.frameId;
            _sessionState.phase = payload.phase;
            _sessionState.clockMinute = payload.clockMinute;
            _sessionState.@implicit = true;

            RecordRuntimeEvent("SESSION_IMPLICIT");
        }

        private void UpdateSessionFromPayload(MatchSceneSyncPayload payload)
        {
            EnsureSessionState();
            _sessionState.sessionId = ResolveSessionId(payload.sessionId, payload.matchId);
            _sessionState.matchId = payload.matchId;
            _sessionState.runtime = runtimeId;
            _sessionState.platformViewAttached = platformViewAttached;
            _sessionState.ackCount += 1;
            _sessionState.entityCount = payload.entities != null ? payload.entities.Length : 0;
            _sessionState.playerCount = CountPlayers(payload);
            _sessionState.lastFrameId = payload.frameId;
            _sessionState.phase = payload.phase;
            _sessionState.clockMinute = payload.clockMinute;
            if (!_sessionState.@implicit)
            {
                _sessionState.status = "open";
            }
        }

        private MatchNativeRuntimeInfoDto BuildRuntimeInfo()
        {
            EnsureSessionState();
            return new MatchNativeRuntimeInfoDto
            {
                available = true,
                platform = "unity",
                runtime = runtimeId,
                viewType = viewType,
                supportsSessions = true,
                platformViewAttached = _sessionState.platformViewAttached,
                sessionStatus = _sessionState.status,
                sessionId = _sessionState.sessionId,
                matchId = _sessionState.matchId,
                ackCount = _sessionState.ackCount,
            };
        }

        private string RecordRuntimeEvent(string type, string actionType = null)
        {
            MatchNativeRuntimeEventDto payload = BuildRuntimeEvent(type, actionType);
            _lastRuntimeEventJson = MatchRuntimeJson.SerializeRuntimeEvent(payload);
            return _lastRuntimeEventJson;
        }

        private MatchNativeRuntimeEventDto BuildRuntimeEvent(string type, string actionType)
        {
            EnsureSessionState();
            return new MatchNativeRuntimeEventDto
            {
                type = type,
                available = true,
                platform = "unity",
                runtime = runtimeId,
                viewType = viewType,
                supportsSessions = true,
                platformViewAttached = _sessionState.platformViewAttached,
                sessionStatus = _sessionState.status,
                sessionId = _sessionState.sessionId,
                matchId = _sessionState.matchId,
                status = _sessionState.status,
                ackCount = _sessionState.ackCount,
                entityCount = _sessionState.entityCount,
                playerCount = _sessionState.playerCount,
                lastFrameId = _sessionState.lastFrameId,
                phase = _sessionState.phase,
                clockMinute = _sessionState.clockMinute,
                actionType = actionType,
                @implicit = _sessionState.@implicit,
            };
        }

        private static int CountPlayers(MatchSceneSyncPayload payload)
        {
            if (payload == null || payload.entities == null)
            {
                return 0;
            }

            int count = 0;
            for (int index = 0; index < payload.entities.Length; index += 1)
            {
                MatchSceneNodeDto entity = payload.entities[index];
                if (entity != null &&
                    string.Equals(entity.type, "player", System.StringComparison.OrdinalIgnoreCase))
                {
                    count += 1;
                }
            }

            return count;
        }

        private static string ResolveSessionId(string preferredSessionId, string matchId)
        {
            if (!string.IsNullOrWhiteSpace(preferredSessionId))
            {
                return preferredSessionId;
            }

            if (!string.IsNullOrWhiteSpace(matchId))
            {
                return "unity_match_3d:" + matchId;
            }

            return "unity_match_3d:implicit";
        }
    }
}
