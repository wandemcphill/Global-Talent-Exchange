using System;
using FStudio.GTEX.Core;
using UnityEngine;

namespace FStudio.GTEX.Engine
{
    public sealed class GtexLegacyLiveMatchExecutor : IGtexMatchExecutor
    {
        public string Name => "LegacyLiveBootstrap";

        public GtexRuntimeMode RuntimeMode => GtexRuntimeMode.LivePlayback;

        public bool IsRuntimeActive()
        {
            return UnityEngine.Object.FindFirstObjectByType<GtexMatchRuntime>() != null;
        }

        public bool TryAutoStart(GtexMatchConfig config, bool allowLocalSimulationInBatchMode, Action<string> logger)
        {
            logger?.Invoke("Delegating live playback startup to GtexMatchRuntime.");
            return GtexMatchRuntime.TryAutoStart(config);
        }
    }
}
