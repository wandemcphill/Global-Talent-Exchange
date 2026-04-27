using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using FStudio.Data;
using FStudio.Database;
using FStudio.GTEX.Core;
using FStudio.GTEX.Engine;
using FStudio.GTEX.Simulation;
using FStudio.MatchEngine;
using FStudio.MatchEngine.Enums;
using FStudio.UI.MatchThemes.MatchEvents;
using SharedMatchCreateRequest = Shared.Responses.MatchCreateRequest;
using UnityEngine;
using GtexEvent = FStudio.GTEX.Event;

namespace FStudio.GTEX.VisualBridge
{
    public enum GtexOriginalVisualStartupMode
    {
        CommandDriven,
        VisualSmoke
    }

    public sealed class GtexVisualMatchDirector : MonoBehaviour
    {
        private const float SceneDependencyWaitTimeoutSeconds = 10f;
        private const float ReplayDelaySeconds = 1.25f;
        private const float RuntimeReadyTimeoutSeconds = 20f;
        private const float ScriptedReplayLaunchFallbackDelaySeconds = 8f;

        private static GtexVisualMatchDirector activeDirector;

        [SerializeField] private GtexOriginalSimAdapter originalSim;
        [SerializeField] private GtexScoreVisualBridge scoreBridge;
        [SerializeField] private GtexVisualIntentDirector intentDirector;
        [SerializeField] private bool allowStandaloneEditorAutoInitialize = false;
        [SerializeField] private bool subscribeToLiveState = true;
        [SerializeField] private bool preferBackendFeedWhenAvailable = true;
        [SerializeField] private bool logVisualCommands;
        [SerializeField] private GtexOriginalVisualStartupMode startupMode = GtexOriginalVisualStartupMode.CommandDriven;

        private readonly HashSet<string> consumedEvents = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        private GtexMatchConfig config;
        private MatchAPI liveApi;
        private Coroutine bootstrapRoutine;
        private Coroutine liveFeedRoutine;
        private Coroutine localReplayRoutine;
        private Coroutine launchReplayRoutine;
        private GtexSimEngine localSimEngine;
        private bool initializationRequested;
        private bool initialized;
        private bool bootstrappingScene;
        private bool sceneBootstrapped;
        private bool runtimeReady;
        private bool bootstrapFailed;
        private bool startLiveFeedAfterBootstrap;
        private bool startLocalSimulationAfterBootstrap;
        private bool halfEnded;
        private bool matchEnded;
        private bool liveRefreshInFlight;
        private bool scriptedReplayRequestedFromLaunch;
        private bool quitAfterReplayRequestedFromLaunch;
        private bool scriptedReplayLaunchFallbackStarted;
        private float scriptedReplayLaunchRequestedAt;
        private float lastLocalClockPublished = -1f;
        private int lastLocalHomeScore = -1;
        private int lastLocalAwayScore = -1;
        private string lastBallOwnerId = string.Empty;
        private bool scriptedReplayActive;

        public bool IsRuntimeReady => runtimeReady;
        public bool IsScriptedReplayRunning => scriptedReplayActive;

        public bool HasStartupRequest => initializationRequested || initialized;

        private void Awake()
        {
            if (activeDirector != null && activeDirector != this)
            {
                Debug.LogWarning("[GTEX VisualBridge] Duplicate original visual runtime bridge destroyed.");
                Destroy(gameObject);
                return;
            }

            activeDirector = this;
        }

        public static bool TryAutoStart(GtexMatchConfig startupConfig)
        {
            var director = UnityEngine.Object.FindFirstObjectByType<GtexVisualMatchDirector>();
            if (director == null)
            {
                Debug.LogWarning("[GTEX VisualBridge] Original visual runtime requested, but no GtexVisualMatchDirector is present.");
                return false;
            }

            if (!director.enabled)
            {
                director.enabled = true;
                Debug.Log("[GTEX VisualBridge] Enabled GtexVisualMatchDirector for runtime bootstrap.");
            }

            director.Initialize(startupConfig);
            return director.HasStartupRequest || director.IsRuntimeReady;
        }

        public void Initialize(GtexMatchConfig startupConfig)
        {
            if (!enabled)
            {
                enabled = true;
            }

            config = startupConfig ?? GtexMatchConfigLoader.Load();
            if (initialized)
            {
                Debug.Log("[GTEX VisualDirector] Initialize ignored; already initialized.");
                return;
            }

            initialized = true;
            initializationRequested = true;
            runtimeReady = false;
            sceneBootstrapped = false;
            EnsureReferences();
            EnsurePersistentRuntimeHost();
            ConfigureScriptedReplayLaunchMode();
            StopVisualFeeds();
            Debug.Log("[GTEX VisualDirector] Initialize.");
            if (bootstrapRoutine != null)
            {
                StopCoroutine(bootstrapRoutine);
            }

            bootstrapRoutine = StartCoroutine(BootstrapRuntime());
        }

        public void HandleMatchState(MatchResponse state)
        {
            if (!runtimeReady || state == null)
            {
                return;
            }

            state.Normalize();
            EnsureReferences();
            originalSim.RebuildPlayerMap(state);

            HandleCommand(new GtexVisualCommand { type = GtexVisualCommandType.SetClock, matchMinute = state.clockMinute });
            HandleCommand(new GtexVisualCommand { type = GtexVisualCommandType.SetScore, matchMinute = state.clockMinute, homeScore = state.homeScore, awayScore = state.awayScore });

            var currentBallOwner = state.ballPosition != null ? state.ballPosition.playerId ?? string.Empty : string.Empty;
            if (!string.IsNullOrWhiteSpace(currentBallOwner) &&
                !string.Equals(lastBallOwnerId, currentBallOwner, StringComparison.OrdinalIgnoreCase))
            {
                lastBallOwnerId = currentBallOwner;
                HandleCommand(new GtexVisualCommand { type = GtexVisualCommandType.AssignPossession, actorPlayerId = currentBallOwner, matchMinute = state.clockMinute });
            }

            ApplyPhaseBoundary(state.phase, state.clockMinute);

            var activeEvent = state.ResolveActiveEvent();
            if (activeEvent != null)
            {
                HandleEvent(activeEvent, state);
            }

            GtexMatchController.ReportMatchSnapshot(
                GtexRuntimeMode.OriginalVisualRuntime,
                ResolvePhase(state.phase, state.clockMinute),
                true,
                nameof(GtexVisualMatchDirector),
                state.clockMinute,
                state.homeScore,
                state.awayScore,
                activeEvent != null ? activeEvent.type : "live-state");
        }

        public void HandleEvent(GtexEvent matchEvent, MatchResponse state = null)
        {
            if (!runtimeReady || matchEvent == null)
            {
                return;
            }

            var key = ResolveEventKey(matchEvent);
            if (!string.IsNullOrWhiteSpace(key) && consumedEvents.Contains(key))
            {
                return;
            }

            if (!string.IsNullOrWhiteSpace(key))
            {
                consumedEvents.Add(key);
            }

            var command = BuildCommand(matchEvent, state);
            if (command.type != GtexVisualCommandType.None)
            {
                HandleCommand(command);
            }
        }

