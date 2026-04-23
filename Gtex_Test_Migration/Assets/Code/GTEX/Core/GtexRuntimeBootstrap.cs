using System;
using FStudio.GTEX;
using FStudio.GTEX.Engine;
using FStudio.GTEX.Simulation;
using FStudio.MatchEngine;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace FStudio.GTEX.Core
{
    public static class GtexRuntimeBootstrap
    {
        private static bool livePlaybackRequested;

        public static bool IsLivePlaybackPendingOrActive()
        {
            if (UnityEngine.Object.FindFirstObjectByType<GtexMatchRuntime>() != null)
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
            if (UnityEngine.Object.FindFirstObjectByType<GtexMatchRuntime>() != null ||
                UnityEngine.Object.FindFirstObjectByType<GtexSimRuntimeHost>() != null)
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
            var activeSceneName = SceneManager.GetActiveScene().name;
            Debug.Log(
                "[GTEX] Runtime bootstrap requested -> " +
                runtimeMode +
                " in scene '" +
                activeSceneName +
                "' (matchId='" +
                resolvedConfig.matchId +
                "', baseUrl='" +
                resolvedConfig.ResolveBaseUrl() +
                "', localSim3DPlaybackRequested=" +
                resolvedConfig.use3DPlaybackForLocalSimulation +
                ").");
            if (runtimeMode == GtexRuntimeMode.LocalSimulation &&
                string.Equals(activeSceneName, "Gtex_MainScene", StringComparison.Ordinal) &&
                !resolvedConfig.allowLocalSimulationInProductionScene)
            {
                Debug.LogError(
                    "[GTEX] Refusing to auto-start LocalSimulation in Gtex_MainScene. " +
                    "Set allowLocalSimulationInProductionScene=true to override.");
                return false;
            }

            var started = GtexMatchController.TryAutoStart(resolvedConfig, allowLocalSimulationInBatchMode);
            Debug.Log("[GTEX] Runtime bootstrap result -> " + runtimeMode + " started=" + started + ".");
            if (!started)
            {
                livePlaybackRequested = false;
            }

            return started;
        }
    }
}
