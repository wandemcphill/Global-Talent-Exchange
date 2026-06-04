using System;
using FStudio.GTEX.Core;
using FStudio.GTEX.VisualBridge;
using FStudio.Events;
using FStudio.MatchEngine.Events;
using FStudio.UI.MatchThemes.MatchEvents;
using UnityEngine;

namespace FStudio.GTEX.Engine
{
    public enum GtexEngineOwnershipMode
    {
        LegacyBootstrap,
        GtexControllerBoundary
    }

    public sealed class GtexMatchController
    {
        private const string OwnershipModeEnvVar = "GTEX_ENGINE_OWNERSHIP_MODE";
        private const string ControllerOwnershipLabel = "GtexControllerBoundary";
        private const string LegacyOwnershipLabel = "LegacyBootstrap";

        private static GtexMatchController sharedInstance;

        private readonly IGtexMatchExecutor liveExecutor;
        private readonly IGtexMatchExecutor simulationExecutor;
        private readonly IGtexMatchExecutor originalVisualRuntimeExecutor;
        private readonly GtexLegacyMatchManagerAdapter legacyMatchManagerAdapter;
        private readonly GtexLegacyMatchEngineLoaderAdapter legacyMatchEngineLoaderAdapter;
        private readonly GtexLegacyBallAdapter legacyBallAdapter;
        private readonly GtexLegacyCameraAdapter legacyCameraAdapter;
        private readonly ControllerClockSource clockSource;
        private readonly InMemoryEventStream eventStream;
        private readonly LegacyEngineEventRelay legacyEngineEventRelay;
        private event Action<GtexLiveStateSignal> liveStateObserved;
        private GtexMatchState state;

        private GtexMatchController(
            IGtexMatchExecutor liveExecutor,
            IGtexMatchExecutor simulationExecutor,
            IGtexMatchExecutor originalVisualRuntimeExecutor)
        {
            this.liveExecutor = liveExecutor ?? throw new ArgumentNullException(nameof(liveExecutor));
            this.simulationExecutor = simulationExecutor ?? throw new ArgumentNullException(nameof(simulationExecutor));
            this.originalVisualRuntimeExecutor = originalVisualRuntimeExecutor ?? throw new ArgumentNullException(nameof(originalVisualRuntimeExecutor));
            legacyMatchManagerAdapter = new GtexLegacyMatchManagerAdapter();
            legacyMatchEngineLoaderAdapter = new GtexLegacyMatchEngineLoaderAdapter();
            legacyBallAdapter = new GtexLegacyBallAdapter();
            legacyCameraAdapter = new GtexLegacyCameraAdapter();
            clockSource = new ControllerClockSource();
            eventStream = new InMemoryEventStream();
            legacyEngineEventRelay = new LegacyEngineEventRelay(this);
            state = new GtexMatchState
            {
                OwnershipBoundary = ResolveOwnershipBoundaryLabel()
            };
        }

        public static GtexMatchController Shared =>
            sharedInstance ??= new GtexMatchController(
                new GtexLegacyLiveMatchExecutor(),
                new GtexLegacySimulationExecutor(),
                new GtexOriginalVisualRuntimeExecutor());

        public static IGtexClockSource ClockSource => Shared.clockSource;

        public static IGtexEventStream EventStream => Shared.eventStream;

        public static event Action<GtexLiveStateSignal> LiveStateObserved
        {
            add => Shared.liveStateObserved += value;
            remove => Shared.liveStateObserved -= value;
        }

        public static GtexLegacyMatchManagerAdapter MatchManagerAdapter => Shared.legacyMatchManagerAdapter;

        public static GtexLegacyMatchEngineLoaderAdapter MatchEngineLoaderAdapter => Shared.legacyMatchEngineLoaderAdapter;

        public static GtexLegacyBallAdapter BallAdapter => Shared.legacyBallAdapter;

        public static GtexLegacyCameraAdapter CameraAdapter => Shared.legacyCameraAdapter;

        public static GtexMatchState CurrentState => Shared.state.Clone();

        public static void ReportRuntimeState(
            GtexMatchConfig config,
            GtexRuntimeMode runtimeMode,
            GtexMatchPhase phase,
            bool runtimeActive,
            string executorName,
            string message)
        {
            Shared.ReportRuntimeStateInternal(config, runtimeMode, phase, runtimeActive, executorName, message);
        }