        public void HandleCommand(GtexVisualCommand command)
        {
            if (command == null)
            {
                return;
            }

            EnsureReferences();
            ApplyDefaultPassStyle(command);
            var pointText = command.targetWorldPosition.sqrMagnitude > 0.001f
                ? " point=" + command.targetWorldPosition.ToString("F2")
                : string.Empty;
            if (IsPassLike(command.type))
            {
                Debug.Log(
                    "[GTEX VisualBridge] Command -> " + command.type + " style=" + command.passStyle +
                    " actor=" + command.actorPlayerId +
                    " target=" + command.targetPlayerId +
                    pointText);
            }
            else
            {
                Debug.Log("[GTEX VisualBridge] Command -> " + command.type + " actor=" + command.actorPlayerId + " target=" + command.targetPlayerId + pointText + " minute=" + command.matchMinute.ToString("0.##") + " outcome=" + command.outcome);
            }

            switch (command.type)
            {
                case GtexVisualCommandType.StartMatch:
                    originalSim.StartMatch();
                    break;
                case GtexVisualCommandType.SetTeams:
                    originalSim.SetTeams(command.homeTeamName, command.awayTeamName);
                    break;
                case GtexVisualCommandType.SetClock:
                    originalSim.SetClock(command.matchMinute);
                    break;
                case GtexVisualCommandType.SetScore:
                    originalSim.SetScore(command.homeScore, command.awayScore, command.matchMinute, command.outcome);
                    break;
                case GtexVisualCommandType.AssignPossession:
                    originalSim.GiveBallTo(command.actorPlayerId);
                    break;
                case GtexVisualCommandType.CarryBall:
                    originalSim.ExecuteCarry(command.actorPlayerId, command.targetWorldPosition);
                    break;
                case GtexVisualCommandType.SupportRun:
                    originalSim.ExecuteSupportRun(command);
                    break;
                case GtexVisualCommandType.MarkPlayer:
                    originalSim.ExecuteMarkPlayer(command);
                    break;
                case GtexVisualCommandType.PressBallCarrier:
                    originalSim.ExecutePressBallCarrier(command);
                    break;
                case GtexVisualCommandType.HoldShape:
                    originalSim.ExecuteHoldShape(command);
                    break;
                case GtexVisualCommandType.CoverSpace:
                    originalSim.ExecuteCoverSpace(command);
                    break;
                case GtexVisualCommandType.Pass:
                case GtexVisualCommandType.ThroughPass:
                case GtexVisualCommandType.Cross:
                    originalSim.ExecutePass(command);
                    break;
                case GtexVisualCommandType.Shoot:
                    originalSim.ExecuteShot(command.actorPlayerId, command.targetWorldPosition, command.outcome);
                    break;
                case GtexVisualCommandType.KeeperSave:
                    originalSim.ExecuteKeeperSave(command.actorPlayerId, command.targetWorldPosition);
                    break;
                case GtexVisualCommandType.KeeperClaim:
                    originalSim.ExecuteKeeperClaim(command.actorPlayerId);
                    break;
                case GtexVisualCommandType.Goal:
                    originalSim.PlayGoal(command.teamId, command.actorPlayerId);
                    originalSim.SetScore(command.homeScore, command.awayScore, command.matchMinute, "goal");
                    break;
                case GtexVisualCommandType.Foul:
                case GtexVisualCommandType.OutOfPlay:
                    break;
                case GtexVisualCommandType.ResetKickoff:
                    originalSim.ResetKickoff();
                    break;
                case GtexVisualCommandType.EndHalf:
                    originalSim.EndHalf();
                    break;
                case GtexVisualCommandType.EndMatch:
                    originalSim.EndMatch();
                    break;
            }
        }

        [ContextMenu("GTEX/Run Scripted Visual Replay")]
        public void RunScriptedCommandReplay()
        {
            startLiveFeedAfterBootstrap = false;
            startLocalSimulationAfterBootstrap = false;
            if (launchReplayRoutine != null)
            {
                StopCoroutine(launchReplayRoutine);
                launchReplayRoutine = null;
            }

            StopLocalReplayRoutine();
            localReplayRoutine = StartCoroutine(RunScriptedVisualReplayWhenReady());
        }

        [ContextMenu("GTEX/Start Local Sim Feed")]
        public void StartLocalSimulationFeed()
        {
            startLocalSimulationAfterBootstrap = true;
            startLiveFeedAfterBootstrap = false;
            if (!runtimeReady)
            {
                Debug.LogWarning("[GTEX VisualBridge] Local sim feed requested before runtime ready.");
                return;
            }

            StartLocalSimulationFeedInternal();
        }

        [ContextMenu("GTEX/Start Live Feed")]
        public void StartLiveFeed()
        {
            startLiveFeedAfterBootstrap = true;
            startLocalSimulationAfterBootstrap = false;
            if (!runtimeReady)
            {
                Debug.LogWarning("[GTEX VisualBridge] Live feed requested before runtime ready.");
                return;
            }

            StartLiveFeedInternal();
        }

        [ContextMenu("GTEX/Stop Visual Feed")]
        public void StopVisualFeed()
        {
            startLiveFeedAfterBootstrap = false;
            startLocalSimulationAfterBootstrap = false;
            StopVisualFeeds();
        }

        private void OnEnable()
        {
            SubscribeRuntimeEventsOnly();

#if UNITY_EDITOR
            if (allowStandaloneEditorAutoInitialize &&
                !GtexRuntimeState.IsBooting &&
                !GtexRuntimeState.IsStarted)
            {
                var editorConfig = GtexMatchConfigLoader.Load(false);
                if (editorConfig != null && editorConfig.ResolveRuntimeMode() == GtexRuntimeMode.OriginalVisualRuntime)
                {
                    Debug.Log("[GTEX VisualDirector] Standalone editor auto-initialize.");
                    Initialize(editorConfig);
                }
            }
#endif
        }

        private void SubscribeRuntimeEventsOnly()
        {
            EnsureReferences();
            GtexMatchController.LiveStateObserved -= HandleLiveStateObserved;
            if (subscribeToLiveState)
            {
                GtexMatchController.LiveStateObserved += HandleLiveStateObserved;
            }
        }

        private void Update()
        {
            if (localSimEngine == null || !localSimEngine.IsRunning)
            {
                TryStartScriptedReplayLaunchFallback();
                return;
            }

            var deltaTime = Time.unscaledDeltaTime > 0f ? Time.unscaledDeltaTime : Time.deltaTime;
            localSimEngine.UpdateMatch(deltaTime);
            PublishLocalSimulationSnapshot();
            TryStartScriptedReplayLaunchFallback();
        }

        private void OnDisable()
        {
            GtexMatchController.LiveStateObserved -= HandleLiveStateObserved;
            StopVisualFeeds();
            if (launchReplayRoutine != null)
            {
                StopCoroutine(launchReplayRoutine);
                launchReplayRoutine = null;
            }

            initializationRequested = false;
            initialized = false;
            bootstrappingScene = false;
            sceneBootstrapped = false;
            runtimeReady = false;
            bootstrapFailed = false;
            MatchManager.SetGlobalCommandDrivenVisualHold(false);
            GtexRuntimeState.ResetForSceneUnload();
        }

        private void OnDestroy()
        {
            if (activeDirector == this)
            {
                activeDirector = null;
            }
        }

        private IEnumerator BootstrapRuntime()
        {
            Debug.Log("[GTEX VisualBridge] BootstrapRuntime entered.");
            bootstrapFailed = false;
            bootstrappingScene = true;
            sceneBootstrapped = false;
            runtimeReady = false;
            halfEnded = false;
            matchEnded = false;
            lastBallOwnerId = string.Empty;
            consumedEvents.Clear();

            EnsureReferences();
            GtexRuntimeFlags.SetMode(GtexBootMode.OriginalVisualRuntime, true);
            GtexScoreAuthority.Reset(ResolveHomeDisplayName(), ResolveAwayDisplayName());
            MatchManager.SetGlobalCommandDrivenVisualHold(startupMode == GtexOriginalVisualStartupMode.CommandDriven);

            yield return StartCoroutine(WaitForSceneDependencies());
            if (bootstrapFailed)
            {
                yield break;
            }

            if (!HasBootstrappedMatchScene())
            {
                if (!TryBuildMatchRequest(out var matchRequest))
                {
                    HandleBootstrapFailure("Failed to resolve template teams for original visual runtime.");
                    yield break;
                }

                yield return AwaitTask(GtexMatchController.MatchEngineLoaderAdapter.CreateMatch(matchRequest), "CreateMatch");
                if (bootstrapFailed)
                {
                    yield break;
                }

                yield return AwaitTask(
                    GtexMatchController.MatchEngineLoaderAdapter.StartMatchEngine(
                        new UpcomingMatchEvent(matchRequest),
                        false,
                        false,
                        config),
                    "StartMatchEngine");
                if (bootstrapFailed)
                {
                    yield break;
                }
            }

            originalSim.ConfigureOriginalRuntime();
            originalSim.RebuildPlayerMap();
            originalSim.SetTeams(ResolveHomeDisplayName(), ResolveAwayDisplayName());
            originalSim.SetScore(0, 0, 0f, "bootstrap");
            if (startupMode == GtexOriginalVisualStartupMode.CommandDriven)
            {
                originalSim.HoldCommandDrivenReadyState();
            }

            originalSim.FocusToBall();
            yield return StartCoroutine(WaitForOriginalVisualRuntimeReady());
            if (bootstrapFailed)
            {
                yield break;
            }

            MarkRuntimeReady();
            bootstrappingScene = false;
            bootstrapRoutine = null;

            GtexMatchController.ReportRuntimeState(
                config,
                GtexRuntimeMode.OriginalVisualRuntime,
                GtexMatchPhase.Bootstrap,
                true,
                nameof(GtexVisualMatchDirector),
                "Original visual runtime bootstrapped.");

            if (ShouldUseLiveFeed() || startLiveFeedAfterBootstrap)
            {
                StartLiveFeedInternal();
            }
            else if (startLocalSimulationAfterBootstrap)
            {
                StartLocalSimulationFeedInternal();
            }
        }

