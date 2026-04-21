using System;
using FStudio.GTEX.Core;
using FStudio.GTEX.Simulation;
using UnityEngine;

namespace FStudio.GTEX.Engine
{
    public sealed class GtexLegacySimulationExecutor : IGtexMatchExecutor
    {
        public string Name => "LegacySimulationBootstrap";

        public GtexRuntimeMode RuntimeMode => GtexRuntimeMode.LocalSimulation;

        public bool IsRuntimeActive()
        {
            return UnityEngine.Object.FindFirstObjectByType<GtexSimRuntimeHost>() != null;
        }

        public bool TryAutoStart(GtexMatchConfig config, bool allowLocalSimulationInBatchMode, Action<string> logger)
        {
            logger?.Invoke("Delegating local simulation startup to GtexSimRuntimeHost.");
            return GtexSimRuntimeHost.TryAutoStart(config, allowLocalSimulationInBatchMode);
        }
    }
}
