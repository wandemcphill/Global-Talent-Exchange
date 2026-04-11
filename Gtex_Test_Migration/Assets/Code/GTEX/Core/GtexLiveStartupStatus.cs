using System;

namespace FStudio.GTEX.Core
{
    public enum GtexLiveStartupSeverity
    {
        None,
        Warning,
        Error
    }

    public static class GtexLiveStartupStatus
    {
        public static GtexLiveStartupSeverity Severity { get; private set; }

        public static string Code { get; private set; } = string.Empty;

        public static string Title { get; private set; } = string.Empty;

        public static string Message { get; private set; } = string.Empty;

        public static string ActionHint { get; private set; } = string.Empty;

        public static string SourcePath { get; private set; } = string.Empty;

        public static DateTime UpdatedAtUtc { get; private set; } = DateTime.MinValue;

        public static bool HasIssue =>
            Severity != GtexLiveStartupSeverity.None &&
            !string.IsNullOrWhiteSpace(Message);

        public static bool HasBlockingIssue => Severity == GtexLiveStartupSeverity.Error;

        public static void Clear()
        {
            Severity = GtexLiveStartupSeverity.None;
            Code = string.Empty;
            Title = string.Empty;
            Message = string.Empty;
            ActionHint = string.Empty;
            SourcePath = string.Empty;
            UpdatedAtUtc = DateTime.UtcNow;
        }

        public static void ReportWarning(
            string code,
            string title,
            string message,
            string actionHint = "",
            string sourcePath = "")
        {
            Set(
                GtexLiveStartupSeverity.Warning,
                code,
                title,
                message,
                actionHint,
                sourcePath);
        }

        public static void ReportError(
            string code,
            string title,
            string message,
            string actionHint = "",
            string sourcePath = "")
        {
            Set(
                GtexLiveStartupSeverity.Error,
                code,
                title,
                message,
                actionHint,
                sourcePath);
        }

        private static void Set(
            GtexLiveStartupSeverity severity,
            string code,
            string title,
            string message,
            string actionHint,
            string sourcePath)
        {
            Severity = severity;
            Code = code ?? string.Empty;
            Title = title ?? string.Empty;
            Message = message ?? string.Empty;
            ActionHint = actionHint ?? string.Empty;
            SourcePath = sourcePath ?? string.Empty;
            UpdatedAtUtc = DateTime.UtcNow;
        }
    }
}
