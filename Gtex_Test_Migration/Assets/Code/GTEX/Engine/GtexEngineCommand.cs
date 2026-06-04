using System;
using FStudio.GTEX.Core;

namespace FStudio.GTEX.Engine
{
    public enum GtexEngineCommandType
    {
        None,
        AutoStartRuntime,
        StartLivePlayback,
        StartLocalSimulation,
        StartOriginalVisualRuntime,
        StartIllusionRuntime,
        UseLegacyBootstrapFallback
    }

    public readonly struct GtexEngineCommand
    {
        public GtexEngineCommand(GtexEngineCommandType type, GtexRuntimeMode runtimeMode, string reason)
        {
            Type = type;
            RuntimeMode = runtimeMode;
            Reason = reason ?? string.Empty;
            IssuedAtUtc = DateTime.UtcNow;
        }

        public GtexEngineCommandType Type { get; }

        public GtexRuntimeMode RuntimeMode { get; }

        public string Reason { get; }

        public DateTime IssuedAtUtc { get; }

        public override string ToString()
        {
            return Type + " -> " + RuntimeMode + " (" + Reason + ")";
        }
    }
}
