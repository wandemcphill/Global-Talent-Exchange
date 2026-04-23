using System;
using System.Collections;
using System.Collections.Generic;
using System.Threading.Tasks;
using UnityEngine;
using FStudio.GTEX.Core;
using FStudio.GTEX.Engine;
using FStudio.GTEX.Playback;
using FStudio.MatchEngine;
using FStudio.MatchEngine.Enums;
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

        private static PendingBootstrap pendingBootstrap;

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

        private GtexSimEngine engine;
        private GtexMatchConfig activeMatchConfig;
        private bool pendingBootstrapConsumed;
        private float lastReportedMinute = -1f;
        private int lastReportedHomeScore = -1;
        private int lastReportedAwayScore = -1;
        private GtexMatchPhase lastReportedPhase = GtexMatchPhase.None;
        private readonly Dictionary<string, GtexLegacyPlayerHandle> playerBindings = new();
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
        private string lastAppliedCameraPreset = string.Empty;

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

                if (playbackSceneBootstrapped && playbackApplier != null)
                {
                    ApplyCurrentSpatialFrame(pendingInitialPlaybackFrame);
                    playbackApplier.Tick(deltaTime);
                }
            }

            ReportSimulationSnapshot();
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

            playerBindings.Clear();
            currentPlaybackState = null;
            playbackSceneBootstrapped = false;
            playbackSceneBootstrapping = false;
            playbackBootstrapFailed = false;
            pendingInitialPlaybackFrame = true;
            lastAppliedCameraPreset = string.Empty;
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
                !playbackSceneBootstrapped ||
                playbackApplier == null ||
                spatialSynthesizer == null ||
                engine == null)
            {
                return;
            }

            currentPlaybackState = spatialSynthesizer.SynthesizeMatchResponse(engine, activeMatchConfig, ResolveSimulationMatchId());
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
                playerBindings.Clear();
            }
        }

        private void ApplyPlaybackSceneState(MatchResponse state)
        {
            if (state == null || MatchManager.Current == null)
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
            if (state == null || !GtexMatchController.CameraAdapter.IsAvailable)
            {
                return;
            }

            var preset = string.IsNullOrWhiteSpace(state.cameraPreset) ? "broadcast" : state.cameraPreset.Trim().ToLowerInvariant();
            var cameraType = ResolveCameraTypeForPreset(preset);
            if (string.IsNullOrWhiteSpace(cameraType))
            {
                return;
            }

            if (!forceSnap &&
                string.Equals(lastAppliedCameraPreset, preset, StringComparison.Ordinal) &&
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
            if (currentPlaybackState == null || currentPlaybackState.players == null || !GtexMatchController.MatchManagerAdapter.HasTeams)
            {
                return false;
            }

            for (var index = 0; index < currentPlaybackState.players.Length; index += 1)
            {
                var player = currentPlaybackState.players[index];
                if (player == null || player.isBall)
                {
                    continue;
                }

                if (!TryGetBoundPlayer(player, out _))
                {
                    return true;
                }
            }

            return false;
        }

        private void BindPlaybackPlayers()
        {
            playerBindings.Clear();
            if (currentPlaybackState == null || !GtexMatchController.MatchManagerAdapter.HasTeams)
            {
                return;
            }

            BindPlaybackPlayersForSide(FilterPlayersBySide("home"), GtexMatchController.MatchManagerAdapter.GetHomePlayers());
            BindPlaybackPlayersForSide(FilterPlayersBySide("away"), GtexMatchController.MatchManagerAdapter.GetAwayPlayers());
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

            if (!string.IsNullOrWhiteSpace(livePlayer.playerId))
            {
                playerBindings["player:" + livePlayer.playerId] = legacyPlayer;
            }

            if (!string.IsNullOrWhiteSpace(livePlayer.entityId))
            {
                playerBindings[livePlayer.entityId] = legacyPlayer;
            }
        }

        private bool TryGetBoundPlayer(PlayerPosition livePlayer, out GtexLegacyPlayerHandle legacyPlayer)
        {
            if (livePlayer != null &&
                !string.IsNullOrWhiteSpace(livePlayer.playerId) &&
                playerBindings.TryGetValue("player:" + livePlayer.playerId, out legacyPlayer) &&
                legacyPlayer != null &&
                legacyPlayer.IsValid)
            {
                return true;
            }

            if (livePlayer != null &&
                !string.IsNullOrWhiteSpace(livePlayer.entityId) &&
                playerBindings.TryGetValue(livePlayer.entityId, out legacyPlayer) &&
                legacyPlayer != null &&
                legacyPlayer.IsValid)
            {
                return true;
            }

            legacyPlayer = null;
            return false;
        }

        private void DrivePlaybackPlayers(float deltaTime)
        {
            if (currentPlaybackState == null || currentPlaybackState.players == null)
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

                if (!TryGetBoundPlayer(livePlayer, out var player))
                {
                    continue;
                }

                ApplyPlaybackPlayerState(livePlayer, player, false, deltaTime);
            }
        }

        private void SnapPlaybackScene()
        {
            if (currentPlaybackState == null || currentPlaybackState.players == null)
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

                if (!TryGetBoundPlayer(livePlayer, out var player))
                {
                    continue;
                }

                ApplyPlaybackPlayerState(livePlayer, player, true, 0f);
            }

            DrivePlaybackBall();
        }

        private void ApplyPlaybackPlayerState(PlayerPosition livePlayer, GtexLegacyPlayerHandle player, bool snap, float deltaTime)
        {
            var targetPosition = ConvertPlaybackPosition(livePlayer, currentPlaybackState);
            var worldVelocity = ConvertPlaybackVelocity(livePlayer, currentPlaybackState);
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

            var localVelocity = player.InverseTransformDirection(new Vector3(worldVelocity.x, 0f, worldVelocity.z));
            var planarSpeed = new Vector3(worldVelocity.x, 0f, worldVelocity.z).magnitude;
            var moveSpeed = Mathf.Clamp01(planarSpeed / 7.5f);
            var horizontal = planarSpeed > 0.001f ? Mathf.Clamp(localVelocity.x / planarSpeed, -1f, 1f) : 0f;
            var vertical = planarSpeed > 0.001f ? Mathf.Clamp(localVelocity.z / planarSpeed, -1f, 1f) : 0f;
            player.ApplyExternalAnimatorState(livePlayer.hasPossession, Mathf.Max(moveSpeed, livePlayer.speedRatio), horizontal, vertical);
        }

        private void DrivePlaybackBall()
        {
            if (currentPlaybackState == null || currentPlaybackState.ballPosition == null || !GtexMatchController.BallAdapter.IsAvailable)
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

            playerBindings.TryGetValue("player:" + ballPosition.playerId, out var holder);
            return holder != null && holder.IsValid ? holder : null;
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