        private void MarkRuntimeReady()
        {
            sceneBootstrapped = true;
            runtimeReady = true;
            if (!GtexRuntimeState.IsStarted)
            {
                GtexRuntimeState.MarkStarted(GtexRuntimeMode.OriginalVisualRuntime, nameof(GtexVisualMatchDirector));
            }

            Debug.Log("[GTEX VisualBridge] ORIGINAL_VISUAL_RUNTIME_READY");
            if (scriptedReplayRequestedFromLaunch && launchReplayRoutine == null)
            {
                launchReplayRoutine = StartCoroutine(RunLaunchScriptedReplayAfterReady());
            }
        }

        private IEnumerator WaitForSceneDependencies()
        {
            var waitStartedAt = Time.realtimeSinceStartup;
            while (!GtexMatchController.MatchEngineLoaderAdapter.IsPlaybackSceneReady)
            {
                if (Time.realtimeSinceStartup - waitStartedAt >= SceneDependencyWaitTimeoutSeconds)
                {
                    HandleBootstrapFailure(
                        "Timed out waiting for original visual runtime scene dependencies. " +
                        GtexMatchController.MatchEngineLoaderAdapter.DescribePlaybackSceneAvailability());
                    yield break;
                }

                yield return null;
            }
        }

        private IEnumerator WaitForOriginalVisualRuntimeReady()
        {
            var waitStartedAt = Time.realtimeSinceStartup;
            var lastReason = "unknown";
            while (true)
            {
                if (originalSim != null)
                {
                    if (originalSim.IsVerificationReady(out var reason))
                    {
                        originalSim.LogRuntimeReadiness();
                        yield break;
                    }

                    lastReason = reason;
                }

                if (Time.realtimeSinceStartup - waitStartedAt >= RuntimeReadyTimeoutSeconds)
                {
                    HandleBootstrapFailure("Timed out waiting for original visual essentials. Last blocker: " + lastReason);
                    yield break;
                }

                yield return null;
            }
        }

        private IEnumerator AwaitTask(Task task, string label)
        {
            if (task == null)
            {
                HandleBootstrapFailure(label + " did not start.");
                yield break;
            }

            var waitStartedAt = Time.realtimeSinceStartup;
            while (!task.IsCompleted)
            {
                if (Time.realtimeSinceStartup - waitStartedAt >= RuntimeReadyTimeoutSeconds)
                {
                    Debug.LogWarning(
                        "[GTEX VisualBridge] " +
                        label +
                        " did not complete after " +
                        RuntimeReadyTimeoutSeconds.ToString("0.#") +
                        "s; continuing with running original visual scene.");
                    yield break;
                }

                yield return null;
            }

            if (task.IsCanceled)
            {
                HandleBootstrapFailure(label + " was cancelled.");
                yield break;
            }

            if (task.IsFaulted)
            {
                HandleBootstrapFailure(label + " failed: " + (task.Exception != null ? task.Exception.GetBaseException().Message : "Unknown failure."));
            }
        }

        private void StartLiveFeedInternal()
        {
            startLiveFeedAfterBootstrap = false;
            startLocalSimulationAfterBootstrap = false;
            if (!sceneBootstrapped)
            {
                return;
            }

            if (!ShouldUseLiveFeed())
            {
                Debug.LogWarning("[GTEX VisualBridge] Live feed requested, but matchId/baseUrl/auth bootstrap is incomplete.");
                return;
            }

            StopLocalSimulation();
            StopLocalReplayRoutine();
            if (liveFeedRoutine != null)
            {
                StopCoroutine(liveFeedRoutine);
            }

            consumedEvents.Clear();
            EnsureLiveApi();
            HandleCommand(new GtexVisualCommand { type = GtexVisualCommandType.StartMatch });
            liveFeedRoutine = StartCoroutine(LiveFeedLoop());
        }

        private IEnumerator LiveFeedLoop()
        {
            if (config == null)
            {
                yield break;
            }

            if (string.IsNullOrWhiteSpace(config.liveAccessToken) && !string.IsNullOrWhiteSpace(config.liveRefreshToken))
            {
                yield return RefreshLiveAccessToken("initial live visual feed bootstrap");
            }

            while (enabled && sceneBootstrapped && ShouldUseLiveFeed())
            {
                MatchResponse response = null;
                string error = null;
                long responseCode = 0;

                yield return liveApi.GetLiveMatch(
                    config.matchId,
                    success => response = success,
                    (message, code) =>
                    {
                        error = message;
                        responseCode = code;
                    });

                if (response != null)
                {
                    HandleMatchState(response);
                    if (IsTerminalState(response) && config.stopReconnectAfterTerminal)
                    {
                        yield break;
                    }
                }
                else
                {
                    if (responseCode == 401 && !string.IsNullOrWhiteSpace(config.liveRefreshToken))
                    {
                        yield return RefreshLiveAccessToken("401 live visual feed refresh");
                    }
                    else if (!string.IsNullOrWhiteSpace(error))
                    {
                        Debug.LogWarning("[GTEX VisualBridge] Live feed poll failed: " + error);
                    }
                }

                yield return new WaitForSecondsRealtime(Mathf.Max(0.2f, config.pollIntervalSeconds));
            }
        }

        private IEnumerator RefreshLiveAccessToken(string reason)
        {
            if (liveRefreshInFlight || liveApi == null || config == null || string.IsNullOrWhiteSpace(config.liveRefreshToken))
            {
                yield break;
            }

            liveRefreshInFlight = true;

            GtexLiveAccessGrant grant = null;
            string error = null;
            long responseCode = 0;

            yield return liveApi.RefreshLiveAccess(
                config.matchId,
                success => grant = success,
                (message, code) =>
                {
                    error = message;
                    responseCode = code;
                });

            liveRefreshInFlight = false;

            if (grant != null && grant.HasAccessToken)
            {
                config.liveAccessToken = grant.access_token;
                if (grant.HasRefreshToken)
                {
                    config.liveRefreshToken = grant.refresh_token;
                }

                Debug.Log("[GTEX VisualBridge] Refreshed live access token for original visual runtime (" + reason + ").");
                yield break;
            }

            if (!string.IsNullOrWhiteSpace(error))
            {
                Debug.LogWarning(
                    "[GTEX VisualBridge] Failed to refresh live access token for original visual runtime (" +
                    reason +
                    "). code=" +
                    responseCode +
                    " error=" +
                    error);
            }
        }

        private void StartLocalSimulationFeedInternal()
        {
            startLocalSimulationAfterBootstrap = false;
            startLiveFeedAfterBootstrap = false;
            if (!sceneBootstrapped)
            {
                return;
            }

            StopLiveFeed();
            StopLocalSimulation();
            StopLocalReplayRoutine();
            consumedEvents.Clear();

            localSimEngine = new GtexSimEngine(BuildLocalSimulationConfig());
            localSimEngine.StateChanged += HandleLocalSimulationStateChanged;
            localSimEngine.EventSystem.EventGenerated += HandleLocalSimulationEventGenerated;
            lastLocalClockPublished = -1f;
            lastLocalHomeScore = -1;
            lastLocalAwayScore = -1;
            halfEnded = false;
            matchEnded = false;
            lastBallOwnerId = string.Empty;

            GtexScoreAuthority.Reset(ResolveHomeDisplayName(), ResolveAwayDisplayName());
            originalSim.SetTeams(ResolveHomeDisplayName(), ResolveAwayDisplayName());
            originalSim.SetScore(0, 0, 0f, "Kickoff");
            HandleCommand(new GtexVisualCommand { type = GtexVisualCommandType.ResetKickoff });
            HandleCommand(new GtexVisualCommand { type = GtexVisualCommandType.StartMatch });

            localSimEngine.StartMatch();
            PublishLocalSimulationSnapshot(true, "Local simulation feed started.");

            GtexMatchController.ReportRuntimeState(
                config,
                GtexRuntimeMode.OriginalVisualRuntime,
                GtexMatchPhase.Kickoff,
                true,
                nameof(GtexVisualMatchDirector),
                "Original visual runtime local simulation feed started.");
        }

