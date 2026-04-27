using System;
using System.Collections;
using System.Collections.Generic;
using System.Threading.Tasks;
using UnityEngine;
using FStudio.GTEX;
using FStudio.GTEX.Core;
using FStudio.GTEX.Engine;
using FStudio.GTEX.Playback;
using FStudio.MatchEngine;
using FStudio.MatchEngine.Enums;
using FStudio.MatchEngine.Players.PlayerController;
using FStudio.Database;
using FStudio.Data;
using FStudio.UI.MatchThemes.MatchEvents;
using Shared.Responses;

namespace FStudio.GTEX.Simulation
{
    public sealed class GtexSimRuntimeHost : MonoBehaviour
    {
        private const float SceneDependencyWaitTimeoutSeconds = 10f;

        private sealed class PendingBootstrap
        {
            public GtexMatchConfig MatchConfig;
            public bool AllowBatchMode;
        }

        private sealed class GtexPlayerBinding
        {
            public string PlayerId;
            public GtexLegacyPlayerHandle Handle;
            public Transform Root;
            public PlayerAnimator Animator;
            public Rigidbody Rigidbody;
            public MonoBehaviour LegacyController;

            public bool IsAlive()
            {
                return Handle != null &&
                       Handle.IsValid &&
                       Root != null &&
                       Root.gameObject != null &&
                       Root.gameObject.activeInHierarchy &&
                       LegacyController != null;
            }

            public void Clear()
            {
                PlayerId = string.Empty;
                Handle = null;
                Root = null;
                Animator = null;
                Rigidbody = null;
                LegacyController = null;
            }
        }

        private struct FilteredAnimatorState
        {
            public float MoveSpeed;
            public float Horizontal;
            public float Vertical;
        }

        private static PendingBootstrap pendingBootstrap;
        private const float AnimatorDeltaFloorSeconds = 1f / 60f;

        [Header("Startup")]
        [SerializeField] private bool autoStart = true;
        [SerializeField] private bool runInBatchMode;
        [SerializeField] private bool useUnscaledTime = true;
        [SerializeField] private bool logSimulationMessages = true;

        [Header("Simulation")]
        [SerializeField] private float fullMatchMinutes = GtexSimConfig.DefaultFullMatchMinutes;
        [SerializeField] private float halfLengthMinutes = GtexSimConfig.DefaultHalfLengthMinutes;
        [SerializeField] private float targetRealDurationMinutes = GtexSimConfig.DefaultTargetRealDurationMinutes;
        [SerializeField] private float eventCheckWindowMinutes = GtexSimConfig.DefaultEventCheckWindowMinutes;
        [SerializeField, Range(0f, 1f)] private float baseEventChancePerWindow = (float)GtexSimConfig.DefaultEventChancePerWindow;
        [SerializeField] private int randomSeed = GtexSimConfig.DefaultRandomSeed;

        [Header("Adapters")]
        [SerializeField] private GtexSimRenderer simRenderer;
        [SerializeField] private GtexSimCrowdController crowdController;
        [SerializeField] private GtexSimUiBridge uiBridge;
        [SerializeField] private GtexSimHud simHud;

        [Header("Playback Camera")]
        [SerializeField] private float cameraBallWeight = 0.45f;
        [SerializeField] private float cameraCarrierWeight = 0.35f;
        [SerializeField] private float cameraClusterWeight = 0.20f;
        [SerializeField] private float cameraMaxFocusDistanceFromBall = 22f;
        [SerializeField] private float cameraFinalThirdGoalBias = 0.18f;
        [SerializeField] private float cameraSmoothTime = 0.14f;

        private GtexSimEngine engine;
        private GtexMatchConfig activeMatchConfig;
        private bool pendingBootstrapConsumed;
        private float lastReportedMinute = -1f;
        private int lastReportedHomeScore = -1;
        private int lastReportedAwayScore = -1;
        private GtexMatchPhase lastReportedPhase = GtexMatchPhase.None;
        private readonly Dictionary<string, GtexPlayerBinding> playerBindingsByKey = new();
        private readonly List<GtexPlayerBinding> playerBindings = new();
        private readonly Dictionary<string, FilteredAnimatorState> filteredAnimatorStates = new();
        private GtexPlaybackApplier playbackApplier;
        private GtexSimSpatialSynthesizer spatialSynthesizer;
        private GtexPitchSpace pitchSpace;
        private GtexPlaybackSanitizer playbackSanitizer;
        private MatchResponse currentPlaybackState;
        private Coroutine playbackBootstrapRoutine;
        private bool playbackSceneBootstrapped;
        private bool playbackSceneBootstrapping;
        private bool playbackBootstrapFailed;
        private bool pendingInitialPlaybackFrame = true;
        private bool playbackActive;
        private bool bindingsValid;
        private bool isResetting;
        private int bindingGeneration;
        private string lastAppliedCameraPreset = string.Empty;
        private Vector3 cameraFocus = Vector3.zero;
        private Vector3 cameraFocusVelocity = Vector3.zero;
        private float nextRuntimeHealthLogMinute = 30f;
        private bool runtimeHealthLoggedAtFullTime;
        private int deadBindingBlocks;
        private int scoreAuthorityUpdates;
        private int legacyScoreWritesBlocked;
        private int kinematicVelocityWritesBlocked;
        private int cameraFocusClamps;

        public GtexSimEngine Engine => engine;

        public string HomeDisplayName { get; private set; } = "Home";

        public string AwayDisplayName { get; private set; } = "Away";

        public static bool TryAutoStart(GtexMatchConfig matchConfig, bool allowBatchMode = false)
        {
            if (matchConfig == null || !matchConfig.CanAutoStartSelectedRuntime)
            {
                return false;
            }

            if (Application.isBatchMode && !allowBatchMode)
            {
                Debug.Log("[GTEX Sim Host] Local simulation auto-start skipped in batchmode.");
                return false;
            }

            var existing = UnityEngine.Object.FindFirstObjectByType<GtexSimRuntimeHost>();
            if (existing != null)
            {
                existing.ApplyBootstrapConfiguration(matchConfig, allowBatchMode);
                existing.EnsureInitialized();
                existing.StartSimulation();
                return true;
            }

            pendingBootstrap = new PendingBootstrap
            {
                MatchConfig = matchConfig,
                AllowBatchMode = allowBatchMode
            };

            try
            {
                var host = new GameObject("GTEX Local Simulation");
                if (Application.isPlaying)
                {
                    DontDestroyOnLoad(host);
                }

                GetOrAddComponent<GtexSimRenderer>(host);
                GetOrAddComponent<GtexSimUiBridge>(host);
                GetOrAddComponent<GtexSimHud>(host);

                if (matchConfig.showCrowd)
                {
                    GetOrAddComponent<GtexSimCrowdController>(host);
                }

                var runtimeHost = host.AddComponent<GtexSimRuntimeHost>();
                runtimeHost.ConsumePendingBootstrap();
                runtimeHost.EnsureInitialized();
                runtimeHost.StartSimulation();
                return true;
            }
            finally
            {
                pendingBootstrap = null;
            }
        }

        private void Awake()
        {
            ConsumePendingBootstrap();

            if (Application.isBatchMode && !runInBatchMode)
            {
                Debug.Log("[GTEX Sim Host] Skipping simulation host in batchmode.");
                GtexMatchController.ReportRuntimeState(
                    activeMatchConfig,
                    GtexRuntimeMode.LocalSimulation,
                    GtexMatchPhase.None,
                    false,
                    nameof(GtexSimRuntimeHost),
                    "Simulation host skipped in batchmode.");
                enabled = false;
                return;
            }

            EnsureInitialized();
        }

        private void OnEnable()
        {
            MatchManager.MatchResetting += HandleMatchResetting;
            MatchManager.MatchResetComplete += HandleMatchResetComplete;
        }

        private void OnDisable()
        {
            MatchManager.MatchResetting -= HandleMatchResetting;
            MatchManager.MatchResetComplete -= HandleMatchResetComplete;

            StopPlaybackAndClearBindings("Host disabled");
        }

