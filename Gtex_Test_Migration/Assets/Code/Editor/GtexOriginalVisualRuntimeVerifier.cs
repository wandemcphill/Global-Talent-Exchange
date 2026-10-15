#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Text;
using System.Threading;
using Stopwatch = System.Diagnostics.Stopwatch;
using FStudio.GTEX;
using FStudio.GTEX.Core;
using FStudio.GTEX.Simulation;
using FStudio.GTEX.VisualBridge;
using FStudio.MatchEngine;
using FStudio.MatchEngine.Balls;
using FStudio.MatchEngine.Cameras;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace FStudio.GTEX.Editor
{
    public static class GtexOriginalVisualRuntimeVerifier
    {
        private const string AutoStartEnvironmentVariable = "GTEX_ORIGINAL_VISUAL_RUNTIME_VERIFY";
        private const string AutoStartFlagFileRelativePath = "tmp/original-visual-runtime-verification.autostart";
        private static VerificationRun currentRun;
        private static bool autoStartChecked;

        [InitializeOnLoadMethod]
        private static void AutoStartFromEnvironment()
        {
            if (autoStartChecked)
            {
                return;
            }

            autoStartChecked = true;
            var autoStartValue = Environment.GetEnvironmentVariable(AutoStartEnvironmentVariable);
            var autoStartFlagPath = GetAutoStartFlagPath();
            var shouldAutoStart =
                string.Equals(autoStartValue, "1", StringComparison.OrdinalIgnoreCase) ||
                File.Exists(autoStartFlagPath);

            if (!shouldAutoStart)
            {
                return;
            }

            EditorApplication.delayCall += () =>
            {
                if (currentRun == null)
                {
                    Start(true);
                }
            };
        }

        [MenuItem("Tools/GTEX/Runtime/Verify Original Visual Runtime")]
        public static void VerifyFromEditorMenu()
        {
            Start(false);
        }

        public static void VerifyFromCommandLine()
        {
            Start(true);
        }

        private static void Start(bool exitEditorWhenFinished)
        {
            if (currentRun != null)
            {
                throw new InvalidOperationException("Original visual runtime verification is already running.");
            }

            currentRun = new VerificationRun(exitEditorWhenFinished);
            currentRun.Start();
        }

        private sealed class VerificationRun
        {
            private const string ActionName = "Original visual runtime verification";
            private const double BootTimeoutSeconds = 25d;
            private const double NoBackendObserveSeconds = 60d;
            private const double ReplayTimeoutSeconds = 75d;
            private const double LocalSimTimeoutSeconds = 120d;
            private const double LiveFeedTimeoutSeconds = 60d;

            private enum SessionKind
            {
                None,
                NoBackend,
                ScriptedReplay,
                LocalSim,
                LiveFeed
            }

            private sealed class SectionResult
            {
                public string Name;
                public bool Passed;
                public bool Blocked;
                public string Summary = string.Empty;
                public readonly List<string> Notes = new List<string>();
                public readonly List<string> Errors = new List<string>();
                public readonly List<string> Screenshots = new List<string>();
            }

            private readonly bool exitEditorWhenFinished;
            private readonly Stopwatch stopwatch = Stopwatch.StartNew();
            private readonly List<string> consoleLines = new List<string>();
            private readonly string[] disallowedPatterns =
            {
                "matchId is empty for live mode",
                "Live playback auth bootstrap is missing",
                "missing-auth",
                "ResetMatchState",
                "NullReferenceException",
                "GtexPlaybackApplier",
                "kinematic Rigidbody velocity",
                "dead-binding"
            };

            private readonly SectionResult editorNoBackend = new SectionResult { Name = "Editor no-backend test" };
            private readonly SectionResult scriptedReplay = new SectionResult { Name = "Scripted replay" };
            private readonly SectionResult localSim = new SectionResult { Name = "Local sim feed" };
            private readonly SectionResult liveFeed = new SectionResult { Name = "Live backend feed" };

            private readonly string outputDirectory;
            private readonly string screenshotDirectory;
            private readonly string consoleLogPath;
            private readonly string reportPath;
            private readonly string traceLogPath;
            private readonly string configPath;
            private readonly string originalConfigJson;

            private readonly float[] noBackendCaptureTimes = { 0f, 20f, 40f, 60f };
            private readonly string[] replayCaptureLabels =
            {
                "01_start_match",
                "02_reset_kickoff",
                "03_assign_possession",
                "04_carry",
                "05_pass",
                "06_through_pass",
                "07_cross",
                "08_shot",
                "09_keeper_save",
                "10_goal",
                "11_reset_after_goal"
            };
            private readonly double[] replayCaptureTimes =
            {
                0.35d,
                1.65d,
                2.95d,
                4.25d,
                5.55d,
                6.85d,
                8.15d,
                9.45d,
                10.75d,
                12.05d,
                13.35d
            };
            private readonly int[] localMinuteThresholds = { 10, 25, 45, 60, 90 };
            private readonly HashSet<int> localMinuteCaptures = new HashSet<int>();

            private SessionKind currentSession;
            private bool waitingForPlayMode;
            private bool waitingForEditMode;
            private bool runtimeReadyObserved;
            private bool replayStarted;
            private bool localSimStarted;
            private bool localHalfReached;
            private bool localFullTimeReached;
            private bool scoreMismatchObserved;
            private bool externalPlaybackObserved;
            private bool disallowedLogObserved;
            private bool shouldFinalize;
            private bool playModeOptionsOverridden;
            private bool originalEnterPlayModeOptionsEnabled;
            private EnterPlayModeOptions originalEnterPlayModeOptions;
            private Exception unexpectedFailure;
            private double sessionStartedAt;
            private double readyObservedAt;
            private double replayStartedAt;
            private double localSimStartedAt;
            private int sessionConsoleStartIndex;
            private int replayCaptureIndex;
            private int noBackendCaptureIndex;
            private int replayStartHomeScore;
            private int liveFeedRequestCount;
            private int liveFeedServedFrameCount;
            private int liveFeedPort;
            private float sessionStartMatchMinute;
            private float lastObservedMatchMinute;
            private bool liveFeedStarted;
            private bool liveRuntimeObjectObserved;
            private volatile bool liveFeedServerStopping;
            private volatile string liveFeedListenerFailure = string.Empty;
            private volatile HttpListener liveFeedListener;
            private Thread liveFeedServerThread;
            private string[] liveFeedPayloads = Array.Empty<string>();

            public VerificationRun(bool exitEditorWhenFinished)
            {
                this.exitEditorWhenFinished = exitEditorWhenFinished;

                var projectRoot = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
                var stamp = DateTime.Now.ToString("yyyyMMdd-HHmmss");
                outputDirectory = Path.Combine(projectRoot, "tmp", "original-visual-runtime-verification", stamp);
                screenshotDirectory = Path.Combine(outputDirectory, "screenshots");
                consoleLogPath = Path.Combine(outputDirectory, "console.log");
                reportPath = Path.Combine(outputDirectory, "report.md");
                traceLogPath = Path.Combine(outputDirectory, "trace.log");
                configPath = GtexRuntimeModeTools.AbsoluteConfigPath;
                originalConfigJson = File.ReadAllText(configPath);
            }

            public void Start()
            {
                Directory.CreateDirectory(outputDirectory);
                Directory.CreateDirectory(screenshotDirectory);
                Trace("Start");

                GtexRuntimeToolStatus.Begin(ActionName);
                OverrideEnterPlayModeOptions();
                Application.logMessageReceived += HandleLogMessage;
                EditorApplication.playModeStateChanged += HandlePlayModeStateChanged;
                EditorApplication.update += Update;

                WriteVerificationConfig();
                BeginSession(SessionKind.NoBackend);
            }

            private void OverrideEnterPlayModeOptions()
            {
                originalEnterPlayModeOptionsEnabled = EditorSettings.enterPlayModeOptionsEnabled;
                originalEnterPlayModeOptions = EditorSettings.enterPlayModeOptions;
                EditorSettings.enterPlayModeOptionsEnabled = true;
                EditorSettings.enterPlayModeOptions = EnterPlayModeOptions.DisableDomainReload;
                playModeOptionsOverridden = true;
            }

            private void RestoreEnterPlayModeOptions()
            {
                if (!playModeOptionsOverridden)
                {
                    return;
                }

                EditorSettings.enterPlayModeOptionsEnabled = originalEnterPlayModeOptionsEnabled;
                EditorSettings.enterPlayModeOptions = originalEnterPlayModeOptions;
                playModeOptionsOverridden = false;
            }

            private void BeginSession(SessionKind sessionKind)
            {
                currentSession = sessionKind;
                waitingForPlayMode = true;
                waitingForEditMode = false;
                runtimeReadyObserved = false;
                replayStarted = false;
                localSimStarted = false;
                localHalfReached = false;
                localFullTimeReached = false;
                scoreMismatchObserved = false;
                externalPlaybackObserved = false;
                disallowedLogObserved = false;
                replayCaptureIndex = 0;
                noBackendCaptureIndex = 0;
                localMinuteCaptures.Clear();
                sessionConsoleStartIndex = consoleLines.Count;
                sessionStartedAt = EditorApplication.timeSinceStartup;
                readyObservedAt = 0d;
                replayStartedAt = 0d;
                localSimStartedAt = 0d;
                sessionStartMatchMinute = 0f;
                lastObservedMatchMinute = 0f;
                Trace("BeginSession=" + sessionKind);

                if (sessionKind == SessionKind.LiveFeed)
                {
                    try
                    {
                        liveFeedPort = StartLiveFeedListener();
                        WriteLiveFeedVerificationConfig();
                    }
                    catch (Exception exception)
                    {
                        liveFeedListenerFailure = exception.Message;
                        liveFeed.Errors.Add("Could not start the live-feed listener: " + exception.Message);
                    }
                }

                EditorSceneManager.OpenScene(GtexSceneLoader.OriginalVisualRuntimeScenePath, OpenSceneMode.Single);
                EditorApplication.delayCall += EnterPlayMode;
            }

            private void EnterPlayMode()
            {
                if (!waitingForPlayMode || EditorApplication.isPlayingOrWillChangePlaymode || EditorApplication.isPlaying)
                {
                    return;
                }

                Trace("EnterPlayMode");
                EditorApplication.isPlaying = true;
            }

            private void Update()
            {
                if (shouldFinalize || !EditorApplication.isPlaying)
                {
                    return;
                }

                try
                {
                    switch (currentSession)
                    {
                        case SessionKind.NoBackend:
                            UpdateNoBackendSession();
                            break;
                        case SessionKind.ScriptedReplay:
                            UpdateReplaySession();
                            break;
                        case SessionKind.LocalSim:
                            UpdateLocalSimSession();
                            break;
                        case SessionKind.LiveFeed:
                            UpdateLiveFeedSession();
                            break;
                    }
                }
                catch (Exception exception)
                {
                    AbortRun(exception);
                }
            }

            private void UpdateNoBackendSession()
            {
                if (!TryResolveRuntime(out var director))
                {
                    if (Time.realtimeSinceStartupAsDouble - sessionStartedAt >= BootTimeoutSeconds)
                    {
                        editorNoBackend.Errors.Add("Original visual runtime did not become ready in the editor no-backend session.");
                        editorNoBackend.Summary = "Scene did not bootstrap into the original visual runtime.";
                        ExitCurrentPlaySession();
                    }

                    return;
                }

                if (!runtimeReadyObserved)
                {
                    runtimeReadyObserved = true;
                    readyObservedAt = Time.realtimeSinceStartupAsDouble;
                    sessionStartMatchMinute = MatchManager.Current != null ? MatchManager.Current.minutes : 0f;
                    lastObservedMatchMinute = sessionStartMatchMinute;
                    Trace("NoBackendReady");
                }

                TrackSharedGuards(editorNoBackend);

                var observedSeconds = Time.realtimeSinceStartupAsDouble - readyObservedAt;
                while (noBackendCaptureIndex < noBackendCaptureTimes.Length &&
                       observedSeconds >= noBackendCaptureTimes[noBackendCaptureIndex])
                {
                    CaptureScreenshot(editorNoBackend, "A_no_backend_" + noBackendCaptureIndex.ToString("00"));
                    noBackendCaptureIndex += 1;
                }

                if (MatchManager.Current != null)
                {
                    lastObservedMatchMinute = Mathf.Max(lastObservedMatchMinute, MatchManager.Current.minutes);
                }

                if (observedSeconds < NoBackendObserveSeconds)
                {
                    return;
                }

                editorNoBackend.Notes.Add("Scene=" + SceneManager.GetActiveScene().name);
                editorNoBackend.Notes.Add("RuntimeReady=" + director.IsRuntimeReady);
                editorNoBackend.Notes.Add("ClockStart=" + sessionStartMatchMinute.ToString("0.0"));
                editorNoBackend.Notes.Add("ClockEnd=" + lastObservedMatchMinute.ToString("0.0"));
                editorNoBackend.Notes.Add("ExternalPlaybackEnabled=" + (MatchManager.Current != null && MatchManager.Current.ExternalPlaybackEnabled));
                editorNoBackend.Notes.Add("BallPresent=" + (Ball.Current != null));
                editorNoBackend.Notes.Add("CameraPresent=" + (CameraSystem.Current != null));
                editorNoBackend.Notes.Add("MatchManagerPresent=" + (MatchManager.Current != null));

                var clockAdvanced = lastObservedMatchMinute > sessionStartMatchMinute + 0.1f;
                if (!clockAdvanced)
                {
                    editorNoBackend.Errors.Add("Original simulator clock did not advance during the no-backend editor run.");
                }

                if (UnityEngine.Object.FindFirstObjectByType<GtexMatchRuntime>() != null)
                {
                    editorNoBackend.Errors.Add("GtexMatchRuntime should not exist in OriginalVisualRuntime no-backend session.");
                }

                if (UnityEngine.Object.FindFirstObjectByType<GtexSimRuntimeHost>() != null)
                {
                    editorNoBackend.Errors.Add("GtexSimRuntimeHost should not exist in OriginalVisualRuntime no-backend session.");
                }

                editorNoBackend.Passed =
                    director.IsRuntimeReady &&
                    clockAdvanced &&
                    !externalPlaybackObserved &&
                    !scoreMismatchObserved &&
                    !disallowedLogObserved &&
                    editorNoBackend.Errors.Count == 0;
                editorNoBackend.Summary = editorNoBackend.Passed
                    ? "Original visual scene booted, stayed under original visual authority, and advanced match time without backend."
                    : "Original visual scene failed one or more no-backend acceptance checks.";

                ExitCurrentPlaySession();
            }

            private void UpdateReplaySession()
            {
                if (!TryResolveRuntime(out var director))
                {
                    if (Time.realtimeSinceStartupAsDouble - sessionStartedAt >= BootTimeoutSeconds)
                    {
                        scriptedReplay.Errors.Add("Original visual runtime did not become ready before scripted replay.");
                        scriptedReplay.Summary = "Scripted replay could not start because the scene never became ready.";
                        ExitCurrentPlaySession();
                    }

                    return;
                }

                if (!runtimeReadyObserved)
                {
                    runtimeReadyObserved = true;
                    readyObservedAt = Time.realtimeSinceStartupAsDouble;
                    EnableVisualCommandLogging(director);
                    replayStartHomeScore = GtexScoreAuthority.Current.homeScore;
                    director.RunScriptedAcceptanceReplay();
                    replayStarted = true;
                    replayStartedAt = Time.realtimeSinceStartupAsDouble;
                    Trace("ReplayReady");
                }

                TrackSharedGuards(scriptedReplay);

                if (!replayStarted)
                {
                    return;
                }

                var replayElapsed = Time.realtimeSinceStartupAsDouble - replayStartedAt;
                while (replayCaptureIndex < replayCaptureTimes.Length &&
                       replayElapsed >= replayCaptureTimes[replayCaptureIndex])
                {
                    CaptureScreenshot(scriptedReplay, "B_replay_" + replayCaptureLabels[replayCaptureIndex]);
                    replayCaptureIndex += 1;
                }

                if (!director.ScriptedAcceptanceReplayComplete)
                {
                    if (replayElapsed >= ReplayTimeoutSeconds)
                    {
                        scriptedReplay.Errors.Add("Scripted acceptance replay did not complete before the 75-second timeout.");
                        scriptedReplay.Summary = "Scripted acceptance replay timed out.";
                        ExitCurrentPlaySession();
                    }

                    return;
                }

                if (!director.ScriptedAcceptanceReplaySucceeded)
                {
                    scriptedReplay.Errors.Add("Scripted acceptance replay reported failure.");
                }

                var replayLog = GetSessionLogs()
                    .Where(line => line.IndexOf("[GTEX VisualBridge] Command ->", StringComparison.OrdinalIgnoreCase) >= 0)
                    .ToArray();

                var expectedTokens = new[]
                {
                    "StartMatch",
                    "ResetKickoff",
                    "AssignPossession",
                    "CarryBall",
                    "Pass",
                    "ThroughPass",
                    "Cross",
                    "Shoot",
                    "KeeperSave",
                    "Goal"
                };

                foreach (var token in expectedTokens)
                {
                    if (!replayLog.Any(line => line.IndexOf(token, StringComparison.OrdinalIgnoreCase) >= 0))
                    {
                        scriptedReplay.Errors.Add("Missing replay command log for " + token + ".");
                    }
                }

                var goalLogIndex = Array.FindIndex(replayLog, line =>
                    line.IndexOf("Command -> Goal", StringComparison.OrdinalIgnoreCase) >= 0);
                var resetAfterGoal = goalLogIndex >= 0 &&
                                     replayLog.Skip(goalLogIndex + 1).Any(line =>
                                         line.IndexOf("Command -> ResetKickoff", StringComparison.OrdinalIgnoreCase) >= 0);
                if (!resetAfterGoal)
                {
                    scriptedReplay.Errors.Add("No ResetKickoff command was logged after the first Goal command.");
                }

                var expectedHomeScore = replayStartHomeScore + 1;
                if (GtexScoreAuthority.Current.homeScore != expectedHomeScore)
                {
                    scriptedReplay.Errors.Add(
                        "Scripted replay home score was " + GtexScoreAuthority.Current.homeScore +
                        "; expected " + expectedHomeScore + ".");
                }

                if (replayCaptureIndex < replayCaptureTimes.Length)
                {
                    scriptedReplay.Errors.Add("Scripted replay did not finish all expected screenshot checkpoints.");
                }

                scriptedReplay.Notes.Add("CommandLogCount=" + replayLog.Length);
                scriptedReplay.Notes.Add("ExternalPlaybackEnabled=" + (MatchManager.Current != null && MatchManager.Current.ExternalPlaybackEnabled));
                scriptedReplay.Notes.Add("Score=" + GtexScoreAuthority.Current.homeScore + "-" + GtexScoreAuthority.Current.awayScore);
                scriptedReplay.Notes.Add("ReplayStartHomeScore=" + replayStartHomeScore);
                scriptedReplay.Notes.Add("AcceptanceReplaySucceeded=" + director.ScriptedAcceptanceReplaySucceeded);

                scriptedReplay.Passed =
                    !externalPlaybackObserved &&
                    !scoreMismatchObserved &&
                    !disallowedLogObserved &&
                    scriptedReplay.Errors.Count == 0;
                scriptedReplay.Summary = scriptedReplay.Passed
                    ? "Scripted replay exercised the original simulator command path without transform-playback authority taking over."
                    : "Scripted replay exposed command-path or authority issues.";

                ExitCurrentPlaySession();
            }

            private void UpdateLocalSimSession()
            {
                if (!TryResolveRuntime(out var director))
                {
                    if (Time.realtimeSinceStartupAsDouble - sessionStartedAt >= BootTimeoutSeconds)
                    {
                        localSim.Errors.Add("Original visual runtime did not become ready before the local sim feed.");
                        localSim.Summary = "Local sim feed could not start because the scene never became ready.";
                        ExitCurrentPlaySession();
                    }

                    return;
                }

                if (!runtimeReadyObserved)
                {
                    runtimeReadyObserved = true;
                    readyObservedAt = Time.realtimeSinceStartupAsDouble;
                    EnableVisualCommandLogging(director);
                    director.StartLocalSimulationFeed();
                    localSimStarted = true;
                    localSimStartedAt = Time.realtimeSinceStartupAsDouble;
                    Trace("LocalSimReady");
                }

                TrackSharedGuards(localSim);

                if (!localSimStarted)
                {
                    return;
                }

                var score = GtexScoreAuthority.Current;
                foreach (var threshold in localMinuteThresholds)
                {
                    if (score.minute >= threshold && localMinuteCaptures.Add(threshold))
                    {
                        CaptureScreenshot(localSim, "C_local_sim_" + threshold.ToString("00") + "m");
                    }
                }

                var engine = ResolveLocalSimEngine(director);
                if (engine != null)
                {
                    if (engine.State == GtexSimState.HalfTime || engine.Clock.CurrentMatchMinute >= 45f)
                    {
                        localHalfReached = true;
                    }

                    if (engine.State == GtexSimState.FullTime || engine.Clock.CurrentMatchMinute >= 90f)
                    {
                        localFullTimeReached = true;
                    }
                }

                if (!localHalfReached && score.minute >= 45f)
                {
                    localHalfReached = true;
                }

                if (!localFullTimeReached && score.minute >= 90f)
                {
                    localFullTimeReached = true;
                }

                if (!localFullTimeReached &&
                    Time.realtimeSinceStartupAsDouble - localSimStartedAt < LocalSimTimeoutSeconds)
                {
                    return;
                }

                if (!localHalfReached)
                {
                    localSim.Errors.Add("Local sim feed did not clearly reach halftime.");
                }

                if (!localFullTimeReached)
                {
                    localSim.Errors.Add("Local sim feed did not reach fulltime before timeout.");
                }

                foreach (var threshold in localMinuteThresholds)
                {
                    if (!localMinuteCaptures.Contains(threshold))
                    {
                        localSim.Errors.Add("Missing local sim screenshot near " + threshold + "'.");
                    }
                }

                localSim.Notes.Add("HalfReached=" + localHalfReached);
                localSim.Notes.Add("FullTimeReached=" + localFullTimeReached);
                localSim.Notes.Add("FinalScore=" + score.homeScore + "-" + score.awayScore);
                localSim.Notes.Add("FinalMinute=" + score.minute.ToString("0.0"));

                localSim.Passed =
                    localHalfReached &&
                    localFullTimeReached &&
                    !externalPlaybackObserved &&
                    !scoreMismatchObserved &&
                    !disallowedLogObserved &&
                    localSim.Errors.Count == 0;
                localSim.Summary = localSim.Passed
                    ? "Local sim feed reached half and full time through the original visual runtime with GTEX score authority intact."
                    : "Local sim feed failed one or more halftime/fulltime or authority checks.";

                ExitCurrentPlaySession();
            }

            private void UpdateLiveFeedSession()
            {
                TrackSharedGuards(liveFeed);
                if (UnityEngine.Object.FindFirstObjectByType<GtexMatchRuntime>() != null ||
                    UnityEngine.Object.FindFirstObjectByType<GtexSimRuntimeHost>() != null)
                {
                    liveRuntimeObjectObserved = true;
                    if (!liveFeed.Errors.Contains("GtexMatchRuntime or GtexSimRuntimeHost existed during the live-feed OVR session."))
                    {
                        liveFeed.Errors.Add("GtexMatchRuntime or GtexSimRuntimeHost existed during the live-feed OVR session.");
                    }
                }

                if (!string.IsNullOrWhiteSpace(liveFeedListenerFailure) &&
                    !liveFeed.Errors.Contains("Live-feed listener failed: " + liveFeedListenerFailure))
                {
                    liveFeed.Errors.Add("Live-feed listener failed: " + liveFeedListenerFailure);
                }

                if (!liveFeedStarted && TryResolveRuntime(out var director))
                {
                    runtimeReadyObserved = true;
                    EnableVisualCommandLogging(director);
                    liveFeedStarted = true;
                    Trace("LiveFeedReady port=" + liveFeedPort);
                }

                var sessionLogs = GetSessionLogs();
                var endMatchLogged = sessionLogs.Any(line =>
                    line.IndexOf("[GTEX VisualBridge] Command -> EndMatch", StringComparison.OrdinalIgnoreCase) >= 0);
                var timedOut = EditorApplication.timeSinceStartup - sessionStartedAt >= LiveFeedTimeoutSeconds;
                if (!endMatchLogged && !timedOut)
                {
                    return;
                }

                if (!endMatchLogged)
                {
                    liveFeed.Errors.Add("Live backend feed did not log EndMatch before the 60-second timeout.");
                }

                var commandLogs = sessionLogs
                    .Where(line => line.IndexOf("[GTEX VisualBridge] Command ->", StringComparison.OrdinalIgnoreCase) >= 0)
                    .ToArray();
                var expectedTokens = new[]
                {
                    "AssignPossession",
                    "Pass",
                    "Shoot",
                    "KeeperSave",
                    "Goal",
                    "EndHalf",
                    "EndMatch"
                };
                foreach (var token in expectedTokens)
                {
                    if (!commandLogs.Any(line => line.IndexOf(token, StringComparison.OrdinalIgnoreCase) >= 0))
                    {
                        liveFeed.Errors.Add("Missing live-feed command log for " + token + ".");
                    }
                }

                var score = GtexScoreAuthority.Current;
                var requestCount = Interlocked.CompareExchange(ref liveFeedRequestCount, 0, 0);
                if (score.homeScore != 1 || score.awayScore != 0)
                {
                    liveFeed.Errors.Add("Live backend feed final score was " + score.homeScore + "-" + score.awayScore + "; expected 1-0.");
                }

                if (requestCount < 8)
                {
                    liveFeed.Errors.Add("Live backend feed received " + requestCount + " requests; expected at least 8.");
                }

                if (sessionLogs.Any(line =>
                        line.IndexOf("Live feed poll failed", StringComparison.OrdinalIgnoreCase) >= 0))
                {
                    liveFeed.Errors.Add("A Live feed poll failed log was observed.");
                }

                liveFeed.Notes.Add("ListenerPort=" + liveFeedPort);
                liveFeed.Notes.Add("RequestCount=" + requestCount);
                liveFeed.Notes.Add("FinalScore=" + score.homeScore + "-" + score.awayScore);
                liveFeed.Notes.Add("RuntimeObjectGuardTriggered=" + liveRuntimeObjectObserved);
                liveFeed.Notes.Add("EndMatchLogged=" + endMatchLogged);
                liveFeed.Passed =
                    endMatchLogged &&
                    requestCount >= 8 &&
                    score.homeScore == 1 &&
                    score.awayScore == 0 &&
                    !externalPlaybackObserved &&
                    !scoreMismatchObserved &&
                    !disallowedLogObserved &&
                    !liveRuntimeObjectObserved &&
                    liveFeed.Errors.Count == 0;
                liveFeed.Summary = liveFeed.Passed
                    ? "The original visual runtime consumed the scripted local HTTP feed through fulltime without live transform or simulation runtime hosts."
                    : "Live backend feed failed one or more command, score, transport, or runtime-isolation checks.";

                StopLiveFeedListener();
                ExitCurrentPlaySession();
            }

            private bool TryResolveRuntime(out GtexVisualMatchDirector director)
            {
                director = UnityEngine.Object.FindFirstObjectByType<GtexVisualMatchDirector>();
                return director != null && director.IsRuntimeReady && MatchManager.Current != null;
            }

            private void TrackSharedGuards(SectionResult section)
            {
                if (MatchManager.Current != null && MatchManager.Current.ExternalPlaybackEnabled)
                {
                    externalPlaybackObserved = true;
                }

                if (MatchManager.Current != null)
                {
                    var score = GtexScoreAuthority.Current;
                    if (MatchManager.Current.homeTeamScore != score.homeScore ||
                        MatchManager.Current.awayTeamScore != score.awayScore)
                    {
                        scoreMismatchObserved = true;
                    }
                }

                if (!disallowedLogObserved)
                {
                    disallowedLogObserved = GetSessionLogs().Any(IsDisallowedLogLine);
                }

                if (externalPlaybackObserved &&
                    !section.Errors.Contains("External playback became active in OriginalVisualRuntime."))
                {
                    section.Errors.Add("External playback became active in OriginalVisualRuntime.");
                }

                if (scoreMismatchObserved &&
                    !section.Errors.Contains("GTEX score authority diverged from MatchManager score state."))
                {
                    section.Errors.Add("GTEX score authority diverged from MatchManager score state.");
                }

                if (disallowedLogObserved &&
                    !section.Errors.Contains("Disallowed runtime log noise or exceptions were observed."))
                {
                    section.Errors.Add("Disallowed runtime log noise or exceptions were observed.");
                }
            }

            private void ExitCurrentPlaySession()
            {
                if (waitingForEditMode)
                {
                    return;
                }

                waitingForPlayMode = false;
                waitingForEditMode = true;
                Trace("ExitCurrentPlaySession=" + currentSession);
                EditorApplication.isPlaying = false;
            }

            private void HandlePlayModeStateChanged(PlayModeStateChange change)
            {
                if (change == PlayModeStateChange.EnteredPlayMode)
                {
                    waitingForPlayMode = false;
                    Trace("EnteredPlayMode");
                    return;
                }

                if (change != PlayModeStateChange.EnteredEditMode || !waitingForEditMode)
                {
                    return;
                }

                waitingForEditMode = false;
                Trace("EnteredEditMode=" + currentSession);

                if (unexpectedFailure != null)
                {
                    shouldFinalize = true;
                    FinalizeRun();
                    return;
                }

                switch (currentSession)
                {
                    case SessionKind.NoBackend:
                        BeginSession(SessionKind.ScriptedReplay);
                        break;
                    case SessionKind.ScriptedReplay:
                        BeginSession(SessionKind.LocalSim);
                        break;
                    case SessionKind.LocalSim:
                        BeginSession(SessionKind.LiveFeed);
                        break;
                    case SessionKind.LiveFeed:
                        shouldFinalize = true;
                        FinalizeRun();
                        break;
                }
            }

            private void AbortRun(Exception exception)
            {
                unexpectedFailure = exception;
                Trace("AbortRun=" + exception);
                StopLiveFeedListener();

                var section = GetCurrentSection();
                if (section != null)
                {
                    section.Errors.Add("Unexpected verifier failure: " + exception.Message);
                    section.Summary = "Verification aborted by an unexpected error.";
                }

                if (EditorApplication.isPlaying)
                {
                    ExitCurrentPlaySession();
                    return;
                }

                shouldFinalize = true;
                FinalizeRun();
            }

            private SectionResult GetCurrentSection()
            {
                switch (currentSession)
                {
                    case SessionKind.NoBackend:
                        return editorNoBackend;
                    case SessionKind.ScriptedReplay:
                        return scriptedReplay;
                    case SessionKind.LocalSim:
                        return localSim;
                    case SessionKind.LiveFeed:
                        return liveFeed;
                    default:
                        return null;
                }
            }

            private void FinalizeRun()
            {
                Trace("FinalizeRun.Start");
                Exception finalizeFailure = null;
                try
                {
                    try
                    {
                        StopLiveFeedListener();
                        Trace("FinalizeRun.StopLiveFeedListener");
                    }
                    catch (Exception exception)
                    {
                        finalizeFailure ??= exception;
                        Trace("FinalizeRun.StopLiveFeedListenerFailed=" + exception);
                    }

                    try
                    {
                        RestoreConfig();
                        Trace("FinalizeRun.RestoreConfig");
                    }
                    catch (Exception exception)
                    {
                        finalizeFailure ??= exception;
                        Trace("FinalizeRun.RestoreConfigFailed=" + exception);
                    }

                    try
                    {
                        RestoreEnterPlayModeOptions();
                        Trace("FinalizeRun.RestoreEnterPlayModeOptions");
                    }
                    catch (Exception exception)
                    {
                        finalizeFailure ??= exception;
                        Trace("FinalizeRun.RestoreEnterPlayModeOptionsFailed=" + exception);
                    }

                    try
                    {
                        WriteConsoleLog();
                        Trace("FinalizeRun.WriteConsoleLog");
                    }
                    catch (Exception exception)
                    {
                        finalizeFailure ??= exception;
                        Trace("FinalizeRun.WriteConsoleLogFailed=" + exception);
                    }

                    try
                    {
                        WriteReport();
                        Trace("FinalizeRun.WriteReport");
                    }
                    catch (Exception exception)
                    {
                        finalizeFailure ??= exception;
                        Trace("FinalizeRun.WriteReportFailed=" + exception);
                    }
                }
                finally
                {
                    Application.logMessageReceived -= HandleLogMessage;
                    EditorApplication.playModeStateChanged -= HandlePlayModeStateChanged;
                    EditorApplication.update -= Update;
                }

                if (finalizeFailure != null && unexpectedFailure == null)
                {
                    unexpectedFailure = finalizeFailure;
                }

                var passed =
                    unexpectedFailure == null &&
                    editorNoBackend.Passed &&
                    scriptedReplay.Passed &&
                    localSim.Passed &&
                    liveFeed.Passed;

                var score = GtexScoreAuthority.Current;
                var summary =
                    (passed ? "Original visual runtime verification passed." : "Original visual runtime verification failed.") +
                    " Report=" +
                    reportPath;

                if (passed)
                {
                    GtexRuntimeToolStatus.CompleteSuccess(
                        ActionName,
                        summary,
                        score.homeScore + "-" + score.awayScore,
                        stopwatch.Elapsed.TotalMilliseconds);
                }
                else
                {
                    GtexRuntimeToolStatus.CompleteFailure(
                        ActionName,
                        unexpectedFailure ?? new InvalidOperationException(summary),
                        stopwatch.Elapsed.TotalMilliseconds);
                }

                currentRun = null;
                Environment.SetEnvironmentVariable(AutoStartEnvironmentVariable, null);
                DeleteAutoStartFlagFile();
                Trace("FinalizeRun.ExitQueued passed=" + passed);

                if (exitEditorWhenFinished)
                {
                    EditorApplication.delayCall += () => EditorApplication.Exit(passed ? 0 : 1);
                }
            }

            private void WriteVerificationConfig()
            {
                var config = JsonUtility.FromJson<GtexMatchConfig>(originalConfigJson) ?? new GtexMatchConfig();
                config.enabled = true;
                config.autoStartOnBoot = true;
                config.runtimeMode = "original-visual";
                config.matchId = string.Empty;
                config.environment = "local";
                config.customBaseUrl = string.Empty;
                config.liveAccessToken = string.Empty;
                config.liveRefreshToken = string.Empty;
                config.preserveOriginalScenePresentation = true;
                config.useOriginalMatchCamera = true;
                config.enableStadiumUpgrade = false;
                config.showBroadcastScaffolding = false;
                config.showCrowd = false;
                config.use3DPlaybackForLocalSimulation = false;
                config.simulationTargetDurationMinutes = 1f;
                config.simulationEventCheckWindowMinutes = 1f;
                config.simulationBaseEventChancePerWindow = 0.92f;
                config.simulationRandomSeed = 1337;
                config.verboseLogging = true;

                File.WriteAllText(configPath, NormalizeJson(JsonUtility.ToJson(config, true)));
                AssetDatabase.ImportAsset("Assets/Resources/GTEX/match-config.json", ImportAssetOptions.ForceSynchronousImport);
                AssetDatabase.Refresh();
            }

            private int StartLiveFeedListener()
            {
                var portProbe = new TcpListener(IPAddress.Loopback, 0);
                portProbe.Start();
                int port;
                try
                {
                    port = ((IPEndPoint)portProbe.LocalEndpoint).Port;
                }
                finally
                {
                    portProbe.Stop();
                }

                var frames = BuildLiveFeedFrames();
                liveFeedPayloads = frames.Select(frame => JsonUtility.ToJson(frame)).ToArray();
                liveFeedListenerFailure = string.Empty;
                liveFeedServerStopping = false;
                Interlocked.Exchange(ref liveFeedRequestCount, 0);
                Interlocked.Exchange(ref liveFeedServedFrameCount, 0);
                liveFeedListener = new HttpListener();
                liveFeedListener.Prefixes.Add("http://localhost:" + port + "/");
                liveFeedListener.Start();
                liveFeedServerThread = new Thread(ServeLiveFeedRequests)
                {
                    IsBackground = true,
                    Name = "GTEX OVR live-feed listener"
                };
                liveFeedServerThread.Start();
                return port;
            }

            private void ServeLiveFeedRequests()
            {
                var expectedPath = "/match/ovr-verifier-live/live";
                while (!liveFeedServerStopping && liveFeedListener != null && liveFeedListener.IsListening)
                {
                    HttpListenerContext context;
                    try
                    {
                        context = liveFeedListener.GetContext();
                    }
                    catch (HttpListenerException exception)
                    {
                        if (!liveFeedServerStopping)
                        {
                            liveFeedListenerFailure = exception.Message;
                        }

                        break;
                    }
                    catch (ObjectDisposedException)
                    {
                        break;
                    }

                    Interlocked.Increment(ref liveFeedRequestCount);
                    try
                    {
                        var request = context.Request;
                        if (!string.Equals(request.HttpMethod, "GET", StringComparison.OrdinalIgnoreCase) ||
                            request.Url == null ||
                            !string.Equals(request.Url.AbsolutePath, expectedPath, StringComparison.Ordinal))
                        {
                            context.Response.StatusCode = (int)HttpStatusCode.NotFound;
                            context.Response.Close();
                            continue;
                        }

                        var frameIndex = Interlocked.Increment(ref liveFeedServedFrameCount) - 1;
                        var payload = Encoding.UTF8.GetBytes(liveFeedPayloads[Math.Min(frameIndex, liveFeedPayloads.Length - 1)]);
                        context.Response.StatusCode = (int)HttpStatusCode.OK;
                        context.Response.ContentType = "application/json; charset=utf-8";
                        context.Response.ContentEncoding = Encoding.UTF8;
                        context.Response.ContentLength64 = payload.Length;
                        context.Response.OutputStream.Write(payload, 0, payload.Length);
                        context.Response.Close();
                    }
                    catch (Exception exception)
                    {
                        liveFeedListenerFailure = exception.Message;
                        try
                        {
                            context.Response.Close();
                        }
                        catch
                        {
                        }
                    }
                }
            }

            private void StopLiveFeedListener()
            {
                liveFeedServerStopping = true;
                var listener = liveFeedListener;
                liveFeedListener = null;
                if (listener != null)
                {
                    try
                    {
                        if (listener.IsListening)
                        {
                            listener.Stop();
                        }
                    }
                    catch (Exception exception)
                    {
                        Trace("LiveFeedListener.StopFailed=" + exception.Message);
                    }

                    try
                    {
                        listener.Close();
                    }
                    catch (ObjectDisposedException)
                    {
                    }
                    catch (Exception exception)
                    {
                        Trace("LiveFeedListener.CloseFailed=" + exception.Message);
                    }
                }

                var serverThread = liveFeedServerThread;
                liveFeedServerThread = null;
                if (serverThread != null && serverThread.IsAlive && serverThread != Thread.CurrentThread)
                {
                    serverThread.Join(1000);
                }
            }

            private void WriteLiveFeedVerificationConfig()
            {
                var config = JsonUtility.FromJson<GtexMatchConfig>(originalConfigJson) ?? new GtexMatchConfig();
                config.enabled = true;
                config.autoStartOnBoot = true;
                config.runtimeMode = "original-visual";
                config.matchId = "ovr-verifier-live";
                config.environment = "custom";
                config.customBaseUrl = "http://localhost:" + liveFeedPort;
                config.liveAccessToken = "ovr-verifier-token";
                config.liveRefreshToken = string.Empty;
                config.pollIntervalSeconds = 1.5f;
                config.stopReconnectAfterTerminal = true;
                config.preserveOriginalScenePresentation = true;
                config.useOriginalMatchCamera = true;
                config.enableStadiumUpgrade = false;
                config.showBroadcastScaffolding = false;
                config.showCrowd = false;
                config.use3DPlaybackForLocalSimulation = false;
                config.simulationTargetDurationMinutes = 1f;
                config.simulationEventCheckWindowMinutes = 1f;
                config.simulationBaseEventChancePerWindow = 0.92f;
                config.simulationRandomSeed = 1337;
                config.verboseLogging = true;
                File.WriteAllText(configPath, NormalizeJson(JsonUtility.ToJson(config, true)));
                AssetDatabase.ImportAsset("Assets/Resources/GTEX/match-config.json", ImportAssetOptions.ForceSynchronousImport);
                AssetDatabase.Refresh();
            }

            private static MatchResponse[] BuildLiveFeedFrames()
            {
                var players = BuildLiveFeedPlayers();
                return new[]
                {
                    BuildLiveFeedFrame(players, 0, 1f, "first_half", 0, 0, "home-09", "state_update", string.Empty, string.Empty),
                    BuildLiveFeedFrame(players, 1, 2f, "first_half", 0, 0, "home-09", "pass", "home-09", "home-10"),
                    BuildLiveFeedFrame(players, 2, 3f, "first_half", 0, 0, "home-10", "shot", "home-10", string.Empty),
                    BuildLiveFeedFrame(players, 3, 4f, "first_half", 0, 0, "away-01", "keeper_save", "away-01", "home-10"),
                    BuildLiveFeedFrame(players, 4, 5f, "first_half", 1, 0, "home-10", "goal", "home-10", string.Empty),
                    BuildLiveFeedFrame(players, 5, 45f, "halftime", 1, 0, "home-10", "state_update", string.Empty, string.Empty),
                    BuildLiveFeedFrame(players, 6, 46f, "second_half", 1, 0, "home-10", "state_update", string.Empty, string.Empty),
                    BuildLiveFeedFrame(players, 7, 90f, "fulltime", 1, 0, "home-10", "state_update", string.Empty, string.Empty, true)
                };
            }

            private static PlayerPosition[] BuildLiveFeedPlayers()
            {
                var players = new List<PlayerPosition>(22);
                var sides = new[] { "home", "away" };
                foreach (var side in sides)
                {
                    for (var shirtNumber = 1; shirtNumber <= 11; shirtNumber += 1)
                    {
                        var playerId = side + "-" + shirtNumber.ToString("00");
                        players.Add(new PlayerPosition
                        {
                            entityId = playerId,
                            playerId = playerId,
                            teamId = side,
                            teamSide = side,
                            label = side + " player " + shirtNumber,
                            role = shirtNumber == 1 ? "goalkeeper" : "outfield",
                            line = shirtNumber == 1 ? "goalkeeper" : "field",
                            shirtNumber = shirtNumber,
                            active = true,
                            x = side == "home" ? 20f + shirtNumber : 85f - shirtNumber,
                            z = shirtNumber - 6f
                        });
                    }
                }

                return players.ToArray();
            }

            private static MatchResponse BuildLiveFeedFrame(
                PlayerPosition[] players,
                int frameNumber,
                float minute,
                string phase,
                int homeScore,
                int awayScore,
                string ballOwner,
                string eventType,
                string primaryPlayerId,
                string secondaryPlayerId,
                bool terminal = false)
            {
                var eventId = "ovr-live-event-" + frameNumber;
                var eventRecord = new FStudio.GTEX.Event
                {
                    id = eventId,
                    type = eventType,
                    sequence = frameNumber + 1,
                    minute = (int)minute,
                    clockLabel = ((int)minute).ToString(),
                    teamId = primaryPlayerId.StartsWith("away-", StringComparison.OrdinalIgnoreCase) ? "away" : "home",
                    primaryPlayerId = primaryPlayerId,
                    secondaryPlayerId = secondaryPlayerId,
                    homeScore = homeScore,
                    awayScore = awayScore,
                    commentary = "OVR scripted local live-feed frame " + frameNumber
                };
                var ballSide = ballOwner.StartsWith("away-", StringComparison.OrdinalIgnoreCase) ? "away" : "home";
                return new MatchResponse
                {
                    matchId = "ovr-verifier-live",
                    source = "ovr-verifier",
                    status = terminal ? "finished" : "live",
                    frameId = "ovr-live-frame-" + frameNumber,
                    clockMinute = minute,
                    phase = phase,
                    homeScore = homeScore,
                    awayScore = awayScore,
                    possessionSide = ballSide,
                    activeEventId = eventId,
                    players = players,
                    ballPosition = new PlayerPosition
                    {
                        entityId = "ball",
                        playerId = ballOwner,
                        teamId = ballSide,
                        teamSide = ballSide,
                        label = "Ball",
                        isBall = true,
                        hasPossession = true
                    },
                    events = new[] { eventRecord }
                };
            }

            private void RestoreConfig()
            {
                File.WriteAllText(configPath, NormalizeJson(originalConfigJson));
                AssetDatabase.ImportAsset("Assets/Resources/GTEX/match-config.json", ImportAssetOptions.ForceSynchronousImport);
                AssetDatabase.Refresh();
            }

            private void CaptureScreenshot(SectionResult section, string fileStem)
            {
                var path = Path.Combine(screenshotDirectory, fileStem + ".png");
                ScreenCapture.CaptureScreenshot(path);
                section.Screenshots.Add(path);
            }

            private static void EnableVisualCommandLogging(GtexVisualMatchDirector director)
            {
                if (director == null)
                {
                    return;
                }

                var field = typeof(GtexVisualMatchDirector).GetField("logVisualCommands", BindingFlags.Instance | BindingFlags.NonPublic);
                field?.SetValue(director, true);
            }

            private static GtexSimEngine ResolveLocalSimEngine(GtexVisualMatchDirector director)
            {
                if (director == null)
                {
                    return null;
                }

                var field = typeof(GtexVisualMatchDirector).GetField("localSimEngine", BindingFlags.Instance | BindingFlags.NonPublic);
                return field != null ? field.GetValue(director) as GtexSimEngine : null;
            }

            private void HandleLogMessage(string condition, string stackTrace, LogType type)
            {
                var prefix = "[" + type + "]";
                consoleLines.Add(prefix + " " + condition);
                if ((type == LogType.Exception || type == LogType.Error || type == LogType.Assert) &&
                    !string.IsNullOrWhiteSpace(stackTrace))
                {
                    consoleLines.Add(stackTrace);
                }
            }

            private IReadOnlyList<string> GetSessionLogs()
            {
                var startIndex = Mathf.Clamp(sessionConsoleStartIndex, 0, consoleLines.Count);
                return consoleLines.Skip(startIndex).ToArray();
            }

            private bool IsDisallowedLogLine(string line)
            {
                if (string.IsNullOrWhiteSpace(line))
                {
                    return false;
                }

                for (var index = 0; index < disallowedPatterns.Length; index += 1)
                {
                    if (line.IndexOf(disallowedPatterns[index], StringComparison.OrdinalIgnoreCase) >= 0)
                    {
                        return true;
                    }
                }

                return false;
            }

            private void WriteConsoleLog()
            {
                File.WriteAllLines(consoleLogPath, consoleLines);
            }

            private void WriteReport()
            {
                var builder = new StringBuilder();
                builder.AppendLine("# GTEX Original Visual Runtime Verification");
                builder.AppendLine();
                builder.AppendLine("- Generated: " + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"));
                builder.AppendLine("- Duration: " + stopwatch.Elapsed);
                builder.AppendLine("- Console log: `" + consoleLogPath + "`");
                builder.AppendLine("- Screenshot directory: `" + screenshotDirectory + "`");
                builder.AppendLine("- Unexpected verifier failure: " + (unexpectedFailure != null ? unexpectedFailure.Message : "None"));
                builder.AppendLine();

                AppendSection(builder, "A. Editor no-backend test", editorNoBackend);
                AppendSection(builder, "B. Scripted replay", scriptedReplay);
                AppendSection(builder, "C. Local sim feed", localSim);
                AppendSection(builder, "D. Live backend feed", liveFeed);

                File.WriteAllText(reportPath, builder.ToString());
            }

            private static void AppendSection(StringBuilder builder, string heading, SectionResult result)
            {
                builder.AppendLine("## " + heading);
                builder.AppendLine();
                builder.AppendLine("- Result: " + (result.Blocked ? "Blocked" : result.Passed ? "Passed" : "Failed"));
                if (!string.IsNullOrWhiteSpace(result.Summary))
                {
                    builder.AppendLine("- Summary: " + result.Summary);
                }

                if (result.Notes.Count > 0)
                {
                    builder.AppendLine("- Notes:");
                    for (var index = 0; index < result.Notes.Count; index += 1)
                    {
                        builder.AppendLine("  - " + result.Notes[index]);
                    }
                }

                if (result.Errors.Count > 0)
                {
                    builder.AppendLine("- Errors:");
                    for (var index = 0; index < result.Errors.Count; index += 1)
                    {
                        builder.AppendLine("  - " + result.Errors[index]);
                    }
                }

                if (result.Screenshots.Count > 0)
                {
                    builder.AppendLine("- Screenshots:");
                    for (var index = 0; index < result.Screenshots.Count; index += 1)
                    {
                        builder.AppendLine("  - `" + result.Screenshots[index] + "`");
                    }
                }

                builder.AppendLine();
            }

            private static string NormalizeJson(string json)
            {
                return (json ?? string.Empty).Replace("\r\n", "\n").Replace('\r', '\n').TrimEnd() + "\n";
            }

            private void Trace(string message)
            {
                var line = DateTime.Now.ToString("HH:mm:ss.fff") + " " + message + Environment.NewLine;
                File.AppendAllText(traceLogPath, line);
            }
        }

        private static string GetAutoStartFlagPath()
        {
            return Path.GetFullPath(Path.Combine(Application.dataPath, "..", AutoStartFlagFileRelativePath));
        }

        private static void DeleteAutoStartFlagFile()
        {
            var path = GetAutoStartFlagPath();
            if (!File.Exists(path))
            {
                return;
            }

            File.Delete(path);
        }
    }
}
#endif