        private void HandleLocalSimulationStateChanged(GtexSimState nextState)
        {
            switch (nextState)
            {
                case GtexSimState.FirstHalf:
                    HandleCommand(new GtexVisualCommand { type = GtexVisualCommandType.StartMatch });
                    break;
                case GtexSimState.HalfTime:
                    if (!halfEnded)
                    {
                        halfEnded = true;
                        HandleCommand(new GtexVisualCommand { type = GtexVisualCommandType.EndHalf });
                    }
                    break;
                case GtexSimState.SecondHalf:
                    HandleCommand(new GtexVisualCommand { type = GtexVisualCommandType.ResetKickoff });
                    HandleCommand(new GtexVisualCommand { type = GtexVisualCommandType.StartMatch });
                    break;
                case GtexSimState.FullTime:
                    if (!matchEnded)
                    {
                        matchEnded = true;
                        HandleCommand(new GtexVisualCommand { type = GtexVisualCommandType.EndMatch });
                    }
                    break;
            }

            PublishLocalSimulationSnapshot(true, "State changed to " + nextState + ".");
        }

        private void HandleLocalSimulationEventGenerated(GtexSimEvent matchEvent)
        {
            if (matchEvent == null || !sceneBootstrapped)
            {
                return;
            }

            StopLocalReplayRoutine();
            localReplayRoutine = StartCoroutine(ReplayLocalSimulationEvent(matchEvent));
            PublishLocalSimulationSnapshot(true, matchEvent.Summary);
        }

        private IEnumerator ReplayLocalSimulationEvent(GtexSimEvent matchEvent)
        {
            EnsureReferences();
            originalSim.RebuildPlayerMap();

            var attackSide = ResolveEventTeamSide(matchEvent);
            if (!TryResolveAttackPattern(attackSide, out var actor, out var support, out var wide))
            {
                yield break;
            }

            var keeper = FindOpposingKeeper(attackSide);
            var carryTarget = ResolveAdvanceTarget(actor, attackSide, 6f, 0f);
            var throughTarget = ResolveAdvanceTarget(support ?? actor, attackSide, 12f, 1.5f);
            var crossTarget = wide != null ? ResolveAdvanceTarget(wide, attackSide, 10f, 4f) : throughTarget;
            var shotTarget = ResolveShotTarget(attackSide, actor);

            HandleCommand(new GtexVisualCommand { type = GtexVisualCommandType.AssignPossession, actorPlayerId = actor.GtexPlayerId, matchMinute = ResolveEventMinute(matchEvent) });
            yield return WaitBriefly();

            HandleCommand(new GtexVisualCommand { type = GtexVisualCommandType.CarryBall, actorPlayerId = actor.GtexPlayerId, matchMinute = ResolveEventMinute(matchEvent), targetWorldPosition = carryTarget });
            yield return WaitBriefly();

            if (support != null)
            {
                HandleCommand(new GtexVisualCommand { type = GtexVisualCommandType.Pass, actorPlayerId = actor.GtexPlayerId, targetPlayerId = support.GtexPlayerId, matchMinute = ResolveEventMinute(matchEvent), isSuccessful = true });
                actor = support;
                yield return WaitBriefly();
            }

            if (wide != null)
            {
                HandleCommand(new GtexVisualCommand { type = GtexVisualCommandType.ThroughPass, actorPlayerId = actor.GtexPlayerId, targetPlayerId = wide.GtexPlayerId, matchMinute = ResolveEventMinute(matchEvent), targetWorldPosition = throughTarget, isSuccessful = true });
                actor = wide;
                yield return WaitBriefly();

                HandleCommand(new GtexVisualCommand { type = GtexVisualCommandType.Cross, actorPlayerId = actor.GtexPlayerId, matchMinute = ResolveEventMinute(matchEvent), targetWorldPosition = crossTarget, isSuccessful = true });
                yield return WaitBriefly();
            }

            if (matchEvent is GtexGoalEvent goalEvent)
            {
                HandleCommand(new GtexVisualCommand { type = GtexVisualCommandType.Shoot, actorPlayerId = actor.GtexPlayerId, matchMinute = goalEvent.Time, targetWorldPosition = shotTarget, outcome = "goal", isSuccessful = true });
                yield return WaitBriefly();
                HandleCommand(new GtexVisualCommand { type = GtexVisualCommandType.Goal, actorPlayerId = actor.GtexPlayerId, teamId = ResolveTeamToken(attackSide), matchMinute = goalEvent.Time, homeScore = goalEvent.HomeScore, awayScore = goalEvent.AwayScore, outcome = "goal", isSuccessful = true });
                yield return WaitBriefly();
                HandleCommand(new GtexVisualCommand { type = GtexVisualCommandType.ResetKickoff, matchMinute = goalEvent.Time });
                yield break;
            }

            var missedChance = matchEvent as GtexMissedChanceEvent;
            if (missedChance != null)
            {
                HandleCommand(new GtexVisualCommand { type = GtexVisualCommandType.Shoot, actorPlayerId = actor.GtexPlayerId, matchMinute = missedChance.Time, targetWorldPosition = shotTarget, outcome = missedChance.ChanceQuality >= 0.75f ? "saved" : "missed", isSuccessful = false });
                yield return WaitBriefly();
                if (keeper != null && missedChance.ChanceQuality >= 0.55f)
                {
                    HandleCommand(new GtexVisualCommand { type = GtexVisualCommandType.KeeperSave, actorPlayerId = keeper.GtexPlayerId, matchMinute = missedChance.Time, targetWorldPosition = shotTarget, outcome = "save", isSuccessful = true });
                }
            }
        }

        private IEnumerator ScriptedReplayRoutine()
        {
            EnsureReferences();
            originalSim.ConfigureOriginalRuntime();
            originalSim.RebuildPlayerMap();

            var attackers = ResolveTeamOutfieldPlayers(GtexSimTeamSide.Home);
            var defenders = ResolveTeamOutfieldPlayers(GtexSimTeamSide.Away);
            if (attackers.Length < 3 || defenders.Length < 3)
            {
                Debug.LogWarning("[GTEX VisualBridge] Scripted replay needs at least three mapped outfield players per side.");
                yield break;
            }

            var carrier = attackers[0];
            var shortOption = attackers[1];
            var runner = attackers[2];
            var marker = defenders[0];
            var presser = defenders[1];
            var trackingDefender = defenders[2];

            HandleCommand(new GtexVisualCommand { type = GtexVisualCommandType.StartMatch });
            yield return WaitBriefly();
            HandleCommand(new GtexVisualCommand { type = GtexVisualCommandType.ResetKickoff });
            yield return WaitBriefly();
            HandleCommand(new GtexVisualCommand { type = GtexVisualCommandType.AssignPossession, actorPlayerId = carrier.GtexPlayerId });
            yield return WaitBriefly();
            HandleCommand(new GtexVisualCommand
            {
                type = GtexVisualCommandType.SupportRun,
                actorPlayerId = shortOption.GtexPlayerId,
                targetWorldPosition = originalSim.ResolveSupportPoint(shortOption.GtexPlayerId, carrier.GtexPlayerId, originalSim.GetAttackingGoalCenter(0), 0),
                duration = 1.0f,
                urgency = 0.9f
            });
            yield return WaitBriefly();
            HandleCommand(new GtexVisualCommand
            {
                type = GtexVisualCommandType.MarkPlayer,
                actorPlayerId = marker.GtexPlayerId,
                targetPlayerId = shortOption.GtexPlayerId,
                duration = 1.2f,
                urgency = 0.75f
            });
            yield return WaitBriefly();
            HandleCommand(new GtexVisualCommand
            {
                type = GtexVisualCommandType.PressBallCarrier,
                actorPlayerId = presser.GtexPlayerId,
                targetPlayerId = carrier.GtexPlayerId,
                duration = 0.8f,
                urgency = 1f
            });
            yield return WaitBriefly();
            HandleCommand(new GtexVisualCommand
            {
                type = GtexVisualCommandType.CarryBall,
                actorPlayerId = carrier.GtexPlayerId,
                targetWorldPosition = carrier.Root.position + Vector3.forward * 6f
            });
            yield return WaitBriefly();
            HandleCommand(new GtexVisualCommand
            {
                type = GtexVisualCommandType.Pass,
                actorPlayerId = carrier.GtexPlayerId,
                targetPlayerId = shortOption.GtexPlayerId,
                isSuccessful = true,
                passStyle = GtexVisualPassStyle.Ground
            });
            yield return WaitBriefly();
            var attackingGoal = originalSim.GetAttackingGoalCenter(0);
            var throughTarget = originalSim.ResolveSupportPoint(runner.GtexPlayerId, shortOption.GtexPlayerId, attackingGoal, 1);
            HandleCommand(new GtexVisualCommand
            {
                type = GtexVisualCommandType.SupportRun,
                actorPlayerId = runner.GtexPlayerId,
                targetWorldPosition = throughTarget,
                duration = 1.0f,
                urgency = 0.8f
            });
            yield return WaitBriefly();
            HandleCommand(new GtexVisualCommand
            {
                type = GtexVisualCommandType.MarkPlayer,
                actorPlayerId = trackingDefender.GtexPlayerId,
                targetPlayerId = runner.GtexPlayerId,
                duration = 1.2f,
                urgency = 0.75f
            });
            yield return WaitBriefly();
            HandleCommand(new GtexVisualCommand
            {
                type = GtexVisualCommandType.ThroughPass,
                actorPlayerId = shortOption.GtexPlayerId,
                targetPlayerId = runner.GtexPlayerId,
                targetWorldPosition = throughTarget,
                passStyle = GtexVisualPassStyle.ThroughGround
            });
            yield return WaitBriefly();
            HandleCommand(new GtexVisualCommand
            {
                type = GtexVisualCommandType.Shoot,
                actorPlayerId = runner.GtexPlayerId,
                targetWorldPosition = attackingGoal,
                outcome = "saved"
            });
            yield return WaitBriefly();
            var keeper = originalSim.PlayerMap.FindGoalkeeper("away");
            HandleCommand(new GtexVisualCommand
            {
                type = GtexVisualCommandType.KeeperSave,
                actorPlayerId = keeper != null ? keeper.GtexPlayerId : string.Empty,
                targetWorldPosition = attackingGoal
            });
            yield return WaitBriefly();
            HandleCommand(new GtexVisualCommand
            {
                type = GtexVisualCommandType.Goal,
                actorPlayerId = runner.GtexPlayerId,
                homeScore = 1,
                awayScore = 0,
                matchMinute = 12.4f
            });
            yield return WaitBriefly();
            HandleCommand(new GtexVisualCommand { type = GtexVisualCommandType.ResetKickoff });
            Debug.Log("[GTEX VisualBridge] Scripted replay complete.");
            if (quitAfterReplayRequestedFromLaunch)
            {
                StartCoroutine(QuitAfterReplay());
            }
        }