        private void ConsumePendingBootstrap()
        {
            if (pendingBootstrapConsumed)
            {
                return;
            }

            var bootstrap = pendingBootstrap;
            if (bootstrap == null)
            {
                return;
            }

            ApplyBootstrapConfiguration(bootstrap.MatchConfig, bootstrap.AllowBatchMode);
            pendingBootstrapConsumed = true;
        }

        private void Start()
        {
            if (!autoStart || engine == null || engine.IsRunning)
            {
                return;
            }

            StartSimulation();
        }

        private void Update()
        {
            if (engine == null)
            {
                return;
            }

            var deltaTime = useUnscaledTime ? Time.unscaledDeltaTime : Time.deltaTime;
            if (engine.IsRunning)
            {
                engine.UpdateMatch(deltaTime);
            }

            if (ShouldUse3DPlayback)
            {
                if (!playbackSceneBootstrapped && !playbackSceneBootstrapping && !playbackBootstrapFailed)
                {
                    BeginPlaybackSceneBootstrap();
                }

                if (!isResetting && playbackSceneBootstrapped && playbackApplier != null)
                {
                    ApplyCurrentSpatialFrame(pendingInitialPlaybackFrame);
                    playbackApplier.Tick(deltaTime);
                }
            }

            ReportSimulationSnapshot();
            MaybeLogRuntimeHealth();
        }

        private void OnDestroy()
        {
            GtexMatchController.ReportRuntimeState(
                activeMatchConfig,
                GtexRuntimeMode.LocalSimulation,
                engine != null ? ResolveControllerPhase(engine.State) : GtexMatchPhase.None,
                false,
                nameof(GtexSimRuntimeHost),
                "Simulation host destroyed.");

            if (engine != null)
            {
                engine.StateChanged -= OnEngineStateChanged;
            }

            if (simRenderer != null)
            {
                simRenderer.Unbind();
            }

            if (crowdController != null)
            {
                crowdController.Unbind();
            }

            if (uiBridge != null)
            {
                uiBridge.Unbind();
            }

            if (playbackBootstrapRoutine != null)
            {
                StopCoroutine(playbackBootstrapRoutine);
                playbackBootstrapRoutine = null;
            }

            if (MatchManager.Current != null && MatchManager.Current.ExternalPlaybackEnabled)
            {
                MatchManager.Current.SetExternalPlayback(false);
            }

            StopPlaybackAndClearBindings("Host destroyed");
        }

        [ContextMenu("Start Simulation")]
        public void StartSimulation()
        {
            EnsureInitialized();

            if (engine.IsRunning)
            {
                return;
            }

            if (ShouldUse3DPlayback)
            {
                EnsurePlaybackApplier();
                BeginPlaybackSceneBootstrap();
            }

            engine.StartMatch();
            GtexScoreAuthority.SetScore(0, 0, 0f, "Kickoff");
            ReportSimulationSnapshot(true, "Local simulation started.");
        }

        [ContextMenu("Stop Simulation")]
        public void StopSimulation()
        {
            if (engine == null)
            {
                return;
            }

            engine.EndMatch();
            LogGtexRuntimeHealth();
            ReportSimulationSnapshot(true, "Local simulation stopped.");
        }

        private void EnsureInitialized()
        {
            if (engine != null)
            {
                return;
            }

            var config = new GtexSimConfig
            {
                FullMatchMinutes = fullMatchMinutes,
                HalfLengthMinutes = halfLengthMinutes,
                TargetRealDurationMinutes = targetRealDurationMinutes,
                EventCheckWindowMinutes = eventCheckWindowMinutes,
                BaseEventChancePerWindow = baseEventChancePerWindow,
                RandomSeed = randomSeed,
                Logger = logSimulationMessages ? message => Debug.Log(message) : null
            };

            engine = new GtexSimEngine(config);
            engine.StateChanged += OnEngineStateChanged;
            ResetReportedSnapshot();
            spatialSynthesizer ??= new GtexSimSpatialSynthesizer();

            if (simRenderer == null)
            {
                simRenderer = GetComponent<GtexSimRenderer>();
            }

            if (crowdController == null)
            {
                crowdController = GetComponent<GtexSimCrowdController>();
            }

            if (uiBridge == null)
            {
                uiBridge = GetComponent<GtexSimUiBridge>();
            }

            if (simHud == null)
            {
                simHud = GetComponent<GtexSimHud>();
            }

            if (simRenderer != null && simRenderer.isActiveAndEnabled)
            {
                simRenderer.Bind(engine);
            }

            if (crowdController != null && crowdController.isActiveAndEnabled)
            {
                crowdController.Bind(engine);
            }

            if (uiBridge != null && uiBridge.isActiveAndEnabled)
            {
                uiBridge.Bind(this, engine);
            }

            if (simHud != null && simHud.isActiveAndEnabled)
            {
                simHud.Bind(this, simRenderer, crowdController, uiBridge);
            }

            Debug.Log("[GTEX Sim Host] Simulation initialized.");
            GtexMatchController.ReportRuntimeState(
                activeMatchConfig,
                GtexRuntimeMode.LocalSimulation,
                GtexMatchPhase.Bootstrap,
                false,
                nameof(GtexSimRuntimeHost),
                "Simulation host initialized.");
        }

        private void ApplyMatchConfig(GtexMatchConfig matchConfig)
        {
            if (matchConfig == null)
            {
                return;
            }

            logSimulationMessages = matchConfig.verboseLogging;
            targetRealDurationMinutes = matchConfig.simulationTargetDurationMinutes;
            eventCheckWindowMinutes = matchConfig.simulationEventCheckWindowMinutes;
            baseEventChancePerWindow = Mathf.Clamp01(matchConfig.simulationBaseEventChancePerWindow);
            randomSeed = matchConfig.simulationRandomSeed;
            HomeDisplayName = ResolveDisplayName(matchConfig.homeTeamName, matchConfig.homeTemplateTeam, "Home");
            AwayDisplayName = ResolveDisplayName(matchConfig.awayTeamName, matchConfig.awayTemplateTeam, "Away");
            GtexScoreAuthority.Reset(HomeDisplayName, AwayDisplayName);
            ResetRuntimeHealthTracking();

            if (engine != null)
            {
                if (simRenderer != null)
                {
                    simRenderer.Unbind();
                }

                if (crowdController != null)
                {
                    crowdController.Unbind();
                }

                if (uiBridge != null)
                {
                    uiBridge.Unbind();
                }

                engine.StateChanged -= OnEngineStateChanged;
                engine = null;
            }

            if (spatialSynthesizer != null)
            {
                spatialSynthesizer.Reset();
            }

            if (playbackBootstrapRoutine != null)
            {
                StopCoroutine(playbackBootstrapRoutine);
                playbackBootstrapRoutine = null;
            }

            if (MatchManager.Current != null && MatchManager.Current.ExternalPlaybackEnabled)
            {
                MatchManager.Current.SetExternalPlayback(false);
            }

            StopPlaybackAndClearBindings("Applying match config");
            currentPlaybackState = null;
            playbackSceneBootstrapped = false;
            playbackSceneBootstrapping = false;
            playbackBootstrapFailed = false;
            pendingInitialPlaybackFrame = true;
            playbackActive = false;
            bindingsValid = false;
            isResetting = false;
            lastAppliedCameraPreset = string.Empty;
            cameraFocus = Vector3.zero;
            cameraFocusVelocity = Vector3.zero;
            pitchSpace = null;
            playbackSanitizer = null;
            activeMatchConfig = matchConfig;
            playbackApplier?.Reset();
            playbackApplier?.Initialize(activeMatchConfig);
            ResetReportedSnapshot();
        }

        private void ApplyBootstrapConfiguration(GtexMatchConfig matchConfig, bool allowBatchMode)
        {
            runInBatchMode = allowBatchMode;
            autoStart = true;
            ApplyMatchConfig(matchConfig);
        }

