using System;
using System.Collections.Generic;
using UnityEngine;

namespace Gtex.Match3D.Runtime
{
    public sealed class MatchController : MonoBehaviour
    {
        public readonly Dictionary<string, PlayerController> players = new Dictionary<string, PlayerController>();

        [SerializeField] private PlayerController playerPrefab;
        [SerializeField] private Transform playersRoot;
        [SerializeField] private PitchController pitch;
        [SerializeField] private BallController ball;
        [SerializeField] private CameraController cameraController;
        [SerializeField] private ReplayRecorder replayRecorder;
        [SerializeField] private ReplayPlayer replayPlayer;
        [SerializeField] private bool autoCreatePlayers = true;
        [SerializeField] private bool autoPlayGoalReplays = true;
        [SerializeField] private float autoReplayPlaybackSpeed = 0.55f;
        [SerializeField] private bool snapFirstFrame = true;

        private bool _hasSceneSync;
        private bool _replayMode;
        private string _lastFrameId;
        private string _lastActionKey;
        private string _lastEventId;
        private string _lastMarkedReplayEventId;

        private void Awake()
        {
            if (pitch == null)
            {
                pitch = GetComponentInChildren<PitchController>(true);
            }

            if (ball == null)
            {
                ball = GetComponentInChildren<BallController>(true);
            }

            if (cameraController == null)
            {
                cameraController = GetComponentInChildren<CameraController>(true);
            }

            if (replayRecorder == null)
            {
                replayRecorder = GetComponent<ReplayRecorder>();
            }

            if (replayPlayer == null)
            {
                replayPlayer = GetComponent<ReplayPlayer>();
            }
        }

        public void ConfigureScene(
            PitchController pitchController,
            BallController ballController,
            CameraController cameraRig,
            Transform playerContainer,
            PlayerController playerTemplate,
            ReplayRecorder recorder,
            ReplayPlayer player)
        {
            pitch = pitchController;
            ball = ballController;
            cameraController = cameraRig;
            playersRoot = playerContainer;
            playerPrefab = playerTemplate;
            replayRecorder = recorder;
            replayPlayer = player;

            if (replayPlayer != null)
            {
                replayPlayer.SetMatchController(this);
            }
        }

        public void SetReplayMode(bool enabled)
        {
            _replayMode = enabled;
        }

        public void ApplySceneSync(MatchSceneSyncPayload payload)
        {
            if (payload == null || !payload.IsSceneSync())
            {
                return;
            }

            if (replayPlayer != null && replayPlayer.IgnoreLiveSync && _replayMode)
            {
                return;
            }

            if (!string.IsNullOrWhiteSpace(payload.frameId) &&
                string.Equals(_lastFrameId, payload.frameId, StringComparison.Ordinal))
            {
                return;
            }

            bool immediate = !_hasSceneSync && snapFirstFrame;
            _hasSceneSync = true;
            _lastFrameId = payload.frameId;

            MatchSceneNodeDto pitchNode = payload.FindEntity("pitch") ?? payload.FindFirstEntityOfType("pitch");
            if (pitch != null)
            {
                pitch.ApplySceneNode(pitchNode);
            }

            SyncPlayers(payload, immediate);

            MatchSceneNodeDto ballNode = payload.FindEntity("ball") ?? payload.FindFirstEntityOfType("ball");
            if (ball != null && ballNode != null)
            {
                bool treatAsShot = payload.action != null &&
                                   (string.Equals(payload.action.type, "shot", StringComparison.OrdinalIgnoreCase) ||
                                    string.Equals(payload.action.type, "goal", StringComparison.OrdinalIgnoreCase) ||
                                    string.Equals(payload.action.type, "save", StringComparison.OrdinalIgnoreCase) ||
                                    string.Equals(payload.action.type, "miss", StringComparison.OrdinalIgnoreCase));
                ball.ApplySceneNode(ballNode, immediate, treatAsShot);
            }

            if (cameraController != null && payload.camera != null)
            {
                cameraController.ApplyRig(
                    payload.camera,
                    payload.action,
                    ball != null ? ball.transform : null,
                    ResolveTransform(payload.action != null ? payload.action.primaryEntityId : null),
                    ResolveTransform(payload.action != null ? payload.action.secondaryEntityId : null),
                    immediate);
            }

            TriggerAction(payload);
            TriggerEvent(payload.matchEvent);

            if (replayRecorder != null)
            {
                replayRecorder.RecordFrame(payload, players, ball, cameraController);
                MarkReplayHighlight(payload);

                ReplayClip readyClip = replayRecorder.ConsumeReadyHighlight();
                if (readyClip != null &&
                    autoPlayGoalReplays &&
                    replayPlayer != null &&
                    !replayPlayer.IsPlaying)
                {
                    replayPlayer.Play(readyClip, false, autoReplayPlaybackSpeed, true);
                }
            }
        }