        private IEnumerator RunScriptedVisualReplayWhenReady()
        {
            var timeout = RuntimeReadyTimeoutSeconds;
            while (!runtimeReady && timeout > 0f)
            {
                timeout -= Time.deltaTime;
                yield return null;
            }

            if (!runtimeReady)
            {
                Debug.LogError("[GTEX VisualBridge] Scripted replay failed: runtime not ready.");
                localReplayRoutine = null;
                yield break;
            }

            Debug.Log("[GTEX VisualBridge] Scripted replay starting.");
            scriptedReplayActive = true;
            yield return ScriptedReplayRoutine();
            scriptedReplayActive = false;
            localReplayRoutine = null;
        }

        private IEnumerator RunLaunchScriptedReplayAfterReady()
        {
            yield return new WaitForSeconds(1f);
            launchReplayRoutine = null;
            RunScriptedCommandReplay();
        }

        private IEnumerator QuitAfterReplay()
        {
            Debug.Log("[GTEX VisualBridge] QuitAfterReplay requested; quitting after replay settle.");
            yield return new WaitForSeconds(1f);
#if UNITY_EDITOR
            UnityEditor.EditorApplication.isPlaying = false;
#else
            Application.Quit(0);
#endif
        }

        private void HandleLiveStateObserved(GtexLiveStateSignal signal)
        {
            if (signal.State != null)
            {
                HandleMatchState(signal.State);
            }
        }

        private void ApplyPhaseBoundary(string phase, float minute)
        {
            switch (NormalizePhaseToken(phase))
            {
                case "halftime":
                case "half_time":
                    if (!halfEnded)
                    {
                        halfEnded = true;
                        HandleCommand(new GtexVisualCommand { type = GtexVisualCommandType.EndHalf, matchMinute = minute });
                    }
                    break;
                case "fulltime":
                case "full_time":
                    if (!matchEnded)
                    {
                        matchEnded = true;
                        HandleCommand(new GtexVisualCommand { type = GtexVisualCommandType.EndMatch, matchMinute = minute });
                    }
                    break;
            }
        }

        private GtexVisualCommand BuildCommand(GtexEvent matchEvent, MatchResponse state)
        {
            var command = new GtexVisualCommand
            {
                eventId = matchEvent.id ?? string.Empty,
                sequence = matchEvent.sequence,
                sourceEventType = matchEvent.type ?? string.Empty,
                actorPlayerId = matchEvent.primaryPlayerId ?? string.Empty,
                targetPlayerId = matchEvent.secondaryPlayerId ?? string.Empty,
                teamId = matchEvent.teamId ?? string.Empty,
                matchMinute = state != null ? state.clockMinute : matchEvent.minute,
                homeScore = state != null ? state.homeScore : matchEvent.homeScore,
                awayScore = state != null ? state.awayScore : matchEvent.awayScore,
                targetWorldPosition = ResolveTargetPosition(matchEvent, state),
                isSuccessful = !HasFlag(matchEvent, "failed") && !HasFlag(matchEvent, "unsuccessful"),
                outcome = ResolveOutcome(matchEvent)
            };

            switch (NormalizeEventType(matchEvent.type))
            {
                case "kickoff":
                case "start":
                case "startmatch":
                    command.type = GtexVisualCommandType.StartMatch;
                    break;
                case "possession":
                case "assignpossession":
                case "ball_owner":
                    command.type = GtexVisualCommandType.AssignPossession;
                    break;
                case "carry":
                case "carryball":
                case "dribble":
                    command.type = GtexVisualCommandType.CarryBall;
                    break;
                case "supportrun":
                case "support_run":
                    command.type = GtexVisualCommandType.SupportRun;
                    break;
                case "markplayer":
                case "mark_player":
                    command.type = GtexVisualCommandType.MarkPlayer;
                    break;
                case "pressballcarrier":
                case "press_ball_carrier":
                    command.type = GtexVisualCommandType.PressBallCarrier;
                    break;
                case "holdshape":
                case "hold_shape":
                    command.type = GtexVisualCommandType.HoldShape;
                    break;
                case "coverspace":
                case "cover_space":
                    command.type = GtexVisualCommandType.CoverSpace;
                    break;
                case "pass":
                case "routine_pass":
                    command.type = GtexVisualCommandType.Pass;
                    break;
                case "throughpass":
                case "through_pass":
                    command.type = GtexVisualCommandType.ThroughPass;
                    break;
                case "cross":
                    command.type = GtexVisualCommandType.Cross;
                    break;
                case "shot":
                case "shoot":
                case "missed_chance":
                    command.type = GtexVisualCommandType.Shoot;
                    break;
                case "save":
                case "keeper_save":
                case "keepersave":
                    command.type = GtexVisualCommandType.KeeperSave;
                    break;
                case "claim":
                case "keeper_claim":
                case "keeperclaim":
                    command.type = GtexVisualCommandType.KeeperClaim;
                    break;
                case "goal":
                    command.type = GtexVisualCommandType.Goal;
                    break;
                case "foul":
                    command.type = GtexVisualCommandType.Foul;
                    break;
                case "outofplay":
                case "out_of_play":
                    command.type = GtexVisualCommandType.OutOfPlay;
                    break;
                case "resetkickoff":
                case "reset_kickoff":
                    command.type = GtexVisualCommandType.ResetKickoff;
                    break;
                case "halftime":
                case "half_time":
                case "endhalf":
                case "end_half":
                    command.type = GtexVisualCommandType.EndHalf;
                    break;
                case "fulltime":
                case "full_time":
                case "endmatch":
                case "end_match":
                    command.type = GtexVisualCommandType.EndMatch;
                    break;
                default:
                    command.type = GtexVisualCommandType.None;
                    break;
            }

            if (IsPassLike(command.type))
            {
                command.passStyle = ResolvePassStyleFromEvent(matchEvent.type, ResolvePassSubType(matchEvent));
            }
            else
            {
                ApplyDefaultPassStyle(command);
            }

            return command;
        }

