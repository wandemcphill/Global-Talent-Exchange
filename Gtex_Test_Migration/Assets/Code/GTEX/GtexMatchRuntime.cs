using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Threading.Tasks;
using System.Linq;
using FStudio.Database;
using FStudio.GTEX.Core;
using FStudio.GTEX.Engine;
using FStudio.MatchEngine;
using FStudio.MatchEngine.Balls;
using FStudio.Data;
using FStudio.MatchEngine.Enums;
using FStudio.MatchEngine.Players.PlayerController;
using FStudio.UI.Events;
using FStudio.UI.MatchThemes.MatchEvents;
using Shared.Responses;
using UnityEngine;
using System.Net.WebSockets;
using System.Threading;

namespace FStudio.GTEX
{

        public sealed class GtexMatchRuntime : MonoBehaviour
        {
            private const float SceneDependencyWaitTimeoutSeconds = 10f;
            private const float LiveStateClockRegressionToleranceMinutes = 0.25f;
            private const float LivePlayerSnapDistance = 18f;
            private const float LivePlayerCatchUpSeconds = 0.35f;
            private const float LivePlayerMinSpeedUnitsPerSecond = 3f;
            private const float LivePlayerMaxSpeedUnitsPerSecond = 8f;
            private const float LivePlayerRotationLerpSpeed = 10f;
            private const float LiveAnimatorMoveSpeedScale = 6f;
        private const float LiveStatePredictionMaxSeconds = 0.35f;
        private const float LiveBallPassSpeedUnitsPerSecond = 0.5f;
        private const float LiveBallShotSpeedUnitsPerSecond = 1.25f;
            private const float LiveBehaviorMinRoamDistance = 1f;
            private const float LiveBehaviorMaxRoamDistance = 4.75f;
            private const float LiveBehaviorMinSpeedRatio = 0.2f;
            private const float LiveBehaviorTeammateRepulsionRadius = 2.4f;
            private const float LiveBehaviorBlendOutSpeedUnitsPerSecond = 2.75f;
            private const float LiveBehaviorEventStaleSeconds = 7.5f;
            private const float LiveBehaviorEventStaleClockMinutes = 1.25f;
            private const float LiveBallIntentMinLifetimeSeconds = 6f;
            private const float LiveBallIntentMaxLifetimeSeconds = 14f;
            private const float LiveBallIntentFallbackTravelDistance = 4.25f;
            private const float RuntimeTraceFlushIntervalSeconds = 0.75f;
            private const float RuntimeTraceHeartbeatIntervalSeconds = 5f;
        private const float RuntimeTraceStationaryClockDeltaThresholdMinutes = 0.35f;
        private const int RuntimeTraceMaxBufferedLines = 64;

        private GtexMatchConfig config;
        private MatchAPI api;

        private ClientWebSocket socket;
        private CancellationTokenSource socketToken;

        private MatchResponse currentState;
        private MatchResponse lastKnownState;

        private bool matchLoaded;
        private bool bootstrapTaskFailed;
        private bool usingWebSocket;

        private readonly Dictionary<string, GtexLegacyPlayerHandle> playerBindings = new();
        private readonly Dictionary<string, string> lastAnimationStates = new();
        private string lastAppliedCameraPreset = string.Empty;

        private float stateReceivedAt;
        private bool skipBootstrap;
        private bool isConnectingWebSocket;
        private bool isDestroyed;
        private float nextWebSocketReconnectAt;
        private int webSocketReconnectAttempts;
        private int consecutiveTransportFailures;
        private string lastTransportError = string.Empty;
        private string lastTransportSource = "idle";
        private bool staleStateWarningLogged;
        private bool staleFrameWarningLogged;
        private bool isRefreshingLiveAccess;
        private readonly List<string> runtimeTraceBuffer = new();
        private string runtimeTracePath = string.Empty;
        private float runtimeTraceLastFlushAt = -1f;
        private float runtimeTraceLastHeartbeatAt = -1f;
        private float runtimeTraceLastMotionClockMinute = -1f;
        private string runtimeTraceLastLoggedPhase = string.Empty;
        private string runtimeTraceLastLoggedEventId = string.Empty;
        private string runtimeTraceLastLoggedBallHolderId = string.Empty;
        private int runtimeTraceDrivenPlayerCount;
        private int runtimeTraceMovingPlayerCount;
        private float runtimeTraceAveragePlayerSpeed;
        private float runtimeTraceMaxPlayerSpeed;
        private float runtimeTraceBallSpeed;
        private string liveBehaviorEventId = string.Empty;
        private string liveBehaviorEventHolderId = string.Empty;
        private float liveBehaviorEventObservedAt = -1f;
        private float liveBehaviorEventClockMinute = -1f;
        private float liveBallIntentCreatedAt = -1f;
        private float liveBallIntentExpiresAt = -1f;
        private int liveBallIntentSequence = -1;
        private string liveBallIntentReason = string.Empty;
        private string liveBallIntentTeamSide = string.Empty;
        private string liveBallIntentSourcePlayerId = string.Empty;
        private string liveBallIntentTargetPlayerId = string.Empty;
        private Vector3 liveBallIntentOrigin = Vector3.zero;
        private Vector3 liveBallIntentTarget = Vector3.zero;
        private Vector3 liveBallIntentDirection = Vector3.zero;
        private bool liveBallIntentContested;

        public bool HasConfig => config != null;

        public bool SkipBootstrapInCurrentContext => skipBootstrap;

        public string MatchId => config != null ? config.matchId : string.Empty;

        public string BaseUrl => config != null ? config.ResolveBaseUrl() : string.Empty;

        public bool HasReceivedLiveState => lastKnownState != null;

        public bool IsUsingWebSocket => usingWebSocket;

        public bool IsConnectingWebSocket => isConnectingWebSocket;

        public bool IsMatchLoaded => matchLoaded;

        public string LastTransportError => lastTransportError;

        public string LastTransportSource => lastTransportSource;

        public int ConsecutiveTransportFailures => consecutiveTransportFailures;

        public float LastKnownClockMinute => lastKnownState != null ? lastKnownState.clockMinute : 0f;

        public int LastKnownHomeScore => lastKnownState != null ? lastKnownState.homeScore : 0;

        public int LastKnownAwayScore => lastKnownState != null ? lastKnownState.awayScore : 0;

        // =========================
        // INIT
        // =========================

        public static bool TryAutoStart()
        {
            var config = GtexMatchConfigLoader.Load();
            return TryAutoStart(config);
        }

        public static bool TryAutoStart(GtexMatchConfig config)
        {
            if (config == null ||
                config.ResolveRuntimeMode() != GtexRuntimeMode.LivePlayback ||
                !config.CanAutoStartLivePlayback)
            {
                return false;
            }

            var existing = UnityEngine.Object.FindFirstObjectByType<GtexMatchRuntime>();
            if (existing != null) return true;

            var host = new GameObject("GTEX Match Runtime");
            if (Application.isPlaying)
            {
                DontDestroyOnLoad(host);
            }

            var runtime = host.AddComponent<GtexMatchRuntime>();
            runtime.Initialize(config);
            return true;
        }

        private void Initialize(GtexMatchConfig cfg)
        {
            config = cfg;
            api = new MatchAPI(
                () => config.ResolveBaseUrl(),
                () => config != null ? config.liveAccessToken : string.Empty,
                () => config != null ? config.liveRefreshToken : string.Empty,
                config.timeoutSeconds);
            ApplyBootstrapGuardsForCurrentContext();
            InitializeRuntimeTrace();
            AppendRuntimeTrace(
                "init",
                "matchId=" + (config != null ? config.matchId : string.Empty) +
                " baseUrl=" + (config != null ? config.ResolveBaseUrl() : string.Empty) +
                " skipBootstrap=" + skipBootstrap);
            FlushRuntimeTrace(true);
            GtexMatchController.ReportRuntimeState(
                config,
                GtexRuntimeMode.LivePlayback,
                skipBootstrap ? GtexMatchPhase.None : GtexMatchPhase.Bootstrap,
                !skipBootstrap,
                nameof(GtexMatchRuntime),
                skipBootstrap
                    ? "Live runtime initialized but bootstrap is skipped in batchmode/headless context."
                    : "Live runtime initialized.");
        }

        private void Awake()
        {
            InitializeRuntimeTrace();
            Debug.Log(
                "[GTEX] Mode: " +
                GtexConfig.Mode +
                (GtexConfig.IsFastMode ? " (FAST MODE)" : string.Empty));

            AppendRuntimeTrace(
                "awake",
                "mode=" + GtexConfig.Mode +
                " fastMode=" + GtexConfig.IsFastMode +
                " batchMode=" + Application.isBatchMode);
            ApplyBootstrapGuardsForCurrentContext();
        }

        private void Start()
        {
            if (skipBootstrap)
            {
                AppendRuntimeTrace("start", "bootstrap skipped for current context.");
                FlushRuntimeTrace(true);
                return;
            }

            AppendRuntimeTrace("start", "bootstrap started.");
            StartCoroutine(Bootstrap());
        }

        private void ApplyBootstrapGuardsForCurrentContext()
        {
            if (!Application.isBatchMode || skipBootstrap)
            {
                return;
            }

            skipBootstrap = true;
            Debug.Log("[GTEX] Skipping live runtime bootstrap in batchmode/headless context.");
            AppendRuntimeTrace("guard", "bootstrap skipped in batchmode/headless context.");
            FlushRuntimeTrace(true);
        }

        private void InitializeRuntimeTrace()
        {
            if (Application.isBatchMode || !string.IsNullOrWhiteSpace(runtimeTracePath))
            {
                return;
            }

            try
            {
                var runtimeRoot = Path.GetDirectoryName(Application.dataPath);
                if (string.IsNullOrWhiteSpace(runtimeRoot))
                {
                    runtimeRoot = Application.persistentDataPath;
                }

                if (string.IsNullOrWhiteSpace(runtimeRoot))
                {
                    return;
                }

                var traceDirectory = Path.Combine(runtimeRoot, "tmp");
                Directory.CreateDirectory(traceDirectory);
                runtimeTracePath = Path.Combine(traceDirectory, "gtex_live_runtime_trace.log");
                File.WriteAllText(runtimeTracePath, string.Empty);
                runtimeTraceBuffer.Clear();
                runtimeTraceLastFlushAt = Time.unscaledTime;
                runtimeTraceLastHeartbeatAt = Time.unscaledTime;
                runtimeTraceLastMotionClockMinute = -1f;
                AppendRuntimeTrace("boot", "trace initialized path=" + runtimeTracePath);
                FlushRuntimeTrace(true);
            }
            catch (Exception exception)
            {
                runtimeTracePath = string.Empty;
                runtimeTraceBuffer.Clear();
                Debug.LogWarning("[GTEX] Failed to initialize runtime trace file: " + exception.Message);
            }
        }

        private void AppendRuntimeTrace(string category, string message)
        {
            if (string.IsNullOrWhiteSpace(runtimeTracePath))
            {
                return;
            }

            runtimeTraceBuffer.Add(
                DateTime.UtcNow.ToString("O") +
                " | " +
                category +
                " | " +
                message);

            if (runtimeTraceBuffer.Count >= RuntimeTraceMaxBufferedLines)
            {
                FlushRuntimeTrace(true);
            }
        }

        private void FlushRuntimeTrace(bool force)
        {
            if (string.IsNullOrWhiteSpace(runtimeTracePath) || runtimeTraceBuffer.Count == 0)
            {
                return;
            }

            if (!force && Time.unscaledTime - runtimeTraceLastFlushAt < RuntimeTraceFlushIntervalSeconds)
            {
                return;
            }

            try
            {
                File.AppendAllLines(runtimeTracePath, runtimeTraceBuffer);
                runtimeTraceBuffer.Clear();
                runtimeTraceLastFlushAt = Time.unscaledTime;
            }
            catch (Exception exception)
            {
                Debug.LogWarning("[GTEX] Failed to write runtime trace file: " + exception.Message);
                runtimeTraceBuffer.Clear();
            }
        }

        private string BuildRuntimeTraceSummary()
        {
            var activeEvent = currentState != null ? currentState.ResolveActiveEvent() : null;
            return
                "minute=" + (currentState != null ? currentState.clockMinute.ToString("0.##") : "n/a") +
                " score=" + (currentState != null ? currentState.homeScore : 0) + "-" + (currentState != null ? currentState.awayScore : 0) +
                " phase=" + (currentState != null ? ResolveControllerPhase(currentState).ToString() : "None") +
                " seq=" + (currentState != null ? ResolveStateSequence(currentState).ToString() : "-1") +
                " holder=" + ResolveRuntimeBallHolderId(currentState) +
                " ballSpeed=" + runtimeTraceBallSpeed.ToString("0.##") +
                " driven=" + runtimeTraceDrivenPlayerCount +
                " moving=" + runtimeTraceMovingPlayerCount +
                " avgSpeed=" + runtimeTraceAveragePlayerSpeed.ToString("0.##") +
                " maxSpeed=" + runtimeTraceMaxPlayerSpeed.ToString("0.##") +
                " transport=" + lastTransportSource +
                " ws=" + usingWebSocket +
                " loaded=" + matchLoaded +
                " intent=" + ResolveRuntimeIntentToken() +
                " event=" + (activeEvent != null ? ((activeEvent.type ?? string.Empty).Trim()) : string.Empty);
        }

        private static string ResolveRuntimeBallHolderId(MatchResponse state)
        {
            if (state == null || state.ballPosition == null)
            {
                return string.Empty;
            }

            return (state.ballPosition.playerId ?? string.Empty).Trim();
        }

        private string ResolveRuntimeIntentToken()
        {
            if (Time.unscaledTime >= liveBallIntentExpiresAt || string.IsNullOrWhiteSpace(liveBallIntentReason))
            {
                return string.Empty;
            }

            var token = liveBallIntentReason;
            if (!string.IsNullOrWhiteSpace(liveBallIntentTeamSide))
            {
                token += ":" + liveBallIntentTeamSide;
            }

            token += "@" + Mathf.Max(0f, liveBallIntentExpiresAt - Time.unscaledTime).ToString("0.0");
            return token;
        }

