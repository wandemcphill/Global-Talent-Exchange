using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Threading.Tasks;
using System.Linq;
using FStudio.Database;
using FStudio.Events;
using FStudio.GTEX.Core;
using FStudio.MatchEngine;
using FStudio.MatchEngine.Balls;
using FStudio.Data;
using FStudio.MatchEngine.Enums;
using FStudio.MatchEngine.Players;
using FStudio.MatchEngine.Players.PlayerController;
using FStudio.UI;
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
        private const float LivePlayerSnapDistance = 8f;
        private const float LivePlayerCatchUpSeconds = 0.35f;
        private const float LivePlayerMinSpeedUnitsPerSecond = 3f;
        private const float LivePlayerMaxSpeedUnitsPerSecond = 8f;
        private const float LivePlayerRotationLerpSpeed = 10f;
        private const float LiveAnimatorMoveSpeedScale = 6f;

        private GtexMatchConfig config;
        private MatchAPI api;

        private ClientWebSocket socket;
        private CancellationTokenSource socketToken;

        private MatchResponse currentState;
        private MatchResponse lastKnownState;

        private bool matchLoaded;
        private bool usingWebSocket;

        private readonly Dictionary<string, PlayerBase> playerBindings = new();
        private readonly Dictionary<string, string> lastAnimationStates = new();

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
        }

        private void Awake()
        {
            Debug.Log(
                "[GTEX] Mode: " +
                GtexConfig.Mode +
                (GtexConfig.IsFastMode ? " (FAST MODE)" : string.Empty));

            ApplyBootstrapGuardsForCurrentContext();
        }

        private void Start()
        {
            if (skipBootstrap)
            {
                return;
            }

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

            if (MatchEngineLoader.Current == null || UILoader.Current == null)
            {
                RegisterTransportFailure(
                    "bootstrap",
                    "GTEX live runtime could not find the required scene dependencies before starting the match.",
                    0,
                    false);
                yield break;
            }

            yield return AwaitTask(MatchEngineLoader.CreateMatch(matchRequest));

            yield return AwaitTask(
                MatchEngineLoader.Current.StartMatchEngine(
                    new UpcomingMatchEvent(matchRequest),
                    false,
                    false
                )
            );

            if (MatchManager.Current != null)
            {
                MatchManager.Current.SetExternalPlayback(true);
            }
            else if (config != null && config.verboseLogging)
            {
                Debug.LogWarning("[GTEX] MatchManager is not available during live bootstrap. Runtime will continue caching live state.");
            }

            BindPlayers();
            TryConsumeLiveState(lastKnownState, true);

            matchLoaded = true;

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
                if (MatchEngineLoader.Current != null && UILoader.Current != null)
                {
                    yield break;
                }

                if (Time.realtimeSinceStartup - waitStartedAt >= SceneDependencyWaitTimeoutSeconds)
                {
                    Debug.LogWarning(
                        "[GTEX] Timed out waiting for scene dependencies. " +
                        "MatchEngineLoader present=" + (MatchEngineLoader.Current != null) +
                        ", UILoader present=" + (UILoader.Current != null) + ".");
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

            if (!matchLoaded || currentState == null) return;

            if (NeedsPlayerBindingRefresh()) BindPlayers();

            DrivePlayers(Time.deltaTime);
            DriveBall();
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
            }

            return true;
        }

        private static int ResolveStateSequence(MatchResponse state)
        {
            var activeEvent = state != null ? state.ResolveActiveEvent() : null;
            return activeEvent != null ? activeEvent.sequence : -1;
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

        private void ApplyState(MatchResponse state, bool forceSnap)
        {

            if (state == null) return;

            currentState = state;
            stateReceivedAt = Time.unscaledTime;
            staleStateWarningLogged = false;
            consecutiveTransportFailures = 0;
            lastTransportError = string.Empty;

            if (MatchManager.Current != null)
            {
                MatchManager.Current.ApplyExternalLiveState(
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

            if (forceSnap) Snap();

            EventManager.Trigger(new GtexLiveStateEvent(state, !usingWebSocket));

            Debug.Log($"[GTEX] Live: {state.clockMinute}' {state.homeScore}-{state.awayScore}");
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

            if (currentState == null || MatchManager.Current == null)
            {
                return;
            }

            BindPlayersForSide(FilterLivePlayersBySide("home"), MatchManager.Current.GameTeam1);
            BindPlayersForSide(FilterLivePlayersBySide("away"), MatchManager.Current.GameTeam2);

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

                ApplyLivePlayerState(livePlayer, player, dt, false);
            }
        }

        private void DriveBall()
        {
            if (currentState == null || currentState.ballPosition == null || MatchManager.Current == null || Ball.Current == null)
            {
                return;
            }

            Ball.Current.ApplyExternalState(
                ResolveFieldPosition(currentState.ballPosition),
                ResolveFieldVelocity(currentState.ballPosition),
                ResolveBallHolder(currentState.ballPosition));
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

                ApplyLivePlayerState(livePlayer, player, 0f, true);
            }

            DriveBall();
        }

        private bool NeedsPlayerBindingRefresh()
        {
            if (currentState == null || currentState.players == null || MatchManager.Current == null)
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

        private void BindPlayersForSide(PlayerPosition[] livePlayers, GameTeam gameTeam)
        {
            if (livePlayers == null || livePlayers.Length == 0 || gameTeam == null || gameTeam.GamePlayers == null)
            {
                return;
            }

            var availablePlayers = new List<PlayerBase>(gameTeam.GamePlayers.Where(player => player != null));
            foreach (var livePlayer in livePlayers
                .OrderBy(ResolveLiveRoleBucket)
                .ThenBy(player => player.z)
                .ThenBy(player => player.x))
            {
                if (availablePlayers.Count == 0)
                {
                    break;
                }

                var targetPosition = ResolveFieldPosition(livePlayer);
                PlayerBase bestCandidate = null;
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

            return currentState.players
                .Where(player =>
                    player != null &&
                    !player.isBall &&
                    string.Equals(player.teamSide, teamSide, StringComparison.OrdinalIgnoreCase))
                .ToArray();
        }

        private float ScoreBindingCandidate(PlayerPosition livePlayer, PlayerBase candidate, Vector3 targetPosition)
        {
            if (candidate == null || candidate.MatchPlayer == null)
            {
                return float.MaxValue;
            }

            var score = Vector3.Distance(candidate.Position, targetPosition);

            if (ResolveLiveRoleBucket(livePlayer) != ResolveEngineRoleBucket(candidate.MatchPlayer.Position))
            {
                score += 25f;
            }

            if (!string.IsNullOrWhiteSpace(livePlayer.playerId) &&
                int.TryParse(livePlayer.playerId, out var livePlayerId) &&
                candidate.MatchPlayer.Player != null &&
                candidate.MatchPlayer.Player.id == livePlayerId)
            {
                score -= 100f;
            }

            if (livePlayer.shirtNumber > 0 && candidate.MatchPlayer.Number == livePlayer.shirtNumber)
            {
                score -= 10f;
            }

            return score;
        }

        private void StorePlayerBinding(PlayerPosition livePlayer, PlayerBase player)
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

        private bool TryGetBoundPlayer(PlayerPosition livePlayer, out PlayerBase player)
        {
            if (livePlayer != null)
            {
                if (!string.IsNullOrWhiteSpace(livePlayer.entityId) &&
                    playerBindings.TryGetValue(livePlayer.entityId, out player) &&
                    player != null)
                {
                    return true;
                }

                if (!string.IsNullOrWhiteSpace(livePlayer.playerId) &&
                    playerBindings.TryGetValue("player:" + livePlayer.playerId, out player) &&
                    player != null)
                {
                    return true;
                }
            }

            player = null;
            return false;
        }

        private void ApplyLivePlayerState(PlayerPosition livePlayer, PlayerBase player, float dt, bool snap)
        {
            if (livePlayer == null || player == null || player.PlayerController == null)
            {
                return;
            }

            var currentPosition = player.Position;
            var targetPosition = ResolveFieldPosition(livePlayer);

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
                    ResolveLivePlayerMoveSpeed(livePlayer, currentPosition, targetPosition) * Mathf.Max(dt, 0f));
            }

            player.PlayerController.SetInstantPosition(appliedPosition);

            var lookDirection = ResolveLookDirection(livePlayer, appliedPosition - currentPosition, player);
            if (lookDirection.sqrMagnitude > 0.0001f)
            {
                var targetRotation = Quaternion.LookRotation(lookDirection.normalized, Vector3.up);
                var appliedRotation = snap
                    ? targetRotation
                    : Quaternion.Slerp(player.Rotation, targetRotation, Mathf.Clamp01(dt * LivePlayerRotationLerpSpeed));
                player.PlayerController.SetInstantRotation(appliedRotation);
            }

            ApplyLiveAnimatorState(livePlayer, player, appliedPosition - currentPosition, dt, snap);
        }

        private void ApplyLiveAnimatorState(PlayerPosition livePlayer, PlayerBase player, Vector3 frameMovement, float dt, bool snap)
        {
            var animator = player.PlayerController != null ? player.PlayerController.Animator : null;
            if (animator == null)
            {
                return;
            }

            var animationState = (livePlayer.animationState ?? string.Empty).Trim().ToLowerInvariant();
            var explicitIdle =
                !livePlayer.active ||
                animationState == "idle" ||
                animationState == "set_piece" ||
                animationState == "sent_off" ||
                animationState == "save" ||
                animationState == "celebrate";

            var movement = snap ? Vector3.zero : frameMovement;
            var moveSpeed = 0f;
            var localDirection = Vector3.zero;

            if (!explicitIdle && movement.sqrMagnitude > 0.0001f && dt > 0f)
            {
                moveSpeed = Mathf.Clamp01(
                    Mathf.Max(
                        Mathf.Clamp01(livePlayer.speedRatio),
                        movement.magnitude / Mathf.Max(dt * LiveAnimatorMoveSpeedScale, 0.001f)));

                localDirection = player.PlayerController.UnityObject.transform.InverseTransformDirection(movement.normalized);
            }

            animator.SetBool(PlayerAnimatorVariable.IsHoldingBall, livePlayer.hasPossession);
            animator.SetFloat(PlayerAnimatorVariable.MoveSpeed, explicitIdle ? 0f : moveSpeed);
            animator.SetFloat(PlayerAnimatorVariable.Horizontal, moveSpeed > 0.01f ? Mathf.Clamp(localDirection.x, -1f, 1f) : 0f);
            animator.SetFloat(PlayerAnimatorVariable.Vertical, moveSpeed > 0.01f ? Mathf.Clamp(localDirection.z, -1f, 1f) : 0f);

            var bindingKey = ResolveBindingStorageKey(livePlayer);
            if (!string.IsNullOrWhiteSpace(bindingKey))
            {
                lastAnimationStates[bindingKey] = animationState;
            }
        }

        private Vector3 ResolveFieldPosition(PlayerPosition livePosition)
        {
            if (MatchManager.Current == null || livePosition == null)
            {
                return Vector3.zero;
            }

            var pitchLength = currentState != null ? Mathf.Max(1f, currentState.pitchLengthMeters) : 105f;
            var pitchWidth = currentState != null ? Mathf.Max(1f, currentState.pitchWidthMeters) : 68f;
            var fieldSize = MatchManager.Current.SizeOfField;

            var normalizedX = Mathf.InverseLerp(-pitchLength * 0.5f, pitchLength * 0.5f, livePosition.x);
            var normalizedZ = Mathf.InverseLerp(-pitchWidth * 0.5f, pitchWidth * 0.5f, livePosition.z);

            return new Vector3(
                normalizedX * fieldSize.x,
                livePosition.isBall ? Mathf.Max(0.1f, livePosition.y) : 0f,
                normalizedZ * fieldSize.y);
        }

        private Vector3 ResolveFieldVelocity(PlayerPosition livePosition)
        {
            if (MatchManager.Current == null || livePosition == null)
            {
                return Vector3.zero;
            }

            var pitchLength = currentState != null ? Mathf.Max(1f, currentState.pitchLengthMeters) : 105f;
            var pitchWidth = currentState != null ? Mathf.Max(1f, currentState.pitchWidthMeters) : 68f;
            var fieldSize = MatchManager.Current.SizeOfField;

            return new Vector3(
                (livePosition.velocityX / pitchLength) * fieldSize.x,
                livePosition.velocityY,
                (livePosition.velocityZ / pitchWidth) * fieldSize.y);
        }

        private PlayerBase ResolveBallHolder(PlayerPosition ballPosition)
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

        private static Vector3 ResolveLookDirection(PlayerPosition livePlayer, Vector3 movementDelta, PlayerBase player)
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

            return player != null && player.PlayerController != null
                ? player.PlayerController.Forward
                : Vector3.forward;
        }

        private static float ResolveLivePlayerMoveSpeed(PlayerPosition livePlayer, Vector3 currentPosition, Vector3 targetPosition)
        {
            var distance = Vector3.Distance(currentPosition, targetPosition);
            var speedRatio = livePlayer != null ? Mathf.Clamp01(livePlayer.speedRatio) : 0f;
            var speed = Mathf.Lerp(LivePlayerMinSpeedUnitsPerSecond, LivePlayerMaxSpeedUnitsPerSecond, speedRatio);

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

        private IEnumerator AwaitTask(Task task)
        {
            while (!task.IsCompleted) yield return null;
        }
    }
}
