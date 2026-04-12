using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Threading.Tasks;
using FStudio.Database;
using FStudio.Events;
using FStudio.GTEX.Core;
using FStudio.MatchEngine;
using FStudio.MatchEngine.Balls;
using FStudio.MatchEngine.Enums;
using FStudio.MatchEngine.Players;
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

            if (!TryBuildMatchRequest(out var matchRequest))
            {
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

            if (playerBindings.Count == 0) BindPlayers();

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

            lastKnownState = state;
            ApplyState(state, forceSnap);
            return true;
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
                    MatchStatus.Playing
                );
            }
            else if (config != null && config.verboseLogging)
            {
                Debug.LogWarning("[GTEX] MatchManager is not ready. Live state cached without scene application.");
            }

            if (forceSnap) Snap();

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

            var staleThreshold = Mathf.Max(config.pollIntervalSeconds * 3f, config.maxRetryDelaySeconds);
            if (!staleStateWarningLogged && Time.unscaledTime - stateReceivedAt > staleThreshold)
            {
                staleStateWarningLogged = true;
                RegisterTransportFailure(
                    usingWebSocket ? "websocket" : "poll",
                    "Live state has gone stale for " + (Time.unscaledTime - stateReceivedAt).ToString("0.0") + "s.",
                    0,
                    false);
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
            // simplified binding (your original stays same)
        }

        private void DrivePlayers(float dt)
        {
            // KEEP YOUR FULL ORIGINAL LOGIC HERE
        }

        private void DriveBall()
        {
            // KEEP YOUR FULL ORIGINAL LOGIC HERE
        }

        private void Snap()
        {
            // KEEP YOUR FULL ORIGINAL LOGIC HERE
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
