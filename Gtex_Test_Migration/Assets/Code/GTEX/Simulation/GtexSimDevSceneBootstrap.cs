using FStudio.GTEX.Core;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace FStudio.GTEX.Simulation
{
    public static class GtexSimDevSceneBootstrap
    {
        private static GtexMatchConfig pendingLiveConfig;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void TryBootstrap()
        {
            if (Application.isBatchMode)
            {
                return;
            }

            var config = GtexMatchConfigLoader.Load();
            if (config == null)
            {
                return;
            }

            var activeScene = SceneManager.GetActiveScene();
            if (!activeScene.IsValid())
            {
                return;
            }

            var runtimeMode = config.ResolveRuntimeMode();

            if (runtimeMode == GtexRuntimeMode.LivePlayback)
            {
                var liveConfig = pendingLiveConfig ?? config;

                if (string.Equals(activeScene.name, GtexSceneLoader.DevelopmentSceneName) ||
                    string.Equals(activeScene.name, GtexSceneLoader.BuildSceneName))
                {
                    pendingLiveConfig = liveConfig;
                    Debug.Log(
                        "[GTEX Runtime Bootstrap] Redirecting live playback from scene '" +
                        activeScene.name +
                        "' to '" +
                        GtexSceneLoader.ProductionSceneName +
                        "'.");
                    SceneManager.LoadScene(GtexSceneLoader.ProductionSceneName);
                    return;
                }

                if (Object.FindFirstObjectByType<GtexMatchRuntime>() != null)
                {
                    pendingLiveConfig = null;
                    return;
                }

                if (GtexRuntimeBootstrap.TryAutoStart(liveConfig))
                {
                    pendingLiveConfig = null;
                    Debug.Log(
                        "[GTEX Runtime Bootstrap] " +
                        runtimeMode +
                        " auto-started for scene '" +
                        activeScene.name +
                        "'.");
                }

                return;
            }

            if (!string.Equals(activeScene.name, GtexSceneLoader.DevelopmentSceneName) &&
                !string.Equals(activeScene.name, GtexSceneLoader.BuildSceneName))
            {
                return;
            }

            if (Object.FindFirstObjectByType<GtexSimRuntimeHost>() != null ||
                Object.FindFirstObjectByType<GtexMatchRuntime>() != null)
            {
                return;
            }

            if (GtexRuntimeBootstrap.TryAutoStart(config))
            {
                Debug.Log(
                    "[GTEX Runtime Bootstrap] " +
                    runtimeMode +
                    " auto-started for scene '" +
                    activeScene.name +
                    "'.");
            }
        }
    }
}