        private void OnEngineStateChanged(GtexSimState nextState)
        {
            ReportSimulationSnapshot(true, "Local simulation state changed to " + nextState + ".");
            if (nextState == GtexSimState.FullTime)
            {
                MaybeLogRuntimeHealth(true);
            }
        }

        private bool ShouldUse3DPlayback =>
            activeMatchConfig != null &&
            activeMatchConfig.use3DPlaybackForLocalSimulation;

        private void BeginPlaybackSceneBootstrap()
        {
            if (!ShouldUse3DPlayback || playbackSceneBootstrapped || playbackSceneBootstrapping)
            {
                return;
            }

            if (playbackBootstrapRoutine != null)
            {
                StopCoroutine(playbackBootstrapRoutine);
            }

            playbackBootstrapRoutine = StartCoroutine(BootstrapPlaybackScene());
        }

        private IEnumerator BootstrapPlaybackScene()
        {
            playbackSceneBootstrapping = true;
            playbackBootstrapFailed = false;
            var waitStartedAt = Time.realtimeSinceStartup;

            while (!GtexMatchController.MatchEngineLoaderAdapter.IsPlaybackSceneReady)
            {
                if (Time.realtimeSinceStartup - waitStartedAt >= SceneDependencyWaitTimeoutSeconds)
                {
                    Debug.LogWarning("[GTEX Sim Host] Timed out waiting for playback scene dependencies.");
                    playbackBootstrapFailed = true;
                    playbackSceneBootstrapping = false;
                    playbackBootstrapRoutine = null;
                    yield break;
                }

                yield return null;
            }

            if (!TryBuildMatchRequest(out var matchRequest))
            {
                playbackBootstrapFailed = true;
                playbackSceneBootstrapping = false;
                playbackBootstrapRoutine = null;
                yield break;
            }

            yield return AwaitTask(GtexMatchController.MatchEngineLoaderAdapter.CreateMatch(matchRequest), "CreateMatch");
            if (playbackBootstrapFailed)
            {
                playbackSceneBootstrapping = false;
                playbackBootstrapRoutine = null;
                yield break;
            }

            yield return AwaitTask(
                GtexMatchController.MatchEngineLoaderAdapter.StartMatchEngine(
                    new UpcomingMatchEvent(matchRequest),
                    false,
                    false,
                    activeMatchConfig),
                "StartMatchEngine");
            if (playbackBootstrapFailed)
            {
                playbackSceneBootstrapping = false;
                playbackBootstrapRoutine = null;
                yield break;
            }

            if (!GtexMatchController.MatchManagerAdapter.IsAvailable)
            {
                Debug.LogWarning("[GTEX Sim Host] MatchManager is unavailable after 3D playback bootstrap.");
                playbackBootstrapFailed = true;
                playbackSceneBootstrapping = false;
                playbackBootstrapRoutine = null;
                yield break;
            }

            MatchManager.Current.ConfigureExternalPlaybackSettings(activeMatchConfig);
            MatchManager.Current.SetExternalPlayback(true);
            ResolvePitchSpace();
            EnsurePlaybackApplier();
            playbackApplier.Initialize(activeMatchConfig);
            playbackActive = true;
            bindingsValid = false;
            isResetting = false;
            playbackSceneBootstrapped = true;
            playbackSceneBootstrapping = false;
            playbackBootstrapRoutine = null;
            pendingInitialPlaybackFrame = true;
            ApplyCurrentSpatialFrame(true);
        }

        private IEnumerator AwaitTask(Task task, string taskLabel)
        {
            if (task == null)
            {
                playbackBootstrapFailed = true;
                Debug.LogError("[GTEX Sim Host] " + taskLabel + " returned a null task.");
                yield break;
            }

            while (!task.IsCompleted)
            {
                yield return null;
            }

            if (task.IsCanceled)
            {
                playbackBootstrapFailed = true;
                Debug.LogError("[GTEX Sim Host] " + taskLabel + " was cancelled.");
            }
            else if (task.IsFaulted)
            {
                playbackBootstrapFailed = true;
                Debug.LogError("[GTEX Sim Host] " + taskLabel + " failed: " + task.Exception);
            }
        }

        private void ApplyCurrentSpatialFrame(bool forceSnap)
        {
            if (!ShouldUse3DPlayback ||
                isResetting ||
                !playbackSceneBootstrapped ||
                playbackApplier == null ||
                spatialSynthesizer == null ||
                engine == null)
            {
                return;
            }

            currentPlaybackState = spatialSynthesizer.SynthesizeMatchResponse(engine, activeMatchConfig, ResolveSimulationMatchId());
            PublishScoreFromSnapshot(currentPlaybackState);
            playbackApplier.ApplyFrame(currentPlaybackState, forceSnap);
            pendingInitialPlaybackFrame = false;
        }

        private string ResolveSimulationMatchId()
        {
            return !string.IsNullOrWhiteSpace(activeMatchConfig != null ? activeMatchConfig.matchId : null)
                ? activeMatchConfig.matchId
                : "local-sim-3d";
        }

        private void ReportSimulationSnapshot(bool force = false, string message = null)
        {
            if (engine == null)
            {
                return;
            }

            var phase = ResolveControllerPhase(engine.State);
            var minute = engine.Clock.CurrentMatchMinute;
            var homeScore = engine.HomeScore;
            var awayScore = engine.AwayScore;

            if (!force &&
                Mathf.Abs(minute - lastReportedMinute) < 0.25f &&
                homeScore == lastReportedHomeScore &&
                awayScore == lastReportedAwayScore &&
                phase == lastReportedPhase)
            {
                return;
            }

            lastReportedMinute = minute;
            lastReportedHomeScore = homeScore;
            lastReportedAwayScore = awayScore;
            lastReportedPhase = phase;

            GtexMatchController.ReportMatchSnapshot(
                GtexRuntimeMode.LocalSimulation,
                phase,
                engine.IsRunning,
                nameof(GtexSimRuntimeHost),
                minute,
                homeScore,
                awayScore,
                message ?? "Local simulation advanced.");
        }

        private void HandleMatchResetting()
        {
            StopPlaybackAndClearBindings("MatchManager reset started");
            isResetting = true;
        }

        private void HandleMatchResetComplete()
        {
            isResetting = false;

            if (GtexRuntimeFlags.IsLocalSimulation && ShouldUse3DPlayback && playbackSceneBootstrapped)
            {
                playbackActive = true;
                RebuildPlaybackBindings();
                bindingsValid = playerBindings.Count > 0;
            }
        }

        private void RebuildPlaybackBindings()
        {
            if (currentPlaybackState == null)
            {
                return;
            }

            BindPlaybackPlayers();
        }

        private void PublishScoreFromSnapshot(MatchResponse snapshot)
        {
            if (snapshot == null)
            {
                return;
            }

            var score = GtexScoreAuthority.Current;
            if (!string.Equals(score.homeLabel, HomeDisplayName, StringComparison.Ordinal) ||
                !string.Equals(score.awayLabel, AwayDisplayName, StringComparison.Ordinal))
            {
                GtexScoreAuthority.SetTeams(HomeDisplayName, AwayDisplayName);
            }

            var lastEvent = snapshot.ResolveActiveEvent();
            GtexScoreAuthority.SetScore(
                snapshot.homeScore,
                snapshot.awayScore,
                snapshot.clockMinute,
                lastEvent != null ? lastEvent.commentary : uiBridge != null ? uiBridge.LastEventSummary : string.Empty);
        }

        private void ResetRuntimeHealthTracking()
        {
            nextRuntimeHealthLogMinute = 30f;
            runtimeHealthLoggedAtFullTime = false;
            deadBindingBlocks = 0;
            scoreAuthorityUpdates = 0;
            legacyScoreWritesBlocked = 0;
            kinematicVelocityWritesBlocked = 0;
            cameraFocusClamps = 0;
            GtexRuntimeTelemetry.Reset();
        }

