#if UNITY_EDITOR
using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace FStudio.GTEX.Editor
{
    public static class Gtex3DFullSessionVerifier
    {
        [Serializable]
        private sealed class FullSessionSummary
        {
            public string executable;
            public string player_log;
            public string runtime_trace;
            public string[] screenshot_paths;
            public bool bootstrap_seen;
            public bool motion_seen;
            public bool ball_motion_seen;
            public bool camera_stable;
            public bool linear_kinematic_warning_seen;
            public bool angular_kinematic_warning_seen;
            public bool passed;
            public TraceTimeline trace_timeline;
            public ServerSummary server_summary;
        }

        [Serializable]
        private sealed class TraceTimeline
        {
            public int count;
            public float last_minute;
            public bool clock_non_decreasing;
            public bool score_non_decreasing;
            public bool mid_session_seen;
            public bool late_session_seen;
            public bool fulltime_seen;
        }

        [Serializable]
        private sealed class ServerSummary
        {
            public int websocket_connections;
            public int frames_served;
            public bool final_frame_sent;
            public string[] phase_sequence;
            public string[] score_timeline;
            public string[] camera_presets_seen;
        }

        [MenuItem("Tools/GTEX/Simulation/Verify 3D Full Session Summary")]
        public static void VerifyFromEditorMenu()
        {
            Verify();
        }

        public static void VerifyFromCommandLine()
        {
            Verify();
        }

        private static void Verify()
        {
            const string actionName = "3D full-session summary check";
            var stopwatch = Stopwatch.StartNew();
            GtexRuntimeToolStatus.Begin(actionName);

            try
            {
                var summaryPath = ResolveSummaryPath();
                if (!File.Exists(summaryPath))
                {
                    throw new FileNotFoundException(
                        "Full-session summary file is missing. Run tools/run_gtex_full_session_validation.ps1 first.",
                        summaryPath);
                }

                var json = File.ReadAllText(summaryPath);
                var summary = JsonUtility.FromJson<FullSessionSummary>(json);
                if (summary == null)
                {
                    throw new InvalidOperationException("Could not parse the 3D full-session summary JSON.");
                }

                AssertTrue(summary.passed, "Full-session summary reports passed=false.");
                AssertTrue(summary.bootstrap_seen, "Bootstrap did not complete in the full-session summary.");
                AssertTrue(summary.motion_seen, "Player motion was not detected in the full-session summary.");
                AssertTrue(summary.ball_motion_seen, "Ball motion was not detected in the full-session summary.");
                AssertTrue(summary.camera_stable, "Camera stability checks did not pass.");
                AssertTrue(!summary.linear_kinematic_warning_seen, "Linear kinematic warning reappeared.");
                AssertTrue(!summary.angular_kinematic_warning_seen, "Angular kinematic warning reappeared.");
                AssertNotNull(summary.trace_timeline, "Trace timeline is missing from the full-session summary.");
                AssertTrue(summary.trace_timeline.count >= 7, "Trace timeline is too short for a kickoff-to-fulltime run.");
                AssertTrue(summary.trace_timeline.clock_non_decreasing, "Clock regressed during full-session playback.");
                AssertTrue(summary.trace_timeline.score_non_decreasing, "Score regressed during full-session playback.");
                AssertTrue(summary.trace_timeline.mid_session_seen, "Mid-session marker was not observed.");
                AssertTrue(summary.trace_timeline.late_session_seen, "Late-session marker was not observed.");
                AssertTrue(summary.trace_timeline.fulltime_seen, "Fulltime marker was not observed.");
                AssertTrue(summary.trace_timeline.last_minute >= 90f, "Playback did not reach fulltime.");

                AssertNotNull(summary.server_summary, "Server summary is missing from the full-session summary.");
                AssertTrue(summary.server_summary.final_frame_sent, "Server never emitted the fulltime frame.");
                AssertTrue(summary.server_summary.websocket_connections <= 1, "Terminal reconnect churn reappeared in websocket usage.");
                AssertContains(summary.server_summary.phase_sequence, "first_half", "Missing first_half phase.");
                AssertContains(summary.server_summary.phase_sequence, "halftime", "Missing halftime phase.");
                AssertContains(summary.server_summary.phase_sequence, "second_half", "Missing second_half phase.");
                AssertContains(summary.server_summary.phase_sequence, "fulltime", "Missing fulltime phase.");
                AssertContains(summary.server_summary.camera_presets_seen, "broadcast", "Broadcast camera preset was not observed.");
                AssertContains(summary.server_summary.camera_presets_seen, "attack_push", "attack_push camera preset was not observed.");
                AssertContains(summary.server_summary.camera_presets_seen, "box_zoom", "box_zoom camera preset was not observed.");

                var screenshotCount = summary.screenshot_paths != null ? summary.screenshot_paths.Length : 0;
                AssertTrue(screenshotCount >= 5, "Expected at least 5 captured screenshots.");
                foreach (var screenshotPath in summary.screenshot_paths ?? Array.Empty<string>())
                {
                    AssertTrue(File.Exists(screenshotPath), "Missing screenshot artifact: " + screenshotPath);
                }

                if (!string.IsNullOrWhiteSpace(summary.runtime_trace) && File.Exists(summary.runtime_trace))
                {
                    var runtimeTrace = File.ReadAllText(summary.runtime_trace);
                    AssertTrue(runtimeTrace.IndexOf("| error |", StringComparison.OrdinalIgnoreCase) < 0, "Runtime trace contains error markers.");
                    AssertTrue(runtimeTrace.IndexOf("| shutdown |", StringComparison.OrdinalIgnoreCase) >= 0, "Runtime trace never recorded shutdown.");
                }

                if (!string.IsNullOrWhiteSpace(summary.player_log) && File.Exists(summary.player_log))
                {
                    var playerLog = File.ReadAllText(summary.player_log);
                    AssertTrue(playerLog.IndexOf("Exception", StringComparison.OrdinalIgnoreCase) < 0, "Player log contains Exception.");
                }

                var finalScore = summary.server_summary.score_timeline != null && summary.server_summary.score_timeline.Length > 0
                    ? summary.server_summary.score_timeline.Last()
                    : string.Empty;
                var resultSummary =
                    "3D full-session summary passed. " +
                    "Frames=" + summary.server_summary.frames_served +
                    ", WebSockets=" + summary.server_summary.websocket_connections +
                    ", FinalScore=" + finalScore + ".";

                stopwatch.Stop();
                GtexRuntimeToolStatus.CompleteSuccess(
                    actionName,
                    resultSummary,
                    finalScore,
                    stopwatch.Elapsed.TotalMilliseconds);

                UnityEngine.Debug.Log("[GTEX 3D Verify] " + resultSummary);
            }
            catch (Exception exception)
            {
                stopwatch.Stop();
                GtexRuntimeToolStatus.CompleteFailure(actionName, exception, stopwatch.Elapsed.TotalMilliseconds);
                throw;
            }
        }

        private static string ResolveSummaryPath()
        {
            return Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "tmp", "gtex_full_session_summary.json"));
        }

        private static void AssertContains(string[] values, string expected, string message)
        {
            if (values == null || Array.IndexOf(values, expected) < 0)
            {
                throw new InvalidOperationException(message);
            }
        }

        private static void AssertNotNull(object value, string message)
        {
            if (value == null)
            {
                throw new InvalidOperationException(message);
            }
        }

        private static void AssertTrue(bool condition, string message)
        {
            if (!condition)
            {
                throw new InvalidOperationException(message);
            }
        }
    }
}
#endif
