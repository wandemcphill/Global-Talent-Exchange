using FStudio.GTEX.Core;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace FStudio.GTEX.Simulation
{
    public static class GtexSimDevSceneBootstrap
    {
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
                    config.ResolveRuntimeMode() +
                    " auto-started for scene '" +
                    activeScene.name +
                    "'.");
            }
        }
    }
}