        private void MaybeLogRuntimeHealth(bool force = false)
        {
            if (engine == null)
            {
                return;
            }

            var shouldLogFullTime = engine.State == GtexSimState.FullTime && !runtimeHealthLoggedAtFullTime;
            if (!force && !shouldLogFullTime && engine.Clock.CurrentMatchMinute + 0.01f < nextRuntimeHealthLogMinute)
            {
                return;
            }

            LogGtexRuntimeHealth();
            while (nextRuntimeHealthLogMinute <= engine.Clock.CurrentMatchMinute)
            {
                nextRuntimeHealthLogMinute += 30f;
            }

            if (engine.State == GtexSimState.FullTime)
            {
                runtimeHealthLoggedAtFullTime = true;
            }
        }

        private void LogGtexRuntimeHealth()
        {
            deadBindingBlocks = GtexRuntimeTelemetry.DeadBindingBlocks;
            scoreAuthorityUpdates = GtexRuntimeTelemetry.ScoreAuthorityUpdates;
            legacyScoreWritesBlocked = GtexRuntimeTelemetry.LegacyScoreWritesBlocked;
            kinematicVelocityWritesBlocked = GtexRuntimeTelemetry.KinematicVelocityWritesBlocked;
            cameraFocusClamps = GtexRuntimeTelemetry.CameraFocusClamps;

            Debug.Log(
                "[GTEX Runtime Health] " +
                "deadBindingBlocks=" + deadBindingBlocks +
                ", scoreUpdates=" + scoreAuthorityUpdates +
                ", legacyScoreWritesBlocked=" + legacyScoreWritesBlocked +
                ", kinematicVelocityWritesBlocked=" + kinematicVelocityWritesBlocked +
                ", cameraFocusClamps=" + cameraFocusClamps);
        }

        private void StopPlaybackAndClearBindings(string reason)
        {
            if (!string.IsNullOrWhiteSpace(reason))
            {
                Debug.Log("[GTEX Playback] Stop and clear bindings: " + reason);
            }

            playbackActive = false;
            bindingsValid = false;
            bindingGeneration += 1;

            for (var index = 0; index < playerBindings.Count; index += 1)
            {
                playerBindings[index]?.Clear();
            }

            playerBindings.Clear();
            playerBindingsByKey.Clear();
            filteredAnimatorStates.Clear();
            playbackApplier?.Reset();
        }

        private void EnsurePlaybackApplier()
        {
            if (playbackApplier != null)
            {
                playbackApplier.Initialize(activeMatchConfig);
                return;
            }

            playbackApplier = new GtexPlaybackApplier(
                () => playbackSceneBootstrapped,
                NeedsPlaybackBindingRefresh,
                BindPlaybackPlayers,
                DrivePlaybackPlayers,
                DrivePlaybackBall,
                BeforeApplyPlaybackFrame,
                ApplyPlaybackSceneState,
                ApplyPlaybackCameraPreset,
                null,
                null,
                null,
                null,
                SnapPlaybackScene);
            playbackApplier.Initialize(activeMatchConfig);
        }

        private void BeforeApplyPlaybackFrame(MatchResponse state, bool forceSnap)
        {
            currentPlaybackState = state;
            if (forceSnap)
            {
                bindingsValid = false;
                bindingGeneration += 1;
                for (var index = 0; index < playerBindings.Count; index += 1)
                {
                    playerBindings[index]?.Clear();
                }

                playerBindings.Clear();
                playerBindingsByKey.Clear();
            }
        }

        private void ApplyPlaybackSceneState(MatchResponse state)
        {
            if (state == null || MatchManager.Current == null || !playbackActive || isResetting)
            {
                return;
            }

            MatchManager.Current.ApplyExternalLiveState(
                state.clockMinute,
                state.homeScore,
                state.awayScore,
                string.Equals(state.phase, "fulltime", StringComparison.OrdinalIgnoreCase)
                    ? MatchStatus.Special
                    : MatchStatus.Playing);
        }

        private void ApplyPlaybackCameraPreset(MatchResponse state, bool forceSnap)
        {
            if (state == null || !playbackActive || isResetting || !GtexMatchController.CameraAdapter.IsAvailable)
            {
                return;
            }

            if (activeMatchConfig == null || activeMatchConfig.ShouldUseOriginalMatchCamera)
            {
                var originalCameraType = "Stadium";
                var originalCameraChanged = !string.Equals(GtexMatchController.CameraAdapter.CurrentCameraType, originalCameraType, StringComparison.Ordinal);
                if (originalCameraChanged)
                {
                    GtexMatchController.CameraAdapter.SwitchCamera(originalCameraType, forceSnap);
                }

                if (forceSnap || originalCameraChanged)
                {
                    cameraFocus = Vector3.zero;
                    cameraFocusVelocity = Vector3.zero;
                }

                GtexMatchController.CameraAdapter.FocusToPosition(
                    ResolvePlaybackFocusPosition(state, "stadium"),
                    forceSnap || originalCameraChanged);
                lastAppliedCameraPreset = "stadium";
                return;
            }

            var preset = string.IsNullOrWhiteSpace(state.cameraPreset) ? "broadcast" : state.cameraPreset.Trim().ToLowerInvariant();
            var cameraType = ResolveCameraTypeForPreset(preset);
            if (string.IsNullOrWhiteSpace(cameraType))
            {
                return;
            }

            var presetCameraChanged =
                !string.Equals(lastAppliedCameraPreset, preset, StringComparison.Ordinal) ||
                !string.Equals(GtexMatchController.CameraAdapter.CurrentCameraType, cameraType, StringComparison.Ordinal);
            if (presetCameraChanged)
            {
                GtexMatchController.CameraAdapter.SwitchCamera(cameraType, forceSnap);
            }

            if (forceSnap || presetCameraChanged)
            {
                cameraFocus = Vector3.zero;
                cameraFocusVelocity = Vector3.zero;
            }

            GtexMatchController.CameraAdapter.FocusToPosition(
                ResolvePlaybackFocusPosition(state, preset),
                forceSnap || presetCameraChanged);

            lastAppliedCameraPreset = preset;
        }

