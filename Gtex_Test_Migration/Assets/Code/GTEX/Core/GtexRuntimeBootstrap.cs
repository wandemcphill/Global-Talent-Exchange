using System;
using FStudio.GTEX;
using FStudio.GTEX.Engine;
using FStudio.GTEX.Illusion;
using FStudio.GTEX.Simulation;
using FStudio.GTEX.VisualBridge;
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

        public static bool IsOriginalVisualRuntimeActive()
        {
            var director = UnityEngine.Object.FindFirstObjectByType<GtexVisualMatchDirector>();
            return GtexRuntimeFlags.IsOriginalVisualRuntime ||
                   (director != null && director.IsRuntimeReady) ||
                   GtexMatchController.CurrentState.RuntimeMode == GtexRuntimeMode.OriginalVisualRuntime;
        }

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
            if ((runtimeMode == GtexRuntimeMode.LivePlayback &&
                 UnityEngine.Object.FindFirstObjectByType<GtexMatchRuntime>() != null) ||
                (runtimeMode == GtexRuntimeMode.LocalSimulation &&
                 UnityEngine.Object.FindFirstObjectByType<GtexSimRuntimeHost>() != null) ||
                (runtimeMode == GtexRuntimeMode.IllusionRuntime &&
                 UnityEngine.Object.FindFirstObjectByType<GtexIllusionRuntimeHost>() != null))
            {
                return true;
            }

            if (runtimeMode == GtexRuntimeMode.OriginalVisualRuntime ||
                GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntimeScene())
            {
                Debug.Log("[GTEX Runtime Bootstrap] OriginalVisualRuntime requested.");

                var director = UnityEngine.Object.FindFirstObjectByType<GtexVisualMatchDirector>();
                if (director == null)
                {
                    Debug.LogError("[GTEX Runtime Bootstrap] No GtexVisualMatchDirector found in OriginalVisualRuntime scene.");
                    return false;
                }

                director.Initialize(resolvedConfig);
                return true;
            }

            if (runtimeMode == GtexRuntimeMode.IllusionRuntime)
            {
                Debug.Log("[GTEX Runtime Bootstrap] IllusionRuntime requested.");
                var illusionStarted = GtexIllusionRuntimeHost.TryAutoStart(resolvedConfig, allowLocalSimulationInBatchMode);
                Debug.Log("[GTEX Runtime Bootstrap] IllusionRuntime started=" + illusionStarted + ".");
                return illusionStarted;
            }

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