        private void TrackRuntimeTrace()
        {
            if (currentState == null)
            {
                FlushRuntimeTrace(false);
                return;
            }

            var phase = ResolveControllerPhase(currentState).ToString();
            if (!string.Equals(runtimeTraceLastLoggedPhase, phase, StringComparison.Ordinal))
            {
                runtimeTraceLastLoggedPhase = phase;
                AppendRuntimeTrace("phase", BuildRuntimeTraceSummary());
            }

            var activeEvent = currentState.ResolveActiveEvent();
            var activeEventId = activeEvent != null ? (activeEvent.id ?? string.Empty).Trim() : string.Empty;
            if (!string.Equals(runtimeTraceLastLoggedEventId, activeEventId, StringComparison.Ordinal))
            {
                runtimeTraceLastLoggedEventId = activeEventId;
                if (!string.IsNullOrWhiteSpace(activeEventId))
                {
                    AppendRuntimeTrace(
                        "event",
                        "minute=" + currentState.clockMinute.ToString("0.##") +
                        " type=" + ((activeEvent.type ?? string.Empty).Trim()) +
                        " primary=" + ((activeEvent.primaryPlayerId ?? string.Empty).Trim()) +
                        " score=" + currentState.homeScore + "-" + currentState.awayScore);
                }
            }

            var holderId = ResolveRuntimeBallHolderId(currentState);
            if (!string.Equals(runtimeTraceLastLoggedBallHolderId, holderId, StringComparison.Ordinal))
            {
                AppendRuntimeTrace(
                    "holder",
                    "minute=" + currentState.clockMinute.ToString("0.##") +
                    " from=" + runtimeTraceLastLoggedBallHolderId +
                    " to=" + holderId +
                    " ballSpeed=" + runtimeTraceBallSpeed.ToString("0.##"));
                runtimeTraceLastLoggedBallHolderId = holderId;
            }

            if (runtimeTraceMovingPlayerCount > 0 || runtimeTraceBallSpeed >= LiveBallPassSpeedUnitsPerSecond)
            {
                runtimeTraceLastMotionClockMinute = currentState.clockMinute;
            }
            else if (runtimeTraceLastMotionClockMinute < 0f)
            {
                runtimeTraceLastMotionClockMinute = currentState.clockMinute;
            }
            else if (currentState.clockMinute - runtimeTraceLastMotionClockMinute >= RuntimeTraceStationaryClockDeltaThresholdMinutes)
            {
                AppendRuntimeTrace("warn", "clock advanced with no detected motion. " + BuildRuntimeTraceSummary());
                runtimeTraceLastMotionClockMinute = currentState.clockMinute;
            }

            if (Time.unscaledTime - runtimeTraceLastHeartbeatAt >= RuntimeTraceHeartbeatIntervalSeconds)
            {
                runtimeTraceLastHeartbeatAt = Time.unscaledTime;
                AppendRuntimeTrace("tick", BuildRuntimeTraceSummary());
            }

            FlushRuntimeTrace(false);
        }

        // =========================
        // BOOTSTRAP
        // =========================

        private IEnumerator Bootstrap()
        {
#if GTEX_FAST_MODE
            Debug.Log("[GTEX] FAST MODE: Live match bootstrap remains enabled in editor/runtime.");
#else

#endif

            Debug.Log("[GTEX] Bootstrapping match...");
            bootstrapTaskFailed = false;
            GtexMatchController.ReportRuntimeState(
                config,
                GtexRuntimeMode.LivePlayback,
                GtexMatchPhase.Bootstrap,
                true,
                nameof(GtexMatchRuntime),
                "Live runtime bootstrap in progress.");

            if (!HasLiveAccessToken && HasLiveRefreshToken)
            {
                yield return RefreshLiveAccessToken("startup bootstrap", false);
            }

            yield return StartCoroutine(WaitForInitialFrame());

            if (lastKnownState == null)
            {
                RegisterTransportFailure("initial", "No initial frame received.", 0, false);
                yield break;
            }

            if (IsTerminalLiveState(lastKnownState))
            {
                Debug.LogWarning(
                    "[GTEX] Selected match '" +
                    lastKnownState.matchId +
                    "' is already terminal (" +
                    lastKnownState.status +
                    "/" +
                    lastKnownState.phase +
                    "). Playback will show the final frame, not active live motion.");
            }

            if (!TryBuildMatchRequest(out var matchRequest))
            {
                yield break;
            }

            yield return StartCoroutine(WaitForSceneDependencies());

            if (!GtexMatchController.MatchEngineLoaderAdapter.IsPlaybackSceneReady)
            {
                RegisterTransportFailure(
                    "bootstrap",
                    "GTEX live runtime could not find the required scene dependencies before starting the match.",
                    0,
                    false);
                yield break;
            }

            yield return AwaitTask(GtexMatchController.MatchEngineLoaderAdapter.CreateMatch(matchRequest), "CreateMatch");
            if (bootstrapTaskFailed)
            {
                yield break;
            }

            yield return AwaitTask(
                GtexMatchController.MatchEngineLoaderAdapter.StartMatchEngine(
                    new UpcomingMatchEvent(matchRequest),
                    false,
                    false
                ),
                "StartMatchEngine"
            );
            if (bootstrapTaskFailed)
            {
                yield break;
            }

            if (GtexMatchController.MatchManagerAdapter.IsAvailable)
            {
                GtexMatchController.MatchManagerAdapter.SetExternalPlayback(true);
            }
            else if (config != null && config.verboseLogging)
            {
                Debug.LogWarning("[GTEX] MatchManager is not available during live bootstrap. Runtime will continue caching live state.");
            }

            BindPlayers();
            TryConsumeLiveState(lastKnownState, true);

            matchLoaded = true;
            GtexMatchController.CameraAdapter.FocusToBall();
            AppendRuntimeTrace("bootstrap", "scene bootstrap finished.");
            FlushRuntimeTrace(true);
            GtexMatchController.ReportRuntimeState(
                config,
                GtexRuntimeMode.LivePlayback,
                ResolveControllerPhase(lastKnownState),
                true,
                nameof(GtexMatchRuntime),
                "Live runtime finished scene bootstrap.");

            // 🔥 Start WebSocket instead of polling
            StartWebSocket();

            // fallback polling safety net
            StartCoroutine(FallbackPolling());
        }

        private IEnumerator WaitForSceneDependencies()
        {
            var waitStartedAt = Time.realtimeSinceStartup;
            while (!isDestroyed)
            {
                if (GtexMatchController.MatchEngineLoaderAdapter.IsPlaybackSceneReady)
                {
                    yield break;
                }

                if (Time.realtimeSinceStartup - waitStartedAt >= SceneDependencyWaitTimeoutSeconds)
                {
                    Debug.LogWarning(
                        "[GTEX] Timed out waiting for scene dependencies. " +
                        GtexMatchController.MatchEngineLoaderAdapter.DescribePlaybackSceneAvailability());
                    yield break;
                }

                yield return null;
            }
        }

        private bool TryBuildMatchRequest(out MatchCreateRequest matchRequest)
        {
            matchRequest = default;

            var homeTemplate = ResolveTemplateTeam(config.homeTemplateTeam, "City");
            var awayTemplate = ResolveTemplateTeam(config.awayTemplateTeam, "Royal");

            if (homeTemplate == null || awayTemplate == null)
            {
                Debug.LogError("[GTEX] Failed to resolve template teams for live bootstrap.");
                return false;
            }

            matchRequest = new MatchCreateRequest(homeTemplate, awayTemplate)
            {
                dayTime = config.ResolveDayTime(),
                aiLevel = AILevel.Legendary,
                userTeam = MatchCreateRequest.UserTeam.None
            };

            if (!string.IsNullOrWhiteSpace(config.homeTeamName))
            {
                matchRequest.homeTeam.TeamName = config.homeTeamName;
            }

            if (!string.IsNullOrWhiteSpace(config.awayTeamName))
            {
                matchRequest.awayTeam.TeamName = config.awayTeamName;
            }

            return true;
        }