        private Vector3 ResolvePlaybackFocusPosition(MatchResponse state, string preset)
        {
            if (pitchSpace == null || playbackSanitizer == null)
            {
                ResolvePitchSpace();
            }

            var focus = pitchSpace != null ? pitchSpace.Center : Vector3.zero;
            if (state != null && state.ballPosition != null)
            {
                focus = ConvertPlaybackPosition(state.ballPosition, state);
            }

            if (pitchSpace == null)
            {
                return focus;
            }

            var ballVelocity =
                state != null && state.ballPosition != null
                    ? ConvertPlaybackVelocity(state.ballPosition, state)
                    : Vector3.zero;
            var holderPlayerId = ResolvePlaybackBallHolderPlayerId(state);
            Vector3? ballCarrierPosition = null;
            if (!string.IsNullOrWhiteSpace(holderPlayerId) &&
                TryResolvePlaybackPlayerPosition(state, holderPlayerId, out var resolvedCarrierPosition))
            {
                ballCarrierPosition = resolvedCarrierPosition;
            }

            Vector3? receiverPosition = null;
            var activeEvent = state != null ? state.ResolveActiveEvent() : null;
            var receiverPlayerId = activeEvent != null ? (activeEvent.secondaryPlayerId ?? string.Empty).Trim() : string.Empty;
            if (!string.IsNullOrWhiteSpace(receiverPlayerId) &&
                TryResolvePlaybackPlayerPosition(state, receiverPlayerId, out var resolvedReceiverPosition))
            {
                receiverPosition = resolvedReceiverPosition;
            }

            var pitchZones = ResolvePlaybackPitchZones();
            var holderSide = ResolvePlaybackPlayerTeamSide(state, holderPlayerId);
            if (string.IsNullOrWhiteSpace(holderSide))
            {
                holderSide = state != null ? (state.possessionSide ?? string.Empty).Trim() : string.Empty;
            }

            var attackingGoalCenter = focus;
            var inFinalThird = false;
            if (!string.IsNullOrWhiteSpace(holderSide) && pitchZones != null)
            {
                var attackingGoalSide = ResolveOpposingPitchTeamSideIndex(holderSide);
                attackingGoalCenter = pitchZones.GetGoalCenter(attackingGoalSide);
                var distanceToGoal = pitchZones.DistanceToGoalCenter(focus, attackingGoalSide);
                var finalThirdDistance = Mathf.Max(22f, pitchSpace.Length * 0.34f);
                inFinalThird =
                    pitchZones.IsInsidePenaltyArea(focus, attackingGoalSide) ||
                    distanceToGoal <= finalThirdDistance;
            }

            focus = ResolveLocalSimCameraFocus(
                focus,
                ballVelocity,
                ballCarrierPosition,
                receiverPosition,
                CollectNearbyPlaybackPlayerPositions(state, focus, 32f),
                attackingGoalCenter,
                inFinalThird);

            var normalizedPreset = (preset ?? string.Empty).Trim().ToLowerInvariant();
            var safeInsetX =
                string.Equals(normalizedPreset, "box_zoom", StringComparison.Ordinal)
                    ? Mathf.Clamp(pitchSpace.Length * 0.084f, 8.4f, 10.5f)
                    : string.Equals(normalizedPreset, "attack_push", StringComparison.Ordinal)
                        ? Mathf.Clamp(pitchSpace.Length * 0.094f, 9.2f, 11.2f)
                        : Mathf.Clamp(pitchSpace.Length * 0.106f, 10.2f, 13.2f);
            var safeInsetZ =
                string.Equals(normalizedPreset, "box_zoom", StringComparison.Ordinal)
                    ? Mathf.Clamp(pitchSpace.Width * 0.12f, 6.2f, 8.2f)
                    : string.Equals(normalizedPreset, "attack_push", StringComparison.Ordinal)
                        ? Mathf.Clamp(pitchSpace.Width * 0.136f, 6.8f, 8.8f)
                        : Mathf.Clamp(pitchSpace.Width * 0.152f, 7.6f, 9.8f);
            focus.x = Mathf.Clamp(focus.x, pitchSpace.MinX + safeInsetX, pitchSpace.MaxX - safeInsetX);
            focus.z = Mathf.Clamp(focus.z, pitchSpace.MinZ + safeInsetZ, pitchSpace.MaxZ - safeInsetZ);
            focus.y = pitchSpace.GrassY;

            var safeFocus = pitchZones != null ? pitchZones.GetSafeCameraFocusPoint(focus) : pitchSpace.ClampWorld(focus);
            safeFocus.y = pitchSpace.GrassY;
            cameraFocus = Vector3.SmoothDamp(
                cameraFocus == Vector3.zero ? safeFocus : cameraFocus,
                safeFocus,
                ref cameraFocusVelocity,
                cameraSmoothTime);
            cameraFocus.y = pitchSpace.GrassY;
            return cameraFocus;
        }

        private Vector3 ResolveLocalSimCameraFocus(
            Vector3 ballPosition,
            Vector3 ballVelocity,
            Vector3? carrierPosition,
            Vector3? receiverOrPassTarget,
            IReadOnlyList<Vector3> activePlayerPositions,
            Vector3 attackingGoalCenter,
            bool inFinalThird)
        {
            var focus = ballPosition * cameraBallWeight;
            var totalWeight = cameraBallWeight;

            if (carrierPosition.HasValue)
            {
                focus += carrierPosition.Value * cameraCarrierWeight;
                totalWeight += cameraCarrierWeight;
            }

            var cluster = Vector3.zero;
            var clusterCount = 0;
            if (activePlayerPositions != null)
            {
                for (var index = 0; index < activePlayerPositions.Count; index += 1)
                {
                    var position = activePlayerPositions[index];
                    if ((position - ballPosition).sqrMagnitude > 32f * 32f)
                    {
                        continue;
                    }

                    cluster += position;
                    clusterCount += 1;
                }
            }

            if (clusterCount > 0)
            {
                cluster /= clusterCount;
                focus += cluster * cameraClusterWeight;
                totalWeight += cameraClusterWeight;
            }

            focus /= Mathf.Max(0.001f, totalWeight);

            if (receiverOrPassTarget.HasValue)
            {
                focus = Vector3.Lerp(focus, receiverOrPassTarget.Value, 0.18f);
            }

            if (inFinalThird)
            {
                focus = Vector3.Lerp(focus, attackingGoalCenter, cameraFinalThirdGoalBias);
            }

            var lookAhead = ballVelocity;
            lookAhead.y = 0f;
            lookAhead = Vector3.ClampMagnitude(lookAhead, 8f);
            focus += lookAhead * 0.25f;

            var fromBall = focus - ballPosition;
            fromBall.y = 0f;
            if (fromBall.magnitude > cameraMaxFocusDistanceFromBall)
            {
                focus = ballPosition + fromBall.normalized * cameraMaxFocusDistanceFromBall;
                GtexRuntimeTelemetry.RegisterCameraFocusClamp();
            }

            focus.y = pitchSpace != null ? pitchSpace.GrassY : 0f;
            return focus;
        }

        private List<Vector3> CollectNearbyPlaybackPlayerPositions(MatchResponse state, Vector3 ballPosition, float radiusMeters)
        {
            var nearbyPlayers = new List<Vector3>();
            if (state == null || state.players == null)
            {
                return nearbyPlayers;
            }

            var radiusSquared = radiusMeters * radiusMeters;
            for (var index = 0; index < state.players.Length; index += 1)
            {
                var livePlayer = state.players[index];
                if (livePlayer == null ||
                    livePlayer.isBall ||
                    !livePlayer.active ||
                    string.Equals(livePlayer.role, "GK", StringComparison.OrdinalIgnoreCase))
                {
                    continue;
                }

                var position = ConvertPlaybackPosition(livePlayer, state);
                if ((position - ballPosition).sqrMagnitude <= radiusSquared)
                {
                    nearbyPlayers.Add(position);
                }
            }

            return nearbyPlayers;
        }

        private bool TryResolvePlaybackPlayerPosition(MatchResponse state, string playerId, out Vector3 position)
        {
            position = pitchSpace != null ? pitchSpace.Center : Vector3.zero;
            if (state == null || state.players == null || string.IsNullOrWhiteSpace(playerId))
            {
                return false;
            }

            var normalizedPlayerId = playerId.Trim();
            for (var index = 0; index < state.players.Length; index += 1)
            {
                var livePlayer = state.players[index];
                if (livePlayer == null || livePlayer.isBall)
                {
                    continue;
                }

                if (!string.Equals((livePlayer.playerId ?? string.Empty).Trim(), normalizedPlayerId, StringComparison.Ordinal) &&
                    !string.Equals((livePlayer.entityId ?? string.Empty).Trim(), normalizedPlayerId, StringComparison.Ordinal))
                {
                    continue;
                }

                position = ConvertPlaybackPosition(livePlayer, state);
                return true;
            }

            return false;
        }

        private string ResolvePlaybackBallHolderPlayerId(MatchResponse state)
        {
            if (state == null)
            {
                return string.Empty;
            }

            if (state.ballPosition != null && !string.IsNullOrWhiteSpace(state.ballPosition.playerId))
            {
                return state.ballPosition.playerId.Trim();
            }

            if (state.players == null)
            {
                return string.Empty;
            }

            for (var index = 0; index < state.players.Length; index += 1)
            {
                var livePlayer = state.players[index];
                if (livePlayer != null &&
                    !livePlayer.isBall &&
                    livePlayer.hasPossession &&
                    !string.IsNullOrWhiteSpace(livePlayer.playerId))
                {
                    return livePlayer.playerId.Trim();
                }
            }

            return string.Empty;
        }

