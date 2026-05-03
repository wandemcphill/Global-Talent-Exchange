#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using Stopwatch = System.Diagnostics.Stopwatch;
using FStudio.GTEX;
using FStudio.GTEX.Core;
using FStudio.GTEX.VisualBridge;
using FStudio.MatchEngine;
using FStudio.MatchEngine.Balls;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace FStudio.GTEX.Editor
{
    public static class GtexSequenceIntegrityLockVerifier
    {
        private static VerificationRun currentRun;

        [MenuItem("Tools/GTEX/Runtime/Verify Sequence Integrity Lock")]
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
                throw new InvalidOperationException("Sequence integrity lock verification is already running.");
            }

            currentRun = new VerificationRun(exitEditorWhenFinished);
            currentRun.Start();
        }

        private sealed class VerificationRun
        {
            private const string ActionName = "Sequence integrity lock verification";
            private const double TimeoutSeconds = 75d;

            private readonly bool exitEditorWhenFinished;
            private readonly Stopwatch stopwatch = Stopwatch.StartNew();
            private readonly List<string> consoleLines = new List<string>();
            private readonly string outputDirectory;
            private readonly string consoleLogPath;
            private readonly string reportPath;
            private readonly string configPath;
            private readonly string originalConfigJson;

            private bool waitingForEditMode;
            private bool runtimeReadyObserved;
            private bool sequenceStarted;
            private bool sequenceCompleted;
            private bool ballPresentAtCompletion;
            private bool externalPlaybackAtCompletion;
            private Exception unexpectedFailure;
            private double startedAt;

            public VerificationRun(bool exitEditorWhenFinished)
            {
                this.exitEditorWhenFinished = exitEditorWhenFinished;

                var projectRoot = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
                var stamp = DateTime.Now.ToString("yyyyMMdd-HHmmss");
                outputDirectory = Path.Combine(projectRoot, "tmp", "sequence-integrity-lock-verification", stamp);
                consoleLogPath = Path.Combine(outputDirectory, "console.log");
                reportPath = Path.Combine(outputDirectory, "report.md");
                configPath = GtexRuntimeModeTools.AbsoluteConfigPath;
                originalConfigJson = File.Exists(configPath) ? File.ReadAllText(configPath) : string.Empty;
            }

            public void Start()
            {
                Directory.CreateDirectory(outputDirectory);
                GtexRuntimeToolStatus.Begin(ActionName);
                Debug.Log("[GTEX LOCK VERIFY] Starting sequence integrity lock verification.");

                Application.logMessageReceived += HandleLogMessage;
                EditorApplication.playModeStateChanged += HandlePlayModeStateChanged;
                EditorApplication.update += Update;

                WriteVerificationConfig();
                EditorSceneManager.OpenScene(GtexSceneLoader.OriginalVisualRuntimeScenePath, OpenSceneMode.Single);
                startedAt = EditorApplication.timeSinceStartup;
                EditorApplication.delayCall += () => EditorApplication.isPlaying = true;
            }

            private void Update()
            {
                if (!EditorApplication.isPlaying || waitingForEditMode)
                {
                    return;
                }

                try
                {
                    if (EditorApplication.timeSinceStartup - startedAt > TimeoutSeconds)
                    {
                        FinishWithFailure("Timed out before controlled sequence completed.");
                        return;
                    }

                    var director = UnityEngine.Object.FindFirstObjectByType<GtexVisualMatchDirector>();
                    if (director == null)
                    {
                        return;
                    }

                    if (!runtimeReadyObserved && director.IsRuntimeReady)
                    {
                        runtimeReadyObserved = true;
                        Debug.Log("[GTEX LOCK VERIFY] Runtime ready observed.");
                        director.RunScriptedCommandReplay();
                        sequenceStarted = true;
                        return;
                    }

                    if (!sequenceStarted)
                    {
                        return;
                    }

                    if (HasLine("[GTEX Sequence] Aborted") ||
                        HasLine("[GTEX Sequence] Abort") ||
                        HasLine("Action failed") ||
                        HasLine("MissingReferenceException") ||
                        HasLine("NullReferenceException") ||
                        HasLine("DefaultScene"))
                    {
                        FinishWithFailure("Controlled sequence produced an abort/error log.");
                        return;
                    }

                    if (HasLine("[GTEX Sequence] Complete id=central-buildup-shot") ||
                        HasLine("sequence_central-buildup-shot_complete"))
                    {
                        sequenceCompleted = true;
                        ballPresentAtCompletion = Ball.Current != null;
                        externalPlaybackAtCompletion = MatchManager.Current != null && MatchManager.Current.ExternalPlaybackEnabled;
                        Finish();
                    }
                }
                catch (Exception exception)
                {
                    unexpectedFailure = exception;
                    FinishWithFailure("Verifier exception: " + exception.Message);
                }
            }

            private void FinishWithFailure(string reason)
            {
                Debug.LogError("[GTEX LOCK VERIFY] Failed: " + reason);
                Finish();
            }

            private void Finish()
            {
                if (waitingForEditMode)
                {
                    return;
                }

                waitingForEditMode = true;
                EditorApplication.isPlaying = false;
            }

            private void HandlePlayModeStateChanged(PlayModeStateChange change)
            {
                if (change != PlayModeStateChange.EnteredEditMode || !waitingForEditMode)
                {
                    return;
                }

                FinalizeRun();
            }

            private void FinalizeRun()
            {
                Application.logMessageReceived -= HandleLogMessage;
                EditorApplication.playModeStateChanged -= HandlePlayModeStateChanged;
                EditorApplication.update -= Update;

                var passed = Evaluate(out var summary);

                try
                {
                    RestoreConfig();
                    File.WriteAllLines(consoleLogPath, consoleLines);
                    WriteReport(passed, summary);
                }
                catch (Exception exception)
                {
                    passed = false;
                    summary = "Failed to write verifier output: " + exception.Message;
                    unexpectedFailure ??= exception;
                }

                stopwatch.Stop();
                if (passed)
                {
                    GtexRuntimeToolStatus.CompleteSuccess(
                        ActionName,
                        summary + " Report=" + reportPath,
                        string.Empty,
                        stopwatch.Elapsed.TotalMilliseconds);
                    Debug.Log("[GTEX LOCK VERIFY] Passed. Report=" + reportPath);
                }
                else
                {
                    GtexRuntimeToolStatus.CompleteFailure(
                        ActionName,
                        unexpectedFailure ?? new InvalidOperationException(summary + " Report=" + reportPath),
                        stopwatch.Elapsed.TotalMilliseconds);
                    Debug.LogError("[GTEX LOCK VERIFY] Failed. " + summary + " Report=" + reportPath);
                }

                currentRun = null;
                if (exitEditorWhenFinished)
                {
                    EditorApplication.delayCall += () => EditorApplication.Exit(passed ? 0 : 1);
                }
            }

            private bool Evaluate(out string summary)
            {
                var lockPlayerCount = consoleLines.Count(line => line.Contains("[GTEX LOCK] Player locked:"));
                var hasBallRestriction = HasLine("[GTEX LOCK] Ball interaction restricted");
                var hasIntegrityRelease = HasLine("[GTEX LOCK] Sequence integrity maintained");

                var errors = new List<string>();
                if (!runtimeReadyObserved)
                {
                    errors.Add("runtime ready was not observed");
                }

                if (!sequenceStarted)
                {
                    errors.Add("controlled scripted sequence was not started");
                }

                if (!sequenceCompleted)
                {
                    errors.Add("controlled scripted sequence did not complete");
                }

                if (lockPlayerCount < 3)
                {
                    errors.Add("expected at least three player lock logs, found " + lockPlayerCount);
                }

                if (!hasBallRestriction)
                {
                    errors.Add("ball interaction restriction log missing");
                }

                if (!hasIntegrityRelease)
                {
                    errors.Add("sequence integrity release log missing");
                }

                if (externalPlaybackAtCompletion)
                {
                    errors.Add("external transform playback is enabled");
                }

                if (!ballPresentAtCompletion)
                {
                    errors.Add("ball reference missing at sequence completion");
                }

                if (unexpectedFailure != null)
                {
                    errors.Add("unexpected failure: " + unexpectedFailure.Message);
                }

                summary = errors.Count == 0
                    ? "Sequence integrity lock held through central-buildup-shot."
                    : "Sequence integrity lock failed: " + string.Join("; ", errors) + ".";
                return errors.Count == 0;
            }

            private void WriteVerificationConfig()
            {
                var config = string.IsNullOrWhiteSpace(originalConfigJson)
                    ? new GtexMatchConfig()
                    : JsonUtility.FromJson<GtexMatchConfig>(originalConfigJson) ?? new GtexMatchConfig();

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
                config.EnsureDefaults();

                File.WriteAllText(configPath, JsonUtility.ToJson(config, true));
            }

            private void RestoreConfig()
            {
                if (!string.IsNullOrWhiteSpace(originalConfigJson))
                {
                    File.WriteAllText(configPath, originalConfigJson);
                }
            }

            private void WriteReport(bool passed, string summary)
            {
                var builder = new StringBuilder();
                builder.AppendLine("# GTEX Sequence Integrity Lock Verification");
                builder.AppendLine();
                builder.AppendLine("- Result: " + (passed ? "Passed" : "Failed"));
                builder.AppendLine("- Summary: " + summary);
                builder.AppendLine("- RuntimeReadyObserved: " + runtimeReadyObserved);
                builder.AppendLine("- SequenceStarted: " + sequenceStarted);
                builder.AppendLine("- SequenceCompleted: " + sequenceCompleted);
                builder.AppendLine("- PlayerLockLogCount: " + consoleLines.Count(line => line.Contains("[GTEX LOCK] Player locked:")));
                builder.AppendLine("- BallInteractionRestricted: " + HasLine("[GTEX LOCK] Ball interaction restricted"));
                builder.AppendLine("- SequenceIntegrityMaintained: " + HasLine("[GTEX LOCK] Sequence integrity maintained"));
                builder.AppendLine("- BallPresentAtCompletion: " + ballPresentAtCompletion);
                builder.AppendLine("- ExternalPlaybackEnabledAtCompletion: " + externalPlaybackAtCompletion);
                builder.AppendLine("- Console log: `" + consoleLogPath + "`");
                File.WriteAllText(reportPath, builder.ToString());
            }

            private void HandleLogMessage(string condition, string stackTrace, LogType type)
            {
                consoleLines.Add(condition);
                if (type == LogType.Exception && !string.IsNullOrWhiteSpace(stackTrace))
                {
                    consoleLines.Add(stackTrace);
                }
            }

            private bool HasLine(string token)
            {
                return consoleLines.Any(line => line.IndexOf(token, StringComparison.OrdinalIgnoreCase) >= 0);
            }
        }
    }
}
#endif
