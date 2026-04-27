#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
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
            private const double ReplayObserveSeconds = 15d;
            private const double LocalSimTimeoutSeconds = 120d;

            private enum SessionKind
            {
                None,
                NoBackend,
                ScriptedReplay,
                LocalSim
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
            private float sessionStartMatchMinute;
            private float lastObservedMatchMinute;

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
                    director.RunScriptedCommandReplay();
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

                if (replayElapsed < ReplayObserveSeconds)
                {
                    return;
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

                if (replayCaptureIndex < replayCaptureTimes.Length)
                {
                    scriptedReplay.Errors.Add("Scripted replay did not finish all expected screenshot checkpoints.");
                }

                scriptedReplay.Notes.Add("CommandLogCount=" + replayLog.Length);
                scriptedReplay.Notes.Add("ExternalPlaybackEnabled=" + (MatchManager.Current != null && MatchManager.Current.ExternalPlaybackEnabled));
                scriptedReplay.Notes.Add("Score=" + GtexScoreAuthority.Current.homeScore + "-" + GtexScoreAuthority.Current.awayScore);

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
                        shouldFinalize = true;
                        FinalizeRun();
                        break;
                }
            }

            private void AbortRun(Exception exception)
            {
                unexpectedFailure = exception;
                Trace("AbortRun=" + exception);

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
                    localSim.Passed;

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