        private string ResolvePlaybackPlayerTeamSide(MatchResponse state, string playerId)
        {
            if (state == null || state.players == null || string.IsNullOrWhiteSpace(playerId))
            {
                return string.Empty;
            }

            var normalizedPlayerId = playerId.Trim();
            for (var index = 0; index < state.players.Length; index += 1)
            {
                var livePlayer = state.players[index];
                if (livePlayer == null || livePlayer.isBall)
                {
                    continue;
                }

                if (string.Equals((livePlayer.playerId ?? string.Empty).Trim(), normalizedPlayerId, StringComparison.Ordinal) ||
                    string.Equals((livePlayer.entityId ?? string.Empty).Trim(), normalizedPlayerId, StringComparison.Ordinal))
                {
                    return (livePlayer.teamSide ?? string.Empty).Trim();
                }
            }

            return string.Empty;
        }

        private GtexPitchZoneHelper ResolvePlaybackPitchZones()
        {
            if (MatchManager.Current != null && MatchManager.Current.ExternalPlaybackPitchZones != null)
            {
                return MatchManager.Current.ExternalPlaybackPitchZones;
            }

            return pitchSpace != null ? new GtexPitchZoneHelper(pitchSpace) : null;
        }

        private static int ResolvePitchTeamSideIndex(string teamSide)
        {
            return string.Equals((teamSide ?? string.Empty).Trim(), "away", StringComparison.OrdinalIgnoreCase)
                ? GtexPitchZoneHelper.AwayTeamSide
                : GtexPitchZoneHelper.HomeTeamSide;
        }

        private static int ResolveOpposingPitchTeamSideIndex(string teamSide)
        {
            return ResolvePitchTeamSideIndex(teamSide) == GtexPitchZoneHelper.HomeTeamSide
                ? GtexPitchZoneHelper.AwayTeamSide
                : GtexPitchZoneHelper.HomeTeamSide;
        }

        private static string ResolveCameraTypeForPreset(string preset)
        {
            switch ((preset ?? string.Empty).Trim().ToLowerInvariant())
            {
                case "attack_push":
                case "box_zoom":
                case "goal_celebration":
                case "wide_reset":
                    return "Broadcast";
                case "assistant_flag":
                    return "Offside";
                case "broadcast":
                default:
                    return "Broadcast";
            }
        }

        private void ResetReportedSnapshot()
        {
            lastReportedMinute = -1f;
            lastReportedHomeScore = -1;
            lastReportedAwayScore = -1;
            lastReportedPhase = GtexMatchPhase.None;
        }

        private bool NeedsPlaybackBindingRefresh()
        {
            if (!playbackActive ||
                isResetting ||
                currentPlaybackState == null ||
                currentPlaybackState.players == null ||
                !GtexMatchController.MatchManagerAdapter.HasTeams)
            {
                return false;
            }

            if (!bindingsValid || playerBindings.Count == 0)
            {
                return true;
            }

            for (var index = 0; index < currentPlaybackState.players.Length; index += 1)
            {
                var player = currentPlaybackState.players[index];
                if (player == null || player.isBall)
                {
                    continue;
                }

                if (!TryResolveBoundPlayer(player, out var binding) || binding == null || !binding.IsAlive())
                {
                    return true;
                }
            }

            return false;
        }

        private void BindPlaybackPlayers()
        {
            bindingsValid = false;
            bindingGeneration += 1;
            playerBindings.Clear();
            playerBindingsByKey.Clear();

            if (!playbackActive ||
                isResetting ||
                currentPlaybackState == null ||
                !GtexMatchController.MatchManagerAdapter.HasTeams)
            {
                return;
            }

            BindPlaybackPlayersForSide(FilterPlayersBySide("home"), GtexMatchController.MatchManagerAdapter.GetHomePlayers());
            BindPlaybackPlayersForSide(FilterPlayersBySide("away"), GtexMatchController.MatchManagerAdapter.GetAwayPlayers());
            bindingsValid = playerBindings.Count > 0;
        }

        private void BindPlaybackPlayersForSide(PlayerPosition[] livePlayers, IReadOnlyList<GtexLegacyPlayerHandle> legacyPlayers)
        {
            if (livePlayers == null || legacyPlayers == null)
            {
                return;
            }

            Array.Sort(livePlayers, (left, right) =>
            {
                var shirtCompare = left.shirtNumber.CompareTo(right.shirtNumber);
                return shirtCompare != 0 ? shirtCompare : string.Compare(left.playerId, right.playerId, StringComparison.Ordinal);
            });

            var available = new List<GtexLegacyPlayerHandle>(legacyPlayers);
            available.Sort((left, right) =>
            {
                var shirtCompare = left.ShirtNumber.CompareTo(right.ShirtNumber);
                return shirtCompare != 0 ? shirtCompare : left.Position.x.CompareTo(right.Position.x);
            });

            for (var index = 0; index < livePlayers.Length && index < available.Count; index += 1)
            {
                StorePlayerBinding(livePlayers[index], available[index]);
            }
        }

        private PlayerPosition[] FilterPlayersBySide(string teamSide)
        {
            if (currentPlaybackState == null || currentPlaybackState.players == null)
            {
                return Array.Empty<PlayerPosition>();
            }

            var players = new List<PlayerPosition>();
            for (var index = 0; index < currentPlaybackState.players.Length; index += 1)
            {
                var player = currentPlaybackState.players[index];
                if (player != null &&
                    !player.isBall &&
                    string.Equals(player.teamSide, teamSide, StringComparison.OrdinalIgnoreCase))
                {
                    players.Add(player);
                }
            }

            return players.ToArray();
        }

        private void StorePlayerBinding(PlayerPosition livePlayer, GtexLegacyPlayerHandle legacyPlayer)
        {
            if (livePlayer == null || legacyPlayer == null || !legacyPlayer.IsValid)
            {
                return;
            }

            var binding = new GtexPlayerBinding
            {
                PlayerId = !string.IsNullOrWhiteSpace(livePlayer.playerId)
                    ? livePlayer.playerId.Trim()
                    : (livePlayer.entityId ?? string.Empty).Trim(),
                Handle = legacyPlayer,
                Root = legacyPlayer.UnityTransform,
                Animator = legacyPlayer.Animator,
                Rigidbody = legacyPlayer.Rigidbody,
                LegacyController = legacyPlayer.LegacyController
            };
            playerBindings.Add(binding);

            if (!string.IsNullOrWhiteSpace(livePlayer.playerId))
            {
                playerBindingsByKey["player:" + livePlayer.playerId] = binding;
            }

            if (!string.IsNullOrWhiteSpace(livePlayer.entityId))
            {
                playerBindingsByKey[livePlayer.entityId] = binding;
            }
        }

        private bool TryResolveBoundPlayer(PlayerPosition livePlayer, out GtexPlayerBinding binding)
        {
            if (livePlayer != null &&
                !string.IsNullOrWhiteSpace(livePlayer.playerId) &&
                playerBindingsByKey.TryGetValue("player:" + livePlayer.playerId, out binding))
            {
                return true;
            }

            if (livePlayer != null &&
                !string.IsNullOrWhiteSpace(livePlayer.entityId) &&
                playerBindingsByKey.TryGetValue(livePlayer.entityId, out binding))
            {
                return true;
            }

            binding = null;
            return false;
        }

        private void DrivePlaybackPlayers(float deltaTime)
        {
            if (!playbackActive || !bindingsValid || isResetting)
            {
                return;
            }

            if (currentPlaybackState == null || currentPlaybackState.players == null || playerBindings.Count == 0)
            {
                return;
            }

            for (var index = 0; index < currentPlaybackState.players.Length; index += 1)
            {
                var livePlayer = currentPlaybackState.players[index];
                if (livePlayer == null || livePlayer.isBall)
                {
                    continue;
                }

                if (!TryResolveBoundPlayer(livePlayer, out var binding) || binding == null || !binding.IsAlive())
                {
                    bindingsValid = false;
                    deadBindingBlocks += 1;
                    GtexRuntimeTelemetry.RegisterDeadBindingBlock();
                    Debug.LogWarning("[GTEX Playback] Dead binding detected at index " + index + ". Stopping playback tick until rebind.");
                    return;
                }

                ApplyPlaybackPlayerState(livePlayer, binding, false, deltaTime);
            }
        }