        public static void ReportMatchSnapshot(
            GtexRuntimeMode runtimeMode,
            GtexMatchPhase phase,
            bool runtimeActive,
            string executorName,
            float currentMatchMinute,
            int homeScore,
            int awayScore,
            string message)
        {
            Shared.ReportMatchSnapshotInternal(
                runtimeMode,
                phase,
                runtimeActive,
                executorName,
                currentMatchMinute,
                homeScore,
                awayScore,
                message);
        }

        public static void PublishLiveState(MatchResponse state, bool isFallback)
        {
            Shared.PublishLiveStateInternal(state, isFallback);
        }

        public static GtexEngineOwnershipMode ResolveOwnershipMode()
        {
            switch ((Environment.GetEnvironmentVariable(OwnershipModeEnvVar) ?? string.Empty).Trim().ToLowerInvariant())
            {
                case "controller":
                case "gtex":
                case "gtex-controller":
                    return GtexEngineOwnershipMode.GtexControllerBoundary;
                case "legacy":
                case "legacy-bootstrap":
                case "matchmanager":
                default:
                    return GtexEngineOwnershipMode.LegacyBootstrap;
            }
        }

        public static bool TryAutoStart(GtexMatchConfig config, bool allowLocalSimulationInBatchMode = false)
        {
            if (ResolveOwnershipMode() == GtexEngineOwnershipMode.LegacyBootstrap)
            {
                return LegacyTryAutoStart(config, allowLocalSimulationInBatchMode);
            }

            return Shared.TryAutoStartInternal(config, allowLocalSimulationInBatchMode);
        }

        private bool TryAutoStartInternal(GtexMatchConfig config, bool allowLocalSimulationInBatchMode)
        {
            if (config == null)
            {
                Log("GTEX controller received a null match config.");
                UpdateState(
                    config,
                    GtexRuntimeMode.LivePlayback,
                    GtexMatchPhase.Failed,
                false,
                ControllerOwnershipLabel,
                string.Empty,
                new GtexEngineCommand(GtexEngineCommandType.AutoStartRuntime, GtexRuntimeMode.LivePlayback, "Null config."),
                "Config was null.");
                return false;
            }

            var runtimeMode = config.ResolveRuntimeMode();
            var commandType = ResolveCommandType(runtimeMode);
            var command = new GtexEngineCommand(commandType, runtimeMode, "GTEX controller auto-start requested.");

            UpdateState(
                config,
                runtimeMode,
                GtexMatchPhase.Bootstrap,
                false,
                ControllerOwnershipLabel,
                SelectExecutor(runtimeMode).Name,
                command,
                "Preparing runtime bootstrap.");
            eventStream.Publish(new GtexMatchEvent("controller-bootstrap", command.ToString(), runtimeMode, GtexMatchPhase.Bootstrap));

            if (!config.CanAutoStartSelectedRuntime)
            {
                Log("GTEX controller refused auto-start because the selected runtime is not ready.");
                UpdateState(
                    config,
                    runtimeMode,
                    GtexMatchPhase.Failed,
                    false,
                    ControllerOwnershipLabel,
                    SelectExecutor(runtimeMode).Name,
                    command,
                    "Selected runtime cannot auto-start.");
                clockSource.UpdateSnapshot(0f, false, GtexMatchPhase.Failed);
                eventStream.Publish(new GtexMatchEvent("controller-bootstrap-blocked", "Selected runtime cannot auto-start.", runtimeMode, GtexMatchPhase.Failed));
                return false;
            }

            var executor = SelectExecutor(runtimeMode);
            if (executor.IsRuntimeActive())
            {
                Log("GTEX controller detected an already active runtime for " + runtimeMode + ".");
                UpdateState(
                    config,
                    runtimeMode,
                    GtexMatchPhase.Bootstrap,
                    true,
                    ControllerOwnershipLabel,
                    executor.Name,
                    command,
                    "Runtime already active.");
                clockSource.UpdateSnapshot(0f, true, GtexMatchPhase.Bootstrap);
                eventStream.Publish(new GtexMatchEvent("controller-runtime-active", "Runtime already active.", runtimeMode, GtexMatchPhase.Bootstrap));
                return true;
            }

            var started = executor.TryAutoStart(config, allowLocalSimulationInBatchMode, Log);
            var resolvedPhase = started
                ? ResolveStartedPhase(runtimeMode)
                : GtexMatchPhase.Failed;
            var message = started
                ? "Runtime bootstrap delegated through " + executor.Name + "."
                : "Runtime bootstrap failed through " + executor.Name + ".";

            UpdateState(
                config,
                runtimeMode,
                resolvedPhase,
                started,
                ControllerOwnershipLabel,
                executor.Name,
                command,
                message);
            clockSource.UpdateSnapshot(0f, started, resolvedPhase);
            eventStream.Publish(new GtexMatchEvent(
                started ? "controller-runtime-started" : "controller-runtime-failed",
                message,
                runtimeMode,
                resolvedPhase));
            return started;
        }