        public void HandleEvent(MatchEventDto matchEvent)
        {
            if (matchEvent == null)
            {
                return;
            }

            PlayerController primaryPlayer = ResolvePlayerById(matchEvent.primaryPlayerId);
            PlayerController secondaryPlayer = ResolvePlayerById(matchEvent.secondaryPlayerId);

            if (string.Equals(matchEvent.type, "goal", StringComparison.OrdinalIgnoreCase))
            {
                if (primaryPlayer != null)
                {
                    primaryPlayer.PlayAnimation("celebrate", 0.12f);
                    if (cameraController != null)
                    {
                        cameraController.FocusTransform(primaryPlayer.transform);
                    }
                }
            }
            else if (string.Equals(matchEvent.type, "save", StringComparison.OrdinalIgnoreCase))
            {
                if (primaryPlayer != null)
                {
                    primaryPlayer.PlayAnimation("receive", 0.10f);
                }

                if (cameraController != null)
                {
                    cameraController.FocusBall();
                }
            }
            else if (string.Equals(matchEvent.type, "miss", StringComparison.OrdinalIgnoreCase) ||
                     string.Equals(matchEvent.type, "penalty", StringComparison.OrdinalIgnoreCase))
            {
                if (primaryPlayer != null)
                {
                    primaryPlayer.PlayAnimation("shoot", 0.10f);
                }

                if (cameraController != null)
                {
                    cameraController.FocusBall();
                }
            }
            else if (string.Equals(matchEvent.type, "foul", StringComparison.OrdinalIgnoreCase))
            {
                if (primaryPlayer != null)
                {
                    primaryPlayer.PlayAnimation("tackle", 0.08f);
                }

                if (secondaryPlayer != null)
                {
                    secondaryPlayer.PlayAnimation("recover", 0.08f);
                }
            }
            else if (string.Equals(matchEvent.type, "offside", StringComparison.OrdinalIgnoreCase))
            {
                if (primaryPlayer != null)
                {
                    primaryPlayer.PlayAnimation("recover", 0.10f);
                }
            }
        }

        public void ApplyReplayFrame(ReplayFrameData frame, bool immediate)
        {
            if (frame == null)
            {
                return;
            }

            HashSet<string> activeIds = new HashSet<string>(StringComparer.Ordinal);
            for (int index = 0; index < frame.players.Count; index += 1)
            {
                ReplayPlayerFrameData playerFrame = frame.players[index];
                PlayerController controller = GetOrCreatePlayer(playerFrame.id);
                if (controller == null)
                {
                    continue;
                }

                activeIds.Add(playerFrame.id);
                controller.gameObject.SetActive(true);
                controller.ApplyReplayFrame(playerFrame, immediate);
            }

            foreach (KeyValuePair<string, PlayerController> entry in players)
            {
                if (entry.Value == null)
                {
                    continue;
                }

                if (!activeIds.Contains(entry.Key))
                {
                    entry.Value.gameObject.SetActive(false);
                }
            }

            if (ball != null)
            {
                ball.ApplyReplayFrame(frame.ball, immediate);
            }

            if (cameraController != null)
            {
                cameraController.ApplyReplayFrame(frame.camera, immediate);
            }
        }

        private void SyncPlayers(MatchSceneSyncPayload payload, bool immediate)
        {
            HashSet<string> liveIds = new HashSet<string>(StringComparer.Ordinal);

            if (payload.entities != null)
            {
                for (int index = 0; index < payload.entities.Length; index += 1)
                {
                    MatchSceneNodeDto node = payload.entities[index];
                    if (node == null ||
                        !string.Equals(node.type, "player", StringComparison.OrdinalIgnoreCase))
                    {
                        continue;
                    }

                    PlayerController controller = GetOrCreatePlayer(node.id);
                    if (controller == null)
                    {
                        continue;
                    }

                    controller.gameObject.SetActive(true);
                    controller.ApplySceneNode(node, immediate);
                    liveIds.Add(node.id);
                }
            }

            foreach (KeyValuePair<string, PlayerController> entry in players)
            {
                if (entry.Value == null)
                {
                    continue;
                }

                if (!liveIds.Contains(entry.Key))
                {
                    entry.Value.gameObject.SetActive(false);
                }
            }
        }

        private PlayerController GetOrCreatePlayer(string entityId)
        {
            if (string.IsNullOrWhiteSpace(entityId))
            {
                return null;
            }

            PlayerController existing;
            if (players.TryGetValue(entityId, out existing) && existing != null)
            {
                return existing;
            }

            if (!autoCreatePlayers)
            {
                return null;
            }

            if (playersRoot == null)
            {
                playersRoot = transform;
            }

            PlayerController created;
            if (playerPrefab != null)
            {
                created = Instantiate(playerPrefab, playersRoot);
                created.gameObject.SetActive(true);
            }
            else
            {
                GameObject playerObject = GameObject.CreatePrimitive(PrimitiveType.Capsule);
                playerObject.transform.SetParent(playersRoot, false);
                playerObject.transform.localScale = new Vector3(0.60f, 0.90f, 0.60f);
                created = playerObject.AddComponent<PlayerController>();
            }

            created.name = entityId;
            players[entityId] = created;
            return created;
        }