        private void SnapPlaybackScene()
        {
            if (!playbackActive || isResetting || currentPlaybackState == null || currentPlaybackState.players == null)
            {
                return;
            }

            for (var index = 0; index < currentPlaybackState.players.Length; index += 1)
            {
                var livePlayer = currentPlaybackState.players[index];
                if (livePlayer == null || livePlayer.isBall)
                {
                    continue;
                }

                if (!TryResolveBoundPlayer(livePlayer, out var binding) || binding == null || !binding.IsAlive())
                {
                    bindingsValid = false;
                    return;
                }

                ApplyPlaybackPlayerState(livePlayer, binding, true, 0f);
            }

            DrivePlaybackBall();
        }

        private void ApplyPlaybackPlayerState(PlayerPosition livePlayer, GtexPlayerBinding binding, bool snap, float deltaTime)
        {
            if (binding == null || !binding.IsAlive())
            {
                return;
            }

            var player = binding.Handle;
            if (player == null || !player.IsValid)
            {
                return;
            }

            var targetPosition = ConvertPlaybackPosition(livePlayer, currentPlaybackState);
            var worldVelocity = ConvertPlaybackVelocity(livePlayer, currentPlaybackState);
            var frameDelta = binding.Root != null ? targetPosition - binding.Root.position : Vector3.zero;
            frameDelta.y = 0f;
            var lookDirection = new Vector3(livePlayer.facingX, 0f, livePlayer.facingZ);
            if (lookDirection.sqrMagnitude <= 0.0001f)
            {
                lookDirection = worldVelocity.sqrMagnitude > 0.01f
                    ? worldVelocity
                    : string.Equals(livePlayer.teamSide, "home", StringComparison.OrdinalIgnoreCase)
                        ? Vector3.right
                        : Vector3.left;
            }

            lookDirection.y = 0f;
            var targetRotation = lookDirection.sqrMagnitude > 0.0001f
                ? Quaternion.LookRotation(lookDirection.normalized, Vector3.up)
                : player.Rotation;

            player.SetExternalPlaybackPose(targetPosition, targetRotation, snap);

            var effectiveDeltaTime = Mathf.Max(deltaTime, AnimatorDeltaFloorSeconds);
            var actualPlanarVelocity = snap ? Vector3.zero : frameDelta / effectiveDeltaTime;
            var intendedPlanarVelocity = new Vector3(worldVelocity.x, 0f, worldVelocity.z);
            var actualPlanarSpeed = actualPlanarVelocity.magnitude;
            var intendedPlanarSpeed = intendedPlanarVelocity.magnitude;
            var animationState = ((livePlayer.animationState ?? string.Empty).Trim().ToLowerInvariant());
            var phase = ((currentPlaybackState != null ? currentPlaybackState.phase : string.Empty) ?? string.Empty).Trim().ToLowerInvariant();
            var phaseSettled = phase == "halftime" || phase == "fulltime";
            var snapshotRequestsIdle = animationState == "idle" || animationState == "set_piece";
            var directionSource =
                actualPlanarSpeed >= 0.08f
                    ? actualPlanarVelocity
                    : intendedPlanarSpeed >= 0.08f
                        ? intendedPlanarVelocity
                        : Vector3.zero;
            var explicitIdle =
                snap ||
                phaseSettled ||
                !livePlayer.active ||
                animationState == "sent_off" ||
                animationState == "save" ||
                animationState == "celebrate" ||
                (snapshotRequestsIdle &&
                 actualPlanarSpeed < 0.04f &&
                 intendedPlanarSpeed < 0.04f &&
                 Mathf.Clamp01(livePlayer.speedRatio) < 0.08f);

            var moveSpeed = 0f;
            var horizontal = 0f;
            var vertical = 0f;
            if (!explicitIdle && directionSource.sqrMagnitude > 0.0001f)
            {
                var currentRotation = player.Rotation;
                var localDirection = Quaternion.Inverse(currentRotation) * directionSource.normalized;
                var roleSpeedCap = Mathf.Max(ResolvePlaybackRoleSpeedCap(livePlayer), 0.001f);
                var actualSpeed = Mathf.Min(actualPlanarSpeed, roleSpeedCap * 1.1f);
                var intendedSpeed = Mathf.Min(intendedPlanarSpeed, roleSpeedCap * 1.05f);
                var stateSpeed = Mathf.Clamp01(livePlayer.speedRatio) * roleSpeedCap;
                var resolvedPlanarSpeed = Mathf.Max(
                    actualSpeed,
                    Mathf.Max(
                        intendedSpeed * 0.94f,
                        stateSpeed * (livePlayer.hasPossession ? 0.92f : 0.86f)));

                if (animationState == "run")
                {
                    resolvedPlanarSpeed = Mathf.Max(resolvedPlanarSpeed, roleSpeedCap * 0.52f);
                }
                else if (animationState == "jog")
                {
                    resolvedPlanarSpeed = Mathf.Max(resolvedPlanarSpeed, roleSpeedCap * 0.28f);
                }
                else if (animationState == "dribble")
                {
                    resolvedPlanarSpeed = Mathf.Max(resolvedPlanarSpeed, roleSpeedCap * 0.32f);
                }

                if (livePlayer.hasPossession)
                {
                    resolvedPlanarSpeed = Mathf.Min(resolvedPlanarSpeed, roleSpeedCap * 0.92f);
                }

                var targetMoveSpeed = Mathf.Clamp01(resolvedPlanarSpeed / roleSpeedCap);
                moveSpeed = Mathf.Clamp(resolvedPlanarSpeed, 0.5f, roleSpeedCap * 1.08f);
                horizontal = Mathf.Clamp(localDirection.x * targetMoveSpeed, -1f, 1f);
                vertical = Mathf.Clamp(localDirection.z * targetMoveSpeed, -1f, 1f);

                var forwardDot = Vector3.Dot(player.Forward, directionSource.normalized);
                if (forwardDot < 0.18f && targetMoveSpeed > 0.24f)
                {
                    moveSpeed = Mathf.Min(moveSpeed, roleSpeedCap * 0.52f);
                    horizontal *= 0.42f;
                    vertical = Mathf.Clamp(vertical, -0.16f, 0.24f);
                }
            }

            if (explicitIdle || moveSpeed <= 0.15f)
            {
                moveSpeed = 0f;
                horizontal = 0f;
                vertical = 0f;
            }

            ApplyFilteredAnimatorState(
                binding.PlayerId,
                player,
                livePlayer.hasPossession,
                moveSpeed,
                horizontal,
                vertical,
                effectiveDeltaTime,
                snap);
        }

