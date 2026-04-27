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
using FStudio.GTEX.Playback;
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
            private const float LivePlayerCatchUpSeconds = 0.45f;
            private const float LivePlayerMinSpeedUnitsPerSecond = 3f;
            private const float LivePlayerMaxSpeedUnitsPerSecond = 8f;
        private const float LivePlayerRotationLerpSpeed = 10f;
        private const float LiveAnimatorIdlePlanarSpeedUnitsPerSecond = 0.18f;
        private const float LiveAnimatorLocomotionPlanarSpeedUnitsPerSecond = 0.42f;
        private const float LiveStatePredictionMaxSeconds = 0.35f;
            private const float LiveBallPassSpeedUnitsPerSecond = 0.5f;
            private const float LiveBallShotSpeedUnitsPerSecond = 1.25f;
            private const float PlaybackTraceSampleIntervalSeconds = 2f;
            private const float LiveBehaviorMinRoamDistance = 1f;
            private const float LiveBehaviorMaxRoamDistance = 4.75f;
            private const float LiveBehaviorMinSpeedRatio = 0.2f;
            private const float LiveBehaviorTeammateRepulsionRadius = 4.6f;
            private const float LiveBehaviorBlendOutSpeedUnitsPerSecond = 2.75f;
            private const float LiveBehaviorEventStaleSeconds = 7.5f;
            private const float LiveBehaviorEventStaleClockMinutes = 1.25f;
            private const float LiveBallIntentMinLifetimeSeconds = 6f;
            private const float LiveBallIntentMaxLifetimeSeconds = 14f;
            private const float LiveBallIntentFallbackTravelDistance = 4.25f;
            private const float LivePlayerIntentMinLifetimeSeconds = 1.15f;
        private const float LivePlayerIntentMaxLifetimeSeconds = 3.05f;
        private const float LivePlayerIntentFilterSharpness = 4.35f;
        private const float LivePlayerIntentRetargetSpeed = 4.25f;
        private const float LivePlayerShapeHoldWeight = 0.16f;
        private const float LivePlayerShapeHoldDefensiveWeight = 0.22f;
        private const float LivePlayerIntentOpponentPressureRadius = 4.6f;
            private const float LiveTransitReceiverLeadSeconds = 0.24f;
            private const float LiveTransitReceiverLeadDistance = 1.7f;
            private const float LiveMotionBoundaryDurationSeconds = 0.24f;
            private const float LivePhaseBoundaryDurationSeconds = 0.85f;
            private const float LiveTargetFilterSharpness = 11f;
            private const float LiveSettledTargetFilterSharpness = 6.5f;
            private const float LiveTraceDtFloorSeconds = 1f / 30f;
            private const float LiveBallPlaybackMaxPassSpeed = 7.25f;
            private const float LiveBallPlaybackMaxShotSpeed = 10.5f;
            private const float RuntimeTraceFlushIntervalSeconds = 0.75f;
            private const float RuntimeTraceHeartbeatIntervalSeconds = 5f;
            private const float RuntimeTraceStationaryClockDeltaThresholdMinutes = 0.35f;
            private const int RuntimeTraceMaxBufferedLines = 64;
            private const float RuntimeValidationLogThrottleSeconds = 3f;
            private const float WebSocketKeepAliveIntervalSeconds = 20f;
            private const float WebSocketStaleHardCapSeconds = 20f;
            private const int WebSocketFastReconnectAttemptThreshold = 4;
            private const float WebSocketFastReconnectDelaySeconds = 2f;
            private const float RuntimeHierarchyAuditIntervalSeconds = 1f;
            private const float RuntimeDebugMarkerHeight = 0.18f;
            private const int MaxActiveAttackRuns = 3;
            private const int MaxActiveSupportOptions = 2;
            private const int MaxActivePressers = 2;
            private const int MaxFarSideSprints = 1;

        private struct SyntheticBallTransit
        {
            public bool Active;
            public Vector3 Start;
            public Vector3 End;
            public float StartedAt;
            public float Duration;
            public float ArcHeight;
            public bool IsShot;
            public float MaxPlaybackSpeed;
            public string TargetPlayerId;
        }

        private struct PlaybackConversion
        {
            public Vector3 RawIncoming;
            public Vector3 ConvertedWorld;
            public Vector3 ClampedWorld;
            public bool WasFinite;
        }

        private struct LivePlayerIntentState
        {
            public Vector3 Target;
            public string Mode;
            public string SubjectId;
            public float UpdatedAt;
            public float ExpiresAt;
        }

        private struct FilteredAnimatorState
        {
            public float MoveSpeed;
            public float Horizontal;
            public float Vertical;
        }

        private struct RuntimeActiveMoverBreakdown
        {
            public int AttackRuns;
            public int SupportOptions;
            public int Pressers;
            public int Markers;
            public int FarSideDrifts;
            public int Goalkeepers;

            public int TotalOutfield => AttackRuns + SupportOptions + Pressers + Markers + FarSideDrifts;
        }

        private struct RuntimeComparisonSnapshot
        {
            public GtexRuntimeComparisonMode Mode;
            public string PitchRootPath;
            public Vector3 PitchRootPosition;
            public Vector3 PitchRootRotationEuler;
            public Vector3 PitchRootScale;
            public float PitchLength;
            public float PitchWidth;
            public Vector3 LeftGoalPosition;
            public Vector3 RightGoalPosition;
            public Bounds HomePenaltyBox;
            public Bounds AwayPenaltyBox;
            public Vector3 CameraTargetPoint;
            public string BallOwnerId;
            public Vector3 BallPosition;
            public Vector3 HomeGoalkeeperPosition;
            public Vector3 AwayGoalkeeperPosition;
            public RuntimeActiveMoverBreakdown HomeMovers;
            public RuntimeActiveMoverBreakdown AwayMovers;
            public Vector3 PlayFocusCentroid;
            public bool CosmeticEnvironmentActive;
        }

        private GtexMatchConfig config;
        private MatchAPI api;

        private ClientWebSocket socket;
        private CancellationTokenSource socketToken;

        private MatchResponse currentState;
        private MatchResponse lastKnownState;

        private bool matchLoaded;
        private bool bootstrapTaskFailed;
        private bool usingWebSocket;
        private GtexPitchSpace pitchSpace;
        private GtexPitchZoneHelper pitchZones;
        private GtexPlaybackSanitizer playbackSanitizer;
        private GtexPlaybackApplier playbackApplier;
        private string pitchSpaceSource = string.Empty;

        private readonly Dictionary<string, GtexLegacyPlayerHandle> playerBindings = new();
        private readonly Dictionary<string, string> lastAnimationStates = new();
        private readonly Dictionary<string, Vector3> filteredPlayerTargets = new();
        private readonly Dictionary<string, LivePlayerIntentState> livePlayerIntentTargets = new();
        private readonly Dictionary<string, FilteredAnimatorState> filteredAnimatorStates = new();
        private readonly HashSet<string> duplicateBindingKeys = new();
        private readonly HashSet<string> loggedBindingDiagnostics = new();
        private readonly Dictionary<string, int> runtimeValidationCounts = new();
        private readonly Dictionary<string, float> runtimeValidationNextLogAt = new();
        private string lastAppliedCameraPreset = string.Empty;
        private bool hasFilteredBallTarget;
        private Vector3 filteredBallTarget = Vector3.zero;

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
        private bool runtimeScreenshotCaptureArmed;
        private float runtimeTraceLastFlushAt = -1f;
        private float runtimeTraceLastHeartbeatAt = -1f;
        private float runtimeTraceLastPlaybackSampleAt = -1f;
        private float runtimeTraceLastBallSampleAt = -1f;
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
        private float nextRuntimeHierarchyAuditAt = -1f;
        private float lastRuntimeComparisonLogAt = -1f;
        private float lastSyntheticClockLogAt = -1f;
        private float authoritativeClockMinute = -1f;
        private float syntheticDisplayClockMinute = -1f;
        private bool usingSyntheticClockAdvance;
        private RuntimeComparisonSnapshot lastOriginalReferenceSnapshot;
        private RuntimeComparisonSnapshot lastGtexRuntimeSnapshot;
        private Vector3 lastLiveCameraTarget = Vector3.zero;
        private Vector3 lastLivePlayFocusCentroid = Vector3.zero;
        private RuntimeActiveMoverBreakdown lastHomeActiveMoverBreakdown;
        private RuntimeActiveMoverBreakdown lastAwayActiveMoverBreakdown;
        private GUIStyle runtimeOverlayStyle;
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
        private SyntheticBallTransit syntheticBallTransit;
        private float transitionMotionSuppressedUntil = -1f;
        private GtexMatchPhase lastAppliedControllerPhase = GtexMatchPhase.None;
        private string lastAppliedBallHolderId = string.Empty;
        [Header("GTEX Visual Motion")]
        [SerializeField] private bool gtexRuntimeValidation = true;
        [SerializeField] private float visualTurnDegreesPerSecond = 560f;
        [SerializeField] private float nonForwardExceptionMaxSpeed = 1.65f;
        [SerializeField] private float passReleaseMinFacingDot = 0.58f;
        private Vector3 _lastBroadcastFocus = Vector3.zero;
        private Vector3 _broadcastFocusVelocity = Vector3.zero;
        private int _backwardSprintBlocks;
        private int _keeperZoneViolations;
        private int _badPassReleaseBlocks;
        private int _cameraClampCorrections;

        public bool HasConfig => config != null;

        public bool SkipBootstrapInCurrentContext => skipBootstrap;

        public string MatchId => config != null ? config.matchId : string.Empty;

        public string BaseUrl => config != null ? config.ResolveBaseUrl() : string.Empty;

        public bool HasReceivedLiveState => lastKnownState != null;

        public bool IsUsingWebSocket => usingWebSocket;

        public bool IsConnectingWebSocket => isConnectingWebSocket;

        public bool IsMatchLoaded => matchLoaded;

        public GtexPitchSpace CurrentPitchSpace => pitchSpace;

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
            EnsurePlaybackApplier();
            playbackApplier.Initialize(config);
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

            TryStartRuntimeScreenshotCapture();
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

        private void TryStartRuntimeScreenshotCapture()
        {
            if (runtimeScreenshotCaptureArmed || Application.isBatchMode)
            {
                return;
            }

            var request = ResolveRuntimeScreenshotCaptureRequest();
            if (request == null)
            {
                return;
            }

            runtimeScreenshotCaptureArmed = true;
            StartCoroutine(CaptureRuntimeScreenshots(request));
        }

        private RuntimeScreenshotCaptureRequest ResolveRuntimeScreenshotCaptureRequest()
        {
            var outputDirectory = Environment.GetEnvironmentVariable("GTEX_CAPTURE_OUTPUT_DIR");
            if (string.IsNullOrWhiteSpace(outputDirectory))
            {
                return null;
            }

            var offsetsRaw = Environment.GetEnvironmentVariable("GTEX_CAPTURE_OFFSETS_SECONDS");
            if (string.IsNullOrWhiteSpace(offsetsRaw))
            {
                return null;
            }

            var offsets = new List<int>();
            foreach (var token in offsetsRaw.Split(','))
            {
                if (int.TryParse(token.Trim(), out var seconds) && seconds >= 0)
                {
                    offsets.Add(seconds);
                }
            }

            if (offsets.Count == 0)
            {
                return null;
            }

            offsets.Sort();
            return new RuntimeScreenshotCaptureRequest
            {
                OutputDirectory = outputDirectory.Trim(),
                SessionName = ResolveRuntimeScreenshotSessionName(),
                OffsetsSeconds = offsets
            };
        }

        private static string ResolveRuntimeScreenshotSessionName()
        {
            var sessionName = Environment.GetEnvironmentVariable("GTEX_CAPTURE_SESSION_NAME");
            if (!string.IsNullOrWhiteSpace(sessionName))
            {
                return sessionName.Trim();
            }

            return "gtex_runtime_capture";
        }

        private IEnumerator CaptureRuntimeScreenshots(RuntimeScreenshotCaptureRequest request)
        {
            try
            {
                Directory.CreateDirectory(request.OutputDirectory);
            }
            catch (Exception exception)
            {
                AppendRuntimeTrace("capture", "failed to create screenshot directory: " + exception.Message);
                FlushRuntimeTrace(true);
                yield break;
            }

            AppendRuntimeTrace(
                "capture",
                "armed session=" +
                request.SessionName +
                " outputDir=" +
                request.OutputDirectory +
                " offsets=" +
                string.Join(",", request.OffsetsSeconds));
            FlushRuntimeTrace(true);

            var startedAt = Time.realtimeSinceStartup;
            foreach (var offset in request.OffsetsSeconds)
            {
                var targetTime = startedAt + offset;
                while (Time.realtimeSinceStartup < targetTime)
                {
                    yield return null;
                }

                yield return new WaitForEndOfFrame();

                var capturePath = Path.Combine(
                    request.OutputDirectory,
                    string.Format("{0}_t{1:D4}s.png", request.SessionName, offset));

                Texture2D screenshotTexture = null;
                try
                {
                    screenshotTexture = ScreenCapture.CaptureScreenshotAsTexture();
                    if (screenshotTexture == null)
                    {
                        AppendRuntimeTrace("capture", "null texture offset=" + offset + " path=" + capturePath);
                        FlushRuntimeTrace(true);
                        continue;
                    }

                    var screenshotBytes = screenshotTexture.EncodeToPNG();
                    File.WriteAllBytes(capturePath, screenshotBytes);
                    AppendRuntimeTrace("capture", "saved offset=" + offset + " path=" + capturePath);
                    FlushRuntimeTrace(true);
                }
                catch (Exception exception)
                {
                    AppendRuntimeTrace(
                        "capture",
                        "failed offset=" + offset + " path=" + capturePath + " error=" + exception.Message);
                    FlushRuntimeTrace(true);
                }
                finally
                {
                    if (screenshotTexture != null)
                    {
                        Destroy(screenshotTexture);
                    }
                }
            }
        }

        private sealed class RuntimeScreenshotCaptureRequest
        {
            public string OutputDirectory;
            public string SessionName;
            public List<int> OffsetsSeconds;
        }

        private string BuildRuntimeTraceSummary()
        {
            var activeEvent = currentState != null ? currentState.ResolveActiveEvent() : null;
            return
                "minute=" + (currentState != null ? ResolveDisplayClockMinute().ToString("0.##") : "n/a") +
                " score=" + (currentState != null ? currentState.homeScore : 0) + "-" + (currentState != null ? currentState.awayScore : 0) +
                " phase=" + (currentState != null ? ResolveControllerPhase(currentState).ToString() : "None") +
                " seq=" + (currentState != null ? ResolveStateSequence(currentState).ToString() : "-1") +
                " holder=" + ResolveRuntimeBallHolderId(currentState) +
                " ballSpeed=" + runtimeTraceBallSpeed.ToString("0.##") +
                " driven=" + runtimeTraceDrivenPlayerCount +
                " moving=" + runtimeTraceMovingPlayerCount +
                " avgSpeed=" + runtimeTraceAveragePlayerSpeed.ToString("0.##") +
                " maxSpeed=" + runtimeTraceMaxPlayerSpeed.ToString("0.##") +
                " backSprintBlocks=" + _backwardSprintBlocks +
                " keeperViolations=" + _keeperZoneViolations +
                " badReleaseBlocks=" + _badPassReleaseBlocks +
                " cameraClamps=" + _cameraClampCorrections +
                " transport=" + lastTransportSource +
                " ws=" + usingWebSocket +
                " loaded=" + matchLoaded +
                " pitch=" + pitchSpaceSource +
                " intent=" + ResolveRuntimeIntentToken() +
                " event=" + (activeEvent != null ? ((activeEvent.type ?? string.Empty).Trim()) : string.Empty) +
                " synthClock=" + usingSyntheticClockAdvance;
        }

        private static string ResolveRuntimeBallHolderId(MatchResponse state)
        {
            if (state == null || state.ballPosition == null)
            {
                return string.Empty;
            }

            return (state.ballPosition.playerId ?? string.Empty).Trim();
        }

        private float ResolveDisplayClockMinute()
        {
            if (currentState == null)
            {
                return 0f;
            }

            return usingSyntheticClockAdvance
                ? Mathf.Max(currentState.clockMinute, syntheticDisplayClockMinute)
                : currentState.clockMinute;
        }

        private void EnsureRuntimeHierarchy()
        {
            if (Time.unscaledTime < nextRuntimeHierarchyAuditAt)
            {
                return;
            }

            nextRuntimeHierarchyAuditAt = Time.unscaledTime + RuntimeHierarchyAuditIntervalSeconds;
            if (MatchManager.Current == null)
            {
                return;
            }

            GtexRuntimeHierarchyCoordinator.EnsureMatchHierarchy(
                MatchManager.Current,
                UnityEngine.Object.FindFirstObjectByType<GtexStadiumAtmosphere>());
        }

        private void TryAdvanceStalledClock()
        {
            if (!matchLoaded ||
                currentState == null ||
                config == null ||
                !config.continueClockWhenTransportStalls ||
                IsTerminalLiveState(currentState))
            {
                usingSyntheticClockAdvance = false;
                return;
            }

            var staleThreshold = Mathf.Max(config.pollIntervalSeconds * 3f, config.maxRetryDelaySeconds);
            staleThreshold = Mathf.Min(staleThreshold, WebSocketStaleHardCapSeconds);
            var staleDuration = Mathf.Max(0f, Time.unscaledTime - stateReceivedAt);
            if (staleDuration < staleThreshold)
            {
                usingSyntheticClockAdvance = false;
                syntheticDisplayClockMinute = Mathf.Max(syntheticDisplayClockMinute, currentState.clockMinute);
                return;
            }

            if (authoritativeClockMinute < 0f)
            {
                authoritativeClockMinute = currentState.clockMinute;
            }

            syntheticDisplayClockMinute = Mathf.Clamp(
                authoritativeClockMinute +
                (staleDuration - staleThreshold) * Mathf.Max(0.01f, config.stalledClockAdvanceMinutesPerSecond),
                currentState.clockMinute,
                90f);
            usingSyntheticClockAdvance = syntheticDisplayClockMinute > currentState.clockMinute + 0.01f;
            if (!usingSyntheticClockAdvance)
            {
                return;
            }

            if (GtexMatchController.MatchManagerAdapter.IsAvailable)
            {
                GtexMatchController.MatchManagerAdapter.ApplyExternalLiveState(
                    syntheticDisplayClockMinute,
                    currentState.homeScore,
                    currentState.awayScore,
                    ResolveMatchStatus(currentState));
            }

            if (Time.unscaledTime - lastSyntheticClockLogAt >= RuntimeTraceHeartbeatIntervalSeconds)
            {
                lastSyntheticClockLogAt = Time.unscaledTime;
                AppendRuntimeTrace(
                    "stall-clock",
                    "authoritative=" + authoritativeClockMinute.ToString("0.##") +
                    " display=" + syntheticDisplayClockMinute.ToString("0.##") +
                    " staleSeconds=" + staleDuration.ToString("0.0"));
            }
        }

        private void TrackRuntimeComparison()
        {
            if (config == null ||
                !config.enableRuntimeComparisonLogging ||
                currentState == null)
            {
                return;
            }

            EnsurePitchSpaceResolved();
            if (pitchSpace == null)
            {
                return;
            }

            var interval = Mathf.Max(0.25f, config.comparisonLogIntervalSeconds);
            if (Time.unscaledTime - lastRuntimeComparisonLogAt < interval)
            {
                return;
            }

            lastRuntimeComparisonLogAt = Time.unscaledTime;
            lastOriginalReferenceSnapshot = CaptureRuntimeComparisonSnapshot(GtexRuntimeComparisonMode.OriginalReferenceMode);
            lastGtexRuntimeSnapshot = CaptureRuntimeComparisonSnapshot(GtexRuntimeComparisonMode.GtexRuntimeMode);

            AppendRuntimeTrace("compare", BuildRuntimeComparisonSummary(lastOriginalReferenceSnapshot));
            AppendRuntimeTrace("compare", BuildRuntimeComparisonSummary(lastGtexRuntimeSnapshot));
            AppendRuntimeTrace(
                "compare-delta",
                BuildRuntimeDivergenceSummary(lastOriginalReferenceSnapshot, lastGtexRuntimeSnapshot));
        }

        private RuntimeComparisonSnapshot CaptureRuntimeComparisonSnapshot(GtexRuntimeComparisonMode mode)
        {
            EnsurePitchSpaceResolved();

            var pitchRoot = ResolveRuntimeComparisonPitchRoot();
            var ballOwnerId = ResolveRuntimeBallHolderId(currentState);
            var liveBallPosition =
                currentState != null && currentState.ballPosition != null
                    ? ResolvePredictedFieldPosition(currentState.ballPosition, ResolveLivePredictionSeconds())
                    : pitchSpace != null ? pitchSpace.Center : Vector3.zero;
            var cameraTargetPoint =
                mode == GtexRuntimeComparisonMode.OriginalReferenceMode
                    ? ResolveReferenceCameraTarget(currentState)
                    : (GtexMatchController.CameraAdapter.IsAvailable
                        ? GtexMatchController.CameraAdapter.CurrentTargetPosition
                        : lastLiveCameraTarget);
            cameraTargetPoint = ClampToFieldBounds(cameraTargetPoint, false);
            var playFocusCentroid =
                mode == GtexRuntimeComparisonMode.OriginalReferenceMode
                    ? ResolveReferencePlayFocusCentroid(currentState, liveBallPosition, cameraTargetPoint)
                    : ClampToFieldBounds(
                        lastLivePlayFocusCentroid == Vector3.zero
                            ? ResolveLiveCameraActionCentroid(currentState, cameraTargetPoint)
                            : lastLivePlayFocusCentroid,
                        false);

            var snapshot = new RuntimeComparisonSnapshot
            {
                Mode = mode,
                PitchRootPath = ResolveTransformPath(pitchRoot),
                PitchRootPosition = pitchRoot != null ? pitchRoot.position : Vector3.zero,
                PitchRootRotationEuler = pitchRoot != null ? pitchRoot.rotation.eulerAngles : Vector3.zero,
                PitchRootScale = pitchRoot != null ? pitchRoot.lossyScale : Vector3.one,
                PitchLength = pitchSpace != null ? pitchSpace.Length : ResolvePitchLengthMeters(currentState),
                PitchWidth = pitchSpace != null ? pitchSpace.Width : ResolvePitchWidthMeters(currentState),
                LeftGoalPosition = pitchZones != null ? pitchZones.GetGoalCenter(GtexPitchZoneHelper.HomeTeamSide) : Vector3.zero,
                RightGoalPosition = pitchZones != null ? pitchZones.GetGoalCenter(GtexPitchZoneHelper.AwayTeamSide) : Vector3.zero,
                HomePenaltyBox = pitchZones != null ? pitchZones.GetPenaltyBoxBounds(GtexPitchZoneHelper.HomeTeamSide) : default,
                AwayPenaltyBox = pitchZones != null ? pitchZones.GetPenaltyBoxBounds(GtexPitchZoneHelper.AwayTeamSide) : default,
                CameraTargetPoint = cameraTargetPoint,
                BallOwnerId = ballOwnerId,
                BallPosition =
                    mode == GtexRuntimeComparisonMode.OriginalReferenceMode
                        ? ResolveReferenceBallPosition(currentState, ballOwnerId, liveBallPosition)
                        : ResolveComparisonBallPosition(liveBallPosition),
                HomeGoalkeeperPosition = ResolveReferenceGoalkeeperPosition("home", liveBallPosition),
                AwayGoalkeeperPosition = ResolveReferenceGoalkeeperPosition("away", liveBallPosition),
                HomeMovers =
                    mode == GtexRuntimeComparisonMode.OriginalReferenceMode
                        ? ResolveReferenceActiveMoversForSide(currentState, "home")
                        : ResolveObservedActiveMoversForSide(currentState, "home"),
                AwayMovers =
                    mode == GtexRuntimeComparisonMode.OriginalReferenceMode
                        ? ResolveReferenceActiveMoversForSide(currentState, "away")
                        : ResolveObservedActiveMoversForSide(currentState, "away"),
                PlayFocusCentroid = playFocusCentroid,
                CosmeticEnvironmentActive = GtexRuntimeHierarchyCoordinator.FindCosmeticEnvironmentRoot() != null &&
                                           GtexRuntimeHierarchyCoordinator.FindCosmeticEnvironmentRoot().gameObject.activeInHierarchy
            };

            if (mode == GtexRuntimeComparisonMode.GtexRuntimeMode)
            {
                if (TryResolveGoalkeeperPositionBySide(currentState, "home", false, out var homeKeeper))
                {
                    snapshot.HomeGoalkeeperPosition = homeKeeper;
                }

                if (TryResolveGoalkeeperPositionBySide(currentState, "away", false, out var awayKeeper))
                {
                    snapshot.AwayGoalkeeperPosition = awayKeeper;
                }
            }

            return snapshot;
        }

        private Transform ResolveRuntimeComparisonPitchRoot()
        {
            return FindSceneTransformByName("PitchRoot") ??
                   FindSceneTransformByName("Field") ??
                   FindSceneTransformByName("fieldGround")?.parent ??
                   FindSceneTransformByName("Grass")?.parent;
        }

        private Vector3 ResolveComparisonBallPosition(Vector3 fallbackPosition)
        {
            if (GtexMatchController.BallAdapter.IsAvailable)
            {
                return ClampToFieldBounds(GtexMatchController.BallAdapter.Position, true);
            }

            return ClampToFieldBounds(fallbackPosition, true);
        }

        private Vector3 ResolveReferenceBallPosition(MatchResponse state, string ballOwnerId, Vector3 liveBallPosition)
        {
            if (string.IsNullOrWhiteSpace(ballOwnerId))
            {
                return ResolveComparisonBallPosition(liveBallPosition);
            }

            var holderPosition = ResolveRuntimePlayerPositionById(state, ballOwnerId, liveBallPosition);
            var releaseDirection = liveBallPosition - holderPosition;
            releaseDirection.y = 0f;
            if (releaseDirection.sqrMagnitude <= 0.0001f)
            {
                releaseDirection = ResolveAttackDirection(ResolvePlayerTeamSideToken(state, ballOwnerId));
            }

            var footAnchor = ResolveReadableFootAnchor(state, ballOwnerId, holderPosition, releaseDirection);
            if ((liveBallPosition - footAnchor).sqrMagnitude <= 1.4f * 1.4f)
            {
                return footAnchor;
            }

            return ClampToFieldBounds(Vector3.Lerp(footAnchor, liveBallPosition, 0.3f), true);
        }

        private Vector3 ResolveReadableFootAnchor(MatchResponse state, string playerId, Vector3 fallbackOrigin, Vector3 releaseDirection)
        {
            var anchor = ResolveBallReleaseOrigin(state, playerId, fallbackOrigin, releaseDirection);
            if (!TryGetBoundPlayerByPlayerId(playerId, out var boundPlayer) || boundPlayer == null || !boundPlayer.IsValid)
            {
                return anchor;
            }

            var forward = boundPlayer.Forward;
            forward.y = 0f;
            if (forward.sqrMagnitude <= 0.0001f)
            {
                forward = ResolveAttackDirection(ResolvePlayerTeamSideToken(state, playerId));
            }

            forward.Normalize();
            var right = Vector3.Cross(Vector3.up, forward).normalized;
            var computedAnchor =
                boundPlayer.Position +
                forward * 0.45f +
                right * 0.16f * ResolveDeterministicFootSide(playerId);
            computedAnchor.y =
                pitchSpace != null
                    ? pitchSpace.GrassY + GtexPlaybackSanitizer.DefaultBallHeight
                    : anchor.y;
            return ClampToFieldBounds(Vector3.Lerp(computedAnchor, anchor, 0.35f), true);
        }

        private static float ResolveDeterministicFootSide(string playerId)
        {
            if (string.IsNullOrWhiteSpace(playerId))
            {
                return -1f;
            }

            var checksum = 0;
            for (var index = 0; index < playerId.Length; index += 1)
            {
                checksum += playerId[index];
            }

            return checksum % 2 == 0 ? -1f : 1f;
        }

        private Vector3 ResolveReferenceCameraTarget(MatchResponse state)
        {
            EnsurePitchSpaceResolved();
            var ballPosition =
                state != null && state.ballPosition != null
                    ? ResolvePredictedFieldPosition(state.ballPosition, ResolveLivePredictionSeconds())
                    : pitchSpace != null ? pitchSpace.Center : Vector3.zero;
            var holderId = ResolveRuntimeBallHolderId(state);
            Vector3? carrierPosition = null;
            if (!string.IsNullOrWhiteSpace(holderId))
            {
                carrierPosition = ResolveRuntimePlayerPositionById(state, holderId, ballPosition);
            }

            var focus = ballPosition;
            if (carrierPosition.HasValue)
            {
                focus = Vector3.Lerp(focus, carrierPosition.Value, 0.74f);
            }

            var nearbyPlayers = CollectNearbyActivePlayerPositions(state, carrierPosition ?? ballPosition);
            if (nearbyPlayers.Count > 0)
            {
                var centroid = Vector3.zero;
                for (var index = 0; index < nearbyPlayers.Count; index += 1)
                {
                    centroid += nearbyPlayers[index];
                }

                centroid /= Mathf.Max(1, nearbyPlayers.Count);
                focus = Vector3.Lerp(focus, centroid, 0.24f);
            }

            var referenceCentroid = ResolveReferencePlayFocusCentroid(state, ballPosition, focus);
            focus = Vector3.Lerp(focus, referenceCentroid, 0.34f);

            var hasIntentTarget =
                Time.unscaledTime < liveBallIntentExpiresAt &&
                !string.IsNullOrWhiteSpace(liveBallIntentTargetPlayerId);
            if (hasIntentTarget)
            {
                var receiverPosition = ResolveRuntimePlayerPositionById(state, liveBallIntentTargetPlayerId, liveBallIntentTarget);
                focus = Vector3.Lerp(focus, receiverPosition, syntheticBallTransit.Active ? 0.42f : 0.28f);
            }

            if (syntheticBallTransit.Active)
            {
                focus = Vector3.Lerp(focus, Vector3.Lerp(syntheticBallTransit.Start, syntheticBallTransit.End, 0.5f), 0.44f);
            }

            var holderSide = ResolvePlayerTeamSideToken(state, holderId);
            if (!string.IsNullOrWhiteSpace(holderSide) &&
                pitchZones != null &&
                IsNearTeamBox(ballPosition, ResolveOpposingPitchTeamSideIndex(holderSide)))
            {
                var goalSide = ResolveOpposingPitchTeamSideIndex(holderSide);
                var goalCenter = pitchZones.GetGoalCenter(goalSide);
                var boxCenter = pitchZones.GetPenaltyBoxBounds(goalSide).center;
                focus = Vector3.Lerp(focus, Vector3.Lerp(boxCenter, goalCenter, 0.35f), 0.3f);
            }

            var lookAhead = new Vector3(0f, 0f, 0f);
            if (syntheticBallTransit.Active)
            {
                lookAhead = syntheticBallTransit.End - ballPosition;
            }
            else if (hasIntentTarget)
            {
                lookAhead = liveBallIntentTarget - ballPosition;
            }
            else if (state != null && state.ballPosition != null)
            {
                lookAhead = ResolvePlaybackBallVelocity(state.ballPosition, false);
            }

            lookAhead.y = 0f;
            focus += Vector3.ClampMagnitude(lookAhead, 7.5f) * 0.16f;
            if (pitchZones != null)
            {
                focus = pitchZones.GetSafeCameraFocusPoint(focus);
            }

            focus.y = pitchSpace != null ? pitchSpace.GrassY : 0f;
            return ClampToFieldBounds(focus, false);
        }

        private Vector3 ResolveReferencePlayFocusCentroid(MatchResponse state, Vector3 ballPosition, Vector3 fallbackFocus)
        {
            var centroid = ResolveLiveCameraActionCentroid(state, fallbackFocus);
            if (Time.unscaledTime < liveBallIntentExpiresAt &&
                !string.IsNullOrWhiteSpace(liveBallIntentTargetPlayerId))
            {
                centroid = Vector3.Lerp(
                    centroid,
                    ResolveRuntimePlayerPositionById(state, liveBallIntentTargetPlayerId, liveBallIntentTarget),
                    0.24f);
            }

            if (syntheticBallTransit.Active)
            {
                centroid = Vector3.Lerp(centroid, Vector3.Lerp(syntheticBallTransit.Start, syntheticBallTransit.End, 0.5f), 0.34f);
            }

            centroid = ClampToFieldBounds(Vector3.Lerp(ballPosition, centroid, 0.72f), false);
            centroid.y = pitchSpace != null ? pitchSpace.GrassY : 0f;
            return centroid;
        }

        private Vector3 ResolveReferenceGoalkeeperPosition(string teamSide, Vector3 ballPosition)
        {
            EnsurePitchSpaceResolved();
            if (pitchZones == null || pitchSpace == null)
            {
                return ballPosition;
            }

            var teamSideIndex = ResolvePitchTeamSideIndex(teamSide);
            var defaultHome = pitchZones.GetDefaultGoalkeeperHome(teamSideIndex, pitchSpace.GrassY);
            var ballAngleTarget = pitchZones.GetKeeperBallAngleTarget(ballPosition, defaultHome, teamSideIndex);
            var threat01 =
                1f - Mathf.Clamp01(
                    pitchZones.DistanceToGoalCenter(ballPosition, teamSideIndex) /
                    Mathf.Max(1f, pitchSpace.HalfLength));
            if (string.Equals(ResolvePossessionSideToken(), NormalizeTeamSideToken(teamSide), StringComparison.Ordinal))
            {
                threat01 *= 0.22f;
            }

            return ClampToFieldBounds(Vector3.Lerp(defaultHome, ballAngleTarget, Mathf.Lerp(0.18f, 1f, threat01)), false);
        }

        private bool TryResolveGoalkeeperPositionBySide(
            MatchResponse state,
            string teamSide,
            bool referenceMode,
            out Vector3 position)
        {
            if (state != null && state.players != null)
            {
                var normalizedTeamSide = NormalizeTeamSideToken(teamSide);
                var livePlayers = state.players;
                for (var index = 0; index < livePlayers.Length; index += 1)
                {
                    var livePlayer = livePlayers[index];
                    if (livePlayer == null ||
                        livePlayer.isBall ||
                        ResolveLiveRoleBucket(livePlayer) != 0 ||
                        !string.Equals(NormalizeTeamSideToken(livePlayer.teamSide), normalizedTeamSide, StringComparison.Ordinal))
                    {
                        continue;
                    }

                    if (referenceMode)
                    {
                        var ballPosition =
                            state.ballPosition != null
                                ? ResolvePredictedFieldPosition(state.ballPosition, ResolveLivePredictionSeconds())
                                : pitchSpace != null ? pitchSpace.Center : Vector3.zero;
                        position = ResolveReferenceGoalkeeperPosition(normalizedTeamSide, ballPosition);
                        return true;
                    }

                    if (TryGetBoundPlayer(livePlayer, out var handle) && handle != null && handle.IsValid)
                    {
                        position = ClampToFieldBounds(handle.Position, false);
                        return true;
                    }

                    position = ResolveRuntimeFieldPosition(livePlayer, state, Vector3.zero);
                    return true;
                }
            }

            position = ResolveReferenceGoalkeeperPosition(
                teamSide,
                currentState != null && currentState.ballPosition != null
                    ? ResolvePredictedFieldPosition(currentState.ballPosition, ResolveLivePredictionSeconds())
                    : pitchSpace != null ? pitchSpace.Center : Vector3.zero);
            return false;
        }

        private RuntimeActiveMoverBreakdown ResolveObservedActiveMoversForSide(MatchResponse state, string teamSide)
        {
            var breakdown = default(RuntimeActiveMoverBreakdown);
            if (state == null || state.players == null)
            {
                return breakdown;
            }

            var normalizedTeamSide = NormalizeTeamSideToken(teamSide);
            var possessionSide = ResolvePossessionSideToken();
            var ballAnchor =
                state.ballPosition != null
                    ? ResolvePredictedFieldPosition(state.ballPosition, ResolveLivePredictionSeconds())
                    : pitchSpace != null ? pitchSpace.Center : Vector3.zero;
            var holderId = ResolveRuntimeBallHolderId(state);
            var livePlayers = state.players;
            for (var index = 0; index < livePlayers.Length; index += 1)
            {
                var livePlayer = livePlayers[index];
                if (livePlayer == null ||
                    livePlayer.isBall ||
                    !livePlayer.active ||
                    !string.Equals(NormalizeTeamSideToken(livePlayer.teamSide), normalizedTeamSide, StringComparison.Ordinal))
                {
                    continue;
                }

                var roleBucket = ResolveLiveRoleBucket(livePlayer);
                if (roleBucket == 0)
                {
                    breakdown.Goalkeepers += 1;
                    continue;
                }

                var currentPosition = ResolveRuntimeFieldPosition(livePlayer, state, ballAnchor);
                var urgency = ResolveLiveMovementUrgency(livePlayer, currentPosition);
                var ballRank = ResolveTeamBallRank(livePlayer, currentPosition, ballAnchor);
                var markRank = ResolveTeamDistanceRank(
                    livePlayer,
                    currentPosition,
                    ResolveRuntimePlayerPositionById(state, holderId, ballAnchor));
                var sameTeamAsPossession =
                    !string.IsNullOrWhiteSpace(possessionSide) &&
                    string.Equals(normalizedTeamSide, possessionSide, StringComparison.Ordinal);
                var isIntentReceiver =
                    Time.unscaledTime < liveBallIntentExpiresAt &&
                    string.Equals(
                        (livePlayer.playerId ?? string.Empty).Trim(),
                        (liveBallIntentTargetPlayerId ?? string.Empty).Trim(),
                        StringComparison.Ordinal);

                if (!IsLikelyObservedMover(livePlayer, urgency))
                {
                    continue;
                }

                if (livePlayer.hasPossession)
                {
                    breakdown.AttackRuns += 1;
                }
                else if (sameTeamAsPossession)
                {
                    if (isIntentReceiver || ballRank <= 1)
                    {
                        breakdown.SupportOptions += 1;
                    }
                    else if (ballRank <= 2)
                    {
                        breakdown.AttackRuns += 1;
                    }
                    else
                    {
                        breakdown.FarSideDrifts += 1;
                    }
                }
                else if (markRank <= 1)
                {
                    breakdown.Pressers += 1;
                }
                else if (ballRank <= 1)
                {
                    breakdown.Markers += 1;
                }
                else
                {
                    breakdown.FarSideDrifts += 1;
                }
            }

            return breakdown;
        }

        private RuntimeActiveMoverBreakdown ResolveReferenceActiveMoversForSide(MatchResponse state, string teamSide)
        {
            var breakdown = default(RuntimeActiveMoverBreakdown);
            if (state == null || state.players == null)
            {
                return breakdown;
            }

            var normalizedTeamSide = NormalizeTeamSideToken(teamSide);
            var possessionSide = ResolvePossessionSideToken();
            var sameTeamAsPossession = string.Equals(normalizedTeamSide, possessionSide, StringComparison.Ordinal);
            var looseBall =
                string.IsNullOrWhiteSpace(possessionSide) ||
                state.ballPosition == null ||
                string.IsNullOrWhiteSpace(state.ballPosition.playerId);
            var ballAnchor =
                state.ballPosition != null
                    ? ResolvePredictedFieldPosition(state.ballPosition, ResolveLivePredictionSeconds())
                    : pitchSpace != null ? pitchSpace.Center : Vector3.zero;
            var holderId = ResolveRuntimeBallHolderId(state);
            var livePlayers = state.players;
            for (var index = 0; index < livePlayers.Length; index += 1)
            {
                var livePlayer = livePlayers[index];
                if (livePlayer == null ||
                    livePlayer.isBall ||
                    !livePlayer.active ||
                    !string.Equals(NormalizeTeamSideToken(livePlayer.teamSide), normalizedTeamSide, StringComparison.Ordinal))
                {
                    continue;
                }

                var roleBucket = ResolveLiveRoleBucket(livePlayer);
                if (roleBucket == 0)
                {
                    breakdown.Goalkeepers += 1;
                    continue;
                }

                var currentPosition = ResolveRuntimeFieldPosition(livePlayer, state, ballAnchor);
                var ballRank = ResolveTeamBallRank(livePlayer, currentPosition, ballAnchor);
                var markRank = ResolveTeamDistanceRank(
                    livePlayer,
                    currentPosition,
                    ResolveRuntimePlayerPositionById(state, holderId, ballAnchor));
                var isIntentReceiver =
                    Time.unscaledTime < liveBallIntentExpiresAt &&
                    string.Equals(
                        (livePlayer.playerId ?? string.Empty).Trim(),
                        (liveBallIntentTargetPlayerId ?? string.Empty).Trim(),
                        StringComparison.Ordinal);

                if (livePlayer.hasPossession)
                {
                    breakdown.AttackRuns = Mathf.Min(MaxActiveAttackRuns, breakdown.AttackRuns + 1);
                    continue;
                }

                if (sameTeamAsPossession)
                {
                    if (isIntentReceiver || ballRank == 0)
                    {
                        breakdown.SupportOptions = Mathf.Min(MaxActiveSupportOptions, breakdown.SupportOptions + 1);
                    }
                    else if (ballRank <= 2)
                    {
                        breakdown.AttackRuns = Mathf.Min(MaxActiveAttackRuns, breakdown.AttackRuns + 1);
                    }
                    else if (breakdown.FarSideDrifts < MaxFarSideSprints)
                    {
                        breakdown.FarSideDrifts += 1;
                    }

                    continue;
                }

                if (looseBall)
                {
                    if (ballRank <= 1 && breakdown.Pressers < MaxActivePressers)
                    {
                        breakdown.Pressers += 1;
                    }
                    else if (ballRank == 2 && breakdown.Markers < 1)
                    {
                        breakdown.Markers += 1;
                    }
                    else if (breakdown.FarSideDrifts < MaxFarSideSprints)
                    {
                        breakdown.FarSideDrifts += 1;
                    }

                    continue;
                }

                if (markRank <= 1 && breakdown.Pressers < MaxActivePressers)
                {
                    breakdown.Pressers += 1;
                }
                else if (ballRank == 0 && breakdown.Markers < 1)
                {
                    breakdown.Markers += 1;
                }
                else if (breakdown.FarSideDrifts < MaxFarSideSprints)
                {
                    breakdown.FarSideDrifts += 1;
                }
            }

            return breakdown;
        }

        private bool IsLikelyObservedMover(PlayerPosition livePlayer, float urgency)
        {
            if (livePlayer == null)
            {
                return false;
            }

            if (livePlayer.hasPossession)
            {
                return true;
            }

            if (TryGetBoundPlayer(livePlayer, out var handle) && handle != null && handle.IsValid)
            {
                var planarVelocity = handle.Velocity;
                planarVelocity.y = 0f;
                return planarVelocity.magnitude > 0.55f || urgency >= 0.58f;
            }

            var liveVelocity = ResolveLiveFieldVelocity(livePlayer);
            liveVelocity.y = 0f;
            return liveVelocity.magnitude > 0.5f || urgency >= 0.58f;
        }

        private string BuildRuntimeComparisonSummary(RuntimeComparisonSnapshot snapshot)
        {
            return
                snapshot.Mode +
                " minute=" + ResolveDisplayClockMinute().ToString("0.##") +
                " pitchRoot=" + snapshot.PitchRootPath +
                " pitchTransform=" + FormatPlaybackVector(snapshot.PitchRootPosition) +
                "/" + FormatPlaybackVector(snapshot.PitchRootRotationEuler) +
                "/" + FormatPlaybackVector(snapshot.PitchRootScale) +
                " pitchSize=(" + snapshot.PitchLength.ToString("0.##") + "," + snapshot.PitchWidth.ToString("0.##") + ")" +
                " goals=" + FormatPlaybackVector(snapshot.LeftGoalPosition) + "->" + FormatPlaybackVector(snapshot.RightGoalPosition) +
                " penaltyHome=" + FormatBounds(snapshot.HomePenaltyBox) +
                " penaltyAway=" + FormatBounds(snapshot.AwayPenaltyBox) +
                " camera=" + FormatPlaybackVector(snapshot.CameraTargetPoint) +
                " holder=" + snapshot.BallOwnerId +
                " ball=" + FormatPlaybackVector(snapshot.BallPosition) +
                " keepers=" + FormatPlaybackVector(snapshot.HomeGoalkeeperPosition) + "/" + FormatPlaybackVector(snapshot.AwayGoalkeeperPosition) +
                " movers=" + FormatRuntimeMovers(snapshot.HomeMovers) + "|" + FormatRuntimeMovers(snapshot.AwayMovers) +
                " focus=" + FormatPlaybackVector(snapshot.PlayFocusCentroid) +
                " cosmeticActive=" + snapshot.CosmeticEnvironmentActive;
        }

        private static string BuildRuntimeDivergenceSummary(
            RuntimeComparisonSnapshot referenceSnapshot,
            RuntimeComparisonSnapshot runtimeSnapshot)
        {
            return
                "cameraDelta=" + Vector3.Distance(referenceSnapshot.CameraTargetPoint, runtimeSnapshot.CameraTargetPoint).ToString("0.##") +
                " ballDelta=" + Vector3.Distance(referenceSnapshot.BallPosition, runtimeSnapshot.BallPosition).ToString("0.##") +
                " playDelta=" + Vector3.Distance(referenceSnapshot.PlayFocusCentroid, runtimeSnapshot.PlayFocusCentroid).ToString("0.##") +
                " homeKeeperDelta=" + Vector3.Distance(referenceSnapshot.HomeGoalkeeperPosition, runtimeSnapshot.HomeGoalkeeperPosition).ToString("0.##") +
                " awayKeeperDelta=" + Vector3.Distance(referenceSnapshot.AwayGoalkeeperPosition, runtimeSnapshot.AwayGoalkeeperPosition).ToString("0.##") +
                " holderMismatch=" + (!string.Equals(referenceSnapshot.BallOwnerId, runtimeSnapshot.BallOwnerId, StringComparison.Ordinal)) +
                " homeMoverDelta=" + (runtimeSnapshot.HomeMovers.TotalOutfield - referenceSnapshot.HomeMovers.TotalOutfield) +
                " awayMoverDelta=" + (runtimeSnapshot.AwayMovers.TotalOutfield - referenceSnapshot.AwayMovers.TotalOutfield) +
                " cosmeticActive=" + runtimeSnapshot.CosmeticEnvironmentActive;
        }

        private static string FormatBounds(Bounds bounds)
        {
            return
                "c" + FormatPlaybackVector(bounds.center) +
                " s" + FormatPlaybackVector(bounds.size);
        }

        private static string FormatRuntimeMovers(RuntimeActiveMoverBreakdown breakdown)
        {
            return
                "atk=" + breakdown.AttackRuns +
                ",sup=" + breakdown.SupportOptions +
                ",press=" + breakdown.Pressers +
                ",mark=" + breakdown.Markers +
                ",drift=" + breakdown.FarSideDrifts +
                ",gk=" + breakdown.Goalkeepers;
        }

        private static string ResolveTransformPath(Transform transform)
        {
            if (transform == null)
            {
                return "<missing>";
            }

            var path = transform.name;
            var current = transform.parent;
            while (current != null)
            {
                path = current.name + "/" + path;
                current = current.parent;
            }

            return path;
        }

        private static Transform FindSceneTransformByName(string transformName)
        {
            if (string.IsNullOrWhiteSpace(transformName))
            {
                return null;
            }

            var allTransforms = UnityEngine.Object.FindObjectsByType<Transform>(FindObjectsSortMode.None);
            for (var index = 0; index < allTransforms.Length; index += 1)
            {
                var candidate = allTransforms[index];
                if (candidate != null && string.Equals(candidate.name, transformName, StringComparison.Ordinal))
                {
                    return candidate;
                }
            }

            return null;
        }

        private void DrawRuntimeDebugScene()
        {
            if (config == null || !config.showRuntimeDebugOverlay || currentState == null)
            {
                return;
            }

            DrawWorldMarker(lastOriginalReferenceSnapshot.CameraTargetPoint, Color.yellow, 0.55f);
            DrawWorldMarker(lastGtexRuntimeSnapshot.CameraTargetPoint, Color.cyan, 0.55f);
            DrawWorldMarker(lastOriginalReferenceSnapshot.PlayFocusCentroid, new Color(1f, 0.6f, 0.1f), 0.42f);
            DrawWorldMarker(lastGtexRuntimeSnapshot.PlayFocusCentroid, Color.green, 0.42f);

            Debug.DrawLine(
                lastOriginalReferenceSnapshot.CameraTargetPoint + Vector3.up * 0.35f,
                lastGtexRuntimeSnapshot.CameraTargetPoint + Vector3.up * 0.35f,
                Color.magenta);

            var holderId = ResolveRuntimeBallHolderId(currentState);
            if (!string.IsNullOrWhiteSpace(holderId))
            {
                var holderPosition = ResolveRuntimePlayerPositionById(currentState, holderId, lastGtexRuntimeSnapshot.BallPosition);
                Debug.DrawLine(
                    holderPosition + Vector3.up * RuntimeDebugMarkerHeight,
                    lastOriginalReferenceSnapshot.BallPosition + Vector3.up * RuntimeDebugMarkerHeight,
                    Color.yellow);
                Debug.DrawLine(
                    holderPosition + Vector3.up * (RuntimeDebugMarkerHeight + 0.04f),
                    lastGtexRuntimeSnapshot.BallPosition + Vector3.up * (RuntimeDebugMarkerHeight + 0.04f),
                    Color.cyan);
            }

            if (Time.unscaledTime < liveBallIntentExpiresAt &&
                !string.IsNullOrWhiteSpace(liveBallIntentTargetPlayerId))
            {
                var receiverPosition = ResolveRuntimePlayerPositionById(currentState, liveBallIntentTargetPlayerId, liveBallIntentTarget);
                Debug.DrawLine(
                    lastOriginalReferenceSnapshot.BallPosition + Vector3.up * 0.22f,
                    receiverPosition + Vector3.up * 0.22f,
                    Color.green);
            }
        }

        private static void DrawWorldMarker(Vector3 position, Color color, float radius)
        {
            var up = Vector3.up * Mathf.Max(0.05f, radius);
            var right = Vector3.right * Mathf.Max(0.05f, radius);
            var forward = Vector3.forward * Mathf.Max(0.05f, radius);
            Debug.DrawLine(position - right, position + right, color);
            Debug.DrawLine(position - forward, position + forward, color);
            Debug.DrawLine(position, position + up, color);
        }

        private void EnsureRuntimeOverlayStyle()
        {
            if (runtimeOverlayStyle != null)
            {
                return;
            }

            runtimeOverlayStyle = new GUIStyle(GUI.skin.label)
            {
                fontSize = 12,
                wordWrap = true,
                normal = { textColor = Color.white }
            };
        }

        private void OnGUI()
        {
            if (config == null || !config.showRuntimeDebugOverlay || currentState == null)
            {
                return;
            }

            EnsureRuntimeOverlayStyle();
            var summary = new StringBuilder();
            summary.AppendLine("GTEX Runtime Comparison");
            summary.AppendLine(
                "Clock " + ResolveDisplayClockMinute().ToString("0.##") +
                (usingSyntheticClockAdvance ? " (stall-advanced)" : string.Empty) +
                "  Holder " + ResolveRuntimeBallHolderId(currentState));
            summary.AppendLine("Reference: " + BuildRuntimeComparisonSummary(lastOriginalReferenceSnapshot));
            summary.AppendLine("Runtime:   " + BuildRuntimeComparisonSummary(lastGtexRuntimeSnapshot));
            summary.AppendLine("Delta:     " + BuildRuntimeDivergenceSummary(lastOriginalReferenceSnapshot, lastGtexRuntimeSnapshot));

            var rect = new Rect(12f, 12f, Mathf.Min(Screen.width - 24f, 900f), 154f);
            GUI.Box(rect, string.Empty);
            GUI.Label(
                new Rect(rect.x + 8f, rect.y + 8f, rect.width - 16f, rect.height - 16f),
                summary.ToString(),
                runtimeOverlayStyle);
        }

        private void ResolvePitchSpace()
        {
            pitchSpace = GtexPitchLocator.Resolve(out pitchSpaceSource);
            playbackSanitizer = new GtexPlaybackSanitizer(pitchSpace);
            pitchZones = pitchSpace != null ? new GtexPitchZoneHelper(pitchSpace) : null;

            if (MatchManager.Current != null)
            {
                MatchManager.Current.ConfigureExternalPlaybackPitchSpace(pitchSpace);
                if (MatchManager.Current.ExternalPlaybackPitchZones != null)
                {
                    pitchZones = MatchManager.Current.ExternalPlaybackPitchZones;
                }
            }

            var summary = pitchSpace != null
                ? pitchSpace.ToString()
                : "pitch-space unavailable";
            AppendRuntimeTrace("pitch", "source=" + pitchSpaceSource + " " + summary);
            Debug.Log("[GTEX] Pitch space resolved from " + pitchSpaceSource + " " + summary);
            TraceGoalAnchors();
        }

        private void EnsurePitchSpaceResolved()
        {
            if (pitchSpace != null && playbackSanitizer != null && pitchZones != null)
            {
                return;
            }

            ResolvePitchSpace();
        }

        private PlaybackConversion ConvertIncomingPlaybackPosition(PlayerPosition livePosition, MatchResponse state)
        {
            EnsurePitchSpaceResolved();

            var conversion = new PlaybackConversion
            {
                RawIncoming = livePosition != null
                    ? new Vector3(livePosition.x, livePosition.y, livePosition.z)
                    : Vector3.zero,
                ConvertedWorld = pitchSpace != null ? pitchSpace.Center : Vector3.zero,
                ClampedWorld = pitchSpace != null ? pitchSpace.Center : Vector3.zero,
                WasFinite = livePosition != null
            };

            if (livePosition == null || pitchSpace == null || playbackSanitizer == null)
            {
                return conversion;
            }

            conversion.WasFinite = GtexPlaybackSanitizer.IsFinite(conversion.RawIncoming);

            if (conversion.WasFinite)
            {
                var pitchLength = ResolvePitchLengthMeters(state);
                var pitchWidth = ResolvePitchWidthMeters(state);
                var usesPositivePitchCoordinates = UsesPositivePitchCoordinates(state);
                var normalizedPosition = usesPositivePitchCoordinates
                    ? new Vector3(
                        Mathf.InverseLerp(0f, pitchLength, conversion.RawIncoming.x),
                        conversion.RawIncoming.y,
                        Mathf.InverseLerp(0f, pitchWidth, conversion.RawIncoming.z))
                    : new Vector3(
                        Mathf.InverseLerp(
                            -pitchLength * 0.5f,
                            pitchLength * 0.5f,
                            conversion.RawIncoming.x),
                        conversion.RawIncoming.y,
                        Mathf.InverseLerp(
                            -pitchWidth * 0.5f,
                            pitchWidth * 0.5f,
                            conversion.RawIncoming.z));
                conversion.ConvertedWorld = pitchSpace.NormalizedToWorld(normalizedPosition);
            }

            conversion.ClampedWorld = livePosition.isBall
                ? playbackSanitizer.SanitizeBallPosition(conversion.ConvertedWorld)
                : playbackSanitizer.SanitizePlayerPosition(conversion.ConvertedWorld);
            return conversion;
        }

        private Vector3 ConvertIncomingPlaybackVelocity(PlayerPosition livePosition, MatchResponse state)
        {
            if (livePosition == null)
            {
                return Vector3.zero;
            }

            EnsurePitchSpaceResolved();

            var rawVelocity = new Vector3(livePosition.velocityX, livePosition.velocityY, livePosition.velocityZ);
            if (pitchSpace == null || !GtexPlaybackSanitizer.IsFinite(rawVelocity))
            {
                return Vector3.zero;
            }

            var convertedVelocity = new Vector3(
                (rawVelocity.x / ResolvePitchLengthMeters(state)) * pitchSpace.Length,
                rawVelocity.y,
                (rawVelocity.z / ResolvePitchWidthMeters(state)) * pitchSpace.Width);

            if (!GtexPlaybackSanitizer.IsFinite(convertedVelocity))
            {
                return Vector3.zero;
            }

            if (!livePosition.isBall)
            {
                convertedVelocity.y = 0f;
            }

            return convertedVelocity;
        }

        private static bool UsesPositivePitchCoordinates(MatchResponse state)
        {
            if (state == null)
            {
                return false;
            }

            var pitchLength = ResolvePitchLengthMeters(state);
            var pitchWidth = ResolvePitchWidthMeters(state);
            var hasSample = false;
            var hasNegativeSample = false;
            var exceedsCenteredRange = false;

            if (state.players != null)
            {
                for (var index = 0; index < state.players.Length; index += 1)
                {
                    TrackCoordinateOriginSample(
                        state.players[index],
                        pitchLength,
                        pitchWidth,
                        ref hasSample,
                        ref hasNegativeSample,
                        ref exceedsCenteredRange);
                }
            }

            TrackCoordinateOriginSample(
                state.ballPosition,
                pitchLength,
                pitchWidth,
                ref hasSample,
                ref hasNegativeSample,
                ref exceedsCenteredRange);

            return hasSample && !hasNegativeSample && exceedsCenteredRange;
        }

        private static void TrackCoordinateOriginSample(
            PlayerPosition livePosition,
            float pitchLength,
            float pitchWidth,
            ref bool hasSample,
            ref bool hasNegativeSample,
            ref bool exceedsCenteredRange)
        {
            if (livePosition == null)
            {
                return;
            }

            var sample = new Vector3(livePosition.x, livePosition.y, livePosition.z);
            if (!GtexPlaybackSanitizer.IsFinite(sample))
            {
                return;
            }

            hasSample = true;
            if (sample.x < -1f || sample.z < -1f)
            {
                hasNegativeSample = true;
            }

            if (sample.x > pitchLength * 0.5f + 1f ||
                sample.z > pitchWidth * 0.5f + 1f)
            {
                exceedsCenteredRange = true;
            }
        }

        private static float ResolvePitchLengthMeters(MatchResponse state)
        {
            return state != null ? Mathf.Max(1f, state.pitchLengthMeters) : GtexPitchSpace.DefaultLength;
        }

        private static float ResolvePitchWidthMeters(MatchResponse state)
        {
            return state != null ? Mathf.Max(1f, state.pitchWidthMeters) : GtexPitchSpace.DefaultWidth;
        }

        private static string FormatPlaybackVector(Vector3 value)
        {
            return
                "(" +
                value.x.ToString("0.##") +
                "," +
                value.y.ToString("0.##") +
                "," +
                value.z.ToString("0.##") +
                ")";
        }

        private void TraceGoalAnchors()
        {
            if (pitchSpace == null || MatchManager.Current == null)
            {
                return;
            }

            TraceGoalAnchor(MatchManager.Current.goalNet1, pitchSpace.GetHomeGoalCenter(), "home");
            TraceGoalAnchor(MatchManager.Current.goalNet2, pitchSpace.GetAwayGoalCenter(), "away");
        }

        private void TraceGoalAnchor(GoalNet goal, Vector3 expectedGroundCenter, string side)
        {
            if (goal == null)
            {
                return;
            }

            AppendRuntimeTrace(
                "goal-anchor",
                "side=" +
                side +
                " expected=" +
                FormatPlaybackVector(expectedGroundCenter) +
                " actual=" +
                FormatPlaybackVector(goal.GroundAnchorPosition));
        }

        private void TraceBallPitchSample(PlaybackConversion conversion, Vector3 appliedPosition, GtexLegacyPlayerHandle holder)
        {
            AppendRuntimeTrace(
                "ball-pitch-sample",
                "holder=" +
                (holder != null && holder.IsValid
                    ? holder.DatabasePlayerId.HasValue
                        ? holder.DatabasePlayerId.Value.ToString()
                        : holder.ShirtNumber.ToString()
                    : string.Empty) +
                " raw=" +
                FormatPlaybackVector(conversion.RawIncoming) +
                " converted=" +
                FormatPlaybackVector(conversion.ConvertedWorld) +
                " clamped=" +
                FormatPlaybackVector(appliedPosition));
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

            var displayClockMinute = ResolveDisplayClockMinute();
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
                        "minute=" + displayClockMinute.ToString("0.##") +
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
                    "minute=" + displayClockMinute.ToString("0.##") +
                    " from=" + runtimeTraceLastLoggedBallHolderId +
                    " to=" + holderId +
                    " ballSpeed=" + runtimeTraceBallSpeed.ToString("0.##"));
                runtimeTraceLastLoggedBallHolderId = holderId;
            }

            if (runtimeTraceMovingPlayerCount > 0 || runtimeTraceBallSpeed >= LiveBallPassSpeedUnitsPerSecond)
            {
                runtimeTraceLastMotionClockMinute = displayClockMinute;
            }
            else if (runtimeTraceLastMotionClockMinute < 0f)
            {
                runtimeTraceLastMotionClockMinute = displayClockMinute;
            }
            else if (displayClockMinute - runtimeTraceLastMotionClockMinute >= RuntimeTraceStationaryClockDeltaThresholdMinutes)
            {
                AppendRuntimeTrace("warn", "clock advanced with no detected motion. " + BuildRuntimeTraceSummary());
                runtimeTraceLastMotionClockMinute = displayClockMinute;
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
                    false,
                    config
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
                if (MatchManager.Current != null)
                {
                    MatchManager.Current.ConfigureExternalPlaybackSettings(config);
                }
                ResolvePitchSpace();
                EnsureRuntimeHierarchy();
            }
            else if (config != null && config.verboseLogging)
            {
                Debug.LogWarning("[GTEX] MatchManager is not available during live bootstrap. Runtime will continue caching live state.");
            }

            BindPlayers();
            EnsureRuntimeHierarchy();
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

            if (ShouldStopTransportAfterTerminal())
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
                socket.Options.KeepAliveInterval = TimeSpan.FromSeconds(WebSocketKeepAliveIntervalSeconds);
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
                staleStateWarningLogged = false;

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
                if (ShouldStopTransportAfterTerminal())
                {
                    yield return new WaitForSecondsRealtime(Mathf.Max(0.25f, config.pollIntervalSeconds));
                    continue;
                }

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
            EnsureRuntimeHierarchy();

            if (!matchLoaded || playbackApplier == null || playbackApplier.CurrentState == null)
            {
                FlushRuntimeTrace(false);
                return;
            }

            TryAdvanceStalledClock();
            playbackApplier.Tick(Time.deltaTime);
            TrackRuntimeComparison();
            TrackRuntimeTrace();
            DrawRuntimeDebugScene();
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
            EnsurePlaybackApplier();
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

        private bool ShouldStopTransportAfterTerminal()
        {
            return config != null &&
                   config.stopReconnectAfterTerminal &&
                   (IsTerminalLiveState(lastKnownState) || IsTerminalLiveState(currentState));
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

        private static bool IsOpenPlayPhase(GtexMatchPhase phase)
        {
            return phase == GtexMatchPhase.Kickoff ||
                   phase == GtexMatchPhase.FirstHalf ||
                   phase == GtexMatchPhase.SecondHalf;
        }

        private bool ShouldSuppressBoundaryMotion(MatchResponse state)
        {
            if (state == null)
            {
                return true;
            }

            if (!IsOpenPlayPhase(ResolveControllerPhase(state)))
            {
                return true;
            }

            return Time.unscaledTime < transitionMotionSuppressedUntil;
        }

        private void TrackMotionBoundaryState(MatchResponse state, bool forceSnap)
        {
            var phase = ResolveControllerPhase(state);
            var holderId = ResolveRuntimeBallHolderId(state);
            var phaseChanged = lastAppliedControllerPhase != GtexMatchPhase.None && phase != lastAppliedControllerPhase;
            var holderChanged =
                !string.IsNullOrWhiteSpace(lastAppliedBallHolderId) &&
                !string.Equals(lastAppliedBallHolderId, holderId, StringComparison.Ordinal);

            if (forceSnap || phaseChanged)
            {
                transitionMotionSuppressedUntil = Mathf.Max(
                    transitionMotionSuppressedUntil,
                    Time.unscaledTime + LivePhaseBoundaryDurationSeconds);
                ClearSyntheticBallTransit();
                ClearLiveBallIntent();
                ClearPlaybackTargetFilters();
            }
            else if (holderChanged)
            {
                transitionMotionSuppressedUntil = Mathf.Max(
                    transitionMotionSuppressedUntil,
                    Time.unscaledTime + LiveMotionBoundaryDurationSeconds);
            }

            lastAppliedControllerPhase = phase;
            lastAppliedBallHolderId = holderId;
        }

        private void ApplyState(MatchResponse state, bool forceSnap)
        {
            if (state == null || playbackApplier == null)
            {
                return;
            }

            playbackApplier.ApplyFrame(state, forceSnap);

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

        private void EnsurePlaybackApplier()
        {
            if (playbackApplier != null)
            {
                return;
            }

            playbackApplier = new GtexPlaybackApplier(
                () => matchLoaded,
                NeedsPlayerBindingRefresh,
                BindPlayers,
                DrivePlayers,
                DriveBall,
                BeforeApplyPlaybackFrame,
                ApplyScenePlaybackState,
                ApplyLiveCameraPreset,
                UpdateLiveBallIntent,
                TryStartSyntheticBallTransit,
                TryTriggerLiveBallAction,
                TryTriggerLiveEventAction,
                Snap);
        }

        private void BeforeApplyPlaybackFrame(MatchResponse state, bool forceSnap)
        {
            TrackMotionBoundaryState(state, forceSnap);
            currentState = state;
            stateReceivedAt = Time.unscaledTime;
            authoritativeClockMinute = state.clockMinute;
            syntheticDisplayClockMinute = state.clockMinute;
            usingSyntheticClockAdvance = false;
            staleStateWarningLogged = false;
            consecutiveTransportFailures = 0;
            lastTransportError = string.Empty;

            if (config != null && config.stopReconnectAfterTerminal && IsTerminalLiveState(state))
            {
                nextWebSocketReconnectAt = float.PositiveInfinity;
            }

            if (forceSnap || IsTerminalLiveState(state))
            {
                ClearSyntheticBallTransit();
            }

            if (ShouldSuppressBoundaryMotion(state))
            {
                runtimeTraceMovingPlayerCount = 0;
                runtimeTraceAveragePlayerSpeed = 0f;
                runtimeTraceMaxPlayerSpeed = 0f;
                runtimeTraceBallSpeed = 0f;
            }

            UpdateActiveEventLiveness(state);
        }

        private void ApplyScenePlaybackState(MatchResponse state)
        {
            if (GtexMatchController.MatchManagerAdapter.IsAvailable)
            {
                GtexMatchController.MatchManagerAdapter.ApplyExternalLiveState(
                    state.clockMinute,
                    state.homeScore,
                    state.awayScore,
                    ResolveMatchStatus(state));
                return;
            }

            if (config != null && config.verboseLogging)
            {
                Debug.LogWarning("[GTEX] MatchManager is not ready. Live state cached without scene application.");
            }
        }

        private void UpdateLiveBallIntent(MatchResponse previousState, MatchResponse nextState)
        {
            if (nextState == null ||
                nextState.ballPosition == null ||
                !GtexMatchController.MatchManagerAdapter.IsAvailable ||
                IsTerminalLiveState(nextState) ||
                ShouldSuppressBoundaryMotion(nextState))
            {
                ClearLiveBallIntent();
                return;
            }

            var previousHolderId = ResolveRuntimeBallHolderId(previousState);
            var nextHolderId = ResolveRuntimeBallHolderId(nextState);
            var holderChanged = !string.Equals(previousHolderId, nextHolderId, StringComparison.Ordinal);
            var activeEvent = nextState.ResolveActiveEvent();
            var eventType = NormalizeActiveEventTypeToken(nextState, activeEvent);
            var eventSuggestsTravel = EventSuggestsBallTravel(eventType);
            var ballAnchor = ResolvePredictedFieldPosition(nextState.ballPosition, 0f);
            ballAnchor.y = 0f;
            var ballVelocity = ResolvePlaybackBallVelocity(nextState.ballPosition, false);
            ballVelocity.y = 0f;
            var ballSpeed = ballVelocity.magnitude;

            if (holderChanged && !string.IsNullOrWhiteSpace(previousHolderId))
            {
                var sourcePlayerId = ResolvePreferredLiveBallSourcePlayerId(activeEvent, previousHolderId, previousHolderId);
                var targetPlayerId = ResolvePreferredLiveBallTargetPlayerId(activeEvent, nextHolderId, sourcePlayerId);
                var sourceTeamSide = ResolvePlayerTeamSideToken(previousState, sourcePlayerId);
                if (string.IsNullOrWhiteSpace(sourceTeamSide))
                {
                    sourceTeamSide = ResolvePlayerTeamSideToken(nextState, sourcePlayerId);
                }

                var sourceOrigin = ResolveRuntimePlayerPositionById(previousState, sourcePlayerId, ballAnchor);
                var intentTarget = ResolveLiveBallIntentTarget(
                    nextState,
                    targetPlayerId,
                    ballAnchor,
                    sourceOrigin,
                    ballVelocity,
                    LiveBallIntentFallbackTravelDistance,
                    sourceTeamSide);
                var contested = string.IsNullOrWhiteSpace(targetPlayerId);
                if (!contested && !string.IsNullOrWhiteSpace(sourceTeamSide))
                {
                    var nextHolderSide = ResolvePlayerTeamSideToken(nextState, targetPlayerId);
                    contested =
                        !string.IsNullOrWhiteSpace(nextHolderSide) &&
                        !string.Equals(nextHolderSide, sourceTeamSide, StringComparison.Ordinal);
                }

                BeginLiveBallIntent(
                    nextState,
                    sourcePlayerId,
                    targetPlayerId,
                    sourceTeamSide,
                    sourceOrigin,
                    intentTarget,
                    ballVelocity,
                    !string.IsNullOrWhiteSpace(eventType)
                        ? eventType
                        : string.IsNullOrWhiteSpace(targetPlayerId) ? "pass-flight" : "transition",
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

                var sourcePlayerId = ResolvePreferredLiveBallSourcePlayerId(activeEvent, previousHolderId);
                var targetPlayerId = ResolvePreferredLiveBallTargetPlayerId(activeEvent, string.Empty, sourcePlayerId);

                if (!string.IsNullOrWhiteSpace(sourcePlayerId) &&
                    (eventSuggestsTravel ||
                     !string.IsNullOrWhiteSpace(targetPlayerId) ||
                     ballSpeed >= LiveBallPassSpeedUnitsPerSecond))
                {
                    var sourceTeamSide = ResolvePlayerTeamSideToken(nextState, sourcePlayerId);
                    if (string.IsNullOrWhiteSpace(sourceTeamSide))
                    {
                        sourceTeamSide = ResolvePlayerTeamSideToken(previousState, sourcePlayerId);
                    }

                    var intentTarget = ResolveLiveBallIntentTarget(
                        nextState,
                        targetPlayerId,
                        ballAnchor,
                        ballAnchor,
                        ballVelocity,
                        LiveBallIntentFallbackTravelDistance + 2f,
                        sourceTeamSide);
                    var sourceOrigin = ResolveRuntimePlayerPositionById(nextState, sourcePlayerId, ballAnchor);
                    if ((sourceOrigin - ballAnchor).sqrMagnitude <= 0.0001f)
                    {
                        sourceOrigin = ResolveRuntimePlayerPositionById(previousState, sourcePlayerId, ballAnchor);
                    }

                    sourceOrigin = ResolveBallReleaseOrigin(
                        nextState,
                        sourcePlayerId,
                        sourceOrigin,
                        intentTarget - sourceOrigin);

                    BeginLiveBallIntent(
                        nextState,
                        sourcePlayerId,
                        targetPlayerId,
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
                var sourcePlayerId = ResolvePreferredLiveBallSourcePlayerId(activeEvent, previousHolderId, nextHolderId);
                var targetPlayerId = ResolvePreferredLiveBallTargetPlayerId(activeEvent, nextHolderId, sourcePlayerId);
                var sourceTeamSide = ResolvePlayerTeamSideToken(nextState, sourcePlayerId);
                if (string.IsNullOrWhiteSpace(sourceTeamSide))
                {
                    sourceTeamSide = ResolvePlayerTeamSideToken(previousState, sourcePlayerId);
                }

                var intentTarget = ResolveLiveBallIntentTarget(
                    nextState,
                    targetPlayerId,
                    ballAnchor,
                    ballAnchor,
                    ballVelocity,
                    LiveBallIntentFallbackTravelDistance + 2.25f,
                    sourceTeamSide);
                var sourceOrigin = ResolveRuntimePlayerPositionById(nextState, sourcePlayerId, ballAnchor);
                sourceOrigin = ResolveBallReleaseOrigin(
                    nextState,
                    sourcePlayerId,
                    sourceOrigin,
                    intentTarget - sourceOrigin);

                BeginLiveBallIntent(
                    nextState,
                    sourcePlayerId,
                    targetPlayerId,
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

            fallbackPosition.y = pitchSpace != null ? pitchSpace.GrassY : 0f;
            return fallbackPosition;
        }

        private Vector3 ResolveRuntimeFieldPosition(PlayerPosition livePlayer, MatchResponse state, Vector3 fallbackPosition)
        {
            if (TryGetBoundPlayer(livePlayer, out var boundPlayer) && boundPlayer != null && boundPlayer.IsValid)
            {
                return ClampToFieldBounds(boundPlayer.Position, livePlayer != null && livePlayer.isBall);
            }

            if (livePlayer != null && state != null && GtexMatchController.MatchManagerAdapter.IsAvailable)
            {
                return ClampToFieldBounds(ConvertIncomingPlaybackPosition(livePlayer, state).ClampedWorld, livePlayer.isBall);
            }

            if (playbackSanitizer != null &&
                (fallbackPosition.sqrMagnitude <= 0.0001f || !GtexPlaybackSanitizer.IsFinite(fallbackPosition)))
            {
                return livePlayer != null && livePlayer.isBall
                    ? playbackSanitizer.SanitizeBallPosition(pitchSpace != null ? pitchSpace.Center : Vector3.zero)
                    : playbackSanitizer.SanitizePlayerPosition(pitchSpace != null ? pitchSpace.Center : Vector3.zero);
            }

            return ClampToFieldBounds(fallbackPosition, livePlayer != null && livePlayer.isBall);
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

        private static string ResolveActiveEventPrimaryPlayerId(Event activeEvent)
        {
            return ((activeEvent != null ? activeEvent.primaryPlayerId : string.Empty) ?? string.Empty).Trim();
        }

        private static string ResolveActiveEventSecondaryPlayerId(Event activeEvent)
        {
            return ((activeEvent != null ? activeEvent.secondaryPlayerId : string.Empty) ?? string.Empty).Trim();
        }

        private static bool IsPassLikeEventType(string eventType)
        {
            var normalized = (eventType ?? string.Empty).Trim().ToLowerInvariant();
            return normalized.Contains("pass") ||
                   normalized.Contains("assist") ||
                   normalized.Contains("through") ||
                   normalized.Contains("cross") ||
                   normalized.Contains("corner");
        }

        private static bool IsShotLikeEventType(string eventType)
        {
            var normalized = (eventType ?? string.Empty).Trim().ToLowerInvariant();
            return normalized.Contains("save") ||
                   normalized.Contains("miss") ||
                   normalized.Contains("goal") ||
                   normalized.Contains("shot") ||
                   normalized.Contains("chance");
        }

        private static bool EventSuggestsBallTravel(string eventType)
        {
            return IsShotLikeEventType(eventType) || IsPassLikeEventType(eventType);
        }

        private static string ResolvePreferredLiveBallSourcePlayerId(Event activeEvent, string fallbackSourcePlayerId, string fallbackHolderPlayerId = null)
        {
            var primaryPlayerId = ResolveActiveEventPrimaryPlayerId(activeEvent);
            if (!string.IsNullOrWhiteSpace(primaryPlayerId))
            {
                return primaryPlayerId;
            }

            var fallbackSource = (fallbackSourcePlayerId ?? string.Empty).Trim();
            if (!string.IsNullOrWhiteSpace(fallbackSource))
            {
                return fallbackSource;
            }

            return (fallbackHolderPlayerId ?? string.Empty).Trim();
        }

        private static string ResolvePreferredLiveBallTargetPlayerId(Event activeEvent, string fallbackTargetPlayerId, string sourcePlayerId)
        {
            var secondaryPlayerId = ResolveActiveEventSecondaryPlayerId(activeEvent);
            if (!string.IsNullOrWhiteSpace(secondaryPlayerId) &&
                !string.Equals(secondaryPlayerId, sourcePlayerId, StringComparison.Ordinal))
            {
                return secondaryPlayerId;
            }

            var fallbackTarget = (fallbackTargetPlayerId ?? string.Empty).Trim();
            if (!string.IsNullOrWhiteSpace(fallbackTarget) &&
                !string.Equals(fallbackTarget, sourcePlayerId, StringComparison.Ordinal))
            {
                return fallbackTarget;
            }

            return string.Empty;
        }

        private void MaintainLiveTransport()
        {
            if (!matchLoaded || config == null || isDestroyed)
            {
                return;
            }

            if (ShouldStopTransportAfterTerminal())
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
            staleThreshold = Mathf.Min(staleThreshold, WebSocketStaleHardCapSeconds);
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
            if (ShouldStopTransportAfterTerminal())
            {
                nextWebSocketReconnectAt = float.PositiveInfinity;
                AppendRuntimeTrace("ws", "terminal state reached. reconnect suppressed. reason=" + reason);
                FlushRuntimeTrace(false);
                return;
            }

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
                if (scheduleReconnect && !ShouldStopTransportAfterTerminal())
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

            if (ShouldStopTransportAfterTerminal())
            {
                nextWebSocketReconnectAt = float.PositiveInfinity;
                return;
            }

            webSocketReconnectAttempts += 1;
            var liveAndStuck =
                lastKnownState != null &&
                !IsTerminalLiveState(lastKnownState) &&
                webSocketReconnectAttempts >= WebSocketFastReconnectAttemptThreshold;
            var delay =
                liveAndStuck
                    ? WebSocketFastReconnectDelaySeconds
                    : Mathf.Min(
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
            duplicateBindingKeys.Clear();
            loggedBindingDiagnostics.Clear();

            if (currentState == null || !GtexMatchController.MatchManagerAdapter.HasTeams)
            {
                return;
            }

            BindPlayersForSide(FilterLivePlayersBySide("home"), GtexMatchController.MatchManagerAdapter.GetHomePlayers());
            BindPlayersForSide(FilterLivePlayersBySide("away"), GtexMatchController.MatchManagerAdapter.GetAwayPlayers());
            AttachGoalkeeperBehaviors();

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

        private void AttachGoalkeeperBehaviors()
        {
            if (currentState == null || currentState.players == null)
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

                var role = ((livePlayer.role ?? string.Empty).Trim().ToUpperInvariant());
                if (role != "GK" && role != "GOALKEEPER")
                {
                    continue;
                }

                if (!TryGetBoundPlayer(livePlayer, out var handle) || handle == null || !handle.IsValid)
                {
                    continue;
                }

                var isHome =
                    string.Equals(
                        NormalizeTeamSideToken(livePlayer.teamSide),
                        "home",
                        StringComparison.Ordinal);
                GtexGoalkeeperBehavior.AttachToGoalkeeper(handle.RawPlayer, isHome);
            }
        }

        private void DrivePlayers(float dt)
        {
            if (currentState == null)
            {
                return;
            }

            var suppressBoundaryMotion = ShouldSuppressBoundaryMotion(currentState);
            var predictionSeconds = ResolveLivePredictionSeconds();
            var livePlayers = currentState.players;
            var traceSamples = Time.unscaledTime - runtimeTraceLastPlaybackSampleAt >= PlaybackTraceSampleIntervalSeconds;
            var tracedPlayerSamples = 0;
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

                var tracePlayerSample = traceSamples && tracedPlayerSamples < 3;
                var appliedSpeed = ApplyLivePlayerState(
                    livePlayer,
                    player,
                    dt,
                    predictionSeconds,
                    false,
                    tracePlayerSample,
                    suppressBoundaryMotion);
                if (tracePlayerSample)
                {
                    tracedPlayerSamples += 1;
                }
                drivenPlayers += 1;
                accumulatedSpeed += appliedSpeed;
                maxSpeed = Mathf.Max(maxSpeed, appliedSpeed);
                if (appliedSpeed > 0.35f)
                {
                    movingPlayers += 1;
                }
            }

            if (tracedPlayerSamples > 0)
            {
                runtimeTraceLastPlaybackSampleAt = Time.unscaledTime;
            }

            runtimeTraceDrivenPlayerCount = drivenPlayers;
            runtimeTraceMovingPlayerCount = movingPlayers;
            runtimeTraceAveragePlayerSpeed = drivenPlayers > 0 ? accumulatedSpeed / drivenPlayers : 0f;
            runtimeTraceMaxPlayerSpeed = maxSpeed;
            ValidateActiveMoverBudgets(livePlayers);
        }

        private void ValidateActiveMoverBudgets(PlayerPosition[] livePlayers)
        {
            lastHomeActiveMoverBreakdown = ResolveObservedActiveMoversForSide(currentState, "home");
            lastAwayActiveMoverBreakdown = ResolveObservedActiveMoversForSide(currentState, "away");

            if (config == null || !config.verboseLogging || currentState == null || pitchZones == null || livePlayers == null)
            {
                return;
            }

            var referenceHome = ResolveReferenceActiveMoversForSide(currentState, "home");
            var referenceAway = ResolveReferenceActiveMoversForSide(currentState, "away");

            void ReportIfOver(string side, string category, int observed, int allowed, float throttle = 2f)
            {
                if (observed <= allowed)
                {
                    return;
                }

                ReportRuntimeValidation(
                    side + "_" + category + "_over_budget",
                    "observed=" + observed + " allowed=" + allowed,
                    throttle);
            }

            ReportIfOver("home", "attack_runs", lastHomeActiveMoverBreakdown.AttackRuns, MaxActiveAttackRuns);
            ReportIfOver("away", "attack_runs", lastAwayActiveMoverBreakdown.AttackRuns, MaxActiveAttackRuns);
            ReportIfOver("home", "support_options", lastHomeActiveMoverBreakdown.SupportOptions, MaxActiveSupportOptions);
            ReportIfOver("away", "support_options", lastAwayActiveMoverBreakdown.SupportOptions, MaxActiveSupportOptions);
            ReportIfOver("home", "pressers", lastHomeActiveMoverBreakdown.Pressers, MaxActivePressers);
            ReportIfOver("away", "pressers", lastAwayActiveMoverBreakdown.Pressers, MaxActivePressers);
            ReportIfOver("home", "far_side_sprints", lastHomeActiveMoverBreakdown.FarSideDrifts, MaxFarSideSprints);
            ReportIfOver("away", "far_side_sprints", lastAwayActiveMoverBreakdown.FarSideDrifts, MaxFarSideSprints);

            if (lastHomeActiveMoverBreakdown.TotalOutfield > referenceHome.TotalOutfield + 1 ||
                lastAwayActiveMoverBreakdown.TotalOutfield > referenceAway.TotalOutfield + 1)
            {
                ReportRuntimeValidation(
                    "movement_budget_diverged_from_reference",
                    "homeObserved=" + FormatRuntimeMovers(lastHomeActiveMoverBreakdown) +
                    " homeReference=" + FormatRuntimeMovers(referenceHome) +
                    " awayObserved=" + FormatRuntimeMovers(lastAwayActiveMoverBreakdown) +
                    " awayReference=" + FormatRuntimeMovers(referenceAway),
                    2f);
            }
        }

        private void DriveBall()
        {
            if (currentState == null || currentState.ballPosition == null || !GtexMatchController.BallAdapter.IsAvailable)
            {
                ClearSyntheticBallTransit();
                hasFilteredBallTarget = false;
                runtimeTraceBallSpeed = 0f;
                return;
            }

            if (TryDriveSyntheticBallTransit())
            {
                return;
            }

            var ballHolder = ResolveBallHolder(currentState.ballPosition);
            var ballConversion = ConvertIncomingPlaybackPosition(currentState.ballPosition, currentState);
            var suppressBoundaryMotion = ShouldSuppressBoundaryMotion(currentState);
            var targetPosition = ballHolder != null || suppressBoundaryMotion
                ? ballConversion.ClampedWorld
                : ResolvePredictedFieldPosition(currentState.ballPosition, ResolveLivePredictionSeconds());
            var ballVelocity = ResolvePlaybackBallVelocity(currentState.ballPosition, suppressBoundaryMotion);
            runtimeTraceBallSpeed = new Vector3(ballVelocity.x, 0f, ballVelocity.z).magnitude;
            var appliedPosition = ClampToFieldBounds(targetPosition, true);
            appliedPosition = FilterLiveBallTarget(appliedPosition, ballHolder != null || suppressBoundaryMotion);

            if (Time.unscaledTime - runtimeTraceLastBallSampleAt >= PlaybackTraceSampleIntervalSeconds)
            {
                runtimeTraceLastBallSampleAt = Time.unscaledTime;
                TraceBallPitchSample(ballConversion, appliedPosition, ballHolder);
            }

            GtexMatchController.BallAdapter.ApplyExternalState(
                appliedPosition,
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

                ApplyLivePlayerState(livePlayer, player, 0f, 0f, true, false, true);
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

                if (!TryGetBoundPlayer(livePlayer, out _) && !HasKnownBindingIssue(livePlayer))
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
                    LogMissingBindingDiagnostic(livePlayer, "no-unity-candidate");
                    continue;
                }

                var targetPosition = ConvertIncomingPlaybackPosition(livePlayer, currentState).ClampedWorld;
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
                    LogMissingBindingDiagnostic(livePlayer, "no-unity-candidate");
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

            var storedAnyKey = false;
            if (!string.IsNullOrWhiteSpace(livePlayer.entityId))
            {
                storedAnyKey |= TryStorePlayerBindingKey(livePlayer.entityId, livePlayer, player);
            }

            if (!string.IsNullOrWhiteSpace(livePlayer.playerId))
            {
                storedAnyKey |= TryStorePlayerBindingKey("player:" + livePlayer.playerId, livePlayer, player);
            }

            if (!storedAnyKey)
            {
                LogMissingBindingDiagnostic(livePlayer, "missing-storage-key");
            }
        }

        private bool TryStorePlayerBindingKey(string key, PlayerPosition livePlayer, GtexLegacyPlayerHandle player)
        {
            if (string.IsNullOrWhiteSpace(key) || player == null || !player.IsValid)
            {
                return false;
            }

            if (playerBindings.TryGetValue(key, out var existing) &&
                existing != null &&
                existing.IsValid &&
                existing.RawPlayer != player.RawPlayer)
            {
                duplicateBindingKeys.Add(key);
                var message =
                    "duplicate key=" +
                    key +
                    " existing=" +
                    DescribeLegacyPlayer(existing) +
                    " incoming=" +
                    DescribeLivePlayer(livePlayer);
                AppendRuntimeTrace("binding", message);
                Debug.LogWarning("[GTEX] Duplicate live-player binding " + message + ". Ambiguous binding skipped.");
                return false;
            }

            playerBindings[key] = player;
            return true;
        }

        private bool HasKnownBindingIssue(PlayerPosition livePlayer)
        {
            if (livePlayer == null)
            {
                return false;
            }

            if (string.IsNullOrWhiteSpace(livePlayer.entityId) && string.IsNullOrWhiteSpace(livePlayer.playerId))
            {
                return true;
            }

            return (!string.IsNullOrWhiteSpace(livePlayer.entityId) && duplicateBindingKeys.Contains(livePlayer.entityId)) ||
                   (!string.IsNullOrWhiteSpace(livePlayer.playerId) && duplicateBindingKeys.Contains("player:" + livePlayer.playerId));
        }

        private void LogMissingBindingDiagnostic(PlayerPosition livePlayer, string reason)
        {
            var diagnosticKey = ResolveBindingDiagnosticKey(livePlayer, reason);
            if (!loggedBindingDiagnostics.Add(diagnosticKey))
            {
                return;
            }

            var message = "reason=" + reason + " player=" + DescribeLivePlayer(livePlayer);
            AppendRuntimeTrace("binding", message);
            Debug.LogWarning("[GTEX] Unresolved live-player binding " + message + ".");
        }

        private static string ResolveBindingDiagnosticKey(PlayerPosition livePlayer, string reason)
        {
            if (livePlayer == null)
            {
                return "null:" + reason;
            }

            var storageKey = ResolveBindingStorageKey(livePlayer);
            if (!string.IsNullOrWhiteSpace(storageKey))
            {
                return storageKey + ":" + reason;
            }

            return
                (livePlayer.teamSide ?? string.Empty) +
                ":" +
                livePlayer.shirtNumber +
                ":" +
                (livePlayer.label ?? string.Empty) +
                ":" +
                reason;
        }

        private static string DescribeLivePlayer(PlayerPosition livePlayer)
        {
            if (livePlayer == null)
            {
                return "null";
            }

            return
                "label=" +
                (livePlayer.label ?? string.Empty) +
                " entityId=" +
                (livePlayer.entityId ?? string.Empty) +
                " playerId=" +
                (livePlayer.playerId ?? string.Empty) +
                " shirt=" +
                livePlayer.shirtNumber +
                " side=" +
                (livePlayer.teamSide ?? string.Empty) +
                " role=" +
                (livePlayer.role ?? string.Empty);
        }

        private static string DescribeLegacyPlayer(GtexLegacyPlayerHandle player)
        {
            if (player == null)
            {
                return "null";
            }

            return
                "shirt=" +
                player.ShirtNumber +
                " dbId=" +
                (player.DatabasePlayerId.HasValue ? player.DatabasePlayerId.Value.ToString() : string.Empty) +
                " role=" +
                player.PositionRole;
        }

        private bool TryGetBoundPlayer(PlayerPosition livePlayer, out GtexLegacyPlayerHandle player)
        {
            if (livePlayer != null)
            {
                if (!string.IsNullOrWhiteSpace(livePlayer.entityId) &&
                    !duplicateBindingKeys.Contains(livePlayer.entityId) &&
                    playerBindings.TryGetValue(livePlayer.entityId, out player) &&
                    player != null &&
                    player.IsValid)
                {
                    return true;
                }

                if (!string.IsNullOrWhiteSpace(livePlayer.playerId) &&
                    !duplicateBindingKeys.Contains("player:" + livePlayer.playerId) &&
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
                !duplicateBindingKeys.Contains("player:" + playerId) &&
                playerBindings.TryGetValue("player:" + playerId, out player) &&
                player != null &&
                player.IsValid)
            {
                return true;
            }

            player = null;
            return false;
        }

        private float ApplyLivePlayerState(
            PlayerPosition livePlayer,
            GtexLegacyPlayerHandle player,
            float dt,
            float predictionSeconds,
            bool snap,
            bool traceSample,
            bool suppressBoundaryMotion)
        {
            if (livePlayer == null || player == null || !player.IsValid)
            {
                return 0f;
            }

            var currentPosition = player.Position;
            var directIncomingPosition = ConvertIncomingPlaybackPosition(livePlayer, currentState);
            var liveVelocity = snap ? Vector3.zero : ResolveLiveFieldVelocity(livePlayer);
            var targetPosition = snap
                ? directIncomingPosition.ClampedWorld
                : ResolvePredictedFieldPosition(livePlayer, predictionSeconds);
            if (!snap)
            {
                if (suppressBoundaryMotion)
                {
                    targetPosition = directIncomingPosition.ClampedWorld;
                }
                else
                {
                    targetPosition = ResolveBehaviorAnchorPosition(livePlayer, currentPosition, targetPosition);
                    targetPosition = ResolveBehaviorDrivenFieldPosition(livePlayer, targetPosition, currentPosition, liveVelocity);
                    targetPosition = ApplyStructuredTeamSpacing(livePlayer, targetPosition);
                }

                targetPosition = FilterLivePlayerTarget(livePlayer, targetPosition, dt, suppressBoundaryMotion);
            }

            var targetDistance = Vector3.Distance(currentPosition, targetPosition);
            var hardSnapDistance = ResolveHardSnapDistance(suppressBoundaryMotion);
            var requiresHardSnap = snap || targetDistance >= hardSnapDistance;
            var movementUrgency =
                requiresHardSnap || suppressBoundaryMotion
                    ? 1f
                    : ResolveLiveMovementUrgency(livePlayer, currentPosition);
            var movementDeadzone = ResolveLiveMovementDeadzone(movementUrgency, suppressBoundaryMotion);
            var normalizedState = ((livePlayer.state ?? string.Empty).Trim().ToLowerInvariant());
            var desiredMovementDelta = targetPosition - currentPosition;
            desiredMovementDelta.y = 0f;
            var desiredMoveDirection =
                desiredMovementDelta.sqrMagnitude > 0.0001f
                    ? desiredMovementDelta.normalized
                    : Vector3.zero;
            var desiredLookDirection = ResolveLookDirection(livePlayer, desiredMovementDelta, player);
            var targetRotation = player.Rotation;
            var turnAngle = 0f;
            var turnMovementFactor = 1f;
            var forwardDot = 1f;
            var canMoveNonForward = false;
            if (desiredLookDirection.sqrMagnitude > 0.0001f)
            {
                targetRotation = Quaternion.LookRotation(desiredLookDirection.normalized, Vector3.up);
                if (!requiresHardSnap)
                {
                    turnAngle = Quaternion.Angle(player.Rotation, targetRotation);
                    turnMovementFactor = Mathf.InverseLerp(92f, 10f, turnAngle);
                    turnMovementFactor = Mathf.Lerp(0.12f, 1f, turnMovementFactor);
                }
            }

            if (!requiresHardSnap &&
                desiredMoveDirection.sqrMagnitude > 0.0001f &&
                player.Forward.sqrMagnitude > 0.0001f)
            {
                forwardDot = Vector3.Dot(player.Forward.normalized, desiredMoveDirection);
                canMoveNonForward = CanAllowNonForwardMovement(livePlayer, normalizedState, movementUrgency, targetDistance);
                var isBackwardOrSideways = forwardDot < 0.25f;
                if (isBackwardOrSideways)
                {
                    if (canMoveNonForward)
                    {
                        turnMovementFactor = Mathf.Min(turnMovementFactor, 0.46f);
                        ReportRuntimeValidation(
                            "non_forward_motion_allowed",
                            "player=" + DescribeLivePlayer(livePlayer) +
                            " state=" + normalizedState +
                            " dot=" + forwardDot.ToString("0.##"),
                            2.5f);
                    }
                    else
                    {
                        var originalTurnFactor = turnMovementFactor;
                        turnMovementFactor *= Mathf.Clamp01(Mathf.InverseLerp(-0.1f, 0.65f, forwardDot)) * 0.18f;
                        ReportRuntimeValidation(
                            "movement_throttled_while_rotating",
                            "player=" + DescribeLivePlayer(livePlayer) +
                            " state=" + normalizedState +
                            " dot=" + forwardDot.ToString("0.##") +
                            " factor=" + originalTurnFactor.ToString("0.##") + "->" + turnMovementFactor.ToString("0.##"),
                            1.5f);
                    }
                }
            }

            Vector3 appliedPosition;
            if (requiresHardSnap)
            {
                appliedPosition = targetPosition;
            }
            else if (targetDistance <= movementDeadzone)
            {
                appliedPosition = currentPosition;
            }
            else
            {
                var desiredSpeed =
                    ResolveLivePlayerMoveSpeed(
                        livePlayer,
                        currentPosition,
                        targetPosition,
                        liveVelocity,
                        targetDistance,
                        movementUrgency,
                        suppressBoundaryMotion) *
                    (canMoveNonForward ? 0.58f : 1f) *
                    turnMovementFactor;
                var moveException = GetMoveExceptionForPlayer(livePlayer, normalizedState, targetDistance);
                var desiredVelocity = desiredMoveDirection * desiredSpeed;
                var legalVelocity =
                    ResolveLegalPlayerVelocity(
                        player,
                        desiredVelocity,
                        Mathf.Max(dt, LiveTraceDtFloorSeconds),
                        desiredSpeed >= 4.5f && !canMoveNonForward,
                        moveException);
                appliedPosition = Vector3.MoveTowards(
                    currentPosition,
                    targetPosition,
                    legalVelocity.magnitude * Mathf.Max(dt, 0f));
            }

            appliedPosition = ClampToFieldBounds(appliedPosition, false);

            var appliedRotation = player.Rotation;
            if (desiredLookDirection.sqrMagnitude > 0.0001f)
            {
                appliedRotation = requiresHardSnap
                    ? targetRotation
                    : Quaternion.Slerp(
                        player.Rotation,
                        targetRotation,
                        Mathf.Clamp01(dt * Mathf.Lerp(LivePlayerRotationLerpSpeed, LivePlayerRotationLerpSpeed * 1.6f, Mathf.InverseLerp(72f, 12f, turnAngle))));
            }

            if (traceSample)
            {
                AppendRuntimeTrace(
                    "pitch-sample",
                    "player=" +
                    DescribeLivePlayer(livePlayer) +
                    " raw=" +
                    FormatPlaybackVector(directIncomingPosition.RawIncoming) +
                    " converted=" +
                    FormatPlaybackVector(directIncomingPosition.ConvertedWorld) +
                    " clamped=" +
                    FormatPlaybackVector(directIncomingPosition.ClampedWorld));
            }

            player.SetExternalPlaybackPose(appliedPosition, appliedRotation, requiresHardSnap);

            ApplyLiveAnimatorState(
                livePlayer,
                player,
                appliedPosition - currentPosition,
                liveVelocity,
                dt,
                requiresHardSnap,
                normalizedState,
                forwardDot,
                canMoveNonForward);
            if (requiresHardSnap || dt <= 0f)
            {
                return 0f;
            }

            var frameMovement = appliedPosition - currentPosition;
            frameMovement.y = 0f;
            var actualSpeed = frameMovement.magnitude / Mathf.Max(dt, LiveTraceDtFloorSeconds);
            var liveSpeed = new Vector3(liveVelocity.x, 0f, liveVelocity.z).magnitude;
            if (suppressBoundaryMotion)
            {
                return Mathf.Min(actualSpeed, ResolveLiveRoleSpeedCap(livePlayer));
            }

            var weightedLiveSpeed = liveSpeed * Mathf.Clamp01(Mathf.InverseLerp(0.22f, 0.9f, movementUrgency));
            return Mathf.Max(actualSpeed, weightedLiveSpeed);
        }

        private Vector3 ResolveBehaviorAnchorPosition(PlayerPosition livePlayer, Vector3 currentPosition, Vector3 predictedTarget)
        {
            predictedTarget = ClampToFieldBounds(predictedTarget, false);
            currentPosition = ClampToFieldBounds(currentPosition, false);
            var movementUrgency = ResolveLiveMovementUrgency(livePlayer, currentPosition);
            var bindingKey = ResolveBindingStorageKey(livePlayer);
            if (string.IsNullOrWhiteSpace(bindingKey) ||
                !filteredPlayerTargets.TryGetValue(bindingKey, out var previousTarget))
            {
                return ClampToFieldBounds(
                    Vector3.Lerp(
                        currentPosition,
                        predictedTarget,
                        livePlayer != null && livePlayer.hasPossession
                            ? Mathf.Lerp(0.58f, 0.76f, movementUrgency)
                            : Mathf.Lerp(0.08f, 0.42f, movementUrgency)),
                    false);
            }

            var anchorBlend =
                livePlayer != null && livePlayer.hasPossession
                    ? Mathf.Lerp(0.56f, 0.78f, movementUrgency)
                    : (livePlayer != null && livePlayer.active
                        ? Mathf.Lerp(0.06f, 0.36f, movementUrgency)
                        : 0.12f);
            var anchoredTarget = Vector3.Lerp(previousTarget, predictedTarget, anchorBlend);
            var maxShift =
                (ResolveLiveRoleSpeedCap(livePlayer) * Mathf.Lerp(0.12f, 0.82f, movementUrgency) +
                 Mathf.Lerp(0.04f, 0.85f, movementUrgency)) *
                Mathf.Max(Time.deltaTime, LiveTraceDtFloorSeconds);
            anchoredTarget = Vector3.MoveTowards(previousTarget, anchoredTarget, maxShift);
            return ClampToFieldBounds(anchoredTarget, false);
        }

        private float ResolveLiveMovementUrgency(PlayerPosition livePlayer, Vector3 currentPosition)
        {
            if (livePlayer == null || livePlayer.isBall || !livePlayer.active)
            {
                return 0f;
            }

            if (livePlayer.hasPossession)
            {
                return 1f;
            }

            if (currentState == null || currentState.ballPosition == null)
            {
                return 0.5f;
            }

            currentPosition.y = 0f;
            var livePlayerId = ((livePlayer.playerId ?? string.Empty).Trim());
            var possessionSide = ResolvePossessionSideToken();
            var playerTeamSide = NormalizeTeamSideToken(livePlayer.teamSide);
            var looseBall =
                string.IsNullOrWhiteSpace(possessionSide) ||
                string.IsNullOrWhiteSpace(currentState.ballPosition.playerId);
            var sameTeamAsPossession =
                !string.IsNullOrWhiteSpace(playerTeamSide) &&
                string.Equals(playerTeamSide, possessionSide, StringComparison.OrdinalIgnoreCase);
            var actionAnchor = ResolvePredictedFieldPosition(currentState.ballPosition, ResolveLivePredictionSeconds());
            var sameSideBallRank = ResolveTeamBallRank(livePlayer, currentPosition, actionAnchor);
            if (sameSideBallRank == int.MaxValue)
            {
                sameSideBallRank = 4;
            }

            var hasActiveBallIntent =
                Time.unscaledTime < liveBallIntentExpiresAt &&
                !string.IsNullOrWhiteSpace(liveBallIntentReason);
            var intentTargetPlayerId =
                hasActiveBallIntent
                    ? (liveBallIntentTargetPlayerId ?? string.Empty).Trim()
                    : string.Empty;
            var isIntentReceiver =
                !string.IsNullOrWhiteSpace(livePlayerId) &&
                !string.IsNullOrWhiteSpace(intentTargetPlayerId) &&
                string.Equals(livePlayerId, intentTargetPlayerId, StringComparison.Ordinal);

            var primaryThreatPlayerId =
                !string.IsNullOrWhiteSpace(intentTargetPlayerId)
                    ? intentTargetPlayerId
                    : ResolveRuntimeBallHolderId(currentState);
            if (string.IsNullOrWhiteSpace(primaryThreatPlayerId))
            {
                primaryThreatPlayerId = (liveBallIntentSourcePlayerId ?? string.Empty).Trim();
            }

            var primaryThreatPosition = ResolveRuntimePlayerPositionById(currentState, primaryThreatPlayerId, actionAnchor);
            primaryThreatPosition.y = 0f;
            var markRank =
                string.IsNullOrWhiteSpace(primaryThreatPlayerId)
                    ? int.MaxValue
                    : ResolveTeamDistanceRank(livePlayer, currentPosition, primaryThreatPosition);
            var roleBucket = ResolveLiveRoleBucket(livePlayer);
            var eventType = ResolveActiveEventTypeToken();

            float urgency;
            if (looseBall)
            {
                urgency =
                    sameSideBallRank == 0 ? 0.94f :
                    sameSideBallRank == 1 ? 0.72f :
                    sameSideBallRank == 2 ? 0.46f :
                    0.14f;
            }
            else if (sameTeamAsPossession)
            {
                urgency =
                    isIntentReceiver ? 0.98f :
                    sameSideBallRank == 0 ? 0.52f :
                    sameSideBallRank == 1 ? 0.08f :
                    sameSideBallRank == 2 ? 0.02f :
                    0.005f;
            }
            else
            {
                urgency =
                    markRank == 0 ? 0.66f :
                    markRank == 1 ? 0.18f :
                    sameSideBallRank == 0 ? 0.11f :
                    sameSideBallRank == 1 ? 0.05f :
                    0.012f;
            }

            if (EventSuggestsBallTravel(eventType) && sameTeamAsPossession && sameSideBallRank <= 1)
            {
                urgency = Mathf.Max(urgency, isIntentReceiver ? 0.92f : sameSideBallRank == 0 ? 0.64f : 0.18f);
            }

            if (roleBucket == 0)
            {
                urgency *= 0.72f;
            }

            return Mathf.Clamp01(urgency);
        }

        private static float ResolveLiveMovementDeadzone(float movementUrgency, bool suppressBoundaryMotion)
        {
            if (suppressBoundaryMotion)
            {
                return 0.08f;
            }

            return Mathf.Lerp(2.45f, 0.18f, Mathf.Clamp01(movementUrgency));
        }

        private void ApplyLiveAnimatorState(
            PlayerPosition livePlayer,
            GtexLegacyPlayerHandle player,
            Vector3 frameMovement,
            Vector3 liveVelocity,
            float dt,
            bool snap,
            string normalizedState,
            float forwardDot,
            bool canMoveNonForward)
        {
            if (player == null || !player.IsValid)
            {
                return;
            }

            var animationState = (livePlayer.animationState ?? string.Empty).Trim().ToLowerInvariant();
            var settledPhase = !IsOpenPlayPhase(ResolveControllerPhase(currentState));
            var movementUrgency =
                snap
                    ? 1f
                    : ResolveLiveMovementUrgency(livePlayer, player.Position);
            var idleThreshold = Mathf.Lerp(0.34f, LiveAnimatorIdlePlanarSpeedUnitsPerSecond, movementUrgency);
            var locomotionThreshold = Mathf.Lerp(0.72f, LiveAnimatorLocomotionPlanarSpeedUnitsPerSecond, movementUrgency);
            var intendedMotionWeight = Mathf.Clamp01(Mathf.InverseLerp(0.42f, 0.9f, movementUrgency));
            var actualPlanarVelocity =
                !snap && dt > 0f
                    ? new Vector3(frameMovement.x, 0f, frameMovement.z) / Mathf.Max(dt, LiveTraceDtFloorSeconds)
                    : Vector3.zero;
            var intendedPlanarVelocity = snap ? Vector3.zero : new Vector3(liveVelocity.x, 0f, liveVelocity.z);
            var actualPlanarSpeed = actualPlanarVelocity.magnitude;
            var intendedPlanarSpeed = intendedPlanarVelocity.magnitude;
            var syntheticMotion =
                !snap &&
                (actualPlanarSpeed > idleThreshold ||
                 (intendedMotionWeight > 0.15f &&
                  intendedPlanarSpeed > locomotionThreshold * 1.15f &&
                  actualPlanarSpeed >= idleThreshold * 0.35f));
            var explicitIdle =
                settledPhase ||
                !livePlayer.active ||
                animationState == "sent_off" ||
                animationState == "save" ||
                animationState == "celebrate" ||
                (!syntheticMotion && (animationState == "idle" || animationState == "set_piece"));

            var moveSpeed = 0f;
            var localDirection = Vector3.zero;

            if (!explicitIdle && dt > 0f)
            {
                var roleSpeedCap = Mathf.Max(ResolveLiveRoleSpeedCap(livePlayer), 0.001f);
                var actualSpeed01 = Mathf.Clamp01(actualPlanarSpeed / roleSpeedCap);
                var intendedSpeed01 = Mathf.Clamp01(intendedPlanarSpeed / roleSpeedCap);
                var stateSpeed01 = Mathf.Clamp01(livePlayer.speedRatio);
                var stateBias =
                    actualPlanarSpeed >= locomotionThreshold ||
                    (intendedMotionWeight > 0.55f &&
                     intendedPlanarSpeed >= locomotionThreshold &&
                     actualPlanarSpeed >= idleThreshold * 0.55f)
                        ? stateSpeed01 * (livePlayer.hasPossession ? 0.28f : 0.18f)
                        : 0f;
                var directionSource =
                    actualPlanarSpeed >= idleThreshold
                        ? actualPlanarVelocity
                        : (intendedMotionWeight > 0.1f && intendedPlanarSpeed >= locomotionThreshold
                            ? intendedPlanarVelocity
                            : Vector3.zero);

                if (directionSource.sqrMagnitude > 0.0001f)
                {
                    moveSpeed = Mathf.Clamp01(
                        Mathf.Max(
                            actualSpeed01 * Mathf.Lerp(1.04f, 1.42f, movementUrgency),
                            intendedSpeed01 * 0.16f * intendedMotionWeight,
                            stateBias * Mathf.Lerp(0.45f, 0.72f, movementUrgency)));

                    if (movementUrgency >= 0.8f && actualPlanarSpeed >= locomotionThreshold * 0.78f)
                    {
                        moveSpeed = Mathf.Max(moveSpeed, 0.7f);
                    }
                    else if (movementUrgency >= 0.6f && actualPlanarSpeed >= locomotionThreshold)
                    {
                        moveSpeed = Mathf.Max(moveSpeed, 0.52f);
                    }

                    localDirection = player.InverseTransformDirection(directionSource.normalized);
                }
            }

            var locomotionHorizontal = 0f;
            var locomotionVertical = 0f;
            if (!explicitIdle && moveSpeed > 0.01f)
            {
                if (canMoveNonForward)
                {
                    locomotionHorizontal = Mathf.Clamp(localDirection.x, -0.55f, 0.55f);
                    locomotionVertical = Mathf.Clamp(localDirection.z, -0.55f, 0.42f);
                    moveSpeed = Mathf.Min(moveSpeed, 0.58f);
                }
                else
                {
                    if (forwardDot < 0.25f)
                    {
                        moveSpeed *= Mathf.Clamp01(Mathf.InverseLerp(-0.05f, 0.6f, forwardDot));
                    }

                    locomotionHorizontal = Mathf.Clamp(localDirection.x, -0.28f, 0.28f);
                    locomotionVertical = Mathf.Max(0f, localDirection.z);
                }
            }

            if (!canMoveNonForward && forwardDot < 0.15f && moveSpeed > 0.28f)
            {
                ReportRuntimeValidation(
                    "backward_sprint_blocked",
                    "player=" + DescribeLivePlayer(livePlayer) +
                    " state=" + normalizedState +
                    " dot=" + forwardDot.ToString("0.##") +
                    " speed=" + moveSpeed.ToString("0.##"),
                    1.25f);
                moveSpeed = Mathf.Min(moveSpeed, 0.24f);
                locomotionVertical = 0f;
            }

            var bindingKey = ResolveBindingStorageKey(livePlayer);
            ApplyFilteredExternalAnimatorState(
                bindingKey,
                player,
                livePlayer.hasPossession,
                explicitIdle ? 0f : moveSpeed,
                locomotionHorizontal,
                locomotionVertical,
                dt,
                snap,
                explicitIdle,
                canMoveNonForward);

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

        private void ApplyFilteredExternalAnimatorState(
            string bindingKey,
            GtexLegacyPlayerHandle player,
            bool hasPossession,
            float moveSpeed,
            float horizontal,
            float vertical,
            float dt,
            bool snap,
            bool explicitIdle,
            bool canMoveNonForward)
        {
            if (player == null || !player.IsValid)
            {
                return;
            }

            if (snap || string.IsNullOrWhiteSpace(bindingKey) || dt <= 0f)
            {
                player.ApplyExternalAnimatorState(hasPossession, moveSpeed, horizontal, vertical);
                if (!string.IsNullOrWhiteSpace(bindingKey))
                {
                    filteredAnimatorStates[bindingKey] = new FilteredAnimatorState
                    {
                        MoveSpeed = moveSpeed,
                        Horizontal = horizontal,
                        Vertical = vertical,
                    };
                }

                return;
            }

            filteredAnimatorStates.TryGetValue(bindingKey, out var filteredState);
            var sharpness =
                explicitIdle
                    ? 10.5f
                    : (canMoveNonForward ? 8.2f : 6.6f);
            var blend = 1f - Mathf.Exp(-sharpness * Mathf.Max(dt, LiveTraceDtFloorSeconds));
            filteredState.MoveSpeed = Mathf.Lerp(filteredState.MoveSpeed, moveSpeed, blend);
            filteredState.Horizontal = Mathf.Lerp(filteredState.Horizontal, horizontal, Mathf.Clamp01(blend * 0.88f));
            filteredState.Vertical = Mathf.Lerp(filteredState.Vertical, vertical, Mathf.Clamp01(blend * 0.92f));

            if (explicitIdle && filteredState.MoveSpeed <= 0.02f)
            {
                filteredState.MoveSpeed = 0f;
            }

            if (Mathf.Abs(filteredState.Horizontal) <= 0.01f)
            {
                filteredState.Horizontal = 0f;
            }

            if (Mathf.Abs(filteredState.Vertical) <= 0.01f)
            {
                filteredState.Vertical = 0f;
            }

            filteredAnimatorStates[bindingKey] = filteredState;
            player.ApplyExternalAnimatorState(
                hasPossession,
                filteredState.MoveSpeed,
                filteredState.Horizontal,
                filteredState.Vertical);
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

            var cameraChanged =
                !string.Equals(lastAppliedCameraPreset, preset, StringComparison.Ordinal) ||
                !string.Equals(GtexMatchController.CameraAdapter.CurrentCameraType, cameraType, StringComparison.Ordinal);
            if (cameraChanged)
            {
                GtexMatchController.CameraAdapter.SwitchCamera(cameraType, forceSnap);
            }

            GtexMatchController.CameraAdapter.FocusToPosition(
                ResolveLiveCameraFocusPosition(state, preset),
                forceSnap || cameraChanged);

            lastAppliedCameraPreset = preset;
        }

        private Vector3 ResolveLiveCameraFocusPosition(MatchResponse state, string preset)
        {
            EnsurePitchSpaceResolved();
            var focusPosition = pitchSpace != null ? pitchSpace.Center : Vector3.zero;
            if (state != null && state.ballPosition != null)
            {
                focusPosition = ConvertIncomingPlaybackPosition(state.ballPosition, state).ClampedWorld;
            }

            if (pitchSpace == null)
            {
                return focusPosition;
            }

            var holderId = ResolveRuntimeBallHolderId(state);
            Vector3? ballCarrierPosition = null;
            if (!string.IsNullOrWhiteSpace(holderId))
            {
                ballCarrierPosition = ResolveRuntimePlayerPositionById(state, holderId, focusPosition);
            }

            focusPosition = ResolveBroadcastFocus(
                focusPosition,
                state != null && state.ballPosition != null
                    ? ResolvePlaybackBallVelocity(state.ballPosition, false)
                    : Vector3.zero,
                ballCarrierPosition,
                CollectNearbyActivePlayerPositions(state, focusPosition));

            var normalizedPreset = (preset ?? string.Empty).Trim().ToLowerInvariant();
            var center = pitchSpace.Center;
            var actionCentroid = ResolveLiveCameraActionCentroid(state, focusPosition);
            var holderSide = ResolvePlayerTeamSideToken(state, holderId);
            var attackDirection = ResolveAttackDirection(holderSide);
            var activeIntentTargetId =
                Time.unscaledTime < liveBallIntentExpiresAt
                    ? (liveBallIntentTargetPlayerId ?? string.Empty).Trim()
                    : string.Empty;
            var activeIntentSourceId =
                Time.unscaledTime < liveBallIntentExpiresAt
                    ? (liveBallIntentSourcePlayerId ?? string.Empty).Trim()
                    : string.Empty;
            var corridorFocus = focusPosition;
            if (!string.IsNullOrWhiteSpace(holderId))
            {
                corridorFocus = ResolveRuntimePlayerPositionById(state, holderId, corridorFocus);
            }
            else if (!string.IsNullOrWhiteSpace(activeIntentSourceId))
            {
                corridorFocus = ResolveRuntimePlayerPositionById(state, activeIntentSourceId, corridorFocus);
            }

            if (!string.IsNullOrWhiteSpace(activeIntentTargetId))
            {
                var intentTargetPosition = ResolveRuntimePlayerPositionById(state, activeIntentTargetId, corridorFocus);
                corridorFocus = Vector3.Lerp(corridorFocus, intentTargetPosition, 0.64f);
                actionCentroid = Vector3.Lerp(actionCentroid, intentTargetPosition, 0.24f);
            }

            if (syntheticBallTransit.Active)
            {
                var transitMidpoint = Vector3.Lerp(syntheticBallTransit.Start, syntheticBallTransit.End, 0.5f);
                corridorFocus = Vector3.Lerp(corridorFocus, transitMidpoint, 0.72f);
                actionCentroid = Vector3.Lerp(actionCentroid, transitMidpoint, 0.36f);
            }

            var actionBlend =
                string.Equals(normalizedPreset, "box_zoom", StringComparison.Ordinal)
                    ? 0.34f
                    : string.Equals(normalizedPreset, "attack_push", StringComparison.Ordinal)
                        ? 0.28f
                        : 0.22f;
            var laneBlend =
                string.Equals(normalizedPreset, "box_zoom", StringComparison.Ordinal)
                    ? 0.78f
                    : string.Equals(normalizedPreset, "attack_push", StringComparison.Ordinal)
                        ? 0.68f
                        : 0.58f;
            var actionZBlend =
                string.Equals(normalizedPreset, "box_zoom", StringComparison.Ordinal)
                    ? 0.34f
                    : string.Equals(normalizedPreset, "attack_push", StringComparison.Ordinal)
                        ? 0.28f
                        : 0.22f;
            var pullBackFromGoal =
                string.Equals(normalizedPreset, "box_zoom", StringComparison.Ordinal)
                    ? 0.92f
                    : string.Equals(normalizedPreset, "attack_push", StringComparison.Ordinal)
                        ? 0.68f
                        : 0.42f;
            focusPosition = new Vector3(
                Mathf.Lerp(corridorFocus.x, actionCentroid.x, actionBlend) - attackDirection.x * pullBackFromGoal,
                0f,
                Mathf.Lerp(
                    Mathf.Lerp(center.z, corridorFocus.z, laneBlend),
                    actionCentroid.z,
                    actionZBlend));
            if (string.Equals(normalizedPreset, "box_zoom", StringComparison.Ordinal))
            {
                focusPosition.x = Mathf.Lerp(focusPosition.x, corridorFocus.x, 0.52f);
                focusPosition.z = Mathf.Lerp(focusPosition.z, corridorFocus.z, 0.22f);
            }
            else if (string.Equals(normalizedPreset, "attack_push", StringComparison.Ordinal))
            {
                focusPosition.x = Mathf.Lerp(focusPosition.x, corridorFocus.x, 0.46f);
                focusPosition.z = Mathf.Lerp(focusPosition.z, corridorFocus.z, 0.18f);
            }
            else
            {
                focusPosition.z = Mathf.Lerp(focusPosition.z, corridorFocus.z, 0.26f);
            }

            var safeInsetX =
                string.Equals(normalizedPreset, "box_zoom", StringComparison.Ordinal)
                    ? Mathf.Clamp(pitchSpace.Length * 0.084f, 8.4f, 10.5f)
                    : string.Equals(normalizedPreset, "attack_push", StringComparison.Ordinal)
                        ? Mathf.Clamp(pitchSpace.Length * 0.096f, 9.2f, 11.8f)
                        : Mathf.Clamp(pitchSpace.Length * 0.108f, 10.4f, 13.6f);
            var safeInsetZ =
                string.Equals(normalizedPreset, "box_zoom", StringComparison.Ordinal)
                    ? Mathf.Clamp(pitchSpace.Width * 0.12f, 6.2f, 8.2f)
                    : string.Equals(normalizedPreset, "attack_push", StringComparison.Ordinal)
                        ? Mathf.Clamp(pitchSpace.Width * 0.136f, 6.8f, 8.8f)
                        : Mathf.Clamp(pitchSpace.Width * 0.152f, 7.6f, 9.8f);
            focusPosition.x = Mathf.Clamp(
                focusPosition.x,
                pitchSpace.MinX + safeInsetX,
                pitchSpace.MaxX - safeInsetX);
            focusPosition.z = Mathf.Clamp(
                focusPosition.z,
                pitchSpace.MinZ + safeInsetZ,
                pitchSpace.MaxZ - safeInsetZ);
            focusPosition.y = 0f;
            lastLivePlayFocusCentroid = actionCentroid;
            if (pitchZones != null)
            {
                var safeFocusPosition = pitchZones.GetSafeCameraFocusPoint(focusPosition);
                safeFocusPosition.y = pitchSpace.GrassY;
                if ((safeFocusPosition - focusPosition).sqrMagnitude > 0.04f)
                {
                    ReportRuntimeValidation(
                        "camera_target_clamped",
                        "preset=" + normalizedPreset +
                        " target=" + FormatPlaybackVector(focusPosition) +
                        " safe=" + FormatPlaybackVector(safeFocusPosition),
                        2f);
                }

                lastLiveCameraTarget = safeFocusPosition;
                return safeFocusPosition;
            }

            lastLiveCameraTarget = focusPosition;
            return focusPosition;
        }

        private Vector3 ResolveLiveCameraActionCentroid(MatchResponse state, Vector3 fallbackFocus)
        {
            if (state == null || state.players == null)
            {
                return fallbackFocus;
            }

            fallbackFocus.y = 0f;
            var weightedPosition = fallbackFocus * 2.5f;
            var totalWeight = 2.5f;
            var holderId = ResolveRuntimeBallHolderId(state);
            var activeIntentTargetId =
                Time.unscaledTime < liveBallIntentExpiresAt
                    ? (liveBallIntentTargetPlayerId ?? string.Empty).Trim()
                    : string.Empty;
            var activeIntentSourceId =
                Time.unscaledTime < liveBallIntentExpiresAt
                    ? (liveBallIntentSourcePlayerId ?? string.Empty).Trim()
                    : string.Empty;
            const float influenceRadius = 24f;

            var livePlayers = state.players;
            for (var index = 0; index < livePlayers.Length; index += 1)
            {
                var livePlayer = livePlayers[index];
                if (livePlayer == null || livePlayer.isBall || !livePlayer.active)
                {
                    continue;
                }

                var position = ResolveRuntimeFieldPosition(livePlayer, state, fallbackFocus);
                position.y = 0f;
                var distance = Vector3.Distance(position, fallbackFocus);
                if (distance > influenceRadius)
                {
                    continue;
                }

                var weight = 1f - Mathf.Clamp01(distance / influenceRadius);
                if (livePlayer.hasPossession ||
                    (!string.IsNullOrWhiteSpace(holderId) &&
                     string.Equals((livePlayer.playerId ?? string.Empty).Trim(), holderId, StringComparison.Ordinal)))
                {
                    weight += 1.25f;
                }

                var playerId = (livePlayer.playerId ?? string.Empty).Trim();
                if (!string.IsNullOrWhiteSpace(activeIntentTargetId) &&
                    string.Equals(playerId, activeIntentTargetId, StringComparison.Ordinal))
                {
                    weight += 0.95f;
                }

                if (!string.IsNullOrWhiteSpace(activeIntentSourceId) &&
                    string.Equals(playerId, activeIntentSourceId, StringComparison.Ordinal))
                {
                    weight += 0.45f;
                }

                weightedPosition += position * weight;
                totalWeight += weight;
            }

            if (totalWeight <= 0.001f)
            {
                return fallbackFocus;
            }

            var centroid = weightedPosition / totalWeight;
            centroid.y = 0f;
            return centroid;
        }

        private List<Vector3> CollectNearbyActivePlayerPositions(MatchResponse state, Vector3 ballPosition)
        {
            var nearbyPlayers = new List<Vector3>();
            if (state == null || state.players == null)
            {
                return nearbyPlayers;
            }

            var livePlayers = state.players;
            for (var index = 0; index < livePlayers.Length; index += 1)
            {
                var livePlayer = livePlayers[index];
                if (livePlayer == null || livePlayer.isBall || !livePlayer.active || ResolveLiveRoleBucket(livePlayer) == 0)
                {
                    continue;
                }

                var position = ResolveRuntimeFieldPosition(livePlayer, state, ballPosition);
                if ((position - ballPosition).sqrMagnitude <= 32f * 32f)
                {
                    nearbyPlayers.Add(position);
                }
            }

            return nearbyPlayers;
        }

        private Vector3 ResolveBroadcastFocus(
            Vector3 ballPosition,
            Vector3 ballVelocity,
            Vector3? ballCarrierPosition,
            IReadOnlyList<Vector3> nearbyActivePlayers)
        {
            var focus = ballPosition;
            if (ballCarrierPosition.HasValue)
            {
                focus = Vector3.Lerp(focus, ballCarrierPosition.Value, 0.72f);
            }

            if (nearbyActivePlayers != null && nearbyActivePlayers.Count > 0)
            {
                var centroid = Vector3.zero;
                var totalWeight = 0f;
                for (var index = 0; index < nearbyActivePlayers.Count; index += 1)
                {
                    var position = nearbyActivePlayers[index];
                    var distance = Vector3.Distance(position, ballPosition);
                    if (distance > 35f)
                    {
                        continue;
                    }

                    var weight = 1f - Mathf.Clamp01(distance / 35f);
                    centroid += position * Mathf.Max(0.12f, weight);
                    totalWeight += Mathf.Max(0.12f, weight);
                }

                if (totalWeight > 0.001f)
                {
                    centroid /= totalWeight;
                    focus = Vector3.Lerp(focus, centroid, 0.34f);
                }
            }

            if (Time.unscaledTime < liveBallIntentExpiresAt &&
                !string.IsNullOrWhiteSpace(liveBallIntentTargetPlayerId))
            {
                var receiverPosition = ResolveRuntimePlayerPositionById(currentState, liveBallIntentTargetPlayerId, liveBallIntentTarget);
                focus = Vector3.Lerp(focus, receiverPosition, syntheticBallTransit.Active ? 0.42f : 0.26f);
            }

            if (syntheticBallTransit.Active)
            {
                focus = Vector3.Lerp(focus, Vector3.Lerp(syntheticBallTransit.Start, syntheticBallTransit.End, 0.5f), 0.48f);
            }

            var holderId = ResolveRuntimeBallHolderId(currentState);
            var holderSide = ResolvePlayerTeamSideToken(currentState, holderId);
            if (!string.IsNullOrWhiteSpace(holderSide) &&
                pitchZones != null &&
                IsNearTeamBox(ballPosition, ResolveOpposingPitchTeamSideIndex(holderSide)))
            {
                var goalSide = ResolveOpposingPitchTeamSideIndex(holderSide);
                var goalCenter = pitchZones.GetGoalCenter(goalSide);
                var boxCenter = pitchZones.GetPenaltyBoxBounds(goalSide).center;
                focus = Vector3.Lerp(focus, Vector3.Lerp(boxCenter, goalCenter, 0.35f), 0.32f);
            }

            var lookAhead = syntheticBallTransit.Active
                ? syntheticBallTransit.End - ballPosition
                : new Vector3(ballVelocity.x, 0f, ballVelocity.z);
            if (lookAhead.sqrMagnitude <= 0.0001f &&
                Time.unscaledTime < liveBallIntentExpiresAt)
            {
                lookAhead = liveBallIntentTarget - ballPosition;
            }

            lookAhead.y = 0f;
            lookAhead = Vector3.ClampMagnitude(lookAhead, 8f);
            focus += lookAhead * 0.18f;
            var safeFocus = pitchZones != null ? pitchZones.GetSafeCameraFocusPoint(focus) : focus;
            if ((safeFocus - focus).sqrMagnitude > 0.1f)
            {
                _cameraClampCorrections += 1;
            }

            _lastBroadcastFocus = Vector3.SmoothDamp(
                _lastBroadcastFocus == Vector3.zero ? safeFocus : _lastBroadcastFocus,
                safeFocus,
                ref _broadcastFocusVelocity,
                0.12f);
            return _lastBroadcastFocus;
        }

        private static string ResolveCameraTypeForPreset(string preset)
        {
            switch ((preset ?? string.Empty).Trim().ToLowerInvariant())
            {
                case "attack_push":
                    return "Broadcast";
                case "goal_celebration":
                    return "Tele";
                case "box_zoom":
                    return "Broadcast";
                case "assistant_flag":
                    return "Offside";
                case "wide_reset":
                    return "Broadcast";
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
                if (TryGetBoundPlayerByPlayerId(ballPosition.playerId, out var holder) && holder != null)
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

        private float ResolveSnapDistance()
        {
            return config != null ? Mathf.Max(0.5f, config.teleportDistance) : LivePlayerSnapDistance;
        }

        private float ResolveDynamicSnapDistance(bool suppressBoundaryMotion)
        {
            var snapDistance = ResolveSnapDistance();
            return suppressBoundaryMotion ? snapDistance * 1.65f : snapDistance;
        }

        private float ResolveHardSnapDistance(bool suppressBoundaryMotion)
        {
            EnsurePitchSpaceResolved();
            var baseDistance = ResolveDynamicSnapDistance(suppressBoundaryMotion);
            var fieldBound = pitchSpace != null
                ? Mathf.Clamp(pitchSpace.Length * 0.14f, 8f, 14f)
                : 10f;
            var snapMultiplier = suppressBoundaryMotion ? 3.8f : 3.1f;
            return Mathf.Max(fieldBound, baseDistance * snapMultiplier);
        }

        private float ResolveLivePredictionSeconds()
        {
            var maxPrediction = config != null
                ? Mathf.Max(0f, config.stalePredictionSeconds)
                : LiveStatePredictionMaxSeconds;

            if (ShouldSuppressBoundaryMotion(currentState))
            {
                maxPrediction *= 0.15f;
            }

            return currentState == null
                ? 0f
                : Mathf.Clamp(Time.unscaledTime - stateReceivedAt, 0f, maxPrediction);
        }

        private Vector3 FilterLivePlayerTarget(PlayerPosition livePlayer, Vector3 targetPosition, float dt, bool suppressBoundaryMotion)
        {
            var bindingKey = ResolveBindingStorageKey(livePlayer);
            if (string.IsNullOrWhiteSpace(bindingKey))
            {
                bindingKey =
                    NormalizeTeamSideToken(livePlayer != null ? livePlayer.teamSide : string.Empty) +
                    ":" +
                    (livePlayer != null ? livePlayer.shirtNumber : 0);
            }

            if (string.IsNullOrWhiteSpace(bindingKey))
            {
                return targetPosition;
            }

            var previousTarget = targetPosition;
            if (!filteredPlayerTargets.TryGetValue(bindingKey, out previousTarget) || dt <= 0f)
            {
                filteredPlayerTargets[bindingKey] = targetPosition;
                return targetPosition;
            }

            var dtForFilter = Mathf.Max(dt, LiveTraceDtFloorSeconds);
            var movementUrgency =
                suppressBoundaryMotion
                    ? 1f
                    : ResolveLiveMovementUrgency(livePlayer, previousTarget);
            var sharpness = suppressBoundaryMotion
                ? LiveSettledTargetFilterSharpness
                : Mathf.Lerp(LiveSettledTargetFilterSharpness * 0.9f, LiveTargetFilterSharpness, movementUrgency);
            var blend = 1f - Mathf.Exp(-sharpness * dtForFilter);
            var filteredTarget = Vector3.Lerp(previousTarget, targetPosition, Mathf.Clamp01(blend));
            filteredTarget = Vector3.MoveTowards(
                previousTarget,
                filteredTarget,
                ResolveDynamicSnapDistance(suppressBoundaryMotion) *
                Mathf.Lerp(0.02f, 0.95f, Mathf.Clamp01(movementUrgency)) *
                Mathf.Lerp(0.48f, 0.95f, Mathf.Clamp01(dtForFilter * 12f)));
            filteredPlayerTargets[bindingKey] = filteredTarget;
            return filteredTarget;
        }

        private Vector3 FilterLiveBallTarget(Vector3 targetPosition, bool resetFilter)
        {
            if (resetFilter || !hasFilteredBallTarget)
            {
                filteredBallTarget = targetPosition;
                hasFilteredBallTarget = true;
                return targetPosition;
            }

            var blend = 1f - Mathf.Exp(-LiveTargetFilterSharpness * Mathf.Max(Time.deltaTime, LiveTraceDtFloorSeconds));
            filteredBallTarget = Vector3.Lerp(filteredBallTarget, targetPosition, Mathf.Clamp01(blend));
            return filteredBallTarget;
        }

        private void ClearPlaybackTargetFilters()
        {
            filteredPlayerTargets.Clear();
            livePlayerIntentTargets.Clear();
            filteredAnimatorStates.Clear();
            hasFilteredBallTarget = false;
            filteredBallTarget = Vector3.zero;
        }

        private Vector3 ResolvePersistentBehaviorTarget(
            PlayerPosition livePlayer,
            Vector3 anchorPosition,
            Vector3 desiredTarget,
            string mode,
            string subjectId,
            float persistence,
            float maxAnchorDrift)
        {
            anchorPosition = ClampToFieldBounds(anchorPosition, false);
            desiredTarget = ClampToFieldBounds(desiredTarget, false);
            subjectId = (subjectId ?? string.Empty).Trim();
            persistence = Mathf.Clamp01(persistence);

            var anchorOffset = desiredTarget - anchorPosition;
            anchorOffset.y = 0f;
            if (anchorOffset.sqrMagnitude > 0.0001f)
            {
                desiredTarget = anchorPosition + Vector3.ClampMagnitude(anchorOffset, Mathf.Max(1.25f, maxAnchorDrift));
                desiredTarget = ClampToFieldBounds(desiredTarget, false);
            }

            var bindingKey = ResolveBindingStorageKey(livePlayer);
            if (string.IsNullOrWhiteSpace(bindingKey))
            {
                return desiredTarget;
            }

            var now = Time.unscaledTime;
            if (!livePlayerIntentTargets.TryGetValue(bindingKey, out var state) || now >= state.ExpiresAt)
            {
                livePlayerIntentTargets[bindingKey] = new LivePlayerIntentState
                {
                    Target = desiredTarget,
                    Mode = mode ?? string.Empty,
                    SubjectId = subjectId,
                    UpdatedAt = now,
                    ExpiresAt = now + Mathf.Lerp(LivePlayerIntentMinLifetimeSeconds, LivePlayerIntentMaxLifetimeSeconds, persistence),
                };

                return desiredTarget;
            }

            var dt = Mathf.Max(now - state.UpdatedAt, Mathf.Max(Time.deltaTime, LiveTraceDtFloorSeconds));
            var sameMode = string.Equals(state.Mode, mode ?? string.Empty, StringComparison.Ordinal);
            var sameSubject = string.Equals(state.SubjectId, subjectId, StringComparison.Ordinal);
            var blendSharpness =
                sameMode && sameSubject
                    ? LivePlayerIntentFilterSharpness
                    : LivePlayerIntentFilterSharpness * 0.5f;
            var blend = 1f - Mathf.Exp(-blendSharpness * dt);
            var nextTarget = Vector3.Lerp(state.Target, desiredTarget, Mathf.Clamp01(blend));

            var roleSpeedCap = ResolveLiveRoleSpeedCap(livePlayer);
            var retargetSpeed =
                (roleSpeedCap + LivePlayerIntentRetargetSpeed) *
                Mathf.Lerp(0.72f, 1.18f, persistence);
            if (!sameMode || !sameSubject)
            {
                retargetSpeed *= 0.78f;
            }

            nextTarget = Vector3.MoveTowards(state.Target, nextTarget, retargetSpeed * dt);
            var nextOffset = nextTarget - anchorPosition;
            nextOffset.y = 0f;
            if (nextOffset.sqrMagnitude > 0.0001f)
            {
                nextTarget = anchorPosition + Vector3.ClampMagnitude(nextOffset, Mathf.Max(1.25f, maxAnchorDrift));
            }

            nextTarget = ClampToFieldBounds(nextTarget, false);
            state.Target = nextTarget;
            state.Mode = mode ?? string.Empty;
            state.SubjectId = subjectId;
            state.UpdatedAt = now;
            state.ExpiresAt = now + Mathf.Lerp(LivePlayerIntentMinLifetimeSeconds, LivePlayerIntentMaxLifetimeSeconds, persistence);
            livePlayerIntentTargets[bindingKey] = state;
            return nextTarget;
        }

        private Vector3 ResolveOpponentPressure(PlayerPosition livePlayer, Vector3 currentPosition)
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
            var pressure = Vector3.zero;
            var contributors = 0;
            var livePlayers = currentState.players;
            for (var index = 0; index < livePlayers.Length; index += 1)
            {
                var opponent = livePlayers[index];
                if (opponent == null ||
                    opponent.isBall ||
                    !opponent.active ||
                    string.Equals(NormalizeTeamSideToken(opponent.teamSide), playerTeamSide, StringComparison.Ordinal))
                {
                    continue;
                }

                var opponentPosition = ResolveRuntimeFieldPosition(opponent, currentState, Vector3.zero);
                var separation = currentPosition - opponentPosition;
                separation.y = 0f;
                var distance = separation.magnitude;
                if (distance <= 0.001f || distance >= LivePlayerIntentOpponentPressureRadius)
                {
                    continue;
                }

                var weight = 1f - Mathf.Clamp01(distance / LivePlayerIntentOpponentPressureRadius);
                pressure += separation.normalized * weight * weight;
                contributors += 1;
            }

            if (contributors == 0)
            {
                return Vector3.zero;
            }

            pressure /= contributors;
            pressure.y = 0f;
            return Vector3.ClampMagnitude(pressure, 1.45f);
        }

        private Vector3 ResolvePlaybackBallVelocity(PlayerPosition livePosition, bool suppressBoundaryMotion)
        {
            if (livePosition == null)
            {
                return Vector3.zero;
            }

            if (suppressBoundaryMotion)
            {
                return Vector3.zero;
            }

            var ballVelocity = ResolveLiveFieldVelocity(livePosition);
            var planarVelocity = new Vector3(ballVelocity.x, 0f, ballVelocity.z);
            var eventType = ResolveActiveEventTypeToken();
            var maxPlanarSpeed =
                eventType.Contains("goal") ||
                eventType.Contains("shot") ||
                eventType.Contains("chance") ||
                eventType.Contains("save") ||
                eventType.Contains("miss")
                    ? LiveBallPlaybackMaxShotSpeed
                    : LiveBallPlaybackMaxPassSpeed;
            planarVelocity = Vector3.ClampMagnitude(planarVelocity, maxPlanarSpeed);
            ballVelocity.x = planarVelocity.x;
            ballVelocity.z = planarVelocity.z;
            ballVelocity.y = Mathf.Clamp(ballVelocity.y, -2.25f, 4.5f);
            return ballVelocity;
        }

        private void TryStartSyntheticBallTransit(MatchResponse previousState, MatchResponse nextState, bool forceSnap)
        {
            if (forceSnap || nextState == null || IsTerminalLiveState(nextState) || ShouldSuppressBoundaryMotion(nextState))
            {
                ClearSyntheticBallTransit();
                return;
            }

            if (previousState == null || previousState.ballPosition == null || nextState.ballPosition == null)
            {
                return;
            }

            var activeEvent = nextState.ResolveActiveEvent();
            var eventType = NormalizeActiveEventTypeToken(nextState, activeEvent);
            var isShotTransit = IsShotLikeEventType(eventType);
            var isCrossTransit = eventType.Contains("cross") || eventType.Contains("corner");
            var isPassTransit = IsPassLikeEventType(eventType);
            var explicitTransit = isShotTransit || isCrossTransit || isPassTransit;
            var previousHolderId = (previousState.ballPosition.playerId ?? string.Empty).Trim();
            var nextHolderId = (nextState.ballPosition.playerId ?? string.Empty).Trim();
            var sourcePlayerId = ResolvePreferredLiveBallSourcePlayerId(activeEvent, previousHolderId, nextHolderId);
            var targetPlayerId = ResolvePreferredLiveBallTargetPlayerId(activeEvent, nextHolderId, sourcePlayerId);
            var explicitReceiverTransit =
                isPassTransit &&
                !string.IsNullOrWhiteSpace(sourcePlayerId) &&
                !string.IsNullOrWhiteSpace(targetPlayerId) &&
                !string.Equals(sourcePlayerId, targetPlayerId, StringComparison.Ordinal);
            var holderChanged = !string.Equals(previousHolderId, nextHolderId, StringComparison.Ordinal);
            if (!explicitReceiverTransit &&
                (string.IsNullOrWhiteSpace(previousHolderId) ||
                 string.IsNullOrWhiteSpace(nextHolderId) ||
                 !holderChanged))
            {
                return;
            }

            var liveVelocity = ResolvePlaybackBallVelocity(nextState.ballPosition, false);
            liveVelocity.y = 0f;
            var ballSpeed = liveVelocity.magnitude;
            var minimumTransitSpeed =
                explicitReceiverTransit
                    ? LiveBallPassSpeedUnitsPerSecond * 0.72f
                    : LiveBallPassSpeedUnitsPerSecond;
            if (ballSpeed < minimumTransitSpeed)
            {
                return;
            }

            var start = ResolveRuntimePlayerPositionById(previousState, sourcePlayerId, Vector3.zero);
            if (start.sqrMagnitude <= 0.0001f)
            {
                start = ResolveRuntimePlayerPositionById(nextState, sourcePlayerId, Vector3.zero);
            }

            var end = start;
            if (TryResolveLivePlayerByPlayerId(nextState, targetPlayerId, out var nextHolderLive) &&
                GtexMatchController.MatchManagerAdapter.IsAvailable)
            {
                end = ResolveTransitTargetPosition(
                    nextState,
                    targetPlayerId,
                    ConvertIncomingPlaybackPosition(nextHolderLive, nextState).ClampedWorld,
                    LiveTransitReceiverLeadSeconds);
            }
            else
            {
                end = ResolveRuntimePlayerPositionById(nextState, targetPlayerId, start);
            }

            start = ResolveBallReleaseOrigin(nextState, sourcePlayerId, start, end - start);
            end = ClampToFieldBounds(new Vector3(end.x, pitchSpace != null ? pitchSpace.GrassY + GtexPlaybackSanitizer.DefaultBallHeight : 0.1f, end.z), true);
            var distance = Vector3.Distance(start, end);
            if (distance <= 0.01f)
            {
                return;
            }

            var previousHolderSide = ResolvePlayerTeamSideToken(previousState, sourcePlayerId);
            if (string.IsNullOrWhiteSpace(previousHolderSide))
            {
                previousHolderSide = ResolvePlayerTeamSideToken(nextState, sourcePlayerId);
            }

            var nextHolderSide = ResolvePlayerTeamSideToken(nextState, targetPlayerId);
            var sameTeamTransition =
                !string.IsNullOrWhiteSpace(previousHolderSide) &&
                string.Equals(previousHolderSide, nextHolderSide, StringComparison.Ordinal);
            if (!explicitTransit)
            {
                if (!sameTeamTransition)
                {
                    return;
                }

                if (distance < 2.2f || ballSpeed < LiveBallPassSpeedUnitsPerSecond * 1.8f)
                {
                    return;
                }
            }

            if ((sameTeamTransition && distance < (explicitReceiverTransit ? 0.95f : 1.35f)) ||
                (!sameTeamTransition && distance < 2.75f))
            {
                return;
            }

            end = ResolveTransitTargetPosition(
                nextState,
                targetPlayerId,
                end,
                isShotTransit ? LiveTransitReceiverLeadSeconds * 0.45f : LiveTransitReceiverLeadSeconds);
            distance = Vector3.Distance(start, end);

            var referenceSpeed = Mathf.Clamp(
                ballSpeed,
                isShotTransit ? 5.5f : 4f,
                isShotTransit ? LiveBallPlaybackMaxShotSpeed : LiveBallPlaybackMaxPassSpeed);

            syntheticBallTransit = new SyntheticBallTransit
            {
                Active = true,
                Start = start,
                End = end,
                StartedAt = Time.unscaledTime,
                Duration = Mathf.Clamp(
                    distance / Mathf.Max(referenceSpeed * (isShotTransit ? 0.72f : explicitReceiverTransit ? 0.5f : 0.58f), 0.001f),
                    isShotTransit ? 0.4f : explicitReceiverTransit ? 0.38f : 0.34f,
                    isShotTransit ? 1.05f : 0.92f),
                ArcHeight = isShotTransit ? 1.25f : (isCrossTransit ? 0.82f : explicitReceiverTransit ? 0.24f : 0.36f),
                IsShot = isShotTransit,
                MaxPlaybackSpeed = isShotTransit ? LiveBallPlaybackMaxShotSpeed : LiveBallPlaybackMaxPassSpeed,
                TargetPlayerId = targetPlayerId,
            };
        }

        private bool TryDriveSyntheticBallTransit()
        {
            if (!syntheticBallTransit.Active)
            {
                return false;
            }

            var elapsed = Mathf.Max(0f, Time.unscaledTime - syntheticBallTransit.StartedAt);
            var duration = Mathf.Max(0.01f, syntheticBallTransit.Duration);
            if (!syntheticBallTransit.IsShot &&
                !string.IsNullOrWhiteSpace(syntheticBallTransit.TargetPlayerId))
            {
                var updatedEnd = ResolveTransitTargetPosition(
                    currentState,
                    syntheticBallTransit.TargetPlayerId,
                    syntheticBallTransit.End,
                    Mathf.Min(LiveTransitReceiverLeadSeconds, Mathf.Max(duration - elapsed, 0f)));
                syntheticBallTransit.End = Vector3.Lerp(syntheticBallTransit.End, updatedEnd, 0.72f);
            }

            var t = Mathf.Clamp01(elapsed / duration);
            var position = Vector3.Lerp(syntheticBallTransit.Start, syntheticBallTransit.End, t);
            position.y += 4f * syntheticBallTransit.ArcHeight * t * (1f - t);
            position = ClampToFieldBounds(position, true);

            var nextT = Mathf.Clamp01((elapsed + Mathf.Max(Time.deltaTime, 0.016f)) / duration);
            var nextPosition = Vector3.Lerp(syntheticBallTransit.Start, syntheticBallTransit.End, nextT);
            nextPosition.y += 4f * syntheticBallTransit.ArcHeight * nextT * (1f - nextT);
            nextPosition = ClampToFieldBounds(nextPosition, true);
            var velocity = (nextPosition - position) / Mathf.Max(Time.deltaTime, LiveTraceDtFloorSeconds);
            var planarVelocity = new Vector3(velocity.x, 0f, velocity.z);
            planarVelocity = Vector3.ClampMagnitude(
                planarVelocity,
                Mathf.Max(3.5f, syntheticBallTransit.MaxPlaybackSpeed));
            velocity.x = planarVelocity.x;
            velocity.z = planarVelocity.z;
            velocity.y = Mathf.Clamp(velocity.y, -2.5f, syntheticBallTransit.IsShot ? 5.5f : 3.75f);

            runtimeTraceBallSpeed = new Vector3(velocity.x, 0f, velocity.z).magnitude;
            GtexMatchController.BallAdapter.ApplyExternalState(position, velocity, null);

            if (t >= 1f)
            {
                ClearSyntheticBallTransit();
            }

            return true;
        }

        private void ClearSyntheticBallTransit()
        {
            syntheticBallTransit = default;
        }

        private Vector3 ResolveTransitTargetPosition(MatchResponse state, string playerId, Vector3 fallbackEnd, float leadSeconds)
        {
            var resolvedEnd = ResolveRuntimePlayerPositionById(state, playerId, fallbackEnd);
            if (TryResolveLivePlayerByPlayerId(state, playerId, out var livePlayer))
            {
                var receiverVelocity = ResolveLiveFieldVelocity(livePlayer);
                receiverVelocity.y = 0f;
                resolvedEnd += Vector3.ClampMagnitude(
                    receiverVelocity * Mathf.Max(leadSeconds, 0f),
                    LiveTransitReceiverLeadDistance);
            }

            return ClampToFieldBounds(
                new Vector3(
                    resolvedEnd.x,
                    pitchSpace != null ? pitchSpace.GrassY + GtexPlaybackSanitizer.DefaultBallHeight : 0.1f,
                    resolvedEnd.z),
                true);
        }

        private Vector3 ResolveBallReleaseOrigin(
            MatchResponse state,
            string playerId,
            Vector3 fallbackOrigin,
            Vector3 releaseDirection)
        {
            var resolvedOrigin = fallbackOrigin;
            if (!string.IsNullOrWhiteSpace(playerId))
            {
                resolvedOrigin = ResolveRuntimePlayerPositionById(state, playerId, fallbackOrigin);
            }

            if (TryGetBoundPlayerByPlayerId(playerId, out var boundPlayer) &&
                boundPlayer != null &&
                GtexMatchController.BallAdapter.IsAvailable)
            {
                resolvedOrigin =
                    GtexMatchController.BallAdapter.ResolveExternalReleaseAnchor(
                        boundPlayer,
                        releaseDirection,
                        resolvedOrigin);
            }

            resolvedOrigin.y =
                pitchSpace != null
                    ? pitchSpace.GrassY + GtexPlaybackSanitizer.DefaultBallHeight
                    : Mathf.Max(0.1f, resolvedOrigin.y);
            return ClampToFieldBounds(resolvedOrigin, true);
        }

        private bool CanReleaseKickNow(Transform passer, Vector3 targetPoint, bool specialFlickOrBackheel)
        {
            if (passer == null)
            {
                return false;
            }

            if (specialFlickOrBackheel)
            {
                return true;
            }

            var toTarget = targetPoint - passer.position;
            toTarget.y = 0f;
            if (toTarget.sqrMagnitude < 0.001f)
            {
                return true;
            }

            var forward = passer.forward;
            forward.y = 0f;
            if (forward.sqrMagnitude < 0.001f)
            {
                return false;
            }

            var alignment = Vector3.Dot(forward.normalized, toTarget.normalized);
            return alignment >= passReleaseMinFacingDot;
        }

        private bool TryReleaseKick(
            GtexLegacyPlayerHandle player,
            Vector3 targetPoint,
            bool specialFlickOrBackheel)
        {
            if (player == null || !player.IsValid || player.UnityTransform == null)
            {
                return false;
            }

            if (CanReleaseKickNow(player.UnityTransform, targetPoint, specialFlickOrBackheel))
            {
                return true;
            }

            _badPassReleaseBlocks += 1;
            var toTarget = targetPoint - player.UnityTransform.position;
            toTarget.y = 0f;
            if (toTarget.sqrMagnitude > 0.001f)
            {
                var wanted = Quaternion.LookRotation(toTarget.normalized, Vector3.up);
                player.UnityTransform.rotation = Quaternion.RotateTowards(
                    player.UnityTransform.rotation,
                    wanted,
                    visualTurnDegreesPerSecond * Time.deltaTime);
            }

            if (player.Animator != null)
            {
                player.Animator.SetFloat(PlayerAnimatorVariable.MoveSpeed, 0f);
                player.Animator.SetFloat(PlayerAnimatorVariable.Horizontal, 0f);
                player.Animator.SetFloat(PlayerAnimatorVariable.Vertical, 0f);
            }

            return false;
        }

        private Vector3 ResolvePredictedFieldPosition(PlayerPosition livePosition, float predictionSeconds)
        {
            var targetPosition = ConvertIncomingPlaybackPosition(livePosition, currentState).ClampedWorld;
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

            var livePlayerId = ((livePlayer.playerId ?? string.Empty).Trim());
            var hasActiveBallIntent =
                Time.unscaledTime < liveBallIntentExpiresAt &&
                !string.IsNullOrWhiteSpace(liveBallIntentReason);
            var intentTargetPlayerId =
                hasActiveBallIntent
                    ? (liveBallIntentTargetPlayerId ?? string.Empty).Trim()
                    : string.Empty;
            var currentBallHolderId = ResolveRuntimeBallHolderId(currentState);
            var primaryThreatPlayerId =
                !string.IsNullOrWhiteSpace(intentTargetPlayerId)
                    ? intentTargetPlayerId
                    : currentBallHolderId;
            if (string.IsNullOrWhiteSpace(primaryThreatPlayerId))
            {
                primaryThreatPlayerId = (liveBallIntentSourcePlayerId ?? string.Empty).Trim();
            }

            var isIntentReceiver =
                !string.IsNullOrWhiteSpace(livePlayerId) &&
                !string.IsNullOrWhiteSpace(intentTargetPlayerId) &&
                string.Equals(livePlayerId, intentTargetPlayerId, StringComparison.Ordinal);
            var primaryThreatPosition = ResolveRuntimePlayerPositionById(currentState, primaryThreatPlayerId, chaseAnchor);
            primaryThreatPosition.y = 0f;
            var primaryThreatSide = ResolvePlayerTeamSideToken(currentState, primaryThreatPlayerId);
            var markRank =
                string.IsNullOrWhiteSpace(primaryThreatPlayerId)
                    ? int.MaxValue
                    : ResolveTeamDistanceRank(livePlayer, currentPosition, primaryThreatPosition);
            var opponentPressure = ResolveOpponentPressure(livePlayer, currentPosition);
            var attackEvent =
                eventType.Contains("chance") ||
                eventType.Contains("miss") ||
                eventType.Contains("goal") ||
                eventType.Contains("shot") ||
                eventType.Contains("save");
            var widthRunnerCandidate =
                sameSideBallRank == 2 &&
                roleBucket >= 2 &&
                Mathf.Abs(ResolveBehaviorLaneSign(livePlayer, roleBucket)) >= 0.5f;
            var primarySupportBand = looseBallBehavior ? 1 : 0;
            var engagedWithoutBall =
                isIntentReceiver ||
                sameSideBallRank <= primarySupportBand ||
                (!sameTeamAsPossession && markRank != int.MaxValue && markRank <= 1);
            var supportOptionCandidate =
                sameTeamAsPossession &&
                !looseBallBehavior &&
                sameSideBallRank == 0;
            var runnerCandidate =
                sameTeamAsPossession &&
                !looseBallBehavior &&
                (sameSideBallRank == 1 || widthRunnerCandidate);
            var nearestPresserCandidate =
                !sameTeamAsPossession &&
                markRank != int.MaxValue &&
                markRank == 0;
            var coverDefenderCandidate =
                !sameTeamAsPossession &&
                markRank != int.MaxValue &&
                markRank == 1;
            var markerCandidate =
                !sameTeamAsPossession &&
                sameSideBallRank == 0 &&
                roleBucket <= 2;
            var farSideDriftCandidate =
                !livePlayer.hasPossession &&
                !isIntentReceiver &&
                (sameTeamAsPossession
                    ? sameSideBallRank == 3
                    : markRank != int.MaxValue && markRank > 1 && sameSideBallRank <= 2);
            var withinMovementBudget =
                livePlayer.hasPossession ||
                isIntentReceiver ||
                (looseBallBehavior
                    ? sameSideBallRank <= 1 || nearestPresserCandidate
                    : supportOptionCandidate ||
                      runnerCandidate ||
                      nearestPresserCandidate ||
                      coverDefenderCandidate ||
                      markerCandidate ||
                      (farSideDriftCandidate && roleBucket <= 2));
            var passiveShapePlayer =
                !livePlayer.hasPossession &&
                !withinMovementBudget &&
                !engagedWithoutBall &&
                (looseBallBehavior ? sameSideBallRank >= 2 : sameSideBallRank >= 1);
            var playerTeamSideIndex = ResolvePitchTeamSideIndex(playerTeamSide);
            var opponentTeamSideIndex = ResolveOpposingPitchTeamSideIndex(playerTeamSide);
            var nearAttackingBox =
                sameTeamAsPossession &&
                !string.IsNullOrWhiteSpace(playerTeamSide) &&
                IsNearTeamBox(chaseAnchor, opponentTeamSideIndex);
            var nearDefensiveBox =
                !sameTeamAsPossession &&
                !string.IsNullOrWhiteSpace(playerTeamSide) &&
                IsNearTeamBox(chaseAnchor, playerTeamSideIndex);

            if (nearAttackingBox && !looseBallBehavior)
            {
                withinMovementBudget =
                    livePlayer.hasPossession ||
                    isIntentReceiver ||
                    supportOptionCandidate ||
                    (sameSideBallRank == 1 && roleBucket >= 2) ||
                    widthRunnerCandidate;
                passiveShapePlayer = !withinMovementBudget && !livePlayer.hasPossession;
            }

            if (nearDefensiveBox && !looseBallBehavior)
            {
                withinMovementBudget =
                    livePlayer.hasPossession ||
                    nearestPresserCandidate ||
                    coverDefenderCandidate ||
                    markerCandidate;
                passiveShapePlayer = !withinMovementBudget && !livePlayer.hasPossession;
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
                lateralDirection * Mathf.Sin(roamPhase) * roamDistance * 0.045f +
                attackDirection * Mathf.Cos(roamPhase * 0.67f) * roamDistance * 0.028f;
            var movementInvolvement =
                livePlayer.hasPossession
                    ? 1f
                    : isIntentReceiver
                        ? 1f
                        : looseBallBehavior
                            ? (sameSideBallRank <= 1 ? 0.92f : sameSideBallRank == 2 ? 0.38f : 0.12f)
                            : sameTeamAsPossession
                                ? (sameSideBallRank == 0 ? 0.82f : sameSideBallRank == 1 ? 0.12f : sameSideBallRank == 2 ? 0.04f : 0.01f)
                                : (markRank == 0 ? 0.8f : markRank == 1 ? 0.28f : sameSideBallRank == 0 ? 0.12f : sameSideBallRank == 1 ? 0.05f : 0.015f);
            if (!withinMovementBudget && !livePlayer.hasPossession && !isIntentReceiver)
            {
                movementInvolvement *= looseBallBehavior ? 0.12f : 0.03f;
            }
            if (nearAttackingBox && !livePlayer.hasPossession)
            {
                movementInvolvement *= withinMovementBudget ? 0.78f : 0.04f;
            }
            else if (nearDefensiveBox && !livePlayer.hasPossession)
            {
                movementInvolvement *= withinMovementBudget ? 0.72f : 0.05f;
            }
            roamDistance *= Mathf.Lerp(0.48f, 1f, movementInvolvement);
            widthBias *= Mathf.Lerp(0.28f, 1f, movementInvolvement);
            opponentPressure *= Mathf.Lerp(0.22f, 1f, movementInvolvement);
            teammateRepulsion *= Mathf.Lerp(0.38f, 1f, movementInvolvement);
            microMotion *= Mathf.Lerp(0.08f, 0.58f, movementInvolvement);
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
            if (nearAttackingBox || nearDefensiveBox)
            {
                baseBehaviorWeight *= withinMovementBudget ? 0.84f : 0.48f;
            }

            if (looseBallBehavior)
            {
                baseBehaviorWeight = Mathf.Max(baseBehaviorWeight, 0.58f);
            }

            if (liveBallIntentContested)
            {
                baseBehaviorWeight = Mathf.Max(baseBehaviorWeight, 0.62f);
            }

            baseBehaviorWeight *= Mathf.Lerp(0.42f, 1f, movementInvolvement);

            Vector3 ReturnBehaviorTarget(
                Vector3 desiredTarget,
                float weight,
                string mode,
                string subjectId,
                float persistence,
                float maxAnchorDrift)
            {
                return ResolvePersistentBehaviorTarget(
                    livePlayer,
                    anchorPosition,
                    BlendBehaviorDrivenTarget(anchorPosition, desiredTarget, weight),
                    mode,
                    subjectId,
                    persistence,
                    maxAnchorDrift);
            }

            if (passiveShapePlayer && !looseBallBehavior)
            {
                var holdAdvance =
                    sameTeamAsPossession
                        ? (roleBucket == 3 ? 0.34f : roleBucket == 2 ? 0.16f : 0.04f)
                        : -(roleBucket == 1 ? 0.22f : 0.08f);
                var holdTarget =
                    anchorPosition +
                    attackDirection * holdAdvance +
                    widthBias * 0.22f +
                    teammateRepulsion * 0.22f +
                    microMotion * 0.18f;
                return ReturnBehaviorTarget(
                    holdTarget,
                    sameTeamAsPossession ? LivePlayerShapeHoldWeight : LivePlayerShapeHoldDefensiveWeight,
                    sameTeamAsPossession ? "hold-shape" : "defensive-hold",
                    currentBallHolderId,
                    0.24f,
                    roamDistance * 0.55f + 0.95f);
            }

            if (livePlayer.hasPossession)
            {
                var dribbleDirection = attackDirection;
                if (!string.IsNullOrWhiteSpace(intentTargetPlayerId))
                {
                    var intendedReceiverPosition = ResolveRuntimePlayerPositionById(currentState, intentTargetPlayerId, anchorPosition + attackDirection);
                    var toReceiver = intendedReceiverPosition - currentPosition;
                    toReceiver.y = 0f;
                    if (toReceiver.sqrMagnitude > 0.0001f)
                    {
                        dribbleDirection = Vector3.Lerp(dribbleDirection, toReceiver.normalized, 0.32f).normalized;
                    }
                }

                var dribbleTarget =
                    anchorPosition +
                    dribbleDirection * roamDistance * 1.05f +
                    widthBias * 0.32f +
                    opponentPressure * 0.88f +
                    teammateRepulsion * 0.22f +
                    microMotion * 0.18f;
                return ReturnBehaviorTarget(
                    dribbleTarget,
                    Mathf.Max(baseBehaviorWeight + 0.12f, 0.92f),
                    "carry",
                    intentTargetPlayerId,
                    1f,
                    roamDistance * 1.25f + 2.2f);
            }

            if (roleBucket == 0)
            {
                var keeperOffset =
                    sameTeamAsPossession
                        ? attackDirection * 0.35f + widthBias * 0.1f
                        : toBallFromAnchor.normalized * Mathf.Min(0.9f, toBallFromAnchor.magnitude * 0.08f) + widthBias * 0.08f;
                return ReturnBehaviorTarget(
                    anchorPosition + keeperOffset,
                    Mathf.Max(baseBehaviorWeight, 0.7f),
                    "keeper",
                    currentBallHolderId,
                    0.7f,
                    1.35f);
            }

            if (!looseBallBehavior && sameTeamAsPossession && isIntentReceiver)
            {
                var receiveLead =
                    attackDirection * (roleBucket == 3 ? 1.1f : roleBucket == 2 ? 0.75f : 0.42f) +
                    widthBias * 0.4f +
                    opponentPressure * 0.72f +
                    teammateRepulsion * 0.56f +
                    microMotion * 0.22f;
                var receiveTarget = Vector3.Lerp(anchorPosition, liveBallIntentTarget, 0.8f) + receiveLead;
                return ReturnBehaviorTarget(
                    receiveTarget,
                    Mathf.Max(baseBehaviorWeight + 0.18f, 0.88f),
                    "receive",
                    liveBallIntentSourcePlayerId,
                    0.96f,
                    roamDistance + 3.15f);
            }

            if (!looseBallBehavior &&
                !sameTeamAsPossession &&
                !string.IsNullOrWhiteSpace(primaryThreatPlayerId) &&
                markRank != int.MaxValue &&
                markRank <= 1)
            {
                var threatAttackDirection = ResolveAttackDirection(primaryThreatSide);
                var markDistance = markRank == 0 ? (roleBucket == 1 ? 1.15f : 1.45f) : 1.95f;
                var markAnchor =
                    primaryThreatPosition -
                    threatAttackDirection * markDistance +
                    widthBias * (markRank == 0 ? 0.18f : 0.42f) +
                    teammateRepulsion * 0.68f +
                    microMotion * 0.3f;
                return ReturnBehaviorTarget(
                    markAnchor,
                    Mathf.Max(baseBehaviorWeight + (markRank == 0 ? 0.12f : 0.06f), markRank == 0 ? 0.72f : 0.6f),
                    markRank == 0 ? "press-mark" : "cover-mark",
                    primaryThreatPlayerId,
                    markRank == 0 ? 0.9f : 0.78f,
                    roamDistance + (markRank == 0 ? 2.55f : 2.2f));
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
                    return ReturnBehaviorTarget(
                        chaseTarget,
                        Mathf.Max(baseBehaviorWeight + 0.18f, 0.82f),
                        "loose-chase",
                        primaryThreatPlayerId,
                        0.88f,
                        roamDistance + 2.65f);
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
                        return ReturnBehaviorTarget(
                            supportTarget,
                            Mathf.Max(baseBehaviorWeight + 0.12f, 0.68f),
                            "loose-support",
                            primaryThreatPlayerId,
                            0.72f,
                            roamDistance + 2.2f);
                    }

                    var interceptTarget =
                        Vector3.Lerp(recoveryTarget, chaseAnchor, 0.56f) -
                        attackDirection * 0.2f +
                        looseBallTravel * Mathf.Min(ballVelocity.magnitude * 0.3f, 0.55f) +
                        widthBias * 0.3f +
                        teammateRepulsion * 0.65f +
                        microMotion;
                    return ReturnBehaviorTarget(
                        interceptTarget,
                        Mathf.Max(baseBehaviorWeight + 0.08f, 0.64f),
                        "loose-intercept",
                        primaryThreatPlayerId,
                        0.7f,
                        roamDistance + 1.95f);
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
                        return ReturnBehaviorTarget(
                            thirdManTarget,
                            Mathf.Max(baseBehaviorWeight + 0.05f, 0.58f),
                            "third-man",
                            primaryThreatPlayerId,
                            0.6f,
                            roamDistance + 1.8f);
                    }

                    var collapseTarget =
                        Vector3.Lerp(anchorPosition, chaseAnchor, 0.38f) -
                        attackDirection * (roleBucket == 1 ? 0.3f : 0.15f) +
                        widthBias * 0.18f +
                        teammateRepulsion * 0.45f +
                        microMotion;
                    return ReturnBehaviorTarget(
                        collapseTarget,
                        Mathf.Max(baseBehaviorWeight, 0.56f),
                        "collapse",
                        primaryThreatPlayerId,
                        0.56f,
                        roamDistance + 1.55f);
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
                    return ReturnBehaviorTarget(
                        receivingShapeTarget,
                        Mathf.Max(baseBehaviorWeight, 0.46f),
                        "receive-shape",
                        primaryThreatPlayerId,
                        0.48f,
                        roamDistance + 1.45f);
                }

                var contestCompression = liveBallIntentContested ? 0.18f : 0f;
                var looseShapeTarget =
                    anchorPosition +
                    toChaseFromAnchor.normalized * Mathf.Min(toChaseFromAnchor.magnitude * (0.26f + contestCompression), 1.15f) -
                    attackDirection * (roleBucket == 1 ? 0.25f : 0.1f) +
                    widthBias * 0.12f +
                    teammateRepulsion * 0.45f +
                    microMotion;
                return ReturnBehaviorTarget(
                    looseShapeTarget,
                    Mathf.Max(baseBehaviorWeight, 0.44f),
                    "loose-shape",
                    primaryThreatPlayerId,
                    0.42f,
                    roamDistance + 1.25f);
            }

            if (sameTeamAsPossession || stateName.Contains("attack") || stateName.Contains("move"))
            {
                if (sameSideBallRank == 0)
                {
                    var receiveTarget =
                        recoveryTarget +
                        toBallFromCurrent.normalized * Mathf.Min(toBallFromCurrent.magnitude * 0.62f, 1.55f + roamDistance * 0.3f) +
                        attackDirection * (roleBucket == 3 ? 1.2f : roleBucket == 2 ? 0.8f : 0.45f) +
                        widthBias * 0.6f +
                        teammateRepulsion * 0.72f +
                        microMotion * 0.24f;
                    return ReturnBehaviorTarget(
                        receiveTarget,
                        Mathf.Max(baseBehaviorWeight + 0.08f, 0.7f),
                        "support-receive",
                        currentBallHolderId,
                        0.72f,
                        roamDistance + 2.1f);
                }

                if (sameSideBallRank == 1 && attackEvent)
                {
                    var overlapTarget =
                        anchorPosition +
                        toBallFromAnchor.normalized * Mathf.Min(toBallFromAnchor.magnitude * 0.48f, 1.1f) +
                        attackDirection * (roleBucket == 3 ? 1.55f : 0.95f) +
                        widthBias * 0.96f +
                        teammateRepulsion * 0.52f +
                        microMotion * 0.18f;
                    return ReturnBehaviorTarget(
                        overlapTarget,
                        Mathf.Max(baseBehaviorWeight + 0.05f, 0.62f),
                        "overlap",
                        currentBallHolderId,
                        0.68f,
                        roamDistance + 2.3f);
                }

                if (sameSideBallRank == 2 && attackEvent)
                {
                    var recycleTarget =
                        Vector3.Lerp(currentPosition, anchorPosition, 0.55f) +
                        attackDirection * (roleBucket == 1 ? 0.15f : 0.45f) +
                        widthBias * 0.55f +
                        teammateRepulsion * 0.5f +
                        microMotion;
                    return ReturnBehaviorTarget(
                        recycleTarget,
                        Mathf.Max(baseBehaviorWeight, 0.48f),
                        "recycle",
                        currentBallHolderId,
                        0.54f,
                        roamDistance + 1.7f);
                }

                var shapeTarget =
                    anchorPosition +
                    attackDirection * (roleBucket == 1 ? 0.05f : roleBucket == 2 ? 0.25f : 0.5f) +
                    widthBias * 0.35f +
                    teammateRepulsion * 0.35f +
                    microMotion;
                return ReturnBehaviorTarget(
                    shapeTarget,
                    Mathf.Max(baseBehaviorWeight, 0.3f),
                    "attack-shape",
                    currentBallHolderId,
                    0.35f,
                    roamDistance + 1.15f);
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
                return ReturnBehaviorTarget(
                    pressTarget,
                    Mathf.Max(baseBehaviorWeight + 0.08f, 0.62f),
                    "press",
                    currentBallHolderId,
                    0.68f,
                    roamDistance + 1.9f);
            }

            if (sameSideBallRank == 1)
            {
                var coverTarget =
                    Vector3.Lerp(anchorPosition, ballAnchor, 0.58f) +
                    ballGoalSideOffset +
                    widthBias * 0.6f +
                    teammateRepulsion * 0.55f +
                    microMotion;
                return ReturnBehaviorTarget(
                    coverTarget,
                    Mathf.Max(baseBehaviorWeight, 0.48f),
                    "cover",
                    currentBallHolderId,
                    0.56f,
                    roamDistance + 1.7f);
            }

            if (sameSideBallRank == 2)
            {
                var interceptTarget =
                    Vector3.Lerp(anchorPosition, ballAnchor, 0.45f) +
                    ballGoalSideOffset * 1.2f +
                    widthBias * 0.85f +
                    teammateRepulsion * 0.45f +
                    microMotion;
                return ReturnBehaviorTarget(
                    interceptTarget,
                    Mathf.Max(baseBehaviorWeight, 0.42f),
                    "intercept",
                    currentBallHolderId,
                    0.52f,
                    roamDistance + 1.45f);
            }

            var defensiveTarget =
                Vector3.Lerp(currentPosition, anchorPosition, 0.7f) +
                ballGoalSideOffset * (roleBucket == 1 ? 1.1f : 0.8f) +
                widthBias * 0.3f +
                teammateRepulsion * 0.25f +
                microMotion * 0.5f;
            return ReturnBehaviorTarget(
                defensiveTarget,
                Mathf.Max(baseBehaviorWeight, 0.24f),
                "defensive-shape",
                currentBallHolderId,
                0.32f,
                roamDistance + 1.1f);
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

            if (pitchZones != null)
            {
                var safetyMargin =
                    Mathf.Clamp(
                        pitchSpace != null ? pitchSpace.Width * 0.08f : 4.8f,
                        3.6f,
                        6.6f);
                var interiorFreedom = pitchZones.GetInteriorFreedom01(clampedTarget, safetyMargin);
                var boundaryBias = 1f - interiorFreedom;
                if (boundaryBias > 0.0001f)
                {
                    var safeTarget =
                        pitchZones.ClampToPlayableGrass(
                            clampedTarget,
                            Mathf.Lerp(0.7f, 3.2f, boundaryBias));
                    clampedTarget = Vector3.Lerp(clampedTarget, safeTarget, Mathf.Clamp01(boundaryBias * 0.72f));
                    weight *= Mathf.Lerp(0.28f, 1f, interiorFreedom);
                }
            }

            return ClampToFieldBounds(Vector3.Lerp(clampedAnchor, clampedTarget, weight), false);
        }

        private Vector3 ApplyStructuredTeamSpacing(PlayerPosition livePlayer, Vector3 desiredPosition)
        {
            if (livePlayer == null ||
                livePlayer.isBall ||
                currentState == null ||
                currentState.players == null)
            {
                return ClampToFieldBounds(desiredPosition, false);
            }

            var teamSide = NormalizeTeamSideToken(livePlayer.teamSide);
            if (string.IsNullOrWhiteSpace(teamSide))
            {
                return ClampToFieldBounds(desiredPosition, false);
            }

            var movementUrgency = ResolveLiveMovementUrgency(livePlayer, desiredPosition);
            if (!livePlayer.hasPossession && movementUrgency <= 0.12f)
            {
                return ClampToFieldBounds(desiredPosition, false);
            }

            var roleBucket = ResolveLiveRoleBucket(livePlayer);
            if (roleBucket == 0)
            {
                return ResolveGoalkeeperSpacingTarget(livePlayer, desiredPosition, teamSide);
            }

            var attackDirection = ResolveAttackDirection(livePlayer);
            var lateralDirection = Vector3.Cross(Vector3.up, attackDirection).normalized;
            var laneSign = ResolveBehaviorLaneSign(livePlayer, roleBucket);
            var signature = ResolveBehaviorSignature01(livePlayer, roleBucket);
            var laneMagnitude =
                roleBucket == 0 ? 0.25f :
                roleBucket == 1 ? 1.95f :
                roleBucket == 2 ? 2.85f :
                3.95f;
            var depthSignature = Mathf.Lerp(-1f, 1f, signature);
            var depthMagnitude =
                roleBucket == 0 ? 0f :
                roleBucket == 1 ? 0.5f :
                roleBucket == 2 ? 0.75f :
                1.05f;

            var spacingActivity =
                livePlayer.hasPossession
                    ? 1f
                    : Mathf.Clamp01(Mathf.InverseLerp(0.08f, 0.72f, movementUrgency));
            var interiorFreedom =
                pitchZones != null
                    ? pitchZones.GetInteriorFreedom01(
                        desiredPosition,
                        Mathf.Clamp(
                            pitchSpace != null ? pitchSpace.Width * 0.085f : 4.8f,
                            3.8f,
                            6.8f))
                    : 1f;
            spacingActivity *= Mathf.Lerp(0.24f, 1f, interiorFreedom);
            var spacingOffset =
                lateralDirection * laneSign * laneMagnitude * Mathf.Lerp(0.82f, 1.34f, signature) +
                attackDirection * depthSignature * depthMagnitude;
            var spacedTarget = desiredPosition + spacingOffset * Mathf.Lerp(0.14f, 1f, spacingActivity);

            if (roleBucket == 1)
            {
                spacedTarget -= attackDirection * 0.55f;
            }
            else if (roleBucket == 2)
            {
                spacedTarget += attackDirection * 0.12f;
            }
            else if (roleBucket == 3)
            {
                spacedTarget += attackDirection * 0.85f;
            }

            if (!livePlayer.hasPossession &&
                currentState.ballPosition != null &&
                !string.IsNullOrWhiteSpace(currentState.ballPosition.playerId) &&
                TryResolveLivePlayerByPlayerId(currentState, currentState.ballPosition.playerId, out var holderLive) &&
                string.Equals(teamSide, NormalizeTeamSideToken(holderLive.teamSide), StringComparison.Ordinal))
            {
                var holderPosition = ResolveRuntimeFieldPosition(holderLive, currentState, spacedTarget);
                var separationFromHolder = spacedTarget - holderPosition;
                separationFromHolder.y = 0f;
                var desiredHolderSpacing =
                    roleBucket == 3 ? 2.55f :
                    roleBucket == 2 ? 3.05f :
                    3.35f;
                if (separationFromHolder.magnitude > 0.001f &&
                    separationFromHolder.magnitude < desiredHolderSpacing)
                {
                    spacedTarget +=
                        (separationFromHolder.normalized * (desiredHolderSpacing - separationFromHolder.magnitude) +
                         lateralDirection * laneSign * 0.55f) *
                        Mathf.Lerp(0.2f, 1f, spacingActivity);
                }
            }

            if (pitchZones != null && interiorFreedom < 0.999f)
            {
                var boundaryBias = 1f - interiorFreedom;
                var safeTarget =
                    pitchZones.ClampToPlayableGrass(
                        spacedTarget,
                        Mathf.Lerp(0.7f, 2.9f, boundaryBias));
                spacedTarget = Vector3.Lerp(spacedTarget, safeTarget, Mathf.Clamp01(boundaryBias * 0.82f));
                spacedTarget = Vector3.Lerp(spacedTarget, desiredPosition, Mathf.Clamp01(boundaryBias * 0.36f));
            }

            spacedTarget += ResolveLiveSpacingRepulsion(livePlayer, spacedTarget) * Mathf.Lerp(0.18f, 1f, spacingActivity);
            return ClampToFieldBounds(spacedTarget, false);
        }

        private Vector3 ResolveGoalkeeperSpacingTarget(PlayerPosition livePlayer, Vector3 desiredPosition, string teamSide)
        {
            EnsurePitchSpaceResolved();
            if (pitchSpace == null || pitchZones == null)
            {
                return ClampToFieldBounds(desiredPosition, false);
            }

            var normalizedTeamSide = NormalizeTeamSideToken(teamSide);
            var teamSideIndex = ResolvePitchTeamSideIndex(normalizedTeamSide);
            var homeGoal = teamSideIndex == GtexPitchZoneHelper.HomeTeamSide;
            var goalCenter = pitchZones.GetGoalCenter(teamSideIndex);
            var ballAnchor =
                currentState != null && currentState.ballPosition != null
                    ? ResolvePredictedFieldPosition(currentState.ballPosition, 0f)
                    : goalCenter;

            var possessionSide = ResolvePossessionSideToken();
            var distanceToGoal = pitchZones.DistanceToGoalCenter(ballAnchor, teamSideIndex);
            var threat01 = 1f - Mathf.Clamp01(distanceToGoal / Mathf.Max(1f, pitchSpace.HalfLength));
            if (string.Equals(normalizedTeamSide, possessionSide, StringComparison.Ordinal))
            {
                threat01 *= 0.18f;
            }

            var inwardDirection = homeGoal ? pitchZones.HomeToAwayAxis : -pitchZones.HomeToAwayAxis;
            var lateralProjection = Vector3.Project(ballAnchor - goalCenter, pitchZones.LateralAxis);
            lateralProjection = Vector3.ClampMagnitude(lateralProjection, 3.75f);
            var rawKeeperTarget = pitchZones.GetKeeperBallAngleTarget(ballAnchor, desiredPosition, teamSideIndex);
            rawKeeperTarget += lateralProjection * Mathf.Lerp(0.04f, 0.16f, threat01);
            rawKeeperTarget.y = pitchSpace.GrassY;
            var keeperTarget = rawKeeperTarget;
            keeperTarget = pitchZones.ClampGoalkeeperHome(keeperTarget, teamSideIndex);
            var defaultHome = pitchZones.GetDefaultGoalkeeperHome(teamSideIndex, pitchSpace.GrassY);

            var currentKeeperPosition = ResolveRuntimeFieldPosition(livePlayer, currentState, keeperTarget);
            var isSweepState = ((livePlayer.state ?? string.Empty).Trim().ToLowerInvariant()).Contains("sweep");
            if (!isSweepState && !pitchZones.IsInsideGoalkeeperHomeZone(currentKeeperPosition, teamSideIndex))
            {
                _keeperZoneViolations += 1;
                keeperTarget = Vector3.Lerp(defaultHome, keeperTarget, 0.55f);
                keeperTarget = pitchZones.ClampGoalkeeperHome(keeperTarget, teamSideIndex);
                ReportRuntimeValidation(
                    "goalkeeper_outside_home_zone",
                    "player=" + DescribeLivePlayer(livePlayer) +
                    " current=" + FormatPlaybackVector(currentKeeperPosition) +
                    " recover=" + FormatPlaybackVector(keeperTarget),
                    1.5f);
            }

            if (!isSweepState && !pitchZones.IsInsidePenaltyArea(currentKeeperPosition, teamSideIndex))
            {
                _keeperZoneViolations += 1;
                keeperTarget = defaultHome;
                ReportRuntimeValidation(
                    "goalkeeper_forced_recover",
                    "player=" + DescribeLivePlayer(livePlayer) +
                    " current=" + FormatPlaybackVector(currentKeeperPosition) +
                    " target=" + FormatPlaybackVector(keeperTarget),
                    1.25f);
            }

            if ((keeperTarget - rawKeeperTarget).sqrMagnitude > 0.04f)
            {
                ReportRuntimeValidation(
                    "goalkeeper_target_reclamped",
                    "player=" + DescribeLivePlayer(livePlayer) +
                    " raw=" + FormatPlaybackVector(rawKeeperTarget) +
                    " target=" + FormatPlaybackVector(keeperTarget),
                    2f);
            }

            return ClampToFieldBounds(keeperTarget, false);
        }

        private Vector3 ResolveLiveSpacingRepulsion(PlayerPosition livePlayer, Vector3 desiredPosition)
        {
            if (livePlayer == null ||
                currentState == null ||
                currentState.players == null ||
                !GtexMatchController.MatchManagerAdapter.IsAvailable)
            {
                return Vector3.zero;
            }

            var teamSide = NormalizeTeamSideToken(livePlayer.teamSide);
            if (string.IsNullOrWhiteSpace(teamSide))
            {
                return Vector3.zero;
            }

            var roleBucket = ResolveLiveRoleBucket(livePlayer);
            var attackDirection = ResolveAttackDirection(livePlayer);
            var lateralDirection = Vector3.Cross(Vector3.up, attackDirection).normalized;
            var laneSign = ResolveBehaviorLaneSign(livePlayer, roleBucket);
            var minimumSeparation =
                roleBucket == 0 ? 1.25f :
                roleBucket == 1 ? 3.15f :
                roleBucket == 2 ? 3.6f :
                4.15f;
            var repulsionRadius = Mathf.Max(LiveBehaviorTeammateRepulsionRadius, minimumSeparation + 1.45f);

            desiredPosition.y = 0f;
            var repulsion = Vector3.zero;
            var contributors = 0;

            foreach (var teammate in currentState.players)
            {
                if (teammate == null ||
                    teammate.isBall ||
                    !teammate.active ||
                    IsSameLivePlayer(teammate, livePlayer) ||
                    !string.Equals(NormalizeTeamSideToken(teammate.teamSide), teamSide, StringComparison.Ordinal))
                {
                    continue;
                }

                var teammatePosition = ResolveRuntimeFieldPosition(teammate, currentState, desiredPosition);
                var separation = desiredPosition - teammatePosition;
                separation.y = 0f;
                var distance = separation.magnitude;
                if (distance <= 0.001f)
                {
                    separation = lateralDirection * laneSign;
                    distance = 0.001f;
                }

                if (distance >= repulsionRadius)
                {
                    continue;
                }

                var pressure =
                    1f - Mathf.Clamp01(distance / repulsionRadius) +
                    Mathf.Max(0f, minimumSeparation - distance) / Mathf.Max(minimumSeparation, 0.001f);
                repulsion += separation.normalized * pressure;
                contributors += 1;
            }

            if (contributors == 0)
            {
                return Vector3.zero;
            }

            repulsion /= contributors;
            repulsion.y = 0f;
            return Vector3.ClampMagnitude(
                repulsion,
                roleBucket == 3 ? 2.25f : (roleBucket == 2 ? 2.05f : 1.85f));
        }

        private Vector3 ResolveLiveFieldVelocity(PlayerPosition livePosition)
        {
            if (livePosition == null || currentState == null || !GtexMatchController.MatchManagerAdapter.IsAvailable)
            {
                return Vector3.zero;
            }

            var velocity = ConvertIncomingPlaybackVelocity(livePosition, currentState);
            if (!livePosition.isBall)
            {
                velocity.y = 0f;
                velocity = Vector3.ClampMagnitude(velocity, ResolveLiveRoleSpeedCap(livePosition));
            }

            return velocity;
        }

        private Vector3 ClampToFieldBounds(Vector3 position, bool isBall)
        {
            EnsurePitchSpaceResolved();
            var originalPosition = position;
            var margin = isBall ? 0.18f : 0.36f;
            if (playbackSanitizer != null)
            {
                position = isBall
                    ? playbackSanitizer.SanitizeBallPosition(position)
                    : playbackSanitizer.SanitizePlayerPosition(position);
            }
            else
            {
                var fieldSize = GtexMatchController.MatchManagerAdapter.FieldSize;
                if (fieldSize != Vector2.zero)
                {
                    position.x = Mathf.Clamp(position.x, 0f, fieldSize.x);
                    position.z = Mathf.Clamp(position.z, 0f, fieldSize.y);
                }
            }

            if (pitchZones != null)
            {
                position = pitchZones.ClampToPlayableGrass(position, margin);
            }

            position.y =
                isBall
                    ? Mathf.Max(
                        pitchSpace != null
                            ? pitchSpace.GrassY + GtexPlaybackSanitizer.DefaultBallHeight
                            : 0.1f,
                        position.y)
                    : (pitchSpace != null ? pitchSpace.GrassY : 0f);

            if ((position - originalPosition).sqrMagnitude > 0.25f)
            {
                ReportRuntimeValidation(
                    isBall ? "ball_clamped_to_pitch" : "player_clamped_to_pitch",
                    "from=" + FormatPlaybackVector(originalPosition) +
                    " to=" + FormatPlaybackVector(position),
                    2.5f);
            }

            return position;
        }

        private int ResolvePitchTeamSideIndex(string teamSide)
        {
            return NormalizeTeamSideToken(teamSide) == "away"
                ? GtexPitchZoneHelper.AwayTeamSide
                : GtexPitchZoneHelper.HomeTeamSide;
        }

        private int ResolveOpposingPitchTeamSideIndex(string teamSide)
        {
            return ResolvePitchTeamSideIndex(teamSide) == GtexPitchZoneHelper.AwayTeamSide
                ? GtexPitchZoneHelper.HomeTeamSide
                : GtexPitchZoneHelper.AwayTeamSide;
        }

        private bool IsNearTeamBox(Vector3 worldPosition, int teamSide)
        {
            EnsurePitchSpaceResolved();
            if (pitchZones == null)
            {
                return false;
            }

            if (pitchZones.IsInsidePenaltyArea(worldPosition, teamSide))
            {
                return true;
            }

            var distanceToGoal = pitchZones.DistanceToGoalCenter(worldPosition, teamSide);
            return distanceToGoal <= Mathf.Clamp(pitchSpace != null ? pitchSpace.Length * 0.22f : 23f, 16f, 24f);
        }

        private bool IsGoalkeeperStateException(PlayerPosition livePlayer, string normalizedState)
        {
            if (ResolveLiveRoleBucket(livePlayer) != 0)
            {
                return false;
            }

            return normalizedState.Contains("set") ||
                   normalizedState.Contains("ready") ||
                   normalizedState.Contains("recover") ||
                   normalizedState.Contains("claim") ||
                   normalizedState.Contains("save") ||
                   normalizedState.Contains("sweep");
        }

        private static bool IsExplicitNonForwardState(string normalizedState)
        {
            if (string.IsNullOrWhiteSpace(normalizedState))
            {
                return false;
            }

            return normalizedState.Contains("jockey") ||
                   normalizedState.Contains("backpedal") ||
                   normalizedState.Contains("contain");
        }

        private bool CanAllowNonForwardMovement(
            PlayerPosition livePlayer,
            string normalizedState,
            float movementUrgency,
            float targetDistance)
        {
            if (IsExplicitNonForwardState(normalizedState) ||
                IsGoalkeeperStateException(livePlayer, normalizedState))
            {
                return true;
            }

            return normalizedState.Contains("receive") &&
                   targetDistance <= 1.25f &&
                   movementUrgency <= 0.56f;
        }

        private GtexMoveException GetMoveExceptionForPlayer(
            PlayerPosition livePlayer,
            string normalizedState,
            float targetDistance)
        {
            if (IsExplicitNonForwardState(normalizedState))
            {
                if (normalizedState.Contains("jockey"))
                {
                    return GtexMoveException.Jockey;
                }

                if (normalizedState.Contains("backpedal"))
                {
                    return GtexMoveException.Backpedal;
                }

                return GtexMoveException.DefensiveContain;
            }

            if (IsGoalkeeperStateException(livePlayer, normalizedState))
            {
                return normalizedState.Contains("ready")
                    ? GtexMoveException.KeeperReadyStance
                    : GtexMoveException.KeeperSetPosition;
            }

            return normalizedState.Contains("receive") && targetDistance <= 1.25f
                ? GtexMoveException.ReceiverMicroAdjust
                : GtexMoveException.None;
        }

        private Vector3 ResolveLegalPlayerVelocity(
            GtexLegacyPlayerHandle player,
            Vector3 desiredVelocity,
            float deltaTime,
            bool wantsSprint,
            GtexMoveException moveException)
        {
            if (player == null || !player.IsValid)
            {
                return desiredVelocity;
            }

            var motion = GtexVisualMotionGuard.Resolve(
                player.UnityTransform,
                player.Animator,
                desiredVelocity,
                deltaTime,
                moveException,
                wantsSprint,
                visualTurnDegreesPerSecond,
                4.5f,
                nonForwardExceptionMaxSpeed);
            if (gtexRuntimeValidation && motion.blockedBackwardSprint)
            {
                _backwardSprintBlocks += 1;
            }

            return motion.legalVelocity;
        }

        private void ReportRuntimeValidation(string key, string details, float throttleSeconds = RuntimeValidationLogThrottleSeconds)
        {
            if (string.IsNullOrWhiteSpace(key))
            {
                return;
            }

            runtimeValidationCounts.TryGetValue(key, out var existingCount);
            var nextCount = existingCount + 1;
            runtimeValidationCounts[key] = nextCount;

            AppendRuntimeTrace("validation", key + "#" + nextCount + " " + details);

            if (config == null || !config.verboseLogging)
            {
                return;
            }

            runtimeValidationNextLogAt.TryGetValue(key, out var nextLogAt);
            var now = Time.unscaledTime;
            if (now < nextLogAt)
            {
                return;
            }

            runtimeValidationNextLogAt[key] = now + Mathf.Max(0.5f, throttleSeconds);
            Debug.LogWarning("[GTEX][Validate] " + key + " " + details);
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
                    return Mathf.Lerp(LiveBehaviorMinRoamDistance + 0.15f, 3.35f, speedRatio);
                case 2:
                    return Mathf.Lerp(LiveBehaviorMinRoamDistance + 0.45f, 4.2f, speedRatio);
                case 3:
                    return Mathf.Lerp(LiveBehaviorMinRoamDistance + 0.75f, LiveBehaviorMaxRoamDistance, speedRatio);
                default:
                    return Mathf.Lerp(LiveBehaviorMinRoamDistance + 0.2f, 3.85f, speedRatio);
            }
        }

        private int ResolveTeamBallRank(PlayerPosition livePlayer, Vector3 currentPosition, Vector3 ballAnchor)
        {
            return ResolveTeamDistanceRank(livePlayer, currentPosition, ballAnchor);
        }

        private int ResolveTeamDistanceRank(PlayerPosition livePlayer, Vector3 currentPosition, Vector3 targetPosition)
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
            targetPosition.y = 0f;
            var playerDistance = (targetPosition - currentPosition).sqrMagnitude;
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
                if ((targetPosition - candidatePosition).sqrMagnitude + 0.01f < playerDistance)
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
                IsTerminalLiveState(nextState) ||
                ShouldSuppressBoundaryMotion(nextState))
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

            var liveVelocity = ResolvePlaybackBallVelocity(nextState.ballPosition, false);
            liveVelocity.y = 0f;
            var ballSpeed = liveVelocity.magnitude;
            if (ballSpeed < LiveBallPassSpeedUnitsPerSecond)
            {
                return;
            }

            var activeEvent = nextState.ResolveActiveEvent();
            var eventType = NormalizeActiveEventTypeToken(nextState, activeEvent);
            var eventPrimaryPlayerId = ((activeEvent != null ? activeEvent.primaryPlayerId : string.Empty) ?? string.Empty).Trim();
            if (EventSuggestsBallTravel(eventType) &&
                !string.IsNullOrWhiteSpace(eventPrimaryPlayerId) &&
                string.Equals(eventPrimaryPlayerId, previousHolderId, StringComparison.Ordinal))
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
            if (nextState == null || IsTerminalLiveState(nextState) || ShouldSuppressBoundaryMotion(nextState))
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
            var passLikeEvent =
                eventType.Contains("pass") ||
                eventType.Contains("cross") ||
                eventType.Contains("switch");
            var shotLikeEvent =
                eventType.Contains("chance") ||
                eventType.Contains("miss") ||
                eventType.Contains("goal") ||
                eventType.Contains("save") ||
                eventType.Contains("shot");
            if (!passLikeEvent && !shotLikeEvent)
            {
                return;
            }

            var primaryPlayerId = (activeEvent.primaryPlayerId ?? string.Empty).Trim();
            if (!TryGetBoundPlayerByPlayerId(primaryPlayerId, out var player) || player == null)
            {
                return;
            }

            var ballVelocity = ResolvePlaybackBallVelocity(nextState.ballPosition, false);
            ballVelocity.y = 0f;
            if (ballVelocity.sqrMagnitude <= 0.0001f)
            {
                ballVelocity = player.Forward * LiveBallShotSpeedUnitsPerSecond;
            }

            if (passLikeEvent)
            {
                ballVelocity = Vector3.ClampMagnitude(ballVelocity, Mathf.Max(LiveBallPassSpeedUnitsPerSecond, 7.5f));
            }

            var secondaryPlayerId = ResolveActiveEventSecondaryPlayerId(activeEvent);
            var targetPosition =
                !string.IsNullOrWhiteSpace(secondaryPlayerId)
                    ? ResolveRuntimePlayerPositionById(nextState, secondaryPlayerId, player.Position + ballVelocity)
                    : player.Position + ballVelocity;
            targetPosition = ClampToFieldBounds(targetPosition, true);
            var canReleaseNow = TryReleaseKick(player, targetPosition, false);
            var releaseAnchor = ResolveBallReleaseOrigin(nextState, primaryPlayerId, player.Position, targetPosition - player.Position);
            var releaseDirection = targetPosition - releaseAnchor;
            releaseDirection.y = 0f;
            if (releaseDirection.sqrMagnitude <= 0.0001f)
            {
                releaseDirection = ballVelocity;
                releaseDirection.y = 0f;
            }

            if (passLikeEvent && releaseDirection.sqrMagnitude > 0.0001f)
            {
                ballVelocity =
                    releaseDirection.normalized *
                    Mathf.Max(ballVelocity.magnitude, Mathf.Max(LiveBallPassSpeedUnitsPerSecond, 7.5f));
            }

            if (releaseDirection.sqrMagnitude > 0.0001f)
            {
                releaseDirection.Normalize();
                var flattenedForward = player.Forward;
                flattenedForward.y = 0f;
                if (flattenedForward.sqrMagnitude > 0.0001f)
                {
                    flattenedForward.Normalize();
                    var bodyAlignment = Vector3.Dot(flattenedForward, releaseDirection);
                    if (bodyAlignment < 0.52f)
                    {
                        ReportRuntimeValidation(
                            "pass_release_alignment_low",
                            "player=" + primaryPlayerId +
                            " target=" + secondaryPlayerId +
                            " dot=" + bodyAlignment.ToString("0.##") +
                            " type=" + eventType,
                            1.25f);
                    }

                    player.SetExternalPlaybackPose(
                        player.Position,
                        Quaternion.LookRotation(Vector3.Slerp(flattenedForward, releaseDirection, passLikeEvent ? 0.8f : 0.92f), Vector3.up),
                        bodyAlignment < 0.18f);
                }

                if (config != null && (config.verboseLogging || config.showRuntimeDebugOverlay))
                {
                    Debug.DrawLine(releaseAnchor + Vector3.up * 0.2f, targetPosition + Vector3.up * 0.2f, passLikeEvent ? Color.cyan : Color.red, 1.25f, false);
                }
            }

            if (!canReleaseNow && passLikeEvent)
            {
                return;
            }

            AppendRuntimeTrace(
                "event-action",
                "minute=" + nextState.clockMinute.ToString("0.##") +
                " type=" + eventType +
                " player=" + primaryPlayerId +
                " release=" + FormatPlaybackVector(releaseAnchor) +
                " speed=" + ballVelocity.magnitude.ToString("0.##"));
            player.PlayExternalBallHit(ballVelocity, shotLikeEvent);
        }

        private static Vector3 ResolveLookDirection(PlayerPosition livePlayer, Vector3 movementDelta, GtexLegacyPlayerHandle player)
        {
            var movementDirection = Vector3.zero;
            if (movementDelta.sqrMagnitude > 0.0001f)
            {
                movementDirection = movementDelta.normalized;
            }

            if (livePlayer != null)
            {
                var explicitFacing = new Vector3(livePlayer.facingX, 0f, livePlayer.facingZ);
                if (explicitFacing.sqrMagnitude > 0.0001f)
                {
                    explicitFacing.Normalize();
                    if (movementDirection.sqrMagnitude > 0.0001f)
                    {
                        var facingAlignment = Vector3.Dot(explicitFacing, movementDirection);
                        if (facingAlignment > 0.45f)
                        {
                            return Vector3.Slerp(movementDirection, explicitFacing, 0.22f);
                        }
                    }
                    else
                    {
                        return explicitFacing;
                    }
                }
            }

            if (movementDirection.sqrMagnitude > 0.0001f)
            {
                return movementDirection;
            }

            return player != null && player.IsValid
                ? player.Forward
                : Vector3.forward;
        }

        private static float ResolveLivePlayerMoveSpeed(
            PlayerPosition livePlayer,
            Vector3 currentPosition,
            Vector3 targetPosition,
            Vector3 liveVelocity,
            float targetDistance,
            float movementUrgency,
            bool suppressBoundaryMotion)
        {
            var distance = targetDistance > 0f ? targetDistance : Vector3.Distance(currentPosition, targetPosition);
            var speedRatio = livePlayer != null ? Mathf.Clamp01(livePlayer.speedRatio) : 0f;
            var urgency = Mathf.Clamp01(movementUrgency);
            var roleSpeedCap = ResolveLiveRoleSpeedCap(livePlayer);
            var cruisingCap = Mathf.Lerp(roleSpeedCap * 0.42f, roleSpeedCap, urgency);
            var minSpeed = Mathf.Lerp(0.65f, LivePlayerMinSpeedUnitsPerSecond, urgency);
            var speed = Mathf.Lerp(
                minSpeed,
                Mathf.Min(LivePlayerMaxSpeedUnitsPerSecond, cruisingCap),
                Mathf.Lerp(speedRatio * 0.78f, speedRatio, urgency));
            speed = Mathf.Max(
                speed,
                Mathf.Min(new Vector3(liveVelocity.x, 0f, liveVelocity.z).magnitude * Mathf.Lerp(0.5f, 0.92f, urgency), cruisingCap));
            var distanceFactor = Mathf.Clamp01(Mathf.Max(0f, distance - 0.9f) / 4.25f);
            var catchUpCap = cruisingCap + Mathf.Lerp(
                suppressBoundaryMotion ? 0.35f : Mathf.Lerp(0.2f, 0.75f, urgency),
                suppressBoundaryMotion ? 1.25f : Mathf.Lerp(0.95f, 2.55f, urgency),
                distanceFactor);

            if (distance > Mathf.Lerp(1.2f, 0.72f, urgency))
            {
                speed = Mathf.Max(speed, Mathf.Min(distance / LivePlayerCatchUpSeconds, catchUpCap));
            }

            return Mathf.Clamp(speed, minSpeed, catchUpCap);
        }

        private static float ResolveLiveRoleSpeedCap(PlayerPosition livePlayer)
        {
            var speedRatio = livePlayer != null ? Mathf.Clamp01(livePlayer.speedRatio) : 0f;
            switch (ResolveLiveRoleBucket(livePlayer))
            {
                case 0:
                    return Mathf.Lerp(3.4f, 4.2f, speedRatio);
                case 1:
                    return Mathf.Lerp(4.6f, 5.55f, speedRatio);
                case 2:
                    return Mathf.Lerp(5.05f, 6.15f, speedRatio);
                case 3:
                    return Mathf.Lerp(5.4f, 6.45f, speedRatio);
                default:
                    return Mathf.Lerp(4.7f, 5.95f, speedRatio);
            }
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
