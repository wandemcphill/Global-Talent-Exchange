using UnityEngine;
using FStudio.GTEX.Core;
using FStudio.GTEX.Engine;

namespace FStudio.GTEX.Simulation
{
    public sealed class GtexSimRuntimeHost : MonoBehaviour
    {
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

            var existing = Object.FindFirstObjectByType<GtexSimRuntimeHost>();
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
            if (engine == null || !engine.IsRunning)
            {
                return;
            }

            var deltaTime = useUnscaledTime ? Time.unscaledDeltaTime : Time.deltaTime;
            engine.UpdateMatch(deltaTime);
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
        }

        [ContextMenu("Start Simulation")]
        public void StartSimulation()
        {
            EnsureInitialized();

            if (engine.IsRunning)
            {
                return;
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

            activeMatchConfig = matchConfig;
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

        private void ResetReportedSnapshot()
        {
            lastReportedMinute = -1f;
            lastReportedHomeScore = -1;
            lastReportedAwayScore = -1;
            lastReportedPhase = GtexMatchPhase.None;
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