        private void ApplyFilteredAnimatorState(
            string bindingKey,
            GtexLegacyPlayerHandle player,
            bool hasPossession,
            float moveSpeed,
            float horizontal,
            float vertical,
            float deltaTime,
            bool snap)
        {
            if (player == null || !player.IsValid)
            {
                return;
            }

            if (snap || string.IsNullOrWhiteSpace(bindingKey))
            {
                player.ApplyExternalAnimatorState(hasPossession, moveSpeed, horizontal, vertical);
                if (!string.IsNullOrWhiteSpace(bindingKey))
                {
                    filteredAnimatorStates[bindingKey] = new FilteredAnimatorState
                    {
                        MoveSpeed = moveSpeed,
                        Horizontal = horizontal,
                        Vertical = vertical
                    };
                }

                return;
            }

            filteredAnimatorStates.TryGetValue(bindingKey, out var filteredState);
            var sharpness = moveSpeed <= 0.15f
                ? 10.5f
                : Mathf.Lerp(12f, 16f, Mathf.InverseLerp(0.5f, 6f, moveSpeed));
            var blend = 1f - Mathf.Exp(-sharpness * Mathf.Max(deltaTime, AnimatorDeltaFloorSeconds));
            filteredState.MoveSpeed = Mathf.Lerp(filteredState.MoveSpeed, moveSpeed, blend);
            filteredState.Horizontal = Mathf.Lerp(filteredState.Horizontal, horizontal, Mathf.Clamp01(blend * 0.9f));
            filteredState.Vertical = Mathf.Lerp(filteredState.Vertical, vertical, Mathf.Clamp01(blend * 0.95f));

            if (filteredState.MoveSpeed <= 0.1f)
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

        private static float ResolvePlaybackRoleSpeedCap(PlayerPosition livePlayer)
        {
            var speedRatio = livePlayer != null ? Mathf.Clamp01(livePlayer.speedRatio) : 0f;
            switch (ResolvePlaybackRoleBucket(livePlayer))
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

        private static int ResolvePlaybackRoleBucket(PlayerPosition livePlayer)
        {
            var role = ((livePlayer != null ? livePlayer.role : string.Empty) ?? string.Empty).Trim().ToUpperInvariant();
            switch (role)
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

        private void DrivePlaybackBall()
        {
            if (!playbackActive || isResetting || currentPlaybackState == null || currentPlaybackState.ballPosition == null || !GtexMatchController.BallAdapter.IsAvailable)
            {
                return;
            }

            var holder = ResolveBallHolder(currentPlaybackState.ballPosition);
            var targetPosition = ConvertPlaybackPosition(currentPlaybackState.ballPosition, currentPlaybackState);
            var targetVelocity = ConvertPlaybackVelocity(currentPlaybackState.ballPosition, currentPlaybackState);
            GtexMatchController.BallAdapter.ApplyExternalState(targetPosition, targetVelocity, holder);
        }

        private GtexLegacyPlayerHandle ResolveBallHolder(PlayerPosition ballPosition)
        {
            if (ballPosition == null || string.IsNullOrWhiteSpace(ballPosition.playerId))
            {
                return null;
            }

            playerBindingsByKey.TryGetValue("player:" + ballPosition.playerId, out var holder);
            return holder != null && holder.IsAlive() && holder.Handle != null && holder.Handle.IsValid ? holder.Handle : null;
        }

        private void ResolvePitchSpace()
        {
            pitchSpace = GtexPitchLocator.Resolve(out _);
            playbackSanitizer = new GtexPlaybackSanitizer(pitchSpace);
            if (MatchManager.Current != null)
            {
                MatchManager.Current.ConfigureExternalPlaybackPitchSpace(pitchSpace);
            }
        }

        private Vector3 ConvertPlaybackPosition(PlayerPosition livePosition, MatchResponse state)
        {
            if (livePosition == null)
            {
                return Vector3.zero;
            }

            if (pitchSpace == null || playbackSanitizer == null)
            {
                ResolvePitchSpace();
            }

            if (pitchSpace == null || playbackSanitizer == null)
            {
                return Vector3.zero;
            }

            var normalizedPosition = new Vector3(
                Mathf.InverseLerp(-ResolvePitchLengthMeters(state) * 0.5f, ResolvePitchLengthMeters(state) * 0.5f, livePosition.x),
                livePosition.y,
                Mathf.InverseLerp(-ResolvePitchWidthMeters(state) * 0.5f, ResolvePitchWidthMeters(state) * 0.5f, livePosition.z));
            var worldPosition = pitchSpace.NormalizedToWorld(normalizedPosition);
            return livePosition.isBall
                ? playbackSanitizer.SanitizeBallPosition(worldPosition)
                : playbackSanitizer.SanitizePlayerPosition(worldPosition);
        }

        private Vector3 ConvertPlaybackVelocity(PlayerPosition livePosition, MatchResponse state)
        {
            if (livePosition == null || pitchSpace == null)
            {
                return Vector3.zero;
            }

            var velocity = new Vector3(
                (livePosition.velocityX / ResolvePitchLengthMeters(state)) * pitchSpace.Length,
                livePosition.velocityY,
                (livePosition.velocityZ / ResolvePitchWidthMeters(state)) * pitchSpace.Width);
            if (!livePosition.isBall)
            {
                velocity.y = 0f;
            }

            return GtexPlaybackSanitizer.IsFinite(velocity) ? velocity : Vector3.zero;
        }

        private static float ResolvePitchLengthMeters(MatchResponse state)
        {
            return state != null ? Mathf.Max(1f, state.pitchLengthMeters) : GtexPitchSpace.DefaultLength;
        }

        private static float ResolvePitchWidthMeters(MatchResponse state)
        {
            return state != null ? Mathf.Max(1f, state.pitchWidthMeters) : GtexPitchSpace.DefaultWidth;
        }

        private bool TryBuildMatchRequest(out MatchCreateRequest matchRequest)
        {
            matchRequest = default;
            var homeTemplate = ResolveTemplateTeam(activeMatchConfig != null ? activeMatchConfig.homeTemplateTeam : null, "City");
            var awayTemplate = ResolveTemplateTeam(activeMatchConfig != null ? activeMatchConfig.awayTemplateTeam : null, "Royal");
            if (homeTemplate == null || awayTemplate == null)
            {
                Debug.LogError("[GTEX Sim Host] Failed to resolve template teams for local 3D playback.");
                return false;
            }

            matchRequest = new MatchCreateRequest(homeTemplate, awayTemplate)
            {
                dayTime = activeMatchConfig != null ? activeMatchConfig.ResolveDayTime() : DayTimes.Night,
                aiLevel = AILevel.Legendary,
                userTeam = MatchCreateRequest.UserTeam.None
            };

            if (!string.IsNullOrWhiteSpace(activeMatchConfig != null ? activeMatchConfig.homeTeamName : null))
            {
                matchRequest.homeTeam.TeamName = activeMatchConfig.homeTeamName;
            }

            if (!string.IsNullOrWhiteSpace(activeMatchConfig != null ? activeMatchConfig.awayTeamName : null))
            {
                matchRequest.awayTeam.TeamName = activeMatchConfig.awayTeamName;
            }

            return true;
        }

        private static TeamEntry ResolveTemplateTeam(string configuredName, string fallbackName)
        {
            var desiredName = string.IsNullOrWhiteSpace(configuredName) ? fallbackName : configuredName.Trim();
            var direct = Resources.Load<TeamEntry>("Database/" + desiredName);
            if (direct != null)
            {
                return direct;
            }

            var availableTeams = Resources.LoadAll<TeamEntry>("Database");
            for (var index = 0; index < availableTeams.Length; index += 1)
            {
                var candidate = availableTeams[index];
                if (candidate != null &&
                    (string.Equals(candidate.name, desiredName, StringComparison.OrdinalIgnoreCase) ||
                     string.Equals(candidate.TeamName, desiredName, StringComparison.OrdinalIgnoreCase)))
                {
                    return candidate;
                }
            }

            return null;
        }

        private static GtexMatchPhase ResolveControllerPhase(GtexSimState state)
        {
            switch (state)
            {
                case GtexSimState.Kickoff:
                    return GtexMatchPhase.Kickoff;
                case GtexSimState.FirstHalf:
                    return GtexMatchPhase.FirstHalf;
                case GtexSimState.HalfTime:
                    return GtexMatchPhase.HalfTime;
                case GtexSimState.SecondHalf:
                    return GtexMatchPhase.SecondHalf;
                case GtexSimState.FullTime:
                    return GtexMatchPhase.FullTime;
                default:
                    return GtexMatchPhase.None;
            }
        }

        private static T GetOrAddComponent<T>(GameObject host) where T : Component
        {
            var existing = host.GetComponent<T>();
            return existing != null ? existing : host.AddComponent<T>();
        }

        private static string ResolveDisplayName(string preferredName, string fallbackName, string defaultName)
        {
            if (!string.IsNullOrWhiteSpace(preferredName))
            {
                return preferredName.Trim();
            }

            if (!string.IsNullOrWhiteSpace(fallbackName))
            {
                return fallbackName.Trim();
            }

            return defaultName;
        }
    }
}
