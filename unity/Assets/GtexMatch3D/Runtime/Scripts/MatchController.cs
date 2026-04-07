using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;

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
        [SerializeField] private MatchOverlayController overlayController;
        [SerializeField] private ReplayRecorder replayRecorder;
        [SerializeField] private ReplayPlayer replayPlayer;
        [SerializeField] private bool autoCreatePlayers = true;
        [SerializeField] private bool autoPlayGoalReplays = true;
        [SerializeField] private float autoReplayPlaybackSpeed = 0.55f;
        [SerializeField] private bool snapFirstFrame = true;
        [SerializeField] private bool enableLiveFeedPlayback = true;
        [SerializeField] private string backendBaseUrl = "http://localhost:8000";
        [SerializeField] private string liveFeedPathTemplate = "/matches/{0}/live";
        [SerializeField] private string fallbackLiveFeedPathTemplate = "/api/match-engine/live-feed/{0}";
        [SerializeField] private string matchId = "match-001";
        [SerializeField] private float liveFeedPollIntervalSeconds = 5f;
        [SerializeField] private float liveEventPlaybackSeconds = 1.35f;
        [SerializeField] private int maxInitialQueuedEvents = 10;
        [SerializeField] private bool initializeStandardPlayersForLiveFeed = true;

        private bool _hasSceneSync;
        private bool _replayMode;
        private string _activeMatchId;
        private string _lastFrameId;
        private string _lastActionKey;
        private string _lastEventId;
        private string _lastMarkedReplayEventId;
        private readonly Queue<MatchLiveFeedEventDto> _pendingLiveEvents = new Queue<MatchLiveFeedEventDto>();
        private readonly HashSet<string> _seenLiveEventIds = new HashSet<string>(StringComparer.Ordinal);
        private readonly List<SimulatedPlayerSlot> _homeSlots = new List<SimulatedPlayerSlot>();
        private readonly List<SimulatedPlayerSlot> _awaySlots = new List<SimulatedPlayerSlot>();
        private readonly Dictionary<string, SimulatedPlayerSlot> _homeSlotsByName =
            new Dictionary<string, SimulatedPlayerSlot>(StringComparer.OrdinalIgnoreCase);
        private readonly Dictionary<string, SimulatedPlayerSlot> _awaySlotsByName =
            new Dictionary<string, SimulatedPlayerSlot>(StringComparer.OrdinalIgnoreCase);
        private Coroutine _liveFeedRoutine;
        private string _homeTeamName = "Home";
        private string _awayTeamName = "Away";
        private string _homeTeamId = "home";
        private string _awayTeamId = "away";
        private bool _liveSimulationInitialized;
        private bool _seededInitialLiveEvents;

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

            if (overlayController == null)
            {
                overlayController = GetComponentInChildren<MatchOverlayController>(true);
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

        private void Start()
        {
            if (enableLiveFeedPlayback)
            {
                EnsureLiveSimulationSetup();
                if (_liveFeedRoutine == null)
                {
                    _liveFeedRoutine = StartCoroutine(LiveFeedLoop());
                }
            }
        }

        private void OnDisable()
        {
            if (_liveFeedRoutine != null)
            {
                StopCoroutine(_liveFeedRoutine);
                _liveFeedRoutine = null;
            }
        }

        public void ConfigureScene(
            PitchController pitchController,
            BallController ballController,
            CameraController cameraRig,
            Transform playerContainer,
            PlayerController playerTemplate,
            MatchOverlayController overlay,
            ReplayRecorder recorder,
            ReplayPlayer player)
        {
            pitch = pitchController;
            ball = ballController;
            cameraController = cameraRig;
            playersRoot = playerContainer;
            playerPrefab = playerTemplate;
            overlayController = overlay;
            replayRecorder = recorder;
            replayPlayer = player;

            if (replayPlayer != null)
            {
                replayPlayer.SetMatchController(this);
            }

            if (cameraController != null && ball != null && pitch != null && enableLiveFeedPlayback)
            {
                cameraController.EnableLiveBallFollow(ball.transform, pitch, true);
            }
        }

        public void SetReplayMode(bool enabled)
        {
            _replayMode = enabled;
        }

        public void SetLiveFeedPlaybackEnabled(bool enabled)
        {
            enableLiveFeedPlayback = enabled;
            if (!enabled)
            {
                if (_liveFeedRoutine != null)
                {
                    StopCoroutine(_liveFeedRoutine);
                    _liveFeedRoutine = null;
                }
                return;
            }

            if (_liveFeedRoutine == null && isActiveAndEnabled)
            {
                EnsureLiveSimulationSetup();
                _liveFeedRoutine = StartCoroutine(LiveFeedLoop());
            }
        }

        public void SetActiveMatch(string matchId)
        {
            _activeMatchId = string.IsNullOrWhiteSpace(matchId) ? null : matchId.Trim();
        }

        public void ApplySceneSync(MatchSceneSyncPayload payload)
        {
            if (payload == null || !payload.IsSceneSync())
            {
                return;
            }

            if (!string.IsNullOrWhiteSpace(_activeMatchId) &&
                !string.IsNullOrWhiteSpace(payload.matchId) &&
                !string.Equals(_activeMatchId, payload.matchId, StringComparison.Ordinal))
            {
                return;
            }

            if (string.IsNullOrWhiteSpace(_activeMatchId) &&
                !string.IsNullOrWhiteSpace(payload.matchId))
            {
                _activeMatchId = payload.matchId;
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
            if (ball != null)
            {
                ball.gameObject.SetActive(ballNode != null);
                if (ballNode != null)
                {
                    bool treatAsShot = payload.action != null &&
                                       (string.Equals(payload.action.type, "shot", StringComparison.OrdinalIgnoreCase) ||
                                        string.Equals(payload.action.type, "goal", StringComparison.OrdinalIgnoreCase) ||
                                        string.Equals(payload.action.type, "save", StringComparison.OrdinalIgnoreCase) ||
                                        string.Equals(payload.action.type, "miss", StringComparison.OrdinalIgnoreCase));
                    ball.ApplySceneNode(ballNode, immediate, treatAsShot);
                }
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

            UpdateOverlayFromSceneSync(payload);
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

            UpdateOverlayFromMatchEvent(matchEvent);

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

        public void ClearScene()
        {
            _hasSceneSync = false;
            _replayMode = false;
            _activeMatchId = null;
            _lastFrameId = null;
            _lastActionKey = null;
            _lastEventId = null;
            _lastMarkedReplayEventId = null;

            if (replayPlayer != null && replayPlayer.IsPlaying)
            {
                replayPlayer.Stop();
            }

            foreach (KeyValuePair<string, PlayerController> entry in players)
            {
                if (entry.Value != null)
                {
                    entry.Value.gameObject.SetActive(false);
                }
            }

            if (ball != null)
            {
                ball.gameObject.SetActive(false);
            }

            if (overlayController != null)
            {
                overlayController.ResetOverlay();
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
                ball.gameObject.SetActive(true);
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

        private void UpdateOverlayFromSceneSync(MatchSceneSyncPayload payload)
        {
            if (overlayController == null || payload == null)
            {
                return;
            }

            overlayController.UpdateScore(payload.homeScore, payload.awayScore);
            overlayController.UpdateClock(payload.clockMinute);
            overlayController.SetPhase(payload.phase);
        }

        private void UpdateOverlayFromMatchEvent(MatchEventDto matchEvent)
        {
            if (overlayController == null || matchEvent == null)
            {
                return;
            }

            overlayController.UpdateScore(matchEvent.homeScore, matchEvent.awayScore);
            overlayController.UpdateClock(matchEvent.minute);
            overlayController.PushEvent(FormatSceneEventFeed(matchEvent));

            if (string.Equals(matchEvent.type, "goal", StringComparison.OrdinalIgnoreCase))
            {
                overlayController.ShowHeadline(
                    string.IsNullOrWhiteSpace(matchEvent.bannerText)
                        ? (matchEvent.primaryPlayerName + " scores!")
                        : matchEvent.bannerText,
                    2.6f);
            }
        }

        private IEnumerator LiveFeedLoop()
        {
            while (isActiveAndEnabled)
            {
                MatchLiveFeedDto liveFeed = null;
                yield return FetchLiveFeedFromConfiguredUrls(delegate(MatchLiveFeedDto payload)
                {
                    liveFeed = payload;
                });

                if (liveFeed != null)
                {
                    ApplyLiveFeedSnapshot(liveFeed);

                    while (_pendingLiveEvents.Count > 0)
                    {
                        yield return PlayLiveEvent(_pendingLiveEvents.Dequeue());
                    }
                }
                else
                {
                    EnsureLiveSimulationSetup();
                    ApplyNeutralLiveShape(string.Empty, true);
                }

                yield return new WaitForSeconds(Mathf.Max(1f, liveFeedPollIntervalSeconds));
            }
        }

        private IEnumerator FetchLiveFeedFromConfiguredUrls(Action<MatchLiveFeedDto> onComplete)
        {
            MatchLiveFeedDto payload = null;
            string primaryUrl = BuildLiveFeedUrl(liveFeedPathTemplate);
            if (!string.IsNullOrWhiteSpace(primaryUrl))
            {
                yield return FetchLiveFeed(primaryUrl, delegate(MatchLiveFeedDto result)
                {
                    payload = result;
                });
            }

            if (payload == null)
            {
                string fallbackUrl = BuildLiveFeedUrl(fallbackLiveFeedPathTemplate);
                if (!string.IsNullOrWhiteSpace(fallbackUrl) &&
                    !string.Equals(primaryUrl, fallbackUrl, StringComparison.OrdinalIgnoreCase))
                {
                    yield return FetchLiveFeed(fallbackUrl, delegate(MatchLiveFeedDto result)
                    {
                        payload = result;
                    });
                }
            }

            if (onComplete != null)
            {
                onComplete(payload);
            }
        }

        private IEnumerator FetchLiveFeed(string url, Action<MatchLiveFeedDto> onComplete)
        {
            using (UnityWebRequest request = UnityWebRequest.Get(url))
            {
                request.downloadHandler = new DownloadHandlerBuffer();
                yield return request.SendWebRequest();

                if (!IsRequestSuccessful(request))
                {
                    if (!string.IsNullOrWhiteSpace(request.error))
                    {
                        Debug.LogWarning("Live feed request failed: " + request.error + " (" + url + ")");
                    }

                    if (onComplete != null)
                    {
                        onComplete(null);
                    }
                    yield break;
                }

                MatchLiveFeedDto payload =
                    MatchRuntimeJson.DeserializeLiveFeed(request.downloadHandler.text);
                if (onComplete != null)
                {
                    onComplete(payload);
                }
            }
        }

        private void ApplyLiveFeedSnapshot(MatchLiveFeedDto liveFeed)
        {
            if (liveFeed == null)
            {
                return;
            }

            UpdateResolvedTeamIds(liveFeed);
            EnsureLiveSimulationSetup();

            if (!_seededInitialLiveEvents)
            {
                SeedInitialLiveEvents(liveFeed.timeline_events);
                _seededInitialLiveEvents = true;
            }
            else
            {
                QueueNewLiveEvents(liveFeed.timeline_events);
            }

            if (_pendingLiveEvents.Count == 0)
            {
                if (overlayController != null)
                {
                    overlayController.ConfigureTeams(_homeTeamName, _awayTeamName);
                    overlayController.UpdateScore(liveFeed.home_score, liveFeed.away_score);
                    overlayController.UpdateClock(liveFeed.minute);
                    overlayController.SetPhase(liveFeed.phase);
                }

                ApplyNeutralLiveShape(string.Empty, false);
            }
        }

        private void EnsureLiveSimulationSetup()
        {
            if (pitch == null || ball == null || cameraController == null)
            {
                return;
            }

            if (initializeStandardPlayersForLiveFeed)
            {
                EnsureSlotsForSide(_homeSlots, _homeSlotsByName, "home", _homeTeamId, _homeTeamName);
                EnsureSlotsForSide(_awaySlots, _awaySlotsByName, "away", _awayTeamId, _awayTeamName);
                if (!_liveSimulationInitialized)
                {
                    ApplyNeutralLiveShape(string.Empty, true);
                    ball.gameObject.SetActive(true);
                    ball.ApplySimulationPose(pitch.ToWorldPosition(50f, 50f, 0.12f), Vector3.zero, 0f, true);
                }
            }

            cameraController.EnableLiveBallFollow(ball.transform, pitch, !_liveSimulationInitialized);

            if (overlayController != null)
            {
                overlayController.ConfigureTeams(_homeTeamName, _awayTeamName);
            }

            _liveSimulationInitialized = true;
        }

        private void EnsureSlotsForSide(
            List<SimulatedPlayerSlot> slots,
            Dictionary<string, SimulatedPlayerSlot> slotsByName,
            string side,
            string teamId,
            string teamName)
        {
            Vector2[] anchors = BuildAnchorsForSide(side);
            if (slots.Count == 0)
            {
                for (int index = 0; index < anchors.Length; index += 1)
                {
                    int shirtNumber = index + 1;
                    string entityId = "player:" + side + ":" + shirtNumber.ToString("00");
                    PlayerController controller = GetOrCreatePlayer(entityId);
                    if (controller == null)
                    {
                        continue;
                    }

                    SimulatedPlayerSlot slot = new SimulatedPlayerSlot();
                    slot.EntityId = entityId;
                    slot.Side = side;
                    slot.TeamId = teamId;
                    slot.TeamName = teamName;
                    slot.ShirtNumber = shirtNumber;
                    slot.AnchorNormalized = anchors[index];
                    slot.CurrentNormalized = anchors[index];
                    slot.Controller = controller;
                    slots.Add(slot);
                }
            }

            slotsByName.Clear();
            for (int index = 0; index < slots.Count; index += 1)
            {
                SimulatedPlayerSlot slot = slots[index];
                slot.TeamId = teamId;
                slot.TeamName = teamName;
                if (!string.IsNullOrWhiteSpace(slot.PlayerName))
                {
                    slotsByName[slot.PlayerName.Trim()] = slot;
                }
            }
        }

        private void SeedInitialLiveEvents(MatchLiveFeedEventDto[] events)
        {
            int eventCount = events != null ? events.Length : 0;
            int startIndex = Mathf.Max(0, eventCount - Mathf.Max(0, maxInitialQueuedEvents));
            int baselineHomeScore = 0;
            int baselineAwayScore = 0;
            int baselineMinute = 0;

            for (int index = 0; index < eventCount; index += 1)
            {
                MatchLiveFeedEventDto liveEvent = events[index];
                if (liveEvent == null)
                {
                    continue;
                }

                string key = BuildLiveEventKey(liveEvent);
                if (index < startIndex)
                {
                    _seenLiveEventIds.Add(key);
                    baselineHomeScore = liveEvent.home_score;
                    baselineAwayScore = liveEvent.away_score;
                    baselineMinute = liveEvent.minute;
                    continue;
                }

                QueueLiveEvent(liveEvent);
            }

            if (overlayController != null)
            {
                overlayController.ConfigureTeams(_homeTeamName, _awayTeamName);
                overlayController.UpdateScore(baselineHomeScore, baselineAwayScore);
                overlayController.UpdateClock(baselineMinute);
                overlayController.SetPhase("live");
            }
        }

        private void QueueNewLiveEvents(MatchLiveFeedEventDto[] events)
        {
            if (events == null)
            {
                return;
            }

            for (int index = 0; index < events.Length; index += 1)
            {
                QueueLiveEvent(events[index]);
            }
        }

        private void QueueLiveEvent(MatchLiveFeedEventDto liveEvent)
        {
            if (liveEvent == null)
            {
                return;
            }

            string key = BuildLiveEventKey(liveEvent);
            if (_seenLiveEventIds.Contains(key))
            {
                return;
            }

            _seenLiveEventIds.Add(key);
            _pendingLiveEvents.Enqueue(liveEvent);
        }

        private IEnumerator PlayLiveEvent(MatchLiveFeedEventDto liveEvent)
        {
            if (liveEvent == null || pitch == null || ball == null || cameraController == null)
            {
                yield break;
            }

            EnsureLiveSimulationSetup();

            string attackingSide = ResolveSide(liveEvent.team_id, liveEvent.team_name);
            LiveEventKind eventKind = ResolveLiveEventKind(liveEvent.event_type);
            SimulatedPlayerSlot primary = ResolveLivePlayerSlot(attackingSide, liveEvent.player_name);
            SimulatedPlayerSlot secondary = ResolveLiveSecondaryPlayerSlot(attackingSide, liveEvent.secondary_player_name, primary);

            ApplyLiveEventShape(attackingSide, eventKind, primary, secondary, liveEvent, false);
            UpdateOverlayFromLiveEvent(liveEvent, eventKind);

            float preRoll = 0.12f;
            float trailingHold = Mathf.Max(0.5f, liveEventPlaybackSeconds - preRoll);
            Vector3 primaryBallPosition = primary != null
                ? pitch.ToWorldPosition(primary.CurrentNormalized.x, primary.CurrentNormalized.y, 0.12f)
                : pitch.ToWorldPosition(50f, 50f, 0.12f);

            ball.gameObject.SetActive(true);
            ball.ApplySimulationPose(primaryBallPosition, Vector3.zero, 0f, true);

            if (eventKind == LiveEventKind.Pass && primary != null)
            {
                if (secondary == null)
                {
                    secondary = FindAdvanceRunner(attackingSide, primary);
                }

                primary.PlayAnimation("pass", 0.08f);
                if (secondary != null)
                {
                    secondary.PlayAnimation("receive", 0.08f);
                }

                yield return new WaitForSeconds(preRoll);

                Vector3 target = secondary != null
                    ? pitch.ToWorldPosition(secondary.CurrentNormalized.x, secondary.CurrentNormalized.y, 0.12f)
                    : pitch.ToWorldPosition(60f, 50f, 0.12f);
                ball.MoveTo(target, (target - primaryBallPosition) / Mathf.Max(0.1f, trailingHold), 0.22f);
                cameraController.FocusBall();
                yield return new WaitForSeconds(trailingHold);
            }
            else if ((eventKind == LiveEventKind.Shot || eventKind == LiveEventKind.Goal) && primary != null)
            {
                primary.PlayAnimation("shoot", 0.08f);
                SimulatedPlayerSlot goalkeeper = FindGoalkeeper(attackingSide);
                if (goalkeeper != null)
                {
                    goalkeeper.PlayAnimation("intercept", 0.08f);
                }

                yield return new WaitForSeconds(preRoll);

                Vector2 goalPoint = BuildGoalTarget(attackingSide);
                Vector3 goalWorld = pitch.ToWorldPosition(
                    goalPoint.x,
                    goalPoint.y,
                    eventKind == LiveEventKind.Goal ? 0.45f : 0.28f);
                ball.MoveTo(goalWorld, (goalWorld - primaryBallPosition) / Mathf.Max(0.1f, trailingHold), 0.8f);
                cameraController.FocusBall();

                yield return new WaitForSeconds(Mathf.Min(0.55f, trailingHold));

                if (eventKind == LiveEventKind.Goal)
                {
                    primary.PlayAnimation("celebrate", 0.08f);
                    cameraController.FocusTransform(primary.transform);
                }

                yield return new WaitForSeconds(Mathf.Max(0.1f, trailingHold - 0.55f));
                cameraController.FocusBall();
            }
            else
            {
                yield return new WaitForSeconds(Mathf.Max(0.75f, liveEventPlaybackSeconds));
            }
        }

        private void ApplyNeutralLiveShape(string attackingSide, bool immediate)
        {
            ApplyLiveEventShape(attackingSide, LiveEventKind.Neutral, null, null, null, immediate);
        }

        private void ApplyLiveEventShape(
            string attackingSide,
            LiveEventKind eventKind,
            SimulatedPlayerSlot primary,
            SimulatedPlayerSlot secondary,
            MatchLiveFeedEventDto liveEvent,
            bool immediate)
        {
            ApplyBaseShapeForTeam(_homeSlots, attackingSide, immediate);
            ApplyBaseShapeForTeam(_awaySlots, attackingSide, immediate);

            if (primary != null)
            {
                Vector2 primaryTarget = BuildPrimaryTarget(attackingSide, eventKind, BuildLiveEventKey(liveEvent));
                Vector2 primaryFacing = secondary != null
                    ? secondary.CurrentNormalized
                    : BuildGoalTarget(attackingSide);
                ApplySlotPose(
                    primary,
                    primaryTarget,
                    primaryFacing,
                    eventKind == LiveEventKind.Goal || eventKind == LiveEventKind.Shot ? 0.92f : 0.75f,
                    true,
                    true,
                    immediate);
            }

            if (secondary != null)
            {
                Vector2 secondaryTarget = BuildSecondaryTarget(attackingSide, eventKind, BuildLiveEventKey(liveEvent));
                ApplySlotPose(
                    secondary,
                    secondaryTarget,
                    primary != null ? primary.CurrentNormalized : secondaryTarget,
                    0.68f,
                    true,
                    eventKind == LiveEventKind.Pass,
                    immediate);
            }

            SimulatedPlayerSlot goalkeeper = FindGoalkeeper(attackingSide);
            if (goalkeeper != null && (eventKind == LiveEventKind.Shot || eventKind == LiveEventKind.Goal))
            {
                Vector2 keeperTarget = goalkeeper.Side == "home"
                    ? new Vector2(6f, 50f)
                    : new Vector2(94f, 50f);
                ApplySlotPose(goalkeeper, keeperTarget, primary != null ? primary.CurrentNormalized : keeperTarget, 0.42f, true, false, immediate);
            }
        }

        private void ApplyBaseShapeForTeam(List<SimulatedPlayerSlot> slots, string attackingSide, bool immediate)
        {
            for (int index = 0; index < slots.Count; index += 1)
            {
                SimulatedPlayerSlot slot = slots[index];
                Vector2 target = slot.AnchorNormalized;
                if (!string.IsNullOrWhiteSpace(attackingSide))
                {
                    if (string.Equals(slot.Side, attackingSide, StringComparison.OrdinalIgnoreCase))
                    {
                        target.x += string.Equals(slot.Side, "home", StringComparison.OrdinalIgnoreCase) ? 8f : -8f;
                    }
                    else
                    {
                        target.x += string.Equals(slot.Side, "home", StringComparison.OrdinalIgnoreCase) ? -4f : 4f;
                    }
                }

                target = ClampNormalized(target);
                ApplySlotPose(slot, target, slot.Side == "home" ? new Vector2(100f, target.y) : new Vector2(0f, target.y), 0.18f, false, false, immediate);
            }
        }

        private void ApplySlotPose(
            SimulatedPlayerSlot slot,
            Vector2 targetNormalized,
            Vector2 facingNormalized,
            float speedRatio,
            bool highlighted,
            bool hasPossession,
            bool immediate)
        {
            if (slot == null || slot.Controller == null || pitch == null)
            {
                return;
            }

            Vector3 worldPosition = pitch.ToWorldPosition(targetNormalized.x, targetNormalized.y, 0.9f);
            Vector3 facingPoint = pitch.ToWorldPosition(facingNormalized.x, facingNormalized.y, 0.9f);
            Vector3 direction = facingPoint - worldPosition;
            if (direction.sqrMagnitude <= 0.0001f)
            {
                direction = string.Equals(slot.Side, "home", StringComparison.OrdinalIgnoreCase)
                    ? Vector3.right
                    : Vector3.left;
            }

            slot.Controller.ApplySimulationPose(
                slot.EntityId,
                slot.TeamId,
                slot.Side,
                slot.DisplayLabel,
                slot.ShirtNumber,
                worldPosition,
                Quaternion.LookRotation(direction.normalized, Vector3.up),
                speedRatio,
                highlighted,
                hasPossession,
                immediate);

            slot.CurrentNormalized = targetNormalized;
        }

        private SimulatedPlayerSlot ResolveLivePlayerSlot(string side, string playerName)
        {
            if (!string.Equals(side, "away", StringComparison.OrdinalIgnoreCase))
            {
                side = "home";
            }

            Dictionary<string, SimulatedPlayerSlot> lookup = string.Equals(side, "away", StringComparison.OrdinalIgnoreCase)
                ? _awaySlotsByName
                : _homeSlotsByName;
            List<SimulatedPlayerSlot> slots = string.Equals(side, "away", StringComparison.OrdinalIgnoreCase)
                ? _awaySlots
                : _homeSlots;

            if (!string.IsNullOrWhiteSpace(playerName))
            {
                string normalizedName = playerName.Trim();
                SimulatedPlayerSlot existing;
                if (lookup.TryGetValue(normalizedName, out existing))
                {
                    return existing;
                }

                int[] priority = new[] { 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0 };
                for (int index = 0; index < priority.Length; index += 1)
                {
                    int slotIndex = priority[index];
                    if (slotIndex < 0 || slotIndex >= slots.Count)
                    {
                        continue;
                    }

                    SimulatedPlayerSlot candidate = slots[slotIndex];
                    if (string.IsNullOrWhiteSpace(candidate.PlayerName))
                    {
                        candidate.PlayerName = normalizedName;
                        lookup[normalizedName] = candidate;
                        return candidate;
                    }
                }
            }

            return slots.Count > 0 ? slots[Mathf.Clamp(slots.Count - 2, 0, slots.Count - 1)] : null;
        }

        private SimulatedPlayerSlot ResolveLiveSecondaryPlayerSlot(string side, string playerName, SimulatedPlayerSlot primary)
        {
            if (!string.IsNullOrWhiteSpace(playerName))
            {
                SimulatedPlayerSlot resolved = ResolveLivePlayerSlot(side, playerName);
                if (resolved != primary)
                {
                    return resolved;
                }
            }

            return FindAdvanceRunner(side, primary);
        }

        private SimulatedPlayerSlot FindAdvanceRunner(string side, SimulatedPlayerSlot exclude)
        {
            List<SimulatedPlayerSlot> slots = string.Equals(side, "away", StringComparison.OrdinalIgnoreCase)
                ? _awaySlots
                : _homeSlots;
            for (int index = slots.Count - 1; index >= 0; index -= 1)
            {
                SimulatedPlayerSlot candidate = slots[index];
                if (candidate != exclude)
                {
                    return candidate;
                }
            }

            return null;
        }

        private SimulatedPlayerSlot FindGoalkeeper(string attackingSide)
        {
            List<SimulatedPlayerSlot> defendingSlots =
                string.Equals(attackingSide, "away", StringComparison.OrdinalIgnoreCase)
                    ? _homeSlots
                    : _awaySlots;
            return defendingSlots.Count > 0 ? defendingSlots[0] : null;
        }

        private void UpdateResolvedTeamIds(MatchLiveFeedDto liveFeed)
        {
            if (liveFeed == null)
            {
                return;
            }

            if (!string.IsNullOrWhiteSpace(liveFeed.home_team_name))
            {
                _homeTeamName = liveFeed.home_team_name.Trim();
            }

            if (!string.IsNullOrWhiteSpace(liveFeed.away_team_name))
            {
                _awayTeamName = liveFeed.away_team_name.Trim();
            }

            MatchLiveFeedEventDto[] events = liveFeed.timeline_events;
            if (events == null)
            {
                return;
            }

            for (int index = 0; index < events.Length; index += 1)
            {
                MatchLiveFeedEventDto liveEvent = events[index];
                if (liveEvent == null || string.IsNullOrWhiteSpace(liveEvent.team_id))
                {
                    continue;
                }

                if (string.Equals(liveEvent.team_name, _homeTeamName, StringComparison.OrdinalIgnoreCase))
                {
                    _homeTeamId = liveEvent.team_id;
                }
                else if (string.Equals(liveEvent.team_name, _awayTeamName, StringComparison.OrdinalIgnoreCase))
                {
                    _awayTeamId = liveEvent.team_id;
                }
            }
        }

        private void UpdateOverlayFromLiveEvent(MatchLiveFeedEventDto liveEvent, LiveEventKind eventKind)
        {
            if (overlayController == null || liveEvent == null)
            {
                return;
            }

            overlayController.ConfigureTeams(_homeTeamName, _awayTeamName);
            overlayController.UpdateScore(liveEvent.home_score, liveEvent.away_score);
            overlayController.UpdateClock(liveEvent.minute);
            overlayController.SetPhase("live");
            overlayController.PushEvent(FormatLiveEventFeed(liveEvent));

            if (eventKind == LiveEventKind.Goal)
            {
                overlayController.ShowHeadline(BuildLiveHeadline(liveEvent, "scores"), 2.8f);
            }
            else if (eventKind == LiveEventKind.Shot)
            {
                overlayController.ShowHeadline(BuildLiveHeadline(liveEvent, "shoots"), 1.5f);
            }
        }

        private string ResolveSide(string teamId, string teamName)
        {
            if (!string.IsNullOrWhiteSpace(teamId))
            {
                if (string.Equals(teamId, _awayTeamId, StringComparison.OrdinalIgnoreCase))
                {
                    return "away";
                }

                if (string.Equals(teamId, _homeTeamId, StringComparison.OrdinalIgnoreCase))
                {
                    return "home";
                }
            }

            if (!string.IsNullOrWhiteSpace(teamName))
            {
                if (string.Equals(teamName, _awayTeamName, StringComparison.OrdinalIgnoreCase))
                {
                    return "away";
                }

                if (string.Equals(teamName, _homeTeamName, StringComparison.OrdinalIgnoreCase))
                {
                    return "home";
                }
            }

            return "home";
        }

        private static LiveEventKind ResolveLiveEventKind(string eventType)
        {
            string normalized = string.IsNullOrWhiteSpace(eventType)
                ? string.Empty
                : eventType.Trim().ToLowerInvariant();
            if (normalized.Contains("goal"))
            {
                return LiveEventKind.Goal;
            }

            if (normalized.Contains("assist") || normalized.Contains("pass"))
            {
                return LiveEventKind.Pass;
            }

            if (normalized.Contains("shot") ||
                normalized.Contains("chance") ||
                normalized.Contains("penalt") ||
                normalized.Contains("save") ||
                normalized.Contains("woodwork"))
            {
                return LiveEventKind.Shot;
            }

            return LiveEventKind.Neutral;
        }

        private string BuildLiveHeadline(MatchLiveFeedEventDto liveEvent, string fallbackVerb)
        {
            string playerName = string.IsNullOrWhiteSpace(liveEvent.player_name)
                ? "A player"
                : liveEvent.player_name.Trim();
            string teamName = string.IsNullOrWhiteSpace(liveEvent.team_name)
                ? (ResolveSide(liveEvent.team_id, liveEvent.team_name) == "away" ? _awayTeamName : _homeTeamName)
                : liveEvent.team_name.Trim();
            return playerName + " " + fallbackVerb + " for " + teamName;
        }

        private static string FormatLiveEventFeed(MatchLiveFeedEventDto liveEvent)
        {
            string minuteLabel = liveEvent.minute.ToString() + "'";
            string teamName = string.IsNullOrWhiteSpace(liveEvent.team_name) ? "Team" : liveEvent.team_name.Trim();
            string playerName = string.IsNullOrWhiteSpace(liveEvent.player_name) ? HumanizeEventType(liveEvent.event_type) : liveEvent.player_name.Trim();
            if (string.IsNullOrWhiteSpace(liveEvent.description))
            {
                return minuteLabel + "  " + teamName + " - " + playerName;
            }

            return minuteLabel + "  " + teamName + " - " + playerName + ": " + liveEvent.description.Trim();
        }

        private static string FormatSceneEventFeed(MatchEventDto matchEvent)
        {
            string minuteLabel = matchEvent.minute.ToString() + "'";
            string descriptor = string.IsNullOrWhiteSpace(matchEvent.commentary)
                ? matchEvent.bannerText
                : matchEvent.commentary;
            if (string.IsNullOrWhiteSpace(descriptor))
            {
                descriptor = HumanizeEventType(matchEvent.type);
            }

            return minuteLabel + "  " + descriptor;
        }

        private static string HumanizeEventType(string eventType)
        {
            if (string.IsNullOrWhiteSpace(eventType))
            {
                return "Match event";
            }

            string normalized = eventType.Replace('_', ' ').Trim();
            if (normalized.Length == 0)
            {
                return "Match event";
            }

            return char.ToUpperInvariant(normalized[0]) + normalized.Substring(1).ToLowerInvariant();
        }

        private string BuildLiveFeedUrl(string pathTemplate)
        {
            if (string.IsNullOrWhiteSpace(pathTemplate) || string.IsNullOrWhiteSpace(matchId))
            {
                return null;
            }

            if (string.IsNullOrWhiteSpace(backendBaseUrl))
            {
                return null;
            }

            string baseUrl = backendBaseUrl.Trim().TrimEnd('/');
            string relativePath = string.Format(pathTemplate.Trim(), matchId).Trim();
            if (!relativePath.StartsWith("/", StringComparison.Ordinal))
            {
                relativePath = "/" + relativePath;
            }

            return baseUrl + relativePath;
        }

        private static bool IsRequestSuccessful(UnityWebRequest request)
        {
            return request != null && request.result == UnityWebRequest.Result.Success;
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

        private static Vector2[] BuildAnchorsForSide(string side)
        {
            if (string.Equals(side, "away", StringComparison.OrdinalIgnoreCase))
            {
                return new[]
                {
                    new Vector2(92f, 50f),
                    new Vector2(80f, 18f),
                    new Vector2(80f, 38f),
                    new Vector2(80f, 62f),
                    new Vector2(80f, 82f),
                    new Vector2(62f, 24f),
                    new Vector2(62f, 50f),
                    new Vector2(62f, 76f),
                    new Vector2(42f, 18f),
                    new Vector2(42f, 50f),
                    new Vector2(42f, 82f),
                };
            }

            return new[]
            {
                new Vector2(8f, 50f),
                new Vector2(20f, 18f),
                new Vector2(20f, 38f),
                new Vector2(20f, 62f),
                new Vector2(20f, 82f),
                new Vector2(38f, 24f),
                new Vector2(38f, 50f),
                new Vector2(38f, 76f),
                new Vector2(58f, 18f),
                new Vector2(58f, 50f),
                new Vector2(58f, 82f),
            };
        }

        private static Vector2 BuildGoalTarget(string attackingSide)
        {
            return string.Equals(attackingSide, "away", StringComparison.OrdinalIgnoreCase)
                ? new Vector2(2f, 50f)
                : new Vector2(98f, 50f);
        }

        private static Vector2 BuildPrimaryTarget(string side, LiveEventKind eventKind, string seed)
        {
            float lane = SeededRange(seed + ":primary", -18f, 18f);
            if (eventKind == LiveEventKind.Pass)
            {
                return ClampNormalized(new Vector2(
                    string.Equals(side, "away", StringComparison.OrdinalIgnoreCase) ? 44f : 56f,
                    50f + lane));
            }

            if (eventKind == LiveEventKind.Goal || eventKind == LiveEventKind.Shot)
            {
                return ClampNormalized(new Vector2(
                    string.Equals(side, "away", StringComparison.OrdinalIgnoreCase) ? 20f : 80f,
                    50f + (lane * 0.55f)));
            }

            return ClampNormalized(new Vector2(
                string.Equals(side, "away", StringComparison.OrdinalIgnoreCase) ? 34f : 66f,
                50f + lane));
        }

        private static Vector2 BuildSecondaryTarget(string side, LiveEventKind eventKind, string seed)
        {
            float lane = SeededRange(seed + ":secondary", -22f, 22f);
            if (eventKind == LiveEventKind.Pass)
            {
                return ClampNormalized(new Vector2(
                    string.Equals(side, "away", StringComparison.OrdinalIgnoreCase) ? 26f : 74f,
                    50f + lane));
            }

            return ClampNormalized(new Vector2(
                string.Equals(side, "away", StringComparison.OrdinalIgnoreCase) ? 12f : 88f,
                50f + (lane * 0.35f)));
        }

        private static Vector2 ClampNormalized(Vector2 value)
        {
            return new Vector2(
                Mathf.Clamp(value.x, 0f, 100f),
                Mathf.Clamp(value.y, 6f, 94f));
        }

        private static string BuildLiveEventKey(MatchLiveFeedEventDto liveEvent)
        {
            if (liveEvent == null)
            {
                return string.Empty;
            }

            if (!string.IsNullOrWhiteSpace(liveEvent.event_id))
            {
                return liveEvent.event_id;
            }

            return liveEvent.minute + "|" +
                   liveEvent.event_type + "|" +
                   liveEvent.team_name + "|" +
                   liveEvent.player_name + "|" +
                   liveEvent.home_score + "|" +
                   liveEvent.away_score;
        }

        private static float SeededRange(string seed, float minimum, float maximum)
        {
            if (string.IsNullOrEmpty(seed))
            {
                return minimum;
            }

            unchecked
            {
                int hash = 23;
                for (int index = 0; index < seed.Length; index += 1)
                {
                    hash = (hash * 31) + seed[index];
                }

                float t = Mathf.Abs(hash % 1000) / 999f;
                return Mathf.Lerp(minimum, maximum, t);
            }
        }

        private enum LiveEventKind
        {
            Neutral,
            Pass,
            Shot,
            Goal,
        }

        private sealed class SimulatedPlayerSlot
        {
            public string EntityId;
            public string TeamId;
            public string TeamName;
            public string Side;
            public int ShirtNumber;
            public string PlayerName;
            public Vector2 AnchorNormalized;
            public Vector2 CurrentNormalized;
            public PlayerController Controller;

            public string DisplayLabel
            {
                get
                {
                    if (!string.IsNullOrWhiteSpace(PlayerName))
                    {
                        return PlayerName;
                    }

                    string prefix = string.IsNullOrWhiteSpace(TeamName) ? Side : TeamName;
                    return prefix + " " + ShirtNumber.ToString("00");
                }
            }
        }
    }
}