        private static bool LegacyTryAutoStart(GtexMatchConfig config, bool allowLocalSimulationInBatchMode)
        {
            var resolvedConfig = config ?? GtexMatchConfigLoader.Load();
            if (resolvedConfig == null || !resolvedConfig.CanAutoStartSelectedRuntime)
            {
                return false;
            }

            var runtimeMode = resolvedConfig.ResolveRuntimeMode();
            Debug.Log("[GTEX Controller] Legacy bootstrap fallback engaged for " + runtimeMode + ".");
            Shared.eventStream.Publish(new GtexMatchEvent(
                "controller-legacy-fallback",
                "Legacy bootstrap fallback engaged.",
                runtimeMode,
                GtexMatchPhase.Bootstrap));
            Shared.state = new GtexMatchState
            {
                RuntimeMode = runtimeMode,
                Phase = GtexMatchPhase.Bootstrap,
                CanAutoStart = resolvedConfig.CanAutoStartSelectedRuntime,
                RuntimeActive = false,
                MatchId = resolvedConfig.matchId ?? string.Empty,
                BaseUrl = resolvedConfig.ResolveBaseUrl() ?? string.Empty,
                OwnershipBoundary = LegacyOwnershipLabel,
                ExecutorName = runtimeMode == GtexRuntimeMode.LivePlayback
                    ? nameof(GtexMatchRuntime)
                    : runtimeMode == GtexRuntimeMode.LocalSimulation
                        ? "GtexSimRuntimeHost"
                        : runtimeMode == GtexRuntimeMode.IllusionRuntime
                            ? "GtexIllusionRuntimeHost"
                            : nameof(GtexVisualMatchDirector),
                LastMessage = "Legacy bootstrap fallback engaged.",
                UpdatedAtUtc = DateTime.UtcNow,
                LastCommand = new GtexEngineCommand(
                    GtexEngineCommandType.UseLegacyBootstrapFallback,
                    runtimeMode,
                    "Environment forced legacy bootstrap.")
            };

            if (runtimeMode == GtexRuntimeMode.LocalSimulation)
            {
                var started = FStudio.GTEX.Simulation.GtexSimRuntimeHost.TryAutoStart(resolvedConfig, allowLocalSimulationInBatchMode);
                Shared.clockSource.UpdateSnapshot(0f, started, started ? GtexMatchPhase.Kickoff : GtexMatchPhase.Failed);
                return started;
            }

            if (runtimeMode == GtexRuntimeMode.OriginalVisualRuntime)
            {
                var started = GtexVisualMatchDirector.TryAutoStart(resolvedConfig);
                Shared.clockSource.UpdateSnapshot(0f, started, started ? GtexMatchPhase.Bootstrap : GtexMatchPhase.Failed);
                return started;
            }

            if (runtimeMode == GtexRuntimeMode.IllusionRuntime)
            {
                var started = FStudio.GTEX.Illusion.GtexIllusionRuntimeHost.TryAutoStart(resolvedConfig, allowLocalSimulationInBatchMode);
                Shared.clockSource.UpdateSnapshot(0f, started, started ? GtexMatchPhase.FirstHalf : GtexMatchPhase.Failed);
                return started;
            }

            var liveStarted = GtexMatchRuntime.TryAutoStart(resolvedConfig);
            Shared.clockSource.UpdateSnapshot(0f, liveStarted, liveStarted ? GtexMatchPhase.Bootstrap : GtexMatchPhase.Failed);
            return liveStarted;
        }

        private IGtexMatchExecutor SelectExecutor(GtexRuntimeMode runtimeMode)
        {
            switch (runtimeMode)
            {
                case GtexRuntimeMode.LocalSimulation:
                    return simulationExecutor;
                case GtexRuntimeMode.OriginalVisualRuntime:
                    return originalVisualRuntimeExecutor;
                case GtexRuntimeMode.IllusionRuntime:
                    return new FStudio.GTEX.Illusion.GtexIllusionRuntimeExecutor();
                case GtexRuntimeMode.LivePlayback:
                default:
                    return liveExecutor;
            }
        }

