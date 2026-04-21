using FStudio.GTEX;
using FStudio.GTEX.Engine;
using FStudio.GTEX.Simulation;
using FStudio.MatchEngine;
using UnityEngine;

namespace FStudio.GTEX.Core
{
    public static class GtexRuntimeBootstrap
    {
        private static bool livePlaybackRequested;

        public static bool IsLivePlaybackPendingOrActive()
        {
            if (Object.FindFirstObjectByType<GtexMatchRuntime>() != null)
            {
                return true;
            }

            if (MatchManager.Current != null && MatchManager.Current.ExternalPlaybackEnabled)
            {
                return true;
            }

            var state = GtexMatchController.CurrentState;
            if (state.RuntimeMode == GtexRuntimeMode.LivePlayback)
            {
                if (state.RuntimeActive)
                {
                    return true;
                }

                if (state.Phase != GtexMatchPhase.None && state.Phase != GtexMatchPhase.Failed)
                {
                    return true;
                }
            }

            return livePlaybackRequested;
        }

        public static bool TryAutoStart()
        {
            return TryAutoStart(null);
        }

        public static bool TryAutoStart(GtexMatchConfig config, bool allowLocalSimulationInBatchMode = false)
        {
            if (Object.FindFirstObjectByType<GtexMatchRuntime>() != null ||
                Object.FindFirstObjectByType<GtexSimRuntimeHost>() != null)
            {
                return true;
            }

            var resolvedConfig = config ?? GtexMatchConfigLoader.Load();
            if (resolvedConfig == null || !resolvedConfig.CanAutoStartSelectedRuntime)
            {
                return false;
            }

            var runtimeMode = resolvedConfig.ResolveRuntimeMode();
            livePlaybackRequested = runtimeMode == GtexRuntimeMode.LivePlayback;
            Debug.Log("[GTEX] Runtime bootstrap requested -> " + runtimeMode + ".");
            var started = GtexMatchController.TryAutoStart(resolvedConfig, allowLocalSimulationInBatchMode);
            if (!started)
            {
                livePlaybackRequested = false;
            }

            return started;
        }
    }
}
