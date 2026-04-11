using UnityEngine;

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
        private bool pendingBootstrapConsumed;

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
        }

        private void OnDestroy()
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
        }

        [ContextMenu("Stop Simulation")]
        public void StopSimulation()
        {
            if (engine == null)
            {
                return;
            }

            engine.EndMatch();
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

                engine = null;
            }
        }

        private void ApplyBootstrapConfiguration(GtexMatchConfig matchConfig, bool allowBatchMode)
        {
            runInBatchMode = allowBatchMode;
            autoStart = true;
            ApplyMatchConfig(matchConfig);
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