        private static GtexEngineCommandType ResolveCommandType(GtexRuntimeMode runtimeMode)
        {
            switch (runtimeMode)
            {
                case GtexRuntimeMode.LocalSimulation:
                    return GtexEngineCommandType.StartLocalSimulation;
                case GtexRuntimeMode.OriginalVisualRuntime:
                    return GtexEngineCommandType.StartOriginalVisualRuntime;
                case GtexRuntimeMode.IllusionRuntime:
                    return GtexEngineCommandType.StartIllusionRuntime;
                case GtexRuntimeMode.LivePlayback:
                default:
                    return GtexEngineCommandType.StartLivePlayback;
            }
        }

        private static GtexMatchPhase ResolveStartedPhase(GtexRuntimeMode runtimeMode)
        {
            if (runtimeMode == GtexRuntimeMode.LocalSimulation)
            {
                return GtexMatchPhase.Kickoff;
            }

            return runtimeMode == GtexRuntimeMode.IllusionRuntime
                ? GtexMatchPhase.FirstHalf
                : GtexMatchPhase.Bootstrap;
        }

        private void ReportRuntimeStateInternal(
            GtexMatchConfig config,
            GtexRuntimeMode runtimeMode,
            GtexMatchPhase phase,
            bool runtimeActive,
            string executorName,
            string message)
        {
            MutateState(
                snapshot =>
                {
                    ApplyConfig(snapshot, config);
                    snapshot.RuntimeMode = runtimeMode;
                    snapshot.Phase = phase;
                    snapshot.RuntimeActive = runtimeActive;
                    snapshot.OwnershipBoundary = ResolveOwnershipBoundaryLabel();
                    snapshot.ExecutorName = string.IsNullOrWhiteSpace(executorName)
                        ? snapshot.ExecutorName
                        : executorName;
                    snapshot.LastMessage = message ?? string.Empty;
                },
                ShouldClockRun(runtimeActive, phase));

            eventStream.Publish(new GtexMatchEvent(
                "controller-runtime-state",
                message ?? string.Empty,
                runtimeMode,
                phase));
        }

        private void ReportMatchSnapshotInternal(
            GtexRuntimeMode runtimeMode,
            GtexMatchPhase phase,
            bool runtimeActive,
            string executorName,
            float currentMatchMinute,
            int homeScore,
            int awayScore,
            string message)
        {
            MutateState(
                snapshot =>
                {
                    snapshot.RuntimeMode = runtimeMode;
                    snapshot.Phase = phase;
                    snapshot.RuntimeActive = runtimeActive;
                    snapshot.CurrentMatchMinute = Mathf.Max(0f, currentMatchMinute);
                    snapshot.HomeScore = Mathf.Max(0, homeScore);
                    snapshot.AwayScore = Mathf.Max(0, awayScore);
                    snapshot.OwnershipBoundary = ResolveOwnershipBoundaryLabel();
                    snapshot.ExecutorName = string.IsNullOrWhiteSpace(executorName)
                        ? snapshot.ExecutorName
                        : executorName;
                    if (!string.IsNullOrWhiteSpace(message))
                    {
                        snapshot.LastMessage = message;
                    }
                },
                ShouldClockRun(runtimeActive, phase));

            eventStream.Publish(new GtexMatchEvent(
                "controller-match-snapshot",
                message ?? string.Empty,
                runtimeMode,
                phase));
        }

        private void PublishLiveStateInternal(MatchResponse state, bool isFallback)
        {
            if (state == null)
            {
                return;
            }

            liveStateObserved?.Invoke(new GtexLiveStateSignal(state, isFallback));
        }

        private void UpdateState(
            GtexMatchConfig config,
            GtexRuntimeMode runtimeMode,
            GtexMatchPhase phase,
            bool runtimeActive,
            string ownershipBoundary,
            string executorName,
            GtexEngineCommand command,
            string message,
            float currentMatchMinute = 0f,
            int homeScore = 0,
            int awayScore = 0)
        {
            state = new GtexMatchState
            {
                RuntimeMode = runtimeMode,
                Phase = phase,
                CanAutoStart = config != null && config.CanAutoStartSelectedRuntime,
                RuntimeActive = runtimeActive,
                CurrentMatchMinute = Mathf.Max(0f, currentMatchMinute),
                HomeScore = Mathf.Max(0, homeScore),
                AwayScore = Mathf.Max(0, awayScore),
                MatchId = config != null ? config.matchId ?? string.Empty : string.Empty,
                BaseUrl = config != null ? config.ResolveBaseUrl() ?? string.Empty : string.Empty,
                OwnershipBoundary = ownershipBoundary ?? string.Empty,
                ExecutorName = executorName ?? string.Empty,
                LastMessage = message ?? string.Empty,
                UpdatedAtUtc = DateTime.UtcNow,
                LastCommand = command
            };
        }

