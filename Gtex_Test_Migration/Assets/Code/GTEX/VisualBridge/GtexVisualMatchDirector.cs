using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using FStudio.Data;
using FStudio.Database;
using FStudio.GTEX.Core;
using FStudio.GTEX.Engine;
using FStudio.GTEX.Simulation;
using FStudio.MatchEngine;
using FStudio.MatchEngine.Balls;
using FStudio.MatchEngine.Enums;
using FStudio.UI.MatchThemes.MatchEvents;
using SharedMatchCreateRequest = Shared.Responses.MatchCreateRequest;
using UnityEngine;
using GtexEvent = FStudio.GTEX.Event;
#if UNITY_EDITOR
using UnityEditor;
#endif

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
        private const float ReplayCaptureDelaySeconds = 0.72f;
        private const float RuntimeReadyTimeoutSeconds = 20f;
        private const float ScriptedReplayLaunchFallbackDelaySeconds = 8f;
#if UNITY_EDITOR
        internal const string EditorScriptedReplayAutostartSessionKey = "GTEX.Editor.ScriptedReplayAutostart";
        internal const string EditorScriptedReplayQuitAfterSessionKey = "GTEX.Editor.ScriptedReplayQuitAfter";
        internal const string EditorScriptedReplayCaptureFramesSessionKey = "GTEX.Editor.ScriptedReplayCaptureFrames";
        internal const string EditorScriptedReplayCaptureOutputDirSessionKey = "GTEX.Editor.ScriptedReplayCaptureOutputDir";
