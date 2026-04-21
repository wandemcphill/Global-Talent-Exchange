using System;
using FStudio.GTEX.Core;

namespace FStudio.GTEX.Engine
{
    public readonly struct GtexMatchEvent
    {
        public GtexMatchEvent(string name, string message, GtexRuntimeMode runtimeMode, GtexMatchPhase phase)
        {
            Name = name ?? string.Empty;
            Message = message ?? string.Empty;
            RuntimeMode = runtimeMode;
            Phase = phase;
            OccurredAtUtc = DateTime.UtcNow;
        }

        public string Name { get; }

        public string Message { get; }

        public GtexRuntimeMode RuntimeMode { get; }

        public GtexMatchPhase Phase { get; }

        public DateTime OccurredAtUtc { get; }
    }
}