        private void MutateState(Action<GtexMatchState> mutate, bool clockRunning)
        {
            var snapshot = state.Clone();
            mutate?.Invoke(snapshot);
            snapshot.UpdatedAtUtc = DateTime.UtcNow;
            if (string.IsNullOrWhiteSpace(snapshot.OwnershipBoundary))
            {
                snapshot.OwnershipBoundary = ResolveOwnershipBoundaryLabel();
            }

            state = snapshot;
            clockSource.UpdateSnapshot(snapshot.CurrentMatchMinute, clockRunning, snapshot.Phase);
        }

        private static string ResolveOwnershipBoundaryLabel()
        {
            return ResolveOwnershipMode() == GtexEngineOwnershipMode.GtexControllerBoundary
                ? ControllerOwnershipLabel
                : LegacyOwnershipLabel;
        }

        private static void ApplyConfig(GtexMatchState snapshot, GtexMatchConfig config)
        {
            if (snapshot == null || config == null)
            {
                return;
            }

            snapshot.CanAutoStart = config.CanAutoStartSelectedRuntime;
            snapshot.MatchId = config.matchId ?? string.Empty;
            snapshot.BaseUrl = config.ResolveBaseUrl() ?? string.Empty;
        }

        private static bool ShouldClockRun(bool runtimeActive, GtexMatchPhase phase)
        {
            return runtimeActive &&
                   phase != GtexMatchPhase.FullTime &&
                   phase != GtexMatchPhase.Failed;
        }

        private static void Log(string message)
        {
            Debug.Log("[GTEX Controller] " + message);
        }

        private sealed class ControllerClockSource : IGtexClockSource
        {
            public float CurrentMatchMinute { get; private set; }

            public GtexMatchPhase Phase { get; private set; }

            public bool IsRunning { get; private set; }

            public void UpdateSnapshot(float currentMatchMinute, bool isRunning, GtexMatchPhase phase)
            {
                CurrentMatchMinute = Mathf.Max(0f, currentMatchMinute);
                IsRunning = isRunning;
                Phase = phase;
            }
        }

        private sealed class InMemoryEventStream : IGtexEventStream
        {
            public event Action<GtexMatchEvent> EventPublished;

            public void Publish(GtexMatchEvent matchEvent)
            {
                EventPublished?.Invoke(matchEvent);
            }
        }

        private sealed class LegacyEngineEventRelay
        {
            private readonly GtexMatchController controller;

            public LegacyEngineEventRelay(GtexMatchController controller)
            {
                this.controller = controller;
                EventManager.Subscribe<FirstWhistleEvent>(HandleFirstWhistle);
                EventManager.Subscribe<FinalWhistleEvent>(HandleFinalWhistle);
                EventManager.Subscribe<RefereeShortWhistleEvent>(HandleRefereeShortWhistle);
                EventManager.Subscribe<RefereeLongWhistleEvent>(HandleRefereeLongWhistle);
                EventManager.Subscribe<RefereeLastWhistleEvent>(HandleRefereeLastWhistle);
            }

            private void HandleFirstWhistle(FirstWhistleEvent _)
            {
                Publish("legacy-first-whistle", "Legacy first-whistle event relayed.", GtexMatchPhase.FirstHalf);
            }

            private void HandleFinalWhistle(FinalWhistleEvent _)
            {
                Publish("legacy-final-whistle", "Legacy final-whistle event relayed.", GtexMatchPhase.FullTime);
            }

            private void HandleRefereeShortWhistle(RefereeShortWhistleEvent _)
            {
                Publish("legacy-referee-short-whistle", "Legacy short-whistle event relayed.", controller.state.Phase);
            }

            private void HandleRefereeLongWhistle(RefereeLongWhistleEvent _)
            {
                Publish("legacy-referee-long-whistle", "Legacy long-whistle event relayed.", controller.state.Phase);
            }

            private void HandleRefereeLastWhistle(RefereeLastWhistleEvent _)
            {
                Publish("legacy-referee-last-whistle", "Legacy last-whistle event relayed.", GtexMatchPhase.FullTime);
            }

            private void Publish(string name, string message, GtexMatchPhase phase)
            {
                controller.eventStream.Publish(new GtexMatchEvent(
                    name,
                    message,
                    controller.state.RuntimeMode,
                    phase));
            }
        }
    }
}