#endif

        private static GtexVisualMatchDirector activeDirector;

        [SerializeField] private GtexOriginalSimAdapter originalSim;
        [SerializeField] private GtexScoreVisualBridge scoreBridge;
        [SerializeField] private GtexVisualIntentDirector intentDirector;
        [SerializeField] private GtexSequenceRunner sequenceRunner;
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
        private bool scriptedReplayCaptureEnabled;
        private bool scriptedReplayLaunchFallbackStarted;
        private float scriptedReplayLaunchRequestedAt;
        private string scriptedReplaySequenceId = GtexVisualSequencePatternLibrary.CentralBuildupShot;
        private float lastLocalClockPublished = -1f;
        private int lastLocalHomeScore = -1;
        private int lastLocalAwayScore = -1;
        private string lastBallOwnerId = string.Empty;
        private string scriptedReplayCaptureOutputRoot = string.Empty;
        private string scriptedReplayCaptureSessionDirectory = string.Empty;
        private string scriptedReplayCaptureManifestPath = string.Empty;
        private int scriptedReplayCaptureIndex;
        private readonly List<string> scriptedReplayCapturePaths = new List<string>();
        private bool scriptedReplayActive;
        private Coroutine manualHomeAttackRoutine;
        private bool manualHomeAttackActive;

        public bool IsRuntimeReady => runtimeReady;
        public bool IsScriptedReplayRunning => scriptedReplayActive;
        public bool ShouldSuppressAmbientIntent =>
            scriptedReplayActive ||
            scriptedReplayRequestedFromLaunch ||
            localReplayRoutine != null ||
            launchReplayRoutine != null ||
            manualHomeAttackActive ||
            manualHomeAttackRoutine != null;

        public bool HasStartupRequest => initializationRequested || initialized;

        public bool RequestAuthorityLease(string teamId, IEnumerable<string> playerUids, float durationSeconds, bool allowCrossTeam = false)
        {
            EnsureReferences();
            return GtexVisualAuthority.RequestAuthorityLease(
                teamId,
                playerUids,
                durationSeconds,
                originalSim != null ? originalSim.PlayerMap : null,
                allowCrossTeam);
        }

        public bool RefreshAuthorityLease(string teamId, IEnumerable<string> playerUids, float durationSeconds, bool allowCrossTeam = false)
        {
            EnsureReferences();
            return GtexVisualAuthority.RefreshAuthorityLease(
                teamId,
                playerUids,
                durationSeconds,
                originalSim != null ? originalSim.PlayerMap : null,
                allowCrossTeam);
        }

        public void ReleaseAuthority(string reason)
        {
            GtexVisualAuthority.ReleaseAuthority(reason);
        }

        public void ResolveCurrentVisualScore(out int homeScore, out int awayScore, out float matchMinute)
        {
            homeScore = Mathf.Max(0, lastLocalHomeScore);
            awayScore = Mathf.Max(0, lastLocalAwayScore);
            matchMinute = Mathf.Max(0f, lastLocalClockPublished);

            if (localSimEngine == null)
            {
                return;
            }

            homeScore = Mathf.Max(0, localSimEngine.HomeScore);
            awayScore = Mathf.Max(0, localSimEngine.AwayScore);
            matchMinute = localSimEngine.Clock != null
                ? Mathf.Max(0f, localSimEngine.Clock.CurrentMatchMinute)
                : matchMinute;
        }

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
            if (!ValidateCommand(command))
            {
                return;
            }

            GtexVisualAuthority.AllowCommandBallParticipants(command);

            var pointText = command.targetWorldPosition.sqrMagnitude > 0.001f
                ? " point=" + command.targetWorldPosition.ToString("F2")
                : string.Empty;
            LogCommand(command, pointText);
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

        private bool ValidateCommand(GtexVisualCommand command)
        {
            if (command == null)
            {
                return false;
            }

            GtexOriginalPlayerVisualProxy actor = null;
            GtexOriginalPlayerVisualProxy target = null;

            if (RequiresActor(command.type) || !string.IsNullOrWhiteSpace(command.actorPlayerId))
            {
                if (!TryValidateCommandPlayer(command.actorPlayerId, "actor", command.type, out actor))
                {
                    return false;
                }
            }

            if (RequiresTarget(command) || !string.IsNullOrWhiteSpace(command.targetPlayerId))
            {
                if (!TryValidateCommandPlayer(command.targetPlayerId, "target", command.type, out target))
                {
                    return false;
                }
            }

            if (!string.IsNullOrWhiteSpace(command.secondaryTargetPlayerId) &&
                !TryValidateCommandPlayer(command.secondaryTargetPlayerId, "secondaryTarget", command.type, out _))
            {
                return false;
            }

            if (!ValidateCommandTeams(command, actor, target))
            {
                return false;
            }

            if (GtexVisualAuthority.IsLeaseActive && !GtexVisualAuthority.IsPassiveCommand(command.type))
            {
                if (actor != null && !GtexVisualAuthority.IsPlayerControlled(actor.GtexPlayerId))
                {
                    Debug.LogWarning("[GTEX Authority] Command skipped outside lease: " + command.type + " actor=" + actor.GtexPlayerId);
                    return false;
                }

                if (target != null && RequiresControlledTarget(command.type) && !GtexVisualAuthority.IsPlayerControlled(target.GtexPlayerId))
                {
                    Debug.LogWarning("[GTEX Authority] Command skipped outside lease: " + command.type + " target=" + target.GtexPlayerId);
                    return false;
                }
            }

            return true;
        }

        private bool TryValidateCommandPlayer(
            string playerUid,
            string role,
            GtexVisualCommandType commandType,
            out GtexOriginalPlayerVisualProxy proxy)
        {
            proxy = null;
            if (originalSim == null || originalSim.PlayerMap == null)
            {
                Debug.LogWarning("[GTEX CMD] " + commandType + " skipped: player map missing.");
                return false;
            }

            if (!originalSim.PlayerMap.TryGetCommandProxy(playerUid, out proxy, out var reason))
            {
                Debug.LogWarning("[GTEX CMD] " + commandType + " skipped: invalid " + role + " PlayerUid '" + playerUid + "' (" + reason + ").");
                return false;
            }

            return true;
        }

        private bool ValidateCommandTeams(
            GtexVisualCommand command,
            GtexOriginalPlayerVisualProxy actor,
            GtexOriginalPlayerVisualProxy target)
        {
            if (actor == null || target == null)
            {
                return true;
            }

            var actorTeam = GtexPlayerVisualMap.ResolveTeamSide(actor.GtexPlayerId);
            var targetTeam = GtexPlayerVisualMap.ResolveTeamSide(target.GtexPlayerId);
            if (string.IsNullOrWhiteSpace(actorTeam) || string.IsNullOrWhiteSpace(targetTeam))
            {
                Debug.LogError("[GTEX CMD] " + command.type + " skipped: unable to resolve command teams.");
                return false;
            }

            if ((command.type == GtexVisualCommandType.Pass ||
                 command.type == GtexVisualCommandType.ThroughPass) &&
                !string.Equals(actorTeam, targetTeam, StringComparison.OrdinalIgnoreCase))
            {
                Debug.LogError("[GTEX CMD] " + command.type + " skipped: cross-team pass actor=" + actor.GtexPlayerId + " target=" + target.GtexPlayerId);
                return false;
            }

            if ((command.type == GtexVisualCommandType.MarkPlayer ||
                 command.type == GtexVisualCommandType.PressBallCarrier) &&
                string.Equals(actorTeam, targetTeam, StringComparison.OrdinalIgnoreCase))
            {
                Debug.LogError("[GTEX CMD] " + command.type + " skipped: defensive command requires opponent target actor=" + actor.GtexPlayerId + " target=" + target.GtexPlayerId);
                return false;
            }

            return true;
        }

        private static bool RequiresActor(GtexVisualCommandType type)
        {
            switch (type)
            {
                case GtexVisualCommandType.AssignPossession:
                case GtexVisualCommandType.CarryBall:
                case GtexVisualCommandType.SupportRun:
                case GtexVisualCommandType.MarkPlayer:
                case GtexVisualCommandType.PressBallCarrier:
                case GtexVisualCommandType.HoldShape:
                case GtexVisualCommandType.CoverSpace:
                case GtexVisualCommandType.Pass:
                case GtexVisualCommandType.ThroughPass:
                case GtexVisualCommandType.Cross:
                case GtexVisualCommandType.Shoot:
                case GtexVisualCommandType.KeeperSave:
                case GtexVisualCommandType.KeeperClaim:
                case GtexVisualCommandType.Goal:
                    return true;
                default:
                    return false;
            }
        }

        private static bool RequiresTarget(GtexVisualCommand command)
        {
            if (command == null)
            {
                return false;
            }

            switch (command.type)
            {
                case GtexVisualCommandType.MarkPlayer:
                case GtexVisualCommandType.PressBallCarrier:
                case GtexVisualCommandType.Pass:
                    return true;
                case GtexVisualCommandType.ThroughPass:
                    return command.targetWorldPosition.sqrMagnitude <= 0.001f;
                default:
                    return false;
            }
        }

        private static bool RequiresControlledTarget(GtexVisualCommandType type)
        {
            switch (type)
            {
                case GtexVisualCommandType.Pass:
                case GtexVisualCommandType.ThroughPass:
                case GtexVisualCommandType.MarkPlayer:
                case GtexVisualCommandType.PressBallCarrier:
                    return true;
                default:
                    return false;
            }
        }

        private static void LogCommand(GtexVisualCommand command, string pointText)
        {
            var targetText = string.IsNullOrWhiteSpace(command.targetPlayerId)
                ? string.Empty
                : " target=" + command.targetPlayerId;
            var styleText = IsPassLike(command.type) ? " style=" + command.passStyle : string.Empty;
            Debug.Log("[GTEX CMD] " + command.type + ": actor=" + command.actorPlayerId + targetText + styleText + pointText);
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

        [ContextMenu("GTEX/Trigger Test Sequence Home Attack")]
        public void TriggerTestSequence_HomeAttack()
        {
            if (!runtimeReady)
            {
                Debug.LogWarning("[GTEX SEQ] Home Attack rejected: original visual runtime is not ready.");
                return;
            }

            if (manualHomeAttackRoutine != null)
            {
                StopCoroutine(manualHomeAttackRoutine);
                manualHomeAttackRoutine = null;
                ReleaseAuthority("manual-home-attack-restart");
            }

            StopLocalReplayRoutine();
            manualHomeAttackRoutine = StartCoroutine(RunManualHomeAttackSequence());
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
            GtexVisualAuthority.Tick();
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

            if (manualHomeAttackRoutine != null)
            {
                StopCoroutine(manualHomeAttackRoutine);
                manualHomeAttackRoutine = null;
                manualHomeAttackActive = false;
            }

            initializationRequested = false;
            initialized = false;
            bootstrappingScene = false;
            sceneBootstrapped = false;
            runtimeReady = false;
            bootstrapFailed = false;
            MatchManager.SetGlobalCommandDrivenVisualHold(false);
            ReleaseAuthority("director-disabled");
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
            BeginScriptedReplayCaptureSession();

            if (!TryResolveScriptedReplayParticipants(
                    out var attackingSide,
                    out var carrier,
                    out var shortOption,
                    out var runner,
                    out var marker,
                    out var presser,
                    out var trackingDefender))
            {
                Debug.LogWarning("[GTEX VisualBridge] Scripted replay needs at least three mapped outfield players per side.");
                CompleteScriptedReplayCaptureSession(false, "participant_resolution_failed_before_reset");
                yield break;
            }

            yield return ExecuteScriptedReplayStep(
                new GtexVisualCommand { type = GtexVisualCommandType.StartMatch },
                "01_start_match",
                0.4f);
            yield return ExecuteScriptedReplayStep(
                new GtexVisualCommand { type = GtexVisualCommandType.ResetKickoff },
                "02_reset_kickoff",
                0.95f);

            if (!TryResolveScriptedReplayParticipants(
                    out attackingSide,
                    out carrier,
                    out shortOption,
                    out runner,
                    out marker,
                    out presser,
                    out trackingDefender))
            {
                Debug.LogWarning("[GTEX VisualBridge] Scripted replay could not resolve kickoff participants after reset.");
                CompleteScriptedReplayCaptureSession(false, "participant_resolution_failed_after_reset");
                yield break;
            }

            var attackingTeamId = ResolveTeamId(attackingSide);
            var attackingGoal = ResolveShotTarget(attackingSide, runner);
            var carryTarget = originalSim.ClampToPitch(ResolveAdvanceTarget(carrier, attackingSide, 5.5f, 1.75f));
            var shortSupportPoint = originalSim.ResolveSupportPoint(
                shortOption.GtexPlayerId,
                carrier.GtexPlayerId,
                attackingGoal,
                0);
            var throughTarget = ResolveDangerousThroughTarget(shortOption, runner, attackingSide);
            var shotCarryTarget = ResolveShotCarryTarget(runner, attackingSide);
            var keeper = FindOpposingKeeper(attackingSide);
            var controlledPlayers = new List<string>
            {
                carrier.GtexPlayerId,
                shortOption.GtexPlayerId,
                runner.GtexPlayerId,
                marker.GtexPlayerId,
                presser.GtexPlayerId,
                trackingDefender.GtexPlayerId
            };
            if (keeper != null)
            {
                controlledPlayers.Add(keeper.GtexPlayerId);
            }

            Debug.Log(
                "[GTEX VisualBridge] Scripted replay attack side=" + attackingTeamId +
                " carrier=" + carrier.GtexPlayerId +
                " short=" + shortOption.GtexPlayerId +
                " runner=" + runner.GtexPlayerId +
                " keeper=" + (keeper != null ? keeper.GtexPlayerId : "none"));

            if (!RequestAuthorityLease(attackingTeamId, controlledPlayers, 6f, allowCrossTeam: true))
            {
                CompleteScriptedReplayCaptureSession(false, "authority_lease_failed");
                yield break;
            }

            yield return ExecuteScriptedReplayStep(
                new GtexVisualCommand { type = GtexVisualCommandType.AssignPossession, actorPlayerId = carrier.GtexPlayerId },
                "03_assign_possession",
                0.55f);
            yield return ExecuteScriptedReplayStep(
                new GtexVisualCommand
                {
                    type = GtexVisualCommandType.SupportRun,
                    actorPlayerId = shortOption.GtexPlayerId,
                    targetWorldPosition = shortSupportPoint,
                    duration = 1.0f,
                    urgency = 0.9f
                },
                "04_support_run_short",
                0.72f);
            yield return ExecuteScriptedReplayStep(
                new GtexVisualCommand
                {
                    type = GtexVisualCommandType.MarkPlayer,
                    actorPlayerId = marker.GtexPlayerId,
                    targetPlayerId = shortOption.GtexPlayerId,
                    duration = 1.2f,
                    urgency = 0.75f
                },
                "05_mark_player_short",
                0.78f);
            yield return ExecuteScriptedReplayStep(
                new GtexVisualCommand
                {
                    type = GtexVisualCommandType.PressBallCarrier,
                    actorPlayerId = presser.GtexPlayerId,
                    targetPlayerId = carrier.GtexPlayerId,
                    duration = 0.8f,
                    urgency = 1f
                },
                "06_press_ball_carrier",
                0.68f);

            if (!RequestAuthorityLease(attackingTeamId, controlledPlayers, 6f, allowCrossTeam: true))
            {
                CompleteScriptedReplayCaptureSession(false, "authority_lease_failed_before_carry");
                yield break;
            }

            yield return ExecuteScriptedReplayStep(
                new GtexVisualCommand
                {
                    type = GtexVisualCommandType.CarryBall,
                    actorPlayerId = carrier.GtexPlayerId,
                    targetWorldPosition = carryTarget
                },
                "07_carry_ball",
                0.78f);
            yield return ExecuteScriptedReplayStep(
                new GtexVisualCommand
                {
                    type = GtexVisualCommandType.Pass,
                    actorPlayerId = carrier.GtexPlayerId,
                    targetPlayerId = shortOption.GtexPlayerId,
                    isSuccessful = true,
                    passStyle = GtexVisualPassStyle.Ground
                },
                "08_ground_pass_receive",
                0.82f);
            yield return ExecuteScriptedReplayStep(
                new GtexVisualCommand
                {
                    type = GtexVisualCommandType.SupportRun,
                    actorPlayerId = runner.GtexPlayerId,
                    targetWorldPosition = throughTarget,
                    duration = 1.0f,
                    urgency = 0.8f
                },
                "09_support_run_box",
                0.8f);
            yield return ExecuteScriptedReplayStep(
                new GtexVisualCommand
                {
                    type = GtexVisualCommandType.MarkPlayer,
                    actorPlayerId = trackingDefender.GtexPlayerId,
                    targetPlayerId = runner.GtexPlayerId,
                    duration = 1.2f,
                    urgency = 0.75f
                },
                "10_mark_runner",
                0.78f);

            if (!RequestAuthorityLease(attackingTeamId, controlledPlayers, 6f, allowCrossTeam: true))
            {
                CompleteScriptedReplayCaptureSession(false, "authority_lease_failed_before_final_action");
                yield break;
            }

            yield return ExecuteScriptedReplayStep(
                new GtexVisualCommand
                {
                    type = GtexVisualCommandType.ThroughPass,
                    actorPlayerId = shortOption.GtexPlayerId,
                    targetPlayerId = runner.GtexPlayerId,
                    targetWorldPosition = throughTarget,
                    passStyle = GtexVisualPassStyle.ThroughGround
                },
                "11_through_pass_receive",
                0.88f);
            yield return ExecuteScriptedReplayStep(
                new GtexVisualCommand
                {
                    type = GtexVisualCommandType.CarryBall,
                    actorPlayerId = runner.GtexPlayerId,
                    targetWorldPosition = shotCarryTarget
                },
                "12_attack_box_carry",
                0.82f);
            yield return ExecuteScriptedReplayStep(
                new GtexVisualCommand
                {
                    type = GtexVisualCommandType.Shoot,
                    actorPlayerId = runner.GtexPlayerId,
                    targetWorldPosition = attackingGoal,
                    outcome = "saved"
                },
                "13_shot",
                0.82f);
            yield return ExecuteScriptedReplayStep(
                new GtexVisualCommand
                {
                    type = GtexVisualCommandType.KeeperSave,
                    actorPlayerId = keeper != null ? keeper.GtexPlayerId : string.Empty,
                    targetWorldPosition = attackingGoal
                },
                "14_keeper_save",
                0.82f);
            ReleaseAuthority("completed");
            yield return ExecuteScriptedReplayStep(
                new GtexVisualCommand { type = GtexVisualCommandType.ResetKickoff },
                "15_reset_kickoff",
                0.95f);
            Debug.Log("[GTEX VisualBridge] Scripted replay complete with keeper-save ending.");
            CompleteScriptedReplayCaptureSession(true, "scripted_replay_complete");
            if (quitAfterReplayRequestedFromLaunch)
            {
                StartCoroutine(QuitAfterReplay());
            }
        }

        private IEnumerator RunManualHomeAttackSequence()
        {
            manualHomeAttackActive = true;
            Debug.Log("[GTEX SEQ] Start Home Attack");

            EnsureReferences();
            originalSim.ConfigureOriginalRuntime();
            originalSim.RebuildPlayerMap();

            const string teamId = "home";
            const string passerId = "home-7";
            const string receiverId = "home-9";
            const string supporterId = "home-10";

            var controlledPlayers = new[] { passerId, receiverId, supporterId };
            if (!TryResolveManualSequencePlayer(passerId, out var passer) ||
                !TryResolveManualSequencePlayer(receiverId, out var receiver) ||
                !TryResolveManualSequencePlayer(supporterId, out var supporter))
            {
                FailManualHomeAttack("failed to resolve home-7/home-9/home-10");
                yield break;
            }

            if (!RequestManualHomeAttackLease(teamId, controlledPlayers))
            {
                FailManualHomeAttack("authority lease rejected");
                yield break;
            }

            var supportPoint = originalSim.ClampToPitch(ResolveAdvanceTarget(supporter, GtexSimTeamSide.Home, 6f, 3.5f));
            var throughPoint = originalSim.ClampToPitch(ResolveAdvanceTarget(receiver, GtexSimTeamSide.Home, 2.2f, 0f));
            var shotTarget = ResolveShotTarget(GtexSimTeamSide.Home, receiver);
            var score = GtexScoreAuthority.Current;

            Debug.Log("[GTEX SEQ] Step 1: AssignPossession home-7");
            HandleCommand(new GtexVisualCommand
            {
                type = GtexVisualCommandType.AssignPossession,
                actorPlayerId = passerId
            });

            var stepComplete = false;
            yield return WaitForSequenceCompletion(
                "[GTEX SEQ] Waiting for AssignPossession completion home-7",
                "[GTEX SEQ] AssignPossession complete",
                () => IsPlayerHoldingBall(passer),
                null,
                1.5f,
                value => stepComplete = value);
            if (!stepComplete)
            {
                FailManualHomeAttack("AssignPossession did not complete");
                yield break;
            }

            if (!RequestManualHomeAttackLease(teamId, controlledPlayers))
            {
                FailManualHomeAttack("authority lease rejected before SupportRun");
                yield break;
            }

            Debug.Log("[GTEX SEQ] Step 2: SupportRun home-10");
            HandleCommand(new GtexVisualCommand
            {
                type = GtexVisualCommandType.SupportRun,
                actorPlayerId = supporterId,
                targetWorldPosition = supportPoint,
                duration = 1.2f,
                urgency = 0.85f
            });

            stepComplete = false;
            yield return WaitForSequenceCompletion(
                "[GTEX SEQ] Waiting for SupportRun completion home-10",
                "[GTEX SEQ] SupportRun complete",
                () => DistanceXZ(originalSim.GetPlayerPosition(supporterId), supportPoint) <= 1.5f,
                null,
                3.2f,
                value => stepComplete = value);
            if (!stepComplete)
            {
                FailManualHomeAttack("SupportRun did not complete");
                yield break;
            }

            if (!RequestManualHomeAttackLease(teamId, controlledPlayers))
            {
                FailManualHomeAttack("authority lease rejected before GroundPass");
                yield break;
            }

            Debug.Log("[GTEX SEQ] Step 3: GroundPass home-7 -> home-9");
            HandleCommand(new GtexVisualCommand
            {
                type = GtexVisualCommandType.Pass,
                actorPlayerId = passerId,
                targetPlayerId = receiverId,
                passStyle = GtexVisualPassStyle.Ground,
                isSuccessful = true
            });

            stepComplete = false;
            yield return WaitForSequenceCompletion(
                "[GTEX SEQ] Waiting for Pass completion (home-7 -> home-9)",
                "[GTEX SEQ] Pass complete",
                () => IsPlayerHoldingBall(receiver),
                () => HasInterception(passer, receiver),
                4f,
                value => stepComplete = value);
            if (!stepComplete)
            {
                FailManualHomeAttack("GroundPass did not complete");
                yield break;
            }

            if (!RequestManualHomeAttackLease(teamId, controlledPlayers))
            {
                FailManualHomeAttack("authority lease rejected before ThroughPass");
                yield break;
            }

            Debug.Log("[GTEX SEQ] Step 4: ThroughPass home-9");
            HandleCommand(new GtexVisualCommand
            {
                type = GtexVisualCommandType.ThroughPass,
                actorPlayerId = receiverId,
                targetWorldPosition = throughPoint,
                passStyle = GtexVisualPassStyle.ThroughGround,
                isSuccessful = true
            });

            stepComplete = false;
            yield return WaitForSequenceCompletion(
                "[GTEX SEQ] Waiting for ThroughPass completion home-9",
                "[GTEX SEQ] ThroughPass complete",
                () => IsPlayerHoldingBall(receiver) ||
                      DistanceXZ(originalSim.GetBallPosition(), originalSim.GetPlayerPosition(receiverId)) <= 2.1f ||
                      DistanceXZ(originalSim.GetBallPosition(), throughPoint) <= 1.35f,
                () => HasInterception(receiver, null),
                3.2f,
                value => stepComplete = value);
            if (!stepComplete)
            {
                FailManualHomeAttack("ThroughPass did not complete");
                yield break;
            }

            if (!RequestManualHomeAttackLease(teamId, controlledPlayers))
            {
                FailManualHomeAttack("authority lease rejected before Shoot");
                yield break;
            }

            Debug.Log("[GTEX SEQ] Step 5: Shoot home-9");
            HandleCommand(new GtexVisualCommand
            {
                type = GtexVisualCommandType.Shoot,
                actorPlayerId = receiverId,
                targetWorldPosition = shotTarget,
                outcome = "goal"
            });

            stepComplete = false;
            yield return WaitForSequenceCompletion(
                "[GTEX SEQ] Waiting for Shoot completion home-9",
                "[GTEX SEQ] Shoot complete",
                () => HasShotLeftFoot(receiver),
                () => HasInterception(receiver, null),
                2.2f,
                value => stepComplete = value);
            if (!stepComplete)
            {
                FailManualHomeAttack("Shoot did not complete");
                yield break;
            }

            Debug.Log("[GTEX SEQ] Step 6: Outcome Goal");
            HandleCommand(new GtexVisualCommand
            {
                type = GtexVisualCommandType.Goal,
                actorPlayerId = receiverId,
                teamId = teamId,
                homeScore = score.homeScore + 1,
                awayScore = score.awayScore,
                matchMinute = score.minute,
                outcome = "manual_home_attack_goal"
            });

            Debug.Log("[GTEX SEQ] Release Authority");
            ReleaseAuthority("manual-home-attack-complete");
            manualHomeAttackActive = false;
            manualHomeAttackRoutine = null;
        }

        private bool TryResolveManualSequencePlayer(string playerId, out GtexOriginalPlayerVisualProxy proxy)
        {
            proxy = null;
            if (originalSim == null || originalSim.PlayerMap == null)
            {
                Debug.LogError("[GTEX SEQ] Player map missing for manual sequence.");
                return false;
            }

            if (originalSim.PlayerMap.TryGetCommandProxy(playerId, out proxy, out var reason))
            {
                return true;
            }

            Debug.LogError("[GTEX SEQ] Missing manual sequence player " + playerId + ": " + reason);
            return false;
        }

        private bool RequestManualHomeAttackLease(string teamId, IEnumerable<string> controlledPlayers)
        {
            return RequestAuthorityLease(teamId, controlledPlayers, 4f);
        }

        private IEnumerator WaitForSequenceCompletion(
            string waitingLog,
            string completeLog,
            Func<bool> isComplete,
            Func<bool> hasFailed,
            float timeoutSeconds,
            Action<bool> result)
        {
            Debug.Log(waitingLog);
            var end = Time.time + Mathf.Max(0.1f, timeoutSeconds);
            while (Time.time < end)
            {
                if (hasFailed != null && hasFailed())
                {
                    result(false);
                    yield break;
                }

                if (isComplete != null && isComplete())
                {
                    Debug.Log(completeLog);
                    Debug.Log("[GTEX SEQ] Executing next step");
                    result(true);
                    yield break;
                }

                yield return null;
            }

            Debug.LogError(waitingLog + " timed out.");
            result(false);
        }

        private bool IsPlayerHoldingBall(GtexOriginalPlayerVisualProxy player)
        {
            return player != null &&
                   Ball.Current != null &&
                   Ball.Current.HolderPlayer == player.Player;
        }

        private bool HasInterception(
            GtexOriginalPlayerVisualProxy expectedActor,
            GtexOriginalPlayerVisualProxy expectedReceiver)
        {
            if (Ball.Current == null || Ball.Current.HolderPlayer == null)
            {
                return false;
            }

            var holder = Ball.Current.HolderPlayer;
            if (expectedActor != null && holder == expectedActor.Player)
            {
                return false;
            }

            if (expectedReceiver != null && holder == expectedReceiver.Player)
            {
                return false;
            }

            Debug.LogError("[GTEX SEQ] Action failed: ball was taken by " + holder + ".");
            return true;
        }

        private bool HasShotLeftFoot(GtexOriginalPlayerVisualProxy shooter)
        {
            if (shooter == null || Ball.Current == null)
            {
                return false;
            }

            if (Ball.Current.HolderPlayer == shooter.Player)
            {
                return false;
            }

            var ballVelocity = Ball.Current.Velocity;
            var ballDistance = DistanceXZ(Ball.Current.transform.position, shooter.Root.position);
            return ballVelocity.sqrMagnitude >= 1.5f * 1.5f || ballDistance >= 1.2f;
        }

        private void FailManualHomeAttack(string reason)
        {
            Debug.LogError("[GTEX SEQ] Home Attack failed: " + reason);
            Debug.Log("[GTEX SEQ] Release Authority");
            ReleaseAuthority("manual-home-attack-failed");
            manualHomeAttackActive = false;
            manualHomeAttackRoutine = null;
        }

        private static float DistanceXZ(Vector3 a, Vector3 b)
        {
            a.y = 0f;
            b.y = 0f;
            return Vector3.Distance(a, b);
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
            yield return RunScriptedSequencePatternRoutine();
            scriptedReplayActive = false;
            localReplayRoutine = null;
        }

        private IEnumerator RunScriptedSequencePatternRoutine()
        {
            EnsureReferences();
            originalSim.ConfigureOriginalRuntime();
            originalSim.RebuildPlayerMap();
            BeginScriptedReplayCaptureSession();

            var sequenceId = string.IsNullOrWhiteSpace(scriptedReplaySequenceId)
                ? GtexVisualSequencePatternLibrary.CentralBuildupShot
                : scriptedReplaySequenceId;

            if (!GtexVisualSequencePatternLibrary.TryBuild(
                    sequenceId,
                    "home",
                    originalSim,
                    out var sequence,
                    out var reason))
            {
                Debug.LogError("[GTEX Sequence] Could not build sequence id=" + sequenceId + ": " + reason);
                CompleteScriptedReplayCaptureSession(false, "sequence_build_failed");
                yield break;
            }

            yield return sequenceRunner.RunSequence(sequence);
            CompleteScriptedReplayCaptureSession(
                sequenceRunner.LastRunSucceeded,
                sequenceRunner.LastRunSucceeded
                    ? "sequence_" + sequence.sequenceId + "_complete"
                    : "sequence_" + sequence.sequenceId + "_failed_" + sequenceRunner.LastFailureReason);
            if (quitAfterReplayRequestedFromLaunch)
            {
                StartCoroutine(QuitAfterReplay());
            }
        }

        private IEnumerator RunLaunchScriptedReplayAfterReady()
        {
            yield return new WaitForSeconds(1f);
            launchReplayRoutine = null;
            RunScriptedCommandReplay();
        }

        private IEnumerator ExecuteScriptedReplayStep(GtexVisualCommand command, string captureLabel, float captureDelaySeconds = ReplayCaptureDelaySeconds)
        {
            HandleCommand(command);

            if (!scriptedReplayCaptureEnabled || string.IsNullOrWhiteSpace(scriptedReplayCaptureSessionDirectory))
            {
                yield return WaitBriefly();
                yield break;
            }

            var captureDelay = Mathf.Clamp(captureDelaySeconds, 0f, ReplayDelaySeconds);
            if (captureDelay > 0f)
            {
                yield return new WaitForSeconds(captureDelay);
            }

            yield return CaptureScriptedReplayFrame(captureLabel, command);

            var remainingDelay = ReplayDelaySeconds - captureDelay;
            if (remainingDelay > 0f)
            {
                yield return new WaitForSeconds(remainingDelay);
            }
        }

        private void BeginScriptedReplayCaptureSession()
        {
            scriptedReplayCapturePaths.Clear();
            scriptedReplayCaptureIndex = 0;
            scriptedReplayCaptureSessionDirectory = string.Empty;
            scriptedReplayCaptureManifestPath = string.Empty;

            if (!scriptedReplayCaptureEnabled || Application.isBatchMode)
            {
                return;
            }

            var outputRoot = ResolveReplayCaptureOutputRoot();
            if (string.IsNullOrWhiteSpace(outputRoot))
            {
                return;
            }

            try
            {
                var sessionStamp = DateTime.Now.ToString("yyyyMMdd-HHmmss");
                scriptedReplayCaptureSessionDirectory = Path.Combine(
                    outputRoot,
                    "scripted-replay-" + sessionStamp);
                Directory.CreateDirectory(scriptedReplayCaptureSessionDirectory);

                scriptedReplayCaptureManifestPath = Path.Combine(
                    scriptedReplayCaptureSessionDirectory,
                    "manifest.txt");

                var header = new StringBuilder();
                header.AppendLine("session=scripted-replay");
                header.AppendLine("status=started");
                header.AppendLine("directory=" + scriptedReplayCaptureSessionDirectory);
                header.AppendLine("startedAt=" + DateTime.Now.ToString("O"));
                header.AppendLine("captureDelaySeconds=" + ReplayCaptureDelaySeconds.ToString("0.##"));
                header.AppendLine("captures=");
                File.WriteAllText(scriptedReplayCaptureManifestPath, header.ToString());

                Debug.Log("[GTEX VisualBridge] ReplayCapture armed -> " + scriptedReplayCaptureSessionDirectory);
            }
            catch (Exception exception)
            {
                Debug.LogWarning("[GTEX VisualBridge] ReplayCapture disabled: " + exception.Message);
                scriptedReplayCaptureSessionDirectory = string.Empty;
                scriptedReplayCaptureManifestPath = string.Empty;
            }
        }

        private IEnumerator CaptureScriptedReplayFrame(string captureLabel, GtexVisualCommand command)
        {
            if (!scriptedReplayCaptureEnabled ||
                string.IsNullOrWhiteSpace(scriptedReplayCaptureSessionDirectory) ||
                Application.isBatchMode)
            {
                yield break;
            }

            yield return new WaitForEndOfFrame();

            var safeLabel = SanitizeCaptureLabel(captureLabel);
            var capturePath = Path.Combine(
                scriptedReplayCaptureSessionDirectory,
                string.Format("{0:D2}_{1}.png", scriptedReplayCaptureIndex + 1, safeLabel));

            Texture2D screenshotTexture = null;
            try
            {
                screenshotTexture = ScreenCapture.CaptureScreenshotAsTexture();
                if (screenshotTexture == null)
                {
                    AppendReplayCaptureManifestLine(
                        "capture_failed|" +
                        safeLabel +
                        "|reason=null_texture");
                    yield break;
                }

                var pngBytes = screenshotTexture.EncodeToPNG();
                File.WriteAllBytes(capturePath, pngBytes);
                scriptedReplayCaptureIndex += 1;
                scriptedReplayCapturePaths.Add(capturePath);
                AppendReplayCaptureManifestLine(
                    "capture|" +
                    scriptedReplayCaptureIndex.ToString("D2") +
                    "|" + safeLabel +
                    "|" + BuildReplayCaptureCommandSummary(command) +
                    "|path=" + capturePath);
                Debug.Log("[GTEX VisualBridge] ReplayCapture saved -> " + capturePath);
            }
            catch (Exception exception)
            {
                AppendReplayCaptureManifestLine(
                    "capture_failed|" +
                    safeLabel +
                    "|reason=" + exception.Message.Replace(Environment.NewLine, " "));
                Debug.LogWarning("[GTEX VisualBridge] ReplayCapture failed for " + safeLabel + ": " + exception.Message);
            }
            finally
            {
                if (screenshotTexture != null)
                {
                    Destroy(screenshotTexture);
                }
            }
        }

        private void CompleteScriptedReplayCaptureSession(bool completed, string note)
        {
            if (!scriptedReplayCaptureEnabled || string.IsNullOrWhiteSpace(scriptedReplayCaptureManifestPath))
            {
                return;
            }

            AppendReplayCaptureManifestLine("status=" + (completed ? "completed" : "incomplete"));
            AppendReplayCaptureManifestLine("note=" + (string.IsNullOrWhiteSpace(note) ? "n/a" : note));
            AppendReplayCaptureManifestLine("captureCount=" + scriptedReplayCapturePaths.Count);
            AppendReplayCaptureManifestLine("endedAt=" + DateTime.Now.ToString("O"));

            if (!string.IsNullOrWhiteSpace(scriptedReplayCaptureSessionDirectory))
            {
                Debug.Log(
                    "[GTEX VisualBridge] ReplayCapture session " +
                    (completed ? "complete" : "stopped") +
                    " -> " + scriptedReplayCaptureSessionDirectory);
            }
        }

        private static string BuildReplayCaptureCommandSummary(GtexVisualCommand command)
        {
            if (command == null)
            {
                return "type=None";
            }

            var builder = new StringBuilder();
            builder.Append("type=").Append(command.type);
            if (!string.IsNullOrWhiteSpace(command.actorPlayerId))
            {
                builder.Append("|actor=").Append(command.actorPlayerId);
            }

            if (!string.IsNullOrWhiteSpace(command.targetPlayerId))
            {
                builder.Append("|target=").Append(command.targetPlayerId);
            }

            if (IsPassLike(command.type))
            {
                builder.Append("|style=").Append(command.passStyle);
            }

            if (!string.IsNullOrWhiteSpace(command.outcome))
            {
                builder.Append("|outcome=").Append(command.outcome);
            }

            if (command.targetWorldPosition.sqrMagnitude > 0.001f)
            {
                builder.Append("|point=").Append(command.targetWorldPosition.ToString("F2"));
            }

            return builder.ToString();
        }

        private static string SanitizeCaptureLabel(string captureLabel)
        {
            var source = string.IsNullOrWhiteSpace(captureLabel) ? "capture" : captureLabel.Trim();
            var invalidCharacters = Path.GetInvalidFileNameChars();
            var builder = new StringBuilder(source.Length);
            for (var index = 0; index < source.Length; index += 1)
            {
                var character = char.ToLowerInvariant(source[index]);
                if (invalidCharacters.Contains(character))
                {
                    continue;
                }

                builder.Append(char.IsWhiteSpace(character) ? '_' : character);
            }

            return builder.Length > 0 ? builder.ToString() : "capture";
        }

        private void AppendReplayCaptureManifestLine(string line)
        {
            if (string.IsNullOrWhiteSpace(scriptedReplayCaptureManifestPath))
            {
                return;
            }

            try
            {
                File.AppendAllText(scriptedReplayCaptureManifestPath, line + Environment.NewLine);
            }
            catch (Exception exception)
            {
                Debug.LogWarning("[GTEX VisualBridge] ReplayCapture manifest write failed: " + exception.Message);
            }
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
            scriptedReplayCaptureEnabled = ResolveBoolArg(
                scriptedReplayRequestedFromLaunch,
                "captureReplayFrames",
                "capture-replay-frames",
                "replayCaptureFrames",
                "gtex-capture-replay-frames");
            scriptedReplayCaptureOutputRoot = ResolveReplayCaptureOutputRoot();
            scriptedReplayLaunchFallbackStarted = false;
            scriptedReplayLaunchRequestedAt = Time.realtimeSinceStartup;
            scriptedReplaySequenceId = ResolveStringArg(
                GtexVisualSequencePatternLibrary.CentralBuildupShot,
                "sequence",
                "gtex-sequence",
                "scriptedReplaySequence",
                "scripted-replay-sequence");

            if (!scriptedReplayRequestedFromLaunch)
            {
                return;
            }

            ApplyCleanCaptureSettings();
            Debug.Log(
                "[GTEX VisualBridge] Scripted replay launch flag detected. " +
                "quitAfterReplay=" + quitAfterReplayRequestedFromLaunch + " " +
                "sequence=" + scriptedReplaySequenceId + " " +
                "captureReplayFrames=" + scriptedReplayCaptureEnabled + " " +
                "captureDir=" + scriptedReplayCaptureOutputRoot + ".");
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

        private string ResolveReplayCaptureOutputRoot()
        {
            var explicitPath = ResolveStringArg(
                null,
                "replayCaptureOutputDir",
                "replay-capture-output-dir",
                "captureOutputDir",
                "capture-output-dir",
                "gtex-capture-output-dir");
            if (!string.IsNullOrWhiteSpace(explicitPath))
            {
                return Path.GetFullPath(explicitPath.Trim());
            }

            if (Application.isEditor)
            {
                return Path.GetFullPath(Path.Combine(Application.dataPath, "..", "tmp", "original-visual-runtime-replay-captures"));
            }

            return Path.GetFullPath(Path.Combine(Application.dataPath, "..", "ReplayCaptures"));
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

        private static string ResolveStringArg(string defaultValue, params string[] names)
        {
            var value = ResolveRawArgValue(names, out var found);
            if (!found || string.IsNullOrWhiteSpace(value))
            {
                return defaultValue;
            }

            return value.Trim();
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
            if (players.Length == 0)
            {
                actor = null;
                support = null;
                wide = null;
                return false;
            }

            var ballPosition = originalSim != null ? originalSim.GetBallPosition() : Vector3.zero;
            var advancedCandidates = players
                .OrderByDescending(player => ResolveAttackProgress(teamSide, player))
                .Take(Mathf.Min(5, players.Length))
                .ToArray();

            var resolvedActor = advancedCandidates
                .OrderBy(player => Vector3.SqrMagnitude(player.Root.position - ballPosition))
                .FirstOrDefault() ?? advancedCandidates[0];

            var supportCandidates = advancedCandidates.Where(player => player != resolvedActor).ToArray();
            var resolvedSupport = supportCandidates
                .OrderBy(player => Vector3.SqrMagnitude(player.Root.position - resolvedActor.Root.position))
                .FirstOrDefault() ?? players.FirstOrDefault(player => player != resolvedActor);

            var resolvedWide = supportCandidates
                .Where(player => player != resolvedSupport)
                .OrderByDescending(player => Mathf.Abs(player.Root.position.z - resolvedActor.Root.position.z) + ResolveAttackProgress(teamSide, player) * 10f)
                .FirstOrDefault() ?? resolvedSupport;

            actor = resolvedActor;
            support = resolvedSupport;
            wide = resolvedWide;
            return resolvedActor != null;
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

        private bool TryResolveScriptedReplayParticipants(
            out GtexSimTeamSide attackingSide,
            out GtexOriginalPlayerVisualProxy carrier,
            out GtexOriginalPlayerVisualProxy shortOption,
            out GtexOriginalPlayerVisualProxy runner,
            out GtexOriginalPlayerVisualProxy marker,
            out GtexOriginalPlayerVisualProxy presser,
            out GtexOriginalPlayerVisualProxy trackingDefender)
        {
            attackingSide = GtexSimTeamSide.Home;
            carrier = null;
            shortOption = null;
            runner = null;
            marker = null;
            presser = null;
            trackingDefender = null;

            var kickoffBallPosition = originalSim != null ? originalSim.GetBallPosition() : Vector3.zero;
            var kickoffHolder = ResolveCurrentBallHolderProxy();
            attackingSide = ResolveScriptedReplayAttackingSide(kickoffHolder, kickoffBallPosition);
            var defendingSide = attackingSide == GtexSimTeamSide.Home
                ? GtexSimTeamSide.Away
                : GtexSimTeamSide.Home;

            var attackers = ResolveTeamOutfieldPlayers(attackingSide);
            var defenders = ResolveTeamOutfieldPlayers(defendingSide);

            if (attackers.Length < 3 || defenders.Length < 3)
            {
                return false;
            }

            if (kickoffHolder != null &&
                !kickoffHolder.IsGoalkeeper &&
                TryResolveProxyTeamSide(kickoffHolder, out var kickoffHolderSide) &&
                kickoffHolderSide == attackingSide)
            {
                carrier = kickoffHolder;
            }

            if (carrier == null)
            {
                carrier = attackers
                    .OrderBy(proxy => Vector3.SqrMagnitude(proxy.Root.position - kickoffBallPosition))
                    .FirstOrDefault();
            }

            var resolvedCarrier = carrier;
            var resolvedAttackingSide = attackingSide;
            shortOption = attackers
                .Where(proxy => proxy != resolvedCarrier)
                .OrderBy(proxy => Vector3.SqrMagnitude(proxy.Root.position - resolvedCarrier.Root.position))
                .ThenByDescending(proxy => ResolveAttackProgress(resolvedAttackingSide, proxy))
                .FirstOrDefault();

            var resolvedShortOption = shortOption;
            runner = attackers
                .Where(proxy => proxy != resolvedCarrier && proxy != resolvedShortOption)
                .OrderByDescending(proxy => ResolveAttackProgress(resolvedAttackingSide, proxy))
                .ThenBy(proxy => Vector3.SqrMagnitude(proxy.Root.position - resolvedCarrier.Root.position))
                .FirstOrDefault();

            presser = ResolveNearestDistinct(defenders, carrier, null, null);
            marker = ResolveNearestDistinct(defenders, shortOption, presser, null);
            trackingDefender = ResolveNearestDistinct(defenders, runner, presser, marker);

            return carrier != null &&
                   shortOption != null &&
                   runner != null &&
                   marker != null &&
                   presser != null &&
                   trackingDefender != null;
        }

        private GtexOriginalPlayerVisualProxy ResolveCurrentBallHolderProxy()
        {
            var holder = Ball.Current != null ? Ball.Current.HolderPlayer : null;
            if (holder == null || originalSim == null || originalSim.PlayerMap == null)
            {
                return null;
            }

            return originalSim.PlayerMap.Proxies.FirstOrDefault(proxy => proxy != null && proxy.Player == holder);
        }

        private GtexSimTeamSide ResolveScriptedReplayAttackingSide(
            GtexOriginalPlayerVisualProxy kickoffHolder,
            Vector3 kickoffBallPosition)
        {
            if (kickoffHolder != null &&
                !kickoffHolder.IsGoalkeeper &&
                TryResolveProxyTeamSide(kickoffHolder, out var holderSide))
            {
                return holderSide;
            }

            var home = ResolveNearestOutfieldPlayers(GtexSimTeamSide.Home, kickoffBallPosition, 1).FirstOrDefault();
            var away = ResolveNearestOutfieldPlayers(GtexSimTeamSide.Away, kickoffBallPosition, 1).FirstOrDefault();
            if (home == null && away == null)
            {
                return GtexSimTeamSide.Home;
            }

            if (home == null)
            {
                return GtexSimTeamSide.Away;
            }

            if (away == null)
            {
                return GtexSimTeamSide.Home;
            }

            return Vector3.SqrMagnitude(home.Root.position - kickoffBallPosition) <=
                   Vector3.SqrMagnitude(away.Root.position - kickoffBallPosition)
                ? GtexSimTeamSide.Home
                : GtexSimTeamSide.Away;
        }

        private bool TryResolveProxyTeamSide(GtexOriginalPlayerVisualProxy proxy, out GtexSimTeamSide teamSide)
        {
            teamSide = GtexSimTeamSide.Home;
            if (proxy == null)
            {
                return false;
            }

            var commandSide = GtexPlayerVisualMap.ResolveTeamSide(proxy.GtexPlayerId);
            if (string.Equals(commandSide, "home", StringComparison.OrdinalIgnoreCase))
            {
                teamSide = GtexSimTeamSide.Home;
                return true;
            }

            if (string.Equals(commandSide, "away", StringComparison.OrdinalIgnoreCase))
            {
                teamSide = GtexSimTeamSide.Away;
                return true;
            }

            var manager = MatchManager.Current;
            if (manager != null && proxy.Player != null)
            {
                if (proxy.Player.GameTeam == manager.GameTeam1)
                {
                    teamSide = GtexSimTeamSide.Home;
                    return true;
                }

                if (proxy.Player.GameTeam == manager.GameTeam2)
                {
                    teamSide = GtexSimTeamSide.Away;
                    return true;
                }
            }

            return false;
        }

        private static string ResolveTeamId(GtexSimTeamSide teamSide)
        {
            return teamSide == GtexSimTeamSide.Away ? "away" : "home";
        }

        private static GtexOriginalPlayerVisualProxy ResolveNearestDistinct(
            IEnumerable<GtexOriginalPlayerVisualProxy> candidates,
            GtexOriginalPlayerVisualProxy target,
            GtexOriginalPlayerVisualProxy excludedA,
            GtexOriginalPlayerVisualProxy excludedB)
        {
            if (target == null)
            {
                return null;
            }

            return candidates
                .Where(proxy => proxy != null && proxy != excludedA && proxy != excludedB)
                .OrderBy(proxy => Vector3.SqrMagnitude(proxy.Root.position - target.Root.position))
                .FirstOrDefault();
        }

        private GtexOriginalPlayerVisualProxy[] ResolveNearestOutfieldPlayers(GtexSimTeamSide teamSide, Vector3 origin, int maxCount)
        {
            if (maxCount <= 0)
            {
                return Array.Empty<GtexOriginalPlayerVisualProxy>();
            }

            return ResolveTeamOutfieldPlayers(teamSide)
                .Where(proxy => proxy != null && proxy.Player != null && !proxy.IsGoalkeeper)
                .OrderBy(proxy => Vector3.SqrMagnitude(proxy.Root.position - origin))
                .Take(maxCount)
                .ToArray();
        }

        private float ResolveAttackProgress(GtexSimTeamSide teamSide, GtexOriginalPlayerVisualProxy player)
        {
            if (player == null)
            {
                return 0f;
            }

            var manager = MatchManager.Current;
            var fieldLength = manager != null
                ? (manager.fieldEndX > 0f ? manager.fieldEndX : manager.SizeOfField.x)
                : 105f;
            if (fieldLength <= 0.01f)
            {
                fieldLength = 105f;
            }

            return teamSide == GtexSimTeamSide.Home
                ? Mathf.Clamp01(player.Root.position.x / fieldLength)
                : Mathf.Clamp01((fieldLength - player.Root.position.x) / fieldLength);
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

        private Vector3 ResolveDangerousThroughTarget(
            GtexOriginalPlayerVisualProxy passer,
            GtexOriginalPlayerVisualProxy runner,
            GtexSimTeamSide teamSide)
        {
            var manager = MatchManager.Current;
            var goal = ResolveOpposingGoal(teamSide, manager);
            var source = passer != null ? passer.Root.position : runner != null ? runner.Root.position : Vector3.zero;
            var direction = goal - source;
            direction.y = 0f;
            if (direction.sqrMagnitude <= 0.001f)
            {
                direction = teamSide == GtexSimTeamSide.Home ? Vector3.right : Vector3.left;
            }

            direction.Normalize();
            var lateral = Vector3.Cross(Vector3.up, direction).normalized;
            var lateralSign = runner != null && runner.Root.position.z < goal.z ? -1f : 1f;
            var target = goal - direction * 16f + lateral * lateralSign * 3.2f;
            if (runner != null)
            {
                target.y = runner.Root.position.y;
            }

            return originalSim != null ? originalSim.ClampToPitch(target) : target;
        }

        private Vector3 ResolveShotCarryTarget(GtexOriginalPlayerVisualProxy runner, GtexSimTeamSide teamSide)
        {
            if (runner == null)
            {
                return Vector3.zero;
            }

            var manager = MatchManager.Current;
            var goal = ResolveOpposingGoal(teamSide, manager);
            var direction = goal - runner.Root.position;
            direction.y = 0f;
            if (direction.sqrMagnitude <= 0.001f)
            {
                direction = teamSide == GtexSimTeamSide.Home ? Vector3.right : Vector3.left;
            }

            direction.Normalize();
            var target = goal - direction * 12f;
            target.y = runner.Root.position.y;
            return originalSim != null ? originalSim.ClampToPitch(target) : target;
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

            if (sequenceRunner == null)
            {
                sequenceRunner = GetComponent<GtexSequenceRunner>();
                if (sequenceRunner == null)
                {
                    sequenceRunner = gameObject.AddComponent<GtexSequenceRunner>();
                }
            }

            intentDirector.Bind(this, originalSim);
            sequenceRunner.Bind(this, originalSim);
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
