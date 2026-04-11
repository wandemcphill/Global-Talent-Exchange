using FStudio.GTEX.Simulation;
using UnityEngine;

namespace FStudio.GTEX.Core
{
    public static class GtexRuntimeBootstrap
    {
        public static bool TryAutoStart()
        {
            return TryAutoStart(null);
        }

        public static bool TryAutoStart(GtexMatchConfig config, bool allowLocalSimulationInBatchMode = false)
        {
            var resolvedConfig = config ?? GtexMatchConfigLoader.Load();
            if (resolvedConfig == null || !resolvedConfig.CanAutoStartSelectedRuntime)
            {
                return false;
            }

            var runtimeMode = resolvedConfig.ResolveRuntimeMode();
            Debug.Log("[GTEX] Runtime bootstrap requested -> " + runtimeMode + ".");

            if (runtimeMode == GtexRuntimeMode.LocalSimulation)
            {
                return GtexSimRuntimeHost.TryAutoStart(resolvedConfig, allowLocalSimulationInBatchMode);
            }

            return GtexMatchRuntime.TryAutoStart(resolvedConfig);
        }
    }
}