        private static TeamEntry ResolveTemplateTeam(string configuredName, string fallbackName)
        {
            var desiredName = string.IsNullOrWhiteSpace(configuredName)
                ? fallbackName
                : configuredName.Trim();

            var direct = Resources.Load<TeamEntry>("Database/" + desiredName);
            if (direct != null)
            {
                return direct;
            }

            var availableTeams = Resources.LoadAll<TeamEntry>("Database");
            for (int index = 0; index < availableTeams.Length; index += 1)
            {
                var candidate = availableTeams[index];
                if (candidate == null)
                {
                    continue;
                }

                if (string.Equals(candidate.name, desiredName, StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(candidate.TeamName, desiredName, StringComparison.OrdinalIgnoreCase))
                {
                    return candidate;
                }
            }

            Debug.LogError("[GTEX] Could not find TeamEntry template '" + desiredName + "' in Resources/Database.");
            return null;
        }

        // =========================
        // WEBSOCKET
        // =========================

        private async void StartWebSocket()
        {
            if (isDestroyed || skipBootstrap || config == null || !matchLoaded)
            {
                return;
            }

            if (usingWebSocket || isConnectingWebSocket)
            {
                return;
            }

            if (Time.unscaledTime < nextWebSocketReconnectAt)
            {
                return;
            }

            var wsUrl = BuildWebSocketUrl(config.ResolveBaseUrl(), config.matchId);
            if (string.IsNullOrWhiteSpace(wsUrl))
            {
                RegisterTransportFailure("websocket", "WebSocket URL is not configured.", 0, false);
                return;
            }

            if (!HasLiveAccessToken && HasLiveRefreshToken)
            {
                StartCoroutine(RefreshLiveAccessToken("websocket bootstrap", true));
                return;
            }

            isConnectingWebSocket = true;
            try
            {
                DisposeSocket();
                socket = new ClientWebSocket();
                socketToken = new CancellationTokenSource();
                if (!string.IsNullOrWhiteSpace(config.liveAccessToken))
                {
                    socket.Options.SetRequestHeader("Authorization", "Bearer " + config.liveAccessToken.Trim());
                }

                Debug.Log("[GTEX] Connecting WS: " + wsUrl);

                await socket.ConnectAsync(new Uri(wsUrl), socketToken.Token);

                usingWebSocket = true;
                isConnectingWebSocket = false;
                webSocketReconnectAttempts = 0;
                consecutiveTransportFailures = 0;
                lastTransportError = string.Empty;
                lastTransportSource = "websocket";

                _ = ReceiveLoop(socket, socketToken.Token);

            }
            catch (Exception ex)
            {
                isConnectingWebSocket = false;
                usingWebSocket = false;
                if (ShouldAttemptLiveAccessRefresh(0, ex.Message))
                {
                    StartCoroutine(RefreshLiveAccessToken("websocket connect failure", true));
                    return;
                }
                RegisterTransportFailure("websocket", "WS failed, fallback to polling: " + ex.Message, 0, true);
            }
        }

        private async Task ReceiveLoop(ClientWebSocket activeSocket, CancellationToken token)
        {
            var buffer = new byte[8192];
            using var stream = new MemoryStream(8192);

            try
            {
                while (!token.IsCancellationRequested &&
                       activeSocket != null &&
                       ReferenceEquals(activeSocket, socket) &&
                       activeSocket.State == WebSocketState.Open)
                {
                    WebSocketReceiveResult result;
                    do
                    {
                        result = await activeSocket.ReceiveAsync(
                            new ArraySegment<byte>(buffer),
                            token
                        );

                        if (result.MessageType == WebSocketMessageType.Close)
                        {
                            var closeReason = "WS closed by remote peer.";
                            if (result.CloseStatus.HasValue)
                            {
                                closeReason = "WS closed by remote peer (" + (int)result.CloseStatus.Value + ")";
                                if (!string.IsNullOrWhiteSpace(result.CloseStatusDescription))
                                {
                                    closeReason += ": " + result.CloseStatusDescription;
                                }
                                closeReason += ".";
                            }
                            else if (!string.IsNullOrWhiteSpace(result.CloseStatusDescription))
                            {
                                closeReason = "WS closed by remote peer: " + result.CloseStatusDescription + ".";
                            }

                            HandleWebSocketDisconnect(closeReason);
                            return;
                        }

                        if (result.Count > 0)
                        {
                            stream.Write(buffer, 0, result.Count);
                        }
                    }
                    while (!result.EndOfMessage);

                    var json = Encoding.UTF8.GetString(stream.GetBuffer(), 0, (int)stream.Length);
                    stream.SetLength(0);

                    try
                    {
                        var state = JsonUtility.FromJson<MatchResponse>(json);
                        if (state != null)
                        {
                            state.Normalize();
                            lastTransportSource = "websocket";
                            TryConsumeLiveState(state, false);
                            continue;
                        }

                        RegisterTransportFailure("websocket", "Ignored malformed websocket payload.", 0, false);
                    }
                    catch (Exception exception)
                    {
                        RegisterTransportFailure("websocket", "Ignored malformed websocket payload: " + exception.Message, 0, false);
                    }
                }
            }
            catch (OperationCanceledException)
            {
            }
            catch (Exception exception)
            {
                HandleWebSocketDisconnect("WS receive failed: " + exception.Message);
            }
        }

        // =========================
        // FALLBACK POLLING
        // =========================

        private IEnumerator FallbackPolling()
        {
            while (!isDestroyed)
            {
                if (!usingWebSocket && !isConnectingWebSocket)
                {
                    MatchResponse response = null;
                    string error = null;
                    long statusCode = 0;

                    yield return api.GetLiveMatch(
                        config.matchId,
                        r => response = r,
                        (e, c) =>
                        {
                            error = e;
                            statusCode = c;
                        }
                    );

                    if (response != null)
                    {
                        lastTransportSource = "poll";
                        TryConsumeLiveState(response, false);
                    }
                    else if (statusCode == 401 && HasLiveRefreshToken)
                    {
                        var refreshed = false;
                        yield return RefreshLiveAccessToken("poll fallback", true, value => refreshed = value);
                        if (refreshed)
                        {
                            continue;
                        }
                    }
                    else if (!string.IsNullOrWhiteSpace(error))
                    {
                        RegisterTransportFailure("poll", error, statusCode, false);
                    }
                }

                yield return new WaitForSecondsRealtime(Mathf.Max(0.25f, config.pollIntervalSeconds));
            }
        }

        // =========================
        // INITIAL FETCH
        // =========================

        private IEnumerator WaitForInitialFrame()
        {
            var attempts = 0;
            var startedAt = Time.realtimeSinceStartup;
            var maxDurationSeconds = Mathf.Max(config != null ? config.timeoutSeconds * 2f : 10f, 10f);

            while (lastKnownState == null && !isDestroyed)
            {
                MatchResponse response = null;
                string error = null;
                long statusCode = 0;

                yield return api.GetLiveMatch(
                    config.matchId,
                    r => response = r,
                    (e, c) =>
                    {
                        error = e;
                        statusCode = c;
                    }
                );

                if (response != null)
                {
                    lastTransportSource = "initial";
                    TryConsumeLiveState(response, true);
                    yield break;
                }

                if (statusCode == 401 && HasLiveRefreshToken)
                {
                    var refreshed = false;
                    yield return RefreshLiveAccessToken("initial fetch", false, value => refreshed = value);
                    if (refreshed)
                    {
                        continue;
                    }
                }

                attempts += 1;
                if (!string.IsNullOrWhiteSpace(error))
                {
                    RegisterTransportFailure("initial", error, statusCode, false);
                }

                if (Time.realtimeSinceStartup - startedAt >= maxDurationSeconds)
                {
                    RegisterTransportFailure(
                        "initial",
                        "Timed out waiting for initial live frame after " + attempts + " attempts.",
                        statusCode,
                        false);
                    yield break;
                }

                var retryDelay = Mathf.Min(
                    Mathf.Max(config != null ? config.pollIntervalSeconds : 1f, 0.5f) * Mathf.Max(1, attempts),
                    Mathf.Max(config != null ? config.maxRetryDelaySeconds : 8f, 1f));
                yield return new WaitForSecondsRealtime(retryDelay);
            }
        }

        // =========================
        // UPDATE LOOP
        // =========================

        private void Update()
        {
            MaintainLiveTransport();

            if (!matchLoaded || currentState == null)
            {
                FlushRuntimeTrace(false);
                return;
            }

            if (NeedsPlayerBindingRefresh()) BindPlayers();

            DrivePlayers(Time.deltaTime);
            DriveBall();
            TrackRuntimeTrace();
        }

        // =========================
        // CORE APPLY STATE
        // =========================

        public bool TryConsumeLiveState(MatchResponse state, bool forceSnap = false)
        {
            if (state == null)
            {
                return false;
            }

            state.Normalize();

            if (config != null && !string.IsNullOrWhiteSpace(config.matchId))
            {
                if (string.IsNullOrWhiteSpace(state.matchId))
                {
                    state.matchId = config.matchId;
                }
                else if (!string.Equals(state.matchId, config.matchId, StringComparison.Ordinal))
                {
                    RegisterTransportFailure(
                        lastTransportSource,
                        "Ignored live state for unexpected match '" + state.matchId + "'.",
                        0,
                        false);
                    return false;
                }
            }

            if (string.IsNullOrWhiteSpace(lastTransportSource) || string.Equals(lastTransportSource, "idle", StringComparison.OrdinalIgnoreCase))
            {
                lastTransportSource = "external";
            }

            if (!forceSnap && ShouldIgnoreStaleLiveState(state))
            {
                AppendRuntimeTrace(
                    "state-ignored",
                    "minute=" + state.clockMinute.ToString("0.##") +
                    " score=" + state.homeScore + "-" + state.awayScore +
                    " source=" + lastTransportSource);
                FlushRuntimeTrace(false);
                return false;
            }

            staleFrameWarningLogged = false;
            lastKnownState = state;
            ApplyState(state, forceSnap);
            return true;
        }

        private bool ShouldIgnoreStaleLiveState(MatchResponse state)
        {
            if (state == null || lastKnownState == null)
            {
                return false;
            }

            var clockWentBackwards =
                state.clockMinute + LiveStateClockRegressionToleranceMinutes < lastKnownState.clockMinute;
            var homeScoreWentBackwards = state.homeScore < lastKnownState.homeScore;
            var awayScoreWentBackwards = state.awayScore < lastKnownState.awayScore;

            var lastSequence = ResolveStateSequence(lastKnownState);
            var incomingSequence = ResolveStateSequence(state);
            var sequenceWentBackwards =
                lastSequence >= 0 &&
                incomingSequence >= 0 &&
                incomingSequence < lastSequence;

            if (!clockWentBackwards &&
                !homeScoreWentBackwards &&
                !awayScoreWentBackwards &&
                !sequenceWentBackwards)
            {
                return false;
            }

            if (!staleFrameWarningLogged)
            {
                staleFrameWarningLogged = true;
                var stateMatchId = string.IsNullOrWhiteSpace(state.matchId)
                    ? config != null ? config.matchId : string.Empty
                    : state.matchId;
                Debug.LogWarning(
                    "[GTEX] Ignoring stale live frame for match '" +
                    stateMatchId +
                    "'. Incoming=" +
                    state.clockMinute.ToString("0.##") +
                    "' " +
                    state.homeScore +
                    "-" +
                    state.awayScore +
                    ", last=" +
                    lastKnownState.clockMinute.ToString("0.##") +
                    "' " +
                    lastKnownState.homeScore +
                    "-" +
                    lastKnownState.awayScore +
                    ".");
                AppendRuntimeTrace(
                    "stale",
                    "incomingMinute=" + state.clockMinute.ToString("0.##") +
                    " incomingScore=" + state.homeScore + "-" + state.awayScore +
                    " lastMinute=" + lastKnownState.clockMinute.ToString("0.##") +
                    " lastScore=" + lastKnownState.homeScore + "-" + lastKnownState.awayScore);
            }

            return true;
        }

        private static int ResolveStateSequence(MatchResponse state)
        {
            var activeEvent = state != null ? state.ResolveActiveEvent() : null;
            return activeEvent != null ? activeEvent.sequence : -1;
        }

        private void UpdateActiveEventLiveness(MatchResponse state)
        {
            var activeEvent = state != null ? state.ResolveActiveEvent() : null;
            var activeEventId = ((activeEvent != null ? activeEvent.id : string.Empty) ?? string.Empty).Trim();
            var activeEventType = ((activeEvent != null ? activeEvent.type : string.Empty) ?? string.Empty).Trim().ToLowerInvariant();
            var holderId = ResolveRuntimeBallHolderId(state);
            var activeEventKey = !string.IsNullOrWhiteSpace(activeEventId)
                ? activeEventId
                : !string.IsNullOrWhiteSpace(activeEventType)
                    ? activeEventType + "|" + holderId
                    : string.Empty;

            if (string.IsNullOrWhiteSpace(activeEventKey))
            {
                liveBehaviorEventId = string.Empty;
                liveBehaviorEventHolderId = holderId;
                liveBehaviorEventObservedAt = -1f;
                liveBehaviorEventClockMinute = -1f;
                return;
            }

            if (!string.Equals(activeEventKey, liveBehaviorEventId, StringComparison.Ordinal) ||
                !string.Equals(holderId, liveBehaviorEventHolderId, StringComparison.Ordinal))
            {
                liveBehaviorEventId = activeEventKey;
                liveBehaviorEventHolderId = holderId;
                liveBehaviorEventObservedAt = Time.unscaledTime;
                liveBehaviorEventClockMinute = state != null ? state.clockMinute : -1f;
            }
        }

        private string NormalizeActiveEventTypeToken(MatchResponse state, Event activeEvent)
        {
            var eventType = ((activeEvent != null ? activeEvent.type : string.Empty) ?? string.Empty).Trim().ToLowerInvariant();
            if (string.IsNullOrWhiteSpace(eventType))
            {
                return string.Empty;
            }

            var transientType =
                eventType.Contains("kickoff") ||
                eventType.Contains("kick_off") ||
                eventType.Contains("save") ||
                eventType.Contains("miss") ||
                eventType.Contains("corner") ||
                eventType.Contains("throw");
            if (!transientType)
            {
                return eventType;
            }

            var staleByWallTime =
                liveBehaviorEventObservedAt >= 0f &&
                Time.unscaledTime - liveBehaviorEventObservedAt >= LiveBehaviorEventStaleSeconds;
            var staleByClock =
                state != null &&
                liveBehaviorEventClockMinute >= 0f &&
                state.clockMinute - liveBehaviorEventClockMinute >= LiveBehaviorEventStaleClockMinutes;
            return staleByWallTime && staleByClock ? string.Empty : eventType;
        }

        private static MatchStatus ResolveMatchStatus(MatchResponse state)
        {
            return IsTerminalLiveState(state)
                ? MatchStatus.Special
                : MatchStatus.Playing;
        }

        private static bool IsTerminalLiveState(MatchResponse state)
        {
            if (state == null)
            {
                return false;
            }

            var status = (state.status ?? string.Empty).Trim().ToLowerInvariant();
            var phase = (state.phase ?? string.Empty).Trim().ToLowerInvariant();
            var activeEvent = state.ResolveActiveEvent();
            var activeEventType = activeEvent != null
                ? (activeEvent.type ?? string.Empty).Trim().ToLowerInvariant()
                : string.Empty;

            return status.Contains("complete") ||
                   status.Contains("completed") ||
                   status.Contains("finished") ||
                   status.Contains("ended") ||
                   phase.Contains("fulltime") ||
                   phase.Contains("final") ||
                   activeEventType.Contains("fulltime") ||
                   activeEventType.Contains("final");
        }

        private static GtexMatchPhase ResolveControllerPhase(MatchResponse state)
        {
            if (state == null)
            {
                return GtexMatchPhase.Bootstrap;
            }

            if (IsTerminalLiveState(state))
            {
                return GtexMatchPhase.FullTime;
            }

            var normalizedPhase = ((state.phase ?? string.Empty).Trim().ToLowerInvariant())
                .Replace("_", string.Empty)
                .Replace(" ", string.Empty);

            if (normalizedPhase.Contains("halftime"))
            {
                return GtexMatchPhase.HalfTime;
            }

            if (normalizedPhase.Contains("secondhalf"))
            {
                return GtexMatchPhase.SecondHalf;
            }

            if (normalizedPhase.Contains("firsthalf"))
            {
                return GtexMatchPhase.FirstHalf;
            }

            var minute = Mathf.Max(0f, state.clockMinute);
            if (minute <= 0.1f)
            {
                return GtexMatchPhase.Kickoff;
            }

            return minute < 45f
                ? GtexMatchPhase.FirstHalf
                : GtexMatchPhase.SecondHalf;
        }

        private void ApplyState(MatchResponse state, bool forceSnap)
        {

            if (state == null) return;

            var previousState = currentState;
            currentState = state;
            stateReceivedAt = Time.unscaledTime;
            staleStateWarningLogged = false;
            consecutiveTransportFailures = 0;
            lastTransportError = string.Empty;
            UpdateActiveEventLiveness(state);

            if (GtexMatchController.MatchManagerAdapter.IsAvailable)
            {
                GtexMatchController.MatchManagerAdapter.ApplyExternalLiveState(
                    state.clockMinute,
                    state.homeScore,
                    state.awayScore,
                    ResolveMatchStatus(state)
                );
            }
            else if (config != null && config.verboseLogging)
            {
                Debug.LogWarning("[GTEX] MatchManager is not ready. Live state cached without scene application.");
            }

            if (NeedsPlayerBindingRefresh())
            {
                BindPlayers();
            }

            ApplyLiveCameraPreset(state, forceSnap);
            UpdateLiveBallIntent(previousState, state);
            TryTriggerLiveBallAction(previousState, state);
            TryTriggerLiveEventAction(previousState, state);

            if (forceSnap) Snap();

            var controllerPhase = ResolveControllerPhase(state);
            GtexMatchController.ReportMatchSnapshot(
                GtexRuntimeMode.LivePlayback,
                controllerPhase,
                true,
                nameof(GtexMatchRuntime),
                state.clockMinute,
                state.homeScore,
                state.awayScore,
                matchLoaded
                    ? "Live state applied to the GTEX playback runtime."
                    : "Live state cached during GTEX bootstrap.");
            GtexMatchController.PublishLiveState(state, !usingWebSocket);

            Debug.Log($"[GTEX] Live: {state.clockMinute}' {state.homeScore}-{state.awayScore}");
        }

        private void UpdateLiveBallIntent(MatchResponse previousState, MatchResponse nextState)
        {
            if (nextState == null ||
                nextState.ballPosition == null ||
                !GtexMatchController.MatchManagerAdapter.IsAvailable ||
                IsTerminalLiveState(nextState))
            {
                ClearLiveBallIntent();
                return;
            }

            var previousHolderId = ResolveRuntimeBallHolderId(previousState);
            var nextHolderId = ResolveRuntimeBallHolderId(nextState);
            var holderChanged = !string.Equals(previousHolderId, nextHolderId, StringComparison.Ordinal);
            var activeEvent = nextState.ResolveActiveEvent();
            var eventType = NormalizeActiveEventTypeToken(nextState, activeEvent);
            var eventSuggestsTravel =
                eventType.Contains("save") ||
                eventType.Contains("miss") ||
                eventType.Contains("goal") ||
                eventType.Contains("shot") ||
                eventType.Contains("chance") ||
                eventType.Contains("cross") ||
                eventType.Contains("corner");
            var ballAnchor = ResolvePredictedFieldPosition(nextState.ballPosition, 0f);
            ballAnchor.y = 0f;
            var ballVelocity = ResolveLiveFieldVelocity(nextState.ballPosition);
            ballVelocity.y = 0f;
            var ballSpeed = ballVelocity.magnitude;

            if (holderChanged && !string.IsNullOrWhiteSpace(previousHolderId))
            {
                var sourceTeamSide = ResolvePlayerTeamSideToken(previousState, previousHolderId);
                if (string.IsNullOrWhiteSpace(sourceTeamSide))
                {
                    sourceTeamSide = ResolvePlayerTeamSideToken(nextState, previousHolderId);
                }

                var sourceOrigin = ResolveRuntimePlayerPositionById(previousState, previousHolderId, ballAnchor);
                var intentTarget = ResolveLiveBallIntentTarget(
                    nextState,
                    nextHolderId,
                    ballAnchor,
                    sourceOrigin,
                    ballVelocity,
                    LiveBallIntentFallbackTravelDistance,
                    sourceTeamSide);
                var contested = string.IsNullOrWhiteSpace(nextHolderId);
                if (!contested && !string.IsNullOrWhiteSpace(sourceTeamSide))
                {
                    var nextHolderSide = ResolvePlayerTeamSideToken(nextState, nextHolderId);
                    contested =
                        !string.IsNullOrWhiteSpace(nextHolderSide) &&
                        !string.Equals(nextHolderSide, sourceTeamSide, StringComparison.Ordinal);
                }

                BeginLiveBallIntent(
                    nextState,
                    previousHolderId,
                    nextHolderId,
                    sourceTeamSide,
                    sourceOrigin,
                    intentTarget,
                    ballVelocity,
                    string.IsNullOrWhiteSpace(nextHolderId) ? "pass-flight" : "transition",
                    contested);
                return;
            }

            var holderBlank = string.IsNullOrWhiteSpace(nextHolderId);
            if (holderBlank)
            {
                if (Time.unscaledTime < liveBallIntentExpiresAt)
                {
                    RefreshLiveBallIntent(nextState, ballAnchor, ballVelocity);
                    return;
                }

                var sourcePlayerId = ((activeEvent != null ? activeEvent.primaryPlayerId : string.Empty) ?? string.Empty).Trim();
                if (string.IsNullOrWhiteSpace(sourcePlayerId))
                {
                    sourcePlayerId = previousHolderId;
                }

                if (!string.IsNullOrWhiteSpace(sourcePlayerId) &&
                    (eventSuggestsTravel || ballSpeed >= LiveBallPassSpeedUnitsPerSecond))
                {
                    var sourceTeamSide = ResolvePlayerTeamSideToken(nextState, sourcePlayerId);
                    if (string.IsNullOrWhiteSpace(sourceTeamSide))
                    {
                        sourceTeamSide = ResolvePlayerTeamSideToken(previousState, sourcePlayerId);
                    }

                    var sourceOrigin = ResolveRuntimePlayerPositionById(nextState, sourcePlayerId, ballAnchor);
                    if ((sourceOrigin - ballAnchor).sqrMagnitude <= 0.0001f)
                    {
                        sourceOrigin = ResolveRuntimePlayerPositionById(previousState, sourcePlayerId, ballAnchor);
                    }

                    var intentTarget = ResolveLiveBallIntentTarget(
                        nextState,
                        string.Empty,
                        ballAnchor,
                        sourceOrigin,
                        ballVelocity,
                        LiveBallIntentFallbackTravelDistance + 2f,
                        sourceTeamSide);

                    BeginLiveBallIntent(
                        nextState,
                        sourcePlayerId,
                        string.Empty,
                        sourceTeamSide,
                        sourceOrigin,
                        intentTarget,
                        ballVelocity,
                        string.IsNullOrWhiteSpace(eventType) ? "loose-ball" : eventType,
                        true);
                    return;
                }
            }
            else if (eventSuggestsTravel &&
                     !string.IsNullOrWhiteSpace(nextHolderId) &&
                     ballSpeed >= LiveBallPassSpeedUnitsPerSecond * 0.75f)
            {
                var sourceTeamSide = ResolvePlayerTeamSideToken(nextState, nextHolderId);
                var sourceOrigin = ResolveRuntimePlayerPositionById(nextState, nextHolderId, ballAnchor);
                var intentTarget = ResolveLiveBallIntentTarget(
                    nextState,
                    string.Empty,
                    ballAnchor,
                    sourceOrigin,
                    ballVelocity,
                    LiveBallIntentFallbackTravelDistance + 2.25f,
                    sourceTeamSide);

                BeginLiveBallIntent(
                    nextState,
                    nextHolderId,
                    string.Empty,
                    sourceTeamSide,
                    sourceOrigin,
                    intentTarget,
                    ballVelocity,
                    eventType,
                    true);
                return;
            }

            if (Time.unscaledTime < liveBallIntentExpiresAt)
            {
                RefreshLiveBallIntent(nextState, ballAnchor, ballVelocity);
            }

            if (!holderBlank && !eventSuggestsTravel && !string.IsNullOrWhiteSpace(nextHolderId))
            {
                ClearLiveBallIntent();
            }
        }

        private void BeginLiveBallIntent(
            MatchResponse state,
            string sourcePlayerId,
            string targetPlayerId,
            string teamSide,
            Vector3 sourceOrigin,
            Vector3 targetPosition,
            Vector3 ballVelocity,
            string reason,
            bool contested)
        {
            var planarVelocity = new Vector3(ballVelocity.x, 0f, ballVelocity.z);
            var travelDirection = planarVelocity.sqrMagnitude > 0.0001f
                ? planarVelocity.normalized
                : targetPosition - sourceOrigin;
            travelDirection.y = 0f;
            if (travelDirection.sqrMagnitude <= 0.0001f)
            {
                travelDirection = ResolveAttackDirection(teamSide);
            }

            var distance = Vector3.Distance(sourceOrigin, targetPosition);
            var speed = Mathf.Max(planarVelocity.magnitude, LiveBallPassSpeedUnitsPerSecond);
            var lifetimeSeconds = Mathf.Clamp(
                ((distance + 1.35f) / speed) * 1.8f,
                LiveBallIntentMinLifetimeSeconds,
                LiveBallIntentMaxLifetimeSeconds);

            liveBallIntentCreatedAt = Time.unscaledTime;
            liveBallIntentExpiresAt = Time.unscaledTime + lifetimeSeconds;
            liveBallIntentSequence = ResolveStateSequence(state);
            liveBallIntentReason = (reason ?? string.Empty).Trim().ToLowerInvariant();
            liveBallIntentTeamSide = NormalizeTeamSideToken(teamSide);
            liveBallIntentSourcePlayerId = (sourcePlayerId ?? string.Empty).Trim();
            liveBallIntentTargetPlayerId = (targetPlayerId ?? string.Empty).Trim();
            liveBallIntentOrigin = sourceOrigin;
            liveBallIntentOrigin.y = 0f;
            liveBallIntentTarget = ClampToFieldBounds(targetPosition, false);
            liveBallIntentTarget.y = 0f;
            liveBallIntentDirection = travelDirection.normalized;
            liveBallIntentContested = contested;

            AppendRuntimeTrace(
                "intent",
                "minute=" + (state != null ? state.clockMinute.ToString("0.##") : "n/a") +
                " reason=" + liveBallIntentReason +
                " side=" + liveBallIntentTeamSide +
                " from=" + liveBallIntentSourcePlayerId +
                " to=" + liveBallIntentTargetPlayerId +
                " eta=" + lifetimeSeconds.ToString("0.0") +
                " target=(" + liveBallIntentTarget.x.ToString("0.0") + "," + liveBallIntentTarget.z.ToString("0.0") + ")");
        }

        private void RefreshLiveBallIntent(MatchResponse state, Vector3 ballAnchor, Vector3 ballVelocity)
        {
            if (Time.unscaledTime >= liveBallIntentExpiresAt)
            {
                return;
            }

            var fallbackTravelDistance = LiveBallIntentFallbackTravelDistance;
            if (liveBallIntentReason.Contains("save", StringComparison.Ordinal) ||
                liveBallIntentReason.Contains("miss", StringComparison.Ordinal) ||
                liveBallIntentReason.Contains("chance", StringComparison.Ordinal))
            {
                fallbackTravelDistance += 1.5f;
            }

            liveBallIntentTarget = Vector3.Lerp(
                liveBallIntentTarget,
                ResolveLiveBallIntentTarget(
                    state,
                    liveBallIntentTargetPlayerId,
                    ballAnchor,
                    liveBallIntentOrigin,
                    ballVelocity,
                    fallbackTravelDistance,
                    liveBallIntentTeamSide),
                0.4f);
            liveBallIntentTarget.y = 0f;

            var updatedDirection = new Vector3(ballVelocity.x, 0f, ballVelocity.z);
            if (updatedDirection.sqrMagnitude <= 0.0001f)
            {
                updatedDirection = liveBallIntentTarget - liveBallIntentOrigin;
                updatedDirection.y = 0f;
            }

            if (updatedDirection.sqrMagnitude > 0.0001f)
            {
                liveBallIntentDirection = updatedDirection.normalized;
            }
        }

        private bool TryResolveLiveBallIntent(
            out Vector3 intentAnchor,
            out Vector3 intentDirection,
            out string intentTeamSide,
            out bool intentContested,
            out float intentStrength)
        {
            intentAnchor = Vector3.zero;
            intentDirection = Vector3.zero;
            intentTeamSide = string.Empty;
            intentContested = false;
            intentStrength = 0f;

            if (Time.unscaledTime >= liveBallIntentExpiresAt || string.IsNullOrWhiteSpace(liveBallIntentReason))
            {
                return false;
            }

            var lifetime = Mathf.Max(liveBallIntentExpiresAt - liveBallIntentCreatedAt, 0.001f);
            intentStrength = Mathf.Clamp01((liveBallIntentExpiresAt - Time.unscaledTime) / lifetime);
            intentTeamSide = liveBallIntentTeamSide;
            intentContested = liveBallIntentContested;
            intentDirection = liveBallIntentDirection;

            var ballAnchor = currentState != null && currentState.ballPosition != null
                ? ResolvePredictedFieldPosition(currentState.ballPosition, ResolveLivePredictionSeconds())
                : liveBallIntentTarget;
            ballAnchor.y = 0f;

            var target = liveBallIntentTarget;
            if (currentState != null)
            {
                var fallbackTravelDistance = LiveBallIntentFallbackTravelDistance;
                if (liveBallIntentReason.Contains("save", StringComparison.Ordinal) ||
                    liveBallIntentReason.Contains("miss", StringComparison.Ordinal) ||
                    liveBallIntentReason.Contains("chance", StringComparison.Ordinal))
                {
                    fallbackTravelDistance += 1.5f;
                }

                var refreshedTarget = ResolveLiveBallIntentTarget(
                    currentState,
                    liveBallIntentTargetPlayerId,
                    ballAnchor,
                    liveBallIntentOrigin,
                    ResolveLiveFieldVelocity(currentState.ballPosition),
                    fallbackTravelDistance,
                    liveBallIntentTeamSide);
                target = Vector3.Lerp(target, refreshedTarget, 0.55f);
            }

            target.y = 0f;
            if (intentDirection.sqrMagnitude <= 0.0001f)
            {
                intentDirection = target - liveBallIntentOrigin;
                intentDirection.y = 0f;
            }

            if (intentDirection.sqrMagnitude <= 0.0001f)
            {
                intentDirection = ResolveAttackDirection(intentTeamSide);
            }
            else
            {
                intentDirection.Normalize();
            }

            intentAnchor = ClampToFieldBounds(Vector3.Lerp(ballAnchor, target, 0.72f), false);
            return true;
        }

        private void ClearLiveBallIntent()
        {
            liveBallIntentCreatedAt = -1f;
            liveBallIntentExpiresAt = -1f;
            liveBallIntentSequence = -1;
            liveBallIntentReason = string.Empty;
            liveBallIntentTeamSide = string.Empty;
            liveBallIntentSourcePlayerId = string.Empty;
            liveBallIntentTargetPlayerId = string.Empty;
            liveBallIntentOrigin = Vector3.zero;
            liveBallIntentTarget = Vector3.zero;
            liveBallIntentDirection = Vector3.zero;
            liveBallIntentContested = false;
        }

        private Vector3 ResolveLiveBallIntentTarget(
            MatchResponse state,
            string targetPlayerId,
            Vector3 ballAnchor,
            Vector3 sourceOrigin,
            Vector3 ballVelocity,
            float fallbackTravelDistance,
            string fallbackTeamSide)
        {
            var explicitTarget = ResolveRuntimePlayerPositionById(state, targetPlayerId, Vector3.zero);
            if (explicitTarget.sqrMagnitude > 0.0001f)
            {
                explicitTarget.y = 0f;
                return ClampToFieldBounds(Vector3.Lerp(ballAnchor, explicitTarget, 0.72f), false);
            }

            var travelDirection = new Vector3(ballVelocity.x, 0f, ballVelocity.z);
            if (travelDirection.sqrMagnitude <= 0.0001f)
            {
                travelDirection = ballAnchor - sourceOrigin;
                travelDirection.y = 0f;
            }

            if (travelDirection.sqrMagnitude <= 0.0001f)
            {
                travelDirection = ResolveAttackDirection(fallbackTeamSide);
            }
            else
            {
                travelDirection.Normalize();
            }

            return ClampToFieldBounds(ballAnchor + travelDirection * fallbackTravelDistance, false);
        }

        private Vector3 ResolveRuntimePlayerPositionById(MatchResponse state, string playerId, Vector3 fallbackPosition)
        {
            if (TryResolveLivePlayerByPlayerId(state, playerId, out var livePlayer))
            {
                return ResolveRuntimeFieldPosition(livePlayer, state, fallbackPosition);
            }

            fallbackPosition.y = 0f;
            return fallbackPosition;
        }

        private Vector3 ResolveRuntimeFieldPosition(PlayerPosition livePlayer, MatchResponse state, Vector3 fallbackPosition)
        {
            if (TryGetBoundPlayer(livePlayer, out var boundPlayer) && boundPlayer != null && boundPlayer.IsValid)
            {
                var boundPosition = boundPlayer.Position;
                boundPosition.y = 0f;
                return boundPosition;
            }

            if (livePlayer != null && state != null && GtexMatchController.MatchManagerAdapter.IsAvailable)
            {
                var statePosition = GtexMatchController.MatchManagerAdapter.ResolveFieldPosition(livePlayer, state);
                statePosition.y = 0f;
                return ClampToFieldBounds(statePosition, livePlayer.isBall);
            }

            fallbackPosition.y = 0f;
            return fallbackPosition;
        }

        private static bool TryResolveLivePlayerByPlayerId(MatchResponse state, string playerId, out PlayerPosition livePlayer)
        {
            if (!string.IsNullOrWhiteSpace(playerId) && state != null && state.players != null)
            {
                var livePlayers = state.players;
                for (var index = 0; index < livePlayers.Length; index += 1)
                {
                    var candidate = livePlayers[index];
                    if (candidate == null || candidate.isBall)
                    {
                        continue;
                    }

                    if (string.Equals(candidate.playerId, playerId, StringComparison.Ordinal))
                    {
                        livePlayer = candidate;
                        return true;
                    }
                }
            }

            livePlayer = null;
            return false;
        }

        private static string ResolvePlayerTeamSideToken(MatchResponse state, string playerId)
        {
            return TryResolveLivePlayerByPlayerId(state, playerId, out var livePlayer)
                ? NormalizeTeamSideToken(livePlayer.teamSide)
                : string.Empty;
        }

        private void MaintainLiveTransport()
        {
            if (!matchLoaded || config == null || isDestroyed)
            {
                return;
            }

            if (!usingWebSocket &&
                !isConnectingWebSocket &&
                Time.unscaledTime >= nextWebSocketReconnectAt)
            {
                StartWebSocket();
            }

            if (lastKnownState == null)
            {
                return;
            }

            if (IsTerminalLiveState(lastKnownState))
            {
                return;
            }

            var staleThreshold = Mathf.Max(config.pollIntervalSeconds * 3f, config.maxRetryDelaySeconds);
            var staleDuration = Time.unscaledTime - stateReceivedAt;
            if (!staleStateWarningLogged && staleDuration > staleThreshold)
            {
                staleStateWarningLogged = true;
                var staleMessage = "Transport degraded. Live state has gone stale for " + staleDuration.ToString("0.0") + "s.";
                if (usingWebSocket)
                {
                    HandleWebSocketDisconnect(staleMessage);
                    return;
                }

                RegisterTransportFailure("poll", staleMessage, 0, false);
            }
        }

        private static string BuildWebSocketUrl(string baseUrl, string matchId)
        {
            if (string.IsNullOrWhiteSpace(baseUrl) || string.IsNullOrWhiteSpace(matchId))
            {
                return string.Empty;
            }

            var normalized = baseUrl.TrimEnd('/');
            if (normalized.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
            {
                normalized = "wss://" + normalized.Substring("https://".Length);
            }
            else if (normalized.StartsWith("http://", StringComparison.OrdinalIgnoreCase))
            {
                normalized = "ws://" + normalized.Substring("http://".Length);
            }

            return normalized + "/api/v1/ws/match/" + Uri.EscapeDataString(matchId) + "?format=unity";
        }

        private void HandleWebSocketDisconnect(string reason)
        {
            usingWebSocket = false;
            isConnectingWebSocket = false;
            DisposeSocket();
            if (ShouldAttemptLiveAccessRefresh(0, reason))
            {
                StartCoroutine(RefreshLiveAccessToken("websocket disconnect", true));
                return;
            }
            RegisterTransportFailure("websocket", reason, 0, true);
        }

        private bool HasLiveAccessToken =>
            config != null && !string.IsNullOrWhiteSpace(config.liveAccessToken);

        private bool HasLiveRefreshToken =>
            config != null && !string.IsNullOrWhiteSpace(config.liveRefreshToken);

        private static bool ShouldAttemptLiveAccessRefresh(long statusCode, string message)
        {
            if (statusCode == 401)
            {
                return true;
            }

            if (string.IsNullOrWhiteSpace(message))
            {
                return false;
            }

            var normalized = message.Trim().ToLowerInvariant();
            return normalized.Contains("401") ||
                   normalized.Contains("4401") ||
                   normalized.Contains("unauthor");
        }

        private IEnumerator RefreshLiveAccessToken(string reason, bool scheduleReconnect)
        {
            return RefreshLiveAccessToken(reason, scheduleReconnect, null);
        }

        private IEnumerator RefreshLiveAccessToken(string reason, bool scheduleReconnect, Action<bool> onComplete)
        {
            if (isDestroyed || config == null || api == null || !HasLiveRefreshToken)
            {
                onComplete?.Invoke(false);
                yield break;
            }

            if (isRefreshingLiveAccess)
            {
                while (isRefreshingLiveAccess && !isDestroyed)
                {
                    yield return null;
                }

                onComplete?.Invoke(HasLiveAccessToken);
                yield break;
            }

            isRefreshingLiveAccess = true;
            GtexLiveAccessGrant grant = null;
            string error = null;
            long statusCode = 0;

            Debug.Log("[GTEX] Refreshing live access token: " + reason);

            yield return api.RefreshLiveAccess(
                config.matchId,
                value => grant = value,
                (message, code) =>
                {
                    error = message;
                    statusCode = code;
                });

            isRefreshingLiveAccess = false;

            if (grant != null && grant.HasAccessToken)
            {
                config.liveAccessToken = grant.access_token ?? string.Empty;
                if (grant.HasRefreshToken)
                {
                    config.liveRefreshToken = grant.refresh_token ?? config.liveRefreshToken;
                }

                consecutiveTransportFailures = 0;
                lastTransportError = string.Empty;
                lastTransportSource = "auth";
                webSocketReconnectAttempts = 0;
                if (scheduleReconnect)
                {
                    nextWebSocketReconnectAt = Time.unscaledTime;
                }

                Debug.Log("[GTEX] Live access token refreshed successfully.");
                onComplete?.Invoke(true);
                yield break;
            }

            if (!string.IsNullOrWhiteSpace(error))
            {
                RegisterTransportFailure("auth", "Live access refresh failed during " + reason + ": " + error, statusCode, false);
            }

            onComplete?.Invoke(false);
        }

        private void RegisterTransportFailure(string transport, string message, long statusCode, bool scheduleReconnect)
        {
            consecutiveTransportFailures += 1;
            lastTransportSource = string.IsNullOrWhiteSpace(transport) ? "unknown" : transport;
            lastTransportError = statusCode > 0
                ? message + " (HTTP " + statusCode + ")"
                : message;
            AppendRuntimeTrace(
                "transport",
                "source=" + lastTransportSource +
                " failure=" + consecutiveTransportFailures +
                " message=" + lastTransportError +
                " reconnect=" + scheduleReconnect);

            if (consecutiveTransportFailures <= 3 || config == null || config.verboseLogging)
            {
                Debug.LogWarning("[GTEX] " + lastTransportSource + " failure #" + consecutiveTransportFailures + ": " + lastTransportError);
            }

            if (!scheduleReconnect || config == null || !matchLoaded)
            {
                return;
            }

            webSocketReconnectAttempts += 1;
            var delay = Mathf.Min(
                Mathf.Pow(2f, Mathf.Max(0, webSocketReconnectAttempts - 1)) * Mathf.Max(config.pollIntervalSeconds, 0.5f),
                Mathf.Max(config.maxRetryDelaySeconds, 1f));
            nextWebSocketReconnectAt = Time.unscaledTime + delay;
            Debug.LogWarning("[GTEX] Next websocket reconnect attempt in " + delay.ToString("0.0") + "s.");
        }

        // =========================
        // PLAYER + BALL
        // =========================

        private void BindPlayers()
        {
            playerBindings.Clear();
            lastAnimationStates.Clear();

            if (currentState == null || !GtexMatchController.MatchManagerAdapter.HasTeams)
            {
                return;
            }

            BindPlayersForSide(FilterLivePlayersBySide("home"), GtexMatchController.MatchManagerAdapter.GetHomePlayers());
            BindPlayersForSide(FilterLivePlayersBySide("away"), GtexMatchController.MatchManagerAdapter.GetAwayPlayers());

            if (config != null && config.verboseLogging)
            {
                var expectedBindings = 0;
                var resolvedBindings = 0;
                var livePlayers = currentState.players;
                for (var index = 0; index < livePlayers.Length; index += 1)
                {
                    var livePlayer = livePlayers[index];
                    if (livePlayer == null || livePlayer.isBall)
                    {
                        continue;
                    }

                    expectedBindings += 1;
                    if (TryGetBoundPlayer(livePlayer, out _))
                    {
                        resolvedBindings += 1;
                    }
                }

                if (resolvedBindings < expectedBindings)
                {
                    Debug.LogWarning(
                        "[GTEX] Bound " +
                        resolvedBindings +
                        "/" +
                        expectedBindings +
                        " live players to Unity actors.");
                }
            }
        }

        private void DrivePlayers(float dt)
        {
            if (currentState == null)
            {
                return;
            }

            var predictionSeconds = ResolveLivePredictionSeconds();
            var livePlayers = currentState.players;
            var drivenPlayers = 0;
            var movingPlayers = 0;
            var accumulatedSpeed = 0f;
            var maxSpeed = 0f;
            for (var index = 0; index < livePlayers.Length; index += 1)
            {
                var livePlayer = livePlayers[index];
                if (livePlayer == null || livePlayer.isBall)
                {
                    continue;
                }

                if (!TryGetBoundPlayer(livePlayer, out var player) || player == null)
                {
                    continue;
                }

                var appliedSpeed = ApplyLivePlayerState(livePlayer, player, dt, predictionSeconds, false);
                drivenPlayers += 1;
                accumulatedSpeed += appliedSpeed;
                maxSpeed = Mathf.Max(maxSpeed, appliedSpeed);
                if (appliedSpeed > 0.35f)
                {
                    movingPlayers += 1;
                }
            }

            runtimeTraceDrivenPlayerCount = drivenPlayers;
            runtimeTraceMovingPlayerCount = movingPlayers;
            runtimeTraceAveragePlayerSpeed = drivenPlayers > 0 ? accumulatedSpeed / drivenPlayers : 0f;
            runtimeTraceMaxPlayerSpeed = maxSpeed;
        }

        private void DriveBall()
        {
            if (currentState == null || currentState.ballPosition == null || !GtexMatchController.BallAdapter.IsAvailable)
            {
                runtimeTraceBallSpeed = 0f;
                return;
            }

            var ballHolder = ResolveBallHolder(currentState.ballPosition);
            var targetPosition = ballHolder != null
                ? GtexMatchController.MatchManagerAdapter.ResolveFieldPosition(currentState.ballPosition, currentState)
                : ResolvePredictedFieldPosition(currentState.ballPosition, ResolveLivePredictionSeconds());
            var ballVelocity = ResolveLiveFieldVelocity(currentState.ballPosition);
            runtimeTraceBallSpeed = new Vector3(ballVelocity.x, 0f, ballVelocity.z).magnitude;

            GtexMatchController.BallAdapter.ApplyExternalState(
                targetPosition,
                ballVelocity,
                ballHolder);
        }

        private void Snap()
        {
            if (currentState == null)
            {
                return;
            }

            if (NeedsPlayerBindingRefresh())
            {
                BindPlayers();
            }

            var livePlayers = currentState.players;
            for (var index = 0; index < livePlayers.Length; index += 1)
            {
                var livePlayer = livePlayers[index];
                if (livePlayer == null || livePlayer.isBall)
                {
                    continue;
                }

                if (!TryGetBoundPlayer(livePlayer, out var player) || player == null)
                {
                    continue;
                }

                ApplyLivePlayerState(livePlayer, player, 0f, 0f, true);
            }

            DriveBall();
        }

        private bool NeedsPlayerBindingRefresh()
        {
            if (currentState == null || currentState.players == null || !GtexMatchController.MatchManagerAdapter.HasTeams)
            {
                return false;
            }

            var livePlayers = currentState.players;
            for (var index = 0; index < livePlayers.Length; index += 1)
            {
                var livePlayer = livePlayers[index];
                if (livePlayer == null || livePlayer.isBall)
                {
                    continue;
                }

                if (!TryGetBoundPlayer(livePlayer, out _))
                {
                    return true;
                }
            }

            return false;
        }

        private void BindPlayersForSide(PlayerPosition[] livePlayers, IReadOnlyList<GtexLegacyPlayerHandle> teamPlayers)
        {
            if (livePlayers == null || livePlayers.Length == 0 || teamPlayers == null || teamPlayers.Count == 0)
            {
                return;
            }

            var availablePlayers = new List<GtexLegacyPlayerHandle>(teamPlayers.Where(player => player != null && player.IsValid));
            foreach (var livePlayer in livePlayers
                .OrderBy(ResolveLiveRoleBucket)
                .ThenBy(player => player.z)
                .ThenBy(player => player.x))
            {
                if (availablePlayers.Count == 0)
                {
                    break;
                }

                var targetPosition = GtexMatchController.MatchManagerAdapter.ResolveFieldPosition(livePlayer, currentState);
                GtexLegacyPlayerHandle bestCandidate = null;
                var bestScore = float.MaxValue;

                for (var index = 0; index < availablePlayers.Count; index += 1)
                {
                    var candidate = availablePlayers[index];
                    var score = ScoreBindingCandidate(livePlayer, candidate, targetPosition);
                    if (score < bestScore)
                    {
                        bestScore = score;
                        bestCandidate = candidate;
                    }
                }

                if (bestCandidate == null)
                {
                    continue;
                }

                StorePlayerBinding(livePlayer, bestCandidate);
                availablePlayers.Remove(bestCandidate);
            }
        }

        private PlayerPosition[] FilterLivePlayersBySide(string teamSide)
        {
            if (currentState == null || currentState.players == null)
            {
                return Array.Empty<PlayerPosition>();
            }

            var normalizedTeamSide = NormalizeTeamSideToken(teamSide);
            if (string.IsNullOrWhiteSpace(normalizedTeamSide))
            {
                return Array.Empty<PlayerPosition>();
            }

            return currentState.players
                .Where(player =>
                    player != null &&
                    !player.isBall &&
                    string.Equals(NormalizeTeamSideToken(player.teamSide), normalizedTeamSide, StringComparison.Ordinal))
                .ToArray();
        }

        private float ScoreBindingCandidate(PlayerPosition livePlayer, GtexLegacyPlayerHandle candidate, Vector3 targetPosition)
        {
            if (candidate == null || !candidate.IsValid)
            {
                return float.MaxValue;
            }

            var score = Vector3.Distance(candidate.Position, targetPosition);

            if (ResolveLiveRoleBucket(livePlayer) != ResolveEngineRoleBucket(candidate.PositionRole))
            {
                score += 25f;
            }

            if (!string.IsNullOrWhiteSpace(livePlayer.playerId) &&
                int.TryParse(livePlayer.playerId, out var livePlayerId) &&
                candidate.DatabasePlayerId.HasValue &&
                candidate.DatabasePlayerId.Value == livePlayerId)
            {
                score -= 100f;
            }

            if (livePlayer.shirtNumber > 0 && candidate.ShirtNumber == livePlayer.shirtNumber)
            {
                score -= 10f;
            }

            return score;
        }

        private void StorePlayerBinding(PlayerPosition livePlayer, GtexLegacyPlayerHandle player)
        {
            if (livePlayer == null || player == null)
            {
                return;
            }

            if (!string.IsNullOrWhiteSpace(livePlayer.entityId))
            {
                playerBindings[livePlayer.entityId] = player;
            }

            if (!string.IsNullOrWhiteSpace(livePlayer.playerId))
            {
                playerBindings["player:" + livePlayer.playerId] = player;
            }
        }

        private bool TryGetBoundPlayer(PlayerPosition livePlayer, out GtexLegacyPlayerHandle player)
        {
            if (livePlayer != null)
            {
                if (!string.IsNullOrWhiteSpace(livePlayer.entityId) &&
                    playerBindings.TryGetValue(livePlayer.entityId, out player) &&
                    player != null &&
                    player.IsValid)
                {
                    return true;
                }

                if (!string.IsNullOrWhiteSpace(livePlayer.playerId) &&
                    playerBindings.TryGetValue("player:" + livePlayer.playerId, out player) &&
                    player != null &&
                    player.IsValid)
                {
                    return true;
                }
            }

            player = null;
            return false;
        }

        private bool TryGetBoundPlayerByPlayerId(string playerId, out GtexLegacyPlayerHandle player)
        {
            if (!string.IsNullOrWhiteSpace(playerId) &&
                playerBindings.TryGetValue("player:" + playerId, out player) &&
                player != null &&
                player.IsValid)
            {
                return true;
            }

            player = null;
            return false;
        }

        private float ApplyLivePlayerState(PlayerPosition livePlayer, GtexLegacyPlayerHandle player, float dt, float predictionSeconds, bool snap)
        {
            if (livePlayer == null || player == null || !player.IsValid)
            {
                return 0f;
            }

            var currentPosition = player.Position;
            var liveVelocity = snap ? Vector3.zero : ResolveLiveFieldVelocity(livePlayer);
            var targetPosition = snap
                ? GtexMatchController.MatchManagerAdapter.ResolveFieldPosition(livePlayer, currentState)
                : ResolvePredictedFieldPosition(livePlayer, predictionSeconds);
            if (!snap)
            {
                targetPosition = ResolveBehaviorDrivenFieldPosition(livePlayer, targetPosition, currentPosition, liveVelocity);
            }

            Vector3 appliedPosition;
            if (snap || Vector3.Distance(currentPosition, targetPosition) >= LivePlayerSnapDistance)
            {
                appliedPosition = targetPosition;
            }
            else
            {
                appliedPosition = Vector3.MoveTowards(
                    currentPosition,
                    targetPosition,
                    ResolveLivePlayerMoveSpeed(livePlayer, currentPosition, targetPosition, liveVelocity) * Mathf.Max(dt, 0f));
            }

            player.SetInstantPosition(appliedPosition);

            var lookDirection = ResolveLookDirection(livePlayer, appliedPosition - currentPosition, player);
            if (lookDirection.sqrMagnitude > 0.0001f)
            {
                var targetRotation = Quaternion.LookRotation(lookDirection.normalized, Vector3.up);
                var appliedRotation = snap
                    ? targetRotation
                    : Quaternion.Slerp(player.Rotation, targetRotation, Mathf.Clamp01(dt * LivePlayerRotationLerpSpeed));
                player.SetInstantRotation(appliedRotation);
            }

            ApplyLiveAnimatorState(livePlayer, player, appliedPosition - currentPosition, liveVelocity, dt, snap);
            if (snap || dt <= 0f)
            {
                return 0f;
            }

            var frameMovement = appliedPosition - currentPosition;
            frameMovement.y = 0f;
            var actualSpeed = frameMovement.magnitude / Mathf.Max(dt, 0.001f);
            var liveSpeed = new Vector3(liveVelocity.x, 0f, liveVelocity.z).magnitude;
            return Mathf.Max(actualSpeed, liveSpeed);
        }

        private void ApplyLiveAnimatorState(PlayerPosition livePlayer, GtexLegacyPlayerHandle player, Vector3 frameMovement, Vector3 liveVelocity, float dt, bool snap)
        {
            if (player == null || !player.IsValid)
            {
                return;
            }

            var animationState = (livePlayer.animationState ?? string.Empty).Trim().ToLowerInvariant();
            var syntheticMotion =
                !snap &&
                (frameMovement.sqrMagnitude > 0.0001f || new Vector3(liveVelocity.x, 0f, liveVelocity.z).sqrMagnitude > 0.0001f);
            var explicitIdle =
                !livePlayer.active ||
                animationState == "sent_off" ||
                animationState == "save" ||
                animationState == "celebrate" ||
                (!syntheticMotion && (animationState == "idle" || animationState == "set_piece"));

            var movement = snap ? Vector3.zero : frameMovement;
            var planarVelocity = snap ? Vector3.zero : new Vector3(liveVelocity.x, 0f, liveVelocity.z);
            var moveSpeed = 0f;
            var localDirection = Vector3.zero;

            if (!explicitIdle && dt > 0f)
            {
                var directionSource = planarVelocity.sqrMagnitude > 0.0001f ? planarVelocity : movement;
                if (directionSource.sqrMagnitude > 0.0001f)
                {
                    moveSpeed = Mathf.Clamp01(
                        Mathf.Max(
                            Mathf.Clamp01(livePlayer.speedRatio),
                            planarVelocity.magnitude / Mathf.Max(LivePlayerMaxSpeedUnitsPerSecond, 0.001f),
                            movement.magnitude / Mathf.Max(dt * LiveAnimatorMoveSpeedScale, 0.001f)));

                    localDirection = player.InverseTransformDirection(directionSource.normalized);
                }
            }

            player.ApplyExternalAnimatorState(
                livePlayer.hasPossession,
                explicitIdle ? 0f : moveSpeed,
                moveSpeed > 0.01f ? Mathf.Clamp(localDirection.x, -1f, 1f) : 0f,
                moveSpeed > 0.01f ? Mathf.Clamp(localDirection.z, -1f, 1f) : 0f);

            var bindingKey = ResolveBindingStorageKey(livePlayer);
            var previousAnimationState = string.Empty;
            if (!string.IsNullOrWhiteSpace(bindingKey))
            {
                lastAnimationStates.TryGetValue(bindingKey, out previousAnimationState);
            }

            ApplyLiveAnimationTrigger(livePlayer, player, animationState, previousAnimationState);

            if (!string.IsNullOrWhiteSpace(bindingKey))
            {
                lastAnimationStates[bindingKey] = animationState;
            }
        }

        private void ApplyLiveAnimationTrigger(
            PlayerPosition livePlayer,
            GtexLegacyPlayerHandle player,
            string animationState,
            string previousAnimationState)
        {
            if (player == null || !player.IsValid)
            {
                return;
            }

            var celebrating = string.Equals(animationState, "celebrate", StringComparison.Ordinal);
            player.SetAnimatorBool(PlayerAnimatorVariable.IsHappy, celebrating);

            if (string.IsNullOrWhiteSpace(animationState) ||
                string.Equals(previousAnimationState, animationState, StringComparison.Ordinal))
            {
                return;
            }

            switch (animationState)
            {
                case "tackle":
                    player.SetAnimatorTrigger(PlayerAnimatorVariable.Tackling);
                    return;
                case "save":
                    if (string.Equals((livePlayer.role ?? string.Empty).Trim(), "GK", StringComparison.OrdinalIgnoreCase))
                    {
                        player.SetAnimatorTrigger(PlayerAnimatorVariable.GKBallSave_Low);
                    }
                    return;
            }
        }

        private void ApplyLiveCameraPreset(MatchResponse state, bool forceSnap)
        {
            if (state == null || !GtexMatchController.CameraAdapter.IsAvailable)
            {
                return;
            }

            var preset = (state.cameraPreset ?? string.Empty).Trim().ToLowerInvariant();
            if (string.IsNullOrWhiteSpace(preset))
            {
                preset = "broadcast";
            }

            var cameraType = ResolveCameraTypeForPreset(preset);
            if (string.IsNullOrWhiteSpace(cameraType))
            {
                return;
            }

            if (string.Equals(lastAppliedCameraPreset, preset, StringComparison.Ordinal) &&
                string.Equals(GtexMatchController.CameraAdapter.CurrentCameraType, cameraType, StringComparison.Ordinal))
            {
                return;
            }

            GtexMatchController.CameraAdapter.SwitchCamera(cameraType, forceSnap);
            if (GtexMatchController.CameraAdapter.CanFocusBall)
            {
                GtexMatchController.CameraAdapter.FocusToBall(forceSnap);
            }

            lastAppliedCameraPreset = preset;
        }

        private static string ResolveCameraTypeForPreset(string preset)
        {
            switch ((preset ?? string.Empty).Trim().ToLowerInvariant())
            {
                case "attack_push":
                    return "StadiumHigh";
                case "box_zoom":
                case "goal_celebration":
                    return "Tele";
                case "assistant_flag":
                    return "Offside";
                case "var_replay":
                case "broadcast":
                default:
                    return "Broadcast";
            }
        }

        private GtexLegacyPlayerHandle ResolveBallHolder(PlayerPosition ballPosition)
        {
            if (ballPosition != null && !string.IsNullOrWhiteSpace(ballPosition.playerId))
            {
                if (playerBindings.TryGetValue("player:" + ballPosition.playerId, out var holder) && holder != null)
                {
                    return holder;
                }
            }

            if (currentState == null || currentState.players == null)
            {
                return null;
            }

            var livePlayers = currentState.players;
            for (var index = 0; index < livePlayers.Length; index += 1)
            {
                var livePlayer = livePlayers[index];
                if (livePlayer == null || livePlayer.isBall || !livePlayer.hasPossession)
                {
                    continue;
                }

                if (TryGetBoundPlayer(livePlayer, out var holder) && holder != null)
                {
                    return holder;
                }
            }

            return null;
        }

        private float ResolveLivePredictionSeconds()
        {
            return currentState == null
                ? 0f
                : Mathf.Clamp(Time.unscaledTime - stateReceivedAt, 0f, LiveStatePredictionMaxSeconds);
        }

        private Vector3 ResolvePredictedFieldPosition(PlayerPosition livePosition, float predictionSeconds)
        {
            var targetPosition = GtexMatchController.MatchManagerAdapter.ResolveFieldPosition(livePosition, currentState);
            if (livePosition == null || predictionSeconds <= 0f || !GtexMatchController.MatchManagerAdapter.IsAvailable)
            {
                return targetPosition;
            }

            targetPosition += ResolveLiveFieldVelocity(livePosition) * predictionSeconds;
            return ClampToFieldBounds(targetPosition, livePosition.isBall);
        }

        private Vector3 ResolveBehaviorDrivenFieldPosition(PlayerPosition livePlayer, Vector3 anchorPosition, Vector3 currentPosition, Vector3 liveVelocity)
        {
            if (livePlayer == null ||
                livePlayer.isBall ||
                !livePlayer.active ||
                currentState == null ||
                currentState.ballPosition == null)
            {
                return anchorPosition;
            }

            var planarVelocity = new Vector3(liveVelocity.x, 0f, liveVelocity.z);
            var ballAnchor = ResolvePredictedFieldPosition(currentState.ballPosition, ResolveLivePredictionSeconds());
            var toBallFromAnchor = ballAnchor - anchorPosition;
            toBallFromAnchor.y = 0f;
            if (toBallFromAnchor.sqrMagnitude <= 0.0001f)
            {
                return anchorPosition;
            }

            var toBallFromCurrent = ballAnchor - currentPosition;
            toBallFromCurrent.y = 0f;
            if (toBallFromCurrent.sqrMagnitude <= 0.0001f)
            {
                toBallFromCurrent = toBallFromAnchor;
            }

            var stateName = ((livePlayer.state ?? string.Empty).Trim().ToLowerInvariant());
            var eventType = ResolveActiveEventTypeToken();
            var possessionSide = ResolvePossessionSideToken();
            var attackSide = possessionSide;
            var playerTeamSide = NormalizeTeamSideToken(livePlayer.teamSide);
            var looseBall =
                string.IsNullOrWhiteSpace(possessionSide) ||
                currentState.ballPosition == null ||
                string.IsNullOrWhiteSpace(currentState.ballPosition.playerId);
            var roleBucket = ResolveLiveRoleBucket(livePlayer);
            var attackDirection = ResolveAttackDirection(livePlayer);
            var lateralDirection = Vector3.Cross(Vector3.up, attackDirection).normalized;
            var speedRatio = Mathf.Max(Mathf.Clamp01(livePlayer.speedRatio), LiveBehaviorMinSpeedRatio);
            var roamDistance = ResolveBehaviorRoamDistance(roleBucket, speedRatio);
            var ballVelocity = ResolveLiveFieldVelocity(currentState.ballPosition);
            ballVelocity.y = 0f;
            var volatileTransitionPhase =
                !looseBall &&
                ballVelocity.magnitude >= LiveBallPassSpeedUnitsPerSecond * 0.75f &&
                (eventType.Contains("save") ||
                 eventType.Contains("miss") ||
                 eventType.Contains("chance"));
            var looseBallBehavior = looseBall || volatileTransitionPhase;
            var looseBallTravel =
                ballVelocity.sqrMagnitude > 0.0001f
                    ? ballVelocity.normalized
                    : toBallFromCurrent.normalized;
            var projectedLooseBallAnchor =
                looseBallBehavior
                    ? ClampToFieldBounds(
                        ballAnchor + looseBallTravel * Mathf.Min(ballVelocity.magnitude * 2.15f, roamDistance * 0.75f + 1.65f),
                        true)
                    : ballAnchor;
            var chaseAnchor = looseBallBehavior ? projectedLooseBallAnchor : ballAnchor;
            var hasLiveBallIntent = false;
            var liveBallIntentStrength = 0f;
            var liveBallIntentContested = false;
            if (looseBallBehavior &&
                TryResolveLiveBallIntent(
                    out var liveBallIntentAnchor,
                    out var liveBallIntentDirection,
                    out var liveBallIntentSide,
                    out var liveBallIntentIsContested,
                    out liveBallIntentStrength))
            {
                hasLiveBallIntent = true;
                chaseAnchor = Vector3.Lerp(chaseAnchor, liveBallIntentAnchor, 0.82f);
                if (!string.IsNullOrWhiteSpace(liveBallIntentSide))
                {
                    attackSide = liveBallIntentSide;
                }

                if (liveBallIntentDirection.sqrMagnitude > 0.0001f)
                {
                    looseBallTravel = Vector3.Lerp(looseBallTravel, liveBallIntentDirection, 0.75f).normalized;
                }

                roamDistance *= Mathf.Lerp(1f, 1.18f, liveBallIntentStrength);
                liveBallIntentContested = liveBallIntentIsContested;
            }

            var sameTeamAsPossession =
                !string.IsNullOrWhiteSpace(playerTeamSide) &&
                string.Equals(playerTeamSide, attackSide, StringComparison.OrdinalIgnoreCase);
            var toChaseFromAnchor = chaseAnchor - anchorPosition;
            toChaseFromAnchor.y = 0f;
            var toChaseFromCurrent = chaseAnchor - currentPosition;
            toChaseFromCurrent.y = 0f;
            if (toChaseFromCurrent.sqrMagnitude <= 0.0001f)
            {
                toChaseFromCurrent = toBallFromCurrent;
            }
            var sameSideBallRank = ResolveTeamBallRank(livePlayer, currentPosition, chaseAnchor);
            if (sameSideBallRank == int.MaxValue)
            {
                sameSideBallRank = 4;
            }

            var playerSignature = ResolveBehaviorSignature01(livePlayer, roleBucket);
            var laneSign = ResolveBehaviorLaneSign(livePlayer, roleBucket);
            var widthBias =
                lateralDirection *
                laneSign *
                Mathf.Lerp(0.35f, 1.2f, playerSignature) *
                (roleBucket == 3 ? 1.15f : roleBucket == 2 ? 0.95f : 0.7f);
            var baseRecoveryWeight = Mathf.Clamp01(0.3f + sameSideBallRank * 0.12f);
            var recoveryTarget = Vector3.Lerp(currentPosition, anchorPosition, baseRecoveryWeight);
            var teammateRepulsion = ResolveTeammateRepulsion(livePlayer, currentPosition);
            var phaseSeed = Mathf.Lerp(0.5f, 1.35f, playerSignature);
            var roamPhase = Time.unscaledTime * Mathf.Lerp(0.25f, 0.8f, speedRatio) + phaseSeed * 4.1f;
            var microMotion =
                lateralDirection * Mathf.Sin(roamPhase) * roamDistance * 0.08f +
                attackDirection * Mathf.Cos(roamPhase * 0.67f) * roamDistance * 0.05f;
            var attackEvent =
                eventType.Contains("chance") ||
                eventType.Contains("miss") ||
                eventType.Contains("goal") ||
                eventType.Contains("shot") ||
                eventType.Contains("save");
            var defensiveEvent =
                stateName.Contains("press") ||
                stateName.Contains("defend") ||
                eventType.Contains("save") ||
                eventType.Contains("turnover");
            var motionSuppression = Mathf.Clamp01(planarVelocity.magnitude / LiveBehaviorBlendOutSpeedUnitsPerSecond);
            var ballProximity = Mathf.Clamp01(1f - Mathf.Min(toBallFromCurrent.magnitude, 18f) / 18f);
            var baseBehaviorWeight =
                Mathf.Lerp(0.14f, 0.68f, ballProximity) *
                Mathf.Lerp(1f, 0.28f, motionSuppression);

            if (sameSideBallRank == 0)
            {
                baseBehaviorWeight = Mathf.Max(baseBehaviorWeight, 0.42f);
            }
            else if (sameSideBallRank == 1)
            {
                baseBehaviorWeight = Mathf.Max(baseBehaviorWeight, 0.3f);
            }

            if (attackEvent || defensiveEvent)
            {
                baseBehaviorWeight = Mathf.Max(baseBehaviorWeight, 0.26f);
            }

            if (looseBallBehavior)
            {
                baseBehaviorWeight = Mathf.Max(baseBehaviorWeight, 0.58f);
            }

            if (liveBallIntentContested)
            {
                baseBehaviorWeight = Mathf.Max(baseBehaviorWeight, 0.62f);
            }

            if (livePlayer.hasPossession)
            {
                var dribbleTarget =
                    anchorPosition +
                    attackDirection * roamDistance * 0.9f +
                    widthBias * 0.8f +
                    teammateRepulsion * 0.65f +
                    microMotion;
                return BlendBehaviorDrivenTarget(anchorPosition, dribbleTarget, Mathf.Max(baseBehaviorWeight + 0.12f, 0.92f));
            }

            if (roleBucket == 0)
            {
                var keeperOffset =
                    sameTeamAsPossession
                        ? attackDirection * 0.35f + widthBias * 0.1f
                        : toBallFromAnchor.normalized * Mathf.Min(0.9f, toBallFromAnchor.magnitude * 0.08f) + widthBias * 0.08f;
                return BlendBehaviorDrivenTarget(anchorPosition, anchorPosition + keeperOffset, Mathf.Max(baseBehaviorWeight, 0.7f));
            }

            if (looseBallBehavior)
            {
                var looseBallChaseBias = hasLiveBallIntent
                    ? Mathf.Lerp(0.45f, 1.35f, liveBallIntentStrength)
                    : 0.45f;
                if (sameSideBallRank == 0)
                {
                    var chaseTarget =
                        recoveryTarget +
                        toChaseFromCurrent.normalized * Mathf.Min(
                            toChaseFromCurrent.magnitude * (0.94f + looseBallChaseBias * 0.08f),
                            roamDistance * 0.95f + 1.65f + looseBallChaseBias) +
                        looseBallTravel * Mathf.Min(ballVelocity.magnitude * (0.55f + looseBallChaseBias * 0.12f), 1.35f) +
                        widthBias * 0.14f +
                        teammateRepulsion * 0.85f +
                        microMotion;
                    return BlendBehaviorDrivenTarget(anchorPosition, chaseTarget, Mathf.Max(baseBehaviorWeight + 0.18f, 0.82f));
                }

                if (sameSideBallRank == 1)
                {
                    if (sameTeamAsPossession)
                    {
                        var supportTarget =
                            Vector3.Lerp(recoveryTarget, chaseAnchor, 0.62f) +
                            attackDirection * (0.45f + looseBallChaseBias * 0.25f) +
                            looseBallTravel * Mathf.Min(ballVelocity.magnitude * 0.4f, 0.85f) +
                            widthBias * 0.95f +
                            teammateRepulsion * 0.7f +
                            microMotion;
                        return BlendBehaviorDrivenTarget(anchorPosition, supportTarget, Mathf.Max(baseBehaviorWeight + 0.12f, 0.68f));
                    }

                    var interceptTarget =
                        Vector3.Lerp(recoveryTarget, chaseAnchor, 0.56f) -
                        attackDirection * 0.2f +
                        looseBallTravel * Mathf.Min(ballVelocity.magnitude * 0.3f, 0.55f) +
                        widthBias * 0.3f +
                        teammateRepulsion * 0.65f +
                        microMotion;
                    return BlendBehaviorDrivenTarget(anchorPosition, interceptTarget, Mathf.Max(baseBehaviorWeight + 0.08f, 0.64f));
                }

                if (sameSideBallRank == 2)
                {
                    if (sameTeamAsPossession)
                    {
                        var thirdManTarget =
                            Vector3.Lerp(currentPosition, chaseAnchor, 0.34f) +
                            attackDirection * (roleBucket == 1 ? 0.2f : roleBucket == 2 ? 0.55f : 0.85f) +
                            widthBias * 0.95f +
                            teammateRepulsion * 0.55f +
                            microMotion;
                        return BlendBehaviorDrivenTarget(anchorPosition, thirdManTarget, Mathf.Max(baseBehaviorWeight + 0.05f, 0.58f));
                    }

                    var collapseTarget =
                        Vector3.Lerp(anchorPosition, chaseAnchor, 0.38f) -
                        attackDirection * (roleBucket == 1 ? 0.3f : 0.15f) +
                        widthBias * 0.18f +
                        teammateRepulsion * 0.45f +
                        microMotion;
                    return BlendBehaviorDrivenTarget(anchorPosition, collapseTarget, Mathf.Max(baseBehaviorWeight, 0.56f));
                }

                if (sameTeamAsPossession)
                {
                    var receivingShapeTarget =
                        anchorPosition +
                        toChaseFromAnchor.normalized * Mathf.Min(toChaseFromAnchor.magnitude * 0.42f, 1.35f) +
                        attackDirection * (roleBucket == 1 ? 0.2f : roleBucket == 2 ? 0.5f : 0.8f) +
                        widthBias * 0.7f +
                        teammateRepulsion * 0.45f +
                        microMotion;
                    return BlendBehaviorDrivenTarget(anchorPosition, receivingShapeTarget, Mathf.Max(baseBehaviorWeight, 0.46f));
                }

                var contestCompression = liveBallIntentContested ? 0.18f : 0f;
                var looseShapeTarget =
                    anchorPosition +
                    toChaseFromAnchor.normalized * Mathf.Min(toChaseFromAnchor.magnitude * (0.26f + contestCompression), 1.15f) -
                    attackDirection * (roleBucket == 1 ? 0.25f : 0.1f) +
                    widthBias * 0.12f +
                    teammateRepulsion * 0.45f +
                    microMotion;
                return BlendBehaviorDrivenTarget(anchorPosition, looseShapeTarget, Mathf.Max(baseBehaviorWeight, 0.44f));
            }

            if (sameTeamAsPossession || stateName.Contains("attack") || stateName.Contains("move"))
            {
                if (sameSideBallRank == 0)
                {
                    var receiveTarget =
                        recoveryTarget +
                        toBallFromCurrent.normalized * Mathf.Min(toBallFromCurrent.magnitude * 0.62f, 1.55f + roamDistance * 0.3f) +
                        attackDirection * (roleBucket == 3 ? 1.2f : roleBucket == 2 ? 0.8f : 0.45f) +
                        widthBias * 0.85f +
                        teammateRepulsion +
                        microMotion;
                    return BlendBehaviorDrivenTarget(anchorPosition, receiveTarget, Mathf.Max(baseBehaviorWeight + 0.08f, 0.7f));
                }

                if (sameSideBallRank == 1)
                {
                    var overlapTarget =
                        anchorPosition +
                        toBallFromAnchor.normalized * Mathf.Min(toBallFromAnchor.magnitude * 0.48f, 1.1f) +
                        attackDirection * (roleBucket == 3 ? 1.55f : 0.95f) +
                        widthBias * 1.25f +
                        teammateRepulsion * 0.65f +
                        microMotion;
                    return BlendBehaviorDrivenTarget(anchorPosition, overlapTarget, Mathf.Max(baseBehaviorWeight + 0.05f, 0.62f));
                }

                if (sameSideBallRank == 2)
                {
                    var recycleTarget =
                        Vector3.Lerp(currentPosition, anchorPosition, 0.55f) +
                        attackDirection * (roleBucket == 1 ? 0.15f : 0.45f) +
                        widthBias * 0.55f +
                        teammateRepulsion * 0.5f +
                        microMotion;
                    return BlendBehaviorDrivenTarget(anchorPosition, recycleTarget, Mathf.Max(baseBehaviorWeight, 0.48f));
                }

                var shapeTarget =
                    anchorPosition +
                    attackDirection * (roleBucket == 1 ? 0.05f : roleBucket == 2 ? 0.25f : 0.5f) +
                    widthBias * 0.35f +
                    teammateRepulsion * 0.35f +
                    microMotion;
                return BlendBehaviorDrivenTarget(anchorPosition, shapeTarget, Mathf.Max(baseBehaviorWeight, 0.3f));
            }

            var ballGoalSideOffset = -attackDirection * (roleBucket == 1 ? 0.75f : roleBucket == 2 ? 0.45f : 0.2f);
            if (sameSideBallRank == 0)
            {
                var pressDistance = Mathf.Min(
                    toBallFromCurrent.magnitude * (defensiveEvent ? 0.92f : 0.82f),
                    1.55f + roamDistance * 0.25f);
                var pressTarget =
                    recoveryTarget +
                    toBallFromCurrent.normalized * pressDistance +
                    ballGoalSideOffset * 0.35f +
                    widthBias * 0.2f +
                    teammateRepulsion * 0.85f +
                    microMotion;
                return BlendBehaviorDrivenTarget(anchorPosition, pressTarget, Mathf.Max(baseBehaviorWeight + 0.08f, 0.62f));
            }

            if (sameSideBallRank == 1)
            {
                var coverTarget =
                    Vector3.Lerp(anchorPosition, ballAnchor, 0.58f) +
                    ballGoalSideOffset +
                    widthBias * 0.6f +
                    teammateRepulsion * 0.55f +
                    microMotion;
                return BlendBehaviorDrivenTarget(anchorPosition, coverTarget, Mathf.Max(baseBehaviorWeight, 0.48f));
            }

            if (sameSideBallRank == 2)
            {
                var interceptTarget =
                    Vector3.Lerp(anchorPosition, ballAnchor, 0.45f) +
                    ballGoalSideOffset * 1.2f +
                    widthBias * 0.85f +
                    teammateRepulsion * 0.45f +
                    microMotion;
                return BlendBehaviorDrivenTarget(anchorPosition, interceptTarget, Mathf.Max(baseBehaviorWeight, 0.42f));
            }

            var defensiveTarget =
                Vector3.Lerp(currentPosition, anchorPosition, 0.7f) +
                ballGoalSideOffset * (roleBucket == 1 ? 1.1f : 0.8f) +
                widthBias * 0.3f +
                teammateRepulsion * 0.25f +
                microMotion * 0.5f;
            return BlendBehaviorDrivenTarget(anchorPosition, defensiveTarget, Mathf.Max(baseBehaviorWeight, 0.24f));
        }

        private Vector3 BlendBehaviorDrivenTarget(Vector3 anchorPosition, Vector3 desiredTarget, float behaviorWeight)
        {
            var clampedAnchor = ClampToFieldBounds(anchorPosition, false);
            var clampedTarget = ClampToFieldBounds(desiredTarget, false);
            var weight = Mathf.Clamp01(behaviorWeight);
            if (weight <= 0.0001f)
            {
                return clampedAnchor;
            }

            return ClampToFieldBounds(Vector3.Lerp(clampedAnchor, clampedTarget, weight), false);
        }

        private Vector3 ResolveLiveFieldVelocity(PlayerPosition livePosition)
        {
            if (livePosition == null || currentState == null || !GtexMatchController.MatchManagerAdapter.IsAvailable)
            {
                return Vector3.zero;
            }

            var velocity = GtexMatchController.MatchManagerAdapter.ResolveFieldVelocity(livePosition, currentState);
            if (!livePosition.isBall)
            {
                velocity.y = 0f;
            }

            return velocity;
        }

        private Vector3 ClampToFieldBounds(Vector3 position, bool isBall)
        {
            var fieldSize = GtexMatchController.MatchManagerAdapter.FieldSize;
            if (fieldSize != Vector2.zero)
            {
                position.x = Mathf.Clamp(position.x, 0f, fieldSize.x);
                position.z = Mathf.Clamp(position.z, 0f, fieldSize.y);
            }

            position.y = isBall ? Mathf.Max(0.1f, position.y) : 0f;
            return position;
        }

        private static Vector3 ResolveAttackDirection(PlayerPosition livePlayer)
        {
            var teamSide = (livePlayer != null ? livePlayer.teamSide : string.Empty) ?? string.Empty;
            return ResolveAttackDirection(teamSide);
        }

        private static Vector3 ResolveAttackDirection(string teamSide)
        {
            return NormalizeTeamSideToken(teamSide) == "away"
                ? Vector3.left
                : Vector3.right;
        }

        private string ResolvePossessionSideToken()
        {
            var normalized = NormalizeTeamSideToken(currentState != null ? currentState.possessionSide : string.Empty);
            if (!string.IsNullOrWhiteSpace(normalized))
            {
                return normalized;
            }

            var ballPlayerId = currentState != null && currentState.ballPosition != null
                ? currentState.ballPosition.playerId
                : string.Empty;
            if (!string.IsNullOrWhiteSpace(ballPlayerId) && currentState != null && currentState.players != null)
            {
                var livePlayers = currentState.players;
                for (var index = 0; index < livePlayers.Length; index += 1)
                {
                    var livePlayer = livePlayers[index];
                    if (livePlayer == null || livePlayer.isBall)
                    {
                        continue;
                    }

                    if (string.Equals(livePlayer.playerId, ballPlayerId, StringComparison.Ordinal))
                    {
                        return NormalizeTeamSideToken(livePlayer.teamSide);
                    }
                }
            }

            if (currentState != null && currentState.players != null)
            {
                var livePlayers = currentState.players;
                for (var index = 0; index < livePlayers.Length; index += 1)
                {
                    var livePlayer = livePlayers[index];
                    if (livePlayer == null || livePlayer.isBall || !livePlayer.hasPossession)
                    {
                        continue;
                    }

                    return NormalizeTeamSideToken(livePlayer.teamSide);
                }
            }

            return string.Empty;
        }

        private string ResolveActiveEventTypeToken()
        {
            var activeEvent = currentState != null ? currentState.ResolveActiveEvent() : null;
            return NormalizeActiveEventTypeToken(currentState, activeEvent);
        }

        private static string NormalizeTeamSideToken(string teamSide)
        {
            var normalized = (teamSide ?? string.Empty).Trim().ToLowerInvariant();
            switch (normalized)
            {
                case "home":
                case "0":
                case "team1":
                case "team_1":
                    return "home";
                case "away":
                case "1":
                case "team2":
                case "team_2":
                    return "away";
                default:
                    return string.Empty;
            }
        }

        private static float ResolveBehaviorRoamDistance(int roleBucket, float speedRatio)
        {
            switch (roleBucket)
            {
                case 0:
                    return 0.75f;
                case 1:
                    return Mathf.Lerp(LiveBehaviorMinRoamDistance, 3f, speedRatio);
                case 2:
                    return Mathf.Lerp(LiveBehaviorMinRoamDistance + 0.35f, 3.85f, speedRatio);
                case 3:
                    return Mathf.Lerp(LiveBehaviorMinRoamDistance + 0.6f, LiveBehaviorMaxRoamDistance, speedRatio);
                default:
                    return Mathf.Lerp(LiveBehaviorMinRoamDistance, 3.5f, speedRatio);
            }
        }

        private int ResolveTeamBallRank(PlayerPosition livePlayer, Vector3 currentPosition, Vector3 ballAnchor)
        {
            if (livePlayer == null ||
                currentState == null ||
                currentState.players == null ||
                !GtexMatchController.MatchManagerAdapter.IsAvailable)
            {
                return int.MaxValue;
            }

            var playerTeamSide = NormalizeTeamSideToken(livePlayer.teamSide);
            if (string.IsNullOrWhiteSpace(playerTeamSide))
            {
                return int.MaxValue;
            }

            currentPosition.y = 0f;
            var playerDistance = (ballAnchor - currentPosition).sqrMagnitude;
            var rank = 0;

            var livePlayers = currentState.players;
            for (var index = 0; index < livePlayers.Length; index += 1)
            {
                var candidate = livePlayers[index];
                if (candidate == null ||
                    candidate.isBall ||
                    !candidate.active ||
                    IsSameLivePlayer(candidate, livePlayer) ||
                    !string.Equals(NormalizeTeamSideToken(candidate.teamSide), playerTeamSide, StringComparison.Ordinal))
                {
                    continue;
                }

                var candidatePosition = ResolveRuntimeFieldPosition(candidate, currentState, Vector3.zero);
                if ((ballAnchor - candidatePosition).sqrMagnitude + 0.01f < playerDistance)
                {
                    rank += 1;
                }
            }

            return rank;
        }

        private Vector3 ResolveTeammateRepulsion(PlayerPosition livePlayer, Vector3 currentPosition)
        {
            if (livePlayer == null ||
                currentState == null ||
                currentState.players == null ||
                !GtexMatchController.MatchManagerAdapter.IsAvailable)
            {
                return Vector3.zero;
            }

            var playerTeamSide = NormalizeTeamSideToken(livePlayer.teamSide);
            if (string.IsNullOrWhiteSpace(playerTeamSide))
            {
                return Vector3.zero;
            }

            currentPosition.y = 0f;
            var repulsion = Vector3.zero;
            var contributors = 0;
            var livePlayers = currentState.players;
            for (var index = 0; index < livePlayers.Length; index += 1)
            {
                var teammate = livePlayers[index];
                if (teammate == null ||
                    teammate.isBall ||
                    !teammate.active ||
                    IsSameLivePlayer(teammate, livePlayer) ||
                    !string.Equals(NormalizeTeamSideToken(teammate.teamSide), playerTeamSide, StringComparison.Ordinal))
                {
                    continue;
                }

                var teammatePosition = ResolveRuntimeFieldPosition(teammate, currentState, Vector3.zero);
                var separation = currentPosition - teammatePosition;
                separation.y = 0f;
                var distance = separation.magnitude;
                if (distance <= 0.001f || distance >= LiveBehaviorTeammateRepulsionRadius)
                {
                    continue;
                }

                repulsion += separation.normalized * ((LiveBehaviorTeammateRepulsionRadius - distance) / LiveBehaviorTeammateRepulsionRadius);
                contributors += 1;
            }

            if (contributors == 0)
            {
                return Vector3.zero;
            }

            repulsion /= contributors;
            repulsion.y = 0f;
            return Vector3.ClampMagnitude(repulsion, 1f);
        }

        private static bool IsSameLivePlayer(PlayerPosition left, PlayerPosition right)
        {
            if (ReferenceEquals(left, right))
            {
                return true;
            }

            if (left == null || right == null)
            {
                return false;
            }

            if (!string.IsNullOrWhiteSpace(left.entityId) &&
                string.Equals(left.entityId, right.entityId, StringComparison.Ordinal))
            {
                return true;
            }

            return !string.IsNullOrWhiteSpace(left.playerId) &&
                   string.Equals(left.playerId, right.playerId, StringComparison.Ordinal);
        }

        private static float ResolveBehaviorSignature01(PlayerPosition livePlayer, int roleBucket)
        {
            var seed = 17;
            if (livePlayer != null)
            {
                seed = seed * 31 + Mathf.Max(0, livePlayer.shirtNumber);
                seed = seed * 31 + ComputeStableTokenHash(livePlayer.playerId);
                seed = seed * 31 + ComputeStableTokenHash(livePlayer.entityId);
                seed = seed * 31 + ComputeStableTokenHash(livePlayer.label);
            }
            else
            {
                seed = seed * 31 + roleBucket + 1;
            }

            seed = Mathf.Abs(seed % 997);
            return seed / 996f;
        }

        private static float ResolveBehaviorLaneSign(PlayerPosition livePlayer, int roleBucket)
        {
            if (livePlayer != null && livePlayer.shirtNumber > 0)
            {
                return (livePlayer.shirtNumber & 1) == 0 ? -1f : 1f;
            }

            return (roleBucket & 1) == 0 ? -1f : 1f;
        }

        private static int ComputeStableTokenHash(string value)
        {
            if (string.IsNullOrEmpty(value))
            {
                return 0;
            }

            unchecked
            {
                var hash = 23;
                for (var index = 0; index < value.Length; index += 1)
                {
                    hash = (hash * 31) + value[index];
                }

                return hash;
            }
        }

        private void TryTriggerLiveBallAction(MatchResponse previousState, MatchResponse nextState)
        {
            if (previousState == null ||
                nextState == null ||
                previousState.ballPosition == null ||
                nextState.ballPosition == null ||
                IsTerminalLiveState(nextState))
            {
                return;
            }

            var previousHolderId = (previousState.ballPosition.playerId ?? string.Empty).Trim();
            var nextHolderId = (nextState.ballPosition.playerId ?? string.Empty).Trim();
            if (string.IsNullOrWhiteSpace(previousHolderId) ||
                string.Equals(previousHolderId, nextHolderId, StringComparison.Ordinal))
            {
                return;
            }

            var liveVelocity = ResolveLiveFieldVelocity(nextState.ballPosition);
            liveVelocity.y = 0f;
            var ballSpeed = liveVelocity.magnitude;
            if (ballSpeed < LiveBallPassSpeedUnitsPerSecond)
            {
                return;
            }

            if (!TryGetBoundPlayerByPlayerId(previousHolderId, out var previousHolder) || previousHolder == null)
            {
                return;
            }

            AppendRuntimeTrace(
                "ball-action",
                "minute=" + nextState.clockMinute.ToString("0.##") +
                " type=pass from=" + previousHolderId +
                " to=" + nextHolderId +
                " speed=" + ballSpeed.ToString("0.##"));
            previousHolder.PlayExternalBallHit(liveVelocity, false);
        }

        private void TryTriggerLiveEventAction(MatchResponse previousState, MatchResponse nextState)
        {
            if (nextState == null || IsTerminalLiveState(nextState))
            {
                return;
            }

            var previousActiveEventId = (previousState != null ? previousState.activeEventId : string.Empty) ?? string.Empty;
            var activeEvent = nextState.ResolveActiveEvent();
            if (activeEvent == null ||
                string.IsNullOrWhiteSpace(activeEvent.id) ||
                string.Equals(previousActiveEventId, activeEvent.id, StringComparison.Ordinal))
            {
                return;
            }

            var eventType = ((activeEvent.type ?? string.Empty).Trim().ToLowerInvariant());
            if (!eventType.Contains("chance") &&
                !eventType.Contains("miss") &&
                !eventType.Contains("goal") &&
                !eventType.Contains("save"))
            {
                return;
            }

            var primaryPlayerId = (activeEvent.primaryPlayerId ?? string.Empty).Trim();
            if (!TryGetBoundPlayerByPlayerId(primaryPlayerId, out var player) || player == null)
            {
                return;
            }

            var ballVelocity = ResolveLiveFieldVelocity(nextState.ballPosition);
            ballVelocity.y = 0f;
            if (ballVelocity.sqrMagnitude <= 0.0001f)
            {
                ballVelocity = player.Forward * LiveBallShotSpeedUnitsPerSecond;
            }

            AppendRuntimeTrace(
                "event-action",
                "minute=" + nextState.clockMinute.ToString("0.##") +
                " type=" + eventType +
                " player=" + primaryPlayerId +
                " speed=" + ballVelocity.magnitude.ToString("0.##"));
            player.PlayExternalBallHit(ballVelocity, true);
        }

        private static Vector3 ResolveLookDirection(PlayerPosition livePlayer, Vector3 movementDelta, GtexLegacyPlayerHandle player)
        {
            if (livePlayer != null)
            {
                var explicitFacing = new Vector3(livePlayer.facingX, 0f, livePlayer.facingZ);
                if (explicitFacing.sqrMagnitude > 0.0001f)
                {
                    return explicitFacing;
                }
            }

            if (movementDelta.sqrMagnitude > 0.0001f)
            {
                return movementDelta;
            }

            return player != null && player.IsValid
                ? player.Forward
                : Vector3.forward;
        }

        private static float ResolveLivePlayerMoveSpeed(PlayerPosition livePlayer, Vector3 currentPosition, Vector3 targetPosition, Vector3 liveVelocity)
        {
            var distance = Vector3.Distance(currentPosition, targetPosition);
            var speedRatio = livePlayer != null ? Mathf.Clamp01(livePlayer.speedRatio) : 0f;
            var speed = Mathf.Lerp(LivePlayerMinSpeedUnitsPerSecond, LivePlayerMaxSpeedUnitsPerSecond, speedRatio);
            speed = Mathf.Max(speed, new Vector3(liveVelocity.x, 0f, liveVelocity.z).magnitude);

            if (distance > 1f)
            {
                speed = Mathf.Max(speed, distance / LivePlayerCatchUpSeconds);
            }

            return speed;
        }

        private static int ResolveLiveRoleBucket(PlayerPosition livePlayer)
        {
            var role = (livePlayer != null ? livePlayer.role : string.Empty) ?? string.Empty;
            switch (role.Trim().ToUpperInvariant())
            {
                case "GK":
                    return 0;
                case "DF":
                    return 1;
                case "MF":
                    return 2;
                case "FW":
                    return 3;
            }

            var line = ((livePlayer != null ? livePlayer.line : string.Empty) ?? string.Empty).Trim().ToLowerInvariant();
            if (line.Contains("back") || line.Contains("def"))
            {
                return 1;
            }

            if (line.Contains("mid"))
            {
                return 2;
            }

            if (line.Contains("front") || line.Contains("att"))
            {
                return 3;
            }

            return 2;
        }

        private static int ResolveEngineRoleBucket(Positions position)
        {
            if ((position & Positions.GK) != 0)
            {
                return 0;
            }

            if ((position & (Positions.CB | Positions.CB_L | Positions.CB_R | Positions.LB | Positions.RB)) != 0)
            {
                return 1;
            }

            if ((position & (
                    Positions.DMF |
                    Positions.DMF_L |
                    Positions.DMF_R |
                    Positions.CM |
                    Positions.CM_L |
                    Positions.CM_R |
                    Positions.LMF |
                    Positions.RMF |
                    Positions.AMF |
                    Positions.AMF_L |
                    Positions.AMF_R)) != 0)
            {
                return 2;
            }

            if ((position & (Positions.LW | Positions.RW | Positions.ST | Positions.ST_L | Positions.ST_R)) != 0)
            {
                return 3;
            }

            return 2;
        }

        private static string ResolveBindingStorageKey(PlayerPosition livePlayer)
        {
            if (livePlayer == null)
            {
                return string.Empty;
            }

            if (!string.IsNullOrWhiteSpace(livePlayer.entityId))
            {
                return livePlayer.entityId;
            }

            if (!string.IsNullOrWhiteSpace(livePlayer.playerId))
            {
                return "player:" + livePlayer.playerId;
            }

            return string.Empty;
        }

        // =========================
        // CLEANUP
        // =========================

        private void OnDestroy()
        {
            AppendRuntimeTrace("shutdown", BuildRuntimeTraceSummary());
            FlushRuntimeTrace(true);
            GtexMatchController.ReportRuntimeState(
                config,
                GtexRuntimeMode.LivePlayback,
                currentState != null ? ResolveControllerPhase(currentState) : GtexMatchPhase.None,
                false,
                nameof(GtexMatchRuntime),
                "Live runtime destroyed.");
            isDestroyed = true;
            usingWebSocket = false;
            isConnectingWebSocket = false;
            DisposeSocket();
        }

        private void DisposeSocket()
        {
            try
            {
                socketToken?.Cancel();
                socket?.Dispose();
            }
            catch
            {
            }
            finally
            {
                socketToken?.Dispose();
                socketToken = null;
                socket = null;
            }
        }

        private void HandleBootstrapTaskFailure(string label, string message)
        {
            bootstrapTaskFailed = true;
            var operation = string.IsNullOrWhiteSpace(label) ? "bootstrap task" : label;
            var failureMessage = operation + " failed: " + message;
            AppendRuntimeTrace("error", failureMessage);
            FlushRuntimeTrace(true);
            RegisterTransportFailure("bootstrap", failureMessage, 0, false);
            GtexMatchController.ReportRuntimeState(
                config,
                GtexRuntimeMode.LivePlayback,
                GtexMatchPhase.Failed,
                false,
                nameof(GtexMatchRuntime),
                failureMessage);
        }

        private IEnumerator AwaitTask(Task task, string label)
        {
            if (task == null)
            {
                HandleBootstrapTaskFailure(label, "Operation did not start.");
                yield break;
            }

            while (!task.IsCompleted) yield return null;

            if (task.IsCanceled)
            {
                HandleBootstrapTaskFailure(label, "Operation was canceled.");
                yield break;
            }

            if (task.IsFaulted)
            {
                HandleBootstrapTaskFailure(
                    label,
                    task.Exception?.GetBaseException()?.Message ?? "Unknown failure.");
            }
        }
    }
}
