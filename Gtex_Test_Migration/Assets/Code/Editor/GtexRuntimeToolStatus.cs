#if UNITY_EDITOR
using System;

namespace FStudio.GTEX.Editor
{
    public enum GtexRuntimeToolRunState
    {
        NotRun,
        Running,
        Passed,
        Failed
    }

    public static class GtexRuntimeToolStatus
    {
        public static string LastAction { get; private set; } = "None";

        public static GtexRuntimeToolRunState LastState { get; private set; } = GtexRuntimeToolRunState.NotRun;

        public static string LastSummary { get; private set; } = "No GTEX runtime tests have been run in this editor session.";

        public static string LastScoreline { get; private set; } = string.Empty;

        public static double LastDurationMs { get; private set; }

        public static DateTime? LastCompletedAtLocal { get; private set; }

        public static string LastCompletedDisplay =>
            LastCompletedAtLocal.HasValue
                ? LastCompletedAtLocal.Value.ToString("yyyy-MM-dd HH:mm:ss")
                : "Never";

        public static void Begin(string actionName)
        {
            LastAction = actionName ?? "Unnamed action";
            LastState = GtexRuntimeToolRunState.Running;
            LastSummary = LastAction + " is running...";
            LastScoreline = string.Empty;
            LastDurationMs = 0d;
            LastCompletedAtLocal = null;
        }

        public static void CompleteSuccess(string actionName, string summary, string scoreline, double durationMs)
        {
            LastAction = actionName ?? "Unnamed action";
            LastState = GtexRuntimeToolRunState.Passed;
            LastSummary = string.IsNullOrWhiteSpace(summary) ? (LastAction + " passed.") : summary;
            LastScoreline = scoreline ?? string.Empty;
            LastDurationMs = durationMs;
            LastCompletedAtLocal = DateTime.Now;
        }

        public static void CompleteFailure(string actionName, Exception exception, double durationMs)
        {
            LastAction = actionName ?? "Unnamed action";
            LastState = GtexRuntimeToolRunState.Failed;
            LastSummary = exception == null
                ? (LastAction + " failed.")
                : (LastAction + " failed: " + exception.Message);
            LastScoreline = string.Empty;
            LastDurationMs = durationMs;
            LastCompletedAtLocal = DateTime.Now;
        }
    }
}
#endif