        private static void ApplyDefaultPassStyle(GtexVisualCommand command)
        {
            if (command == null)
            {
                return;
            }

            switch (command.type)
            {
                case GtexVisualCommandType.Pass:
                    command.passStyle = GtexVisualPassStyle.Ground;
                    break;
                case GtexVisualCommandType.ThroughPass:
                    command.passStyle = GtexVisualPassStyle.ThroughGround;
                    break;
                case GtexVisualCommandType.Cross:
                    command.passStyle = GtexVisualPassStyle.Cross;
                    break;
            }
        }

        private void ConfigureScriptedReplayLaunchMode()
        {
            scriptedReplayRequestedFromLaunch = ResolveBoolArg(false, "scriptedReplay", "scripted-replay", "gtex-scripted-replay");
            quitAfterReplayRequestedFromLaunch = ResolveBoolArg(false, "quitAfterReplay", "quit-after-replay", "gtex-quit-after-replay");
            scriptedReplayLaunchFallbackStarted = false;
            scriptedReplayLaunchRequestedAt = Time.realtimeSinceStartup;

            if (!scriptedReplayRequestedFromLaunch)
            {
                return;
            }

            ApplyCleanCaptureSettings();
            Debug.Log(
                "[GTEX VisualBridge] Scripted replay launch flag detected. " +
                "quitAfterReplay=" + quitAfterReplayRequestedFromLaunch + ".");
        }

        private void TryStartScriptedReplayLaunchFallback()
        {
            if (!scriptedReplayRequestedFromLaunch ||
                runtimeReady ||
                bootstrapFailed ||
                scriptedReplayLaunchFallbackStarted ||
                Time.realtimeSinceStartup - scriptedReplayLaunchRequestedAt < ScriptedReplayLaunchFallbackDelaySeconds)
            {
                return;
            }

            scriptedReplayLaunchFallbackStarted = true;
            if (bootstrapRoutine != null)
            {
                StopCoroutine(bootstrapRoutine);
                bootstrapRoutine = null;
            }

            Debug.LogWarning("[GTEX VisualBridge] Scripted replay launch fallback starting original runtime readiness probe.");
            bootstrapRoutine = StartCoroutine(BootstrapScriptedReplayFromRunningOriginalScene());
        }

        private IEnumerator BootstrapScriptedReplayFromRunningOriginalScene()
        {
            bootstrapFailed = false;
            bootstrappingScene = true;
            runtimeReady = false;

            EnsureReferences();
            GtexRuntimeFlags.SetMode(GtexBootMode.OriginalVisualRuntime, true);
            GtexScoreAuthority.Reset(ResolveHomeDisplayName(), ResolveAwayDisplayName());
            MatchManager.SetGlobalCommandDrivenVisualHold(startupMode == GtexOriginalVisualStartupMode.CommandDriven);

            originalSim.ConfigureOriginalRuntime();
            originalSim.SetTeams(ResolveHomeDisplayName(), ResolveAwayDisplayName());
            originalSim.SetScore(0, 0, 0f, "scripted-replay-bootstrap");

            var deadline = Time.realtimeSinceStartup + RuntimeReadyTimeoutSeconds;
            var lastReason = "unknown";
            while (Time.realtimeSinceStartup < deadline)
            {
                originalSim.RebuildPlayerMap();
                if (startupMode == GtexOriginalVisualStartupMode.CommandDriven)
                {
                    originalSim.HoldCommandDrivenReadyState();
                }

                originalSim.FocusToBall();
                if (originalSim.IsVerificationReady(out var reason))
                {
                    originalSim.LogRuntimeReadiness();
                    MarkRuntimeReady();
                    bootstrappingScene = false;
                    bootstrapRoutine = null;
                    yield break;
                }

                lastReason = reason;
                yield return new WaitForSeconds(0.5f);
            }

            HandleBootstrapFailure("Scripted replay launch fallback timed out waiting for original visual essentials. Last blocker: " + lastReason);
        }

        private static void ApplyCleanCaptureSettings()
        {
            if (Application.isBatchMode)
            {
                return;
            }

            Cursor.visible = false;
            Cursor.lockState = CursorLockMode.None;

            if (Application.isEditor)
            {
                return;
            }

            var width = ResolveIntArg(1280, "captureWidth", "capture-width", "screenWidth", "screen-width");
            var height = ResolveIntArg(720, "captureHeight", "capture-height", "screenHeight", "screen-height");
            Screen.SetResolution(Mathf.Max(640, width), Mathf.Max(360, height), FullScreenMode.Windowed);
        }

        private static bool ResolveBoolArg(bool defaultValue, params string[] names)
        {
            var value = ResolveRawArgValue(names, out var found);
            if (!found)
            {
                return defaultValue;
            }

            if (string.IsNullOrWhiteSpace(value))
            {
                return true;
            }

            switch (value.Trim().TrimStart('-', '/').ToLowerInvariant())
            {
                case "1":
                case "true":
                case "yes":
                case "on":
                    return true;
                case "0":
                case "false":
                case "no":
                case "off":
                    return false;
                default:
                    return true;
            }
        }

        private static int ResolveIntArg(int defaultValue, params string[] names)
        {
            var value = ResolveRawArgValue(names, out var found);
            return found && int.TryParse(value, out var parsed) ? parsed : defaultValue;
        }

        private static string ResolveRawArgValue(string[] names, out bool found)
        {
            found = false;
            if (names == null || names.Length == 0)
            {
                return null;
            }

            var args = Environment.GetCommandLineArgs() ?? Array.Empty<string>();
            for (var index = 0; index < args.Length; index += 1)
            {
                var token = NormalizeArg(args[index]);
                if (string.IsNullOrWhiteSpace(token))
                {
                    continue;
                }

                for (var nameIndex = 0; nameIndex < names.Length; nameIndex += 1)
                {
                    var expected = NormalizeArg(names[nameIndex]);
                    if (string.IsNullOrWhiteSpace(expected))
                    {
                        continue;
                    }

                    if (string.Equals(token, expected, StringComparison.OrdinalIgnoreCase))
                    {
                        found = true;
                        if (index + 1 < args.Length && !(args[index + 1] ?? string.Empty).TrimStart().StartsWith("-", StringComparison.Ordinal))
                        {
                            return args[index + 1];
                        }

                        return string.Empty;
                    }

                    var equalsPrefix = expected + "=";
                    if (token.StartsWith(equalsPrefix, StringComparison.OrdinalIgnoreCase))
                    {
                        found = true;
                        return token.Substring(equalsPrefix.Length);
                    }
                }
            }

            return null;
        }

        private static string NormalizeArg(string value)
        {
            return string.IsNullOrWhiteSpace(value)
                ? string.Empty
                : value.Trim().TrimStart('-', '/');
        }

        private static bool IsPassLike(GtexVisualCommandType type)
        {
            return type == GtexVisualCommandType.Pass ||
                   type == GtexVisualCommandType.ThroughPass ||
                   type == GtexVisualCommandType.Cross;
        }

        private static string ResolvePassSubType(GtexEvent matchEvent)
        {
            if (matchEvent == null)
            {
                return string.Empty;
            }

            var tokens = new List<string>();
            if (!string.IsNullOrWhiteSpace(matchEvent.playbackProfile))
            {
                tokens.Add(matchEvent.playbackProfile);
            }

            if (!string.IsNullOrWhiteSpace(matchEvent.missVariant))
            {
                tokens.Add(matchEvent.missVariant);
            }

            if (!string.IsNullOrWhiteSpace(matchEvent.scoreCommit))
            {
                tokens.Add(matchEvent.scoreCommit);
            }

            if (matchEvent.flags != null && matchEvent.flags.Length > 0)
            {
                tokens.Add(string.Join("|", matchEvent.flags));
            }

            return string.Join("|", tokens);
        }

        private static GtexVisualPassStyle ResolvePassStyleFromEvent(string eventType, string subType)
        {
            var normalizedEventType = (eventType ?? string.Empty).ToLowerInvariant();
            var normalizedSubType = (subType ?? string.Empty).ToLowerInvariant();

            if (normalizedEventType.Contains("cross") || normalizedSubType.Contains("cross"))
            {
                return GtexVisualPassStyle.Cross;
            }

            if (normalizedSubType.Contains("loft") ||
                normalizedSubType.Contains("long_ball") ||
                normalizedSubType.Contains("longball") ||
                normalizedSubType.Contains("lob"))
            {
                return GtexVisualPassStyle.Lofted;
            }

            if (normalizedEventType.Contains("through") || normalizedSubType.Contains("through"))
            {
                return GtexVisualPassStyle.ThroughGround;
            }

            return GtexVisualPassStyle.Ground;
        }

