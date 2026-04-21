using System;
using FStudio.GTEX.Core;

namespace FStudio.GTEX.Engine
{
    public interface IGtexMatchExecutor
    {
        string Name { get; }

        GtexRuntimeMode RuntimeMode { get; }

        bool IsRuntimeActive();

        bool TryAutoStart(GtexMatchConfig config, bool allowLocalSimulationInBatchMode, Action<string> logger);
    }
}