        private void TriggerAction(MatchSceneSyncPayload payload)
        {
            if (payload == null || payload.action == null)
            {
                return;
            }

            string key = BuildActionKey(payload);
            if (string.Equals(_lastActionKey, key, StringComparison.Ordinal))
            {
                return;
            }

            _lastActionKey = key;
            MatchSceneActionDto action = payload.action;
            PlayerController primaryPlayer = ResolveEntity(action.primaryEntityId);
            PlayerController secondaryPlayer = ResolveEntity(action.secondaryEntityId);

            if (string.Equals(action.type, "pass", StringComparison.OrdinalIgnoreCase))
            {
                if (primaryPlayer != null)
                {
                    primaryPlayer.PlayAnimation("pass", 0.08f);
                }

                if (secondaryPlayer != null)
                {
                    secondaryPlayer.PlayAnimation("receive", 0.08f);
                }
            }
            else if (string.Equals(action.type, "shot", StringComparison.OrdinalIgnoreCase))
            {
                if (primaryPlayer != null)
                {
                    primaryPlayer.PlayAnimation("shoot", 0.10f);
                }

                if (cameraController != null)
                {
                    cameraController.FocusBall();
                }
            }
            else if (string.Equals(action.type, "goal", StringComparison.OrdinalIgnoreCase))
            {
                if (primaryPlayer != null)
                {
                    primaryPlayer.PlayAnimation("celebrate", 0.10f);
                    if (cameraController != null)
                    {
                        cameraController.FocusTransform(primaryPlayer.transform);
                    }
                }
            }
            else if (string.Equals(action.type, "save", StringComparison.OrdinalIgnoreCase))
            {
                if (primaryPlayer != null)
                {
                    primaryPlayer.PlayAnimation("receive", 0.08f);
                }
            }
            else if (string.Equals(action.type, "miss", StringComparison.OrdinalIgnoreCase))
            {
                if (primaryPlayer != null)
                {
                    primaryPlayer.PlayAnimation("shoot", 0.08f);
                }
            }
            else if (string.Equals(action.type, "foul", StringComparison.OrdinalIgnoreCase))
            {
                if (primaryPlayer != null)
                {
                    primaryPlayer.PlayAnimation("tackle", 0.08f);
                }
            }
            else if (string.Equals(action.type, "offside", StringComparison.OrdinalIgnoreCase))
            {
                if (primaryPlayer != null)
                {
                    primaryPlayer.PlayAnimation("recover", 0.08f);
                }
            }
            else if (string.Equals(action.type, "kickoff", StringComparison.OrdinalIgnoreCase) ||
                     string.Equals(action.type, "setPiece", StringComparison.OrdinalIgnoreCase))
            {
                if (primaryPlayer != null)
                {
                    primaryPlayer.PlayAnimation("pass", 0.08f);
                }
            }
        }

        private void TriggerEvent(MatchEventDto matchEvent)
        {
            if (matchEvent == null || string.IsNullOrWhiteSpace(matchEvent.id))
            {
                return;
            }

            if (string.Equals(_lastEventId, matchEvent.id, StringComparison.Ordinal))
            {
                return;
            }

            _lastEventId = matchEvent.id;
            HandleEvent(matchEvent);
        }

        private void MarkReplayHighlight(MatchSceneSyncPayload payload)
        {
            if (payload == null || payload.matchEvent == null || replayRecorder == null)
            {
                return;
            }

            string eventId = payload.matchEvent.id;
            if (!string.IsNullOrWhiteSpace(eventId) &&
                string.Equals(_lastMarkedReplayEventId, eventId, StringComparison.Ordinal))
            {
                return;
            }

            if (string.Equals(payload.matchEvent.type, "goal", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(payload.matchEvent.type, "save", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(payload.matchEvent.type, "miss", StringComparison.OrdinalIgnoreCase))
            {
                replayRecorder.MarkHighlightFromPayload(payload);
                _lastMarkedReplayEventId = eventId;
            }
        }

        private PlayerController ResolveEntity(string entityId)
        {
            if (string.IsNullOrWhiteSpace(entityId))
            {
                return null;
            }

            PlayerController player;
            if (players.TryGetValue(entityId, out player))
            {
                return player;
            }

            return null;
        }

        private PlayerController ResolvePlayerById(string playerId)
        {
            if (string.IsNullOrWhiteSpace(playerId))
            {
                return null;
            }

            return ResolveEntity("player:" + playerId);
        }

        private Transform ResolveTransform(string entityId)
        {
            if (string.Equals(entityId, "ball", StringComparison.OrdinalIgnoreCase) && ball != null)
            {
                return ball.transform;
            }

            PlayerController player = ResolveEntity(entityId);
            return player != null ? player.transform : null;
        }

        private static string BuildActionKey(MatchSceneSyncPayload payload)
        {
            string sequence = string.IsNullOrWhiteSpace(payload.sequenceId) ? payload.frameId : payload.sequenceId;
            string actionType = payload.action != null ? payload.action.type : "neutral";
            string primary = payload.action != null ? payload.action.primaryEntityId : null;
            return sequence + "|" + actionType + "|" + primary;
        }
    }
}