        private Vector3 ResolveTargetPosition(GtexEvent matchEvent, MatchResponse state)
        {
            var targetId = matchEvent != null ? matchEvent.secondaryPlayerId : string.Empty;
            if (!string.IsNullOrWhiteSpace(targetId) && originalSim.PlayerMap.TryGetProxy(targetId, out var proxy))
            {
                return proxy.Root.position;
            }

            if (state != null && state.ballPosition != null)
            {
                return new Vector3(state.ballPosition.x, state.ballPosition.y, state.ballPosition.z);
            }

            return Vector3.zero;
        }

        private void PublishLocalSimulationSnapshot(bool force = false, string message = null)
        {
            if (localSimEngine == null)
            {
                return;
            }

            var minute = localSimEngine.Clock.CurrentMatchMinute;
            var homeScore = localSimEngine.HomeScore;
            var awayScore = localSimEngine.AwayScore;
            if (!force &&
                Mathf.Abs(minute - lastLocalClockPublished) < 0.2f &&
                homeScore == lastLocalHomeScore &&
                awayScore == lastLocalAwayScore)
            {
                return;
            }

            lastLocalClockPublished = minute;
            lastLocalHomeScore = homeScore;
            lastLocalAwayScore = awayScore;

            HandleCommand(new GtexVisualCommand { type = GtexVisualCommandType.SetClock, matchMinute = minute });
            HandleCommand(new GtexVisualCommand { type = GtexVisualCommandType.SetScore, matchMinute = minute, homeScore = homeScore, awayScore = awayScore, outcome = message ?? "local-sim" });

            GtexMatchController.ReportMatchSnapshot(
                GtexRuntimeMode.OriginalVisualRuntime,
                ResolvePhase(localSimEngine.State),
                true,
                nameof(GtexVisualMatchDirector),
                minute,
                homeScore,
                awayScore,
                message ?? "local-sim");
        }

        private GtexSimConfig BuildLocalSimulationConfig()
        {
            return new GtexSimConfig
            {
                TargetRealDurationMinutes = config != null ? Mathf.Max(1f, config.simulationTargetDurationMinutes) : GtexSimConfig.DefaultTargetRealDurationMinutes,
                EventCheckWindowMinutes = config != null ? Mathf.Max(0.25f, config.simulationEventCheckWindowMinutes) : GtexSimConfig.DefaultEventCheckWindowMinutes,
                BaseEventChancePerWindow = config != null ? Mathf.Clamp01(config.simulationBaseEventChancePerWindow) : GtexSimConfig.DefaultEventChancePerWindow,
                RandomSeed = config != null && config.simulationRandomSeed != 0 ? config.simulationRandomSeed : GtexSimConfig.DefaultRandomSeed,
                Logger = message =>
                {
                    if (config != null && config.verboseLogging)
                    {
                        Debug.Log(message);
                    }
                }
            };
        }

        private bool TryResolveAttackPattern(GtexSimTeamSide teamSide, out GtexOriginalPlayerVisualProxy actor, out GtexOriginalPlayerVisualProxy support, out GtexOriginalPlayerVisualProxy wide)
        {
            var players = ResolveTeamOutfieldPlayers(teamSide);
            actor = players.Length > 0 ? players[0] : null;
            support = players.Length > 1 ? players[1] : null;
            wide = players.Length > 2 ? players[2] : support;
            return actor != null;
        }

        private GtexOriginalPlayerVisualProxy[] ResolveTeamOutfieldPlayers(GtexSimTeamSide teamSide)
        {
            var manager = MatchManager.Current;
            var teamId = teamSide == GtexSimTeamSide.Home
                ? manager != null && manager.GameTeam1 != null ? manager.GameTeam1.TeamId : -1
                : manager != null && manager.GameTeam2 != null ? manager.GameTeam2.TeamId : -1;

            return originalSim.PlayerMap.Proxies
                .Where(proxy => proxy != null && proxy.Player != null && !proxy.IsGoalkeeper && proxy.Player.GameTeam != null && (teamId < 0 || proxy.Player.GameTeam.TeamId == teamId))
                .OrderBy(proxy => proxy.Player.MatchPlayer != null ? proxy.Player.MatchPlayer.Number : int.MaxValue)
                .ToArray();
        }

        private GtexOriginalPlayerVisualProxy FindOpposingKeeper(GtexSimTeamSide attackingSide)
        {
            return originalSim.PlayerMap.FindGoalkeeper(attackingSide == GtexSimTeamSide.Home ? "away" : "home");
        }

        private Vector3 ResolveAdvanceTarget(GtexOriginalPlayerVisualProxy actor, GtexSimTeamSide teamSide, float forwardDistance, float lateralDistance)
        {
            if (actor == null)
            {
                return Vector3.zero;
            }

            var goal = ResolveOpposingGoal(teamSide, MatchManager.Current);
            var direction = goal - actor.Root.position;
            direction.y = 0f;
            if (direction.sqrMagnitude <= 0.001f)
            {
                direction = teamSide == GtexSimTeamSide.Home ? Vector3.right : Vector3.left;
            }

            direction.Normalize();
            var lateral = Vector3.Cross(Vector3.up, direction).normalized * lateralDistance;
            return actor.Root.position + direction * forwardDistance + lateral;
        }

        private Vector3 ResolveShotTarget(GtexSimTeamSide teamSide, GtexOriginalPlayerVisualProxy actor)
        {
            var goal = ResolveOpposingGoal(teamSide, MatchManager.Current);
            if (goal.sqrMagnitude > 0.001f)
            {
                return goal + Vector3.up * 1.1f;
            }

            return ResolveAdvanceTarget(actor, teamSide, 20f, 0f) + Vector3.up * 1.1f;
        }

        private static Vector3 ResolveOpposingGoal(GtexSimTeamSide teamSide, MatchManager manager)
        {
            if (manager == null)
            {
                return Vector3.zero;
            }

            var goal = teamSide == GtexSimTeamSide.Home ? manager.goalNet2 : manager.goalNet1;
            return goal != null ? goal.Position : Vector3.zero;
        }

        private static GtexSimTeamSide ResolveEventTeamSide(GtexSimEvent matchEvent)
        {
            switch (matchEvent)
            {
                case GtexGoalEvent goalEvent:
                    return goalEvent.ScoringTeam;
                case GtexMissedChanceEvent missedChanceEvent:
                    return missedChanceEvent.Team;
                case GtexFoulEvent foulEvent:
                    return foulEvent.Team;
                case GtexCardEvent cardEvent:
                    return cardEvent.Team;
                default:
                    return GtexSimTeamSide.Home;
            }
        }

        private static float ResolveEventMinute(GtexSimEvent matchEvent)
        {
            return matchEvent != null ? Mathf.Max(0f, matchEvent.Time) : 0f;
        }

        private static string ResolveTeamToken(GtexSimTeamSide teamSide)
        {
            return teamSide == GtexSimTeamSide.Home ? "home" : "away";
        }

        private bool HasBootstrappedMatchScene()
        {
            return MatchManager.Current != null &&
                   MatchManager.Current.GameTeam1 != null &&
                   MatchManager.Current.GameTeam2 != null;
        }

        private bool ShouldUseLiveFeed()
        {
            return preferBackendFeedWhenAvailable &&
                   config != null &&
                   !string.IsNullOrWhiteSpace(config.matchId) &&
                   !string.IsNullOrWhiteSpace(config.ResolveBaseUrl()) &&
                   config.HasLiveAuthBootstrap;
        }

        private bool TryBuildMatchRequest(out SharedMatchCreateRequest matchRequest)
        {
            matchRequest = default;
            var homeTemplate = ResolveTemplateTeam(config != null ? config.homeTemplateTeam : null, "City");
            var awayTemplate = ResolveTemplateTeam(config != null ? config.awayTemplateTeam : null, "Royal");
            if (homeTemplate == null || awayTemplate == null)
            {
                return false;
            }

            matchRequest = new SharedMatchCreateRequest(homeTemplate, awayTemplate)
            {
                dayTime = config != null ? config.ResolveDayTime() : DayTimes.Night,
                aiLevel = AILevel.Legendary,
                userTeam = SharedMatchCreateRequest.UserTeam.None
            };

            if (!string.IsNullOrWhiteSpace(config != null ? config.homeTeamName : null))
            {
                matchRequest.homeTeam.TeamName = config.homeTeamName;
            }

            if (!string.IsNullOrWhiteSpace(config != null ? config.awayTeamName : null))
            {
                matchRequest.awayTeam.TeamName = config.awayTeamName;
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

        private string ResolveHomeDisplayName()
        {
            if (!string.IsNullOrWhiteSpace(config != null ? config.homeTeamName : null))
            {
                return config.homeTeamName.Trim();
            }

            if (!string.IsNullOrWhiteSpace(config != null ? config.homeTemplateTeam : null))
            {
                return config.homeTemplateTeam.Trim();
            }

            return "Home";
        }

        private string ResolveAwayDisplayName()
        {
            if (!string.IsNullOrWhiteSpace(config != null ? config.awayTeamName : null))
            {
                return config.awayTeamName.Trim();
            }

            if (!string.IsNullOrWhiteSpace(config != null ? config.awayTemplateTeam : null))
            {
                return config.awayTemplateTeam.Trim();
            }

            return "Away";
        }

        private void EnsureLiveApi()
        {
            if (liveApi != null || config == null)
            {
                return;
            }

            liveApi = new MatchAPI(
                () => config != null ? config.ResolveBaseUrl() : string.Empty,
                () => config != null ? config.liveAccessToken : string.Empty,
                () => config != null ? config.liveRefreshToken : string.Empty,
                config.timeoutSeconds);
        }

        private void EnsureReferences()
        {
            if (originalSim == null)
            {
                originalSim = GetComponent<GtexOriginalSimAdapter>();
                if (originalSim == null)
                {
                    originalSim = gameObject.AddComponent<GtexOriginalSimAdapter>();
                }
            }

            if (scoreBridge == null)
            {
                scoreBridge = GetComponent<GtexScoreVisualBridge>();
                if (scoreBridge == null)
                {
                    scoreBridge = gameObject.AddComponent<GtexScoreVisualBridge>();
                }
            }

            if (intentDirector == null)
            {
                intentDirector = GetComponent<GtexVisualIntentDirector>();
                if (intentDirector == null)
                {
                    intentDirector = gameObject.AddComponent<GtexVisualIntentDirector>();
                }
            }

            intentDirector.Bind(this, originalSim);
        }

        private void EnsurePersistentRuntimeHost()
        {
            if (!Application.isPlaying)
            {
                return;
            }

            if (transform.parent != null)
            {
                transform.SetParent(null, true);
            }

            DontDestroyOnLoad(gameObject);
            activeDirector = this;
            Debug.Log("[GTEX VisualBridge] Runtime bridge marked persistent across original stadium scene load.");
        }

        private void StopVisualFeeds()
        {
            StopLiveFeed();
            StopLocalSimulation();
            StopLocalReplayRoutine();
            liveApi = null;
        }

        private void StopLiveFeed()
        {
            if (liveFeedRoutine != null)
            {
                StopCoroutine(liveFeedRoutine);
                liveFeedRoutine = null;
            }
        }

        private void StopLocalSimulation()
        {
            if (localSimEngine == null)
            {
                return;
            }

            localSimEngine.StateChanged -= HandleLocalSimulationStateChanged;
            localSimEngine.EventSystem.EventGenerated -= HandleLocalSimulationEventGenerated;
            localSimEngine = null;
        }

        private void StopLocalReplayRoutine()
        {
            if (localReplayRoutine != null)
            {
                StopCoroutine(localReplayRoutine);
                localReplayRoutine = null;
            }
        }

        private void HandleBootstrapFailure(string message)
        {
            bootstrapFailed = true;
            bootstrappingScene = false;
            sceneBootstrapped = false;
            runtimeReady = false;
            initialized = false;
            initializationRequested = false;
            bootstrapRoutine = null;
            MatchManager.SetGlobalCommandDrivenVisualHold(false);
            GtexRuntimeState.ResetForSceneUnload();
            Debug.LogError("[GTEX VisualBridge] " + message);
            GtexMatchController.ReportRuntimeState(
                config,
                GtexRuntimeMode.OriginalVisualRuntime,
                GtexMatchPhase.Failed,
                false,
                nameof(GtexVisualMatchDirector),
                message);
        }

        private static string ResolveEventKey(GtexEvent matchEvent)
        {
            if (!string.IsNullOrWhiteSpace(matchEvent.id))
            {
                return matchEvent.id.Trim();
            }

            if (matchEvent.sequence >= 0)
            {
                return "seq:" + matchEvent.sequence;
            }

            return (matchEvent.type ?? string.Empty) + ":" + matchEvent.minute + ":" + matchEvent.primaryPlayerId + ":" + matchEvent.secondaryPlayerId;
        }

        private static bool HasFlag(GtexEvent matchEvent, string flag)
        {
            if (matchEvent == null || matchEvent.flags == null || string.IsNullOrWhiteSpace(flag))
            {
                return false;
            }

            return matchEvent.flags.Any(candidate => string.Equals(candidate, flag, StringComparison.OrdinalIgnoreCase));
        }

        private static string ResolveOutcome(GtexEvent matchEvent)
        {
            if (matchEvent == null)
            {
                return string.Empty;
            }

            if (!string.IsNullOrWhiteSpace(matchEvent.scoreCommit))
            {
                return matchEvent.scoreCommit;
            }

            if (!string.IsNullOrWhiteSpace(matchEvent.playbackProfile))
            {
                return matchEvent.playbackProfile;
            }

            if (!string.IsNullOrWhiteSpace(matchEvent.missVariant))
            {
                return matchEvent.missVariant;
            }

            return matchEvent.type ?? string.Empty;
        }

        private static string NormalizeEventType(string value)
        {
            return string.IsNullOrWhiteSpace(value) ? string.Empty : value.Trim().ToLowerInvariant().Replace("-", "_").Replace(" ", "_");
        }

        private static string NormalizePhaseToken(string value)
        {
            return string.IsNullOrWhiteSpace(value) ? string.Empty : value.Trim().ToLowerInvariant().Replace("-", "_").Replace(" ", "_");
        }

        private static GtexMatchPhase ResolvePhase(string phase, float minute)
        {
            switch (NormalizePhaseToken(phase))
            {
                case "kickoff":
                    return GtexMatchPhase.Kickoff;
                case "firsthalf":
                case "first_half":
                    return GtexMatchPhase.FirstHalf;
                case "halftime":
                case "half_time":
                    return GtexMatchPhase.HalfTime;
                case "secondhalf":
                case "second_half":
                    return GtexMatchPhase.SecondHalf;
                case "fulltime":
                case "full_time":
                    return GtexMatchPhase.FullTime;
            }

            if (minute >= 90f)
            {
                return GtexMatchPhase.FullTime;
            }

            if (minute >= 45f)
            {
                return GtexMatchPhase.SecondHalf;
            }

            return minute <= 0.1f ? GtexMatchPhase.Kickoff : GtexMatchPhase.FirstHalf;
        }

        private static GtexMatchPhase ResolvePhase(GtexSimState state)
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

        private static bool IsTerminalState(MatchResponse response)
        {
            if (response == null)
            {
                return false;
            }

            var phase = NormalizePhaseToken(response.phase);
            var status = NormalizePhaseToken(response.status);
            return phase == "fulltime" || phase == "full_time" || status == "complete" || status == "completed" || status == "finished";
        }

        private static WaitForSeconds WaitBriefly()
        {
            return new WaitForSeconds(ReplayDelaySeconds);
        }
    }

    internal static class GtexOriginalVisualPlayerExtensions
    {
        public static bool IsGoalkeeper(this GtexOriginalPlayerVisualProxy proxy)
        {
            return proxy != null && proxy.Player != null && proxy.Player.IsGK;
        }
    }

    public sealed class GtexOriginalVisualRuntimeExecutor : IGtexMatchExecutor
    {
        public string Name => "OriginalVisualRuntimeBridge";

        public GtexRuntimeMode RuntimeMode => GtexRuntimeMode.OriginalVisualRuntime;

        public bool IsRuntimeActive()
        {
            var director = UnityEngine.Object.FindFirstObjectByType<GtexVisualMatchDirector>();
            return director != null && director.IsRuntimeReady;
        }

        public bool TryAutoStart(GtexMatchConfig config, bool allowLocalSimulationInBatchMode, Action<string> logger)
        {
            logger?.Invoke("Delegating original visual runtime startup to GtexVisualMatchDirector.");
            return GtexVisualMatchDirector.TryAutoStart(config);
        }
    }
}
